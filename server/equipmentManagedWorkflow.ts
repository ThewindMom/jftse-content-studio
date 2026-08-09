import {
  existsSync,
  lstatSync,
  readFileSync,
  statSync,
} from "node:fs";
import { join, resolve } from "node:path";
import { runBridgeWithPayload } from "./bridge.ts";
import { loadManagedProfile } from "./clientProfileStore.ts";
import { inside, sha256, takeSnapshot } from "./clientHarnessTree.ts";
import {
  installManagedClientFiles,
  type ManagedClientInstallReceipt,
  type ManagedInstallEntry,
} from "./managedClientInstall.ts";
import { exportOutputPath, trustedRegularFilePath } from "./pathPolicy.ts";

type JsonObject = Record<string, unknown>;
type SqlAuditReceipt = JsonObject & {
  ok: boolean;
  dryRun?: boolean;
  applied?: boolean;
  audit?: JsonObject;
};

type EquipmentPackageDescriptor = {
  packageId: string;
  installPlan: ManagedInstallEntry[];
  sqlPath: string;
};

type EquipmentWorkflowContext = {
  exportsRoot: string;
  managedStoreRoot: string;
  forbiddenRoots: string[];
};

export class EquipmentManagedWorkflowError extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "EquipmentManagedWorkflowError";
  }
}

function object(value: unknown, code: string): JsonObject {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new EquipmentManagedWorkflowError(code);
  }
  return value as JsonObject;
}

function requiredString(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new EquipmentManagedWorkflowError(code);
  }
  return value;
}

function loadDescriptor(
  packageId: string,
  exportsRoot: string,
): EquipmentPackageDescriptor {
  if (!/^equipment-creator-[a-z0-9-]+$/i.test(packageId)) {
    throw new EquipmentManagedWorkflowError("EQUIPMENT_PACKAGE_ID_INVALID");
  }
  const root = exportOutputPath(packageId, exportsRoot);
  const manifestPath = trustedRegularFilePath(
    join(root, "creator-manifest.json"),
    [exportsRoot],
  );
  const manifest = object(
    JSON.parse(readFileSync(manifestPath, "utf8")),
    "EQUIPMENT_MANIFEST_INVALID",
  );
  const contentPack = object(
    manifest.contentPack,
    "EQUIPMENT_CONTENT_PACK_INVALID",
  );
  const receipt = object(
    contentPack.receipt,
    "EQUIPMENT_CONTENT_PACK_INVALID",
  );
  if (!Array.isArray(receipt.installPlan) || receipt.installPlan.length === 0) {
    throw new EquipmentManagedWorkflowError("EQUIPMENT_INSTALL_PLAN_INVALID");
  }
  const installPlan = receipt.installPlan.map((entry) => {
    const row = object(entry, "EQUIPMENT_INSTALL_PLAN_INVALID");
    return {
      source: requiredString(
        row.source,
        "EQUIPMENT_INSTALL_SOURCE_INVALID",
      ),
      destRelative: requiredString(
        row.destRelative,
        "EQUIPMENT_INSTALL_DESTINATION_INVALID",
      ),
    };
  });
  const sqlPath = trustedRegularFilePath(
    requiredString(receipt.sqlPath, "EQUIPMENT_SQL_PATH_INVALID"),
    [exportsRoot],
  );
  return { packageId, installPlan, sqlPath };
}

async function auditSql(sqlPath: string): Promise<SqlAuditReceipt> {
  return runBridgeWithPayload(
    "equipment-creator-sql-audit",
    { path: sqlPath, dryRun: true },
    (payloadPath) => ["sql-apply", "--payload", payloadPath],
  ) as Promise<SqlAuditReceipt>;
}

function assertSafeAudit(receipt: SqlAuditReceipt): void {
  if (
    receipt.ok !== true ||
    receipt.dryRun !== true ||
    receipt.applied === true ||
    object(receipt.audit, "EQUIPMENT_SQL_AUDIT_FAILED").safe !== true
  ) {
    throw new EquipmentManagedWorkflowError("EQUIPMENT_SQL_AUDIT_FAILED");
  }
}

export async function auditEquipmentPackage(
  packageId: string,
  context: EquipmentWorkflowContext,
) {
  const descriptor = loadDescriptor(packageId, context.exportsRoot);
  const receipt = await auditSql(descriptor.sqlPath);
  assertSafeAudit(receipt);
  return {
    ok: true,
    packageId,
    audit: receipt.audit,
    sqlPath: descriptor.sqlPath,
    sqlApplyEligible: true,
    receipt,
  };
}

export async function installEquipmentPackage(
  packageId: string,
  profileName: string,
  context: EquipmentWorkflowContext,
) {
  const descriptor = loadDescriptor(packageId, context.exportsRoot);
  const stored = loadManagedProfile(context.managedStoreRoot, profileName);
  const rollbackReceipt = takeSnapshot(stored.profile.root).receipt;
  const install = installManagedClientFiles({
    profile: stored.profile,
    installPlan: descriptor.installPlan,
    exportsRoot: context.exportsRoot,
    managedStoreRoot: context.managedStoreRoot,
    forbiddenRoots: context.forbiddenRoots,
  });
  return {
    ok: true,
    packageId,
    profileName,
    install,
    rollbackReceipt,
  };
}

function installedChecks(
  descriptor: EquipmentPackageDescriptor,
  clientRoot: string,
  exportsRoot: string,
) {
  return descriptor.installPlan.map((entry) => {
    const source = trustedRegularFilePath(entry.source, [exportsRoot]);
    const destination = resolve(clientRoot, ...entry.destRelative.split("/"));
    const safeDestination =
      inside(clientRoot, destination) &&
      existsSync(destination) &&
      !lstatSync(destination).isSymbolicLink() &&
      statSync(destination).isFile();
    const matches =
      safeDestination &&
      sha256(readFileSync(source)) === sha256(readFileSync(destination));
    return {
      id: `installed-${entry.destRelative}`,
      ok: matches,
      label: `Installed bytes match -> ${entry.destRelative}`,
    };
  });
}

export async function preflightEquipmentPackage(
  packageId: string,
  profileName: string,
  context: EquipmentWorkflowContext,
) {
  const descriptor = loadDescriptor(packageId, context.exportsRoot);
  const stored = loadManagedProfile(context.managedStoreRoot, profileName);
  const clientRoot = resolve(stored.profile.root, "client");
  const sql = await auditSql(descriptor.sqlPath);
  assertSafeAudit(sql);
  const launcher = resolve(stored.profile.root, stored.profile.launcher);
  const checks = [
    {
      id: "managed-profile",
      ok: inside(context.managedStoreRoot, stored.profile.root),
      label: `Managed profile -> ${profileName}`,
    },
    {
      id: "client-exe",
      ok: existsSync(resolve(clientRoot, "FantaTennis.exe")),
      label: "Managed FantaTennis.exe is present",
    },
    {
      id: "client-dll",
      ok: existsSync(resolve(clientRoot, "jftse.dll")),
      label: "Managed jftse.dll is present",
    },
    ...installedChecks(descriptor, clientRoot, context.exportsRoot),
    {
      id: "sql-audit",
      ok: sql.audit?.safe === true,
      label: "Generated item SQL passed the INSERT-only audit",
    },
    {
      id: "launcher",
      ok:
        inside(stored.profile.root, launcher) &&
        existsSync(launcher) &&
        !lstatSync(launcher).isSymbolicLink(),
      label: "Managed launcher is present",
    },
  ];
  const miss = checks.filter((check) => !check.ok).map((check) => check.id);
  const preflightPassed = miss.length === 0;
  return {
    ok: preflightPassed,
    packageId,
    profileName,
    preflightPassed,
    pass: checks.filter((check) => check.ok).map((check) => check.id),
    miss,
    checks,
    manualHandoff:
      "Managed preflight passed. Real DX9 verification remains manual: open the local client, log in, equip the authored item, and visually inspect it.",
    handoff: {
      packageId,
      profileName,
      targetClient: clientRoot,
      launcher,
      realClientAutomation: false,
      manualDx9Required: true,
    },
  };
}
