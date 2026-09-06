"""Longer fully dressed table variant, extended bench cloth and floral centerpiece."""
from common import *
from picnic import table, plate, drape

start()
table(3.5,festive=True)
for x in (-1.13,1.02):
    for y in (-.34,.34): mug('Festive_Tankards',(x,y,1.12),1.03)
plate((-.31,-.18,1.12))
wheat('Full_Wheat_Flower_Centerpiece',(.24,.2,1.12),full=True)
for x in (-1.47,1.47):
    bow('Table_End_Bow',(x,-.65,.92))
    drape('Full_End_Drape',x,.45,[(-.79,.49),(-.61,1.12),(.61,1.12),(.79,.49)])
finish('beer-garden-festive')
