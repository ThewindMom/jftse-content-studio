"""Sparse/keyframe/delta scorers for phase-shifted ANI section B. Viable only at ≥0.9."""

from __future__ import annotations

import math
import struct
from typing import Any, Final

_UNIT_LO: Final = 0.95
_UNIT_HI: Final = 1.05
_CONFIDENT: Final = 0.9


def _is_unit(q: tuple[float, float, float, float]) -> bool:
    if not all(math.isfinite(v) for v in q):
        return False
    length = math.sqrt(sum(v * v for v in q))
    return _UNIT_LO <= length <= _UNIT_HI


def _read_float4s(blob: bytes) -> list[tuple[float, float, float, float]]:
    return [struct.unpack_from("<4f", blob, i * 16) for i in range(len(blob) // 16)]


def _unit_mask(quats: list[tuple[float, float, float, float]]) -> list[bool]:
    return [_is_unit(q) for q in quats]


def _run_lengths(mask: list[bool]) -> list[int]:
    lengths: list[int] = []
    run = 0
    for u in mask + [False]:
        if u:
            run += 1
        elif run:
            lengths.append(run)
            run = 0
    return lengths


def _hist_top(values: list[int], n: int = 12) -> dict[int, int]:
    hist: dict[int, int] = {}
    for v in values:
        hist[v] = hist.get(v, 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: (-kv[1], -kv[0]))[:n])


def _unit_run_harvest(quats: list[tuple[float, float, float, float]]) -> dict[str, Any]:
    n = len(quats)
    if n == 0:
        return {
            "quatSlots": 0,
            "unitCount": 0,
            "unitRatio": None,
            "runLengthsTop": {},
            "gapHistTop": {},
            "medianGap": None,
        }
    mask = _unit_mask(quats)
    unit_count = sum(1 for u in mask if u)
    unit_idx = [i for i, u in enumerate(mask) if u]
    gaps = [b - a for a, b in zip(unit_idx, unit_idx[1:])]
    return {
        "quatSlots": n,
        "unitCount": unit_count,
        "unitRatio": unit_count / n,
        "runLengthsTop": _hist_top(_run_lengths(mask)),
        "gapHistTop": _hist_top(gaps) if gaps else {},
        "medianGap": float(sorted(gaps)[len(gaps) // 2]) if gaps else None,
    }


def _exact_nf_stats(
    quats: list[tuple[float, float, float, float]],
    frame_count: int,
) -> dict[str, Any]:
    if frame_count <= 0 or not quats:
        return {"exactNfRuns": 0, "nonConstRuns": 0, "meanMotion": None}
    mask = _unit_mask(quats)
    exact = non_const = 0
    motions: list[float] = []
    run = run_start = 0
    for i, u in enumerate(mask + [False]):
        if u:
            if run == 0:
                run_start = i
            run += 1
            continue
        if run == frame_count:
            exact += 1
            track = quats[run_start : run_start + frame_count]
            q0 = track[0]
            m = sum(
                math.sqrt(sum((a - b) ** 2 for a, b in zip(q, q0))) for q in track[1:]
            ) / max(1, frame_count - 1)
            motions.append(m)
            if m > 1e-4:
                non_const += 1
        run = 0
    return {
        "exactNfRuns": exact,
        "nonConstRuns": non_const,
        "meanMotion": (sum(motions) / len(motions)) if motions else None,
        "frameCount": frame_count,
    }


def _near_nf_count(
    quats: list[tuple[float, float, float, float]], frame_count: int
) -> int:
    if frame_count <= 2 or not quats:
        return 0
    near = 0
    for run in _run_lengths(_unit_mask(quats)):
        if abs(run - frame_count) <= 2 and run >= 4:
            near += 1
    return near


def _additive_delta_unit_ratio(
    quats: list[tuple[float, float, float, float]], *, max_samples: int = 4000
) -> float | None:
    if len(quats) < 2:
        return None
    step = max(1, (len(quats) - 1) // max_samples)
    unit = total = 0
    acc = list(quats[0])
    for i in range(1, len(quats), step):
        d = quats[i]
        if _is_unit(d):
            unit += 1
            acc = list(d)
        else:
            recon = (acc[0] + d[0], acc[1] + d[1], acc[2] + d[2], acc[3] + d[3])
            if _is_unit(recon):
                unit += 1
                acc = list(recon)
            elif all(math.isfinite(v) for v in d):
                acc = list(d)
        total += 1
    return unit / total if total else None


def _mul_delta_unit_ratio(
    quats: list[tuple[float, float, float, float]], *, max_samples: int = 4000
) -> float | None:
    if len(quats) < 2:
        return None
    step = max(1, (len(quats) - 1) // max_samples)
    unit = total = 0
    prev = quats[0]
    for i in range(1, len(quats), step):
        cur = quats[i]
        x1, y1, z1, w1 = cur
        x2, y2, z2, w2 = -prev[0], -prev[1], -prev[2], prev[3]
        dq = (
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        )
        if _is_unit(dq):
            unit += 1
        total += 1
        prev = cur
    return unit / total if total else None


def _window_unit_density(
    quats: list[tuple[float, float, float, float]],
    window: int,
    *,
    step: int = 16,
) -> dict[str, Any]:
    if window <= 0 or len(quats) < window:
        return {"bestDensity": None, "bestOffset": None, "viable": False, "window": window}
    best, best_off = 0.0, 0
    for off in range(0, len(quats) - window + 1, max(1, step)):
        dens = sum(1 for q in quats[off : off + window] if _is_unit(q)) / window
        if dens > best:
            best, best_off = dens, off
            if best >= _CONFIDENT:
                break
    return {
        "bestDensity": best,
        "bestOffset": best_off,
        "window": window,
        "viable": best >= _CONFIDENT,
    }


def _interleaved_pack_unit(
    blob: bytes, floats_per_sample: int, *, max_samples: int = 3000
) -> float | None:
    if floats_per_sample < 4:
        return None
    stride = floats_per_sample * 4
    n = len(blob) // stride
    if n <= 0:
        return None
    step = max(1, n // max_samples)
    unit = total = 0
    quat_off = (floats_per_sample - 4) * 4
    for i in range(0, n, step):
        q = struct.unpack_from("<4f", blob, i * stride + quat_off)
        total += 1
        if _is_unit(q):
            unit += 1
    return unit / total if total else None


def score_sparse_phase_b(
    blob: bytes, *, track_count: int, frame_count: int, phase: int = 1
) -> list[dict[str, Any]]:
    """encodingProbe candidates for phase-shifted sparse/delta B hypotheses."""
    phased = blob[phase:] if phase else blob
    quats = _read_float4s(phased)
    need = max(1, track_count)
    harvest = _unit_run_harvest(quats)
    ur = harvest.get("unitRatio")
    exact = _exact_nf_stats(quats, frame_count)
    cover = exact["exactNfRuns"] / need
    exact_viable = cover >= _CONFIDENT and (exact.get("nonConstRuns") or 0) >= need * 0.5
    add_r = _additive_delta_unit_ratio(quats)
    mul_r = _mul_delta_unit_ratio(quats)
    win = _window_unit_density(
        quats, window=track_count * frame_count, step=max(8, frame_count)
    )
    out: list[dict[str, Any]] = [
        {
            "name": "sparse-unit-run-harvest-phase1",
            "phase": phase,
            **harvest,
            "viable": bool(ur is not None and float(ur) >= _CONFIDENT),
        },
        {
            "name": "sparse-exact-nf-unit-runs",
            "phase": phase,
            **exact,
            "trackCoverage": cover,
            "trackCount": track_count,
            "viable": bool(exact_viable),
        },
        {
            "name": "sparse-near-nf-unit-runs",
            "phase": phase,
            "nearNfRuns": _near_nf_count(quats, frame_count),
            "frameCount": frame_count,
            "viable": False,
        },
        {
            "name": "float4-additive-delta-phase1",
            "phase": phase,
            "unitRatio": add_r,
            "viable": bool(add_r is not None and add_r >= _CONFIDENT),
        },
        {
            "name": "float4-mul-delta-phase1",
            "phase": phase,
            "unitRatio": mul_r,
            "viable": bool(mul_r is not None and mul_r >= _CONFIDENT),
        },
        {"name": "window-unit-density-phase1", "phase": phase, **win},
    ]
    for n_f in (5, 7):
        r = _interleaved_pack_unit(phased, n_f)
        out.append(
            {
                "name": f"interleaved-{n_f}f-quat-tail-phase1",
                "phase": phase,
                "floatsPerSample": n_f,
                "unitRatio": r,
                "viable": bool(r is not None and r >= _CONFIDENT),
            }
        )
    return out
