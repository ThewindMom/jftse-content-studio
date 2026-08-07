import { resolve } from "node:path";

const studioRoot = resolve(import.meta.dir, "..");

export const config = {
  studioRoot,
  port: Number(process.env.PORT ?? 4310),
  jftseRoot: resolve(
    process.env.JFTSE_ROOT ??
      "/home/thewind/Projects/00_Random_Coding/260705_fanta_tennis/JFTSE",
  ),
  stockClient:
    process.env.JFTSE_STOCK_CLIENT ??
    "/home/thewind/Projects/00_Random_Coding/260705_fanta_tennis/JFTSE/.jftse-client-linux/client",
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
  };
}
