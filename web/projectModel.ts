export const PROJECT_SCHEMA_VERSION = 1;
export const DEFAULT_HISTORY_LIMIT = 100;

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | { [key: string]: JsonValue };

export type ProjectDraft = {
  shell: { [key: string]: JsonValue };
  editors: { [key: string]: JsonValue };
};

export type ProjectEnvelope = {
  schemaVersion: typeof PROJECT_SCHEMA_VERSION;
  name: string;
  draft: ProjectDraft;
};

type ProjectSnapshot = {
  envelope: ProjectEnvelope;
  revision: number;
};

export type ProjectModel = {
  present: ProjectSnapshot;
  past: ProjectSnapshot[];
  future: ProjectSnapshot[];
  historyLimit: number;
  savedRevision: number;
  dirty: boolean;
};

export type ProjectAction =
  | { type: "update"; name?: string; draft?: ProjectDraft }
  | { type: "undo" }
  | { type: "redo" }
  | { type: "mark-saved" };

export type ProjectRecovery =
  | { status: "recovered"; model: ProjectModel }
  | {
      status: "unavailable";
      reason: "absent" | "malformed" | "newer-version";
      schemaVersion?: number;
    };

function cloneJson<T extends JsonValue>(value: T): T {
  return structuredClone(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isJsonValue(value: unknown): value is JsonValue {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return true;
  }
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(isJsonValue);
  return isRecord(value) && Object.values(value).every(isJsonValue);
}

function isProjectDraft(value: unknown): value is ProjectDraft {
  if (!isRecord(value)) return false;
  return (
    isRecord(value.shell) &&
    isJsonValue(value.shell) &&
    isRecord(value.editors) &&
    isJsonValue(value.editors)
  );
}

function sameEnvelope(left: ProjectEnvelope, right: ProjectEnvelope): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function withPresent(
  model: ProjectModel,
  present: ProjectSnapshot,
  past: ProjectSnapshot[],
  future: ProjectSnapshot[],
): ProjectModel {
  return {
    ...model,
    present,
    past,
    future,
    dirty: present.revision !== model.savedRevision,
  };
}

export function createProjectModel(
  name: string,
  draft: ProjectDraft,
  options: { historyLimit?: number } = {},
): ProjectModel {
  const historyLimit = options.historyLimit ?? DEFAULT_HISTORY_LIMIT;
  if (!Number.isInteger(historyLimit) || historyLimit < 0) {
    throw new Error("historyLimit must be a non-negative integer");
  }
  if (!isProjectDraft(draft)) {
    throw new Error("draft must be JSON-serializable project data");
  }
  const present: ProjectSnapshot = {
    envelope: {
      schemaVersion: PROJECT_SCHEMA_VERSION,
      name,
      draft: cloneJson(draft),
    },
    revision: 0,
  };
  return {
    present,
    past: [],
    future: [],
    historyLimit,
    savedRevision: 0,
    dirty: false,
  };
}

export function projectReducer(
  model: ProjectModel,
  action: ProjectAction,
): ProjectModel {
  if (action.type === "mark-saved") {
    if (!model.dirty && model.savedRevision === model.present.revision) {
      return model;
    }
    return {
      ...model,
      savedRevision: model.present.revision,
      dirty: false,
    };
  }

  if (action.type === "undo") {
    const previous = model.past.at(-1);
    if (!previous) return model;
    return withPresent(
      model,
      previous,
      model.past.slice(0, -1),
      [model.present, ...model.future],
    );
  }

  if (action.type === "redo") {
    const next = model.future[0];
    if (!next) return model;
    return withPresent(
      model,
      next,
      [...model.past, model.present],
      model.future.slice(1),
    );
  }

  const envelope: ProjectEnvelope = {
    ...model.present.envelope,
    name: action.name ?? model.present.envelope.name,
    draft: action.draft
      ? cloneJson(action.draft)
      : model.present.envelope.draft,
  };
  if (sameEnvelope(envelope, model.present.envelope)) return model;

  const revision =
    Math.max(
      model.present.revision,
      ...model.past.map((snapshot) => snapshot.revision),
      ...model.future.map((snapshot) => snapshot.revision),
    ) + 1;
  const past =
    model.historyLimit === 0
      ? []
      : [...model.past, model.present].slice(-model.historyLimit);
  return withPresent(model, { envelope, revision }, past, []);
}

export function serializeProject(model: ProjectModel): string {
  return JSON.stringify(model.present.envelope);
}

export function parseProjectRecovery(value: string | null): ProjectRecovery {
  if (value === null) return { status: "unavailable", reason: "absent" };

  let candidate: unknown;
  try {
    candidate = JSON.parse(value);
  } catch {
    return { status: "unavailable", reason: "malformed" };
  }
  if (!isRecord(candidate)) {
    return { status: "unavailable", reason: "malformed" };
  }

  const schemaVersion = candidate.schemaVersion;
  if (
    typeof schemaVersion === "number" &&
    Number.isInteger(schemaVersion) &&
    schemaVersion > PROJECT_SCHEMA_VERSION
  ) {
    return {
      status: "unavailable",
      reason: "newer-version",
      schemaVersion,
    };
  }
  if (
    schemaVersion !== PROJECT_SCHEMA_VERSION ||
    typeof candidate.name !== "string" ||
    !isProjectDraft(candidate.draft)
  ) {
    return { status: "unavailable", reason: "malformed" };
  }

  return {
    status: "recovered",
    model: createProjectModel(candidate.name, candidate.draft),
  };
}
