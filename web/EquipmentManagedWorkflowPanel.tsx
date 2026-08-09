import { ConfirmDialog } from "./ConfirmDialog.tsx";
import {
  type EquipmentBuildWorkflow,
  useEquipmentManagedWorkflow,
} from "./useEquipmentManagedWorkflow.ts";

export function EquipmentManagedWorkflowPanel({
  build,
}: {
  build: EquipmentBuildWorkflow;
}) {
  const workflow = useEquipmentManagedWorkflow(build);
  return (
    <section className="panel-lite" aria-labelledby="equipment-handoff-title">
      <header className="creator-heading">
        <div>
          <p className="eyebrow">Managed production handoff</p>
          <h3 id="equipment-handoff-title">Install, audit, preflight</h3>
          <p className="muted">
            Browser topology, material, and attachment edits remain design
            evidence. Runtime metadata, particle, and Effect 15 bindings are
            written into the generated archives.
          </p>
        </div>
      </header>

      <dl className="runtime-contract">
        {Object.entries(workflow.runtimeFields).map(
          ([field, classification]) => (
            <div key={field}>
              <dt>{field}</dt>
              <dd>{String(classification)}</dd>
            </div>
          ),
        )}
      </dl>

      <div className="harness-controls">
        <label>
          Managed client profile
          <select
            value={workflow.profileName}
            onChange={(event) => workflow.setProfileName(event.target.value)}
          >
            <option value="">Choose a profile</option>
            {workflow.profiles.map((profile) => (
              <option key={profile.name} value={profile.name}>
                {profile.name} · {profile.mode}
              </option>
            ))}
          </select>
        </label>
        <button
          className="btn"
          disabled={workflow.busy}
          onClick={() => void workflow.createProfile()}
          type="button"
        >
          Create managed profile
        </button>
      </div>

      <div className="actions" aria-label="Equipment production handoff actions">
        <button
          className="btn primary"
          disabled={workflow.busy || !workflow.profileName}
          onClick={() => workflow.setConfirmation("install")}
          type="button"
        >
          Install archives
        </button>
        <button
          className="btn"
          disabled={workflow.busy}
          onClick={() => void workflow.auditSql()}
          type="button"
        >
          Audit item SQL
        </button>
        <button
          className="btn"
          disabled={workflow.busy || !workflow.audit}
          onClick={() => workflow.setConfirmation("sqlApply")}
          type="button"
        >
          Apply audited SQL
        </button>
        <button
          className="btn"
          disabled={
            workflow.busy ||
            !workflow.profileName ||
            !workflow.install ||
            !workflow.audit
          }
          onClick={() => void workflow.runPreflight()}
          type="button"
        >
          Run local client preflight
        </button>
      </div>

      <ol className="validation" aria-label="Equipment handoff progress">
        <li className={workflow.install ? "ok" : ""}>
          {workflow.install ? "PASS" : "WAIT"} · managed install
        </li>
        <li className={workflow.audit ? "ok" : ""}>
          {workflow.audit ? "PASS" : "WAIT"} · SQL audit
        </li>
        <li className={workflow.sqlApply ? "ok" : ""}>
          {workflow.sqlApply ? "PASS" : "OPTIONAL"} · live SQL apply
        </li>
        <li className={workflow.preflight ? "ok" : ""}>
          {workflow.preflight ? "PASS" : "WAIT"} · preflight
        </li>
      </ol>
      <p role="status">{workflow.status}</p>
      {workflow.error && (
        <p className="validation bad" role="alert">
          {workflow.error}
        </p>
      )}
      {workflow.preflight && (
        <p className="validation ok">
          {String(workflow.preflight.manualHandoff)}
        </p>
      )}

      <ConfirmDialog
        confirmLabel={
          workflow.confirmation === "sqlApply"
            ? "Apply SQL"
            : "Install archives"
        }
        description={
          workflow.confirmation === "sqlApply"
            ? `Apply the audited SQL for ${build.packageId} to the configured JFTSE database.`
            : `Write ${build.packageId} archives only into managed profile ${workflow.profileName}.`
        }
        onCancel={() => workflow.setConfirmation(null)}
        onConfirm={() => {
          const action = workflow.confirmation;
          workflow.setConfirmation(null);
          if (action === "sqlApply") void workflow.applySql();
          if (action === "install") void workflow.installPackage();
        }}
        open={workflow.confirmation !== null}
        title={
          workflow.confirmation === "sqlApply"
            ? "Apply audited item SQL?"
            : "Install Equipment archives?"
        }
      />
    </section>
  );
}
