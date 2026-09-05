"""Bounded reader for the observed SV_Court / SV_All static AduMesh family.

Counts and section ends drive every read. No byte scanning or vertex scoring.
The per-child count is a triangle-strip primitive count, including degenerates.
Names occupy fixed buffers whose bytes after the first NUL are uninitialized.
"""

from __future__ import annotations

import math
import re
import struct
from typing import Any


class _InvalidLayout(ValueError):
    pass


class _Reader:
    def __init__(self, data: bytes, start: int, end: int):
        self.data, self.pos, self.end = data, start, end

    def take(self, size: int) -> bytes:
        if size < 0 or self.pos + size > self.end:
            raise _InvalidLayout("section overrun")
        start = self.pos
        self.pos += size
        return self.data[start:self.pos]

    def unpack(self, fmt: str) -> tuple:
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))

    def expect(self, value: bytes) -> None:
        if self.take(len(value)) != value:
            raise _InvalidLayout("unsupported tag")

    def name(self, size: int) -> str:
        raw = self.take(size)
        stem, sep, _ = raw.partition(b"\0")
        if not sep or re.fullmatch(rb"[A-Za-z][A-Za-z0-9_]{1,62}", stem) is None:
            raise _InvalidLayout("invalid name")
        return stem.decode("ascii")

    def bounds(self) -> None:
        values = self.unpack("<6f")
        if not all(math.isfinite(v) for v in values) or any(
            values[i] < values[i + 3] for i in range(3)
        ):
            raise _InvalidLayout("invalid bounds")


def bounds(positions: list[list[float]]) -> dict[str, list[float]]:
    return {
        "min": [min(p[i] for p in positions) for i in range(3)],
        "max": [max(p[i] for p in positions) for i in range(3)],
    }


def parse_twinkle_static(data: bytes) -> dict[str, Any] | None:
    """Validate the observed layout, returning None for any unsupported variant.

    Callers must additionally gate by member name for deterministic decoding.
    Metadata extraction can identify the family from its SV_ group names.
    """
    try:
        return _parse(data)
    except (_InvalidLayout, struct.error):
        return None


def parse_static_decoration(data: bytes) -> dict[str, Any] | None:
    """Read the same validated static layout for the Studio's explicit prop catalog."""
    try:
        return _parse(data, twinkle=False)
    except (_InvalidLayout, struct.error):
        return None


def _parse(data: bytes, *, twinkle: bool = True) -> dict[str, Any]:
    header = _Reader(data, 0, len(data)).unpack("<8I")
    total, index_end, material_start = (12 + 4 * n for n in header[:3])
    count = header[4]
    if not (total == len(data) and 32 < index_end < material_start < total
            and 1 <= count <= 40 and header[3:] == (2, count, 0, count, 0)):
        raise _InvalidLayout("unsupported header")
    vertices = _Reader(data, 32, index_end)
    groups = []
    primitives = []
    for slot in range(count):
        vertices.expect(struct.pack("<4I", 1, slot + 1, 0, 0))
        vertices.bounds()
        children, = vertices.unpack("<I")
        if not 1 <= children <= 64:
            raise _InvalidLayout("unsupported child count")
        group = {"index": slot, "primitives": []}
        for _ in range(children):
            vertices.bounds()
            one, lightmapped = vertices.unpack("<2I")
            if one != 1 or lightmapped not in (0, 1):
                raise _InvalidLayout("unsupported child")
            if lightmapped:
                vertices.expect(b"\0" * 4)
            vertex_count, strip_count, layout = vertices.unpack("<3I")
            if not (3 <= vertex_count <= 65536 and strip_count >= 1
                    and layout == (6 if lightmapped else 4)):
                raise _InvalidLayout("unsupported vertex layout")
            if 2 * (strip_count + 2) > material_start - index_end:
                raise _InvalidLayout("invalid strip count")
            stride = 40 if lightmapped else 32
            offset = vertices.pos
            raw = vertices.take(vertex_count * stride)
            positions, normals, uvs, uv1 = [], [], [], []
            for record in struct.iter_unpack("<10f" if lightmapped else "<8f", raw):
                if not all(math.isfinite(v) for v in record):
                    raise _InvalidLayout("nonfinite vertex")
                positions.append(list(record[:3]))
                normals.append(list(record[3:6]))
                uvs.append(list(record[6:8]))
                if lightmapped:
                    uv1.append(list(record[8:10]))
            primitive = {
                "materialSlot": slot, "vertexOffset": offset,
                "vertexStride": stride, "vertexCount": vertex_count,
                "sourcePrimitiveCount": strip_count,
                "positions": positions, "normals": normals, "uvs": uvs,
                "uv1": uv1,
                "bounds": bounds(positions),
            }
            primitives.append(primitive)
            group["primitives"].append(primitive)
        groups.append(group)

    # Each group has a 304-byte node record, then a four-byte trailer.
    if vertices.end - vertices.pos != count * 304 + 4:
        raise _InvalidLayout("node table boundary")
    node_names = []
    for _ in groups:
        node_names.append(vertices.name(32))
        vertices.take(272)
    vertices.expect(b"\0" * 4)

    indices = _Reader(data, index_end, material_start)
    indices.expect(b"\0\0")
    for slot, group in enumerate(groups):
        indices.expect(struct.pack("<H", slot + 1))
        for primitive in group["primitives"]:
            primitive["indexOffset"] = indices.pos
            size = primitive["sourcePrimitiveCount"] + 2
            strip = indices.unpack(f"<{size}H")
            if any(i >= primitive["vertexCount"] for i in strip):
                raise _InvalidLayout("index out of range")
            triangles = []
            for i in range(size - 2):
                a, b, c = strip[i:i + 3]
                if a == b or b == c or a == c:
                    continue
                if i & 1:
                    a, b = b, a
                triangles.extend((a, b, c))
            primitive["indices"] = triangles
            primitive["indexCount"] = len(triangles)
            primitive["sourceIndexCount"] = size
    # Only the entire section is aligned, never an individual odd-length strip.
    if twinkle:
        indices.expect(b"\0" * (-indices.pos % 4))
    else:
        indices.take(-indices.pos % 4)
    if indices.pos != indices.end:
        raise _InvalidLayout("index section boundary")

    materials = _Reader(data, material_start, total)
    materials.expect(b"\0\0")
    for slot, group in enumerate(groups):
        materials.expect(bytes([slot + 1]))
        group["offset"] = materials.pos
        group["name"] = materials.name(64)
        if group["name"] != node_names[slot] or (twinkle and not group["name"].startswith("SV_")):
            raise _InvalidLayout("not a Twinkle node")
        flags = materials.take(6)
        if flags not in (b"\0\1\0\0\0\0", b"\0\1\0\0\1\0"):
            raise _InvalidLayout("unsupported material flags")
        for child, primitive in enumerate(group["primitives"]):
            material_flags = materials.take(4)
            if material_flags not in (b"\0\0\0\0", b"\0\1\0\0"):
                raise _InvalidLayout("unsupported child material flags")
            textures = []
            for channel in range(2):
                if channel:
                    materials.expect(b"\0\0")
                present, = materials.unpack("<B")
                expected = channel == 0 or primitive["vertexStride"] == 40
                if present != int(expected):
                    raise _InvalidLayout("unsupported texture channel")
                if present:
                    offset = materials.pos
                    name = materials.name(64)
                    textures.append({"name": name, "offset": offset,
                                     "texCandidate": f"{name}.tex", "uvSet": channel})
            primitive["materialChild"] = child
            primitive["materialName"] = group["name"]
            primitive["textures"] = textures
        # Keep positional duplicates: one group may use several albedos.
    padding = -materials.pos % 4
    materials.take(padding)  # File-alignment bytes are uninitialized.
    if materials.pos != materials.end:
        raise _InvalidLayout("material section boundary")
    return {"primitives": primitives, "materials": [
        {key: value for key, value in group.items() if key != "primitives"}
        for group in groups
    ]}
