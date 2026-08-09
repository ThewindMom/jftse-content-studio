import type { EquipmentDraft } from "../web/equipmentTypes.ts";

export type EquipmentRuntimeField =
  | "assetTopology"
  | "materials"
  | "attachment"
  | "comparison"
  | "metadata"
  | "particle"
  | "effectBinding";

export type EquipmentRuntimeClassification = Record<
  EquipmentRuntimeField,
  "design-only" | "evidence-only" | "runtime-written"
>;

export type EquipmentRuntimeProof = {
  metadata?: boolean;
  particle?: boolean;
  effectBinding?: boolean;
};

const DESIGN_FIELDS: EquipmentRuntimeField[] = [
  "assetTopology",
  "materials",
  "attachment",
];

export function classifyEquipmentRuntimeFields(
  draft: EquipmentDraft,
  proof: EquipmentRuntimeProof = {
    metadata: true,
    particle: draft.runtimeEffect.effectId === 15,
    effectBinding: true,
  },
): EquipmentRuntimeClassification {
  return {
    assetTopology: "design-only",
    materials: "design-only",
    attachment: "design-only",
    comparison: "evidence-only",
    metadata: proof.metadata ? "runtime-written" : "design-only",
    particle:
      draft.runtimeEffect.effectId === 15 && proof.particle
        ? "runtime-written"
        : "design-only",
    effectBinding: proof.effectBinding ? "runtime-written" : "design-only",
  };
}

export function buildEquipmentRuntimeReceipt(
  draft: EquipmentDraft,
  proof?: EquipmentRuntimeProof,
) {
  const fields = classifyEquipmentRuntimeFields(draft, proof);
  const pass = (Object.keys(fields) as EquipmentRuntimeField[]).filter(
    (field) => fields[field] === "runtime-written",
  );
  const miss = DESIGN_FIELDS.filter((field) => fields[field] === "design-only");
  if (fields.particle === "design-only") miss.push("particle");
  if (fields.effectBinding === "design-only") miss.push("effectBinding");
  if (fields.metadata === "design-only") miss.push("metadata");
  return {
    itemIndex: draft.metadata.itemIndex,
    effectId: draft.runtimeEffect.effectId,
    fields,
    pass,
    miss,
    evidence: ["comparison"],
  };
}
