"""Five-bay gentle foreground bow: GLB endpoints +/-7,-1.25, radius20.225."""
from reference_shapes import *

start_reference()
curve_run(7,1.25,5,swag_segments=20)
finish('festival-fence-foreground')
