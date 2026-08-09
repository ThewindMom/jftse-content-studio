export type ManagedClientProfileV1 = {
  version: 1;
  root: string;
  launcher: string;
  capturePath: string;
  readiness: string;
};

export type TreeReceipt = {
  sha256: string;
  files: Record<string, string>;
};

export type ManagedClientResult = {
  status: "passed" | "failed";
  ready: boolean;
  timedOut: boolean;
  exitCode: number;
  rolledBack: boolean;
  stdout: string;
  stderr: string;
  capture: { relativePath: string; sha256: string } | null;
  before: TreeReceipt;
  after: TreeReceipt;
};

export type ManagedClientOptions = {
  forbiddenRoots: string[];
  timeoutMs?: number;
  outputLimit?: number;
};

export class ClientHarnessError extends Error {
  constructor(
    readonly code:
      | "INVALID_PROFILE"
      | "INVALID_ROOT"
      | "FORBIDDEN_ROOT"
      | "PATH_ESCAPE"
      | "SYMLINK_ESCAPE"
      | "INVALID_LAUNCHER",
    message: string,
  ) {
    super(message);
    this.name = "ClientHarnessError";
  }
}
