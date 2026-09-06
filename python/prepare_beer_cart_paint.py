"""Crop stock carriage/stall TEX paint islands for the beer-cart builder.

Host-only (Pillow). Blender does not import this module.
Never writes client bytes into tracked source; output is private under .amp/tmp.

Usage:
  PYTHONPATH=python python python/prepare_beer_cart_paint.py [--stock-root DIR] [--output DIR]
Defaults:
  STOCK_ROOT = env JFTSE_STOCK_CLIENT, else ../JFTSE/.jftse-client-linux/client
  OUTPUT     = .amp/tmp/beer-cart/stock-paint
"""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import io
import json
import os
import sys
import zipfile
from pathlib import Path

from PIL import Image

from mesh_texture import tex_to_png_bytes

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLIENT = ROOT.parent / "JFTSE" / ".jftse-client-linux" / "client"
DEFAULT_OUTPUT = ROOT / ".amp" / "tmp" / "beer-cart" / "stock-paint"

# Pixel rectangles are (x, y, w, h) in decoded PNG space, origin top-left.
# Chosen by inspecting decoded albedos; animals/medallions/hardware excluded.
ISLANDS = (
    {
        "name": "wood-planks",
        "archiveRel": "Res/StageObj/Object02.res",
        "member": "Carriage00a.tex",
        "sha256": "8bbefce53e9699964ac8d6b4afbf920a0d09863151c78e1b1e8d53f4ba45d056",
        "rect": [48, 374, 312, 94],
        "role": "honey-brown vertical plank panel, lower center of Carriage00a",
        "recolor": None,
    },
    {
        "name": "wood-planks-tall",
        "archiveRel": "Res/StageObj/Object02.res",
        "member": "Carriage00c.tex",
        "sha256": "304c57fc05d13ea9bb1ff00251afa22d5771bc17424a1a7ff9243fdbce28182f",
        "rect": [356, 110, 64, 390],
        "role": "large right honey-brown plank island of Carriage00c",
        "recolor": None,
    },
    {
        "name": "wood-stall",
        "archiveRel": "Res/Stage/Tex009.res",
        "member": "SV_Stall01a_B.tex",
        "sha256": "20c021f62dbd52b77352eb32784f6a52e1e1b2c691b1536b0ed985069d84c2e9",
        "rect": [73, 248, 124, 100],
        "role": "lower-left stall plank rectangle of SV_Stall01a_B",
        "recolor": None,
    },
    {
        "name": "canvas-fold",
        "archiveRel": "Res/StageObj/Object02.res",
        "member": "Carriage00a.tex",
        "sha256": "8bbefce53e9699964ac8d6b4afbf920a0d09863151c78e1b1e8d53f4ba45d056",
        "rect": [135, 10, 240, 195],
        "role": "upper-half white folded canvas of Carriage00a",
        "recolor": None,
    },
    {
        "name": "cloth-stripes",
        "archiveRel": "Res/Stage/Tex009.res",
        "member": "SV_Stall01b_B.tex",
        "sha256": "35967f013f375de41289e438f52d7af7bf4900c3d1816ece66a069e4739a2821",
        "rect": [0, 0, 256, 335],
        "role": "SV_Stall01b_B canopy stripe cloth; rose remapped to blue, luminance/folds kept",
        "recolor": "rose_to_blue",
    },
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_stock_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("JFTSE_STOCK_CLIENT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_CLIENT.resolve()


def zip_member(archive: Path, member: str) -> bytes:
    with zipfile.ZipFile(archive) as packed:
        return packed.read(member)


def decode_tex(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(tex_to_png_bytes(data))).convert("RGBA")


def crop_rect(image: Image.Image, rect: list[int]) -> Image.Image:
    x, y, width, height = rect
    box = (x, y, x + width, y + height)
    if box[2] > image.size[0] or box[3] > image.size[1] or x < 0 or y < 0:
        raise ValueError(f"crop {rect} outside {image.size}")
    return image.crop(box)


def recolor_rose_to_blue(image: Image.Image) -> Image.Image:
    """Keep fold luminance; send rose/pink chroma to Bavarian blue, pale stripes to cream."""
    pixels = image.load()
    width, height = image.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            wrap = h < 0.10 or h > 0.88
            if not wrap:
                continue
            # Continuous chroma mapping keeps painted highlights inside blue stripes blue.
            nr, ng, nb = colorsys.hsv_to_rgb(0.565, min(0.62, s * 0.85), v)
            pixels[x, y] = (
                max(0, min(255, int(nr * 255 + 0.5))),
                max(0, min(255, int(ng * 255 + 0.5))),
                max(0, min(255, int(nb * 255 + 0.5))),
                a,
            )
    return image


def prepare(stock_root: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    decoded_cache: dict[tuple[str, str], tuple[bytes, Image.Image]] = {}
    records = []
    for island in ISLANDS:
        key = (island["archiveRel"], island["member"])
        archive = stock_root / island["archiveRel"]
        if not archive.is_file():
            raise FileNotFoundError(f"missing stock archive {archive}")
        if key not in decoded_cache:
            raw = zip_member(archive, island["member"])
            digest = sha256_bytes(raw)
            if digest != island["sha256"]:
                raise ValueError(
                    f"hash mismatch {island['member']}: got {digest}, pinned {island['sha256']}"
                )
            decoded_cache[key] = (raw, decode_tex(raw))
        raw, source = decoded_cache[key]
        crop = crop_rect(source, island["rect"])
        if island["recolor"] == "rose_to_blue":
            crop = recolor_rose_to_blue(crop.copy())
        filename = island["name"] + ".png"
        dest = output / filename
        crop.save(dest)
        records.append(
            {
                "name": island["name"],
                "file": filename,
                "archiveRel": island["archiveRel"],
                "member": island["member"],
                "sourceSha256": island["sha256"],
                "sourceSize": list(source.size),
                "cropXYWH": island["rect"],
                "cropSize": list(crop.size),
                "cropSha256": sha256_bytes(dest.read_bytes()),
                "role": island["role"],
                "recolor": island["recolor"],
            }
        )
    report = {
        "evidence": "host Pillow crop of hash-pinned decoded TEX members; not native DX9",
        "stockRoot": str(stock_root),
        "output": str(output),
        "islands": records,
        "limitations": [
            "Crops are selected paint islands, not full atlas reuse or runtime materials",
            "Rose-to-blue is a luminance-preserving hue remap, not a stock blue canopy texture",
            "Does not claim exact 100 parity with Carriage00 or SV stall fixtures",
        ],
    }
    (output / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-root", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    stock = resolve_stock_root(args.stock_root)
    output = Path(args.output).expanduser().resolve() if args.output else DEFAULT_OUTPUT
    result = prepare(stock, output)
    print(json.dumps({"output": result["output"], "islands": [i["name"] for i in result["islands"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
