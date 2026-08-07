import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { cpSync, existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const port = 4317;
const base = `http://127.0.0.1:${port}`;
const jftseRoot =
  process.env.JFTSE_ROOT ??
  "/home/thewind/Projects/00_Random_Coding/260705_fanta_tennis/JFTSE";
const stockClient = join(jftseRoot, ".jftse-client-linux/client");

let serverProc: ReturnType<typeof Bun.spawn> | null = null;
let disposableClient = "";

const softPayload = {
  texturePath: "Res/Effect/EftB/A_feather",
  color: "80,160,205",
  quantity: 18,
  speed: 0.3,
  life: 16,
  size: 1.4,
  offAxisSpread: 180,
  offPlaneSpread: 180,
  phase: 180,
  phaseVar: 100,
  subTexSize: "STS_64",
  subTexCount: 8,
  allowBannedAtlas: false,
  includeItemBinding: false,
};

beforeAll(async () => {
  disposableClient = mkdtempSync(join(tmpdir(), "jftse-studio-client-"));
  await Bun.write(join(disposableClient, "Res/Effect/.keep"), "");
  cpSync(
    join(stockClient, "Res/Effect/Particle.res"),
    join(disposableClient, "Res/Effect/Particle.res"),
  );

  serverProc = Bun.spawn(["bun", "run", "server/index.ts"], {
    cwd: join(import.meta.dir, ".."),
    env: {
      ...process.env,
      PORT: String(port),
      JFTSE_ROOT: jftseRoot,
      JFTSE_STOCK_CLIENT: stockClient,
      JFTSE_LOCAL_CLIENT: disposableClient,
    },
    stdout: "pipe",
    stderr: "pipe",
  });
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${base}/api/health`);
      if (response.ok || response.status >= 400) return;
    } catch {
      await Bun.sleep(100);
    }
  }
  throw new Error("server failed to start");
});

afterAll(() => {
  serverProc?.kill();
  serverProc = null;
  if (disposableClient && existsSync(disposableClient)) {
    rmSync(disposableClient, { recursive: true, force: true });
  }
});

describe("content studio production API", () => {
  test("health bridge is online", async () => {
    const response = await fetch(`${base}/api/health`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.particleRes).toBe(true);
  });

  test("maps list is non-empty", async () => {
    const response = await fetch(`${base}/api/maps`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(Array.isArray(body.maps)).toBe(true);
    expect(body.maps.length).toBeGreaterThan(0);
    expect(body.maps[0]).toHaveProperty("name");
  });

  test("banned atlas build is rejected", async () => {
    const response = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        texturePath: "Res/Effect/EftB/A_spaak_Line",
        quantity: 12,
        allowBannedAtlas: false,
        includeItemBinding: false,
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(400);
    expect(body.error).toBe("BANNED_ATLAS");
  });

  test("shared racket script path is rejected", async () => {
    const response = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        ...softPayload,
        texturePath: "Res/Effect/Particle/Racket_001",
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(400);
    expect(body.error).toBe("SHARED_RACKET_SCRIPT_FORBIDDEN");
  });

  test("malformed JSON is rejected", async () => {
    const response = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{not-json",
    });
    const body = await response.json();
    expect(response.status).toBe(400);
    expect(body.error).toBe("INVALID_JSON");
  });

  test("soft effect build exports verified isolated particle archive", async () => {
    const response = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(softPayload),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(typeof body.particleArchive).toBe("string");
    expect(await Bun.file(body.particleArchive).exists()).toBe(true);
    expect(body.verification).toBeDefined();
    expect(body.verification.sharedRacket001Identical).toBe(true);
    expect(body.verification.sharedRacket002Identical).toBe(true);
    expect(body.verification.changedMembers).toEqual(["Ice_Smoke02.set"]);
    expect(body.verification.fields.TexturePath).toContain("A_feather");
    expect(body.verification.fields.PQ_Quantity).toBe("18");
    expect(body.verification.archiveSizeBytes).toBeGreaterThan(0);
  }, 120000);

  test("install refuses stock client path", async () => {
    const build = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(softPayload),
    }).then((r) => r.json());
    const response = await fetch(`${base}/api/effects/install`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        particleArchive: build.particleArchive,
        targetClient: stockClient,
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(400);
    expect(body.error).toBe("REFUSE_STOCK_CLIENT");
  }, 120000);

  test("install accepts disposable local client", async () => {
    const build = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(softPayload),
    }).then((r) => r.json());
    const response = await fetch(`${base}/api/effects/install`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        particleArchive: build.particleArchive,
        targetClient: disposableClient,
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.installed.particle).toContain("Particle.res");
    expect(await Bun.file(body.installed.particle).exists()).toBe(true);
  }, 120000);

  test("presets endpoint lists designer presets", async () => {
    const response = await fetch(`${base}/api/presets`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.presets.length).toBeGreaterThanOrEqual(3);
    expect(body.presets[0]).toHaveProperty("effect");
  });

  test("workflow endpoint returns ordered designer steps", async () => {
    const response = await fetch(`${base}/api/workflow`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.steps.map((step: { id: string }) => step.id)).toEqual([
      "item",
      "effect",
      "export",
      "install",
      "playtest",
    ]);
  });

  test("map sql export writes seed file", async () => {
    const response = await fetch(`${base}/api/maps/export-sql`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        maps: [{ id: 1, map: 0, name: "Rubycrab", isBossStage: false }],
        stageByMap: { "0": "0_Tutorial.set" },
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(await Bun.file(body.path).exists()).toBe(true);
    const sql = await Bun.file(body.path).text();
    expect(sql).toContain("INSERT INTO S_Maps");
    expect(sql).toContain("Rubycrab");
  });

  test("pack save and load round-trip", async () => {
    const name = `test-pack-${Date.now()}`;
    const create = await fetch(`${base}/api/packs`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name,
        item: { index: "10728", name: "Dragon Slayer(Black)" },
        effect: softPayload,
        notes: "round-trip",
      }),
    }).then((r) => r.json());
    expect(create.ok).toBe(true);
    const loaded = await fetch(`${base}/api/packs/${name}`).then((r) => r.json());
    expect(loaded.ok).toBe(true);
    expect(loaded.pack.notes).toBe("round-trip");
    expect(loaded.pack.item.index).toBe("10728");
  });

  test("atlas preview returns png bytes", async () => {
    const response = await fetch(
      `${base}/api/atlases/preview?archive=EftB.res&member=A_feather.tex`,
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("image/png");
    const bytes = new Uint8Array(await response.arrayBuffer());
    expect(bytes[0]).toBe(0x89);
    expect(bytes[1]).toBe(0x50);
    expect(bytes[2]).toBe(0x4e);
    expect(bytes[3]).toBe(0x47);
  }, 120000);

  test("map studio catalog includes relations and stage candidates", async () => {
    const response = await fetch(`${base}/api/map-studio/catalog`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.maps.length).toBeGreaterThan(0);
    const emerald = body.maps.find((row: { map: number }) => row.map === 1);
    expect(emerald).toBeDefined();
    expect(emerald.name).toContain("Emerald");
    expect(Array.isArray(emerald.scenarioIds)).toBe(true);
    expect(emerald.scenarioIds.length).toBeGreaterThan(0);
    expect(emerald.guardianCount).toBeGreaterThan(0);
    expect(Array.isArray(emerald.stageCandidates)).toBe(true);
    expect(emerald.stageCandidates.some((s: string) => s.includes("Emerald"))).toBe(
      true,
    );
  });

  test("map studio validate accepts known stage script", async () => {
    const response = await fetch(`${base}/api/map-studio/validate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ stageScript: "1_Emerald_Beach.set" }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.valid).toBe(true);
    expect(body.stage.WorldFile).toContain("Mesh");
  });

  test("map studio validate rejects missing stage script", async () => {
    const response = await fetch(`${base}/api/map-studio/validate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ stageScript: "99_Does_Not_Exist.set" }),
    });
    const body = await response.json();
    expect(response.status).toBe(400);
    expect(body.error).toBe("STAGE_SCRIPT_MISSING");
  });

  test("map studio export pack writes relational SQL bundle", async () => {
    const response = await fetch(`${base}/api/map-studio/export-pack`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        mapIds: [2],
        stageByMapId: { "2": "1_Emerald_Beach.set" },
        includeGuardians: true,
        includeScenarios: true,
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(await Bun.file(body.path).exists()).toBe(true);
    const sql = await Bun.file(body.path).text();
    expect(sql).toContain("INSERT INTO S_Maps");
    expect(sql).toContain("Map_2_Scenarios");
    expect(sql).toContain("Guardian_2_Maps");
    expect(sql).toContain("Emerald Beach");
    expect(sql).toContain("1_Emerald_Beach.set");
  });
});
