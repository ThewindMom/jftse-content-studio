import { afterEach, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import {
  chmodSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readlinkSync,
  readdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  ClientHarnessError,
  runManagedClient,
  type ManagedClientProfileV1,
} from "../server/clientHarness.ts";

const roots: string[] = [];

function fixture(script: string): { root: string; profile: ManagedClientProfileV1 } {
  const root = mkdtempSync(join(tmpdir(), "jftse-managed-client-"));
  roots.push(root);
  mkdirSync(join(root, "client", "Res"), { recursive: true });
  writeFileSync(join(root, "client", "FantaTennis.exe"), "MZ-fixture");
  const launcher = join(root, "START-FAKE-CLIENT.sh");
  writeFileSync(launcher, `#!/bin/sh\nset -eu\n${script}\n`);
  chmodSync(launcher, 0o755);
  return {
    root,
    profile: {
      version: 1,
      root,
      launcher: "START-FAKE-CLIENT.sh",
      capturePath: "captures/client.png",
      readiness: "FAKE_CLIENT_READY",
    },
  };
}

function byteTreeHash(root: string): string {
  const hash = createHash("sha256");
  const walk = (directory: string, prefix = "") => {
    for (const name of readdirSync(directory).sort()) {
      const path = join(directory, name);
      const relative = prefix ? `${prefix}/${name}` : name;
      const stat = lstatSync(path);
      hash.update(`${relative}\0${stat.mode & 0o7777}\0`);
      if (stat.isDirectory()) {
        hash.update("d\0");
        walk(path, relative);
      } else if (stat.isSymbolicLink()) {
        hash.update(`l\0${readlinkSync(path)}\0`);
      } else {
        hash.update("f\0").update(readFileSync(path));
      }
    }
  };
  walk(root);
  return hash.digest("hex");
}

function isRunning(pid: number): boolean {
  try {
    return !/^State:\s+Z/m.test(readFileSync(`/proc/${pid}/status`, "utf8"));
  } catch {
    return false;
  }
}

async function captureHarnessError(
  work: () => Promise<unknown>,
): Promise<ClientHarnessError> {
  try {
    await work();
  } catch (error) {
    if (error instanceof ClientHarnessError) return error;
    throw error;
  }
  throw new Error("expected client harness failure");
}

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

describe("managed fake-client lifecycle", () => {
  test("captures readiness, bounded logs, screenshot, and tree receipts", async () => {
    const { root, profile } = fixture(`
mkdir -p captures
printf 'prefix FAKE_CLIENT_'
printf 'READY suffix\\n'
printf 'launcher diagnostic\\n' >&2
printf '\\211PNG\\r\\nfixture' > captures/client.png
printf 'changed' > client/Res/runtime.dat
`);

    const result = await runManagedClient(profile, {
      forbiddenRoots: [],
      outputLimit: 128,
      timeoutMs: 2_000,
    });

    expect(result.status).toBe("passed");
    expect(result.ready).toBe(true);
    expect(result.exitCode).toBe(0);
    expect(result.rolledBack).toBe(false);
    expect(result.stdout).toContain("FAKE_CLIENT_READY");
    expect(result.stderr).toContain("launcher diagnostic");
    expect(result.capture?.relativePath).toBe("captures/client.png");
    expect(result.capture?.sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(result.before.sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(result.after.sha256).not.toBe(result.before.sha256);
    expect(readFileSync(join(root, "captures/client.png")).subarray(0, 4)).toEqual(
      Buffer.from([0x89, 0x50, 0x4e, 0x47]),
    );
  });

  test("restores the byte-identical pre-run tree after a failed launch", async () => {
    const { root, profile } = fixture(`
rm client/FantaTennis.exe
printf 'corrupt' > client/Res/runtime.dat
mkdir -p captures
printf 'partial' > captures/client.png
printf 'launch failed\\n' >&2
exit 9
`);
    chmodSync(join(root, "client", "FantaTennis.exe"), 0o640);
    const originalHash = byteTreeHash(root);

    const result = await runManagedClient(profile, {
      forbiddenRoots: [],
      timeoutMs: 2_000,
    });

    expect(result.status).toBe("failed");
    expect(result.exitCode).toBe(9);
    expect(result.ready).toBe(false);
    expect(result.rolledBack).toBe(true);
    expect(result.before.sha256).toBe(result.after.sha256);
    expect(byteTreeHash(root)).toBe(originalHash);
    expect(readFileSync(join(root, "client", "FantaTennis.exe"), "utf8")).toBe(
      "MZ-fixture",
    );
    expect(lstatSync(join(root, "client", "FantaTennis.exe")).mode & 0o777).toBe(
      0o640,
    );
    expect(existsSync(join(root, "captures"))).toBe(false);
  });

  test("refuses forbidden roots, aliases to them, and tree symlink escapes", async () => {
    const forbidden = fixture("touch SHOULD_NOT_RUN");
    const aliasParent = mkdtempSync(join(tmpdir(), "jftse-managed-alias-"));
    roots.push(aliasParent);
    const alias = join(aliasParent, "client-alias");
    symlinkSync(forbidden.root, alias, "dir");

    for (const root of [forbidden.root, alias]) {
      const profile = { ...forbidden.profile, root };
      const error = await captureHarnessError(() =>
        runManagedClient(profile, { forbiddenRoots: [forbidden.root] }),
      );
      expect(error.code).toBe("FORBIDDEN_ROOT");
    }
    expect(existsSync(join(forbidden.root, "SHOULD_NOT_RUN"))).toBe(false);

    const escaped = fixture("exit 0");
    const outside = mkdtempSync(join(tmpdir(), "jftse-managed-outside-"));
    roots.push(outside);
    symlinkSync(outside, join(escaped.root, "client", "escape"), "dir");
    const error = await captureHarnessError(() =>
      runManagedClient(escaped.profile, { forbiddenRoots: [forbidden.root] }),
    );
    expect(error.code).toBe("SYMLINK_ESCAPE");
  });

  test("terminates the launched process group without leaking a grandchild", async () => {
    const { root, profile } = fixture(`
bun -e 'setInterval(() => {}, 1000)' &
child=$!
printf '%s' "$child" > grandchild.pid
printf 'CHILD_PID=%s\\n' "$child"
printf 'no readiness here\\n'
exit 7
`);

    const result = await runManagedClient(profile, {
      forbiddenRoots: [],
      timeoutMs: 2_000,
    });
    const pid = Number(result.stdout.match(/CHILD_PID=(\d+)/)?.[1] ?? 0);

    expect(result.status).toBe("failed");
    expect(result.rolledBack).toBe(true);
    expect(pid).toBeGreaterThan(0);
    expect(isRunning(pid)).toBe(false);
    expect(existsSync(join(root, "grandchild.pid"))).toBe(false);
  });
});
