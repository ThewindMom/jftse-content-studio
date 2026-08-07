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

    verification = _verify_particle_archive(
        source_particle,
        particle_out,
        member_name=member_name,
        wind_assets=wind_assets,
    )
    if not verification.get("ok"):
        return verification

    return {
        "ok": True,
        "particleArchive": str(particle_out),
        "itemArchive": None if item_out is None else str(item_out),
        "effectArchive": None if etc_out is None else str(etc_out),
        "slot": member_name,
        "texturePath": payload.get("texturePath"),
        "verification": verification,
    }


def _parse_fields(plaintext: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in plaintext.splitlines():
        if b"=" not in line:
            continue
        key, value = line.split(b"=", 1)
        fields[key.strip().decode("ascii", errors="replace")] = (
            value.strip().strip(b'"').decode("ascii", errors="replace")
        )
    return fields


def _verify_particle_archive(
    source_particle: Path,
    particle_out: Path,
    *,
    member_name: str,
    wind_assets: Any,
) -> dict[str, Any]:
    source_bytes = source_particle.read_bytes()
    result_bytes = particle_out.read_bytes()
    with zipfile.ZipFile(source_particle) as source, zipfile.ZipFile(particle_out) as result:
        source_names = source.namelist()
        result_names = result.namelist()
        if source_names != result_names:
            return {"ok": False, "error": "MEMBER_LIST_CHANGED"}
        changed = [
            name
            for name in source_names
            if source.read(name) != result.read(name)
        ]
        if changed != [member_name]:
            return {
                "ok": False,
                "error": "UNEXPECTED_MEMBER_MUTATION",
                "changedMembers": changed,
            }
        fields = _parse_fields(wind_assets.decrypt_set(result.read(member_name)))
        return {
            "ok": True,
            "sharedRacket001Identical": source.read("Racket_001.set")
            == result.read("Racket_001.set"),
            "sharedRacket002Identical": source.read("Racket_002.set")
            == result.read("Racket_002.set"),
            "changedMembers": changed,
            "memberOrderIdentical": source_names == result_names,
            "archiveSizeBytes": len(result_bytes),
            "archiveSizeUnchanged": len(source_bytes) == len(result_bytes),
            "fields": {
                "TexturePath": fields.get("TexturePath", ""),
                "PQ_Quantity": fields.get("PQ_Quantity", ""),
                "Color": fields.get("Color", "").replace("\t", ""),
                "PS_Size": fields.get("PS_Size", ""),
                "SubTexSize": fields.get("SubTexSize", ""),
            },
        }


def cmd_install(args: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    stock = _client_root(jftse).resolve()
    target = Path(args.target_client).expanduser().resolve()
    if target == stock:
        return {"ok": False, "error": "REFUSE_STOCK_CLIENT"}

    local_client = os.environ.get("JFTSE_LOCAL_CLIENT", "").strip()
    allow_prefix = os.environ.get("JFTSE_INSTALL_ALLOW_PREFIX", "").strip()
    allowed = False
    if local_client and target == Path(local_client).expanduser().resolve():
        allowed = True
    if allow_prefix and str(target).startswith(
        str(Path(allow_prefix).expanduser().resolve())
    ):
        allowed = True
    if str(target).startswith("/tmp/") or "/tmp/" in str(target):
        allowed = True
    if not allowed:
        return {"ok": False, "error": "TARGET_NOT_ALLOWLISTED"}

    particle_src = Path(args.particle_archive).resolve()
    if not particle_src.is_file():
        return {"ok": False, "error": "PARTICLE_ARCHIVE_MISSING"}

    dest_particle = target / "Res" / "Effect" / "Particle.res"
    dest_particle.parent.mkdir(parents=True, exist_ok=True)
    dest_particle.write_bytes(particle_src.read_bytes())
    installed: dict[str, str] = {"particle": str(dest_particle)}

    if args.item_archive:
        item_src = Path(args.item_archive).resolve()
        if item_src.is_file():
            dest_item = target / "Res" / "Script" / "Item.res"
            dest_item.parent.mkdir(parents=True, exist_ok=True)
            dest_item.write_bytes(item_src.read_bytes())
            installed["item"] = str(dest_item)
    if args.effect_archive:
        effect_src = Path(args.effect_archive).resolve()
        if effect_src.is_file():
            dest_effect = target / "Res" / "Script" / "ETC.res"
            dest_effect.parent.mkdir(parents=True, exist_ok=True)
            dest_effect.write_bytes(effect_src.read_bytes())
            installed["effect"] = str(dest_effect)

    return {"ok": True, "targetClient": str(target), "installed": installed}


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


def cmd_export_map_sql(args: argparse.Namespace) -> dict[str, Any]:
    maps_payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    selected = {
        int(entry["map"])
        for entry in maps_payload.get("maps", [])
        if "map" in entry
    }
    if not selected:
        return {"ok": False, "error": "NO_MAPS_SELECTED"}
    catalog = cmd_list_maps(args)
    rows = [row for row in catalog["maps"] if int(row["map"]) in selected]
    if not rows:
        return {"ok": False, "error": "MAPS_NOT_FOUND"}
    out = Path(args.out_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "-- Generated by JFTSE Content Studio",
        "-- Metadata-only map seed (binds existing client stages)",
        "",
    ]
    for row in rows:
        lines.append(
            "INSERT INTO S_Maps (id, created, modified, bossPlayTime, breathTime, "
            "description, isBossStage, `map`, name, playTime, triggerBossTime, useBreathTime) "
            f"VALUES({int(row['id'])}, NOW(6), NOW(6), NULL, 100, NULL, "
            f"{1 if row['isBossStage'] else 0}, {int(row['map'])}, "
            f"'{str(row['name']).replace(chr(39), chr(39)+chr(39))}', NULL, NULL, 0) "
            f"ON DUPLICATE KEY UPDATE name=VALUES(name), isBossStage=VALUES(isBossStage);"
        )
        stage = maps_payload.get("stageByMap", {}).get(str(row["map"]))
        if stage:
            lines.append(f"-- suggested Stage/Info.res member for map {row['map']}: {stage}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "path": str(out),
        "count": len(rows),
        "maps": rows,
    }


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
    if args.limit and args.limit > 0:
        # Prefer well-known designer bases first, then fill remaining slots.
        preferred = [item for item in items if item["index"] in {"10728", "10729", "10730"}]
        rest = [item for item in items if item not in preferred]
        items = (preferred + rest)[: args.limit]
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

    p_install = sub.add_parser("install")
    p_install.add_argument("--target-client", required=True)
    p_install.add_argument("--particle-archive", required=True)
    p_install.add_argument("--item-archive", default="")
    p_install.add_argument("--effect-archive", default="")

    sub.add_parser("list-maps")

    p_map_sql = sub.add_parser("export-map-sql")
    p_map_sql.add_argument("--payload", required=True)
    p_map_sql.add_argument("--out-file", required=True)

    p_items = sub.add_parser("list-items")
    p_items.add_argument("--part", default="")
    p_items.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()
    handlers = {
        "health": cmd_health,
        "list-atlases": cmd_list_atlases,
        "atlas-preview": cmd_atlas_preview,
        "build-effect": cmd_build_effect,
        "install": cmd_install,
        "list-maps": cmd_list_maps,
        "export-map-sql": cmd_export_map_sql,
        "list-items": cmd_list_items,
    }
    result = handlers[args.command](args)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
