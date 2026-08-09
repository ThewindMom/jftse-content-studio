import { useEffect, useMemo, useState } from "react";
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
  bossPlayTime: number | null;
  breathTime: number;
  description: string | null;
  playTime: number | null;
  triggerBossTime: number | null;
  useBreathTime: boolean;
  scenarioIds: number[];
  guardianCount: number;
  guardians: Guardian[];
  stageCandidates: string[];
  defaultStageScript: string | null;
};

type Scenario = {
  id: number;
  name: string;
  description?: string;
  gameMode?: string;
  isDefault?: boolean;
  statusId?: number;
};

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

type RetryAction = "catalog" | "validation";

class StudioApiError extends Error {
  constructor(
    readonly code: string,
    readonly detail?: unknown,
  ) {
    super(code);
  }
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  const data = (await response.json()) as T & {
    error?: string;
    detail?: unknown;
  };
  if (!response.ok) {
    throw new StudioApiError(
      data.error ?? `HTTP ${response.status}`,
      data.detail,
    );
  }
  return data;
}

function errorText(error: unknown): string {
  if (error instanceof StudioApiError) {
    const detail = typeof error.detail === "string"
      ? error.detail
      : error.detail == null
      ? ""
      : JSON.stringify(error.detail, null, 2);
    return detail ? `${error.code}\n${detail}` : error.code;
  }
  return error instanceof Error ? error.message : String(error);
}

export function MapStudio({
  active,
  onOpenMesh,
}: {
  active: boolean;
  onOpenMesh?: (archive: string, member: string) => void;
}) {
  const [maps, setMaps] = useState<MapStudioRow[]>([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [stageScript, setStageScript] = useState("");
  const [includeScenarios, setIncludeScenarios] = useState(true);
  const [includeGuardians, setIncludeGuardians] = useState(true);
  const [status, setStatus] = useState("Loading map catalog…");
  const [error, setError] = useState("");
  const [retryAction, setRetryAction] = useState<RetryAction | null>(null);
  const [busy, setBusy] = useState(false);
  const [validation, setValidation] = useState<ValidateResult | null>(null);
  const [exportPath, setExportPath] = useState("");
  const [draftName, setDraftName] = useState("");
  const [draftBoss, setDraftBoss] = useState(false);
  const [draftPlayTime, setDraftPlayTime] = useState("");
  const [draftBossPlayTime, setDraftBossPlayTime] = useState("");
  const [draftTriggerBoss, setDraftTriggerBoss] = useState("");
  const [draftBreath, setDraftBreath] = useState("100");
  const [draftDescription, setDraftDescription] = useState("");
  const [draftScenarioIds, setDraftScenarioIds] = useState("");
  const [worldFileOverride, setWorldFileOverride] = useState("");
  const [createName, setCreateName] = useState("Custom Court");
  const hasCurrentValidStage =
    validation?.valid === true && validation.stageScript === stageScript;
  const validationReason = !stageScript
    ? "Choose a stage script first."
    : validation?.stageScript !== stageScript
    ? "Validate the current stage script before exporting."
    : validation.valid
    ? ""
    : "Resolve the failed stage checks, then validate again.";
  const worldPath = useMemo(() => {
    const hit = validation?.assetChecks.find(
      (check) => check.field === "WorldFile" && check.exists && check.path,
    );
    return hit?.path ?? "";
  }, [validation]);

  const loadCatalog = async () => {
    setError("");
    setRetryAction(null);
    setStatus("Loading map catalog…");
    try {
      const data = await api<{
      ok: boolean;
      maps: MapStudioRow[];
      scenarios: Scenario[];
      relationCounts: Record<string, number>;
      }>("/api/map-studio/catalog");
      setMaps(data.maps);
      if (selectedId == null) {
        const first = data.maps[0] ?? null;
        setSelectedId(first?.id ?? null);
        setStageScript(first?.defaultStageScript ?? "");
        setDraftName(first?.name ?? "");
        setDraftBoss(Boolean(first?.isBossStage));
        setDraftPlayTime(first?.playTime == null ? "" : String(first.playTime));
        setDraftBossPlayTime(
          first?.bossPlayTime == null ? "" : String(first.bossPlayTime),
        );
        setDraftTriggerBoss(
          first?.triggerBossTime == null ? "" : String(first.triggerBossTime),
        );
        setDraftBreath(String(first?.breathTime ?? 100));
        setDraftDescription(first?.description ?? "");
        setDraftScenarioIds((first?.scenarioIds ?? []).join(","));
      }
      setStatus(
        `Loaded ${data.maps.length} maps · ${data.relationCounts.map2scenarios} scenario links · ${data.relationCounts.guardian2maps} guardian rows`,
      );
    } catch (err) {
      setError(errorText(err));
      setRetryAction("catalog");
      setStatus("Failed to load map catalog");
    }
  };

  useEffect(() => {
    void loadCatalog();
    // Initial catalog load only; Retry invokes the latest closure.
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    setDraftPlayTime(selected.playTime == null ? "" : String(selected.playTime));
    setDraftBossPlayTime(
      selected.bossPlayTime == null ? "" : String(selected.bossPlayTime),
    );
    setDraftTriggerBoss(
      selected.triggerBossTime == null ? "" : String(selected.triggerBossTime),
    );
    setDraftBreath(String(selected.breathTime ?? 100));
    setDraftDescription(selected.description ?? "");
    setDraftScenarioIds(selected.scenarioIds.join(","));
    setValidation(null);
    setExportPath("");
  }, [selectedId]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectMap = (row: MapStudioRow) => {
    setSelectedId(row.id);
    setStageScript(row.defaultStageScript ?? row.stageCandidates[0] ?? "");
    setDraftName(row.name);
    setDraftBoss(row.isBossStage);
    setDraftPlayTime(row.playTime == null ? "" : String(row.playTime));
    setDraftBossPlayTime(row.bossPlayTime == null ? "" : String(row.bossPlayTime));
    setDraftTriggerBoss(
      row.triggerBossTime == null ? "" : String(row.triggerBossTime),
    );
    setDraftBreath(String(row.breathTime ?? 100));
    setDraftDescription(row.description ?? "");
    setDraftScenarioIds(row.scenarioIds.join(","));
    setValidation(null);
    setExportPath("");
    setError("");
    setRetryAction(null);
    setStatus(`Selected ${row.name} (map byte ${row.map})`);
  };

  const draftPayload = () => {
    const optInt = (raw: string) => {
      const t = raw.trim();
      if (!t) return null;
      const n = Number(t);
      return Number.isFinite(n) ? Math.trunc(n) : null;
    };
    return {
      name: draftName,
      isBossStage: draftBoss,
      playTime: optInt(draftPlayTime),
      bossPlayTime: optInt(draftBossPlayTime),
      triggerBossTime: optInt(draftTriggerBoss),
      breathTime: optInt(draftBreath) ?? 100,
      description: draftDescription || null,
    };
  };

  const validateStage = async () => {
    if (!stageScript) {
      setError("Choose a stage script");
      return;
    }
    setBusy(true);
    setError("");
    setRetryAction(null);
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
      setError(errorText(err));
      setRetryAction("validation");
      setStatus("Stage validation failed");
    } finally {
      setBusy(false);
    }
  };

  const exportPack = async () => {
    if (!selected || !hasCurrentValidStage) return;
    setBusy(true);
    setError("");
    setRetryAction(null);
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
          draft: draftPayload(),
        }),
      });
      setExportPath(result.path);
      setStatus(
        `Exported pack · maps ${result.mapCount} · scenarios ${result.scenarioLinkCount} · guardians ${result.guardianCount}`,
      );
    } catch (err) {
      setError(errorText(err));
      setStatus("Map pack export failed");
    } finally {
      setBusy(false);
    }
  };

  const saveMapPack = async () => {
    if (!selected) return;
    setBusy(true);
    setError("");
    setRetryAction(null);
    try {
      const result = await api<{ path: string }>("/api/packs", {
        method: "POST",
        body: JSON.stringify({
          name: `map-${selected.map}-${Date.now()}`,
          step: "maps",
          map: {
            ...selected,
            ...draftPayload(),
            stageScript,
          },
          stageScript,
          notes: `Map studio draft for ${draftName}`,
          export: exportPath ? { sql: exportPath } : null,
        }),
      });
      setStatus(`Saved map content pack: ${result.path}`);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const createNewMap = async () => {
    if (!hasCurrentValidStage) return;
    setBusy(true);
    setError("");
    setRetryAction(null);
    setStatus("Creating greenfield map SQL…");
    try {
      const scenarioIds = draftScenarioIds
        .split(/[,\s]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number(s))
        .filter((n) => Number.isFinite(n));
      const result = await api<{ path: string; map: MapStudioRow }>(
        "/api/map-studio/create",
        {
          method: "POST",
          body: JSON.stringify({
            draft: {
              name: createName || "Custom Court",
              isBossStage: draftBoss,
              playTime: draftPlayTime ? Number(draftPlayTime) : 180,
              breathTime: draftBreath ? Number(draftBreath) : 100,
              description: draftDescription || "custom map",
              bossPlayTime: draftBossPlayTime ? Number(draftBossPlayTime) : null,
              triggerBossTime: draftTriggerBoss
                ? Number(draftTriggerBoss)
                : null,
            },
            scenarioIds,
            stageScript: stageScript || "1_Emerald_Beach.set",
            includeScenarios: includeScenarios,
            includeGuardians: includeGuardians,
          }),
        },
      );
      setExportPath(result.path);
      setStatus(
        `Created map SQL · id ${result.map.id} map byte ${result.map.map} → ${result.path}`,
      );
    } catch (err) {
      setError(errorText(err));
      setStatus("Map create failed");
    } finally {
      setBusy(false);
    }
  };

  const writeStageSet = async () => {
    if (!stageScript) {
      setError("Choose a stage script");
      return;
    }
    setBusy(true);
    setError("");
    setRetryAction(null);
    setStatus("Writing stage .set…");
    try {
      const fields: Record<string, string> = {};
      if (worldFileOverride.trim()) {
        fields.WorldFile = worldFileOverride.trim();
      }
      const result = await api<{ infoArchive: string; setPath: string }>(
        "/api/stage-set/write",
        {
          method: "POST",
          body: JSON.stringify({
            member: stageScript,
            fields,
          }),
        },
      );
      setStatus(`Stage set written · ${result.infoArchive}`);
    } catch (err) {
      setError(errorText(err));
      setStatus("Stage set write failed");
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
            {maps.length === 0 && !error && (
              <p className="empty">No maps are available in the catalog.</p>
            )}
            {maps.length > 0 && filtered.length === 0 && (
              <p className="empty">
                No maps match “{query.trim()}”. Clear the search to browse all maps.
              </p>
            )}
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
                    onChange={(event) => {
                      setStageScript(event.target.value);
                      setValidation(null);
                      setExportPath("");
                      setError("");
                      setRetryAction(null);
                      setStatus("Stage script changed — validation required.");
                    }}
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
                  Scenario ids (comma)
                  <input
                    value={draftScenarioIds}
                    onChange={(event) => setDraftScenarioIds(event.target.value)}
                    placeholder="1, 2"
                  />
                </label>
                <label>
                  bossPlayTime
                  <input
                    value={draftBossPlayTime}
                    onChange={(event) => setDraftBossPlayTime(event.target.value)}
                    placeholder="NULL"
                  />
                </label>
                <label>
                  playTime
                  <input
                    value={draftPlayTime}
                    onChange={(event) => setDraftPlayTime(event.target.value)}
                    placeholder="NULL"
                  />
                </label>
                <label>
                  triggerBossTime
                  <input
                    value={draftTriggerBoss}
                    onChange={(event) => setDraftTriggerBoss(event.target.value)}
                    placeholder="NULL"
                  />
                </label>
                <label>
                  breathTime
                  <input
                    value={draftBreath}
                    onChange={(event) => setDraftBreath(event.target.value)}
                  />
                </label>
                <label>
                  description
                  <input
                    value={draftDescription}
                    onChange={(event) => setDraftDescription(event.target.value)}
                  />
                </label>
                <label>
                  New map name (create)
                  <input
                    value={createName}
                    onChange={(event) => setCreateName(event.target.value)}
                  />
                </label>
                <label>
                  WorldFile override (stage write)
                  <input
                    value={worldFileOverride}
                    onChange={(event) => setWorldFileOverride(event.target.value)}
                    placeholder="Res/Stage/Mesh01/BF_Court01.dat"
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
                  disabled={busy || !hasCurrentValidStage}
                  onClick={() => void exportPack()}
                  title={validationReason || undefined}
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
                <button
                  className="btn primary"
                  type="button"
                  disabled={busy || !hasCurrentValidStage}
                  onClick={() => void createNewMap()}
                  title={validationReason || undefined}
                >
                  Create new map SQL
                </button>
                <button
                  className="btn"
                  type="button"
                  disabled={busy || !stageScript}
                  onClick={() => void writeStageSet()}
                >
                  Write stage .set
                </button>
              </div>

              <p className="empty">
                Map Studio authors server metadata (including greenfield create), validates stage
                graphs, writes stage .set packs, multi-draws World + Object layers, and authors FTM
                placements. Court mesh topology: Mesh Studio transform/export; full Blender
                authoring remains out of scope.
              </p>
              {!hasCurrentValidStage && (
                <p className="empty">{validationReason}</p>
              )}
              {(stageScript || worldPath) && (
                <>
                  <strong>Stage scene compositor</strong>
                  <StageMeshPreview
                    active={active}
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
            <div role="alert">
              <strong>Error</strong>
              <pre className="mono" style={{ color: "var(--danger)" }}>
                {error}
              </pre>
              {retryAction && (
                <button
                  className="btn"
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    void (retryAction === "catalog"
                      ? loadCatalog()
                      : validateStage())
                  }
                >
                  Retry {retryAction === "catalog" ? "map catalog" : "stage validation"}
                </button>
              )}
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
