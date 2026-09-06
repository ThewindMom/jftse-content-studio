"""Gabled cookie shop, pretzel plaque, iced hearts and separate side peg rack."""
from common import *
from stall import counter, roof, plaque

start()
counter()
roof('gable')
plaque()
beam('Cookie_Rail',(-1.07,-.15,2.49),(1.07,-.15,2.49),.06)
for i in range(5):
    x=-.85+i*.42;z=2.04+.1*(i%2)
    beam('Cookie_Ribbon',(x,-.16,2.49),(x,-.16,z+.16),.018,'blue')
    heart('Hanging_Iced_Heart',(x,-.17,z),.19)
tray('Cookie_Tray',(-.35,-.28,1.2),.95,.5)
for i in range(4): heart('Tray_Cookie',(-.66+i*.22,-.32,1.42),.1)
barrel('Cookie_Tub',(-.96,.05,1.35),.18,.33)
for i in range(3):
    beam('Cookie_Stick',(-1.06+i*.1,.02,1.41),(-1.06+i*.1,.02,1.76),.012,'post')
    heart('Stick_Cookie',(-1.06+i*.1,0,1.81),.09)
box('Peg_Rack_Foot',(1.48,.2,.08),(.48,.65,.16),'end')
beam('Peg_Rack_Mast',(1.48,.2,.1),(1.48,.2,2.04),.07)
for z in (1.4,1.92):
    beam('Peg_Rack_Crossbar',(1.22,.2,z),(1.75,.2,z),.05)
    for x in (1.27,1.67):
        beam('Peg_String',(x,.18,z),(x,.18,z-.12),.013,'cream')
        heart('Peg_Heart',(x,.16,z-.22),.11)
finish('gingerbread-stand')
