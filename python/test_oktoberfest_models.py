import json
import math
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from oktoberfest_models import (ASSET_BUILDERS, NAMES, PREFIX, Model, add,
                                build_model, collision_boxes, cross, mul,
                                prepare_originals)
from twinkle_studio import initial_document, compile_layout


class OriginalModelTests(unittest.TestCase):
    def test_festzelt_has_peaked_canopy_and_open_service_access(self):
        model = build_model("Oktoberfest_Festzelt")
        self.assertEqual(max(model.positions[1::3]), 65)
        self.assertLessEqual(max(abs(x) for x in model.positions[0::3]), 36)
        self.assertLessEqual(max(abs(z) for z in model.positions[2::3]), 42)
        boxes = collision_boxes("Oktoberfest_Festzelt")
        for point in [(0,4,-22),(10,4,6),(-22,4,-10)]:
            self.assertFalse(any(all(abs(p-c) < size/2 for p,c,size in zip(point,center,sizes))
                                 for center,sizes in boxes))
        self.assertTrue(any(all(abs(p-c) < size/2 for p,c,size in zip((0,4,23),center,sizes))
                            for center,sizes in boxes))

    def test_all_meshes_have_complete_finite_attributes_and_real_triangles(self):
        for name in NAMES:
            with self.subTest(name=name):
                model = build_model(name)
                count = len(model.positions) // 3
                self.assertGreater(count, 0)
                self.assertLessEqual(count, 65535)
                self.assertEqual(len(model.normals), count * 3)
                self.assertEqual(len(model.colors), count * 3)
                self.assertEqual(len(model.uvs), count * 2)
                self.assertTrue(all(math.isfinite(x) for x in model.positions + model.normals))
                self.assertTrue(all(0 <= x <= 1 for x in model.uvs + model.colors))
                self.assertTrue(all(0 <= i < count for i in model.indices))
                self.assertTrue(all(i <= 65535 for i in model.indices))
                for i in range(0, len(model.indices), 3):
                    points = [model.positions[j*3:j*3+3] for j in model.indices[i:i+3]]
                    area = cross(add(points[1], mul(points[0], -1)), add(points[2], mul(points[0], -1)))
                    self.assertGreater(sum(x*x for x in area), 1e-15)
                for i in range(0, len(model.normals), 3):
                    self.assertAlmostEqual(sum(x*x for x in model.normals[i:i+3]), 1)

    def test_detail_assets_have_positive_collision_proxies_and_clear_space(self):
        self.assertEqual(set(ASSET_BUILDERS), {
            "Oktoberfest_Festzelt", "Oktoberfest_PretzelStand",
            "Oktoberfest_FoodStand", "Oktoberfest_GingerbreadStand",
            "Oktoberfest_BeerGarden", "Oktoberfest_Maypole",
            "Oktoberfest_FestivalArch", "Oktoberfest_BarrelDisplay",
            "Oktoberfest_PretzelDisplay",
        })
        for name in ASSET_BUILDERS:
            with self.subTest(name=name):
                boxes = collision_boxes(name)
                self.assertTrue(boxes)
                self.assertTrue(all(all(math.isfinite(value) for value in center + sizes)
                                    and all(size > 0 for size in sizes)
                                    for center, sizes in boxes))
                self.assertFalse(any(all(abs(point - center_axis) < size / 2
                                         for point, center_axis, size in zip((1000, 1, 1000), center, sizes))
                                     for center, sizes in boxes))

    def test_roof_normals_face_up_and_heart_caps_face_out(self):
        model = Model("roof")
        model.roof(25, 19, 23, 29)
        for i in range(0, 16 * 16, 16):
            self.assertGreater(model.normals[i * 3 + 1], 0)
        model = Model("heart")
        model.heart((0, 0, 0))
        self.assertGreater(model.normals[2], 0)

    def test_character_surface_normals_and_crest_ring_face_outward(self):
        model = Model("skin")
        model.ellipsoid((0,0,0),(2,3,4),"plaster")
        for i in range(0,len(model.positions),3):
            self.assertGreater(sum(a*b for a,b in zip(model.positions[i:i+3],model.normals[i:i+3])),0)
        crest = build_model("Oktoberfest_CourtCrest")
        self.assertTrue(all(crest.normals[i] > 0 for i in range(len(crest.normals)-16*12+1,len(crest.normals),3)))

    def test_portable_pack_has_embedded_textures_and_matching_glb_geometry(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            assets = prepare_originals(out)
            self.assertEqual(len(assets), len(NAMES))
            with zipfile.ZipFile(out / "oktoberfest-original-models.zip") as archive:
                self.assertEqual(len(archive.namelist()), 2 * len(NAMES) + 3)
                self.assertFalse(any(name.endswith((".dat", ".res")) for name in archive.namelist()))
                png = archive.read("Oktoberfest_Atlas.png")
                for asset, name in zip(assets, NAMES):
                    preview = json.loads((out / asset["geometry"]).read_text())[0]
                    data = archive.read(name + ".glb")
                    magic, version, length = struct.unpack_from("<III", data)
                    self.assertEqual((magic, version, length), (0x46546C67, 2, len(data)))
                    size, kind = struct.unpack_from("<I4s", data, 12)
                    self.assertEqual(kind, b"JSON")
                    document = json.loads(data[20:20+size])
                    binary = data[28+size:]
                    primitive = document["meshes"][0]["primitives"][0]
                    accessor = document["accessors"][primitive["attributes"]["POSITION"]]
                    view = document["bufferViews"][accessor["bufferView"]]
                    positions = struct.unpack_from(f'<{accessor["count"]*3}f', binary, view["byteOffset"])
                    self.assertEqual(accessor["count"], asset["vertices"])
                    for actual, expected in zip(positions, preview["positions"]):
                        self.assertAlmostEqual(actual, expected, places=4)
                    image = document["bufferViews"][document["images"][0]["bufferView"]]
                    self.assertEqual(binary[image["byteOffset"]:image["byteOffset"]+image["byteLength"]], png)
                    for view in document["bufferViews"]:
                        self.assertEqual(view["byteOffset"] % 4, 0)
                        self.assertLessEqual(view["byteOffset"] + view["byteLength"], len(binary))
                    self.assertIn(b"mtllib Oktoberfest_Atlas.mtl", archive.read(name + ".obj"))

    def test_native_export_never_silently_writes_glb_paths(self):
        text = '[Default]\r\nWorldFile= "Res/Stage/Mesh02/SV_Court.dat"\r\n'
        doc = initial_document(text)
        doc["objects"] = [{"id": "new-model", "name": "Arch", "file": PREFIX + "Oktoberfest_FestivalArch.glb",
                           "position": [90, 0, 20], "rotation": 0, "scale": 1, "level": 1, "visible": True}]
        compiled = compile_layout(text, doc)
        self.assertIn("Res/StageObj/Oktoberfest/Oktoberfest_FestivalArch.dat", compiled)
        self.assertNotIn(".glb", compiled)
        self.assertNotIn("AnimIndex", compiled)
        self.assertTrue(doc["objects"][0]["file"].endswith(".glb"))
        doc["objects"][0]["visible"] = False
        self.assertEqual(compile_layout(text, doc), text)


if __name__ == "__main__":
    unittest.main()
