"""Long decorated beer-garden table with paired benches."""

from .common import cloth, flowers, mug


def _runner(model):
    # A broad crosswise runner, broken into purposeful blue/ivory cloth islands.
    for row in range(4):
        z0, z1 = -4.2 + row * 2.1, -2.1 + row * 2.1
        for column in range(2):
            x0, x1 = -2.3 + column * 2.3, column * 2.3
            cloth(model, [(x0, 8.72, z0), (x1, 8.72, z0),
                          (x1, 8.72, z1), (x0, 8.72, z1)],
                  "blue" if (row + column) % 2 else "ivory")
    for z, facing in ((-4.25, -1), (4.25, 1)):
        cloth(model, [(-2.3, 8.7, z), (2.3, 8.7, z),
                      (1.85, 6.65, z + facing*.14), (0, 6.0, z + facing*.2),
                      (-1.85, 6.65, z + facing*.14)], "blue" if facing < 0 else "ivory")


def build(model):
    # Three broad tabletop boards and slab benches retain the chunky stock silhouette.
    for z, material in [(-2.75, "oak"), (0, "darkwood"), (2.75, "oak")]:
        model.box((0, 8.25, z), (24, 1.0, 2.65), material, bevel=.22)
    for z in (-7.0, 7.0):
        model.box((0, 5.15, z), (25, .9, 2.5), "oak", bevel=.22)
        for x in (-8.0, 8.0):
            model.box((x, 2.7, z), (2.0, 4.9, 1.9), "darkwood", bevel=.18)

    # Heavy trestles and longitudinal stretcher, visibly joined rather than delicate.
    for x in (-8.0, 8.0):
        for z in (-1, 1):
            model.beam((x + z*2.7, .25, z*3.4), (x + z*.8, 7.9, z*2.0), .72, "darkwood", 6)
        model.beam((x, 1.35, -4.0), (x, 1.35, 4.0), .55, "oak", 6)
    model.beam((-9.0, 2.15, 0), (9.0, 2.15, 0), .62, "darkwood", 6)
    _runner(model)

    # Four steins leave the center arrangement readable.
    for x, z, scale in [(-7.7, -1.8, .8), (-6.2, 2.1, .72), (6.3, -2.0, .75), (7.8, 1.8, .82)]:
        mug(model, (x, 8.8, z), scale)

    # Low plate with two overlapping pretzels, grounded on the tabletop.
    model.beam((0, 8.76, 1.1), (0, 9.0, 1.1), 2.65, "darkwood", 12)
    model.pretzel((-1.0, 9.25, 1.45), .56)
    model.pretzel((1.0, 9.35, 1.25), .56)

    # Central jug, wheat fan, and restrained edelweiss spray.
    model.beam((0, 8.75, -1.0), (0, 10.8, -1.0), 1.05, "oak", 8)
    for index, x in enumerate((-1.25, -.7, 0, .7, 1.25)):
        end = (x, 13.1 - abs(index-2)*.25, -1.0 + .18*abs(index-2))
        model.beam((0, 10.5, -1.0), end, .09, "leaf", 5)
        model.beam(end, (end[0], end[1] + .65, end[2]), .2, "amber", 5)
    flowers(model, (0, 11.25, -.55), .58)


def collision_boxes():
    return [((0, 8.25, 0), (24, 1, 8.1)),
            ((0, 5.15, -7), (25, .9, 2.5)), ((0, 5.15, 7), (25, .9, 2.5)),
            ((-8, 3.7, 0), (6.8, 7.4, 7.5)), ((8, 3.7, 0), (6.8, 7.4, 7.5))]
