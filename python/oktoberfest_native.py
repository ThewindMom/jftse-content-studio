"""Bounded stock-template AduMesh and collision authoring, not a runtime certificate.

Opaque 304-byte nodes are retained from private, fingerprinted stock templates.
Only established section/count/bounds/name/vertex/index fields are rewritten.
"""
import hashlib
import io
import math
import struct
import zipfile

from PIL import Image

from oktoberfest_models import NAMES, PREFIX, atlas, build_model, collision_boxes, unit, cross, add, mul
from tex_codec import dds_to_tex
from twinkle_mesh import bounds, parse_static_decoration

STATIC_HASH = "c35da60975c51f03a1fa2e6648cba2b48efc4b5e143cdcd10c51f799203147a9"
COLLISION_ARCHIVE_HASH = "8bc8e777c1c820887dad07b1fe4883710bb0053349757d3821bef5acaafbc0e9"
ATLAS = "Oktoberfest_Atlas"


def model_name(file):
    name = file.removeprefix(PREFIX).removesuffix(".glb")
    return name if file == PREFIX + name + ".glb" and name in NAMES else None


def triangle_strip(triangles):
    if len(triangles) % 3 or not triangles:
        raise ValueError("Expected complete triangles")
    result = list(triangles[:3])
    for i in range(3, len(triangles), 3):
        if len(result) % 2:
            result.append(result[-1])
        a, b, c = triangles[i:i+3]
        result.extend((result[-1], a, a, b, c))
    return result


def _header(data, index, material):
    struct.pack_into("<3I", data, 0, (len(data)-12)//4, (index-12)//4, (material-12)//4)


def _bounds(data, positions):
    box = bounds(positions)
    for offset in (48, 76):
        struct.pack_into("<6f", data, offset, *box["max"], *box["min"])


def _name(text, length):
    encoded = text.encode("ascii")
    if len(encoded) >= length:
        raise ValueError("Native name buffer overflow")
    return encoded.ljust(length, b"\0")


def rebuild_static(template, vertices, strip, *, name=None, texture=None):
    parsed = parse_static_decoration(template)
    if not parsed or len(parsed["primitives"]) != 1 or len(parsed["materials"]) != 1:
        raise ValueError("Expected one-group static template")
    part = parsed["primitives"][0]
    if part["vertexOffset"] != 120 or part["vertexStride"] != 32:
        raise ValueError("Unsupported static template layout")
    count = len(vertices)//32
    if len(vertices) % 32 or not 3 <= count <= 65536 or len(strip) < 3 or min(strip) < 0 or max(strip) >= count:
        raise ValueError("Invalid native vertex/index counts")
    records = list(struct.iter_unpack("<8f", vertices))
    if not all(math.isfinite(v) for row in records for v in row):
        raise ValueError("Nonfinite native vertex")
    _, old_index, old_material = (12 + 4*n for n in struct.unpack_from("<3I", template))
    result = bytearray(template[:120])
    struct.pack_into("<2I", result, 108, count, len(strip)-2)
    if name is not None:
        _bounds(result, [list(row[:3]) for row in records])
    result.extend(vertices)
    node = bytearray(template[old_index-308:old_index])
    if name is not None:
        node[:32] = _name(name, 32)
    result.extend(node)
    index = len(result)
    result.extend(b"\0\0\1\0" + struct.pack(f"<{len(strip)}H", *strip))
    old_padding = template[part["indexOffset"] + part["sourceIndexCount"]*2:old_material]
    padding = -len(result) % 4
    result.extend(old_padding if len(old_padding) == padding else b"\0" * padding)
    material = len(result)
    tail = bytearray(template[old_material:])
    if name is not None:
        tail[3:67] = _name(name, 64)
    if texture is not None:
        offset = part["textures"][0]["offset"] - old_material
        tail[offset:offset+64] = _name(texture, 64)
    result.extend(tail)
    _header(result, index, material)
    if parse_static_decoration(bytes(result)) is None:
        raise ValueError("Generated DAT failed structural validation")
    return bytes(result)


def native_mesh(model, template):
    # Explicit reverse faces make cloth/signs visible from either side without
    # inventing undocumented material culling flags. Back normals are reversed.
    count = len(model.positions)//3
    if count * 2 > 65536:
        raise ValueError("Model exceeds bounded single-part u16 native writer")
    vertices = bytearray()
    for sign in (1, -1):
        for i in range(count):
            vertices.extend(struct.pack("<8f", *model.positions[i*3:i*3+3],
                                        *(n*sign for n in model.normals[i*3:i*3+3]), *model.uvs[i*2:i*2+2]))
    triangles = list(model.indices)
    for i in range(0, len(model.indices), 3):
        a, b, c = model.indices[i:i+3]
        triangles.extend((a+count, c+count, b+count))
    return rebuild_static(template, vertices, triangle_strip(triangles), name=model.name, texture=ATLAS)


def native_texture():
    # Standard DDS A8R8G8B8, supported by DX9; TEX XOR is the existing codec.
    image = Image.open(io.BytesIO(atlas())).convert("RGBA")
    width, height = image.size
    header = struct.pack("<7I", 124, 0x100F, height, width, width*4, 0, 0) + b"\0"*44
    header += struct.pack("<8I", 32, 0x41, 0, 32, 0xFF0000, 0xFF00, 0xFF, 0xFF000000)
    header += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    return dds_to_tex(b"DDS " + header + image.tobytes("raw", "BGRA"))


def parse_collision(data):
    if len(data) < 512:
        raise ValueError("Truncated collision")
    head = struct.unpack_from("<8I", data)
    total, index, material = (12 + 4*n for n in head[:3])
    count, triangles, layout = struct.unpack_from("<3I", data, 104)
    if (total != len(data) or head[3:] != (2, 1, 0, 1, 0) or not 3 <= count <= 65536
            or layout != 4 or not 1 <= triangles <= 200000 or index != 116+count*32+308
            or material != index+4+triangles*6 + (-(index+4+triangles*6) % 4)
            or total-material != 84 or data[32:48] != struct.pack("<4I", 1, 1, 0, 0)
            or data[72:76] != struct.pack("<I", 1) or data[100:104] != b"\0"*4
            or data[index-4:index+4] != b"\0"*6+b"\1\0"):
        raise ValueError("Unsupported collision layout")
    node = data[index-308:index-4]
    tail = data[material:]
    if tail[:3] != b"\0\0\1" or tail[67:] != b"\0"*17 or node[:32].split(b"\0")[0] != tail[3:67].split(b"\0")[0]:
        raise ValueError("Unsupported collision metadata")
    records = list(struct.iter_unpack("<8f", data[116:index-308]))
    indices = list(struct.unpack_from(f"<{triangles*3}H", data, index+4))
    if not all(math.isfinite(v) for row in records for v in row) or max(indices) >= count:
        raise ValueError("Invalid collision geometry")
    for offset in (48, 76):
        box = struct.unpack_from("<6f", data, offset)
        if not all(math.isfinite(v) for v in box) or any(box[i] < box[i+3] for i in range(3)):
            raise ValueError("Invalid collision bounds")
    return records, indices, index, material


def append_collision(template, vertices, triangles):
    records, old_triangles, old_index, old_material = parse_collision(template)
    if not vertices and not triangles:
        return template
    count = len(records)
    if len(vertices) + count > 65536 or len(triangles) % 3 or not triangles or min(triangles) < 0 or max(triangles) >= len(vertices):
        raise ValueError("Collision capacity or index boundary exceeded")
    records.extend(vertices)
    indices = old_triangles + [count+i for i in triangles]
    result = bytearray(template[:116])
    struct.pack_into("<2I", result, 104, len(records), len(indices)//3)
    _bounds(result, [list(row[:3]) for row in records])
    result.extend(b"".join(struct.pack("<8f", *row) for row in records))
    result.extend(template[old_index-308:old_index])
    index = len(result)
    result.extend(b"\0\0\1\0" + struct.pack(f"<{len(indices)}H", *indices))
    result.extend(b"\0" * (-len(result) % 4))
    material = len(result)
    result.extend(template[old_material:])
    _header(result, index, material)
    parse_collision(bytes(result))
    return bytes(result)


def collision_geometry(objects):
    records, indices = [], []
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    for obj in objects:
        name = model_name(obj["file"])
        if not name or not obj["visible"]:
            continue
        angle = math.radians(obj["rotation"])
        ca, sa = math.cos(angle), math.sin(angle)
        for center, size in collision_boxes(name):
            corners = []
            for x in (-1, 1):
                for y in (-1, 1):
                    for z in (-1, 1):
                        p = [(center[i] + sign*size[i]/2)*obj["scale"] for i, sign in enumerate((x,y,z))]
                        corners.append((p[0]*ca+p[2]*sa+obj["position"][0], p[1]+obj["position"][1],
                                        -p[0]*sa+p[2]*ca+obj["position"][2]))
            for face in faces:
                a,b,c,d = face[::-1]
                normal = unit(cross(add(corners[b], mul(corners[a], -1)), add(corners[c], mul(corners[a], -1))))
                start = len(records)
                records.extend((*corners[i], *normal, 0, 0) for i in (a,b,c,d))
                indices.extend(start+i for i in (0,1,2,0,2,3))
    return records, indices


def native_resources(client, objects):
    names = sorted({model_name(obj["file"]) for obj in objects if obj["visible"] and model_name(obj["file"])})
    if not names:
        return {}, None
    with zipfile.ZipFile(client / "Res/MapRes/DecoRes/Mesh00.res") as archive:
        template = archive.read("P0_Barrel01_C01.dat")
    collision = (client / "Res/Collision.res").read_bytes()
    if hashlib.sha256(template).hexdigest() != STATIC_HASH or hashlib.sha256(collision).hexdigest() != COLLISION_ARCHIVE_HASH:
        raise ValueError("Native export requires the verified pristine static and Collision.res templates")
    part = parse_static_decoration(template)["primitives"][0]
    vertices = template[part["vertexOffset"]:part["vertexOffset"]+part["vertexCount"]*32]
    strip = struct.unpack_from(f'<{part["sourceIndexCount"]}H', template, part["indexOffset"])
    if rebuild_static(template, vertices, strip) != template:
        raise ValueError("Stock static byte round-trip failed")
    texture = native_texture()
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.writestr(name + ".dat", native_mesh(build_model(name), template))
        archive.writestr(ATLAS + ".tex", texture)
    vertices, triangles = collision_geometry(objects)
    collision_out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(collision)) as source, zipfile.ZipFile(collision_out, "w", compression=zipfile.ZIP_DEFLATED) as dest:
        for entry in source.infolist():
            raw = source.read(entry)
            if entry.filename in ("ColMesh_TT.dat", "ColMesh_TT_CR.dat"):
                raw = append_collision(raw, vertices, triangles)
            dest.writestr(entry, raw)
    return {"Res/StageObj/Oktoberfest.res": packed.getvalue(), "Res/Collision.res": collision_out.getvalue()}, texture
