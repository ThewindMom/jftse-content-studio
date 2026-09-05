"""Extend the private detailed layout with court trim and experimental costumes.

Preserves every actor's animation values. No clip is assigned an inferred action.
"""
import json
import math
import sys
from pathlib import Path

from oktoberfest_costumes import SOURCES


def compose(document):
    document = {**document,"objects":[dict(o) for o in document["objects"] if not o["id"].startswith("court-fest-")]}
    counts = {}
    for obj in document["objects"]:
        for role,(archive,member,_) in SOURCES.items():
            if obj["file"] == f"Res/StageObj/{archive}/{member}.dat":
                count = counts.get(role,0)
                style = "Forest" if count%2 == 0 else "Wine"
                obj["file"] = f"Res/StageObj/OktoberNPC/Oktoberfest_{role}{style}.dat"
                obj["name"] += f" · {style} costume"
                counts[role] = count+1
                break

    # Codex reference: larger connected destinations, asymmetric table groups,
    # and no row of tiny detached stalls beside the playing surface.
    staging = {
        "festplatz-hall": ([0,-7.3557,260],180,1.4),
        "festplatz-pretzels": ([190,-7.3558,40],95,1.25),
        "festplatz-hearts": ([220,-7.3558,-25],110,1.15),
        "festplatz-food": ([185,-7.3558,-135],70,1.5),
        "festplatz-table-0": ([238,-7.3558,-74],80,1),
        "festplatz-table-1": ([247,-7.3558,-16],105,1),
        "festplatz-table-2": ([239,-7.3558,52],90,1),
        "festplatz-terrace-table": ([-215,-7.3558,-180],75,1),
        "festplatz-pretzel-customer": ([217,-7.3558,36],-85,.8),
        "festplatz-heart-customer": ([246,-7.3558,-37],-70,.8),
        "festplatz-food-customer": ([220,-7.3558,-124],-110,.8),
        "detail-market-south": ([226,-7.3558,-108],15,1),
        "detail-market-north": ([223,-7.3558,85],-10,1),
    }
    for obj in document["objects"]:
        if obj["id"] in staging:
            obj["position"],obj["rotation"],obj["scale"] = staging[obj["id"]]
    document["objects"] = [o for o in document["objects"] if not o["id"].startswith("festplatz-market-flowers-")]

    def add(identity,model,position,rotation=0,scale=1):
        document["objects"].append(dict(id="court-fest-"+identity,name=identity.replace("-"," "),
            file="Studio/Oktoberfest/Oktoberfest_"+model+".glb",position=position,
            rotation=rotation,scale=scale,visible=True,level=1,animation=-1,phase=0))

    add("fountain-crown","FountainCrown",[-154.15,58,.25])
    for z in (-133,133):
        add(f"crest-{z}","CourtCrest",[0,.03,z],0 if z<0 else 180)
        for x in (-46,46):
            add(f"baseline-{x}-{z}","CourtRibbon",[x,0,math.copysign(146,z)])
        for x in (-80,80):
            add(f"corner-{x}-{z}","CourtCorner",[x,0,math.copysign(136,z)],0 if z<0 else 180)
    # Fitted to the stock net's sag; adds no collision or above-tape obstacles.
    add("net-dressing","NetDressing",[0,0,0])
    add("judge-chair-dressing","JudgeDressing",[0,0,0])
    for z in (-18,18):
        add(f"judge-chair-{z}","CourtRibbon",[90,0,z],0,.5)
    # Flowers on the basin platform, not in its water or east-side player lane.
    for i,degrees in enumerate((55,90,125,160,195,230,265,300)):
        angle = math.radians(degrees)
        document["objects"].append(dict(id=f"court-fest-fountain-flowers-{i}",name=f"Fountain flowers {i+1}",
            file="Res/MapRes/DecoRes/Mesh00/P0_Flower00b.dat",
            position=[round(-154.15+61*math.cos(angle),4),6.6,round(.25+61*math.sin(angle),4)],
            rotation=degrees,scale=.4,visible=True,level=1,animation=-1,phase=0))
    # Replace the rejected primitive-built figures with the original identities.
    for identity,model,position,rotation,scale in [
        ("brewery-host","BrewerForest",[-205,-7.3558,-160],125,1),
        ("music-guest","BrewerWine",[215,-3.3558,-180],-45,1),
        ("bakery-helper","VisitorWine",[207,-7.3558,14],105,1),
        ("chick-welcome","ChickForest",[35,0,-145],-25,2),
    ]:
        document["objects"].append(dict(id="court-fest-"+identity,name=identity.replace("-"," "),
            file="Res/StageObj/OktoberNPC/Oktoberfest_"+model+".dat",position=position,
            rotation=rotation,scale=scale,visible=True,level=1,animation=0,phase=0))
    return document


if __name__ == "__main__":
    source,destination = map(Path,sys.argv[1:])
    document = compose(json.loads(source.read_text()))
    destination.write_text(json.dumps(document,indent=2)+"\n")
    print(len(document["objects"]),"placements; stock transforms and existing animation/phase preserved")
