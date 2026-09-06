"""Bound rectangular straw bale with visible fiber tufts and two rope belts."""
from dressing import *

start()
MATS['hay']=material('Festival_Painted_Hay',(.6,.45,.15),'hay-paint.png')
box('Bound_Hay_Bale',(0,0,.32),(1.05,.67,.64),'hay',.12)
for x in (-.28,.28):
    tube('Bale_Rope',[(x,-.345,.06),(x,-.345,.61),(x,-.29,.66),(x,.29,.66),(x,.345,.61),(x,.345,.06),(x,-.345,.06)],.018,'brass',5)
for i in range(48):
    x=-.5+(i%12)*.09;y=-.27+(i//12)*.18
    beam('Loose_Straw',(x,y,.642),(x+.06*math.sin(i*1.7),y+.045*math.cos(i),.644),.003,'brass')
finish('hay-bale')
