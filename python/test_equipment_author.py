import tempfile
import unittest
import zipfile
from pathlib import Path

from client_crypto import decrypt_set_file, encrypt_set_file
from equipment_author import build_item_sql_pack, patch_item_mesh_catalog


class EquipmentWriterTests(unittest.TestCase):
    def test_item_archive_and_sql_bind_target_to_effect_15(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            item_res = root / "Res" / "Script" / "Item.res"
            item_res.parent.mkdir(parents=True)
            mesh = (
                '<?xml version="1.0"?><ItemMeshList>'
                '<Item Char="NIKI" Index="214" '
                'Path="Res/Player/PlayerA/Item07/Niki_CommonRacket41.dat" '
                'Desc="Stock"/></ItemMeshList>'
            )
            parts = (
                '<?xml version="1.0"?><ItemList>'
                '<Item Index="10728" Char="NIKI" Part="RACKET" '
                'Mesh="214" Tex="1" Effect="7"/></ItemList>'
            )
            with zipfile.ZipFile(item_res, "w") as archive:
                archive.writestr("Info_Item_Mesh.set", encrypt_set_file(mesh.encode()))
                archive.writestr("Item_Parts.set", encrypt_set_file(parts.encode()))
                archive.writestr("Unchanged.bin", b"stock")

            result = patch_item_mesh_catalog(
                root,
                char="NIKI",
                source_index=214,
                new_index=41001,
                path="Res/Player/PlayerA/Item07/Niki_CommonRacket41.dat",
                desc="Aurora Racket",
                out_dir=root / "out",
                source_item_index=10728,
                effect=15,
            )
            with zipfile.ZipFile(str(result["itemArchive"])) as archive:
                decoded_mesh = decrypt_set_file(archive.read("Info_Item_Mesh.set"))
                decoded_parts = decrypt_set_file(archive.read("Item_Parts.set"))
                self.assertEqual(archive.read("Unchanged.bin"), b"stock")
            self.assertIn(b'Index="41001"', decoded_mesh)
            self.assertIn(
                b'Index="41001" Char="NIKI" Part="RACKET" Mesh="41001" Tex="1" Effect="15"',
                decoded_parts,
            )

            sql = build_item_sql_pack(
                product_index=41001,
                name="Aurora Racket",
                mesh=41001,
                effect=15,
            )
            self.assertEqual(sql.count("41001, 'Aurora Racket'"), 2)
            self.assertEqual(sql.count(", 41001, 0, 15, 0)"), 2)


if __name__ == "__main__":
    _ = unittest.main()
