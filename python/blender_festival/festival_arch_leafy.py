"""Broad compact reference gate with a connected leafy crown and deep drapery."""
from dressing import striped_mast, banner
from reference_shapes import *

start_reference()
for x in (-2,2):
    box('Gate_Pillar_Plinth',(x,0,.16),(.52,.62,.32),'end',.08)
    striped_mast('Gate_Striped_Pillar',(x,0,.28),2.4,.18)
    beam('Gate_Knee',(x,.09,2.17),(x-math.copysign(.53,x),.09,2.73),.18)
    banner('Gate_Hanging_Banner',(x-math.copysign(.46,x),-.08,2.68),.64,1.52)
    barrel('Gate_Flower_Planter',(x,-.1,.38),.36,.76)
    bouquet('Gate_Foot_Flowers',(x,-.14,.95),.97,3)
    bouquet('Gate_Pillar_Flowers',(x,-.12,2.76),1.0,3)
    spill('Gate_Pillar_Trailing',(x,-.19,2.57),1.0)
soft_rail('Gate_Deep_Crown_Beam',-2.15,2.15,2.7)
soft_rail('Gate_Upper_Crown_Beam',-2.15,2.15,2.87)
for a,b in [(-1.96,0),(0,1.96)]:deep_swag('Gate_Full_Fabric',a,b,-.16,2.79,.26)
for i in range(5):
    x=-1.4+i*.7
    bouquet('Gate_Lush_Crown',(x,-.04,2.97+.08*math.cos(x)),.94,3)
shaped_panel('Gate_Shaped_Crest',(0,-.33,2.94),.55)
round_daisy('Gate_Crest_Flower',(0,-.3,3.46),.19)
for x in (-.93,.93):
    beam('Gate_Lantern_Hook',(x,-.05,2.67),(x,-.05,2.29),.03,'iron')
    lantern('Gate_Lantern',(x,-.05,1.96))
finish('festival-arch-leafy')
