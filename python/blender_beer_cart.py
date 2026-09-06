"""Build, preview, save, and export an original Oktoberfest beer vendor cart."""

import math
import os
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports" / "blender-beer-cart"
OUT.mkdir(parents=True, exist_ok=True)
DEFAULT_PAINT = ROOT / ".amp" / "tmp" / "beer-cart" / "stock-paint"
ASSET_OBJECTS = []
for startup_object in bpy.context.scene.objects:
    startup_object.hide_render = True


def parse_builder_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    paint_root = None
    stock_root = None
    index = 0
    while index < len(argv):
        flag = argv[index]
        if flag == "--paint-root" and index + 1 < len(argv):
            paint_root = Path(argv[index + 1]).expanduser()
            index += 2
        elif flag == "--stock-root" and index + 1 < len(argv):
            stock_root = Path(argv[index + 1]).expanduser()
            index += 2
        else:
            index += 1
    if paint_root is None:
        env_paint = os.environ.get("JFTSE_BEER_CART_PAINT", "").strip()
        paint_root = Path(env_paint).expanduser() if env_paint else DEFAULT_PAINT
    if stock_root is None:
        env_stock = os.environ.get("JFTSE_STOCK_CLIENT", "").strip()
        stock_root = Path(env_stock).expanduser() if env_stock else (ROOT.parent / "JFTSE" / ".jftse-client-linux" / "client")
    return paint_root, stock_root


PAINT_ROOT, STOCK_ROOT = parse_builder_args()
WOOD_TEX = PAINT_ROOT / "wood-planks.png"
WOOD_TALL_TEX = PAINT_ROOT / "wood-planks-tall.png"
WOOD_STALL_TEX = PAINT_ROOT / "wood-stall.png"
CLOTH_TEX = PAINT_ROOT / "cloth-stripes.png"
SWAG_TEX = PAINT_ROOT / "canvas-fold.png"
for paint_path in (WOOD_TEX, WOOD_TALL_TEX, WOOD_STALL_TEX, CLOTH_TEX, SWAG_TEX):
    if not paint_path.is_file():
        raise FileNotFoundError(
            f"missing stock paint {paint_path}; run python/prepare_beer_cart_paint.py --stock-root {STOCK_ROOT}"
        )


def socket(node, name):
    return node.inputs[name]


def material(name, color, texture=None, emission=None):
    mat = bpy.data.materials.new(name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    socket(bsdf, "Base Color").default_value = (*color, 1)
    socket(bsdf, "Roughness").default_value = 1.0
    socket(bsdf, "Metallic").default_value = 0.0
    if texture:
        image = bpy.data.images.load(str(texture), check_existing=True)
        image.pack()
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Linear"
        # Stock paint already contains its highlights and shadows. Do not relight it orange.
        socket(bsdf, "Base Color").default_value = (0, 0, 0, 1)
        links.new(tex.outputs["Color"], socket(bsdf, "Emission Color"))
        socket(bsdf, "Emission Strength").default_value = 0.8
    if emission:
        socket(bsdf, "Emission Color").default_value = (*emission, 1)
        socket(bsdf, "Emission Strength").default_value = 0.6
    return mat


MATS = {
    "wood": material("M_Wood_PaintedGrain", (.62, .38, .16), texture=WOOD_TEX),
    "wood_end": material("M_Wood_EndGrain", (.52, .3, .12), texture=WOOD_STALL_TEX),
    "wood_tall": material("M_Wood_TallPlank", (.55, .32, .16), texture=WOOD_TALL_TEX),
    "wood_dark": material("M_Wood_DarkRail", (.28, .12, .05), texture=WOOD_STALL_TEX),
    "blue": material("M_Bavarian_Blue", (.08, .22, .32)),
    "cream": material("M_Warm_Cream", (.80, .76, .64)),
    "cloth": material("M_Canopy_PaintedStripes", (.8, .8, .8), texture=CLOTH_TEX),
    "swag": material("M_Swag_PaintedCloth", (.8, .8, .8), texture=SWAG_TEX),
    "metal": material("M_Blackened_Iron", (.075, .06, .05)),
    "brass": material("M_Brass", (.52, .30, .08)),
    "beer": material("M_Amber_Beer", (.60, .32, .09)),
    "foam": material("M_Beer_Foam", (.88, .78, .59)),
    "green": material("M_Leaf_Green", (.12, .25, .08)),
    "flower": material("M_Flower_Cream", (.88, .82, .64)),
    "glow": material("M_Lantern_Glow", (.55, .30, .08), emission=(1.0, .65, .20)),
}


def assign_uv(mesh, grain="auto", scale=0.55):
    uv = mesh.uv_layers.new(name="UVMap")
    coords = [tuple(vertex.co) for vertex in mesh.vertices]
    low = [min(co[axis] for co in coords) for axis in range(3)]
    span = [max(co[axis] for co in coords) - low[axis] for axis in range(3)]
    for poly in mesh.polygons:
        nx, ny, nz = abs(poly.normal.x), abs(poly.normal.y), abs(poly.normal.z)
        axes = (0, 1) if nz >= nx and nz >= ny else (0, 2) if ny >= nx else (1, 2)
        # Map complete painted islands, with the grain along each timber's long edge.
        if grain not in ("length", "canopy") and span[axes[0]] > span[axes[1]]:
            axes = (axes[1], axes[0])
        for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
            co = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            u = (co[axes[0]] - low[axes[0]]) / max(span[axes[0]], 0.0001)
            v = (co[axes[1]] - low[axes[1]]) / max(span[axes[1]], 0.0001)
            if grain == "canopy":
                u = (co.x - low[0]) / span[0]
                v = math.acos(max(-1, min(1, -co.y / 0.84))) / math.pi
            uv.data[loop_index].uv = (0.02 + u * 0.96, 0.02 + v * 0.96)
    return uv


def mesh_obj(name, verts, faces, mat, grain="auto", uv_scale=0.55, collection=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    ASSET_OBJECTS.append(obj)
    mesh.materials.append(mat)
    assign_uv(mesh, grain, uv_scale)
    return obj


def chamfer_box(name, loc, size, mat=None, chamfer=0.045, grain="auto"):
    mat = mat or MATS["wood"]
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    c = min(chamfer, sx * 0.42, sy * 0.42, sz * 0.42)
    verts = []
    for iz in (-1, 1):
        z = iz * sz
        zi = iz * (sz - c)
        for iy in (-1, 1):
            y = iy * sy
            yi = iy * (sy - c)
            for ix in (-1, 1):
                x = ix * sx
                xi = ix * (sx - c)
                verts.extend([(xi, yi, z), (xi, y, zi), (x, yi, zi)])
    # 8 corners * 3 verts = 24. Faces: 6 large insets + 12 chamfer strips + 8 corner tris.
    def corner(iz, iy, ix):
        return ((iz + 1) // 2 * 12) + ((iy + 1) // 2 * 6) + ((ix + 1) // 2 * 3)

    faces = []
    # +Z / -Z inset quads (verts 0 of each corner)
    faces.append((corner(-1, -1, -1) + 0, corner(-1, -1, 1) + 0, corner(-1, 1, 1) + 0, corner(-1, 1, -1) + 0))
    faces.append((corner(1, -1, -1) + 0, corner(1, 1, -1) + 0, corner(1, 1, 1) + 0, corner(1, -1, 1) + 0))
    # +Y / -Y inset (vert 1)
    faces.append((corner(-1, -1, -1) + 1, corner(1, -1, -1) + 1, corner(1, -1, 1) + 1, corner(-1, -1, 1) + 1))
    faces.append((corner(-1, 1, -1) + 1, corner(-1, 1, 1) + 1, corner(1, 1, 1) + 1, corner(1, 1, -1) + 1))
    # +X / -X inset (vert 2)
    faces.append((corner(-1, -1, -1) + 2, corner(-1, 1, -1) + 2, corner(1, 1, -1) + 2, corner(1, -1, -1) + 2))
    faces.append((corner(-1, -1, 1) + 2, corner(1, -1, 1) + 2, corner(1, 1, 1) + 2, corner(-1, 1, 1) + 2))
    # edge chamfers
    for iz in (-1, 1):
        faces.append((corner(iz, -1, -1) + 0, corner(iz, -1, -1) + 1, corner(iz, -1, 1) + 1, corner(iz, -1, 1) + 0))
        faces.append((corner(iz, 1, -1) + 0, corner(iz, 1, 1) + 0, corner(iz, 1, 1) + 1, corner(iz, 1, -1) + 1))
        faces.append((corner(iz, -1, -1) + 0, corner(iz, 1, -1) + 0, corner(iz, 1, -1) + 2, corner(iz, -1, -1) + 2))
        faces.append((corner(iz, -1, 1) + 0, corner(iz, -1, 1) + 2, corner(iz, 1, 1) + 2, corner(iz, 1, 1) + 0))
    for iy in (-1, 1):
        faces.append((corner(-1, iy, -1) + 1, corner(-1, iy, -1) + 2, corner(1, iy, -1) + 2, corner(1, iy, -1) + 1))
        faces.append((corner(-1, iy, 1) + 1, corner(1, iy, 1) + 1, corner(1, iy, 1) + 2, corner(-1, iy, 1) + 2))
    for iz in (-1, 1):
        for iy in (-1, 1):
            for ix in (-1, 1):
                base = corner(iz, iy, ix)
                if (iz * iy * ix) > 0:
                    faces.append((base + 0, base + 2, base + 1))
                else:
                    faces.append((base + 0, base + 1, base + 2))
    obj = mesh_obj(name, verts, faces, mat, grain)
    obj.location = loc
    return obj


def cylinder(name, loc, radius, depth, mat, segments=16, axis="Z", grain="auto"):
    verts = []
    faces = []
    for d in (-depth / 2, depth / 2):
        for i in range(segments):
            a = 2 * math.pi * i / segments
            p = (radius * math.cos(a), radius * math.sin(a), d)
            if axis == "Y":
                p = (p[0], p[2], p[1])
            elif axis == "X":
                p = (p[2], p[0], p[1])
            verts.append(p)
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j, segments + i))
    faces += [tuple(range(segments - 1, -1, -1)), tuple(range(segments, 2 * segments))]
    obj = mesh_obj(name, verts, faces, mat, grain)
    obj.location = loc
    return obj


def beam_between(name, a, b, width, mat=None, chamfer=0.02):
    mat = mat or MATS["wood"]
    mid = tuple((a[i] + b[i]) / 2 for i in range(3))
    length = math.dist(a, b)
    obj = chamfer_box(name, mid, (width, width, length), mat, chamfer, grain="z")
    dx, dy, dz = (b[i] - a[i] for i in range(3))
    obj.rotation_euler = (0, math.atan2(math.hypot(dx, dy), dz), math.atan2(dy, dx))
    return obj


def ring(name, loc, major, minor, mat, axis="Y", segments=24, sides=8, grain="auto"):
    verts = []
    faces = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        for j in range(sides):
            b = 2 * math.pi * j / sides
            x = (major + minor * math.cos(b)) * math.cos(a)
            z = (major + minor * math.cos(b)) * math.sin(a)
            y = minor * math.sin(b)
            verts.append((x, y, z) if axis == "Y" else (-y, x, z) if axis == "X" else (x, -z, y))
    for i in range(segments):
        for j in range(sides):
            ni = (i + 1) % segments
            nj = (j + 1) % sides
            faces.append((i * sides + j, ni * sides + j, ni * sides + nj, i * sides + nj))
    obj = mesh_obj(name, verts, faces, mat, grain)
    obj.location = loc
    return obj


def ribbon_bow(prefix, loc, scale=1.0):
    x, y, z = loc
    knot = cylinder(f"{prefix}_Knot", (x, y, z), 0.07 * scale, 0.08 * scale, MATS["cream"], 12, "Y")
    for side in (-1, 1):
        loop_verts = []
        loop_faces = []
        for i in range(10):
            a = math.pi * i / 9
            rx = 0.16 * scale * math.sin(a)
            rz = 0.11 * scale * math.sin(2 * a) * 0.35 + 0.09 * scale * (1 - math.cos(a))
            for t in (-0.018 * scale, 0.018 * scale):
                loop_verts.append((side * (0.05 * scale + rx), t, rz))
        for i in range(9):
            loop_faces.append((i * 2, i * 2 + 1, (i + 1) * 2 + 1, (i + 1) * 2))
        obj = mesh_obj(f"{prefix}_Loop_{side:+}", loop_verts, loop_faces, MATS["blue"], "auto", 1.2)
        obj.location = (x, y, z)
        tail_verts = [
            (side * 0.02 * scale, -0.015 * scale, -0.02 * scale),
            (side * 0.11 * scale, -0.015 * scale, -0.38 * scale),
            (side * 0.02 * scale, 0.015 * scale, -0.02 * scale),
            (side * 0.11 * scale, 0.015 * scale, -0.38 * scale),
            (side * -0.02 * scale, -0.015 * scale, -0.02 * scale),
            (side * 0.03 * scale, -0.015 * scale, -0.38 * scale),
            (side * -0.02 * scale, 0.015 * scale, -0.02 * scale),
            (side * 0.03 * scale, 0.015 * scale, -0.38 * scale),
        ]
        tail_faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4), (1, 5, 7, 3), (2, 3, 7, 6), (0, 4, 5, 1)]
        tail = mesh_obj(f"{prefix}_Tail_{side:+}", tail_verts, tail_faces, MATS["blue"], "z", 1.4)
        tail.location = (x, y, z - 0.02 * scale)
        tail.rotation_euler[1] = side * 0.18
    return knot


def canopy_cloth():
    """One connected arched canvas with striped UVs and a scalloped front valance."""
    xs = 16
    arcs = 11
    x0, x1 = -1.38, 1.38
    verts = []
    for i in range(xs + 1):
        x = x0 + (x1 - x0) * i / xs
        for j in range(arcs):
            a = math.pi * j / (arcs - 1)
            y = -0.84 * math.cos(a)
            z = 2.78 + 0.46 * math.sin(a) - 0.035 * math.sin(i * math.pi / 2) ** 2
            verts.append((x, y, z))
    faces = []
    for i in range(xs):
        for j in range(arcs - 1):
            a = i * arcs + j
            faces.append((a, a + 1, a + 1 + arcs, a + arcs))
    mesh_obj("Canopy_Cloth", verts, faces, MATS["cloth"], "canopy", 0.39)

    # Scalloped front valance as thin cloth, not cylinders.
    val_verts = []
    val_faces = []
    scallops = 4
    depth = 0.16
    for i in range(scallops * 4 + 1):
        t = i / (scallops * 4)
        x = x0 + (x1 - x0) * t
        dip = abs(math.sin(t * scallops * math.pi)) * depth
        val_verts.append((x, -0.84, 2.78))
        val_verts.append((x, -0.88, 2.78 - 0.09 - dip))
    for i in range(scallops * 4):
        val_faces.append((i * 2, i * 2 + 1, i * 2 + 3, i * 2 + 2))
    mesh_obj("Canopy_Valance_Front", val_verts, val_faces, MATS["cloth"], "length", 0.39)

    rear_verts = [(x, -y, z) for x, y, z in val_verts]
    mesh_obj("Canopy_Valance_Rear", rear_verts, val_faces, MATS["cloth"], "length", 0.39)

    # Timber roof rails that actually meet the cloth.
    for y, name in ((-0.02, "Canopy_Ridge_Beam"),):
        chamfer_box(name, (0, y, 3.11), (2.58, 0.16, 0.12), MATS["wood"], 0.03, "x")
    chamfer_box("Canopy_Front_Rail", (0, -0.72, 2.69), (2.58, 0.16, 0.14), MATS["wood"], 0.03, "x")
    chamfer_box("Canopy_Rear_Rail", (0, 0.72, 2.69), (2.58, 0.16, 0.14), MATS["wood"], 0.03, "x")
    for x, side in ((-1.32, "L"), (1.32, "R")):
        chamfer_box(f"Canopy_Side_Rail_{side}", (x, 0, 2.69), (0.12, 1.46, 0.12), MATS["wood"], 0.025, "y")
        cap = [(math.copysign(1.38, x), -0.84 * math.cos(j * math.pi / 10), 2.78 + 0.46 * math.sin(j * math.pi / 10)) for j in range(11)]
        mesh_obj(f"Canopy_EndCloth_{side}", cap, [(0, j, j + 1) for j in range(1, 10)], MATS["swag"], "length")


def lower_swag(name, x0, x1, y, z, depth=0.28):
    verts = []
    faces = []
    steps = 10
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        dip = depth * math.sin(t * math.pi)
        verts.append((x, y, z))
        verts.append((x, y + 0.04, z - 0.05 - dip))
        verts.append((x, y, z - 0.12 - dip))
    for i in range(steps):
        for r in range(2):
            a = i * 3 + r
            faces.append((a, a + 1, a + 4, a + 3))
    return mesh_obj(name, verts, faces, MATS["swag"], "length", 0.55)


def flower_cluster(prefix, loc):
    x, y, z = loc
    for leaf, ang in enumerate((0.2, 1.1, 2.2, 3.4, 4.5, 5.4)):
        w, h = 0.16, 0.09
        cx = x + 0.12 * math.cos(ang)
        cz = z + 0.10 * math.sin(ang)
        verts = [
            (cx + w * math.cos(ang), y, cz + w * math.sin(ang)),
            (cx - 0.04 * math.cos(ang) + h * math.cos(ang + 1.2), y + 0.01, cz - 0.04 * math.sin(ang) + h * math.sin(ang + 1.2)),
            (cx - 0.04 * math.cos(ang) - h * math.cos(ang + 1.2), y + 0.01, cz - 0.04 * math.sin(ang) - h * math.sin(ang + 1.2)),
        ]
        mesh_obj(f"{prefix}_Leaf_{leaf}", verts, [(0, 1, 2)], MATS["green"], "auto", 1.4)
    cylinder(f"{prefix}_Center", (x, y - 0.02, z), 0.035, 0.04, MATS["brass"], 8, "Y")
    for petal in range(5):
        a = 2 * math.pi * petal / 5
        px = x + 0.055 * math.cos(a)
        pz = z + 0.055 * math.sin(a)
        cylinder(f"{prefix}_Petal_{petal}", (px, y - 0.03, pz), 0.028, 0.02, MATS["flower"], 8, "Y")


# Cart body: planked sides, shaped rim, inset end, chunky frame.
chamfer_box("Cart_Floor", (0, 0, 0.68), (2.28, 1.22, 0.14), MATS["wood"], 0.04, "x")
for i, x in enumerate((-0.95, -0.48, 0.0, 0.48, 0.95)):
    chamfer_box(f"Counter_Plank_{i}", (x, 0, 1.48), (0.44, 1.38, 0.08), MATS["wood"], 0.02, "y")
chamfer_box("Counter_Rim_Front", (0, -0.72, 1.52), (2.42, 0.1, 0.12), MATS["wood"], 0.03, "x")
chamfer_box("Counter_Rim_Rear", (0, 0.72, 1.52), (2.42, 0.1, 0.12), MATS["wood"], 0.03, "x")
chamfer_box("Counter_Rim_Left", (-1.22, 0, 1.52), (0.1, 1.42, 0.12), MATS["wood"], 0.03, "y")
chamfer_box("Counter_Rim_Right", (1.22, 0, 1.52), (0.1, 1.42, 0.12), MATS["wood"], 0.03, "y")

for y, side in ((-0.58, "Front"), (0.58, "Rear")):
    chamfer_box(f"Body_PaintedPanel_{side}", (0, y, 1.06), (2.20, 0.10, 0.68), MATS["wood"], 0.025, "length")
for x, end in ((-1.12, "Left"), (1.12, "Right")):
    for i, y in enumerate((-0.38, 0.0, 0.38)):
        chamfer_box(f"Body_End_{end}_{i}", (x, y, 1.06), (0.08, 0.36, 0.62), MATS["wood_tall"], 0.018, "y")
    chamfer_box(f"Body_EndRail_{end}", (x, 0, 1.34), (0.1, 1.12, 0.08), MATS["wood_dark"], 0.02, "y")

for x in (-1.08, 1.08):
    chamfer_box(f"Frame_Post_{x:+}", (x, 0, 1.08), (0.16, 1.18, 0.72), MATS["wood_dark"], 0.03, "y")

# Tow shafts: blunt timber, iron caps, no floating rings.
for y in (-0.38, 0.38):
    beam_between(f"Tow_Handle_{y:+}", (-0.95, y, 0.82), (-2.18, y, 0.46), 0.12, MATS["wood"], 0.02)
    chamfer_box(f"Tow_Cap_{y:+}", (-2.22, y, 0.45), (0.1, 0.12, 0.12), MATS["metal"], 0.015, "x")

# Wheels.
for y, label, x in ((-0.78, "Front", 0.52), (0.78, "Behind", 0.52)):
    loc = (x, y, 0.56)
    ring(f"Wheel_{label}_Wood_Rim", loc, 0.52, 0.095, MATS["wood_tall"], segments=16, sides=6)
    ring(f"Wheel_{label}_Iron_Tyre", loc, 0.62, 0.035, MATS["metal"], segments=16, sides=4)
    cylinder(f"Wheel_{label}_Hub", loc, 0.13, 0.2, MATS["metal"], 12, "Y")
    for i in range(8):
        a = 2 * math.pi * i / 8
        p = (loc[0] + 0.48 * math.cos(a), y, loc[2] + 0.48 * math.sin(a))
        beam_between(f"Wheel_{label}_Spoke_{i:02}", loc, p, 0.085, MATS["wood"], 0.012)

# Canopy uprights, cloth, bows, lanterns.
for x in (-1.08, 1.08):
    for y in (-0.52, 0.52):
        chamfer_box(f"Canopy_Upright_{x:+}_{y:+}", (x, y, 2.18), (0.17, 0.17, 1.28), MATS["wood_tall"], 0.025, "y")
canopy_cloth()
ribbon_bow("Bow_Left", (-1.16, -0.88, 2.68), 1.25)
ribbon_bow("Bow_Right", (1.16, -0.88, 2.68), 1.25)

for x, tag in ((-1.38, "L"), (1.38, "R")):
    cylinder(f"Lantern_{tag}_Glow", (x, -0.82, 2.18), 0.12, 0.3, MATS["glow"], 8)
    for z, cap in ((1.98, "Bot"), (2.38, "Top")):
        cylinder(f"Lantern_{tag}_Cap_{cap}", (x, -0.82, z), 0.16, 0.08, MATS["metal"], 8)
    for a in range(4):
        ang = 2 * math.pi * a / 4
        chamfer_box(
            f"Lantern_{tag}_Cage_{a}",
            (x + 0.12 * math.cos(ang), -0.82 + 0.12 * math.sin(ang), 2.18),
            (0.03, 0.03, 0.32),
            MATS["metal"],
            0.008,
            "z",
        )

# Horizontal keg, hoops, head, brass tap.
cylinder("Keg_Barrel", (0.58, 0.08, 1.82), 0.42, 0.7, MATS["wood_tall"], 18, "X", "z")
for i, x in enumerate((0.32, 0.58, 0.84)):
    ring(f"Keg_Iron_Hoop_{i}", (x, 0.08, 1.82), 0.425, 0.03, MATS["metal"], axis="X", segments=18, sides=6)
cylinder("Keg_Front_Head", (0.94, 0.08, 1.82), 0.36, 0.05, MATS["wood_end"], 16, "X")
cylinder("Brass_Tap_Body", (1.02, 0.08, 1.82), 0.055, 0.12, MATS["brass"], 10, "X")
beam_between("Brass_Tap_Spout", (1.08, 0.08, 1.82), (1.22, 0.08, 1.64), 0.045, MATS["brass"], 0.01)
cylinder("Brass_Tap_Nozzle", (1.24, 0.08, 1.62), 0.035, 0.06, MATS["brass"], 8, "Z")
beam_between("Brass_Tap_Handle", (1.02, 0.08, 1.88), (1.02, 0.08, 2.08), 0.04, MATS["brass"], 0.008)
chamfer_box("Brass_Tap_TBar", (1.02, 0.08, 2.1), (0.16, 0.04, 0.04), MATS["brass"], 0.008, "x")

# Mugs.
for i, x in enumerate((-0.68, -0.18)):
    cylinder(f"Beer_Mug_{i}_Body", (x, -0.32, 1.72), 0.15, 0.36, MATS["beer"], 12)
    ring(f"Beer_Mug_{i}_Rim", (x, -0.32, 1.9), 0.15, 0.02, MATS["metal"], axis="Z", segments=12, sides=6)
    ring(f"Beer_Mug_{i}_Handle", (x + 0.2, -0.32, 1.72), 0.12, 0.028, MATS["metal"], axis="Y", segments=12, sides=6)
    cylinder(f"Beer_Mug_{i}_Foam", (x, -0.32, 1.94), 0.14, 0.08, MATS["foam"], 10)

# Bunting.
for i in range(5):
    x = -0.84 + i * 0.42
    z = 2.42 - 0.07 * (1 - abs(i - 2) / 2)
    verts = [(x - 0.14, -0.72, z), (x + 0.14, -0.72, z), (x, -0.72, z - 0.24)]
    mesh_obj(f"Bunting_Flag_{i}", verts, [(0, 1, 2)], MATS["cream"] if i in (2, 4) else MATS["blue"])

# Lower fabric swags and floral clusters.
flower_xs = (-0.92, 0.0, 0.92)
for i, x in enumerate(flower_xs):
    flower_cluster(f"Floral_{i}", (x, -0.78, 1.22))
for i in range(2):
    lower_swag(f"Lower_Swag_{i}", flower_xs[i] + 0.12, flower_xs[i + 1] - 0.12, -0.76, 1.20, 0.28)

# Preview-only distant cyclorama, excluded from GLB. Same color on floor and walls so it reads as air, not a table.
sky = material("M_Preview_Sky", (.46, .54, .62))
back = chamfer_box("PREVIEW_Back", (0.0, 8.5, 3.0), (24.0, 0.2, 16.0), sky, 0.02, "x")
left = chamfer_box("PREVIEW_Left", (-8.8, 0.0, 3.0), (0.2, 24.0, 16.0), sky, 0.02, "y")
right = chamfer_box("PREVIEW_Right", (8.8, 0.0, 3.0), (0.2, 24.0, 16.0), sky, 0.02, "y")
floor = chamfer_box("PREVIEW_Floor", (0.0, 0.0, -3.4), (24.0, 24.0, 0.2), sky, 0.02, "x")
for preview in (back, left, right, floor):
    ASSET_OBJECTS.remove(preview)

# Preview camera and lights; no ground slab. Neutral blue-gray world fills the frame.
camera_data = bpy.data.cameras.new("PREVIEW_Camera")
camera = bpy.data.objects.new("PREVIEW_Camera", camera_data)
bpy.context.scene.collection.objects.link(camera)
camera.location = (-5.55, -7.15, 2.72)
camera.rotation_euler = (math.radians(74), 0, math.radians(-38))
camera_data.lens = 40
bpy.context.scene.camera = camera
for name, loc, energy, size in (
    ("PREVIEW_Key", (-3.2, -4.6, 6.4), 1100, 4.2),
    ("PREVIEW_Fill", (4.2, -2.4, 4.2), 620, 3.4),
    ("PREVIEW_Rim", (1.2, 4.4, 5.2), 780, 3.2),
):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = loc

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "preview.png")
if scene.world:
    scene.world.color = (0.42, 0.50, 0.58)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "beer-cart.blend"), compress=True, check_existing=False)
bpy.ops.render.render(write_still=True)

for obj in scene.objects:
    obj.select_set(False)
for obj in ASSET_OBJECTS:
    obj.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=str(OUT / "beer-cart.glb"),
    export_format="GLB",
    use_selection=True,
    export_animations=False,
    export_skins=False,
    export_morph=False,
    export_cameras=False,
    export_lights=False,
    export_draco_mesh_compression_enable=False,
    export_meshopt_compression_enable=False,
    export_yup=True,
    export_apply=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
)

triangles = sum(len(p.vertices) - 2 for o in ASSET_OBJECTS for p in o.data.polygons)
materials = {m.name for o in ASSET_OBJECTS for m in o.data.materials}
print(f"BEER_CART_RESULT triangles={triangles} materials={len(materials)} meshes={len(ASSET_OBJECTS)}")
