import { afterEach, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  buildRuntimeMapPackage,
  packageMapScene,
} from "../server/mapScenePackage.ts";
import {
  addMapObject,
  addMapSpawn,
  createEmptyMapScene,
  setMapReferences,
} from "../web/mapSceneDocument.ts";

const temporaryRoots: string[] = [];

function temporaryRoot(): string {
  const root = mkdtempSync(join(tmpdir(), "map-scene-package-"));
  temporaryRoots.push(root);
  return root;
}

async function rejectionMessage(operation: Promise<unknown>): Promise<string> {
  try {
    await operation;
  } catch (error) {
    return error instanceof Error ? error.message : String(error);
  }
  throw new Error("Expected operation to reject");
}

function playableScene() {
  let scene = createEmptyMapScene("QA Court");
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
  return setMapReferences(scene, {
    stageScript: "Stage/QA_Court.set",
    ftmArchive: "Res/MapSet/QA_Court.res",
    ftmMember: "QA_Court.ftm",
    collisionAsset: "Stage/QA_Court_Collision.dat",
    terrainSource: "roundtrip/qa-court.blend",
    materials: [{ slot: "court", texture: "Texture/qa-court.png" }],
  });
}

afterEach(() => {
  for (const root of temporaryRoots.splice(0)) {
    rmSync(root, { recursive: true, force: true });
  }
});

describe("map scene package", () => {
  test("builds verified runtime artifacts through the content-pack writer", async () => {
    const scene = playableScene();
    const dependencies = new Set([
      "court/net.glb",
      "Stage/QA_Court.set",
      "Res/MapSet/QA_Court.res",
      "Stage/QA_Court_Collision.dat",
      "roundtrip/qa-court.blend",
      "Texture/qa-court.png",
    ]);
    const outputDirectory = join(temporaryRoot(), "runtime-packages");
    let compiledPayload: Record<string, unknown> | undefined;

    const receipt = await buildRuntimeMapPackage(
      scene,
      dependencies,
      outputDirectory,
      async (payload, outDir) => {
        compiledPayload = payload;
        const stage = join(outDir, "stage", "Info.res");
        const ftm = join(outDir, "ftm", "QA_Court.res");
        const sql = join(outDir, "map", "map-create.sql");
        await Bun.write(stage, "stage");
        await Bun.write(ftm, "ftm");
        await Bun.write(sql, "INSERT INTO S_Maps (id) VALUES (300);");
        return {
          ok: true,
          outDir,
          parts: {
            map: { sql },
            stage: { infoArchive: stage },
            ftm: { archive: ftm },
          },
          sqlPath: sql,
          installPlan: [
            { source: stage, destRelative: "Res/Stage/Info.res" },
            { source: ftm, destRelative: "Res/MapSet/QA_Court.res" },
          ],
        };
      },
    );

    expect(compiledPayload).toMatchObject({
      name: "QA Court",
      map: { draft: { name: "QA Court" } },
      ftm: { add: [expect.objectContaining({ prefabIndex: 0 })] },
    });
    expect(receipt.contentPack.installPlan).toHaveLength(2);
    expect(receipt.runtimeUnsupported).toEqual([
      "player-spawn compilation",
      "terrain geometry compilation",
      "stage material binding compilation",
    ]);
    expect(receipt.hash).toMatch(/^[a-f0-9]{64}$/);
    const manifest = await Bun.file(receipt.path).json();
    expect(manifest.scene).toEqual(scene);
    expect(manifest.contentPack.parts).toHaveProperty("ftm");
  });

  test("atomically writes a deterministic manifest and identical scene", async () => {
    const scene = playableScene();
    const dependencies = new Set([
      "court/net.glb",
      "Stage/QA_Court.set",
      "Res/MapSet/QA_Court.res",
      "Stage/QA_Court_Collision.dat",
      "roundtrip/qa-court.blend",
      "Texture/qa-court.png",
    ]);
    const outputDirectory = join(temporaryRoot(), "packages");

    const first = await packageMapScene(scene, dependencies, outputDirectory);
    const firstBytes = await Bun.file(first.path).arrayBuffer();
    const artifact = JSON.parse(new TextDecoder().decode(firstBytes));

    expect(first.path).toBe(join(outputDirectory, "QA Court.map-package.json"));
    expect(first.bytes).toBe(firstBytes.byteLength);
    expect(first.hash).toBe(
      createHash("sha256").update(new Uint8Array(firstBytes)).digest("hex"),
    );
    expect(first.dependencies).toEqual([...dependencies]);
    expect(artifact.scene).toEqual(scene);
    expect(artifact).toMatchObject({
      schemaVersion: 1,
      kind: "map",
      name: "QA Court",
      counts: { objects: 1, spawns: 2, blockedCells: 0 },
    });
    expect(readdirSync(outputDirectory)).toEqual(["QA Court.map-package.json"]);

    const second = await packageMapScene(scene, dependencies, outputDirectory);
    expect(second).toEqual(first);
    expect(await Bun.file(second.path).arrayBuffer()).toEqual(firstBytes);
    expect(readdirSync(outputDirectory)).toEqual(["QA Court.map-package.json"]);
  });

  test("rejects traversal without creating output", async () => {
    const scene = { ...playableScene(), name: "../escaped" };
    const root = temporaryRoot();
    const outputDirectory = join(root, "packages");

    expect(
      await rejectionMessage(
        packageMapScene(
          scene,
          new Set([
            "court/net.glb",
            "Stage/QA_Court.set",
            "Res/MapSet/QA_Court.res",
            "Stage/QA_Court_Collision.dat",
            "roundtrip/qa-court.blend",
            "Texture/qa-court.png",
          ]),
          outputDirectory,
        ),
      ),
    ).toContain("Unsafe map package name");
    expect(existsSync(outputDirectory)).toBe(false);
    expect(existsSync(join(root, "escaped.map-package.json"))).toBe(false);
  });

  test("rejects missing dependencies without creating output", async () => {
    const outputDirectory = join(temporaryRoot(), "packages");

    expect(
      await rejectionMessage(
        packageMapScene(playableScene(), new Set(), outputDirectory),
      ),
    ).toContain("Missing map dependencies");
    expect(existsSync(outputDirectory)).toBe(false);
  });
});
