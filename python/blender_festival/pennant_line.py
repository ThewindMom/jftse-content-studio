"""Freely placeable overhead blue/cream pennant span; origin is lowest tip."""
from dressing import *
start()
bunting('Overhead_Pennant_Line',-2.5,2.5,0,.6,13)
for x in (-2.5,2.5): ring('Rope_Tie',(x,0,.6),.065,.016,'cream','Y',10)
finish('pennant-line')
