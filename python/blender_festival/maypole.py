"""Spiral mast, heraldic shield, floral ring, streamers and directional signs."""
from common import *

start()
lathe('Round_Platform',(0,0,0),[(0,.83),(.12,.89),(.38,.89),(.43,.82)],'wood',segments=16)
ring('Platform_Rim',(0,0,.42),.82,.06,'post',segments=16)
lathe('Cream_Mast',(0,0,.4),[(0,.115),(4.05,.115)],'cream',segments=16)
vs=[];uv=[]
for i in range(145):
    t=i/144;a=t*math.pi*12
    for offset in (0,.14):
        vs.append((.119*math.cos(a),.119*math.sin(a),.43+3.76*t+offset));uv.append((offset/.14,t*6))
mesh('Blue_Spiral_Mast_Paint',vs,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(144)],'blue',uv)
ring('Floral_Wreath_Structure',(0,0,3.24),.86,.09,'green',segments=32)
for i in range(14):
    a=i*2*math.pi/14
    flower('Wreath_Flowers',(.86*math.cos(a),.86*math.sin(a)-.04,3.25),.115)
for i in range(6):
    a=i*math.pi/3
    beam('Wreath_Suspension',(0,0,4.22),(.84*math.cos(a),.84*math.sin(a),3.24),.018,'cream')
    vs=[];uv=[]
    for j in range(13):
        t=j/12;r=.14+1.22*t
        z=4.22-2.1*t+.2*math.sin(math.pi*t)
        wave=.13*math.sin(t*math.pi*2)*t
        for side in (-1,1):
            vs.append((r*math.cos(a)+(side*.13+wave)*math.sin(a),r*math.sin(a)-(side*.13+wave)*math.cos(a),z));uv.append(((side+1)/2,t))
    mesh('Long_Wreath_Streamer',vs,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(12)],'blue' if i%2 else 'fold',uv)
shield=[(-.25,4.35),(.25,4.35),(.3,4.08),(.19,3.85),(0,3.69),(-.19,3.85),(-.3,4.08)]
mesh('Shield_Crown',[(x,-.18,z) for x,z in shield],[(0,1,2,3,4,5,6)],'cloth')
tube('Shield_Gold_Edge',[(x,-.21,z) for x,z in shield+shield[:1]],.034,'brass')
box('Crown_Finial',(0,0,4.5),(.2,.2,.15),'post')
for side,z in [(-1,1.83),(1,1.53)]:
    xs=[.08,.85,1.03,.85,.08];zs=[z+.17,z+.17,z,z-.17,z-.17]
    mesh('Directional_Sign',[(side*x,-.04,h) for x,h in zip(xs,zs)],[(0,1,2,3,4)],'end')
    if side<0: pretzel('Pretzel_Direction',(-.51,-.09,z),.13)
    else:
        box('Beer_Direction_Icon',(.48,-.1,z),(.18,.035,.22),'cream')
        ring('Beer_Icon_Handle',(.62,-.1,z),.06,.015,'cream','Y',10)
for x in (-.67,.67):
    beam('Lantern_Wreath_Hook',(x,0,3.23),(x,0,2.94),.018,'iron')
    lantern('Wreath_Lantern',(x,0,2.59))
for i in range(6):
    a=i*math.pi/3;flower('Platform_Floral',(.72*math.cos(a),.72*math.sin(a),.47),.15)
finish('maypole')
