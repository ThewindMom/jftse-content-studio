"""Gabled grill kiosk with sausage rail, grill bars, condiment jars and flowers."""
from common import *
from stall import counter, roof

start()
counter(faceted=True)
roof('gable')
beam('Sausage_Rail',(-1.18,.16,2.46),(1.18,.16,2.46),.07,'iron')
for x in (-1.18,1.18): beam('Sausage_Rail_Mount',(x,.16,2.46),(x,.48,2.46),.07,'iron')
for i in range(5):
    x=-.91+i*.22
    ring('Butcher_Hook',(x,.13,2.38),.055,.012,'iron','Y',10)
    tube('Hanging_Sausage',[(x+.04*math.sin(j*math.pi/8),.12,2.32-j*.055) for j in range(9)],.055,'red' if i%2 else 'bread',8)
box('Grill_Brazier',(-.38,-.18,1.23),(1.15,.7,.19),'iron')
box('Grill_Coals',(-.38,-.18,1.34),(1.02,.6,.025),'red')
for i in range(9): beam('Grill_Bar',(-.86+i*.12,-.51,1.36),(-.86+i*.12,.16,1.36),.027,'iron')
for i in range(4):
    tube('Grilled_Sausage',[(-.68+i*.19+.03*math.sin(j),-.35+j*.075,1.42) for j in range(6)],.045,'bread' if i%2 else 'red',8)
for i in range(3):
    x=.47+i*.24
    lathe('Condiment_Jar',(x,.05,1.18),[(0,.09),(.05,.13),(.23,.12),(.28,.075)],'brass' if i%2 else 'red')
    lathe('Jar_Lid',(x,.05,1.48),[(-.02,.09),(.02,.09)],'cream')
for x in (-1.13,1.13):
    for z in (.7,.85,1): flower('Trailing_Hops',(x,-.84,z),.095)
finish('food-stand')
