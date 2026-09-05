"""Inspect private stock mesh/texture evidence without running the client.

Usage: PYTHONPATH=python python python/audit_twinkle_style.py FIXTURES OUTPUT
OUTPUT contains private decoded textures; keep it outside version control.
"""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw
from mesh_texture import tex_to_png_bytes
from twinkle_mesh import parse_twinkle_static


def audit(fixtures, output):
    output.mkdir(parents=True, exist_ok=True)
    raw = (fixtures / "SV_All.dat").read_bytes()
    parsed = parse_twinkle_static(raw)
    if parsed is None:
        raise ValueError("Unsupported stock SV_All.dat; no heuristic geometry recovery")
    names = ["SV_Stall01a_B", "SV_Stall01b_B", "SV_Tent00_A", "SV_Tent01_A", "SV_Stall00_all_B_LM"]
    report = {"evidence": "static resource inspection, not native rendering",
              "meshSha256": hashlib.sha256(raw).hexdigest(), "textures": [], "primitives": []}
    for primitive in parsed["primitives"]:
        if not primitive["textures"] or primitive["textures"][0]["name"] not in names:
            continue
        report["primitives"].append({
            "material": primitive["materialName"], "vertices": primitive["vertexCount"],
            "triangles": len(primitive["indices"]) // 3,
            "bounds": primitive["bounds"],
            "textureChannels": [t["name"] for t in primitive["textures"]],
            "uvBounds": [[min(p[i] for p in primitive["uvs"]), max(p[i] for p in primitive["uvs"])] for i in (0,1)],
        })
    sheet = Image.new("RGB", (1152, 768), (39, 43, 46))
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate(names):
        archive = "Tex010.res" if name.startswith("SV_Tent") else "Tex009.res"
        with zipfile.ZipFile(fixtures / archive) as packed:
            texture = packed.read(name + ".tex")
        image = Image.open(io.BytesIO(tex_to_png_bytes(texture))).convert("RGB")
        report["textures"].append({"archive": archive, "member": name + ".tex",
                                  "sha256": hashlib.sha256(texture).hexdigest(), "size": list(image.size)})
        image.save(output / (name + ".png"))
        image.thumbnail((360, 340))
        x, y = i % 3 * 384, i // 3 * 384
        sheet.paste(image, (x + 12, y + 30))
        draw.text((x + 12, y + 8), name, fill="white")
    sheet.save(output / "stock-style-textures.jpg", quality=93)
    (output / "stock-style-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    result = audit(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, indent=2))
