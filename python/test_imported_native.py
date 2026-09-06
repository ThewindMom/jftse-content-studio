import copy
import hashlib
import io
import json
import os
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from imported_native import convert, decode, imported_resources, ARCHIVE
from test_oktoberfest_native import fixture
from test_twinkle_studio import SOURCE
from twinkle_studio import compile_layout, initial_document, export_layout
from twinkle_mesh import parse_static_decoration
from tex_codec import tex_to_dds
from client_crypto import encrypt_set_file, decrypt_set_file


def sample():
    chunks = [struct.pack('<9f',0,0,1, 1,0,1, 0,1,1),
              struct.pack('<9f',0,0,1, 0,0,1, 0,0,1),
              struct.pack('<6f',0,0, 1,0, 0,1),struct.pack('<3H',0,1,2)]
    image = io.BytesIO(); Image.new('RGB',(4,4),(128,64,32)).save(image,format='PNG')
    chunks.append(image.getvalue()); binary = bytearray(); views=[]
    for chunk in chunks:
        binary.extend(b'\0'*(-len(binary)%4))
        views.append({'buffer':0,'byteOffset':len(binary),'byteLength':len(chunk)})
        binary.extend(chunk)
    g = {'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
         'nodes':[{'translation':[10,2,3],'children':[1]},{'mesh':0,'scale':[2,3,4]}],
         'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'TEXCOORD_0':2},'indices':3,'material':0}]}],
         'materials':[{'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[0,0,0,1],'metallicFactor':0},'emissiveFactor':[.8,.8,.8],'emissiveTexture':{'index':0}}],
         'textures':[{'source':0}],'images':[{'mimeType':'image/png','bufferView':4}],
         'accessors':[{'bufferView':i,'componentType':5123 if i==3 else 5126,'count':3,'type':t} for i,t in enumerate(('VEC3','VEC3','VEC2','SCALAR'))],
         'buffers':[{'byteLength':len(binary)}],'bufferViews':views}
    return g, bytes(binary)


def encode(g,binary):
    metadata=json.dumps(g).encode(); metadata+=b' '*(-len(metadata)%4)
    binary+=b'\0'*(-len(binary)%4)
    return struct.pack('<5I',0x46546c67,2,28+len(metadata)+len(binary),len(metadata),0x4e4f534a)+metadata+struct.pack('<2I',len(binary),0x004e4942)+binary


class ImportedTests(unittest.TestCase):
    def test_transform_normals_reflection_and_color(self):
        g,b=sample(); groups,paints=decode(encode(g,b))
        vertices,indices=groups[0]
        np.testing.assert_allclose(np.array(vertices)[:,:3],[[10,2,-7],[12,2,-7],[10,5,-7]])
        np.testing.assert_allclose(np.array(vertices)[:,3:6],[[0,0,-1]]*3)
        self.assertEqual(indices,[0,2,1])
        self.assertEqual(vertices[1][6:],[1,0])
        pixel=Image.open(io.BytesIO(paints[0][0])).getpixel((0,0))
        self.assertEqual(pixel,(115,57,28))
        g['nodes'][1]['scale'][0]=-2
        self.assertEqual(decode(encode(g,b))[0][0][1],[0,1,2])
        g['nodes'][1]={'mesh':0,'matrix':[2,0,0,0, 1,3,0,0, 0,0,4,0, 0,0,0,1]}
        np.testing.assert_allclose(np.array(decode(encode(g,b))[0][0][0])[2,:3],[11,5,-7])
        g,b=sample();b=bytearray(b)
        struct.pack_into('<9f',b,g['bufferViews'][1]['byteOffset'],*([0,2**-.5,2**-.5]*3))
        np.testing.assert_allclose(np.array(decode(encode(g,bytes(b)))[0][0][0])[:,3:6],[[0,.8,-.6]]*3)

    def test_rejects_unsupported_and_corrupt_glbs(self):
        original,b=sample()
        changes=[lambda g:g.update(animations=[{}]),
                 lambda g:g['buffers'][0].update(uri='../../secret'),
                 lambda g:g['materials'][0].update(alphaMode='BLEND'),
                 lambda g:g['materials'][0].update(normalTexture={'index':0}),
                 lambda g:g['materials'][0].update(doubleSided='true'),
                 lambda g:g['materials'][0]['pbrMetallicRoughness'].update(metallicFactor=float('nan')),
                 lambda g:g['accessors'][3].update(type='VEC3',count=1),
                 lambda g:g['nodes'][1].update(children=[0]),
                 lambda g:g['nodes'][1].update(scale=[0,1,1]),
                 lambda g:g['accessors'][0].update(sparse={}),
                 lambda g:g['accessors'][0].update(byteOffset=99999),
                 lambda g:g['materials'][0]['emissiveTexture'].update(texCoord=1),
                 lambda g:g['meshes'][0]['primitives'][0].update(mode=5),
                 lambda g:g['meshes'][0]['primitives'][0]['attributes'].pop('TEXCOORD_0')]
        for change in changes:
            g=copy.deepcopy(original);change(g)
            with self.subTest(change=change), self.assertRaises(ValueError): decode(encode(g,b))
        raw=encode(original,b)
        for end in (0,12,27,len(raw)-1):
            with self.assertRaises(ValueError): decode(raw[:end])

    def test_aggregate_and_u16_budgets(self):
        g,b=sample()
        g['materials'] *= 33
        with self.assertRaisesRegex(ValueError,'count budget'):decode(encode(g,b))
        g,b=sample(); g['meshes'][0]['primitives'] *= 10923
        with self.assertRaisesRegex(ValueError,'u16 budget'):decode(encode(g,b))
        g,b=sample()
        g['accessors']=[{'bufferView':0,'componentType':5126,'count':600000,'type':'VEC3'}]*7
        b=bytes(7200000);g['buffers'][0]['byteLength']=len(b);g['bufferViews']=[{'buffer':0,'byteLength':len(b)}]
        with self.assertRaisesRegex(ValueError,'Accessor budget'):decode(encode(g,b))
        g,b=sample();g['images']*=8
        tiny=Image.new('RGBA',(1,1),(0,0,0,255))
        with patch('imported_native.Image.open') as image:
            image.return_value.width=image.return_value.height=2048
            image.return_value.convert.return_value=tiny
            with self.assertRaisesRegex(ValueError,'pixel budget'):decode(encode(g,b))

    def test_hash_path_and_native_roundtrip(self):
        g,b=sample(); raw=encode(g,b); digest=hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); path=root/(digest+'.glb');path.write_bytes(raw)
            identity='Studio/Imported/'+digest+'.glb'
            names,parts,textures=convert(identity,fixture(),root)
            parsed=parse_static_decoration(next(iter(parts.values())))['primitives'][0]
            self.assertEqual(parsed['vertexCount'],6)
            self.assertEqual(parsed['indices'],[0,2,1,3,4,5])
            self.assertEqual(parsed['positions'][0],[10,2,-7])
            self.assertEqual(parsed['normals'][3],[0,0,1])
            image=Image.open(io.BytesIO(tex_to_dds(next(iter(textures.values())))))
            self.assertEqual(image.size,(4,4));image.load()
            self.assertEqual(parsed['textures'][0]['name']+'.tex',next(iter(textures)))
            path.write_bytes(raw+b'bad')
            with self.assertRaisesRegex(ValueError,'SHA256'): convert(identity,fixture(),root)
            with self.assertRaisesRegex(ValueError,'identity'): convert('Studio/Imported/../../bad.glb',fixture(),root)
            path.unlink();path.symlink_to(root/'elsewhere')
            with self.assertRaisesRegex(ValueError,'path'): convert(identity,fixture(),root)
            path.unlink();os.mkfifo(path)
            with self.assertRaisesRegex(ValueError,'regular file'): convert(identity,fixture(),root)

    def test_material_split_set_expansion_cache_and_private_bundle(self):
        g,b=sample();g['materials'].append({'pbrMetallicRoughness':{'baseColorFactor':[.25,.5,1,1],'metallicFactor':0}})
        g['meshes'][0]['primitives'].append({**g['meshes'][0]['primitives'][0],'material':1})
        raw=encode(g,b);digest=hashlib.sha256(raw).hexdigest();identity='Studio/Imported/'+digest+'.glb'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/(digest+'.glb')).write_bytes(raw)
            client=root/'client';(client/'Res/MapRes/DecoRes').mkdir(parents=True);(client/'Res/Stage').mkdir(parents=True)
            with zipfile.ZipFile(client/'Res/MapRes/DecoRes/Mesh00.res','w') as z:z.writestr('P0_Barrel01_C01.dat',fixture())
            with zipfile.ZipFile(client/'Res/Stage/Info.res','w') as z:z.writestr('2_Twinkle_Town.set',encrypt_set_file(SOURCE.encode()))
            with zipfile.ZipFile(client/'Res/Stage/Tex010.res','w') as z:z.writestr('original.tex',b'unchanged')
            doc=initial_document(SOURCE)
            doc['objects'] += [{**doc['objects'][0],'id':f'import-{i}','file':identity} for i in range(2)]
            with patch.dict(os.environ,{'JFTSE_IMPORTED_PROPS':str(root)}),patch('imported_native.STATIC_HASH',hashlib.sha256(fixture()).hexdigest()),patch('imported_native.convert',wraps=convert) as call:
                mapping,resources,textures,report=imported_resources(client,doc['objects'])
                self.assertEqual(call.call_count,1)
                compiled=compile_layout(SOURCE,doc,mapping)
                objects=initial_document(compiled)['objects']
                self.assertEqual(len(objects),5)
                for o in objects[1:]:
                    self.assertIn(o['file'],mapping[identity]);self.assertEqual(o['position'],doc['objects'][0]['position']);self.assertEqual(o['animation'],-1)
                export_layout(client,doc,root/'out')
            with zipfile.ZipFile(root/'out/twinkle-layout.zip') as bundle:
                self.assertNotIn('Res/Collision.res',bundle.namelist())
                self.assertFalse(json.loads(bundle.read('native-export.json'))['nativeRuntimeVerified'])
                with zipfile.ZipFile(io.BytesIO(bundle.read(ARCHIVE))) as packed:
                    self.assertEqual(len(packed.namelist()),4)
                with zipfile.ZipFile(io.BytesIO(bundle.read('Res/Stage/Info.res'))) as info:
                    self.assertEqual(decrypt_set_file(info.read('2_Twinkle_Town.set')).decode(),compiled)
                with zipfile.ZipFile(io.BytesIO(bundle.read('Res/Stage/Tex010.res'))) as tex:
                    self.assertEqual(tex.read('original.tex'),b'unchanged')
                    for name in textures:self.assertEqual(tex.read(name),textures[name])


if __name__=='__main__':unittest.main()
