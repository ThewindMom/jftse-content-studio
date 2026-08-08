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
from ftm_codec import (
    add_scene_object,
    patch_scene_objects,
    remove_scene_object,
    serialize_ftm,
    set_blocked_tiles,
)
from local_install import InstallError, install_files
from map_author import build_create_map_sql, create_map_row, patch_relations_sql
from map_sql_export import parse_s_maps
from stage_set_author import write_stage_set
from tex_codec import dds_to_tex, tex_to_dds, write_tex_from_dds


def _jftse_and_client(bridge_jftse: Callable[[], Path], bridge_client: Callable[[Path], Path]):
    jftse = bridge_jftse()
    return jftse, bridge_client(jftse)


def make_handlers(
    jftse_fn: Callable[[], Path],
    client_fn: Callable[[Path], Path],
    parse_ftm_member: Callable[..., Any],
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
        jftse, client = _jftse_and_client(jftse_fn, client_fn)
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
        new_index = int(args.new_index) if args.new_index else list_catalog_max_index(
            client, args.char
        ) + 1
        catalog = patch_item_mesh_catalog(
            client,
            char=args.char,
            source_index=args.mesh_index,
            new_index=new_index,
            path=str(pack["path"]),
            desc=args.desc or f"Custom mesh {new_index}",
            out_dir=out_dir / "catalog",
        )
        sql = build_item_sql_pack(
            product_index=int(args.product_index or new_index),
            name=args.desc or f"Custom Item {new_index}",
            mesh=new_index,
            part=args.part or "Racket",
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
                {
                    "source": pack["archive"],
                    "destRelative": pack["destRelative"],
                },
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
        seed_text = (jftse / "scripts" / "sql" / "maps.sql").read_text(encoding="utf-8")
        existing = parse_s_maps(seed_text)
        draft = dict(payload.get("draft") or payload)
        row = create_map_row(existing, draft)
        scenario_ids = [int(x) for x in payload.get("scenarioIds", [])]
        guardians = list(payload.get("guardians") or [])
        stage = payload.get("stageScript") or draft.get("stageScript")
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
        jftse, client = _jftse_and_client(jftse_fn, client_fn)
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
        jftse, client = _jftse_and_client(jftse_fn, client_fn)
        del jftse  # reserved for future jftse-relative maps
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        archive = str(payload.get("archive") or args.archive)
        member = str(payload.get("member") or args.member)
        from ftm_codec import FtmParseError, load_ftm_from_res, parse_ftm_bytes

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
        from mesh_obj_import import import_obj_into_dat

        jftse, client = _jftse_and_client(jftse_fn, client_fn)
        del jftse
        out = Path(args.out)
        return import_obj_into_dat(
            client,
            args.archive,
            args.member,
            Path(args.obj),
            out,
        )

    return {
        "tex-encode": cmd_tex_encode,
        "tex-roundtrip": cmd_tex_roundtrip,
        "equipment-pack": cmd_equipment_pack,
        "client-install": cmd_client_install,
        "map-create": cmd_map_create,
        "stage-set-write": cmd_stage_set_write,
        "ftm-author": cmd_ftm_author,
        "mesh-obj-import": cmd_mesh_obj_import,
    }
