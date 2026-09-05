"""Complete bind-pose geometry for the observed skinned StageObj AduMesh layout.

Skin palettes and sampled animation tracks are bounded and validated, not played.
Positions are the stored model-space bind pose; no heuristic vertex scan is used.
"""
import math
import struct

from twinkle_mesh import _InvalidLayout, _Reader, bounds


def parse_bind_pose(data: bytes) -> dict | None:
    try:
        return _parse(data)
    except (_InvalidLayout, struct.error):
        return None


def _parse(data: bytes) -> dict:
    h = _Reader(data, 0, len(data)).unpack("<8I")
    total, index_start, material_start = (12 + 4 * n for n in h[:3])
    nodes, animations, groups = h[4:7]
    if not (total == len(data) and 32 < index_start < material_start < total
            and h[3] == 2 and h[7] == 0 and 1 <= nodes <= 256
            and 1 <= animations <= 128 and 1 <= groups <= nodes):
        raise _InvalidLayout("unsupported skinned header")
    r = _Reader(data, 32, index_start)
    materials, primitives = [], []
    for slot in range(groups):
        tag, identity, influences, zero = r.unpack("<4I")
        if (tag, identity, zero) != (1, slot + 1, 0) or not 1 <= influences <= 4:
            raise _InvalidLayout("skin group")
        r.bounds()
        children, = r.unpack("<I")
        if not 1 <= children <= 64:
            raise _InvalidLayout("skin children")
        material = {"index": slot, "children": []}
        for child in range(children):
            r.bounds()
            one, palettes = r.unpack("<2I")
            if one != 1 or not 1 <= palettes <= 64:
                raise _InvalidLayout("skin palettes")
            parts = []
            for _ in range(palettes):
                batches, bone_count = r.unpack("<2I")
                if not 1 <= batches <= 4 or not 1 <= bone_count <= nodes:
                    raise _InvalidLayout("skin batch count")
                bones = r.unpack(f"<{bone_count}I")
                if any(b >= nodes for b in bones):
                    raise _InvalidLayout("bone palette reference")
                previous = -1
                for _ in range(batches):
                    blend, lightmapped, vc, ic, layout = r.unpack("<5I")
                    if not (previous < blend <= 3 and lightmapped == 0
                            and 3 <= vc <= 65536 and 1 <= ic <= (material_start - index_start) // 2
                            and layout == (0 if blend == 0 else 2)):
                        raise _InvalidLayout("skin vertex layout")
                    previous = blend
                    stride = 36 if layout == 0 else 56
                    offset = r.pos
                    positions, normals, uvs = [], [], []
                    for record in struct.iter_unpack("<8fI" if layout == 0 else "<12f4H", r.take(vc * stride)):
                        if not all(math.isfinite(v) for v in record[:8]):
                            raise _InvalidLayout("nonfinite skin vertex")
                        if layout == 0:
                            if record[8] >= bone_count:
                                raise _InvalidLayout("rigid palette index")
                        else:
                            weights, joints = record[8:12], record[12:16]
                            if (not all(math.isfinite(v) and 0 <= v <= 1.001 for v in weights)
                                    or abs(sum(weights) - 1) > 0.002
                                    or any(w > 0 and j >= bone_count for w, j in zip(weights, joints))):
                                raise _InvalidLayout("skin weights")
                        positions.append(list(record[:3]))
                        normals.append(list(record[3:6]))
                        uvs.append(list(record[6:8]))
                    part = {"materialSlot": slot, "materialChild": child,
                            "vertexOffset": offset, "vertexStride": stride, "vertexCount": vc,
                            "bonePalette": list(bones),
                            "sourcePrimitiveCount": ic, "positions": positions,
                            "normals": normals, "uvs": uvs, "uv1": [], "bounds": bounds(positions)}
                    parts.append(part)
                    primitives.append(part)
            material["children"].append(parts)
        materials.append(material)
    geometry_end = r.pos
    for _ in range(nodes):
        raw = r.take(304)
        name = raw[:32].split(b"\0", 1)[0]
        if not name or len(name) == 32:
            raise _InvalidLayout("skin node name")
    count, = r.unpack("<I")
    if count != animations:
        raise _InvalidLayout("animation count")
    for _ in range(animations):
        duration, frames = r.unpack("<fI")
        if not math.isfinite(duration) or duration <= 0 or not 1 <= frames <= 100000:
            raise _InvalidLayout("animation duration")
        for _ in range(nodes):
            for width in (3, 4, 3):
                count, = r.unpack("<I")
                if count not in (0, 1, frames):
                    raise _InvalidLayout("animation samples")
                samples = r.take(count * width * 4)
                if any(not math.isfinite(v[0]) for v in struct.iter_unpack("<f", samples)):
                    raise _InvalidLayout("nonfinite animation")
    if r.pos != r.end:
        raise _InvalidLayout("animation boundary")
    r = _Reader(data, index_start, material_start)
    r.expect(b"\0\0")
    for slot, material in enumerate(materials):
        r.expect(struct.pack("<H", slot + 1))
        for parts in material["children"]:
            for part in parts:
                part["indexOffset"] = r.pos
                strip = r.unpack(f'<{part["sourcePrimitiveCount"] + 2}H')
                if any(i >= part["vertexCount"] for i in strip):
                    raise _InvalidLayout("skin triangle reference")
                triangles = []
                for i in range(len(strip) - 2):
                    a, b, c = strip[i:i + 3]
                    if len({a, b, c}) == 3:
                        triangles.extend((b, a, c) if i & 1 else (a, b, c))
                part["indices"] = triangles
                part["indexCount"] = len(triangles)
    indices_end = r.pos
    r.take(-r.pos % 4)
    if r.pos != r.end:
        raise _InvalidLayout("skin index boundary")
    r = _Reader(data, material_start, total)
    r.expect(b"\1\0")
    for slot, material in enumerate(materials):
        r.expect(bytes([slot + 1]))
        name = r.name(64)
        material["name"] = name
        flags = r.take(6)
        if flags not in (b"\1\1\0\0\0\0", b"\1\1\0\0\1\0"):
            raise _InvalidLayout("skin material flags")
        for parts in material["children"]:
            flags = r.take(4)
            if flags not in (b"\0\0\0\0", b"\0\1\0\0"):
                raise _InvalidLayout("skin child flags")
            r.expect(b"\1")
            texture_offset = r.pos
            texture = r.name(64)
            r.expect(b"\0\0\0")
            for part in parts:
                part["materialName"] = name
                part["textures"] = [{"name": texture, "uvSet": 0, "offset": texture_offset}]
    # Animation labels/exporter descriptors follow materials. They are opaque:
    # sampled track boundaries above, not these labels, delimit the geometry.
    if r.end - r.pos < animations * 128:
        raise _InvalidLayout("animation descriptors")
    return {"primitives": primitives, "materials": materials, "pose": "bind",
            "animationCount": animations, "nodeCount": nodes,
            "geometryEnd": geometry_end, "indicesEnd": indices_end, "materialsEnd": r.pos}
