import {
  mkdirSync,
  readdirSync,
  readFileSync,
  writeFileSync,
  existsSync,
  rmSync,
  statSync,
} from "node:fs";
import { join, relative } from "node:path";
import index from "../web/index.html";
import mapStudio from "../web/map-studio.html";
import { twinkleScene, twinkleFile, twinkleDraft, twinkleExport, twinkleClient } from "./twinkleStudio.ts";
import {
  BridgeError,
  buildEffect,
  installClientFiles,
  runBridge,
  runBridgeWithPayload,
  shutdownBridgeProcesses,
} from "./bridge.ts";
import { BridgeSchedulerBusyError } from "./bridgeScheduler.ts";
import { buildCompatibilityReport } from "./compatibility.ts";
import { config } from "./config.ts";
import { runManagedClient } from "./clientHarness.ts";
import { runClientHarnessPipeline } from "./clientHarnessPipeline.ts";
import { managedHarnessBuildPayload } from "./clientHarnessPayload.ts";
import {
  clearManagedProfiles,
  createManagedProfile,
  listManagedProfiles,
  loadManagedProfile,
  type ManagedProfileMode,
} from "./clientProfileStore.ts";
import { buildRuntimeMapPackage } from "./mapScenePackage.ts";
import {
  packageEquipmentCreator,
  validateEquipmentPackageRequest,
} from "./equipmentCreatorPackage.ts";
import {
  auditEquipmentPackage,
  installEquipmentPackage,
  preflightEquipmentPackage,
} from "./equipmentManagedWorkflow.ts";
import {
  archiveMemberName,
  clientRelativePath,
  exportOutputPath,
  PathPolicyError,
  trustedReadPath,
  trustedRegularFilePath,
} from "./pathPolicy.ts";
import { EFFECT_PRESETS } from "./presets.ts";
import { parseMapScene } from "../web/mapSceneDocument.ts";
import {
  parseBoundedInteger,
  readJsonObject,
  RequestPolicyError,
} from "./requestPolicy.ts";
import { developmentServeOptions } from "./serverMode.ts";

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

function operationalError(error: unknown): Response | null {
  if (error instanceof RequestPolicyError) return bad(error.code, error.status);
  if (error instanceof BridgeSchedulerBusyError) return bad(error.code, error.status);
  if (error instanceof BridgeError) {
    return json(
      { ok: false, error: error.code, detail: error.detail },
      error.code === "BRIDGE_TIMEOUT" ? 504 : 500,
    );
  }
  return null;
}

function checkedInteger(
  raw: string | null,
  policy: Parameters<typeof parseBoundedInteger>[1],
): { value: string } | { response: Response } {
  try {
    return { value: String(parseBoundedInteger(raw, policy)) };
  } catch (error) {
    const response = operationalError(error);
    if (response) return { response };
    throw error;
  }
}

function checkedPath<T>(work: () => T): { value: T } | { response: Response } {
  try {
    return { value: work() };
  } catch (error) {
    if (error instanceof PathPolicyError) return { response: bad(error.code) };
    throw error;
  }
}

const trustedStudioReadRoots = [
  config.exportsDir,
  config.stockClient,
  config.localClient,
];

type SetupCheck = { id: string; ok: boolean; label: string };

function buildSetup(
  health: Record<string, unknown>,
  preflight: Record<string, unknown>,
) {
  const stockExists = existsSync(config.stockClient);
  const localExists = existsSync(config.localClient);
  const particleRes = Boolean(health.particleRes);
  const itemRes = Boolean(health.itemRes);
  const stageInfo = Boolean(health.stageInfo);
  const localParticle = existsSync(
    join(config.localClient, "Res/Effect/Particle.res"),
  );
  const installReady = localExists || Boolean(process.env.JFTSE_LOCAL_CLIENT);
  const launchReady = preflight.launchScriptExists === true;
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
    {
      id: "launch-script",
      ok: launchReady,
      label: launchReady
        ? `Executable launch script → ${String(preflight.launchScript)}`
        : "Executable local-client launch script not found",
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
    launchReady,
    launchCommand: preflight.launchCommand ?? null,
    manualHandoff: preflight.manualHandoff ?? null,
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
      return json(result, 400);
    }
    return json(result);
  } catch (error) {
    const response = operationalError(error);
    if (response) return response;
    return json(
      {
        ok: false,
        error: "BRIDGE_FAILED",
      },
      500,
    );
  }
}

const server = Bun.serve({
  hostname: "127.0.0.1",
  port: config.port,
  idleTimeout: 120,
  routes: {
    "/": index,
    "/map-studio": mapStudio,
    "/api/twinkle/scene": { GET: twinkleScene },
    "/api/twinkle/file": { GET: twinkleFile },
    "/api/twinkle/draft": { GET: twinkleDraft, PUT: twinkleDraft },
    "/api/twinkle/export": { POST: twinkleExport },
    "/api/twinkle/client": { GET: twinkleClient, POST: twinkleClient },
    "/api/health": {
      GET: async () =>
        safeBridge(async () => {
          const [health, preflight] = await Promise.all([
            runBridge(["health"]),
            runBridge(["playtest-status"]),
          ]);
          const setup = buildSetup(health, preflight);
          return {
            ok: true,
            ...health,
            port: config.port,
            localClient: config.localClient,
            stockClient: config.stockClient,
            launchHint: preflight.launchCommand ?? null,
            preflight,
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
    "/api/compatibility": {
      GET: async (req) =>
        new URL(req.url).search
          ? bad("COMPATIBILITY_QUERY_FORBIDDEN")
          : json(await buildCompatibilityReport()),
    },
    "/api/atlases": {
      GET: async (req) => {
        const url = new URL(req.url);
        const limit = checkedInteger(url.searchParams.get("limit"), {
          name: "limit",
          minimum: 1,
          maximum: 500,
          fallback: 200,
        });
        if ("response" in limit) return limit.response;
        const q = (url.searchParams.get("q") ?? "").toLowerCase();
        const result = await runBridge(["list-atlases", "--limit", limit.value]);
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
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: clientRelativePath(member),
        }));
        if ("response" in paths) return paths.response;
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
        const limit = checkedInteger(url.searchParams.get("limit"), {
          name: "limit",
          minimum: 1,
          maximum: 500,
          fallback: 80,
        });
        if ("response" in limit) return limit.response;
        const q = (url.searchParams.get("q") ?? "").toLowerCase();
        const result = await runBridge([
          "list-items",
          "--part",
          part,
          "--limit",
          limit.value,
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
        const outFile = join(
          config.exportsDir,
          `maps-${Date.now()}.sql`,
        );
        return safeBridge(() =>
          runBridgeWithPayload("maps", body, (payloadPath) => [
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
        const rawMeshIndex = url.searchParams.get("meshIndex");
        const char = url.searchParams.get("char") ?? "NIKI";
        if (!rawMeshIndex) return bad("MESH_INDEX_REQUIRED");
        const meshIndex = checkedInteger(rawMeshIndex, {
          name: "meshIndex",
          minimum: 0,
          maximum: 1_000_000,
        });
        if ("response" in meshIndex) return meshIndex.response;
        const metaOnly = url.searchParams.get("metaOnly") === "1";
        const args = [
          "item-mesh-resolve",
          "--mesh-index",
          meshIndex.value,
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
        const path = checkedPath(() => clientRelativePath(member));
        if ("response" in path) return path.response;
        return safeBridge(() =>
          runBridge(["stage-set-decrypt", "--member", path.value]),
        );
      },
    },
    "/api/stage-scene": {
      GET: async (req) => {
        const url = new URL(req.url);
        const member = url.searchParams.get("member") ?? "1_Emerald_Beach.set";
        const listAll = url.searchParams.get("listAll") === "1";
        const path = checkedPath(() => clientRelativePath(member));
        if ("response" in path) return path.response;
        const args = ["stage-scene"];
        if (listAll) args.push("--list-all");
        else args.push("--member", path.value);
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
        const paths = checkedPath(() => ({
          archive: archive ? clientRelativePath(archive) : "",
          member: clientRelativePath(member),
        }));
        if ("response" in paths) return paths.response;
        const args = ["ftm-parse", "--member", paths.value.member];
        if (paths.value.archive) args.push("--archive", paths.value.archive);
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
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: clientRelativePath(member),
        }));
        if ("response" in paths) return paths.response;
        const outDir = join(config.exportsDir, `ftm-${Date.now()}`);
        const patches = Array.isArray(body.patches) ? body.patches : [];
        return safeBridge(() =>
          runBridge([
            "ftm-export",
            "--archive",
            paths.value.archive,
            "--member",
            paths.value.member,
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
        const maxFrames = checkedInteger(url.searchParams.get("maxFrames"), {
          name: "maxFrames",
          minimum: 1,
          maximum: 5_000,
          fallback: 8,
        });
        if ("response" in maxFrames) return maxFrames.response;
        const clipIndex = checkedInteger(url.searchParams.get("clipIndex"), {
          name: "clipIndex",
          minimum: 0,
          maximum: 255,
          fallback: 0,
        });
        if ("response" in clipIndex) return clipIndex.response;
        const channel = url.searchParams.get("channel") ?? "A";
        const char = url.searchParams.get("char") ?? "";
        const motion = url.searchParams.get("motion") ?? "";
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: clientRelativePath(member),
          motion: motion ? clientRelativePath(motion) : "",
        }));
        if ("response" in paths) return paths.response;
        const args = [
          "ani-parse",
          "--archive",
          paths.value.archive,
          "--member",
          paths.value.member,
          "--max-frames",
          maxFrames.value,
          "--clip-index",
          clipIndex.value,
          "--channel",
          channel,
        ];
        if (char.trim()) {
          args.push("--char", char.trim());
        }
        if (paths.value.motion.trim()) {
          args.push("--motion", paths.value.motion.trim());
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
        const maxVertices = checkedInteger(url.searchParams.get("maxVertices"), {
          name: "maxVertices",
          minimum: 1,
          maximum: 10_000,
          fallback: 2_000,
        });
        if ("response" in maxVertices) return maxVertices.response;
        const args = ["skin-parse", "--char", char, "--max-vertices", maxVertices.value];
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
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: clientRelativePath(member),
        }));
        if ("response" in paths) return paths.response;
        return safeBridge(() =>
          runBridge([
            "mesh-meta",
            "--archive",
            paths.value.archive,
            "--member",
            paths.value.member,
          ]),
        );
      },
    },
    "/api/mesh-studio/parse": {
      GET: async (req) => {
        const url = new URL(req.url);
        const archive = url.searchParams.get("archive");
        const member = url.searchParams.get("member");
        if (!archive || !member) return bad("ARCHIVE_AND_MEMBER_REQUIRED");
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: clientRelativePath(member),
        }));
        if ("response" in paths) return paths.response;
        const metaOnly = url.searchParams.get("metaOnly") === "1";
        const args = [
          "mesh-parse",
          "--archive",
          paths.value.archive,
          "--member",
          paths.value.member,
        ];
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
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: clientRelativePath(member),
        }));
        if ("response" in paths) return paths.response;
        const outDir = join(config.exportsDir, `mesh-${Date.now()}`);
        return safeBridge(() =>
          runBridge([
            "mesh-export",
            "--archive",
            paths.value.archive,
            "--member",
            paths.value.member,
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
        const archive = String(body.archive ?? "");
        const member = String(body.member ?? "");
        if (!archive || !member) return bad("ARCHIVE_AND_MEMBER_REQUIRED");
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: archiveMemberName(member),
        }));
        if ("response" in paths) return paths.response;
        const outDir = join(config.exportsDir, `mesh-edit-${Date.now()}`);
        return safeBridge(() =>
          runBridgeWithPayload(
            "mesh-transform",
            { ...body, ...paths.value },
            (payloadPath) => [
              "mesh-transform",
              "--payload",
              payloadPath,
              "--out-dir",
              outDir,
            ],
          ),
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
        const paths = checkedPath(() => ({
          meshMember: meshMember ? clientRelativePath(meshMember) : "",
          archive: archive ? clientRelativePath(archive) : "",
          member: member ? clientRelativePath(member) : "",
        }));
        if ("response" in paths) return paths.response;
        const outDir = join(config.tmpDir, `mesh-tex-${crypto.randomUUID()}`);
        const args = ["mesh-texture", "--out-dir", outDir];
        if (paths.value.meshMember) args.push("--mesh-member", paths.value.meshMember);
        if (paths.value.archive) args.push("--archive", paths.value.archive);
        if (paths.value.member) args.push("--member", paths.value.member);
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
          const bytes = await Bun.file(body.png).arrayBuffer();
          return new Response(bytes, {
            headers: {
              "content-type": "image/png",
              "cache-control": "public, max-age=3600",
              "x-jftse-texture-source": body.source ?? "unknown",
            },
          });
        } catch (error) {
          if (error instanceof BridgeError) {
            if (
              error.code === "BRIDGE_EXIT_FAILED" &&
              error.detail.includes("There is no item named")
            ) {
              return new Response(null, {
                status: 204,
                headers: {
                  "x-jftse-texture-missing": "true",
                },
              });
            }
            return json(
              { ok: false, error: error.code, detail: error.detail },
              error.code === "BRIDGE_TIMEOUT" ? 504 : 500,
            );
          }
          return json(
            {
              ok: false,
              error: "BRIDGE_FAILED",
            },
            500,
          );
        } finally {
          rmSync(outDir, { recursive: true, force: true });
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
        const outFile = join(
          config.exportsDir,
          `map-pack-${Date.now()}.sql`,
        );
        return safeBridge(() =>
          runBridgeWithPayload("map-pack", body, (payloadPath) => [
            "map-studio-export-pack",
            "--payload",
            payloadPath,
            "--out-file",
            outFile,
          ]),
        );
      },
    },
    "/api/map-scene/package": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        if (
          !Array.isArray(body.availableDependencies) ||
          !body.availableDependencies.every(
            (dependency) => typeof dependency === "string",
          )
        ) {
          return bad("AVAILABLE_DEPENDENCIES_REQUIRED");
        }
        try {
          const scene = parseMapScene(JSON.stringify(body.scene));
          const receipt = await buildRuntimeMapPackage(
            scene,
            new Set(body.availableDependencies),
            config.exportsDir,
          );
          return json({ ok: true, ...receipt });
        } catch (error) {
          return bad(error instanceof Error ? error.message : String(error));
        }
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
        const paths = checkedPath(() => ({
          particleArchive: particleArchive
            ? trustedReadPath(particleArchive, [config.exportsDir])
            : "",
          member: clientRelativePath(member),
        }));
        if ("response" in paths) return paths.response;
        const args = ["effect-slot-fields", "--member", paths.value.member];
        if (particleArchive) {
          args.push("--particle-archive", paths.value.particleArchive);
        }
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/playtest/status": {
      GET: async (req) => {
        const url = new URL(req.url);
        const exportArchive = url.searchParams.get("exportArchive") ?? "";
        const path = checkedPath(() =>
          exportArchive
            ? trustedReadPath(exportArchive, [config.exportsDir])
            : "",
        );
        if ("response" in path) return path.response;
        const args = ["playtest-status"];
        if (exportArchive) {
          args.push("--export-archive", path.value);
        }
        return safeBridge(() => runBridge(args));
      },
    },
    "/api/client-harness/profiles": {
      GET: () => {
        const profileRoot = join(config.tmpDir, "managed-client-profiles");
        return json({
          ok: true,
          profiles: listManagedProfiles(profileRoot).map(
            ({ name, mode, profile }) => ({
              name,
              mode,
              root: profile.root,
              launcher: profile.launcher,
              capturePath: profile.capturePath,
            }),
          ),
          realClientAutomation: false,
          limitation:
            "The managed harness automates disposable profiles only. Real DX9 login and content selection remain manual.",
        });
      },
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        const name = String(body.name ?? "");
        const mode = String(body.mode ?? "");
        try {
          const stored = createManagedProfile(
            join(config.tmpDir, "managed-client-profiles"),
            name,
            mode as ManagedProfileMode,
          );
          return json({
            ok: true,
            profile: {
              name: stored.name,
              mode: stored.mode,
              root: stored.profile.root,
              launcher: stored.profile.launcher,
              capturePath: stored.profile.capturePath,
            },
          });
        } catch (error) {
          return bad(error instanceof Error ? error.message : String(error));
        }
      },
      DELETE: () => {
        const deleted = clearManagedProfiles(
          join(config.tmpDir, "managed-client-profiles"),
        );
        return json({ ok: true, deleted });
      },
    },
    "/api/client-harness/run": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        try {
          const stored = loadManagedProfile(
            join(config.tmpDir, "managed-client-profiles"),
            String(body.name ?? ""),
          );
          const result = await runManagedClient(stored.profile, {
            forbiddenRoots: [config.stockClient],
            timeoutMs: 10_000,
          });
          const capturePath = result.capture
            ? join(stored.profile.root, result.capture.relativePath)
            : "";
          const captureDataUrl =
            capturePath && existsSync(capturePath)
              ? `data:image/png;base64,${readFileSync(capturePath).toString(
                  "base64",
                )}`
              : null;
          return json({
            ok: true,
            profile: { name: stored.name, mode: stored.mode },
            ...result,
            captureDataUrl,
            realClientAutomation: false,
          });
        } catch (error) {
          return bad(error instanceof Error ? error.message : String(error));
        }
      },
    },
    "/api/client-harness/pipeline": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = (await req.json()) as Record<string, unknown>;
        } catch {
          return bad("INVALID_JSON");
        }
        try {
          const managedStoreRoot = join(
            config.tmpDir,
            "managed-client-profiles",
          );
          const stored = loadManagedProfile(
            managedStoreRoot,
            String(body.name ?? ""),
          );
          const result = await runClientHarnessPipeline({
            profile: stored.profile,
            buildPayload: managedHarnessBuildPayload(stored.name),
            applySql: body.applySql === true,
            forbiddenRoots: [config.stockClient],
            managedStoreRoot,
            exportsRoot: config.exportsDir,
          });
          const capturePath = result.launch?.capture
            ? join(
                stored.profile.root,
                result.launch.capture.relativePath,
              )
            : "";
          const captureDataUrl =
            capturePath && existsSync(capturePath)
              ? `data:image/png;base64,${readFileSync(capturePath).toString(
                  "base64",
                )}`
              : null;
          return json({
            ok: true,
            profile: { name: stored.name, mode: stored.mode },
            ...result,
            captureDataUrl,
            sqlApplyEligible: result.receipts.sqlAudit.status === "passed",
          });
        } catch (error) {
          return bad(error instanceof Error ? error.message : String(error));
        }
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
        const sourcePaths = checkedPath(() => ({
          particleArchive: trustedRegularFilePath(particleArchive, [config.exportsDir]),
          itemArchive:
            typeof body.itemArchive === "string" && body.itemArchive
              ? trustedRegularFilePath(body.itemArchive, [config.exportsDir])
              : "",
          effectArchive:
            typeof body.effectArchive === "string" && body.effectArchive
              ? trustedRegularFilePath(body.effectArchive, [config.exportsDir])
              : "",
        }));
        if ("response" in sourcePaths) {
          return bad("SOURCE_OUTSIDE_EXPORTS");
        }
        const files = [
          {
            source: sourcePaths.value.particleArchive,
            destRelative: "Res/Effect/Particle.res",
          },
        ];
        if (sourcePaths.value.itemArchive) {
          files.push({
            source: sourcePaths.value.itemArchive,
            destRelative: "Res/Script/Item.res",
          });
        }
        if (sourcePaths.value.effectArchive) {
          files.push({
            source: sourcePaths.value.effectArchive,
            destRelative: "Res/Script/ETC.res",
          });
        }
        return safeBridge(() =>
          installClientFiles({
            targetClient,
            files,
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
          const dat = checkedPath(() =>
            trustedReadPath(body.dat as string, trustedStudioReadRoots),
          );
          if ("response" in dat) return dat.response;
          args.push("--dat", dat.value);
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
        return safeBridge(() =>
          installClientFiles({
            targetClient,
            files: files as Array<{ source: string; destRelative: string }>,
          }),
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
        const outFile = join(config.exportsDir, `map-create-${Date.now()}.sql`);
        return safeBridge(() =>
          runBridgeWithPayload("map-create", body, (payloadPath) => [
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
        const outDir = join(config.exportsDir, `stage-set-${Date.now()}`);
        const member = checkedPath(() =>
          clientRelativePath(String(body.member ?? "1_Emerald_Beach.set")),
        );
        if ("response" in member) return member.response;
        return safeBridge(() =>
          runBridgeWithPayload("stage-set-write", body, (payloadPath) => [
            "stage-set-write",
            "--payload",
            payloadPath,
            "--out-dir",
            outDir,
            "--member",
            member.value,
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
        const outDir = join(config.exportsDir, `ftm-author-${Date.now()}`);
        const paths = checkedPath(() => ({
          archive: clientRelativePath(String(body.archive ?? "")),
          member: clientRelativePath(String(body.member ?? "")),
        }));
        if ("response" in paths) return paths.response;
        return safeBridge(() =>
          runBridgeWithPayload("ftm-author", body, (payloadPath) => [
            "ftm-author",
            "--payload",
            payloadPath,
            "--out-dir",
            outDir,
            "--archive",
            paths.value.archive,
            "--member",
            paths.value.member,
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
        const paths = checkedPath(() => ({
          dds: trustedReadPath(dds, trustedStudioReadRoots),
          out: exportOutputPath(
            String(body.out ?? join(config.exportsDir, `tex-${Date.now()}.tex`)),
            config.exportsDir,
          ),
        }));
        if ("response" in paths) return paths.response;
        return safeBridge(() =>
          runBridge(["tex-encode", "--dds", paths.value.dds, "--out", paths.value.out]),
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
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: clientRelativePath(member),
          obj: trustedReadPath(obj, trustedStudioReadRoots),
          out: exportOutputPath(
            String(
              body.out ??
                join(config.exportsDir, `mesh-obj-${Date.now()}`, member),
            ),
            config.exportsDir,
          ),
        }));
        if ("response" in paths) return paths.response;
        return safeBridge(() =>
          runBridge([
            "mesh-obj-import",
            "--archive",
            paths.value.archive,
            "--member",
            paths.value.member,
            "--obj",
            paths.value.obj,
            "--out",
            paths.value.out,
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
        const paths = checkedPath(() => ({
          obj: trustedReadPath(obj, trustedStudioReadRoots),
          out: exportOutputPath(
            String(
              body.out ??
                join(config.exportsDir, `mesh-new-${Date.now()}`, "authored.dat"),
            ),
            config.exportsDir,
          ),
        }));
        if ("response" in paths) return paths.response;
        return safeBridge(() =>
          runBridge([
            "mesh-from-obj",
            "--obj",
            paths.value.obj,
            "--out",
            paths.value.out,
          ]),
        );
      },
    },
    "/api/eft/parse": {
      GET: async (req) => {
        const url = new URL(req.url);
        const path = url.searchParams.get("path") ?? "";
        if (!path) return bad("PATH_REQUIRED");
        const checked = checkedPath(() => clientRelativePath(path));
        if ("response" in checked) return checked.response;
        return safeBridge(() => runBridge(["eft-parse", "--path", checked.value]));
      },
    },
    "/api/ani/section-b-status": {
      GET: async (req) => {
        const url = new URL(req.url);
        const archive =
          url.searchParams.get("archive") ?? "Res/Player/PlayerA/AniA.res";
        const member = url.searchParams.get("member") ?? "NikiAniA.ani";
        const char = url.searchParams.get("char") ?? "NIKI";
        const paths = checkedPath(() => ({
          archive: clientRelativePath(archive),
          member: clientRelativePath(member),
        }));
        if ("response" in paths) return paths.response;
        return safeBridge(() =>
          runBridge([
            "ani-section-b-status",
            "--archive",
            paths.value.archive,
            "--member",
            paths.value.member,
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
          body = await readJsonObject(req, 2 * 1024 * 1024);
        } catch (error) {
          return operationalError(error) ?? bad("INVALID_JSON");
        }
        const stage =
          body.stage && typeof body.stage === "object" && !Array.isArray(body.stage)
            ? (body.stage as Record<string, unknown>)
            : null;
        const ftm =
          body.ftm && typeof body.ftm === "object" && !Array.isArray(body.ftm)
            ? (body.ftm as Record<string, unknown>)
            : null;
        const paths = checkedPath(() => ({
          stageMember: stage?.member
            ? archiveMemberName(String(stage.member))
            : "",
          ftmArchive: ftm?.archive
            ? clientRelativePath(String(ftm.archive))
            : "",
          ftmMember: ftm?.member
            ? archiveMemberName(String(ftm.member))
            : "",
          particleArchive:
            typeof body.particleArchive === "string" && body.particleArchive
              ? trustedRegularFilePath(body.particleArchive, [config.exportsDir])
              : "",
        }));
        if ("response" in paths) return paths.response;
        const payload = {
          ...body,
          ...(stage && paths.value.stageMember
            ? { stage: { ...stage, member: paths.value.stageMember } }
            : {}),
          ...(ftm
            ? {
                ftm: {
                  ...ftm,
                  ...(paths.value.ftmArchive
                    ? { archive: paths.value.ftmArchive }
                    : {}),
                  ...(paths.value.ftmMember
                    ? { member: paths.value.ftmMember }
                    : {}),
                },
              }
            : {}),
          ...(paths.value.particleArchive
            ? { particleArchive: paths.value.particleArchive }
            : {}),
        };
        const outDir = join(
          config.exportsDir,
          `content-pack-${Date.now()}`,
        );
        return safeBridge(() =>
          runBridgeWithPayload("content-pack", payload, (payloadPath) => [
            "content-pack-build",
            "--payload",
            payloadPath,
            "--out-dir",
            outDir,
          ]),
        );
      },
    },
    "/api/equipment-creator/package": {
      POST: async (req) => {
        let body: unknown;
        try {
          body = await req.json();
        } catch {
          return bad("INVALID_JSON");
        }
        try {
          validateEquipmentPackageRequest(body);
        } catch (error) {
          return bad(error instanceof Error ? error.message : "INVALID_EQUIPMENT_PACKAGE");
        }
        return safeBridge(() => packageEquipmentCreator(body));
      },
    },
    "/api/equipment-creator/install": {
      POST: (req) =>
        safeBridge(async () => {
          const body = await readJsonObject(req, 4 * 1024);
          return installEquipmentPackage(
            String(body.packageId ?? ""),
            String(body.profileName ?? ""),
            {
              exportsRoot: config.exportsDir,
              managedStoreRoot: join(
                config.tmpDir,
                "managed-client-profiles",
              ),
              forbiddenRoots: [config.stockClient],
            },
          );
        }),
    },
    "/api/equipment-creator/audit": {
      POST: (req) =>
        safeBridge(async () => {
          const body = await readJsonObject(req, 4 * 1024);
          return auditEquipmentPackage(String(body.packageId ?? ""), {
            exportsRoot: config.exportsDir,
            managedStoreRoot: join(config.tmpDir, "managed-client-profiles"),
            forbiddenRoots: [config.stockClient],
          });
        }),
    },
    "/api/equipment-creator/preflight": {
      POST: (req) =>
        safeBridge(async () => {
          const body = await readJsonObject(req, 4 * 1024);
          return preflightEquipmentPackage(
            String(body.packageId ?? ""),
            String(body.profileName ?? ""),
            {
              exportsRoot: config.exportsDir,
              managedStoreRoot: join(
                config.tmpDir,
                "managed-client-profiles",
              ),
              forbiddenRoots: [config.stockClient],
            },
          );
        }),
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
        const installed = await safeBridge(() =>
          runBridgeWithPayload(
            "content-pack-install",
            { files },
            (payloadPath) => [
              "client-install",
              "--target-client",
              targetClient,
              "--payload",
              payloadPath,
            ],
          ),
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
        return safeBridge(() =>
          runBridgeWithPayload(
            "content-pack-playtest",
            { installPlan },
            (payloadPath) => [
              "content-pack-playtest",
              "--target-client",
              targetClient,
              "--payload",
              payloadPath,
            ],
          ),
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
        return safeBridge(() =>
          runBridgeWithPayload(
            "content-pack-playtest-full",
            body,
            (payloadPath) => [
              "content-pack-playtest-full",
              "--target-client",
              targetClient,
              "--payload",
              payloadPath,
            ],
          ),
        );
      },
    },
    "/api/sql/apply": {
      POST: async (req) => {
        let body: Record<string, unknown>;
        try {
          body = await readJsonObject(req, 16 * 1024);
        } catch (error) {
          return operationalError(error) ?? bad("INVALID_JSON");
        }
        if (!body.path) return bad("PATH_REQUIRED");
        if ("databaseUrl" in body) {
          return bad("DATABASE_URL_OVERRIDE_FORBIDDEN");
        }
        if ("allowDeletes" in body) {
          return bad("SQL_DELETE_OVERRIDE_FORBIDDEN");
        }
        if (
          Object.keys(body).some(
            (field) => field !== "path" && field !== "dryRun",
          )
        ) {
          return bad("SQL_REQUEST_FIELD_FORBIDDEN");
        }
        return safeBridge(() =>
          runBridgeWithPayload("sql-apply", body, (payloadPath) => [
            "sql-apply",
            "--payload",
            payloadPath,
          ]),
        );
      },
    },
    "/api/packs": {
      GET: async () => {
        const files = readdirSync(config.packsDir).filter((name) =>
          name.endsWith(".json"),
        );
        const packs = files.flatMap((name) => {
          try {
            const raw = readFileSync(join(config.packsDir, name), "utf8");
            return [
              { file: name, ...(JSON.parse(raw) as Record<string, unknown>) },
            ];
          } catch {
            return [];
          }
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
        safeBridge(async () => {
          const preflight = await runBridge(["playtest-status"]);
          return {
            ok: true,
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
            launchHint: preflight.launchCommand ?? null,
            preflight,
          };
        }),
    },
  },
  error(error) {
    return operationalError(error) ?? bad("INTERNAL_SERVER_ERROR", 500);
  },
  ...developmentServeOptions(process.env),
});

let shuttingDown = false;
async function shutdown(): Promise<void> {
  if (shuttingDown) return;
  shuttingDown = true;
  server.stop();
  await shutdownBridgeProcesses();
}
process.once("SIGINT", shutdown);
process.once("SIGTERM", shutdown);

process.stdout.write(
  `jftse-content-studio listening on http://127.0.0.1:${server.port}\n`,
);
