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

  test("health exposes designer setup readiness checklist", async () => {
    const response = await fetch(`${base}/api/health`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.setup).toBeDefined();
    expect(typeof body.setup.ready).toBe("boolean");
    expect(typeof body.setup.stockClient).toBe("string");
    expect(typeof body.setup.localClient).toBe("string");
    expect(typeof body.setup.stockExists).toBe("boolean");
    expect(typeof body.setup.localExists).toBe("boolean");
    expect(typeof body.setup.particleRes).toBe("boolean");
    expect(typeof body.setup.installReady).toBe("boolean");
    expect(Array.isArray(body.setup.checklist)).toBe(true);
    expect(body.setup.checklist.length).toBeGreaterThan(0);
    expect(body.setup.checklist[0]).toHaveProperty("id");
    expect(body.setup.checklist[0]).toHaveProperty("ok");
    expect(body.setup.checklist[0]).toHaveProperty("label");
  });

  test("exports library lists recent studio artifacts", async () => {
    const build = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(softPayload),
    }).then((r) => r.json());
    expect(build.ok).toBe(true);
    const response = await fetch(`${base}/api/exports?limit=20`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(Array.isArray(body.exports)).toBe(true);
    expect(body.exports.length).toBeGreaterThan(0);
    const hit = body.exports.find(
      (row: { path?: string }) => row.path === build.particleArchive,
    );
    expect(hit).toBeDefined();
    expect(hit.kind).toBe("effect");
    expect(typeof hit.name).toBe("string");
    expect(typeof hit.bytes).toBe("number");
    expect(typeof hit.mtimeMs).toBe("number");
  }, 120000);

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
    // Stock may already carry the soft wind slot (idempotent rebuild → []).
    // Only Ice_Smoke02.set may appear in changedMembers.
    expect(
      body.verification.changedMembers.every(
        (name: string) => name === "Ice_Smoke02.set",
      ),
    ).toBe(true);
    expect(body.verification.fields.TexturePath).toContain("A_feather");
    expect(body.verification.fields.PQ_Quantity).toBe("18");
    expect(body.verification.archiveSizeBytes).toBeGreaterThan(0);
  }, 120000);

  test("soft effect build is idempotent when stock slot already matches", async () => {
    const first = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(softPayload),
    }).then((r) => r.json());
    expect(first.ok).toBe(true);
    const second = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(softPayload),
    });
    const body = await second.json();
    expect(second.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.verification.fields.TexturePath).toContain("A_feather");
    expect(body.verification.fields.PQ_Quantity).toBe("18");
    expect(
      body.verification.changedMembers.every(
        (name: string) => name === "Ice_Smoke02.set",
      ),
    ).toBe(true);
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

  test("mesh studio lists and parses court mesh", async () => {
    const list = await fetch(`${base}/api/mesh-studio/list`).then((r) => r.json());
    expect(list.ok).toBe(true);
    expect(list.meshes.length).toBeGreaterThan(0);
    const court =
      list.meshes.find((row: { member: string }) => /court/i.test(row.member)) ??
      list.meshes[0];
    const parsed = await fetch(
      `${base}/api/mesh-studio/parse?archive=${encodeURIComponent(court.archive)}&member=${encodeURIComponent(court.member)}&metaOnly=1`,
    ).then((r) => r.json());
    expect(parsed.ok).toBe(true);
    expect(parsed.mesh.vertexCount).toBeGreaterThan(10);
    expect(parsed.mesh.bounds.min.length).toBe(3);
  }, 120000);

  test("mesh studio export writes obj and gltf", async () => {
    const list = await fetch(`${base}/api/mesh-studio/list`).then((r) => r.json());
    const court =
      list.meshes.find((row: { member: string }) => row.member === "BF_Court01.dat") ??
      list.meshes.find((row: { member: string }) => /court/i.test(row.member)) ??
      list.meshes[0];
    const response = await fetch(`${base}/api/mesh-studio/export`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ archive: court.archive, member: court.member }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(await Bun.file(body.obj).exists()).toBe(true);
    expect(await Bun.file(body.gltf).exists()).toBe(true);
    const obj = await Bun.file(body.obj).text();
    expect(obj).toContain("\nv ");
    expect(obj).toContain("\nvn ");
    const gltf = await Bun.file(body.gltf).json();
    expect(gltf.meshes[0].primitives[0].attributes.NORMAL).toBeDefined();
    expect(gltf.extras?.jftseConfidence?.score).toBeGreaterThan(0);
  }, 120000);

  test("mesh decode rejects cubic false-positive runs for TU_Court", async () => {
    const response = await fetch(
      `${base}/api/mesh-studio/parse?archive=${encodeURIComponent("Res/Stage/Mesh00.res")}&member=${encodeURIComponent("TU_Court.dat")}&metaOnly=1`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    const min = body.mesh.bounds.min as number[];
    const max = body.mesh.bounds.max as number[];
    const extent = max.map((v: number, i: number) => v - min[i]!);
    const maxE = Math.max(...extent);
    const minRatio = Math.min(...extent.map((e: number) => e / maxE));
    // A perfect cube (~1.0 ratio on all axes) was the prior false positive silhouette.
    expect(minRatio).toBeLessThan(0.5);
    expect(body.mesh.vertexCount).toBeGreaterThan(100);
  }, 120000);

  test("mesh transform rewrites BF_Court01 with stride-aware vertex packing", async () => {
    // Multi-stride decode (s16) must not pack positions at *12 or interleaved channels corrupt.
    const list = await fetch(`${base}/api/mesh-studio/list`).then((r) => r.json());
    const court =
      list.meshes.find((row: { member: string }) => row.member === "BF_Court01.dat") ??
      list.meshes[0];
    const before = await fetch(
      `${base}/api/mesh-studio/parse?archive=${encodeURIComponent(court.archive)}&member=${encodeURIComponent(court.member)}`,
    ).then((r) => r.json());
    expect(before.ok).toBe(true);
    const stride = Number(before.mesh.vertexStride ?? 12);
    const offset = Number(before.mesh.vertexOffset);
    expect(stride).toBeGreaterThan(12);
    const p0 = before.mesh.positions[0] as number[];
    const response = await fetch(`${base}/api/mesh-studio/transform`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        archive: court.archive,
        member: court.member,
        translate: [3, 0, 0],
        scale: [1, 1, 1],
        rotateDeg: [0, 0, 0],
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.sameSize).toBe(true);
    // float3 at vertexOffset is translated; interleave bytes between verts unchanged.
    const check = Bun.spawnSync(
      [
        "python3",
        "-c",
        [
          "import struct,zipfile",
          "from pathlib import Path",
          `orig=zipfile.ZipFile(Path(${JSON.stringify(stockClient)})/'Res/Stage/Mesh01.res').read('BF_Court01.dat')`,
          `rew=open(${JSON.stringify(body.dat)},'rb').read()`,
          `off,stride=${offset},${stride}`,
          "x,y,z=struct.unpack_from('<fff', rew, off)",
          "print(x,y,z)",
          "gap=all(rew[off+12+i*stride:off+stride+i*stride]==orig[off+12+i*stride:off+stride+i*stride] for i in range(50))",
          "print(int(gap))",
        ].join(";"),
      ],
      { cwd: join(import.meta.dir, "..") },
    );
    expect(check.exitCode).toBe(0);
    const lines = check.stdout.toString().trim().split("\n");
    const xyz = lines[0]!.trim().split(/\s+/).map(Number);
    expect(Math.abs(xyz[0]! - (p0[0]! + 3))).toBeLessThan(0.05);
    expect(lines[1]!.trim()).toBe("1");
  }, 120000);

  test("mesh index recovery increases BF_Court01 solid topology coverage", async () => {
    // RE: first-long u16 run was sparse (~322 tris / 15% verts); area-scored buffer ~580 tris / 39%.
    const response = await fetch(
      `${base}/api/mesh-studio/parse?archive=${encodeURIComponent("Res/Stage/Mesh01.res")}&member=${encodeURIComponent("BF_Court01.dat")}&metaOnly=1`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.mesh.confidence.nonDegenerateTriangles).toBeGreaterThan(500);
    expect(body.mesh.confidence.solidArea).toBeGreaterThan(300_000);
  }, 120000);

  test("item mesh resolve maps Dragon Slayer mesh 214 to PlayerA racket DAT", async () => {
    const response = await fetch(
      `${base}/api/item-mesh/resolve?meshIndex=214&char=NIKI&metaOnly=1`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.resolved.member).toMatch(/Racket/i);
    expect(body.resolved.path).toContain("PlayerA");
    expect(body.mesh.vertexCount).toBeGreaterThan(50);
  }, 120000);

  test("stage set AES decrypt exposes Emerald Beach WorldFile", async () => {
    const response = await fetch(
      `${base}/api/stage-set/decrypt?member=${encodeURIComponent("1_Emerald_Beach.set")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(String(body.fields.WorldFile)).toContain("BF_Court01.dat");
    expect(String(body.fields.SkyFile)).toContain("BF_Sky");
  }, 60000);

  test("stage scene graph parses WorldFile + Object + Effect layers", async () => {
    const response = await fetch(
      `${base}/api/stage-scene?member=${encodeURIComponent("1_Emerald_Beach.set")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.scene.worldFile).toContain("BF_Court01.dat");
    expect(body.scene.world.member).toBe("BF_Court01.dat");
    expect(body.scene.objectCount).toBeGreaterThanOrEqual(2);
    expect(body.scene.objects.some((o: { file: string }) => /BF_All\.dat/i.test(o.file))).toBe(
      true,
    );
    expect(body.scene.effectCount).toBeGreaterThanOrEqual(1);
  }, 60000);

  test("map catalog exposes MapObjRes / MapTileRes entries", async () => {
    const response = await fetch(`${base}/api/map-catalog`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.catalog.objectCount).toBeGreaterThan(10);
    expect(body.catalog.tileCount).toBeGreaterThanOrEqual(4);
    expect(body.catalog.objects[0].path).toMatch(/\.dat$/i);
  }, 60000);

  test("mesh meta extracts multi-material texture names from BF_Court01", async () => {
    const response = await fetch(
      `${base}/api/mesh-studio/meta?archive=${encodeURIComponent("Res/Stage/Mesh01.res")}&member=${encodeURIComponent("BF_Court01.dat")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.meta.materialCount).toBeGreaterThanOrEqual(3);
    const names = (body.meta.materials as { name: string }[]).map((m) => m.name);
    expect(names.some((n) => /Coat/i.test(n))).toBe(true);
  }, 60000);

  test("mesh meta extracts Bone_Racket socket from Niki body mesh", async () => {
    const response = await fetch(
      `${base}/api/mesh-studio/meta?archive=${encodeURIComponent("Res/Player/PlayerA/Mesh.res")}&member=${encodeURIComponent("Niki.dat")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.meta.hasSkeleton).toBe(true);
    expect(body.meta.boneCount).toBeGreaterThan(20);
    const boneNames = (body.meta.bones as { name: string }[]).map((b) => b.name);
    expect(boneNames.some((n) => /Racket/i.test(n))).toBe(true);
  }, 120000);

  test("mesh meta parses 64-byte equipment material table on Dragon Slayer racket", async () => {
    const response = await fetch(
      `${base}/api/mesh-studio/meta?archive=${encodeURIComponent("Res/Player/PlayerA/Item07.res")}&member=${encodeURIComponent("Niki_CommonRacket41.dat")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    const table = body.meta.equipmentMaterialTable;
    expect(table).toBeDefined();
    expect(table.count).toBeGreaterThanOrEqual(2);
    expect(table.recordSize).toBe(64);
    expect(table.stems[0]).toMatch(/Racket/i);
  }, 60000);

  test("FTM parse returns scene placements with prefabIndex xyz scale rotation", async () => {
    const response = await fetch(
      `${base}/api/ftm/parse?archive=${encodeURIComponent("Res/MapSet/FantaCastle.res")}&member=${encodeURIComponent("FantaCastleOutSide.ftm")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.kind).toBe("ftm");
    expect(body.ftm.tileCountX).toBeGreaterThan(10);
    expect(body.ftm.sceneObjectCount).toBeGreaterThanOrEqual(1);
    const obj = body.ftm.sceneObjects[0];
    expect(obj).toMatchObject({
      prefabIndex: expect.any(Number),
      x: expect.any(Number),
      y: expect.any(Number),
      scaleHeight: expect.any(Number),
      scaleWidth: expect.any(Number),
      rotationY: expect.any(Number),
      rotationX: expect.any(Number),
    });
    expect(obj.prefabName).toBeTruthy();
  }, 60000);

  test("PRJ parse lists child FTM paths", async () => {
    const response = await fetch(
      `${base}/api/ftm/parse?archive=${encodeURIComponent("Res/MapSet/FantaCastle.res")}&member=${encodeURIComponent("FantaCastle.prj")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.kind).toBe("prj");
    expect(body.prj.ftmCount).toBe(2);
    expect(body.prj.ftmPaths[0]).toMatch(/FantaCastle/);
  }, 60000);

  test("FTM parse rejects truncated blob cleanly", async () => {
    // empty member path without archive should fail structured
    const response = await fetch(
      `${base}/api/ftm/parse?member=${encodeURIComponent("missing.ftm")}`,
    );
    const body = await response.json();
    // bridge returns ok:false or HTTP error — not a crash
    expect([200, 400, 500]).toContain(response.status);
    if (response.status === 200) {
      expect(body.ok).toBe(false);
    }
  }, 30000);

  test("ANI parse recovers NikiAniA tracks and frame duration", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.ani.header.trackCount).toBe(40);
    expect(body.ani.header.frameCount).toBe(44);
    expect(body.ani.duration).toBeGreaterThan(1.4);
    expect(body.ani.duration).toBeLessThan(1.5);
    expect(body.ani.trackCount).toBe(40);
    expect(body.ani.tracks[0].positions.length).toBeGreaterThan(0);
  }, 60000);

  test("ANI maxFrames=0 returns full frame samples for scrubber", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}&maxFrames=0`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.ani.frameCount).toBe(44);
    expect(body.ani.sampled).toBe(false);
    expect(body.ani.sampleMaxFrames).toBeNull();
    expect(body.ani.tracks[0].positions.length).toBe(44);
    expect(body.ani.tracks[0].times.length).toBe(44);
    // Section probe for RE (A/B/C sizes + quat hypothesis)
    expect(body.ani.sectionProbe).toBeDefined();
    expect(body.ani.sectionProbe.A.size).toBeGreaterThan(1000);
    expect(body.ani.sectionProbe.C.size).toBeGreaterThan(1000);
    expect(body.ani.sectionProbe.rotationHypothesis).toBeDefined();
    expect(typeof body.ani.sectionProbe.rotationHypothesis.confident).toBe("boolean");
    // Multi-clip stack in section A (NikiAniA has 16 float3 clips)
    expect(body.ani.sectionProbe.multiClip).toBeDefined();
    expect(body.ani.sectionProbe.multiClip.clipCount).toBeGreaterThanOrEqual(2);
    expect(body.ani.sectionProbe.clipIndex ?? body.ani.clipIndex ?? 0).toBe(0);
    expect(String(body.ani.layout)).toMatch(/multi-clip/);
  }, 60000);

  test("ANI clipIndex selects alternate multi-clip float3 stack", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}&maxFrames=2&clipIndex=1`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.ani.clipIndex).toBe(1);
    expect(body.ani.sectionProbe.selectedClip.index).toBe(1);
    expect(body.ani.tracks[0].positions.length).toBeGreaterThan(0);
  }, 60000);

  test("ANI clipIndex out of range fails structured", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}&clipIndex=999`,
    );
    const body = await response.json();
    expect([200, 400, 500]).toContain(response.status);
    if (response.status === 200) {
      expect(body.ok).toBe(false);
      expect(String(body.detail ?? body.error)).toMatch(/clipIndex|out of range|ANI/i);
    }
  }, 30000);

  test("ANI section B/C/tail hypotheses expose structural RE fields", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}&maxFrames=1`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    const probe = body.ani.sectionProbe;
    expect(probe.sectionBHypothesis.sameSizeAsC).toBe(true);
    expect(probe.sectionBHypothesis.sectionAMinusB).toBe(1290);
    expect(probe.sectionBHypothesis.oddSized).toBe(true);
    expect(probe.sectionBHypothesis.boneIndexLike).toBe(false);
    expect(probe.multiClipC.clipCount).toBeGreaterThanOrEqual(2);
    expect(probe.tailHypothesis.size).toBeGreaterThan(1000);
    expect(probe.rotationHypothesis.confident).toBe(false);
  }, 60000);

  test("ANI channel=C decodes secondary float3 multi-clip stack", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}&maxFrames=2&channel=C&clipIndex=0`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.ani.channel).toBe("C");
    expect(String(body.ani.layout)).toMatch(/multi-clip-C/);
    expect(body.ani.tracks[0].positions.length).toBeGreaterThan(0);
  }, 60000);

  test("skin-parse recovers 56-byte skinned vertices from NIKI body", async () => {
    const response = await fetch(`${base}/api/skin/parse?char=NIKI`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.member.toLowerCase()).toContain("niki");
    expect(body.skin.recordSize).toBe(56);
    expect(body.skin.vertexCount).toBeGreaterThan(100);
    expect(body.skin.runCount).toBeGreaterThan(0);
    expect(body.skin.layout.blendWeight.offset).toBe(0);
    expect(body.skin.layout.blendIndex.offset).toBe(16);
    expect(body.skin.boneIndexCount).toBeGreaterThan(5);
    expect(body.skin.runs[0].sample[0].weights.length).toBe(4);
    expect(body.skin.runs[0].sample[0].indices.length).toBe(4);
  }, 120000);

  test("skin-parse LUCY uses PlayerD body", async () => {
    const response = await fetch(`${base}/api/skin/parse?char=LUCY`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.archive).toContain("PlayerD");
    expect(body.skin.vertexCount).toBeGreaterThan(50);
  }, 120000);

  test("stage-scene lists World + Object layers for Emerald Beach compositor", async () => {
    const response = await fetch(
      `${base}/api/stage-scene?member=${encodeURIComponent("1_Emerald_Beach.set")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.scene.world.member).toMatch(/BF_Court01/i);
    expect(body.scene.objectCount).toBeGreaterThanOrEqual(1);
    expect(body.scene.objects[0].member || body.scene.objects[0].file).toBeTruthy();
  }, 60000);

  test("ANI parse fails cleanly on missing member", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NoSuch.ani")}`,
    );
    const body = await response.json();
    expect([200, 400, 500]).toContain(response.status);
    if (response.status === 200) {
      expect(body.ok).toBe(false);
    }
  }, 30000);

  test("bone-attach resolves Bone_Racket matrix for NIKI", async () => {
    const response = await fetch(
      `${base}/api/bone-attach?char=NIKI&attachBone=Bone_Racket`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.hasAttach).toBe(true);
    expect(body.attach.name).toMatch(/Racket/i);
    expect(body.attach.position.length).toBe(3);
    expect(body.attach.matrix4.length).toBe(16);
    expect(Math.abs(body.attach.position[0])).toBeGreaterThan(1);
    // Three.js / D3D column-major: translation lives at 12–14
    expect(body.matrixLayout).toBe("column-major");
    expect(body.threeJsFromArray).toBe(true);
    expect(body.attach.matrix4[12]).toBeCloseTo(body.attach.position[0], 5);
    expect(body.attach.matrix4[13]).toBeCloseTo(body.attach.position[1], 5);
    expect(body.attach.matrix4[14]).toBeCloseTo(body.attach.position[2], 5);
  }, 60000);

  test("bone-attach LUCY loads Lucy.dat under PlayerD (not Dhanpir)", async () => {
    const response = await fetch(
      `${base}/api/bone-attach?char=LUCY&attachBone=Bone_Racket`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.archive).toContain("PlayerD");
    expect(String(body.member).toLowerCase()).toContain("lucy");
  }, 60000);

  test("FTM export patches placement and round-trips parse", async () => {
    const response = await fetch(`${base}/api/ftm/export`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        archive: "Res/MapSet/FantaCastle.res",
        member: "FantaCastleOutSide.ftm",
        patches: [{ index: 0, x: 51, y: 13 }],
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.path).toMatch(/FantaCastleOutSide\.ftm$/);
    expect(body.sceneObjectCount).toBeGreaterThanOrEqual(1);
    expect(body.sceneObjects[0].x).toBe(51);
    expect(body.sceneObjects[0].y).toBe(13);
    expect(body.patchesApplied).toBe(1);
  }, 60000);

  test("FTM export rejects out-of-range placement index", async () => {
    const response = await fetch(`${base}/api/ftm/export`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        archive: "Res/MapSet/FantaCastle.res",
        member: "FantaCastleOutSide.ftm",
        patches: [{ index: 9999, x: 1, y: 1 }],
      }),
    });
    const body = await response.json();
    // structured failure, not crash
    expect([200, 400, 500]).toContain(response.status);
    if (response.status === 200) {
      expect(body.ok).toBe(false);
      expect(String(body.detail ?? body.error)).toMatch(/out of range|FTM/i);
    }
  }, 60000);

  test("bone-attach missing socket falls back gracefully", async () => {
    const response = await fetch(
      `${base}/api/bone-attach?char=NIKI&attachBone=NoSuchBone_XYZ`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.hasAttach).toBe(false);
    expect(body.attach).toBeNull();
  }, 60000);

  test("mesh parse exposes planar UVs and stage texture for BF_Court01", async () => {
    const response = await fetch(
      `${base}/api/mesh-studio/parse?archive=${encodeURIComponent("Res/Stage/Mesh01.res")}&member=${encodeURIComponent("BF_Court01.dat")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.mesh.hasUvs).toBe(true);
    expect(body.mesh.uvMode).toMatch(/planar|interleaved/);
    expect(body.mesh.uvs.length).toBe(body.mesh.vertexCount);
    const [u0, v0] = body.mesh.uvs[0] as number[];
    expect(u0).toBeGreaterThanOrEqual(0);
    expect(u0).toBeLessThanOrEqual(1);
    expect(v0).toBeGreaterThanOrEqual(0);
    expect(v0).toBeLessThanOrEqual(1);
    expect(body.mesh.texture).toBeDefined();
    expect(String(body.mesh.texture.member)).toMatch(/\.tex$/i);
  }, 120000);

  test("mesh studio texture endpoint returns PNG for BF_Court01 lawn", async () => {
    const response = await fetch(
      `${base}/api/mesh-studio/texture?meshMember=${encodeURIComponent("BF_Court01.dat")}`,
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("image/png");
    const bytes = new Uint8Array(await response.arrayBuffer());
    // PNG signature
    expect(bytes[0]).toBe(0x89);
    expect(bytes[1]).toBe(0x50);
    expect(bytes[2]).toBe(0x4e);
    expect(bytes[3]).toBe(0x47);
    expect(bytes.length).toBeGreaterThan(1000);
  }, 120000);

  test("mesh decode prefers solid stage geometry over UV/normal false runs for BF_Court01", async () => {
    // Prior multi-stride scorer rewarded ultra-flat s20 UV/normal channels → ~485 solid area, nearly invisible pad.
    const response = await fetch(
      `${base}/api/mesh-studio/parse?archive=${encodeURIComponent("Res/Stage/Mesh01.res")}&member=${encodeURIComponent("BF_Court01.dat")}&metaOnly=1`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.mesh.confidence).toBeDefined();
    expect(body.mesh.confidence.solidArea).toBeGreaterThan(10_000);
    expect(body.mesh.confidence.nonDegenerateTriangles).toBeGreaterThan(300);
    // Reject unit-vector / UV-channel silhouettes (Y extent ≈ 1 with tiny solid fill).
    const min = body.mesh.bounds.min as number[];
    const max = body.mesh.bounds.max as number[];
    const extent = max.map((v: number, i: number) => v - min[i]!);
    expect(Math.max(...extent)).toBeGreaterThan(50);
    expect(body.mesh.vertexCount).toBeGreaterThan(500);
  }, 120000);

  test("mesh parse exposes decode confidence diagnostics", async () => {
    const list = await fetch(`${base}/api/mesh-studio/list`).then((r) => r.json());
    const court =
      list.meshes.find((row: { member: string }) => row.member === "BF_Court01.dat") ??
      list.meshes[0];
    const response = await fetch(
      `${base}/api/mesh-studio/parse?archive=${encodeURIComponent(court.archive)}&member=${encodeURIComponent(court.member)}&metaOnly=1`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.mesh.confidence).toBeDefined();
    expect(typeof body.mesh.confidence.score).toBe("number");
    expect(body.mesh.confidence.score).toBeGreaterThan(0);
    expect(body.mesh.header).toBeDefined();
  }, 120000);

  test("effect slot fields return Ice_Smoke02 readout", async () => {
    const response = await fetch(`${base}/api/effects/slot-fields`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(String(body.fields.TexturePath).length).toBeGreaterThan(0);
    expect(body.fields.PQ_Quantity).toBeTruthy();
    expect(body.fields.SubTexCount).toBeTruthy();
    // After a soft build, the export archive slot should carry A_feather.
    const build = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(softPayload),
    }).then((r) => r.json());
    expect(build.ok).toBe(true);
    const exported = await fetch(
      `${base}/api/effects/slot-fields?particleArchive=${encodeURIComponent(build.particleArchive)}`,
    ).then((r) => r.json());
    expect(exported.ok).toBe(true);
    expect(String(exported.fields.TexturePath)).toContain("A_feather");
  }, 120000);

  test("playtest status reports install and launch readiness", async () => {
    const response = await fetch(`${base}/api/playtest/status`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(typeof body.ready).toBe("boolean");
    expect(typeof body.installPresent).toBe("boolean");
    expect(typeof body.launchScriptExists).toBe("boolean");
    expect(Array.isArray(body.checklist)).toBe(true);
    expect(body.checklist.length).toBeGreaterThan(0);
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
