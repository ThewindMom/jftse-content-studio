import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { runBridgeWithPayload } from "./bridge.ts";
import { runManagedClient } from "./clientHarness.ts";
import { restoreSnapshot, takeSnapshot, type Snapshot } from "./clientHarnessTree.ts";
import type { ManagedClientProfileV1, ManagedClientResult, TreeReceipt } from "./clientHarnessTypes.ts";
import {
  installManagedClientFiles,
  type ManagedClientInstallInput,
  type ManagedClientInstallReceipt,
  type ManagedInstallEntry,
} from "./managedClientInstall.ts";

export type ContentPackBuildReceipt = Record<string, unknown> & {
  ok: true;
  outDir: string;
  installPlan: ManagedInstallEntry[];
  sqlPath?: string | null;
};

export type SqlPipelineReceipt = Record<string, unknown> & {
  ok: boolean;
  dryRun?: boolean;
  applied?: boolean;
  audit?: { safe?: boolean; [key: string]: unknown };
};

export type ClientHarnessPipelineDependencies = {
  build(payload: Record<string, unknown>, outDir: string): Promise<ContentPackBuildReceipt>;
  install(input: ManagedClientInstallInput): Promise<ManagedClientInstallReceipt> | ManagedClientInstallReceipt;
  sql(input: { sqlPath: string; dryRun: boolean }): Promise<SqlPipelineReceipt>;
  launch(profile: ManagedClientProfileV1, options: { forbiddenRoots: string[] }): Promise<ManagedClientResult>;
};

export type PipelineStage = "build" | "install" | "sqlAudit" | "sqlApply" | "launch";
type StageReceipt<T> =
  | { status: "passed"; value: T }
  | { status: "failed"; error: string; value?: T }
  | { status: "skipped"; reason: string };

export type ClientHarnessPipelineResult = {
  status: "passed" | "failed";
  failedStage: PipelineStage | null;
  receipts: {
    build: StageReceipt<ContentPackBuildReceipt>;
    install: StageReceipt<ManagedClientInstallReceipt>;
    sqlAudit: StageReceipt<SqlPipelineReceipt>;
    sqlApply: StageReceipt<SqlPipelineReceipt>;
    launch: StageReceipt<ManagedClientResult>;
  };
  before: TreeReceipt;
  after: TreeReceipt;
  rolledBack: boolean;
  launch: ManagedClientResult | null;
  databaseMayHaveApplied: boolean;
  realClientAutomation: false;
};

export type ClientHarnessPipelineInput = {
  profile: ManagedClientProfileV1;
  buildPayload: Record<string, unknown>;
  applySql: boolean;
  forbiddenRoots: string[];
  managedStoreRoot: string;
  exportsRoot: string;
  dependencies?: Partial<ClientHarnessPipelineDependencies>;
};

const skipped = (reason: string): StageReceipt<never> => ({ status: "skipped", reason });

async function defaultBuild(payload: Record<string, unknown>, outDir: string): Promise<ContentPackBuildReceipt> {
  mkdirSync(outDir, { recursive: true });
  const result = await runBridgeWithPayload("client-harness-pack", payload, (payloadPath) => [
    "content-pack-build", "--payload", payloadPath, "--out-dir", outDir,
  ], { timeoutMs: 300_000 });
  if (result.ok !== true || typeof result.outDir !== "string" || !Array.isArray(result.installPlan)) {
    throw new Error(typeof result.error === "string" ? result.error : "CONTENT_PACK_BUILD_FAILED");
  }
  return result as ContentPackBuildReceipt;
}

const defaults: ClientHarnessPipelineDependencies = {
  build: defaultBuild,
  install: installManagedClientFiles,
  sql: ({ sqlPath, dryRun }) => runBridgeWithPayload("client-harness-sql", { path: sqlPath, dryRun },
    (payloadPath) => ["sql-apply", "--payload", payloadPath]) as Promise<SqlPipelineReceipt>,
  launch: (profile, options) => runManagedClient(profile, options),
};

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function restore(root: string, before: Snapshot): TreeReceipt {
  restoreSnapshot(root, before);
  const receipt = takeSnapshot(root).receipt;
  if (receipt.sha256 !== before.receipt.sha256) throw new Error("PIPELINE_ROLLBACK_MISMATCH");
  return receipt;
}

export async function runClientHarnessPipeline(
  input: ClientHarnessPipelineInput,
  injected: Partial<ClientHarnessPipelineDependencies> = {},
): Promise<ClientHarnessPipelineResult> {
  const dependencies = { ...defaults, ...input.dependencies, ...injected };
  const root = input.profile.root;
  const beforeSnapshot = takeSnapshot(root);
  const receipts: ClientHarnessPipelineResult["receipts"] = {
    build: skipped("not reached"), install: skipped("not reached"),
    sqlAudit: skipped("not reached"), sqlApply: skipped("not reached"), launch: skipped("not reached"),
  };
  let failedStage: PipelineStage | null = null;
  let launch: ManagedClientResult | null = null;
  let databaseMayHaveApplied = false;

  const fail = (stage: PipelineStage, error: unknown, value?: unknown): ClientHarnessPipelineResult => {
    failedStage = stage;
    receipts[stage] = { status: "failed", error: message(error), ...(value === undefined ? {} : { value }) } as never;
    return {
      status: "failed", failedStage, receipts, before: beforeSnapshot.receipt,
      after: restore(root, beforeSnapshot), rolledBack: true, launch,
      databaseMayHaveApplied, realClientAutomation: false,
    };
  };

  let build: ContentPackBuildReceipt;
  try {
    const outDir = join(input.exportsRoot, `client-harness-${crypto.randomUUID()}`);
    build = await dependencies.build(input.buildPayload, outDir);
    if (build.ok !== true || !Array.isArray(build.installPlan)) throw new Error("CONTENT_PACK_BUILD_FAILED");
    receipts.build = { status: "passed", value: build };
  } catch (error) { return fail("build", error); }

  try {
    const installed = await dependencies.install({
      profile: input.profile, installPlan: build.installPlan, exportsRoot: input.exportsRoot,
      managedStoreRoot: input.managedStoreRoot, forbiddenRoots: input.forbiddenRoots,
    });
    receipts.install = { status: "passed", value: installed };
  } catch (error) { return fail("install", error); }

  if (typeof build.sqlPath === "string" && build.sqlPath.length > 0) {
    let audit: SqlPipelineReceipt;
    try {
      audit = await dependencies.sql({ sqlPath: build.sqlPath, dryRun: true });
      if (audit.ok !== true || audit.dryRun !== true || audit.applied === true || audit.audit?.safe !== true) {
        return fail("sqlAudit", "SQL_AUDIT_UNSAFE", audit);
      }
      receipts.sqlAudit = { status: "passed", value: audit };
    } catch (error) { return fail("sqlAudit", error); }

    if (input.applySql) {
      databaseMayHaveApplied = true;
      try {
        const applied = await dependencies.sql({ sqlPath: build.sqlPath, dryRun: false });
        if (applied.ok !== true || applied.applied !== true) return fail("sqlApply", "SQL_APPLY_FAILED", applied);
        receipts.sqlApply = { status: "passed", value: applied };
      } catch (error) { return fail("sqlApply", error); }
    } else receipts.sqlApply = skipped("applySql is false");
  } else {
    receipts.sqlAudit = skipped("build returned no SQL");
    receipts.sqlApply = skipped("build returned no SQL");
  }

  try {
    launch = await dependencies.launch(input.profile, { forbiddenRoots: input.forbiddenRoots });
    if (launch.status === "failed") return fail("launch", "CLIENT_LAUNCH_FAILED", launch);
    receipts.launch = { status: "passed", value: launch };
  } catch (error) { return fail("launch", error); }

  return {
    status: "passed", failedStage: null, receipts, before: beforeSnapshot.receipt,
    after: takeSnapshot(root).receipt, rolledBack: false, launch,
    databaseMayHaveApplied, realClientAutomation: false,
  };
}
