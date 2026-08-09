import { useEffect, useReducer, useRef, useState } from "react";
import { ConfirmDialog } from "./ConfirmDialog";
import {
  ContentPackPanels,
  type DraftField,
} from "./ContentPackPanels";
import {
  contentPackApi as api,
  initialContentPackDraft,
  type ApiRecord,
  type PackManifest,
  type PreflightResult,
} from "./contentPackApi";
import {
  createContentPackWorkflow,
  getContentPackActionReason,
  getNextContentPackAction,
  reduceContentPackWorkflow,
  type ContentPackAction,
} from "./contentPackWorkflow";

export function ContentPackDesk() {
  const [workflow, dispatch] = useReducer(
    reduceContentPackWorkflow,
    undefined,
    createContentPackWorkflow,
  );
  const revisionRef = useRef(workflow.revision);
  revisionRef.current = workflow.revision;
  const [draft, setDraft] = useState(initialContentPackDraft);
  const [localClient, setLocalClient] = useState("");
  const [busy, setBusy] = useState<ContentPackAction | null>(null);
  const [confirm, setConfirm] = useState<"install" | "sqlApply" | null>(null);
  const [status, setStatus] = useState("Configure the draft, then build.");
  const [preflight, setPreflight] = useState<PreflightResult | null>(null);
  const manifest = workflow.build?.value as PackManifest | undefined;
  const sqlPath = manifest?.sqlPath ?? "";
  const next = getNextContentPackAction(workflow);

  useEffect(() => {
    let active = true;
    void api<{ localClient?: string }>("/api/health")
      .then((result) => active && setLocalClient(result.localClient ?? ""))
      .catch(() => active && setLocalClient(""));
    return () => {
      active = false;
    };
  }, []);

  const edit = (field: DraftField, value: string | boolean) => {
    setDraft((current) => ({ ...current, [field]: value }));
    dispatch({ type: "draftChanged" });
    setConfirm(null);
    setPreflight(null);
    setStatus("Draft changed — rebuild required.");
  };
  const can = (action: ContentPackAction) =>
    !busy && (
      action === "build" ||
      next === action ||
      (action === "preflight" && next === "complete")
    );
  const fail = (
    action: ContentPackAction,
    label: string,
    error: unknown,
    revision: number,
  ) => {
    if (revision !== revisionRef.current) return;
    const detail = error instanceof Error ? error.message : String(error);
    dispatch({ type: "actionFailed", revision, action, message: detail });
    setStatus(`${label} MISS — ${detail}`);
  };

  const build = async () => {
    const revision = workflow.revision;
    setBusy("build");
    dispatch({ type: "retry", action: "build" });
    try {
      const scenarios = draft.scenarioIds.split(/[,\s]+/).filter(Boolean)
        .map(Number).filter(Number.isFinite);
      const body: ApiRecord = {
        name: draft.name,
        equipment: {
          meshIndex: Number(draft.meshIndex) || draft.meshIndex,
          char: draft.char,
          desc: draft.itemDesc,
        },
        map: {
          draft: { name: draft.mapName, playTime: 180, breathTime: 100 },
          scenarioIds: scenarios,
          stageScript: draft.stageScript,
        },
        stage: { member: draft.stageScript, fields: {} },
      };
      if (draft.includeFtm) {
        body.ftm = {
          archive: draft.ftmArchive,
          member: draft.ftmMember,
          patches: [{ index: 0, x: 10, y: 10 }],
        };
      }
      const result = await api<PackManifest>("/api/content-pack/build", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (revision !== revisionRef.current) {
        return;
      }
      dispatch({
        type: "buildSucceeded",
        revision,
        hasSql: Boolean(result.sqlPath),
        receipt: result,
      });
      setPreflight(null);
      setStatus(`Build PASS — ${result.installPlan?.length ?? 0} files.`);
    } catch (error) {
      fail("build", "Build", error, revision);
    } finally {
      setBusy(null);
    }
  };

  const install = async () => {
    if (!manifest?.installPlan?.length || !localClient) return;
    const revision = workflow.revision;
    setBusy("install");
    setConfirm(null);
    try {
      const result = await api<ApiRecord>("/api/content-pack/install", {
        method: "POST",
        body: JSON.stringify({
          targetClient: localClient,
          installPlan: manifest.installPlan,
        }),
      });
      if (revision !== revisionRef.current) return;
      dispatch({ type: "installSucceeded", revision, receipt: result });
      setStatus(`Install PASS — ${manifest.installPlan.length} verified files.`);
    } catch (error) {
      fail("install", "Install", error, revision);
    } finally {
      setBusy(null);
    }
  };

  const runSql = async (dryRun: boolean) => {
    if (!sqlPath) return;
    const revision = workflow.revision;
    const action = dryRun ? "sqlAudit" : "sqlApply";
    setBusy(action);
    setConfirm(null);
    try {
      const result = await api<ApiRecord>("/api/sql/apply", {
        method: "POST",
        body: JSON.stringify({ path: sqlPath, dryRun }),
      });
      if (revision !== revisionRef.current) return;
      dispatch({
        type: dryRun ? "sqlAuditSucceeded" : "sqlApplySucceeded",
        revision,
        receipt: result,
      });
      setStatus(dryRun ? "SQL audit PASS." : "SQL apply PASS.");
    } catch (error) {
      fail(action, dryRun ? "SQL audit" : "SQL apply", error, revision);
    } finally {
      setBusy(null);
    }
  };

  const runPreflight = async () => {
    if (!manifest?.installPlan) return;
    const revision = workflow.revision;
    setBusy("preflight");
    try {
      const result = await api<PreflightResult>(
        "/api/content-pack/playtest-full",
        {
          method: "POST",
          body: JSON.stringify({
            targetClient: localClient,
            installPlan: manifest.installPlan,
            sqlPath: sqlPath || undefined,
            sqlApplyReceipt: workflow.sqlApply?.value,
          }),
        },
      );
      if (revision !== revisionRef.current) return;
      setPreflight(result);
      if (!result.preflightPassed) {
        fail(
          "preflight",
          "Local client preflight",
          "Fix every MISS below.",
          revision,
        );
        return;
      }
      dispatch({
        type: "preflightSucceeded",
        revision,
        receipt: result,
      });
      setStatus("Local client preflight PASS — manual DX9 check required.");
    } catch (error) {
      fail("preflight", "Local client preflight", error, revision);
    } finally {
      setBusy(null);
    }
  };

  const act = (action: ContentPackAction) => {
    dispatch({ type: "retry", action });
    if (action === "build") void build();
    if (action === "install") setConfirm("install");
    if (action === "sqlAudit") void runSql(true);
    if (action === "sqlApply") setConfirm("sqlApply");
    if (action === "preflight") void runPreflight();
  };

  const copyLaunchCommand = async () => {
    const command = preflight?.launchCommand;
    if (!command) return;
    try {
      await navigator.clipboard.writeText(command);
      setStatus("Launch command copied.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      setStatus(`Copy MISS — ${detail}`);
    }
  };

  return <>
    <ContentPackPanels
      busy={busy}
      can={can}
      draft={draft}
      installPlan={manifest?.installPlan}
      localClient={localClient}
      next={next}
      onAction={act}
      onCopyLaunchCommand={() => void copyLaunchCommand()}
      onDraftChange={edit}
      preflight={preflight}
      reason={(action) => getContentPackActionReason(workflow, action)}
      sqlPath={sqlPath}
      status={status}
      workflow={workflow}
    />
    <ConfirmDialog
      confirmLabel={confirm === "install" ? "Install verified files" : "Apply audited SQL"}
      description={confirm === "install"
        ? `Write ${manifest?.installPlan?.length ?? 0} generated files to ${localClient}. Stock files are refused.`
        : `Apply ${sqlPath} using only the server-configured database credentials.`}
      onCancel={() => setConfirm(null)}
      onConfirm={() => void (confirm === "install" ? install() : runSql(false))}
      open={confirm !== null}
      title={confirm === "install" ? "Install to local client?" : "Apply SQL to local database?"}
      tone={confirm === "sqlApply" ? "danger" : "default"}
    />
  </>;
}
