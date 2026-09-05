import copy
import math
import unittest

from compose_festplatz_perimeter import compose
from oktoberfest_models import build_model, collision_boxes


def stock():
    return dict(mapId="twinkle", objects=[
        dict(id="stock-0", file="Res/StageObj/Object02/Soldier00.dat",
             position=[-80,0,110], rotation=120, scale=1.3, animation=0, phase=0),
        dict(id="stock-1", file="Res/StageObj/Object02/Carriage00.dat",
             position=[-105,0,90], rotation=-85, scale=1.3, animation=0, phase=0),
    ])


class PerimeterTests(unittest.TestCase):
    def test_composition_preserves_actors_fingerprint_and_unrelated_edits(self):
        source = dict(mapId="oktoberfest", sourceHash="synthetic-source", objects=[
            dict(id="designer-tree", file="Res/Tree.dat", position=[250,0,100], name="Keep this"),
        ])
        before = copy.deepcopy(source)
        original = stock()
        result = compose(source, original)
        self.assertEqual(source, before)
        self.assertEqual(result["sourceHash"], source["sourceHash"])
        self.assertEqual(result["objects"][:2], original["objects"])
        self.assertEqual(result["objects"][2], source["objects"][0])
        self.assertEqual(original, stock())
        self.assertEqual(compose(result, original), result)
        self.assertEqual(len({o["id"] for o in result["objects"]}), len(result["objects"]))

    def test_keeps_costume_choice_on_original_actor(self):
        original = dict(mapId="twinkle", objects=[dict(
            id="stock-0", file="Res/StageObj/Object01/Jjijil00.dat",
            name="Jjijil00", position=[70,0,10], rotation=90, scale=1)])
        dressed = {**original["objects"][0], "name":"Forest greeter",
                   "file":"Res/StageObj/OktoberNPC/Oktoberfest_GreeterForest.dat"}
        result = compose(dict(mapId="oktoberfest", objects=[dressed]), original)
        self.assertEqual(result["objects"][0], dressed)
        self.assertEqual(compose(result, original), result)

    def test_restores_stock_cast_and_carts_without_added_people(self):
        result = compose(dict(mapId="oktoberfest", sourceHash="synthetic", objects=[
            dict(id="festplatz-pretzels", file="Studio/Oktoberfest/Oktoberfest_PretzelStand.glb"),
            dict(id="stock-0", file="Res/StageObj/Object02/Soldier00.dat", position=[0,0,0]),
            dict(id="extra-soldier", file="Res/StageObj/Object02/Soldier00.dat"),
            dict(id="extra-cart", file="Res/StageObj/FestivalPretzel/Carriage00.dat"),
            dict(id="guest", file="Res/StageObj/OktoberNPC/Oktoberfest_BrewerWine.dat"),
            dict(id="engineer", file="Res/StageObj/Object03/Engineer00h.dat"),
            dict(id="court-fest-crest-133"), dict(id="court-fest-judge-chair-18"),
        ]), stock())
        objects = {o["id"]: o for o in result["objects"]}
        self.assertEqual(result["objects"][:2], stock()["objects"])
        for removed in ("extra-soldier", "extra-cart", "guest", "engineer",
                        "court-fest-crest-133", "court-fest-judge-chair-18"):
            self.assertNotIn(removed, objects)
        for identity, archive in [("pretzels","FestivalPretzel"), ("hearts","FestivalHeart"), ("food","FestivalFood")]:
            self.assertEqual(objects["festplatz-"+identity]["file"], f"Res/StageObj/{archive}/Carriage00.dat")
        self.assertEqual(compose(result, stock()), result)
        with self.assertRaises(ValueError):
            compose(dict(mapId="twinkle", objects=[]), stock())
        with self.assertRaises(ValueError):
            compose(dict(mapId="oktoberfest", objects=[]), dict(mapId="twinkle", objects=[]))

    def test_new_perimeter_geometry_stays_outside_playing_rectangle(self):
        result = compose(dict(mapId="oktoberfest", objects=[]), stock())
        for obj in result["objects"]:
            if not obj["file"].endswith(".glb") or obj["id"].startswith("court-fest-"):
                continue
            model = build_model(obj["file"].split("/")[-1][:-4])
            a = math.radians(obj["rotation"])
            for i in range(0,len(model.positions),3):
                x,y,z = [v*obj["scale"] for v in model.positions[i:i+3]]
                x,z = x*math.cos(a)+z*math.sin(a)+obj["position"][0], z*math.cos(a)-x*math.sin(a)+obj["position"][2]
                self.assertTrue(abs(x)>65 or abs(z)>120, obj["id"])

    def test_trim_has_no_collision_and_keeps_net_mesh_open(self):
        for name in ("CornerInlay", "NetDressing", "JudgeDressing"):
            self.assertEqual(collision_boxes("Oktoberfest_"+name), [])
        net = build_model("Oktoberfest_NetDressing")
        for i in range(0,len(net.positions),3):
            x,y,z = net.positions[i:i+3]
            if abs(x)<=60:
                top = 8.33548+abs(x)/60*(9.70674-8.33548)
                self.assertGreaterEqual(y, top-1.45)
                self.assertLessEqual(y, top+.13)
        judge = build_model("Oktoberfest_JudgeDressing")
        self.assertGreater(min(judge.positions[1::3]), 21)
        inlay = build_model("Oktoberfest_CornerInlay")
        self.assertLessEqual(max(inlay.positions[1::3]), .11)


if __name__ == "__main__":
    unittest.main()
