import json
import math
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from oktoberfest_models import NAMES, PREFIX, Model, build_model, prepare_originals, cross, add, mul
from twinkle_studio import initial_document, compile_layout


class OriginalModelTests(unittest.TestCase):
    def test_all_meshes_have_complete_finite_attributes_and_real_triangles(self):
        for name in NAMES:
            with self.subTest(name=name):
                model = build_model(name)
                count = len(model.positions) // 3
                self.assertGreater(count, 300)
                self.assertEqual(len(model.normals), count * 3)
                self.assertEqual(len(model.colors), count * 3)
                self.assertEqual(len(model.uvs), count * 2)
                self.assertTrue(all(math.isfinite(x) for x in model.positions + model.normals))
                self.assertTrue(all(0 <= x <= 1 for x in model.uvs + model.colors))
                self.assertTrue(all(0 <= i < count for i in model.indices))
                for i in range(0, len(model.indices), 3):
                    points = [model.positions[j*3:j*3+3] for j in model.indices[i:i+3]]
                    area = cross(add(points[1], mul(points[0], -1)), add(points[2], mul(points[0], -1)))
                    self.assertGreater(sum(x*x for x in area), 1e-15)
                for i in range(0, len(model.normals), 3):
                    self.assertAlmostEqual(sum(x*x for x in model.normals[i:i+3]), 1)

    def test_roof_normals_face_up_and_heart_caps_face_out(self):
        model = Model("roof")
        model.roof(25, 19, 23, 29)
        for i in range(0, 16 * 16, 16):
            self.assertGreater(model.normals[i * 3 + 1], 0)
        model = Model("heart")
        model.heart((0, 0, 0))
        self.assertGreater(model.normals[2], 0)

    def test_portable_pack_has_embedded_textures_and_matching_glb_geometry(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            assets = prepare_originals(out)
            self.assertEqual(len(assets), 10)
            with zipfile.ZipFile(out / "oktoberfest-original-models.zip") as archive:
                self.assertEqual(len(archive.namelist()), 23)
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
