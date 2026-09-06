"""Rounded canopy heart shop with large asymmetric hanging cookies and base braces."""
from common import *
from stall import counter, roof, plaque

start()
counter(braces=True)
roof('round')
plaque(heart_crest=True)
heart('Heart_Crest',(0,-1.07,2.78),.22)
for x,z,s in [(-.88,2.12,.24),(0,2.0,.36),(.86,1.94,.28),(-.47,1.56,.13),(.54,1.48,.13),(.55,2.38,.1)]:
    beam('Blue_Cookie_Ribbon',(x,-.15,2.71),(x,-.15,z+s*.8),.023,'blue')
    heart('Large_Heart_Cookie',(x,-.19,z),s)
tray('Heart_Tray',(.53,-.22,1.21),1.02,.55)
for i in range(3): heart('Heart_Tray_Cookie',(.24+i*.26,-.27,1.45),.13)
barrel('Cookie_Bucket',(-.72,-.05,1.38),.23,.45)
bow('Bucket_Bow',(-.72,-.27,1.36))
for i in range(3):
    beam('Bucket_Stick',(-.88+i*.15,-.04,1.54),(-.88+i*.15,-.04,1.84),.015,'post')
    pretzel('Bucket_Pretzel',(-.88+i*.15,-.04,1.88),.09)
finish('gingerbread-heart')
