import { mkdirSync, rmSync } from "node:fs";
import { basename, join } from "node:path";
import { buildEquipmentManifest } from "../web/equipmentDraft.ts";
import { buildEquipmentRuntimeReceipt } from "./equipmentRuntimeContract.ts";
import type { EquipmentDraft } from "../web/equipmentTypes.ts";
import { buildEffect, runBridgeWithPayload } from "./bridge.ts";
import { config } from "./config.ts";

type JsonObject = Record<string, unknown>;
type Writer = (payload: JsonObject, outDir: string) => Promise<JsonObject>;
export type EquipmentPackageRequest = {
  draft: EquipmentDraft;
  stockMeshIndex: number;
};
export type EquipmentPackageDependencies = {
  exportsDir: string;
  buildEffect: Writer;
  buildContentPack: Writer;
};

function fail(code: string): never {
  throw new Error(code);
}

function record(value: unknown, code: string): JsonObject {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(code);
  return value as JsonObject;
}

function string(value: unknown, code: string, max = 200): string {
  if (typeof value !== "string" || !value.trim() || value.length > max) fail(code);
  return value;
}

function number(value: unknown, code: string, min: number, max: number): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max) fail(code);
  return value;
}

function filename(value: unknown, code: string): string {
  const result = string(value, code);
  if (basename(result) !== result || /[\\/]/.test(result) || result === "." || result === "..") fail(code);
  return result;
}

function vector(value: unknown, code: string): [number, number, number] {
  if (!Array.isArray(value) || value.length !== 3) fail(code);
  return value.map((entry) => number(entry, code, -10_000, 10_000)) as [number, number, number];
}

export function validateEquipmentPackageRequest(value: unknown): EquipmentPackageRequest {
  const body = record(value, "INVALID_EQUIPMENT_PACKAGE");
  const draft = record(body.draft, "DRAFT_REQUIRED");
  const asset = record(draft.asset, "ASSET_REQUIRED");
  filename(asset.sourceName, "SOURCE_NAME_INVALID");
  string(asset.meshName, "MESH_NAME_REQUIRED");
  number(asset.vertexCount, "VERTEX_COUNT_INVALID", 1, 250_000);
  number(asset.indexCount, "INDEX_COUNT_INVALID", 3, 1_500_000);
  if (!Array.isArray(asset.materials) || asset.materials.length < 1 || asset.materials.length > 64) fail("MATERIAL_SLOTS_INVALID");
  const ids = new Set<string>();
  for (const raw of asset.materials) {
    const material = record(raw, "MATERIAL_SLOT_INVALID");
    const id = string(material.id, "MATERIAL_ID_INVALID", 80);
    string(material.name, "MATERIAL_NAME_INVALID", 120);
    if (ids.has(id)) fail("MATERIAL_ID_DUPLICATE");
    ids.add(id);
  }
  if (!Array.isArray(asset.warnings) || !asset.warnings.every((entry) => typeof entry === "string")) fail("ASSET_WARNINGS_INVALID");

  const assignments = record(draft.materials, "MATERIAL_ASSIGNMENTS_REQUIRED");
  for (const id of ids) {
    const assignment = record(assignments[id], "MATERIAL_ASSIGNMENT_REQUIRED");
    filename(assignment.textureName, "TEXTURE_NAME_INVALID");
    if (typeof assignment.color !== "string" || !/^#[0-9a-f]{6}$/i.test(assignment.color)) fail("MATERIAL_COLOR_INVALID");
    number(assignment.metallic, "METALLIC_INVALID", 0, 1);
    number(assignment.roughness, "ROUGHNESS_INVALID", 0, 1);
  }

  const attachment = record(draft.attachment, "ATTACHMENT_REQUIRED");
  string(attachment.bone, "ATTACHMENT_BONE_REQUIRED", 100);
  vector(attachment.position, "ATTACHMENT_POSITION_INVALID");
  vector(attachment.rotation, "ATTACHMENT_ROTATION_INVALID");
  vector(attachment.scale, "ATTACHMENT_SCALE_INVALID");

  const metadata = record(draft.metadata, "METADATA_REQUIRED");
  const itemIndex = number(metadata.itemIndex, "ITEM_INDEX_INVALID", 1, 2_147_483_647);
  if (!Number.isInteger(itemIndex)) fail("ITEM_INDEX_INVALID");
  string(metadata.name, "ITEM_NAME_REQUIRED", 120);
  string(metadata.character, "CHARACTER_REQUIRED", 30);
  number(metadata.price, "PRICE_INVALID", 0, 2_147_483_647);
  if (!Array.isArray(metadata.compatibleCharacters) || metadata.compatibleCharacters.length < 1 || !metadata.compatibleCharacters.every((entry) => typeof entry === "string" && entry.trim())) fail("COMPATIBLE_CHARACTERS_INVALID");

  const particle = record(draft.particle, "PARTICLE_REQUIRED");
  if (typeof particle.color !== "string" || !/^#[0-9a-f]{6}$/i.test(particle.color)) fail("PARTICLE_COLOR_INVALID");
  const rate = number(particle.rate, "PARTICLE_RATE_INVALID", 1, 40);
  if (!Number.isInteger(rate)) fail("PARTICLE_RATE_INVALID");
  number(particle.lifetime, "PARTICLE_LIFETIME_INVALID", 0.1, 5);
  number(particle.size, "PARTICLE_SIZE_INVALID", 0.05, 3);
  if (!Array.isArray(particle.curve) || particle.curve.length < 2 || particle.curve.length > 32) fail("PARTICLE_CURVE_INVALID");
  let prior = -1;
  for (const point of particle.curve) {
    if (!Array.isArray(point) || point.length !== 2) fail("PARTICLE_CURVE_INVALID");
    const time = number(point[0], "PARTICLE_CURVE_INVALID", 0, 1);
    number(point[1], "PARTICLE_CURVE_INVALID", 0, 3);
    if (time <= prior) fail("PARTICLE_CURVE_INVALID");
    prior = time;
  }

  const runtimeEffect = record(draft.runtimeEffect, "RUNTIME_EFFECT_REQUIRED");
  const effectId = number(runtimeEffect.effectId, "RUNTIME_EFFECT_INVALID", 0, 15);
  if (!Number.isInteger(effectId) || (effectId !== 0 && effectId !== 15)) fail("RUNTIME_EFFECT_INVALID");
  if (effectId === 15 && runtimeEffect.sourceItemIndex !== 10728) fail("RUNTIME_EFFECT_SOURCE_INVALID");
  if (effectId === 0 && runtimeEffect.sourceItemIndex !== null) fail("RUNTIME_EFFECT_SOURCE_INVALID");

  const comparison = record(draft.comparison, "COMPARISON_REQUIRED");
  const browserCapture = filename(comparison.browserScreenshot, "COMPARISON_BROWSER_REQUIRED");
  const clientCapture = filename(comparison.clientScreenshot, "COMPARISON_CLIENT_REQUIRED");
  if (!/\.(?:png|jpe?g)$/i.test(browserCapture)) fail("COMPARISON_BROWSER_INVALID");
  if (!/\.(?:png|jpe?g)$/i.test(clientCapture)) fail("COMPARISON_CLIENT_INVALID");
  const stockMeshIndex = number(body.stockMeshIndex, "STOCK_MESH_INDEX_REQUIRED", 0, 2_147_483_647);
  if (!Number.isInteger(stockMeshIndex)) fail("STOCK_MESH_INDEX_REQUIRED");
  return { draft: draft as EquipmentDraft, stockMeshIndex };
}

function effectPayload(draft: EquipmentDraft): JsonObject {
  const rgb = draft.particle.color.slice(1).match(/../g)!.map((part) => parseInt(part, 16));
  const life = Math.round(draft.particle.lifetime * 30);
  const peak = Math.max(...draft.particle.curve.map((point) => point[1]));
  const peakPoints = draft.particle.curve.filter((point) => point[1] === peak);
  const fadeIn = Math.round(peakPoints[0][0] * life);
  const fadeOut = Math.round(draft.particle.curve.at(-1)![0] * life);
  return {
    texturePath: "Res/Effect/EftB/A_feather",
    color: rgb.join(","), quantity: draft.particle.rate,
    life, size: draft.particle.size,
    fadeIn, fadeOut: Math.max(fadeIn + 1, fadeOut), fadeFor: Math.max(1, fadeOut - fadeIn),
    allowBannedAtlas: false,
    includeItemBinding: false,
    includeEffectBinding: true,
    effectId: draft.runtimeEffect.effectId,
  };
}

async function receipt(path: string) {
  const file = Bun.file(path);
  if (!(await file.exists())) fail("WRITER_ARTIFACT_MISSING");
  const bytes = await file.arrayBuffer();
  return { path, bytes: bytes.byteLength, sha256: new Bun.CryptoHasher("sha256").update(bytes).digest("hex") };
}

const defaults: EquipmentPackageDependencies = {
  exportsDir: config.exportsDir,
  buildEffect,
  buildContentPack: (payload, outDir) => runBridgeWithPayload(
    "equipment-content-pack", payload,
    (payloadPath) => ["content-pack-build", "--payload", payloadPath, "--out-dir", outDir],
    { timeoutMs: 300_000 },
  ),
};

export async function packageEquipmentCreator(input: unknown, deps = defaults) {
  const { draft, stockMeshIndex } = validateEquipmentPackageRequest(input);
  const packageId = `equipment-creator-${Date.now()}-${crypto.randomUUID()}`;
  const root = join(deps.exportsDir, packageId);
  mkdirSync(root, { recursive: true });
  try {
    const selectedEffect = draft.runtimeEffect.effectId === 15;
    const effect: JsonObject = selectedEffect
      ? await deps.buildEffect(effectPayload(draft), join(root, "effect"))
      : { ok: true };
    if (
      effect.ok === false ||
      (selectedEffect && typeof effect.particleArchive !== "string")
    ) fail("EFFECT_BUILD_FAILED");
    const contentPackPayload: JsonObject = {
      name: draft.metadata.name,
      equipment: {
        meshIndex: stockMeshIndex,
        newIndex: draft.metadata.itemIndex,
        productIndex: draft.metadata.itemIndex,
        sourceItemIndex: selectedEffect
          ? draft.runtimeEffect.sourceItemIndex
          : 10728,
        char: draft.metadata.character,
        desc: draft.metadata.name,
        part: "Racket",
        effect: draft.runtimeEffect.effectId,
        gold: draft.metadata.price,
      },
    };
    if (selectedEffect) {
      contentPackPayload.particleArchive = effect.particleArchive;
      if (typeof effect.effectArchive === "string") {
        contentPackPayload.effectArchive = effect.effectArchive;
      }
    }
    const contentPack = await deps.buildContentPack(
      contentPackPayload,
      join(root, "content-pack"),
    );
    if (contentPack.ok === false || !Array.isArray(contentPack.installPlan) || typeof contentPack.sqlPath !== "string") fail("CONTENT_PACK_BUILD_FAILED");
    const plan = contentPack.installPlan.map((entry) => {
      const item = record(entry, "INSTALL_PLAN_INVALID");
      return {
        source: string(item.source, "INSTALL_SOURCE_INVALID"),
        destRelative: string(item.destRelative, "INSTALL_DESTINATION_INVALID"),
      };
    });
    const destinations = plan.map((entry) => entry.destRelative);
    if (new Set(destinations).size !== destinations.length) fail("INSTALL_PLAN_DUPLICATE");
    const sources = plan.map((entry) => entry.source);
    const hasItem = destinations.filter((path) => path === "Res/Script/Item.res").length === 1;
    const hasParticle = destinations.filter((path) => path === "Res/Effect/Particle.res").length === 1;
    const hasEffect = destinations.filter((path) => path === "Res/Script/ETC.res").length === 1;
    if (!hasItem || sources.filter((path) => path.endsWith(".res")).length < 2) fail("INSTALL_PLAN_INCOMPLETE");
    if (selectedEffect && (!hasParticle || !sources.includes(effect.particleArchive as string))) fail("INSTALL_PLAN_INCOMPLETE");
    if (typeof effect.effectArchive === "string" && (!hasEffect || !sources.includes(effect.effectArchive))) fail("INSTALL_PLAN_INCOMPLETE");
    if (!selectedEffect && (hasParticle || hasEffect)) fail("INSTALL_PLAN_UNSUPPORTED_EFFECT_ARTIFACT");
    const artifacts = await Promise.all([...new Set([...sources, contentPack.sqlPath])].map(receipt));
    const creatorManifest = {
      schemaVersion: 1, kind: "equipment-creator-production",
      draftManifest: buildEquipmentManifest(draft),
      comparisonScreenshots: draft.comparison,
      writer: { mode: "stock-topology-clone", importedTopology: "preview-spec-only", limitations: ["Imported glTF/OBJ topology and material/attachment edits are specification and comparison data only.", "Production compatibility is bounded by the automatically selected stock racket topology.", "Particle curves are approximated as the recovered writer's fade envelope; DX9 client verification remains authoritative."] },
      effect: selectedEffect
        ? {
            effectId: 15,
            atlas: "Res/Effect/EftB/A_feather",
            slot: effect.slot,
            parameters: draft.particle,
            verification: effect.verification,
            particleArchive: await receipt(effect.particleArchive as string),
            effectArchive: typeof effect.effectArchive === "string"
              ? await receipt(effect.effectArchive)
              : null,
          }
        : { effectId: 0, selection: "none" },
      contentPack: { receipt: contentPack, installPlan: contentPack.installPlan, sqlPath: contentPack.sqlPath, artifacts },
    };
    const creatorManifestPath = join(root, "creator-manifest.json");
    await Bun.write(creatorManifestPath, JSON.stringify(creatorManifest, null, 2));
    const runtimeReceipt = buildEquipmentRuntimeReceipt(draft, {
      metadata: hasItem && typeof contentPack.sqlPath === "string",
      particle: selectedEffect && hasParticle,
      effectBinding: hasItem && (!selectedEffect || hasEffect),
    });
    return {
      ok: true,
      contentPack,
      creatorManifestPath,
      creatorManifestSha256: (await receipt(creatorManifestPath)).sha256,
      runtimeReceipt,
      handoff: {
        packageId,
        descriptor: {
          root,
          creatorManifestPath,
          installPlan: contentPack.installPlan,
          sqlPath: contentPack.sqlPath,
        },
      },
    };
  } catch (error) {
    rmSync(root, { recursive: true, force: true });
    throw error;
  }
}
