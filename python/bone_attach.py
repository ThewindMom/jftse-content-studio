"""Extract bind-pose bone sockets (position + 4x4 matrix) from character DATs.

Bone table lives near the end of body meshes (e.g. Niki.dat). Names are
null-terminated (Bip01*, Bone_Racket, Bone_ball, …). Immediately after the
name field, FT stores 4x4 matrices.

Matrix layout (verified Niki Bone_Racket + Bip01 sample):
- Flat 16 float32 values with translation at indices 12, 13, 14
  (matches scored position with distance 0; indices 3, 7, 11 are 0).
- Compatible with D3D9 / Three.js Matrix4.fromArray column-major layout.
- Homogeneous diagonal m[15] ~ 1; upper 3x3 is orthonormal (det ~ 1).
"""

from __future__ import annotations

import math
import re
import struct
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from collections.abc import Mapping

# Char token -> Res/Player/Player* folder (body meshes + Info_Item_Mesh paths).
_CHAR_TO_PLAYER: dict[str, str] = {
    "NIKI": "PlayerA",
    "LUN": "PlayerB",
    "LUNLUN": "PlayerB",
    "DHAN": "PlayerC",
    "DHANPIR": "PlayerC",
    "LUCY": "PlayerD",
    "SHUA": "PlayerE",
    "POCHI": "PlayerF",
    "AL": "PlayerG",
    "PIKARO": "PlayerE",
    "RONA": "PlayerF",
}

_BODY_HINT: dict[str, str] = {
    "PlayerA": "niki",
    "PlayerB": "lun",
    "PlayerC": "dhan",
    "PlayerD": "lucy",
    "PlayerE": "shua",
    "PlayerF": "pochi",
    "PlayerG": "al",
}

_SOCKET_HINTS: tuple[str, ...] = ("Racket", "ball", "bag", "Weapon", "Attach", "Hand")


def _player_folder(char: str | None) -> str:
    key = (char or "NIKI").strip().upper() or "NIKI"
    return _CHAR_TO_PLAYER.get(key, "PlayerA")


def _mesh_archive_rel(char: str | None) -> str:
    return f"Res/Player/{_player_folder(char)}/Mesh.res"


def _prefer_body_member(members: list[str], char: str | None) -> str:
    dats = [m for m in members if m.lower().endswith(".dat")]
    if not dats:
        return members[0] if members else ""
    hint = _BODY_HINT.get(_player_folder(char), "")
    if hint:
        for member in dats:
            lowered = member.lower()
            if hint in lowered and "ran" not in lowered:
                return member
    non_ran = [m for m in dats if "ran" not in m.lower()]
    return (non_ran or dats)[0]


@dataclass
class BoneSocket:
    name: str
    offset: int
    position: list[float]
    matrix4: list[float]  # Three.js / D3D column-major flat 16 floats
    socket: bool
    matrixLayout: str = "column-major"


def _is_unitish_row(a: float, b: float, c: float) -> bool:
    length = math.sqrt(a * a + b * b + c * c)
    return 0.5 <= length <= 1.5


def _score_matrix(m: tuple[float, ...]) -> tuple[float, list[float]] | None:
    """Score a 16-float matrix; prefer Three/D3D translation at indices 12-14."""
    if len(m) != 16 or not all(math.isfinite(x) for x in m):
        return None
    if abs(m[15] - 1.0) > 0.15:
        return None
    candidates: list[tuple[list[float], float]] = [
        ([m[12], m[13], m[14]], 3.0),
        ([m[3], m[7], m[11]], 0.0),
    ]
    best: tuple[float, list[float]] | None = None
    for translation, bonus in candidates:
        if not all(abs(x) < 500 for x in translation):
            continue
        r0 = (m[0], m[1], m[2])
        r1 = (m[4], m[5], m[6])
        r2 = (m[8], m[9], m[10])
        if not (
            _is_unitish_row(*r0)
            or _is_unitish_row(*r1)
            or _is_unitish_row(*r2)
            or sum(abs(x) for x in translation) > 0.5
        ):
            continue
        score = sum(abs(x) for x in translation) + bonus
        if _is_unitish_row(*r0) and _is_unitish_row(*r1):
            score += 5.0
        if best is None or score > best[0]:
            best = (score, translation)
    return best


def extract_bone_sockets(data: bytes) -> list[BoneSocket]:
    """Find bone names and nearest bind matrices in a mesh DAT."""
    sockets: list[BoneSocket] = []
    seen: set[str] = set()
    pattern = re.compile(rb"(?:Bip01[A-Za-z0-9_]{0,40}|Bone[A-Za-z0-9_]{0,24})\x00")
    name_split = re.compile(r"Bip01(?:_[A-Za-z0-9]+)+|Bone_[A-Za-z0-9]+|Bone\d+|Bone")
    for match in pattern.finditer(data):
        raw = match.group()[:-1].decode("ascii", errors="ignore")
        parts: list[str] = name_split.findall(raw)
        names: list[str] = parts if parts else ([raw] if raw else [])
        for name in names:
            if name in seen or len(name) < 3:
                continue
            seen.add(name)
            name_off = match.start()
            search_from = name_off + len(name) + 1
            search_to = min(len(data) - 64, name_off + 300)
            best: tuple[float, int, list[float], list[float]] | None = None
            for off in range(search_from, search_to, 4):
                mat = struct.unpack_from("<16f", data, off)
                scored = _score_matrix(mat)
                if scored is None:
                    continue
                score, translation = scored
                if best is None or score > best[0]:
                    best = (score, off, translation, list(mat))
            if best is None:
                continue
            is_socket = any(hint.lower() in name.lower() for hint in _SOCKET_HINTS)
            sockets.append(
                BoneSocket(
                    name=name,
                    offset=name_off,
                    position=[float(x) for x in best[2]],
                    matrix4=best[3],
                    socket=is_socket,
                    matrixLayout="column-major",
                )
            )
    return sockets


def extract_attach_socket(
    data: bytes, bone_name: str = "Bone_Racket"
) -> BoneSocket | None:
    sockets = extract_bone_sockets(data)
    exact = next((socket for socket in sockets if socket.name == bone_name), None)
    if exact is not None:
        return exact
    needle = bone_name.lower()
    return next((socket for socket in sockets if needle in socket.name.lower()), None)


def load_body_attach(
    client_root: Path,
    *,
    char: str = "NIKI",
    attach_bone: str = "Bone_Racket",
) -> dict[str, object]:
    """Load Player mesh DAT and resolve attach bone for equipment preview."""
    archive = _mesh_archive_rel(char)
    with zipfile.ZipFile(client_root / archive) as zf:
        members = list(zf.namelist())
        body = _prefer_body_member(members, char)
        data = zf.read(body)
    sockets = extract_bone_sockets(data)
    attach = extract_attach_socket(data, attach_bone)
    attach_dict: Mapping[str, object] | None = (
        asdict(attach) if attach is not None else None
    )
    bones: list[dict[str, object]] = [
        {"name": socket.name, "position": socket.position} for socket in sockets[:64]
    ]
    return {
        "ok": True,
        "char": char.upper() if char else "NIKI",
        "archive": archive,
        "member": body,
        "attachBone": attach_bone,
        "attach": attach_dict,
        "hasAttach": attach is not None,
        "matrixLayout": "column-major",
        "threeJsFromArray": True,
        "socketCount": len(sockets),
        "sockets": [asdict(socket) for socket in sockets if socket.socket],
        "bones": bones,
    }
