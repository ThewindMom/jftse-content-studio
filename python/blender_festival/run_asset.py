"""Blender entry point for individually source-bound festival builders."""
import runpy
import sys
from pathlib import Path

folder=Path(__file__).resolve().parent
sys.path.insert(0,str(folder))
slug=sys.argv[sys.argv.index('--')+1]
allowed={'pretzel-stand','food-stand','beer-garden','beer-garden-festive','gingerbread-stand','gingerbread-heart','barrel-display','maypole','festival-arch'}
if slug not in allowed:
    raise ValueError(slug)
runpy.run_path(str(folder/(slug.replace('-','_')+'.py')),run_name='__main__')
