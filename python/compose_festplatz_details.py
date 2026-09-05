"""Add measured festival decorations to a private, existing Festplatz layout.

Usage: python python/compose_festplatz_details.py URL INPUT.json OUTPUT.json
Reads Studio geometry; never reads or writes a client installation.
"""
import json
import math
import sys
import urllib.request
from pathlib import Path


def compose(url, document):
    def get(path):
        return json.load(urllib.request.urlopen(url.rstrip("/") + path))

    scene = get("/api/twinkle/scene?map=oktoberfest")
    if document["sourceHash"] != scene["document"]["sourceHash"]:
        raise ValueError("Stock/festival source changed; do not rewrite the fingerprint")
    assets = {a["file"]: a for a in scene["assets"]}
    town = get("/api/twinkle/file?name=" + assets["Res/Stage/Mesh02/SV_All.dat"]["geometry"])
    court = get("/api/twinkle/file?name=" + assets["Res/Stage/Mesh02/SV_Court.dat"]["geometry"])

    def intersect(parts, axis, point):
        axes = [i for i in range(3) if i != axis]
        hits = []
        for part in parts:
            v, indices = part["positions"], part["indices"]
            for i in range(0, len(indices), 3):
                a,b,c = [[v[j*3+k] for k in axes] for j in indices[i:i+3]]
                determinant = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                if abs(determinant) < 1e-7:
                    continue
                u = ((b[1]-c[1])*(point[0]-c[0])+(c[0]-b[0])*(point[1]-c[1]))/determinant
                w = ((c[1]-a[1])*(point[0]-c[0])+(a[0]-c[0])*(point[1]-c[1]))/determinant
                if min(u,w,1-u-w) >= -1e-6:
                    heights = [v[j*3+axis] for j in indices[i:i+3]]
                    hits.append(u*heights[0]+w*heights[1]+(1-u-w)*heights[2])
        if not hits:
            raise ValueError(f"No measured surface: axis={axis}, point={point}")
        return hits

    document = {**document, "objects": [o for o in document["objects"] if not o["id"].startswith("detail-")]}

    def place(identity, model, position, rotation=0, scale=1):
        file = "Studio/Oktoberfest/Oktoberfest_"+model+".glb"
        if file not in assets:
            raise ValueError("Missing generated asset: " + file)
        document["objects"].append(dict(id="detail-"+identity, name=identity.replace("-"," "),
            file=file, position=[round(v,4) for v in position], rotation=rotation, scale=scale,
            visible=True, level=1, animation=-1, phase=0))

    # Measured basin bounds: x[-207.9,-100.4], z[-53.5,54.0], water y15.4.
    place("fountain-rim", "FountainGarland", [-154.15,19,.25])
    # Match the spacing of the market stalls. No poles in the customer aisle.
    for identity,x,z,rotation in [("market-south",190,-115,0), ("market-north",190,110,0),
                                   ("tent-approach",0,174,0)]:
        y = max(h for h in intersect(court,1,[x,z]) if -10 <= h <= 1)
        place(identity,"FlagLine",[x,y,z],rotation)
    for identity,x,z,rotation in [("entry-west",-47,-200,0),("entry-east",47,-200,180),
                                   ("fountain-west",-211,83,0),("fountain-east",-99,83,180)]:
        y = max(h for h in intersect(court,1,[x,z]) if -10 <= h <= 1)
        place(identity,"FlagPost",[x,y,z],rotation)
    # Cast toward the plaza-facing house walls, not their aggregate AABBs.
    for identity,name,axis,point,side,rotation in [
        ("west-house", "SV_House02_C01",0,[51,65],1,90),
        ("southwest-house", "SV_House02_C02",2,[-220,55],1,0),
        ("north-house", "SV_House01_C",2,[-65,65],-1,180),
        ("northeast-house", "SV_House03_B",2,[180,55],-1,180),
    ]:
        parts = [p for p in town if p.get("name") == name]
        hits = intersect(parts,axis,point)
        value = (max(hits) if side > 0 else min(hits)) + side*3
        position = list(point)
        position.insert(axis,value)
        place(identity,"HouseBanner",position,rotation,1.3)
    assert all(math.isfinite(v) for o in document["objects"] for v in o["position"])
    return document


if __name__ == "__main__":
    url, source, destination = sys.argv[1:]
    document = compose(url, json.loads(Path(source).read_text()))
    Path(destination).write_text(json.dumps(document,indent=2)+"\n")
    print(f"PASS: {len(document['objects'])} placements; measured fountain and four house attachments; sourceHash unchanged")
