"""Braced open gateway with pretzel crest, suspended beer sign and flower barrels."""
from common import *

start()
for x in (-1.42,1.42):
    box('Post_Foot',(x,0,.13),(.46,.7,.26),'end')
    box('Arch_Post',(x,0,1.75),(.26,.28,3.5),'post')
    for y in (-.37,.37): beam('Post_Foot_Brace',(x,y,.18),(x,0,1.07),.16)
    beam('Upper_Knee_Brace',(x,0,2.6),(x-math.copysign(.59,x),0,3.35),.16)
beam('Gate_Top_Beam',(-1.76,0,3.43),(1.76,0,3.43),.25,'wood')
for a,b in [(-1.45,0),(0,1.45)]:
    swag('Top_Blue_Swag',a,b,-.19,3.47,.32,'blue')
    swag('Top_Cream_Swag',a,b,-.23,3.51,.25)
bunting('Gateway_Bunting',-1.21,1.21,-.05,3.0,7)
box('Pretzel_Crest_Board',(0,-.26,3.53),(1.17,.17,.58),'end',.15)
pretzel('Gateway_Pretzel_Crest',(0,-.4,3.55),.29)
for x in (-.47,.47): flower('Crest_Flower',(x,-.36,3.51),.095)
for x in (-.27,.27):
    for j in range(5): ring('Sign_Chain',(x,-.1,3.19-j*.085),.049,.01,'iron','Y',10)
box('Suspended_Beer_Sign',(0,-.1,2.64),(.81,.1,.4),'end',.12)
box('Beer_Icon',(0,-.17,2.64),(.23,.04,.25),'cream')
ring('Beer_Icon_Handle',(.2,-.19,2.65),.085,.021,'cream','Y',12)
for x in (-1.42,1.42):
    bow('Post_Bow',(x,-.19,3.4))
    beam('Lantern_Bracket',(x,-.05,3.38),(x+math.copysign(.31,x),-.07,3.02),.04,'iron')
    lantern('Gateway_Lantern',(x+math.copysign(.31,x),-.07,2.67))
    for dx,h in [(0,.69),(.35,.49)]:
        xx=x+math.copysign(dx,x)
        barrel('Flower_Barrel',(xx,-.1,h/2),.29,h)
        for i in range(6):
            a=i*math.pi/3; flower('Barrel_Flowers',(xx+.18*math.cos(a),-.1+.15*math.sin(a),h+.08),.12)
    for z in (1.5,1.7,1.9): flower('Post_Garland',(x,-.2,z),.11)
    bow('Lower_Post_Bow',(x,-.24,1.48))
finish('festival-arch')
