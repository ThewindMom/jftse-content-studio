"""Tall Bavarian maypole with a timber planter and wind-worn festival dressings."""

import math

from .common import bow, cloth, flowers, lantern


def _ring(model, radius, y, thickness, material, sides=16):
    points = [(radius * math.cos(i * math.tau / sides), y,
               radius * math.sin(i * math.tau / sides)) for i in range(sides)]
    model.tube(points, thickness, material, sides=6, closed=True)


def _shield(model, center, scale=1):
    x, y, z = center
    outline = [(-2.0, 2.2), (2.0, 2.2), (2.15, .25),
               (1.35, -1.75), (0, -2.65), (-1.35, -1.75), (-2.15, .25)]
    front = [(x + px * scale, y + py * scale, z + .24) for px, py in outline]
    back = [(px, py, z - .24) for px, py, _ in front]
    model.face(front, "oak")
    model.face(list(reversed(back)), "darkwood")
    for index in range(len(front)):
        nxt = (index + 1) % len(front)
        model.face([back[index], front[index], front[nxt], back[nxt]], "darkwood")
    # Large painted lozenges read at game distance without expensive relief.
    for row in range(3):
        for column in range(3):
            cx = x + (column - 1) * .92 * scale
            cy = y + (1.15 - row * 1.05) * scale
            diamond = [(cx, cy + .62*scale, z + .27), (cx + .48*scale, cy, z + .27),
                       (cx, cy - .62*scale, z + .27), (cx - .48*scale, cy, z + .27)]
            model.face(diamond, "blue" if (row + column) % 2 else "ivory")


def _sign(model, x, y, points_right, symbol):
    tip = 5.6 if points_right else -5.6
    inner = -1.0 if points_right else 1.0
    points = [(inner, y + 1.25, 1.2), (tip, y + .9, 1.2),
              ((tip + (1 if points_right else -1)), y, 1.2),
              (tip, y - .9, 1.2), (inner, y - 1.25, 1.2)]
    cloth(model, points, "oak")
    if symbol == "pretzel":
        model.pretzel(((inner + tip) / 2, y - .2, 1.45), .55)
    else:
        model.mug(((inner + tip) / 2, y - .7, 1.45), .42)


def build(model):
    # Open-topped circular planter: stout, plank-built, and grounded at y=0.
    for index in range(14):
        angle = index * math.tau / 14
        model.box((4.15*math.cos(angle), 2.15, 4.15*math.sin(angle)),
                  (1.8, 4.3, .65), "oak" if index % 4 else "darkwood",
                  yaw=-angle, bevel=.14)
    _ring(model, 4.35, .45, .35, "darkwood")
    _ring(model, 4.35, 3.95, .3, "oak")
    for angle in (0, math.pi/2, math.pi, math.pi*3/2):
        model.box((4.55*math.cos(angle), 2.5, 4.55*math.sin(angle)),
                  (1.0, 5.0, .9), "darkwood", yaw=-angle, bevel=.16)
    for angle in (-2.4, .7):
        flowers(model, (3.65*math.cos(angle), 4.15, 3.65*math.sin(angle)), .55)

    # The broad blue spiral is painted cloth/paint, not a dense modeled helix.
    model.beam((0, 1.2, 0), (0, 40.3, 0), .78, "ivory", sides=12)
    turns = 8
    steps = 96
    for index in range(steps):
        a0 = index * turns * math.tau / steps
        a1 = (index + 1) * turns * math.tau / steps
        y0, y1 = 3.0 + index * 36.0 / steps, 3.0 + (index + 1) * 36.0 / steps
        width = 1.55
        model.face([(.81*math.cos(a0), y0, .81*math.sin(a0)),
                    (.81*math.cos(a1), y1, .81*math.sin(a1)),
                    (.81*math.cos(a1), y1 + width, .81*math.sin(a1)),
                    (.81*math.cos(a0), y0 + width, .81*math.sin(a0))], "blue")

    _ring(model, 7.0, 30.2, .72, "leaf", sides=18)
    for angle in (-2.65, -1.35, -.2, 1.0, 2.15):
        point = (7*math.cos(angle), 30.2, 7*math.sin(angle))
        model.beam((0, 34.1, 0), point, .1, "rope", sides=4)
        # Long, asymmetric tied streamers.
        x, _, z = point
        bow(model, (x, 30.3, z), .58)
        drift = .65 if angle < 0 else -.45
        cloth(model, [(x-.45, 29.9, z), (x+.38, 29.9, z),
                      (x+drift+.65, 21.5+(angle % .8), z+.3),
                      (x+drift-.25, 22.4+(angle % .8), z+.2)],
              "blue" if angle < 0 else "ivory")
    for angle in (-2.0, .1):
        x, z = 5.6*math.cos(angle), 5.6*math.sin(angle)
        model.beam((x, 30, z), (x, 27.8, z), .09, "rope", 4)
        lantern(model, (x, 25.9, z), .62)

    _sign(model, 0, 16.0, False, "beer")
    _sign(model, 0, 12.8, True, "pretzel")
    model.beam((0, 14.4, .9), (0, 17.3, .9), .24, "rope", 6)
    _shield(model, (0, 38.5, .72), .72)
    model.box((0, 42.0, 0), (1.8, 1.6, 1.8), "oak", bevel=.28)


def collision_boxes():
    return [((0, 2.25, 0), (10, 4.5, 10)), ((0, 22.2, 0), (1.7, 35.5, 1.7))]
