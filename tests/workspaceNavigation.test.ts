import { describe, expect, test } from "bun:test";
import {
  WORKSPACE_ORDER,
  moveTab,
} from "../web/workspaceNavigation";

describe("workspace navigation", () => {
  test("promotes Equipment in the fixed workspace order", () => {
    expect(WORKSPACE_ORDER).toEqual([
      "equipment",
      "packs",
      "maps",
      "meshes",
    ]);
  });

  test("moves right and left with wrapping", () => {
    expect(moveTab(WORKSPACE_ORDER, "equipment", "ArrowRight")).toBe("packs");
    expect(moveTab(WORKSPACE_ORDER, "meshes", "ArrowRight")).toBe("equipment");
    expect(moveTab(WORKSPACE_ORDER, "equipment", "ArrowLeft")).toBe("meshes");
    expect(moveTab(WORKSPACE_ORDER, "maps", "ArrowLeft")).toBe("packs");
  });

  test("moves Home and End to the boundaries", () => {
    expect(moveTab(WORKSPACE_ORDER, "maps", "Home")).toBe("equipment");
    expect(moveTab(WORKSPACE_ORDER, "packs", "End")).toBe("meshes");
  });

  test("supports the same keys for Equipment workflow steps", () => {
    const steps = ["items", "effect", "preview"] as const;
    expect(moveTab(steps, "items", "ArrowLeft")).toBe("preview");
    expect(moveTab(steps, "effect", "ArrowRight")).toBe("preview");
    expect(moveTab(steps, "preview", "Home")).toBe("items");
    expect(moveTab(steps, "items", "End")).toBe("preview");
  });

  test("ignores unrelated keys", () => {
    expect(moveTab(WORKSPACE_ORDER, "maps", "Enter")).toBe("maps");
  });
});
