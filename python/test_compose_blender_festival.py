import copy
import hashlib
import math
import unittest

from compose_blender_festival import compose


SLUGS = ('festival-arch-leafy pretzel-stand food-stand gingerbread-stand '
         'beer-garden beer-garden-festive maypole barrel-display gingerbread-heart '
         'festival-fence festival-fence-curved festival-fence-fountain festival-fence-foreground '
         'flower-barrel festival-banner chalkboard-pretzel '
         'chalkboard-tennis chalkboard-beer hay-bale pennant-line').split()


class DenseFestivalCompositionTests(unittest.TestCase):
    def setUp(self):
        self.assets = {slug: {'file': 'Studio/Imported/' + hashlib.sha256(slug.encode()).hexdigest() + '.glb'}
                       for slug in SLUGS}
        self.doc = dict(version=1, mapId='oktoberfest', name='Private study', sourceHash='a'*64,
                        objects=[dict(id='stock-10', name='Original carriage',
                                      file='Res/StageObj/Object02/Carriage00.dat',
                                      position=[-105,0,90], rotation=-85, scale=1.3,
                                      visible=True, animation=0, phase=0, level=2)])

    def test_preserves_stock_and_fingerprint_without_mutating_input(self):
        original = copy.deepcopy(self.doc)
        result = compose(self.doc, self.assets)
        self.assertEqual(self.doc, original)
        self.assertEqual(result['sourceHash'], original['sourceHash'])
        self.assertEqual(result['objects'][0], original['objects'][0])

    def test_repeated_composition_is_identical_and_perimeter_stays_clear(self):
        result = compose(self.doc, self.assets)
        self.assertEqual(compose(result, self.assets), result)
        self.assertEqual(len({o['id'] for o in result['objects']}), len(result['objects']))
        for obj in result['objects'][1:]:
            x, _, z = obj['position']
            self.assertTrue(abs(x) >= 70 or abs(z) >= 130, obj['id'])
        self.assertLess(len(result['objects']), 500)

    def test_foreground_sweep_joins_corners_and_entrance_stays_clear(self):
        objects = {o['id']: o for o in compose(self.doc, self.assets)['objects']}
        front = objects['dense-foreground-curve']
        self.assertEqual(front['rotation'], 180)
        self.assertEqual(front['position'], [0,0,183])
        self.assertAlmostEqual(7*front['scale'], 84)
        self.assertAlmostEqual(front['position'][2]-1.25*front['scale'], 168)
        self.assertEqual(objects['festplatz-entrance']['rotation'], 180)
        self.assertLess(objects['festplatz-entrance']['position'][2], -130)

    def test_curved_corners_join_perimeter_posts(self):
        objects = {o['id']: o for o in compose(self.doc, self.assets)['objects']}
        radius = 2.8
        for side in (-1, 1):
            for end in (-1, 1):
                obj = objects[f'dense-curved-corner-{side}-{end}']
                angle = math.radians(obj['rotation'])
                actual = []
                for x in (-radius/math.sqrt(2), radius/math.sqrt(2)):
                    z = radius/math.sqrt(2)-radius
                    actual.append((obj['position'][0]+obj['scale']*(math.cos(angle)*x-math.sin(angle)*z),
                                   obj['position'][2]+obj['scale']*(-math.sin(angle)*x-math.cos(angle)*z)))
                expected = [(side*84, end*168), (side*117.6, end*134.4)]
                for point in expected:
                    self.assertLess(min(math.dist(point, p) for p in actual), 1e-8)
                self.assertEqual(obj['scale'], 12)

    def test_pennant_ends_meet_gate_and_banner_poles(self):
        objects = {o['id']: o for o in compose(self.doc, self.assets)['objects']}
        for side in (-1, 1):
            obj = objects[f'dense-overhead-{side}']
            angle = math.radians(obj['rotation'])
            ends = [(obj['position'][0]+x*obj['scale']*math.cos(angle),
                     obj['position'][2]-x*obj['scale']*math.sin(angle)) for x in (-2.5,2.5)]
            for point in [(side*44,-168),(side*133,-149)]:
                self.assertLess(min(math.dist(point, p) for p in ends), 1e-8)
            self.assertAlmostEqual(obj['position'][1]+.5*obj['scale'], 58.8)

    def test_fountain_run_bows_between_court_and_stock_basin(self):
        objects = {o['id']: o for o in compose(self.doc, self.assets)['objects']}
        obj = objects['dense-fountain-curve']
        self.assertEqual(obj['position'], [-93,0,0])
        self.assertEqual(obj['rotation'], -90)
        radius = (5.6**2+2.05**2)/(2*2.05)
        arc = math.asin(5.6/radius)
        for i in range(33):
            t = -arc+2*arc*i/32
            x = -93+(radius*math.cos(t)-radius)*obj['scale']
            z = radius*math.sin(t)*obj['scale']
            self.assertGreater(abs(x), 70)
            self.assertGreater(math.hypot(x+154.13,z-.23), 53.72)
        self.assertAlmostEqual(x, -117.6)
        self.assertAlmostEqual(z, 67.2)

    def test_rejects_another_map(self):
        self.doc['mapId'] = 'twinkle'
        with self.assertRaises(ValueError):
            compose(self.doc, self.assets)


if __name__ == '__main__':
    unittest.main()
