"""Canonical Fantasy Tennis character → Player* folder mapping.

Source of truth: client body meshes + Info_Item_Mesh Char paths.

| Char      | Folder   | Body DAT    |
|-----------|----------|-------------|
| NIKI      | PlayerA  | Niki.dat    |
| LUNLUN    | PlayerB  | LunLun.dat  |
| DHANPIR   | PlayerC  | Dhanpir.dat |
| LUCY      | PlayerD  | Lucy.dat    |
| SHUA      | PlayerE  | Shua.dat    |
| POCHI     | PlayerF  | Pochi.dat   |
| AL        | PlayerG  | Al.dat      |
"""

from __future__ import annotations

from typing import Final

# Catalog Char values from Info_Item_Mesh.set (primary keys)
CHAR_TO_PLAYER: Final[dict[str, str]] = {
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

# Common community / UI aliases → catalog Char
CHAR_ALIASES: Final[dict[str, str]] = {
    "LUNLUN": "LUNLUN",
    "LUN": "LUNLUN",
    "DHAN": "DHANPIR",
    "DHANPIR": "DHANPIR",
    # Historical wrong names sometimes used in tools — map to closest real char
    "PIKARO": "SHUA",
    "RONA": "POCHI",
}

PLAYER_BODY_HINT: Final[dict[str, str]] = {
    "PlayerA": "niki",
    "PlayerB": "lun",
    "PlayerC": "dhan",
    "PlayerD": "lucy",
    "PlayerE": "shua",
    "PlayerF": "pochi",
    "PlayerG": "al",
}


def normalize_char(char: str | None) -> str:
    raw = (char or "NIKI").strip().upper()
    if not raw:
        return "NIKI"
    if raw in CHAR_TO_PLAYER:
        return raw
    alias = CHAR_ALIASES.get(raw)
    if alias and alias in CHAR_TO_PLAYER:
        return alias
    return raw


def player_folder(char: str | None) -> str:
    """Return Res/Player/<folder> segment for a character token."""
    key = normalize_char(char)
    return CHAR_TO_PLAYER.get(key, "PlayerA")


def mesh_archive_rel(char: str | None) -> str:
    return f"Res/Player/{player_folder(char)}/Mesh.res"


def prefer_body_member(members: list[str], char: str | None) -> str:
    """Pick the primary body .dat from a Mesh.res member list."""
    dats = [m for m in members if m.lower().endswith(".dat")]
    if not dats:
        return members[0] if members else ""
    folder = player_folder(char)
    hint = PLAYER_BODY_HINT.get(folder, "")
    if hint:
        for m in dats:
            if hint in m.lower() and "ran" not in m.lower():
                return m
    # Prefer non-Ran when multiple (PlayerG has Al.dat + Ran.dat)
    non_ran = [m for m in dats if "ran" not in m.lower()]
    return (non_ran or dats)[0]
