"""Dense perimeter foliage and heraldic fabric derived from the court reference."""
from common import *


def leaf(name,p,length=.2,angle=0,tilt=0,mat='leaf'):
    x,y,z=p
    u=(math.cos(angle),0,math.sin(angle));v=(-math.sin(angle),0,math.cos(angle))
    outline=[(-1,0),(-.45,.42),(.35,.42),(1,0),(.35,-.42),(-.45,-.42)]
    vertices=[(x+length*(a*u[0]+b*v[0]),y+tilt*a,z+length*(a*u[2]+b*v[2])) for a,b in outline]
    vertices.append((x,y-.055,z))
    mesh(name,vertices,[(i,(i+1)%6,6) for i in range(6)],mat)


def daisy(name,p,s=.18,blue=False):
    x,y,z=p
    for i in range(8):
        a=i*math.pi/4
        leaf(name+'_Petal',(x+s*.52*math.cos(a),y,z+s*.52*math.sin(a)),s*.48,a,mat='blue' if blue else 'icing')
    lathe(name+'_Pollen',(x,y-.075,z),[(-.025,s*.23),(0,s*.28),(.025,s*.2)],'brass','Y',8)


def cluster(name,p,s=1,flowers=5):
    x,y,z=p
    for i in range(48):
        a=i*2.39996;r=.12+.28*((i*7)%13)/13
        center=(x+s*r*math.cos(a),y+s*.16*math.sin(i*1.7),z+s*r*.6*math.sin(a))
        leaf(name+'_Foliage',center,s*(.09+.025*(i%3)),a,.025,'leaf' if i%3 else 'green')
    for i in range(flowers):
        a=i*2.39996; r=0 if i==0 else s*.23
        daisy(name+'_Daisy',(x+r*math.cos(a),y-.15*s,z+r*.7*math.sin(a)),s*(.15 if i==0 else .085),blue=i%4==3)


def trailing(name,p,s=1):
    x,y,z=p
    for side in (-1,1):
        points=[(x+side*s*(.08+.09*math.sin(i*.7)),y,z-i*.09*s) for i in range(9)]
        tube(name+'_Stem',points,.017*s,'green',5)
        for i,q in enumerate(points):
            leaf(name+'_Hops',q,.13*s,side*.7+i*.4,.025,'leaf' if i%2 else 'green')


def medallion(name,p,s=.38,icon='pretzel'):
    x,y,z=p
    lathe(name+'_Carved_Plaque',p,[(-.09,s),(-.06,s*1.06),(.05,s*1.06),(.09,s)],'end','Y',12)
    ring(name+'_Gold_Inset',(x,y-.1,z),s*.85,.027,'brass','Y',20)
    if icon=='pretzel': pretzel(name+'_Raised_Pretzel',(x,y-.15,z),s*.62)
    elif icon=='beer':
        box(name+'_Beer_Body',(x,y-.16,z),(s*.65,.055,s*.85),'cream')
        ring(name+'_Beer_Handle',(x+s*.45,y-.17,z),s*.2,.022,'cream','Y',12)


def banner(name,p,w=.65,h=1.65):
    x,y,z=p
    beam(name+'_Crossbar',(x-w*.65,y,z),(x+w*.65,y,z),.07,'brass')
    for i in range(7):
        vertices=[];uv=[]
        for j in range(9):
            t=j/8
            for side in (0,1):
                u=(i+side)/7
                bottom=h-.16*abs(2*u-1)
                vertices.append((x+(u-.5)*w,y-.06*math.sin(u*math.pi*6)-.04*math.sin(t*math.pi),z-t*bottom))
                uv.append((u,t))
        mesh(name+'_Vertical_Stripe',vertices,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(8)],'blue' if i%2==0 else 'fold',uv)
    medallion(name+'_Seal',(x,y-.12,z-h*.47),w*.24)


def flower_barrel_at(p,s=1):
    x,y,z=p
    barrel('Flower_Planter',(x,y,z+.42*s),.4*s,.84*s)
    cluster('Full_Planter_Crown',(x,y-.04,z+.99*s),1.3*s,9)
    cluster('Planter_Rear_Crown',(x,y+.2,z+1.08*s),.85*s,5)
    trailing('Planter_Spilling_Hops',(x+.23*s,y-.33*s,z+.99*s),.66*s)


def striped_mast(name,p,h=3.2,r=.115):
    x,y,z=p
    lathe(name+'_Cream_Mast',p,[(0,r),(h,r)],'fold',segments=16)
    vertices=[];uv=[]
    for i in range(129):
        t=i/128;a=t*math.pi*10
        for delta in (0,.18):
            vertices.append((x+(r+.003)*math.cos(a),y+(r+.003)*math.sin(a),z+t*(h-.18)+delta));uv.append((delta/.18,t))
    mesh(name+'_Spiral_Blue',vertices,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(128)],'blue',uv)
    lathe(name+'_Finial',(x,y,z+h),[(0,r*1.3),(.12,r*1.5),(.24,r*.65),(.3,.015)],'blue',segments=10)


def chalk_sign(kind):
    MATS['chalk']=material('Festival_Chalk_'+kind,(.1,.12,.1),'chalk-'+kind+'.png')
    for x in (-.52,.52):
        beam('AFrame_Front_Leg',(x,-.18,.06),(x,.02,1.68),.12)
        beam('AFrame_Rear_Leg',(x,.68,.06),(x,.02,1.68),.12)
        beam('AFrame_Side_Limiter',(x,-.12,.43),(x,.52,.43),.045,'iron')
    box('Chalkboard_Backing',(0,-.17,1.04),(1.07,.1,1.24),'end')
    mesh('Painted_Chalk_Icon',[(-.46,-.228,.48),(.46,-.228,.48),(.46,-.228,1.6),(-.46,-.228,1.6)],[(0,1,2,3)],'chalk',[(0,0),(1,0),(1,1),(0,1)])
    for x in (-.53,.53): box('Chalkboard_Side_Frame',(x,-.24,1.06),(.12,.15,1.32),'post')
    for z in (.43,1.69): box('Chalkboard_Frame',(0,-.24,z),(1.2,.15,.12),'wood')
    cluster('Sign_Floral',(.52,-.3,.43),.62,3)
