import { describe, expect, test } from "bun:test";
import {
  addMapObject,
  addMapSpawn,
  createEmptyMapScene,
  paintCollisionCell,
  setMapReferences,
} from "../web/mapSceneDocument";
import { compileMapScene } from "../server/mapSceneCompiler";

function authoredScene() {
  let scene = createEmptyMapScene("Compiled Court");
  scene = addMapObject(scene, {
    assetId: "court/net.glb",
    name: "Center net",
    layer: "objects",
    position: [3, 0, 4],
    rotation: [0, 90, 0],
    scale: [1.5, 2, 1.5],
  });
  scene = addMapObject(scene, {
    assetId: "court/tree.glb",
    name: "Scenery tree",
    layer: "objects",
    position: [8, 0, -6],
    rotation: [0, 45, 0],
    scale: [1, 1.5, 1],
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
  scene = paintCollisionCell(scene, [2, 3], true);
  return setMapReferences(scene, {
    stageScript: "1_Emerald_Beach.set",
    ftmArchive: "Res/MapSet/FantaCastle.res",
    ftmMember: "FantaCastleOutSide.ftm",
    collisionAsset: "Res/MapSet/FantaCastle.res",
    terrainSource: "roundtrip/compiled-court.blend",
    materials: [{ slot: "court", texture: "Texture/Court01.tex" }],
  });
}

describe("map scene content-pack compiler", () => {
  test("compiles bounded runtime fields and preserves unsupported design data", () => {
    const result = compileMapScene(authoredScene());

    expect(result.payload).toMatchObject({
      name: "Compiled Court",
      map: {
        draft: { name: "Compiled Court" },
        scenarioIds: [1],
        stageScript: "1_Emerald_Beach.set",
      },
      stage: { member: "1_Emerald_Beach.set" },
      ftm: {
        archive: "Res/MapSet/FantaCastle.res",
        member: "FantaCastleOutSide.ftm",
        blockedTiles: [{ x: 2, y: 3 }],
        add: [
          {
            prefabIndex: 0,
            x: 3,
            y: 4,
            scaleHeight: 2,
            scaleWidth: 1.5,
            rotationY: 90,
          },
          {
            prefabIndex: 1,
            x: 8,
            y: -6,
            scaleHeight: 1.5,
            scaleWidth: 1,
            rotationY: 45,
          },
        ],
      },
    });
    expect(result.design.spawns).toHaveLength(2);
    expect(result.design.materials).toEqual([
      { slot: "court", texture: "Texture/Court01.tex" },
    ]);
    expect(result.runtimeUnsupported).toEqual([
      "player-spawn compilation",
      "terrain geometry compilation",
      "stage material binding compilation",
    ]);
  });

  test("rejects objects without a recovered FTM prefab mapping", () => {
    const scene = addMapObject(authoredScene(), {
      assetId: "unknown/custom.glb",
      name: "Unknown",
      layer: "objects",
      position: [0, 0, 0],
      rotation: [0, 0, 0],
      scale: [1, 1, 1],
    });

    expect(() => compileMapScene(scene)).toThrow(
      "UNMAPPED_FTM_ASSET:unknown/custom.glb",
    );
  });
});
