export type ImportedMaterial = { id: string; name: string };

export type ImportedEquipmentAsset = {
  sourceName: string;
  meshName: string;
  vertexCount: number;
  indexCount: number;
  materials: ImportedMaterial[];
  warnings: string[];
};

export type MaterialAssignment = {
  textureName: string;
  color: string;
  metallic: number;
  roughness: number;
};

export type EquipmentAttachment = {
  bone: string;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
};

export type EquipmentMetadata = {
  itemIndex: number;
  name: string;
  character: string;
  compatibleCharacters: string[];
  price: number;
};

export type EquipmentParticle = {
  color: string;
  rate: number;
  lifetime: number;
  size: number;
  curve: Array<[number, number]>;
};

export type EquipmentComparison = {
  browserScreenshot: string | null;
  clientScreenshot: string | null;
};

export type EquipmentRuntimeEffect =
  | { effectId: 0; sourceItemIndex: null }
  | { effectId: 15; sourceItemIndex: 10728 };

export type EquipmentDraft = {
  asset: ImportedEquipmentAsset;
  materials: Record<string, MaterialAssignment>;
  attachment: EquipmentAttachment | null;
  metadata: EquipmentMetadata;
  particle: EquipmentParticle;
  runtimeEffect: EquipmentRuntimeEffect;
  comparison: EquipmentComparison;
};

export type EquipmentValidation = { field: string; message: string };
