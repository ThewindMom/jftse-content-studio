import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { join } from "node:path";

const port = 4317;
const base = `http://127.0.0.1:${port}`;
let serverProc: ReturnType<typeof Bun.spawn> | null = null;

beforeAll(async () => {
  serverProc = Bun.spawn(["bun", "run", "server/index.ts"], {
    cwd: join(import.meta.dir, ".."),
    env: {
      ...process.env,
      PORT: String(port),
      JFTSE_ROOT:
        process.env.JFTSE_ROOT ??
        "/home/thewind/Projects/00_Random_Coding/260705_fanta_tennis/JFTSE",
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
});

describe("content studio API", () => {
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

  test("soft effect build exports particle archive", async () => {
    const response = await fetch(`${base}/api/effects/preview-build`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
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
      }),
    });
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(typeof body.particleArchive).toBe("string");
    const file = Bun.file(body.particleArchive);
    expect(await file.exists()).toBe(true);
  }, 120000);
});
