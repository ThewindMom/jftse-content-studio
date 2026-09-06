"""Compose the dense reference court from verified, privately imported Blender props.

Usage: python compose_blender_festival.py INPUT.json ASSETS.json OUTPUT.json
ASSETS maps builder slugs to the actual Studio import API responses.
"""
import copy
import json
import math
import sys
from pathlib import Path


def compose(document, assets):
    if document.get('mapId') != 'oktoberfest':
        raise ValueError('Expected the fingerprinted Oktoberfest layout')
    result = copy.deepcopy(document)
    result['objects'] = [o for o in result['objects'] if not o['id'].startswith(
        ('dense-', 'court-fest-baseline-', 'court-fest-corner-', 'detail-entry-',
         'detail-market-', 'detail-tent-approach', 'detail-fountain-west', 'detail-fountain-east'))]
    objects = {o['id']: o for o in result['objects']}

    def place(identity, slug, position, rotation=0, scale=12):
        asset = assets[slug]
        if identity not in objects:
            obj = dict(id=identity, level=1, animation=-1, phase=0)
            objects[identity] = obj
            result['objects'].append(obj)
        obj = objects[identity]
        obj.update(name=slug.replace('-', ' '), file=asset['file'],
                   position=position, rotation=rotation, scale=scale, visible=True,
                   animation=-1, phase=0)

    # The reference looks from +stage-Z. Its far entrance is the -Z baseline.
    # Imported front +GLB-Z becomes -stage-Z in the native/Studio world.
    place('festplatz-entrance', 'festival-arch-leafy', [0, 0, -168], 180, 22)
    place('festplatz-hall', 'pretzel-stand', [165, -7.35, -213], 130, 18)
    place('festplatz-pretzels', 'pretzel-stand', [150, -7.35, -75], 115, 23)
    place('festplatz-food', 'food-stand', [-130, -7.35, -220], -145, 16)
    place('festplatz-hearts', 'gingerbread-stand', [-221, -7.35, -83], -90, 15)
    place('festplatz-table-0', 'beer-garden', [-168, -7.35, -105], 15, 12)
    place('festplatz-table-1', 'beer-garden-festive', [-215, -7.35, -145], -15, 12)
    place('festplatz-table-2', 'beer-garden', [-224, -7.35, 111], 60, 12)
    place('festplatz-terrace-table', 'beer-garden-festive', [199, -7.35, -141], 20, 12)
    place('festplatz-maypole-0', 'maypole', [128, -7.35, -167], 180, 16)
    place('festplatz-maypole-1', 'maypole', [-115, -7.35, -187], 180, 11)
    place('dense-barrel-display', 'barrel-display', [-100, -7.35, -185], 180, 13)
    place('dense-heart-alternate', 'gingerbread-heart', [214, -7.35, -85], 110, 16)

    # Curved sections share post centers; the foreground bows beyond the baseline.
    pitch = 2.8 * 12
    radius = pitch
    corner_x, corner_z = 2.5 * pitch, 4 * pitch
    place('dense-foreground-curve', 'festival-fence-foreground', [0,0,183], 180)
    for side in (-1, 1):
        place(f'dense-back-fence-{side}', 'festival-fence', [side*2*pitch, 0, -corner_z-radius], 180)
        for end in (-1, 1):
            place(f'dense-curved-corner-{side}-{end}', 'festival-fence-curved',
                  [side*(corner_x+radius/math.sqrt(2)), 0, end*(corner_z+radius/math.sqrt(2))],
                  math.degrees(math.atan2(-side, -end)))
        for i in range(8):
            z = (i-3.5)*pitch
            # The right middle run bows around the fountain; carriages keep open bays.
            if side == -1 and z > -67.2:
                continue
            if side == 1 and -110 < z < -30:
                continue
            place(f'dense-side-fence-{side}-{i}', 'festival-fence', [side*(corner_x+radius), 0, z],
                  90 if side == 1 else -90)
    place('dense-fountain-curve', 'festival-fence-fountain', [-93,0,0], -90)

    # Interior corner bouquets anchor small hay/sign groups, not an even scatter.
    corners = [(-94,-145),(-84,151),(98,-147),(84,151)]
    for i, (x, z) in enumerate(corners + [(-108,-111),(101,92)]):
        place(f'dense-flower-anchor-{i}', 'flower-barrel', [x, 0, z], 180, 18)
    for i, (x, y, z) in enumerate([(105,0,-110),(94,0,54),(-139,-7.35,-151),(-139,-7.35,-105),
                                  (-215,-7.35,-113),(-190,-7.35,-166),(147,-7.35,150),(26,0,169),
                                  (-27,0,169),(-138,-7.35,133),(94,0,106),(155,-7.35,-130)]):
        place(f'dense-flower-secondary-{i}', 'flower-barrel', [x,y,z], 180 if y == 0 else i*37, 13)

    for i, (x, z, yaw) in enumerate([(133,-149,135),(-133,-149,-135),
                                    (103,130,155),(-103,130,-155)]):
        place(f'dense-banner-{i}', 'festival-banner', [x,-7.35 if i < 2 else 0,z], yaw, 20)
    for i, (x, z, yaw) in enumerate([(87,-112,165),(-89,-114,-165),
                                    (100,72,155),(-88,128,-155),
                                    (96,30,155),(-189,-150,-155)]):
        place(f'dense-chalkboard-{i}', ('chalkboard-pretzel','chalkboard-tennis','chalkboard-beer')[i%3],
              [x, 0 if i < 5 else -7.35, z], yaw, 14)
    for i, (x, z) in enumerate([(101,150),(85,165),(-102,153),(-84,166),
                               (83,-158),(108,-163),(-108,-156),(-106,-130),
                               (108,43),(109,114),(-197,-145),(-175,-171)]):
        place(f'dense-hay-{i}', 'hay-bale', [x,0 if i < 10 else -7.35,z], i*29, 16)

    # Rope spans terminate at banner/gate supports, well behind the baseline.
    rope_scale = math.hypot(133-44, 168-149) / 5
    for side in (-1, 1):
        place(f'dense-overhead-{side}', 'pennant-line', [side*88.5, 58.8-.5*rope_scale, -158.5],
              -side*math.degrees(math.atan2(19,89)), rope_scale)
    for i, (x,z) in enumerate([(45,158),(-50,159),(86,-185),(-76,-185)]):
        place(f'dense-small-barrel-{i}', 'barrel-display', [x,0 if i < 2 else -7.35,z], 180, 9)

    protected = [o for o in document['objects'] if o['id'].startswith('stock-')]
    if [o for o in result['objects'] if o['id'].startswith('stock-')] != protected:
        raise AssertionError('Stock actors and carriages changed')
    if len(result['objects']) > 500:
        raise ValueError('Composition exceeds Studio placement limit')
    return result


if __name__ == '__main__':
    source, assets, destination = map(Path, sys.argv[1:])
    result = compose(json.loads(source.read_text()), json.loads(assets.read_text()))
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(result["objects"])} placements; stock records and fingerprint preserved')
