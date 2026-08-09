import { describe, expect, test } from "bun:test";
import { mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  packageEquipmentCreator,
  validateEquipmentPackageRequest,
} from "../server/equipmentCreatorPackage.ts";
import type { EquipmentDraft } from "../web/equipmentTypes.ts";

function completeDraft(): EquipmentDraft {
  return {
    asset: {
      sourceName: "aurora.obj",
      meshName: "Aurora",
      vertexCount: 3,
      indexCount: 3,
      materials: [{ id: "material-0", name: "Frame" }],
      warnings: ["preview-only"],
    },
    materials: {
      "material-0": {
        textureName: "aurora.png",
        color: "#66ddff",
        metallic: 0.2,
        roughness: 0.6,
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
      price: 25000,
    },
    particle: {
      color: "#66ddff",
      rate: 18,
      lifetime: 1.2,
      size: 0.55,
      curve: [[0, 0], [0.25, 1], [1, 0]],
    },
    runtimeEffect: {
      effectId: 15,
      sourceItemIndex: 10728,
    },
    comparison: {
      browserScreenshot: "aurora-browser.png",
      clientScreenshot: "aurora-client.png",
    },
  } as EquipmentDraft;
}

describe("equipment creator production package", () => {
  test("deep validation rejects a missing comparison capture", () => {
    const draft = completeDraft();
    draft.comparison.clientScreenshot = null;
    expect(() =>
      validateEquipmentPackageRequest({ draft, stockMeshIndex: 214 }),
    ).toThrow("COMPARISON_CLIENT_REQUIRED");
  });

  test("writes explicit equipment effect binding", async () => {
    const exportsDir = mkdtempSync(join(tmpdir(), "equipment-creator-"));
    const calls: Array<Record<string, unknown>> = [];
    try {
      const result = await packageEquipmentCreator(
        { draft: completeDraft(), stockMeshIndex: 214 },
        {
          exportsDir,
          buildEffect: async (payload, outDir) => {
            calls.push({ kind: "effect", payload });
            const particleArchive = join(outDir, "Particle.studio.res");
            await Bun.write(particleArchive, "particle");
            return {
              ok: true,
              particleArchive,
              slot: "Ice_Smoke02.set",
              verification: { ok: true, fields: { PQ_Quantity: "18" } },
            };
          },
          buildContentPack: async (payload, outDir) => {
            calls.push({ kind: "pack", payload });
            const mesh = join(outDir, "equipment-mesh.res");
            const catalog = join(outDir, "Item.res");
            const sqlPath = join(outDir, "content-pack.sql");
            await Promise.all([
              Bun.write(mesh, "mesh"),
              Bun.write(catalog, "catalog"),
              Bun.write(sqlPath, "INSERT INTO S_Product VALUES (41001);"),
            ]);
            return {
              ok: true,
              outDir,
              installPlan: [
                { source: mesh, destRelative: "Res/Item/NikiItem.res" },
                { source: catalog, destRelative: "Res/Script/Item.res" },
                {
                  source: String(payload.particleArchive),
                  destRelative: "Res/Effect/Particle.res",
                },
              ],
              sqlPath,
              parts: { equipment: {}, particle: payload.particleArchive },
            };
          },
        },
      );

      expect(calls[0]?.payload).toMatchObject({
        texturePath: "Res/Effect/EftB/A_feather",
        color: "102,221,255",
        quantity: 18,
        life: 36,
        size: 0.55,
        includeItemBinding: false,
        includeEffectBinding: true,
        effectId: 15,
      });
      expect(calls[1]?.payload).toMatchObject({
        equipment: {
          meshIndex: 214,
          newIndex: 41001,
          productIndex: 41001,
          sourceItemIndex: 10728,
          char: "NIKI",
          desc: "Aurora Racket",
          part: "Racket",
          effect: 15,
          gold: 25000,
        },
      });
      expect(result.contentPack.installPlan).toHaveLength(3);
      expect(result.creatorManifestSha256).toMatch(/^[a-f0-9]{64}$/);
      const manifest = await Bun.file(result.creatorManifestPath).json();
      expect(manifest.draftManifest.comparison).toEqual(completeDraft().comparison);
      expect(manifest.writer.mode).toBe("stock-topology-clone");
      expect(manifest.writer.importedTopology).toBe("preview-spec-only");
      expect(manifest.contentPack.artifacts).toHaveLength(4);
      expect(manifest.contentPack.artifacts[0].sha256).toMatch(/^[a-f0-9]{64}$/);
      expect(manifest.contentPack.artifacts[0].bytes).toBeGreaterThan(0);
    } finally {
      rmSync(exportsDir, { recursive: true, force: true });
    }
  });

  test("reports design-only equipment fields", async () => {
    const {
      buildEquipmentRuntimeReceipt,
      classifyEquipmentRuntimeFields,
    } = await import("../server/equipmentRuntimeContract.ts");
    expect(classifyEquipmentRuntimeFields(completeDraft())).toEqual({
      assetTopology: "design-only",
      materials: "design-only",
      attachment: "design-only",
      comparison: "evidence-only",
      metadata: "runtime-written",
      particle: "runtime-written",
      effectBinding: "runtime-written",
    });
    expect(buildEquipmentRuntimeReceipt(completeDraft())).toMatchObject({
      itemIndex: 41001,
      effectId: 15,
      pass: ["metadata", "particle", "effectBinding"],
      miss: ["assetTopology", "materials", "attachment"],
    });
  });

  test("removes the bounded export directory when a writer fails", async () => {
    const exportsDir = mkdtempSync(join(tmpdir(), "equipment-creator-failure-"));
    try {
      await expect(packageEquipmentCreator(
        { draft: completeDraft(), stockMeshIndex: 214 },
        {
          exportsDir,
          buildEffect: async (_payload, outDir) => {
            const particleArchive = join(outDir, "Particle.studio.res");
            await Bun.write(particleArchive, "particle");
            return { ok: true, particleArchive };
          },
          buildContentPack: async () => {
            throw new Error("writer failed");
          },
        },
      )).rejects.toThrow("writer failed");
      expect(readdirSync(exportsDir)).toEqual([]);
    } finally {
      rmSync(exportsDir, { recursive: true, force: true });
    }
  });
});
