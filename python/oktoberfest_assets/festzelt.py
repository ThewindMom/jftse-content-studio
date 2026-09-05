"""Peaked serving pavilion authored from the user's Oktoberfest kiosk reference.

All surfaces are original geometry; the reference image is not a texture.
The front faces +Z. Dimensions stay inside the former terrace's placement area.
"""
import math
from . import common


def counter_z(x):
    return 17 + 6 * math.cos(x / 26 * math.pi / 2)


def build_pavilion(model):
    def cloth(points, material):
        model.face(points, material)
        model.face(points[::-1], material)

    def bow(x, y, z, scale=1):
        for side in (-1, 1):
            for i in range(12):
                a, b = i * math.tau / 12, (i + 1) * math.tau / 12
                def loop(t, inner):
                    return (x + side * scale * (1.4 + (1.3-inner)*math.cos(t)),
                            y + scale*(.65-inner*.4)*math.sin(t),
                            z + .5*scale*math.sin(t))
                cloth([loop(a,0),loop(b,0),loop(b,.55),loop(a,.55)], "blue")
            cloth([(x,y,z), (x+side*1.4*scale,y-.1,z),
                   (x+side*2.1*scale,y-4.8*scale,z+.6),
                   (x+side*.4*scale,y-4.2*scale,z+.9)], "blue")
            cloth([(x+side*.4*scale,y-.6,z+.15), (x+side*.7*scale,y-.5,z+.2),
                   (x+side*1.5*scale,y-4.1*scale,z+.8),
                   (x+side*1.1*scale,y-4.3*scale,z+.85)], "ivory")
        model.ellipsoid((x,y,z),(.7*scale,.65*scale,.65*scale),"ivory")

    def swag(start, end, sag, width):
        for layer, material in enumerate(("blue", "ivory")):
            def point(t, lower):
                x = start[0]*(1-t)+end[0]*t
                y = start[1]*(1-t)+end[1]*t - sag*math.sin(t*math.pi)
                z = start[2]*(1-t)+end[2]*t + .7*math.sin(t*math.pi)
                return (x, y + layer*.65 - lower*width*(1-layer*.35), z+layer*.2)
            for i in range(16):
                a,b=i/16,(i+1)/16
                cloth([point(a,0),point(b,0),point(b,1),point(a,1)],material)

    def flowers(x,y,z):
        for i in range(7):
            a=i*math.tau/7
            dx,dy=math.cos(a),math.sin(a)
            cloth([(x,y,z),(x+dx-dy*.5,y+dy+dx*.5,z+.15),
                   (x+dx*2,y+dy*2,z),(x+dx+dy*.5,y+dy-dx*.5,z+.15)],"leaf")
        for dx,dy in ((-.7,.4),(.6,-.5)):
            for i in range(5):
                a=i*math.tau/5
                px,py=x+dx+.35*math.cos(a),y+dy+.35*math.sin(a)
                cloth([(px-.25,py,z+.4),(px,py-.3,z+.4),(px+.25,py,z+.4),(px,py+.3,z+.4)],"ivory")
            model.face([(x+dx-.15,y+dy-.15,z+.5),(x+dx+.15,y+dy-.15,z+.5),
                        (x+dx,y+dy+.18,z+.5)],"amber")

    # Individual counter staves follow the serving arc, not a straight box.
    for i in range(20):
        x=-24.7+i*2.6
        slope=-6*math.pi/52*math.sin(x/26*math.pi/2)
        model.box((x,5.6,counter_z(x)),(2.48,11.2,1.45),"oak",
                  yaw=-math.atan(slope),bevel=.18)
    for i in range(10):
        x=-23.4+i*5.2
        slope=-6*math.pi/52*math.sin(x/26*math.pi/2)
        model.box((x,11.7,counter_z(x)-.5),(5.4,1.6,6),"oak",
                  yaw=-math.atan(slope),bevel=.35)
    for x in (-26,-13,0,13,26):
        z=counter_z(x)
        model.box((x,5.6,z+.4),(1.3,11.2,1.4),"darkwood",bevel=.15)
        if abs(x)<26:
            flowers(x,8,z+1.5)
    for a,b in zip((-26,-13,0,13),(-13,0,13,26)):
        swag((a,10,counter_z(a)+1),(b,10,counter_z(b)+1),2.1,1.3)
    # The service shelf and rear opening leave room for an actual attendant.
    model.box((0,10,-10),(40,1.5,7),"oak",bevel=.3)
    for x in (-17,17):
        model.box((x,5,-10),(2,10,4),"darkwood",bevel=.2)

    for x in (-26,26):
        for z in (-18,18):
            model.beam((x,0,z),(x,34,z),1.55,"oak",8)
            model.beam((x,25,z),(x*.72,30.5,z),.8,"oak")
            model.beam((x,30,z),(x*1.35,1,z*1.28),.22,"rope")
            model.beam((x*1.35,0,z*1.28),(x*1.35,3,z*1.28),.5,"oak")
            for y in (29.4,30.2,31):
                model.beam((x,y,z),(x,y+.35,z),1.7,"rope",10)
        model.beam((x,30.5,-23),(x,30.5,23),1.3,"oak",8)
    for z in (-18,18):
        model.beam((-30,30.5,z),(30,30.5,z),1.4,"oak",8)
    model.beam((0,0,0),(0,63,0),1.9,"oak",10)
    model.beam((0,61,0),(0,65,0),2.35,"oak",10)

    # A tensioned four-corner canopy: steep around the mast, soft at the eaves.
    def canopy(u,v):
        r=max(abs(u),abs(v))
        folds=.45*math.sin(u*math.pi*4)*math.sin(v*math.pi*3)*r
        return (u*29, 33+27*(1-r)**1.8+folds, v*22)
    for z in (-18,18):
        for x in (-26,26):
            path=[canopy(x/29*t,z/22*t) for t in (.05,.2,.4,.6,.8,1)]
            model.tube([(a,b-3,c) for a,b,c in path],.35,"oak")
    for j in range(6):
        va,vb=-1+j/3,-1+(j+1)/3
        for i in range(8):
            ua,ub=-1+i/4,-1+(i+1)/4
            um,vm=(ua+ub)/2,(va+vb)/2
            diamond=[canopy(ua,vm),canopy(um,vb),canopy(ub,vm),canopy(um,va)]
            # Four triangles keep the diamond on the peaked surface, including the apex.
            center=canopy(um,vm)
            for k in range(4):
                cloth([center,diamond[k],diamond[(k+1)%4]],"blue")
            for corner,a,b in [(canopy(ua,va),0,3),(canopy(ua,vb),1,0),
                               (canopy(ub,vb),2,1),(canopy(ub,va),3,2)]:
                cloth([corner,diamond[a],diamond[b]],"ivory")
    for z in (-22,22):
        swag((-28,33,z),(0,33,z),3.3,2)
        swag((0,33,z),(28,33,z),3.3,2)
        for x in (-26,26):
            bow(x,32,z,1.35)
    for x in (-29,29):
        # Side swags use the same draped construction rotated about the mast.
        start=len(model.positions)
        swag((-22,33,0),(22,33,0),3.6,2)
        for i in range(start,len(model.positions),3):
            px,py,pz=model.positions[i:i+3]
            nx,ny,nz=model.normals[i:i+3]
            model.positions[i:i+3]=(x+pz,py,-px)
            model.normals[i:i+3]=(nz,ny,-nx)
    bow(0,60,2,1.1)

    # Carved, rounded sign assembled from three shaped planks.
    for y,width in ((24.6,18),(26.5,21),(28.4,18)):
        model.box((0,y,24),(width,2,1.3),"oak",bevel=.55)
    for x in (-7,7):
        model.tube([(x,34,18),(x,34.8,20),(x,33,24),(x,29,24),(x,28,25)],.3,"rope")
        model.ellipsoid((x,28,25),(.45,.45,.2),"metal")
    model.pretzel((0,26,25),2.5)
    for side in (-1,1):
        model.tube([(side*6,24.8,24.8),(side*7,26,24.8),(side*7.5,27.5,24.8)],.12,"ivory")
        for i in range(3):
            model.ellipsoid((side*(6+i*.55),25+i*.7,24.85),(.5,.22,.1),"ivory")
    model.bunting((-23,27,17),(-7,22,18),6)
    for x in (-29,29):
        model.tube([(x,33,18),(x,31,21),(x,28,22)],.25,"rope")
        model.lantern((x,21,22),1.8)

    for x,z in ((-29,10),(29,8)):
        model.keg((x,0,z),4.2,9)
        for i in range(12):
            a=i*math.tau/12
            for y in (2.3,7):
                cx,cz=x+4.3*math.cos(a),z+4.3*math.sin(a)
                dx,dz=-.16*math.sin(a),.16*math.cos(a)
                model.face([(cx-dx,y-.16,cz-dz),(cx-dx,y+.16,cz-dz),
                            (cx+dx,y+.16,cz+dz),(cx+dx,y-.16,cz+dz)],"metal")


def build(model):
    build_pavilion(model)
    # Turn a stave-built keg onto a cradle, with a tap on the visible end.
    start=len(model.positions)
    model.keg((0,0,0),5,9)
    for i in range(start,len(model.positions),3):
        x,y,z=model.positions[i:i+3]
        nx,ny,nz=model.normals[i:i+3]
        model.positions[i:i+3]=(10+x,16+z,-10+y)
        model.normals[i:i+3]=(nx,nz,ny)
    # The axis swap reverses handedness; reverse only the keg's triangles.
    first_vertex=start//3
    for i in range(len(model.indices)-1,-1,-3):
        if model.indices[i]<first_vertex:
            break
        model.indices[i-1],model.indices[i]=model.indices[i],model.indices[i-1]
    for z in (-9,-2):
        model.box((10,10.9,z),(10,1.2,1.8),"darkwood",bevel=.2)
    model.beam((10,14,-.7),(10,14,2),.65,"amber",8)
    model.beam((10,14,2),(10,12.8,2),.5,"amber",8)
    model.beam((10,14.2,1),(10,16,1),.22,"metal")
    model.beam((9,16,1),(11,16,1),.3,"oak")

    for x,z in ((-13,21),(-3,22),(9,21)):
        model.keg((x,12.5,z),1.15,2.5)
        model.tube([(x+1,13,z),(x+2,13,z),(x+2,14.5,z),(x+1,14.5,z)],.2,"metal")
        for dx,dy,dz,r in ((0,0,0,1),(-.6,.1,.2,.65),(.6,.15,0,.6),(0,.35,-.4,.7)):
            model.ellipsoid((x+dx,15.2+dy,z+dz),(r,.65*r,r),"foam")
    model.box((-15,12,-10),(5,2,4),"darkwood",bevel=.15)
    for x,z,h in ((-16,-10,4),(-14.5,-10,5),(-15,-9,3)):
        model.beam((x,13,z),(x+.3,13+h,z),.45,"oak")
    # Small chalkboard: geometry illustration, not unreadable generated lettering.
    model.box((20,17,21),(7,8,.5),"metal",bevel=.1)
    for x in (16.2,23.8): model.beam((x,12,21),(x,22,21),.45,"oak")
    for y in (13,21): model.beam((16, y,21),(24,y,21),.45,"oak")
    model.tube([(18.5,18.5,21.4),(18.5,15.3,21.4),(21,15.3,21.4),(21,18.5,21.4)],.12,"ivory")
    model.tube([(21,18,21.4),(22,18,21.4),(22,16,21.4),(21,16,21.4)],.12,"ivory")
    for x in (19,20,21): model.ellipsoid((x,18.8,21.4),(.6,.45,.12),"ivory")
    # A folded serving cloth actually runs over the counter's front lip.
    for i in range(4):
        x=-20+i*1.4
        common.cloth(model,[(x,12.65,19),(x+1.4,12.65,19),(x+1.4,12.65,24),(x,12.65,24)],
              "blue" if i%2 else "ivory")
        common.cloth(model,[(x,12.65,24),(x+1.4,12.65,24),(x+1.5,7.4,24.8),(x+.1,7.7,24.8)],
              "blue" if i%2 else "ivory")


def collision_boxes():
    boxes=[((x,17,z),(3.2,34,3.2)) for x in (-26,26) for z in (-18,18)]
    boxes += [((0,30,0),(4,60,4)), ((0,5,-10),(40,10,7))]
    boxes += [((x,6,counter_z(x)),(6.8,12,6)) for x in (-22.75,-16.25,-9.75,-3.25,3.25,9.75,16.25,22.75)]
    boxes += [((x,4.5,z),(8.4,9,8.4)) for x,z in ((-29,10),(29,8))]
    return boxes
