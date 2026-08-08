"""Resolve Fantasy Tennis equipment mesh paths from Info_Item_Mesh.set.

RE (AES TIMOTEI_ZION): Info_Item_Mesh.set decrypts to UTF-8 XML:
  <Item Char="NIKI" Index="214" Path="Res/Player/PlayerA/Item07/Niki_CommonRacket41.dat" Desc="..."/>
Item.res mesh field on shop rows is this Index (per character family).
"""

from __future__ import annotations

import re
import zipfile
from functools import lru_cache
from pathlib import Path

from .client_crypto import decrypt_set_file

# Keep in sync with char_player.py / bone_attach._CHAR_TO_PLAYER
_CHAR_TO_PLAYER = {
    "NIKI": "PlayerA",
    "LUN": "PlayerB",
    "LUNLUN": "PlayerB",
    "DHAN": "PlayerC",
    "DHANPIR": "PlayerC",
    "LUCY": "PlayerD",
    "SHUA": "PlayerE",
    "POCHI": "PlayerF",
    "AL": "PlayerG",
}


@lru_cache(maxsize=1)
def _load_item_mesh_xml(client_root_str: str) -> str:
    client = Path(client_root_str)
    with zipfile.ZipFile(client / "Res" / "Script" / "Item.res") as archive:
        raw = archive.read("Info_Item_Mesh.set")
    return decrypt_set_file(raw).decode("utf-8", errors="replace")


def parse_item_mesh_entries(client_root: Path) -> list[dict[str, str]]:
    xml = _load_item_mesh_xml(str(client_root.resolve()))
    entries: list[dict[str, str]] = []
    for match in re.finditer(
        r'<Item\s+Char="([^"]+)"\s+Index="(\d+)"\s+Path="([^"]+)"(?:\s+Desc="([^"]*)")?',
        xml,
    ):
        char, index, path, desc = match.groups()
        entries.append(
            {
                "char": char,
                "index": index,
                "path": path.replace("\\", "/"),
                "desc": desc or "",
            }
        )
    return entries


def resolve_item_mesh_path(
    client_root: Path,
    mesh_index: int | str,
    *,
    char: str = "NIKI",
) -> dict[str, str] | None:
    """Map shop mesh index + character to archive/member under Res/Player/…"""
    want = str(int(mesh_index))
    char_u = char.upper()
    for entry in parse_item_mesh_entries(client_root):
        if entry["index"] != want:
            continue
        if entry["char"].upper() != char_u and char_u not in (
            entry["char"].upper(),
            _CHAR_TO_PLAYER.get(entry["char"].upper(), ""),
        ):
            # Prefer exact Char match; allow first match for unknown char alias
            if char_u not in _CHAR_TO_PLAYER and entry["char"].upper() != "NIKI":
                continue
            if char_u in _CHAR_TO_PLAYER and entry["char"].upper() != char_u:
                # only accept if player folder matches
                player = _CHAR_TO_PLAYER.get(entry["char"].upper(), "")
                if player and f"/{player}/" not in entry["path"].replace("\\", "/"):
                    continue
        path = entry["path"]
        # Res/Player/PlayerA/Item07/Niki_CommonRacket41.dat → archive Item07.res
        parts = [p for p in path.split("/") if p]
        if len(parts) < 2 or not parts[-1].lower().endswith(".dat"):
            continue
        member = parts[-1]
        parent = "/".join(parts[:-1])
        archive = f"{parent}.res"
        if not (client_root / archive).is_file():
            continue
        return {
            "archive": archive,
            "member": member,
            "path": path,
            "char": entry["char"],
            "index": entry["index"],
            "desc": entry["desc"],
        }
    # fallback: first index match any char
    for entry in parse_item_mesh_entries(client_root):
        if entry["index"] != want:
            continue
        path = entry["path"].replace("\\", "/")
        parts = [p for p in path.split("/") if p]
        if len(parts) < 2:
            continue
        member = parts[-1]
        archive = f"{'/'.join(parts[:-1])}.res"
        if (client_root / archive).is_file():
            return {
                "archive": archive,
                "member": member,
                "path": path,
                "char": entry["char"],
                "index": entry["index"],
                "desc": entry["desc"],
            }
    return None


def client_path_to_archive_member(path: str) -> dict[str, str] | None:
    cleaned = path.replace("\\", "/").strip().strip('"')
    if not cleaned.lower().endswith(".dat"):
        return None
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) < 2:
        return None
    return {"archive": "/".join(parts[:-1]) + ".res", "member": parts[-1], "path": cleaned}
