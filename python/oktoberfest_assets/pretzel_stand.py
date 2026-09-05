"""Peaked pretzel kiosk: shared timber construction, its own bread displays."""
import math

from .festzelt import build_pavilion, collision_boxes as pavilion_collision
from .common import diamond_panel


def build(model):
    build_pavilion(model)
    for x,y in ((-21,23),(-16,19),(17,22),(23,18)):
        model.beam((x,31,18),(x,y+2.5,18),.16,"rope")
        model.pretzel((x,y,18),1.5)
    # Shallow crate: open top and upright bread resting on its bottom.
    model.box((-13,13,21),(15,1,5),"darkwood",bevel=.25)
    for z in (18.5,23.5): model.box((-13,14,z),(15,2,1),"oak",bevel=.15)
    for x in (-20,-6): model.box((x,14,21),(1,2,5),"oak",bevel=.15)
    for x,y,z in ((-17,15.3,21),(-13,15.1,20),(-9,15.4,21.5)):
        model.pretzel((x,y,z),1.7)
    # Basket weave is deliberately broad, readable at the original game scale.
    for y in (13,14,15):
        model.tube([(15+5*math.cos(i*math.tau/16),y,21+2.6*math.sin(i*math.tau/16))
                    for i in range(16)],.3,"rope",closed=True)
    for i in range(12):
        a=i*math.tau/12
        model.beam((15+4.5*math.cos(a),12.5,21+2.2*math.sin(a)),
                   (15+5*math.cos(a),15,21+2.6*math.sin(a)),.2,"oak")
    for x,z in ((12,21),(16,20),(18,22)):
        model.pretzel((x,15,z),1.3)
    model.beam((2,12.5,21),(2,22,21),.5,"oak")
    model.beam((-1,21,21),(5,21,21),.45,"oak")
    for x in (-.5,4.5):
        model.beam((x,21,21),(x,20,21),.12,"rope")
        model.pretzel((x,18.4,21),1)
    diamond_panel(model,lambda u,v:(-19+7*u,12.7-5*max(0,(v-.65)/.35),19+6*v),4,4)
    # Match the original small-stall library envelope; no map transforms change.
    model.positions[:]=[v*.45 for v in model.positions]


def collision_boxes():
    return [(tuple(v*.45 for v in center),tuple(v*.45 for v in size))
            for center,size in pavilion_collision()]
