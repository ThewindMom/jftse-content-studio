"""Unified designer content packs: equipment + map SQL + stage + FTM → install plan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from equipment_author import (
    build_item_sql_pack,
    clone_equipment_mesh,
    list_catalog_max_index,
    patch_item_mesh_catalog,
)
from ftm_codec import (
    FtmParseError,
    add_scene_object,
    load_ftm_from_res,
    parse_ftm_bytes,
    patch_scene_objects,
    serialize_ftm,
    set_blocked_tiles,
)
from map_author import build_create_map_sql, create_map_row, write_aggregate_sql
from map_sql_export import parse_s_maps
from stage_set_author import write_stage_set


def _safe_client_relative(path: str) -> str:
    normalized = path.replace("\\", "/")
    if (
        not path
        or "\\" in path
        or Path(path).is_absolute()
        or (len(path) >= 3 and path[0].isalpha() and path[1:3] in {":/", ":\\"})
        or ".." in normalized.split("/")
    ):
        raise ValueError("PATH_CLIENT_RELATIVE_INVALID")
    return path


def _safe_member_name(member: str) -> str:
    if not member or member in {".", ".."} or "/" in member or "\\" in member:
        raise ValueError("PATH_MEMBER_INVALID")
    return member


def _write_ftm_bundle(
    client: Path,
    *,
    archive: str,
    member: str,
    out_dir: Path,
    patches: list[dict[str, Any]] | None = None,
    add: list[dict[str, Any]] | None = None,
    blocked_tiles: list[dict[str, int]] | None = None,
) -> dict[str, Any]:
    archive = _safe_client_relative(archive)
    member = _safe_member_name(member)
    ftm = load_ftm_from_res(client, archive, member)
    if patches:
        ftm = patch_scene_objects(ftm, patches)
    for placement in add or []:
        ftm = add_scene_object(ftm, placement)
    if blocked_tiles is not None:
        ftm = set_blocked_tiles(ftm, blocked_tiles)
    raw = serialize_ftm(ftm)
    verify = parse_ftm_bytes(raw)
    if len(verify.sceneObjects) != len(ftm.sceneObjects):
        raise FtmParseError("FTM_ROUNDTRIP_MISMATCH")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_ftm = out_dir / Path(member).name
    out_ftm.write_bytes(raw)
    stock = client / archive
    out_res = out_dir / Path(archive).name
    import zipfile

    with zipfile.ZipFile(stock, "r") as zin:
        with zipfile.ZipFile(out_res, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                blob = raw if info.filename == member else zin.read(info.filename)
                zout.writestr(info, blob)
    return {
        "path": str(out_ftm),
        "archive": str(out_res),
        "destRelative": archive,
        "sceneObjectCount": len(ftm.sceneObjects),
        "blockedTileCount": len(ftm.blockedTiles),
    }


def build_content_pack(
    client_root: Path,
    jftse_root: Path,
    out_dir: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Build a multi-asset pack and install plan (never writes client itself)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    install_plan: list[dict[str, str]] = []
    parts: dict[str, Any] = {}
    name = str(payload.get("name") or f"pack-{int(__import__('time').time())}")

    equip = payload.get("equipment")
    equipment_effect: int | None = None
    if isinstance(equip, dict) and equip.get("meshIndex") is not None:
        e_out = out_dir / "equipment"
        pack = clone_equipment_mesh(
            client_root,
            mesh_index=equip["meshIndex"],
            char=str(equip.get("char") or "NIKI"),
            out_dir=e_out / "mesh",
        )
        if not pack.get("ok"):
            return pack
        new_index = int(
            equip.get("newIndex")
            or list_catalog_max_index(client_root, str(equip.get("char") or "NIKI")) + 1
        )
        effect = int(equip.get("effect", 0))
        equipment_effect = effect
        if effect not in {0, 15}:
            raise ValueError("EQUIPMENT_EFFECT_UNSUPPORTED")
        source_item_index = int(equip.get("sourceItemIndex", 10728))
        catalog = patch_item_mesh_catalog(
            client_root,
            char=str(equip.get("char") or "NIKI"),
            source_index=equip["meshIndex"],
            new_index=new_index,
            path=str(pack["path"]),
            desc=str(equip.get("desc") or f"Custom {new_index}"),
            out_dir=e_out / "catalog",
            source_item_index=source_item_index,
            part=str(equip.get("part") or "Racket"),
            effect=effect,
        )
        sql = build_item_sql_pack(
            product_index=int(equip.get("productIndex") or new_index),
            name=str(equip.get("desc") or f"Custom Item {new_index}"),
            mesh=new_index,
            part=str(equip.get("part") or "Racket"),
            effect=effect,
            gold=int(equip.get("gold") or 0),
        )
        sql_path = e_out / "item-pack.sql"
        sql_path.write_text(sql, encoding="utf-8")
        install_plan.extend(
            [
                {"source": pack["archive"], "destRelative": pack["destRelative"]},
                {
                    "source": catalog["itemArchive"],
                    "destRelative": catalog["destRelative"],
                },
            ]
        )
        parts["equipment"] = {
            "mesh": pack,
            "catalog": catalog,
            "sql": str(sql_path),
            "newIndex": new_index,
            "sourceItemIndex": source_item_index,
            "effect": effect,
        }

    map_payload = payload.get("map")
    if isinstance(map_payload, dict):
        seed = (jftse_root / "scripts" / "sql" / "maps.sql").read_text(encoding="utf-8")
        existing = parse_s_maps(seed)
        draft = dict(map_payload.get("draft") or map_payload)
        row = create_map_row(existing, draft)
        scenario_ids = [int(x) for x in map_payload.get("scenarioIds", [])]
        sql = build_create_map_sql(
            row,
            scenario_ids=scenario_ids,
            guardians=list(map_payload.get("guardians") or []),
            stage_script=str(map_payload.get("stageScript") or "") or None,
        )
        sql_path = out_dir / "map" / "map-create.sql"
        sql_path.parent.mkdir(parents=True, exist_ok=True)
        sql_path.write_text(sql, encoding="utf-8")
        parts["map"] = {"sql": str(sql_path), "map": row.as_catalog_dict()}

    stage = payload.get("stage")
    if isinstance(stage, dict) and stage.get("member"):
        s_out = out_dir / "stage"
        fields = {str(k): str(v) for k, v in dict(stage.get("fields") or {}).items()}
        written = write_stage_set(
            client_root,
            str(stage["member"]),
            out_dir=s_out,
            fields=fields or None,
            append_objects=list(stage.get("appendObjects") or []),
            plaintext_override=stage.get("plaintext"),
        )
        install_plan.append(
            {
                "source": written["infoArchive"],
                "destRelative": written["destRelative"],
            }
        )
        parts["stage"] = written

    ftm_payload = payload.get("ftm")
    if isinstance(ftm_payload, dict) and ftm_payload.get("archive") and ftm_payload.get("member"):
        f_out = out_dir / "ftm"
        try:
            ftm_part = _write_ftm_bundle(
                client_root,
                archive=str(ftm_payload["archive"]),
                member=str(ftm_payload["member"]),
                out_dir=f_out,
                patches=list(ftm_payload.get("patches") or []) or None,
                add=list(ftm_payload.get("add") or []) or None,
                blocked_tiles=list(ftm_payload["blockedTiles"])
                if "blockedTiles" in ftm_payload
                else None,
            )
        except FtmParseError as exc:
            return {"ok": False, "error": "FTM_PACK_FAILED", "detail": str(exc)}
        install_plan.append(
            {
                "source": ftm_part["archive"],
                "destRelative": ftm_part["destRelative"],
            }
        )
        parts["ftm"] = ftm_part

    # Optional proven Effect 15 artifacts are passed through independently.
    runtime_archives = (
        ("particle", payload.get("particleArchive"), "Res/Effect/Particle.res"),
        ("effect", payload.get("effectArchive"), "Res/Script/ETC.res"),
    )
    for key, archive, destination in runtime_archives:
        if (
            equipment_effect != 0
            and isinstance(archive, str)
            and archive
            and Path(archive).is_file()
        ):
            if any(entry["destRelative"] == destination for entry in install_plan):
                raise ValueError("INSTALL_DESTINATION_DUPLICATE")
            install_plan.append({"source": archive, "destRelative": destination})
            parts[key] = archive

    sql_parts = [str(parts[part]["sql"]) for part in ("equipment", "map")
                 if isinstance(parts.get(part), dict) and parts[part].get("sql")]
    aggregate_sql_path = write_aggregate_sql(out_dir, sql_parts)

    manifest = {
        "ok": True,
        "name": name,
        "outDir": str(out_dir),
        "parts": parts,
        "sqlPath": aggregate_sql_path,
        "sqlParts": sql_parts,
        "installPlan": install_plan,
        "fileCount": len(install_plan),
        "playtest": {
            "requiresLocalClient": True,
            "checks": [
                "installPlan non-empty files exist after client-install",
                "optional: apply map SQL to JFTSE DB outside studio",
            ],
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
