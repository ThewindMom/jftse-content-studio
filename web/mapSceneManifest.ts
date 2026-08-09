import { MAP_SCENE_SCHEMA_VERSION, type MapSceneDocument } from "./mapSceneTypes.ts";

function dependencyList(scene: MapSceneDocument): string[] {
  return [
    ...scene.objects.map((object) => object.assetId),
    scene.references.stageScript,
    scene.references.ftmArchive,
    scene.references.collisionAsset,
    scene.references.terrainSource,
    ...scene.references.materials.map((material) => material.texture),
  ].filter((value, index, values) => value && values.indexOf(value) === index);
}

export function validateMapDependencies(
  scene: MapSceneDocument,
  available: ReadonlySet<string>,
): string[] {
  return dependencyList(scene).filter((dependency) => !available.has(dependency));
}

export function buildMapManifest(
  scene: MapSceneDocument,
  available: ReadonlySet<string>,
) {
  const missing = validateMapDependencies(scene, available);
  if (missing.length > 0) {
    throw new Error(`Missing map dependencies: ${missing.join(", ")}`);
  }
  if (scene.spawns.length < 2) {
    throw new Error("A playable map requires at least two spawns.");
  }
  return {
    schemaVersion: MAP_SCENE_SCHEMA_VERSION,
    kind: "map" as const,
    name: scene.name,
    counts: {
      objects: scene.objects.length,
      spawns: scene.spawns.length,
      blockedCells: scene.collision.blockedCells.length,
    },
    dependencies: dependencyList(scene),
    packaging: {
      stageScript: scene.references.stageScript,
      ftmArchive: scene.references.ftmArchive,
      ftmMember: scene.references.ftmMember,
      collisionAsset: scene.references.collisionAsset,
    },
    scene,
  };
}
