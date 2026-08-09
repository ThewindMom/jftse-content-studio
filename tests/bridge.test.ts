import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import {
  chmodSync,
  mkdtempSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runBridge } from "../server/bridge.ts";

type BridgeFailure = Error & { code?: string; detail?: string };
type RunBridgeWithOptions = (
  args: string[],
  options?: { timeoutMs?: number },
) => Promise<Record<string, unknown>>;

const originalPath = process.env.PATH;
const runBridgeWithOptions = runBridge as RunBridgeWithOptions;
let fakeBinDir = "";

async function captureFailure(work: () => Promise<unknown>): Promise<BridgeFailure> {
  try {
    await work();
  } catch (error) {
    if (error instanceof Error) return error as BridgeFailure;
    throw error;
  }
  throw new Error("expected bridge failure");
}

beforeAll(async () => {
  fakeBinDir = mkdtempSync(join(tmpdir(), "jftse-bridge-fixture-"));
  const fakeUv = join(fakeBinDir, "uv");
  await Bun.write(
    fakeUv,
    `#!/bin/sh
case "$JFTSE_BRIDGE_FIXTURE" in
  timeout)
    exec bun -e 'setTimeout(() => console.log(JSON.stringify({ ok: true })), 200)'
    ;;
  tree-timeout)
    exec bun -e 'const child = Bun.spawn(["bun", "-e", "setInterval(() => {}, 1000)"], { stdin: "ignore", stdout: "ignore", stderr: "ignore" }); await Bun.write(process.env.JFTSE_CHILD_PID_FILE, String(child.pid)); setInterval(() => {}, 1000)'
    ;;
  exit)
    bun -e 'console.error("x".repeat(5000)); process.exit(9)'
    ;;
  invalid)
    printf 'diagnostic line\\nnot-json\\n'
    ;;
  valid)
    printf 'diagnostic line\\n{"ok":true,"fixture":"valid"}\\n'
    ;;
esac
`,
  );
  chmodSync(fakeUv, 0o755);
  process.env.PATH = `${fakeBinDir}:${originalPath ?? ""}`;
});

afterAll(() => {
  if (originalPath === undefined) {
    delete process.env.PATH;
  } else {
    process.env.PATH = originalPath;
  }
  delete process.env.JFTSE_BRIDGE_FIXTURE;
  delete process.env.JFTSE_CHILD_PID_FILE;
  if (fakeBinDir) rmSync(fakeBinDir, { recursive: true, force: true });
});

describe("bridge lifecycle", () => {
  test("stable bridge error times out and kills the child", async () => {
    process.env.JFTSE_BRIDGE_FIXTURE = "timeout";
    const error = await captureFailure(() =>
      runBridgeWithOptions(["health"], { timeoutMs: 25 }),
    );
    expect(error.code).toBe("BRIDGE_TIMEOUT");
    expect(error.detail).toContain("25ms");
  });

  test("bridge timeout terminates the spawned process group", async () => {
    const childPidFile = join(fakeBinDir, "grandchild.pid");
    rmSync(childPidFile, { force: true });
    process.env.JFTSE_BRIDGE_FIXTURE = "tree-timeout";
    process.env.JFTSE_CHILD_PID_FILE = childPidFile;
    let childPid = 0;
    try {
      const error = await captureFailure(() =>
        runBridgeWithOptions(["health"], { timeoutMs: 150 }),
      );
      childPid = Number(readFileSync(childPidFile, "utf8"));
      expect(error.code).toBe("BRIDGE_TIMEOUT");
      let running = true;
      try {
        const status = readFileSync(`/proc/${childPid}/status`, "utf8");
        running = !/^State:\s+Z/m.test(status);
      } catch {
        running = false;
      }
      expect(running).toBe(false);
    } finally {
      if (childPid > 0) {
        try {
          process.kill(childPid, "SIGKILL");
        } catch {
          // The fixed bridge already reaped it.
        }
      }
      delete process.env.JFTSE_CHILD_PID_FILE;
      rmSync(childPidFile, { force: true });
    }
  });

  test("stable bridge error reports bounded nonzero exit detail", async () => {
    process.env.JFTSE_BRIDGE_FIXTURE = "exit";
    const error = await captureFailure(() => runBridge(["health"]));
    expect(error.code).toBe("BRIDGE_EXIT_FAILED");
    expect(error.detail?.length).toBeLessThanOrEqual(2_000);
  });

  test("stable bridge error classifies malformed final JSON", async () => {
    process.env.JFTSE_BRIDGE_FIXTURE = "invalid";
    const error = await captureFailure(() => runBridge(["health"]));
    expect(error.code).toBe("BRIDGE_INVALID_JSON");
    expect(error.detail).toContain("not-json");
  });

  test("bridge lifecycle returns the final JSON line", async () => {
    process.env.JFTSE_BRIDGE_FIXTURE = "valid";
    const result = await runBridge(["health"]);
    expect(result).toEqual({ ok: true, fixture: "valid" });
  });
});
