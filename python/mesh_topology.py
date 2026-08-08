"""Author new mesh topology from OBJ (studio DAT layout, not stock FVF parity)."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import json
import re

from mesh_obj_import import parse_obj_positions

_F_RE_FACE = re.compile(r"^f\s+(.+)$")


def parse_obj_faces(text: str) -> list[list[int]]:
    """Return 0-based triangle index lists (fans polygon faces)."""
    faces: list[list[int]] = []
    for line in text.splitlines():
        m = _F_RE_FACE.match(line.strip())
        if not m:
            continue
        parts = m.group(1).split()
        idxs: list[int] = []
        for part in parts:
            # v / v/t / v/t/n / v//n
            token = part.split("/")[0]
            if not token:
                continue
            idxs.append(int(token) - 1)
        if len(idxs) < 3:
            continue
        for i in range(1, len(idxs) - 1):
            faces.append([idxs[0], idxs[i], idxs[i + 1]])
    return faces


def pack_studio_dat(
    positions: list[list[float]],
    triangles: list[list[int]],
) -> bytes:
    """Pack a studio-authored DAT: header + float3 verts + u16 indices.

    Layout chosen so mesh_codec multi-stride recovery still finds geometry:
    - 48 B header (12×u32)
    - tightly packed float3 positions
    - tightly packed u16 triangle indices
    """
    if not positions:
        raise ValueError("EMPTY_POSITIONS")
    if not triangles:
        raise ValueError("EMPTY_TRIANGLES")
    for tri in triangles:
        if len(tri) != 3:
            raise ValueError("NON_TRIANGLE")
        for i in tri:
            if i < 0 or i >= len(positions):
                raise ValueError("INDEX_OOB")

    vert_bytes = b"".join(struct.pack("<fff", float(p[0]), float(p[1]), float(p[2])) for p in positions)
    idx_bytes = b"".join(struct.pack("<HHH", t[0], t[1], t[2]) for t in triangles)
    # pad indices to even
    if len(idx_bytes) % 4:
        idx_bytes += b"\x00" * (4 - (len(idx_bytes) % 4))

    section_a = len(vert_bytes)
    section_b = len(idx_bytes)
    section_c = 0
    header = struct.pack(
        "<12I",
        section_a,
        section_b,
        section_c,
        2,  # version-ish
        1,  # count1
        0,
        1,  # count2
        0,
        0,
        0,
        0,
        0,
    )
    return header + vert_bytes + idx_bytes


def create_mesh_from_obj(obj_path: Path, out_dat: Path) -> dict[str, Any]:
    text = obj_path.read_text(encoding="utf-8", errors="replace")
    positions = parse_obj_positions(text)
    triangles = parse_obj_faces(text)
    if not positions:
        return {"ok": False, "error": "OBJ_NO_VERTICES"}
    if not triangles:
        return {"ok": False, "error": "OBJ_NO_FACES"}
    data = pack_studio_dat(positions, triangles)
    out_dat.parent.mkdir(parents=True, exist_ok=True)
    out_dat.write_bytes(data)
    # Companion OBJ/glTF from authored topology (no stock-style recovery required).
    obj_lines = ["# studio-authored", f"# verts {len(positions)} tris {len(triangles)}"]
    for p in positions:
        obj_lines.append(f"v {p[0]} {p[1]} {p[2]}")
    for t in triangles:
        obj_lines.append(f"f {t[0] + 1} {t[1] + 1} {t[2] + 1}")
    obj_out = out_dat.with_suffix(".obj")
    meta_out = out_dat.with_suffix(".json")
    obj_out.write_text("\n".join(obj_lines) + "\n", encoding="utf-8")
    meta = {
        "vertexCount": len(positions),
        "triangleCount": len(triangles),
        "layout": "studio-header+float3+u16",
        "headerBytes": 48,
    }
    meta_out.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "path": str(out_dat),
        "obj": str(obj_out),
        "meta": str(meta_out),
        "vertexCount": len(positions),
        "triangleCount": len(triangles),
        "bytes": len(data),
        "layout": "studio-header+float3+u16",
        "note": (
            "Studio DAT for tooling/export/new topology. Stock DX9 FVF materials/submeshes "
            "are not synthesized; pack into equipment RES for local experiments only."
        ),
    }
