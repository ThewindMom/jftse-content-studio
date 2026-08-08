"""Import OBJ vertex positions into an existing DAT (same vertex count)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mesh_codec import decode_member, write_positions_into_dat


_V_RE = re.compile(
    r"^v\s+([-+eE0-9.]+)\s+([-+eE0-9.]+)\s+([-+eE0-9.]+)",
)


def parse_obj_positions(text: str) -> list[list[float]]:
    positions: list[list[float]] = []
    for line in text.splitlines():
        m = _V_RE.match(line.strip())
        if not m:
            continue
        positions.append([float(m.group(1)), float(m.group(2)), float(m.group(3))])
    return positions


def import_obj_into_dat(
    client_root: Path,
    archive: str,
    member: str,
    obj_path: Path,
    out_dat: Path,
) -> dict[str, Any]:
    mesh = decode_member(client_root, archive, member)
    # DecodedMesh fields are camelCase: vertexCount / vertexOffset / vertexStride.
    vertex_count = mesh.vertexCount
    vertex_offset = mesh.vertexOffset
    vertex_stride = mesh.vertexStride
    positions = parse_obj_positions(obj_path.read_text(encoding="utf-8", errors="replace"))
    if not positions:
        return {"ok": False, "error": "OBJ_NO_VERTICES"}
    if len(positions) != vertex_count:
        return {
            "ok": False,
            "error": "VERTEX_COUNT_MISMATCH",
            "objCount": len(positions),
            "datCount": vertex_count,
            "detail": "OBJ must match DAT vertex count (topology-preserving import)",
        }
    import zipfile

    with zipfile.ZipFile(client_root / archive, "r") as zin:
        data = zin.read(member)
    patched = write_positions_into_dat(
        data,
        vertex_offset,
        positions,
        stride=vertex_stride,
    )
    out_dat.parent.mkdir(parents=True, exist_ok=True)
    out_dat.write_bytes(patched)
    return {
        "ok": True,
        "path": str(out_dat),
        "vertexCount": len(positions),
        "sameSize": len(patched) == len(data),
        "bytes": len(patched),
    }
