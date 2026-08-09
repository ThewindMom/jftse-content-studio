import {
  createEmptyMapScene,
  parseMapScene,
  serializeMapScene,
  setMapReferences,
  type MapSceneDocument,
} from "./mapSceneDocument.ts";
import type { EquipmentDraft } from "./equipmentCreator.ts";
import type { JsonValue, ProjectDraft } from "./projectModel.ts";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isVector(value: unknown): value is [number, number, number] {
  return (
    Array.isArray(value) &&
    value.length === 3 &&
    value.every(isFiniteNumber)
  );
}

function isEquipmentDraft(value: unknown): value is EquipmentDraft {
  if (!isRecord(value)) return false;
  const {
    asset,
    materials,
    attachment,
    metadata,
    particle,
    runtimeEffect,
    comparison,
  } = value;
  if (
    !isRecord(asset) ||
    typeof asset.sourceName !== "string" ||
    typeof asset.meshName !== "string" ||
    !isFiniteNumber(asset.vertexCount) ||
    !isFiniteNumber(asset.indexCount) ||
    !Array.isArray(asset.materials) ||
    !asset.materials.every(
      (entry) =>
        isRecord(entry) &&
        typeof entry.id === "string" &&
        typeof entry.name === "string",
    ) ||
    !isStringArray(asset.warnings) ||
    !isRecord(materials) ||
    !isRecord(metadata) ||
    !Number.isInteger(metadata.itemIndex) ||
    typeof metadata.name !== "string" ||
    typeof metadata.character !== "string" ||
    !isStringArray(metadata.compatibleCharacters) ||
    !isFiniteNumber(metadata.price) ||
    !isRecord(particle) ||
    typeof particle.color !== "string" ||
    !isFiniteNumber(particle.rate) ||
    !isFiniteNumber(particle.lifetime) ||
    !isFiniteNumber(particle.size) ||
    !Array.isArray(particle.curve) ||
    !particle.curve.every(
      (point) =>
        Array.isArray(point) &&
        point.length === 2 &&
        point.every(isFiniteNumber),
    ) ||
    !isRecord(runtimeEffect) ||
    !(
      (runtimeEffect.effectId === 0 && runtimeEffect.sourceItemIndex === null) ||
      (runtimeEffect.effectId === 15 && runtimeEffect.sourceItemIndex === 10728)
    ) ||
    !isRecord(comparison) ||
    !(
      comparison.browserScreenshot === null ||
      typeof comparison.browserScreenshot === "string"
    ) ||
    !(
      comparison.clientScreenshot === null ||
      typeof comparison.clientScreenshot === "string"
    )
  ) {
    return false;
  }
  if (
    attachment !== null &&
    (!isRecord(attachment) ||
      typeof attachment.bone !== "string" ||
      !isVector(attachment.position) ||
      !isVector(attachment.rotation) ||
      !isVector(attachment.scale))
  ) {
    return false;
  }
  return Object.values(materials).every(
    (entry) =>
      isRecord(entry) &&
      typeof entry.textureName === "string" &&
      typeof entry.color === "string" &&
      isFiniteNumber(entry.metallic) &&
      isFiniteNumber(entry.roughness),
  );
}

function safeMapStem(value: string): string {
  return (
    value
      .trim()
      .replace(/[^A-Za-z0-9_-]+/g, "_")
      .replace(/^_+|_+$/g, "") || "Untitled_Court"
  );
}

export function createStockMapScene(name: string): MapSceneDocument {
  return setMapReferences(createEmptyMapScene(name), {
    stageScript: "1_Emerald_Beach.set",
    ftmArchive: "Res/MapSet/FantaCastle.res",
    ftmMember: "FantaCastleOutSide.ftm",
    collisionAsset: "Res/MapSet/FantaCastle.res",
    terrainSource: `roundtrip/${safeMapStem(name)}.blend`,
    materials: [{ slot: "court", texture: "Texture/Court01.tex" }],
  });
}

export function updateProjectShell(
  draft: ProjectDraft,
  workspace: string,
  step: string,
): ProjectDraft {
  return {
    shell: { ...draft.shell, workspace, step },
    editors: draft.editors,
  };
}

export function updateProjectEditor(
  draft: ProjectDraft,
  key: string,
  value: JsonValue,
): ProjectDraft {
  return {
    shell: draft.shell,
    editors: { ...draft.editors, [key]: value },
  };
}

export function mapSceneProjectValue(scene: MapSceneDocument): JsonValue {
  return JSON.parse(serializeMapScene(scene)) as JsonValue;
}

export function equipmentDraftProjectValue(
  draft: EquipmentDraft,
): JsonValue {
  return JSON.parse(JSON.stringify(draft)) as JsonValue;
}

export function readProjectEquipmentDraft(
  draft: ProjectDraft,
): EquipmentDraft | null {
  const stored = draft.editors.equipment;
  return isEquipmentDraft(stored) ? structuredClone(stored) : null;
}

export function readProjectMapScene(draft: ProjectDraft): MapSceneDocument {
  const stored = draft.editors.map;
  if (stored !== undefined) {
    try {
      return parseMapScene(JSON.stringify(stored));
    } catch {
      // Malformed or legacy template data falls back to a safe empty scene.
    }
  }
  return createStockMapScene("Untitled Court");
}
