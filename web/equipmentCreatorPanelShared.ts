import type { EquipmentDraft, MaterialAssignment } from "./equipmentCreator.ts";

export type DraftChange = (draft: EquipmentDraft | null) => void;
export type CapturePreview = { filename: string; url: string };

export function matchingCapturePreview(
  preview: CapturePreview | null,
  filename: string | null,
): CapturePreview | null {
  return preview && preview.filename === filename ? preview : null;
}

export const SAMPLE_GLTF = JSON.stringify({
  asset: { version: "2.0", generator: "JFTSE Content Studio" },
  accessors: [
    { count: 3, componentType: 5126, type: "VEC3" },
    { count: 3, componentType: 5123, type: "SCALAR" },
  ],
  materials: [{ name: "Frame" }],
  meshes: [
    {
      name: "Studio sample racket",
      primitives: [{ attributes: { POSITION: 0 }, indices: 1, material: 0 }],
    },
  ],
});

export const DEFAULT_MATERIAL: MaterialAssignment = {
  textureName: "",
  color: "#57d7ff",
  metallic: 0.25,
  roughness: 0.6,
};
