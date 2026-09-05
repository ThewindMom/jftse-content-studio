"""Small geometry motifs shared by the independent asset builders."""

import math


def _mix(a, b, t):
    return tuple(x * (1 - t) + y * t for x, y in zip(a, b))


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def cloth(model, points, material="blue"):
    """Emit a polygonal cloth patch with visible front and back faces."""
    if len(points) < 3:
        return
    model.face(points, material)
    model.face(list(reversed(points)), material)


def diamond_panel(model, surface, columns=6, rows=4):
    """Tile a parametric surface in alternating Bavarian diamonds."""
    for row in range(rows):
        for column in range(columns):
            u0, u1 = column / columns, (column + 1) / columns
            v0, v1 = row / rows, (row + 1) / rows
            um, vm = (u0 + u1) / 2, (v0 + v1) / 2
            corners = [surface(u0, v0), surface(u1, v0), surface(u1, v1), surface(u0, v1)]
            mids = [surface(um,v0),surface(u1,vm),surface(um,v1),surface(u0,vm)]
            center = surface(um, vm)
            for index in range(4):
                cloth(model, [center,mids[index],mids[(index+1)%4]],"blue")
                cloth(model, [mids[index],corners[(index+1)%4],mids[(index+1)%4]],"ivory")


def swag(model, start, end, sag=2, width=1):
    """A broad, gently folded two-sided fabric garland."""
    top = []
    lower = []
    for index in range(9):
        t = index / 8
        point = _mix(start, end, t)
        drop = sag * math.sin(math.pi * t)
        ripple = .12 * width * math.sin(t * math.pi * 4)
        top.append(_add(point, (0, -drop + ripple, 0)))
        lower.append(_add(point, (0, -drop - width, .08)))
    for index in range(8):
        cloth(model, [top[index], top[index + 1], lower[index + 1], lower[index]], "blue")
        inner = [_add(p,(0,width*.25,.1)) for p in (top[index],top[index+1])]
        cloth(model,[inner[0],inner[1],_add(inner[1],(0,-width*.6,.1)),
                     _add(inner[0],(0,-width*.6,.1))],"ivory")


def bow(model, center, scale=1):
    x, y, z = center
    cloth(model, [(x, y, z), (x - 2.0*scale, y + .8*scale, z),
                  (x - 1.65*scale, y - .8*scale, z), (x, y - .2*scale, z)], "blue")
    cloth(model, [(x, y, z), (x + 2.0*scale, y + .8*scale, z),
                  (x + 1.65*scale, y - .8*scale, z), (x, y - .2*scale, z)], "ivory")
    cloth(model, [(x - .35*scale, y - .2*scale, z), (x, y - 2.1*scale, z + .08),
                  (x + .55*scale, y - .35*scale, z)], "blue")
    model.box(center, (.8*scale, .8*scale, .35*scale), "ivory", bevel=.1*scale)


def flowers(model, center, scale=1):
    """Compact edelweiss cluster made from inexpensive faceted beams."""
    for offset in (-1, 0, 1):
        flower = _add(center, (offset * .75*scale, abs(offset) * .18*scale, 0))
        for angle in range(0, 360, 72):
            radians = math.radians(angle)
            tip = _add(flower, (math.cos(radians)*.55*scale, math.sin(radians)*.55*scale, .04))
            model.beam(flower, tip, .18*scale, "ivory", 5)
        model.box(_add(flower, (0, 0, .1)), (.25*scale, .25*scale, .2*scale), "amber", bevel=.05)
    model.beam(_add(center, (-1.1*scale, -.4*scale, -.1)), _add(center, (1.1*scale, .35*scale, -.1)), .3*scale, "leaf", 5)


def lantern(model, center, scale=1):
    model.lantern(center, scale)


def mug(model, center, scale=1):
    model.mug(center, scale)


def barrel(model, center, radius=3, height=6):
    model.keg(center, radius, height)
