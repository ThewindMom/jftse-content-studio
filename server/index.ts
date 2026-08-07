import {
  mkdirSync,
  readdirSync,
  readFileSync,
  writeFileSync,
  existsSync,
} from "node:fs";
import { join } from "node:path";
import index from "../web/index.html";
import { buildEffect, installEffect, runBridge } from "./bridge.ts";
import { config } from "./config.ts";
import { EFFECT_PRESETS } from "./presets.ts";

mkdirSync(config.exportsDir, { recursive: true });
mkdirSync(config.packsDir, { recursive: true });
mkdirSync(config.tmpDir, { recursive: true });
mkdirSync(join(config.tmpDir, "atlas"), { recursive: true });

function json(data: unknown, status = 200): Response {
  return Response.json(data, { status });
}

function bad(error: string, status = 400): Response {
  return json({ ok: false, error }, status);
}

async function safeBridge(
  work: () => Promise<Record<string, unknown>>,
): Promise<Response> {
  try {
    const result = await work();
    if (result.ok === false) {
      return bad(String(result.error ?? "BRIDGE_FAILED"));
    }
    return json(result);
  } catch (error) {
    return json(
      {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      },
      500,
    );
  }
}

const server = Bun.serve({
  port: config.port,
  routes: {
    "/": index,
    "/api/health": {
      GET: async () =>
        safeBridge(async () => {
          const health = await runBridge(["health"]);
          return {
            ok: true,
            ...health,
            port: config.port,
            localClient: config.localClient,
            stockClient: config.stockClient,
            launchHint: `cd ${join(config.jftseRoot, "FantaTennis-Local-Client")} && ./START-FANTA-TENNIS.sh`,
          };
        }),
    },
    "/api/presets": {
      GET: () => json({ presets: EFFECT_PRESETS }),
    },
    "/api/atlases": {
      GET: async (req) => {
        const url = new URL(req.url);
        const limit = url.searchParams.get("limit") ?? "0";
        const q = (url.searchParams.get("q") ?? "").toLowerCase();
        const result = await runBridge(["list-atlases", "--limit", limit]);
        const atlases = Array.isArray(result.atlases) ? result.atlases : [];
        const filtered = q
          ? atlases.filter((entry) => {
              const row = entry as Record<string, unknown>;
              return JSON.stringify(row).toLowerCase().includes(q);
            })
          : atlases;
        return json({ ...result, atlases: filtered, count: filtered.length });
      },
    },
    "/api/atlases/preview": {
      GET: async (req) => {
        const url = new URL(req.url);
        const archive = url.searchParams.get("archive");
        const member = url.searchParams.get("member");
        if (!archive || !member) {
          return bad("ARCHIVE_AND_MEMBER_REQUIRED");
        }
        const safeArchive = archive.replace(/[^A-Za-z0-9._-]/g, "_");
        const safeMember = member.replace(/[^A-Za-z0-9._-]/g, "_");
        const output = join(
          config.tmpDir,
          "atlas",
          `${safeArchive}__${safeMember}.png`,
        );
        try {
          if (!existsSync(output)) {
            await runBridge([
              "atlas-preview",
              "--archive",
              archive,
              "--member",
              member,
              "--output",
              output,
            ]);
          }
          const file = Bun.file(output);
          return new Response(file, {
            headers: {
              "content-type": "image/png",
              "cache-control": "public, max-age=3600",
            },
          });
        } catch (error) {
          return json(
            {
              ok: false,
              error: error instanceof Error ? error.message : String(error),
            },
            500,
          );
        }
      },
    },
    "/api/items": {
      GET: async (req) => {
        const url = new URL(req.url);
        const part = url.searchParams.get("part") ?? "RACKET";
        const limit = url.searchParams.get("limit") ?? "80";
        const q = (url.searchParams.get("q") ?? "").toLowerCase();
        const result = await runBridge([
          "list-items",
          "--part",
          part,
          "--limit",
          limit,
        ]);
        const items = Array.isArray(result.items) ? result.items : [];
        const filtered = q
          ? items.filter((entry) => {
              const row = entry as Record<string, unknown>;
              return JSON.stringify(row).toLowerCase().includes(q);
            })
          : items;
        return json({ items: filtered, count: filtered.length });
      },
    },
    "/api/maps": {
      GET: async () => safeBridge(() => runBridge(["list-maps"])),
    },
    "/api/maps/export-sql": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const payloadPath = join(
          config.tmpDir,
          `maps-${crypto.randomUUID()}.json`,
        );
        const outFile = join(
          config.exportsDir,
          `maps-${Date.now()}.sql`,
        );
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge([
            "export-map-sql",
            "--payload",
            payloadPath,
            "--out-file",
            outFile,
          ]),
        );
      },
    },
    "/api/map-studio/catalog": {
      GET: async () => safeBridge(() => runBridge(["map-studio-catalog"])),
    },
    "/api/map-studio/validate": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const stageScript = String(body.stageScript ?? "");
        if (!stageScript) return bad("STAGE_SCRIPT_REQUIRED");
        return safeBridge(() =>
          runBridge(["map-studio-validate", "--stage-script", stageScript]),
        );
      },
    },
    "/api/map-studio/export-pack": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const payloadPath = join(
          config.tmpDir,
          `map-pack-${crypto.randomUUID()}.json`,
        );
        const outFile = join(
          config.exportsDir,
          `map-pack-${Date.now()}.sql`,
        );
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge([
            "map-studio-export-pack",
            "--payload",
            payloadPath,
            "--out-file",
            outFile,
          ]),
        );
      },
    },
    "/api/effects/preview-build": {
      POST: async (req) => {
        let payload: Record<string, unknown>;
        try {
          payload = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        return safeBridge(() => buildEffect(payload));
      },
    },
    "/api/effects/install": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const particleArchive = String(body.particleArchive ?? "");
        const targetClient = String(body.targetClient ?? config.localClient);
        if (!particleArchive) {
          return bad("PARTICLE_ARCHIVE_REQUIRED");
        }
        return safeBridge(() =>
          installEffect({
            particleArchive,
            targetClient,
            itemArchive:
              typeof body.itemArchive === "string" ? body.itemArchive : undefined,
            effectArchive:
              typeof body.effectArchive === "string"
                ? body.effectArchive
                : undefined,
          }),
        );
      },
    },
    "/api/packs": {
      GET: async () => {
        const files = readdirSync(config.packsDir).filter((name) =>
          name.endsWith(".json"),
        );
        const packs = files.map((name) => {
          const raw = readFileSync(join(config.packsDir, name), "utf8");
          return { file: name, ...(JSON.parse(raw) as Record<string, unknown>) };
        });
        return json({ packs });
      },
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const name = String(body.name ?? `pack-${Date.now()}`).replace(
          /[^a-zA-Z0-9._-]/g,
          "_",
        );
        const path = join(config.packsDir, `${name}.json`);
        const pack = {
          name,
          version: 4,
          savedAt: new Date().toISOString(),
          step: body.step ?? null,
          item: body.item ?? null,
          effect: body.effect ?? null,
          map: body.map ?? null,
          stageScript: body.stageScript ?? null,
          export: body.export ?? null,
          notes: body.notes ?? "",
        };
        writeFileSync(path, JSON.stringify(pack, null, 2));
        return json({ ok: true, path, pack });
      },
    },
    "/api/packs/:name": {
      GET: (req) => {
        const name = String(req.params.name ?? "").replace(/[^a-zA-Z0-9._-]/g, "");
        if (!name) return bad("PACK_NAME_REQUIRED");
        const file = name.endsWith(".json") ? name : `${name}.json`;
        const path = join(config.packsDir, file);
        if (!existsSync(path)) return bad("PACK_NOT_FOUND", 404);
        const pack = JSON.parse(readFileSync(path, "utf8")) as Record<
          string,
          unknown
        >;
        return json({ ok: true, file, pack });
      },
    },
    "/api/workflow": {
      GET: async () =>
        json({
          steps: [
            {
              id: "item",
              title: "Pick a base racket",
              detail: "Start from a stock item so mesh/UV stay valid.",
            },
            {
              id: "effect",
              title: "Tune the aura",
              detail: "Choose a preset, atlas, and emitter values.",
            },
            {
              id: "export",
              title: "Build & verify",
              detail: "Fixed-size Particle.res with isolation checks.",
            },
            {
              id: "install",
              title: "Install to local client",
              detail: "Never writes the stock client.",
            },
            {
              id: "playtest",
              title: "Launch & check Equipment",
              detail: "Browser preview is approximate; game is authority.",
            },
          ],
          presets: EFFECT_PRESETS.map((preset) => ({
            id: preset.id,
            name: preset.name,
            summary: preset.summary,
          })),
          launchHint: `cd ${join(config.jftseRoot, "FantaTennis-Local-Client")} && ./START-FANTA-TENNIS.sh`,
        }),
    },
  },
  development: {
    hmr: true,
    console: true,
  },
});

process.stdout.write(
  `jftse-content-studio listening on http://127.0.0.1:${server.port}\n`,
);
