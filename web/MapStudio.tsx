import React, { useEffect, useMemo, useState } from "react";
import { FtmDesk } from "./FtmDesk.tsx";
import { StageMeshPreview } from "./StageMeshPreview.tsx";

type Guardian = {
  id: number;
  side: string;
  bossGuardianId: number | null;
  guardianId: number | null;
  mapId: number;
  scenarioId: number;
  statusId: number;
};

export type MapStudioRow = {
  id: number;
  map: number;
  name: string;
  isBossStage: boolean;
  scenarioIds: number[];
  guardianCount: number;
  guardians: Guardian[];
  stageCandidates: string[];
  defaultStageScript: string | null;
};

type Scenario = { id: number; name: string };

type ValidateResult = {
  valid: boolean;
  stageScript: string;
  stage: Record<string, string>;
  assetChecks: Array<{
    field: string;
    path: string;
    exists: boolean;
    resolved?: string;
    kind?: string;
  }>;
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  const data = (await response.json()) as T & { error?: string };
  if (!response.ok) {
    throw new Error(data.error ?? `HTTP ${response.status}`);
  }
  return data;
}

export function MapStudio({
  onOpenMesh,
}: {
  onOpenMesh?: (archive: string, member: string) => void;
} = {}) {
  const [maps, setMaps] = useState<MapStudioRow[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [stageScript, setStageScript] = useState("");
  const [includeScenarios, setIncludeScenarios] = useState(true);
  const [includeGuardians, setIncludeGuardians] = useState(true);
  const [status, setStatus] = useState("Loading map catalog…");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [validation, setValidation] = useState<ValidateResult | null>(null);
  const [exportPath, setExportPath] = useState("");
  const [draftName, setDraftName] = useState("");
  const [draftBoss, setDraftBoss] = useState(false);
  const worldPath = useMemo(() => {
    const hit = validation?.assetChecks.find(
      (check) => check.field === "WorldFile" && check.exists && check.path,
    );
    return hit?.path ?? "";
  }, [validation]);

  useEffect(() => {
    void api<{
      ok: boolean;
      maps: MapStudioRow[];
      scenarios: Scenario[];
      relationCounts: Record<string, number>;
    }>("/api/map-studio/catalog")
      .then((data) => {
        setMaps(data.maps);
        setScenarios(data.scenarios);
        const first = data.maps[0] ?? null;
        setSelectedId(first?.id ?? null);
        setStageScript(first?.defaultStageScript ?? "");
        setDraftName(first?.name ?? "");
        setDraftBoss(Boolean(first?.isBossStage));
        setStatus(
          `Loaded ${data.maps.length} maps · ${data.relationCounts.map2scenarios} scenario links · ${data.relationCounts.guardian2maps} guardian rows`,
        );
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
        setStatus("Failed to load map catalog");
      });
  }, []);

  const selected = useMemo(
    () => maps.find((row) => row.id === selectedId) ?? null,
    [maps, selectedId],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return maps;
    return maps.filter((row) =>
      `${row.name} ${row.map} ${row.id} ${row.defaultStageScript ?? ""}`
        .toLowerCase()
        .includes(q),
    );
  }, [maps, query]);

  useEffect(() => {
    if (!selected) return;
    setStageScript(selected.defaultStageScript ?? selected.stageCandidates[0] ?? "");
    setDraftName(selected.name);
    setDraftBoss(selected.isBossStage);
    setValidation(null);
    setExportPath("");
  }, [selectedId]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectMap = (row: MapStudioRow) => {
    setSelectedId(row.id);
    setStageScript(row.defaultStageScript ?? row.stageCandidates[0] ?? "");
    setDraftName(row.name);
    setDraftBoss(row.isBossStage);
    setValidation(null);
    setExportPath("");
    setStatus(`Selected ${row.name} (map byte ${row.map})`);
  };

  const validateStage = async () => {
    if (!stageScript) {
      setError("Choose a stage script");
      return;
    }
    setBusy(true);
    setError("");
    setStatus("Validating stage assets…");
    try {
      const result = await api<ValidateResult>("/api/map-studio/validate", {
        method: "POST",
        body: JSON.stringify({ stageScript }),
      });
      setValidation(result);
      setStatus(
        result.valid
          ? `Stage valid: ${stageScript}`
          : `Stage has missing assets: ${stageScript}`,
      );
    } catch (err) {
      setValidation(null);
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Stage validation failed");
    } finally {
      setBusy(false);
    }
  };

  const exportPack = async () => {
    if (!selected) return;
    setBusy(true);
    setError("");
    setStatus("Exporting relational map pack…");
    try {
      const result = await api<{
        path: string;
        mapCount: number;
        scenarioLinkCount: number;
        guardianCount: number;
      }>("/api/map-studio/export-pack", {
        method: "POST",
        body: JSON.stringify({
          mapIds: [selected.id],
          stageByMapId: { [String(selected.id)]: stageScript },
          includeScenarios,
          includeGuardians,
          draft: {
            name: draftName,
            isBossStage: draftBoss,
          },
        }),
      });
      setExportPath(result.path);
      setStatus(
        `Exported pack · maps ${result.mapCount} · scenarios ${result.scenarioLinkCount} · guardians ${result.guardianCount}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Map pack export failed");
    } finally {
      setBusy(false);
    }
  };

  const saveMapPack = async () => {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<{ path: string }>("/api/packs", {
        method: "POST",
        body: JSON.stringify({
          name: `map-${selected.map}-${Date.now()}`,
          step: "maps",
          map: {
            ...selected,
            name: draftName,
            isBossStage: draftBoss,
            stageScript,
          },
          stageScript,
          notes: `Map studio draft for ${draftName}`,
          export: exportPath ? { sql: exportPath } : null,
        }),
      });
      setStatus(`Saved map content pack: ${result.path}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="workspace">
      <section className="panel" aria-label="Map catalog">
        <header>
          <h2>Map catalog</h2>
        </header>
        <div className="body">
          <label>
            Search maps
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="emerald, boss, arena…"
            />
          </label>
          <div className="list">
            {filtered.map((row) => (
              <button
                key={row.id}
                type="button"
                data-active={selectedId === row.id}
                onClick={() => selectMap(row)}
              >
                {row.name}
                <small>
                  id {row.id} · map {row.map}
                  {row.isBossStage ? " · boss" : ""} · scn{" "}
                  {row.scenarioIds.join(",") || "—"} · g {row.guardianCount}
                </small>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="panel" aria-label="Map editor">
        <header>
          <h2>Map design desk</h2>
        </header>
        <div className="body">
          {!selected && <p className="empty">Select a map to inspect bindings.</p>}
          {selected && (
            <>
              <div className="field-grid">
                <label>
                  Display name
                  <input
                    value={draftName}
                    onChange={(event) => setDraftName(event.target.value)}
                  />
                </label>
                <label>
                  Map byte
                  <input value={String(selected.map)} readOnly />
                </label>
                <label>
                  Database id
                  <input value={String(selected.id)} readOnly />
                </label>
                <label>
                  Boss stage
                  <select
                    value={draftBoss ? "yes" : "no"}
                    onChange={(event) => setDraftBoss(event.target.value === "yes")}
                  >
                    <option value="no">no</option>
                    <option value="yes">yes</option>
                  </select>
                </label>
                <label>
                  Stage script
                  <select
                    value={stageScript}
                    onChange={(event) => setStageScript(event.target.value)}
                  >
                    {(selected.stageCandidates.length
                      ? selected.stageCandidates
                      : [stageScript].filter(Boolean)
                    ).map((script) => (
                      <option key={script} value={script}>
                        {script}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Scenarios
                  <input
                    readOnly
                    value={
                      selected.scenarioIds
                        .map((id) => {
                          const row = scenarios.find((scenario) => scenario.id === id);
                          return row ? `${id}:${row.name}` : String(id);
                        })
                        .join(", ") || "none"
                    }
                  />
                </label>
              </div>

              <label>
                <span>
                  <input
                    type="checkbox"
                    checked={includeScenarios}
                    onChange={(event) => setIncludeScenarios(event.target.checked)}
                  />{" "}
                  Include Map_2_Scenarios links in export
                </span>
              </label>
              <label>
                <span>
                  <input
                    type="checkbox"
                    checked={includeGuardians}
                    onChange={(event) => setIncludeGuardians(event.target.checked)}
                  />{" "}
                  Include Guardian_2_Maps rows in export
                </span>
              </label>

              <div className="actions">
                <button
                  className="btn primary"
                  type="button"
                  disabled={busy}
                  onClick={() => void validateStage()}
                >
                  {busy ? "Working…" : "Validate stage assets"}
                </button>
                <button
                  className="btn primary"
                  type="button"
                  disabled={busy}
                  onClick={() => void exportPack()}
                >
                  Export SQL map pack
                </button>
                <button
                  className="btn"
                  type="button"
                  disabled={busy}
                  onClick={() => void saveMapPack()}
                >
                  Save map pack
                </button>
              </div>

              <p className="empty">
                Map Studio authors server metadata, validates stage asset graphs, multi-draws World +
                Object layers, and inspects FTM placements. Full terrain sculpting remains out of
                scope — open Mesh Studio for DAT recovery/export of bound geometry.
              </p>
              {(stageScript || worldPath) && (
                <>
                  <strong>Stage scene compositor</strong>
                  <StageMeshPreview
                    stageScript={stageScript || undefined}
                    worldPath={worldPath || undefined}
                    onOpenMesh={onOpenMesh}
                  />
                </>
              )}
            </>
          )}
        </div>
      </section>

      <section className="panel" aria-label="Map validation and FTM">
        <header>
          <h2>Stage & FTM</h2>
        </header>
        <div className="body">
          <div>
            <strong>Status</strong>
            <div className="empty">{status}</div>
          </div>
          {error && (
            <div>
              <strong>Error</strong>
              <div className="mono" style={{ color: "var(--danger)" }}>
                {error}
              </div>
            </div>
          )}
          {exportPath && (
            <div>
              <strong>Export</strong>
              <div className="mono">{exportPath}</div>
            </div>
          )}
          {validation && (
            <>
              <ul className="validation">
                <li className={validation.valid ? "ok" : "bad"}>
                  {validation.valid ? "PASS" : "FAIL"} — stage asset graph
                </li>
                {validation.assetChecks.map((check) => (
                  <li key={check.field} className={check.exists ? "ok" : "bad"}>
                    {check.exists ? "PASS" : "MISS"} — {check.field}: {check.path}
                  </li>
                ))}
              </ul>
              <div>
                <strong>Stage fields</strong>
                <div className="mono">
                  {Object.entries(validation.stage)
                    .slice(0, 16)
                    .map(([key, value]) => `${key}=${value}`)
                    .join("\n")}
                </div>
              </div>
            </>
          )}
          {selected && (
            <div>
              <strong>Guardians (sample)</strong>
              <div className="list" style={{ marginTop: "0.5rem" }}>
                {selected.guardians.length === 0 && (
                  <p className="empty">No guardian rows for this map.</p>
                )}
                {selected.guardians.map((guardian) => (
                  <div key={guardian.id} className="mono">
                    #{guardian.id} {guardian.side} scn {guardian.scenarioId} g=
                    {guardian.guardianId ?? "—"} boss={guardian.bossGuardianId ?? "—"}
                  </div>
                ))}
              </div>
            </div>
          )}
          <hr className="soft-rule" />
          <strong>FTM overworld desk</strong>
          <p className="empty">
            Inspect MapSet placements (FT-ResTool schema). Select markers to read prefab + transform
            fields.
          </p>
          <FtmDesk />
        </div>
      </section>
    </main>
  );
}
