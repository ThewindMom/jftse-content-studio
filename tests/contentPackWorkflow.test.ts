import { describe, expect, test } from "bun:test";
import {
  createContentPackWorkflow,
  getNextContentPackAction,
  reduceContentPackWorkflow,
} from "../web/contentPackWorkflow";

const buildReceipt = { packId: "pack-a" };
const installReceipt = { targetClient: "/tmp/client" };
const auditReceipt = { safe: true };
const applyReceipt = { applied: true };
const preflightReceipt = { preflightPassed: true };

describe("content pack workflow", () => {
  test("advances through every SQL-backed phase in order", () => {
    let state = createContentPackWorkflow();
    expect(getNextContentPackAction(state)).toBe("build");
    state = reduceContentPackWorkflow(state, {
      type: "buildSucceeded",
      revision: 0,
      hasSql: true,
      receipt: buildReceipt,
    });
    expect(getNextContentPackAction(state)).toBe("install");
    state = reduceContentPackWorkflow(state, {
      type: "installSucceeded",
      revision: 0,
      receipt: installReceipt,
    });
    expect(getNextContentPackAction(state)).toBe("sqlAudit");
    state = reduceContentPackWorkflow(state, {
      type: "sqlAuditSucceeded",
      revision: 0,
      receipt: auditReceipt,
    });
    expect(getNextContentPackAction(state)).toBe("sqlApply");
    state = reduceContentPackWorkflow(state, {
      type: "sqlApplySucceeded",
      revision: 0,
      receipt: applyReceipt,
    });
    expect(getNextContentPackAction(state)).toBe("preflight");
    state = reduceContentPackWorkflow(state, {
      type: "preflightSucceeded",
      revision: 0,
      receipt: preflightReceipt,
    });
    expect(getNextContentPackAction(state)).toBe("complete");
    expect(state.preflight?.value).toEqual(preflightReceipt);
  });

  test("ignores out-of-order actions", () => {
    const initial = createContentPackWorkflow();
    for (const event of [
      {
        type: "installSucceeded",
        revision: 0,
        receipt: installReceipt,
      },
      {
        type: "sqlAuditSucceeded",
        revision: 0,
        receipt: auditReceipt,
      },
      {
        type: "sqlApplySucceeded",
        revision: 0,
        receipt: applyReceipt,
      },
      {
        type: "preflightSucceeded",
        revision: 0,
        receipt: preflightReceipt,
      },
    ] as const) {
      expect(reduceContentPackWorkflow(initial, event)).toBe(initial);
    }
  });

  test("skips SQL phases when the build has no SQL", () => {
    let state = createContentPackWorkflow();
    state = reduceContentPackWorkflow(state, {
      type: "buildSucceeded",
      revision: 0,
      hasSql: false,
      receipt: buildReceipt,
    });
    state = reduceContentPackWorkflow(state, {
      type: "installSucceeded",
      revision: 0,
      receipt: installReceipt,
    });
    expect(getNextContentPackAction(state)).toBe("preflight");
    expect(
      reduceContentPackWorkflow(state, {
        type: "sqlAuditSucceeded",
        revision: 0,
        receipt: auditReceipt,
      }),
    ).toBe(state);
  });

  test("draft edits invalidate build and every downstream receipt", () => {
    let state = createContentPackWorkflow();
    state = reduceContentPackWorkflow(state, {
      type: "buildSucceeded",
      revision: 0,
      hasSql: true,
      receipt: buildReceipt,
    });
    state = reduceContentPackWorkflow(state, {
      type: "installSucceeded",
      revision: 0,
      receipt: installReceipt,
    });
    state = reduceContentPackWorkflow(state, {
      type: "draftChanged",
    });
    expect(state.revision).toBe(1);
    expect(state.build).toBeUndefined();
    expect(state.install).toBeUndefined();
    expect(state.sqlAudit).toBeUndefined();
    expect(state.sqlApply).toBeUndefined();
    expect(state.preflight).toBeUndefined();
    expect(getNextContentPackAction(state)).toBe("build");
  });

  test("a new build replaces prior build and downstream receipts", () => {
    let state = createContentPackWorkflow();
    state = reduceContentPackWorkflow(state, {
      type: "buildSucceeded",
      revision: 0,
      hasSql: true,
      receipt: buildReceipt,
    });
    state = reduceContentPackWorkflow(state, {
      type: "installSucceeded",
      revision: 0,
      receipt: installReceipt,
    });
    state = reduceContentPackWorkflow(state, {
      type: "buildSucceeded",
      revision: 0,
      hasSql: false,
      receipt: { packId: "pack-b" },
    });
    expect(state.build?.value).toEqual({ packId: "pack-b" });
    expect(state.install).toBeUndefined();
    expect(getNextContentPackAction(state)).toBe("install");
  });

  test("failed actions preserve valid receipts and retry clears only the error", () => {
    let state = createContentPackWorkflow();
    state = reduceContentPackWorkflow(state, {
      type: "buildSucceeded",
      revision: 0,
      hasSql: true,
      receipt: buildReceipt,
    });
    state = reduceContentPackWorkflow(state, {
      type: "actionFailed",
      action: "install",
      message: "Install refused",
    });
    expect(state.build?.value).toEqual(buildReceipt);
    expect(state.error).toEqual({
      action: "install",
      message: "Install refused",
    });
    state = reduceContentPackWorkflow(state, {
      type: "retry",
      action: "install",
    });
    expect(state.build?.value).toEqual(buildReceipt);
    expect(state.error).toBeUndefined();
  });

  test("ignores stale receipts from a previous draft revision", () => {
    const edited = reduceContentPackWorkflow(createContentPackWorkflow(), {
      type: "draftChanged",
    });
    expect(
      reduceContentPackWorkflow(edited, {
        type: "buildSucceeded",
        revision: 0,
        hasSql: true,
        receipt: buildReceipt,
      }),
    ).toBe(edited);
  });
});
