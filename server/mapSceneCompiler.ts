import { basename } from "node:path";
import {
  parseMapScene,
  serializeMapScene,
  type MapObject,
  type MapSceneDocument,
} from "../web/mapSceneDocument.ts";

const PREFAB_BY_ASSET: Readonly<Record<string, number>> = {
  "court/net.glb": 0,
  "court/tree.glb": 1,
  "nature/tree.glb": 1,
};

type RuntimePlacement = {
  prefabIndex: number;
  x: number;
  y: number;
  scaleHeight: number;
  scaleWidth: number;
  rotationY: number;
  rotationX: number;
};

export type CompiledMapScene = {
  payload: Record<string, unknown>;
  design: {
    objects: MapSceneDocument["objects"];
    spawns: MapSceneDocument["spawns"];
    collision: MapSceneDocument["collision"];
    materials: MapSceneDocument["references"]["materials"];
    terrainSource: string;
  };
  runtimeUnsupported: string[];
};

function compilePlacement(object: MapObject): RuntimePlacement {
  const prefabIndex = PREFAB_BY_ASSET[object.assetId];
  if (prefabIndex === undefined) {
    throw new Error(`UNMAPPED_FTM_ASSET:${object.assetId}`);
  }
  return {
    prefabIndex,
    x: Math.round(object.position[0]),
    y: Math.round(object.position[2]),
    scaleHeight: object.scale[1],
    scaleWidth: (object.scale[0] + object.scale[2]) / 2,
    rotationY: object.rotation[1],
    rotationX: object.rotation[0],
  };
}

export function compileMapScene(scene: MapSceneDocument): CompiledMapScene {
  const validated = parseMapScene(serializeMapScene(scene));
  const { references } = validated;
  if (!references.stageScript.trim()) {
    throw new Error("MAP_STAGE_TEMPLATE_REQUIRED");
  }
  if (!references.ftmArchive.trim() || !references.ftmMember.trim()) {
    throw new Error("MAP_FTM_TEMPLATE_REQUIRED");
  }

  const runtimeUnsupported: string[] = [];
  if (validated.spawns.length > 0) {
    runtimeUnsupported.push("player-spawn compilation");
  }
  if (references.terrainSource.trim()) {
    runtimeUnsupported.push("terrain geometry compilation");
  }
  if (references.materials.length > 0) {
    runtimeUnsupported.push("stage material binding compilation");
  }

  return {
    payload: {
      name: validated.name,
      map: {
        draft: {
          name: validated.name,
          playTime: 180,
          breathTime: 100,
        },
        scenarioIds: [1],
        stageScript: basename(references.stageScript),
      },
      stage: {
        member: basename(references.stageScript),
        fields: {},
      },
      ftm: {
        archive: references.ftmArchive,
        member: references.ftmMember,
        add: validated.objects.map(compilePlacement),
        blockedTiles: validated.collision.blockedCells.map(([x, y]) => ({
          x,
          y,
        })),
      },
    },
    design: {
      objects: structuredClone(validated.objects),
      spawns: structuredClone(validated.spawns),
      collision: structuredClone(validated.collision),
      materials: structuredClone(references.materials),
      terrainSource: references.terrainSource,
    },
    runtimeUnsupported,
  };
}
