"""Extract multi-material texture names and bone attach metadata from mesh DATs.

RE findings (2026-08 deep pass):
- Stage/prop DATs embed albedo basenames as ASCII (e.g. BF_Coat00_B, A_BF_CoatMark00_A)
  near the tail / material records. Header fields count1/count2 often track submesh
  or material slot counts (BF_All: 74; BF_Court01: 2).
- Character body DATs (e.g. Niki.dat) embed a Bip01 / Bone* skeleton table including
  equipment sockets Bone_Racket, Bone_ball, Bone_bag used by DX9 attach.
- Runtime scripts (Rtmovie .set) use AttachBone / AttachPath / ShadowBone fields.
"""

from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path
from typing import Any


# Texture-like basenames used as material ids (no .tex suffix in DAT).
_TEX_NAME = re.compile(
    rb"(?:A_)?(?:BF|SV|AS|LW|AT|SM|ML|MB|CT|TU|GA|EF|IC|P0|NHS|CLE|CH|SV|JP|TA|MDM|DTE|TTN)"
    rb"_[A-Za-z0-9_]{2,48}"
)
# Broader pass for prop meshes without stage prefixes.
_TEX_NAME_LOOSE = re.compile(rb"[A-Za-z][A-Za-z0-9_]{2,40}(?:_A|_B|_C|_D|_SM|_LM|_MI)\b")
_BONE_NAME = re.compile(
    rb"(?:Bip01[A-Za-z0-9_ ]{0,40}|Bone[A-Za-z0-9_]{0,24}|Attach[A-Za-z0-9_]{0,24})\x00"
)
_SOCKET_HINTS = ("Racket", "ball", "bag", "Hand", "Attach", "Weapon", "Ball")


def extract_material_names(data: bytes) -> list[dict[str, Any]]:
    """Return Twinkle texture bindings, or unique heuristic names for other DATs."""
    from twinkle_mesh import parse_twinkle_static

    static = parse_twinkle_static(data)
    if static is not None:
        # Unlike the regex fallback, retain each positional texture binding.
        return [
            {**texture, "materialSlot": primitive["materialSlot"],
             "materialChild": primitive["materialChild"],
             "materialName": primitive["materialName"]}
            for primitive in static["primitives"]
            for texture in primitive["textures"]
        ]
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pattern in (_TEX_NAME, _TEX_NAME_LOOSE):
        for m in pattern.finditer(data):
            name = m.group().decode("ascii", errors="ignore").rstrip("_")
            # Filter noise from float garbage that looks short
            if len(name) < 5 or name in seen:
                continue
            if re.fullmatch(r"[A-Za-z0-9_]+", name) is None:
                continue
            # Reject pure bone-like false positives from loose pattern
            if name.startswith("Bip01") or name in ("Bone", "Bone01"):
                continue
            seen.add(name)
            found.append({"name": name, "offset": m.start(), "texCandidate": f"{name}.tex"})
    return found


def extract_bone_names(data: bytes) -> list[dict[str, Any]]:
    """Return skeleton / attach bone names from character/prop DATs."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in _BONE_NAME.finditer(data):
        raw = m.group()[:-1].decode("ascii", errors="ignore").strip()
        name = re.sub(r"\s+", "_", raw)
        # Split accidental concatenations (packed fixed fields)
        parts = re.findall(
            r"Bip01(?:_[A-Za-z0-9]+)+|Bone_[A-Za-z0-9]+|Bone\d+|Bone|Attach[A-Za-z0-9_]+",
            name,
        )
        if not parts:
            parts = [name] if name else []
        for part in parts:
            if part in seen or len(part) < 3:
                continue
            seen.add(part)
            is_socket = any(h.lower() in part.lower() for h in _SOCKET_HINTS)
            found.append(
                {
                    "name": part,
                    "offset": m.start(),
                    "socket": is_socket,
                }
            )
    return found


def parse_mesh_header_fields(data: bytes) -> dict[str, Any]:
    if len(data) < 48:
        return {}
    vals = struct.unpack_from("<12I", data, 0)
    return {
        "raw": list(vals),
        "sectionA": vals[0],
        "sectionB": vals[1],
        "sectionC": vals[2],
        "versionOrFlags": vals[3],
        "count1": vals[4],
        "z1": vals[5],
        "count2": vals[6],
        "z2": vals[7],
        "u8": vals[8],
        "u9": vals[9],
        "u10": vals[10],
        "u11": vals[11],
        # Heuristic: for multi-mat stage props count1≈count2≈submesh/material slots
        "likelySubmeshOrMaterialCount": vals[4] if vals[4] == vals[6] else None,
    }


def parse_equipment_material_table(data: bytes) -> dict[str, Any] | None:
    """Parse positional 64-byte material records in equipment DATs (FORMAT_NOTES).

    Verified on Niki_CommonRacket41.dat:
      - uint32le count at offset 0x64
      - table at file_size - 6 - count*64
      - each record: null-terminated material stem (→ .tex / .ifl) + padding
    Keys are positional (Item_Parts Tex index); do not append/reorder without
    a full dependent-offset parser.
    """
    if len(data) < 0x68 + 64:
        return None
    count = struct.unpack_from("<I", data, 0x64)[0]
    if count < 1 or count > 64:
        return None
    table_off = len(data) - 6 - count * 64
    if table_off < 0x68 or table_off + count * 64 > len(data):
        return None
    records: list[dict[str, Any]] = []
    for i in range(count):
        rec = data[table_off + i * 64 : table_off + (i + 1) * 64]
        name = rec.split(b"\x00", 1)[0]
        if not name or not all(32 <= b < 127 for b in name):
            return None
        stem = name.decode("ascii")
        records.append(
            {
                "index": i,
                "stem": stem,
                "texCandidate": f"{stem}.tex",
                "offset": table_off + i * 64,
            }
        )
    if not records:
        return None
    return {
        "countOffset": 0x64,
        "count": count,
        "tableOffset": table_off,
        "recordSize": 64,
        "trailerSize": 6,
        "records": records,
        "stems": [r["stem"] for r in records],
    }


def analyze_mesh_dat(data: bytes, *, name: str = "") -> dict[str, Any]:
    materials = extract_material_names(data)
    bones = extract_bone_names(data)
    sockets = [b for b in bones if b.get("socket")]
    header = parse_mesh_header_fields(data)
    equip_table = parse_equipment_material_table(data)
    return {
        "name": name,
        "byteLength": len(data),
        "header": header,
        "materials": materials,
        "materialCount": len(materials),
        "equipmentMaterialTable": equip_table,
        "bones": bones,
        "boneCount": len(bones),
        "sockets": sockets,
        "socketNames": [s["name"] for s in sockets],
        "hasSkeleton": len(bones) >= 3,
        "hasMultiMaterial": len(materials) >= 2 or bool(equip_table and equip_table["count"] >= 2),
    }


def analyze_member(client_root: Path, archive_rel: str, member: str) -> dict[str, Any]:
    path = client_root / archive_rel
    with zipfile.ZipFile(path) as zf:
        data = zf.read(member)
    meta = analyze_mesh_dat(data, name=member)
    meta["archive"] = archive_rel
    meta["member"] = member
    return meta
