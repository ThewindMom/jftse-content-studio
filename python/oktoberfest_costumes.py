"""Private costumes retaining stock identities, skeleton and animation bytes.

Material aliases and masked texture blocks supplement an experimental extra
skinned garment group. Jjijil hair receives a bounded vertex refit beneath the
hat. Native attachment and deformation remain unverified.
"""
import hashlib
import io
import struct
import zipfile

from PIL import Image

from adu_pose import parse_bind_pose
from tex_codec import tex_to_dds, dds_to_tex
from oktoberfest_garments import append_garments
from oktoberfest_native import ATLAS, native_texture
from oktoberfest_models import add, cross, mul, unit

ARCHIVE = "Res/StageObj/OktoberNPC.res"
SOURCES = {
    "Judge": ("Object02", "RefereeOwl00", "f4bc94a8be4823c501977cb469609683a55ed3baab639f29d9c501976dfb32b8"),
    "Chick": ("Object02", "Chick00", "28b5fdb34e6faff5811a06559b677f2b8116ff6db172331d19e22a6dd38453f8"),
    "Brewer": ("Object03", "Engineer00h", "6e477e5b23cdb2bbc3e2b313319bdcab8841beb88b677e50f7a8d5a36e5e0387"),
    "Visitor": ("Object03", "Pirate00", "4c105c58db3fb79670374a8137e5def2055d1776e616e29125ac7725c58feeeb"),
    "Greeter": ("Object01", "Jjijil00", "0505a3ff7d8f1c687e9d02a347a3e94b88b7125a7a5401eae65e1ae7eaac8544"),
}
VARIANTS = {f"Oktoberfest_{role}{style}": (role,style) for role in SOURCES for style in ("Forest","Wine")}
TEXTURES = {
    "RefereeOwl00": "163e8100c3bd35f615c0ebd5b3695011d635ea493039eb775879697a34ece6c6",
    "Chick00": "efd35c5385af3110d6e2c7a132a8d118d103d0f7ae1d36c15c948d034692fe74",
    "Engineer00": "c0348b05c533f3292cdfb430a210ede31e5ca2f3a119f28f965ac97f500bcf58",
    "Pirate00a": "a7a5d7f08e2f97316bfa2bf71fb8bdf1a737a27b325a1b9afa55aa188eec8a3b",
    "Pirate00b": "444fac6cfaf5478adc8ddf3e264acdd26db9127b84ee0a8a3bcd5acef61967c5",
    "Jjijil00": "39e5025fbda164212ec91433fd766d14a56f233bd5e67d4b036fd1385d3fa9b1",
}


def paint_costume(image, role, style, material):
    """UV-space garment masks, authored against inspected private atlases."""
    image = image.convert("RGBA")
    result = image.copy()
    mask = Image.new("L",image.size)
    base = (52,91,59) if style == "Forest" else (126,48,48)
    trim = (222,181,85) if style == "Forest" else (230,213,165)
    src, dst, changed = image.load(), result.load(), mask.load()
    for y in range(image.height):
        for x in range(image.width):
            u,v = x*256/image.width,y*256/image.height
            r,g,b,a = src[x,y]
            blue = b > r*1.15 and g > r*.95
            if role == "Greeter":
                # Inspected Jjijil UV islands: sleeves at the top, white jacket
                # in the middle, shorts at the bottom. Face, hands, shoes and
                # the characteristic sweet are outside these garment masks.
                sleeve = blue and v<96 and u>58
                jacket = 97<u<194 and 77<v<150 and min(r,g,b)>150 and max(r,g,b)-min(r,g,b)<70
                shorts = blue and v>194
                if a and (sleeve or jacket or shorts):
                    shade = .72+.28*(r+g+b)/(3*255)
                    color = (240,226,188) if sleeve else (109,70,43) if shorts else base
                    if jacket:
                        seam = abs(u-131.5)<.7 and 82<v<132
                        button = any((u-133.5)**2+(v-yb)**2<1.1 for yb in (90,102,114,126))
                        hem = 114<v<116 and u<130 or 132<v<134 and u>130
                        if seam or hem: color = (41,61,37) if style=="Forest" else (87,35,35)
                        if button: color = (224,190,112)
                    dst[x,y] = (*[min(255,int(c*shade)) for c in color],a)
                    changed[x,y] = 255
                continue
            selected = False
            if role == "Judge":
                selected = 48<u<154 and 90<v<184 and r>g*1.25 and g>b*1.25
            elif role == "Chick":
                selected = False  # Feather identity stays stock; clothes are geometry.
            elif role == "Brewer":
                selected = (205<v<249 and 62<u<246) or (109<v<181 and 12<u<147 and r>g*1.12 and g>b)
            elif role == "Visitor" and material == "Pirate00a":
                selected = blue
            if not selected or a == 0:
                continue
            # Garment-specific seams/buttons, not a grid stamped over every UV.
            shade = .65 + .55*(r+g+b)/(3*255)
            if role == "Chick":
                strap = (abs(u-125)<2 or abs(u-185)<2) and v>148 or abs(v-210)<1.5
            elif role == "Judge":
                strap = any((u-120)**2+(v-y)**2 < 3 for y in (130,143,156))
            elif role == "Brewer":
                strap = abs(u-78)<1.5 and v<180 or abs(v-208)<1.5
            else:
                strap = abs(v-151)<1.5
            color = trim if strap else base
            dst[x,y] = (*[min(255,int(c*shade)) for c in color],a)
            changed[x,y] = 255
    return result, mask


def encode_masked_texture(original, image, mask):
    """Keep the observed DDS format/header; replace only touched DXT blocks."""
    source = tex_to_dds(original)
    height,width = struct.unpack_from("<2I",source,12)
    levels = max(1,struct.unpack_from("<I",source,28)[0])
    fourcc = source[84:88]
    if fourcc not in (b"DXT1",b"DXT3",b"DXT5") or image.size != (width,height):
        raise ValueError("Unsupported costume texture format")
    result = bytearray(source)
    offset, block = 128, 8 if fourcc == b"DXT1" else 16
    for _ in range(levels):
        encoded = io.BytesIO()
        image.save(encoded,format="DDS",pixel_format=fourcc.decode())
        raw = encoded.getvalue()
        columns,rows = max(1,(image.width+3)//4),max(1,(image.height+3)//4)
        size = columns*rows*block
        if raw[84:88] != fourcc or len(raw) != size+128 or offset+size>len(source):
            raise ValueError("Unexpected compressed costume payload")
        for y in range(rows):
            for x in range(columns):
                if mask.crop((x*4,y*4,min(image.width,x*4+4),min(image.height,y*4+4))).getbbox():
                    start = (y*columns+x)*block
                    result[offset+start:offset+start+block] = raw[128+start:128+start+block]
        offset += size
        size = (max(1,image.width//2),max(1,image.height//2))
        image = image.resize(size,Image.Resampling.LANCZOS)
        mask = mask.resize(size,Image.Resampling.LANCZOS)
    if offset != len(source):
        raise ValueError("Unexpected costume mip boundary")
    return dds_to_tex(bytes(result))


def refit_source_geometry(data, parsed, role, images):
    """Refit Jjijil's covered tuft; retain topology and skin weights.

    Only hash-locked source callers use this. Face-color vertices are not moved.
    Node and animation payloads are not interpreted or modified.
    """
    if role != "Greeter":
        return
    for part in parsed["primitives"]:
        image=images[part["textures"][0]["name"]]
        changed=False
        positions=[list(p) for p in part["positions"]]
        for i,(position,uv) in enumerate(zip(positions,part["uvs"])):
            x,y,z=position
            r,g,b,*_=image.getpixel((min(image.width-1,max(0,int(uv[0]*image.width))),
                                    min(image.height-1,max(0,int(uv[1]*image.height)))))
            if role == "Greeter" and y>8.6 and g>r*1.05:
                position[1]=8.6
            if position != part["positions"][i]:
                struct.pack_into("<3f",data,part["vertexOffset"]+i*part["vertexStride"],*position)
                changed=True
        if changed:
            normals=[[0.,0.,0.] for _ in positions]
            for start in range(0,len(part["indices"]),3):
                indices=part["indices"][start:start+3]
                a,b,c=[positions[j] for j in indices]
                normal=cross(add(b,mul(a,-1)),add(c,mul(a,-1)))
                for j in indices:
                    normals[j]=add(normals[j],normal)
            for i,normal in enumerate(normals):
                struct.pack_into("<3f",data,part["vertexOffset"]+i*part["vertexStride"]+12,*unit(normal))


def build_costumes(client, names=None):
    names = list(VARIANTS) if names is None else sorted(set(names))
    packed = io.BytesIO()
    textures = {}
    with zipfile.ZipFile(packed,"w",compression=zipfile.ZIP_DEFLATED) as output:
        for name in names:
            role,style = VARIANTS[name]
            archive,member,expected = SOURCES[role]
            with zipfile.ZipFile(client/f"Res/StageObj/{archive}.res") as source:
                original = source.read(member+".dat")
                if hashlib.sha256(original).hexdigest() != expected:
                    raise ValueError("Costume source DAT changed: "+member)
                parsed = parse_bind_pose(original)
                if parsed is None:
                    raise ValueError("Unsupported costume rig: "+member)
                data = bytearray(original)
                images = {}
                for part in parsed["primitives"]:
                    for texture in part["textures"]:
                        material = texture["name"]
                        alias = name+"_"+material
                        if len(alias.encode()) >= 64:
                            raise ValueError("Costume texture alias too long")
                        if alias+".tex" not in textures:
                            raw = source.read(material+".tex")
                            if hashlib.sha256(raw).hexdigest() != TEXTURES.get(material):
                                raise ValueError("Costume source TEX changed: "+material)
                            image = Image.open(io.BytesIO(tex_to_dds(raw))).convert("RGBA")
                            images[material] = image
                            painted,mask = paint_costume(image,role,style,material)
                            textures[alias+".tex"] = encode_masked_texture(raw,painted,mask)
                        offset = texture["offset"]
                        data[offset:offset+64] = alias.encode().ljust(64,b"\0")
                # Fields are fixed width; everything before materials, including
                # vertices, bones, animation samples and indices, stays identical.
                material_start = 12+struct.unpack_from("<I",original,8)[0]*4
                if data[:material_start] != original[:material_start] or parse_bind_pose(bytes(data)) is None:
                    raise ValueError("Costume rig preservation failed")
                refit_source_geometry(data,parsed,role,images)
                output.writestr(name+".dat",append_garments(bytes(data),role,style))
        if names:
            textures[ATLAS+".tex"] = native_texture()
        for name,data in textures.items():
            output.writestr(name,data)
    return packed.getvalue(),textures
