"""Refine a private court study and restore its original Twinkle actors and carts.

Usage: python python/compose_festplatz_perimeter.py INPUT.json STOCK_SCENE.json OUTPUT.json
"""
import copy
import json
import sys
from pathlib import Path


def compose(document, stock):
    document = copy.deepcopy(document)
    if document.get("mapId") != "oktoberfest":
        raise ValueError("Expected an Oktoberfest layout")
    if stock.get("mapId") != "twinkle" or not stock.get("objects"):
        raise ValueError("Original Twinkle placements are required")
    removed = {"court-fest-crest--133", "court-fest-crest-133",
               "court-fest-judge-chair--18", "court-fest-judge-chair-18"}
    vendors = {"festplatz-pretzels", "festplatz-hearts", "festplatz-food"}
    actors = {Path(o["file"]).name for o in stock["objects"]}
    actors.update({"Engineer00h.dat", "Pirate00.dat", "Oktoberfest_Brewmaster.glb",
                   "Oktoberfest_Accordionist.glb", "Oktoberfest_PretzelBaker.glb",
                   "Oktoberfest_FestivalChick.glb"})
    originals = copy.deepcopy(stock["objects"])
    current = {o["id"]: o for o in document["objects"]}
    for obj in originals:
        prior = current.get(obj["id"])
        if prior and prior["file"].startswith("Res/StageObj/OktoberNPC/"):
            obj.update(file=prior["file"], name=prior["name"])
    document["objects"] = originals + [
        o for o in document["objects"]
        if not o["id"].startswith("stock-") and o["id"] not in removed
        and not o["file"].startswith("Res/StageObj/OktoberNPC/")
        and (Path(o["file"]).name not in actors or o["id"] in vendors)
    ]
    objects = {o["id"]: o for o in document["objects"]}

    def place(identity, name, file, position, rotation=0, scale=1):
        if identity not in objects:
            objects[identity] = dict(id=identity, level=1, animation=-1, phase=0)
            document["objects"].append(objects[identity])
        objects[identity].update(name=name, file=file, position=position,
                                 rotation=rotation, scale=scale, visible=True)

    def prop(identity, model, position, rotation=0, scale=1):
        place(identity, model, f"Studio/Oktoberfest/Oktoberfest_{model}.glb", position, rotation, scale)

    # Unequal poles mark the tent approach and entrance, not a ring around the court.
    prop("festplatz-maypole-0", "Maypole", [-88, 0, 151], 15, 1.5)
    prop("festplatz-maypole-1", "WelcomeMaypole", [-67, -7.3558, -222], -20, 1.1)
    prop("festplatz-wagon", "BarrelWagon", [132, -6.8758, 193], 90, 1.2)
    prop("perimeter-welcome-planter", "CourtCorner", [-140, -7.2558, -196], -18, 1)
    for identity, archive, name, position, rotation, scale in [
        ("festplatz-pretzels", "FestivalPretzel", "Pretzel cart", [80,-7.1363,222], 85, .68),
        ("festplatz-hearts", "FestivalHeart", "Gingerbread cart", [-97,-7.1557,-209], -110, .62),
        ("festplatz-food", "FestivalFood", "Food cart", [230,-7.1138,25], 5, .75),
    ]:
        place(identity, name, f"Res/StageObj/{archive}/Carriage00.dat", position, rotation, scale)
    for identity, position, rotation in [
        ("festplatz-table-0", [245,-7.1983,-34], 18),
        ("festplatz-table-1", [254,-7.1983,-5], -8),
        ("festplatz-table-2", [242,-7.1983,108], 65),
    ]:
        if identity in objects:
            objects[identity].update(position=position, rotation=rotation)

    for x,z,rotation in [(-74,-127,0),(74,-127,270),(74,127,180),(-74,127,90)]:
        prop(f"perimeter-inlay-{x}-{z}", "CornerInlay", [x,.02,z], rotation)
    prop("court-fest-net-dressing", "NetDressing", [0,0,0])
    prop("court-fest-judge-chair-dressing", "JudgeDressing", [0,0,0])
    return document


if __name__ == "__main__":
    source, stock_scene, destination = map(Path, sys.argv[1:])
    document = compose(json.loads(source.read_text()), json.loads(stock_scene.read_text())["document"])
    destination.write_text(json.dumps(document, indent=2) + "\n")
    print(f"PASS: {len(document['objects'])} placements; stock transforms restored, existing stock costume choices and fingerprint preserved")
