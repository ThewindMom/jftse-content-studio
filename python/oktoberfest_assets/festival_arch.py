"""Heavy timber festival gate with an open central walking span."""

import math

from .common import bow, cloth, flowers, lantern, swag


def _plaque(model, center, size):
    x, y, z = center
    width, height = size
    points = [(x-width/2+.7, y+height/2, z), (x+width/2-.7, y+height/2, z),
              (x+width/2, y+height/2-.7, z), (x+width/2-.5, y-height/2, z),
              (x-width/2+.5, y-height/2, z), (x-width/2, y+height/2-.7, z)]
    cloth(model, points, "darkwood")


def _vine(model, x, side):
    path = []
    for index in range(8):
        y = 4.5 + index * 2.45
        path.append((x + side*.55*math.sin(index*1.7), y, 4.35))
    model.tube(path, .32, "leaf", sides=5)
    # Sparse hand-placed leaf shoots avoid the bead/blob look.
    for index in (1, 2, 4, 6):
        point = path[index]
        model.beam(point, (point[0]+side*(1.0 if index % 2 else -.8),
                           point[1]+.6, point[2]+.15), .38, "leaf", 5)


def build(model):
    # Forty-unit silhouette, nine-unit depth, with a 25-unit clear opening.
    for x in (-16.3, 16.3):
        model.box((x, 1.0, 0), (7.0, 2.0, 8.8), "stone", bevel=.5)
        model.box((x, 12.7, 0), (3.5, 23.4, 3.8), "oak", bevel=.3)
        model.box((x, 4.4, 0), (4.1, .65, 4.5), "metal", bevel=.08)
        model.box((x, 15.2, 0), (4.0, .55, 4.4), "darkwood", bevel=.08)
        model.beam((x, 2.0, -2.3), (x, 23.6, -2.0), .44, "darkwood", 6)
        _vine(model, x, -1 if x < 0 else 1)

    # Segmented shallow curved lintel gives a stock low-poly arc.
    arc = []
    for index in range(9):
        x = -17.5 + index * 35 / 8
        y = 27.0 + 5.0 * (1 - (x/17.5)**2)
        arc.append((x, y, 0))
    for start, end in zip(arc, arc[1:]):
        model.beam(start, end, 1.35, "oak", sides=8)
        model.beam((start[0], start[1]-.65, -1.35),
                   (end[0], end[1]-.65, -1.35), .55, "darkwood", sides=6)
    model.beam((-16.3, 22.5, 0), (-11.5, 28.7, 0), .72, "darkwood", 6)
    model.beam((16.3, 22.5, 0), (11.5, 28.7, 0), .72, "darkwood", 6)

    # Crest and readable hanging beer sign occupy overhead space only.
    _plaque(model, (0, 30.2, 1.55), (11.5, 5.4))
    model.pretzel((0, 29.6, 1.85), 1.65)
    model.beam((-3.2, 27.7, 1.2), (-3.2, 23.3, 1.2), .1, "rope", 4)
    model.beam((3.2, 27.7, 1.2), (3.2, 23.3, 1.2), .1, "rope", 4)
    _plaque(model, (0, 21.8, 1.4), (8.5, 4.1))
    model.mug((0, 20.3, 1.72), .62)

    swag(model, (-14.8, 28.0, 1.55), (-5.4, 30.5, 1.55), 2.0, 1.15)
    swag(model, (5.4, 30.5, 1.55), (14.8, 28.0, 1.55), 2.0, 1.15)
    for x in (-15.3, 15.3):
        bow(model, (x, 27.5, 1.7), .85)
        model.beam((x, 26.5, 2.0), (x + (-2 if x < 0 else 2), 23.2, 3.3), .1, "rope", 4)
        lantern(model, (x + (-2.2 if x < 0 else 2.2), 21.1, 3.35), .7)

    # Barrel flower planters sit outside the posts, never in the walkway.
    for x in (-19.0, 19.0):
        model.keg((x, 0, .2), 2.45, 5.2)
        flowers(model, (x, 5.25, 1.1), .75)
        model.beam((x-.9, 4.7, 0), (x-1.8, 7.2, .5), .45, "leaf", 5)
        model.beam((x+.8, 4.7, 0), (x+1.5, 6.7, -.3), .42, "leaf", 5)


def collision_boxes():
    return [((-16.3, 12.7, 0), (7.0, 25.4, 8.8)),
            ((16.3, 12.7, 0), (7.0, 25.4, 8.8)),
            ((-19.0, 2.6, .2), (5.0, 5.2, 5.0)),
            ((19.0, 2.6, .2), (5.0, 5.2, 5.0))]
