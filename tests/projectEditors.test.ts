import { describe, expect, test } from "bun:test";
import { compileMapScene } from "../server/mapSceneCompiler";
import {
  addMapObject,
  createEmptyMapScene,
  setMapReferences,
} from "../web/mapSceneDocument";
import {
  createEquipmentDraft,
  setEquipmentMetadata,
} from "../web/equipmentCreator";
import {
  equipmentDraftProjectValue,
  mapSceneProjectValue,
  readProjectEquipmentDraft,
  readProjectMapScene,
  updateProjectEditor,
  updateProjectShell,
} from "../web/projectEditors";
import type { ProjectDraft } from "../web/projectModel";

function playableScene() {
  return setMapReferences(createEmptyMapScene("Project Court"), {
    stageScript: "Stage/Project_Court.set",
    ftmArchive: "Res/MapSet/Project_Court.res",
    ftmMember: "Project_Court.ftm",
    collisionAsset: "Stage/Project_Court_Collision.dat",
    terrainSource: "roundtrip/Project_Court.blend",
    materials: [{ slot: "court", texture: "Texture/Project_Court.png" }],
  });
}

describe("project-owned editor drafts", () => {
  test("workspace navigation preserves every editor payload", () => {
    const draft: ProjectDraft = {
      shell: { workspace: "equipment", step: "item", custom: "keep" },
      editors: {
        equipment: { name: "Project racket" },
        map: mapSceneProjectValue(playableScene()),
      },
    };

    const next = updateProjectShell(draft, "maps", "item");

    expect(next.shell).toEqual({
      workspace: "maps",
      step: "item",
      custom: "keep",
    });
    expect(next.editors).toEqual(draft.editors);
  });

  test("map edits round-trip through the project envelope", () => {
    const scene = addMapObject(playableScene(), {
      assetId: "net.glb",
      name: "Center net",
      layer: "objects",
      position: [0, 0, 0],
      rotation: [0, 90, 0],
      scale: [1, 1.25, 1],
    });
    const draft: ProjectDraft = {
      shell: { workspace: "maps", step: "item" },
      editors: {},
    };

    const next = updateProjectEditor(
      draft,
      "map",
      mapSceneProjectValue(scene),
    );

    expect(readProjectMapScene(next)).toEqual(scene);
  });

  test("malformed template map data recovers to a safe empty scene", () => {
    const draft: ProjectDraft = {
      shell: { workspace: "maps", step: "item" },
      editors: { map: { name: "partial template" } },
    };

    const recovered = readProjectMapScene(draft);

    expect(recovered.name).toBe("Untitled Court");
    expect(recovered.objects).toEqual([]);
  });

  test("fresh project fallback uses compilable stock templates", () => {
    const fresh: ProjectDraft = {
      shell: { workspace: "maps", step: "item" },
      editors: {},
    };

    const scene = readProjectMapScene(fresh);
    const compiled = compileMapScene(scene);

    expect(scene.references).toMatchObject({
      stageScript: "1_Emerald_Beach.set",
      ftmArchive: "Res/MapSet/FantaCastle.res",
      ftmMember: "FantaCastleOutSide.ftm",
      collisionAsset: "Res/MapSet/FantaCastle.res",
    });
    expect(compiled.payload).toMatchObject({
      stage: { member: "1_Emerald_Beach.set" },
      ftm: {
        archive: "Res/MapSet/FantaCastle.res",
        member: "FantaCastleOutSide.ftm",
      },
    });
  });

  test("equipment edits round-trip through the project envelope", () => {
    const draft = setEquipmentMetadata(
      createEquipmentDraft({
        sourceName: "project-racket.gltf",
        meshName: "Project Racket",
        vertexCount: 12,
        indexCount: 18,
        materials: [{ id: "court", name: "Court" }],
        warnings: [],
      }),
      {
        itemIndex: 9001,
        name: "Project Racket",
        character: "NIKI",
        compatibleCharacters: ["NIKI"],
        price: 2500,
      },
    );
    const project: ProjectDraft = {
      shell: { workspace: "equipment", step: "item" },
      editors: {},
    };

    const next = updateProjectEditor(
      project,
      "equipment",
      equipmentDraftProjectValue(draft),
    );

    expect(readProjectEquipmentDraft(next)).toEqual(draft);
  });

  test("malformed equipment data recovers to an empty creator", () => {
    const draft: ProjectDraft = {
      shell: { workspace: "equipment", step: "item" },
      editors: { equipment: { metadata: { name: "partial" } } },
    };

    expect(readProjectEquipmentDraft(draft)).toBeNull();
  });
});
