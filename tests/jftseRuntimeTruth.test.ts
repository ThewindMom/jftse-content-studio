import { afterEach, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { buildRuntimeMapPackage } from "../server/mapScenePackage.ts";
import {
  addMapSpawn,
  createEmptyMapScene,
  setMapReferences,
} from "../web/mapSceneDocument.ts";

type TruthFixture = {
  schemaVersion: number;
  kind: string;
  provenance: {
    textSources: Array<{ path: string; sha256: string; anchors: string[] }>;
    resourceRoots: Record<"stock" | "local", string>;
    resources: Array<{
      client: "stock" | "local";
      path: string;
      sha256: string;
      members: string[];
    }>;
  };
  itemIndexContract: Record<string, unknown>;
  mapSpawnContract: {
    authoredCoordinates: { classification: string; compiledToJftseRuntime: boolean };
    runtimeReceiptContract: {
      fields: string[];
      forbiddenAuthoredCoordinateFields: string[];
      requiredLimitation: string;
    };
  };
};

const fixturePath = join(import.meta.dir, "fixtures/compatibility/jftse-runtime-truth.json");
const temporaryRoots: string[] = [];

async function sha256(path: string): Promise<string> {
  const bytes = await Bun.file(path).arrayBuffer();
  return createHash("sha256").update(new Uint8Array(bytes)).digest("hex");
}

function collectKeys(value: unknown, keys: string[] = []): string[] {
  if (!value || typeof value !== "object") return keys;
  for (const [key, child] of Object.entries(value)) {
    keys.push(key);
    collectKeys(child, keys);
  }
  return keys;
}

afterEach(() => {
  for (const root of temporaryRoots.splice(0)) {
    rmSync(root, { recursive: true, force: true });
  }
});

describe("authoritative sibling JFTSE runtime truth", () => {
  test("pins the fixture schema and every textual source hash and anchor", async () => {
    const fixture = (await Bun.file(fixturePath).json()) as TruthFixture;
    expect(fixture.schemaVersion).toBe(1);
    expect(fixture.kind).toBe("jftse-item-effect-map-spawn-runtime-truth");
    expect(fixture.provenance.textSources.length).toBeGreaterThanOrEqual(9);
    expect(fixture.itemIndexContract).toBeObject();
    expect(fixture.mapSpawnContract.authoredCoordinates).toEqual(
      expect.objectContaining({ classification: "design-only", compiledToJftseRuntime: false }),
    );

    for (const source of fixture.provenance.textSources) {
      const path = resolve(dirname(fixturePath), "../../..", source.path);
      expect(await sha256(path), source.path).toBe(source.sha256);
      const text = await Bun.file(path).text();
      for (const anchor of source.anchors) expect(text, `${source.path}: ${anchor}`).toContain(anchor);
    }
  });

  test("pins exact stock/local resource hashes and ZIP member references", async () => {
    const fixture = (await Bun.file(fixturePath).json()) as TruthFixture;
    expect(fixture.provenance.resources).toHaveLength(16);

    for (const resource of fixture.provenance.resources) {
      const root = fixture.provenance.resourceRoots[resource.client];
      const path = resolve(dirname(fixturePath), "../../..", root, resource.path);
      expect(await sha256(path), `${resource.client}:${resource.path}`).toBe(resource.sha256);
      const archiveBytes = Buffer.from(await Bun.file(path).arrayBuffer()).toString("latin1");
      for (const member of resource.members) {
        expect(archiveBytes, `${resource.client}:${resource.path}::${member}`).toContain(member);
      }
    }
  });

  test("keeps authored spawn coordinates in design evidence and out of runtime receipts", async () => {
    const fixture = (await Bun.file(fixturePath).json()) as TruthFixture;
    const contract = fixture.mapSpawnContract.runtimeReceiptContract;
    let scene = createEmptyMapScene("Truth Court");
    scene = addMapSpawn(scene, { team: "home", position: [-137, 2, 419], facing: 73 });
    scene = addMapSpawn(scene, { team: "away", position: [251, 3, -607], facing: -81 });
    scene = setMapReferences(scene, {
      stageScript: "Stage/Info/1_Emerald_Beach.set",
      ftmArchive: "Res/MapSet/FantaCastle.res",
      ftmMember: "FantaCastle.ftm",
      collisionAsset: "Res/Collision.res",
      terrainSource: "",
      materials: [],
    });
    const root = mkdtempSync(join(tmpdir(), "jftse-truth-"));
    temporaryRoots.push(root);
    const receipt = await buildRuntimeMapPackage(scene, new Set([
      "Stage/Info/1_Emerald_Beach.set",
      "Res/MapSet/FantaCastle.res",
      "Res/Collision.res",
    ]), root, async (_payload, outDir) => {
      const stage = join(outDir, "Info.res");
      const ftm = join(outDir, "FantaCastle.res");
      const sql = join(outDir, "map.sql");
      await Promise.all([Bun.write(stage, "stage"), Bun.write(ftm, "ftm"), Bun.write(sql, "sql")]);
      return {
        ok: true,
        outDir,
        parts: { map: {}, stage: {}, ftm: {} },
        sqlPath: sql,
        installPlan: [
          { source: stage, destRelative: "Res/Stage/Info.res" },
          { source: ftm, destRelative: "Res/MapSet/FantaCastle.res" },
        ],
      };
    });

    expect(Object.keys(receipt).sort()).toEqual([...contract.fields].sort());
    const receiptKeys = collectKeys(receipt);
    for (const forbidden of contract.forbiddenAuthoredCoordinateFields) {
      expect(receiptKeys, `runtime receipt field ${forbidden}`).not.toContain(forbidden);
    }
    expect(receipt.runtimeUnsupported).toContain(contract.requiredLimitation);
    const designManifest = await Bun.file(receipt.path).json();
    expect(designManifest.design.spawns).toEqual(scene.spawns);
  });
});
