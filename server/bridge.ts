import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { bridgeEnv, config } from "./config.ts";

export type BridgeResult = Record<string, unknown>;

export async function runBridge(
  args: string[],
  options: { stdinJson?: unknown } = {},
): Promise<BridgeResult> {
  mkdirSync(config.tmpDir, { recursive: true });
  const proc = Bun.spawn(["uv", "run", "python", config.pythonBridge, ...args], {
    cwd: config.jftseRoot,
    env: bridgeEnv(),
    stdout: "pipe",
    stderr: "pipe",
    stdin: options.stdinJson === undefined ? "ignore" : "pipe",
  });
  if (options.stdinJson !== undefined && proc.stdin) {
    proc.stdin.write(JSON.stringify(options.stdinJson));
    proc.stdin.end();
  }
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
  const payloadPath = join(config.tmpDir, `payload-${Date.now()}.json`);
  await Bun.write(payloadPath, JSON.stringify(payload, null, 2));
  return runBridge([
    "build-effect",
    "--payload",
    payloadPath,
    "--out-dir",
    destination,
  ]);
}
