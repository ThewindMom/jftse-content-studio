import { afterEach, describe, expect, test } from "bun:test";
import {
  chmodSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { takeSnapshot } from "../server/clientHarnessTree.ts";
import { installManagedClientFiles } from "../server/managedClientInstall.ts";
import {
  runClientHarnessPipeline,
  type ClientHarnessPipelineDependencies,
} from "../server/clientHarnessPipeline.ts";
import type { ManagedClientProfileV1, ManagedClientResult } from "../server/clientHarness.ts";

const cleanup: string[] = [];

function fixtures() {
  const base = mkdtempSync(join(tmpdir(), "jftse-pipeline-"));
  cleanup.push(base);
  const managedStoreRoot = join(base, "managed");
  const exportsRoot = join(base, "exports");
  const root = join(managedStoreRoot, "profile");
  mkdirSync(join(root, "client", "Res"), { recursive: true });
  mkdirSync(exportsRoot, { recursive: true });
  writeFileSync(join(root, "existing.dat"), "before");
  const launcher = join(root, "launch.sh");
  writeFileSync(launcher, "#!/bin/sh\nexit 0\n");
  chmodSync(launcher, 0o755);
  const profile: ManagedClientProfileV1 = {
    version: 1, root, launcher: "launch.sh",
    capturePath: "captures/client.png", readiness: "READY",
  };
  return { base, managedStoreRoot, exportsRoot, root, profile };
}

function launchResult(root: string, status: "passed" | "failed" = "passed"): ManagedClientResult {
  const receipt = takeSnapshot(root).receipt;
  return {
    status, ready: status === "passed", timedOut: false, exitCode: status === "passed" ? 0 : 9,
    rolledBack: status === "failed", stdout: "READY", stderr: "",
    capture: status === "passed" ? { relativePath: "captures/client.png", sha256: "a".repeat(64) } : null,
    before: receipt, after: receipt,
  };
}

function stages(
  fixture: ReturnType<typeof fixtures>,
  order: string[],
  overrides: Partial<ClientHarnessPipelineDependencies> = {},
): ClientHarnessPipelineDependencies {
  const source = join(fixture.exportsRoot, "pack", "Item.res");
  const sqlPath = join(fixture.exportsRoot, "pack", "content-pack.sql");
  return {
    build: async (_payload, outDir) => {
      order.push("build");
      mkdirSync(outDir, { recursive: true });
      mkdirSync(join(fixture.exportsRoot, "pack"), { recursive: true });
      writeFileSync(source, "resource");
      writeFileSync(sqlPath, "INSERT INTO S_Product (id) VALUES (1);");
      return { ok: true, outDir, sqlPath, installPlan: [{ source, destRelative: "Res/Script/Item.res" }] };
    },
    install: async (input) => { order.push("install"); return installManagedClientFiles(input); },
    sql: async ({ dryRun }) => {
      order.push(dryRun ? "audit" : "apply");
      return { ok: true, dryRun, applied: !dryRun, audit: { safe: true } };
    },
    launch: async (profile) => { order.push("launch"); return launchResult(profile.root); },
    ...overrides,
  };
}

async function run(
  fixture: ReturnType<typeof fixtures>,
  dependencies: ClientHarnessPipelineDependencies,
  applySql = true,
) {
  return runClientHarnessPipeline({
    profile: fixture.profile, buildPayload: { name: "test" }, applySql,
    forbiddenRoots: [], managedStoreRoot: fixture.managedStoreRoot,
    exportsRoot: fixture.exportsRoot, dependencies,
  });
}

afterEach(() => { for (const path of cleanup.splice(0)) rmSync(path, { recursive: true, force: true }); });

describe("client harness pipeline", () => {
  test("runs build, install, audit, apply, and captured launch in order", async () => {
    const fixture = fixtures();
    const order: string[] = [];
    const result = await run(fixture, stages(fixture, order));
    expect(order).toEqual(["build", "install", "audit", "apply", "launch"]);
    expect(result.status).toBe("passed");
    expect(
      readFileSync(join(fixture.root, "client/Res/Script/Item.res"), "utf8"),
    ).toBe("resource");
    expect(result.failedStage).toBeNull();
    expect(result.launch?.capture?.relativePath).toBe("captures/client.png");
    expect(result.receipts.sqlAudit.status).toBe("passed");
    expect(result.databaseMayHaveApplied).toBe(true);
    expect(result.realClientAutomation).toBe(false);
    expect(result.after.sha256).not.toBe(result.before.sha256);
  });

  test("unsafe SQL prevents launch and restores the pre-pipeline tree", async () => {
    const fixture = fixtures();
    const before = takeSnapshot(fixture.root).receipt.sha256;
    const order: string[] = [];
    const deps = stages(fixture, order, {
      sql: async ({ dryRun }) => {
        order.push(dryRun ? "audit" : "apply");
        return { ok: false, dryRun, applied: false, audit: { safe: false } };
      },
    });
    const result = await run(fixture, deps);
    expect(order).toEqual(["build", "install", "audit"]);
    expect(result.failedStage).toBe("sqlAudit");
    expect(result.rolledBack).toBe(true);
    expect(result.after.sha256).toBe(before);
    expect(result.databaseMayHaveApplied).toBe(false);
  });

  test("install failure rolls back", async () => {
    const fixture = fixtures();
    const before = takeSnapshot(fixture.root).receipt.sha256;
    const order: string[] = [];
    const result = await run(fixture, stages(fixture, order, {
      install: async () => { order.push("install"); writeFileSync(join(fixture.root, "partial"), "x"); throw new Error("install failed"); },
    }));
    expect(result.failedStage).toBe("install");
    expect(result.after.sha256).toBe(before);
    expect(order).toEqual(["build", "install"]);
  });

  test("apply failure reports database risk and rolls back", async () => {
    const fixture = fixtures();
    const before = takeSnapshot(fixture.root).receipt.sha256;
    const order: string[] = [];
    const result = await run(fixture, stages(fixture, order, {
      sql: async ({ dryRun }) => {
        order.push(dryRun ? "audit" : "apply");
        if (!dryRun) throw new Error("connection lost");
        return { ok: true, dryRun: true, applied: false, audit: { safe: true } };
      },
    }));
    expect(result.failedStage).toBe("sqlApply");
    expect(result.databaseMayHaveApplied).toBe(true);
    expect(result.after.sha256).toBe(before);
    expect(order).toEqual(["build", "install", "audit", "apply"]);
  });

  test("launch failure restores the outer pre-install hash", async () => {
    const fixture = fixtures();
    const before = takeSnapshot(fixture.root).receipt.sha256;
    const order: string[] = [];
    const result = await run(fixture, stages(fixture, order, {
      launch: async (profile) => { order.push("launch"); return launchResult(profile.root, "failed"); },
    }), false);
    expect(result.failedStage).toBe("launch");
    expect(result.launch?.rolledBack).toBe(true);
    expect(result.after.sha256).toBe(before);
  });
});

describe("managed content-pack install", () => {
  test("rejects traversal, symlink sources, and forbidden roots", async () => {
    const fixture = fixtures();
    const source = join(fixture.exportsRoot, "safe.res");
    writeFileSync(source, "safe");
    const input = { profile: fixture.profile, exportsRoot: fixture.exportsRoot,
      managedStoreRoot: fixture.managedStoreRoot, forbiddenRoots: [] as string[],
      installPlan: [{ source, destRelative: "../escape.res" }] };
    expect(() => installManagedClientFiles(input)).toThrow("INSTALL_DESTINATION_INVALID");
    const link = join(fixture.exportsRoot, "link.res");
    symlinkSync(source, link);
    expect(() => installManagedClientFiles({ ...input, installPlan: [{ source: link, destRelative: "Res/link.res" }] })).toThrow("INSTALL_SOURCE_SYMLINK");
    expect(() => installManagedClientFiles({ ...input, forbiddenRoots: [fixture.root], installPlan: [{ source, destRelative: "Res/safe.res" }] })).toThrow("INSTALL_FORBIDDEN_ROOT");
  });
});
