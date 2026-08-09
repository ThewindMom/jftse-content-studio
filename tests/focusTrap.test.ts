import { describe, expect, test } from "bun:test";
import { getFocusTrapTarget } from "../web/focusTrap.ts";

describe("confirmation focus trap", () => {
  test("wraps forward from the final control", () => {
    expect(getFocusTrapTarget(1, 2, false)).toBe(0);
  });

  test("wraps backward from the first control", () => {
    expect(getFocusTrapTarget(0, 2, true)).toBe(1);
  });

  test("leaves interior focus movement to the browser", () => {
    expect(getFocusTrapTarget(0, 2, false)).toBeNull();
    expect(getFocusTrapTarget(1, 2, true)).toBeNull();
  });

  test("moves outside focus to the safe boundary", () => {
    expect(getFocusTrapTarget(-1, 2, false)).toBe(0);
    expect(getFocusTrapTarget(-1, 2, true)).toBe(1);
  });

  test("handles an empty dialog", () => {
    expect(getFocusTrapTarget(-1, 0, false)).toBeNull();
  });
});
