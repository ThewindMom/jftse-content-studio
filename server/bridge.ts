import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { bridgeEnv, config } from "./config.ts";

export type BridgeResult = Record<string, unknown>;

export async function runBridge(args: string[]): Promise<BridgeResult> {
  mkdirSync(config.tmpDir, { recursive: true });
  const proc = Bun.spawn(
    [
      "uv",
      "run",
      "--with",
      "pillow",
      "--with",
      "cryptography",
      "python",
      config.pythonBridge,
      ...args,
    ],
    {
    cwd: config.jftseRoot,
    env: bridgeEnv(),
    stdout: "pipe",
    stderr: "pipe",
    stdin: "ignore",
    },
  );
  const stdout = await new Response(proc.stdout).text();
  const stderr = await new Response(proc.stderr).text();
  const code = await proc.exited;
  if (code !== 0) {
    throw new Error(stderr || stdout || `bridge exited ${code}`);
  }
  const line = stdout.trim().split("\n").filter(Boolean).at(-1) ?? "{}";
  return JSON.parse(line) as BridgeResult;
}

export async function buildEffect(
  payload: Record<string, unknown>,
  outDir?: string,
): Promise<BridgeResult> {
  const destination =
    outDir ?? join(config.exportsDir, `effect-${Date.now()}`);
  mkdirSync(destination, { recursive: true });
  const payloadPath = join(config.tmpDir, `payload-${crypto.randomUUID()}.json`);
  await Bun.write(payloadPath, JSON.stringify(payload, null, 2));
  return runBridge([
    "build-effect",
    "--payload",
    payloadPath,
    "--out-dir",
    destination,
  ]);
}

export async function installEffect(input: {
  particleArchive: string;
  targetClient: string;
  itemArchive?: string;
  effectArchive?: string;
}): Promise<BridgeResult> {
  const args = [
    "install",
    "--target-client",
    input.targetClient,
    "--particle-archive",
    input.particleArchive,
  ];
  if (input.itemArchive) {
    args.push("--item-archive", input.itemArchive);
  }
  if (input.effectArchive) {
    args.push("--effect-archive", input.effectArchive);
  }
  return runBridge(args);
}
