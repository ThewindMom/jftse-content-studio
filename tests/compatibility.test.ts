import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  buildCompatibilityReport,
  materializeCompatibilityFixtures,
} from "../server/compatibility.ts";

const root = join(import.meta.dir, "fixtures", "compatibility");
const jarPaths = [
  "/home/thewind/Downloads/ft_restool.jar",
  "/home/thewind/Downloads/ft_restool (1).jar",
];
type OracleReport = {
  ftm: {
    roundTripSemantic: boolean;
    semantic: unknown;
    storedSha256: string;
  };
  prj: {
    roundTripEqual: boolean;
    outputSha256: string;
  };
  set: {
    roundTripEqual: boolean;
    encryptedBase64: string;
  };
  tex: {
    roundTripEqual: boolean;
    transformedBase64: string;
  };
};
let work = "";
let oracle: OracleReport;
let report: Awaited<ReturnType<typeof buildCompatibilityReport>>;
let server: ReturnType<typeof Bun.spawn> | undefined;
let base = "";

async function waitForMarker(stream: ReadableStream<Uint8Array>): Promise<string> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let text = "";
  let timer: Timer | undefined;
  try {
    return await Promise.race([
      (async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) throw new Error(`server exited before startup: ${text}`);
          text += decoder.decode(value, { stream: true });
          if (text.includes("jftse-content-studio listening on")) return text;
        }
      })(),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error("server startup timed out")), 20_000);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
    reader.releaseLock();
  }
}

beforeAll(async () => {
  work = mkdtempSync(join(tmpdir(), "jftse-compat-"));
  materializeCompatibilityFixtures(root, work);
  const proc = Bun.spawn([
    "java",
    "--class-path",
    jarPaths[0],
    join(root, "oracle", "CompatibilityOracle.java"),
    work,
  ], { stdout: "pipe", stderr: "pipe" });
  const [stdout, stderr, exit] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ]);
  expect(exit, stderr).toBe(0);
  oracle = JSON.parse(stdout) as OracleReport;
  report = await buildCompatibilityReport();

  server = Bun.spawn(["bun", "run", "server/index.ts"], {
    cwd: join(import.meta.dir, ".."),
    env: { ...process.env, PORT: "0" },
    stdout: "pipe",
    stderr: "pipe",
  });
  const output = await waitForMarker(server.stdout as ReadableStream<Uint8Array>);
  const match = output.match(/(http:\/\/127\.0\.0\.1:\d+)/);
  if (!match) throw new Error(`startup URL missing: ${output}`);
  base = match[1];
});

afterAll(async () => {
  if (server) {
    server.kill();
    await server.exited;
  }
  if (work && existsSync(work)) rmSync(work, { recursive: true, force: true });
});

describe("ResTool compatibility fixtures", () => {
  test("FTM semantic parse/store/fromJson/toJson agrees with the Java oracle", () => {
    expect(oracle.ftm.roundTripSemantic).toBe(true);
    expect(report.fixtures.ftm.status).toBe("proven");
    expect(report.fixtures.ftm.semantic).toEqual(oracle.ftm.semantic);
    expect(report.fixtures.ftm.outputSha256).toBe(oracle.ftm.storedSha256);
  });

  test("PRJ read/write round-trip agrees with the Java oracle", () => {
    expect(oracle.prj.roundTripEqual).toBe(true);
    expect(report.fixtures.prj).toMatchObject({ status: "proven", compatible: true });
    expect(report.fixtures.prj.outputSha256).toBe(oracle.prj.outputSha256);
  });

  test("SET encrypt/decrypt agrees with the Java oracle", () => {
    expect(oracle.set.roundTripEqual).toBe(true);
    expect(report.fixtures.set).toMatchObject({ status: "proven", compatible: true });
    expect(report.fixtures.set.outputBase64).toBe(oracle.set.encryptedBase64);
  });

  test("TEX XOR round-trip agrees with the Java oracle", () => {
    expect(oracle.tex.roundTripEqual).toBe(true);
    expect(report.fixtures.tex).toMatchObject({ status: "proven", compatible: true });
    expect(report.fixtures.tex.outputBase64).toBe(oracle.tex.transformedBase64);
  });

  test("both read-only ResTool jars have the recorded identical hash", async () => {
    const hashes = await Promise.all(jarPaths.map(async (path) =>
      createHash("sha256").update(Buffer.from(await Bun.file(path).arrayBuffer())).digest("hex"),
    ));
    expect(new Set(hashes).size).toBe(1);
    expect(report.oracle.clients.map((client) => client.sha256)).toEqual(hashes);
    expect(report.oracle.jarsEqual).toBe(true);
  });

  test("live endpoint reports proven and unproven capabilities without path input", async () => {
    const response = await fetch(`${base}/api/compatibility`);
    expect(response.status).toBe(200);
    const body = await response.json() as typeof report;
    expect(body.ok).toBe(true);
    expect(body.fixtures.ftm.compatible).toBe(true);
    expect(body.capabilities.some((item) => item.status === "proven")).toBe(true);
    expect(body.capabilities.some((item) => item.status === "unproven")).toBe(true);

    const rejected = await fetch(`${base}/api/compatibility?path=/etc/passwd`);
    expect(rejected.status).toBe(400);
    expect(await rejected.json()).toEqual({ ok: false, error: "COMPATIBILITY_QUERY_FORBIDDEN" });
  });
});
