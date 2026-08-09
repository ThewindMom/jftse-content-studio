import { describe, expect, test } from "bun:test";
import {
  matchingCapturePreview,
  type CapturePreview,
} from "../web/EquipmentCreatorPanel.tsx";
import {
  assignEquipmentMaterial,
  buildEquipmentManifest,
  createEquipmentDraft,
  importEquipmentGltf,
  importEquipmentObj,
  setEquipmentAttachment,
  setEquipmentComparison,
  setEquipmentMetadata,
  setEquipmentParticle,
  validateEquipmentDraft,
} from "../web/equipmentCreator.ts";

test("comparison previews remain only while project filenames match", () => {
  const preview: CapturePreview = {
    filename: "browser-current.png",
    url: "blob:browser-current",
  };

  expect(matchingCapturePreview(preview, "browser-current.png")).toBe(preview);
  expect(matchingCapturePreview(preview, "browser-older.png")).toBeNull();
  expect(matchingCapturePreview(preview, null)).toBeNull();
  expect(matchingCapturePreview(null, "persisted-without-blob.png")).toBeNull();
});

const triangleGltf = {
  asset: { version: "2.0", generator: "JFTSE test fixture" },
  buffers: [
    {
      byteLength: 42,
      uri: `data:application/octet-stream;base64,${Buffer.from(
        new Uint8Array([
          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 128, 63, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 128, 63, 0, 0, 0, 0, 1, 0, 2, 0,
          0, 0,
        ]),
      ).toString("base64")}`,
    },
  ],
  bufferViews: [
    { buffer: 0, byteOffset: 0, byteLength: 36 },
    { buffer: 0, byteOffset: 36, byteLength: 6 },
  ],
  accessors: [
    {
      bufferView: 0,
      componentType: 5126,
      count: 3,
      type: "VEC3",
      min: [0, 0, 0],
      max: [1, 1, 0],
    },
    { bufferView: 1, componentType: 5123, count: 3, type: "SCALAR" },
  ],
  materials: [{ name: "Frame" }],
  meshes: [
    {
      name: "New racket",
      primitives: [{ attributes: { POSITION: 0 }, indices: 1, material: 0 }],
    },
  ],
  nodes: [{ name: "RacketRoot", mesh: 0 }],
  scenes: [{ nodes: [0] }],
  scene: 0,
};

describe("equipment creator", () => {
  test("imports OBJ geometry and material slots as preview-only metadata", () => {
    const asset = importEquipmentObj(
      "new-racket.obj",
      [
        "o New racket",
        "v 0 0 0",
        "v 1 0 0",
        "v 1 1 0",
        "v 0 1 0",
        "usemtl Frame",
        "f 1 2 3 4",
      ].join("\n"),
    );

    expect(asset).toEqual({
      sourceName: "new-racket.obj",
      meshName: "New racket",
      vertexCount: 4,
      indexCount: 6,
      materials: [{ id: "material-0", name: "Frame" }],
      warnings: [
        "Imported OBJ topology is preview/spec-only; production uses the selected stock racket topology.",
      ],
    });
  });

  test("imports glTF geometry and material slots without raw paths", () => {
    const asset = importEquipmentGltf(
      "new-racket.gltf",
      JSON.stringify(triangleGltf),
    );

    expect(asset.sourceName).toBe("new-racket.gltf");
    expect(asset.meshName).toBe("New racket");
    expect(asset.vertexCount).toBe(3);
    expect(asset.indexCount).toBe(3);
    expect(asset.materials).toEqual([{ id: "material-0", name: "Frame" }]);
    expect(asset.warnings).toEqual([]);
  });

  test("validates missing designer decisions with actionable fields", () => {
    const draft = createEquipmentDraft(
      importEquipmentGltf("new-racket.gltf", JSON.stringify(triangleGltf)),
    );

    expect(validateEquipmentDraft(draft)).toEqual([
      { field: "materials.material-0", message: "Assign a texture to Frame." },
      { field: "attachment.bone", message: "Choose an attachment bone." },
      { field: "metadata.itemIndex", message: "Choose an item index." },
      { field: "metadata.name", message: "Name this equipment." },
      {
        field: "comparison.browserScreenshot",
        message: "Add the browser comparison capture name.",
      },
      {
        field: "comparison.clientScreenshot",
        message: "Add the DX9 client comparison capture name.",
      },
    ]);
  });

  test("builds a deterministic complete manifest from visual controls", () => {
    let draft = createEquipmentDraft(
      importEquipmentGltf("new-racket.gltf", JSON.stringify(triangleGltf)),
    );
    draft = assignEquipmentMaterial(draft, "material-0", {
      textureName: "racket_frame.png",
      color: "#57d7ff",
      metallic: 0.25,
      roughness: 0.6,
    });
    draft = setEquipmentAttachment(draft, {
      bone: "Bone_Racket",
      position: [0, 0, 0],
      rotation: [0, 0, 0],
      scale: [1, 1, 1],
    });
    draft = setEquipmentMetadata(draft, {
      itemIndex: 41001,
      name: "Aurora Racket",
      character: "NIKI",
      compatibleCharacters: ["NIKI", "LUCY"],
      price: 25000,
    });
    draft = setEquipmentParticle(draft, {
      color: "#66ddff",
      rate: 18,
      lifetime: 1.2,
      size: 0.55,
      curve: [
        [0, 0],
        [0.25, 1],
        [1, 0],
      ],
    });
    draft = setEquipmentComparison(draft, {
      browserScreenshot: "aurora-browser.png",
      clientScreenshot: "aurora-client.png",
    });

    expect(validateEquipmentDraft(draft)).toEqual([]);
    expect(buildEquipmentManifest(draft)).toEqual({
      schemaVersion: 1,
      kind: "equipment",
      source: {
        name: "new-racket.gltf",
        meshName: "New racket",
        vertexCount: 3,
        indexCount: 3,
      },
      materials: [
        {
          slot: "material-0",
          name: "Frame",
          textureName: "racket_frame.png",
          color: "#57d7ff",
          metallic: 0.25,
          roughness: 0.6,
        },
      ],
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
        compatibleCharacters: ["NIKI", "LUCY"],
        price: 25000,
      },
      particle: {
        color: "#66ddff",
        rate: 18,
        lifetime: 1.2,
        size: 0.55,
        curve: [
          [0, 0],
          [0.25, 1],
          [1, 0],
        ],
      },
      comparison: {
        browserScreenshot: "aurora-browser.png",
        clientScreenshot: "aurora-client.png",
      },
      warnings: [
        "Imported glTF/OBJ topology is preview/spec-only; production clones the selected stock racket topology. Verify the package in the DX9 client.",
      ],
    });
  });

  test("rejects malformed glTF at the import boundary", () => {
    expect(() => importEquipmentGltf("broken.gltf", "{}")).toThrow(
      "glTF mesh",
    );
    expect(() =>
      importEquipmentGltf("broken.gltf", JSON.stringify(triangleGltf), {
        maxVertices: 2,
      }),
    ).toThrow("vertex limit");
  });

  test("records browser and client captures for visual comparison", () => {
    const draft = createEquipmentDraft(
      importEquipmentGltf("new-racket.gltf", JSON.stringify(triangleGltf)),
    );
    const compared = setEquipmentComparison(draft, {
      browserScreenshot: "aurora-browser.png",
      clientScreenshot: "aurora-client.png",
    });

    expect(compared.comparison).toEqual({
      browserScreenshot: "aurora-browser.png",
      clientScreenshot: "aurora-client.png",
    });
  });
});
