import { createHash } from "node:crypto";
import {
  chmodSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  readlinkSync,
  realpathSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { ClientHarnessError, type TreeReceipt } from "./clientHarnessTypes.ts";

type StoredEntry = {
  path: string;
  type: "directory" | "file" | "symlink";
  mode: number;
  bytes?: Buffer;
  link?: string;
};

export type Snapshot = {
  entries: StoredEntry[];
  receipt: TreeReceipt;
  rootMode: number;
};

export function inside(root: string, path: string): boolean {
  const rel = relative(root, path);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

export function declaredPath(root: string, value: string): string {
  if (!value || isAbsolute(value)) {
    throw new ClientHarnessError("INVALID_PROFILE", "Profile paths must be relative");
  }
  const path = resolve(root, value);
  if (!inside(root, path)) {
    throw new ClientHarnessError("PATH_ESCAPE", `Path escapes managed root: ${value}`);
  }
  return path;
}

export function sha256(value: Uint8Array | string): string {
  return createHash("sha256").update(value).digest("hex");
}

export function takeSnapshot(root: string): Snapshot {
  const entries: StoredEntry[] = [];
  const files: Record<string, string> = {};
  const walk = (directory: string) => {
    for (const name of readdirSync(directory).sort()) {
      const path = resolve(directory, name);
      const rel = relative(root, path).split("\\").join("/");
      const stat = lstatSync(path);
      const mode = stat.mode & 0o7777;
      if (stat.isSymbolicLink()) {
        let target: string;
        try {
          target = realpathSync(path);
        } catch {
          throw new ClientHarnessError("SYMLINK_ESCAPE", `Broken symlink: ${rel}`);
        }
        if (!inside(root, target)) {
          throw new ClientHarnessError("SYMLINK_ESCAPE", `Symlink escapes root: ${rel}`);
        }
        const link = readlinkSync(path);
        entries.push({ path: rel, type: "symlink", mode, link });
        files[rel] = sha256(link);
      } else if (stat.isDirectory()) {
        entries.push({ path: rel, type: "directory", mode });
        walk(path);
      } else if (stat.isFile()) {
        const bytes = readFileSync(path);
        entries.push({ path: rel, type: "file", mode, bytes });
        files[rel] = sha256(bytes);
      } else {
        throw new ClientHarnessError("INVALID_ROOT", `Unsupported tree entry: ${rel}`);
      }
    }
  };
  walk(root);
  const manifest = entries.map((entry) => [
    entry.path,
    entry.type,
    entry.mode,
    entry.type === "file" ? files[entry.path] : entry.link ?? "",
  ]);
  return {
    entries,
    receipt: { sha256: sha256(JSON.stringify(manifest)), files },
    rootMode: statSync(root).mode & 0o7777,
  };
}

export function restoreSnapshot(root: string, snapshot: Snapshot): void {
  rmSync(root, { recursive: true, force: true });
  mkdirSync(root, { recursive: true, mode: snapshot.rootMode });
  for (const entry of snapshot.entries.filter((item) => item.type === "directory")) {
    const path = resolve(root, entry.path);
    mkdirSync(path, { recursive: true, mode: entry.mode });
    chmodSync(path, entry.mode);
  }
  for (const entry of snapshot.entries.filter((item) => item.type !== "directory")) {
    const path = resolve(root, entry.path);
    mkdirSync(dirname(path), { recursive: true });
    if (entry.type === "symlink") symlinkSync(entry.link!, path);
    else {
      writeFileSync(path, entry.bytes!);
      chmodSync(path, entry.mode);
    }
  }
  chmodSync(root, snapshot.rootMode);
}
