"""Bridge command handlers for equipment + map authoring (keeps studio_bridge thinner)."""

from __future__ import annotations

import json
import zipfile
from argparse import Namespace
from pathlib import Path
from typing import Any, Callable

from equipment_author import (
    build_item_sql_pack,
    clone_equipment_mesh,
    list_catalog_max_index,
    patch_item_mesh_catalog,
)
from content_pack import build_content_pack
from playtest_preflight import run_local_preflight
from sql_apply import apply_sql_file
from ftm_codec import (
    FtmParseError,
    add_scene_object,
    load_ftm_from_res,
    paint_tile_layer,
    parse_ftm_bytes,
    patch_scene_objects,
    remove_scene_object,
    serialize_ftm,
    set_blocked_tiles,
)
from local_install import InstallError, install_files
from map_author import build_create_map_sql, create_map_row, patch_relations_sql
from map_sql_export import parse_s_maps
from eft_codec import load_eft_from_path
from mesh_obj_import import import_obj_into_dat
from mesh_topology import create_mesh_from_obj
from stage_set_author import write_stage_set
from stage_validation import validate_stage_script
from tex_codec import dds_to_tex, tex_to_dds, write_tex_from_dds


def _jftse_and_client(
    bridge_jftse: Callable[[], Path],
    bridge_client: Callable[[Path], Path],
) -> tuple[Path, Path]:
    jftse = bridge_jftse()
    return jftse, bridge_client(jftse)


def make_handlers(
    jftse_fn: Callable[[], Path],
    client_fn: Callable[[Path], Path],
    _parse_ftm_member: Callable[..., Any],
) -> dict[str, Callable[[Namespace], dict[str, Any]]]:
    def cmd_tex_encode(args: Namespace) -> dict[str, Any]:
        dds = Path(args.dds).expanduser().resolve()
        out = Path(args.out).expanduser().resolve()
        if not dds.is_file():
            return {"ok": False, "error": "DDS_MISSING"}
        return {**write_tex_from_dds(dds, out), "ok": True}

    def cmd_tex_roundtrip(args: Namespace) -> dict[str, Any]:
        tex = Path(args.tex).read_bytes()
        dds = tex_to_dds(tex)
        back = dds_to_tex(dds)
        return {
            "ok": True,
            "inputBytes": len(tex),
            "ddsMagic": dds[:4].decode("latin1", errors="replace"),
            "roundtripEqual": back == tex,
        }

    def cmd_equipment_pack(args: Namespace) -> dict[str, Any]:
        _jftse, client = _jftse_and_client(jftse_fn, client_fn)
        out_dir = Path(args.out_dir).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        dat_override = Path(args.dat) if args.dat else None
        pack = clone_equipment_mesh(
            client,
            mesh_index=args.mesh_index,
            char=args.char,
            out_dir=out_dir / "mesh",
            dat_override=dat_override if dat_override and dat_override.is_file() else None,
        )
        if not pack.get("ok"):
            return pack
        new_index = (
            int(args.new_index)
            if args.new_index
            else list_catalog_max_index(client, args.char) + 1
        )
        catalog = patch_item_mesh_catalog(
            client,
            char=args.char,
            source_index=args.mesh_index,
            new_index=new_index,
            path=str(pack["path"]),
            desc=args.desc or f"Custom mesh {new_index}",
            out_dir=out_dir / "catalog",
            source_item_index=int(args.source_item_index),
            part=args.part or "Racket",
            effect=int(args.effect),
        )
        sql = build_item_sql_pack(
            product_index=int(args.product_index or new_index),
            name=args.desc or f"Custom Item {new_index}",
            mesh=new_index,
            part=args.part or "Racket",
            effect=int(args.effect),
            gold=int(args.gold or 0),
        )
        sql_path = out_dir / "item-pack.sql"
        sql_path.write_text(sql, encoding="utf-8")
        manifest = {
            "ok": True,
            "outDir": str(out_dir),
            "mesh": pack,
            "catalog": catalog,
            "sql": str(sql_path),
            "newIndex": new_index,
            "installPlan": [
                {"source": pack["archive"], "destRelative": pack["destRelative"]},
                {
                    "source": catalog["itemArchive"],
                    "destRelative": catalog["destRelative"],
                },
            ],
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        return manifest

    def cmd_client_install(args: Namespace) -> dict[str, Any]:
        jftse = jftse_fn()
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        files = payload.get("files") or []
        try:
            return install_files(
                Path(args.target_client),
                files,
                jftse=jftse,
            )
        except InstallError as exc:
            return {"ok": False, "error": exc.code}

    def cmd_map_create(args: Namespace) -> dict[str, Any]:
        jftse = jftse_fn()
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        seed_text = (jftse / "scripts" / "sql" / "maps.sql").read_text(
            encoding="utf-8"
        )
        existing = parse_s_maps(seed_text)
        draft = dict(payload.get("draft") or payload)
        stage = payload.get("stageScript") or draft.get("stageScript")
        validation = validate_stage_script(
            client_fn(jftse),
            str(stage or ""),
        )
        if not bool(validation["valid"]):
            return {
                "ok": False,
                "error": "STAGE_VALIDATION_REQUIRED",
                "validation": validation,
            }
        row = create_map_row(existing, draft)
        scenario_ids = [int(x) for x in payload.get("scenarioIds", [])]
        guardians = list(payload.get("guardians") or [])
        sql = build_create_map_sql(
            row,
            scenario_ids=scenario_ids,
            guardians=guardians,
            stage_script=str(stage) if stage else None,
            include_scenarios=bool(payload.get("includeScenarios", True)),
            include_guardians=bool(payload.get("includeGuardians", True)),
        )
        rel = patch_relations_sql(
            row.id,
            add_scenario_ids=scenario_ids,
            add_guardians=guardians,
        )
        out = Path(args.out_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sql + "\n" + rel, encoding="utf-8")
        return {
            "ok": True,
            "path": str(out),
            "map": row.as_catalog_dict(),
            "scenarioIds": scenario_ids,
            "guardianCount": len(guardians),
        }

    def cmd_stage_set_write(args: Namespace) -> dict[str, Any]:
        _jftse, client = _jftse_and_client(jftse_fn, client_fn)
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        fields = {str(k): str(v) for k, v in dict(payload.get("fields") or {}).items()}
        return write_stage_set(
            client,
            str(payload.get("member") or args.member),
            out_dir=Path(args.out_dir),
            fields=fields or None,
            append_objects=list(payload.get("appendObjects") or []),
            plaintext_override=payload.get("plaintext"),
        )

    def cmd_ftm_author(args: Namespace) -> dict[str, Any]:
        _jftse, client = _jftse_and_client(jftse_fn, client_fn)
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        archive = str(payload.get("archive") or args.archive)
        member = str(payload.get("member") or args.member)
        try:
            ftm = load_ftm_from_res(client, archive, member)
            for patch in payload.get("patches") or []:
                ftm = patch_scene_objects(ftm, [patch])
            removes = sorted(
                {
                    int(i)
                    for i in list(payload.get("remove") or [])
                    + list(payload.get("removeIndices") or [])
                },
                reverse=True,
            )
            for idx in removes:
                ftm = remove_scene_object(ftm, idx)
            for add in payload.get("add") or []:
                ftm = add_scene_object(ftm, add)
            if "blockedTiles" in payload:
                ftm = set_blocked_tiles(ftm, list(payload["blockedTiles"]))
            tile_paint = payload.get("tilePaint")
            if isinstance(tile_paint, dict) and tile_paint.get("cells"):
                ftm = paint_tile_layer(
                    ftm,
                    layer_index=int(tile_paint.get("layerIndex", 0)),
                    cells=list(tile_paint["cells"]),
                )
            raw = serialize_ftm(ftm)
            verify = parse_ftm_bytes(raw)
            if len(verify.sceneObjects) != len(ftm.sceneObjects):
                return {"ok": False, "error": "FTM_ROUNDTRIP_MISMATCH"}
        except FtmParseError as exc:
            return {"ok": False, "error": "FTM_AUTHOR_FAILED", "detail": str(exc)}
        except Exception as exc:  # noqa: BLE001 — bridge boundary
            return {"ok": False, "error": "FTM_AUTHOR_FAILED", "detail": str(exc)}

        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_ftm = out_dir / Path(member).name
        out_ftm.write_bytes(raw)
        stock = client / archive
        out_res = out_dir / Path(archive).name
        with zipfile.ZipFile(stock, "r") as zin:
            with zipfile.ZipFile(out_res, "w", compression=zipfile.ZIP_DEFLATED) as zout:
                for info in zin.infolist():
                    blob = raw if info.filename == member else zin.read(info.filename)
                    zout.writestr(info, blob)
        return {
            "ok": True,
            "path": str(out_ftm),
            "archive": str(out_res),
            "destRelative": archive,
            "sceneObjectCount": len(ftm.sceneObjects),
            "blockedTileCount": len(ftm.blockedTiles),
        }

    def cmd_mesh_obj_import(args: Namespace) -> dict[str, Any]:
        _jftse, client = _jftse_and_client(jftse_fn, client_fn)
        return import_obj_into_dat(
            client,
            str(args.archive),
            str(args.member),
            Path(args.obj),
            Path(args.out),
        )

    def cmd_mesh_from_obj(args: Namespace) -> dict[str, Any]:
        return create_mesh_from_obj(Path(args.obj), Path(args.out))

    def cmd_eft_parse(args: Namespace) -> dict[str, Any]:
        _jftse, client = _jftse_and_client(jftse_fn, client_fn)
        return load_eft_from_path(client, str(args.path))

    def cmd_content_pack_build(args: Namespace) -> dict[str, Any]:
        jftse, client = _jftse_and_client(jftse_fn, client_fn)
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        return build_content_pack(
            client,
            jftse,
            Path(args.out_dir),
            payload,
        )

    def _content_pack_preflight(args: Namespace) -> dict[str, Any]:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        target = Path(args.target_client).expanduser()
        plan = [
            {
                "source": str(entry.get("source", "")),
                "destRelative": str(entry.get("destRelative", "")),
            }
            for entry in list(payload.get("installPlan") or [])
            if isinstance(entry, dict)
        ]
        receipt_raw = payload.get("sqlApplyReceipt")
        receipt = dict(receipt_raw) if isinstance(receipt_raw, dict) else None
        return run_local_preflight(
            target,
            plan,
            sql_path=str(payload.get("sqlPath") or "") or None,
            sql_apply_receipt=receipt,
        )

    def cmd_content_pack_playtest(args: Namespace) -> dict[str, Any]:
        return _content_pack_preflight(args)

    def cmd_content_pack_playtest_full(args: Namespace) -> dict[str, Any]:
        return _content_pack_preflight(args)

    def cmd_sql_apply(args: Namespace) -> dict[str, Any]:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        return apply_sql_file(
            Path(str(payload.get("path") or args.path)),
            dry_run=bool(payload.get("dryRun", True)),
        )

    def cmd_ani_section_b_status(args: Namespace) -> dict[str, Any]:
        """Expose honest section-B / float4 probe status for the studio UI."""
        import struct

        client = client_fn(jftse_fn())
        archive = str(args.archive or "Res/Player/PlayerA/AniA.res")
        member = str(args.member or "NikiAniA.ani")
        char = str(args.char or "NIKI")
        payload: dict[str, Any] = {
            "ok": True,
            "archive": archive,
            "member": member,
            "char": char,
            "onDiskDenseFloat4": {
                "confident": False,
                "unitRatioCap": 0.62,
                "note": (
                    "Exhaustive A/B/C/tail probes never reached ≥0.9 unit float4 on Niki-class ANI. "
                    "Client runtime uses float4; on-disk rotation channel remains unrecovered."
                ),
            },
            "sectionB": {
                "encoding": "unknown",
                "probes": [
                    "float3",
                    "float4",
                    "s16-quat",
                    "f16",
                    "zlib-raw",
                    "sparse-keyframe",
                    "delta",
                ],
                "viable": False,
                "note": "Section B size matches C with A−B=1290 name-table span; bitstream packing unknown.",
            },
            "productionDrive": {
                "driveMode": "quat",
                "rotationSource": "hierarchical-derived",
                "fallback": "hierarchical-fk",
                "note": "Studio derives unit local quats from float3 positions + skeleton when char is set.",
            },
        }
        try:
            with zipfile.ZipFile(client / archive) as zin:
                raw = zin.read(member)
            if len(raw) >= 12:
                n0, n1, n2 = struct.unpack_from("<III", raw, 0)
                payload["streamHeader"] = {
                    "n0": n0,
                    "n1": n1,
                    "n2": n2,
                    "fileSize": len(raw),
                    "n0Times4Plus12": n0 * 4 + 12,
                }
        except Exception as exc:  # noqa: BLE001 — boundary
            payload["streamHeaderError"] = str(exc)
        return payload

    return {
        "tex-encode": cmd_tex_encode,
        "tex-roundtrip": cmd_tex_roundtrip,
        "equipment-pack": cmd_equipment_pack,
        "client-install": cmd_client_install,
        "map-create": cmd_map_create,
        "stage-set-write": cmd_stage_set_write,
        "ftm-author": cmd_ftm_author,
        "mesh-obj-import": cmd_mesh_obj_import,
        "mesh-from-obj": cmd_mesh_from_obj,
        "eft-parse": cmd_eft_parse,
        "ani-section-b-status": cmd_ani_section_b_status,
        "content-pack-build": cmd_content_pack_build,
        "content-pack-playtest": cmd_content_pack_playtest,
        "content-pack-playtest-full": cmd_content_pack_playtest_full,
        "sql-apply": cmd_sql_apply,
    }
