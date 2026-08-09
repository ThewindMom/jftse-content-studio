import { describe, expect, test } from "bun:test";
import {
  DEFAULT_HISTORY_LIMIT,
  PROJECT_SCHEMA_VERSION,
  createProjectModel,
  parseProjectRecovery,
  projectReducer,
  serializeProject,
  type ProjectDraft,
} from "../web/projectModel";
import { travelProjectSnapshot } from "../web/app";

const draft = (workspace: string, value: number): ProjectDraft => ({
  shell: { workspace, sidebarOpen: true },
  editors: {
    equipment: { value, tags: ["draft", null] },
    map: { selected: null },
  },
});

describe("project model", () => {
  test("creates a clean, versioned named project", () => {
    const model = createProjectModel("First Project", draft("equipment", 1));

    expect(PROJECT_SCHEMA_VERSION).toBe(1);
    expect(DEFAULT_HISTORY_LIMIT).toBeGreaterThan(0);
    expect(model.present.envelope).toEqual({
      schemaVersion: PROJECT_SCHEMA_VERSION,
      name: "First Project",
      draft: draft("equipment", 1),
    });
    expect(model.present.revision).toBe(0);
    expect(model.past).toEqual([]);
    expect(model.future).toEqual([]);
    expect(model.dirty).toBe(false);
  });

  test("updates immutably, marks dirty, and clears redo history", () => {
    const initial = createProjectModel("Project", draft("equipment", 1));
    const changed = projectReducer(initial, {
      type: "update",
      name: "Renamed",
      draft: draft("maps", 2),
    });
    const undone = projectReducer(changed, { type: "undo" });
    const branched = projectReducer(undone, {
      type: "update",
      draft: draft("meshes", 3),
    });

    expect(changed).not.toBe(initial);
    expect(initial.present.envelope.name).toBe("Project");
    expect(changed.present.envelope.name).toBe("Renamed");
    expect(changed.present.envelope.draft).toEqual(draft("maps", 2));
    expect(changed.dirty).toBe(true);
    expect(branched.future).toEqual([]);
    expect(branched.present.envelope.name).toBe("Project");
    expect(branched.present.envelope.draft).toEqual(draft("meshes", 3));
  });

  test("does not create history for a semantic no-op update", () => {
    const initial = createProjectModel("Project", draft("equipment", 1));
    const result = projectReducer(initial, {
      type: "update",
      name: "Project",
      draft: draft("equipment", 1),
    });

    expect(result).toBe(initial);
  });

  test("undoes and redoes updates without mutating prior states", () => {
    const initial = createProjectModel("Project", draft("equipment", 1));
    const first = projectReducer(initial, {
      type: "update",
      draft: draft("maps", 2),
    });
    const second = projectReducer(first, {
      type: "update",
      draft: draft("meshes", 3),
    });
    const undone = projectReducer(second, { type: "undo" });
    const redone = projectReducer(undone, { type: "redo" });

    expect(undone.present.envelope.draft).toEqual(draft("maps", 2));
    expect(redone.present.envelope.draft).toEqual(draft("meshes", 3));
    expect(second.past).toHaveLength(2);
    expect(undone.past).toHaveLength(1);
    expect(undone.future).toHaveLength(1);
    expect(projectReducer(initial, { type: "undo" })).toBe(initial);
    expect(projectReducer(second, { type: "redo" })).toBe(second);
  });

  test("repeated project travel derives navigation from each resulting snapshot", () => {
    const initial = createProjectModel("Project", draft("equipment", 1));
    const maps = projectReducer(initial, {
      type: "update",
      draft: { ...draft("maps", 2), shell: { workspace: "maps", step: "export" } },
    });
    const meshes = projectReducer(maps, {
      type: "update",
      draft: { ...draft("meshes", 3), shell: { workspace: "meshes", step: "playtest" } },
    });

    const first = travelProjectSnapshot(meshes, "undo");
    const autosaved = projectReducer(first.model, { type: "mark-saved" });
    const second = travelProjectSnapshot(autosaved, "undo");

    expect(first).toMatchObject({ workspace: "maps", step: "export" });
    expect(second).toMatchObject({ workspace: "equipment", step: "item" });
    expect(second.model.present.envelope.draft.editors.equipment).toEqual({
      value: 1,
      tags: ["draft", null],
    });
  });

  test("bounds undo history to the configured limit", () => {
    let model = createProjectModel("Project", draft("equipment", 0), {
      historyLimit: 2,
    });
    for (let value = 1; value <= 4; value += 1) {
      model = projectReducer(model, {
        type: "update",
        draft: draft("equipment", value),
      });
    }

    expect(model.past).toHaveLength(2);
    model = projectReducer(model, { type: "undo" });
    model = projectReducer(model, { type: "undo" });
    model = projectReducer(model, { type: "undo" });
    expect(model.present.envelope.draft).toEqual(draft("equipment", 2));
  });

  test("tracks dirty state against the exact marked-saved revision", () => {
    const initial = createProjectModel("Project", draft("equipment", 1));
    const changed = projectReducer(initial, {
      type: "update",
      draft: draft("maps", 2),
    });
    const saved = projectReducer(changed, { type: "mark-saved" });
    const edited = projectReducer(saved, {
      type: "update",
      draft: draft("meshes", 3),
    });
    const backAtSaved = projectReducer(edited, { type: "undo" });
    const beforeSaved = projectReducer(backAtSaved, { type: "undo" });
    const returnedToSaved = projectReducer(beforeSaved, { type: "redo" });

    expect(saved.dirty).toBe(false);
    expect(edited.dirty).toBe(true);
    expect(backAtSaved.dirty).toBe(false);
    expect(beforeSaved.dirty).toBe(true);
    expect(returnedToSaved.dirty).toBe(false);
  });

  test("serializes only the project envelope and recovers a clean model", () => {
    let model = createProjectModel("Serializable", draft("maps", 7));
    model = projectReducer(model, {
      type: "update",
      draft: draft("meshes", 8),
    });

    const serialized = serializeProject(model);
    expect(JSON.parse(serialized)).toEqual(model.present.envelope);
    expect(serialized).not.toContain("historyLimit");
    expect(serialized).not.toContain("dirty");

    const recovery = parseProjectRecovery(serialized);
    expect(recovery.status).toBe("recovered");
    if (recovery.status !== "recovered") throw new Error("expected recovery");
    expect(recovery.model.present.envelope).toEqual(model.present.envelope);
    expect(recovery.model.dirty).toBe(false);
    expect(recovery.model.past).toEqual([]);
  });

  test("returns deterministic recovery outcomes for absent and malformed data", () => {
    expect(parseProjectRecovery(null)).toEqual({
      status: "unavailable",
      reason: "absent",
    });
    expect(parseProjectRecovery("not-json")).toEqual({
      status: "unavailable",
      reason: "malformed",
    });
    expect(
      parseProjectRecovery(
        JSON.stringify({
          schemaVersion: PROJECT_SCHEMA_VERSION,
          name: "Broken",
          draft: { shell: [], editors: {} },
        }),
      ),
    ).toEqual({ status: "unavailable", reason: "malformed" });
  });

  test("identifies newer envelopes without attempting recovery", () => {
    expect(
      parseProjectRecovery(
        JSON.stringify({
          schemaVersion: PROJECT_SCHEMA_VERSION + 1,
          name: "From the future",
          draft: draft("maps", 1),
        }),
      ),
    ).toEqual({
      status: "unavailable",
      reason: "newer-version",
      schemaVersion: PROJECT_SCHEMA_VERSION + 1,
    });
  });

  test("rejects invalid history limits at the model boundary", () => {
    expect(() =>
      createProjectModel("Project", draft("maps", 1), { historyLimit: -1 }),
    ).toThrow("historyLimit");
    expect(() =>
      createProjectModel("Project", draft("maps", 1), { historyLimit: 1.5 }),
    ).toThrow("historyLimit");
  });
});
