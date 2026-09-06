"""Derive richer royal-blue festival cloth from private, pinned stock-fold paint."""
import hashlib
import json
import math
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.amp/tmp/beer-cart/stock-paint'
OUT=ROOT/'exports/blender-festival/textures'


def main():
    fold=SOURCE/'canvas-fold.png'; diamonds=SOURCE/'cloth-diamonds.png'
    assert hashlib.sha256(fold.read_bytes()).hexdigest()=='00b5162dc68c0dd96999bf437de7511a5b98b4bf178e6e9f888cd87f35032ddb'
    assert hashlib.sha256(diamonds.read_bytes()).hexdigest()=='5dc55028e4206113745990e734f0badae10c50222a1998997c86a1094863e81f'
    OUT.mkdir(parents=True,exist_ok=True)
    records=[]
    for path,name in [(fold,'royal-swag.png'),(fold,'cream-swag.png'),(diamonds,'royal-diamonds.png')]:
        image=Image.open(path).convert('RGB'); pixels=[]
        for index,(r,g,b) in enumerate(image.getdata()):
            luminance=(.2126*r+.7152*g+.0722*b)/255
            if path==fold:
                v=1-(index//image.width)/(image.height-1)
                if name=='royal-swag.png':
                    wave=math.cos(2*math.pi*(v-.10))
                    factor=(.80+.22*wave+.12*math.cos(6*math.pi*(v-.03))-.14*math.exp(-((v-.97)/.03)**2))*(.8+.3*luminance)
                    highlight=max(0,wave)*18
                    pixel=tuple(round(min(255,c*factor+highlight)) for c in (39,84,154))
                else:
                    factor=(.90+.15*math.cos(2*math.pi*(v-.57)/.34)-.14*math.exp(-((v-.76)/.035)**2))*(.85+.2*luminance)
                    pixel=tuple(round(min(255,c*factor)) for c in (227,222,205))
            else:
                # Blue and cream are separated by signed chroma, continuously
                # interpolated at antialiased edges rather than clipping highlights.
                weight=max(0,min(1,(b-r)/24))
                factor=.6+.65*luminance
                pixel=tuple(round(old*(1-weight)+v*factor*weight) for old,v in zip((r,g,b),(39,84,154)))
            pixels.append(pixel)
        image.putdata(pixels);image.save(OUT/name)
        records.append({'input':str(path),'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'output':str(OUT/name),'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()})
    (OUT/'provenance.json').write_text(json.dumps({'reference':'.amp/tmp/festival/references/dense-court.png','stockProvenance':str(SOURCE/'provenance.json'),'diamondProvenance':str(SOURCE/'cloth-diamonds-provenance.json'),'method':'Royal-blue RGB39/84/154 art direction; stock-fold luminance retained. Broad UV-v fold crest/trough modulation and rolled-hem shadow authored for blue/cream swag paint. Continuous blue-chroma remap preserves cream diamonds. Original PNGs untouched.','textures':records},indent=2)+'\n')


if __name__=='__main__':main()
