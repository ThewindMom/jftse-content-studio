import { existsSync, lstatSync, realpathSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";

export class PathPolicyError extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "PathPolicyError";
  }
}

function isPortableAbsolute(path: string): boolean {
  return isAbsolute(path) || /^[A-Za-z]:[\\/]/.test(path) || /^\\\\/.test(path);
}

function hasTraversal(path: string): boolean {
  return path.replaceAll("\\", "/").split("/").includes("..");
}

function isWithin(root: string, candidate: string): boolean {
  const child = relative(root, candidate);
  return child === "" || (!child.startsWith("..") && !isAbsolute(child));
}

function canonicalRoot(root: string): string | null {
  return existsSync(root) ? realpathSync(root) : null;
}

export function clientRelativePath(path: string): string {
  if (path.includes("\0")) throw new PathPolicyError("PATH_INVALID");
  if (isPortableAbsolute(path)) {
    throw new PathPolicyError("PATH_ABSOLUTE_FORBIDDEN");
  }
  if (hasTraversal(path)) {
    throw new PathPolicyError("PATH_TRAVERSAL_FORBIDDEN");
  }
  if (path.includes("\\")) {
    throw new PathPolicyError("PATH_BACKSLASH_FORBIDDEN");
  }
  return path;
}

export function archiveMemberName(path: string): string {
  const member = clientRelativePath(path);
  if (!member || member === "." || member.includes("/")) {
    throw new PathPolicyError("PATH_MEMBER_INVALID");
  }
  return member;
}

export function trustedReadPath(path: string, roots: string[]): string {
  if (!path || path.includes("\0")) throw new PathPolicyError("PATH_INVALID");
  if (hasTraversal(path)) {
    throw new PathPolicyError("PATH_TRAVERSAL_FORBIDDEN");
  }

  const trustedRoots = roots
    .map(canonicalRoot)
    .filter((root): root is string => root !== null);
  const candidates = isPortableAbsolute(path)
    ? [resolve(path)]
    : trustedRoots.map((root) => join(root, path));
  for (const candidate of candidates) {
    if (!existsSync(candidate)) continue;
    const canonical = realpathSync(candidate);
    if (trustedRoots.some((root) => isWithin(root, canonical))) return canonical;
  }
  throw new PathPolicyError("PATH_OUTSIDE_TRUSTED_ROOTS");
}

export function trustedRegularFilePath(path: string, roots: string[]): string {
  if (!path || path.includes("\0")) throw new PathPolicyError("PATH_INVALID");
  if (hasTraversal(path)) {
    throw new PathPolicyError("PATH_TRAVERSAL_FORBIDDEN");
  }

  const trustedRoots = roots
    .map(canonicalRoot)
    .filter((root): root is string => root !== null);
  for (const root of trustedRoots) {
    const candidate = isPortableAbsolute(path) ? resolve(path) : resolve(root, path);
    if (!isWithin(root, candidate) || !existsSync(candidate)) continue;

    let current = root;
    let safe = true;
    for (const part of relative(root, candidate).split(/[\\/]/).filter(Boolean)) {
      current = join(current, part);
      if (lstatSync(current).isSymbolicLink()) {
        safe = false;
        break;
      }
    }
    if (!safe || !lstatSync(candidate).isFile()) continue;
    const canonical = realpathSync(candidate);
    if (isWithin(root, canonical)) return canonical;
  }
  throw new PathPolicyError("PATH_OUTSIDE_TRUSTED_ROOTS");
}

function nearestExistingAncestor(path: string): string {
  let current = path;
  while (true) {
    try {
      if (lstatSync(current).isSymbolicLink()) {
        throw new PathPolicyError("OUTPUT_OUTSIDE_EXPORTS");
      }
      return realpathSync(current);
    } catch (error) {
      if (error instanceof PathPolicyError) throw error;
      const code = (error as NodeJS.ErrnoException).code;
      if (code !== "ENOENT" && code !== "ENOTDIR") throw error;
    }
    const parent = dirname(current);
    if (parent === current) break;
    current = parent;
  }
  throw new PathPolicyError("OUTPUT_PATH_INVALID");
}

export function exportOutputPath(path: string, exportsDir: string): string {
  if (!path || path.includes("\0")) throw new PathPolicyError("OUTPUT_PATH_INVALID");
  const root = realpathSync(exportsDir);
  const candidate = isPortableAbsolute(path) ? resolve(path) : resolve(root, path);
  if (!isWithin(root, candidate)) {
    throw new PathPolicyError("OUTPUT_OUTSIDE_EXPORTS");
  }
  const canonicalBoundary = nearestExistingAncestor(candidate);
  if (!isWithin(root, canonicalBoundary)) {
    throw new PathPolicyError("OUTPUT_OUTSIDE_EXPORTS");
  }
  return candidate;
}
