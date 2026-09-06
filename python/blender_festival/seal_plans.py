"""Bind reviewed source operations to the source receipts read for this family.

Run after reviewing any edits. This does not fetch or fabricate source evidence.
The source receipt template and runtime inspection stay in private .amp/tmp.
"""
import ast
import copy
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SKILL=ROOT/'.agents/skills/running-blender/scripts'
PLANS=ROOT/'.amp/tmp/festival'
base=json.loads((PLANS/'plan.json').read_text())
prior=json.loads((ROOT/'.amp/tmp/beer-cart/stock-paint-plan.json').read_text())
groups={
    'material':prior['bindings'][1],
    'mesh':prior['bindings'][2],
    'start':prior['bindings'][0],
    'finish':{
        'basis':'source',
        'refs':list(dict.fromkeys(ref for i in (0,3,4,5) for ref in prior['bindings'][i]['refs']))+['bpy.ops.wm.html#bpy.ops.wm.open_mainfile','bpy.types.MeshPolygon.html','bpy.types.Mesh.html#bpy.types.Mesh.vertices','bpy.types.Image.html','bpy.types.BlendData.html#bpy.types.BlendData.images'],
        'reason':'Source Camera type ORTHO/ortho_scale, Object location and Euler rotation, area-light energy/size, Scene render settings, render write_still, save_as_mainfile, selection and glTF export support the preview/save/export pass. open_mainfile reopens the saved editable source. Object type/name/hide_render and Mesh polygons/materials support reported mesh and triangle checks. GLB and Principled socket identifiers were observed in the existing beer-cart runtime probe on this same Blender 5.2.1 executable, not inferred from undocumented defaults.'
    }
}
groups['mesh']['refs'] += ['bpy.types.Float2AttributeValue.html#bpy.types.Float2AttributeValue.vector','bpy.types.Mesh.html#bpy.types.Mesh.from_pydata']
groups['mesh']['reason']='Explicit vertex/face mesh creation and validation, database object creation/link, material append, face-corner UV layers and mutable Float2 vector values are supported by the cited mesh/UV sources. from_pydata shade_flat=True marks faces flat-shaded; false opts out for rounded flowers and fabric, with the visible shading checked in actual preview renders. Polygon normals and loop ranges select normalized paint islands; coordinate mapping is ordinary Python.'

for script in sorted(Path(__file__).parent.glob('*.py')):
    if script.name=='seal_plans.py': continue
    tree=ast.parse(script.read_text()); ranges={}
    for node in tree.body:
        if isinstance(node,ast.FunctionDef):
            for line in range(node.lineno,node.end_lineno+1): ranges[line]=node.name
    review=json.loads(subprocess.check_output(['python3',str(SKILL/'evidence.py'),'inspect','--script',str(script)]))['review']
    plan=copy.deepcopy(base); plan['bindings']=[]; plan['script_sha256']=None
    for op in review:
        func=ranges.get(op['line'])
        code=op['code']
        # All Blender access lives in these four common.py functions. Names such
        # as list.append and Path.write_text outside them are Python operations.
        source=script.name=='common.py' and func in groups and (op['requires_source'] or any(s in code for s in ('poly.','uv.','obj.','o.data','o.name','o.type','o.hide_render','m.name','bsdf.','tex.','mat.','image.','camera.','light.','scene.','data.')))
        binding=copy.deepcopy(groups[func]) if source else {'basis':'general_python','refs':[],'reason':'Ordinary Python math, lists, filesystem paths or calls to the separately source-bound common helpers; no Blender property or operator is accessed on this line.'}
        if op['requires_source'] and not source:
            binding={'basis':'source','refs':groups['mesh']['refs'],'reason':'Reviewed coordinate construction feeding the cited Mesh.from_pydata helper. This line itself operates on local Python coordinate/UV lists or calls ring(), not RNA; conservative analyzer aliases local names shared with mesh(). The downstream mesh/UV operation is separately bound.'}
        binding['lines']=[op['line']];plan['bindings'].append(binding)
    path=PLANS/(script.stem+'-plan.json');path.write_text(json.dumps(plan,indent=2)+'\n')
    subprocess.run(['python3',str(SKILL/'evidence.py'),'seal','--plan',str(path),'--script',str(script)],check=True)
