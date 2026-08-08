import React, { useState } from "react";

/**
 * Content Pack desk — one job: build → install → SQL dry-run/apply → playtest checklist.
 * Design: progressive steps, PASS/TODO honesty, mono paths, no marketing chrome.
 */
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  const data = (await response.json()) as T & { error?: string; detail?: string };
  if (!response.ok) {
    throw new Error(data.detail ?? data.error ?? `HTTP ${response.status}`);
  }
  return data;
}

type Check = { id?: string; ok: boolean; label?: string; destRelative?: string; path?: string };

export function ContentPackDesk() {
  const [name, setName] = useState("designer-pack");
  const [meshIndex, setMeshIndex] = useState("214");
  const [char, setChar] = useState("NIKI");
  const [itemDesc, setItemDesc] = useState("Studio Custom Racket");
  const [mapName, setMapName] = useState("Studio Custom Court");
  const [scenarioIds, setScenarioIds] = useState("1");
  const [stageScript, setStageScript] = useState("1_Emerald_Beach.set");
  const [includeFtm, setIncludeFtm] = useState(true);
  const [ftmArchive, setFtmArchive] = useState("Res/MapSet/FantaCastle.res");
  const [ftmMember, setFtmMember] = useState("FantaCastleOutSide.ftm");
  const [status, setStatus] = useState("Configure a pack, then Build.");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [manifest, setManifest] = useState<{
    outDir?: string;
    installPlan?: Array<{ source: string; destRelative: string }>;
    parts?: Record<string, unknown>;
  } | null>(null);
  const [sqlPath, setSqlPath] = useState("");
  const [sqlResult, setSqlResult] = useState("");
  const [checks, setChecks] = useState<Check[]>([]);
  const [ready, setReady] = useState(false);

  const build = async () => {
    setBusy(true);
    setError("");
    setStatus("Building content pack…");
    try {
      const scn = scenarioIds
        .split(/[,\s]+/)
        .filter(Boolean)
        .map((s) => Number(s))
        .filter((n) => Number.isFinite(n));
      const body: Record<string, unknown> = {
        name,
        equipment: {
          meshIndex: Number(meshIndex) || meshIndex,
          char,
          desc: itemDesc,
        },
        map: {
          draft: { name: mapName, playTime: 180, breathTime: 100 },
          scenarioIds: scn,
          stageScript,
        },
        stage: {
          member: stageScript,
          fields: {},
        },
      };
      if (includeFtm) {
        body.ftm = {
          archive: ftmArchive,
          member: ftmMember,
          patches: [{ index: 0, x: 10, y: 10 }],
        };
      }
      const pack = await api<{
        ok?: boolean;
        outDir?: string;
        installPlan?: Array<{ source: string; destRelative: string }>;
        parts?: { map?: { sql?: string }; equipment?: { sql?: string } };
      }>("/api/content-pack/build", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setManifest(pack);
      const mapSql = pack.parts?.map?.sql ?? pack.parts?.equipment?.sql ?? "";
      setSqlPath(mapSql);
      setStatus(
        `Built · ${pack.installPlan?.length ?? 0} install files · ${pack.outDir ?? ""}`,
      );
      setChecks([]);
      setReady(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Build failed");
    } finally {
      setBusy(false);
    }
  };

  const install = async () => {
    if (!manifest?.installPlan?.length) {
      setError("Build a pack first");
      return;
    }
    setBusy(true);
    setError("");
    setStatus("Installing to local client…");
    try {
      const result = await api<{ ok?: boolean; installed?: Record<string, string> }>(
        "/api/client/install",
        {
          method: "POST",
          body: JSON.stringify({ files: manifest.installPlan }),
        },
      );
      setStatus(
        `Installed · ${Object.keys(result.installed ?? {}).length} paths`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Install failed");
    } finally {
      setBusy(false);
    }
  };

  const sqlDryRun = async () => {
    if (!sqlPath) {
      setError("No SQL path from pack (map create)");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api<{
        ok?: boolean;
        dryRun?: boolean;
        audit?: { insertCount?: number; statementCount?: number; safe?: boolean };
        error?: string;
      }>("/api/sql/apply", {
        method: "POST",
        body: JSON.stringify({ path: sqlPath, dryRun: true }),
      });
      setSqlResult(
        `Dry-run · statements ${result.audit?.statementCount ?? "?"} · inserts ${result.audit?.insertCount ?? "?"} · safe=${result.audit?.safe}`,
      );
      setStatus("SQL dry-run complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("SQL dry-run failed");
    } finally {
      setBusy(false);
    }
  };

  const sqlApply = async () => {
    if (!sqlPath) {
      setError("No SQL path");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api<{
        ok?: boolean;
        applied?: boolean;
        error?: string;
        hint?: string;
      }>("/api/sql/apply", {
        method: "POST",
        body: JSON.stringify({ path: sqlPath, dryRun: false }),
      });
      if (!result.ok) {
        throw new Error(result.error ?? result.hint ?? "apply failed");
      }
      setSqlResult(`Applied · applied=${result.applied}`);
      setStatus("SQL applied to database");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("SQL apply failed (need JFTSE_DATABASE_URL + mysql client)");
    } finally {
      setBusy(false);
    }
  };

  const runPlaytest = async () => {
    setBusy(true);
    setError("");
    setStatus("Running playtest checklist…");
    try {
      const body: Record<string, unknown> = {};
      if (manifest?.installPlan) body.installPlan = manifest.installPlan;
      if (sqlPath) body.sqlPath = sqlPath;
      const result = await api<{
        ready?: boolean;
        checklist?: Check[];
        checks?: Check[];
        launchCommand?: string;
      }>("/api/content-pack/playtest-full", {
        method: "POST",
        body: JSON.stringify(body),
      });
      const list = result.checklist ?? result.checks ?? [];
      setChecks(list);
      setReady(Boolean(result.ready));
      setStatus(
        result.ready
          ? `Playtest ready · ${result.launchCommand ?? "launch local client"}`
          : "Playtest incomplete — fix failing checks",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Playtest check failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="workspace">
      <section className="panel" aria-label="Pack configuration">
        <header>
          <h2>Content pack</h2>
        </header>
        <div className="body">
          <p className="empty">
            One path: build multi-asset pack → install local client → dry-run/apply map SQL →
            checklist. Stock client writes are refused.
          </p>
          <div className="field-grid">
            <label>
              Pack name
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label>
              Mesh index
              <input value={meshIndex} onChange={(e) => setMeshIndex(e.target.value)} />
            </label>
            <label>
              Character
              <input value={char} onChange={(e) => setChar(e.target.value)} />
            </label>
            <label>
              Item name
              <input value={itemDesc} onChange={(e) => setItemDesc(e.target.value)} />
            </label>
            <label>
              Map name
              <input value={mapName} onChange={(e) => setMapName(e.target.value)} />
            </label>
            <label>
              Scenario ids
              <input value={scenarioIds} onChange={(e) => setScenarioIds(e.target.value)} />
            </label>
            <label>
              Stage script
              <input value={stageScript} onChange={(e) => setStageScript(e.target.value)} />
            </label>
            <label>
              <span>
                <input
                  type="checkbox"
                  checked={includeFtm}
                  onChange={(e) => setIncludeFtm(e.target.checked)}
                />{" "}
                Include FTM patch sample
              </span>
            </label>
            {includeFtm && (
              <>
                <label>
                  FTM archive
                  <input value={ftmArchive} onChange={(e) => setFtmArchive(e.target.value)} />
                </label>
                <label>
                  FTM member
                  <input value={ftmMember} onChange={(e) => setFtmMember(e.target.value)} />
                </label>
              </>
            )}
          </div>
          <div className="actions">
            <button className="btn primary" type="button" disabled={busy} onClick={() => void build()}>
              1 · Build pack
            </button>
            <button
              className="btn primary"
              type="button"
              disabled={busy || !manifest?.installPlan?.length}
              onClick={() => void install()}
            >
              2 · Install local
            </button>
            <button
              className="btn"
              type="button"
              disabled={busy || !sqlPath}
              onClick={() => void sqlDryRun()}
            >
              3 · SQL dry-run
            </button>
            <button
              className="btn"
              type="button"
              disabled={busy || !sqlPath}
              onClick={() => void sqlApply()}
            >
              3b · SQL apply
            </button>
            <button
              className="btn primary"
              type="button"
              disabled={busy}
              onClick={() => void runPlaytest()}
            >
              4 · Playtest checklist
            </button>
          </div>
        </div>
      </section>

      <section className="panel" aria-label="Pack status">
        <header>
          <h2>Status</h2>
        </header>
        <div className="body">
          <div className="empty">{status}</div>
          {error && (
            <div className="mono" style={{ color: "var(--danger)" }} role="alert">
              {error}
            </div>
          )}
          {manifest?.outDir && (
            <div>
              <strong>Out</strong>
              <div className="mono">{manifest.outDir}</div>
            </div>
          )}
          {sqlPath && (
            <div>
              <strong>Map SQL</strong>
              <div className="mono">{sqlPath}</div>
            </div>
          )}
          {sqlResult && <div className="empty mono">{sqlResult}</div>}
          {manifest?.installPlan && (
            <ul className="validation">
              {manifest.installPlan.map((f) => (
                <li key={f.destRelative} className="ok">
                  FILE — {f.destRelative}
                </li>
              ))}
            </ul>
          )}
          {checks.length > 0 && (
            <>
              <strong>Playtest</strong>
              <ul className="validation">
                <li className={ready ? "ok" : "bad"}>
                  {ready ? "PASS" : "TODO"} — overall ready
                </li>
                {checks.map((row, i) => (
                  <li key={row.id ?? row.destRelative ?? i} className={row.ok ? "ok" : "bad"}>
                    {row.ok ? "PASS" : "MISS"} — {row.label ?? row.destRelative ?? row.path}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
