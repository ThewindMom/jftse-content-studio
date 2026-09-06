"""Build a Bavarian diamond cloth PNG from hash-pinned stock folds.

Host-only (Pillow). Does not modify original stock TEX or island crops.
Uses canvas-fold.png luminance for painted shading and cloth-stripes.png
blue chroma so diamonds are not a flat shader checker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAINT = ROOT / ".amp" / "tmp" / "beer-cart" / "stock-paint"
FOLD_SHA = "00b5162dc68c0dd96999bf437de7511a5b98b4bf178e6e9f888cd87f35032ddb"
STRIPE_SHA = "b5eecedd392dd4a55c3d079e51db7af5ab92c34c82627f34502bb2a32ff2c322"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sample(image: Image.Image, pixels, x: float, y: float) -> tuple[int, int, int, int]:
    width, height = image.size
    sx = min(width - 1, max(0, int(x * width) % width))
    sy = min(height - 1, max(0, int(y * height) % height))
    return pixels[sx, sy]


def make_diamond_cloth(paint_root: Path, size: int = 512, cells: int = 4) -> dict:
    fold_path = paint_root / "canvas-fold.png"
    stripe_path = paint_root / "cloth-stripes.png"
    fold_bytes = fold_path.read_bytes()
    stripe_bytes = stripe_path.read_bytes()
    fold_hash = sha256_bytes(fold_bytes)
    stripe_hash = sha256_bytes(stripe_bytes)
    if fold_hash != FOLD_SHA:
        raise ValueError(f"canvas-fold hash mismatch: {fold_hash}")
    if stripe_hash != STRIPE_SHA:
        raise ValueError(f"cloth-stripes hash mismatch: {stripe_hash}")

    fold = Image.open(fold_path).convert("RGBA")
    stripes = Image.open(stripe_path).convert("RGBA")
    fold_px = fold.load()
    out = Image.new("RGBA", (size, size))
    dest = out.load()

    cream = (236, 226, 196)
    blue_pixels = [p for p in stripes.getdata() if p[2] > p[0] * 1.3 and p[1] > p[0] * 1.15]
    if not blue_pixels:
        raise ValueError("Stock stripe crop contains no blue chroma samples")
    blue = tuple(sum(p[c] for p in blue_pixels) / len(blue_pixels) for c in range(3))
    for y in range(size):
        for x in range(size):
            u = (x + 0.5) / size
            v = (y + 0.5) / size
            # 45-degree lozenges, not an axis-aligned checker.
            s = (u + v) * cells
            t = (u - v) * cells
            diamond = (math.floor(s) + math.floor(t)) & 1
            fr, fg, fb, fa = sample(fold, fold_px, u * 1.35, v * 1.15)
            lum = (0.30 * fr + 0.59 * fg + 0.11 * fb) / 255.0
            shade = 0.72 + 0.46 * lum
            if diamond:
                # Chroma comes only from blue paint; pale stripes cannot cut white holes.
                r, g, b = (int(max(0, min(255, channel * shade))) for channel in blue)
            else:
                r = int(max(0, min(255, cream[0] * shade * (0.55 + 0.45 * fr / 255.0))))
                g = int(max(0, min(255, cream[1] * shade * (0.55 + 0.45 * fg / 255.0))))
                b = int(max(0, min(255, cream[2] * shade * (0.55 + 0.45 * fb / 255.0))))
            dest[x, y] = (r, g, b, 255)

    dest_path = paint_root / "cloth-diamonds.png"
    out.save(dest_path)
    report = {
        "evidence": "host Pillow lozenge cloth from hash-pinned stock fold luminance and stripe chroma; not a shader checker",
        "file": "cloth-diamonds.png",
        "size": [size, size],
        "cells": cells,
        "blueChromaMean": blue,
        "sources": [
            {
                "name": "canvas-fold.png",
                "sha256": fold_hash,
                "role": "painted fold luminance for both diamond colors",
            },
            {
                "name": "cloth-stripes.png",
                "sha256": stripe_hash,
                "role": "blue chroma for dark lozenges; rose-to-blue remap already applied",
            },
        ],
        "outputSha256": sha256_bytes(dest_path.read_bytes()),
        "limitations": [
            "Diamonds are generated, not cropped from a stock lozenge atlas",
            "Fold tiling is a host approximation of painted shading, not a native unwrap",
        ],
    }
    (paint_root / "cloth-diamonds-provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paint-root", default=None)
    args = parser.parse_args(argv)
    paint = Path(args.paint_root).expanduser().resolve() if args.paint_root else DEFAULT_PAINT
    result = make_diamond_cloth(paint)
    print(json.dumps({"file": str(paint / "cloth-diamonds.png"), "sha256": result["outputSha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
