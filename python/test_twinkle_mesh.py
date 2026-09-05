import base64
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from mesh_codec import (
    decode_member, decode_mesh_bytes, decoded_to_dict, mesh_to_gltf,
    write_positions_into_dat,
)
from mesh_meta import extract_material_names
from twinkle_mesh import parse_static_decoration, parse_twinkle_static


def synthetic_mesh(*, first_strip=None):
    """Two groups, mixed strides, repeated names, odd strips and degenerates."""
    groups = [[(40, first_strip or [0, 1, 2, 3, 4]), (32, [0, 1, 1, 2, 3, 4])],
              [(40, [0, 1, 2])]]
    data = bytearray(32)
    vertex_offsets = []
    index_offsets = []
    box = struct.pack("<6f", 10, 10, 10, -10, -10, -10)

    def name(text, size):
        # Deliberately nonzero trailing bytes, as in the stock records.
        return text.encode() + b"\0" + b"x" * (size - len(text) - 1)

    for slot, children in enumerate(groups):
        data.extend(struct.pack("<4I", 1, slot + 1, 0, 0) + box)
        data.extend(struct.pack("<I", len(children)))
        for stride, strip in children:
            data.extend(box + struct.pack("<2I", 1, int(stride == 40)))
            if stride == 40:
                data.extend(b"\0" * 4)
            data.extend(struct.pack("<3I", 5, len(strip) - 2, 6 if stride == 40 else 4))
            vertex_offsets.append(len(data))
            for i in range(5):
                record = (i, i % 2, 0, 0, 0, 1, i / 4, 0.25)
                if stride == 40:
                    record += (0.8, 0.9)
                data.extend(struct.pack(f"<{stride // 4}f", *record))
    for slot in range(len(groups)):
        data.extend(name(f"SV_Group{slot}", 32) + b"\0" * 272)
    data.extend(b"\0" * 4)
    index_start = len(data)
    data.extend(b"\0\0")
    for slot, children in enumerate(groups):
        data.extend(struct.pack("<H", slot + 1))
        for _, strip in children:
            index_offsets.append(len(data))
            data.extend(struct.pack(f"<{len(strip)}H", *strip))
    data.extend(b"\0" * (-len(data) % 4))
    material_start = len(data)
    data.extend(b"\0\0")
    for slot, children in enumerate(groups):
        data.extend(bytes([slot + 1]) + name(f"SV_Group{slot}", 64))
        data.extend(b"\0\1\0\0\1\0")
        for stride, _ in children:
            data.extend(b"\0" * 4 + b"\1" + name("BF_Shared_A", 64))
            data.extend(b"\0\0" + bytes([int(stride == 40)]))
            if stride == 40:
                data.extend(name("SV_Shared_LM", 64))
    data.extend(b"\x99" * (-len(data) % 4))
    struct.pack_into("<8I", data, 0, (len(data) - 12) // 4,
                     (index_start - 12) // 4, (material_start - 12) // 4,
                     2, 2, 0, 2, 0)
    return bytes(data), vertex_offsets, index_offsets


class TwinkleStaticTests(unittest.TestCase):
    def test_static_prop_path_preserves_twinkle_name_gate_and_uv1(self):
        data, _, _ = synthetic_mesh()
        renamed = data.replace(b"SV_", b"P0_")
        self.assertIsNone(parse_twinkle_static(renamed))
        prop = parse_static_decoration(renamed)
        self.assertIsNotNone(prop)
        self.assertAlmostEqual(prop["primitives"][0]["uv1"][0][0], 0.8)
        self.assertEqual(prop["primitives"][1]["uv1"], [])

    def test_index_section_without_final_alignment_bytes(self):
        data, _, offsets = synthetic_mesh(first_strip=[0, 1, 2, 3])
        parsed = parse_twinkle_static(data)
        self.assertIsNotNone(parsed)
        material_start = struct.unpack_from("<I", data, 8)[0] * 4 + 12
        self.assertEqual(offsets[-1] + 6, material_start)

    def test_complete_geometry_and_local_to_aggregate_indices(self):
        data, vertices, indices = synthetic_mesh()
        with patch("mesh_codec.find_vertex_run", side_effect=AssertionError("heuristic called")):
            mesh = decode_mesh_bytes(data, name="SV_All.dat", max_vertices=3)
        self.assertEqual(mesh.decodeMode, "indexed-twinkle-static")
        self.assertEqual(mesh.vertexCount, 15)
        self.assertEqual(len(mesh.normals), 15)
        self.assertEqual(mesh.uvs[0], [0.0, 0.25])
        self.assertEqual(mesh.normals[0], [0.0, 0.0, 1.0])
        self.assertEqual(mesh.bounds, {"min": [0, 0, 0], "max": [4, 1, 0]})
        self.assertEqual([p["vertexOffset"] for p in mesh.primitives], vertices)
        self.assertEqual([p["indexOffset"] for p in mesh.primitives], indices)
        self.assertEqual(indices[1] - indices[0], 10)
        self.assertEqual(mesh.primitives[0]["indices"], [0, 1, 2, 2, 1, 3, 2, 3, 4])
        self.assertEqual(mesh.primitives[1]["indices"], [1, 2, 3, 3, 2, 4])
        self.assertEqual(mesh.indices[-3:], [10, 11, 12])
        self.assertEqual([p["materialSlot"] for p in mesh.primitives], [0, 0, 1])
        self.assertEqual([p["materialChild"] for p in mesh.primitives], [0, 1, 0])
        self.assertEqual([p["vertexStride"] for p in mesh.primitives], [40, 32, 40])
        # No single contiguous stride exists. Legacy writers must fail closed.
        with self.assertRaisesRegex(ValueError, "INVALID_VERTEX_STRIDE"):
            write_positions_into_dat(data, mesh.vertexOffset, mesh.positions, stride=mesh.vertexStride)

    def test_positional_materials_not_regex_noise_or_deduplicated(self):
        data, _, _ = synthetic_mesh()
        mats = extract_material_names(data)
        self.assertEqual([m["name"] for m in mats], [
            "BF_Shared_A", "SV_Shared_LM", "BF_Shared_A", "BF_Shared_A", "SV_Shared_LM",
        ])
        self.assertEqual([m["materialSlot"] for m in mats], [0, 0, 0, 1, 1])
        self.assertEqual([m["uvSet"] for m in mats], [0, 1, 0, 0, 1])
        for mat in mats:
            self.assertTrue(data[mat["offset"]:].startswith(mat["name"].encode() + b"\0"))

    def test_every_truncation_and_trailing_byte_rejected(self):
        data, _, _ = synthetic_mesh()
        for end in range(len(data)):
            self.assertIsNone(parse_twinkle_static(data[:end]), end)
        self.assertIsNone(parse_twinkle_static(data + b"\0"))

    def test_malformed_sections_tags_counts_and_values(self):
        data, vertices, indices = synthetic_mesh()
        material = struct.unpack_from("<I", data, 8)[0] * 4 + 12
        mutations = [
            (4, "<I", 5), (8, "<I", 0xffffffff), (16, "<I", 41),
            (24, "<I", 3), (32, "<I", 2), (72, "<I", 0xffffffff),
            (vertices[0] - 12, "<I", 65537),
            (vertices[0] - 8, "<I", 0xffffffff),
            (vertices[0] - 4, "<I", 4),
            (vertices[0], "<f", float("nan")),
            (vertices[0] + 12, "<f", float("inf")),
            (vertices[0] + 24, "<f", float("nan")),
            (indices[0], "<H", 5), (indices[0] - 2, "<H", 2),
            (material + 2, "<B", 2), (material + 3, "<B", ord("X")),
        ]
        for offset, fmt, value in mutations:
            with self.subTest(offset=offset):
                changed = bytearray(data)
                struct.pack_into(fmt, changed, offset, value)
                self.assertIsNone(parse_twinkle_static(bytes(changed)))

    def test_invalid_twinkle_and_nonfamily_keep_generic_fallback(self):
        data, _, _ = synthetic_mesh()
        run = [(0., 0., 0.), (10., 0., 0.), (0., 0., 10.)]
        for raw, name in [(data[:-1], "SV_All.dat"), (data, "BF_All.dat")]:
            with patch("mesh_codec.find_vertex_run", return_value=(48, run, 12)) as finder, \
                 patch("mesh_codec.find_u16_indices", return_value=[0, 1, 2]):
                mesh = decode_mesh_bytes(raw, name=name)
                finder.assert_called_once_with(raw)
                self.assertEqual(mesh.decodeMode, "indexed-s12")
                self.assertIsNone(mesh.primitives)
        self.assertEqual(extract_material_names(b"BF_Test_A\0")[0]["name"], "BF_Test_A")

    def test_metadata_omits_nested_geometry_without_mutating_mesh(self):
        mesh = decode_mesh_bytes(synthetic_mesh()[0], name="SV_Court.dat")
        meta = decoded_to_dict(mesh, include_geometry=False)
        for field in ("positions", "indices", "uvs", "uv1", "normals"):
            self.assertNotIn(field, meta)
            self.assertTrue(all(field not in p for p in meta["primitives"]))
            self.assertIn(field, mesh.primitives[0])
        self.assertTrue(meta["hasUvs"])

    def test_archive_decode_does_not_replace_uvs_with_heuristics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(root / "mesh.res", "w") as archive:
                archive.writestr("SV_Court.dat", synthetic_mesh()[0])
            with patch("mesh_texture.attach_uvs_and_texture_meta", side_effect=AssertionError("called")):
                mesh = decode_member(root, "mesh.res", "SV_Court.dat")
            self.assertEqual(mesh.uvMode, "adu-uv0")
            self.assertIsNone(mesh.texture)

    def test_aggregate_export_keeps_indices_above_u16_limit(self):
        mesh = decode_mesh_bytes(synthetic_mesh()[0], name="SV_All.dat")
        mesh.positions = [[0., 0., 0.]] * 65537
        mesh.normals = [[0., 1., 0.]] * 65537
        mesh.vertexCount = len(mesh.positions)
        mesh.indices = [65534, 65535, 65536]
        mesh.indexCount = 3
        with patch("mesh_codec.decode_confidence", return_value={}):
            gltf = mesh_to_gltf(mesh)
        self.assertEqual(gltf["accessors"][0]["componentType"], 5125)
        blob = base64.b64decode(gltf["buffers"][0]["uri"].split(",")[1])
        self.assertEqual(struct.unpack_from("<3I", blob), tuple(mesh.indices))


if __name__ == "__main__":
    unittest.main()
