"""Host Pillow paint preparation; private output, source crops unchanged."""
import hashlib
import json
import math
import random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

root=Path(__file__).resolve().parents[2]/'.amp/tmp/beer-cart/stock-paint'
source=root/'canvas-fold.png'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='00b5162dc68c0dd96999bf437de7511a5b98b4bf178e6e9f888cd87f35032ddb'
fold=Image.open(source).convert('L').resize((512,512))
rng=random.Random(728)
hay=Image.new('RGB',(512,512));pixels=hay.load()
for y in range(512):
    for x in range(512):
        shade=.65+.35*fold.getpixel((x,y))/255
        pixels[x,y]=tuple(int(v*shade) for v in (196,156,69))
draw=ImageDraw.Draw(hay)
for i in range(2200):
    x=rng.randrange(512);y=rng.randrange(512);dy=rng.randrange(6,65)
    draw.line((x,y,x+rng.randrange(-5,6),y+dy),fill=rng.choice(['#d4b46a','#af8a38','#e7ce82','#8d742f']),width=1)
hay.save(root/'hay-paint.png')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',34)
for kind,label in [('beer','BIER'),('pretzel','BREZEL'),('tennis','TENNIS')]:
    im=Image.new('RGB',(384,512));px=im.load()
    for y in range(512):
        for x in range(384):
            v=30+int(fold.getpixel((x,y))*.035)+rng.randrange(5)
            px[x,y]=(v,v+7,v+3)
    d=ImageDraw.Draw(im);chalk='#e9dfbf'
    d.rounded_rectangle((17,18,367,494),radius=12,outline='#b6b399',width=3)
    d.text((192,68),label,font=font,anchor='mm',fill=chalk)
    if kind=='beer':
        d.rounded_rectangle((104,171,241,328),radius=15,outline=chalk,width=8)
        d.arc((200,186,306,300),270,90,fill=chalk,width=9)
        for x in (140,174,208): d.line((x,207,x,302),fill=chalk,width=5)
        for x,y in ((115,169),(146,154),(181,160),(215,167)):
            d.ellipse((x-23,y-17,x+23,y+17),fill=chalk)
    elif kind=='pretzel':
        path=[(-.5,-.3),(-.3,-.15),(.15,.4),(.4,.65),(.7,.65),(.93,.4),(1,.05),(.9,-.32),(.65,-.55),(0,-.68),(-.65,-.55),(-.9,-.32),(-1,.05),(-.93,.4),(-.7,.65),(-.4,.65),(-.15,.4),(.3,-.15),(.5,-.3)]
        d.line([(192+x*116,245-z*116) for x,z in path],fill=chalk,width=13,joint='curve')
    else:
        for cx,cy,sign in [(130,207,1),(250,207,-1)]:
            d.ellipse((cx-45,cy-63,cx+45,cy+63),outline=chalk,width=7)
            for dx in (-24,-12,0,12,24): d.line((cx+dx,cy-43,cx+dx,cy+43),fill=chalk,width=2)
            for dy in (-36,-18,0,18,36): d.line((cx-31,cy+dy,cx+31,cy+dy),fill=chalk,width=2)
            d.line((cx,cy+63,cx+sign*65,cy+155),fill=chalk,width=9)
        d.ellipse((176,277,204,305),outline=chalk,width=4)
    for y in (383,410,437):
        d.line([(91,y),(142,y-3),(190,y+1),(238,y-2),(285,y)],fill='#aaa78f',width=3)
    im.save(root/f'chalk-{kind}.png')
outputs=['hay-paint.png']+[f'chalk-{k}.png' for k in ('beer','pretzel','tennis')]
report={'source':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sourceProvenance':'provenance.json canvas-fold Carriage00a crop','method':'Stock fold luminance recolored to straw with drawn fibers; authored opaque chalk pictograms on stock-fold-modulated dark board','outputs':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in outputs}}
(root/'dressing-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
