import io
import math
import struct
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageStat

from oktoberfest_models import Model, NAMES, PREFIX, atlas, collision_boxes
from oktoberfest_native import (append_collision, collision_geometry, native_mesh,
                               native_texture, parse_collision, rebuild_static, triangle_strip)
from tex_codec import tex_to_dds
from twinkle_mesh import parse_static_decoration


def fixture(collision=False):
    """Minimal derived format, no client bytes or opaque metadata copied."""
    data = bytearray(32)
    box = struct.pack("<6f", 2, 2, 2, -2, -2, -2)
    data += struct.pack("<4I", 1, 1, 0, 0) + box + struct.pack("<I", 1) + box
    data += struct.pack("<I", 0) if collision else struct.pack("<2I", 1, 0)
    data += struct.pack("<3I", 3, 1, 4)
    for x,y in [(0,0),(1,0),(0,1)]: data += struct.pack("<8f", x,y,0,0,0,1,0,0)
    data += b"Fixture\0".ljust(32,b"x") + b"Z"*272 + b"\0"*4
    index = len(data)
    data += struct.pack("<5H", 0,1,0,1,2)
    data += b"\0"*(-len(data)%4)
    material = len(data)
    data += b"\0\0\1" + b"Fixture\0".ljust(64,b"\0")
    if collision: data += b"\0"*17
    else: data += b"\0\1\0\0\0\0" + b"\0"*4 + b"\1" + b"Atlas\0".ljust(64,b"\0") + b"\0"*3
    data += b"\0"*(-len(data)%4)
    struct.pack_into("<8I",data,0,(len(data)-12)//4,(index-12)//4,(material-12)//4,2,1,0,1,0)
    return bytes(data)


class NativeTests(unittest.TestCase):
    def test_strip_stitching_preserves_winding_without_spurious_faces(self):
        source = [0,1,2, 3,5,4, 6,7,8, 2,7,4]
        strip = triangle_strip(source)
        decoded = []
        for i in range(len(strip)-2):
            a,b,c = strip[i:i+3]
            if len({a,b,c}) != 3: continue
            decoded.extend((b,a,c) if i % 2 else (a,b,c))
        self.assertEqual(decoded, source)

    def test_static_byte_round_trip_and_new_topology(self):
        raw = fixture()
        self.assertEqual(rebuild_static(raw, raw[120:216], [0,1,2]), raw)
        model = Model("Oktoberfest_Test")
        model.box((4,5,6),(2,3,4))
        output = native_mesh(model, raw)
        parsed = parse_static_decoration(output)["primitives"][0]
        count = len(model.positions)//3
        self.assertEqual(parsed["vertexCount"], count*2)
        self.assertEqual(parsed["indices"][:len(model.indices)], model.indices)
        self.assertEqual(parsed["textures"][0]["name"], "Oktoberfest_Atlas")
        self.assertEqual(parsed["materialName"], model.name)
        for i in range(count):
            for j in range(3): self.assertAlmostEqual(parsed["positions"][i][j],model.positions[i*3+j],places=5)
            self.assertEqual(parsed["normals"][i+count], [-n for n in parsed["normals"][i]])
        index = struct.unpack_from("<I",output,4)[0]*4+12
        self.assertEqual(output[index-276:index-4], b"Z"*272)
        with self.assertRaises(ValueError): rebuild_static(raw, raw[120:216], [0,1,3])
        with self.assertRaises(ValueError): rebuild_static(raw, raw[120:216], [0,1,2], name="X"*32)

    def test_collision_retains_stock_and_rejects_every_truncation(self):
        raw = fixture(True)
        before, old_indices, old_index, old_material = parse_collision(raw)
        self.assertEqual(append_collision(raw, [], []), raw)
        added = [(10,0,0,0,0,1,0,0),(12,0,0,0,0,1,0,0),(10,2,0,0,0,1,0,0)]
        output = append_collision(raw, added, [0,1,2])
        after, indices, index, material = parse_collision(output)
        self.assertEqual(after, before+added)
        self.assertEqual(indices, old_indices+[3,4,5])
        self.assertEqual(output[index-308:index], raw[old_index-308:old_index])
        self.assertEqual(output[material:], raw[old_material:])
        for end in range(len(raw)):
            with self.assertRaises(ValueError): parse_collision(raw[:end])
        corrupt = bytearray(raw)
        struct.pack_into("<H",corrupt,old_index+4,3)
        with self.assertRaises(ValueError): parse_collision(corrupt)
        with self.assertRaises(ValueError): append_collision(raw, [(math.nan,)*8]*3, [0,1,2])

    def test_collision_transforms_and_exclusion(self):
        obj = {"file": PREFIX+"Oktoberfest_Maypole.glb", "visible":True, "position":[10,2,30], "rotation":90, "scale":2}
        vertices, triangles = collision_geometry([obj])
        self.assertEqual(len(vertices),24)
        self.assertEqual(len(triangles),36)
        for vertex in vertices:
            self.assertGreater(sum((vertex[i]-[10,42,30][i])*vertex[i+3] for i in range(3)),0)
        self.assertAlmostEqual(min(p[0] for p in vertices),8)
        self.assertAlmostEqual(max(p[0] for p in vertices),12)
        self.assertAlmostEqual(min(p[1] for p in vertices),2)
        self.assertAlmostEqual(max(p[1] for p in vertices),82)
        self.assertEqual(collision_geometry([{**obj,"visible":False}]),([],[]))
        for name in NAMES:
            if name in ("Oktoberfest_HouseBanner", "Oktoberfest_FountainGarland", "Oktoberfest_FountainCrown", "Oktoberfest_CourtCrest", "Oktoberfest_NetDressing", "Oktoberfest_JudgeDressing"):
                self.assertEqual(collision_boxes(name), [])
                self.assertEqual(collision_geometry([{**obj,"file":PREFIX+name+".glb"}]), ([],[]))
            else:
                self.assertTrue(collision_boxes(name))
        # The entrance remains open at center, unlike a whole-model AABB.
        for center,size in collision_boxes("Oktoberfest_FestivalArch"):
            self.assertGreater(abs(center[0]),size[0]/2)

    def test_native_tex_matches_observed_stock_dxt1_headers_and_all_mips(self):
        data = tex_to_dds(native_texture())
        self.assertEqual(data[:4], b"DDS ")
        # Scalar fields observed in stock 512-square SV_Tent00_A/SV_Tent01_A.
        self.assertEqual(struct.unpack_from("<7I",data,4), (124,0xA1007,512,512,131072,0,10))
        self.assertEqual(data[32:76], bytes(44))
        self.assertEqual(struct.unpack_from("<II4s5I",data,76), (32,4,b"DXT1",0,0,0,0,0))
        self.assertEqual(struct.unpack_from("<5I",data,108), (0x401008,0,0,0,0))
        self.assertEqual(len(data),174904)
        offset = 128
        original = Image.open(io.BytesIO(atlas())).convert("RGB")
        for level in range(10):
            side = max(1,512 >> level)
            size = max(1,(side+3)//4)**2 * 8
            header = bytearray(data[:128])
            struct.pack_into("<6I",header,8,0x81007,side,side,size,0,0)
            struct.pack_into("<I",header,108,0x1000)
            decoded = Image.open(io.BytesIO(header+data[offset:offset+size])).convert("RGBA")
            self.assertEqual(decoded.size,(side,side))
            self.assertEqual(decoded.getchannel("A").getextrema(), (255,255))
            error = ImageStat.Stat(ImageChops.difference(decoded.convert("RGB"),original)).mean
            # Below 16px, one DXT1 block spans multiple unrelated atlas swatches;
            # its two endpoints cannot preserve all their colors. Check visual
            # fidelity while swatches remain at least one block wide.
            if side >= 16:
                self.assertLess(max(error),5, f"Mip {level} compression error: {error}")
            offset += size
            original = original.resize((max(1,side//2),max(1,side//2)),Image.Resampling.LANCZOS)
        self.assertEqual(offset,len(data))

    def test_native_dxt1_rejects_transparency_instead_of_discarding_it(self):
        source = io.BytesIO()
        Image.new("RGBA",(4,4),(255,255,255,0)).save(source,format="PNG")
        with patch("oktoberfest_native.atlas",return_value=source.getvalue()):
            with self.assertRaisesRegex(ValueError,"must be opaque"):
                native_texture()


if __name__ == "__main__": unittest.main()
