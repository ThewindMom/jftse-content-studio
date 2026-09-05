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
from oktoberfest_assets import (barrel_display, beer_garden, festival_arch,
                                food_stand, gingerbread_stand, maypole,
                                pretzel_display, pretzel_stand)
from oktoberfest_assets import festzelt


ASSET_BUILDERS = {
    "Oktoberfest_Festzelt": festzelt.build,
    "Oktoberfest_PretzelStand": pretzel_stand.build,
    "Oktoberfest_FoodStand": food_stand.build,
    "Oktoberfest_GingerbreadStand": gingerbread_stand.build,
    "Oktoberfest_BeerGarden": beer_garden.build,
    "Oktoberfest_Maypole": maypole.build,
    "Oktoberfest_FestivalArch": festival_arch.build,
    "Oktoberfest_BarrelDisplay": barrel_display.build,
    "Oktoberfest_PretzelDisplay": pretzel_display.build,
}

ASSET_COLLISIONS = {
    "Oktoberfest_Festzelt": festzelt.collision_boxes,
    "Oktoberfest_PretzelStand": pretzel_stand.collision_boxes,
    "Oktoberfest_FoodStand": food_stand.collision_boxes,
    "Oktoberfest_GingerbreadStand": gingerbread_stand.collision_boxes,
    "Oktoberfest_BeerGarden": beer_garden.collision_boxes,
    "Oktoberfest_Maypole": maypole.collision_boxes,
    "Oktoberfest_FestivalArch": festival_arch.collision_boxes,
    "Oktoberfest_BarrelDisplay": barrel_display.collision_boxes,
    "Oktoberfest_PretzelDisplay": pretzel_display.collision_boxes,
}

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
    "Oktoberfest_WelcomeMaypole": "Original · Small welcome maypole",
    "Oktoberfest_BarrelDisplay": "Original · Barrel display",
    "Oktoberfest_PretzelDisplay": "Original · Pretzel display",
    "Oktoberfest_BarrelWagon": "Original · Barrel wagon",
    "Oktoberfest_Bandstand": "Original · Brass bandstand",
    "Oktoberfest_HouseBanner": "Original · Pretzel house banner",
    "Oktoberfest_FlagLine": "Original · Lane pennants",
    "Oktoberfest_FlagPost": "Original · Welcome flag",
    "Oktoberfest_FountainGarland": "Original · Fountain rim garland",
    "Oktoberfest_FountainCrown": "Original · Fountain wreath & ribbons",
    "Oktoberfest_CourtCrest": "Original · Court-end pretzel crest",
    "Oktoberfest_CornerInlay": "Original · Blue-white corner inlay",
    "Oktoberfest_CourtRibbon": "Original · Court-side festival trim",
    "Oktoberfest_NetDressing": "Original · Fitted net tape & post ribbons",
    "Oktoberfest_JudgeDressing": "Original · Judge chair festival drapery",
    "Oktoberfest_CourtCorner": "Original · Low court-corner flower box",
    "Oktoberfest_Brewmaster": "Original · Brewmaster · raised stein pose",
    "Oktoberfest_Accordionist": "Original · Accordionist · seated pose",
    "Oktoberfest_PretzelBaker": "Original · Baker · serving pose",
    "Oktoberfest_FestivalChick": "Original · Festival chick · dressed pose",
}
MATERIALS = ["oak", "darkwood", "blue", "ivory", "bread", "icing", "ginger", "metal",
             "plaster", "leaf", "terracotta", "amber", "foam", "stone", "red", "rope"]
PALETTE = [(181, 118, 59), (90, 56, 32), (54, 111, 165), (232, 221, 177),
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
                brush = math.sin(x * .055 + math.sin(y * .022) * .7) * 9 if slot in (0, 1) else math.sin(x * .04 + y * .012) * 6
                edge = min(x, y, 127 - x, 127 - y)
                value = brush + randomizer.uniform(-1, 1) + min(edge, 18) * .7 - 9
                pixels[slot % 4 * 128 + x, slot // 4 * 128 + y] = tuple(max(0, min(255, int(v + value))) for v in color)
    draw = ImageDraw.Draw(image)
    for slot in (0, 1):
        ox, oy = slot % 4 * 128, slot // 4 * 128
        for x in (20, 63, 106):
            path = [(ox + x + math.sin(y * .025 + x) * 2, oy + y) for y in range(5, 124, 4)]
            draw.line(path, fill=tuple(int(c * .85) for c in PALETTE[slot]), width=1)
            draw.line([(px + 2, py) for px, py in path], fill=tuple(min(255, int(c * 1.12)) for c in PALETTE[slot]), width=1)
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

    def ellipsoid(self, center, radii, material):
        start = len(self.positions)
        rings = [[add(center,(radii[0]*math.sin(p)*math.cos(a),radii[1]*math.cos(p),radii[2]*math.sin(p)*math.sin(a)))
                  for a in [j*math.tau/12 for j in range(12)]]
                 for p in [i*math.pi/6 for i in range(1,6)]]
        for j in range(12):
            k = (j+1)%12
            self.face([add(center,(0,radii[1],0)),rings[0][k],rings[0][j]],material)
            for a,b in zip(rings,rings[1:]):
                self.face([a[j],a[k],b[k],b[j]],material)
            self.face([add(center,(0,-radii[1],0)),rings[-1][j],rings[-1][k]],material)
        for i in range(start,len(self.positions),3):
            normal = unit(tuple((self.positions[i+j]-center[j])/radii[j]**2 for j in range(3)))
            self.normals[i:i+3] = normal
            shade = .76+.22*max(0,sum(a*b for a,b in zip(normal,unit((-.5,1,.7)))))
            self.colors[i:i+3] = (shade,)*3

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
            for j in range(2):
                t = j / 2
                xy = [.5 * ((2 * b[k]) + (-a[k] + c[k]) * t + (2 * a[k] - 5 * b[k] + 4 * c[k] - d[k]) * t*t + (-a[k] + 3*b[k] - 3*c[k] + d[k]) * t*t*t) for k in range(2)]
                path.append(add(center, (xy[0] * scale, xy[1] * scale, math.sin(i * .6) * scale * .1)))
        self.tube(path, scale * .19, "bread", closed=True)
        for i in range(0, len(path), 5):
            center = add(path[i], (0, 0, scale * .2))
            self.face([add(center,(-scale*.05,-scale*.05,0)),
                       add(center,(scale*.05,-scale*.03,0)),
                       add(center,(0,scale*.08,0))], "icing")

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
    builder = ASSET_BUILDERS.get(name)
    if builder is not None:
        builder(model)
        return model
    if name in ("Oktoberfest_Brewmaster", "Oktoberfest_Accordionist", "Oktoberfest_PretzelBaker"):
        musician = name.endswith("Accordionist")
        baker = name.endswith("PretzelBaker")
        cloth = "red" if musician else "ivory" if baker else "leaf"
        for side in (-1,1):
            hip = (side*1.6,7.5,0)
            knee = (side*2,4,2 if musician else .4)
            foot = (side*2,1,3 if musician else 1)
            model.beam(hip,knee,1.45,"darkwood",10)
            model.beam(knee,foot,.8,"ivory",10)
            model.ellipsoid(add(foot,(0,-.25,.65)),(1.1,.75,1.8),"darkwood")
            model.box((side*1.6,6.5,1.2),(1.4,2,.3),"oak",bevel=.2)
        model.ellipsoid((0,11,0),(4,4.5,2.5),cloth)
        model.beam((-2.2,14.6,1.8),(-1.8,7.5,2),.3,"darkwood",6)
        model.beam((2.2,14.6,1.8),(1.8,7.5,2),.3,"darkwood",6)
        model.box((0,8.3,2.2),(4.4,.6,.35),"darkwood",bevel=.15)
        for y in (10,11.5,13): model.ellipsoid((0,y,2.5),(.18,.18,.12),"amber")
        model.ellipsoid((0,17,0),(2.9,3.1,2.4),"plaster")
        for x in (-1,1):
            model.ellipsoid((x,17.7,2.1),(.5,.55,.25),"ivory")
            model.ellipsoid((x,17.7,2.34),(.21,.3,.12),"darkwood")
            model.beam((x-.45,18.4,2),(x+.4,18.5,2),.13,"darkwood",6)
            model.ellipsoid((x*2.8,17,.1),(.45,.7,.5),"plaster")
        model.ellipsoid((0,16.7,2.45),(.6,.65,.6),"plaster")
        model.ellipsoid((0,15.8,2.3),(1.6,.4,.55),"darkwood")
        if not baker: model.ellipsoid((0,14.8,1.5),(1.7,1.5,.9),"darkwood")
        model.beam((0,19.4,0),(0,19.8,0),3.35,"darkwood",16)
        model.ellipsoid((0,20.3,0),(2.5,1.7,2),"leaf" if not musician else "red")
        model.beam((0,19.8,0),(0,20.2,0),2.52,"rope",16)
        model.tube([(-2.1,20,0),(-3,22,.2),(-3.5,24,.4)],.23,"ivory")
        for y in (21,22,23): model.beam((-2.5-(y-21)*.35,y,0),(-3.7-(y-21)*.15,y+.5,.2),.15,"ivory",5)
        hands = [(-4,10,3),(4,10,3)] if baker else [(-4,11,4),(4,11,4)] if musician else [(-4.7,9,1),(5.7,19.7,3)]
        for side,hand in zip((-1,1),hands):
            elbow = (side*5,12 if side<0 or musician or baker else 16,1.2)
            model.beam((side*3.1,13.3,0),elbow,1.15,cloth,10)
            model.beam(elbow,hand,.8,"plaster",10)
            model.ellipsoid(hand,(.9,.85,.9),"plaster")
        if musician:
            model.box((0,11,4),(7,4.5,2.8),"darkwood",bevel=.3)
            for x in range(-3,4): model.box((x,11,5.5),(.35,4,1),"red",bevel=.1)
            for y in (9.5,10.2,10.9,11.6,12.3): model.box((3.5,y,5.5),(.8,.45,.3),"ivory")
            model.beam((0,0,0),(0,7,0),.8,"oak",8)
            model.beam((0,6.5,0),(0,7,0),3,"oak",12)
        elif baker:
            model.box((0,9.5,4.5),(9,.55,4),"oak",bevel=.2)
            for x in (-2.7,0,2.7): model.pretzel((x,10.7,4.8),.75)
            model.box((0,10,2.3),(4.5,5,.2),"ivory",bevel=.1)
        else:
            model.mug((5.7,19.8,3),1.2)
    elif name == "Oktoberfest_FestivalChick":
        model.ellipsoid((0,4,0),(2.5,3,2.2),"amber")
        for x in (-.9,.9):
            model.ellipsoid((x,5,1.95),(.45,.55,.3),"ivory")
            model.ellipsoid((x,5,2.22),(.18,.26,.12),"darkwood")
            model.ellipsoid((x,1,.4),(.6,.5,.9),"bread")
        model.beam((0,4.3,2),(0,4.3,2.85),.45,"bread",3)
        model.ellipsoid((0,2.1,0),(2.25,1.4,1.95),"darkwood")
        for x in (-2.2,2.2): model.ellipsoid((x,3.8,.1),(.7,1.2,1),"amber")
        model.box((0,3.4,2),(1.9,1.9,.25),"oak",bevel=.15)
        for x in (-.8,.8):
            model.beam((x,4.7,1.8),(x,2.8,2.1),.14,"rope",6)
            model.ellipsoid((x,3.1,2.25),(.15,.15,.15),"amber")
        model.beam((0,6.6,0),(0,6.9,0),2.1,"leaf",16)
        model.ellipsoid((0,7.2,0),(1.5,1.1,1.35),"leaf")
        model.beam((0,6.9,0),(0,7.1,0),1.52,"rope",16)
        model.tube([(-1.4,7,0),(-2,8,.2),(-2.3,9,.3)],.18,"ivory")
    elif name == "Oktoberfest_JudgeDressing":
        # Measured chair footprint x72.49..102.03, z±15.9, height39.97.
        # Short valances expose the chair frame, steps and original canopy.
        for side in (-1,1):
            z=side*16.1
            for i in range(6):
                x0,x1=81+i*3,84+i*3
                bottom=22+abs(i-2.5)*.5
                points=[(x0,28,z),(x1,28,z),(x1,bottom,z),(x0,bottom,z)]
                model.face(points if side<0 else points[::-1],"ivory")
                model.box(((x0+x1)/2,27.2,z),(2.6,1.3,.12),"blue",bevel=.03)
            model.garland((81,28,z),(99,28,z),.7)
        model.box((102.3,27,0),(.18,10,12),"blue",bevel=.06)
        wreath=[(102.6,33+3.5*math.cos(i*math.tau/24),3.5*math.sin(i*math.tau/24)) for i in range(24)]
        model.tube(wreath,.65,"leaf",closed=True)
        for z in (-2,2):
            model.beam((102.6,30,z),(102.6,25,z*1.3),.3,"ivory",6)
    elif name == "Oktoberfest_CourtCorner":
        model.box((0,1.6,0),(18,3.2,5),"oak",bevel=.4)
        model.box((0,3.15,0),(16,.2,3.8),"ginger",bevel=.08)
        for x in (-7.5,7.5):model.box((x,1.5,0),(.5,3.2,5.2),"metal",bevel=.07)
        model.garland((-8,3,2.6),(8,3,2.6),1)
        for i in range(9):
            x=-7+i*1.7;y=4.7+(i%3)*.35;z=.7*math.sin(i*2)
            model.beam((x,3,z),(x,y,z),.07,"leaf",5)
            for j in range(5):
                a=j*math.tau/5
                model.ellipsoid((x+.5*math.cos(a),y+.4*math.sin(a),z),(.38,.32,.16),"ivory" if i%3 else "blue")
            model.ellipsoid((x,y,z+.15),(.2,.2,.13),"amber")
        for x in (-5,5):
            model.box((x,1.8,2.62),(2.5,2,.12),"blue",bevel=.05)
    elif name == "Oktoberfest_NetDressing":
        # Stock SV_Net00_A top edge: endpoints 9.70674, midpoint 8.33548.
        for i in range(30):
            x0,x1=-60+i*4,-60+(i+1)*4
            y0,y1=[8.33548+abs(x)/60*(9.70674-8.33548) for x in (x0,x1)]
            for z in (-.18,.18):
                points=[(x0,y0+.12,z),(x1,y1+.12,z),(x1,y1-1.4,z),(x0,y0-1.4,z)]
                model.face(points if z<0 else points[::-1],"ivory")
                mid=(x0+x1)/2
                ym=(y0+y1)/2
                diamond=[(mid,ym+.05,z*1.1),(x1-.2,ym-.64,z*1.1),(mid,ym-1.32,z*1.1),(x0+.2,ym-.64,z*1.1)]
                model.face(diamond if z<0 else diamond[::-1],"blue")
        for x in (-67,67):
            wreath=[(x+1.6*math.cos(i*math.tau/24),11+1.9*math.sin(i*math.tau/24),1.1) for i in range(24)]
            model.tube(wreath,.4,"leaf",closed=True)
            model.pretzel((x,10.5,1.65),.65)
            model.ellipsoid((x,12,1.4),(.65,.65,.3),"amber")
            for side in (-1,1):
                model.ellipsoid((x+side*1.2,12,1.35),(1.1,.55,.25),"blue" if side<0 else "ivory")
                points=[(x+side*.2,11.7,1.35),(x+side*1.1,7.4,1.4),
                        (x+side*.6,7.7,1.5),(x+side*.8,12,1.35)]
                model.face(points,"blue" if side<0 else "ivory")
                model.face(points[::-1],"blue" if side<0 else "ivory")
    elif name == "Oktoberfest_CornerInlay":
        # Flat L-shaped ornament outside the playing lines, not a raised decal.
        for yaw in (0,math.pi/2):
            for i in range(8):
                x=2+i*2.8
                def turn(px,pz,y=.08):
                    return (px*math.cos(yaw)-pz*math.sin(yaw),y,px*math.sin(yaw)+pz*math.cos(yaw))
                model.face([turn(x-1.35,-1.4),turn(x-1.35,1.4),turn(x+1.35,1.4),turn(x+1.35,-1.4)],"ivory")
                model.face([turn(x-1.15,0,.1),turn(x,1.05,.1),turn(x+1.15,0,.1),turn(x,-1.05,.1)],"blue")
        model.beam((0,0,0),(0,.1,0),1.5,"bread",12)
    elif name == "Oktoberfest_CourtCrest":
        model.pretzel((0,0,0),3.2)
        for i in range(0,len(model.positions),3):
            x,y,z = model.positions[i:i+3]
            model.positions[i:i+3] = [x,z+.7,-y]
            x,y,z = model.normals[i:i+3]
            model.normals[i:i+3] = [x,z,-y]
        model.beam((0,0,0),(0,.2,0),8.5,"ivory",32)
        for i in range(16):
            a,b = i*math.tau/16,(i+1)*math.tau/16
            model.face([(r*math.cos(t),.25,r*math.sin(t)) for r,t in [(7,b),(8.4,b),(8.4,a),(7,a)]],"blue" if i%2 else "ivory")
    elif name == "Oktoberfest_FountainCrown":
        for i in range(12):
            a,b = i*math.tau/12,(i+1)*math.tau/12
            start,end = [(17*math.cos(t),0,17*math.sin(t)) for t in (a,b)]
            model.garland(start,end,.6)
            if i%3 == 0:
                model.lantern(add(start,(0,-3,0)),1.2)
                for delta,color in [(-1,"blue"),(1,"ivory")]:
                    x,y,z=start
                    points=[(x+delta,y,z),(x+delta-1,y-11,z+2),(x+delta+1,y-10,z+3),(x+delta+1,y,z)]
                    model.face(points,color)
                    model.face(points[::-1],color)
    elif name == "Oktoberfest_CourtRibbon":
        for x in (-15,15):
            model.beam((x,0,0),(x,8,0),.45,"oak")
            model.beam((x,7.5,0),(x,8.5,0),.7,"metal")
        model.garland((-15,8,0),(15,8,0),1)
        model.bunting((-15,7,0),(15,7,0),10)
    elif name == "Oktoberfest_HouseBanner":
        model.beam((-7, 0, 0), (7, 0, 0), .5, "metal")
        for x in (-6, 6): model.beam((x, 0, -3), (x, 0, 0), .4, "metal")
        for i in range(8):
            x0, x1 = -6 + i * 1.5, -4.5 + i * 1.5
            z0, z1 = math.sin(i * math.pi / 4) * .5, math.sin((i+1) * math.pi / 4) * .5
            panel = [(x0,0,z0),(x0,-20+abs(x0)*.5,z0),(x1,-20+abs(x1)*.5,z1),(x1,0,z1)]
            model.face(panel, "blue" if i in (0,1,6,7) else "ivory")
            model.face(panel[::-1], "blue" if i in (0,1,6,7) else "ivory")
        model.pretzel((0,-8,1), 2.1)
        model.garland((-7,1,0),(7,1,0),1)
    elif name == "Oktoberfest_FlagLine":
        for x in (-30,30):
            model.beam((x,0,0),(x,38,0),.55,"darkwood")
            model.beam((x,36,0),(x,39,0),.8,"metal")
            model.lantern((x,30,0),.9)
        model.bunting((-30,36,0),(30,36,0),14)
        model.garland((-30,37,0),(30,37,0),3)
    elif name == "Oktoberfest_FlagPost":
        model.beam((0,0,0),(0,47,0),.7,"darkwood")
        model.beam((0,45,0),(0,49,0),1,"metal")
        model.beam((0,44,0),(12,44,0),.4,"metal")
        for i in range(6):
            x0,x1 = i*2,(i+1)*2
            z0,z1 = math.sin(i*.8),math.sin((i+1)*.8)
            panel = [(x0,44,z0),(x0,24+abs(x0-6)*.4,z0),(x1,24+abs(x1-6)*.4,z1),(x1,44,z1)]
            for points in (panel,panel[::-1]): model.face(points,"blue" if i%2 else "ivory")
        model.pretzel((6,35,1.5),1.5)
        model.garland((0,43,0),(12,43,0),1)
    elif name == "Oktoberfest_FountainGarland":
        # Rim radius measured from the stock basin; local origin is its center.
        for i in range(16):
            a,b = i*math.tau/16,(i+1)*math.tau/16
            start,end = [(54*math.cos(t),0,54*math.sin(t)) for t in (a,b)]
            model.garland(start,end,1.5)
            model.bunting(add(start,(0,-1,0)),add(end,(0,-1,0)),4)
            if i%4 == 0: model.lantern(add(start,(0,-3,0)),.9)
    elif name == "Oktoberfest_BrewersPavilion":
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
    elif name == "Oktoberfest_WelcomeMaypole":
        model.box((0,1,0),(7,2,7),"stone",bevel=.6)
        model.beam((0,2,0),(0,30,0),.85,"ivory",12)
        for i in range(108):
            a,b=i*math.tau/32,(i+1)*math.tau/32
            y=2+i*.24
            model.face([(.87*math.cos(a),y,.87*math.sin(a)),(.87*math.cos(b),y+.24,.87*math.sin(b)),
                        (.87*math.cos(b),y+2.64,.87*math.sin(b)),(.87*math.cos(a),y+2.4,.87*math.sin(a))],"blue")
        for y,radius in [(26,4.5)]:
            points = [(math.cos(i*math.tau/32)*radius,y,math.sin(i*math.tau/32)*radius) for i in range(32)]
            model.tube(points,1.05,"leaf",closed=True)
            for i in range(6):
                a=i*math.tau/6
                x,z=radius*math.cos(a),radius*math.sin(a)
                model.beam((0,y+3,0),(x,y,z),.1,"rope",5)
                ribbon=[(x-.8,y,z),(x+.8,y,z),(x+1.3,y-8,z+1.1),(x-.3,y-9,z+1.2)]
                model.face(ribbon,"blue" if i%2 else "ivory")
                model.face(ribbon[::-1],"blue" if i%2 else "ivory")
        for y in (13,):
            model.beam((-7,y,0),(7,y,0),.35)
            for x in (-6,6): model.heart((x,y-2,0),.7)
        model.pretzel((0,29,1),1.2)
    elif name == "Oktoberfest_BarrelWagon":
        model.box((0,5,0),(21,2,12),"darkwood",bevel=.3)
        for x in (-8,8):
            model.beam((x,3,-8),(x,3,8),.5,"metal")
            for z in (-7,7):
                rim = [(x+3*math.cos(i*math.tau/24),3+3*math.sin(i*math.tau/24),z) for i in range(24)]
                model.tube(rim,.4,"darkwood",closed=True)
                for i in range(8): model.beam((x,3,z),rim[i*3],.2,"oak",4)
        for x in (-6,0,6): model.keg((x,6,0),2.6,6)
        for x in (-6,6):
            model.tube([(x,6,-5),(x,12,-2.5),(x,12,2.5),(x,6,5)],.18,"rope")
        model.beam((10,5,0),(19,2,0),.4)
        for z in (-5,5): model.box((0,8,z),(22,1,1),"oak")
        model.garland((-9,9,6),(9,9,6),2)
        model.box((-7,12.15,0),(5,.25,4),"ivory",bevel=.05)
        for x in (-8.5,-6.5): model.box((x,12.3,0),(.6,.08,4),"blue",bevel=.02)
        model.pretzel((0,7.6,6.6),1)
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
    if name == "Oktoberfest_BrewersPavilion":
        model.garland((-14,27,13),(14,27,13),2)
        for x in (-12,12): model.lantern((x,21,13),1.1)
        for x in (-9,9): model.keg((x,2.5,-8),2.3,5)
        model.box((0,1,16),(19,2,5),"oak",bevel=.3)
    return model


def collision_boxes(name):
    """Coarse solid proxies; doorways stay open, hanging decor is nonblocking."""
    collision_builder = ASSET_COLLISIONS.get(name)
    if collision_builder is not None:
        return collision_builder()
    if name in ("Oktoberfest_Brewmaster", "Oktoberfest_Accordionist", "Oktoberfest_PretzelBaker"):
        return [((0,8,0),(7,16,6))]
    if name == "Oktoberfest_FestivalChick":
        return [((0,3,0),(4,6,4))]
    if name in ("Oktoberfest_HouseBanner", "Oktoberfest_FountainGarland", "Oktoberfest_FountainCrown", "Oktoberfest_CourtCrest", "Oktoberfest_CornerInlay", "Oktoberfest_NetDressing", "Oktoberfest_JudgeDressing"):
        return []
    if name == "Oktoberfest_CourtCorner":
        return [((0,1.6,0),(18,3.2,5))]
    if name == "Oktoberfest_CourtRibbon":
        return [((x,4,0),(.9,8,.9)) for x in (-15,15)]
    if name == "Oktoberfest_FlagLine":
        return [((x,19,0),(1.1,38,1.1)) for x in (-30,30)]
    if name == "Oktoberfest_FlagPost":
        return [((0,24,0),(1.4,48,1.4))]
    if name == "Oktoberfest_BrewersPavilion":
        return [((x,15,z),(3.8,30,3.8)) for x in (-15,15) for z in (-11,11)] + [((0,6,-7),(27,12,7))]
    if name == "Oktoberfest_WelcomeMaypole": return [((0,15,0),(2,30,2))]
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
                         f"{len(NAMES)} newly constructed meshes and an original procedural painted-style texture atlas.\n"
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
