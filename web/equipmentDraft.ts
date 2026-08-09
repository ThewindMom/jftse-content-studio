import type {
  EquipmentAttachment,
  EquipmentComparison,
  EquipmentDraft,
  EquipmentMetadata,
  EquipmentParticle,
  EquipmentRuntimeEffect,
  EquipmentValidation,
  ImportedEquipmentAsset,
  MaterialAssignment,
} from "./equipmentTypes.ts";

export function createEquipmentDraft(
  asset: ImportedEquipmentAsset,
): EquipmentDraft {
  return {
    asset,
    materials: {},
    attachment: null,
    metadata: {
      itemIndex: 0,
      name: "",
      character: "NIKI",
      compatibleCharacters: ["NIKI"],
      price: 0,
    },
    particle: {
      color: "#66ddff",
      rate: 12,
      lifetime: 1,
      size: 0.5,
      curve: [
        [0, 0],
        [0.25, 1],
        [1, 0],
      ],
    },
    runtimeEffect: { effectId: 0, sourceItemIndex: null },
    comparison: { browserScreenshot: null, clientScreenshot: null },
  };
}

export function assignEquipmentMaterial(
  draft: EquipmentDraft,
  slot: string,
  assignment: MaterialAssignment,
): EquipmentDraft {
  if (!draft.asset.materials.some((material) => material.id === slot)) {
    throw new Error(`Unknown equipment material slot: ${slot}`);
  }
  return {
    ...draft,
    materials: { ...draft.materials, [slot]: { ...assignment } },
  };
}

export function setEquipmentAttachment(
  draft: EquipmentDraft,
  attachment: EquipmentAttachment,
): EquipmentDraft {
  return { ...draft, attachment: structuredClone(attachment) };
}

export function setEquipmentMetadata(
  draft: EquipmentDraft,
  metadata: EquipmentMetadata,
): EquipmentDraft {
  return { ...draft, metadata: structuredClone(metadata) };
}

export function setEquipmentParticle(
  draft: EquipmentDraft,
  particle: EquipmentParticle,
): EquipmentDraft {
  return { ...draft, particle: structuredClone(particle) };
}

export function setEquipmentRuntimeEffect(
  draft: EquipmentDraft,
  runtimeEffect: EquipmentRuntimeEffect,
): EquipmentDraft {
  return { ...draft, runtimeEffect: { ...runtimeEffect } };
}

export function setEquipmentComparison(
  draft: EquipmentDraft,
  comparison: EquipmentComparison,
): EquipmentDraft {
  return { ...draft, comparison: { ...comparison } };
}

export function validateEquipmentDraft(
  draft: EquipmentDraft,
): EquipmentValidation[] {
  const issues: EquipmentValidation[] = [];
  for (const material of draft.asset.materials) {
    if (!draft.materials[material.id]?.textureName.trim()) {
      issues.push({
        field: `materials.${material.id}`,
        message: `Assign a texture to ${material.name}.`,
      });
    }
  }
  if (!draft.attachment?.bone.trim()) {
    issues.push({
      field: "attachment.bone",
      message: "Choose an attachment bone.",
    });
  }
  if (
    !Number.isInteger(draft.metadata.itemIndex) ||
    draft.metadata.itemIndex <= 0
  ) {
    issues.push({
      field: "metadata.itemIndex",
      message: "Choose an item index.",
    });
  }
  if (!draft.metadata.name.trim()) {
    issues.push({ field: "metadata.name", message: "Name this equipment." });
  }
  if (!draft.comparison.browserScreenshot?.trim()) {
    issues.push({
      field: "comparison.browserScreenshot",
      message: "Add the browser comparison capture name.",
    });
  }
  if (!draft.comparison.clientScreenshot?.trim()) {
    issues.push({
      field: "comparison.clientScreenshot",
      message: "Add the DX9 client comparison capture name.",
    });
  }
  return issues;
}

export function buildEquipmentManifest(draft: EquipmentDraft) {
  const issues = validateEquipmentDraft(draft);
  if (issues.length > 0) {
    throw new Error(`Equipment draft has ${issues.length} unresolved issue(s).`);
  }
  return {
    schemaVersion: 1,
    kind: "equipment" as const,
    source: {
      name: draft.asset.sourceName,
      meshName: draft.asset.meshName,
      vertexCount: draft.asset.vertexCount,
      indexCount: draft.asset.indexCount,
    },
    materials: draft.asset.materials.map((material) => ({
      slot: material.id,
      name: material.name,
      ...draft.materials[material.id],
    })),
    attachment: draft.attachment,
    metadata: draft.metadata,
    particle: draft.particle,
    comparison: draft.comparison,
    warnings: [
      ...draft.asset.warnings,
      "Imported glTF/OBJ topology is preview/spec-only; production clones the selected stock racket topology. Verify the package in the DX9 client.",
    ],
  };
}
