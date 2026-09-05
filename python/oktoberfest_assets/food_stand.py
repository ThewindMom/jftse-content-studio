"""Harvest grill stall, built as a warm, irregular timber market prop."""

import math

from .common import bow, diamond_panel, flowers, lantern, swag


def _sausage(model, center, scale=1, vertical=False):
    x, y, z = center
    if vertical:
        path = [(x + math.sin(i * math.pi / 6) * .22*scale, y + i*.55*scale, z) for i in range(7)]
    else:
        path = [(x + i*.55*scale, y + math.sin(i * math.pi / 6)*.18*scale, z) for i in range(-3, 4)]
    model.tube(path, .32*scale, "ginger", sides=6)


def build(model):
    # Grounded cabinet and deliberately varied stock-like planks.
    model.box((0, 3.1, 0), (22, 6.2, 13), "darkwood", bevel=.28)
    for x, width, material in [(-8.8, 3.3, "oak"), (-5.4, 3.0, "oak"), (-2.1, 3.4, "darkwood"),
                               (1.4, 3.2, "oak"), (4.8, 3.5, "oak"), (8.5, 3.1, "darkwood")]:
        model.box((x, 3.5, 6.58), (width, 5.5, .42), material, bevel=.1)
    model.box((0, 6.8, .4), (24, 1.1, 14.5), "oak", bevel=.3)
    for x in (-10.5, 10.5):
        model.box((x, 1.0, 0), (2.2, 2, 13), "metal", bevel=.2)
        model.beam((x, 1, 0), (x, 23.7, 0), .72, "darkwood", 6)
        model.beam((x, 7, -5), (x, 16, -5), .52, "oak", 6)
    model.beam((-11, 21.5, 0), (11, 21.5, 0), .8, "darkwood", 6)
    model.beam((-10.5, 7, -5.2), (-10.5, 19, 5.2), .45, "oak", 6)
    model.beam((10.5, 7, -5.2), (10.5, 19, 5.2), .45, "oak", 6)

    # Draped checked canopy, open beneath on both front and rear.
    def canopy(u, v):
        x = -13 + 26*u
        z = -6.8 + 13.6*v
        y = 24.4 - 2.2*math.sin(math.pi*u) + .35*math.cos(math.pi*2*v)
        return (x, y, z)
    diamond_panel(model, canopy, 8, 4)
    swag(model, (-12.5, 21.8, 6.95), (12.5, 21.8, 6.95), 1.5, 1.1)
    for x in (-11.5, 11.5):
        bow(model, (x, 22.1, 7.08), .8)
        lantern(model, (x*1.14, 17.2, 5.8), .72)

    # Grill and counter stock.
    model.box((0, 7.75, 2.8), (9.5, 1.0, 6.0), "metal", bevel=.25)
    for x in (-3, 0, 3):
        _sausage(model, (x, 8.5, 4.4), .8)
    model.box((7.0, 8.0, 3.8), (4.2, .45, 3.5), "oak", bevel=.16)
    _sausage(model, (6.2, 8.45, 4.8), .55)
    _sausage(model, (7.2, 8.45, 3.8), .55)
    for x, material in [(-7.8, "amber"), (-6.2, "red")]:
        model.beam((x, 7.4, 4.4), (x, 10.0, 4.4), .42, material, 6)
        model.box((x, 10.2, 4.4), (.35, .55, .35), material, bevel=.05)

    # Food hangs from hooks and cord rather than floating in the opening.
    model.beam((-5.5, 18.0, 2.3), (5.5, 18.0, 2.3), .28, "darkwood", 6)
    for x, drop in [(-3.5, 1.0), (0, 1.8), (3.4, .7)]:
        model.beam((x, 18, 2.3), (x, 16.8-drop, 2.3), .08, "metal", 4)
        _sausage(model, (x, 13.7-drop, 2.3), .85, True)
    swag(model, (-9.5, 5.8, 6.86), (9.5, 5.8, 6.86), 1.3, .8)
    for x in (-6, 0, 6):
        flowers(model, (x, 5.0, 7.05), .65)


def collision_boxes():
    return [((0, 3.4, 0), (22, 6.8, 13)), ((-10.5, 14.5, 0), (2, 15, 2)),
            ((10.5, 14.5, 0), (2, 15, 2))]
