"""Trestle table joinery and fabric laid along physical drape paths."""
from common import *


def table(length=3.1,festive=False):
    for j in range(4): box('Tabletop_Plank',(0,-.45+j*.3,1.04),(length,.29,.13),'wood')
    for x in (-length*.32,length*.32):
        for side in (-1,1):
            beam('Table_Trestle',(x,side*.57,.08),(x,-side*.3,.98),.2)
        beam('Table_Trestle_Crossbar',(x,-.55,.8),(x,.55,.8),.19)
    beam('Long_Stretcher',(-length*.32,0,.41),(length*.32,0,.41),.15)
    for y in (-1.0,1.0):
        box('Bench_Seat',(0,y,.55),(length,.38,.16),'wood')
        for x in (-length*.34,length*.34):
            for side in (-1,1):
                beam('Bench_Splayed_Foot',(x+side*.16,y,.07),(x+side*.06,y,.49),.13)
        beam('Bench_Stretcher',(-length*.34,y,.25),(length*.34,y,.25),.1)
    for x in (-length*.3,length*.3):
        drape('Table_Checked_Runner',x,.45,[(-.92,.48),(-.65,.93),(-.58,1.12),(.58,1.12),(.65,.93),(.92,.48)])
    for y in (-1,1):
        if festive:
            mesh('Bench_Long_Checked_Runner',[(-length/2,y-.15,.638),(length/2,y-.15,.638),(length/2,y+.15,.638),(-length/2,y+.15,.638)],[(0,1,2,3)],'cloth',[(0,0),(2,0),(2,.3),(0,.3)])
        else:
            for x in (-length*.31,length*.31):
                drape('Bench_Checked_End',x,.4,[(y-.25,.35),(y-.19,.638),(y+.19,.638),(y+.25,.35)])
    for y in (-.65,.65):
        bunting('Table_Bunting',-length*.39,length*.39,y,.94,7)
    for x in (-length*.44,length*.44):
        for y in (-.66,.66): flower('Table_Corner_Floral',(x,y,.91),.1)


def drape(name,x,width,path):
    vs=[(x+side*width/2,y,z) for y,z in path for side in (-1,1)]
    arc=[0]
    for a,b in zip(path,path[1:]): arc.append(arc[-1]+math.dist(a,b))
    uv=[(i*width/1.8,arc[j]/1.8) for j in range(len(path)) for i in range(2)]
    mesh(name,vs,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(len(path)-1)],'cloth',uv)


def plate(p):
    lathe('Ceramic_Pretzel_Plate',p,[(0,.34),(.025,.39),(.065,.4)],'cream')
    for i in range(3): pretzel('Plate_Pretzel',(p[0]-.1+i*.1,p[1],p[2]+.1+i*.05),.2,flat=True)
