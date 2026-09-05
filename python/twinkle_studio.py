"""Private, read-only stock asset preparation and isolated Twinkle layout export."""

import hashlib
import csv
import io
import json
import math
import os
import re
import zipfile
from pathlib import Path

from client_crypto import decrypt_set_file, encrypt_set_file
from mesh_texture import tex_to_png_bytes
from twinkle_mesh import parse_static_decoration, parse_twinkle_static
from adu_pose import parse_bind_pose
from oktoberfest_models import prepare_originals, PREFIX, NAMES
from oktoberfest_native import native_resources, model_name, ATLAS

STAGE = "2_Twinkle_Town.set"
PROPS = ["P0_Barrel01_C01.dat", "P0_Log00_B.dat", "P0_Flower00a.dat",
         "P0_Flower00b.dat", "P0_Flower00c.dat", "P0_Flower01.dat",
         "P0_Flower03d.dat", "P0_Leaf00_00.dat"]
PROP_PREFIX = "Res/MapRes/DecoRes/Mesh00/"
SECTION = re.compile(r"(?=^\[[^\]]+\]\s*\r?$)", re.M)
FESTIVAL = {"FestivalHall": ("BlackSmith_Shop.dat", "Brewers’ pavilion"),
            "FestivalPretzel": ("Carriage00.dat", "Pretzel cart"),
            "FestivalHeart": ("Carriage00.dat", "Gingerbread cart"),
            "FestivalFood": ("Carriage00.dat", "Food cart")}
STOCK_PROPS = {"Object01": ["Jjijil00.dat"],
               "Object02": ["Carriage00.dat", "Chick00.dat", "Dc_Clock.dat", "RefereeOwl00.dat", "Soldier00.dat"],
               "Object03": ["Engineer00h.dat", "Pirate00.dat"],
               "Extra": ["BlackSmith_Shop.dat", "chest.dat", "Moai.dat"]}


def festival_root() -> Path | None:
    value = os.environ.get("JFTSE_FESTIVAL_RESOURCES")
    return Path(value) if value else None


def resource_path(client: Path, archive: str) -> Path:
    root = festival_root()
    if Path(archive).stem in FESTIVAL:
        if root is None:
            raise ValueError("Set JFTSE_FESTIVAL_RESOURCES to the private authored resource folder.")
        return root / Path(archive).name
    return client / archive


def catalog() -> list[tuple[str, str, str, bool, str]]:
    result = [("Res/Stage/Mesh02.res", "SV_Court.dat", "Court", True, "world"),
              ("Res/Stage/Mesh02.res", "SV_All.dat", "Town", True, "world")]
    result += [("Res/MapRes/DecoRes/Mesh00.res", n, n[:-4], False, "scenery") for n in PROPS]
    result += [(f"Res/StageObj/{a}.res", n, n[:-4], False, "stock") for a, names in STOCK_PROPS.items() for n in names]
    if festival_root():
        result += [(f"Res/StageObj/{a}.res", n, label, False, "festival") for a, (n, label) in FESTIVAL.items()]
    return result


def source_text(client: Path) -> str:
    with zipfile.ZipFile(client / "Res/Stage/Info.res") as archive:
        return decrypt_set_file(archive.read(STAGE)).decode("utf-8")


def fields(block: str) -> dict:
    return dict(re.findall(r'^([A-Za-z0-9_]+)\s*=\s*([^\r\n]*)', block, re.M))


def number(value: str) -> float:
    result = float(value.strip().rstrip("fF"))
    if not math.isfinite(result):
        raise ValueError("Nonfinite stage transform")
    return result


def initial_document(text: str, map_id: str = "twinkle") -> dict:
    objects = []
    for block in SECTION.split(text):
        if not block.startswith("[DecoObj]"):
            continue
        values = fields(block)
        file = values["File"].strip().strip('"')
        objects.append({
            "id": f"stock-{len(objects)}", "name": Path(file).stem,
            "file": file, "position": [number(v) for v in values["Position"].split(",")],
            "rotation": number(values.get("Rotation", "0")),
            "scale": number(values.get("Scale", "1")),
            "level": int(values.get("Level", "0")), "visible": True,
            "animation": int(values.get("AnimIndex", "-1")), "phase": number(values.get("AnimPos", "0")),
        })
    fingerprint = text.encode()
    if map_id == "oktoberfest":
        root = festival_root()
        if root is None:
            raise ValueError("Oktoberfest requires JFTSE_FESTIVAL_RESOURCES.")
        preset = (root / "festival-placements.tsv").read_bytes()
        fingerprint += preset
        for name in [*FESTIVAL, "Tex009", "Tex010"]:
            fingerprint += hashlib.sha256((root / f"{name}.res").read_bytes()).digest()
        objects = [o for o in objects if o["file"] != "Res/StageObj/Object02/Carriage00.dat"]
        for row in csv.DictReader(preset.decode().splitlines(), delimiter="\t"):
            objects.append({"id": f'festival-{row["id"]}', "name": row["id"].replace("-", " "),
                            "file": row["file"], "position": [number(row[k]) for k in ("x", "y", "z")],
                            "rotation": number(row["rotation"]), "scale": number(row["scale"]),
                            "animation": int(row["animation"]), "phase": number(row["phase"]),
                            "level": 1, "visible": True})
    elif map_id != "twinkle":
        raise ValueError("Unknown map design")
    return {"version": 1, "mapId": map_id, "name": "Oktoberfest" if map_id == "oktoberfest" else "Twinkle Town",
            "sourceHash": hashlib.sha256(fingerprint).hexdigest(),
            "objects": objects}


def prepare(client: Path, out: Path, map_id: str = "twinkle") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    document = initial_document(source_text(client), map_id)
    texture_index = {}
    for path in [*sorted((client / "Res/Stage").glob("Tex*.res")),
                 *sorted((client / "Res/MapRes/DecoRes").glob("Tex*.res")),
                 *sorted((client / "Res/StageObj").glob("Object*.res"))]:
        if map_id == "oktoberfest" and path.name in ("Tex009.res", "Tex010.res"):
            path = festival_root() / path.name
        if not path.exists():
            continue
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if member.lower().endswith(".tex"):
                    texture_index[member.lower()] = (path, member)
    converted = {}
    missing = set()

    def texture(stem: str, local: Path) -> str | None:
        key = f"{stem}.tex".lower()
        cache_key = (str(local), key)
        if cache_key in converted:
            return converted[cache_key]
        with zipfile.ZipFile(local) as archive:
            names = {n.lower(): n for n in archive.namelist()}
        source = (local, names[key]) if key in names else texture_index.get(key)
        if not source:
            missing.add(key)
            return None
        path, member = source
        with zipfile.ZipFile(path) as archive:
            raw = archive.read(member)
        filename = hashlib.sha256(raw).hexdigest()[:24] + ".png"
        if not (out / filename).exists():
            (out / filename).write_bytes(tex_to_png_bytes(raw))
        converted[cache_key] = filename
        return filename

    assets = []
    warnings = []
    for archive_path, member, label, fixed, category in catalog():
        path = resource_path(client, archive_path)
        if not path.exists():
            if fixed:
                raise ValueError(f"Stock resource missing: {archive_path}")
            warnings.append(f"Prop unavailable: {member}")
            continue
        with zipfile.ZipFile(path) as archive:
            raw = archive.read(member)
        parsed = parse_twinkle_static(raw) if fixed else (parse_static_decoration(raw) or parse_bind_pose(raw))
        if parsed is None:
            if fixed:
                raise ValueError(f"Unsupported static layout: {member}")
            warnings.append(f"{member}: unsupported layout; guide only, not a partial mesh")
            continue
        file = f"{archive_path[:-4]}/{member}"
        geometry = []
        for primitive in parsed["primitives"]:
            textures = primitive["textures"]
            geometry.append({
                "positions": [v for p in primitive["positions"] for v in p],
                "normals": [v for p in primitive["normals"] for v in p],
                "uvs": [v for p in primitive["uvs"] for v in p],
                "uv1": [v for p in primitive["uv1"] for v in p],
                "indices": primitive["indices"], "bounds": primitive["bounds"],
                "name": primitive["materialName"], "slot": primitive["materialSlot"],
                "albedo": texture(textures[0]["name"], path),
                "lightmap": texture(textures[1]["name"], path) if len(textures) > 1 else None,
            })
        encoded = json.dumps(geometry, separators=(",", ":"))
        filename = hashlib.sha256(encoded.encode()).hexdigest()[:24] + ".json"
        (out / filename).write_text(encoded)
        assets.append({"file": file, "name": label, "fixed": fixed, "geometry": filename,
                       "category": category, "pose": parsed.get("pose", "static"),
                       "vertices": sum(p["vertexCount"] for p in parsed["primitives"]),
                       "triangles": sum(p["indexCount"] // 3 for p in parsed["primitives"]),
                       "submeshes": len(geometry), "thumbnail": geometry[0]["albedo"]})
    assets.extend(prepare_originals(out))
    result = {"ok": True, "assets": assets, "document": document,
              "warnings": warnings + [f"Texture unavailable: {name}" for name in sorted(missing)]}
    (out / f"manifest-{map_id}.json").write_text(json.dumps(result))
    return {"ok": True}


def compile_layout(text: str, document: dict) -> str:
    original = initial_document(text)
    if document["sourceHash"] != initial_document(text, document.get("mapId", "twinkle"))["sourceHash"]:
        raise ValueError("Stock stage changed. Reopen Twinkle Town before exporting.")
    originals = {obj["id"]: obj for obj in original["objects"]}
    allowed = {obj["file"] for obj in originals.values()} | {f"{a[:-4]}/{n}" for a, n, _, fixed, _ in catalog() if not fixed}
    allowed |= {PREFIX + name + ".glb" for name in NAMES}
    if any(obj["file"] not in allowed for obj in document["objects"]):
        raise ValueError("Asset is not in the Twinkle catalog")
    desired = {obj["id"]: {**originals.get(obj["id"], {}), **obj} for obj in document["objects"]}
    if len(desired) != len(document["objects"]) or len(desired) > 500:
        raise ValueError("Duplicate IDs or too many placements")
    for identity, obj in desired.items():
        if identity.startswith("stock-") and identity not in originals:
            raise ValueError("Unknown stock placement")
        if len(obj["position"]) != 3 or not all(math.isfinite(v) for v in [*obj["position"], obj["rotation"], obj["scale"]]):
            raise ValueError("Invalid placement transform")
        animation, phase = obj.get("animation", -1), obj.get("phase", 0)
        if not isinstance(animation, int) or not -1 <= animation <= 127 or not math.isfinite(phase):
            raise ValueError("Invalid animation metadata")
        name = model_name(obj["file"])
        if name:
            obj.update(file=f"Res/StageObj/Oktoberfest/{name}.dat", animation=-1, phase=0)
    blocks = []
    stock_index = 0

    def replace(block: str, obj: dict) -> str:
        changes = {"File": f'"{obj["file"]}"', "Position": ", ".join(f"{v:.6g}" for v in obj["position"]),
                   "Rotation": f'{obj["rotation"]:.6g}', "Scale": f'{obj["scale"]:.6g}',
                   "Level": str(obj["level"])}
        for key, value in changes.items():
            block = re.sub(rf"^({key}\s*=\s*)[^\r\n]*", lambda m: m[1] + value, block, flags=re.M)
        if "animation" in obj:
            if obj["animation"] < 0:
                block = re.sub(r"^Anim(?:Index|Pos)\s*=[^\r\n]*\r?\n", "", block, flags=re.M)
            else:
                for key, value in {"AnimIndex": str(obj["animation"]), "AnimPos": f'{obj.get("phase", 0):.6g}'}.items():
                    pattern = rf"^({key}\s*=\s*)[^\r\n]*"
                    if re.search(pattern, block, re.M):
                        block = re.sub(pattern, lambda m: m[1] + value, block, flags=re.M)
                    else:
                        block += f"{key}= {value}\r\n"
        return block

    for block in SECTION.split(text):
        if not block.startswith("[DecoObj]"):
            blocks.append(block)
            continue
        identity = f"stock-{stock_index}"
        stock_index += 1
        obj = desired.get(identity)
        if obj is None or not obj["visible"]:
            continue
        if obj == originals[identity]:
            blocks.append(block)
        else:
            blocks.append(replace(block, obj))
    for obj in desired.values():
        if obj["id"] in originals or not obj["visible"]:
            continue
        blocks.append(replace('\r\n[DecoObj]\r\nFile= ""\r\nPosition= 0, 0, 0\r\nRotation= 0\r\n'
                              'Scale= 1\r\nShadow= true\r\nLevel= 0\r\n', obj))
    return "".join(blocks)


def export_layout(client: Path, document: dict, out: Path) -> dict:
    text = source_text(client)
    compiled = compile_layout(text, document)
    resources, texture = native_resources(client, document["objects"])
    if resources:
        if fields(text).get("Collision", "").strip('"') != "Res/Collision/ColMesh_TT.dat" or fields(text).get("Coll_Chat", "").strip('"') != "Res/Collision/ColMesh_TT_CR.dat":
            raise ValueError("Native collision export requires the original Twinkle collision references")
        path = (festival_root() if document.get("mapId") == "oktoberfest" else client / "Res/Stage") / "Tex010.res"
        packed = io.BytesIO()
        with zipfile.ZipFile(path) as source, zipfile.ZipFile(packed, "w", compression=zipfile.ZIP_DEFLATED) as dest:
            for entry in source.infolist():
                if entry.filename == ATLAS + ".tex":
                    raise ValueError("Source texture archive already contains an Oktoberfest atlas")
                dest.writestr(entry, source.read(entry))
            dest.writestr(ATLAS + ".tex", texture)
        resources["Res/Stage/Tex010.res"] = packed.getvalue()
    encrypted = encrypt_set_file(compiled.encode())
    out.mkdir(parents=True, exist_ok=True)
    info = out / "Info.res"
    with zipfile.ZipFile(client / "Res/Stage/Info.res") as source, zipfile.ZipFile(info, "w") as dest:
        for entry in source.infolist():
            dest.writestr(entry, encrypted if entry.filename == STAGE else source.read(entry))
    # Round-trip the actual archive, rather than trusting the draft or receipt.
    with zipfile.ZipFile(info) as archive:
        if decrypt_set_file(archive.read(STAGE)).decode() != compiled:
            raise ValueError("Stage export round-trip failed")
    (out / "layout.json").write_text(json.dumps(document, indent=2))
    (out / "2_Twinkle_Town.set.txt").write_text(compiled)
    bundle = out / "twinkle-layout.zip"
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(info, "Res/Stage/Info.res")
        archive.write(out / "layout.json", "layout.json")
        archive.write(out / "2_Twinkle_Town.set.txt", "2_Twinkle_Town.set.txt")
        used = {Path(obj["file"]).parent.name for obj in document["objects"] if obj["visible"]}
        for name in sorted(used & FESTIVAL.keys()):
            archive.write(resource_path(client, f"Res/StageObj/{name}.res"), f"Res/StageObj/{name}.res")
        if document.get("mapId") == "oktoberfest":
            for name in ("Tex009.res", "Tex010.res"):
                if f"Res/Stage/{name}" not in resources:
                    archive.write(festival_root() / name, f"Res/Stage/{name}")
        for name, data in resources.items():
            archive.writestr(name, data)
        if resources:
            archive.writestr("native-export.json", json.dumps({
                "format": "stock-template-static-adumesh", "nativeRuntimeVerified": False,
                "collision": "coarse solid proxies appended to stock match and chat meshes",
                "placements": [obj["id"] for obj in document["objects"] if obj["visible"] and model_name(obj["file"])],
                "texture": "A8R8G8B8 DDS/TEX, same-archive plus Stage/Tex010 registration candidate",
                "limits": "Loader lookup order, opaque node semantics, native shading and collision response need native verification.",
            }, indent=2))
        archive.writestr("README.txt", "PRIVATE TEST-CLIENT INSTALLATION\n"
                         "This design replaces Twinkle Town (map 2); it does not register a new game map.\n"
                         "1. Close the game. Make a separate pristine client copy and back up its Res folder.\n"
                         "2. Extract this ZIP to a staging folder. Review the Res files before copying.\n"
                         "3. Copy ONLY the ZIP's Res folder over the separate test client's Res folder.\n"
                         "   Include supplied StageObj/Festival*.res and Stage/Tex*.res files, not just Info.res.\n"
                         "4. Start that test copy with your existing JFTSE setup and select Twinkle Town.\n"
                         "5. Restore the backup to undo. Never install over the pristine or working client.\n"
                         "Requires the original stock DAT/TEX archives. Existing custom Info.res edits would be replaced.\n"
                         "Original models include DAT/TEX and coarse collision additions when present; review native-export.json.\n"
                         "Keep the supplied Collision.res and Tex010.res. Cameras remain stock.\n"
                         "Opaque node metadata is retained from a fingerprinted stock template, not independently understood.\n"
                         "Native material resolution, collision response, animation and gameplay are untested.\n")
    return {"ok": True, "placements": sum(obj["visible"] for obj in document["objects"])}
