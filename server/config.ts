import { existsSync } from "node:fs";
import { resolve } from "node:path";

const studioRoot = resolve(import.meta.dir, "..");

function discoverJftseRoot(): string {
  if (process.env.JFTSE_ROOT?.trim()) {
    return resolve(process.env.JFTSE_ROOT);
  }
  const sibling = resolve(studioRoot, "../JFTSE");
  if (existsSync(sibling)) {
    return sibling;
  }
  throw new Error(
    "JFTSE_ROOT is not set and sibling ../JFTSE was not found from the studio repo",
  );
}

const jftseRoot = discoverJftseRoot();

function discoverStockClient(): string {
  if (process.env.JFTSE_STOCK_CLIENT?.trim()) {
    return resolve(process.env.JFTSE_STOCK_CLIENT);
  }
  return resolve(jftseRoot, ".jftse-client-linux/client");
}

function discoverLocalClient(): string {
  if (process.env.JFTSE_LOCAL_CLIENT?.trim()) {
    return resolve(process.env.JFTSE_LOCAL_CLIENT);
  }
  const candidate = resolve(jftseRoot, "FantaTennis-Local-Client/client");
  return candidate;
}

export const config = {
  studioRoot,
  port: Number(process.env.PORT ?? 4310),
  jftseRoot,
  stockClient: discoverStockClient(),
  localClient: discoverLocalClient(),
  pythonBridge: resolve(studioRoot, "python/studio_bridge.py"),
  exportsDir: resolve(studioRoot, "exports"),
  packsDir: resolve(studioRoot, "content-packs"),
  tmpDir: resolve(studioRoot, ".tmp"),
};

export function bridgeEnv(): Record<string, string> {
  return {
    ...process.env,
    JFTSE_ROOT: config.jftseRoot,
    JFTSE_STOCK_CLIENT: config.stockClient,
    JFTSE_LOCAL_CLIENT: config.localClient,
    JFTSE_STUDIO_EXPORTS: config.exportsDir,
  };
}
