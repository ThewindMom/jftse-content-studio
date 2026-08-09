import { realpathSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { boundedOutput, terminateGroup } from "./clientHarnessProcess.ts";
import {
  declaredPath,
  inside,
  restoreSnapshot,
  sha256,
  takeSnapshot,
  type Snapshot,
} from "./clientHarnessTree.ts";
import {
  ClientHarnessError,
  type ManagedClientOptions,
  type ManagedClientProfileV1,
  type ManagedClientResult,
} from "./clientHarnessTypes.ts";

export {
  ClientHarnessError,
  type ManagedClientOptions,
  type ManagedClientProfileV1,
  type ManagedClientResult,
  type TreeReceipt,
} from "./clientHarnessTypes.ts";

const DEFAULT_TIMEOUT_MS = 30_000;
const DEFAULT_OUTPUT_LIMIT = 64 * 1024;

export async function runManagedClient(
  profile: ManagedClientProfileV1,
  options: ManagedClientOptions,
): Promise<ManagedClientResult> {
  if (profile.version !== 1 || !profile.readiness) {
    throw new ClientHarnessError("INVALID_PROFILE", "Unsupported managed profile");
  }
  let root: string;
  try {
    root = realpathSync(resolve(profile.root));
  } catch {
    throw new ClientHarnessError("INVALID_ROOT", "Managed root must exist");
  }
  if (!statSync(root).isDirectory()) {
    throw new ClientHarnessError("INVALID_ROOT", "Managed root must be a directory");
  }
  for (const forbidden of options.forbiddenRoots) {
    let blocked = resolve(forbidden);
    try { blocked = realpathSync(blocked); } catch { /* Compare unresolved paths too. */ }
    if (inside(blocked, root)) {
      throw new ClientHarnessError("FORBIDDEN_ROOT", "Refusing forbidden client root");
    }
  }
  const launcher = declaredPath(root, profile.launcher);
  const capturePath = declaredPath(root, profile.capturePath);
  let actualLauncher: string;
  try { actualLauncher = realpathSync(launcher); } catch {
    throw new ClientHarnessError("INVALID_LAUNCHER", "Launcher does not exist");
  }
  if (!inside(root, actualLauncher) || !statSync(actualLauncher).isFile()) {
    throw new ClientHarnessError("INVALID_LAUNCHER", "Launcher escapes or is not a file");
  }
  if ((statSync(actualLauncher).mode & 0o111) === 0) {
    throw new ClientHarnessError("INVALID_LAUNCHER", "Launcher is not executable");
  }

  const beforeSnapshot = takeSnapshot(root);
  const limit = Math.max(1, options.outputLimit ?? DEFAULT_OUTPUT_LIMIT);
  const timeoutMs = Math.max(1, options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  const child = Bun.spawn([actualLauncher], {
    cwd: root,
    detached: true,
    stdin: "ignore",
    stdout: "pipe",
    stderr: "pipe",
  });
  const stdoutPromise = boundedOutput(child.stdout, profile.readiness, limit);
  const stderrPromise = boundedOutput(child.stderr, profile.readiness, limit);
  let timer: Timer | undefined;
  const outcome = await Promise.race([
    child.exited.then((code) => ({ code, timedOut: false })),
    new Promise<{ code: number; timedOut: true }>((resolveTimeout) => {
      timer = setTimeout(() => resolveTimeout({ code: -1, timedOut: true }), timeoutMs);
    }),
  ]);
  if (timer) clearTimeout(timer);
  terminateGroup(child.pid);
  const exitCode = outcome.timedOut ? await child.exited : outcome.code;
  const [stdout, stderr] = await Promise.all([stdoutPromise, stderrPromise]);
  const ready = stdout.ready || stderr.ready;

  let observed: Snapshot | null = null;
  let capture: ManagedClientResult["capture"] = null;
  try {
    observed = takeSnapshot(root);
    const captureEntry = observed.entries.find(
      (entry) => resolve(root, entry.path) === capturePath && entry.type === "file",
    );
    if (captureEntry?.bytes) capture = { relativePath: profile.capturePath, sha256: sha256(captureEntry.bytes) };
  } catch {
    // An unsafe post-run tree is always rolled back without reading escaped targets.
  }
  const failed = outcome.timedOut || exitCode !== 0 || !ready || !capture || !observed;
  if (failed) restoreSnapshot(root, beforeSnapshot);
  const after = failed ? takeSnapshot(root).receipt : observed!.receipt;
  return {
    status: failed ? "failed" : "passed",
    ready,
    timedOut: outcome.timedOut,
    exitCode,
    rolledBack: failed,
    stdout: stdout.text,
    stderr: stderr.text,
    capture,
    before: beforeSnapshot.receipt,
    after,
  };
}
