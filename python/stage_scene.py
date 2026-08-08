"""Stage scene-graph RE for Fantasy Tennis.

AES-decrypted stage scripts under Res/Stage/Info.res define a full scene:

- [Default] WorldFile / World_Chat / Collision / Sky / fog / cameras
- repeated [Object] blocks: File= path, Level=
- repeated [Effect] blocks: File=, Position=, Head=, Level=

The client loads WorldFile as the primary court mesh and layers Object/Effect
entries (props, ads, VFX). This module parses that graph for Content Studio.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

from client_crypto import decrypt_set_file
from mesh_codec import client_dat_path_to_ref


_KV = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*(.*)$")
_SECTION = re.compile(r"^\[([^\]]+)\]\s*$")


def _parse_vec3(raw: str) -> list[float] | None:
    parts = [p.strip() for p in raw.replace("\t", " ").split(",") if p.strip()]
    if len(parts) != 3:
        return None
    try:
        return [float(p) for p in parts]
    except ValueError:
        return None


def _clean_value(raw: str) -> str:
    return raw.strip().strip('"').strip()


def parse_stage_set_text(text: str, *, member: str = "") -> dict[str, Any]:
    """Parse decrypted stage .set text into a structured scene graph."""
    default: dict[str, Any] = {}
    objects: list[dict[str, Any]] = []
    effects: list[dict[str, Any]] = []
    bgm: dict[str, str] = {}
    end_present: dict[str, str] = {}
    other_sections: dict[str, list[dict[str, str]]] = {}

    section = "Default"
    current: dict[str, str] = {}

    def flush() -> None:
        nonlocal current
        if not current:
            return
        if section == "Object":
            entry: dict[str, Any] = {
                "file": current.get("File") or current.get("file") or "",
                "level": int(current["Level"]) if current.get("Level", "").isdigit() else current.get("Level"),
            }
            ref = client_dat_path_to_ref(entry["file"]) if entry["file"] else None
            if ref:
                entry["archive"] = ref["archive"]
                entry["member"] = ref["member"]
            objects.append(entry)
        elif section == "Effect":
            entry = {
                "file": current.get("File") or "",
                "level": int(current["Level"]) if current.get("Level", "").isdigit() else current.get("Level"),
            }
            if "Position" in current:
                entry["position"] = _parse_vec3(current["Position"]) or current["Position"]
            if "Head" in current:
                entry["head"] = _parse_vec3(current["Head"]) or current["Head"]
            effects.append(entry)
        elif section == "Default":
            default.update(current)
        elif section in ("BGM", "BGM_TW"):
            bgm.update({f"{section}.{k}" if section != "BGM" else k: v for k, v in current.items()})
        elif section == "EndPresent":
            end_present.update(current)
        else:
            other_sections.setdefault(section, []).append(dict(current))
        current = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        sec = _SECTION.match(line)
        if sec:
            flush()
            section = sec.group(1)
            current = {}
            continue
        m = _KV.match(line)
        if not m:
            continue
        key, val = m.group(1), _clean_value(m.group(2))
        # Repeated [Object]/[Effect] sections: each File= starts a new block if we
        # already have a File (handles consecutive sections without blank flush edge).
        if section in ("Object", "Effect") and key == "File" and "File" in current:
            flush()
        current[key] = val
    flush()

    world = default.get("WorldFile") or default.get("World_Chat") or ""
    world_ref = client_dat_path_to_ref(world) if world else None

    return {
        "member": member,
        "worldFile": world or None,
        "world": world_ref,
        "worldChat": default.get("World_Chat"),
        "skyFile": default.get("SkyFile"),
        "collision": default.get("Collision"),
        "collChat": default.get("Coll_Chat"),
        "fogNear": default.get("FogNear"),
        "fogFar": default.get("FogFar"),
        "shadowColor": default.get("ShadowColor"),
        "camIntro": default.get("Cam_Intro"),
        "camEnter": default.get("Cam_Enter"),
        "default": default,
        "objects": objects,
        "effects": effects,
        "objectCount": len(objects),
        "effectCount": len(effects),
        "bgm": bgm,
        "endPresent": end_present,
        "otherSections": other_sections,
    }


def load_stage_scene(client_root: Path, member: str = "1_Emerald_Beach.set") -> dict[str, Any]:
    """Decrypt + parse one stage set from Res/Stage/Info.res."""
    info = client_root / "Res" / "Stage" / "Info.res"
    with zipfile.ZipFile(info) as archive:
        raw = archive.read(member)
    plain = decrypt_set_file(raw).decode("utf-8", errors="replace")
    scene = parse_stage_set_text(plain, member=member)
    scene["textPreview"] = plain[:2000]
    return scene


def list_stage_sets(client_root: Path) -> list[str]:
    info = client_root / "Res" / "Stage" / "Info.res"
    with zipfile.ZipFile(info) as archive:
        return sorted(n for n in archive.namelist() if n.endswith(".set"))


def load_all_stage_scenes(client_root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for member in list_stage_sets(client_root):
        scene = load_stage_scene(client_root, member)
        # Drop bulky text from bulk dump
        scene.pop("textPreview", None)
        scene.pop("default", None)
        scene.pop("endPresent", None)
        scene.pop("otherSections", None)
        out[member] = scene
    return out
