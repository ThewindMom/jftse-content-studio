import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import index from "../web/index.html";
import { buildEffect, installEffect, runBridge } from "./bridge.ts";
import { config } from "./config.ts";

mkdirSync(config.exportsDir, { recursive: true });
mkdirSync(config.packsDir, { recursive: true });
mkdirSync(config.tmpDir, { recursive: true });

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
          };
        }),
    },
    "/api/atlases": {
      GET: async (req) => {
        const url = new URL(req.url);
        const limit = url.searchParams.get("limit") ?? "0";
        return safeBridge(() => runBridge(["list-atlases", "--limit", limit]));
      },
    },
    "/api/items": {
      GET: async (req) => {
        const url = new URL(req.url);
        const part = url.searchParams.get("part") ?? "RACKET";
        const limit = url.searchParams.get("limit") ?? "40";
        return safeBridge(() =>
          runBridge(["list-items", "--part", part, "--limit", limit]),
        );
      },
    },
    "/api/maps": {
      GET: async () => safeBridge(() => runBridge(["list-maps"])),
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
          return { name, ...(JSON.parse(raw) as Record<string, unknown>) };
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
          version: 3,
          savedAt: new Date().toISOString(),
          item: body.item ?? null,
          effect: body.effect ?? null,
          map: body.map ?? null,
          export: body.export ?? null,
        };
        writeFileSync(path, JSON.stringify(pack, null, 2));
        return json({ ok: true, path, pack });
      },
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
