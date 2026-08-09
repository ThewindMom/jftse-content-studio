import type {
  ContentPackAction,
  ContentPackNextAction,
  ContentPackWorkflow,
} from "./contentPackWorkflow";

export type InstallFile = { source: string; destRelative: string };
export type Check = { id?: string; ok: boolean; label?: string; path?: string };
export type PreflightView = {
  checklist?: Check[];
  launchCommand?: string | null;
  manualHandoff?: string;
};
export type DraftField =
  | "name"
  | "meshIndex"
  | "char"
  | "itemDesc"
  | "mapName"
  | "scenarioIds"
  | "stageScript"
  | "includeFtm"
  | "ftmArchive"
  | "ftmMember";
export type ContentPackDraft = Record<
  Exclude<DraftField, "includeFtm">,
  string
> & { includeFtm: boolean };

type Props = {
  draft: ContentPackDraft;
  workflow: ContentPackWorkflow;
  next: ContentPackNextAction;
  busy: ContentPackAction | null;
  localClient: string;
  sqlPath: string;
  status: string;
  installPlan?: InstallFile[];
  preflight: PreflightView | null;
  can: (action: ContentPackAction) => boolean;
  reason: (action: ContentPackAction) => string | null;
  onDraftChange: (field: DraftField, value: string | boolean) => void;
  onAction: (action: ContentPackAction) => void;
};

export function ContentPackPanels({
  draft,
  workflow,
  next,
  busy,
  localClient,
  sqlPath,
  status,
  installPlan,
  preflight,
  can,
  reason,
  onDraftChange,
  onAction,
}: Props) {
  const button = (
    action: ContentPackAction,
    label: string,
    primary = false,
  ) => (
    <button
      className={`btn${primary ? " primary" : ""}`}
      disabled={!can(action)}
      onClick={() => onAction(action)}
      title={reason(action) ?? undefined}
      type="button"
    >
      {busy === action ? "Working…" : label}
    </button>
  );
  const textField = (
    field: Exclude<DraftField, "includeFtm">,
    label: string,
  ) => (
    <label>
      {label}
      <input
        disabled={Boolean(busy)}
        value={draft[field]}
        onChange={(event) => onDraftChange(field, event.target.value)}
      />
    </label>
  );

  return (
    <main className="workspace">
      <section className="panel" aria-label="Pack configuration">
        <header><h2>Content pack</h2></header>
        <div className="body">
          <p className="empty">Build → confirm install → audit → confirm apply → local client preflight.</p>
          <div className="field-grid">
            {textField("name", "Pack name")}
            {textField("meshIndex", "Mesh index")}
            {textField("char", "Character")}
            {textField("itemDesc", "Item name")}
            {textField("mapName", "Map name")}
            {textField("scenarioIds", "Scenario ids")}
            {textField("stageScript", "Stage script")}
            <label>
              <span>
                <input
                  checked={draft.includeFtm}
                  disabled={Boolean(busy)}
                  type="checkbox"
                  onChange={(event) =>
                    onDraftChange("includeFtm", event.target.checked)
                  }
                />{" "}
                Include FTM patch sample
              </span>
            </label>
            {draft.includeFtm && <>
              {textField("ftmArchive", "FTM archive")}
              {textField("ftmMember", "FTM member")}
            </>}
          </div>
          <div className="actions">
            {button("build", "1 · Build pack", true)}
            {button("install", "2 · Confirm install", true)}
            {sqlPath && button("sqlAudit", "3 · Audit SQL")}
            {sqlPath && button("sqlApply", "4 · Confirm SQL apply")}
            {button("preflight", "5 · Local client preflight", true)}
          </div>
        </div>
      </section>
      <section className="panel" aria-label="Pack workflow">
        <header><h2>Workflow</h2></header>
        <div className="body">
          <p
            className={workflow.error ? "status bad" : "status"}
            role={workflow.error ? "alert" : "status"}
          >
            {status}
          </p>
          <dl className="kv">
            <dt>Revision</dt><dd>{workflow.revision}</dd>
            <dt>Next</dt><dd>{next}</dd>
            <dt>Target</dt><dd className="mono">{localClient || "Target not configured"}</dd>
            <dt>Aggregate SQL</dt><dd className="mono">{sqlPath || "No SQL in this pack"}</dd>
          </dl>
          {installPlan?.map((file) => (
            <p className="mono" key={file.destRelative}>
              FILE — {file.destRelative}
            </p>
          ))}
        </div>
      </section>
      <section className="panel" aria-label="Local client preflight">
        <header><h2>Local client preflight</h2></header>
        <div className="body">
          {!preflight && <p className="empty">Complete the valid steps to run preflight.</p>}
          {preflight?.checklist?.map((check) => (
            <p
              className={check.ok ? "status ok" : "status bad"}
              key={check.id ?? check.label}
            >
              {check.ok ? "PASS" : "MISS"} — {check.label}
            </p>
          ))}
          {preflight?.manualHandoff && <p>{preflight.manualHandoff}</p>}
          {preflight?.launchCommand && (
            <code className="mono">{preflight.launchCommand}</code>
          )}
        </div>
      </section>
    </main>
  );
}
