"""Map world catalog RE: MapObjRes / MapTileRes / MapHouseRes from MapSet/Script.res.

AES-decrypted INI catalogs map Obj_Number → mesh DAT path for overworld deco
and Tile_Number → layer tiles. Used by the in-game map editor / house system.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

from client_crypto import decrypt_set_file
from mesh_codec import client_dat_path_to_ref


_KV = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*(.*)$")


def _clean(val: str) -> str:
    return val.strip().strip('"').strip()


def _parse_add_blocks(text: str, section_prefix: str) -> list[dict[str, str]]:
    """Parse repeated [Add_*] blocks into list of key/value dicts."""
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            if current:
                blocks.append(current)
            title = line[1:-1]
            if title.lower().startswith(section_prefix.lower()) or section_prefix.lower() in title.lower():
                current = {"_section": title}
            else:
                current = None
            continue
        if current is None:
            continue
        m = _KV.match(line)
        if m:
            current[m.group(1)] = _clean(m.group(2))
    if current:
        blocks.append(current)
    return blocks


def parse_map_obj_res(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in _parse_add_blocks(text, "Add_MapRes") + _parse_add_blocks(text, "Add MapRes"):
        path = block.get("Obj_Path") or block.get("Obj_path") or ""
        # Fix truncated quotes from source scripts
        path = path.rstrip('"')
        ref = client_dat_path_to_ref(path) if path.endswith(".dat") else None
        items.append(
            {
                "number": block.get("Obj_Number"),
                "id": block.get("Obj_ID"),
                "path": path,
                "archive": ref["archive"] if ref else None,
                "member": ref["member"] if ref else None,
            }
        )
    return items


def parse_map_tile_res(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in _parse_add_blocks(text, "Add_MapTile"):
        path = (block.get("Tile_Path") or "").rstrip('"')
        ref = client_dat_path_to_ref(path) if path.endswith(".dat") else None
        items.append(
            {
                "number": block.get("Tile_Number"),
                "id": block.get("Tile_ID"),
                "layer": block.get("Tile_Layer"),
                "useHeight": block.get("Tile_Use_Height"),
                "useWater": block.get("Tile_Use_Water"),
                "height": block.get("Tile_Height"),
                "path": path,
                "archive": ref["archive"] if ref else None,
                "member": ref["member"] if ref else None,
            }
        )
    return items


def parse_map_house_res(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in _parse_add_blocks(text, "Add_MapHouse"):
        path = (block.get("House_Path") or "").rstrip('"')
        ref = client_dat_path_to_ref(path) if path.endswith(".dat") else None
        items.append(
            {
                "index": block.get("House_Index"),
                "id": block.get("House_ID"),
                "path": path,
                "archive": ref["archive"] if ref else None,
                "member": ref["member"] if ref else None,
            }
        )
    return items


def load_map_catalogs(client_root: Path) -> dict[str, Any]:
    script = client_root / "Res" / "MapSet" / "Script.res"
    with zipfile.ZipFile(script) as zf:
        members = {n: zf.read(n) for n in zf.namelist()}

    def decrypt_member(name: str) -> str:
        raw = members[name]
        return decrypt_set_file(raw).decode("utf-8", errors="replace")

    objects = parse_map_obj_res(decrypt_member("MapObjRes.set")) if "MapObjRes.set" in members else []
    tiles = parse_map_tile_res(decrypt_member("MapTileRes.set")) if "MapTileRes.set" in members else []
    houses = parse_map_house_res(decrypt_member("MapHouseRes.set")) if "MapHouseRes.set" in members else []

    return {
        "objects": objects,
        "tiles": tiles,
        "houses": houses,
        "objectCount": len(objects),
        "tileCount": len(tiles),
        "houseCount": len(houses),
    }
