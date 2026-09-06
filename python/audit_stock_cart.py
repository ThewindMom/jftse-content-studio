"""Inspect stock carriage/stall/shop fixtures without running the client.

Usage:
  PYTHONPATH=python python python/audit_stock_cart.py [CLIENT_ROOT] [OUTPUT]
Defaults:
  CLIENT_ROOT = ../JFTSE/.jftse-client-linux/client
  OUTPUT      = .amp/tmp/beer-cart/stock-study

Output is private decoded evidence, not native rendering. Keep it untracked.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from adu_pose import parse_bind_pose
from mesh_texture import tex_to_png_bytes
from twinkle_mesh import parse_static_decoration, parse_twinkle_static

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLIENT = ROOT.parent / "JFTSE" / ".jftse-client-linux" / "client"
DEFAULT_OUTPUT = ROOT / ".amp" / "tmp" / "beer-cart" / "stock-study"
BEER_PREVIEW = ROOT / "exports" / "blender-beer-cart" / "preview.png"

STALL_ALBEDOS = {
    "SV_Stall01a_B",
    "SV_Stall01b_B",
    "SV_Tent00_A",
    "SV_Tent01_A",
    "SV_BoxAll01_B",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def zip_member(archive: Path, member: str) -> tuple[bytes, dict]:
    with zipfile.ZipFile(archive) as packed:
        info = packed.getinfo(member)
        data = packed.read(member)
    return data, {
        "archive": str(archive),
        "archiveRel": None,
        "member": member,
        "crc32": f"{info.CRC:08x}",
        "zipBytes": info.file_size,
        "sha256": sha256_bytes(data),
    }


def decode_tex(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(tex_to_png_bytes(data))).convert("RGBA")


def uv_bounds(uvs: list[list[float]]) -> list[list[float]]:
    return [[min(p[i] for p in uvs), max(p[i] for p in uvs)] for i in (0, 1)]


def size_of(bounds: dict) -> list[float]:
    return [bounds["max"][i] - bounds["min"][i] for i in range(3)]


def centroid(positions: list[list[float]]) -> list[float]:
    n = len(positions)
    return [sum(p[i] for p in positions) / n for i in range(3)]


def finite_uvs(uvs: list[list[float]]) -> tuple[int, int]:
    in01 = sum(1 for u, v in uvs if 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0)
    return in01, len(uvs) - in01


def sample_texel_mean(image: Image.Image, uvs: list[list[float]], indices: list[int], cap: int = 4000) -> list[float] | None:
    if not uvs or not indices:
        return None
    pixels = image.load()
    width, height = image.size
    acc = [0.0, 0.0, 0.0]
    count = 0
    step = max(1, (len(indices) // 3) // max(1, cap // 3))
    for tri in range(0, len(indices) - 2, 3 * step):
        a, b, c = indices[tri], indices[tri + 1], indices[tri + 2]
        for w in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)):
            s = sum(w)
            u = (uvs[a][0] * w[0] + uvs[b][0] * w[1] + uvs[c][0] * w[2]) / s
            v = (uvs[a][1] * w[0] + uvs[b][1] * w[1] + uvs[c][1] * w[2]) / s
            if not (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
                continue
            x = min(width - 1, max(0, int(u * (width - 1))))
            y = min(height - 1, max(0, int((1.0 - v) * (height - 1))))
            px = pixels[x, y]
            acc[0] += px[0]
            acc[1] += px[1]
            acc[2] += px[2]
            count += 1
            if count >= cap:
                break
        if count >= cap:
            break
    if count == 0:
        return None
    return [round(c / count, 2) for c in acc]


def overlay_uv(image: Image.Image, primitives: list[dict], color=(255, 220, 40, 220)) -> Image.Image:
    overlay = image.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    width, height = overlay.size
    for primitive in primitives:
        uvs = primitive["uvs"]
        indices = primitive["indices"]
        for i in range(0, len(indices) - 2, 3):
            pts = []
            skip = False
            for idx in indices[i:i + 3]:
                u, v = uvs[idx]
                if not (-0.05 <= u <= 1.05 and -0.05 <= v <= 1.05):
                    skip = True
                    break
                pts.append((u * (width - 1), (1.0 - v) * (height - 1)))
            if skip or len(pts) < 3:
                continue
            draw.line(pts + [pts[0]], fill=color, width=1)
    return overlay


def primitive_record(primitive: dict, *, textures: dict[str, Image.Image] | None = None) -> dict:
    channels = [
        {
            "name": texture["name"],
            "uvSet": texture.get("uvSet"),
            "offset": texture.get("offset"),
            "texCandidate": texture.get("texCandidate", texture["name"] + ".tex"),
        }
        for texture in primitive.get("textures", [])
    ]
    albedo = channels[0]["name"] if channels else None
    mean = None
    if textures and albedo and albedo in textures:
        mean = sample_texel_mean(textures[albedo], primitive["uvs"], primitive["indices"])
    in01, outside = finite_uvs(primitive["uvs"])
    record = {
        "material": primitive["materialName"],
        "materialSlot": primitive.get("materialSlot"),
        "materialChild": primitive.get("materialChild"),
        "vertices": primitive["vertexCount"],
        "triangles": primitive["indexCount"] // 3,
        "vertexStride": primitive.get("vertexStride"),
        "sourcePrimitiveCount": primitive.get("sourcePrimitiveCount"),
        "lightmapped": bool(primitive.get("uv1")),
        "bonePalette": primitive.get("bonePalette", []),
        "bounds": primitive["bounds"],
        "size": size_of(primitive["bounds"]),
        "centroid": [round(v, 5) for v in centroid(primitive["positions"])],
        "uvBounds": uv_bounds(primitive["uvs"]),
        "uvInUnitSquare": in01,
        "uvOutsideUnitSquare": outside,
        "textureChannels": channels,
        "sampledAlbedoMeanRGB": mean,
    }
    if primitive.get("uv1"):
        record["uv1Bounds"] = uv_bounds(primitive["uv1"])
    return record


def load_named_textures(client: Path, specs: list[tuple[str, str]]) -> tuple[list[dict], dict[str, Image.Image]]:
    report = []
    images: dict[str, Image.Image] = {}
    for rel, member in specs:
        archive = client / rel
        data, meta = zip_member(archive, member)
        image = decode_tex(data)
        stem = Path(member).stem
        meta["archiveRel"] = rel
        meta["archiveSha256"] = sha256_file(archive)
        meta["size"] = list(image.size)
        meta["mode"] = image.mode
        meta["decodedPng"] = stem + ".png"
        report.append(meta)
        images[stem] = image
    return report, images


def save_images(output: Path, images: dict[str, Image.Image]) -> None:
    for name, image in images.items():
        image.save(output / f"{name}.png")


def beer_cart_authored_dimensions() -> dict:
    """Constants copied from python/blender_beer_cart.py; not a Blender evaluation."""
    return {
        "source": "python/blender_beer_cart.py authored numbers, not a native DAT",
        "floorSize": [2.28, 1.22, 0.14],
        "floorCenterZ": 0.68,
        "wheelWoodRadius": 0.52,
        "wheelIronRadius": 0.62,
        "wheelHubZ": 0.56,
        "canopyX": [-1.28, 1.28],
        "canopyY": [-0.78, 0.78],
        "canopyZ": [2.78, 3.24],
        "towTipX": -2.22,
        "approxOverall": {
            "x": 4.5,
            "y": 1.72,
            "z": 3.3,
            "note": "Blender object-space meters-like units; Y depth, Z up",
        },
        "uvMode": "planar projection from vertex axes, generated 256 TGA grain/stripes",
        "construction": "chamfer boxes, torus rims, 8 spoke beams, striped canopy mesh",
    }


def sheet_tile(draw, sheet, image, x, y, label, tile=300, pad=10):
    thumb = image.convert("RGB").copy()
    thumb.thumbnail((tile - 16, tile - 36))
    ox = x + pad + (tile - 16 - thumb.size[0]) // 2
    oy = y + 28
    sheet.paste(thumb, (ox, oy))
    draw.rectangle((x + 4, y + 4, x + tile - 4, y + tile - 4), outline=(90, 96, 102))
    draw.text((x + 10, y + 8), label, fill=(240, 240, 240))


def build_sheet(output: Path, images: dict[str, Image.Image], overlays: dict[str, Image.Image], beer: Image.Image | None) -> None:
    tiles = [
        ("Carriage00a albedo", images.get("Carriage00a")),
        ("Carriage00b albedo", images.get("Carriage00b")),
        ("Carriage00c albedo", images.get("Carriage00c")),
        ("Doiggi00 animal", images.get("Doiggi00")),
        ("Carriage00a UV", overlays.get("Carriage00a")),
        ("Carriage00b UV", overlays.get("Carriage00b")),
        ("Carriage00c UV", overlays.get("Carriage00c")),
        ("SV_Carriage00a_B", images.get("SV_Carriage00a_B")),
        ("SV_Stall01a_B timber", images.get("SV_Stall01a_B")),
        ("SV_Stall01b_B", images.get("SV_Stall01b_B")),
        ("SV_Tent00_A canvas", images.get("SV_Tent00_A")),
        ("SV_Tent01_A canvas", images.get("SV_Tent01_A")),
        ("Stall lightmap", images.get("SV_Stall00_all_B_LM")),
        ("BlackSmith_House00", images.get("BlackSmith_House00")),
        ("BlackSmith_House01", images.get("BlackSmith_House01")),
        ("BlackSmith_obj00", images.get("BlackSmith_obj00")),
    ]
    if beer is not None:
        tiles.append(("beer-cart preview.png", beer))
    cols = 4
    tile = 310
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * tile + 20, rows * tile + 48), (32, 35, 38))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), "Stock cart/stall/shop decoded albedos + UV overlays. Resource inspection, not native DX9.", fill=(220, 220, 220))
    for i, (label, image) in enumerate(tiles):
        if image is None:
            continue
        x = 10 + (i % cols) * tile
        y = 36 + (i // cols) * tile
        sheet_tile(draw, sheet, image, x, y, label, tile=tile)
    sheet.save(output / "stock-cart-contact.jpg", quality=92)


def audit(client: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    object02 = client / "Res" / "StageObj" / "Object02.res"
    extra = client / "Res" / "StageObj" / "Extra.res"
    mesh02 = client / "Res" / "Stage" / "Mesh02.res"

    carriage_raw, carriage_meta = zip_member(object02, "Carriage00.dat")
    shop_raw, shop_meta = zip_member(extra, "BlackSmith_Shop.dat")
    stall_raw, stall_meta = zip_member(mesh02, "SV_All.dat")
    for meta, archive, rel in (
        (carriage_meta, object02, "Res/StageObj/Object02.res"),
        (shop_meta, extra, "Res/StageObj/Extra.res"),
        (stall_meta, mesh02, "Res/Stage/Mesh02.res"),
    ):
        meta["archiveRel"] = rel
        meta["archiveSha256"] = sha256_file(archive)

    carriage = parse_bind_pose(carriage_raw)
    shop = parse_static_decoration(shop_raw)
    stall = parse_twinkle_static(stall_raw)
    if carriage is None:
        raise ValueError("Unsupported Carriage00.dat; bind-pose parser rejected the layout")
    if shop is None:
        raise ValueError("Unsupported BlackSmith_Shop.dat; static decoration parser rejected the layout")
    if stall is None:
        raise ValueError("Unsupported SV_All.dat; twinkle static parser rejected the layout")

    texture_specs = [
        ("Res/StageObj/Object02.res", "Carriage00a.tex"),
        ("Res/StageObj/Object02.res", "Carriage00b.tex"),
        ("Res/StageObj/Object02.res", "Carriage00c.tex"),
        ("Res/StageObj/Object02.res", "Doiggi00.tex"),
        ("Res/StageObj/Extra.res", "BlackSmith_House00.tex"),
        ("Res/StageObj/Extra.res", "BlackSmith_House01.tex"),
        ("Res/StageObj/Extra.res", "BlackSmith_obj00.tex"),
        ("Res/Stage/Tex009.res", "SV_Stall01a_B.tex"),
        ("Res/Stage/Tex009.res", "SV_Stall01b_B.tex"),
        ("Res/Stage/Tex009.res", "SV_Stall00_all_B_LM.tex"),
        ("Res/Stage/Tex010.res", "SV_Tent00_A.tex"),
        ("Res/Stage/Tex010.res", "SV_Tent01_A.tex"),
        ("Res/Stage/Tex007.res", "SV_Carriage00a_B.tex"),
        ("Res/Stage/Tex007.res", "SV_Carriage00b_B.tex"),
    ]
    texture_report, images = load_named_textures(client, texture_specs)
    save_images(output, images)

    # node names from the 304-byte table after geometry
    nodes = []
    cursor = carriage["geometryEnd"]
    for index in range(carriage["nodeCount"]):
        raw = carriage_raw[cursor:cursor + 32]
        nodes.append(raw.split(b"\0", 1)[0].decode("ascii"))
        cursor += 304

    carriage_prims = [primitive_record(p, textures=images) for p in carriage["primitives"]]
    shop_prims = [primitive_record(p, textures=images) for p in shop["primitives"]]
    stall_prims = []
    stall_source = []
    for primitive in stall["primitives"]:
        names = [t["name"] for t in primitive.get("textures", [])]
        if primitive["materialName"] != "SV_Stall00_all_B" and not (names and names[0] in STALL_ALBEDOS):
            continue
        stall_prims.append(primitive_record(primitive, textures=images))
        stall_source.append(primitive)

    overlays: dict[str, Image.Image] = {}
    grouped: dict[str, list] = {}
    for primitive in carriage["primitives"]:
        if not primitive.get("textures"):
            continue
        grouped.setdefault(primitive["textures"][0]["name"], []).append(primitive)
    for name, group in grouped.items():
        if name not in images:
            continue
        overlay = overlay_uv(images[name], group)
        overlay.save(output / f"{name}-uv.png")
        overlays[name] = overlay
    for name, group_name in (
        ("SV_Stall01a_B", "SV_Stall01a_B"),
        ("SV_Stall01b_B", "SV_Stall01b_B"),
        ("SV_Tent00_A", "SV_Tent00_A"),
        ("SV_Tent01_A", "SV_Tent01_A"),
        ("BlackSmith_House00", "BlackSmith_House00"),
        ("BlackSmith_House01", "BlackSmith_House01"),
        ("BlackSmith_obj00", "BlackSmith_obj00"),
    ):
        group = [p for p in list(shop["primitives"]) + stall_source if p.get("textures") and p["textures"][0]["name"] == group_name]
        if name in images and group:
            overlay = overlay_uv(images[name], group)
            overlay.save(output / f"{name}-uv.png")
            overlays[name] = overlay

    beer = None
    beer_meta = None
    if BEER_PREVIEW.is_file():
        beer = Image.open(BEER_PREVIEW).convert("RGBA")
        beer_meta = {
            "path": str(BEER_PREVIEW),
            "size": list(beer.size),
            "sha256": sha256_file(BEER_PREVIEW),
            "note": "Current beer-cart Blender preview only; not a stock client capture",
        }

    build_sheet(output, images, overlays, beer)

    cart_only = [p for p in carriage["primitives"] if p["materialName"] != "Doiggi00"]
    def union_bounds(prims):
        mins = [min(p["bounds"]["min"][i] for p in prims) for i in range(3)]
        maxs = [max(p["bounds"]["max"][i] for p in prims) for i in range(3)]
        return {"min": mins, "max": maxs, "size": [maxs[i] - mins[i] for i in range(3)]}

    report = {
        "evidence": "bounded DAT/TEX resource inspection, not native client rendering or lighting",
        "clientRoot": str(client),
        "fixtures": {
            "carriage": carriage_meta,
            "shop": shop_meta,
            "svAll": stall_meta,
        },
        "parsers": {
            "Carriage00.dat": "adu_pose.parse_bind_pose",
            "BlackSmith_Shop.dat": "twinkle_mesh.parse_static_decoration",
            "SV_All.dat": "twinkle_mesh.parse_twinkle_static",
        },
        "textures": texture_report,
        "carriage": {
            "layout": "skinned StageObj AduMesh bind pose",
            "nodeCount": carriage["nodeCount"],
            "animationCount": carriage["animationCount"],
            "animationNameInDat": "Carriage00_Idle",
            "pose": carriage.get("pose"),
            "nodes": nodes,
            "materials": [{"index": m["index"], "name": m["name"]} for m in carriage["materials"]],
            "primitives": carriage_prims,
            "boundsIncludingAnimal": union_bounds(carriage["primitives"]),
            "boundsExcludingAnimal": union_bounds(cart_only),
            "channelRolesFromBindings": {
                "Carriage00a": {
                    "usedBy": ["Carriage00a child 2"],
                    "binding": "material group Carriage00a / texture Carriage00a",
                    "geometryHint": "mid/high body panel, y 5.20..37.39, 387 verts",
                },
                "Carriage00b": {
                    "usedBy": [
                        "Carriage00a child 1 (main body 2117 verts)",
                        "Carriage00b (low wide pair y -0.32..9.68)",
                        "Carriage00c (second low pair y -0.18..6.99)",
                        "Carriage00d (long low member z -13.56..21.09)",
                        "Carriage00e/f/h/j/k small fittings",
                    ],
                    "binding": "shared atlas for timber, wheels, shafts, small hardware",
                },
                "Carriage00c": {
                    "usedBy": ["Carriage00a child 0 (tallest y 13.86..45.97)", "Carriage00g", "Carriage00i", "Carriage00j child 0"],
                    "binding": "high canopy/cover plus hanging extras",
                },
                "Doiggi00": {
                    "usedBy": ["Doiggi00 skinned animal, 4 primitives"],
                    "binding": "draft animal albedo, not cart timber",
                },
            },
        },
        "shop": {
            "layout": "static decoration AduMesh, no lightmap UV1",
            "materials": [{"index": m["index"], "name": m["name"]} for m in shop["materials"]],
            "primitives": shop_prims,
            "bounds": union_bounds(shop["primitives"]),
        },
        "stallTent": {
            "layout": "static Twinkle SV_ group with albedo + shared lightmap",
            "group": "SV_Stall00_all_B",
            "primitives": stall_prims,
            "note": "These primitives are one combined village cluster, not one kiosk. Bounds span many placed copies.",
        },
        "beerCartComparison": {
            "preview": beer_meta,
            "authored": beer_cart_authored_dimensions(),
            "stockCarriageUnits": union_bounds(cart_only),
            "axisConventionStock": "bind-pose Y-up; X width ~28, Y height ~46, Z length ~61 excluding animal",
            "axisConventionBeerCart": "Blender Z-up; overall ~4.5 x 1.72 x 3.3",
            "reuse": {
                "anatomyReusable": True,
                "reason": "Carriage00 already encodes two wheel pairs, timber body, high cover, shafts, and fittings as separate material groups with painted 512 atlases",
                "notADropIn": "Doiggi00 animal, idle animation, and skinned palettes are part of the same DAT; a static beer cart would need a static layout or stripped groups",
            },
        },
        "unknown": [
            "Native DX9 combine of albedo and lightmap, vertex color, and fog is not recovered here",
            "304-byte node records after names are not fully decoded; bone world matrices are not applied beyond stored bind-pose vertices",
            "12 UVs on Carriage00a child 1 sit far outside 0..1 and were excluded from overlays",
            "SV_Carriage00a_B / SV_Carriage00b_B in Tex007 are not referenced by Carriage00.dat or SV_All.dat stall group",
            "FurnitureRes L05_Carriage.dat is a separate 30668-byte mesh and was not treated as the stage carriage",
        ],
    }
    (output / "stock-cart-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "README.txt").write_text(
        "Private stock inspection dump. Decoded TEX/DAT evidence only; not a client screenshot.\n"
    )
    return report


if __name__ == "__main__":
    client = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CLIENT
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    result = audit(client, output)
    summary = {
        "output": str(output),
        "fixtures": {k: v["sha256"] for k, v in result["fixtures"].items()},
        "carriagePrimitives": len(result["carriage"]["primitives"]),
        "shopPrimitives": len(result["shop"]["primitives"]),
        "stallPrimitives": len(result["stallTent"]["primitives"]),
        "textures": len(result["textures"]),
    }
    print(json.dumps(summary, indent=2))
