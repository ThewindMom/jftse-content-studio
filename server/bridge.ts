import { mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { kill as signalProcess, platform } from "node:process";
import { bridgeEnv, config } from "./config.ts";

export type BridgeResult = Record<string, unknown>;

export type BridgeOptions = {
  timeoutMs?: number;
};

export class BridgeError extends Error {
  constructor(
    readonly code:
      | "BRIDGE_TIMEOUT"
      | "BRIDGE_EXIT_FAILED"
      | "BRIDGE_INVALID_JSON",
    readonly detail: string,
  ) {
    super(code);
    this.name = "BridgeError";
  }
}

const DEFAULT_TIMEOUT_MS = 180_000;
const DETAIL_LIMIT = 2_000;
const OUTPUT_LIMIT = 1_000_000;
const TERMINATION_GRACE_MS = 1_000;

function sanitizeDetail(value: string): string {
  return value.replace(/[^\x09\x0a\x0d\x20-\x7e]/g, "?").slice(-DETAIL_LIMIT);
}

async function readBoundedTail(
  stream: ReadableStream<Uint8Array>,
): Promise<string> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let tail = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      tail = (tail + decoder.decode(value, { stream: true })).slice(
        -OUTPUT_LIMIT,
      );
    }
    return (tail + decoder.decode()).slice(-OUTPUT_LIMIT);
  } finally {
    reader.releaseLock();
  }
}

export async function runBridge(
  args: string[],
  options: BridgeOptions = {},
): Promise<BridgeResult> {
  mkdirSync(config.tmpDir, { recursive: true });
  const process = Bun.spawn(
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
      detached: true,
      env: bridgeEnv(),
      stdout: "pipe",
      stderr: "pipe",
      stdin: "ignore",
    },
  );
  const completion = Promise.all([
    readBoundedTail(process.stdout),
    readBoundedTail(process.stderr),
    process.exited,
  ]);
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  let timeout: Timer | undefined;
  const outcome = await Promise.race([
    completion.then((result) => ({ kind: "complete" as const, result })),
    new Promise<{ kind: "timeout" }>((resolve) => {
      timeout = setTimeout(() => resolve({ kind: "timeout" }), timeoutMs);
    }),
  ]);
  if (timeout) clearTimeout(timeout);
  if (outcome.kind === "timeout") {
    const terminate = (signal: "SIGTERM" | "SIGKILL") => {
      if (platform !== "win32") {
        try {
          signalProcess(-process.pid, signal);
          return;
        } catch (error) {
          const code = (error as NodeJS.ErrnoException).code;
          if (code === "ESRCH") return;
        }
      }
      try {
        process.kill(signal);
      } catch {
        // The direct child already exited.
      }
    };
    terminate("SIGTERM");
    let grace: Timer | undefined;
    const exitedDuringGrace = await Promise.race([
      process.exited.then(() => true),
      new Promise<boolean>((resolve) => {
        grace = setTimeout(() => resolve(false), TERMINATION_GRACE_MS);
      }),
    ]);
    if (grace) clearTimeout(grace);
    if (!exitedDuringGrace) terminate("SIGKILL");
    await completion;
    throw new BridgeError(
      "BRIDGE_TIMEOUT",
      `Bridge timed out after ${timeoutMs}ms`,
    );
  }

  const [stdout, stderr, code] = outcome.result;
  if (code !== 0) {
    throw new BridgeError(
      "BRIDGE_EXIT_FAILED",
      sanitizeDetail(stderr || stdout || `Bridge exited ${code}`),
    );
  }
  const line = stdout.trim().split("\n").filter(Boolean).at(-1) ?? "";
  try {
    return JSON.parse(line) as BridgeResult;
  } catch {
    throw new BridgeError(
      "BRIDGE_INVALID_JSON",
      sanitizeDetail(line || "Bridge returned no JSON"),
    );
  }
}

export async function runBridgeWithPayload(
  prefix: string,
  payload: Record<string, unknown>,
  argsForPath: (payloadPath: string) => string[],
  options?: BridgeOptions,
): Promise<BridgeResult> {
  mkdirSync(config.tmpDir, { recursive: true });
  const payloadPath = join(
    config.tmpDir,
    `${prefix}-${crypto.randomUUID()}.json`,
  );
  await Bun.write(payloadPath, JSON.stringify(payload, null, 2));
  try {
    return await runBridge(argsForPath(payloadPath), options);
  } finally {
    rmSync(payloadPath, { force: true });
  }
}

export async function buildEffect(
  payload: Record<string, unknown>,
  outDir?: string,
): Promise<BridgeResult> {
  const destination =
    outDir ?? join(config.exportsDir, `effect-${Date.now()}`);
  mkdirSync(destination, { recursive: true });
  return runBridgeWithPayload(
    "payload",
    payload,
    (payloadPath) => [
      "build-effect",
      "--payload",
      payloadPath,
      "--out-dir",
      destination,
    ],
    { timeoutMs: 300_000 },
  );
}

export async function installClientFiles(input: {
  targetClient: string;
  files: Array<{
    source: string;
    destRelative: string;
  }>;
}): Promise<BridgeResult> {
  return runBridgeWithPayload(
    "client-install",
    { files: input.files },
    (payloadPath) => [
      "client-install",
      "--target-client",
      input.targetClient,
      "--payload",
      payloadPath,
    ],
  );
}
