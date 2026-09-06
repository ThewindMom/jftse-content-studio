"""Broad cloth masses, rounded foliage and softened joinery from dense-court.png.

No new Blender operations: all explicit coordinates feed the source-bound common
mesh/UV and primitive helpers. Stock PNG crops/provenance are unchanged.
"""
from common import *
import common


def start_reference():
    start()
    textures=ROOT/'exports/blender-festival/textures'
    MATS['blue']=material('Festival_Royal_Stock_Folds',(0,0,0),str(textures/'royal-swag.png'))
    MATS['swagcream']=material('Festival_Cream_Stock_Folds',(0,0,0),str(textures/'cream-swag.png'))
    MATS['cloth']=material('Festival_Royal_Diamonds',(0,0,0),str(textures/'royal-diamonds.png'))
    for name,color in [('leaf',(.23,.33,.077)),('green',(.115,.22,.047)),('icing',(.91,.82,.63)),('flowerblue',(.21,.39,.55))]:
        MATS[name]=material('Festival_Ambient_'+name,color,ambient=.4)


def cushion(name,p,rx,rz,depth,mat='leaf',angle=0):
    x,y,z=p; outline=[]
    for i in range(10):
        a=2*math.pi*i/10; u=rx*math.cos(a);v=rz*math.sin(a)
        outline.append((x+u*math.cos(angle)-v*math.sin(angle),y,z+u*math.sin(angle)+v*math.cos(angle)))
    mesh(name,outline+[(x,y-depth,z),(x,y+depth*.45,z)],
         [(i,(i+1)%10,10) for i in range(10)]+[((i+1)%10,i,11) for i in range(10)],mat,smooth=True)


def round_daisy(name,p,s=.2,blue=False,facing=-1):
    x,y,z=p
    if 'flowerblue' not in MATS:
        MATS['flowerblue']=material('Festival_Flower_Blue',(.21,.39,.55))
    for i in range(7):
        a=i*2*math.pi/7
        cushion(name+'_Rounded_Petal',(x+s*.52*math.cos(a),y,z+s*.52*math.sin(a)),s*.43,s*.23,s*.13,'flowerblue' if blue else 'icing',a)
    cushion(name+'_Golden_Center',(x,y+facing*s*.19,z),s*.23,s*.23,s*.15,'brass')


def bouquet(name,p,s=1,flowers=7,facing=-1):
    x,y,z=p
    # Overlapping broad oval leaves make a full silhouette, not a fan of spikes.
    for i in range(26):
        a=i*2.39996; r=.1+.27*((i*7)%13)/13
        cushion(name+'_Round_Hops',(x+s*r*math.cos(a),y+s*.15*math.sin(i*1.7),z+s*r*.7*math.sin(a)),s*.10,s*.068,s*.04,'leaf' if i%3 else 'green',a)
    for i in range(flowers):
        a=i*2.39996;r=0 if i==0 else s*.26
        round_daisy(name+'_Flower',(x+r*math.cos(a),y+facing*.19*s,z+r*.73*math.sin(a)),s*(.17 if i==0 else .115),blue=i%5==4,facing=facing)


def spill(name,p,s=1):
    x,y,z=p
    for side in (-1,1):
        points=[(x+side*s*(.06+.08*math.sin(i*.6)),y-.015*i*s,z-i*.085*s) for i in range(8)]
        tube(name+'_Vine',points,.019*s,'green',5)
        for i,q in enumerate(points):
            cushion(name+'_Hops',q,.115*s,.07*s,.035*s,'leaf' if i%2 else 'green',side*.8+i*.15)


def deep_swag(name,left,right,y,z,drop=.65,facing=-1,segments=32):
    # Broad gathered fabric with nested blue/cream folds and rolled hems.
    for layer,(upper,lower,mat) in enumerate([(0,1,'blue'),(.46,.78,'swagcream'),(.78,.9,'blue')]):
        vs=[];uv=[];hem=[]
        for i in range(segments+1):
            t=i/segments;dip=math.sin(math.pi*t)**.72
            for j in range(5):
                v=upper+(lower-upper)*j/4
                depth=.09+.11*math.sin(math.pi*v)+.025*math.cos(v*math.pi*10)
                q=(left+(right-left)*t,y+facing*(depth*dip+layer*.008),z-((.3+.7*v)*drop+.1*v)*dip-.035*v)
                vs.append(q);uv.append((t,v))
                if j==4:hem.append(q)
        mesh(name+'_Gathered_Layer',vs,[(i*5+j,i*5+j+1,(i+1)*5+j+1,(i+1)*5+j) for i in range(segments) for j in range(4)],mat,uv,smooth=True)
        tube(name+'_Rolled_Hem',hem,.018,mat,6)


def crest_pretzel(name,p,s):
    # Ends join the outer shoulders; the crossed tails now enclose a third,
    # broad lower opening instead of ending loose inside an infinity silhouette.
    if 'crestbread' not in MATS:
        MATS['crestbread']=material('Festival_Carved_Golden_Dough',(.72,.4,.14),ambient=.3)
    control=[(-.72,-.53),(-.45,-.27),(.30,.4),(.53,.68),(.77,.68),(.98,.4),(.99,.02),(.88,-.30),(.72,-.53),(.38,-.79),(0,-.86),(-.38,-.79),(-.72,-.53),(-.88,-.30),(-.99,.02),(-.98,.4),(-.77,.68),(-.53,.68),(-.30,.4),(.45,-.27),(.72,-.53)]
    points=[]
    for i in range(len(control)-1):
        a,b,c,d=[control[min(len(control)-1,max(0,j))] for j in (i-1,i,i+1,i+2)]
        for step in range(4):
            t=step/4
            x,z=[.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in (0,1)]
            depth=-.018 if i<3 else (.018 if i>17 else 0)
            points.append((p[0]+s*x,p[1]+depth,p[2]+s*z))
    points.append((p[0]+s*control[-1][0],p[1],p[2]+s*control[-1][1]))
    tube(name,points,.115*s,'crestbread',10,smooth=True)


def shaped_panel(name,p,s=.42):
    x,y,z=p
    outline=[(-.9,-.68),(-1,-.45),(-1,.5),(-.65,.68),(-.5,.92),(.5,.92),(.65,.68),(1,.5),(1,-.45),(.9,-.68)]
    for scale,depth,mat in [(1,.12,'post'),(.88,.16,'end')]:
        vs=[(x+a*s*scale,y+dy,z+b*s*scale) for dy in (-depth,.08) for a,b in outline]
        mesh(name+'_Shaped_Timber',vs,[tuple(range(9,-1,-1)),tuple(range(10,20))]+[(i,(i+1)%10,(i+1)%10+10,i+10) for i in range(10)],mat)
    crest_pretzel(name+'_Raised_Pretzel',(x,y-.2,z+.06),s*.67)


def soft_rail(name,left,right,z):
    # Longitudinal segments become a real curve when the coordinate map is set.
    cross_section=[(-.105,-.065),(-.08,-.09),(.08,-.09),(.105,-.065),(.105,.065),(.08,.09),(-.08,.09),(-.105,.065)]
    vs=[]
    for i in range(33):
        x=left+(right-left)*i/32
        vs.extend((x,y,z+h) for y,h in cross_section)
    fs=[];uv=[]
    for i in range(32):
        for j in range(8):
            fs.append((i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j))
            uv.append([(.02,.02+.96*i/32),(.98,.02+.96*i/32),(.98,.02+.96*(i+1)/32),(.02,.02+.96*(i+1)/32)])
    fs += [tuple(range(7,-1,-1)),tuple(32*8+i for i in range(8))]
    uv += [[(.5+.45*math.cos(i*math.pi/4),.5+.45*math.sin(i*math.pi/4)) for i in range(8)]]*2
    mesh(name,vs,fs,'wood',face_uvs=uv)


def fence(curved=False,half_width=None,skip_left_post=False,swag_segments=32):
    half=half_width if half_width is not None else (2.8*math.pi/4 if curved else 1.4)
    if curved:
        def bend(p):
            x,y,z=p;t=x/2.8
            return ((2.8-y)*math.sin(t),2.8-(2.8-y)*math.cos(t),z)
        common.COORDINATE_MAP=bend
    for x in (-half,half):
        if skip_left_post and x==-half:
            continue
        box('Fence_Chunky_Post',(x,0,.94),(.25,.29,1.88),'post',.065)
        box('Fence_Soft_Cap',(x,0,1.95),(.33,.36,.15),'end',.075)
    for z in (.31,1.73):soft_rail('Fence_Soft_Long_Rail',-half,half,z)
    count=13 if curved else 9
    for i in range(count):
        x=-half+.16+(2*half-.32)*i/(count-1)
        box('Fence_Broad_Picket',(x,.025,.99),(.15,.13,1.34),'post',.035)
    deep_swag('Large_Blue_Cream_Drape',-half+.02,half-.02,-.16,1.82,.88,segments=swag_segments)
    deep_swag('Rear_Blue_Cream_Drape',-half+.02,half-.02,.18,1.82,.88,facing=1,segments=swag_segments)
    shaped_panel('Fence_Carved_Plaque',(-half,-.2,1.57),.39)
    bouquet('Fence_Lush_Rosette',(half,-.2,1.91),1.05,7)
    spill('Fence_Leaf_Cascade',(half,-.22,1.75),.9)
    bouquet('Fence_Small_Green_Gather',(-half,-.02,2.0),.52,3)
    bouquet('Fence_Rear_Rosette',(half,.3,1.96),.75,5,facing=1)


def curve_run(half_chord,sag,bays,swag_segments=32):
    radius=(half_chord**2+sag**2)/(2*sag)
    half_angle=math.asin(half_chord/radius)
    half_bay=radius*half_angle/bays
    for bay in range(bays):
        offset=(bay-(bays-1)/2)*2*half_bay
        def bend(p):
            x,y,z=p;t=(x+offset)/radius
            return ((radius-y)*math.sin(t),radius-(radius-y)*math.cos(t),z)
        common.COORDINATE_MAP=bend
        fence(half_width=half_bay,skip_left_post=bay>0,swag_segments=swag_segments)


def full_barrel(p=(0,0,0),s=1):
    x,y,z=p
    barrel('Rounded_Flower_Barrel',(x,y,z+.44*s),.43*s,.88*s)
    # Hemispherical arrangement, with flowers on front, top and sides.
    bouquet('Planter_Front',(x,y-.16*s,z+1.13*s),1.35*s,9)
    bouquet('Planter_Back',(x,y+.23*s,z+1.25*s),.85*s,5)
    for side in (-1,1):
        bouquet('Planter_Side',(x+side*.31*s,y+.02*s,z+1.04*s),.58*s,3)
    spill('Planter_Trailing',(x+.26*s,y-.34*s,z+1.07*s),.7*s)


def billowed_roof():
    # Low rounded hip canopy, generous edge overhang and broad diamond islands.
    outline=[(-1.65,-1.03),(1.65,-1.03),(1.65,1.03),(-1.65,1.03)]
    for edge in range(4):
        a=outline[edge];b=outline[(edge+1)%4];vs=[];uv=[]
        for j in range(13):
            t=j/12;contract=1-t
            for i in range(25):
                u=i/24;x=(a[0]+(b[0]-a[0])*u)*contract;y=(a[1]+(b[1]-a[1])*u)*contract
                z=2.79+.53*math.sin(t*math.pi/2)-.13*math.sin(math.pi*u)*contract+.055*math.sin(math.pi*t)*math.sin(math.pi*u)
                vs.append((x,y,z));uv.append((.16+x*.21,.18+y*.34))
        # Final row shares the apex; triangles avoid degenerate apex quads.
        faces=[(j*25+i,j*25+i+1,(j+1)*25+i+1,(j+1)*25+i) for j in range(11) for i in range(24)]
        faces += [(11*25+i,11*25+i+1,12*25+i) for i in range(24)]
        mesh('Billowed_Check_Canvas',vs,faces,'cloth',uv,smooth=True)
        hem=[vs[i] for i in range(25)]
        tube('Canopy_Soft_Piped_Edge',hem,.032,'blue',7)
        for segment in range(8):
            u0=segment/8;u1=(segment+1)/8
            verts=[]
            for i in range(9):
                t=i/8;u=u0+(u1-u0)*t
                x=a[0]+(b[0]-a[0])*u;y=a[1]+(b[1]-a[1])*u;z=2.79-.13*math.sin(math.pi*u)
                verts.extend([(x,y,z),(x,y,z-.10-.07*math.sin(math.pi*t))])
            mesh('Round_Canopy_Scallop',verts,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(8)],'blue' if segment%2 else 'fold')
    beam('Canopy_Central_Mast',(0,0,2.7),(0,0,3.38),.12,'post')
    lathe('Canopy_Rounded_Finial',(0,0,3.3),[(0,.10),(.1,.12),(.2,.055),(.22,.015)],'brass',segments=10)
    for y in (-.83,.83):beam('Canopy_Eave',(-1.6,y,2.72),(1.6,y,2.72),.15,'wood')
    for x in (-1.55,1.55):
        lantern('Canopy_Lantern',(x,-.91,2.17))
        beam('Lantern_Hanger',(x,-.91,2.69),(x,-.91,2.45),.024,'iron')
        bouquet('Canopy_Floral_Tie',(x,-.95,2.69),.49,3)
