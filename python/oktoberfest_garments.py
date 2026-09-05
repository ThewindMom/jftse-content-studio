"""Experimental extra skinned material group for observed StageObj DATs.

Existing vertices, skeleton records and animation samples remain byte-identical.
Garment pieces copy weights from a nearby stock anchor. Native deformation is a
required validation gate, not implied by the structural round trip.
"""
import math
import struct

from adu_pose import parse_bind_pose
from oktoberfest_models import Model, add
from oktoberfest_native import ATLAS, triangle_strip


def chicken_garments(style):
    """Clothing fitted to the hash-locked Chick00 body, not its hair-tip bounds."""
    model, anchors = Model("FestivalWear"), []
    felt = "leaf" if style == "Forest" else "red"

    def face(points, material, anchor):
        start = len(model.positions)//3
        model.face(points,material)
        anchors.extend([anchor]*(len(model.positions)//3-start))

    def piece(anchor, draw):
        start = len(model.positions)//3
        draw()
        anchors.extend([anchor]*(len(model.positions)//3-start))

    head = (0,2.7,0)
    # The last 0.5 units of source height are a thin feather stalk, not skull.
    rings = [(2.78,1.08,.89),(2.84,1.12,.93),(2.91,.83,.72),
             (3.42,.72,.62),(3.73,.48,.43)]
    for (ya,xa,za),(yb,xb,zb) in zip(rings,rings[1:]):
        for i in range(24):
            a,b=i*math.tau/24,(i+1)*math.tau/24
            face([(xa*math.cos(a),ya,za*math.sin(a)),(xb*math.cos(a),yb,zb*math.sin(a)),
                  (xb*math.cos(b),yb,zb*math.sin(b)),(xa*math.cos(b),ya,za*math.sin(b))],felt,head)
    for i in range(24):
        a,b=i*math.tau/24,(i+1)*math.tau/24
        face([(0,3.76,0),(.48*math.cos(b),3.73,.43*math.sin(b)),
              (.48*math.cos(a),3.73,.43*math.sin(a))],felt,head)
    piece(head,lambda:model.tube([(.85*math.cos(i*math.tau/32),2.98,.73*math.sin(i*math.tau/32)) for i in range(33)],.035,"rope"))
    feather=[(-.7,2.99,.1),(-.83,3.2,.12),(-1.02,3.5,.14),(-1.11,3.77,.16),(-1.2,3.94,.17)]
    piece(head,lambda:model.tube(feather,.018,"rope"))
    for i in range(len(feather)-1):
        a,b=feather[i],feather[i+1]
        wa,wb=(.02,.13,.11,.08,0)[i:i+2]
        points=[add(a,(-wa,0,0)),add(b,(-wb,0,0)),add(b,(wb,0,0)),add(a,(wa,0,0))]
        if wb == 0:
            points.pop(2)
        face(points,"ivory",head)
        face(points[::-1],"ivory",head)

    # Two connected hip panels taper to distinct open leg hems. Unlike the
    # rejected ellipsoids, these are a hollow garment with visible feet.
    for side in (-1,1):
        top=[(side*1.35*math.cos(t),1.12,1.66*math.sin(t)) for t in [-math.pi/2+i*math.pi/12 for i in range(13)]]
        top += [(0,1.12,1.66*(1-i/2)) for i in range(1,4)]
        angles=[-math.pi/2+i*math.pi/12 for i in range(13)]+[math.pi/2+i*math.pi/4 for i in range(1,4)]
        hem=[(side*(.57+.58*math.cos(t)),.24,.86*math.sin(t)) for t in angles]
        middle=[(a[0]*1.02,.62,a[2]*.95) for a in top]
        anchor=(side*.55,.6,0)
        for lower,upper in ((hem,middle),(middle,top)):
            for i in range(16):
                j=(i+1)%16
                points=[lower[i],upper[i],upper[j],lower[j]]
                face(points if side>0 else points[::-1],"ginger",anchor)
        piece(anchor,lambda hem=hem:model.tube(hem+[hem[0]],.025,"rope"))
    waist=[(1.37*math.cos(i*math.tau/32),1.13,1.68*math.sin(i*math.tau/32)) for i in range(33)]
    piece((0,1,1.5),lambda:model.tube(waist,.045,"ginger"))
    piece((0,1,1.5),lambda:model.tube([(x,1.18,z) for x,_,z in waist],.009,"rope"))
    # Straps curve around the wings and run down the back, rather than through
    # the eyes or as rigid rods on a flat bib.
    for side in (-1,1):
        # Radial surface intersections + .035; endpoints fasten to the waistband.
        path=[(side*x,y,z) for x,y,z in [
            (.85,1.17,1.34),(.8697,1.2966,1.0569),(.9702,1.4734,.9643),
            (1.0475,1.65,.8467),(1.0399,1.7767,.7462),(1.0376,1.9033,.643),
            (1.0405,2.03,.5348),(1.1071,2.07,.3412),(1.1365,2.11,.1118),
            (1.1196,2.15,-.1292),(1.1208,2.0733,-.3995),(1.0552,1.9967,-.6227),
            (.9601,1.92,-.7839),(.8441,1.6634,-1.0233),(.6828,1.4066,-1.2136),
            (.56,1.17,-1.53)]]
        for a,b in zip(path,path[1:]):
            face([add(a,(-.09,0,0)),add(b,(-.09,0,0)),add(b,(.09,0,0)),add(a,(.09,0,0))],"ivory",a)
            piece(a,lambda a=a,b=b:model.beam(a,b,.022,felt,6))
        piece(path[0],lambda p=path[0]:model.ellipsoid(add(p,(0,0,.035)),(.085,.085,.035),"amber"))
    piece((0,1,1.5),lambda:model.tube([(0,.42,1.1),(0,.75,1.55),(0,1.08,1.7)],.012,"rope"))
    return model,anchors


def garments(parsed, role, style):
    if role == "Chick":
        return chicken_garments(style)
    # Local coordinates measured on each source body. Aggregate bounds include
    # weapons, hair and helmets and are not a clothing pattern.
    profiles = {
        "Brewer": ((-1.25,20.8,1.8),2.75,1.8, (-.6,1.8),[(8.2,3.5,2.5),(10,4.3,3),(13,4.4,3),(15.4,4,2.5),(16.6,2.2,1.7)]),
        "Visitor": ((0,12.4,-.6),2.1,1.5, (0,-.7),[(4.1,1.35,.9),(5.5,1.65,1),(7,1.65,1),(7.9,.85,.65)]),
        "Greeter": ((0,7.7,0),2.15,1.55, (0,-.4),[(1.3,.8,.65),(2,.95,.7),(2.8,1,.65),(3.3,.55,.45)]),
        "Judge": ((82.4,22.45,.15),3.35,2.5, (82,.15),[]),
    }
    head,radius,depth,(cx,cz),torso = profiles[role]
    model,anchors = Model("FestivalWear"),[]
    cloth = "leaf" if style == "Forest" else "red"

    def piece(anchor, draw):
        start = len(model.positions)//3
        draw()
        anchors.extend([anchor]*(len(model.positions)//3-start))

    def face(points, material, anchor):
        piece(anchor,lambda:model.face(points,material))

    if role != "Visitor":
        hx,hy,hz=head
        crown = radius*.72
        rings=[(hy,radius,depth),(hy+.1,radius,depth),
               (hy+.18,crown,depth*.8),(hy+radius*.52,crown*.86,depth*.67)]
        for (ya,xa,za),(yb,xb,zb) in zip(rings,rings[1:]):
            for i in range(24):
                a,b=i*math.tau/24,(i+1)*math.tau/24
                face([(hx+xa*math.cos(a),ya,hz+za*math.sin(a)),(hx+xb*math.cos(a),yb,hz+zb*math.sin(a)),
                      (hx+xb*math.cos(b),yb,hz+zb*math.sin(b)),(hx+xa*math.cos(b),ya,hz+za*math.sin(b))],cloth,head)
        y,x,z=rings[-1]
        for i in range(24):
            a,b=i*math.tau/24,(i+1)*math.tau/24
            face([(hx,y+.08,hz),(hx+x*math.cos(b),y,hz+z*math.sin(b)),(hx+x*math.cos(a),y,hz+z*math.sin(a))],cloth,head)
        piece(head,lambda:model.tube([(hx+crown*math.cos(i*math.tau/24),hy+.25,hz+depth*.8*math.sin(i*math.tau/24)) for i in range(25)],radius*.025,"ginger"))
        feather=[(hx-crown*.9,hy+.25,hz),(hx-crown*1.15,hy+radius*.7,hz+.05),
                 (hx-crown*1.3,hy+radius,hz+.1),(hx-crown*1.45,hy+radius*1.2,hz+.13)]
        piece(head,lambda:model.tube(feather,radius*.012,"rope"))
        for i,(a,b) in enumerate(zip(feather,feather[1:])):
            wa,wb=(.035,.11,.07,0)[i:i+2]
            points=[add(a,(-radius*wa,0,0)),add(b,(-radius*wb,0,0)),add(b,(radius*wb,0,0)),add(a,(radius*wa,0,0))]
            if wb==0:points.pop(2)
            face(points,"ivory",head)
            face(points[::-1],"ivory",head)
    if role == "Greeter":
        # Existing clothing follows the source body and bent arms. Paint that
        # surface instead of layering a disconnected torso/sleeve shell over it.
        return model,anchors
    if role == "Judge":
        # Owl faces -X in its source coordinates, not +Z like the humanoids.
        piece((79.5,18,.15),lambda:model.tube([(80,20,-1.7),(78.8,18,.15),(80,20,2)],.12,"rope"))
        piece((79.5,18,.15),lambda:model.ellipsoid((78.65,17.8,.15),(.18,.7,.7),"amber"))
        return model,anchors

    # Shirt forms the continuous underlayer; the front vest opens at the collar.
    for lower,upper in zip(torso,torso[1:]):
        for i in range(24):
            a,b=i*math.tau/24,(i+1)*math.tau/24
            ya,xa,za=lower;yb,xb,zb=upper
            material = "ivory" if math.sin((a+b)/2)>.72 and upper==torso[-1] else cloth
            points=[(cx+xa*math.cos(a),ya,cz+za*math.sin(a)),(cx+xb*math.cos(a),yb,cz+zb*math.sin(a)),
                    (cx+xb*math.cos(b),yb,cz+zb*math.sin(b)),(cx+xa*math.cos(b),ya,cz+za*math.sin(b))]
            face(points,material,(cx,(ya+yb)/2,cz))
    waist,width,waist_depth=torso[0]
    collar,cw,cd=torso[-1]
    height=collar-waist
    piece((cx,collar,cz),lambda:model.tube([(cx+cw*math.cos(i*math.tau/24),collar+.03,cz+cd*math.sin(i*math.tau/24)) for i in range(25)],height*.045,"ivory"))
    piece((cx,waist,cz),lambda:model.tube([(cx+width*math.cos(i*math.tau/24),waist+.05,cz+waist_depth*math.sin(i*math.tau/24)) for i in range(25)],height*.035,"ginger"))
    for fraction in (.15,.32,.49,.66):
        y=waist+height*fraction
        lower,upper=next((a,b) for a,b in zip(torso,torso[1:]) if a[0]<=y<=b[0])
        t=(y-lower[0])/(upper[0]-lower[0]);z=cz+lower[2]+t*(upper[2]-lower[2])+.06
        piece((cx,y,z),lambda y=y,z=z:model.ellipsoid((cx,y,z),(height*.025,)*3,"amber"))
        # Small stitched leaf motifs on both vest fronts, not a wood-grain bib.
        for side in (-1,1):
            x=cx+side*width*.5
            piece((cx,y,cz),lambda x=x,y=y,z=z:model.beam((x,y,z-.1),(x+side*height*.08,y+height*.045,z-.1),height*.012,"rope",5))
    sleeves={
        "Brewer":[((-4.2,14.8,2.5),(-5.7,13,3.5)),((3.4,14.8,2.5),(4.5,13.3,4))],
        "Visitor":[((-1.6,7,-.7),(-2.6,6.7,-.7)),((1.6,7,-.7),(2.6,6.7,-.7))],
        "Greeter":[((-1,2.8,-.4),(-1.4,2.3,-.4)),((1,2.8,-.4),(1.4,2.3,-.4))],
    }
    for shoulder,cuff in sleeves[role]:
        piece(shoulder,lambda shoulder=shoulder,cuff=cuff:model.beam(shoulder,cuff,height*.17,"ivory",12))
        piece(cuff,lambda cuff=cuff:model.ellipsoid(cuff,(height*.18,height*.1,height*.18),"ivory"))
    return model,anchors


def append_garments(data, role, style):
    parsed = parse_bind_pose(data)
    if parsed is None:
        raise ValueError("Unsupported garment source")
    model,anchors = garments(parsed,role,style)
    nodes,groups = parsed["nodeCount"],len(parsed["materials"])
    count = len(model.positions)//3
    if groups+1 > min(nodes,255) or count>65536:
        raise ValueError("Garment group exceeds bounded writer")
    candidates = []
    for part in parsed["primitives"]:
        fmt = "<8fI" if part["vertexStride"] == 36 else "<12f4H"
        for i in range(part["vertexCount"]):
            row = struct.unpack_from(fmt,data,part["vertexOffset"]+i*part["vertexStride"])
            palette = part["bonePalette"]
            weights = (1.,0.,0.,0.) if part["vertexStride"] == 36 else row[8:12]
            joints = (palette[row[8]],0,0,0) if part["vertexStride"] == 36 else tuple(palette[j] if w else 0 for j,w in zip(row[12:16],weights))
            candidates.append((row[:3],weights,joints))
    bindings = {}
    for anchor in anchors:
        if anchor not in bindings:
            bindings[anchor] = min(candidates,key=lambda p:sum((a-b)**2 for a,b in zip(p[0],anchor)))[1:]
    palette = sorted({j for weights,joints in bindings.values() for w,j in zip(weights,joints) if w>0})
    local = {joint:i for i,joint in enumerate(palette)}
    records = bytearray()
    for i,anchor in enumerate(anchors):
        weights,joints = bindings[anchor]
        records.extend(struct.pack("<12f4H",*model.positions[i*3:i*3+3],*model.normals[i*3:i*3+3],
                                   *model.uvs[i*2:i*2+2],*weights,*(local[j] if w>0 else 0 for w,j in zip(weights,joints))))
    strip = triangle_strip(model.indices)
    box = struct.pack("<6f",*[max(model.positions[i::3]) for i in range(3)],*[min(model.positions[i::3]) for i in range(3)])
    group = struct.pack("<4I",1,groups+1,4,0)+box+struct.pack("<I",1)+box
    group += struct.pack("<4I",1,1,1,len(palette))+struct.pack(f"<{len(palette)}I",*palette)
    group += struct.pack("<5I",3,0,count,len(strip)-2,2)+records
    old_index,old_material = [12+4*n for n in struct.unpack_from("<2I",data,4)]
    result = bytearray(data[:parsed["geometryEnd"]]+group+data[parsed["geometryEnd"]:old_index])
    index = len(result)
    result.extend(data[old_index:parsed["indicesEnd"]]+struct.pack("<H",groups+1)+struct.pack(f"<{len(strip)}H",*strip))
    result.extend(bytes(-len(result)%4))
    material = len(result)
    extra = bytes([groups+1])+b"FestivalWear\0".ljust(64,b"\0")+b"\1\1\0\0\0\0"
    extra += bytes(4)+b"\1"+(ATLAS+"\0").encode().ljust(64,b"\0")+bytes(3)
    result.extend(data[old_material:parsed["materialsEnd"]]+extra+data[parsed["materialsEnd"]:])
    result.extend(bytes(-len(result)%4))
    struct.pack_into("<3I",result,0,(len(result)-12)//4,(index-12)//4,(material-12)//4)
    struct.pack_into("<I",result,24,groups+1)
    checked = parse_bind_pose(bytes(result))
    if checked is None or len(checked["materials"]) != groups+1:
        raise ValueError("Garment structural round trip failed")
    return bytes(result)
