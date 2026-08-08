"""Exhaustive rotation-channel probes for Fantasy Tennis .ani sections.

Section B matches C’s byte length (A−B=1290 on Niki) but is not plain float3/float4.
This module scores candidate encodings and reports whether any yield a confident
unit-quaternion graph (unit ratio ≥ 0.9 over trackCount×frameCount samples).
"""

from __future__ import annotations

import math
import struct
import zlib
from typing import Any

# Keep in sync with ani_codec.AniHeader fields used here.
_UNIT_LO = 0.95
_UNIT_HI = 1.05
_CONFIDENT = 0.9


def _float3_block(track_count: int, frame_count: int) -> int:
    return track_count * frame_count * 12


def _float4_block(track_count: int, frame_count: int) -> int:
    return track_count * frame_count * 16


def _unit_ratio_float4(blob: bytes, *, max_samples: int = 4000) -> float | None:
    n = len(blob) // 16
    if n <= 0:
        return None
    step = max(1, n // max_samples)
    unit = 0
    total = 0
    for i in range(0, n, step):
        q = struct.unpack_from("<4f", blob, i * 16)
        if not all(math.isfinite(v) for v in q):
            continue
        total += 1
        length = math.sqrt(sum(v * v for v in q))
        if _UNIT_LO <= length <= _UNIT_HI:
            unit += 1
    return (unit / total) if total else None


def _s16_xyz_compress_ratio(blob: bytes, *, max_samples: int = 8000) -> float | None:
    n = len(blob) // 6
    if n <= 0:
        return None
    step = max(1, n // max_samples)
    ok = 0
    total = 0
    for i in range(0, n, step):
        x, y, z = struct.unpack_from("<3h", blob, i * 6)
        xf, yf, zf = x / 32767.0, y / 32767.0, z / 32767.0
        m2 = xf * xf + yf * yf + zf * zf
        total += 1
        if 0.0 <= m2 <= 1.001:
            ok += 1
    return (ok / total) if total else None


def _s16_float4_unit_ratio(blob: bytes, *, max_samples: int = 4000) -> float | None:
    n = len(blob) // 8
    if n <= 0:
        return None
    step = max(1, n // max_samples)
    unit = 0
    total = 0
    for i in range(0, n, step):
        x, y, z, w = struct.unpack_from("<4h", blob, i * 8)
        q = (x / 32767.0, y / 32767.0, z / 32767.0, w / 32767.0)
        total += 1
        length = math.sqrt(sum(v * v for v in q))
        if _UNIT_LO <= length <= _UNIT_HI:
            unit += 1
    return (unit / total) if total else None


def _f16_float4_unit_ratio(blob: bytes, *, max_samples: int = 4000) -> float | None:
    # Half-float via struct may be unavailable on older Python; use int bitcast.
    try:
        import numpy as np
    except ImportError:
        return None
    n = len(blob) // 2
    if n < 4:
        return None
    arr = np.frombuffer(blob[: n * 2], dtype="<f2").astype(np.float64)
    nq = (len(arr) // 4) * 4
    if nq <= 0:
        return None
    qs = arr[:nq].reshape(-1, 4)
    finite = np.all(np.isfinite(qs), axis=1)
    qs = qs[finite]
    if len(qs) == 0:
        return None
    step = max(1, len(qs) // max_samples)
    qs = qs[::step]
    norms = np.linalg.norm(qs, axis=1)
    return float(np.mean((norms >= _UNIT_LO) & (norms <= _UNIT_HI)))


def _float3_finite_ratio(blob: bytes, track_count: int, frame_count: int) -> float | None:
    need = _float3_block(track_count, frame_count)
    if len(blob) < need:
        return None
    total = track_count * frame_count
    ok = 0
    for i in range(total):
        p = struct.unpack_from("<3f", blob, i * 12)
        if all(math.isfinite(v) and abs(v) < 500 for v in p):
            ok += 1
    return ok / total if total else None


def _zlib_raw_score(blob: bytes) -> dict[str, Any]:
    for skip in (0, 1, 2, 4, 8, 16):
        try:
            out = zlib.decompress(blob[skip:], -15)
            if len(out) >= 64:
                return {
                    "viable": True,
                    "skip": skip,
                    "decompressedBytes": len(out),
                    "note": "zlib raw inflate produced payload",
                }
        except zlib.error:
            continue
    return {"viable": False, "note": "zlib raw inflate failed for skips 0..16"}


def _phase_float4_unit_ratios(blob: bytes) -> list[dict[str, Any]]:
    """Unit ratio of float4 streams at byte phases 0..3 (odd sections need phase hunt)."""
    out: list[dict[str, Any]] = []
    for phase in range(4):
        ratio = _unit_ratio_float4(blob[phase:])
        out.append(
            {
                "phase": phase,
                "unitRatio": ratio,
                "viable": bool(ratio is not None and ratio >= _CONFIDENT),
            }
        )
    return out


def _first_clip_float4_unit(
    blob: bytes, track_count: int, frame_count: int
) -> list[dict[str, Any]]:
    """Unit ratio of the first trackCount×frameCount float4 block at each phase."""
    need = _float4_block(track_count, frame_count)
    out: list[dict[str, Any]] = []
    for phase in range(4):
        chunk = blob[phase : phase + need]
        if len(chunk) < need:
            out.append({"phase": phase, "unitRatio": None, "viable": False})
            continue
        ratio = _unit_ratio_float4(chunk, max_samples=track_count * frame_count)
        out.append(
            {
                "phase": phase,
                "unitRatio": ratio,
                "viable": bool(ratio is not None and ratio >= _CONFIDENT),
            }
        )
    return out


def _bit48_unitish_ratio(blob: bytes, n_samples: int) -> float | None:
    """3×15-bit components + 2-bit index (LE bit order) reconstructable unitish ratio."""
    need_bytes = (n_samples * 48 + 7) // 8
    if len(blob) < need_bytes or n_samples <= 0:
        return None
    bits: list[int] = []
    for b in blob[:need_bytes]:
        for i in range(8):
            bits.append((b >> i) & 1)
    ok = 0
    for i in range(n_samples):
        base = i * 48
        if base + 48 > len(bits):
            break
        comps: list[float] = []
        for c in range(3):
            v = 0
            for bi in range(15):
                v |= bits[base + 2 + c * 15 + bi] << bi
            comps.append((v - 16384) / 16384.0)
        m2 = sum(x * x for x in comps)
        if m2 <= 1.0:
            ok += 1
    return ok / n_samples


def _scan_contiguous_float4_block(
    data: bytes,
    *,
    track_count: int,
    frame_count: int,
    search_start: int,
    search_end: int,
    step: int = 256,
) -> dict[str, Any]:
    """Scan for a contiguous trackCount×frameCount float4 block with high unit ratio."""
    need = _float4_block(track_count, frame_count)
    best: tuple[float, int] | None = None
    if search_end - search_start < need:
        return {"viable": False, "bestUnitRatio": None, "bestOffset": None}
    for off in range(search_start, search_end - need + 1, step):
        ratio = _unit_ratio_float4(data[off : off + need], max_samples=track_count * frame_count)
        if ratio is None:
            continue
        if best is None or ratio > best[0]:
            best = (ratio, off)
            if ratio >= _CONFIDENT:
                break
    if best is None:
        return {"viable": False, "bestUnitRatio": None, "bestOffset": None}
    return {
        "viable": best[0] >= _CONFIDENT,
        "bestUnitRatio": best[0],
        "bestOffset": best[1],
        "blockBytes": need,
    }


def probe_section_b(
    data: bytes,
    *,
    section_a: int,
    section_b: int,
    section_c: int,
    track_count: int,
    frame_count: int,
) -> dict[str, Any]:
    """Score section B encoding candidates; set viableRotationEncoding if confident."""
    off_b = 28 + section_a
    blob = data[off_b : off_b + section_b] if off_b + section_b <= len(data) else b""
    candidates: list[dict[str, Any]] = []

    f3 = _float3_finite_ratio(blob, track_count, frame_count)
    candidates.append(
        {
            "name": "float3-dense-first-clip",
            "finiteRatio": f3,
            "viable": bool(f3 is not None and f3 >= 0.95),
        }
    )

    f4 = _unit_ratio_float4(blob)
    candidates.append(
        {
            "name": "float4-unit-sample",
            "unitRatio": f4,
            "viable": bool(f4 is not None and f4 >= _CONFIDENT),
        }
    )

    s16_4 = _s16_float4_unit_ratio(blob)
    candidates.append(
        {
            "name": "s16-float4-div32767",
            "unitRatio": s16_4,
            "viable": bool(s16_4 is not None and s16_4 >= _CONFIDENT),
        }
    )

    s16_3 = _s16_xyz_compress_ratio(blob)
    candidates.append(
        {
            "name": "s16-xyz-compressed-quat",
            "unitishRatio": s16_3,
            "viable": bool(s16_3 is not None and s16_3 >= _CONFIDENT),
        }
    )

    f16 = _f16_float4_unit_ratio(blob)
    candidates.append(
        {
            "name": "f16-float4-unit",
            "unitRatio": f16,
            "viable": bool(f16 is not None and f16 >= _CONFIDENT),
        }
    )

    z = _zlib_raw_score(blob)
    candidates.append({"name": "zlib-raw-inflate", **z})

    # Even-length drop last odd padding byte
    even = blob[:-1] if len(blob) % 2 == 1 else blob
    f4e = _unit_ratio_float4(even)
    candidates.append(
        {
            "name": "float4-unit-drop-odd-pad",
            "unitRatio": f4e,
            "viable": bool(f4e is not None and f4e >= _CONFIDENT),
        }
    )

    # Contiguous float4 block inside B only (whole-file scan is offline RE; too slow for API)
    scan_b = _scan_contiguous_float4_block(
        data,
        track_count=track_count,
        frame_count=frame_count,
        search_start=off_b,
        search_end=off_b + len(blob),
        step=2048,
    )
    candidates.append({"name": "contiguous-float4-block-in-B", **scan_b})
    # Offline RE note: whole-file scan (step 4096) on NikiAniA best unit ratio ≈0.61 < 0.9
    candidates.append(
        {
            "name": "contiguous-float4-block-whole-file",
            "viable": False,
            "bestUnitRatio": None,
            "bestOffset": None,
            "skipped": True,
            "note": (
                "Skipped in API path for latency; offline RE: NikiAniA best ≈0.61 unit "
                "(not confident)"
            ),
        }
    )

    # Odd-size phase hunt (B is odd-length; phase1 often looks float-like)
    phase_ratios = _phase_float4_unit_ratios(blob)
    candidates.append(
        {
            "name": "float4-unit-byte-phases",
            "phases": phase_ratios,
            "viable": any(p.get("viable") for p in phase_ratios),
            "bestPhaseUnitRatio": max(
                (p.get("unitRatio") or 0.0) for p in phase_ratios
            ),
        }
    )
    clip_phases = _first_clip_float4_unit(blob, track_count, frame_count)
    candidates.append(
        {
            "name": "float4-first-clip-byte-phases",
            "phases": clip_phases,
            "viable": any(p.get("viable") for p in clip_phases),
            "bestPhaseUnitRatio": max(
                (p.get("unitRatio") or 0.0) for p in clip_phases
            ),
        }
    )
    # Also try blob[1:] (drop leading odd pad) first-clip
    if len(blob) % 2 == 1:
        clip_drop = _first_clip_float4_unit(blob[1:], track_count, frame_count)
        candidates.append(
            {
                "name": "float4-first-clip-drop-leading-byte",
                "phases": clip_drop,
                "viable": any(p.get("viable") for p in clip_drop),
                "bestPhaseUnitRatio": max(
                    (p.get("unitRatio") or 0.0) for p in clip_drop
                ),
            }
        )

    n_tf = track_count * frame_count
    b48 = _bit48_unitish_ratio(blob, n_tf)
    candidates.append(
        {
            "name": "bitstream-48bit-3x15-plus-index",
            "unitishRatio": b48,
            "viable": bool(b48 is not None and b48 >= _CONFIDENT),
        }
    )
    b48_16 = _bit48_unitish_ratio(blob, n_tf * 16)
    candidates.append(
        {
            "name": "bitstream-48bit-16clips",
            "unitishRatio": b48_16,
            "viable": bool(b48_16 is not None and b48_16 >= _CONFIDENT),
        }
    )

    # Phase-shifted sparse / keyframe / delta (odd B length → phase 1 often float-aligned)
    from ani_sparse_probe import score_sparse_phase_b

    sparse = score_sparse_phase_b(
        blob, track_count=track_count, frame_count=frame_count, phase=1
    )
    candidates.extend(sparse)

    viable = next((c["name"] for c in candidates if c.get("viable")), None)
    return {
        "offset": off_b,
        "size": section_b,
        "sameSizeAsC": section_b == section_c,
        "sectionAMinusB": section_a - section_b,
        "oddSized": section_b % 2 == 1,
        "candidates": candidates,
        "viableRotationEncoding": viable,
        "note": (
            f"Viable rotation encoding: {viable}"
            if viable
            else (
                "No confident rotation encoding in section B (or whole-file dense float4 "
                "block). Tried float3/float4, s16 quat, s16 xyz-compress, f16, zlib-raw, "
                "odd-pad drop, contiguous float4 scans, byte-phase/bitstream, and "
                "phase1 sparse/keyframe/delta harvests. Prefer hierarchical-fk drive."
            )
        ),
    }


def probe_tail(
    data: bytes,
    *,
    section_a: int,
    section_b: int,
    section_c: int,
    track_count: int,
    frame_count: int,
) -> dict[str, Any]:
    """Score tail residual after A|B|C for rotation / float packing candidates."""
    off_t = 28 + section_a + section_b + section_c
    blob = data[off_t:] if off_t < len(data) else b""
    candidates: list[dict[str, Any]] = []

    f3 = _float3_finite_ratio(blob, track_count, frame_count)
    candidates.append(
        {
            "name": "float3-dense-first-clip",
            "finiteRatio": f3,
            "viable": bool(f3 is not None and f3 >= 0.95),
        }
    )
    f4 = _unit_ratio_float4(blob)
    candidates.append(
        {
            "name": "float4-unit-sample",
            "unitRatio": f4,
            "viable": bool(f4 is not None and f4 >= _CONFIDENT),
        }
    )
    z = _zlib_raw_score(blob)
    candidates.append({"name": "zlib-raw-inflate", **z})
    phase_ratios = _phase_float4_unit_ratios(blob)
    candidates.append(
        {
            "name": "float4-unit-byte-phases",
            "phases": phase_ratios,
            "viable": any(p.get("viable") for p in phase_ratios),
            "bestPhaseUnitRatio": max(
                (p.get("unitRatio") or 0.0) for p in phase_ratios
            ),
        }
    )
    clip_phases = _first_clip_float4_unit(blob, track_count, frame_count)
    candidates.append(
        {
            "name": "float4-first-clip-byte-phases",
            "phases": clip_phases,
            "viable": any(p.get("viable") for p in clip_phases),
            "bestPhaseUnitRatio": max(
                (p.get("unitRatio") or 0.0) for p in clip_phases
            ),
        }
    )
    n_tf = track_count * frame_count
    t48 = _bit48_unitish_ratio(blob, n_tf)
    candidates.append(
        {
            "name": "bitstream-48bit-3x15-plus-index",
            "unitishRatio": t48,
            "viable": bool(t48 is not None and t48 >= _CONFIDENT),
        }
    )

    viable = next((c["name"] for c in candidates if c.get("viable")), None)
    return {
        "offset": off_t,
        "size": len(blob),
        "oddSized": len(blob) % 2 == 1,
        "candidates": candidates,
        "viableRotationEncoding": viable,
        "note": (
            f"Viable tail rotation encoding: {viable}"
            if viable
            else (
                "Tail residual is high-entropy and not a clean float3 multi-clip or "
                "confident unit-float4 stream (phase hunt ~56% unit max on Niki). "
                "Encoding unknown (possible custom compression)."
            )
        ),
    }


def try_extract_confident_quats(
    data: bytes,
    *,
    track_count: int,
    frame_count: int,
    section_a: int,
    section_b: int,
    section_c: int,
    b_probe: dict[str, Any] | None = None,
) -> tuple[list[list[list[float]]] | None, dict[str, Any]]:
    """If a confident dense float4 block exists, return tracks[track][frame]=xyzw."""
    probe = b_probe or probe_section_b(
        data,
        section_a=section_a,
        section_b=section_b,
        section_c=section_c,
        track_count=track_count,
        frame_count=frame_count,
    )
    # Prefer whole-file or B contiguous block hit from probe
    best_off: int | None = None
    best_ratio = 0.0
    for c in probe.get("candidates") or []:
        if c.get("name", "").startswith("contiguous-float4-block") and c.get(
            "bestUnitRatio"
        ) is not None:
            r = float(c["bestUnitRatio"])
            if r > best_ratio:
                best_ratio = r
                best_off = c.get("bestOffset")
    # Classic C section start (first float4 block) if unit ratio high
    c_off = 28 + section_a + section_b
    need = _float4_block(track_count, frame_count)
    if c_off + need <= len(data):
        c_ratio = _unit_ratio_float4(data[c_off : c_off + need], max_samples=track_count * frame_count)
        if c_ratio is not None and c_ratio >= _CONFIDENT and c_ratio > best_ratio:
            best_ratio = c_ratio
            best_off = c_off

    meta: dict[str, Any] = {
        "selectedOffset": best_off,
        "selectedUnitRatio": best_ratio if best_off is not None else None,
        "confident": bool(best_off is not None and best_ratio >= _CONFIDENT),
    }
    if best_off is None or best_ratio < _CONFIDENT:
        return None, meta

    need = _float4_block(track_count, frame_count)
    blob = data[best_off : best_off + need]
    # Decode track-major then frame-major; pick higher unit ratio path
    def decode(order: str) -> tuple[list[list[list[float]]], float] | None:
        tracks: list[list[list[float]]] = [[] for _ in range(track_count)]
        unit = total = 0
        if order == "track-major":
            for ti in range(track_count):
                for fi in range(frame_count):
                    q = list(struct.unpack_from("<4f", blob, (ti * frame_count + fi) * 16))
                    if not all(math.isfinite(v) for v in q):
                        return None
                    length = math.sqrt(sum(v * v for v in q))
                    total += 1
                    if _UNIT_LO <= length <= _UNIT_HI:
                        unit += 1
                    tracks[ti].append(q)
        else:
            for fi in range(frame_count):
                for ti in range(track_count):
                    q = list(struct.unpack_from("<4f", blob, (fi * track_count + ti) * 16))
                    if not all(math.isfinite(v) for v in q):
                        return None
                    length = math.sqrt(sum(v * v for v in q))
                    total += 1
                    if _UNIT_LO <= length <= _UNIT_HI:
                        unit += 1
                    tracks[ti].append(q)
        ratio = unit / total if total else 0.0
        return tracks, ratio

    tm = decode("track-major")
    fm = decode("frame-major")
    chosen: tuple[list[list[list[float]]], float] | None = None
    order: str | None = None
    if tm and fm:
        if tm[1] >= fm[1]:
            chosen, order = tm, "track-major"
        else:
            chosen, order = fm, "frame-major"
    elif tm:
        chosen, order = tm, "track-major"
    elif fm:
        chosen, order = fm, "frame-major"
    if chosen is None or chosen[1] < _CONFIDENT:
        meta["confident"] = False
        meta["decodeNote"] = "block found but ordered decode unit ratio < 0.9"
        return None, meta
    meta["order"] = order
    meta["decodeUnitRatio"] = chosen[1]
    meta["confident"] = True
    return chosen[0], meta
