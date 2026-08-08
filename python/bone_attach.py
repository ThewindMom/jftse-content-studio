"""Extract bind-pose bone sockets + ordered skeleton palette from character DATs.

Body meshes (e.g. Niki.dat) store a fixed-stride skeleton table near the file
tail:

  record size 304 bytes
    name[32]           null-terminated bone name
    parent[32]         null-terminated parent name ("None" for root)
    … padding …
    localMatrix@+96    4×4 float32 column-major (D3D / Three.js)
    auxMatrix@+160     4×4 float32 column-major
    worldMatrix@+224   4×4 float32 column-major

Index order in this table is the palette used for skin blend indices (0..N)
and is the natural order for Three.js Skeleton.bones[i].

Matrix layout (verified Niki Bone_Racket + Bip01 sample):
- Flat 16 float32 values with translation at indices 12, 13, 14
- Compatible with D3D9 / Three.js Matrix4.fromArray column-major layout
"""

from __future__ import annotations

import math
import re
import struct
import zipfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

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

BONE_RECORD_SIZE: Final[int] = 304
_NAME_FIELD: Final[int] = 32
_PARENT_FIELD: Final[int] = 32
_LOCAL_MATRIX_OFF: Final[int] = 96
_AUX_MATRIX_OFF: Final[int] = 160
_WORLD_MATRIX_OFF: Final[int] = 224
_NAME_RE: Final[re.Pattern[bytes]] = re.compile(rb"[A-Za-z][A-Za-z0-9_]{1,30}")


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


@dataclass(frozen=True, slots=True)
class BoneSocket:
    name: str
    offset: int
    position: list[float]
    matrix4: list[float]  # Three.js / D3D column-major flat 16 floats
    socket: bool
    matrixLayout: str = "column-major"


@dataclass(frozen=True, slots=True)
class SkeletonBone:
    """One entry in the skin/skeleton palette (index == table order)."""

    index: int
    name: str
    parent: str | None
    parentIndex: int | None
    offset: int
    position: list[float]
    matrix4: list[float]  # local bind (record +96)
    worldMatrix4: list[float]  # world bind (record +224)
    auxMatrix4: list[float]  # aux/offset bind (record +160)
    socket: bool
    matrixLayout: str = "column-major"


def _is_unitish_row(a: float, b: float, c: float) -> bool:
    length = math.sqrt(a * a + b * b + c * c)
    return 0.5 <= length <= 1.5


def _score_matrix(m: tuple[float, ...] | list[float]) -> tuple[float, list[float]] | None:
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


def _read_c_string(data: bytes, off: int, size: int) -> str:
    raw = data[off : off + size]
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")


def _is_bone_name(name: str) -> bool:
    if len(name) < 3 or len(name) > 30:
        return False
    return _NAME_RE.fullmatch(name.encode("ascii", errors="ignore")) is not None


def _is_parent_name(name: str) -> bool:
    if name in ("None", "NoBone", ""):
        return True
    return _is_bone_name(name)


def find_skeleton_table_base(data: bytes) -> int | None:
    """Locate the first 304-byte skeleton record (usually root Bip01)."""
    # Prefer the classic root: name "Bip01" + parent "None"
    needle = b"Bip01\x00"
    start = 0
    while True:
        hit = data.find(needle, start)
        if hit < 0:
            break
        if hit + BONE_RECORD_SIZE <= len(data):
            parent = _read_c_string(data, hit + _NAME_FIELD, _PARENT_FIELD)
            if parent == "None":
                # Confirm next record also looks like a bone name
                nxt = hit + BONE_RECORD_SIZE
                if nxt + _NAME_FIELD <= len(data):
                    nxt_name = _read_c_string(data, nxt, _NAME_FIELD)
                    if _is_bone_name(nxt_name):
                        return hit
        start = hit + 1
    # Fallback: any Bip01* that starts a clean 304-stride run of ≥8 bones
    for m in re.finditer(rb"Bip01[A-Za-z0-9_]*\x00", data):
        hit = m.start()
        if _count_stride_bones(data, hit) >= 8:
            return hit
    return None


def _count_stride_bones(data: bytes, base: int, limit: int = 128) -> int:
    count = 0
    for i in range(limit):
        off = base + i * BONE_RECORD_SIZE
        if off + BONE_RECORD_SIZE > len(data):
            break
        name = _read_c_string(data, off, _NAME_FIELD)
        parent = _read_c_string(data, off + _NAME_FIELD, _PARENT_FIELD)
        if not _is_bone_name(name) or not _is_parent_name(parent):
            break
        count += 1
    return count


def extract_skeleton_palette(data: bytes) -> list[SkeletonBone]:
    """Return ordered skeleton palette (index 0..N-1 matches skin blend indices)."""
    base = find_skeleton_table_base(data)
    if base is None:
        return []
    raw: list[tuple[int, str, str | None, int, list[float], list[float], list[float]]] = []
    for i in range(256):
        off = base + i * BONE_RECORD_SIZE
        if off + BONE_RECORD_SIZE > len(data):
            break
        name = _read_c_string(data, off, _NAME_FIELD)
        parent_raw = _read_c_string(data, off + _NAME_FIELD, _PARENT_FIELD)
        if not _is_bone_name(name) or not _is_parent_name(parent_raw):
            break
        parent = None if parent_raw in ("None", "NoBone", "") else parent_raw
        local = list(struct.unpack_from("<16f", data, off + _LOCAL_MATRIX_OFF))
        aux = list(struct.unpack_from("<16f", data, off + _AUX_MATRIX_OFF))
        world = list(struct.unpack_from("<16f", data, off + _WORLD_MATRIX_OFF))
        raw.append((i, name, parent, off, local, aux, world))

    name_to_index = {name: i for i, name, *_ in raw}
    bones: list[SkeletonBone] = []
    for i, name, parent, off, local, aux, world in raw:
        parent_index = name_to_index.get(parent) if parent else None
        # Prefer local matrix translation; fall back to world if non-finite
        pos = [float(local[12]), float(local[13]), float(local[14])]
        if not all(math.isfinite(x) for x in pos):
            pos = [float(world[12]), float(world[13]), float(world[14])]
        is_socket = any(hint.lower() in name.lower() for hint in _SOCKET_HINTS)
        bones.append(
            SkeletonBone(
                index=i,
                name=name,
                parent=parent,
                parentIndex=parent_index,
                offset=off,
                position=pos,
                matrix4=local,
                worldMatrix4=world,
                auxMatrix4=aux,
                socket=is_socket,
            )
        )
    return bones


def extract_bone_sockets(data: bytes) -> list[BoneSocket]:
    """Compat wrapper: sockets derived from the ordered skeleton palette."""
    palette = extract_skeleton_palette(data)
    if palette:
        return [
            BoneSocket(
                name=b.name,
                offset=b.offset,
                position=list(b.position),
                matrix4=list(b.matrix4),
                socket=b.socket,
            )
            for b in palette
        ]
    # Legacy heuristic fallback if table not found
    return _extract_bone_sockets_heuristic(data)


def _extract_bone_sockets_heuristic(data: bytes) -> list[BoneSocket]:
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
    palette = extract_skeleton_palette(data)
    if palette:
        exact = next((b for b in palette if b.name == bone_name), None)
        if exact is not None:
            return BoneSocket(
                name=exact.name,
                offset=exact.offset,
                position=list(exact.position),
                matrix4=list(exact.matrix4),
                socket=exact.socket,
            )
        needle = bone_name.lower()
        soft = next((b for b in palette if needle in b.name.lower()), None)
        if soft is not None:
            return BoneSocket(
                name=soft.name,
                offset=soft.offset,
                position=list(soft.position),
                matrix4=list(soft.matrix4),
                socket=soft.socket,
            )
    sockets = _extract_bone_sockets_heuristic(data)
    exact = next((socket for socket in sockets if socket.name == bone_name), None)
    if exact is not None:
        return exact
    needle = bone_name.lower()
    return next((socket for socket in sockets if needle in socket.name.lower()), None)


def skeleton_to_api(palette: list[SkeletonBone]) -> dict[str, object]:
    """Serialize palette for API / Three.js Skeleton construction."""
    return {
        "recordSize": BONE_RECORD_SIZE,
        "boneCount": len(palette),
        "matrixLayout": "column-major",
        "threeJsFromArray": True,
        "localMatrixOffset": _LOCAL_MATRIX_OFF,
        "auxMatrixOffset": _AUX_MATRIX_OFF,
        "worldMatrixOffset": _WORLD_MATRIX_OFF,
        "bones": [
            {
                "index": b.index,
                "name": b.name,
                "parent": b.parent,
                "parentIndex": b.parentIndex,
                "position": b.position,
                "matrix4": b.matrix4,
                "worldMatrix4": b.worldMatrix4,
                "auxMatrix4": b.auxMatrix4,
                "socket": b.socket,
                "matrixLayout": "column-major",
            }
            for b in palette
        ],
        "names": [b.name for b in palette],
    }


def load_body_attach(
    client_root: Path,
    *,
    char: str = "NIKI",
    attach_bone: str = "Bone_Racket",
) -> dict[str, object]:
    """Load Player mesh DAT and resolve attach bone + ordered skeleton palette."""
    archive = _mesh_archive_rel(char)
    with zipfile.ZipFile(client_root / archive) as zf:
        members = list(zf.namelist())
        body = _prefer_body_member(members, char)
        data = zf.read(body)
    palette = extract_skeleton_palette(data)
    attach = extract_attach_socket(data, attach_bone)
    attach_dict: Mapping[str, object] | None = (
        asdict(attach) if attach is not None else None
    )
    skeleton = skeleton_to_api(palette)
    # bones[]: ordered palette entries (name + position + matrix) for UI lists
    bones: list[dict[str, object]] = [
        {
            "index": b.index,
            "name": b.name,
            "parent": b.parent,
            "parentIndex": b.parentIndex,
            "position": b.position,
            "matrix4": b.matrix4,
            "socket": b.socket,
        }
        for b in palette
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
        "socketCount": sum(1 for b in palette if b.socket),
        "sockets": [
            {
                "name": b.name,
                "index": b.index,
                "position": b.position,
                "matrix4": b.matrix4,
            }
            for b in palette
            if b.socket
        ],
        "bones": bones,
        "boneCount": len(palette),
        "skeleton": skeleton,
    }
