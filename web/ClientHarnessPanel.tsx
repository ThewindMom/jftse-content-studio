import { useEffect, useState } from "react";
import {
  ClientHarnessReceipt,
  type HarnessResult,
} from "./ClientHarnessReceipt.tsx";

type ManagedProfile = {
  name: string;
  mode: "pass" | "fail";
  root: string;
  launcher: string;
  capturePath: string;
};

type PipelineResponse = {
  status: "passed" | "failed";
  failedStage: string | null;
  rolledBack: boolean;
  before: { sha256: string };
  after: { sha256: string };
  launch: HarnessResult | null;
  captureDataUrl: string | null;
  sqlApplyEligible: boolean;
  receipts: Record<string, { status: "passed" | "failed" | "skipped" }>;
};

async function responseJson<T>(response: Response): Promise<T> {
  const body = (await response.json()) as T & { error?: string };
  if (!response.ok) throw new Error(body.error ?? "Client harness request failed.");
  return body;
}

export function ClientHarnessPanel() {
  const [profiles, setProfiles] = useState<ManagedProfile[]>([]);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState<HarnessResult | null>(null);
  const [status, setStatus] = useState("Create a disposable profile to begin.");
  const [busy, setBusy] = useState(false);
  const [pipeline, setPipeline] = useState<PipelineResponse | null>(null);

  const loadProfiles = async () => {
    const body = await responseJson<{ profiles: ManagedProfile[] }>(
      await fetch("/api/client-harness/profiles"),
    );
    setProfiles(body.profiles);
    setSelected((current) => current || body.profiles[0]?.name || "");
  };

  useEffect(() => {
    void loadProfiles().catch((error) =>
      setStatus(error instanceof Error ? error.message : String(error)),
    );
  }, []);

  const createProfile = async (mode: "pass" | "fail") => {
    setBusy(true);
    try {
      const name =
        mode === "pass" ? "designer-safe-pass" : "designer-rollback-demo";
      await responseJson(
        await fetch("/api/client-harness/profiles", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ name, mode }),
        }),
      );
      await loadProfiles();
      setSelected(name);
      setResult(null);
      setStatus(
        mode === "pass"
          ? "Disposable capture profile ready."
          : "Disposable failure profile ready for rollback proof.",
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const run = async () => {
    if (!selected) return;
    setBusy(true);
    setResult(null);
    setPipeline(null);
    setStatus("Building, installing, auditing and launching the disposable client…");
    try {
      const body = await responseJson<PipelineResponse>(
        await fetch("/api/client-harness/pipeline", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ name: selected, applySql: false }),
        }),
      );
      setPipeline(body);
      setResult(
        body.launch
          ? {
              ...body.launch,
              before: body.before,
              after: body.after,
              rolledBack: body.rolledBack,
              captureDataUrl: body.captureDataUrl,
            }
          : null,
      );
      setStatus(
        body.status === "passed"
          ? "Build, install, DB eligibility, launch and capture PASS."
        : body.rolledBack
          ? `${body.failedStage ?? "Pipeline"} failed as designed; byte-identical rollback PASS.`
          : "Pipeline failed without a verified rollback.",
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const selectedProfile = profiles.find((profile) => profile.name === selected);
  const steps = [
    ["Profile", selectedProfile ? "PASS" : "WAIT"],
    ["Build", pipeline?.receipts.build.status.toUpperCase() ?? "WAIT"],
    ["Snapshot", result?.before.sha256 ? "PASS" : "WAIT"],
    ["Install", pipeline?.receipts.install.status.toUpperCase() ?? "WAIT"],
    [
      "DB eligibility",
      pipeline?.sqlApplyEligible
        ? "ELIGIBLE"
        : pipeline
          ? pipeline.receipts.sqlAudit.status.toUpperCase()
          : "WAIT",
    ],
    ["Launch", result ? `exit ${result.exitCode}` : "WAIT"],
    ["Monitor", result?.ready ? "READY" : result ? "NO READY" : "WAIT"],
    [
      "Capture",
      result?.captureDataUrl
        ? "PASS"
        : result?.capture && result.rolledBack
          ? "DISCARDED"
          : result?.capture
            ? "RECEIPT ONLY"
            : result
              ? "NONE"
              : "WAIT",
    ],
    [
      "Rollback",
      result?.rolledBack
        ? result.before.sha256 === result.after.sha256
          ? "RESTORED"
          : "MISMATCH"
        : result
          ? "NOT NEEDED"
          : "WAIT",
    ],
  ];

  return (
    <details className="client-harness panel-lite">
      <summary>Managed client test harness · launch, capture & rollback</summary>
      <div className="harness-content" aria-label="Managed client harness">
      <header className="creator-heading">
        <div>
          <p className="eyebrow">Build & launch workbench</p>
          <h3>Managed client test harness</h3>
          <p className="muted">
            Disposable profiles prove snapshot, launch, monitor, capture and
            rollback safely. Real DX9 login and authored-content selection
            remain manual and are never implied by this test.
          </p>
        </div>
        <div className="actions">
          <button
            className="btn"
            disabled={busy}
            onClick={() => void createProfile("pass")}
            type="button"
          >
            Create safe profile
          </button>
          <button
            className="btn"
            disabled={busy}
            onClick={() => void createProfile("fail")}
            type="button"
          >
            Create rollback profile
          </button>
        </div>
      </header>

      <div className="harness-controls">
        <label>
          Client profile
          <select
            aria-label="Managed client profile"
            value={selected}
            onChange={(event) => {
              setSelected(event.target.value);
              setResult(null);
            }}
          >
            <option value="">Choose a profile</option>
            {profiles.map((profile) => (
              <option key={profile.name} value={profile.name}>
                {profile.name} · {profile.mode}
              </option>
            ))}
          </select>
        </label>
        <button
          className="btn primary"
          disabled={busy || !selected}
          onClick={() => void run()}
          type="button"
        >
          {busy ? "Running…" : "Run build & launch"}
        </button>
      </div>

      <ol className="harness-steps">
        {steps.map(([label, value]) => (
          <li key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </li>
        ))}
      </ol>
      <p className="status" role="status">
        {status}
      </p>

      {result && <ClientHarnessReceipt result={result} />}
      </div>
    </details>
  );
}
