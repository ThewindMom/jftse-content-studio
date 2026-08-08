import {
  mkdirSync,
  readdirSync,
  readFileSync,
  writeFileSync,
  existsSync,
  statSync,
} from "node:fs";
import { join, relative } from "node:path";
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

type SetupCheck = { id: string; ok: boolean; label: string };

function buildSetup(health: Record<string, unknown>) {
  const stockExists = existsSync(config.stockClient);
  const localExists = existsSync(config.localClient);
  const particleRes = Boolean(health.particleRes);
  const itemRes = Boolean(health.itemRes);
  const stageInfo = Boolean(health.stageInfo);
  const localParticle = existsSync(
    join(config.localClient, "Res/Effect/Particle.res"),
  );
  const installReady = localExists || Boolean(process.env.JFTSE_LOCAL_CLIENT);
  const checklist: SetupCheck[] = [
    {
      id: "jftse-root",
      ok: existsSync(config.jftseRoot),
      label: `JFTSE_ROOT → ${config.jftseRoot}`,
    },
    {
      id: "stock-client",
      ok: stockExists,
      label: `Stock client readable → ${config.stockClient}`,
    },
    {
      id: "particle-res",
      ok: particleRes,
      label: "Stock Particle.res available for soft exports",
    },
    {
      id: "item-res",
      ok: itemRes,
      label: "Stock Item.res available for racket catalog",
    },
    {
      id: "stage-info",
      ok: stageInfo,
      label: "Stage/Info.res available for Map Studio",
    },
    {
      id: "local-client",
      ok: installReady,
      label: installReady
        ? `Local install target → ${config.localClient}`
        : "Set JFTSE_LOCAL_CLIENT to an allowlisted local client path",
    },
    {
      id: "local-particle",
      ok: !installReady || localParticle || localExists,
      label: localParticle
        ? "Local client has Res/Effect/Particle.res"
        : "Local Particle.res will be created on first install",
    },
  ];
  const ready = checklist
    .filter((row) => row.id !== "local-particle")
    .every((row) => row.ok);
  return {
    ready,
    stockClient: config.stockClient,
    localClient: config.localClient,
    jftseRoot: config.jftseRoot,
    stockExists,
    localExists,
    particleRes,
    itemRes,
    stageInfo,
    installReady,
    checklist,
  };
}

type ExportRow = {
  kind: string;
  name: string;
  path: string;
  relativePath: string;
  bytes: number;
  mtimeMs: number;
};

function listExports(limit = 30): ExportRow[] {
  if (!existsSync(config.exportsDir)) return [];
  const rows: ExportRow[] = [];
  const top = readdirSync(config.exportsDir, { withFileTypes: true });
  for (const entry of top) {
    const full = join(config.exportsDir, entry.name);
    if (entry.isFile()) {
      const st = statSync(full);
      const kind = entry.name.startsWith("map-pack-")
        ? "map"
        : entry.name.startsWith("maps-")
          ? "map"
          : entry.name.includes("Particle")
            ? "effect"
            : "file";
      rows.push({
        kind,
        name: entry.name,
        path: full,
        relativePath: entry.name,
        bytes: st.size,
        mtimeMs: st.mtimeMs,
      });
      continue;
    }
    if (!entry.isDirectory()) continue;
    const kind = entry.name.startsWith("effect-")
      ? "effect"
      : entry.name.startsWith("mesh-")
        ? "mesh"
        : entry.name.startsWith("map")
          ? "map"
          : "other";
    for (const child of readdirSync(full, { withFileTypes: true })) {
      if (!child.isFile()) continue;
      const childPath = join(full, child.name);
      const st = statSync(childPath);
      rows.push({
        kind,
        name: child.name,
        path: childPath,
        relativePath: relative(config.exportsDir, childPath),
        bytes: st.size,
        mtimeMs: st.mtimeMs,
      });
    }
  }
  rows.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return rows.slice(0, Math.max(1, Math.min(limit, 100)));
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
          const setup = buildSetup(health);
          return {
            ok: true,
            ...health,
            port: config.port,
            localClient: config.localClient,
            stockClient: config.stockClient,
            launchHint: `cd ${join(config.jftseRoot, "FantaTennis-Local-Client")} && ./START-FANTA-TENNIS.sh`,
            setup,
          };
        }),
    },
    "/api/exports": {
      GET: (req) => {
        const url = new URL(req.url);
        const limit = Number(url.searchParams.get("limit") ?? "30");
        const kind = (url.searchParams.get("kind") ?? "").toLowerCase();
        let exports = listExports(Number.isFinite(limit) ? limit : 30);
        if (kind) {
          exports = exports.filter((row) => row.kind === kind);
        }
        return json({ ok: true, exports, count: exports.length });
      },
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
    "/api/mesh-studio/list": {
      GET: async () => safeBridge(() => runBridge(["mesh-list"])),
    },
    "/api/item-mesh/resolve": {
      GET: async (req) => {
        const url = new URL(req.url);
        const meshIndex = url.searchParams.get("meshIndex") ?? "";
        const char = url.searchParams.get("char") ?? "NIKI";
        if (!meshIndex) return bad("MESH_INDEX_REQUIRED");
        const metaOnly = url.searchParams.get("metaOnly") === "1";
        const args = [
          "item-mesh-resolve",
          "--mesh-index",
          meshIndex,
          "--char",
          char,
        ];
        if (metaOnly) args.push("--meta-only");
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/stage-set/decrypt": {
      GET: async (req) => {
        const url = new URL(req.url);
        const member = url.searchParams.get("member") ?? "1_Emerald_Beach.set";
        return safeBridge(() =>
          runBridge(["stage-set-decrypt", "--member", member]),
        );
      },
    },
    "/api/stage-scene": {
      GET: async (req) => {
        const url = new URL(req.url);
        const member = url.searchParams.get("member") ?? "1_Emerald_Beach.set";
        const listAll = url.searchParams.get("listAll") === "1";
        const args = ["stage-scene"];
        if (listAll) args.push("--list-all");
        else args.push("--member", member);
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/map-catalog": {
      GET: async () => safeBridge(() => runBridge(["map-catalog"])),
    },
    "/api/ftm/parse": {
      GET: async (req) => {
        const url = new URL(req.url);
        const archive = url.searchParams.get("archive") ?? "";
        const member = url.searchParams.get("member");
        if (!member) return bad("MEMBER_REQUIRED");
        const args = ["ftm-parse", "--member", member];
        if (archive) args.push("--archive", archive);
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/ftm/export": {
      POST: async (req) => {
        const body = (await req.json()) as {
          archive?: string;
          member?: string;
          patches?: unknown[];
        };
        const archive = body.archive?.trim() ?? "";
        const member = body.member?.trim() ?? "";
        if (!archive || !member) {
          return bad("ARCHIVE_AND_MEMBER_REQUIRED");
        }
        const outDir = join(config.exportsDir, `ftm-${Date.now()}`);
        const patches = Array.isArray(body.patches) ? body.patches : [];
        return safeBridge(() =>
          runBridge([
            "ftm-export",
            "--archive",
            archive,
            "--member",
            member,
            "--out-dir",
            outDir,
            "--patches",
            JSON.stringify(patches),
          ]),
        );
      },
    },
    "/api/ani/parse": {
      GET: async (req) => {
        const url = new URL(req.url);
        const archive = url.searchParams.get("archive");
        const member = url.searchParams.get("member");
        if (!archive || !member) return bad("ARCHIVE_AND_MEMBER_REQUIRED");
        const maxFrames = url.searchParams.get("maxFrames") ?? "8";
        const clipIndex = url.searchParams.get("clipIndex") ?? "0";
        const channel = url.searchParams.get("channel") ?? "A";
        const char = url.searchParams.get("char") ?? "";
        const motion = url.searchParams.get("motion") ?? "";
        const args = [
          "ani-parse",
          "--archive",
          archive,
          "--member",
          member,
          "--max-frames",
          maxFrames,
          "--clip-index",
          clipIndex,
          "--channel",
          channel,
        ];
        if (char.trim()) {
          args.push("--char", char.trim());
        }
        if (motion.trim()) {
          args.push("--motion", motion.trim());
        }
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/bone-attach": {
      GET: async (req) => {
        const url = new URL(req.url);
        const char = url.searchParams.get("char") ?? "NIKI";
        const attachBone =
          url.searchParams.get("attachBone") ?? "Bone_Racket";
        return safeBridge(() =>
          runBridge([
            "bone-attach",
            "--char",
            char,
            "--attach-bone",
            attachBone,
          ]),
        );
      },
    },
    "/api/skin/parse": {
      GET: async (req) => {
        const url = new URL(req.url);
        const char = url.searchParams.get("char") ?? "NIKI";
        const includeVertices =
          url.searchParams.get("includeVertices") === "1";
        const maxVertices = url.searchParams.get("maxVertices") ?? "2000";
        const args = ["skin-parse", "--char", char, "--max-vertices", maxVertices];
        if (includeVertices) args.push("--include-vertices");
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/mesh-studio/meta": {
      GET: async (req) => {
        const url = new URL(req.url);
        const archive = url.searchParams.get("archive");
        const member = url.searchParams.get("member");
        if (!archive || !member) return bad("ARCHIVE_AND_MEMBER_REQUIRED");
        return safeBridge(() =>
          runBridge(["mesh-meta", "--archive", archive, "--member", member]),
        );
      },
    },
    "/api/mesh-studio/parse": {
      GET: async (req) => {
        const url = new URL(req.url);
        const archive = url.searchParams.get("archive");
        const member = url.searchParams.get("member");
        if (!archive || !member) return bad("ARCHIVE_AND_MEMBER_REQUIRED");
        const metaOnly = url.searchParams.get("metaOnly") === "1";
        const args = ["mesh-parse", "--archive", archive, "--member", member];
        if (metaOnly) args.push("--meta-only");
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/mesh-studio/export": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const archive = String(body.archive ?? "");
        const member = String(body.member ?? "");
        if (!archive || !member) return bad("ARCHIVE_AND_MEMBER_REQUIRED");
        const outDir = join(config.exportsDir, `mesh-${Date.now()}`);
        return safeBridge(() =>
          runBridge([
            "mesh-export",
            "--archive",
            archive,
            "--member",
            member,
            "--out-dir",
            outDir,
          ]),
        );
      },
    },
    "/api/mesh-studio/transform": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const payloadPath = join(
          config.tmpDir,
          `mesh-transform-${crypto.randomUUID()}.json`,
        );
        const outDir = join(config.exportsDir, `mesh-edit-${Date.now()}`);
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge([
            "mesh-transform",
            "--payload",
            payloadPath,
            "--out-dir",
            outDir,
          ]),
        );
      },
    },
    "/api/mesh-studio/texture": {
      GET: async (req) => {
        const url = new URL(req.url);
        const meshMember = url.searchParams.get("meshMember") ?? "";
        const archive = url.searchParams.get("archive") ?? "";
        const member = url.searchParams.get("member") ?? "";
        if (!meshMember && (!archive || !member)) {
          return bad("MESH_MEMBER_OR_TEXTURE_REQUIRED");
        }
        const outDir = join(config.tmpDir, `mesh-tex-${crypto.randomUUID()}`);
        const args = ["mesh-texture", "--out-dir", outDir];
        if (meshMember) args.push("--mesh-member", meshMember);
        if (archive) args.push("--archive", archive);
        if (member) args.push("--member", member);
        try {
          const body = (await runBridge(args)) as {
            ok?: boolean;
            png?: string;
            error?: string;
            source?: string;
          };
          if (!body.ok || !body.png) {
            return bad(String(body.error ?? "TEXTURE_FAILED"));
          }
          return new Response(Bun.file(body.png), {
            headers: {
              "content-type": "image/png",
              "cache-control": "public, max-age=3600",
              "x-jftse-texture-source": body.source ?? "unknown",
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
    "/api/effects/slot-fields": {
      GET: async (req) => {
        const url = new URL(req.url);
        const particleArchive = url.searchParams.get("particleArchive") ?? "";
        const member = url.searchParams.get("member") ?? "Ice_Smoke02.set";
        const args = ["effect-slot-fields", "--member", member];
        if (particleArchive) {
          args.push("--particle-archive", particleArchive);
        }
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/playtest/status": {
      GET: async (req) => {
        const url = new URL(req.url);
        const exportArchive = url.searchParams.get("exportArchive") ?? "";
        const args = ["playtest-status"];
        if (exportArchive) {
          args.push("--export-archive", exportArchive);
        }
        return safeBridge(() => runBridge(args));
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
    "/api/equipment/pack": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const meshIndex = String(body.meshIndex ?? body.mesh_index ?? "");
        if (!meshIndex) return bad("MESH_INDEX_REQUIRED");
        const outDir = join(config.exportsDir, `equipment-pack-${Date.now()}`);
        const args = [
          "equipment-pack",
          "--mesh-index",
          meshIndex,
          "--char",
          String(body.char ?? "NIKI"),
          "--out-dir",
          outDir,
          "--desc",
          String(body.desc ?? body.name ?? ""),
          "--part",
          String(body.part ?? "Racket"),
          "--gold",
          String(body.gold ?? "0"),
        ];
        if (body.newIndex != null && String(body.newIndex)) {
          args.push("--new-index", String(body.newIndex));
        }
        if (body.productIndex != null && String(body.productIndex)) {
          args.push("--product-index", String(body.productIndex));
        }
        if (typeof body.dat === "string" && body.dat) {
          args.push("--dat", body.dat);
        }
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/client/install": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const targetClient = String(body.targetClient ?? config.localClient);
        const files = body.files;
        if (!Array.isArray(files) || files.length === 0) {
          return bad("FILES_REQUIRED");
        }
        const payloadPath = join(
          config.tmpDir,
          `client-install-${crypto.randomUUID()}.json`,
        );
        await Bun.write(payloadPath, JSON.stringify({ files }, null, 2));
        return safeBridge(() =>
          runBridge([
            "client-install",
            "--target-client",
            targetClient,
            "--payload",
            payloadPath,
          ]),
        );
      },
    },
    "/api/map-studio/create": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const payloadPath = join(
          config.tmpDir,
          `map-create-${crypto.randomUUID()}.json`,
        );
        const outFile = join(config.exportsDir, `map-create-${Date.now()}.sql`);
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge([
            "map-create",
            "--payload",
            payloadPath,
            "--out-file",
            outFile,
          ]),
        );
      },
    },
    "/api/stage-set/write": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const payloadPath = join(
          config.tmpDir,
          `stage-set-write-${crypto.randomUUID()}.json`,
        );
        const outDir = join(config.exportsDir, `stage-set-${Date.now()}`);
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge([
            "stage-set-write",
            "--payload",
            payloadPath,
            "--out-dir",
            outDir,
            "--member",
            String(body.member ?? "1_Emerald_Beach.set"),
          ]),
        );
      },
    },
    "/api/ftm/author": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const payloadPath = join(
          config.tmpDir,
          `ftm-author-${crypto.randomUUID()}.json`,
        );
        const outDir = join(config.exportsDir, `ftm-author-${Date.now()}`);
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge([
            "ftm-author",
            "--payload",
            payloadPath,
            "--out-dir",
            outDir,
            "--archive",
            String(body.archive ?? ""),
            "--member",
            String(body.member ?? ""),
          ]),
        );
      },
    },
    "/api/tex/encode": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const dds = String(body.dds ?? "");
        if (!dds) return bad("DDS_REQUIRED");
        const out = String(
          body.out ?? join(config.exportsDir, `tex-${Date.now()}.tex`),
        );
        return safeBridge(() =>
          runBridge(["tex-encode", "--dds", dds, "--out", out]),
        );
      },
    },
    "/api/mesh-studio/import-obj": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const archive = String(body.archive ?? "");
        const member = String(body.member ?? "");
        const obj = String(body.obj ?? "");
        if (!archive || !member || !obj) {
          return bad("ARCHIVE_MEMBER_OBJ_REQUIRED");
        }
        const out = String(
          body.out ??
            join(config.exportsDir, `mesh-obj-${Date.now()}`, member),
        );
        return safeBridge(() =>
          runBridge([
            "mesh-obj-import",
            "--archive",
            archive,
            "--member",
            member,
            "--obj",
            obj,
            "--out",
            out,
          ]),
        );
      },
    },
    "/api/mesh-studio/from-obj": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const obj = String(body.obj ?? "");
        if (!obj) return bad("OBJ_REQUIRED");
        const out = String(
          body.out ??
            join(config.exportsDir, `mesh-new-${Date.now()}`, "authored.dat"),
        );
        return safeBridge(() =>
          runBridge(["mesh-from-obj", "--obj", obj, "--out", out]),
        );
      },
    },
    "/api/eft/parse": {
      GET: async (req) => {
        const url = new URL(req.url);
        const path = url.searchParams.get("path") ?? "";
        if (!path) return bad("PATH_REQUIRED");
        return safeBridge(() => runBridge(["eft-parse", "--path", path]));
      },
    },
    "/api/ani/section-b-status": {
      GET: async (req) => {
        const url = new URL(req.url);
        const archive =
          url.searchParams.get("archive") ?? "Res/Player/PlayerA/AniA.res";
        const member = url.searchParams.get("member") ?? "NikiAniA.ani";
        const char = url.searchParams.get("char") ?? "NIKI";
        return safeBridge(() =>
          runBridge([
            "ani-section-b-status",
            "--archive",
            archive,
            "--member",
            member,
            "--char",
            char,
          ]),
        );
      },
    },
    "/api/content-pack/build": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const payloadPath = join(
          config.tmpDir,
          `content-pack-${crypto.randomUUID()}.json`,
        );
        const outDir = join(
          config.exportsDir,
          `content-pack-${Date.now()}`,
        );
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge([
            "content-pack-build",
            "--payload",
            payloadPath,
            "--out-dir",
            outDir,
          ]),
        );
      },
    },
    "/api/content-pack/install": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const targetClient = String(body.targetClient ?? config.localClient);
        const files = body.installPlan ?? body.files;
        if (!Array.isArray(files) || files.length === 0) {
          return bad("INSTALL_PLAN_REQUIRED");
        }
        const payloadPath = join(
          config.tmpDir,
          `content-pack-install-${crypto.randomUUID()}.json`,
        );
        await Bun.write(payloadPath, JSON.stringify({ files }, null, 2));
        const installed = await safeBridge(() =>
          runBridge([
            "client-install",
            "--target-client",
            targetClient,
            "--payload",
            payloadPath,
          ]),
        );
        // safeBridge returns Response - need raw bridge for chaining
        return installed;
      },
    },
    "/api/content-pack/playtest": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const targetClient = String(body.targetClient ?? config.localClient);
        const installPlan = body.installPlan;
        if (!Array.isArray(installPlan)) return bad("INSTALL_PLAN_REQUIRED");
        const payloadPath = join(
          config.tmpDir,
          `content-pack-playtest-${crypto.randomUUID()}.json`,
        );
        await Bun.write(
          payloadPath,
          JSON.stringify({ installPlan }, null, 2),
        );
        return safeBridge(() =>
          runBridge([
            "content-pack-playtest",
            "--target-client",
            targetClient,
            "--payload",
            payloadPath,
          ]),
        );
      },
    },
    "/api/content-pack/playtest-full": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const targetClient = String(body.targetClient ?? config.localClient);
        const payloadPath = join(
          config.tmpDir,
          `content-pack-playtest-full-${crypto.randomUUID()}.json`,
        );
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge([
            "content-pack-playtest-full",
            "--target-client",
            targetClient,
            "--payload",
            payloadPath,
          ]),
        );
      },
    },
    "/api/sql/apply": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        if (!body.path) return bad("PATH_REQUIRED");
        const payloadPath = join(
          config.tmpDir,
          `sql-apply-${crypto.randomUUID()}.json`,
        );
        await Bun.write(payloadPath, JSON.stringify(body, null, 2));
        return safeBridge(() =>
          runBridge(["sql-apply", "--payload", payloadPath]),
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
