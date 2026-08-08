import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import {
  chmodSync,
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  rmSync,
  symlinkSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const port = 4317;
const base = `http://127.0.0.1:${port}`;
const jftseRoot =
  process.env.JFTSE_ROOT ??
  "/home/thewind/Projects/00_Random_Coding/260705_fanta_tennis/JFTSE";
const stockClient = join(jftseRoot, ".jftse-client-linux/client");
const studioRoot = join(import.meta.dir, "..");
const artifactRoots = ["exports", "content-packs", ".tmp"].map((name) =>
  join(studioRoot, name),
);

let serverProc: ReturnType<typeof Bun.spawn> | null = null;
let disposableClient = "";
let initialArtifacts = new Map<string, Set<string>>();
let fakeMysqlDir = "";
let fakeMysqlArgs = "";
let fakeMysqlEnv = "";

async function postInstall(
  targetClient: string,
  files: Array<{ source: string; destRelative: string }>,
): Promise<{ response: Response; body: Record<string, unknown> }> {
  const response = await fetch(`${base}/api/client/install`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ targetClient, files }),
  });
  return {
    response,
    body: (await response.json()) as Record<string, unknown>,
  };
}

async function postSql(
  payload: Record<string, unknown>,
): Promise<{
  response: Response;
  body: {
    ok?: boolean;
    error?: string;
    dryRun?: boolean;
    audit?: {
      safe: boolean;
      insertCount: number;
      statementCount: number;
      tables: string[];
    };
  };
}> {
  const response = await fetch(`${base}/api/sql/apply`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return {
    response,
    body: (await response.json()) as {
      ok?: boolean;
      error?: string;
      dryRun?: boolean;
      audit?: {
        safe: boolean;
        insertCount: number;
        statementCount: number;
        tables: string[];
      };
    },
  };
}

async function writeExportSql(sql: string): Promise<string> {
  const path = join(
    studioRoot,
    "exports",
    `sql-policy-${Date.now()}-${crypto.randomUUID()}.sql`,
  );
  await Bun.write(path, sql);
  return path;
}

function snapshotArtifacts(): Map<string, Set<string>> {
  return new Map(
    artifactRoots.map((root) => [
      root,
      new Set(existsSync(root) ? readdirSync(root) : []),
    ]),
  );
}

async function waitForServerOutput(
  stream: ReadableStream<Uint8Array>,
  marker: string,
  timeoutMs: number,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let output = "";
  let timeout: Timer | undefined;
  try {
    await Promise.race([
      (async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          output += decoder.decode(value, { stream: true });
          if (output.includes(marker)) return;
        }
        throw new Error(`server exited before startup marker: ${output}`);
      })(),
      new Promise<never>((_, reject) => {
        timeout = setTimeout(
          () => reject(new Error(`server startup marker timed out: ${marker}`)),
          timeoutMs,
        );
      }),
    ]);
  } finally {
    if (timeout) clearTimeout(timeout);
    reader.releaseLock();
  }
}

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
  initialArtifacts = snapshotArtifacts();
  disposableClient = mkdtempSync(join(tmpdir(), "jftse-studio-client-"));
  fakeMysqlDir = mkdtempSync(join(tmpdir(), "jftse-studio-mysql-"));
  fakeMysqlArgs = join(fakeMysqlDir, "args.txt");
  fakeMysqlEnv = join(fakeMysqlDir, "env.txt");
  const fakeMysql = join(fakeMysqlDir, "mysql");
  await Bun.write(
    fakeMysql,
    `#!/bin/sh
printf '%s\\n' "$@" > "$JFTSE_TEST_MYSQL_ARGS"
if [ "$MYSQL_PWD" = "super-secret" ]; then
  printf 'password_set=yes\\n' > "$JFTSE_TEST_MYSQL_ENV"
else
  printf 'password_set=no\\n' > "$JFTSE_TEST_MYSQL_ENV"
fi
cat >/dev/null
`,
  );
  chmodSync(fakeMysql, 0o755);
  await Bun.write(join(disposableClient, "Res/Effect/.keep"), "");
  cpSync(
    join(stockClient, "Res/Effect/Particle.res"),
    join(disposableClient, "Res/Effect/Particle.res"),
  );

  serverProc = Bun.spawn(["bun", "run", "server/index.ts"], {
    cwd: studioRoot,
    env: {
      ...process.env,
      PORT: String(port),
      JFTSE_ROOT: jftseRoot,
      JFTSE_STOCK_CLIENT: stockClient,
      JFTSE_LOCAL_CLIENT: disposableClient,
      JFTSE_DATABASE_URL:
        "mysql://studio:super-secret@127.0.0.1:3306/fantasytennis",
      JFTSE_TEST_MYSQL_ARGS: fakeMysqlArgs,
      JFTSE_TEST_MYSQL_ENV: fakeMysqlEnv,
      PATH: `${fakeMysqlDir}:${process.env.PATH ?? ""}`,
    },
    stdout: "pipe",
    stderr: "pipe",
  });
  try {
    await waitForServerOutput(
      serverProc.stdout as ReadableStream<Uint8Array>,
      `jftse-content-studio listening on http://127.0.0.1:${port}`,
      20_000,
    );
  } catch (error) {
    serverProc.kill();
    await serverProc.exited;
    serverProc = null;
    throw error;
  }
});

afterAll(async () => {
  if (serverProc) {
    serverProc.kill();
    await serverProc.exited;
  }
  serverProc = null;
  if (disposableClient && existsSync(disposableClient)) {
    rmSync(disposableClient, { recursive: true, force: true });
  }
  if (fakeMysqlDir && existsSync(fakeMysqlDir)) {
    rmSync(fakeMysqlDir, { recursive: true, force: true });
  }
  for (const [root, before] of initialArtifacts) {
    if (!existsSync(root)) continue;
    for (const entry of readdirSync(root)) {
      if (!before.has(entry)) {
        rmSync(join(root, entry), { recursive: true, force: true });
      }
    }
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

  test("install containment rejects tmp-like target", async () => {
    const target = mkdtempSync("/var/tmp/jftse-looks-like-tmp-");
    const source = join(studioRoot, "exports", `containment-${Date.now()}.res`);
    await Bun.write(source, "generated");
    try {
      const { response, body } = await postInstall(target, [
        { source, destRelative: "Res/Script/Test.res" },
      ]);
      expect(response.status).toBe(400);
      expect(body.error).toBe("TARGET_NOT_ALLOWLISTED");
    } finally {
      rmSync(target, { recursive: true, force: true });
    }
  });

  test("install containment rejects export-prefix sibling target", async () => {
    const target = join(studioRoot, `exports-evil-client-${Date.now()}`);
    const source = join(studioRoot, "exports", `containment-${Date.now()}.res`);
    await Bun.write(source, "generated");
    try {
      const { response, body } = await postInstall(target, [
        { source, destRelative: "Res/Script/Test.res" },
      ]);
      expect(response.status).toBe(400);
      expect(body.error).toBe("TARGET_NOT_ALLOWLISTED");
    } finally {
      rmSync(target, { recursive: true, force: true });
    }
  });

  test("install containment rejects symlink alias to stock", async () => {
    const aliasRoot = mkdtempSync(join(tmpdir(), "jftse-stock-alias-"));
    const alias = join(aliasRoot, "client");
    symlinkSync(stockClient, alias, "dir");
    const source = join(studioRoot, "exports", `containment-${Date.now()}.res`);
    await Bun.write(source, "generated");
    try {
      const { response, body } = await postInstall(alias, [
        { source, destRelative: "Res/Script/Test.res" },
      ]);
      expect(response.status).toBe(400);
      expect(body.error).toBe("REFUSE_STOCK_CLIENT");
    } finally {
      rmSync(aliasRoot, { recursive: true, force: true });
    }
  });

  test("install containment rejects source outside exports", async () => {
    const { response, body } = await postInstall(disposableClient, [
      { source: "/etc/hosts", destRelative: "Res/Script/Hosts.res" },
    ]);
    expect(response.status).toBe(400);
    expect(body.error).toBe("SOURCE_OUTSIDE_EXPORTS");
  });

  test("install containment rejects symlink source inside exports", async () => {
    const source = join(studioRoot, "exports", `containment-link-${Date.now()}.res`);
    symlinkSync("/etc/hosts", source);
    const { response, body } = await postInstall(disposableClient, [
      { source, destRelative: "Res/Script/Hosts.res" },
    ]);
    expect(response.status).toBe(400);
    expect(body.error).toBe("SOURCE_SYMLINK");
  });

  for (const destRelative of [
    "../FantaTennis.exe",
    "/Res/Script/Absolute.res",
    "FantaTennis.exe",
    "Res/../jftse.dll",
  ]) {
    test(`install containment rejects destination ${destRelative}`, async () => {
      const source = join(studioRoot, "exports", `containment-${Date.now()}.res`);
      await Bun.write(source, "generated");
      const { response, body } = await postInstall(disposableClient, [
        { source, destRelative },
      ]);
      expect(response.status).toBe(400);
      expect(body.error).toBe("INVALID_DEST_PATH");
    });
  }

  test("install containment rejects destination symlink escape", async () => {
    const outside = mkdtempSync(join(tmpdir(), "jftse-install-escape-"));
    const segment = `Escape-${Date.now()}`;
    const link = join(disposableClient, "Res", segment);
    mkdirSync(join(disposableClient, "Res"), { recursive: true });
    symlinkSync(outside, link, "dir");
    const source = join(studioRoot, "exports", `containment-${Date.now()}.res`);
    await Bun.write(source, "generated");
    try {
      const { response, body } = await postInstall(disposableClient, [
        { source, destRelative: `Res/${segment}/Escaped.res` },
      ]);
      expect(response.status).toBe(400);
      expect(body.error).toBe("DEST_SYMLINK_ESCAPE");
      expect(existsSync(join(outside, "Escaped.res"))).toBe(false);
    } finally {
      rmSync(link, { recursive: true, force: true });
      rmSync(outside, { recursive: true, force: true });
    }
  });

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
    expect(String(body.ani.layout)).toMatch(/multi-clip|sequential-float3/);
    // Drive mode: quats only when extract confident; else hierarchical-fk
    expect(["quat", "hierarchical-fk", "position-only-fk"]).toContain(
      body.ani.driveMode,
    );
    expect(body.ani.sectionProbe.rotationHypothesis.recommendedDriveMode).toBeDefined();
    // Section B + tail encoding probes always present with scored candidates
    const bHyp = body.ani.sectionProbe.sectionBHypothesis;
    expect(bHyp.encodingProbe).toBeDefined();
    expect(Array.isArray(bHyp.encodingProbe.candidates)).toBe(true);
    expect(bHyp.encodingProbe.candidates.length).toBeGreaterThanOrEqual(8);
    expect(bHyp.encodingProbe.candidates.every((c: { name: string }) => c.name)).toBe(
      true,
    );
    // Phase / bitstream scorers for custom B packing
    const bNames = bHyp.encodingProbe.candidates.map((c: { name: string }) => c.name);
    expect(bNames).toContain("float4-unit-byte-phases");
    expect(bNames).toContain("bitstream-48bit-3x15-plus-index");
    // Phase1 sparse / keyframe / delta rotation hypotheses (not dense float4)
    expect(bNames).toContain("sparse-unit-run-harvest-phase1");
    expect(bNames).toContain("sparse-exact-nf-unit-runs");
    expect(bNames).toContain("float4-additive-delta-phase1");
    expect(bNames).toContain("float4-mul-delta-phase1");
    expect(bNames).toContain("window-unit-density-phase1");
    const sparseHarvest = bHyp.encodingProbe.candidates.find(
      (c: { name: string }) => c.name === "sparse-unit-run-harvest-phase1",
    );
    expect(sparseHarvest).toBeDefined();
    expect(typeof sparseHarvest.unitRatio).toBe("number");
    // Still not a confident rotation channel on Niki
    expect(sparseHarvest.viable).toBe(false);
    const tHyp = body.ani.sectionProbe.tailHypothesis;
    expect(tHyp.encodingProbe).toBeDefined();
    expect(Array.isArray(tHyp.encodingProbe.candidates)).toBe(true);
    expect(tHyp.encodingProbe.candidates.length).toBeGreaterThanOrEqual(4);
    if (body.ani.hasRotations) {
      expect(body.ani.driveMode).toBe("quat");
      expect(body.ani.tracks[0].hasRotations).toBe(true);
      expect(body.ani.sectionProbe.rotationHypothesis.confident).toBe(true);
    } else {
      expect(body.ani.driveMode).toBe("hierarchical-fk");
      expect(body.ani.tracks[0].hasRotations).toBe(false);
      expect(body.ani.sectionProbe.rotationHypothesis.confident).toBe(false);
      // Niki: no viable B/tail rotation encoding yet
      expect(bHyp.viableRotationEncoding).toBeNull();
      expect(tHyp.viableRotationEncoding).toBeNull();
    }
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
    // Client-decoder RE trail (static FantaTennis.exe; no stock client writes)
    const clientHyp = probe.clientDecoderHypothesis;
    expect(clientHyp).toBeDefined();
    expect(clientHyp.streamHeader.sizeMatch).toBe(true);
    expect(clientHyp.streamHeader.viable).toBe(true);
    expect(clientHyp.streamHeader.n0MinusN1).toBe(1290);
    expect(clientHyp.rotationChannel.encoding).toBe("float4");
    expect(clientHyp.rotationChannel.confidentExtract).toBe(false);
    expect(clientHyp.recommendedDriveMode).toBe("hierarchical-fk");
    expect(Array.isArray(clientHyp.runtimeChannels)).toBe(true);
    expect(clientHyp.runtimeChannels.some((c: { name: string }) => c.name === "float4")).toBe(
      true,
    );
    expect(clientHyp.vas.readFloat4xn).toMatch(/^0x/i);
    // Bulk cursor walk: sequential float3 clips + 129B motion name table
    const walk = clientHyp.bulkWalk;
    expect(walk).toBeDefined();
    expect(walk.ok).toBe(true);
    expect(walk.sequentialFloat3Clips).toBeGreaterThanOrEqual(16);
    expect(walk.motionNameCount).toBe(40);
    expect(walk.nameRecordBytes).toBe(129);
    expect(walk.motionNames[0].name).toMatch(/\.ani$/i);
    expect(walk.confidentExtract).toBe(false);
    expect(typeof walk.denseFloat4Scan.bestUnitRatio).toBe("number");
    expect(walk.denseFloat4Scan.bestUnitRatio).toBeLessThan(0.9);
    // Motion names surface on multi-clip / probe
    expect(Array.isArray(probe.motionNames)).toBe(true);
    expect(probe.motionNames.length).toBe(40);
    // Motion catalog binds name → clipIndex/offset for named multi-clip set
    const catalog = clientHyp.motionCatalog ?? probe.motionCatalog;
    expect(Array.isArray(catalog)).toBe(true);
    expect(catalog.length).toBe(40);
    expect(catalog[0].name).toMatch(/Rootidle\.ani/i);
    expect(catalog[0].clipIndex).toBe(0);
    expect(catalog[0].hasFloat3Clip).toBe(true);
    expect(typeof catalog[0].offset).toBe("number");
  }, 60000);

  test("ANI motion=RunForward.ani resolves clipIndex from name table", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}&maxFrames=2&motion=${encodeURIComponent("RunForward.ani")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.ani.motion).toMatch(/RunForward/i);
    expect(body.ani.clipIndex).toBe(1);
    expect(body.ani.tracks[0].positions.length).toBeGreaterThan(0);
    // without char/skeleton: no derived quats
    expect(body.ani.driveMode).toBe("hierarchical-fk");
    // Top-level motionCatalog for equipment UI selectors
    expect(Array.isArray(body.ani.motionCatalog)).toBe(true);
    expect(body.ani.motionCatalog.length).toBe(40);
    expect(body.ani.motionCatalog[1].name).toMatch(/RunForward/i);
    expect(body.ani.motionCatalog[1].clipIndex).toBe(1);
  }, 60000);

  test("ANI with char=NIKI derives unit quats → driveMode=quat", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}&maxFrames=2&char=NIKI&motion=${encodeURIComponent("RunForward.ani")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.ani.hasRotations).toBe(true);
    expect(body.ani.driveMode).toBe("quat");
    expect(body.ani.rotationSource).toBe("hierarchical-derived");
    expect(body.ani.sectionProbe.rotationHypothesis.confident).toBe(true);
    expect(body.ani.tracks[0].hasRotations).toBe(true);
    expect(body.ani.tracks[0].rotations?.length).toBeGreaterThan(0);
    const q = body.ani.tracks[0].rotations[0];
    const len = Math.sqrt(q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2);
    expect(len).toBeGreaterThan(0.95);
    expect(len).toBeLessThan(1.05);
  }, 90000);

  test("ANI motion unknown fails structured", async () => {
    const response = await fetch(
      `${base}/api/ani/parse?archive=${encodeURIComponent("Res/Player/PlayerA/AniA.res")}&member=${encodeURIComponent("NikiAniA.ani")}&motion=${encodeURIComponent("NoSuchMotion.ani")}`,
    );
    const body = await response.json();
    expect([200, 400, 500]).toContain(response.status);
    if (response.status === 200) {
      expect(body.ok).toBe(false);
      expect(String(body.error ?? body.detail)).toMatch(/MOTION|not found/i);
    }
  }, 30000);

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

  test("skin-parse includes ordered skeleton palette covering skin indices", async () => {
    const response = await fetch(
      `${base}/api/skin/parse?char=NIKI&includeVertices=1&maxVertices=64`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.skeleton).toBeDefined();
    expect(body.skeleton.recordSize).toBe(304);
    expect(body.skeleton.boneCount).toBeGreaterThanOrEqual(25);
    expect(body.skeleton.bones[0].index).toBe(0);
    expect(body.skeleton.bones[0].name).toMatch(/Bip01/i);
    expect(body.skeleton.bones[0].matrix4.length).toBe(16);
    expect(body.skeleton.matrixLayout).toBe("column-major");
    // Skin blend indices must fall inside the palette
    expect(body.skeletonCoversSkin).toBe(true);
    expect(body.skin.boneIndexMax).toBeLessThan(body.skeleton.boneCount);
    expect(Array.isArray(body.vertices)).toBe(true);
    expect(body.vertices.length).toBeGreaterThan(0);
    expect(body.vertices[0].indices.length).toBe(4);
    expect(body.vertices[0].weights.length).toBe(4);
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

  test("bone-attach returns ordered skeleton palette 0..N with parents", async () => {
    const response = await fetch(
      `${base}/api/bone-attach?char=NIKI&attachBone=Bone_Racket`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.skeleton.boneCount).toBeGreaterThanOrEqual(40);
    expect(body.skeleton.bones.length).toBe(body.skeleton.boneCount);
    expect(body.skeleton.bones[0].name).toBe("Bip01");
    expect(body.skeleton.bones[0].parent).toBeNull();
    // Contiguous indices 0..N-1
    body.skeleton.bones.forEach((b: { index: number }, i: number) => {
      expect(b.index).toBe(i);
    });
    const racket = body.skeleton.bones.find(
      (b: { name: string }) => /Racket/i.test(b.name),
    );
    expect(racket).toBeDefined();
    expect(racket.matrix4.length).toBe(16);
    expect(typeof racket.parentIndex === "number" || racket.parentIndex === null).toBe(
      true,
    );
    // API bones list mirrors palette order
    expect(body.bones[0].name).toBe(body.skeleton.bones[0].name);
    expect(body.bones[0].matrix4.length).toBe(16);
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
    expect(sql).toContain("M_Scenarios");
    expect(sql).toContain("Emerald Beach");
    expect(sql).toContain("1_Emerald_Beach.set");
    expect(sql).toContain("playTime=VALUES(playTime)");
    expect(sql).toContain("ON DUPLICATE KEY UPDATE");
  });

  test("map studio catalog exposes wiki S_Maps timing columns", async () => {
    const response = await fetch(`${base}/api/map-studio/catalog`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    const atlantis = body.maps.find((row: { name: string }) => row.name === "Atlantis");
    expect(atlantis).toBeDefined();
    expect(atlantis.bossPlayTime).toBe(5);
    expect(atlantis.playTime).toBe(8);
    expect(atlantis.triggerBossTime).toBe(4);
    expect(atlantis.breathTime).toBe(100);
    expect(atlantis.isBossStage).toBe(true);
    const scn = body.scenarios.find((row: { id: number }) => row.id === 1);
    expect(scn?.gameMode).toBe("GUARDIAN");
  });

  test("map studio export pack preserves seed timing and applies draft overrides", async () => {
    const response = await fetch(`${base}/api/map-studio/export-pack`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        mapIds: [11],
        includeGuardians: true,
        includeScenarios: true,
        draft: {
          name: "Atlantis Custom",
          isBossStage: true,
        },
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.scenarioDefCount).toBeGreaterThan(0);
    const sql = await Bun.file(body.path).text();
    expect(sql).toContain("Atlantis Custom");
    // Seed Atlantis: bossPlayTime=5, breathTime=100, playTime=8, triggerBossTime=4
    expect(sql).toMatch(
      /INSERT INTO S_Maps[\s\S]*VALUES\(11,\s*NOW\(6\),\s*NOW\(6\),\s*5,\s*100,\s*NULL,\s*1,\s*10,\s*'Atlantis Custom',\s*8,\s*4,\s*0\)/,
    );
    expect(sql).toContain("INSERT INTO M_Scenarios");
    expect(sql).toContain("gameMode=VALUES(gameMode)");
    expect(sql).toContain(
      "ON DUPLICATE KEY UPDATE side=VALUES(side), boss_guardian_id=VALUES(boss_guardian_id)",
    );
    expect(sql).toContain(
      "ON DUPLICATE KEY UPDATE scenario_id=VALUES(scenario_id), map_id=VALUES(map_id)",
    );
  });

  test("map sql bulk export includes relations and full S_Maps columns", async () => {
    const response = await fetch(`${base}/api/maps/export-sql`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        maps: [{ map: 2, name: "Twinkle Town Draft" }],
        includeRelations: true,
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    const sql = await Bun.file(body.path).text();
    expect(sql).toContain("Twinkle Town Draft");
    // Twinkle Town seed: bossPlayTime=10, playTime=15, triggerBossTime=10
    expect(sql).toMatch(/VALUES\(3,\s*NOW\(6\),\s*NOW\(6\),\s*10,\s*100,/);
    expect(sql).toContain(", 15, 10, 0)");
    expect(sql).toContain("Map_2_Scenarios");
    expect(sql).toContain("Guardian_2_Maps");
    expect(sql).toContain("M_Scenarios");
  });

  test("install containment accepts generated equipment with verified receipts", async () => {
    const packRes = await fetch(`${base}/api/equipment/pack`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        meshIndex: 214,
        char: "NIKI",
        desc: "API Test Racket",
      }),
    });
    const pack = await packRes.json();
    expect(packRes.status).toBe(200);
    expect(pack.ok).toBe(true);
    expect(pack.installPlan?.length).toBeGreaterThanOrEqual(2);
    expect(await Bun.file(pack.sql).text()).toContain("API Test Racket");
    expect(pack.catalog?.sizeMatch).toBe(true);

    const installRes = await fetch(`${base}/api/client/install`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        targetClient: disposableClient,
        files: pack.installPlan,
      }),
    });
    const installed = await installRes.json();
    expect(installRes.status).toBe(200);
    expect(installed.ok).toBe(true);
    for (const receipt of Object.values(installed.installed) as Array<{
      sourceSha256: string;
      installedSha256: string;
      matches: boolean;
    }>) {
      expect(receipt.sourceSha256).toMatch(/^[a-f0-9]{64}$/);
      expect(receipt.installedSha256).toBe(receipt.sourceSha256);
      expect(receipt.matches).toBe(true);
    }
  });

  test("map studio create emits greenfield S_Maps SQL", async () => {
    const response = await fetch(`${base}/api/map-studio/create`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        draft: {
          name: "API Custom Court",
          playTime: 200,
          breathTime: 100,
          description: "from test",
        },
        scenarioIds: [1],
        stageScript: "1_Emerald_Beach.set",
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.map.name).toBe("API Custom Court");
    const sql = await Bun.file(body.path).text();
    expect(sql).toContain("API Custom Court");
    expect(sql).toContain("INSERT INTO S_Maps");
    expect(sql).toContain("Map_2_Scenarios");
  });

  test("stage-set write encrypts and packages Info.res", async () => {
    const response = await fetch(`${base}/api/stage-set/write`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        member: "1_Emerald_Beach.set",
        fields: { WorldFile: "Res/Stage/Mesh01/BF_Court01.dat" },
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.sizeMatch).toBe(true);
    expect(existsSync(body.infoArchive)).toBe(true);
  });

  test("sql apply dry-run accepts generated map SQL", async () => {
    const create = await fetch(`${base}/api/map-studio/create`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        draft: { name: "SQL Dry Court", playTime: 90 },
        scenarioIds: [1],
      }),
    });
    const created = await create.json();
    expect(create.status).toBe(200);
    const { response: dry, body: dryBody } = await postSql({
      path: created.path,
      dryRun: true,
    });
    expect(dry.status).toBe(200);
    expect(dryBody.ok).toBe(true);
    expect(dryBody.dryRun).toBe(true);
    expect(dryBody.audit?.safe).toBe(true);
    expect(dryBody.audit?.insertCount).toBeGreaterThan(0);
    expect(dryBody.audit?.tables).toContain("s_maps");
  });

  test("sql apply rejects path outside generated exports", async () => {
    const { response, body } = await postSql({
      path: "/etc/hosts",
      dryRun: true,
    });
    expect(response.status).toBe(400);
    expect(body.error).toBe("SQL_OUTSIDE_EXPORTS");
  });

  test("sql apply rejects symlink inside generated exports", async () => {
    const path = join(
      studioRoot,
      "exports",
      `sql-policy-link-${Date.now()}.sql`,
    );
    symlinkSync("/etc/hosts", path);
    const { response, body } = await postSql({ path, dryRun: true });
    expect(response.status).toBe(400);
    expect(body.error).toBe("SQL_SYMLINK");
  });

  test("sql apply rejects caller database URL override", async () => {
    const path = await writeExportSql("INSERT INTO S_Maps (id) VALUES (1);");
    const { response, body } = await postSql({
      path,
      dryRun: false,
      databaseUrl: "mysql://attacker:secret@127.0.0.1/other",
    });
    expect(response.status).toBe(400);
    expect(body.error).toBe("DATABASE_URL_OVERRIDE_FORBIDDEN");
  });

  test("sql apply rejects caller delete override", async () => {
    const path = await writeExportSql("DELETE FROM S_Maps WHERE id = 1;");
    const { response, body } = await postSql({
      path,
      dryRun: true,
      allowDeletes: true,
    });
    expect(response.status).toBe(400);
    expect(body.error).toBe("SQL_DELETE_OVERRIDE_FORBIDDEN");
  });

  test("sql apply accepts only generated insert tables", async () => {
    const allowed = [
      "S_Product",
      "product",
      "S_Maps",
      "M_Scenarios",
      "Map_2_Scenarios",
      "Guardian_2_Maps",
    ];
    const path = await writeExportSql(
      allowed
        .map(
          (table, index) =>
            `INSERT INTO ${table} (id) VALUES (${index + 1}) ON DUPLICATE KEY UPDATE id = VALUES(id);`,
        )
        .join("\n"),
    );
    const { response, body } = await postSql({ path, dryRun: true });
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.audit?.insertCount).toBe(allowed.length);
    expect(body.audit?.tables).toEqual([
      "s_product",
      "product",
      "s_maps",
      "m_scenarios",
      "map_2_scenarios",
      "guardian_2_maps",
    ]);
  });

  for (const [label, sql, error] of [
    ["unknown table", "INSERT INTO mysql.user (Host) VALUES ('%');", "SQL_STATEMENT_NOT_ALLOWED"],
    ["update", "UPDATE S_Maps SET name = 'owned';", "SQL_STATEMENT_NOT_ALLOWED"],
    ["delete", "DELETE FROM S_Maps WHERE id = 1;", "SQL_STATEMENT_NOT_ALLOWED"],
    ["drop after insert", "INSERT INTO S_Maps (id) VALUES (1); DROP TABLE S_Maps;", "SQL_STATEMENT_NOT_ALLOWED"],
    ["block comment", "INSERT/**/INTO S_Maps (id) VALUES (1);", "SQL_PARSE_FAILED"],
    ["executable comment", "/*!50000 DROP TABLE S_Maps */;", "SQL_PARSE_FAILED"],
    ["unterminated quote", "INSERT INTO S_Maps (name) VALUES ('oops);", "SQL_PARSE_FAILED"],
    ["backslash escape", "INSERT INTO S_Maps (name) VALUES ('bad\\\\'quote');", "SQL_PARSE_FAILED"],
  ] as const) {
    test(`sql apply rejects ${label}`, async () => {
      const path = await writeExportSql(sql);
      const { response, body } = await postSql({ path, dryRun: true });
      expect(response.status).toBe(400);
      expect(body.error).toBe(error);
      expect(body.audit?.safe).toBe(false);
    });
  }

  test("sql apply strips line comments without treating quoted tokens as verbs", async () => {
    const path = await writeExportSql(`
      -- Generated by the studio
      INSERT INTO S_Maps (name, description)
      VALUES ('DROP TABLE is text', 'semi;colon');
    `);
    const { response, body } = await postSql({ path, dryRun: true });
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.audit?.statementCount).toBe(1);
    expect(body.audit?.tables).toEqual(["s_maps"]);
  });

  test("sql apply live mode uses configured client without exposing password", async () => {
    const path = await writeExportSql("INSERT INTO S_Maps (id) VALUES (99);");
    const response = await fetch(`${base}/api/sql/apply`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ path, dryRun: false }),
    });
    const raw = await response.text();
    const body = JSON.parse(raw) as {
      ok: boolean;
      applied: boolean;
      exitCode: number;
    };
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.applied).toBe(true);
    expect(body.exitCode).toBe(0);
    expect(await Bun.file(fakeMysqlEnv).text()).toBe("password_set=yes\n");
    expect(await Bun.file(fakeMysqlArgs).text()).toBe(
      "-h\n127.0.0.1\n-P\n3306\n-u\nstudio\nfantasytennis\n",
    );
    expect(raw).not.toContain("super-secret");
    expect(raw).not.toContain("MYSQL_PWD");
  });

  test("content pack playtest-full returns checklist", async () => {
    const buildRes = await fetch(`${base}/api/content-pack/build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: "playtest-full",
        equipment: { meshIndex: 214, char: "NIKI", desc: "PF" },
        map: { draft: { name: "PF Map" }, scenarioIds: [1] },
      }),
    });
    const pack = await buildRes.json();
    expect(pack.ok).toBe(true);
    await fetch(`${base}/api/client/install`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        targetClient: disposableClient,
        files: pack.installPlan,
      }),
    });
    const full = await fetch(`${base}/api/content-pack/playtest-full`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        targetClient: disposableClient,
        installPlan: pack.installPlan,
        sqlPath: pack.parts?.map?.sql,
      }),
    });
    const body = await full.json();
    expect(full.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.ready).toBe(true);
    expect(body.checklist.length).toBeGreaterThan(2);
    expect(body.checklist.some((c: { id: string }) => c.id === "sql-dry-run")).toBe(
      true,
    );
  });

  test("content pack builds equipment+map and installs + playtest ready", async () => {
    const buildRes = await fetch(`${base}/api/content-pack/build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: "ulw-product-pack",
        equipment: {
          meshIndex: 214,
          char: "NIKI",
          desc: "ULW Pack Racket",
        },
        map: {
          draft: { name: "ULW Pack Court", playTime: 120, breathTime: 100 },
          scenarioIds: [1],
          stageScript: "1_Emerald_Beach.set",
        },
        ftm: {
          archive: "Res/MapSet/FantaCastle.res",
          member: "FantaCastleOutSide.ftm",
          patches: [{ index: 0, x: 7, y: 8 }],
        },
      }),
    });
    const pack = await buildRes.json();
    expect(buildRes.status).toBe(200);
    expect(pack.ok).toBe(true);
    expect(pack.installPlan?.length).toBeGreaterThanOrEqual(2);
    expect(pack.parts?.equipment?.sql).toBeTruthy();
    expect(pack.parts?.map?.sql).toBeTruthy();
    expect(pack.parts?.ftm?.archive).toBeTruthy();

    const installRes = await fetch(`${base}/api/client/install`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        targetClient: disposableClient,
        files: pack.installPlan,
      }),
    });
    const installed = await installRes.json();
    expect(installRes.status).toBe(200);
    expect(installed.ok).toBe(true);

    const playRes = await fetch(`${base}/api/content-pack/playtest`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        targetClient: disposableClient,
        installPlan: pack.installPlan,
      }),
    });
    const play = await playRes.json();
    expect(playRes.status).toBe(200);
    expect(play.ready).toBe(true);
    expect(play.passed).toBe(play.total);
  });

  test("item mesh resolve exposes multi-material silhouette stems", async () => {
    const response = await fetch(
      `${base}/api/item-mesh/resolve?meshIndex=214&char=NIKI&metaOnly=1`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.silhouette?.stemCount).toBeGreaterThan(0);
    expect(Array.isArray(body.silhouette?.stems)).toBe(true);
    expect(body.hasMultiMaterial === true || body.equipmentMaterialTable != null).toBe(
      true,
    );
  });

  test("ftm tile paint sets layer cell", async () => {
    const response = await fetch(`${base}/api/ftm/author`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        archive: "Res/MapSet/FantaCastle.res",
        member: "FantaCastleOutSide.ftm",
        tilePaint: {
          layerIndex: 0,
          cells: [{ x: 0, y: 0, value: 1 }],
        },
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(existsSync(body.path)).toBe(true);
  });

  test("mesh-from-obj authors new topology studio DAT", async () => {
    const objPath = join(disposableClient, "tiny.obj");
    await Bun.write(
      objPath,
      ["v 0 0 0", "v 2 0 0", "v 0 2 0", "v 0 0 2", "f 1 2 3", "f 1 3 4"].join("\n"),
    );
    const response = await fetch(`${base}/api/mesh-studio/from-obj`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ obj: objPath }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.vertexCount).toBe(4);
    expect(body.triangleCount).toBe(2);
    expect(existsSync(body.path)).toBe(true);
  });

  test("eft parse returns header for Atlantis bubble", async () => {
    const response = await fetch(
      `${base}/api/eft/parse?path=${encodeURIComponent("Res/Stage/Mesh11/EF_Atlantis_Bubble01.Eft")}`,
    );
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.byteLength).toBeGreaterThan(1000);
    expect(body.sectionA).toBeGreaterThan(0);
  });

  test("ani section-b status is honest about float4 non-viability", async () => {
    const response = await fetch(`${base}/api/ani/section-b-status`);
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.onDiskDenseFloat4.confident).toBe(false);
    expect(body.sectionB.viable).toBe(false);
    expect(body.productionDrive.rotationSource).toBe("hierarchical-derived");
    expect(body.streamHeader.fileSize).toBeGreaterThan(0);
  });

  test("ftm author blocked tile paint export", async () => {
    const response = await fetch(`${base}/api/ftm/author`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        archive: "Res/MapSet/FantaCastle.res",
        member: "FantaCastleOutSide.ftm",
        blockedTiles: [
          { x: 1, y: 1 },
          { x: 2, y: 2 },
        ],
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.blockedTileCount).toBe(2);
    expect(existsSync(body.path)).toBe(true);
  });

  test("ftm author add placement and refuse stock install", async () => {
    const authorRes = await fetch(`${base}/api/ftm/author`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        archive: "Res/MapSet/FantaCastle.res",
        member: "FantaCastleOutSide.ftm",
        add: [
          {
            prefabIndex: 0,
            x: 3,
            y: 4,
            scaleHeight: 1,
            scaleWidth: 1,
            rotationY: 0,
            rotationX: 0,
          },
        ],
      }),
    });
    const author = await authorRes.json();
    expect(authorRes.status).toBe(200);
    expect(author.ok).toBe(true);
    expect(author.sceneObjectCount).toBeGreaterThanOrEqual(1);
    expect(existsSync(author.archive)).toBe(true);

    const refuse = await fetch(`${base}/api/client/install`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        targetClient: stockClient,
        files: [
          {
            source: author.archive,
            destRelative: "Res/MapSet/FantaCastle.res",
          },
        ],
      }),
    });
    const refused = await refuse.json();
    expect(refused.ok).toBe(false);
    expect(refused.error).toBe("REFUSE_STOCK_CLIENT");
  });
});
