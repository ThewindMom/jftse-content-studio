import {
  MAP_SCENE_SCHEMA_VERSION,
  type MapLayer,
  type MapLayerId,
  type MapObject,
  type MapReferences,
  type MapSceneDocument,
  type MapSpawn,
  type Vec2,
  type Vec3,
} from "./mapSceneTypes.ts";

const LAYERS: MapLayer[] = [
  { id: "terrain", name: "Terrain", visible: true },
  { id: "objects", name: "Objects", visible: true },
  { id: "collision", name: "Collision", visible: true },
  { id: "spawns", name: "Spawns", visible: true },
  { id: "effects", name: "Effects", visible: true },
];

const EMPTY_REFERENCES: MapReferences = {
  stageScript: "",
  ftmArchive: "",
  ftmMember: "",
  collisionAsset: "",
  terrainSource: "",
  materials: [],
};

function cloneVec3(value: Vec3): Vec3 {
  return [...value];
}

function nextId(prefix: string, values: Array<{ id: string }>): string {
  const highest = values.reduce((maximum, value) => {
    const match = value.id.match(new RegExp(`^${prefix}-(\\d+)$`));
    return match ? Math.max(maximum, Number(match[1])) : maximum;
  }, 0);
  return `${prefix}-${highest + 1}`;
}

export function createEmptyMapScene(name: string): MapSceneDocument {
  return {
    schemaVersion: MAP_SCENE_SCHEMA_VERSION,
    name,
    layers: structuredClone(LAYERS),
    objects: [],
    spawns: [],
    collision: { blockedCells: [] },
    references: structuredClone(EMPTY_REFERENCES),
  };
}

export function addMapObject(
  scene: MapSceneDocument,
  object: Omit<MapObject, "id">,
): MapSceneDocument {
  return {
    ...scene,
    objects: [
      ...scene.objects,
      {
        ...object,
        id: nextId("object", scene.objects),
        position: cloneVec3(object.position),
        rotation: cloneVec3(object.rotation),
        scale: cloneVec3(object.scale),
      },
    ],
  };
}

export function transformMapObject(
  scene: MapSceneDocument,
  id: string,
  transform: { position: Vec3; rotation: Vec3; scale: Vec3; snap?: number },
): MapSceneDocument {
  const snap = transform.snap ?? 0;
  const snapValue = (value: number) =>
    snap > 0 ? Math.round(value / snap) * snap : value;
  let found = false;
  const objects = scene.objects.map((object) => {
    if (object.id !== id) return object;
    found = true;
    return {
      ...object,
      position: transform.position.map(snapValue) as Vec3,
      rotation: cloneVec3(transform.rotation),
      scale: cloneVec3(transform.scale),
    };
  });
  if (!found) throw new Error(`Unknown map object: ${id}`);
  return { ...scene, objects };
}

export function duplicateMapObject(
  scene: MapSceneDocument,
  id: string,
): MapSceneDocument {
  const source = scene.objects.find((object) => object.id === id);
  if (!source) throw new Error(`Unknown map object: ${id}`);
  return addMapObject(scene, {
    ...source,
    name: `${source.name} copy`,
    position: [
      source.position[0] + 0.5,
      source.position[1],
      source.position[2] + 0.5,
    ],
  });
}

export function setMapLayerVisibility(
  scene: MapSceneDocument,
  id: MapLayerId,
  visible: boolean,
): MapSceneDocument {
  return {
    ...scene,
    layers: scene.layers.map((layer) =>
      layer.id === id ? { ...layer, visible } : layer,
    ),
  };
}

export function addMapSpawn(
  scene: MapSceneDocument,
  spawn: Omit<MapSpawn, "id">,
): MapSceneDocument {
  return {
    ...scene,
    spawns: [
      ...scene.spawns,
      {
        ...spawn,
        id: nextId("spawn", scene.spawns),
        position: cloneVec3(spawn.position),
      },
    ],
  };
}

export function paintCollisionCell(
  scene: MapSceneDocument,
  cell: Vec2,
  blocked: boolean,
): MapSceneDocument {
  const same = (value: Vec2) => value[0] === cell[0] && value[1] === cell[1];
  const without = scene.collision.blockedCells.filter((value) => !same(value));
  return {
    ...scene,
    collision: { blockedCells: blocked ? [...without, [...cell]] : without },
  };
}

export function setMapReferences(
  scene: MapSceneDocument,
  references: MapReferences,
): MapSceneDocument {
  return { ...scene, references: structuredClone(references) };
}
