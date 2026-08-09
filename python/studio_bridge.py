#!/usr/bin/env python3
"""CLI bridge from Content Studio to JFTSE wind_dragon_slayer tooling."""

from __future__ import annotations

import argparse
from pathlib import Path as _BridgePath
import sys as _sys

# Support package imports (`python.bone_attach`) and flat sibling imports.
_PKG_DIR = _BridgePath(__file__).resolve().parent
_STUDIO_ROOT = _PKG_DIR.parent
if str(_STUDIO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_STUDIO_ROOT))
if str(_PKG_DIR) not in _sys.path:
    _sys.path.insert(0, str(_PKG_DIR))

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
from stage_validation import validate_stage_script
from playtest_preflight import run_local_preflight


def _jftse_root() -> Path:
    root = Path(os.environ.get("JFTSE_ROOT", "")).expanduser()
    if not root.is_dir():
        raise SystemExit("JFTSE_ROOT is missing or not a directory")
    sys.path.insert(0, str(root))
    return root


def _client_root(jftse: Path) -> Path:
    configured = os.environ.get("JFTSE_STOCK_CLIENT", "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend(
        [
            jftse / ".jftse-client-linux" / "client",
            jftse / "FantaTennis-Local-Client" / "client",
        ]
    )
    for path in candidates:
        if path.is_dir():
            return path
    raise SystemExit(f"stock client not found; tried: {', '.join(str(p) for p in candidates)}")


def _load_wind_assets():
    import importlib
    import sys
    from pathlib import Path as _P

    # Ensure JFTSE tools package is importable even if caller skipped _jftse_root().
    root = _P(__import__("os").environ.get("JFTSE_ROOT", "")).expanduser()
    if root.is_dir() and str(root) not in sys.path:
        sys.path.insert(0, str(root))
    mod = importlib.import_module("tools.wind_dragon_slayer.wind_assets")
    return mod


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


def _load_s_maps(jftse: Path) -> list[Any]:
    from map_sql_export import parse_s_maps

    return parse_s_maps((jftse / "scripts" / "sql" / "maps.sql").read_text(encoding="utf-8"))


def cmd_list_maps(_: argparse.Namespace) -> dict[str, Any]:
    jftse = _jftse_root()
    maps = [row.as_catalog_dict() for row in _load_s_maps(jftse)]
    stage_info = _client_root(jftse) / "Res" / "Stage" / "Info.res"
    stage_scripts: list[str] = []
    if stage_info.is_file():
        with zipfile.ZipFile(stage_info) as archive:
            stage_scripts = sorted(archive.namelist())
    return {"maps": maps, "stageScripts": stage_scripts}


def cmd_export_map_sql(args: argparse.Namespace) -> dict[str, Any]:
    from map_sql_export import (
        apply_map_draft,
        build_map_pack_sql,
        parse_guardian2maps,
        parse_map2scenarios,
        parse_scenarios,
    )

    jftse = _jftse_root()
    maps_payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    selected_bytes = {
        int(entry["map"])
        for entry in maps_payload.get("maps", [])
        if "map" in entry
    }
    if not selected_bytes:
        return {"ok": False, "error": "NO_MAPS_SELECTED"}

    include_relations = bool(maps_payload.get("includeRelations", True))
    seed_rows = _load_s_maps(jftse)
    selected = [row for row in seed_rows if row.map in selected_bytes]
    if not selected:
        return {"ok": False, "error": "MAPS_NOT_FOUND"}

    # Optional per-map-byte draft overrides from bulk UI.
    drafts_by_byte = {
        int(entry["map"]): entry
        for entry in maps_payload.get("maps", [])
        if "map" in entry
    }
    selected = [apply_map_draft(row, drafts_by_byte.get(row.map)) for row in selected]
    map_ids = {row.id for row in selected}

    map2 = parse_map2scenarios(
        (jftse / "scripts" / "sql" / "map2scenarios.sql").read_text(encoding="utf-8")
    )
    guardians = parse_guardian2maps(
        (jftse / "scripts" / "sql" / "guardian2maps.sql").read_text(encoding="utf-8")
    )
    scenarios = parse_scenarios(
        (jftse / "scripts" / "sql" / "scenarios.sql").read_text(encoding="utf-8")
    )
    map2_sel = [row for row in map2 if row.map_id in map_ids]
    g_sel = [row for row in guardians if row.map_id in map_ids]
    scenario_ids = {row.scenario_id for row in map2_sel}
    scn_sel = [row for row in scenarios if row.id in scenario_ids]

    stage_by_map_id = {
        str(row.id): str(maps_payload.get("stageByMap", {}).get(str(row.map), "") or "")
        for row in selected
    }
    stage_by_map_id = {key: value for key, value in stage_by_map_id.items() if value}
    client = _client_root(jftse)
    for row in selected:
        validation = validate_stage_script(
            client,
            stage_by_map_id.get(str(row.id), ""),
        )
        if not bool(validation["valid"]):
            return {
                "ok": False,
                "error": "STAGE_VALIDATION_REQUIRED",
                "validation": validation,
            }

    sql = build_map_pack_sql(
        maps=selected,
        map2=map2_sel if include_relations else [],
        guardians=g_sel if include_relations else [],
        scenarios=scn_sel if include_relations else [],
        stage_by_map_id=stage_by_map_id,
        include_scenarios=include_relations,
        include_guardians=include_relations,
        include_m_scenarios=include_relations,
    )
    # Keep legacy header for bulk seed exports.
    sql = sql.replace(
        "-- JFTSE Content Studio map pack\n-- Relational metadata export aligned with wiki Database Schema",
        "-- Generated by JFTSE Content Studio\n-- Metadata map seed (wiki-aligned columns + optional relations)",
        1,
    )
    out = Path(args.out_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(sql, encoding="utf-8")
    return {
        "ok": True,
        "path": str(out),
        "count": len(selected),
        "maps": [row.as_catalog_dict() for row in selected],
        "scenarioLinkCount": len(map2_sel) if include_relations else 0,
        "guardianCount": len(g_sel) if include_relations else 0,
        "scenarioDefCount": len(scn_sel) if include_relations else 0,
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
    from map_sql_export import parse_map2scenarios

    return [
        {"scenarioId": row.scenario_id, "mapId": row.map_id}
        for row in parse_map2scenarios(
            (jftse / "scripts" / "sql" / "map2scenarios.sql").read_text(encoding="utf-8")
        )
    ]


def _parse_guardian2maps(jftse: Path) -> list[dict[str, Any]]:
    from map_sql_export import parse_guardian2maps

    return [
        row.as_catalog_dict()
        for row in parse_guardian2maps(
            (jftse / "scripts" / "sql" / "guardian2maps.sql").read_text(encoding="utf-8")
        )
    ]


def _parse_scenarios(jftse: Path) -> list[dict[str, Any]]:
    from map_sql_export import parse_map2scenarios, parse_scenarios

    path = jftse / "scripts" / "sql" / "scenarios.sql"
    if path.is_file():
        rows = [row.as_catalog_dict() for row in parse_scenarios(path.read_text(encoding="utf-8"))]
        if rows:
            return rows
    # Fallback: derive scenario ids from link table if seed parse fails.
    links = parse_map2scenarios(
        (jftse / "scripts" / "sql" / "map2scenarios.sql").read_text(encoding="utf-8")
    )
    link_ids = sorted({link.scenario_id for link in links})
    return [{"id": i, "name": f"Scenario {i}"} for i in link_ids]


def _stage_scripts(client: Path) -> list[str]:
    stage_info = client / "Res" / "Stage" / "Info.res"
    if not stage_info.is_file():
        return []
    with zipfile.ZipFile(stage_info) as archive:
        return sorted(archive.namelist())


def _infer_stage_candidates(map_byte: int, scripts: list[str]) -> list[str]:
    prefix = f"{map_byte}_"
    return [script for script in scripts if script.startswith(prefix)]


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
            "scenarios": len(scenarios),
        },
    }


def cmd_map_studio_validate(args: argparse.Namespace) -> dict[str, Any]:
    client = _client_root(_jftse_root())
    script = str(args.stage_script)
    validation = validate_stage_script(client, script)
    return {"ok": bool(validation["valid"]), **validation}


def cmd_map_studio_export_pack(args: argparse.Namespace) -> dict[str, Any]:
    from map_sql_export import (
        apply_map_draft,
        build_map_pack_sql,
        parse_guardian2maps,
        parse_map2scenarios,
        parse_scenarios,
    )

    jftse = _jftse_root()
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    map_ids = {int(value) for value in payload.get("mapIds", [])}
    if not map_ids:
        return {"ok": False, "error": "NO_MAP_IDS"}
    include_scenarios = bool(payload.get("includeScenarios", True))
    include_guardians = bool(payload.get("includeGuardians", True))
    include_m_scenarios = bool(payload.get("includeMScenarios", include_scenarios))
    stage_by_map_id = {
        str(key): str(value)
        for key, value in dict(payload.get("stageByMapId", {})).items()
        if value
    }

    seed_rows = _load_s_maps(jftse)
    selected_seed = [row for row in seed_rows if row.id in map_ids]
    if not selected_seed:
        return {"ok": False, "error": "MAPS_NOT_FOUND"}

    # Draft may be a single object (UI) or mapId -> fields.
    draft_raw = payload.get("draft")
    drafts_by_id: dict[int, dict[str, Any]] = {}
    if isinstance(draft_raw, dict):
        # Single draft applies to all selected when no numeric keys.
        numeric_keys = [key for key in draft_raw if str(key).isdigit()]
        if numeric_keys:
            drafts_by_id = {int(key): dict(draft_raw[key]) for key in numeric_keys}
        else:
            for map_id in map_ids:
                drafts_by_id[map_id] = dict(draft_raw)
    map_overrides = payload.get("mapOverrides")
    if isinstance(map_overrides, dict):
        for key, value in map_overrides.items():
            if str(key).isdigit() and isinstance(value, dict):
                drafts_by_id[int(key)] = {**drafts_by_id.get(int(key), {}), **value}

    selected = [
        apply_map_draft(row, drafts_by_id.get(row.id)) for row in selected_seed
    ]

    # Fill missing stage binds from catalog defaults.
    catalog = cmd_map_studio_catalog(args)
    for row in catalog["maps"]:
        mid = str(row["id"])
        if mid in stage_by_map_id:
            continue
        default = row.get("defaultStageScript")
        if default and int(row["id"]) in map_ids:
            stage_by_map_id[mid] = str(default)
    client = _client_root(jftse)
    for row in selected:
        validation = validate_stage_script(
            client,
            stage_by_map_id.get(str(row.id), ""),
        )
        if not bool(validation["valid"]):
            return {
                "ok": False,
                "error": "STAGE_VALIDATION_REQUIRED",
                "validation": validation,
            }

    map2 = [
        row
        for row in parse_map2scenarios(
            (jftse / "scripts" / "sql" / "map2scenarios.sql").read_text(encoding="utf-8")
        )
        if row.map_id in map_ids
    ]
    guardians = [
        row
        for row in parse_guardian2maps(
            (jftse / "scripts" / "sql" / "guardian2maps.sql").read_text(encoding="utf-8")
        )
        if row.map_id in map_ids
    ]
    scenario_ids = {row.scenario_id for row in map2}
    scenarios = [
        row
        for row in parse_scenarios(
            (jftse / "scripts" / "sql" / "scenarios.sql").read_text(encoding="utf-8")
        )
        if row.id in scenario_ids
    ]

    sql = build_map_pack_sql(
        maps=selected,
        map2=map2,
        guardians=guardians,
        scenarios=scenarios,
        stage_by_map_id=stage_by_map_id,
        include_scenarios=include_scenarios,
        include_guardians=include_guardians,
        include_m_scenarios=include_m_scenarios,
    )
    out = Path(args.out_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(sql, encoding="utf-8")
    return {
        "ok": True,
        "path": str(out),
        "mapCount": len(selected),
        "scenarioLinkCount": len(map2) if include_scenarios else 0,
        "guardianCount": len(guardians) if include_guardians else 0,
        "scenarioDefCount": len(scenarios) if include_scenarios and include_m_scenarios else 0,
        "maps": [row.as_catalog_dict() for row in selected],
    }



def cmd_mesh_list(_: argparse.Namespace) -> dict[str, Any]:
    client = _client_root(_jftse_root())
    items = list_mesh_members(client)
    return {"ok": True, "meshes": items, "count": len(items)}


def cmd_item_mesh_resolve(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve shop mesh index → Player Item*.res DAT via AES-decrypted Info_Item_Mesh."""
    import importlib

    from mesh_codec import decode_member, decoded_to_dict

    # Package-style import so item_mesh relative imports resolve.
    item_mesh = importlib.import_module("python.item_mesh")
    resolve_item_mesh_path = item_mesh.resolve_item_mesh_path
    client = _client_root(_jftse_root())
    mesh_index = str(getattr(args, "mesh_index", "") or "")
    char = str(getattr(args, "char", "") or "NIKI")
    if not mesh_index:
        return {"ok": False, "error": "MESH_INDEX_REQUIRED"}
    resolved = resolve_item_mesh_path(client, mesh_index, char=char)
    if not resolved:
        return {"ok": False, "error": "ITEM_MESH_NOT_FOUND"}
    include_geometry = not bool(getattr(args, "meta_only", False))
    mesh = decode_member(client, resolved["archive"], resolved["member"])
    payload = decoded_to_dict(mesh, include_geometry=include_geometry)
    # Multi-material equipment table (positional stems → .tex candidates)
    from mesh_meta import analyze_member

    meta = analyze_member(client, resolved["archive"], resolved["member"])
    equip_table = meta.get("equipmentMaterialTable")
    materials = meta.get("materials") or payload.get("materials") or []
    return {
        "ok": True,
        "resolved": resolved,
        "mesh": payload,
        "equipmentMaterialTable": equip_table,
        "materials": materials,
        "hasMultiMaterial": bool(meta.get("hasMultiMaterial")),
        "silhouette": {
            "mode": "equipment-material-table"
            if equip_table
            else "recovered-materials",
            "stemCount": (equip_table or {}).get("count") or len(materials),
            "stems": (equip_table or {}).get("stems")
            or [m.get("name") for m in materials if isinstance(m, dict)],
            "note": "Studio draws best-effort multi-stem albedo; not full DX9 FVF submesh ranges.",
        },
    }


def cmd_stage_set_decrypt(args: argparse.Namespace) -> dict[str, Any]:
    """Decrypt stage .set from Info.res (AES TIMOTEI_ZION) to plaintext fields."""
    from client_crypto import decrypt_set_file

    client = _client_root(_jftse_root())
    member = str(getattr(args, "member", "") or "1_Emerald_Beach.set")
    with zipfile.ZipFile(client / "Res" / "Stage" / "Info.res") as archive:
        raw = archive.read(member)
    plain = decrypt_set_file(raw).decode("utf-8", errors="replace")
    fields: dict[str, str] = {}
    for line in plain.splitlines():
        line = line.strip()
        if not line or line.startswith("[") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        fields[key.strip()] = val.strip().strip('"')
    return {"ok": True, "member": member, "fields": fields, "text": plain[:4000]}


def cmd_stage_scene(args: argparse.Namespace) -> dict[str, Any]:
    """Parse AES stage .set into WorldFile + [Object]/[Effect] scene graph."""
    from stage_scene import list_stage_sets, load_all_stage_scenes, load_stage_scene

    client = _client_root(_jftse_root())
    member = str(getattr(args, "member", "") or "")
    list_all = bool(getattr(args, "list_all", False))
    if list_all or member in ("*", "all"):
        scenes = load_all_stage_scenes(client)
        return {
            "ok": True,
            "count": len(scenes),
            "sets": list_stage_sets(client),
            "scenes": scenes,
        }
    if not member:
        member = "1_Emerald_Beach.set"
    scene = load_stage_scene(client, member)
    return {"ok": True, "scene": scene}


def cmd_map_catalog(args: argparse.Namespace) -> dict[str, Any]:
    """Decrypt MapSet Script catalogs (objects / tiles / houses)."""
    from map_catalog import load_map_catalogs

    client = _client_root(_jftse_root())
    catalog = load_map_catalogs(client)
    return {"ok": True, "catalog": catalog}


def cmd_ftm_parse(args: argparse.Namespace) -> dict[str, Any]:
    """Parse FTM/PRJ map placement files (FT-ResTool schema)."""
    from ftm_codec import FtmParseError, load_ftm_from_res, load_prj_from_res, parse_ftm_bytes, parse_prj_bytes

    client = _client_root(_jftse_root())
    archive = str(getattr(args, "archive", "") or "")
    member = str(getattr(args, "member", "") or "")
    try:
        if member.lower().endswith(".prj"):
            if archive:
                prj = load_prj_from_res(client, archive, member)
            else:
                prj = parse_prj_bytes(Path(member).read_bytes())
            return {"ok": True, "kind": "prj", "prj": prj}
        if archive:
            ftm = load_ftm_from_res(client, archive, member)
        else:
            ftm = parse_ftm_bytes(Path(member).read_bytes())
        # Compact tile indices in API (full grid can be huge)
        payload = ftm.to_dict()
        for layer in payload.get("tileLayers", []):
            idxs = layer.get("indices") or []
            layer["indexCount"] = len(idxs)
            layer["indicesSample"] = idxs[:32]
            del layer["indices"]
        return {"ok": True, "kind": "ftm", "ftm": payload}
    except FtmParseError as exc:
        return {"ok": False, "error": "FTM_PARSE_FAILED", "detail": str(exc)}


def cmd_ftm_export(args: argparse.Namespace) -> dict[str, Any]:
    """Patch scene placements and write a new .ftm under out-dir (never stock client)."""
    import json
    from pathlib import Path

    from ftm_codec import (
        FtmParseError,
        load_ftm_from_res,
        patch_scene_objects,
        serialize_ftm,
    )

    client = _client_root(_jftse_root())
    archive = str(getattr(args, "archive", "") or "")
    member = str(getattr(args, "member", "") or "")
    out_dir = Path(str(getattr(args, "out_dir", "") or ""))
    patches_raw = str(getattr(args, "patches", "") or "[]")
    if not archive or not member:
        return {"ok": False, "error": "ARCHIVE_AND_MEMBER_REQUIRED"}
    if not out_dir:
        return {"ok": False, "error": "OUT_DIR_REQUIRED"}
    try:
        patches = json.loads(patches_raw) if patches_raw else []
        if not isinstance(patches, list):
            return {"ok": False, "error": "PATCHES_MUST_BE_ARRAY"}
        ftm = load_ftm_from_res(client, archive, member)
        patched = patch_scene_objects(ftm, patches) if patches else ftm
        blob = serialize_ftm(patched)
        # Round-trip verify before write
        from ftm_codec import parse_ftm_bytes

        verify = parse_ftm_bytes(blob)
        if len(verify.sceneObjects) != len(patched.sceneObjects):
            return {
                "ok": False,
                "error": "FTM_ROUNDTRIP_MISMATCH",
                "detail": "sceneObjectCount changed after serialize",
            }
        out_dir.mkdir(parents=True, exist_ok=True)
        out_name = Path(member).name
        if not out_name.lower().endswith(".ftm"):
            out_name = f"{out_name}.ftm"
        out_path = out_dir / out_name
        out_path.write_bytes(blob)
        return {
            "ok": True,
            "path": str(out_path),
            "byteLength": len(blob),
            "sourceByteLength": ftm.byteLength,
            "sceneObjectCount": len(verify.sceneObjects),
            "patchesApplied": len(patches),
            "sceneObjects": [
                {
                    "index": i,
                    "prefabIndex": o.prefabIndex,
                    "x": o.x,
                    "y": o.y,
                    "scaleHeight": o.scaleHeight,
                    "scaleWidth": o.scaleWidth,
                    "rotationY": o.rotationY,
                    "rotationX": o.rotationX,
                    "prefabName": o.prefabName,
                }
                for i, o in enumerate(verify.sceneObjects)
            ],
        }
    except FtmParseError as exc:
        return {"ok": False, "error": "FTM_EXPORT_FAILED", "detail": str(exc)}
    except FileNotFoundError as exc:
        return {"ok": False, "error": "FTM_ARCHIVE_NOT_FOUND", "detail": str(exc)}
    except KeyError as exc:
        return {"ok": False, "error": "FTM_MEMBER_NOT_FOUND", "detail": str(exc)}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": "PATCHES_JSON_INVALID", "detail": str(exc)}


def cmd_ani_parse(args: argparse.Namespace) -> dict[str, Any]:
    """Parse character .ani animation header + position tracks.

    ``--max-frames``: positive = compact sample; ``0`` or negative = all frames
    (for ANI scrubbers / live attach). Default remains 8 for light API clients.
    ``--clip-index``: multi-clip float3 stack index (default 0).
    ``--motion``: motion name (e.g. RunForward.ani); overrides clip-index when found.
    ``--channel``: ``A`` (primary positions) or ``C`` (secondary float3 stack).
    ``--char``: optional character token to label tracks from body skeleton order.
    """
    from ani_client_re import resolve_motion_clip_index
    from ani_codec import AniParseError, load_ani_member
    from bone_attach import extract_skeleton_palette, _mesh_archive_rel, _prefer_body_member

    client = _client_root(_jftse_root())
    archive = str(getattr(args, "archive", "") or "")
    member = str(getattr(args, "member", "") or "")
    raw_max = getattr(args, "max_frames", 8)
    try:
        max_frames_int = int(raw_max)
    except (TypeError, ValueError):
        max_frames_int = 8
    try:
        clip_index = int(getattr(args, "clip_index", 0) or 0)
    except (TypeError, ValueError):
        clip_index = 0
    motion = str(getattr(args, "motion", "") or "").strip()
    channel = str(getattr(args, "channel", "A") or "A")
    char = str(getattr(args, "char", "") or "").strip()
    # 0 / negative → full tracks (None in to_dict)
    max_frames: int | None = None if max_frames_int <= 0 else max_frames_int
    bone_names: list[str] | None = None
    skeleton: list[Any] | None = None
    if char:
        try:
            mesh_rel = _mesh_archive_rel(char)
            with zipfile.ZipFile(client / mesh_rel) as zf:
                body = _prefer_body_member(list(zf.namelist()), char)
                skeleton = list(extract_skeleton_palette(zf.read(body)))
                bone_names = [b.name for b in skeleton]
        except (OSError, KeyError, zipfile.BadZipFile):
            bone_names = None
            skeleton = None
    try:
        # Resolve motion name → clipIndex from on-disk name table when provided
        resolved_motion: str | None = None
        if motion:
            with zipfile.ZipFile(client / archive) as zf:
                raw = zf.read(member)
            resolved = resolve_motion_clip_index(raw, motion)
            if resolved is None:
                return {
                    "ok": False,
                    "error": "ANI_MOTION_NOT_FOUND",
                    "detail": f"motion {motion!r} not in name table",
                }
            clip_index = resolved
            resolved_motion = motion
        ani = load_ani_member(
            client,
            archive,
            member,
            bone_names=bone_names,
            clip_index=clip_index,
            channel=channel,
            skeleton=skeleton,
        )
        payload = ani.to_dict(max_frames=max_frames)
        payload["sampled"] = max_frames is not None
        payload["sampleMaxFrames"] = max_frames
        payload["clipIndex"] = clip_index
        payload["channel"] = channel.upper()
        if resolved_motion is not None:
            payload["motion"] = resolved_motion
        # Surface motion catalog at top-level for UI selectors
        probe = payload.get("sectionProbe") or {}
        catalog = (
            probe.get("motionCatalog")
            or (probe.get("clientDecoderHypothesis") or {}).get("motionCatalog")
            or []
        )
        if catalog:
            payload["motionCatalog"] = catalog
            if not payload.get("motion"):
                for entry in catalog:
                    if entry.get("clipIndex") == clip_index and entry.get("name"):
                        payload["motion"] = entry["name"]
                        break
        # quat when file extract OR hierarchical-derived conf; else hierarchical-fk
        hyp = (payload.get("sectionProbe") or {}).get("rotationHypothesis") or {}
        if payload.get("hasRotations"):
            payload["driveMode"] = "quat"
            if hyp.get("rotationSource"):
                payload["rotationSource"] = hyp["rotationSource"]
        else:
            payload["driveMode"] = str(
                hyp.get("recommendedDriveMode") or "hierarchical-fk"
            )
        if bone_names is not None:
            payload["boneNames"] = bone_names[: payload.get("trackCount", 0) or 0]
        return {"ok": True, "ani": payload}
    except AniParseError as exc:
        return {"ok": False, "error": "ANI_PARSE_FAILED", "detail": str(exc)}
    except KeyError as exc:
        return {"ok": False, "error": "ANI_MEMBER_NOT_FOUND", "detail": str(exc)}
    except FileNotFoundError as exc:
        return {"ok": False, "error": "ANI_ARCHIVE_NOT_FOUND", "detail": str(exc)}


def cmd_bone_attach(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve Bone_Racket (or other) socket transform from character body mesh."""
    from bone_attach import load_body_attach

    client = _client_root(_jftse_root())
    char = str(getattr(args, "char", "") or "NIKI")
    bone = str(getattr(args, "attach_bone", "") or "Bone_Racket")
    return load_body_attach(client, char=char, attach_bone=bone)


def cmd_skin_parse(args: argparse.Namespace) -> dict[str, Any]:
    """Extract 56-byte skinned vertices (weights/indices/pos/normal/uv) from body DAT."""
    from skin_codec import load_body_skin

    client = _client_root(_jftse_root())
    char = str(getattr(args, "char", "") or "NIKI")
    include = bool(getattr(args, "include_vertices", False))
    try:
        max_verts = int(getattr(args, "max_vertices", 2000) or 2000)
    except (TypeError, ValueError):
        max_verts = 2000
    try:
        return load_body_skin(
            client,
            char=char,
            include_vertices=include,
            max_vertices=max_verts,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "error": "SKIN_ARCHIVE_NOT_FOUND", "detail": str(exc)}
    except KeyError as exc:
        return {"ok": False, "error": "SKIN_MEMBER_NOT_FOUND", "detail": str(exc)}
    except Exception as exc:  # noqa: BLE001 — bridge boundary
        return {"ok": False, "error": "SKIN_PARSE_FAILED", "detail": str(exc)}


def cmd_mesh_meta(args: argparse.Namespace) -> dict[str, Any]:
    """Extract multi-material texture names + bone/socket table from a mesh DAT."""
    from mesh_meta import analyze_member

    client = _client_root(_jftse_root())
    meta = analyze_member(client, args.archive, args.member)
    return {"ok": True, "meta": meta}


def cmd_mesh_parse(args: argparse.Namespace) -> dict[str, Any]:
    from mesh_meta import analyze_member

    client = _client_root(_jftse_root())
    mesh = decode_member(client, args.archive, args.member)
    include_geometry = not bool(args.meta_only)
    payload = decoded_to_dict(mesh, include_geometry=include_geometry)
    try:
        meta = analyze_member(client, args.archive, args.member)
        payload["materials"] = meta["materials"]
        payload["materialCount"] = meta["materialCount"]
        payload["bones"] = meta["bones"]
        payload["boneCount"] = meta["boneCount"]
        payload["sockets"] = meta["sockets"]
        payload["hasSkeleton"] = meta["hasSkeleton"]
        payload["hasMultiMaterial"] = meta["hasMultiMaterial"]
        payload["headerFields"] = meta["header"]
    except Exception as exc:  # noqa: BLE001 — non-fatal RE enrichment
        payload["metaError"] = str(exc)
    return {"ok": True, "mesh": payload}


def cmd_mesh_texture(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve + decrypt stock stage .tex → PNG path for mesh preview materials."""
    from mesh_texture import load_stage_texture_png, resolve_stage_texture

    client = _client_root(_jftse_root())
    archive = str(getattr(args, "archive", "") or "")
    member = str(getattr(args, "member", "") or "")
    mesh_member = str(getattr(args, "mesh_member", "") or "")
    if mesh_member and (not archive or not member):
        resolved = resolve_stage_texture(client, mesh_member)
        if not resolved:
            return {"ok": False, "error": "TEXTURE_NOT_RESOLVED"}
        archive, member = resolved["archive"], resolved["member"]
        source = resolved["source"]
    else:
        source = "explicit"
    if not archive or not member:
        return {"ok": False, "error": "ARCHIVE_AND_MEMBER_REQUIRED"}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{Path(member).stem}.png"
    png_path.write_bytes(load_stage_texture_png(client, archive, member))
    return {
        "ok": True,
        "archive": archive,
        "member": member,
        "png": str(png_path),
        "source": source,
        "bytes": png_path.stat().st_size,
    }


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
    def _vec3(raw: object, default: tuple[float, float, float]) -> tuple[float, float, float]:
        if not isinstance(raw, (list, tuple)) or len(raw) < 3:
            return default
        return (float(raw[0]), float(raw[1]), float(raw[2]))

    translate = _vec3(payload.get("translate"), (0.0, 0.0, 0.0))
    scale = _vec3(payload.get("scale"), (1.0, 1.0, 1.0))
    rotate = _vec3(payload.get("rotateDeg"), (0.0, 0.0, 0.0))
    mesh = decode_member(client, archive, member)
    transformed = apply_transform(mesh.positions, translate=translate, scale=scale, rotate_deg=rotate)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(client / archive) as handle:
        original = handle.read(member)
    rewritten = write_positions_into_dat(
        original,
        mesh.vertexOffset,
        transformed,
        stride=getattr(mesh, "vertexStride", 12) or 12,
    )
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


def cmd_effect_slot_fields(args: argparse.Namespace) -> dict[str, Any]:
    """Read decoded fields from the dormant Ice_Smoke02 particle slot (stock or export)."""
    jftse = _jftse_root()
    wind_assets = _load_wind_assets()
    member_name = str(getattr(args, "member", "") or "Ice_Smoke02.set")
    source = Path(args.particle_archive).expanduser() if getattr(args, "particle_archive", "") else None
    if source is None or not str(source):
        client = _client_root(jftse)
        source = client / "Res" / "Effect" / "Particle.res"
    if not source.is_file():
        return {"ok": False, "error": "PARTICLE_ARCHIVE_MISSING", "path": str(source)}
    with zipfile.ZipFile(source) as archive:
        if member_name not in archive.namelist():
            return {"ok": False, "error": "SLOT_MISSING", "member": member_name}
        plain = wind_assets.decrypt_set(archive.read(member_name))
    fields = _parse_fields(plain)
    return {
        "ok": True,
        "path": str(source),
        "member": member_name,
        "fields": {
            "TexturePath": fields.get("TexturePath", ""),
            "PQ_Quantity": fields.get("PQ_Quantity", ""),
            "Color": fields.get("Color", "").replace("\t", ""),
            "PM_Speed": fields.get("PM_Speed", ""),
            "PT_Life": fields.get("PT_Life", ""),
            "PS_Size": fields.get("PS_Size", ""),
            "SubTexSize": fields.get("SubTexSize", ""),
            "SubTexCount": fields.get("SubTexCount", ""),
            "SubPlayTime": fields.get("SubPlayTime", ""),
            "SubPlayBack": fields.get("SubPlayBack", ""),
            "SRCBlend": fields.get("SRCBlend", ""),
            "DESTBlend": fields.get("DESTBlend", ""),
        },
    }


def cmd_playtest_status(args: argparse.Namespace) -> dict[str, Any]:
    local = Path(os.environ.get("JFTSE_LOCAL_CLIENT", "")).expanduser()
    particle = local / "Res" / "Effect" / "Particle.res"
    export_path = Path(args.export_archive).expanduser() if getattr(args, "export_archive", "") else None
    plan = (
        [
            {
                "source": str(export_path),
                "destRelative": "Res/Effect/Particle.res",
            }
        ]
        if export_path
        else []
    )
    return {
        **run_local_preflight(local, plan),
        "installPresent": particle.is_file(),
        "particlePath": str(particle),
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

    p_item_mesh = sub.add_parser("item-mesh-resolve")
    p_item_mesh.add_argument("--mesh-index", required=True)
    p_item_mesh.add_argument("--char", default="NIKI")
    p_item_mesh.add_argument("--meta-only", action="store_true")

    p_stage_set = sub.add_parser("stage-set-decrypt")
    p_stage_set.add_argument("--member", default="1_Emerald_Beach.set")

    p_stage_scene = sub.add_parser("stage-scene")
    p_stage_scene.add_argument("--member", default="1_Emerald_Beach.set")
    p_stage_scene.add_argument("--list-all", action="store_true")

    sub.add_parser("map-catalog")

    p_ftm = sub.add_parser("ftm-parse")
    p_ftm.add_argument("--archive", default="")
    p_ftm.add_argument("--member", required=True)

    p_ftm_export = sub.add_parser("ftm-export")
    p_ftm_export.add_argument("--archive", required=True)
    p_ftm_export.add_argument("--member", required=True)
    p_ftm_export.add_argument("--out-dir", required=True)
    p_ftm_export.add_argument("--patches", default="[]")

    p_ani = sub.add_parser("ani-parse")
    p_ani.add_argument("--archive", required=True)
    p_ani.add_argument("--member", required=True)
    p_ani.add_argument("--max-frames", type=int, default=8)
    p_ani.add_argument("--clip-index", type=int, default=0)
    p_ani.add_argument("--channel", default="A")
    p_ani.add_argument(
        "--motion",
        default="",
        help="Motion name from name table (e.g. RunForward.ani); overrides --clip-index",
    )
    p_ani.add_argument(
        "--char",
        default="",
        help="Character token for skeleton bone-name labels (optional)",
    )

    p_bone = sub.add_parser("bone-attach")
    p_bone.add_argument("--char", default="NIKI")
    p_bone.add_argument("--attach-bone", default="Bone_Racket")

    p_skin = sub.add_parser("skin-parse")
    p_skin.add_argument("--char", default="NIKI")
    p_skin.add_argument("--include-vertices", action="store_true")
    p_skin.add_argument("--max-vertices", type=int, default=2000)

    p_mesh_meta = sub.add_parser("mesh-meta")
    p_mesh_meta.add_argument("--archive", required=True)
    p_mesh_meta.add_argument("--member", required=True)

    p_mesh_export = sub.add_parser("mesh-export")
    p_mesh_export.add_argument("--archive", required=True)
    p_mesh_export.add_argument("--member", required=True)
    p_mesh_export.add_argument("--out-dir", required=True)

    p_mesh_transform = sub.add_parser("mesh-transform")
    p_mesh_transform.add_argument("--payload", required=True)
    p_mesh_transform.add_argument("--out-dir", required=True)

    p_mesh_texture = sub.add_parser("mesh-texture")
    p_mesh_texture.add_argument("--mesh-member", default="")
    p_mesh_texture.add_argument("--archive", default="")
    p_mesh_texture.add_argument("--member", default="")
    p_mesh_texture.add_argument("--out-dir", required=True)

    p_items = sub.add_parser("list-items")
    p_items.add_argument("--part", default="")
    p_items.add_argument("--limit", type=int, default=50)

    p_slot = sub.add_parser("effect-slot-fields")
    p_slot.add_argument("--particle-archive", default="")
    p_slot.add_argument("--member", default="Ice_Smoke02.set")

    p_play = sub.add_parser("playtest-status")
    p_play.add_argument("--export-archive", default="")

    p_tex = sub.add_parser("tex-encode")
    p_tex.add_argument("--dds", required=True)
    p_tex.add_argument("--out", required=True)

    p_tex_rt = sub.add_parser("tex-roundtrip")
    p_tex_rt.add_argument("--tex", required=True)

    p_equip = sub.add_parser("equipment-pack")
    p_equip.add_argument("--mesh-index", required=True)
    p_equip.add_argument("--char", default="NIKI")
    p_equip.add_argument("--out-dir", required=True)
    p_equip.add_argument("--dat", default="")
    p_equip.add_argument("--new-index", default="")
    p_equip.add_argument("--product-index", default="")
    p_equip.add_argument("--desc", default="")
    p_equip.add_argument("--part", default="Racket")
    p_equip.add_argument("--gold", default="0")

    p_cinst = sub.add_parser("client-install")
    p_cinst.add_argument("--target-client", required=True)
    p_cinst.add_argument("--payload", required=True)

    p_map_create = sub.add_parser("map-create")
    p_map_create.add_argument("--payload", required=True)
    p_map_create.add_argument("--out-file", required=True)

    p_stage_write = sub.add_parser("stage-set-write")
    p_stage_write.add_argument("--payload", required=True)
    p_stage_write.add_argument("--out-dir", required=True)
    p_stage_write.add_argument("--member", default="1_Emerald_Beach.set")

    p_ftm_author = sub.add_parser("ftm-author")
    p_ftm_author.add_argument("--payload", required=True)
    p_ftm_author.add_argument("--out-dir", required=True)
    p_ftm_author.add_argument("--archive", default="")
    p_ftm_author.add_argument("--member", default="")

    p_obj = sub.add_parser("mesh-obj-import")
    p_obj.add_argument("--archive", required=True)
    p_obj.add_argument("--member", required=True)
    p_obj.add_argument("--obj", required=True)
    p_obj.add_argument("--out", required=True)

    p_from_obj = sub.add_parser("mesh-from-obj")
    p_from_obj.add_argument("--obj", required=True)
    p_from_obj.add_argument("--out", required=True)

    p_eft = sub.add_parser("eft-parse")
    p_eft.add_argument("--path", required=True)

    p_ani_b = sub.add_parser("ani-section-b-status")
    p_ani_b.add_argument("--archive", default="Res/Player/PlayerA/AniA.res")
    p_ani_b.add_argument("--member", default="NikiAniA.ani")
    p_ani_b.add_argument("--char", default="NIKI")

    p_cp = sub.add_parser("content-pack-build")
    p_cp.add_argument("--payload", required=True)
    p_cp.add_argument("--out-dir", required=True)

    p_cpp = sub.add_parser("content-pack-playtest")
    p_cpp.add_argument("--target-client", required=True)
    p_cpp.add_argument("--payload", required=True)

    p_cpfull = sub.add_parser("content-pack-playtest-full")
    p_cpfull.add_argument("--target-client", required=True)
    p_cpfull.add_argument("--payload", required=True)

    p_sql = sub.add_parser("sql-apply")
    p_sql.add_argument("--payload", required=True)
    p_sql.add_argument("--path", default="")

    args = parser.parse_args()
    from author_cmds import make_handlers as make_author_handlers

    author_handlers = make_author_handlers(_jftse_root, _client_root, cmd_ftm_parse)
    handlers = {
        "health": cmd_health,
        "list-atlases": cmd_list_atlases,
        "atlas-preview": cmd_atlas_preview,
        "build-effect": cmd_build_effect,
        "list-maps": cmd_list_maps,
        "export-map-sql": cmd_export_map_sql,
        "map-studio-catalog": cmd_map_studio_catalog,
        "map-studio-validate": cmd_map_studio_validate,
        "map-studio-export-pack": cmd_map_studio_export_pack,
        "list-items": cmd_list_items,
        "mesh-list": cmd_mesh_list,
        "item-mesh-resolve": cmd_item_mesh_resolve,
        "stage-set-decrypt": cmd_stage_set_decrypt,
        "stage-scene": cmd_stage_scene,
        "map-catalog": cmd_map_catalog,
        "ftm-parse": cmd_ftm_parse,
        "ftm-export": cmd_ftm_export,
        "ani-parse": cmd_ani_parse,
        "bone-attach": cmd_bone_attach,
        "skin-parse": cmd_skin_parse,
        "mesh-meta": cmd_mesh_meta,
        "mesh-parse": cmd_mesh_parse,
        "mesh-export": cmd_mesh_export,
        "mesh-transform": cmd_mesh_transform,
        "mesh-texture": cmd_mesh_texture,
        "effect-slot-fields": cmd_effect_slot_fields,
        "playtest-status": cmd_playtest_status,
        **author_handlers,
    }
    result = handlers[args.command](args)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
