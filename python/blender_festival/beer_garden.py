"""Compact picnic table with two benches, four tankards, pretzels and wheat."""
from common import *
from picnic import table, plate

start()
table()
for x in (-.95,.95):
    for y in (-.33,.33): mug('Four_Table_Tankards',(x,y,1.12),.87)
plate((-.18,-.12,1.12))
wheat('Wheat_Vase',(.25,.22,1.12))
finish('beer-garden')
