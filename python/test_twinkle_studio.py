import copy
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from client_crypto import decrypt_set_file, encrypt_set_file
from twinkle_studio import compile_layout, export_layout, initial_document, PROP_PREFIX


SOURCE = ('[Default]\r\nWorldFile= "Res/Stage/Mesh02/SV_Court.dat"\r\n'
          'Collision= "Res/Collision/ColMesh_TT.dat"\r\nCam_Intro= "KEEP_CAMERA"\r\n'
          '[Object]\r\nFile= "Res/Stage/Mesh02/SV_All.dat"\r\nLevel= 0\r\n'
          '[DecoObj]\r\nFile= "Res/StageObj/Object02/Carriage00.dat"\r\n'
          'Position= -105.0, 0.0, 90.0f\r\nRotation= -85\r\nScale= 1.3\r\n'
          'AnimIndex= 4\r\nAnimPos= 0.2\r\nShadow= true\r\nLevel= 1\r\n'
          '[Effect]\r\nFile= "keep.eft"\r\nPosition= 1, 2, 3\r\n')


class TwinkleAuthorTests(unittest.TestCase):
    def test_unchanged_layout_is_byte_identical(self):
        doc = initial_document(SOURCE)
        self.assertEqual(doc["objects"][0]["position"], [-105, 0, 90])
        self.assertEqual(compile_layout(SOURCE, doc), SOURCE)

    def test_changed_transform_preserves_cameras_effects_and_animation(self):
        doc = initial_document(SOURCE)
        doc["objects"][0]["position"] = [99, 2, 40]
        doc["objects"][0]["rotation"] = 30
        result = compile_layout(SOURCE, doc)
        self.assertEqual(result.split("[DecoObj]")[0], SOURCE.split("[DecoObj]")[0])
        self.assertEqual(result.split("[Effect]")[1], SOURCE.split("[Effect]")[1])
        self.assertIn("Position= 99, 2, 40", result)
        self.assertIn("AnimIndex= 4\r\nAnimPos= 0.2\r\nShadow= true", result)

    def test_add_delete_and_exclude_compile_to_real_deco_blocks(self):
        doc = initial_document(SOURCE)
        added = {**doc["objects"][0], "id": "new-barrel", "file": PROP_PREFIX + "P0_Barrel01_C01.dat",
                 "position": [100, 0, 20], "rotation": 0, "scale": 2}
        doc["objects"] = [added]
        result = compile_layout(SOURCE, doc)
        self.assertNotIn("Carriage00.dat", result)
        self.assertIn(added["file"], result)
        self.assertEqual(len(initial_document(result)["objects"]), 1)
        doc["objects"][0]["visible"] = False
        self.assertNotIn("[DecoObj]", compile_layout(SOURCE, doc))

    def test_stale_source_and_unlisted_asset_are_rejected(self):
        doc = initial_document(SOURCE)
        with self.assertRaisesRegex(ValueError, "changed"):
            compile_layout(SOURCE + "\r\n", doc)
        doc["objects"][0]["file"] = '../../secret.dat'
        with self.assertRaisesRegex(ValueError, "catalog"):
            compile_layout(SOURCE, doc)

    def test_cli_rejects_invalid_transforms_and_reserved_ids(self):
        doc = initial_document(SOURCE)
        duplicate = copy.deepcopy(doc)
        duplicate["objects"].append(duplicate["objects"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compile_layout(SOURCE, duplicate)
        doc["objects"][0]["id"] = "stock-999"
        with self.assertRaisesRegex(ValueError, "Unknown"):
            compile_layout(SOURCE, doc)
        doc["objects"][0]["id"] = "stock-0"
        doc["objects"][0]["position"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "transform"):
            compile_layout(SOURCE, doc)

    def test_zip_round_trip_preserves_stock_and_unrelated_members(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "client/Res/Stage/Info.res"
            source.parent.mkdir(parents=True)
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("2_Twinkle_Town.set", encrypt_set_file(SOURCE.encode()))
                archive.writestr("untouched.bin", b"UNRELATED")
            before = source.read_bytes()
            doc = initial_document(SOURCE)
            doc["objects"][0]["position"][0] = 101
            result = export_layout(root / "client", doc, root / "export")
            self.assertTrue(result["ok"])
            self.assertEqual(source.read_bytes(), before)
            with zipfile.ZipFile(root / "export/twinkle-layout.zip") as bundle:
                with zipfile.ZipFile(io.BytesIO(bundle.read("Res/Stage/Info.res"))) as archive:
                    self.assertEqual(archive.read("untouched.bin"), b"UNRELATED")
                    actual = decrypt_set_file(archive.read("2_Twinkle_Town.set")).decode()
                    self.assertEqual(actual, compile_layout(SOURCE, doc))
                    self.assertEqual(initial_document(actual)["objects"][0]["position"][0], 101)

    def test_festival_variant_removes_carriages_and_bundles_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = root / "client"
            (client / "Res/Stage").mkdir(parents=True)
            for name in ["FestivalHall", "FestivalPretzel", "FestivalHeart", "FestivalFood", "Tex009", "Tex010"]:
                with zipfile.ZipFile(root / f"{name}.res", "w") as archive:
                    archive.writestr("synthetic.tex", name.encode())
            rows = ["id\tfile\tx\ty\tz\trotation\tscale\tanimation\tphase"]
            files = ["Res/StageObj/FestivalHall/BlackSmith_Shop.dat",
                     "Res/StageObj/FestivalPretzel/Carriage00.dat",
                     "Res/StageObj/FestivalHeart/Carriage00.dat",
                     "Res/StageObj/FestivalFood/Carriage00.dat",
                     "Res/StageObj/Object03/Engineer00h.dat"]
            for i in range(30):
                file = files[i] if i < len(files) else PROP_PREFIX + "P0_Barrel01_C01.dat"
                animation = 0 if i < 5 else -1
                rows.append(f"prop-{i}\t{file}\t90\t0\t{i}\t45\t1\t{animation}\t-1")
            (root / "festival-placements.tsv").write_text("\n".join(rows))
            text = SOURCE + SOURCE[SOURCE.index("[DecoObj]"):SOURCE.index("[Effect]")]
            text += '[DecoObj]\r\nFile= "Res/StageObj/Object01/Jjijil00.dat"\r\nPosition= 0, 0, 0\r\n'
            with zipfile.ZipFile(client / "Res/Stage/Info.res", "w") as archive:
                archive.writestr("2_Twinkle_Town.set", encrypt_set_file(text.encode()))
                archive.writestr("other.set", b"UNCHANGED")
            with patch.dict(os.environ, {"JFTSE_FESTIVAL_RESOURCES": str(root)}):
                stock = initial_document(text)
                doc = initial_document(text, "oktoberfest")
                self.assertEqual(len(stock["objects"]), 3)
                self.assertEqual(len(doc["objects"]), 31)
                self.assertNotEqual(doc["sourceHash"], stock["sourceHash"])
                compiled = compile_layout(text, doc)
                self.assertNotIn("Res/StageObj/Object02/Carriage00.dat", compiled)
                self.assertIn("AnimPos= -1", compiled)
                self.assertEqual(compiled.count("AnimIndex="), 5)
                export_layout(client, doc, root / "export")
                with zipfile.ZipFile(root / "export/twinkle-layout.zip") as bundle:
                    self.assertEqual(len(bundle.namelist()), 10)
                    self.assertEqual(bundle.read("Res/Stage/Tex009.res"), (root / "Tex009.res").read_bytes())
                    self.assertIn(b"separate", bundle.read("README.txt"))
                (root / "festival-placements.tsv").write_text("\n".join(rows) + "\n")
                with self.assertRaisesRegex(ValueError, "changed"):
                    compile_layout(text, doc)

    def test_legacy_stock_draft_preserves_animation_metadata(self):
        doc = initial_document(SOURCE)
        del doc["objects"][0]["animation"]
        del doc["objects"][0]["phase"]
        self.assertEqual(compile_layout(SOURCE, doc), SOURCE)


if __name__ == "__main__":
    unittest.main()
