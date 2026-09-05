"""Draped gingerbread-heart stall with independently suspended cookies."""

import math

from .common import bow, diamond_panel, flowers, lantern, swag


def _hanging_heart(model, center, scale, ribbon_material):
    x, y, z = center
    top = y + 3.0*scale
    model.beam((x, 20.6, z), (x, top, z), .08, ribbon_material, 4)
    model.heart(center, scale)


def build(model):
    model.box((0, 3.0, 0), (23, 6, 13), "darkwood", bevel=.3)
    for x in (-9, -6, -3, 0, 3, 6, 9):
        model.box((x, 3.4, 6.58), (2.7, 5.1, .42), "oak" if x % 6 else "darkwood", bevel=.12)
    model.box((0, 6.65, .3), (24.5, 1.05, 14), "oak", bevel=.3)
    for x in (-10.7, 10.7):
        model.box((x, 1, 0), (2.1, 2, 12.5), "metal", bevel=.22)
        model.beam((x, 1, 0), (x, 24, 0), .75, "darkwood", 6)
    model.beam((-11, 21.6, 0), (11, 21.6, 0), .78, "darkwood", 6)
    model.beam((-10, 1.2, 6.75), (-3, 6.0, 6.75), .35, "darkwood", 5)
    model.beam((10, 1.2, 6.75), (3, 6.0, 6.75), .35, "darkwood", 5)

    def canopy(u, v):
        x = -13.2 + 26.4*u
        z = -6.7 + 13.4*v
        y = 24.7 - 3.0*math.sin(math.pi*u) + .25*math.cos(math.pi*2*v)
        return (x, y, z)
    diamond_panel(model, canopy, 8, 4)
    swag(model, (-12.5, 22.0, 6.95), (12.5, 22.0, 6.95), 2.5, 1.0)
    for x in (-11.5, 11.5):
        bow(model, (x, 22.1, 7.1), .85)
        lantern(model, (x*1.14, 17.0, 5.8), .72)

    # Each cookie has a visible ribbon reaching the canopy rail.
    for x, y, scale, ribbon in [(-7.2, 14.4, 1.25, "ivory"), (-3.6, 15.2, 1.05, "blue"),
                                (0, 13.7, 1.4, "red"), (3.8, 15.0, 1.1, "ivory"),
                                (7.3, 14.1, 1.25, "blue")]:
        _hanging_heart(model, (x, y, 5.55), scale, ribbon)

    # Crest, counter baskets, and restrained floral trim.
    model.box((0, 25.2, 0), (7.0, 3.6, .7), "oak", bevel=.35)
    model.pretzel((0, 24.6, .55), .85)
    flowers(model, (0, 26.2, .75), .55)
    for x in (-8.2, 8.2):
        model.box((x, 8.1, 3.8), (4.1, 2.0, 4.2), "oak", bevel=.2)
    for x in (-9, -8, 7.5, 8.6):
        model.box((x, 9.55, 5.15), (1.25, 1.8, .35), "ginger", bevel=.17)
        model.box((x, 9.55, 5.36), (.65, .12, .08), "icing", bevel=.02)
    swag(model, (-9.7, 5.8, 6.88), (9.7, 5.8, 6.88), 1.4, .8)
    for x in (-6, 0, 6):
        flowers(model, (x, 5.0, 7.05), .62)


def collision_boxes():
    return [((0, 3.35, 0), (23, 6.7, 13)), ((-10.7, 14.8, 0), (2, 15.5, 2)),
            ((10.7, 14.8, 0), (2, 15.5, 2))]
