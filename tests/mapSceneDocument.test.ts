import { describe, expect, test } from "bun:test";
import { mapSceneAcknowledgementKey } from "../web/MapCreatorPanel.tsx";
import {
  addMapObject,
  addMapSpawn,
  buildMapManifest,
  createEmptyMapScene,
  duplicateMapObject,
  paintCollisionCell,
  parseMapScene,
  serializeMapScene,
  setMapLayerVisibility,
  setMapReferences,
  transformMapObject,
  validateMapDependencies,
} from "../web/mapSceneDocument.ts";

describe("editable map scene document", () => {
  test("dependency acknowledgement key changes only with scene content", () => {
    const scene = createEmptyMapScene("Acknowledged Court");
    const clone = structuredClone(scene);
    const changed = setMapReferences(clone, {
      ...clone.references,
      stageScript: "1_Emerald_Beach.set",
    });

    expect(mapSceneAcknowledgementKey(clone)).toBe(
      mapSceneAcknowledgementKey(scene),
    );
    expect(mapSceneAcknowledgementKey(changed)).not.toBe(
      mapSceneAcknowledgementKey(scene),
    );
  });

  test("starts from an empty, versioned playable-court template", () => {
    const scene = createEmptyMapScene("QA Court");

    expect(scene.schemaVersion).toBe(1);
    expect(scene.name).toBe("QA Court");
    expect(scene.layers.map(({ id, visible }) => ({ id, visible }))).toEqual([
      { id: "terrain", visible: true },
      { id: "objects", visible: true },
      { id: "collision", visible: true },
      { id: "spawns", visible: true },
      { id: "effects", visible: true },
    ]);
    expect(scene.objects).toEqual([]);
    expect(scene.spawns).toEqual([]);
    expect(scene.collision.blockedCells).toEqual([]);
  });

  test("places, snaps, rotates, scales, duplicates, and hides objects", () => {
    let scene = createEmptyMapScene("QA Court");
    scene = addMapObject(scene, {
      assetId: "court/net.glb",
      name: "Center net",
      layer: "objects",
      position: [2.24, 0, 3.76],
      rotation: [0, 0, 0],
      scale: [1, 1, 1],
    });
    const id = scene.objects[0].id;
    scene = transformMapObject(scene, id, {
      position: [2.24, 0, 3.76],
      rotation: [0, 90, 0],
      scale: [1, 1.25, 1],
      snap: 0.5,
    });
    scene = duplicateMapObject(scene, id);
    scene = setMapLayerVisibility(scene, "objects", false);

    expect(scene.objects[0]).toMatchObject({
      position: [2, 0, 4],
      rotation: [0, 90, 0],
      scale: [1, 1.25, 1],
    });
    expect(scene.objects[1]).toMatchObject({
      id: "object-2",
      name: "Center net copy",
      position: [2.5, 0, 4.5],
    });
    expect(scene.layers.find(({ id: layer }) => layer === "objects")?.visible)
      .toBe(false);
  });

  test("authors spawns, collision, FTM, stage, material, and Blender links", () => {
    let scene = createEmptyMapScene("QA Court");
    scene = addMapSpawn(scene, {
      team: "home",
      position: [-4, 0, 0],
      facing: 90,
    });
    scene = addMapSpawn(scene, {
      team: "away",
      position: [4, 0, 0],
      facing: -90,
    });
    scene = paintCollisionCell(scene, [3, 7], true);
    scene = setMapReferences(scene, {
      stageScript: "Stage/QA_Court.set",
      ftmArchive: "Res/MapSet/QA_Court.res",
      ftmMember: "QA_Court.ftm",
      collisionAsset: "Stage/QA_Court_Collision.dat",
      terrainSource: "roundtrip/qa-court.blend",
      materials: [
        { slot: "court", texture: "Texture/qa-court.png" },
        { slot: "lines", texture: "Texture/qa-lines.png" },
      ],
    });

    expect(scene.spawns).toHaveLength(2);
    expect(scene.collision.blockedCells).toEqual([[3, 7]]);
    expect(scene.references.terrainSource).toEndWith(".blend");
    expect(scene.references.materials).toHaveLength(2);
  });

  test("reports every unresolved dependency and builds a complete manifest", () => {
    let scene = createEmptyMapScene("QA Court");
    scene = addMapObject(scene, {
      assetId: "court/net.glb",
      name: "Center net",
      layer: "objects",
      position: [0, 0, 0],
      rotation: [0, 0, 0],
      scale: [1, 1, 1],
    });
    scene = addMapSpawn(scene, {
      team: "home",
      position: [-4, 0, 0],
      facing: 90,
    });
    scene = addMapSpawn(scene, {
      team: "away",
      position: [4, 0, 0],
      facing: -90,
    });
    scene = setMapReferences(scene, {
      stageScript: "Stage/QA_Court.set",
      ftmArchive: "Res/MapSet/QA_Court.res",
      ftmMember: "QA_Court.ftm",
      collisionAsset: "Stage/QA_Court_Collision.dat",
      terrainSource: "roundtrip/qa-court.blend",
      materials: [{ slot: "court", texture: "Texture/qa-court.png" }],
    });

    expect(validateMapDependencies(scene, new Set())).toEqual([
      "court/net.glb",
      "Stage/QA_Court.set",
      "Res/MapSet/QA_Court.res",
      "Stage/QA_Court_Collision.dat",
      "roundtrip/qa-court.blend",
      "Texture/qa-court.png",
    ]);
    const available = new Set(validateMapDependencies(scene, new Set()));
    expect(validateMapDependencies(scene, available)).toEqual([]);
    expect(buildMapManifest(scene, available)).toMatchObject({
      schemaVersion: 1,
      kind: "map",
      name: "QA Court",
      counts: { objects: 1, spawns: 2, blockedCells: 0 },
      dependencies: [...available],
      packaging: {
        stageScript: "Stage/QA_Court.set",
        ftmArchive: "Res/MapSet/QA_Court.res",
        ftmMember: "QA_Court.ftm",
        collisionAsset: "Stage/QA_Court_Collision.dat",
      },
    });
  });

  test("round-trips the complete scene document identically", () => {
    let scene = createEmptyMapScene("Round trip");
    scene = addMapObject(scene, {
      assetId: "court/tree.glb",
      name: "Tree",
      layer: "objects",
      position: [1, 0, 2],
      rotation: [0, 15, 0],
      scale: [1.5, 1.5, 1.5],
    });
    scene = paintCollisionCell(scene, [1, 2], true);

    expect(parseMapScene(serializeMapScene(scene))).toEqual(scene);
    expect(() => parseMapScene('{"schemaVersion":2}')).toThrow(
      "map scene version",
    );
  });
});
