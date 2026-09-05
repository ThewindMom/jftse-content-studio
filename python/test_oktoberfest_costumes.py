import hashlib
import io
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from adu_pose import parse_bind_pose
from compose_festplatz_court import compose
from oktoberfest_costumes import build_costumes, encode_masked_texture, paint_costume, VARIANTS
from oktoberfest_garments import chicken_garments, garments
from oktoberfest_models import add, cross, mul
from test_adu_pose import synthetic_pose
from tex_codec import dds_to_tex, tex_to_dds


def texture(format="DXT1"):
    out = io.BytesIO()
    Image.new("RGBA",(16,16),(210,180,140,255)).save(out,format="DDS",pixel_format=format)
    return dds_to_tex(out.getvalue())


class CostumeTests(unittest.TestCase):
    def test_soldier_remains_stock_and_has_no_costume_variant(self):
        soldier=dict(id="stock-soldier",file="Res/StageObj/Object02/Soldier00.dat",name="Soldier",
                     position=[-80,0,110],rotation=120,scale=1.3,animation=0,phase=0,visible=True,level=2)
        self.assertEqual(compose({"objects":[soldier]})["objects"][0],soldier)
        self.assertFalse(any("Steward" in name for name in VARIANTS))

    def test_jjijil_uses_original_clothing_surface_not_an_extra_body_shell(self):
        for style in ("Forest","Wine"):
            model,anchors = garments(None,"Greeter",style)
            self.assertEqual(len(anchors),len(model.positions)//3)
            self.assertGreaterEqual(min(model.positions[1::3]),7.7)
            image = Image.new("RGBA",(256,256),(240,195,160,255))
            # Representative sleeve, jacket, shorts, face, hand and sweet.
            samples = {(75,40):(20,110,170,255),(120,100):(220,225,230,255),
                       (170,210):(20,110,170,255),(60,175):(240,195,160,255),
                       (205,125):(240,195,160,255),(230,175):(240,235,220,255)}
            for point,color in samples.items(): image.putpixel(point,color)
            result,mask = paint_costume(image,"Greeter",style,"Jjijil00")
            for point in ((75,40),(120,100),(170,210)):
                self.assertNotEqual(result.getpixel(point),image.getpixel(point))
                self.assertEqual(mask.getpixel(point),255)
            for point in ((60,175),(205,125),(230,175)):
                self.assertEqual(result.getpixel(point),image.getpixel(point))
                self.assertEqual(mask.getpixel(point),0)

    def test_chicken_tailoring_has_complete_bindings_and_no_wood_or_degenerate_faces(self):
        for style in ("Forest","Wine"):
            model,anchors = chicken_garments(style)
            self.assertEqual(len(anchors),len(model.positions)//3)
            # Wood swatches occupy the first half of the top atlas row.
            self.assertFalse(any(u<.5 and v<.25 for u,v in zip(model.uvs[::2],model.uvs[1::2])))
            for i in range(0,len(model.indices),3):
                a,b,c = [model.positions[j*3:j*3+3] for j in model.indices[i:i+3]]
                normal = cross(add(b,mul(a,-1)),add(c,mul(a,-1)))
                self.assertGreater(sum(x*x for x in normal),1e-15)

    def test_masked_dxt_blocks_preserve_header_untouched_pixels_and_alpha(self):
        for format in ("DXT1","DXT3"):
            original = texture(format)
            image = Image.open(io.BytesIO(tex_to_dds(original))).convert("RGBA")
            blank = Image.new("L",image.size)
            self.assertEqual(encode_masked_texture(original,image,blank),original)
            image.putpixel((2,2),(20,90,50,255))
            blank.putpixel((2,2),255)
            new = encode_masked_texture(original,image,blank)
            block = 8 if format == "DXT1" else 16
            self.assertEqual(new[:128],original[:128])
            self.assertNotEqual(new[128:128+block],original[128:128+block])
            self.assertEqual(new[128+block:],original[128+block:])
            result = Image.open(io.BytesIO(tex_to_dds(new))).convert("RGBA")
            self.assertEqual(result.getchannel("A").getextrema(),(255,255))

    def test_chick_feathers_stay_stock_when_costumes_are_geometry(self):
        image = Image.new("RGBA",(256,256),(245,225,190,255))
        forest,mask = paint_costume(image,"Chick","Forest","Chick00")
        wine,_ = paint_costume(image,"Chick","Wine","Chick00")
        self.assertEqual(forest.tobytes(),image.tobytes())
        self.assertIsNone(mask.getbbox())
        self.assertEqual(forest.tobytes(),wine.tobytes())

    def test_extra_garment_group_preserves_body_and_rig_and_hashes_fail_closed(self):
        data,_,_ = synthetic_pose()
        tex = texture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"Res/StageObj").mkdir(parents=True)
            with zipfile.ZipFile(root/"Res/StageObj/Object02.res","w") as z:
                z.writestr("Chick00.dat",data)
                z.writestr("BodyTex.tex",tex)
            sources = {"Chick":("Object02","Chick00",hashlib.sha256(data).hexdigest())}
            with patch("oktoberfest_costumes.SOURCES",sources), patch("oktoberfest_costumes.TEXTURES",{"BodyTex":hashlib.sha256(tex).hexdigest()}):
                archive,_ = build_costumes(root,["Oktoberfest_ChickForest"])
                with zipfile.ZipFile(io.BytesIO(archive)) as z:
                    new = z.read("Oktoberfest_ChickForest.dat")
                before,after = parse_bind_pose(data),parse_bind_pose(new)
                self.assertEqual(new[32:before["geometryEnd"]],data[32:before["geometryEnd"]])
                old_index = 12+struct.unpack_from("<I",data,4)[0]*4
                new_index = 12+struct.unpack_from("<I",new,4)[0]*4
                self.assertEqual(new[after["geometryEnd"]:new_index],data[before["geometryEnd"]:old_index])
                self.assertEqual(after["animationCount"],1)
                self.assertEqual(len(after["materials"]),len(before["materials"])+1)
                self.assertEqual(after["primitives"][-1]["textures"][0]["name"],"Oktoberfest_Atlas")
                with patch("oktoberfest_costumes.TEXTURES",{}):
                    with self.assertRaisesRegex(ValueError,"source TEX changed"):
                        build_costumes(root,["Oktoberfest_ChickForest"])
            with self.assertRaisesRegex(ValueError,"source DAT changed"):
                build_costumes(root,["Oktoberfest_ChickForest"])

    def test_composition_is_idempotent_and_retains_clip_values(self):
        doc = {"objects":[dict(id="stock-0",file="Res/StageObj/Object02/Chick00.dat",name="Chick",
               position=[70,0,20],rotation=90,scale=2,animation=0,phase=0,visible=True,level=2)]}
        new = compose(doc)
        self.assertEqual(compose(new),new)
        for key in ("position","rotation","scale","animation","phase"):
            self.assertEqual(new["objects"][0][key],doc["objects"][0][key])


if __name__ == "__main__":
    unittest.main()
