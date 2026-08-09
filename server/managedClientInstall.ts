import {
  lstatSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, extname, isAbsolute, relative, resolve, sep } from "node:path";
import { inside, sha256 } from "./clientHarnessTree.ts";
import type { ManagedClientProfileV1 } from "./clientHarnessTypes.ts";

export type ManagedInstallEntry = { source: string; destRelative: string };

export type ManagedClientInstallInput = {
  profile: ManagedClientProfileV1;
  installPlan: ManagedInstallEntry[];
  exportsRoot: string;
  managedStoreRoot: string;
  forbiddenRoots: string[];
};

export type ManagedClientInstallReceipt = {
  root: string;
  files: Array<{ source: string; destination: string; bytes: number; sha256: string }>;
};

export class ManagedClientInstallError extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "ManagedClientInstallError";
  }
}

function realDirectory(path: string, code: string): string {
  try {
    const real = realpathSync(resolve(path));
    if (!statSync(real).isDirectory()) throw new Error();
    return real;
  } catch {
    throw new ManagedClientInstallError(code);
  }
}

function resolvedIfPresent(path: string): string {
  try { return realpathSync(resolve(path)); } catch { return resolve(path); }
}

function assertNoSymlinkBetween(root: string, path: string, code: string): void {
  const rel = relative(root, path);
  if (!inside(root, path)) throw new ManagedClientInstallError(code);
  let cursor = root;
  for (const part of rel.split(sep).filter(Boolean)) {
    cursor = resolve(cursor, part);
    try {
      if (lstatSync(cursor).isSymbolicLink()) throw new ManagedClientInstallError(code);
    } catch (error) {
      if (error instanceof ManagedClientInstallError) throw error;
      break;
    }
  }
}

function destinationPath(root: string, declared: string): string {
  if (!declared || isAbsolute(declared) || declared.includes("\\")) {
    throw new ManagedClientInstallError("INSTALL_DESTINATION_INVALID");
  }
  const parts = declared.split("/");
  if (parts[0] !== "Res" || parts.length < 2 || parts.some((part) => !part || part === "." || part === "..")) {
    throw new ManagedClientInstallError("INSTALL_DESTINATION_INVALID");
  }
  const destination = resolve(root, ...parts);
  if (!inside(root, destination) || extname(destination).toLowerCase() !== ".res") {
    throw new ManagedClientInstallError("INSTALL_DESTINATION_INVALID");
  }
  return destination;
}

export function installManagedClientFiles(input: ManagedClientInstallInput): ManagedClientInstallReceipt {
  const profileRoot = realDirectory(
    input.profile.root,
    "INSTALL_ROOT_INVALID",
  );
  const root = realDirectory(
    resolve(profileRoot, "client"),
    "INSTALL_ROOT_INVALID",
  );
  const managedRoot = realDirectory(input.managedStoreRoot, "INSTALL_STORE_INVALID");
  const exportsRoot = realDirectory(input.exportsRoot, "INSTALL_EXPORTS_INVALID");
  if (
    lstatSync(resolve(input.profile.root)).isSymbolicLink() ||
    lstatSync(resolve(profileRoot, "client")).isSymbolicLink() ||
    !inside(managedRoot, profileRoot)
  ) {
    throw new ManagedClientInstallError("INSTALL_UNMANAGED_ROOT");
  }
  for (const forbidden of input.forbiddenRoots) {
    if (
      inside(resolvedIfPresent(forbidden), profileRoot) ||
      inside(resolvedIfPresent(forbidden), root)
    ) {
      throw new ManagedClientInstallError("INSTALL_FORBIDDEN_ROOT");
    }
  }

  const destinations = new Set<string>();
  const prepared = input.installPlan.map((entry) => {
    const source = resolve(exportsRoot, entry.source);
    const destination = destinationPath(root, entry.destRelative);
    if (!inside(exportsRoot, source) || extname(source).toLowerCase() !== ".res") {
      throw new ManagedClientInstallError("INSTALL_SOURCE_INVALID");
    }
    assertNoSymlinkBetween(exportsRoot, source, "INSTALL_SOURCE_SYMLINK");
    let sourceStat;
    try { sourceStat = lstatSync(source); } catch { throw new ManagedClientInstallError("INSTALL_SOURCE_INVALID"); }
    if (!sourceStat.isFile() || sourceStat.isSymbolicLink()) {
      throw new ManagedClientInstallError("INSTALL_SOURCE_INVALID");
    }
    assertNoSymlinkBetween(root, dirname(destination), "INSTALL_DESTINATION_SYMLINK");
    if (destinations.has(destination)) throw new ManagedClientInstallError("INSTALL_DESTINATION_DUPLICATE");
    destinations.add(destination);
    const bytes = readFileSync(source);
    return { source, destination, bytes, hash: sha256(bytes) };
  });

  const files = prepared.map(({ source, destination, bytes, hash }) => {
    mkdirSync(dirname(destination), { recursive: true });
    assertNoSymlinkBetween(root, dirname(destination), "INSTALL_DESTINATION_SYMLINK");
    try {
      const current = lstatSync(destination);
      if (!current.isFile() || current.isSymbolicLink()) throw new ManagedClientInstallError("INSTALL_DESTINATION_INVALID");
    } catch (error) {
      if (error instanceof ManagedClientInstallError) throw error;
    }
    const temporary = `${destination}.tmp-${crypto.randomUUID()}`;
    try {
      writeFileSync(temporary, bytes, { flag: "wx" });
      if (sha256(readFileSync(temporary)) !== hash) throw new ManagedClientInstallError("INSTALL_HASH_MISMATCH");
      renameSync(temporary, destination);
    } finally {
      rmSync(temporary, { force: true });
    }
    if (sha256(readFileSync(destination)) !== hash) throw new ManagedClientInstallError("INSTALL_HASH_MISMATCH");
    return { source, destination: relative(root, destination).split(sep).join("/"), bytes: bytes.length, sha256: hash };
  });
  return { root, files };
}
