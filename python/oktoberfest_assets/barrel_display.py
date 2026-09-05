"""Independent keg, tap, and serving-counter festival display."""

import math

from .common import bow, cloth, flowers, mug, swag


def _horizontal_keg(model, center, radius, length):
    """A low-sided stave barrel facing +Z, including end caps and hoops."""
    cx, cy, cz = center
    rings = [(-length/2, radius*.82), (-length*.32, radius),
             (length*.32, radius), (length/2, radius*.82)]
    sides = 12
    points = []
    for z, r in rings:
        points.append([(cx+r*math.cos(i*math.tau/sides), cy+r*math.sin(i*math.tau/sides), cz+z)
                       for i in range(sides)])
    for section in range(3):
        for i in range(sides):
            j = (i+1) % sides
            model.face([points[section][i], points[section][j],
                        points[section+1][j], points[section+1][i]],
                       "darkwood" if i % 4 == 0 else "oak")
    for ring, reverse in ((points[0], True), (points[-1], False)):
        cap = (cx, cy, sum(p[2] for p in ring)/sides)
        for i in range(sides):
            tri = [cap, ring[i], ring[(i+1) % sides]]
            model.face(tri[::-1] if reverse else tri, "oak")
    for z in (-length*.32, length*.32):
        model.beam((cx, cy, cz+z-.16), (cx, cy, cz+z+.16), radius*1.04, "metal", sides)


def build(model):
    # Grounded timber counter and short feet.
    model.box((0, 3.0, 0), (21, 6, 12), "darkwood", bevel=.28)
    for x in (-8.2, -4.8, -1.2, 2.5, 6.0, 8.6):
        model.box((x, 3.25, 6.15), (3.0, 5.0, .45), "oak" if x != -1.2 else "darkwood", bevel=.1)
    model.box((0, 6.45, .2), (23, .9, 13.2), "oak", bevel=.25)
    for x in (-9.4, 9.4):
        model.box((x, .65, 0), (2.0, 1.3, 11), "metal", bevel=.18)

    # Rear upright keg and two properly cradled horizontal barrels.
    model.keg((-6.2, 6.9, -2.6), 3.7, 11.0)
    for x in (1.2, 7.6):
        model.box((x, 8.0, -2.7), (1.1, 2.6, 5.2), "darkwood", bevel=.15)
    _horizontal_keg(model, (4.4, 13.0, -2.7), 4.8, 4.8)
    model.box((-5.5, 7.5, 1.6), (6.3, 2.0, 5.4), "darkwood", bevel=.22)
    _horizontal_keg(model, (-5.5, 10.3, 1.0), 3.0, 4.0)

    # Brass tap is attached to the forward end face of the large keg.
    model.beam((4.4, 12.4, -.25), (4.4, 12.4, 1.0), .25, "amber", 6)
    model.beam((4.4, 12.4, .8), (4.4, 11.0, .8), .18, "amber", 6)
    model.box((4.4, 10.85, .8), (.65, .3, .35), "metal", bevel=.06)
    for x in (-2.0, 1.0, 4.0):
        mug(model, (x, 6.95, 4.1), .7)

    # Barrel cloths, front swag and bows are explicitly two-sided.
    cloth(model, [(-9.5, 17.0, -1.4), (-6.0, 18.0, -1.1),
                  (-3.2, 15.2, -.7), (-5.2, 13.8, -.55), (-8.8, 14.7, -.65)], "blue")
    cloth(model, [(1.4, 17.0, 2.0), (5.2, 17.9, 2.0),
                  (8.3, 15.9, 1.3), (5.8, 14.0, 1.75), (2.4, 14.8, 1.8)], "ivory")
    swag(model, (-9.8, 5.5, 6.42), (9.8, 5.5, 6.42), 1.25, .85)
    for x in (-9.5, 9.5):
        bow(model, (x, 5.7, 6.65), .68)
    for center in [(-8.0, 18.2, -.8), (7.7, 17.4, -.8), (-8.4, 7.2, 5.9)]:
        flowers(model, center, .62)


def collision_boxes():
    return [((0, 3.25, 0), (23, 6.5, 13.2)),
            ((-6.2, 12.4, -2.6), (7.4, 11, 7.4)),
            ((4.4, 13, -2.7), (9.6, 9.6, 4.8)),
            ((-5.5, 10.3, 1), (6, 6, 4))]
