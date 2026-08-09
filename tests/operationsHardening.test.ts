import { describe, expect, test } from "bun:test";
import {
  RequestPolicyError,
  parseBoundedInteger,
  readJsonObject,
} from "../server/requestPolicy.ts";
import {
  BridgeScheduler,
  BridgeSchedulerBusyError,
} from "../server/bridgeScheduler.ts";
import { developmentServeOptions } from "../server/serverMode.ts";

function deferred<T = void>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

async function policyFailure(work: () => Promise<unknown>) {
  try {
    await work();
  } catch (error) {
    if (error instanceof RequestPolicyError) return error;
    throw error;
  }
  throw new Error("expected request policy failure");
}

describe("operations request hardening", () => {
  test("rejects oversized JSON from content-length and streamed bytes with 413", async () => {
    const declared = new Request("http://localhost/api/content-pack/build", {
      method: "POST",
      headers: { "content-length": "1025" },
      body: "{}",
    });
    const declaredError = await policyFailure(() => readJsonObject(declared, 1024));
    expect(declaredError).toMatchObject({ status: 413, code: "REQUEST_BODY_TOO_LARGE" });

    const streamed = new Request("http://localhost/api/sql/apply", {
      method: "POST",
      body: "x".repeat(1025),
    });
    const streamedError = await policyFailure(() => readJsonObject(streamed, 1024));
    expect(streamedError).toMatchObject({ status: 413, code: "REQUEST_BODY_TOO_LARGE" });
  });

  test("rejects invalid and extreme atlas/item/ANI/mesh numeric knobs", () => {
    for (const [value, options] of [
      ["NaN", { name: "limit", minimum: 1, maximum: 500, fallback: 100 }],
      ["1000000", { name: "limit", minimum: 1, maximum: 500, fallback: 80 }],
      ["-1", { name: "clipIndex", minimum: 0, maximum: 255, fallback: 0 }],
      ["999999", { name: "maxFrames", minimum: 1, maximum: 5000, fallback: 8 }],
      ["3.5", { name: "maxVertices", minimum: 1, maximum: 10000, fallback: 2000 }],
      ["1e99", { name: "meshIndex", minimum: 0, maximum: 1_000_000 }],
    ] as const) {
      expect(() => parseBoundedInteger(value, options)).toThrow(RequestPolicyError);
      try {
        parseBoundedInteger(value, options);
      } catch (error) {
        expect(error).toMatchObject({ status: 400, code: `INVALID_${options.name.toUpperCase()}` });
      }
    }
    expect(parseBoundedInteger(null, { name: "limit", minimum: 1, maximum: 500, fallback: 80 })).toBe(80);
  });
});

describe("bounded bridge scheduling", () => {
  test("caps active work, bounds its queue, and preserves job results", async () => {
    const scheduler = new BridgeScheduler({ concurrency: 2, maxQueue: 1 });
    const firstRelease = deferred();
    const secondRelease = deferred();
    const started = deferred();
    const events: string[] = [];
    let active = 0;

    const job = (name: string, release: Promise<void>) => scheduler.schedule(async () => {
      active += 1;
      events.push(`start:${name}:${active}`);
      if (active === 2) started.resolve();
      await release;
      active -= 1;
      events.push(`end:${name}:${active}`);
      return name;
    });

    const first = job("first", firstRelease.promise);
    const second = job("second", secondRelease.promise);
    const third = job("third", Promise.resolve());
    await started.promise;
    const rejected = scheduler.schedule(async () => "fourth").catch((error) => error);
    expect(await rejected).toBeInstanceOf(BridgeSchedulerBusyError);
    expect(await rejected).toMatchObject({ status: 429, code: "BRIDGE_BUSY" });
    expect(events).toEqual(["start:first:1", "start:second:2"]);

    firstRelease.resolve();
    expect(await first).toBe("first");
    expect(await third).toBe("third");
    secondRelease.resolve();
    expect(await second).toBe("second");
    expect(events.some((entry) => entry === "start:third:2")).toBe(true);
  });

  test("does not swallow scheduled job failures", async () => {
    const scheduler = new BridgeScheduler({ concurrency: 1, maxQueue: 1 });
    const failure = new Error("bridge exploded");
    let caught: unknown;
    try {
      await scheduler.schedule(async () => {
        throw failure;
      });
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(failure);
  });
});

describe("production server mode", () => {
  test("omits Bun development/HMR options unless explicitly enabled", () => {
    expect(developmentServeOptions({})).toEqual({});
    expect(developmentServeOptions({ NODE_ENV: "production" })).toEqual({});
    expect(developmentServeOptions({ JFTSE_STUDIO_DEV: "1" })).toEqual({
      development: { hmr: true, console: true },
    });
  });
});
