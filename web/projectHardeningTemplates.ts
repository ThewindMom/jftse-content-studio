import {
  PROJECT_SCHEMA_VERSION,
  type ProjectDraft,
  type ProjectEnvelope,
} from "./projectModel.ts";
import {
  equipmentDraftProjectValue,
  mapSceneProjectValue,
} from "./projectEditors.ts";
import {
  addMapObject,
  addMapSpawn,
  createEmptyMapScene,
  paintCollisionCell,
  setMapReferences,
} from "./mapSceneDocument.ts";
import type { EquipmentDraft } from "./equipmentCreator.ts";

export type ProjectTemplateId =
  | "equipment-starter"
  | "empty-court"
  | "combined-showcase";

export type ProjectTemplate = {
  id: ProjectTemplateId;
  title: string;
  description: string;
  draft: ProjectDraft;
};

export type ReferenceProject = {
  id: "equipment-golden" | "map-golden" | "combined-golden";
  project: ProjectEnvelope;
};

function cloneDraft(draft: ProjectDraft): ProjectDraft {
  return structuredClone(draft);
}

const EQUIPMENT_DRAFT: ProjectDraft = {
  shell: { workspace: "equipment", step: "item" },
  editors: { equipment: null },
};

function createCourt(name: string, populated: boolean) {
  let scene = setMapReferences(createEmptyMapScene(name), {
    stageScript: "1_Emerald_Beach.set",
    ftmArchive: "Res/MapSet/FantaCastle.res",
    ftmMember: "FantaCastleOutSide.ftm",
    collisionAsset: "Res/MapSet/FantaCastle.res",
    terrainSource: `roundtrip/${name.replaceAll(" ", "_")}.blend`,
    materials: [{ slot: "court", texture: "Texture/Court01.tex" }],
  });
  if (!populated) return scene;
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
  return paintCollisionCell(scene, [2, 2], true);
}

const GOLDEN_EQUIPMENT: EquipmentDraft = {
  asset: {
    sourceName: "aurora-racket.gltf",
    meshName: "Aurora Racket",
    vertexCount: 96,
    indexCount: 144,
    materials: [{ id: "frame", name: "Frame" }],
    warnings: [],
  },
  materials: {
    frame: {
      textureName: "aurora-frame.png",
      color: "#66ddff",
      metallic: 0.45,
      roughness: 0.35,
    },
  },
  attachment: {
    bone: "Bone_Racket",
    position: [0, 0, 0],
    rotation: [0, 0, 0],
    scale: [1, 1, 1],
  },
  metadata: {
    itemIndex: 41001,
    name: "Aurora Racket",
    character: "NIKI",
    compatibleCharacters: ["NIKI"],
    price: 2500,
  },
  particle: {
    color: "#66ddff",
    rate: 18,
    lifetime: 1.4,
    size: 0.75,
    curve: [[0, 0], [0.25, 1], [1, 0]],
  },
  runtimeEffect: { effectId: 15, sourceItemIndex: 10728 },
  comparison: {
    browserScreenshot: "aurora-browser.png",
    clientScreenshot: "aurora-client.png",
  },
};

const MAP_DRAFT: ProjectDraft = {
  shell: { workspace: "maps", step: "item" },
  editors: { map: mapSceneProjectValue(createCourt("Untitled Court", false)) },
};

export const PROJECT_TEMPLATES: ProjectTemplate[] = [
  {
    id: "equipment-starter",
    title: "Equipment starter",
    description: "New equipment model, attachment, material and particle draft.",
    draft: EQUIPMENT_DRAFT,
  },
  {
    id: "empty-court",
    title: "Empty playable court",
    description: "Scene document ready for objects, spawns and collision.",
    draft: MAP_DRAFT,
  },
  {
    id: "combined-showcase",
    title: "Equipment + court showcase",
    description: "A combined content pack project with both authoring desks.",
    draft: {
      shell: { workspace: "equipment", step: "item" },
      editors: {
        ...EQUIPMENT_DRAFT.editors,
        ...MAP_DRAFT.editors,
      },
    },
  },
];

export function createProjectEnvelope(
  name: string,
  draft: ProjectDraft,
): ProjectEnvelope {
  return {
    schemaVersion: PROJECT_SCHEMA_VERSION,
    name,
    draft: cloneDraft(draft),
  };
}

export const REFERENCE_PROJECTS: ReferenceProject[] = [
  {
    id: "equipment-golden",
    project: createProjectEnvelope("Golden Aurora Racket", {
      ...cloneDraft(EQUIPMENT_DRAFT),
      editors: { equipment: equipmentDraftProjectValue(GOLDEN_EQUIPMENT) },
    }),
  },
  {
    id: "map-golden",
    project: createProjectEnvelope("Golden QA Court", {
      ...cloneDraft(MAP_DRAFT),
      editors: { map: mapSceneProjectValue(createCourt("QA Court", true)) },
    }),
  },
  {
    id: "combined-golden",
    project: createProjectEnvelope(
      "Golden Combined Pack",
      PROJECT_TEMPLATES[2].draft,
    ),
  },
];
