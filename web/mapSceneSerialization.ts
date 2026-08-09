import {
  MAP_SCENE_SCHEMA_VERSION,
  type MapLayer,
  type MapMaterialReference,
  type MapObject,
  type MapReferences,
  type MapSceneDocument,
  type MapSpawn,
  type Vec2,
  type Vec3,
} from "./mapSceneTypes.ts";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isVec2(value: unknown): value is Vec2 {
  return Array.isArray(value) && value.length === 2 && value.every(isNumber);
}

function isVec3(value: unknown): value is Vec3 {
  return Array.isArray(value) && value.length === 3 && value.every(isNumber);
}

function isLayer(value: unknown): value is MapLayer {
  return (
    isRecord(value) &&
    ["terrain", "objects", "collision", "spawns", "effects"].includes(
      String(value.id),
    ) &&
    typeof value.name === "string" &&
    typeof value.visible === "boolean"
  );
}

function isMapObject(value: unknown): value is MapObject {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.assetId === "string" &&
    typeof value.name === "string" &&
    ["terrain", "objects", "collision", "spawns", "effects"].includes(
      String(value.layer),
    ) &&
    isVec3(value.position) &&
    isVec3(value.rotation) &&
    isVec3(value.scale)
  );
}

function isSpawn(value: unknown): value is MapSpawn {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    ["home", "away", "spectator"].includes(String(value.team)) &&
    isVec3(value.position) &&
    isNumber(value.facing)
  );
}

function isMaterial(value: unknown): value is MapMaterialReference {
  return (
    isRecord(value) &&
    typeof value.slot === "string" &&
    typeof value.texture === "string"
  );
}

function isReferences(value: unknown): value is MapReferences {
  return (
    isRecord(value) &&
    typeof value.stageScript === "string" &&
    typeof value.ftmArchive === "string" &&
    typeof value.ftmMember === "string" &&
    typeof value.collisionAsset === "string" &&
    typeof value.terrainSource === "string" &&
    Array.isArray(value.materials) &&
    value.materials.every(isMaterial)
  );
}

function isMapSceneDocument(value: unknown): value is MapSceneDocument {
  return (
    isRecord(value) &&
    value.schemaVersion === MAP_SCENE_SCHEMA_VERSION &&
    typeof value.name === "string" &&
    Array.isArray(value.layers) &&
    value.layers.every(isLayer) &&
    Array.isArray(value.objects) &&
    value.objects.every(isMapObject) &&
    Array.isArray(value.spawns) &&
    value.spawns.every(isSpawn) &&
    isRecord(value.collision) &&
    Array.isArray(value.collision.blockedCells) &&
    value.collision.blockedCells.every(isVec2) &&
    isReferences(value.references)
  );
}

export function serializeMapScene(scene: MapSceneDocument): string {
  return JSON.stringify(scene);
}

export function parseMapScene(value: string): MapSceneDocument {
  const parsed: unknown = JSON.parse(value);
  if (
    !isRecord(parsed) ||
    parsed.schemaVersion !== MAP_SCENE_SCHEMA_VERSION
  ) {
    throw new Error("Unsupported map scene version.");
  }
  if (!isMapSceneDocument(parsed)) {
    throw new Error("Malformed map scene document.");
  }
  return structuredClone(parsed);
}
