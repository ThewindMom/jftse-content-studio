"""Stage .Eft effect member inspection (header + emitter heuristics)."""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path
from typing import Any


def parse_eft_bytes(data: bytes, *, name: str = "") -> dict[str, Any]:
    """Best-effort .Eft parse for studio markers (not full emitter simulation)."""
    if len(data) < 48:
        return {"ok": False, "error": "EFT_TOO_SMALL", "name": name}
    a, b, c, flags, n0, f0, n1, n2, n3, n4, n5, n6 = struct.unpack_from("<12I", data, 0)
    # f0 often looks like float bits (e.g. 20.0) when interpreted as float
    f0_as_float = struct.unpack_from("<f", data, 20)[0]
    # Sample candidate float3 positions in first 4 KB after header
    sample_pos: list[list[float]] = []
    region = data[48 : min(len(data), 48 + 4096)]
    for i in range(0, max(0, len(region) - 12), 12):
        x, y, z = struct.unpack_from("<fff", region, i)
        if not all(abs(v) < 5000 and abs(v) == abs(v) for v in (x, y, z)):
            continue
        if abs(x) + abs(y) + abs(z) < 1e-3:
            continue
        # Prefer modest magnitudes typical of stage props
        if max(abs(x), abs(y), abs(z)) > 200:
            continue
        sample_pos.append([float(x), float(y), float(z)])
        if len(sample_pos) >= 8:
            break
    return {
        "ok": True,
        "name": name,
        "byteLength": len(data),
        "sectionA": a,
        "sectionB": b,
        "sectionC": c,
        "flags": flags,
        "headerU32": [a, b, c, flags, n0, f0, n1, n2, n3, n4, n5, n6],
        "headerFloatAt20": float(f0_as_float),
        "emitterHint": n0,
        "positionSamples": sample_pos,
        "note": "Heuristic .Eft header; full particle simulation remains client-side.",
    }


def load_eft_from_path(client_root: Path, file_path: str) -> dict[str, Any]:
    """Resolve Res/.../Name.Eft or .eft inside a sibling .res archive."""
    cleaned = file_path.replace("\\", "/").strip().strip('"')
    # Direct file
    direct = client_root / cleaned
    if direct.is_file():
        return parse_eft_bytes(direct.read_bytes(), name=direct.name)
    # Archive member: Res/Stage/Mesh11/EF_x.Eft → Mesh11.res
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) < 2:
        return {"ok": False, "error": "EFT_PATH_INVALID", "path": cleaned}
    member = parts[-1]
    archive = client_root / ("/".join(parts[:-1]) + ".res")
    if not archive.is_file():
        return {"ok": False, "error": "EFT_ARCHIVE_MISSING", "path": cleaned, "archive": str(archive)}
    try:
        with zipfile.ZipFile(archive, "r") as zin:
            # case-insensitive member match
            names = {n.lower(): n for n in zin.namelist()}
            key = member.lower()
            if key not in names:
                return {"ok": False, "error": "EFT_MEMBER_MISSING", "member": member}
            data = zin.read(names[key])
    except zipfile.BadZipFile:
        return {"ok": False, "error": "EFT_BAD_ZIP", "archive": str(archive)}
    payload = parse_eft_bytes(data, name=member)
    try:
        payload["archive"] = str(archive.relative_to(client_root))
    except ValueError:
        payload["archive"] = str(archive)
    payload["path"] = cleaned
    return payload
