#!/usr/bin/env python3
"""CLI bridge from Content Studio to JFTSE wind_dragon_slayer tooling."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any


def _jftse_root() -> Path:
    root = Path(os.environ.get("JFTSE_ROOT", "")).expanduser()
    if not root.is_dir():
        raise SystemExit("JFTSE_ROOT is missing or not a directory")
    sys.path.insert(0, str(root))
    return root


def _client_root(jftse: Path) -> Path:
    configured = os.environ.get("JFTSE_STOCK_CLIENT", "").strip()
    if configured:
        path = Path(configured).expanduser()
    else:
        path = jftse / ".jftse-client-linux" / "client"
    if not path.is_dir():
        raise SystemExit(f"stock client not found: {path}")
    return path


def _load_wind_assets():
    from tools.wind_dragon_slayer import wind_assets

    return wind_assets


BANNED_ATLAS_MARKERS = (
    "spaak",
    "spark",
    "electric",
    "cloud_ice",
    "a_cloud",
)


def cmd_health(_: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    client = _client_root(jftse)
    return {
        "ok": True,
        "jftseRoot": str(jftse),
        "stockClient": str(client),
        "particleRes": (client / "Res/Effect/Particle.res").is_file(),
        "itemRes": (client / "Res/Script/Item.res").is_file(),
        "stageInfo": (client / "Res/Stage/Info.res").is_file(),
    }


def cmd_list_atlases(args: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    client = _client_root(jftse)
    wind_assets = _load_wind_assets()
    effect_dir = client / "Res" / "Effect"
    atlases: list[dict[str, Any]] = []
    for archive_path in sorted(effect_dir.glob("Eft*.res")):
        with zipfile.ZipFile(archive_path) as archive:
            for name in archive.namelist():
                if not name.lower().endswith(".tex"):
                    continue
                lower = name.lower()
                banned = any(marker in lower for marker in BANNED_ATLAS_MARKERS)
                class_name = "soft"
                if banned:
                    class_name = "banned"
                elif "wind" in lower or "feather" in lower or "halo_line" in lower:
                    class_name = "windish"
                elif "dust" in lower or "smoke" in lower or "cloud" in lower:
                    class_name = "smoke"
                atlases.append(
                    {
                        "archive": archive_path.name,
                        "member": name,
                        "texturePath": f"Res/Effect/{archive_path.stem}/{Path(name).stem}",
                        "className": class_name,
                        "banned": banned,
                    }
                )
    if args.limit > 0:
        atlases = atlases[: args.limit]
    return {"atlases": atlases, "count": len(atlases)}


def cmd_atlas_preview(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as error:
        raise SystemExit("Pillow is required for atlas-preview") from error
    jftse = _jftse_root()
    client = _client_root(jftse)
    wind_assets = _load_wind_assets()
    archive_path = client / "Res" / "Effect" / args.archive
    with zipfile.ZipFile(archive_path) as archive:
        tex = archive.read(args.member)
    dds = wind_assets.decode_tex(tex)
    image = Image.open(BytesIO(dds)).convert("RGBA")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return {
        "path": str(out),
        "width": image.width,
        "height": image.height,
    }


def _validate_effect_payload(payload: dict[str, Any]) -> None:
    texture = str(payload.get("texturePath", ""))
    lower = texture.lower()
    allow_banned = bool(payload.get("allowBannedAtlas", False))
    if "racket_001" in lower or "racket_002" in lower:
        raise ValueError("SHARED_RACKET_SCRIPT_FORBIDDEN")
    if (not allow_banned) and any(marker in lower for marker in BANNED_ATLAS_MARKERS):
        raise ValueError("BANNED_ATLAS")
    quantity = int(payload.get("quantity", 0))
    if quantity < 1 or quantity > 40:
        raise ValueError("QUANTITY_OUT_OF_RANGE")


def cmd_build_effect(args: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    client = _client_root(jftse)
    wind_assets = _load_wind_assets()
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    try:
        _validate_effect_payload(payload)
    except ValueError as error:
        return {"ok": False, "error": str(error)}

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source_particle = client / "Res" / "Effect" / "Particle.res"
    source_item = client / "Res" / "Script" / "Item.res"
    source_etc = client / "Res" / "Script" / "ETC.res"

    member_name = "Ice_Smoke02.set"
    with zipfile.ZipFile(source_particle) as source:
        encrypted = source.read(member_name)
        racket_001 = source.read("Racket_001.set")
        racket_002 = source.read("Racket_002.set")
    plaintext = wind_assets.decrypt_set(encrypted)

    replacements: dict[bytes, bytes] = {
        b"FrameRate": str(int(payload.get("frameRate", 30))).encode(),
        b"Color": _color_bytes(str(payload.get("color", "80,160,205"))),
        b"PF_OffAxisSpread": _f(payload.get("offAxisSpread", 180.0)),
        b"PF_OffPlaneSpread": _f(payload.get("offPlaneSpread", 180.0)),
        b"PQ_Quantity": str(int(payload.get("quantity", 18))).encode(),
        b"PM_Speed": _f(payload.get("speed", 0.30)),
        b"PM_SpeedVar": _f(payload.get("speedVar", 0.05)),
        b"PT_EmitStop": str(int(payload.get("emitStop", 20))).encode(),
        b"PT_DisplayUntil": b"-1",
        b"PT_Life": str(int(payload.get("life", 16))).encode(),
        b"PT_LifeVar": str(int(payload.get("lifeVar", 2))).encode(),
        b"PS_Size": _f(payload.get("size", 1.40)),
        b"PS_SizeVar": _f(payload.get("sizeVar", 0.25)),
        b"PS_FadeFor": str(int(payload.get("fadeFor", 12))).encode(),
        b"SSC_Phase": _f(payload.get("phase", 180.0)),
        b"SSC_PhaseVar": _f(payload.get("phaseVar", 100.0)),
        b"BM_Amplitude": b"0.00",
        b"BM_AmplitudeVar": b"0.00",
        b"EX_FadeIn": str(int(payload.get("fadeIn", 1))).encode(),
        b"EX_FadeOut": str(int(payload.get("fadeOut", 16))).encode(),
        b"EX_Accel": _accel_bytes(str(payload.get("accel", "0.00,0.01,0.00"))),
        b"TexturePath": f'"{payload.get("texturePath", "Res/Effect/EftB/A_feather")}"'.encode(),
        b"SubTexSize": f'"{payload.get("subTexSize", "STS_64")}"'.encode(),
        b"SubTexCount": str(int(payload.get("subTexCount", 8))).encode(),
        b"SubPlayBack": str(int(payload.get("subPlayBack", 1))).encode(),
        b"SubPlayTime": str(int(payload.get("subPlayTime", 3))).encode(),
        b"SRCBlend": b'"ADUBLEND_SRCALPHA"',
        b"DESTBlend": b'"ADUBLEND_ONE"',
    }
    patched_plain = _apply_replacements(plaintext, replacements)
    target_size = len(encrypted) - 5
    if len(patched_plain) > target_size:
        return {"ok": False, "error": "SCRIPT_TOO_LARGE"}
    patched_plain = patched_plain + (b" " * (target_size - len(patched_plain)))
    patched_member = wind_assets.encrypt_set_to_size(patched_plain, len(encrypted))

    particle_out = out_dir / "Particle.studio.res"
    wind_assets.patch_fixed_archive(
        source_particle,
        particle_out,
        (wind_assets.ArchiveReplacement(name=member_name, content=patched_member),),
    )

    item_out = out_dir / "Item.studio.res"
    etc_out = out_dir / "ETC.studio.res"
    if bool(payload.get("includeItemBinding", True)):
        wind_assets.build_item_binding_archive(source_item, item_out)
        wind_assets.build_racket_effect_archive(source_etc, etc_out)
    else:
        item_out = None
        etc_out = None

    with zipfile.ZipFile(particle_out) as result:
        assert result.read("Racket_001.set") == racket_001
        assert result.read("Racket_002.set") == racket_002
        only = {
            name: result.read(name)
            for name in result.namelist()
            if name not in {"Racket_001.set", "Racket_002.set", member_name}
        }
    with zipfile.ZipFile(source_particle) as source:
        for name, content in only.items():
            if source.read(name) != content:
                return {"ok": False, "error": "UNEXPECTED_MEMBER_MUTATION", "member": name}

    return {
        "ok": True,
        "particleArchive": str(particle_out),
        "itemArchive": None if item_out is None else str(item_out),
        "effectArchive": None if etc_out is None else str(etc_out),
        "slot": member_name,
        "texturePath": payload.get("texturePath"),
    }


def _color_bytes(value: str) -> bytes:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        raise ValueError("COLOR_INVALID")
    return f"{parts[0]},\t{parts[1]},\t{parts[2]}".encode()


def _accel_bytes(value: str) -> bytes:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        raise ValueError("ACCEL_INVALID")
    return f"{parts[0]},\t{parts[1]},\t{parts[2]}".encode()


def _f(value: Any) -> bytes:
    return f"{float(value):.2f}".encode()


def _apply_replacements(source_script: bytes, replacements: dict[bytes, bytes]) -> bytes:
    found: set[bytes] = set()
    result_lines: list[bytes] = []
    for line in source_script.splitlines(keepends=True):
        field = line.split(b"=", 1)[0].strip()
        replacement = replacements.get(field)
        if replacement is None:
            result_lines.append(line)
            continue
        newline = b"\r\n" if line.endswith(b"\r\n") else b"\n"
        result_lines.append(field + b"=" + replacement + newline)
        found.add(field)
    missing = replacements.keys() - found
    if missing:
        names = ", ".join(sorted(field.decode("ascii") for field in missing))
        raise ValueError(f"MISSING_FIELDS:{names}")
    return b"".join(result_lines)


def cmd_list_maps(_: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    sql_path = jftse / "scripts" / "sql" / "maps.sql"
    text = sql_path.read_text(encoding="utf-8")
    maps: list[dict[str, Any]] = []
    for line in text.splitlines():
        if "INSERT INTO S_Maps" not in line:
            continue
        m = re.search(
            r"VALUES\((?P<id>\d+),[^,]*,[^,]*,(?P<bossPlayTime>[^,]*),(?P<breathTime>[^,]*),(?P<description>[^,]*),(?P<isBossStage>[^,]*),\s*(?P<map>\d+),\s*'(?P<name>[^']*)'",
            line,
        )
        if not m:
            continue
        maps.append(
            {
                "id": int(m.group("id")),
                "map": int(m.group("map")),
                "name": m.group("name"),
                "isBossStage": m.group("isBossStage").strip() in {"1", "true", "TRUE"},
            }
        )

    stage_info = _client_root(jftse) / "Res" / "Stage" / "Info.res"
    stage_scripts: list[str] = []
    if stage_info.is_file():
        with zipfile.ZipFile(stage_info) as archive:
            stage_scripts = sorted(archive.namelist())
    return {"maps": maps, "stageScripts": stage_scripts}


def cmd_list_items(args: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    client = _client_root(jftse)
    wind_assets = _load_wind_assets()
    item_res = client / "Res" / "Script" / "Item.res"
    with zipfile.ZipFile(item_res) as archive:
        plaintext = wind_assets.decrypt_set(archive.read("Item_Parts.set")).decode(
            "utf-8",
            errors="replace",
        )
    items: list[dict[str, str]] = []
    for match in re.finditer(
        r'<Item\s+Index="(\d+)"[^>]*Part="([^"]*)"[^>]*Mesh="([^"]*)"[^>]*Tex="([^"]*)"[^>]*Effect="([^"]*)"',
        plaintext,
    ):
        index, part, mesh, tex, effect = match.groups()
        if args.part and part != args.part:
            continue
        name_match = re.search(
            rf'<Item\s+Index="{re.escape(index)}"[^>]*Name_en="([^"]*)"',
            plaintext,
        )
        items.append(
            {
                "index": index,
                "part": part,
                "mesh": mesh,
                "tex": tex,
                "effect": effect,
                "name": name_match.group(1) if name_match else index,
            }
        )
        if args.limit and len(items) >= args.limit:
            break
    return {"items": items, "count": len(items)}


def main() -> None:
    parser = argparse.ArgumentParser(prog="studio_bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")

    p_atlases = sub.add_parser("list-atlases")
    p_atlases.add_argument("--limit", type=int, default=0)

    p_preview = sub.add_parser("atlas-preview")
    p_preview.add_argument("--archive", required=True)
    p_preview.add_argument("--member", required=True)
    p_preview.add_argument("--output", required=True)

    p_build = sub.add_parser("build-effect")
    p_build.add_argument("--payload", required=True)
    p_build.add_argument("--out-dir", required=True)

    sub.add_parser("list-maps")

    p_items = sub.add_parser("list-items")
    p_items.add_argument("--part", default="")
    p_items.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()
    handlers = {
        "health": cmd_health,
        "list-atlases": cmd_list_atlases,
        "atlas-preview": cmd_atlas_preview,
        "build-effect": cmd_build_effect,
        "list-maps": cmd_list_maps,
        "list-items": cmd_list_items,
    }
    result = handlers[args.command](args)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
