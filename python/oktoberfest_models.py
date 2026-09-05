"""Original stylized geometry and textures. No client assets are read or copied.

The editable source is this deterministic model generator. Deliverables are GLB,
OBJ, an original painted-style atlas, and Studio previews. The separate native
writer uses private stock metadata templates, never stock model geometry.
"""
import hashlib
import io
import json
import math
import random
import struct
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

PREFIX = "Studio/Oktoberfest/"
NAMES = {
    "Oktoberfest_BrewersPavilion": "Original · Brewers’ pavilion",
    "Oktoberfest_PretzelStand": "Original · Pretzel stand",
    "Oktoberfest_GingerbreadStand": "Original · Gingerbread stand",
    "Oktoberfest_FoodStand": "Original · Harvest food stand",
    "Oktoberfest_BeerGarden": "Original · Table & benches",
    "Oktoberfest_FestivalArch": "Original · Festival arch",
    "Oktoberfest_Festzelt": "Original · Grand festzelt",
    "Oktoberfest_Maypole": "Original · Wreath maypole",
    "Oktoberfest_BarrelWagon": "Original · Barrel wagon",
    "Oktoberfest_Bandstand": "Original · Brass bandstand",
}
MATERIALS = ["oak", "darkwood", "blue", "ivory", "bread", "icing", "ginger", "metal",
             "plaster", "leaf", "terracotta", "amber", "foam", "stone", "red", "rope"]
PALETTE = [(164, 109, 56), (90, 56, 32), (72, 133, 168), (232, 221, 177),
           (199, 124, 44), (248, 227, 184), (124, 61, 31), (86, 99, 97),
           (214, 181, 120), (97, 131, 58), (158, 85, 46), (225, 154, 42),
           (246, 229, 178), (128, 126, 110), (166, 65, 44), (167, 143, 93)]


def atlas() -> bytes:
    """Sixteen original surface swatches, with grain, cloth and edge wear."""
    image = Image.new("RGB", (512, 512))
    randomizer = random.Random(20260905)
    pixels = image.load()
    for slot, color in enumerate(PALETTE):
        for y in range(128):
            for x in range(128):
                brush = math.sin(x * .22 + math.sin(y * .05) * 2) * 5 if slot in (0, 1) else math.sin(x * .06 + y * .08) * 3
                edge = min(x, y, 127 - x, 127 - y)
                value = brush + randomizer.uniform(-2, 2) + min(edge, 14) * .5 - 5
                pixels[slot % 4 * 128 + x, slot // 4 * 128 + y] = tuple(max(0, min(255, int(v + value))) for v in color)
    draw = ImageDraw.Draw(image)
    for slot in (0, 1):
        ox, oy = slot % 4 * 128, slot // 4 * 128
        for x in range(12, 128, 23):
            path = [(ox + x + math.sin(y * .055 + x) * 2, oy + y) for y in range(5, 124, 4)]
            draw.line(path, fill=tuple(int(c * .78) for c in PALETTE[slot]), width=2)
            draw.line([(px + 2, py) for px, py in path], fill=tuple(min(255, int(c * 1.14)) for c in PALETTE[slot]), width=1)
        draw.ellipse((ox + 48, oy + 37, ox + 62, oy + 62), outline=tuple(int(c * .7) for c in PALETTE[slot]), width=2)
    for slot in (2, 3):
        ox, oy = slot % 4 * 128, slot // 4 * 128
        for y in range(4, 128, 6):
            draw.line((ox + 4, oy + y, ox + 123, oy + y), fill=tuple(int(c * .96) for c in PALETTE[slot]))
        draw.line((ox + 5, oy + 7, ox + 122, oy + 7), fill=(245, 234, 191), width=2)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def mul(a, value):
    return tuple(x * value for x in a)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    length = math.sqrt(sum(v * v for v in a))
    return mul(a, 1 / length) if length > 1e-8 else (0, 1, 0)


class Model:
    def __init__(self, name):
        self.name = name
        self.positions, self.normals, self.uvs, self.colors, self.indices = [], [], [], [], []

    def face(self, points, material):
        normal = unit(cross(add(points[1], mul(points[0], -1)), add(points[2], mul(points[0], -1))))
        shade = .76 + .22 * max(0, sum(a * b for a, b in zip(normal, unit((-.5, 1, .7)))))
        slot = MATERIALS.index(material)
        x, y = slot % 4 * .25, slot // 4 * .25
        uv = [(x + .018, y + .018), (x + .232, y + .018), (x + .232, y + .232), (x + .018, y + .232)]
        start = len(self.positions) // 3
        for i, point in enumerate(points):
            self.positions.extend(point)
            self.normals.extend(normal)
            self.uvs.extend(uv[i % 4])
            self.colors.extend((shade, shade, shade))
        for i in range(1, len(points) - 1):
            self.indices.extend((start, start + i, start + i + 1))

    def box(self, center, size, material="oak", yaw=0, bevel=.12):
        sx, sy, sz = (v / 2 for v in size)
        bevel = min(bevel, sx * .3, sy * .3, sz * .3)
        ca, sa = math.cos(yaw), math.sin(yaw)
        def ring(y, inset):
            x, z = sx - inset, sz - inset
            edge = max(bevel - inset, .001)
            outline = [(-x + edge, -z), (x - edge, -z), (x, -z + edge), (x, z - edge),
                       (x - edge, z), (-x + edge, z), (-x, z - edge), (-x, -z + edge)]
            return [add(center, (px * ca + pz * sa, y, pz * ca - px * sa)) for px, pz in outline]
        rings = [ring(-sy, bevel * .7), ring(-sy + bevel, 0), ring(sy - bevel, 0), ring(sy, bevel * .7)]
        for lower, upper in zip(rings, rings[1:]):
            for i in range(8):
                j = (i + 1) % 8
                self.face([lower[i], upper[i], upper[j], lower[j]], material)
        for rim, reverse in [(rings[0], False), (rings[-1], True)]:
            mid = tuple(sum(p[i] for p in rim) / 8 for i in range(3))
            for i in range(8):
                triangle = [mid, rim[i], rim[(i + 1) % 8]]
                self.face(triangle[::-1] if reverse else triangle, material)

    def beam(self, start, end, radius, material="darkwood", sides=6):
        direction = unit(add(end, mul(start, -1)))
        u = unit(cross(direction, (0, 0, 1) if abs(direction[2]) < .9 else (1, 0, 0)))
        v = cross(direction, u)
        rings = [[add(center, add(mul(u, math.cos(i * math.tau / sides) * radius), mul(v, math.sin(i * math.tau / sides) * radius))) for i in range(sides)] for center in (start, end)]
        for i in range(sides):
            j = (i + 1) % sides
            self.face([rings[0][i], rings[0][j], rings[1][j], rings[1][i]], material)
            self.face([start, rings[0][j], rings[0][i]], material)
            self.face([end, rings[1][i], rings[1][j]], material)

    def tube(self, path, radius, material="bread", sides=6, closed=False):
        rings = []
        for i, point in enumerate(path):
            prev = path[(i - 1) % len(path)] if closed or i > 0 else path[0]
            nxt = path[(i + 1) % len(path)] if closed or i + 1 < len(path) else path[-1]
            tangent = unit(add(nxt, mul(prev, -1)))
            u = unit(cross(tangent, (0, 0, 1)))
            v = cross(tangent, u)
            rings.append([add(point, add(mul(u, radius * math.cos(j * math.tau / sides)), mul(v, radius * math.sin(j * math.tau / sides)))) for j in range(sides)])
        for i in range(len(rings) if closed else len(rings) - 1):
            nxt = (i + 1) % len(rings)
            for j in range(sides):
                k = (j + 1) % sides
                self.face([rings[i][j], rings[i][k], rings[nxt][k], rings[nxt][j]], material)

    def bunting(self, start, end, count=9):
        points = []
        for i in range(count + 1):
            t = i / count
            points.append(tuple(start[k] * (1 - t) + end[k] * t - (math.sin(t * math.pi) * 2 if k == 1 else 0) for k in range(3)))
        self.tube(points, .12, "rope")
        for i, (a, b) in enumerate(zip(points, points[1:])):
            c = tuple((a[k] + b[k]) / 2 - (2.4 if k == 1 else 0) for k in range(3))
            self.face([a, b, c], "blue" if i % 2 else "ivory")

    def pretzel(self, center, scale=1):
        knots = [(-1.2, .2), (-1.35, 1), (-.8, 1.5), (-.25, 1.2), (.7, -.65), (1.15, -.3),
                 (1.25, .1), (.8, .5), (-.8, .5), (-1.25, .1), (-1.15, -.3), (-.7, -.65),
                 (.25, 1.2), (.8, 1.5), (1.35, 1), (1.2, .2), (.6, -.7), (0, -.85), (-.6, -.7)]
        path = []
        for i in range(len(knots)):
            a, b, c, d = [knots[(i + delta) % len(knots)] for delta in (-1, 0, 1, 2)]
            for j in range(3):
                t = j / 3
                xy = [.5 * ((2 * b[k]) + (-a[k] + c[k]) * t + (2 * a[k] - 5 * b[k] + 4 * c[k] - d[k]) * t*t + (-a[k] + 3*b[k] - 3*c[k] + d[k]) * t*t*t) for k in range(2)]
                path.append(add(center, (xy[0] * scale, xy[1] * scale, math.sin(i * .6) * scale * .1)))
        self.tube(path, scale * .19, "bread", closed=True)
        for i in range(0, len(path), 5):
            self.box(add(path[i], (0, 0, scale * .17)), (scale * .09, scale * .15, scale * .05), "icing", bevel=.01)

    def heart(self, center, scale=1):
        points = []
        for i in range(32):
            t = i * math.tau / 32
            points.append(add(center, (math.sin(t)**3 * 2 * scale, (13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t)) / 8 * scale, .3)))
        back = [add(p, (0, 0, -.65)) for p in points]
        for i in range(len(points)):
            j = (i + 1) % len(points)
            self.face([add(center, (0, 0, .3)), points[j], points[i]], "ginger")
            self.face([points[i], points[j], back[j], back[i]], "ginger")
            self.face([add(center, (0, 0, -.35)), back[i], back[j]], "ginger")
        icing = [add(center, ((p[0] - center[0]) * .84, (p[1] - center[1]) * .84, .47)) for p in points]
        self.tube(icing, .08 * scale, "icing", closed=True)

    def mug(self, center, scale=1):
        self.beam(add(center, (0, 0, 0)), add(center, (0, 2.3 * scale, 0)), .8 * scale, "amber", 10)
        self.beam(add(center, (0, 2.3 * scale, 0)), add(center, (0, 2.7 * scale, 0)), .9 * scale, "foam", 10)
        path = [add(center, (scale * (.75 + .65 * math.sin(t)), scale * (1.2 + .85 * math.cos(t)), 0)) for t in [i * math.pi / 10 for i in range(11)]]
        self.tube(path, scale * .18, "metal")

    def roof(self, width, depth, height, ridge, cloth="blue"):
        for side in (-1, 1):
            for j in range(8):
                z0, z1 = -depth / 2 + j * depth / 8, -depth / 2 + (j + 1) * depth / 8
                profile = [(0, ridge), (width * .35 * side, height + 2), (width * .5 * side, height), (width * .55 * side, height + .5)]
                for (x0, y0), (x1, y1) in zip(profile, profile[1:]):
                    panel = [(x0,y0,z0),(x1,y1,z0),(x1,y1,z1),(x0,y0,z1)]
                    self.face(panel[::-1] if side > 0 else panel, cloth if j % 2 == 0 else "ivory")
                self.face([(profile[-1][0],height+.5,z0),(profile[-1][0],height+.5,z1),(profile[-1][0],height-1.3,z1),(profile[-1][0],height-1.3,z0)], cloth if j % 2 == 0 else "ivory")
        self.beam((0, ridge, -depth/2-.4), (0, ridge, depth/2+.4), .65)

    def garland(self, start, end, sag=2):
        path = [tuple(start[k]*(1-t)+end[k]*t - (sag*math.sin(t*math.pi) if k == 1 else 0)
                      for k in range(3)) for t in [i/16 for i in range(17)]]
        self.tube(path, .55, "leaf")
        for i, point in enumerate(path[1:-1]):
            self.beam(point, add(point, ((-1 if i % 2 else 1)*.8, -.9, .35)), .45, "leaf", 5)

    def lantern(self, center, scale=1):
        self.beam(add(center, (0, 2.4*scale, 0)), add(center, (0, 4*scale, 0)), .1, "rope")
        self.box(center, (1.5*scale, 2.4*scale, 1.5*scale), "amber", bevel=.3)
        for y in (-1.3, 1.3): self.box(add(center, (0, y*scale, 0)), (2*scale, .3*scale, 2*scale), "metal")
        for x in (-.8,.8):
            for z in (-.8,.8): self.beam(add(center, (x*scale,-1.3*scale,z*scale)), add(center,(x*scale,1.3*scale,z*scale)), .1, "metal", 4)

    def keg(self, center, radius=2.3, height=5):
        rings = [(0, radius*.82), (height*.22, radius), (height*.78, radius), (height, radius*.82)]
        for (y0,r0),(y1,r1) in zip(rings, rings[1:]):
            for i in range(12):
                a,b = i*math.tau/12,(i+1)*math.tau/12
                self.face([add(center,(r0*math.cos(a),y0,r0*math.sin(a))),add(center,(r1*math.cos(a),y1,r1*math.sin(a))),
                           add(center,(r1*math.cos(b),y1,r1*math.sin(b))),add(center,(r0*math.cos(b),y0,r0*math.sin(b)))], "oak" if i % 3 else "darkwood")
        for y in (height*.22,height*.75):
            self.beam(add(center,(0,y,0)),add(center,(0,y+.35,0)),radius*1.03,"metal",12)
        self.beam(add(center,(0,height-.1,0)),add(center,(0,height,0)),radius*.83,"oak",12)


def build_model(name):
    model = Model(name)
    if name == "Oktoberfest_BrewersPavilion":
        model.box((0, 1, 0), (36, 2, 28), "darkwood", bevel=.35)
        for x in range(-15, 17, 4):
            model.box((x, 2.1, 0), (3.8, .7, 25), "oak")
        for x in (-15, 15):
            for z in (-11, 11):
                model.box((x, 15, z), (2.7, 26, 2.7), "darkwood", bevel=.3)
                model.box((x, 3.5, z), (3.8, 3, 3.8), "stone", bevel=.4)
                model.beam((x, 19, z), (x - math.copysign(7, x), 27, z), .85)
        for z in (-11, 11):
            model.box((0, 27, z), (33, 2, 2), "oak")
            model.beam((-16, 26, z), (0, 36, z), .8)
            model.beam((16, 26, z), (0, 36, z), .8)
        model.roof(37, 31, 28, 41)
        model.box((0, 8, -10), (27, 12, 1.5), "plaster")
        for x in (-12, 0, 12):
            model.box((x, 8, -8.8), (1, 12, 1), "darkwood")
        model.box((0, 11, -5), (25, 1.6, 5), "oak")
        for x in (-8, -3, 5): model.mug((x, 12, -5))
        model.bunting((-14, 25, 12), (14, 25, 12), 10)
        model.box((0, 31, 16), (9, 6.4, .9), "darkwood", bevel=.3)
        model.mug((0, 29, 17), 1.4)
    elif name in ("Oktoberfest_PretzelStand", "Oktoberfest_GingerbreadStand", "Oktoberfest_FoodStand"):
        model.box((0, 1, 0), (24, 2, 15), "darkwood", bevel=.35)
        for x in range(-10, 12, 4):
            model.box((x, 5.5, 6), (3.7, 7, 1), "oak", bevel=.18)
        model.box((0, 9.5, 5), (25.5, 1.5, 5), "oak", bevel=.3)
        for x in (-10, 10):
            model.box((x, 13.5, -5), (1.8, 24, 1.8), "darkwood", bevel=.2)
            model.box((x, 12.5, 5), (1.6, 23, 1.6), "darkwood", bevel=.2)
            model.beam((x, 19, 5), (x * .55, 23, 5), .55)
        model.roof(25, 19, 23, 29, "red" if name.endswith("GingerbreadStand") else "darkwood" if name.endswith("FoodStand") else "blue")
        model.box((0, 20, -5), (20, 1, 1), "oak")
        if name.endswith("PretzelStand"):
            for x in (-7, 0, 7):
                model.beam((x, 23, 10), (x, 20, 10), .12, "rope")
                model.pretzel((x, 17.7, 10), 1.6)
            for x in (-7, -2, 4): model.pretzel((x, 11, 5.5), .8)
        elif name.endswith("GingerbreadStand"):
            for x in (-6, 0, 6):
                model.beam((x, 24, 10), (x, 21, 10), .12, "rope")
                model.heart((x, 18, 10), 1.2)
            for x in (-5, 4): model.heart((x, 12, 5.8), .7)
        else:
            model.box((0, 11, 4.5), (12, 1, 4), "metal")
            for x in (-4,-2,0,2,4): model.beam((x, 12, 3), (x+.5,12,6), .65, "bread", 7)
            model.box((-7, 14, -2), (4, 5, 4), "terracotta", bevel=.5)
            model.box((6, 12, 5), (4, 2.5, 4), "oak", bevel=.2)
            model.mug((6, 13.5, 5), .8)
        model.bunting((-10, 7.5, 7), (10, 7.5, 7), 7)
    elif name == "Oktoberfest_BeerGarden":
        for x in (-10, 10):
            model.beam((x, 0, -3.5), (x, 9, -1.4), .8)
            model.beam((x, 0, 3.5), (x, 9, 1.4), .8)
        model.beam((-11, 3, 0), (11, 3, 0), .7)
        for z in (-2.7, 0, 2.7): model.box((0, 9, z), (28, 1.3, 2.55), "oak", bevel=.25)
        for z in (-8, 8):
            for x in (-10, 10): model.box((x, 2.7, z), (2.2, 5.4, 3.2), "darkwood", bevel=.2)
            model.box((0, 5.6, z), (29, 1.2, 4.2), "oak", bevel=.3)
        for x, z in [(-7,-1), (6,1), (0,2)]: model.mug((x, 9.7, z), .7)
        model.pretzel((0, 11, 0), .7)
    elif name == "Oktoberfest_FestivalArch":
        for x in (-15, 15):
            model.box((x, 1.5, 0), (6, 3, 6), "stone", bevel=.6)
            model.box((x, 16, 0), (3, 29, 3), "darkwood", bevel=.3)
            for y in (6, 15, 25): model.box((x, y, 0), (3.6, 1, 3.6), "metal", bevel=.1)
        model.box((0, 30, 0), (37, 3, 3), "oak", bevel=.3)
        model.beam((-15, 23, 0), (-8, 30, 0), .85)
        model.beam((15, 23, 0), (8, 30, 0), .85)
        model.box((0, 29.5, 2.2), (11, 8, 1), "darkwood", bevel=.4)
        model.pretzel((0, 29, 3.1), 2.4)
        model.bunting((-14, 26, 0), (14, 26, 0), 12)
        for x in (-18, 18):
            model.box((x, 4, 0), (5, 5, 5), "terracotta", bevel=.7)
            for dx, dz in [(-1,-1),(1,1),(-1,1),(1,-1)]:
                model.beam((x+dx,5,dz), (x+dx*1.8,9,dz*1.8), .9, "leaf", 5)
    elif name == "Oktoberfest_Festzelt":
        model.box((0, 1, 0), (68, 2, 78), "darkwood", bevel=.5)
        for x in (-30,30):
            for z in (-34,-17,0,17,34):
                model.box((x,17,z),(2.6,32,2.6),"darkwood",bevel=.3)
                model.beam((x,26,z),(x*.7,33,z),.7)
            model.box((x,12,-5),(1.2,20,66),"ivory")
        model.roof(66,84,32,48,"ivory")
        for z in (-35,-17,0,17,35):
            model.beam((-31,29,z),(0,43,z),.65)
            model.beam((31,29,z),(0,43,z),.65)
        for x in (-24,24):
            model.box((x,16,39),(17,29,1.5),"plaster")
            model.box((x,10,40),(18,1.5,2),"darkwood")
            model.garland((x-8,29,41),(x+8,29,41),3)
        # A clock-tower-inspired entrance, with an original pretzel crest.
        for x in (-9,9): model.box((x,22,41),(2.6,42,2.6),"darkwood",bevel=.3)
        model.box((0,38,41),(21,10,3),"blue",bevel=.4)
        model.pretzel((0,37,43),2.7)
        model.box((0,45,41),(25,2,8),"oak",bevel=.3)
        model.beam((-12,46,38),(0,57,41),1)
        model.beam((12,46,38),(0,57,41),1)
        model.face([(-13,46,36),(0,58,40),(0,58,46),(-13,46,46)],"blue")
        model.face([(0,58,40),(13,46,36),(13,46,46),(0,58,46)],"blue")
        model.garland((-8,32,43),(8,32,43),3)
        for x in (-15,15):
            for z in (-25,-5,15):
                model.box((x,8,z),(10,1.2,15),"oak")
                for dx in (-7,7):
                    model.box((x+dx,4.5,z),(3,1,16),"oak")
                    for dz in (-5,5): model.box((x+dx,2,z+dz),(2,4,2),"darkwood")
                for dz in (-5,5): model.box((x,4,z+dz),(2,8,2),"darkwood")
        for x in (-6,6): model.lantern((x,26,43),1.2)
        model.bunting((-30,31,43),(-10,31,43),6)
        model.bunting((10,31,43),(30,31,43),6)
    elif name == "Oktoberfest_Maypole":
        model.box((0,1,0),(7,2,7),"stone",bevel=.6)
        for y in range(2,39,3): model.beam((0,y,0),(0,y+3,0),.85,"blue" if y % 2 else "ivory",8)
        for y,radius in [(28,6),(36,4)]:
            points = [(math.cos(i*math.tau/32)*radius,y+math.sin(i*math.tau/32)*radius,0) for i in range(32)]
            model.tube(points,.8,"leaf",closed=True)
            for x in (-radius, radius): model.beam((x,y,0),(x,y-8,0),.18,"red",4)
        for y in (13,20):
            model.beam((-7,y,0),(7,y,0),.35)
            for x in (-6,6): model.heart((x,y-2,0),.7)
        model.pretzel((0,38,1),1.2)
    elif name == "Oktoberfest_BarrelWagon":
        model.box((0,5,0),(21,2,12),"darkwood",bevel=.3)
        for x in (-8,8):
            model.beam((x,3,-8),(x,3,8),.5,"metal")
            for z in (-7,7):
                rim = [(x+3*math.cos(i*math.tau/24),3+3*math.sin(i*math.tau/24),z) for i in range(24)]
                model.tube(rim,.4,"darkwood",closed=True)
                for i in range(8): model.beam((x,3,z),rim[i*3],.2,"oak",4)
        for x in (-6,0,6): model.keg((x,6,0),2.6,6)
        model.beam((10,5,0),(19,2,0),.4)
        for z in (-5,5): model.box((0,8,z),(22,1,1),"oak")
        model.garland((-9,9,6),(9,9,6),2)
    elif name == "Oktoberfest_Bandstand":
        model.box((0,2,0),(31,4,23),"darkwood",bevel=.5)
        for z,y in [(14,.7),(12,2)]: model.box((0,y,z),(17,1.4,3),"oak")
        for x in (-13,13):
            for z in (-9,9): model.box((x,15,z),(2,24,2),"darkwood",bevel=.2)
        model.roof(32,27,26,35,"red")
        model.garland((-13,25,11),(13,25,11),3)
        for x in (-9,9): model.lantern((x,19,11))
        # Static bass drum and brass bell, not animated musicians.
        model.beam((0,8,-4),(0,8,0),3.5,"ivory",12)
        model.beam((0,8,-4.2),(0,8,-3.8),3.65,"metal",12)
        model.beam((0,8,-.2),(0,8,.2),3.65,"metal",12)
        model.beam((7,5,-1),(7,13,-1),1.2,"amber",8)
        model.beam((7,12,-1),(7,13,-1),2.5,"amber",10)
        model.box((-7,8,-2),(5,1,4),"oak")
        model.beam((-7,4,-2),(-7,8,-2),.4,"metal")
    else:
        raise ValueError("Unknown original model")
    if name in ("Oktoberfest_PretzelStand", "Oktoberfest_GingerbreadStand", "Oktoberfest_FoodStand"):
        model.garland((-10,23,10),(10,23,10),1.2)
        for x in (-11,11): model.lantern((x,19,8),.7)
        for x in range(-8,9,4): model.box((x,3.3,6.7),(2.6,2,.25),"blue" if name.endswith("PretzelStand") else "red",bevel=.1)
        if name.endswith("FoodStand"):
            model.box((7,27,-3),(3.5,11,3.5),"stone",bevel=.3)
            model.box((7,32,-3),(5,1,5),"metal")
        elif name.endswith("GingerbreadStand"):
            model.heart((0,29,10),1.8)
    elif name == "Oktoberfest_BrewersPavilion":
        model.garland((-14,27,13),(14,27,13),2)
        for x in (-12,12): model.lantern((x,21,13),1.1)
        for x in (-9,9): model.keg((x,2.5,-8),2.3,5)
        model.box((0,1,16),(19,2,5),"oak",bevel=.3)
    elif name == "Oktoberfest_FestivalArch":
        model.garland((-15,29,2),(15,29,2),3)
        for x in (-12,12): model.lantern((x,21,2))
    elif name == "Oktoberfest_BeerGarden":
        model.box((0,10.1,0),(5,.15,7),"ivory",bevel=.01)
        model.lantern((8,11,0),.6)
    return model


def collision_boxes(name):
    """Coarse solid proxies; doorways stay open, hanging decor is nonblocking."""
    if name == "Oktoberfest_BrewersPavilion":
        return [((x,15,z),(3.8,30,3.8)) for x in (-15,15) for z in (-11,11)] + [((0,6,-7),(27,12,7))]
    if name in ("Oktoberfest_PretzelStand","Oktoberfest_GingerbreadStand","Oktoberfest_FoodStand"):
        return [((0,5,4),(24,10,6))] + [((x,13,-5),(2,26,2)) for x in (-10,10)]
    if name == "Oktoberfest_BeerGarden":
        return [((0,5,0),(28,10,8))] + [((0,3,z),(29,6,4.2)) for z in (-8,8)]
    if name == "Oktoberfest_FestivalArch":
        return [((x,16,0),(6,32,6)) for x in (-15,15)] + [((x,4,0),(5,8,5)) for x in (-18,18)]
    if name == "Oktoberfest_Festzelt":
        return [((x,16,-5),(3,32,70)) for x in (-30,30)] + [((x,16,39),(18,32,4)) for x in (-24,24)] + [((x,4,z),(24,8,16)) for x in (-15,15) for z in (-25,-5,15)]
    if name == "Oktoberfest_Maypole": return [((0,20,0),(2,40,2))]
    if name == "Oktoberfest_BarrelWagon": return [((0,6,0),(22,12,15))]
    if name == "Oktoberfest_Bandstand": return [((0,2,0),(31,4,23))] + [((x,15,z),(2,30,2)) for x in (-13,13) for z in (-9,9)]
    raise ValueError("No collision proxy for model")


def glb(model, png):
    buffer = bytearray()
    views, accessors = [], []
    def append(raw):
        buffer.extend(b"\0" * (-len(buffer) % 4))
        views.append({"buffer": 0, "byteOffset": len(buffer), "byteLength": len(raw)})
        buffer.extend(raw)
        return len(views) - 1
    def accessor(values, width, component, kind):
        index = append(struct.pack(f'<{len(values)}{"f" if component == 5126 else "I"}', *values))
        views[index]["target"] = 34963 if kind == "SCALAR" else 34962
        entry = {"bufferView": index, "componentType": component, "count": len(values)//width, "type": kind}
        if kind == "VEC3":
            entry.update(min=[min(values[i::3]) for i in range(3)], max=[max(values[i::3]) for i in range(3)])
        accessors.append(entry)
        return len(accessors) - 1
    attributes = {name: accessor(values, width, 5126, kind) for name, values, width, kind in
                  [("POSITION", model.positions, 3, "VEC3"), ("NORMAL", model.normals, 3, "VEC3"),
                   ("TEXCOORD_0", model.uvs, 2, "VEC2"), ("COLOR_0", model.colors, 3, "VEC3")]}
    indices = accessor(model.indices, 1, 5125, "SCALAR")
    image_view = append(png)
    document = {"asset": {"version": "2.0", "generator": "FT Studio original Oktoberfest modeller"},
                "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"name": model.name, "mesh": 0}],
                "meshes": [{"primitives": [{"attributes": attributes, "indices": indices, "material": 0}]}],
                "materials": [{"name": "Original painted surfaces", "doubleSided": True,
                               "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0, "roughnessFactor": .9}}],
                "textures": [{"source": 0}], "images": [{"bufferView": image_view, "mimeType": "image/png"}],
                "buffers": [{"byteLength": len(buffer)}], "bufferViews": views, "accessors": accessors}
    encoded = json.dumps(document, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    buffer += b"\0" * (-len(buffer) % 4)
    return struct.pack("<III", 0x46546C67, 2, 28 + len(encoded) + len(buffer)) + struct.pack("<I4s", len(encoded), b"JSON") + encoded + struct.pack("<I4s", len(buffer), b"BIN\0") + buffer


def prepare_originals(out: Path) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    png = atlas()
    texture_name = hashlib.sha256(png).hexdigest()[:24] + ".png"
    (out / texture_name).write_bytes(png)
    assets = []
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Oktoberfest_Atlas.png", png)
        archive.writestr("Oktoberfest_Atlas.mtl", "newmtl OriginalSurfaces\nKd 1 1 1\nmap_Kd Oktoberfest_Atlas.png\n")
        for name, label in NAMES.items():
            model = build_model(name)
            part = {"positions": model.positions, "normals": model.normals, "uvs": model.uvs,
                    "uv1": [], "colors": model.colors, "indices": model.indices, "name": name,
                    "slot": 0, "albedo": texture_name, "lightmap": None}
            encoded = json.dumps([part], separators=(",", ":"))
            geometry = hashlib.sha256(encoded.encode()).hexdigest()[:24] + ".json"
            (out / geometry).write_text(encoded)
            archive.writestr(name + ".glb", glb(model, png))
            obj = ["mtllib Oktoberfest_Atlas.mtl", "usemtl OriginalSurfaces", "o " + name]
            for prefix, values, width in [("v", model.positions, 3), ("vt", model.uvs, 2), ("vn", model.normals, 3)]:
                for i in range(0, len(values), width):
                    row = values[i:i+width]
                    if prefix == "vt": row = [row[0], 1-row[1]]
                    obj.append(prefix + " " + " ".join(f"{v:.6g}" for v in row))
            for i in range(0, len(model.indices), 3):
                obj.append("f " + " ".join(f"{v+1}/{v+1}/{v+1}" for v in model.indices[i:i+3]))
            archive.writestr(name + ".obj", "\n".join(obj))
            assets.append({"file": PREFIX + name + ".glb", "name": label, "fixed": False,
                           "category": "original", "pose": "static", "geometry": geometry,
                           "vertices": len(model.positions)//3, "triangles": len(model.indices)//3,
                           "collisionBoxes": [{"center": center, "size": size} for center, size in collision_boxes(name)],
                           "submeshes": 1, "thumbnail": texture_name})
        archive.writestr("README.txt", "ORIGINAL OKTOBERFEST MODELS\n"
                         "Ten newly constructed meshes and an original procedural painted-style texture atlas.\n"
                         "No stock mesh or texture bytes are used. Y-up; coordinates use Studio-sized units.\n"
                         "GLB includes UVs, normals, face shading and embedded texture. OBJ/MTL uses the shared PNG.\n"
                         "Import GLB in Blender or another glTF editor to refine the models.\n"
                         "These are Studio/portable assets, NOT native Fantasy Tennis DATs.\n"
                         "Do not copy GLB/OBJ into Res. Studio stage ZIP export builds DAT/TEX and collision additions using private stock templates.\n"
                         "Native runtime compatibility remains unverified; use a separate backed-up test client.\n")
    with tempfile.NamedTemporaryFile(dir=out, delete=False) as temporary:
        temporary.write(packed.getvalue())
    Path(temporary.name).replace(out / "oktoberfest-original-models.zip")
    return assets
