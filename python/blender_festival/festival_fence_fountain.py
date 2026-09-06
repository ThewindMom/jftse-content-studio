"""Three continuous curved bays clearing the protected stock fountain.

GLB endpoints X/Z +/-5.6/-2.05; apex origin, groundY0/front+Z.
The exact radius is8.673780487804876; capheight2.025 is not scaled.
"""
from reference_shapes import *

start_reference()
curve_run(5.6,2.05,3)
finish('festival-fence-fountain')
