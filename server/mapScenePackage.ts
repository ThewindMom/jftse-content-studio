import { createHash, randomUUID } from "node:crypto";
import { mkdir, open, rename, rm } from "node:fs/promises";
import { isAbsolute, join, relative, resolve, sep } from "node:path";
import { runBridgeWithPayload } from "./bridge.ts";
import {
  compileMapScene,
  type CompiledMapScene,
} from "./mapSceneCompiler.ts";
import {
  buildMapManifest,
  parseMapScene,
  serializeMapScene,
  type MapSceneDocument,
} from "../web/mapSceneDocument.ts";

export type MapScenePackageReceipt = {
  path: string;
  hash: string;
  bytes: number;
  dependencies: string[];
};

type InstallEntry = { source: string; destRelative: string };

export type RuntimeContentPackReceipt = {
  ok: true;
  outDir: string;
  parts: Record<string, unknown>;
  sqlPath: string;
  installPlan: InstallEntry[];
  [key: string]: unknown;
};

export type RuntimeMapPackageReceipt = MapScenePackageReceipt & {
  contentPack: RuntimeContentPackReceipt;
  runtimeUnsupported: string[];
};

export type MapContentPackBuilder = (
  payload: Record<string, unknown>,
  outDir: string,
) => Promise<Record<string, unknown>>;

function packagePath(sceneName: string, outputDirectory: string): string {
  if (
    sceneName.length === 0 ||
    sceneName === "." ||
    sceneName === ".." ||
    sceneName.includes("/") ||
    sceneName.includes("\\") ||
    sceneName.includes("\0")
  ) {
    throw new Error(`Unsafe map package name: ${JSON.stringify(sceneName)}`);
  }

  const outputRoot = resolve(outputDirectory);
  const destination = resolve(outputRoot, `${sceneName}.map-package.json`);
  const relativeDestination = relative(outputRoot, destination);
  if (
    relativeDestination === ".." ||
    relativeDestination.startsWith(`..${sep}`) ||
    isAbsolute(relativeDestination)
  ) {
    throw new Error(`Map package path escapes output directory: ${destination}`);
  }
  return destination;
}

export async function packageMapScene(
  scene: MapSceneDocument,
  availableDependencies: ReadonlySet<string>,
  outputDirectory: string,
): Promise<MapScenePackageReceipt> {
  const validatedScene = parseMapScene(serializeMapScene(scene));
  const destination = packagePath(validatedScene.name, outputDirectory);
  const manifest = buildMapManifest(validatedScene, availableDependencies);
  const contents = `${JSON.stringify(manifest, null, 2)}\n`;
  const bytes = Buffer.byteLength(contents, "utf8");
  const hash = createHash("sha256").update(contents, "utf8").digest("hex");

  const outputRoot = resolve(outputDirectory);
  await mkdir(outputRoot, { recursive: true });
  const temporaryPath = resolve(
    outputRoot,
    `.${validatedScene.name}.${randomUUID()}.tmp`,
  );
  let published = false;
  try {
    const handle = await open(temporaryPath, "wx");
    try {
      await handle.writeFile(contents, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    await rename(temporaryPath, destination);
    published = true;
  } finally {
    if (!published) {
      await rm(temporaryPath, { force: true });
    }
  }

  return {
    path: destination,
    hash,
    bytes,
    dependencies: [...manifest.dependencies],
  };
}

function safeStem(value: string): string {
  return (
    value
      .trim()
      .replace(/[^A-Za-z0-9_-]+/g, "_")
      .replace(/^_+|_+$/g, "") || "Untitled_Court"
  );
}

function contentPackReceipt(
  result: Record<string, unknown>,
): RuntimeContentPackReceipt {
  if (
    result.ok !== true ||
    typeof result.outDir !== "string" ||
    typeof result.sqlPath !== "string" ||
    !result.parts ||
    typeof result.parts !== "object" ||
    !Array.isArray(result.installPlan) ||
    !result.installPlan.every(
      (entry) =>
        entry &&
        typeof entry === "object" &&
        typeof (entry as InstallEntry).source === "string" &&
        typeof (entry as InstallEntry).destRelative === "string",
    )
  ) {
    throw new Error(
      typeof result.error === "string"
        ? result.error
        : "MAP_CONTENT_PACK_INVALID",
    );
  }
  return result as RuntimeContentPackReceipt;
}

async function defaultContentPackBuilder(
  payload: Record<string, unknown>,
  outDir: string,
): Promise<Record<string, unknown>> {
  return runBridgeWithPayload("map-scene-pack", payload, (payloadPath) => [
    "content-pack-build",
    "--payload",
    payloadPath,
    "--out-dir",
    outDir,
  ]);
}

async function assertRuntimeArtifacts(
  receipt: RuntimeContentPackReceipt,
): Promise<void> {
  if (!(await Bun.file(receipt.sqlPath).exists())) {
    throw new Error("MAP_SQL_ARTIFACT_MISSING");
  }
  if (receipt.installPlan.length < 2) {
    throw new Error("MAP_INSTALL_PLAN_INCOMPLETE");
  }
  for (const entry of receipt.installPlan) {
    if (!(await Bun.file(entry.source).exists())) {
      throw new Error(`MAP_ARTIFACT_MISSING:${entry.destRelative}`);
    }
  }
  for (const part of ["map", "stage", "ftm"]) {
    if (!(part in receipt.parts)) {
      throw new Error(`MAP_PACKAGE_PART_MISSING:${part}`);
    }
  }
}

export async function buildRuntimeMapPackage(
  scene: MapSceneDocument,
  availableDependencies: ReadonlySet<string>,
  outputDirectory: string,
  buildContentPack: MapContentPackBuilder = defaultContentPackBuilder,
): Promise<RuntimeMapPackageReceipt> {
  const validatedScene = parseMapScene(serializeMapScene(scene));
  const manifest = buildMapManifest(validatedScene, availableDependencies);
  const compiled: CompiledMapScene = compileMapScene(validatedScene);
  const outDir = join(
    resolve(outputDirectory),
    `map-runtime-${safeStem(validatedScene.name)}-${Date.now()}`,
  );
  const contentPack = contentPackReceipt(
    await buildContentPack(compiled.payload, outDir),
  );
  await assertRuntimeArtifacts(contentPack);

  const destination = packagePath(validatedScene.name, outDir);
  const contents = `${JSON.stringify(
    {
      ...manifest,
      design: compiled.design,
      runtimeUnsupported: compiled.runtimeUnsupported,
      contentPack,
    },
    null,
    2,
  )}\n`;
  const bytes = Buffer.byteLength(contents, "utf8");
  const hash = createHash("sha256").update(contents, "utf8").digest("hex");
  await mkdir(outDir, { recursive: true });
  const temporaryPath = join(outDir, `.${randomUUID()}.tmp`);
  let published = false;
  try {
    const handle = await open(temporaryPath, "wx");
    try {
      await handle.writeFile(contents, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    await rename(temporaryPath, destination);
    published = true;
  } finally {
    if (!published) await rm(temporaryPath, { force: true });
  }

  return {
    path: destination,
    hash,
    bytes,
    dependencies: [...manifest.dependencies],
    contentPack,
    runtimeUnsupported: compiled.runtimeUnsupported,
  };
}
