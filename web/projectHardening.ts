import {
  PROJECT_SCHEMA_VERSION,
  parseProjectRecovery,
  type ProjectEnvelope,
} from "./projectModel.ts";
import {
  PROJECT_TEMPLATES,
  createProjectEnvelope,
  type ProjectTemplateId,
  type ReferenceProject,
} from "./projectHardeningTemplates.ts";

export {
  PROJECT_TEMPLATES,
  REFERENCE_PROJECTS,
  type ProjectTemplate,
  type ProjectTemplateId,
  type ReferenceProject,
} from "./projectHardeningTemplates.ts";

export type ProjectMigration =
  | {
      status: "ready";
      migratedFrom: number | null;
      envelope: ProjectEnvelope;
    }
  | {
      status: "unavailable";
      reason: "malformed" | "newer-version";
      raw: string;
      schemaVersion?: number;
    };

export type ProjectAutosaveRecovery =
  | {
      status: "ready";
      envelope: ProjectEnvelope;
      migratedFrom: number | null;
    }
  | {
      status: "recovered-from-backup";
      envelope: ProjectEnvelope;
      migratedFrom: number | null;
      failedPrimary: string;
    }
  | {
      status: "unavailable";
      primary: ProjectMigration;
      backup: ProjectMigration | null;
    };

export function migrateProjectFile(raw: string): ProjectMigration {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { status: "unavailable", reason: "malformed", raw };
  }
  if (typeof parsed !== "object" || parsed === null) {
    return { status: "unavailable", reason: "malformed", raw };
  }
  const schemaVersion =
    "schemaVersion" in parsed ? parsed.schemaVersion : undefined;
  if (
    typeof schemaVersion === "number" &&
    schemaVersion > PROJECT_SCHEMA_VERSION
  ) {
    return {
      status: "unavailable",
      reason: "newer-version",
      schemaVersion,
      raw,
    };
  }
  if (
    schemaVersion === 0 &&
    "name" in parsed &&
    typeof parsed.name === "string" &&
    "workspace" in parsed &&
    typeof parsed.workspace === "string" &&
    "step" in parsed &&
    typeof parsed.step === "string"
  ) {
    return {
      status: "ready",
      migratedFrom: 0,
      envelope: createProjectEnvelope(parsed.name, {
        shell: { workspace: parsed.workspace, step: parsed.step },
        editors: {},
      }),
    };
  }

  const recovery = parseProjectRecovery(raw);
  if (recovery.status === "recovered") {
    return {
      status: "ready",
      migratedFrom: null,
      envelope: recovery.model.present.envelope,
    };
  }
  return { status: "unavailable", reason: "malformed", raw };
}

export function recoverProjectAutosave(
  primaryRaw: string,
  backupRaw: string | null,
): ProjectAutosaveRecovery {
  const primary = migrateProjectFile(primaryRaw);
  if (primary.status === "ready") {
    return {
      status: "ready",
      envelope: primary.envelope,
      migratedFrom: primary.migratedFrom,
    };
  }
  const backup = backupRaw === null ? null : migrateProjectFile(backupRaw);
  if (backup?.status === "ready") {
    return {
      status: "recovered-from-backup",
      envelope: backup.envelope,
      migratedFrom: backup.migratedFrom,
      failedPrimary: primaryRaw,
    };
  }
  return { status: "unavailable", primary, backup };
}

export function instantiateProjectTemplate(
  id: ProjectTemplateId,
  name: string,
): ProjectEnvelope {
  const template = PROJECT_TEMPLATES.find((entry) => entry.id === id);
  if (!template) throw new Error(`Unknown project template: ${id}`);
  return createProjectEnvelope(name, template.draft);
}

export function roundTripReferenceProject(
  reference: ReferenceProject,
): ReferenceProject {
  const migrated = migrateProjectFile(JSON.stringify(reference.project));
  if (migrated.status !== "ready") {
    throw new Error(`Reference project failed to round-trip: ${reference.id}`);
  }
  return { id: reference.id, project: migrated.envelope };
}
