export const MAP_SCENE_SCHEMA_VERSION = 1;

export type Vec2 = [number, number];
export type Vec3 = [number, number, number];
export type MapLayerId =
  | "terrain"
  | "objects"
  | "collision"
  | "spawns"
  | "effects";

export type MapLayer = {
  id: MapLayerId;
  name: string;
  visible: boolean;
};

export type MapObject = {
  id: string;
  assetId: string;
  name: string;
  layer: MapLayerId;
  position: Vec3;
  rotation: Vec3;
  scale: Vec3;
};

export type MapSpawn = {
  id: string;
  team: "home" | "away" | "spectator";
  position: Vec3;
  facing: number;
};

export type MapMaterialReference = {
  slot: string;
  texture: string;
};

export type MapReferences = {
  stageScript: string;
  ftmArchive: string;
  ftmMember: string;
  collisionAsset: string;
  terrainSource: string;
  materials: MapMaterialReference[];
};

export type MapSceneDocument = {
  schemaVersion: typeof MAP_SCENE_SCHEMA_VERSION;
  name: string;
  layers: MapLayer[];
  objects: MapObject[];
  spawns: MapSpawn[];
  collision: { blockedCells: Vec2[] };
  references: MapReferences;
};
