export type ContentPackAction =
  | "build"
  | "install"
  | "sqlAudit"
  | "sqlApply"
  | "preflight";

export type ContentPackNextAction = ContentPackAction | "complete";
export type ReceiptValue = Readonly<Record<string, unknown>>;

export type WorkflowReceipt = {
  revision: number;
  value: ReceiptValue;
};

export type ContentPackWorkflow = {
  revision: number;
  hasSql?: boolean;
  build?: WorkflowReceipt;
  install?: WorkflowReceipt;
  sqlAudit?: WorkflowReceipt;
  sqlApply?: WorkflowReceipt;
  preflight?: WorkflowReceipt;
  error?: {
    action: ContentPackAction;
    message: string;
  };
};

export type ContentPackWorkflowEvent =
  | { type: "draftChanged" }
  | {
      type: "buildSucceeded";
      revision: number;
      hasSql: boolean;
      receipt: ReceiptValue;
    }
  | {
      type:
        | "installSucceeded"
        | "sqlAuditSucceeded"
        | "sqlApplySucceeded"
        | "preflightSucceeded";
      revision: number;
      receipt: ReceiptValue;
    }
  | {
      type: "actionFailed";
      revision: number;
      action: ContentPackAction;
      message: string;
    }
  | { type: "retry"; action: ContentPackAction };

export function createContentPackWorkflow(): ContentPackWorkflow {
  return { revision: 0 };
}

function receipt(
  revision: number,
  value: ReceiptValue,
): WorkflowReceipt {
  return { revision, value };
}

function current(
  state: ContentPackWorkflow,
  revision: number,
): boolean {
  return revision === state.revision;
}

export function reduceContentPackWorkflow(
  state: ContentPackWorkflow,
  event: ContentPackWorkflowEvent,
): ContentPackWorkflow {
  switch (event.type) {
    case "draftChanged":
      return { revision: state.revision + 1 };
    case "buildSucceeded":
      if (!current(state, event.revision)) return state;
      return {
        revision: state.revision,
        hasSql: event.hasSql,
        build: receipt(event.revision, event.receipt),
      };
    case "installSucceeded":
      if (!current(state, event.revision) || !state.build) return state;
      return {
        ...state,
        install: receipt(event.revision, event.receipt),
        sqlAudit: undefined,
        sqlApply: undefined,
        preflight: undefined,
        error: undefined,
      };
    case "sqlAuditSucceeded":
      if (
        !current(state, event.revision) ||
        !state.build ||
        !state.install ||
        !state.hasSql
      ) {
        return state;
      }
      return {
        ...state,
        sqlAudit: receipt(event.revision, event.receipt),
        sqlApply: undefined,
        preflight: undefined,
        error: undefined,
      };
    case "sqlApplySucceeded":
      if (
        !current(state, event.revision) ||
        !state.build ||
        !state.install ||
        !state.hasSql ||
        !state.sqlAudit
      ) {
        return state;
      }
      return {
        ...state,
        sqlApply: receipt(event.revision, event.receipt),
        preflight: undefined,
        error: undefined,
      };
    case "preflightSucceeded":
      if (
        !current(state, event.revision) ||
        !state.build ||
        !state.install ||
        (state.hasSql && !state.sqlApply)
      ) {
        return state;
      }
      return {
        ...state,
        preflight: receipt(event.revision, event.receipt),
        error: undefined,
      };
    case "actionFailed":
      if (!current(state, event.revision)) return state;
      return {
        ...state,
        error: { action: event.action, message: event.message },
      };
    case "retry":
      if (state.error?.action !== event.action) return state;
      return { ...state, error: undefined };
  }
}

export function getNextContentPackAction(
  state: ContentPackWorkflow,
): ContentPackNextAction {
  if (!state.build) return "build";
  if (!state.install) return "install";
  if (!state.hasSql) return state.preflight ? "complete" : "preflight";
  if (!state.sqlAudit) return "sqlAudit";
  if (!state.sqlApply) return "sqlApply";
  return state.preflight ? "complete" : "preflight";
}

export function getContentPackActionReason(
  state: ContentPackWorkflow,
  action: ContentPackAction,
): string | null {
  const next = getNextContentPackAction(state);
  if (next === action) return null;
  if (action === "build") return null;
  if (!state.build) return "Build the current draft first.";
  if (action === "install") return "This build is already installed.";
  if (!state.install) return "Install this build before continuing.";
  if (action === "sqlAudit") {
    return state.hasSql ? "SQL is already audited." : "This pack has no SQL.";
  }
  if (!state.hasSql) {
    return action === "preflight"
      ? null
      : "This pack has no SQL to apply.";
  }
  if (!state.sqlAudit) return "Run the SQL dry-run first.";
  if (action === "sqlApply") return "SQL is already applied.";
  if (!state.sqlApply) return "Apply the audited SQL before preflight.";
  return "Preflight already passed.";
}
