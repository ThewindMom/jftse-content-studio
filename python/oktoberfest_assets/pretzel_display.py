"""Counter display with woven bread basket and supported hanging pretzels."""

import math

from .common import cloth, flowers, swag


def _pretzel(model, center, scale):
    """Coarse display pretzel; broad facets replace the high-detail food motif."""
    knots = [(-1.2, .2), (-1.35, 1), (-.8, 1.5), (-.25, 1.2), (.7, -.65),
             (1.2, -.2), (.8, .5), (-.8, .5), (-1.2, -.2), (-.7, -.65),
             (.25, 1.2), (.8, 1.5), (1.35, 1), (1.2, .2), (.6, -.7),
             (0, -.85), (-.6, -.7)]
    x, y, z = center
    path = [(x+px*scale, y+py*scale, z + .08*scale*math.sin(index*.8))
            for index, (px, py) in enumerate(knots)]
    model.tube(path, .2*scale, "bread", sides=5, closed=True)
    cloth(model, [(x-.07*scale, y+.45*scale, z+.22*scale),
                  (x+.07*scale, y+.45*scale, z+.22*scale),
                  (x+.07*scale, y+.65*scale, z+.22*scale),
                  (x-.07*scale, y+.65*scale, z+.22*scale)], "icing")


def _basket(model, center):
    cx, cy, cz = center
    # Sparse structural weave reads at game distance without a mesh of tiny parts.
    for y, rx, rz in [(cy, 4.5, 2.5), (cy+1.0, 4.8, 2.8), (cy+2.0, 4.55, 2.6)]:
        path = [(cx+rx*math.cos(i*math.tau/16), y, cz+rz*math.sin(i*math.tau/16)) for i in range(17)]
        model.tube(path, .18, "darkwood", sides=5)
    for i in range(12):
        angle = i*math.tau/12
        model.beam((cx+4.25*math.cos(angle), cy, cz+2.25*math.sin(angle)),
                   (cx+4.45*math.cos(angle), cy+2.05, cz+2.5*math.sin(angle)),
                   .13, "oak", 5)
    handle = [(cx-4.0+i, cy+1.8+3.6*math.sin(math.pi*i/8), cz) for i in range(9)]
    model.tube(handle, .3, "darkwood", sides=6)


def build(model):
    model.box((0, 3.0, 0), (22, 6, 12), "darkwood", bevel=.28)
    for x in (-9, -6, -3, 0, 3, 6, 9):
        model.box((x, 3.35, 6.15), (2.7, 5.1, .44), "oak" if x % 6 else "darkwood", bevel=.1)
    model.box((0, 6.5, .15), (24, 1.0, 13.2), "oak", bevel=.27)
    for x in (-9.7, 9.7):
        model.box((x, .65, 0), (2.0, 1.3, 11.5), "metal", bevel=.18)

    # Rear-left woven basket; its contents sit against a real basket floor.
    model.box((-5.4, 7.15, -.8), (8.5, .5, 4.8), "oak", bevel=.18)
    _basket(model, (-5.4, 7.2, -.8))
    for x, y, z, scale in [(-7.5, 9.3, -.2, .62), (-5.5, 9.6, -.3, .65),
                            (-3.5, 9.25, -.15, .6)]:
        _pretzel(model, (x, y, z), scale)

    # Front-right bread crate with broad rails and a restrained bread arrangement.
    model.box((5.1, 7.4, 2.0), (9.3, .55, 5.4), "darkwood", bevel=.16)
    for x in (1.0, 9.2):
        model.box((x, 8.55, 2.0), (.55, 2.6, 5.4), "oak", bevel=.12)
    for z in (-.35, 4.35):
        model.box((5.1, 8.55, z), (8.7, 2.6, .5), "oak", bevel=.12)
    for x, y, z in [(3.0, 9.15, 2.0), (5.2, 9.25, 1.6), (7.4, 9.15, 2.1)]:
        _pretzel(model, (x, y, z), .62)

    # Peg stand: every hanging item has a visible rope to a solid crossbar.
    model.beam((2.0, 6.9, -3.0), (2.0, 20.0, -3.0), .55, "darkwood", 6)
    model.beam((-4.2, 18.9, -3.0), (8.2, 18.9, -3.0), .48, "oak", 6)
    model.beam((-1.5, 14.7, -2.9), (5.5, 14.7, -2.9), .38, "oak", 6)
    for x, bar_y, pretzel_y, scale in [(-2.3, 18.9, 15.4, 1.0), (6.4, 18.9, 15.3, 1.0),
                                       (2.0, 14.7, 11.7, .9)]:
        model.beam((x, bar_y, -2.8), (x, pretzel_y+1.65*scale, -2.8), .09, "rope", 4)
        _pretzel(model, (x, pretzel_y, -2.65), scale)

    # Checked cloth panels, front bunting, and flowers stay clear of collision.
    cloth(model, [(-9.6, 10.0, 1.55), (-4.5, 9.8, 1.7),
                  (-4.2, 7.4, 2.7), (-7.0, 6.8, 3.0), (-9.7, 7.7, 2.5)], "blue")
    cloth(model, [(1.0, 9.8, 4.65), (9.2, 9.8, 4.65),
                  (8.4, 7.6, 5.0), (5.0, 7.0, 5.15), (1.2, 7.8, 5.0)], "ivory")
    swag(model, (-9.8, 5.6, 6.42), (9.8, 5.6, 6.42), 1.3, .8)
    for x in (-9.5, 0, 9.5):
        flowers(model, (x, 5.0, 6.65), .6)


def collision_boxes():
    return [((0, 3.25, 0), (24, 6.5, 13.2)),
            ((-5.4, 8.25, -.8), (9.6, 2.6, 5.6)),
            ((5.1, 8.55, 2), (9.3, 2.6, 5.4)),
            ((2, 13.4, -3), (1.2, 13.2, 1.2))]
