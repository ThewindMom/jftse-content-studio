"""Extract bind-pose bone sockets (position + 3x3 rotation) from character DATs.

Bone table lives near the end of body meshes (e.g. Niki.dat). Names are
null-terminated (Bip01*, Bone_Racket, Bone_ball, …). Immediately after the
name field, FT stores 4x4 matrices; we recover translation + rotation for
equipment attach (AttachBone=Bone_Racket).
"""

from __future__ import annotations

import math
import re
import struct
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class BoneSocket:
    name: str
    offset: int
    position: list[float]
    matrix4: list[float]  # row-major 4x4
    socket: bool


_SOCKET_HINTS = ("Racket", "ball", "bag", "Weapon", "Attach", "Hand")


def _is_unitish_row(a: float, b: float, c: float) -> bool:
    length = math.sqrt(a * a + b * b + c * c)
    return 0.5 <= length <= 1.5


def _score_matrix(m: tuple[float, ...]) -> tuple[float, list[float]] | None:
    """Return (score, translation) for a plausible row-major 4x4 bind matrix."""
    if len(m) != 16 or not all(math.isfinite(x) for x in m):
        return None
    if abs(m[15] - 1.0) > 0.15:
        return None
    # translation candidates: row-major last column vs D3D column-major
    candidates = [
        ([m[12], m[13], m[14]], "rm"),
        ([m[3], m[7], m[11]], "cm"),
    ]
    best: tuple[float, list[float]] | None = None
    for t, _kind in candidates:
        if not all(abs(x) < 500 for x in t):
            continue
        # rotation block should look roughly orthonormal
        r0 = (m[0], m[1], m[2])
        r1 = (m[4], m[5], m[6])
        r2 = (m[8], m[9], m[10])
        if not (
            _is_unitish_row(*r0)
            or _is_unitish_row(*r1)
            or _is_unitish_row(*r2)
            or sum(abs(x) for x in t) > 0.5
        ):
            continue
        score = sum(abs(x) for x in t)
        # prefer matrices with some rotation structure
        if _is_unitish_row(*r0) and _is_unitish_row(*r1):
            score += 5
        if best is None or score > best[0]:
            best = (score, t)
    return best


def extract_bone_sockets(data: bytes) -> list[BoneSocket]:
    """Find bone names and nearest bind matrices in a mesh DAT."""
    sockets: list[BoneSocket] = []
    seen: set[str] = set()
    for m in re.finditer(
        rb"(?:Bip01[A-Za-z0-9_]{0,40}|Bone[A-Za-z0-9_]{0,24})\x00",
        data,
    ):
        raw = m.group()[:-1].decode("ascii", errors="ignore")
        # split accidental concatenations
        parts = re.findall(r"Bip01(?:_[A-Za-z0-9]+)+|Bone_[A-Za-z0-9]+|Bone\d+|Bone", raw)
        names = parts or ([raw] if raw else [])
        for name in names:
            if name in seen or len(name) < 3:
                continue
            seen.add(name)
            name_off = m.start()
            # search matrices after the name within ~280 bytes
            search_from = name_off + len(name) + 1
            search_to = min(len(data) - 64, name_off + 300)
            best: tuple[float, int, list[float], list[float]] | None = None
            for off in range(search_from, search_to, 4):
                mat = struct.unpack_from("<16f", data, off)
                scored = _score_matrix(mat)
                if scored is None:
                    continue
                score, t = scored
                if best is None or score > best[0]:
                    best = (score, off, t, list(mat))
            if best is None:
                continue
            is_socket = any(h.lower() in name.lower() for h in _SOCKET_HINTS)
            sockets.append(
                BoneSocket(
                    name=name,
                    offset=name_off,
                    position=[float(x) for x in best[2]],
                    matrix4=best[3],
                    socket=is_socket,
                )
            )
    return sockets


def extract_attach_socket(
    data: bytes, bone_name: str = "Bone_Racket"
) -> BoneSocket | None:
    sockets = extract_bone_sockets(data)
    exact = next((s for s in sockets if s.name == bone_name), None)
    if exact:
        return exact
    # fuzzy
    return next((s for s in sockets if bone_name.lower() in s.name.lower()), None)


def load_body_attach(
    client_root: Path,
    *,
    char: str = "NIKI",
    attach_bone: str = "Bone_Racket",
) -> dict[str, Any]:
    """Load Player mesh DAT and resolve attach bone for equipment preview."""
    char = (char or "NIKI").upper()
    player_map = {
        "NIKI": "PlayerA",
        "LUN": "PlayerB",
        "LUCY": "PlayerC",
        "SHUA": "PlayerD",
        "PIKARO": "PlayerE",
        "RONA": "PlayerF",
        "AL": "PlayerG",
    }
    folder = player_map.get(char, "PlayerA")
    # Mesh file name is character name-ish: Niki.dat, etc.
    archive = f"Res/Player/{folder}/Mesh.res"
    with zipfile.ZipFile(client_root / archive) as zf:
        members = zf.namelist()
        body = next((m for m in members if m.lower().endswith(".dat")), members[0])
        data = zf.read(body)
    sockets = extract_bone_sockets(data)
    attach = extract_attach_socket(data, attach_bone)
    return {
        "ok": True,
        "char": char,
        "archive": archive,
        "member": body,
        "attachBone": attach_bone,
        "attach": asdict(attach) if attach else None,
        "hasAttach": attach is not None,
        "socketCount": len(sockets),
        "sockets": [asdict(s) for s in sockets if s.socket],
        "bones": [{"name": s.name, "position": s.position} for s in sockets[:64]],
    }
