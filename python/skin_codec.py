"""Extract DX9-style skinned vertices from Fantasy Tennis body mesh DATs.

Verified layout on Niki.dat (56-byte records, little-endian):

    float  blendWeight[4]   @ +0    # sum ≈ 1, each in [0,1]
    uint16 blendIndex[4]    @ +16   # bone indices for nonzero weights
    float  position[3]      @ +24
    float  normal[3]        @ +36   # unit length
    float  uv[2]            @ +48

Records appear in multiple contiguous runs (submeshes). This recovers those
runs for equipment/skin preview work without claiming full AduMesh parity.
"""

from __future__ import annotations

import math
import struct
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bone_attach import _mesh_archive_rel, _prefer_body_member

RECORD_SIZE = 56


@dataclass
class SkinVertex:
    weights: list[float]
    indices: list[int]
    position: list[float]
    normal: list[float]
    uv: list[float]


@dataclass
class SkinRun:
    offset: int
    count: int
    vertices: list[SkinVertex]


def _is_skin_record(data: bytes, off: int) -> bool:
    if off < 0 or off + RECORD_SIZE > len(data):
        return False
    w = struct.unpack_from("<4f", data, off)
    if not all(math.isfinite(x) and -0.05 <= x <= 1.05 for x in w):
        return False
    if not (0.95 <= sum(w) <= 1.05) or max(w) < 0.2:
        return False
    idx = struct.unpack_from("<4H", data, off + 16)
    if not all((w[k] < 0.05) or (idx[k] < 128) for k in range(4)):
        return False
    n = struct.unpack_from("<3f", data, off + 36)
    if not all(math.isfinite(x) for x in n):
        return False
    length = math.sqrt(sum(x * x for x in n))
    if not (0.8 <= length <= 1.2):
        return False
    p = struct.unpack_from("<3f", data, off + 24)
    if not all(math.isfinite(x) and abs(x) < 500 for x in p):
        return False
    u, v = struct.unpack_from("<2f", data, off + 48)
    if not all(math.isfinite(x) and -5 <= x <= 5 for x in (u, v)):
        return False
    return True


def _read_vertex(data: bytes, off: int) -> SkinVertex:
    w = list(struct.unpack_from("<4f", data, off))
    idx = list(struct.unpack_from("<4H", data, off + 16))
    pos = list(struct.unpack_from("<3f", data, off + 24))
    nrm = list(struct.unpack_from("<3f", data, off + 36))
    uv = list(struct.unpack_from("<2f", data, off + 48))
    return SkinVertex(weights=w, indices=idx, position=pos, normal=nrm, uv=uv)


def find_skin_runs(
    data: bytes,
    *,
    scan_start: int | None = None,
    scan_end: int | None = None,
    max_runs: int = 512,
    max_vertices_per_run: int = 50_000,
) -> list[SkinRun]:
    """Scan DAT bytes for contiguous 56-byte skinned vertex runs.

    Body meshes keep skin tables in the upper portion of the file; default scan
    starts at 40% of the file to avoid geometry false positives and keep runtime
    interactive.
    """
    end = len(data) if scan_end is None else min(scan_end, len(data))
    if scan_start is None:
        scan_start = max(0, (len(data) * 2) // 5)  # ~40%
    runs: list[SkinRun] = []
    off = max(0, scan_start)
    # Coarse scan by record size; probe 4-byte phase offsets when hunting a run head
    while off + RECORD_SIZE <= end and len(runs) < max_runs:
        found_phase = -1
        for phase in (0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52):
            cand = off + phase
            if cand + RECORD_SIZE <= end and _is_skin_record(data, cand):
                found_phase = phase
                break
        if found_phase < 0:
            off += RECORD_SIZE
            continue
        start = off + found_phase
        verts: list[SkinVertex] = []
        cur = start
        while (
            cur + RECORD_SIZE <= end
            and len(verts) < max_vertices_per_run
            and _is_skin_record(data, cur)
        ):
            verts.append(_read_vertex(data, cur))
            cur += RECORD_SIZE
        if len(verts) >= 8:  # ignore tiny false positives
            runs.append(SkinRun(offset=start, count=len(verts), vertices=verts))
        off = cur if cur > off else off + RECORD_SIZE
    runs.sort(key=lambda r: r.count, reverse=True)
    return runs


def summarize_runs(runs: list[SkinRun], *, sample: int = 3) -> dict[str, Any]:
    total = sum(r.count for r in runs)
    bones: set[int] = set()
    for run in runs:
        for v in run.vertices:
            for k in range(4):
                if v.weights[k] > 0.05:
                    bones.add(int(v.indices[k]))
    return {
        "recordSize": RECORD_SIZE,
        "layout": {
            "blendWeight": {"offset": 0, "type": "float4"},
            "blendIndex": {"offset": 16, "type": "uint16x4"},
            "position": {"offset": 24, "type": "float3"},
            "normal": {"offset": 36, "type": "float3"},
            "uv": {"offset": 48, "type": "float2"},
        },
        "runCount": len(runs),
        "vertexCount": total,
        "boneIndexMax": max(bones) if bones else None,
        "boneIndexCount": len(bones),
        "boneIndices": sorted(bones)[:128],
        "runs": [
            {
                "offset": r.offset,
                "count": r.count,
                "sample": [
                    {
                        "weights": [round(x, 5) for x in v.weights],
                        "indices": v.indices,
                        "position": [round(x, 5) for x in v.position],
                        "normal": [round(x, 5) for x in v.normal],
                        "uv": [round(x, 5) for x in v.uv],
                    }
                    for v in r.vertices[:sample]
                ],
            }
            for r in runs[:32]
        ],
    }


def load_body_skin(
    client_root: Path,
    *,
    char: str = "NIKI",
    include_vertices: bool = False,
    max_vertices: int = 2000,
) -> dict[str, Any]:
    """Load character body DAT and extract skinned vertex runs."""
    archive = _mesh_archive_rel(char)
    with zipfile.ZipFile(client_root / archive) as zf:
        member = _prefer_body_member(list(zf.namelist()), char)
        data = zf.read(member)
    runs = find_skin_runs(data)
    summary = summarize_runs(runs)
    payload: dict[str, Any] = {
        "ok": True,
        "char": (char or "NIKI").upper(),
        "archive": archive,
        "member": member,
        "byteLength": len(data),
        "skin": summary,
    }
    if include_vertices and runs:
        # Flatten top runs up to max_vertices for preview pipelines
        verts: list[dict[str, Any]] = []
        for run in runs:
            for v in run.vertices:
                verts.append(asdict(v))
                if len(verts) >= max_vertices:
                    break
            if len(verts) >= max_vertices:
                break
        payload["vertices"] = verts
        payload["verticesTruncated"] = summary["vertexCount"] > len(verts)
    return payload
