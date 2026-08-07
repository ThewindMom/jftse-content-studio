#!/usr/bin/env python3
"""CLI bridge from Content Studio to JFTSE wind_dragon_slayer tooling."""

from __future__ import annotations

import argparse
from pathlib import Path as _BridgePath
import sys as _sys
_sys.path.insert(0, str(_BridgePath(__file__).resolve().parent))
import json
import os
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from mesh_codec import (
    apply_transform,
    decode_member,
    decoded_to_dict,
    list_mesh_members,
    mesh_to_gltf,
    mesh_to_obj,
    write_positions_into_dat,
)


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
        expected_texture_path=str(
            payload.get("texturePath", "Res/Effect/EftB/A_feather")
        ),
        expected_quantity=str(int(payload.get("quantity", 18))),
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
    expected_texture_path: str | None = None,
    expected_quantity: str | None = None,
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
        # Allow idempotent rebuilds (no byte delta) when stock already matches payload.
        # Only the target member may change; any other mutation is fatal.
        unexpected = [name for name in changed if name != member_name]
        if unexpected:
            return {
                "ok": False,
                "error": "UNEXPECTED_MEMBER_MUTATION",
                "changedMembers": changed,
            }
        if member_name not in result_names:
            return {"ok": False, "error": "TARGET_MEMBER_MISSING"}
        fields = _parse_fields(wind_assets.decrypt_set(result.read(member_name)))
        texture = fields.get("TexturePath", "")
        quantity = fields.get("PQ_Quantity", "")
        if expected_texture_path and expected_texture_path not in texture:
            return {
                "ok": False,
                "error": "PATCH_FIELDS_MISMATCH",
                "fields": {"TexturePath": texture, "PQ_Quantity": quantity},
            }
        if expected_quantity is not None and quantity != str(expected_quantity):
            return {
                "ok": False,
                "error": "PATCH_FIELDS_MISMATCH",
                "fields": {"TexturePath": texture, "PQ_Quantity": quantity},
            }
        return {
            "ok": True,
            "sharedRacket001Identical": source.read("Racket_001.set")
            == result.read("Racket_001.set"),
            "sharedRacket002Identical": source.read("Racket_002.set")
            == result.read("Racket_002.set"),
            "changedMembers": changed,
            "idempotent": changed == [],
            "memberOrderIdentical": source_names == result_names,
            "archiveSizeBytes": len(result_bytes),
            "archiveSizeUnchanged": len(source_bytes) == len(result_bytes),
            "fields": {
                "TexturePath": texture,
                "PQ_Quantity": quantity,
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


def _parse_map2scenarios(jftse: Path) -> list[dict[str, int]]:
    path = jftse / "scripts" / "sql" / "map2scenarios.sql"
    rows: list[dict[str, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.search(
            r"VALUES\((?P<scenario_id>\d+),\s*(?P<map_id>\d+)\)",
            line,
        )
        if match:
            rows.append(
                {
                    "scenarioId": int(match.group("scenario_id")),
                    "mapId": int(match.group("map_id")),
                }
            )
    return rows


def _parse_guardian2maps(jftse: Path) -> list[dict[str, Any]]:
    path = jftse / "scripts" / "sql" / "guardian2maps.sql"
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.search(
            r"VALUES\((?P<id>\d+),[^,]*,[^,]*,\s*'(?P<side>[^']*)',\s*(?P<boss>[^,]*),\s*(?P<guardian>[^,]*),\s*(?P<map_id>\d+),\s*(?P<scenario_id>\d+),\s*(?P<status_id>\d+)\)",
            line,
        )
        if not match:
            continue
        boss_raw = match.group("boss").strip()
        guardian_raw = match.group("guardian").strip()
        rows.append(
            {
                "id": int(match.group("id")),
                "side": match.group("side"),
                "bossGuardianId": None if boss_raw.upper() == "NULL" else int(boss_raw),
                "guardianId": None
                if guardian_raw.upper() == "NULL"
                else int(guardian_raw),
                "mapId": int(match.group("map_id")),
                "scenarioId": int(match.group("scenario_id")),
                "statusId": int(match.group("status_id")),
            }
        )
    return rows


def _parse_scenarios(jftse: Path) -> list[dict[str, Any]]:
    path = jftse / "scripts" / "sql" / "scenarios.sql"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.search(
            r"VALUES\((?P<id>\d+),.*?,'(?:[^']*)',\s*'(?P<name>[^']*)'",
            line,
        )
        # fallback simpler: first int is id
        if not match:
            match = re.search(r"VALUES\((?P<id>\d+)", line)
            if match:
                rows.append({"id": int(match.group("id")), "name": f"Scenario {match.group('id')}"})
            continue
        rows.append({"id": int(match.group("id")), "name": match.group("name")})
    if not rows:
        # scenarios.sql may use different shape; derive ids from relations
        ids = sorted(
            {
                row["scenarioId"]
                for row in _parse_map2scenarios(jftse)
            }
        )
        rows = [{"id": i, "name": f"Scenario {i}"} for i in ids]
    return rows


def _stage_scripts(client: Path) -> list[str]:
    stage_info = client / "Res" / "Stage" / "Info.res"
    if not stage_info.is_file():
        return []
    with zipfile.ZipFile(stage_info) as archive:
        return sorted(archive.namelist())


def _infer_stage_candidates(map_byte: int, scripts: list[str]) -> list[str]:
    prefix = f"{map_byte}_"
    return [script for script in scripts if script.startswith(prefix)]


def _decode_stage_script(client: Path, script: str) -> dict[str, str]:
    wind_assets = _load_wind_assets()
    stage_info = client / "Res" / "Stage" / "Info.res"
    with zipfile.ZipFile(stage_info) as archive:
        if script not in archive.namelist():
            raise FileNotFoundError(script)
        text = wind_assets.decrypt_set(archive.read(script)).decode("utf-8", errors="replace")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line or line.strip().startswith(";") or line.strip().startswith("["):
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def _resolve_client_asset(client: Path, relative: str) -> dict[str, Any]:
    """Resolve loose files or members inside sibling .res archives."""
    normalized = relative.replace("\\", "/").lstrip("/")
    if not normalized:
        return {"exists": False, "resolved": "", "kind": "empty"}
    direct = client / normalized
    if direct.is_file():
        return {"exists": True, "resolved": str(direct), "kind": "file"}
    parts = Path(normalized).parts
    if len(parts) >= 2:
        member = parts[-1]
        archive = client.joinpath(*parts[:-1]).with_suffix(".res")
        if archive.is_file():
            with zipfile.ZipFile(archive) as handle:
                names = set(handle.namelist())
                if member in names:
                    return {
                        "exists": True,
                        "resolved": f"{archive}::{member}",
                        "kind": "archive-member",
                    }
    return {"exists": False, "resolved": normalized, "kind": "missing"}


def cmd_map_studio_catalog(_: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    client = _client_root(jftse)
    base = cmd_list_maps(_)
    scripts = list(base.get("stageScripts") or _stage_scripts(client))
    map2 = _parse_map2scenarios(jftse)
    guardians = _parse_guardian2maps(jftse)
    scenarios = _parse_scenarios(jftse)
    enriched = []
    for row in base["maps"]:
        map_id = int(row["id"])
        map_byte = int(row["map"])
        scenario_ids = sorted(
            {link["scenarioId"] for link in map2 if link["mapId"] == map_id}
        )
        guardian_rows = [g for g in guardians if g["mapId"] == map_id]
        candidates = _infer_stage_candidates(map_byte, scripts)
        enriched.append(
            {
                **row,
                "scenarioIds": scenario_ids,
                "guardianCount": len(guardian_rows),
                "guardians": guardian_rows[:40],
                "stageCandidates": candidates,
                "defaultStageScript": candidates[0] if candidates else None,
            }
        )
    return {
        "ok": True,
        "maps": enriched,
        "stageScripts": scripts,
        "scenarios": scenarios,
        "relationCounts": {
            "map2scenarios": len(map2),
            "guardian2maps": len(guardians),
        },
    }


def cmd_map_studio_validate(args: argparse.Namespace) -> dict[str, Any]:
    client = _client_root(_jftse_root())
    script = str(args.stage_script)
    scripts = _stage_scripts(client)
    if script not in scripts:
        return {"ok": False, "error": "STAGE_SCRIPT_MISSING", "stageScript": script}
    fields = _decode_stage_script(client, script)
    checks: list[dict[str, Any]] = []
    for key in ("WorldFile", "SkyFile", "Collision", "Coll_Chat", "World_Chat"):
        rel = fields.get(key, "")
        if not rel:
            continue
        resolved = _resolve_client_asset(client, rel)
        checks.append(
            {
                "field": key,
                "path": rel,
                "exists": bool(resolved["exists"]),
                "resolved": resolved["resolved"],
                "kind": resolved["kind"],
            }
        )
    required = [check for check in checks if check["field"] in {"WorldFile", "SkyFile", "Collision"}]
    valid = bool(required) and all(check["exists"] for check in required)
    return {
        "ok": True,
        "valid": valid,
        "stageScript": script,
        "stage": fields,
        "assetChecks": checks,
    }


def cmd_map_studio_export_pack(args: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    map_ids = {int(value) for value in payload.get("mapIds", [])}
    if not map_ids:
        return {"ok": False, "error": "NO_MAP_IDS"}
    include_scenarios = bool(payload.get("includeScenarios", True))
    include_guardians = bool(payload.get("includeGuardians", True))
    stage_by_map_id = {
        str(key): str(value)
        for key, value in dict(payload.get("stageByMapId", {})).items()
    }

    catalog = cmd_map_studio_catalog(args)
    selected = [row for row in catalog["maps"] if int(row["id"]) in map_ids]
    if not selected:
        return {"ok": False, "error": "MAPS_NOT_FOUND"}

    map2 = [row for row in _parse_map2scenarios(jftse) if row["mapId"] in map_ids]
    guardians = [row for row in _parse_guardian2maps(jftse) if row["mapId"] in map_ids]

    out = Path(args.out_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "-- JFTSE Content Studio map pack",
        "-- Relational metadata export (client stage geometry remains stock-bound)",
        "",
        "-- === S_Maps ===",
    ]
    for row in selected:
        stage = stage_by_map_id.get(str(row["id"])) or row.get("defaultStageScript")
        lines.append(
            "INSERT INTO S_Maps (id, created, modified, bossPlayTime, breathTime, "
            "description, isBossStage, `map`, name, playTime, triggerBossTime, useBreathTime) "
            f"VALUES({int(row['id'])}, NOW(6), NOW(6), NULL, 100, NULL, "
            f"{1 if row['isBossStage'] else 0}, {int(row['map'])}, "
            f"'{str(row['name']).replace(chr(39), chr(39)+chr(39))}', NULL, NULL, 0) "
            "ON DUPLICATE KEY UPDATE name=VALUES(name), isBossStage=VALUES(isBossStage);"
        )
        if stage:
            lines.append(
                f"-- stage bind map_id={row['id']} map_byte={row['map']}: Stage/Info.res::{stage}"
            )
    if include_scenarios:
        lines.extend(["", "-- === Map_2_Scenarios ==="])
        for row in map2:
            lines.append(
                "INSERT INTO Map_2_Scenarios (scenario_id, map_id) "
                f"VALUES({row['scenarioId']}, {row['mapId']});"
            )
    if include_guardians:
        lines.extend(["", "-- === Guardian_2_Maps ==="])
        for row in guardians:
            boss = "NULL" if row["bossGuardianId"] is None else str(row["bossGuardianId"])
            guardian = "NULL" if row["guardianId"] is None else str(row["guardianId"])
            lines.append(
                "INSERT INTO Guardian_2_Maps (id, created, modified, side, boss_guardian_id, "
                "guardian_id, map_id, scenario_id, status_id) VALUES("
                f"{row['id']}, NOW(6), NOW(6), '{row['side']}', {boss}, {guardian}, "
                f"{row['mapId']}, {row['scenarioId']}, {row['statusId']});"
            )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "path": str(out),
        "mapCount": len(selected),
        "scenarioLinkCount": len(map2) if include_scenarios else 0,
        "guardianCount": len(guardians) if include_guardians else 0,
        "maps": selected,
    }



def cmd_mesh_list(_: argparse.Namespace) -> dict[str, Any]:
    client = _client_root(_jftse_root())
    items = list_mesh_members(client)
    return {"ok": True, "meshes": items, "count": len(items)}


def cmd_mesh_parse(args: argparse.Namespace) -> dict[str, Any]:
    client = _client_root(_jftse_root())
    mesh = decode_member(client, args.archive, args.member)
    include_geometry = not bool(args.meta_only)
    payload = decoded_to_dict(mesh, include_geometry=include_geometry)
    return {"ok": True, "mesh": payload}


def cmd_mesh_export(args: argparse.Namespace) -> dict[str, Any]:
    client = _client_root(_jftse_root())
    mesh = decode_member(client, args.archive, args.member)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.member).stem
    obj_path = out / f"{stem}.obj"
    gltf_path = out / f"{stem}.gltf"
    meta_path = out / f"{stem}.meta.json"
    obj_path.write_text(mesh_to_obj(mesh), encoding="utf-8")
    gltf_path.write_text(json.dumps(mesh_to_gltf(mesh)), encoding="utf-8")
    meta_path.write_text(json.dumps(decoded_to_dict(mesh, include_geometry=False), indent=2), encoding="utf-8")
    return {
        "ok": True,
        "obj": str(obj_path),
        "gltf": str(gltf_path),
        "meta": str(meta_path),
        "vertexCount": mesh.vertexCount,
        "indexCount": mesh.indexCount,
        "decodeMode": mesh.decodeMode,
    }


def cmd_mesh_transform(args: argparse.Namespace) -> dict[str, Any]:
    client = _client_root(_jftse_root())
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    archive = str(payload["archive"])
    member = str(payload["member"])
    translate = tuple(float(v) for v in payload.get("translate", [0, 0, 0]))
    scale = tuple(float(v) for v in payload.get("scale", [1, 1, 1]))
    rotate = tuple(float(v) for v in payload.get("rotateDeg", [0, 0, 0]))
    mesh = decode_member(client, archive, member)
    transformed = apply_transform(mesh.positions, translate=translate, scale=scale, rotate_deg=rotate)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(client / archive) as handle:
        original = handle.read(member)
    rewritten = write_positions_into_dat(original, mesh.vertexOffset, transformed)
    dat_path = out_dir / member
    dat_path.write_bytes(rewritten)
    mesh.positions = transformed
    obj_path = out_dir / f"{Path(member).stem}.transformed.obj"
    obj_path.write_text(mesh_to_obj(mesh), encoding="utf-8")
    return {
        "ok": True,
        "dat": str(dat_path),
        "obj": str(obj_path),
        "byteLength": len(rewritten),
        "sameSize": len(rewritten) == len(original),
        "vertexCount": len(transformed),
    }


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

    sub.add_parser("map-studio-catalog")

    p_map_validate = sub.add_parser("map-studio-validate")
    p_map_validate.add_argument("--stage-script", required=True)

    p_map_pack = sub.add_parser("map-studio-export-pack")
    p_map_pack.add_argument("--payload", required=True)
    p_map_pack.add_argument("--out-file", required=True)

    sub.add_parser("mesh-list")

    p_mesh_parse = sub.add_parser("mesh-parse")
    p_mesh_parse.add_argument("--archive", required=True)
    p_mesh_parse.add_argument("--member", required=True)
    p_mesh_parse.add_argument("--meta-only", action="store_true")

    p_mesh_export = sub.add_parser("mesh-export")
    p_mesh_export.add_argument("--archive", required=True)
    p_mesh_export.add_argument("--member", required=True)
    p_mesh_export.add_argument("--out-dir", required=True)

    p_mesh_transform = sub.add_parser("mesh-transform")
    p_mesh_transform.add_argument("--payload", required=True)
    p_mesh_transform.add_argument("--out-dir", required=True)

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
        "map-studio-catalog": cmd_map_studio_catalog,
        "map-studio-validate": cmd_map_studio_validate,
        "map-studio-export-pack": cmd_map_studio_export_pack,
        "list-items": cmd_list_items,
        "mesh-list": cmd_mesh_list,
        "mesh-parse": cmd_mesh_parse,
        "mesh-export": cmd_mesh_export,
        "mesh-transform": cmd_mesh_transform,
    }
    result = handlers[args.command](args)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
