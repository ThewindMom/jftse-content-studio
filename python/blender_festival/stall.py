"""Timber stall joinery and three explicitly different canvas constructions."""
import math
from common import beam, box, mesh, swag, flower, bow, lantern, pretzel


def counter(faceted=False,braces=False):
    box('Base_Sill',(0,0,.12),(2.65,1.25,.24),'post')
    for x in (-1.18,1.18):
        for y in (-.48,.48):
            box('Corner_Post',(x,y,1.43),(.2,.2,2.86),'post')
            beam('Roof_Knee',(x,y,2.33),(x-math.copysign(.4,x),y,2.75),.12)
    if faceted:
        for a,b in [((-1.25,-.44),(-.85,-.72)),((-.85,-.72),(.85,-.72)),((.85,-.72),(1.25,-.44))]:
            vs=[(x,y,z) for z in (.22,1.03) for x,y in (a,b)]
            mesh('Faceted_Counter_Panel',vs,[(0,1,3,2)],'wood')
            beam('Faceted_Rim',(a[0],a[1],1.09),(b[0],b[1],1.09),.15,'wood')
        mesh('Counter_Top',[(-1.35,.65,1.09),(1.35,.65,1.09),(1.35,-.48,1.09),(.9,-.78,1.09),(-.9,-.78,1.09),(-1.35,-.48,1.09)],[(5,4,3,2,1,0)],'wood')
    else:
        box('Counter_PaintedFront',(0,-.52,.62),(2.36,.12,.8),'wood')
        box('Counter_Top',(0,-.03,1.09),(2.73,1.42,.14),'wood')
    for x in (-1.2,1.2): box('Counter_Side',(x,0,.61),(.12,1.08,.8),'post')
    box('Rear_Work_Shelf',(0,.53,.52),(2.3,.24,.08),'wood')
    for a,b in [(-1.1,0),(0,1.1)]:
        swag('Front_Blue_Underswag',a,b,-.8,1.0,.2,'blue')
        swag('Front_Painted_Swag',a,b,-.82,1.04,.15)
    for x in (-1.1,0,1.1):
        flower('Counter_Flowers',(x,-.86,.83),.13)
    if braces:
        for x in (-1.14,1.14): beam('Diagonal_Base_Brace',(x,-.62,.15),(x-math.copysign(.55,x),-.62,.97),.12)


def roof(kind='gable'):
    if kind=='peak':
        outline=[(-1.5,-.88),(1.5,-.88),(1.5,.88),(-1.5,.88)]
        for edge in range(4):
            a=outline[edge];b=outline[(edge+1)%4];vs=[];uv=[]
            for j in range(7):
                t=j/6
                for i in range(13):
                    u=i/12; x=(a[0]+(b[0]-a[0])*u)*(1-t*.96);y=(a[1]+(b[1]-a[1])*u)*(1-t*.96)
                    z=2.8+.93*t*t-.07*math.sin(math.pi*u)*(1-t)
                    vs.append((x,y,z));uv.append((x/3+.5,y/1.76+.5))
            mesh('Peaked_Canvas_Panel',vs,[(j*13+i,j*13+i+1,(j+1)*13+i+1,(j+1)*13+i) for j in range(6) for i in range(12)],'cloth',uv)
        box('Peak_Finial',(0,0,3.77),(.2,.2,.2),'post')
        beam('Peak_Mast',(0,0,2.7),(0,0,3.8),.12)
    else:
        vs=[];uv=[]
        for i in range(17):
            x=-1.5+3*i/16
            for j in range(13):
                t=j/12;y=-.92+1.84*t
                z=2.8+(.62*(1-abs(2*t-1)) if kind=='gable' else .34*math.sin(math.pi*t))-.045*math.sin(math.pi*i/16)
                vs.append((x,y,z));uv.append((i/16,t))
        mesh('Gabled_Canvas' if kind=='gable' else 'Rounded_Canvas',vs,[(i*13+j,(i+1)*13+j,(i+1)*13+j+1,i*13+j+1) for i in range(16) for j in range(12)],'cloth',uv)
        for x in (-1.5,1.5):
            cap=[(x,-.92+1.84*j/12,2.8+(.62*(1-abs(2*j/12-1)) if kind=='gable' else .34*math.sin(math.pi*j/12))) for j in range(13)]
            mesh('Closed_Canopy_End',cap,[(0,j,j+1) for j in range(1,12)],'fold')
            for side in (-1,1): beam('Gable_Rafter',(x,side*.9,2.76),(x,0,3.36 if kind=='gable' else 3.09),.1)
        beam('Roof_Ridge',(-1.6,0,3.38 if kind=='gable' else 3.09),(1.6,0,3.38 if kind=='gable' else 3.09),.16)
    for y in (-.84,.84):
        beam('Eave_Beam',(-1.62,y,2.75),(1.62,y,2.75),.16)
        for a,b in [(-1.5,-.5),(-.5,.5),(.5,1.5)]:
            swag('Scalloped_Valance',a,b,y,2.8,.13,'stripe')
    for x in (-1.5,1.5):
        bow('Eave_Bow',(x,-.92,2.75))
        beam('Lantern_Hook',(x,-.85,2.72),(x+math.copysign(.18,x),-.86,2.43),.035,'iron')
        lantern('Eave_Lantern',(x+math.copysign(.18,x),-.86,2.08))


def plaque(heart_crest=False):
    box('Carved_Sign_Board',(0,-.98,2.73),(1.02,.12,.45),'end',.13)
    if not heart_crest: pretzel('Pretzel_Crest',(0,-1.07,2.76),.23)
    for x in (-.39,.39): flower('Sign_Rosette',(x,-1.06,2.73),.065)
