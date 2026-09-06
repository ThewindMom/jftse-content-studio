"""Stock-painted construction parts. Blender API evidence: private festival plans.

Geometry is authored here as explicit coordinates, not imported from the old
Oktoberfest generators. All component transforms are baked into those coordinates.
"""
import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
PAINT = ROOT / '.amp/tmp/beer-cart/stock-paint'
OBJECTS = []
MATS = {}
POINTS = []


def material(name, color, texture=None):
    mat = bpy.data.materials.new(name)
    nodes = mat.node_tree.nodes
    bsdf = next(n for n in nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = 1
    bsdf.inputs['Metallic'].default_value = 0
    if texture:
        image = bpy.data.images.load(str(PAINT / texture), check_existing=True)
        image.pack()
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.interpolation = 'Linear'
        bsdf.inputs['Base Color'].default_value = (0, 0, 0, 1)
        mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = .8
    return mat


def start():
    for obj in bpy.context.scene.objects:
        obj.hide_render = True
    for name, color, texture in [
        ('wood', (.5,.3,.12), 'wood-planks.png'),
        ('post', (.4,.25,.1), 'wood-planks-tall.png'),
        ('end', (.35,.2,.1), 'wood-stall.png'),
        ('cloth', (.8,.8,.8), 'cloth-diamonds.png'),
        ('fold', (.8,.8,.8), 'canvas-fold.png'),
        ('stripe', (.8,.8,.8), 'cloth-stripes.png'),
        ('blue', (.055,.16,.25), None), ('cream', (.81,.74,.57), None),
        ('iron', (.065,.057,.047), None), ('brass', (.47,.29,.07), None),
        ('bread', (.44,.18,.044), None), ('icing', (.91,.82,.63), None),
        ('heart', (.29,.063,.03), None), ('red', (.46,.11,.066), None),
        ('green', (.115,.22,.047), None), ('leaf', (.23,.33,.077), None),
        ('beer', (.53,.27,.054), None), ('glow', (.9,.6,.17), None),
    ]:
        MATS[name] = material('Festival_' + name, color, texture)


def mesh(name, vertices, faces, mat='wood', uvs=None, preview=False, face_uvs=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    assert not data.validate(), name
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    data.materials.append(MATS[mat])
    uv = data.uv_layers.new(name='StockPaintIslands')
    low = [min(p[a] for p in vertices) for a in range(3)]
    span = [max(p[a] for p in vertices) - low[a] for a in range(3)]
    for pi, poly in enumerate(data.polygons):
        n = tuple(abs(v) for v in poly.normal)
        axes = [a for a in range(3) if a != n.index(max(n))]
        if span[axes[0]] > span[axes[1]]:
            axes.reverse()
        mapped = uvs and all(max(uvs[v][a] for v in faces[pi])-min(uvs[v][a] for v in faces[pi]) > 1e-7 for a in (0,1))
        for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
            vi = data.loops[li].vertex_index
            co = vertices[vi]
            pair = uvs[vi] if mapped else tuple(.02 + .96 * (co[a]-low[a])/max(span[a],1e-6) for a in axes)
            if face_uvs:
                pair = face_uvs[pi][li-poly.loop_start]
            uv.uv[li].vector = pair
    if not preview:
        OBJECTS.append(obj)
        POINTS.extend(vertices)
    return obj


def box(name, p, size, mat='wood', bevel=.035):
    x,y,z=p; a,b,c=(v/2 for v in size); k=min(bevel,a*.35,b*.35)
    ring=[(-a+k,-b), (a-k,-b), (a,-b+k), (a,b-k), (a-k,b),(-a+k,b),(-a,b-k),(-a,-b+k)]
    vs=[(x+i,y+j,z+h) for h in (-c,c) for i,j in ring]
    fs=[tuple(range(7,-1,-1)),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
    return mesh(name,vs,fs,mat)


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def unit(v):
    length=math.sqrt(sum(x*x for x in v))
    return tuple(x/length for x in v)


def beam(name,a,b,width=.15,mat='post'):
    direction=unit(tuple(b[i]-a[i] for i in range(3)))
    u=unit(cross(direction,(0,1,0) if abs(direction[1])<.9 else (1,0,0)))
    v=cross(direction,u)
    vs=[tuple(p[i]+width/2*(s*u[i]+t*v[i]) for i in range(3)) for p in (a,b) for s,t in ((-1,-1),(1,-1),(1,1),(-1,1))]
    island=[(.02,.02),(.98,.02),(.98,.98),(.02,.98)]
    return mesh(name,vs,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,face_uvs=[island]*6)


def lathe(name,p,profile,mat='wood',axis='Z',segments=16):
    vs=[]; uv=[]
    for j,(z,r) in enumerate(profile):
        for i in range(segments+1):
            t=2*math.pi*i/segments; q=(r*math.cos(t),r*math.sin(t),z)
            if axis=='Y': q=(q[0],-q[2],q[1])
            vs.append(tuple(p[k]+q[k] for k in range(3))); uv.append((.02+.96*i/segments,.02+.96*j/(len(profile)-1)))
    fs=[]
    for j in range(len(profile)-1):
        for i in range(segments):
            k=j*(segments+1)+i; fs.append((k,k+1,k+segments+2,k+segments+1))
    fs.extend([tuple(range(segments-1,-1,-1)),tuple((len(profile)-1)*(segments+1)+i for i in range(segments))])
    return mesh(name,vs,fs,mat,uv)


def tube(name,points,r,mat='bread',sides=7):
    vs=[]; uv=[]
    for j,p in enumerate(points):
        a=points[max(0,j-1)]; b=points[min(len(points)-1,j+1)]
        tangent=unit(tuple(b[k]-a[k] for k in range(3)))
        u=unit(cross(tangent,(0,1,0) if abs(tangent[1])<.9 else (1,0,0))); v=cross(tangent,u)
        for i in range(sides):
            t=i*2*math.pi/sides
            vs.append(tuple(p[k]+r*(u[k]*math.cos(t)+v[k]*math.sin(t)) for k in range(3)))
            uv.append((i/sides,j/(len(points)-1)))
    fs=[(j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i) for j in range(len(points)-1) for i in range(sides)]
    fs += [tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+i for i in range(sides))]
    return mesh(name,vs,fs,mat,uv)


def ring(name,p,r,thick,mat='iron',axis='Z',segments=24):
    points=[]
    for i in range(segments+1):
        a=i*2*math.pi/segments; q=(r*math.cos(a),r*math.sin(a),0)
        if axis=='Y': q=(q[0],0,q[1])
        points.append(tuple(p[k]+q[k] for k in range(3)))
    return tube(name,points,thick,mat,6)


def barrel(name,p,r=.35,h=.75,horizontal=False):
    x,y,z=p; axis='Y' if horizontal else 'Z'
    profile=[(-h/2,r*.82),(-h*.38,r*.93),(0,r),(h*.38,r*.93),(h/2,r*.82)]
    lathe(name+'_Staves',p,profile,'post',axis,16)
    for t in (-.39,.39):
        center=(x,y-h*t,z) if horizontal else (x,y,z+h*t)
        ring(name+'_Hoop',center,r*.94,.032,'iron',axis,16)
    head=(x,y-h/2-.013,z) if horizontal else (x,y,z+h/2+.013)
    lathe(name+'_Head',head,[(-.02,r*.8),(.02,r*.8)],'end',axis)


def pretzel(name,p,s=.3,flat=False):
    # Single continuous bent dough with crossed tails and three recognizable holes.
    path=[(-.5,-.3),(-.3,-.15),(.15,.4),(.4,.65),(.7,.65),(.93,.4),(1,.05),(.9,-.32),(.65,-.55),(0,-.68),(-.65,-.55),(-.9,-.32),(-1,.05),(-.93,.4),(-.7,.65),(-.4,.65),(-.15,.4),(.3,-.15),(.5,-.3)]
    points=[(p[0]+x*s,p[1]+z*s if flat else p[1]-.025*math.sin(i),p[2] if flat else p[2]+z*s) for i,(x,z) in enumerate(path)]
    tube(name,points,.16*s,'bread',8)
    for i in (2,5,8,11,14,16):
        q=points[i]; box(name+'_Salt',(q[0],q[1] if flat else q[1]-.13*s,q[2]+.13*s if flat else q[2]),(.025,.015,.024),'icing',.002)


def heart(name,p,s=.3,iced=True):
    outline=[]
    for i in range(40):
        t=2*math.pi*i/40
        outline.append((math.sin(t)**3, (13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t))/16))
    vs=[(p[0]+s*x,p[1]+dy,p[2]+s*z) for dy in (-.035,.035) for x,z in outline]
    vs += [(p[0],p[1]-.035,p[2]),(p[0],p[1]+.035,p[2])]
    fs=[(80,(i+1)%40,i) for i in range(40)]+[(81,40+i,40+(i+1)%40) for i in range(40)]+[(i,(i+1)%40,40+(i+1)%40,40+i) for i in range(40)]
    mesh(name,vs,fs,'heart')
    if iced:
        tube(name+'_Icing',[(p[0]+s*x*.87,p[1]-.05,p[2]+s*z*.87) for x,z in outline+outline[:1]],.018,'icing',6)
        flower(name+'_Rosette',(p[0],p[1]-.075,p[2]),s*.45)


def flower(name,p,s=.15):
    x,y,z=p
    for i in range(5):
        t=i*2*math.pi/5
        lathe(name+'_Petal',(x+s*.45*math.cos(t),y,z+s*.45*math.sin(t)),[(-s*.08,s*.3),(0,s*.37),(s*.08,s*.2)],'icing','Y',6)
    lathe(name+'_Center',(x,y-.035,z),[(-.02,s*.2),(.02,s*.2)],'brass','Y',8)
    for i in range(4):
        t=i*math.pi/2+.4; u=math.cos(t);v=math.sin(t)
        mesh(name+'_Leaf',[(x,y+.02,z),(x+s*1.5*u,y+.015,z+s*1.5*v),(x+s*.6*u-s*.4*v,y+.07,z+s*.6*v+s*.4*u)],[(0,1,2)],'green')


def swag(name,x0,x1,y,z,drop=.3,mat='fold'):
    vs=[]; uv=[]
    for i in range(17):
        t=i/16; dip=drop*math.sin(math.pi*t)
        for j in range(3):
            vs.append((x0+(x1-x0)*t,y-.035*math.sin(j*math.pi/2),z-dip-.09*j));uv.append((t,j/2))
    mesh(name,vs,[(i*3+j,i*3+j+1,i*3+j+4,i*3+j+3) for i in range(16) for j in range(2)],mat,uv)


def bunting(name,x0,x1,y,z,n=7):
    tube(name+'_Cord',[(x0+(x1-x0)*i/16,y,z-.18*math.sin(math.pi*i/16)) for i in range(17)],.018,'cream',5)
    step=(x1-x0)/n
    for i in range(n):
        x=x0+(i+.5)*step; h=z-.18*math.sin(math.pi*(i+.5)/n)
        mesh(name+'_Flag',[(x-step*.44,y,h),(x,y,h-.32),(x+step*.44,y,h)],[(0,1,2)],'cloth' if i%2 else 'blue',[(0,1),(.5,0),(1,1)])


def bow(name,p):
    x,y,z=p
    for side in (-1,1):
        mesh(name+'_Loop',[(x,y,z),(x+side*.28,y-.02,z+.14),(x+side*.24,y-.05,z-.12)],[(0,1,2)],'stripe')
        mesh(name+'_Tail',[(x+side*.02,y,z),(x+side*.12,y,z),(x+side*.22,y-.02,z-.46),(x+side*.08,y-.015,z-.4)],[(0,1,2,3)],'stripe')
    box(name+'_Knot',p,(.1,.07,.12),'cream')


def mug(name,p,s=1):
    x,y,z=p
    lathe(name+'_Tankard',(x,y,z),[(0,.12*s),(.035*s,.15*s),(.31*s,.14*s),(.34*s,.13*s)],'beer')
    for dz in (.04,.29): ring(name+'_Band',(x,y,z+dz*s),.145*s,.014*s,'iron')
    ring(name+'_Handle',(x+.185*s,y,z+.17*s),.105*s,.027*s,'iron','Y',14)
    lathe(name+'_Foam',(x,y,z+.35*s),[(-.025*s,.13*s),(.02*s,.145*s),(.06*s,.1*s)],'icing',segments=10)


def lantern(name,p):
    x,y,z=p
    ring(name+'_Hanger',(x,y,z+.3),.075,.019,'iron','Y',12)
    lathe(name+'_Roof',(x,y,z+.15),[(-.04,.16),(0,.18),(.14,.07)],'iron',segments=4)
    lathe(name+'_Glass',p,[(-.17,.09),(-.1,.14),(.12,.13)],'glow',segments=4)
    lathe(name+'_Foot',(x,y,z-.18),[(-.035,.12),(.035,.16)],'iron',segments=4)
    for sx,sy in ((1,0),(-1,0),(0,1),(0,-1)):
        beam(name+'_Rib',(x+sx*.14,y+sy*.14,z-.12),(x+sx*.13,y+sy*.13,z+.13),.025,'iron')


def tray(name,p,w=.6,d=.38):
    x,y,z=p; box(name+'_Base',p,(w,d,.04),'end')
    for sx in (-1,1): box(name+'_Side',(x+sx*w/2,y,z+.07),(.035,d,.14),'wood')
    for sy in (-1,1): box(name+'_Rim',(x,y+sy*d/2,z+.07),(w,.035,.14),'wood')


def wheat(name,p,full=False):
    x,y,z=p
    lathe(name+'_Vase',p,[(0,.13),(.12,.18),(.3,.1),(.34,.11)],'blue')
    for i in range(7 if full else 5):
        dx=(i-3)*.055; h=.64+.11*math.sin(i*1.6)
        beam(name+'_Stem',(x,y,z+.22),(x+dx,y+.03*math.sin(i),z+h),.016,'brass')
        for j in range(4):
            for side in (-1,1):
                beam(name+'_Grain',(x+dx,y,z+h-.035*j),(x+dx+side*.043,y,z+h-.035*j+.05),.033,'cream')
    if full:
        for i in range(5): flower(name+'_Flowers',(x+.2*math.cos(i*1.3),y-.1,z+.33+.08*math.sin(i)),.1)


def finish(slug):
    out=ROOT/'exports/blender-festival'/slug; out.mkdir(parents=True,exist_ok=True)
    low=[min(p[a] for p in POINTS) for a in range(3)]; high=[max(p[a] for p in POINTS) for a in range(3)]
    ground=low[2]
    for obj in OBJECTS:
        obj.location=(0,0,-ground)
    high[2]-=ground;low[2]=0
    center=tuple((low[a]+high[a])/2 for a in range(3)); size=max(high[a]-low[a] for a in range(3))
    camera_data=bpy.data.cameras.new('PREVIEW_Camera')
    camera=bpy.data.objects.new('PREVIEW_Camera',camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera_data.type='ORTHO'
    camera_data.ortho_scale=size*1.5
    bpy.context.scene.camera=camera
    for name,loc,energy in [('Key',(-3,-4,7),1000),('Fill',(4,-2,5),500)]:
        light=bpy.data.lights.new('PREVIEW_'+name,'AREA')
        light.energy=energy;light.size=5
        obj=bpy.data.objects.new('PREVIEW_'+name,light)
        bpy.context.scene.collection.objects.link(obj);obj.location=loc
    MATS['sky']=material('PREVIEW_Sky',(.24,.36,.43))
    mesh('PREVIEW_Floor',[(-200,-200,low[2]-.04),(200,-200,low[2]-.04),(200,200,low[2]-.04),(-200,200,low[2]-.04)],[(0,1,2,3)],'sky',preview=True)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    for angle,label in [(-.42,'preview'),(math.pi+.42,'rear'),(0,'front')]:
        elevation=.32 if size>3.6 else .43
        camera.location=(center[0]+8*math.sin(angle),center[1]-8*math.cos(angle),center[2]+8*math.tan(elevation))
        camera.rotation_euler=(math.pi/2-elevation,0,angle)
        scene.render.filepath=str(out/(label+'.png'))
        bpy.ops.render.render(write_still=True)
        if label=='preview': bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True,check_existing=False)
    for obj in scene.objects: obj.select_set(False)
    for obj in OBJECTS: obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out/(slug+'.glb')),export_format='GLB',use_selection=True,export_animations=False,export_skins=False,export_morph=False,export_cameras=False,export_lights=False,export_draco_mesh_compression_enable=False,export_meshopt_compression_enable=False,export_yup=True,export_apply=True,export_materials='EXPORT',export_image_format='AUTO')
    report={'slug':slug,'boundsBlenderZUp':{'min':low,'max':high},'triangles':sum(len(p.vertices)-2 for o in OBJECTS for p in o.data.polygons),'materials':len({m.name for o in OBJECTS for m in o.data.materials}),'meshes':len(OBJECTS)}
    (out/'model-report.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(out/(slug+'.blend')),load_ui=False,use_scripts=False)
    saved=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('PREVIEW_') and not o.hide_render]
    assert len(saved)==report['meshes'], (slug,len(saved),report)
    report['reopenedMeshCount']=len(saved)
    report['origin']='Ground center of construction; Blender Z up/front -Y; GLB Y up/front +Z'
    report['packedImages']=sum(bool(image.packed_file) for image in bpy.data.images)
    assert report['packedImages']>=3
    (out/'model-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('FESTIVAL_RESULT',json.dumps(report))
