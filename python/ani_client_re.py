"""Client ANI stream walker + decoder RE (read-only FantaTennis.exe). Stock never written.

Layout (Niki): [0:12) n0,n1,n2 dword counts; [12:28) mini-header; [28:12+n1×4)
sequential float3 clips; [12+n1×4:) 129 B motion-name records. VAs: 0x5DE920,
0x5E0EE0, 0x608E70, 0x5DD640 (float4), 0x5E08D0.
"""

from __future__ import annotations

import math
import struct
from typing import Any, Final

_CONFIDENT: Final = 0.9
_UNIT_LO: Final = 0.95
_UNIT_HI: Final = 1.05
_NAME_REC: Final = 129

CLIENT_VAS: Final[dict[str, int]] = {
    "aniExtensionGate": 0x5DE920,
    "readFloat4xn": 0x5DD640,
    "denseTrackLoad": 0x5E08D0,
    "streamThreeU32BulkLoad": 0x5E0EE0,
    "bindStreamCursors": 0x608E70,
}

RUNTIME_CHANNELS: Final[tuple[dict[str, Any], ...]] = (
    {"name": "float3", "floatsPerSample": 3, "role": "position", "readerVa": 0x5DD620},
    {"name": "float4", "floatsPerSample": 4, "role": "rotation", "readerVa": 0x5DD640},
    {"name": "float7", "floatsPerSample": 7, "role": "unknown", "readerVa": 0x5DD680},
)


def _is_unit(q: tuple[float, float, float, float]) -> bool:
    if not all(math.isfinite(v) for v in q):
        return False
    length = math.sqrt(sum(v * v for v in q))
    return _UNIT_LO <= length <= _UNIT_HI


def _unit_ratio_f4(blob: bytes, *, max_samples: int = 2000) -> float | None:
    n = len(blob) // 16
    if n <= 0:
        return None
    step = max(1, n // max_samples)
    unit = total = 0
    for i in range(0, n, step):
        q = struct.unpack_from("<4f", blob, i * 16)
        total += 1
        if _is_unit(q):
            unit += 1
    return unit / total if total else None


def probe_client_stream_header(data: bytes) -> dict[str, Any]:
    """Score the 12-byte dword-count stream header against file length."""
    if len(data) < 28:
        return {"viable": False, "note": "ANI shorter than 28 bytes", "fileBytes": len(data)}
    n0, n1, n2 = struct.unpack_from("<3I", data, 0)
    expected = n0 * 4 + 12
    size_match = expected == len(data)
    bulk = data[12 : 12 + min(n0 * 4, max(0, len(data) - 12))]
    mini: dict[str, Any] | None = None
    if len(bulk) >= 16:
        track_count = struct.unpack_from("<I", bulk, 0)[0]
        duration = struct.unpack_from("<f", bulk, 4)[0]
        fc1, fc2 = struct.unpack_from("<2I", bulk, 8)
        mini = {
            "trackCount": track_count,
            "duration": duration,
            "frameCount": fc1,
            "frameCount2": fc2,
            "plausible": (
                1 <= track_count <= 256
                and 1 <= fc1 <= 10_000
                and fc1 == fc2
                and 0.0 < duration < 600.0
            ),
        }
    return {
        "name": "stream-header-12b-dword-counts",
        "n0": n0,
        "n1": n1,
        "n2": n2,
        "fileBytes": len(data),
        "expectedFileBytes": expected,
        "sizeMatch": size_match,
        "tailDwords": max(0, n0 - n1) if n0 >= n1 else None,
        "tailBytes": (max(0, n0 - n1) * 4) if n0 >= n1 else None,
        "n0MinusN1": (n0 - n1) if n0 >= n1 else None,
        "bulkMiniHeader": mini,
        "viable": bool(size_match and mini and mini.get("plausible")),
        "note": (
            "First three LE u32 are dword counts; n0×4+12 == file size on Niki; "
            "n0−n1 is the name-table dword span (historic A−B=1290)."
        ),
    }


def _parse_name_table(table: bytes) -> list[dict[str, Any]]:
    """Parse fixed 129-byte motion name records at stream mid/end."""
    out: list[dict[str, Any]] = []
    if len(table) < _NAME_REC:
        return out
    n = len(table) // _NAME_REC
    for i in range(n):
        rec = table[i * _NAME_REC : (i + 1) * _NAME_REC]
        raw = rec.split(b"\0", 1)[0]
        try:
            name = raw.decode("ascii")
        except UnicodeDecodeError:
            name = raw.decode("latin-1", errors="replace")
        if not name:
            continue
        field16 = struct.unpack_from("<I", rec, 16)[0] if len(rec) >= 20 else None
        out.append({"index": i, "name": name, "fieldU32At16": field16})
    return out


def walk_client_bulk(data: bytes) -> dict[str, Any]:
    """Walk ANI bulk with client stream semantics; score float4 extract candidates."""
    header = probe_client_stream_header(data)
    if not header.get("viable"):
        return {
            "ok": False,
            "streamHeader": header,
            "confidentExtract": False,
            "note": "stream header not viable",
        }
    n1 = int(header["n1"])
    mini = header["bulkMiniHeader"] or {}
    track_count = int(mini["trackCount"])
    frame_count = int(mini["frameCount"])
    f3 = track_count * frame_count * 12
    f4 = track_count * frame_count * 16
    main_end = 12 + n1 * 4
    payload_start = 28
    float3_clips = 0
    off = payload_start
    while off + f3 <= main_end:
        float3_clips += 1
        off += f3
    remainder = data[off:main_end]
    motions = _parse_name_table(data[main_end:])
    best_r, best_off = 0.0, None
    step = max(256, f4 // 4)
    for scan_off in range(payload_start, max(payload_start, main_end - f4) + 1, step):
        ratio = _unit_ratio_f4(data[scan_off : scan_off + f4])
        if ratio is not None and ratio > best_r:
            best_r, best_off = ratio, scan_off
            if ratio >= _CONFIDENT:
                break
    mid_start = payload_start + 16 * f3
    mid = data[mid_start:main_end] if mid_start < main_end else b""
    confident = bool(best_off is not None and best_r >= _CONFIDENT)
    return {
        "ok": True,
        "streamHeader": header,
        "payloadStart": payload_start,
        "mainEnd": main_end,
        "float3BlockBytes": f3,
        "float4BlockBytes": f4,
        "sequentialFloat3Clips": float3_clips,
        "float3RegionBytes": float3_clips * f3,
        "remainderAfterFloat3Clips": len(remainder),
        "remainderFileOffset": off,
        "motionNames": motions,
        "motionNameCount": len(motions),
        "nameRecordBytes": _NAME_REC,
        "denseFloat4Scan": {
            "bestUnitRatio": best_r if best_off is not None else None,
            "bestFileOffset": best_off,
            "blockBytes": f4,
        },
        "midAfter16Float3Clips": {
            "fileOffset": mid_start,
            "bytes": len(mid),
            "unitRatioSample": _unit_ratio_f4(mid) if mid else None,
        },
        "confidentExtract": confident,
        "recommendedDriveMode": "quat" if confident else "hierarchical-fk",
        "note": (
            f"Main region: {float3_clips} sequential float3 clips ({f3}B); "
            f"name table {len(motions)}×{_NAME_REC}B; dense float4 best unit "
            f"ratio={best_r:.3f} (need ≥{_CONFIDENT})."
        ),
    }


def try_extract_from_client_walk(
    data: bytes, *, track_count: int, frame_count: int
) -> tuple[list[list[list[float]]] | None, dict[str, Any]]:
    """Extract dense float4 only when walk scan hits unit ratio ≥ 0.9."""
    walk = walk_client_bulk(data)
    meta: dict[str, Any] = {
        "source": "client-bulk-walk",
        "confident": False,
        "walk": {
            k: walk.get(k)
            for k in (
                "sequentialFloat3Clips",
                "motionNameCount",
                "denseFloat4Scan",
                "confidentExtract",
            )
        },
    }
    scan = walk.get("denseFloat4Scan") or {}
    off = scan.get("bestFileOffset")
    ratio = scan.get("bestUnitRatio")
    if off is None or ratio is None or float(ratio) < _CONFIDENT:
        meta["note"] = walk.get("note")
        return None, meta
    need = track_count * frame_count * 16
    blob = data[int(off) : int(off) + need]
    if len(blob) < need:
        return None, meta
    tracks: list[list[list[float]]] = [[] for _ in range(track_count)]
    unit = total = 0
    for ti in range(track_count):
        for fi in range(frame_count):
            q = list(struct.unpack_from("<4f", blob, (ti * frame_count + fi) * 16))
            if not all(math.isfinite(v) for v in q):
                return None, {**meta, "note": "non-finite in extract"}
            length = math.sqrt(sum(v * v for v in q))
            total += 1
            if _UNIT_LO <= length <= _UNIT_HI:
                unit += 1
            tracks[ti].append(q)
    decode_ratio = unit / total if total else 0.0
    meta["selectedOffset"] = int(off)
    meta["decodeUnitRatio"] = decode_ratio
    meta["order"] = "track-major"
    if decode_ratio < _CONFIDENT:
        meta["note"] = f"block unit {decode_ratio:.3f} < {_CONFIDENT}"
        return None, meta
    meta["confident"] = True
    meta["note"] = f"client-walk dense float4 @+{off} ratio={decode_ratio:.3f}"
    return tracks, meta


def build_client_decoder_hypothesis(data: bytes) -> dict[str, Any]:
    """API sectionProbe.clientDecoderHypothesis payload including bulk walk."""
    walk = walk_client_bulk(data)
    confident = bool(walk.get("confidentExtract"))
    return {
        "source": "FantaTennis.exe static RE + bulk cursor walk (read-only)",
        "imageBase": 0x400000,
        "vas": {k: f"0x{v:08X}" for k, v in CLIENT_VAS.items()},
        "runtimeChannels": list(RUNTIME_CHANNELS),
        "streamHeader": walk.get("streamHeader") or probe_client_stream_header(data),
        "bulkWalk": walk,
        "rotationChannel": {
            "encoding": "float4",
            "readerVa": "0x5DD640",
            "denseLoadVa": "0x5E08D0",
            "confidentExtract": confident,
            "bestUnitRatio": (walk.get("denseFloat4Scan") or {}).get("bestUnitRatio"),
            "note": (
                "Runtime float4; on-disk main region is sequential float3 clips + "
                "129B motion names; dense float4 unit <0.9 on Niki → hierarchical-fk."
            ),
        },
        "viableRotationEncoding": "client-bulk-dense-float4" if confident else None,
        "recommendedDriveMode": "quat" if confident else "hierarchical-fk",
        "note": walk.get("note") or "No confident on-disk float4 extract.",
    }
