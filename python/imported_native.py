"""Bounded opaque static GLB -> stock-template DAT/TEX, without collision."""
import hashlib
import io
import json
import math
import os
import re
import struct
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from oktoberfest_native import STATIC_HASH, rebuild_static, triangle_strip, native_texture

IDENTITY = re.compile(r"Studio/Imported/([a-f0-9]{64})\.glb\Z")
ARCHIVE = "Res/StageObj/Imported.res"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ref(items, index):
    require(type(index) is int and 0 <= index < len(items), "Invalid GLB reference")
    return items[index]


def keys(value, allowed):
    require(isinstance(value, dict) and not (value.keys() - set(allowed.split())), "Unsupported GLB field")


def vector(value, size):
    require(isinstance(value, list) and len(value) == size and all(type(x) in (int, float) and math.isfinite(x) for x in value), "Invalid GLB vector")
    return np.asarray(value, dtype=float)


def decode(raw):
    require(28 <= len(raw) <= 16*1024*1024, "GLB size limit")
    require(struct.unpack_from('<3I', raw) == (0x46546c67, 2, len(raw)), "Invalid GLB header")
    size, kind = struct.unpack_from('<2I', raw, 12)
    end = 20+size
    require(size <= 2000000 and size % 4 == 0 and end+8 <= len(raw) and kind == 0x4e4f534a, "Invalid JSON chunk")
    length, kind = struct.unpack_from('<2I', raw, end)
    require(kind == 0x004e4942 and length % 4 == 0 and end+8+length == len(raw), "Invalid BIN chunk")
    g = json.loads(raw[20:end]); binary = memoryview(raw)[end+8:]
    keys(g, 'asset scene scenes nodes meshes materials textures images samplers accessors bufferViews buffers extras extensionsUsed extensionsRequired')
    require(set(g.get('extensionsUsed',[])+g.get('extensionsRequired',[])) <= {'KHR_materials_emissive_strength'}, 'Unsupported extension')
    require(len(g.get('materials',[])) <= 32 and len(g.get('images',[])) <= 16 and len(g.get('textures',[])) <= 32, 'Material/image count budget exceeded')
    require(g['asset']['version'] == '2.0' and len(g['buffers']) == 1, 'Unsupported GLB asset')
    keys(g['buffers'][0], 'byteLength')
    available = g['buffers'][0]['byteLength']
    require(type(available) is int and 0 <= length-available <= 3, 'Invalid buffer length')
    views = []
    for v in g['bufferViews']:
        keys(v, 'buffer byteOffset byteLength byteStride target name')
        offset, count, stride = v.get('byteOffset', 0), v['byteLength'], v.get('byteStride', 0)
        require(v['buffer'] == 0 and all(type(n) is int and n >= 0 for n in (offset,count,stride)) and offset+count <= available and (stride == 0 or 4 <= stride <= 252 and stride % 4 == 0), 'Invalid buffer view')
        views.append((binary[offset:offset+count], stride))
    accessors = []; components = 0
    for a in g['accessors']:
        keys(a, 'bufferView byteOffset componentType count type min max name')
        data, stride = ref(views, a['bufferView'])
        dtype = {5121:'<u1',5123:'<u2',5125:'<u4',5126:'<f4'}.get(a['componentType'])
        channels = {'SCALAR':1,'VEC2':2,'VEC3':3}.get(a['type'])
        require(dtype and channels, 'Unsupported accessor type')
        components += a['count']*channels
        require(components <= 12000000, 'Accessor budget exceeded')
        width = np.dtype(dtype).itemsize; packed = width*channels
        stride = stride or packed; offset = a.get('byteOffset',0); count = a['count']
        require(type(count) is int and 0 < count <= 600000 and type(offset) is int and offset >= 0 and offset % width == 0 and stride >= packed and offset+(count-1)*stride+packed <= len(data), 'Accessor outside view')
        array = np.ndarray((count,channels), dtype=dtype, buffer=data, offset=offset, strides=(stride,width)).copy()
        require(np.isfinite(array).all(), 'Nonfinite accessor')
        accessors.append(array)
    images = []; pixels = 0
    for im in g.get('images',[]):
        keys(im, 'mimeType bufferView name')
        require(im['mimeType'] == 'image/png', 'Embedded PNG required')
        data, _ = ref(views,im['bufferView'])
        require(data[:8] == b'\x89PNG\r\n\x1a\n', 'Invalid PNG')
        image = Image.open(io.BytesIO(data))
        require(1 <= image.width <= 4096 and 1 <= image.height <= 4096, 'PNG dimension limit')
        pixels += image.width*image.height
        require(pixels <= 32000000, 'Texture pixel budget exceeded')
        image = image.convert('RGBA')
        require(image.getchannel('A').getextrema() == (255,255), 'Opaque PNG required')
        images.append(image.convert('RGB'))
    for sampler in g.get('samplers',[]):
        keys(sampler, 'magFilter minFilter wrapS wrapT name')
        require(sampler.get('wrapS',10497) == 10497 and sampler.get('wrapT',10497) == 10497, 'Only repeating native textures supported')
    for texture in g.get('textures',[]):
        keys(texture, 'source sampler name')
        ref(images,texture['source'])
        if 'sampler' in texture: ref(g.get('samplers',[]),texture['sampler'])
    paints = []
    for m in g['materials']:
        keys(m, 'name pbrMetallicRoughness emissiveFactor emissiveTexture doubleSided alphaMode extensions')
        require(m.get('alphaMode','OPAQUE') == 'OPAQUE', 'Opaque material required')
        require(type(m.get('doubleSided',False)) is bool, 'Invalid doubleSided flag')
        p = m.get('pbrMetallicRoughness',{})
        keys(p, 'baseColorFactor baseColorTexture metallicFactor roughnessFactor')
        require(0 <= p.get('metallicFactor',1) <= 1 and 0 <= p.get('roughnessFactor',1) <= 1, 'Invalid PBR factors')
        base = vector(p.get('baseColorFactor',[1,1,1,1]),4)
        emission = vector(m.get('emissiveFactor',[0,0,0]),3)
        require(base[3] == 1 and np.all((base >= 0)&(base <= 1)) and np.all((emission >= 0)&(emission <= 1)), 'Unsupported color factors')
        extensions = m.get('extensions',{})
        keys(extensions, 'KHR_materials_emissive_strength')
        strength = extensions.get('KHR_materials_emissive_strength',{})
        keys(strength, 'emissiveStrength')
        factor = strength.get('emissiveStrength',1)
        require(type(factor) in (int,float) and math.isfinite(factor) and 0 <= factor <= 16, 'Invalid emission strength')
        emission *= factor
        require(not ('baseColorTexture' in p and 'emissiveTexture' in m), 'Combined texture channels unsupported')
        slot = m.get('emissiveTexture',p.get('baseColorTexture'))
        if slot is not None:
            keys(slot, 'index texCoord')
            require(slot.get('texCoord',0) == 0, 'UV0 required')
            image = ref(images,ref(g['textures'],slot['index'])['source'])
            rgb = np.asarray(image,dtype=float)/255
            linear = np.where(rgb <= .04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
            if 'emissiveTexture' in m:
                require(np.all(base[:3] == 0), 'Textured emission requires black base')
                linear *= emission
            else:
                linear = linear*base[:3]+emission
        else:
            linear = np.broadcast_to(base[:3]+emission,(4,4,3))
        rgb = np.where(linear <= .0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
        image = Image.fromarray(np.uint8(np.clip(np.rint(rgb*255),0,255)))
        png = io.BytesIO(); image.save(png,format='PNG')
        paints.append((png.getvalue(),m.get('doubleSided',False)))
    groups = {}; visited = set(); total = 0
    def visit(index, parent, depth=0):
        nonlocal total
        require(depth <= 64 and index not in visited and len(visited) < 2000, 'Invalid scene tree')
        node = ref(g['nodes'],index); visited.add(index)
        keys(node, 'name mesh children matrix translation rotation scale extras')
        if 'matrix' in node:
            require(not any(k in node for k in ('translation','rotation','scale')), 'Mixed node transform')
            local = vector(node['matrix'],16).reshape(4,4).T
        else:
            x,y,z,w = vector(node.get('rotation',[0,0,0,1]),4)
            require(abs(x*x+y*y+z*z+w*w-1) < 1e-4, 'Invalid quaternion')
            local = np.eye(4)
            local[:3,:3] = [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
            local[:3,:3] *= vector(node.get('scale',[1,1,1]),3)
            local[:3,3] = vector(node.get('translation',[0,0,0]),3)
        require(np.allclose(local[3],[0,0,0,1]), 'Non-affine transform')
        world = parent @ local; determinant = np.linalg.det(world[:3,:3])
        require(abs(determinant) > 1e-12, 'Singular transform')
        if 'mesh' in node:
            mesh = ref(g['meshes'],node['mesh']); keys(mesh,'name primitives')
            for part in mesh['primitives']:
                keys(part,'attributes indices material mode')
                require(part.get('mode',4) == 4, 'Triangle lists required')
                attrs = part['attributes']; keys(attrs,'POSITION NORMAL TEXCOORD_0')
                pos = ref(accessors,attrs['POSITION']); normal = ref(accessors,attrs['NORMAL'])
                mat = ref(g['materials'],part['material'])
                require('TEXCOORD_0' in attrs or not ('emissiveTexture' in mat or 'baseColorTexture' in mat.get('pbrMetallicRoughness',{})), 'Textured geometry requires UV0')
                uv = ref(accessors,attrs['TEXCOORD_0']) if 'TEXCOORD_0' in attrs else np.zeros((len(pos),2))
                require(pos.shape == normal.shape == (len(pos),3) and uv.shape == (len(pos),2) and pos.dtype.kind == normal.dtype.kind == 'f' and uv.dtype.kind == 'f', 'Invalid vertex attributes')
                indices = ref(accessors,part['indices']).reshape(-1) if 'indices' in part else np.arange(len(pos))
                require('indices' not in part or ref(accessors,part['indices']).shape[1] == 1, 'Scalar indices required')
                require(indices.dtype.kind == 'u' or 'indices' not in part, 'Unsigned indices required')
                require(len(indices)>0 and len(indices)%3 == 0 and indices.max()<len(pos), 'Invalid triangles')
                total += len(indices)//3; require(total <= 200000, 'Triangle budget exceeded')
                material = part['material']; ref(paints,material)
                vertices, faces = groups.setdefault(material,([],[])); start = len(vertices)
                require(start+len(pos) <= 32768, 'Per-material u16 budget exceeded')
                pos = pos @ world[:3,:3].T + world[:3,3]
                normal = normal @ np.linalg.inv(world[:3,:3])
                lengths = np.linalg.norm(normal,axis=1)
                require(np.all(lengths>1e-10), 'Zero normals')
                normal /= lengths[:,None]
                vertices.extend(np.concatenate((pos,normal,uv),axis=1).tolist())
                triangles = indices.reshape(-1,3)
                if determinant < 0: triangles = triangles[:,[0,2,1]]
                faces.extend((triangles+start).reshape(-1).tolist())
        for child in node.get('children',[]): visit(child,world,depth+1)
    scene = ref(g['scenes'],g.get('scene',0)); keys(scene,'name nodes extras')
    for node in scene['nodes']: visit(node,np.diag([1,1,-1,1]))
    require(groups, 'Empty GLB')
    return groups, paints


def convert(file, template, root=None):
    match = IDENTITY.fullmatch(file)
    require(match is not None, 'Invalid imported identity')
    digest = match[1]
    root = Path(root or os.environ.get('JFTSE_IMPORTED_PROPS',Path(__file__).resolve().parents[1]/'exports/imported-props')).resolve()
    path = root/(digest+'.glb')
    require(path.resolve().parent == root and not path.is_symlink(), 'Imported path escapes storage')
    require(path.is_file(), 'Imported path must be a regular file')
    require(path.stat().st_size <= 16*1024*1024, 'GLB size limit')
    raw = path.read_bytes(); require(hashlib.sha256(raw).hexdigest() == digest, 'Imported SHA256 mismatch')
    groups, paints = decode(raw); files = {}; textures = {}; names = []
    for material,(vertices,faces) in sorted(groups.items()):
        name = 'I'+digest[:20]+f'_{material:03d}'
        png, double = paints[material]
        if double:
            count = len(vertices)
            vertices += [v[:3]+[-n for n in v[3:6]]+v[6:] for v in vertices]
            faces += [i+count for a,b,c in zip(faces[::3],faces[1::3],faces[2::3]) for i in (a,c,b)]
        data = b''.join(struct.pack('<8f',*v) for v in vertices)
        files[name+'.dat'] = rebuild_static(template,data,triangle_strip(faces),name=name,texture=name)
        textures[name+'.tex'] = native_texture(png)
        names.append(ARCHIVE[:-4]+'/'+name+'.dat')
    return names, files, textures


def imported_resources(client, objects):
    identities = sorted({o['file'] for o in objects if o['file'].startswith('Studio/Imported/')})
    if not identities: return {}, {}, {}, []
    with zipfile.ZipFile(client/'Res/MapRes/DecoRes/Mesh00.res') as archive:
        template = archive.read('P0_Barrel01_C01.dat')
    require(hashlib.sha256(template).hexdigest() == STATIC_HASH, 'Unverified static template')
    mapping = {}; files = {}; textures = {}; report = []
    for identity in identities:
        names, parts, paint = convert(identity,template)
        require(not files.keys() & parts.keys(), 'Native name collision')
        mapping[identity] = names; files.update(parts); textures.update(paint)
        report.append({'identity':identity,'parts':names})
    packed = io.BytesIO()
    with zipfile.ZipFile(packed,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in (files|textures).items(): archive.writestr(name,data)
    return mapping, {ARCHIVE:packed.getvalue()}, textures, report
