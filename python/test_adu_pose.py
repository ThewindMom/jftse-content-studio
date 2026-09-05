import struct
import unittest

from adu_pose import parse_bind_pose


def synthetic_pose():
    box = struct.pack("<6f", 50, 50, 50, -50, -50, -50)
    vertices = bytearray(struct.pack("<4I", 1, 1, 2, 0) + box + struct.pack("<I", 1))
    vertices += box + struct.pack("<2I", 1, 2)
    offsets = []
    for blend in (0, 1):
        vertices += struct.pack("<4I", 1, 2, 0, 1)
        vertices += struct.pack("<5I", blend, 0, 3, 1, 0 if blend == 0 else 2)
        offsets.append(32 + len(vertices))
        for position in [(0, 0, 0), (20, 0, 0), (0, 20, 0)]:
            values = [*position, 0, 0, 1, 0.25, 0.75]
            vertices += struct.pack("<8fI", *values, 0) if blend == 0 else struct.pack("<12f4H", *values, .5, .5, 0, 0, 0, 1, 0, 0)
    vertices += b"Root\0".ljust(304, b"\0") + b"Child\0".ljust(304, b"\0")
    vertices += struct.pack("<IfI", 1, 1.0, 1) + b"\0" * 24
    index_start = 32 + len(vertices)
    indices = struct.pack("<8H", 0, 1, 0, 1, 2, 0, 1, 2)
    material_start = index_start + len(indices)
    materials = b"\1\0\1" + b"Body\0".ljust(64, b"\0") + b"\1\1\0\0\0\0"
    materials += b"\0" * 4 + b"\1" + b"BodyTex\0".ljust(64, b"\0") + b"\0\0\0" + b"Idle\0".ljust(128, b"\0")
    materials += b"\0" * (-(material_start + len(materials)) % 4)
    total = material_start + len(materials)
    header = struct.pack("<8I", (total - 12) // 4, (index_start - 12) // 4, (material_start - 12) // 4, 2, 2, 1, 1, 0)
    return bytearray(header + vertices + indices + materials), offsets, index_start


class BindPoseTests(unittest.TestCase):
    def test_all_palettes_and_material_association(self):
        data, offsets, _ = synthetic_pose()
        result = parse_bind_pose(data)
        self.assertIsNotNone(result)
        self.assertEqual(result["pose"], "bind")
        self.assertEqual(len(result["primitives"]), 2)
        for part, offset, stride in zip(result["primitives"], offsets, (36, 56)):
            self.assertEqual(part["vertexOffset"], offset)
            self.assertEqual(part["vertexStride"], stride)
            self.assertEqual(part["indices"], [0, 1, 2])
            self.assertEqual(part["materialName"], "Body")
            self.assertEqual(part["textures"][0]["name"], "BodyTex")
            self.assertEqual(part["bounds"]["max"], [20, 20, 0])

    def test_truncation_never_returns_partial_geometry(self):
        data, _, _ = synthetic_pose()
        for length in range(len(data)):
            self.assertIsNone(parse_bind_pose(data[:length]))

    def test_invalid_weights_indices_and_nonfinite_vertices_rejected(self):
        data, offsets, indices = synthetic_pose()
        for offset, fmt, value in [(offsets[0], "f", float("nan")),
                                   (offsets[0] + 32, "I", 2),
                                   (offsets[1] + 32, "f", 2),
                                   (indices + 4, "H", 3), (20, "I", 2)]:
            broken = data.copy()
            struct.pack_into("<" + fmt, broken, offset, value)
            self.assertIsNone(parse_bind_pose(broken))


if __name__ == "__main__":
    unittest.main()
