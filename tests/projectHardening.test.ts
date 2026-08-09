import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  PROJECT_TEMPLATES,
  REFERENCE_PROJECTS,
  instantiateProjectTemplate,
  migrateProjectFile,
  recoverProjectAutosave,
  roundTripReferenceProject,
} from "../web/projectHardening.ts";
import {
  readProjectEquipmentDraft,
  readProjectMapScene,
} from "../web/projectEditors.ts";
import { PROJECT_SCHEMA_VERSION } from "../web/projectModel.ts";

describe("project production hardening", () => {
  test("migrates legacy workspace files into the current project envelope", () => {
    const legacy = JSON.stringify({
      schemaVersion: 0,
      name: "Legacy Court",
      workspace: "maps",
      step: "item",
    });

    expect(migrateProjectFile(legacy)).toEqual({
      status: "ready",
      migratedFrom: 0,
      envelope: {
        schemaVersion: PROJECT_SCHEMA_VERSION,
        name: "Legacy Court",
        draft: {
          shell: { workspace: "maps", step: "item" },
          editors: {},
        },
      },
    });
  });

  test("rejects newer files without discarding the raw recovery payload", () => {
    const raw = JSON.stringify({
      schemaVersion: PROJECT_SCHEMA_VERSION + 1,
      name: "Future",
      draft: { shell: {}, editors: {} },
    });

    expect(migrateProjectFile(raw)).toEqual({
      status: "unavailable",
      reason: "newer-version",
      schemaVersion: PROJECT_SCHEMA_VERSION + 1,
      raw,
    });
  });

  test("recovers a malformed primary autosave from the last valid backup", () => {
    const backup = JSON.stringify({
      schemaVersion: PROJECT_SCHEMA_VERSION,
      name: "Recovered",
      draft: {
        shell: { workspace: "equipment", step: "effect" },
        editors: { equipment: { itemIndex: 41001 } },
      },
    });

    const recovery = recoverProjectAutosave("{bad-json", backup);
    expect(recovery.status).toBe("recovered-from-backup");
    if (recovery.status !== "recovered-from-backup") {
      throw new Error("expected backup recovery");
    }
    expect(recovery.envelope.name).toBe("Recovered");
    expect(recovery.failedPrimary).toBe("{bad-json");
  });

  test("provides independent equipment, map, and combined templates", () => {
    expect(PROJECT_TEMPLATES.map(({ id }) => id)).toEqual([
      "equipment-starter",
      "empty-court",
      "combined-showcase",
    ]);
    const first = instantiateProjectTemplate(
      "equipment-starter",
      "Aurora Project",
    );
    const second = instantiateProjectTemplate(
      "equipment-starter",
      "Copy Project",
    );

    expect(first.name).toBe("Aurora Project");
    expect(second.name).toBe("Copy Project");
    first.draft.editors.equipment = { changed: true };
    expect(second.draft.editors.equipment).not.toEqual({ changed: true });
  });

  test("templates and golden references load into real editor models", () => {
    const equipment = instantiateProjectTemplate(
      "equipment-starter",
      "Equipment",
    );
    const map = instantiateProjectTemplate("empty-court", "Map");
    const combined = instantiateProjectTemplate(
      "combined-showcase",
      "Combined",
    );
    const goldenEquipment = REFERENCE_PROJECTS.find(
      ({ id }) => id === "equipment-golden",
    );
    const goldenMap = REFERENCE_PROJECTS.find(({ id }) => id === "map-golden");

    expect(readProjectEquipmentDraft(equipment.draft)).toBeNull();
    expect(readProjectMapScene(map.draft).name).toBe("Untitled Court");
    expect(readProjectMapScene(combined.draft).references.ftmMember).toBe(
      "FantaCastleOutSide.ftm",
    );
    expect(
      readProjectEquipmentDraft(goldenEquipment!.project.draft)?.metadata.name,
    ).toBe("Aurora Racket");
    expect(readProjectMapScene(goldenMap!.project.draft).objects).toHaveLength(
      1,
    );
  });

  test("round-trips every checked-in golden reference project", () => {
    expect(REFERENCE_PROJECTS.map(({ id }) => id)).toEqual([
      "equipment-golden",
      "map-golden",
      "combined-golden",
    ]);
    for (const reference of REFERENCE_PROJECTS) {
      expect(roundTripReferenceProject(reference)).toEqual(reference);
    }
  });

  test("loads checked-in JSON fixtures through the migration boundary", () => {
    const root = join(import.meta.dir, "..", "reference-projects");
    for (const reference of REFERENCE_PROJECTS) {
      const raw = readFileSync(join(root, `${reference.id}.json`), "utf8");
      const migrated = migrateProjectFile(raw);
      expect(migrated.status).toBe("ready");
      if (migrated.status !== "ready") {
        throw new Error(`fixture did not migrate: ${reference.id}`);
      }
      expect(migrated.envelope).toEqual(reference.project);
    }
  });
});
