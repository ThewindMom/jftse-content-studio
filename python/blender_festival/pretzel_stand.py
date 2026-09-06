"""Peaked kiosk with faceted counter, suspended pretzels, trays and side barrels."""
from common import *
from stall import counter, roof, plaque

start()
counter(faceted=True)
roof('peak')
plaque()
for x in (-.94,-.55,.55,.94):
    beam('Pretzel_Hanging_Cord',(x,-.65,2.63),(x,-.65,2.13),.016,'cream')
    pretzel('Hanging_Pretzel',(x,-.67,1.99),.16)
for x in (-.74,.67):
    tray('Pretzel_Tray',(x,-.19,1.19),.78,.58)
    for i in range(3): pretzel('Tray_Pretzel',(x-.22+i*.22,-.23,1.35),.12)
for x in (-1.57,1.57): barrel('Side_Barrel',(x,.1,.43),.3,.86)
lathe('Pretzel_Bowl',(.02,.06,1.22),[(0,.17),(.15,.25),(.19,.24)],'cloth')
for i in range(3): pretzel('Bowl_Merchandise',(-.14+i*.13,.05,1.5),.105)
finish('pretzel-stand')
