"""Three coopered barrels on a deck, tap, tankards, hops sack and draped cloth."""
from common import *

start()
for i in range(6): box('Deck_Plank',(-1.05+i*.42,0,.12),(.41,1.65,.24),'wood')
for x in (-1.17,1.17): box('Deck_Corner',(x,-.72,.27),(.14,.14,.52),'post')
barrel('Upright_Cask',(-.57,.33,.98),.46,1.48)
barrel('Large_Horizontal_Cask',(.58,.3,1.2),.55,.83,True)
barrel('Small_Horizontal_Cask',(-.65,-.23,.68),.36,.61,True)
for x in (.2,.96): beam('Keg_Cradle',(x,.3,.27),(x,.3,.82),.15)
beam('Tap_Body',(.58,-.15,1.16),(.58,-.44,1.16),.065,'brass')
tube('Tap_Elbow',[(.58,-.4,1.16),(.58,-.51,1.12),(.58,-.52,.99)],.035,'brass')
beam('Tap_Lever',(.58,-.37,1.15),(.58,-.37,1.35),.033,'brass')
box('Tap_TBar',(.58,-.37,1.35),(.17,.04,.05),'brass')
for x in (-.08,.45,.95): mug('Deck_Tankard',(x,-.59,.25),.85)
pretzel('Upright_Pretzel',(-.57,.28,1.97),.23)
vs=[];uv=[]
for j in range(13):
    t=j/12;a=math.pi*.9*t
    for side in (-1,1):
        vs.append((.58+.57*math.sin(a),.25+side*.24,1.2+.57*math.cos(a)));uv.append(((side+1)/2,t))
mesh('Cask_Diamond_Drape',vs,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(12)],'cloth',uv)
lathe('Hops_Sack',(-1,-.63,.24),[(0,.24),(.2,.29),(.44,.19),(.49,.22)],'fold',segments=10)
for i in range(5): flower('Sack_Hops',(-1+.1*math.sin(i*2),-.68,.73+.08*math.cos(i)),.105)
bunting('Deck_Bunting',-1.06,1.06,-.86,.49,7)
bow('Cask_Bow',(-.55,-.62,.5))
finish('barrel-display')
