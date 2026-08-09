import {
  chmodSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { isAbsolute, relative, resolve } from "node:path";
import type { ManagedClientProfileV1 } from "./clientHarness.ts";

export type ManagedProfileMode = "pass" | "fail";

export type StoredManagedProfile = {
  name: string;
  mode: ManagedProfileMode;
  profile: ManagedClientProfileV1;
};

function safeName(name: string): string {
  if (!/^[a-z0-9][a-z0-9_-]{0,47}$/i.test(name)) {
    throw new Error("Profile name must use 1-48 letters, numbers, _ or -.");
  }
  return name;
}

function profileRoot(storeRoot: string, name: string): string {
  const root = resolve(storeRoot);
  const target = resolve(root, safeName(name));
  const rel = relative(root, target);
  if (!rel || rel.startsWith("..") || isAbsolute(rel)) {
    throw new Error("Managed profile path escapes the profile store.");
  }
  return target;
}

function launcherSource(mode: ManagedProfileMode): string {
  if (mode === "fail") {
    return `#!/bin/sh
set -eu
rm client/FantaTennis.exe
printf 'corrupt' > client/Res/runtime.dat
mkdir -p captures
printf 'partial' > captures/client.png
printf 'FAKE_CLIENT_FAILED\\n' >&2
exit 9
`;
  }
  return `#!/bin/sh
set -eu
mkdir -p captures
printf 'FAKE_CLIENT_READY\\n'
printf 'managed launcher diagnostic\\n' >&2
printf 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=' | base64 -d > captures/client.png
printf 'runtime-change' > client/Res/runtime.dat
`;
}

export function createManagedProfile(
  storeRoot: string,
  name: string,
  mode: ManagedProfileMode,
): StoredManagedProfile {
  if (mode !== "pass" && mode !== "fail") {
    throw new Error("Managed profile mode must be pass or fail.");
  }
  const root = profileRoot(storeRoot, name);
  rmSync(root, { recursive: true, force: true });
  mkdirSync(resolve(root, "client/Res"), { recursive: true });
  writeFileSync(resolve(root, "client/FantaTennis.exe"), "MZ-managed-fixture");
  writeFileSync(resolve(root, "client/jftse.dll"), "managed-dll-fixture");
  writeFileSync(resolve(root, "START-FAKE-CLIENT.sh"), launcherSource(mode));
  chmodSync(resolve(root, "START-FAKE-CLIENT.sh"), 0o755);
  const stored: StoredManagedProfile = {
    name,
    mode,
    profile: {
      version: 1,
      root,
      launcher: "START-FAKE-CLIENT.sh",
      capturePath: "captures/client.png",
      readiness: "FAKE_CLIENT_READY",
    },
  };
  writeFileSync(
    resolve(root, "profile.json"),
    `${JSON.stringify(stored, null, 2)}\n`,
  );
  return stored;
}

export function loadManagedProfile(
  storeRoot: string,
  name: string,
): StoredManagedProfile {
  const path = resolve(profileRoot(storeRoot, name), "profile.json");
  if (!existsSync(path)) throw new Error(`Managed profile not found: ${name}`);
  const stored = JSON.parse(readFileSync(path, "utf8")) as StoredManagedProfile;
  if (
    stored.name !== name ||
    stored.profile?.version !== 1 ||
    stored.profile.root !== profileRoot(storeRoot, name)
  ) {
    throw new Error(`Managed profile is malformed: ${name}`);
  }
  return stored;
}

export function listManagedProfiles(
  storeRoot: string,
): StoredManagedProfile[] {
  const root = resolve(storeRoot);
  if (!existsSync(root)) return [];
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => loadManagedProfile(root, entry.name))
    .sort((left, right) => left.name.localeCompare(right.name));
}

export function clearManagedProfiles(storeRoot: string): number {
  const profiles = listManagedProfiles(storeRoot);
  rmSync(resolve(storeRoot), { recursive: true, force: true });
  return profiles.length;
}
