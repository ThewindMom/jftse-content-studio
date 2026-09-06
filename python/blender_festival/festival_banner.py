"""Tall striped fabric standard, stock-like finial, lantern and floral base."""
from dressing import *

start()
box('Banner_Foot',(0,0,.1),(.48,.48,.2),'end')
striped_mast('Banner_Pole',(0,0,.2),3.1)
banner('Long_Festival_Banner',(.39,-.08,2.95),.67,2.0)
beam('Lantern_Arm',(-.42,0,3.08),(0,0,3.08),.07,'iron')
lantern('Banner_Lantern',(-.43,0,2.69))
cluster('Banner_Top_Foliage',(.06,-.04,2.94),.65,3)
flower_barrel_at((-.18,.08,0),.65)
finish('festival-banner')
