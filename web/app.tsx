import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { MapStudio } from "./MapStudio.tsx";
import { MeshStudio } from "./MeshStudio.tsx";

type WorkspaceMode = "items" | "maps" | "meshes";
type StepId = "item" | "effect" | "export" | "install" | "playtest";

type Atlas = {
  archive: string;
  member: string;
  texturePath: string;
  className: string;
  banned: boolean;
};

type Item = {
  index: string;
  part: string;
  mesh: string;
  tex: string;
  effect: string;
  name: string;
};

type MapRow = {
  id: number;
  map: number;
  name: string;
  isBossStage: boolean;
};

type Preset = {
  id: string;
  name: string;
  summary: string;
  effect?: EffectDraft;
};

type EffectDraft = {
  texturePath: string;
  color: string;
  quantity: number;
  speed: number;
  life: number;
  size: number;
  offAxisSpread: number;
  offPlaneSpread: number;
  phase: number;
  phaseVar: number;
  subTexSize: string;
  subTexCount: number;
  allowBannedAtlas: boolean;
  includeItemBinding: boolean;
};

type PackSummary = {
  file: string;
  name?: string;
  savedAt?: string;
};

type SetupCheck = { id: string; ok: boolean; label: string };

type SetupInfo = {
  ready: boolean;
  stockClient: string;
  localClient: string;
  jftseRoot: string;
  stockExists: boolean;
  localExists: boolean;
  particleRes: boolean;
  itemRes: boolean;
  stageInfo: boolean;
  installReady: boolean;
  checklist: SetupCheck[];
};

type ExportRow = {
  kind: string;
  name: string;
  path: string;
  relativePath: string;
  bytes: number;
  mtimeMs: number;
};

const GS_KEY = "studio.gettingStarted.dismissed";

const STEPS: Array<{ id: StepId; title: string; detail: string }> = [
  { id: "item", title: "1 · Item", detail: "Pick a stock racket base" },
  { id: "effect", title: "2 · Effect", detail: "Preset + atlas + emitter" },
  { id: "export", title: "3 · Export", detail: "Build verified archives" },
  { id: "install", title: "4 · Install", detail: "Write local client only" },
  { id: "playtest", title: "5 · Playtest", detail: "Launch Equipment check" },
];

const defaultEffect = (): EffectDraft => ({
  texturePath: "Res/Effect/EftB/A_feather",
  color: "80,160,205",
  quantity: 18,
  speed: 0.3,
  life: 16,
  size: 1.4,
  offAxisSpread: 180,
  offPlaneSpread: 180,
  phase: 180,
  phaseVar: 100,
  subTexSize: "STS_64",
  subTexCount: 8,
  allowBannedAtlas: false,
  includeItemBinding: false,
});

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

function ParticlePreview({ draft }: { draft: EffectDraft }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const size = 360;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    type P = {
      x: number;
      y: number;
      vx: number;
      vy: number;
      life: number;
      max: number;
      r: number;
      rot: number;
    };
    const particles: P[] = [];
    const count = Math.max(1, Math.min(40, draft.quantity));
    const [cr, cg, cb] = draft.color.split(",").map((v) => Number(v.trim()) || 0);
    const spawn = (): P => {
      const angle =
        ((Math.random() * draft.offAxisSpread - draft.offAxisSpread / 2) * Math.PI) /
        180;
      const speed = draft.speed * (0.8 + Math.random() * 0.4) * 2.2;
      return {
        x: size / 2,
        y: size / 2 + 20,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 0.2,
        life: 0,
        max: Math.max(6, draft.life),
        r: Math.max(2, draft.size * 4),
        rot:
          ((draft.phase + (Math.random() * 2 - 1) * draft.phaseVar) * Math.PI) / 180,
      };
    };
    for (let i = 0; i < count; i += 1) particles.push(spawn());
    let frame = 0;
    let raf = 0;
    const draw = () => {
      ctx.clearRect(0, 0, size, size);
      ctx.fillStyle = "rgba(255,255,255,0.04)";
      ctx.beginPath();
      ctx.ellipse(size / 2, size / 2 + 28, 18, 54, -0.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "rgba(232,238,249,0.35)";
      ctx.stroke();
      for (const p of particles) {
        if (!reduced) {
          p.x += p.vx;
          p.y += p.vy;
          p.vy += 0.01;
          p.life += 1;
          if (p.life > p.max) Object.assign(p, spawn());
        }
        const alpha = Math.max(0, 1 - p.life / p.max) * 0.85;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot + frame * 0.01);
        const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, p.r * 2.2);
        gradient.addColorStop(0, `rgba(${cr},${cg},${cb},${alpha})`);
        gradient.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.ellipse(0, 0, p.r * 0.55, p.r * 1.8, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
      frame += 1;
      if (!reduced) raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [draft]);
  return (
    <canvas
      className="preview-canvas"
      ref={canvasRef}
      aria-label="Approximate particle preview"
    />
  );
}

function App() {
  const [workspace, setWorkspace] = useState<WorkspaceMode>("items");
  const [step, setStep] = useState<StepId>("item");
  const [healthOk, setHealthOk] = useState(false);
  const [healthDetail, setHealthDetail] = useState("connecting…");
  const [launchHint, setLaunchHint] = useState("");
  const [localClient, setLocalClient] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [atlases, setAtlases] = useState<Atlas[]>([]);
  const [maps, setMaps] = useState<MapRow[]>([]);
  const [stageScripts, setStageScripts] = useState<string[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [itemQuery, setItemQuery] = useState("");
  const [atlasQuery, setAtlasQuery] = useState("feather");
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [selectedMap, setSelectedMap] = useState<MapRow | null>(null);
  const [stageScript, setStageScript] = useState("");
  const [effect, setEffect] = useState<EffectDraft>(defaultEffect);
  const [status, setStatus] = useState("Pick a stock racket to begin.");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastExport, setLastExport] = useState<{
    particleArchive?: string;
    itemArchive?: string;
    effectArchive?: string;
  }>({});
  const [verification, setVerification] = useState("");
  const [installedPath, setInstalledPath] = useState("");
  const [mapSqlPath, setMapSqlPath] = useState("");
  const [packName, setPackName] = useState(`designer-${Date.now()}`);
  const [notes, setNotes] = useState("");
  const [setup, setSetup] = useState<SetupInfo | null>(null);
  const [exportsList, setExportsList] = useState<ExportRow[]>([]);
  const [showGettingStarted, setShowGettingStarted] = useState(() => {
    try {
      return localStorage.getItem(GS_KEY) !== "1";
    } catch {
      return true;
    }
  });
  const [installConfirmOpen, setInstallConfirmOpen] = useState(false);
  const [toast, setToast] = useState("");

  const pushToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast((current) => (current === message ? "" : current)), 3200);
  };

  const copyText = async (value: string, label: string) => {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    pushToast(`${label} copied`);
    setStatus(`${label} copied`);
  };

  const refreshExports = async () => {
    try {
      const data = await api<{ exports: ExportRow[] }>("/api/exports?limit=12");
      setExportsList(data.exports ?? []);
    } catch {
      /* non-fatal */
    }
  };

  useEffect(() => {
    void (async () => {
      try {
        const health = await api<{
          ok: boolean;
          localClient?: string;
          launchHint?: string;
          stockClient?: string;
          setup?: SetupInfo;
        }>("/api/health");
        setHealthOk(Boolean(health.ok));
        setLocalClient(health.localClient ?? "");
        setLaunchHint(health.launchHint ?? "");
        setSetup(health.setup ?? null);
        setHealthDetail(
          health.setup?.ready
            ? (health.localClient ?? health.stockClient ?? "ready")
            : "Setup incomplete — expand checklist",
        );
      } catch (err) {
        setHealthOk(false);
        setSetup(null);
        setHealthDetail(err instanceof Error ? err.message : String(err));
      }
    })();
    void refreshExports();
  }, []);

  useEffect(() => {
    void api<{ items: Item[] }>(`/api/items?part=RACKET&limit=120`)
      .then((data) => {
        setItems(data.items);
        const preferred =
          data.items.find((item) => item.index === "10728") ??
          data.items.find((item) => /dragon slayer/i.test(item.name)) ??
          data.items[0] ??
          null;
        setSelectedItem(preferred);
      })
      .catch((err: unknown) => setError(String(err)));
    void api<{ presets: Preset[] }>("/api/presets")
      .then((data) => setPresets(data.presets))
      .catch((err: unknown) => setError(String(err)));
    void api<{ maps: MapRow[]; stageScripts: string[] }>("/api/maps")
      .then((data) => {
        setMaps(data.maps);
        setStageScripts(data.stageScripts);
        setSelectedMap(data.maps[0] ?? null);
        setStageScript(data.stageScripts[0] ?? "");
      })
      .catch((err: unknown) => setError(String(err)));
    void api<{ packs: PackSummary[] }>("/api/packs")
      .then((data) => setPacks(data.packs))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void api<{ atlases: Atlas[] }>(
        `/api/atlases?limit=80&q=${encodeURIComponent(atlasQuery)}`,
      )
        .then((data) => setAtlases(data.atlases))
        .catch((err: unknown) => setError(String(err)));
    }, 200);
    return () => window.clearTimeout(handle);
  }, [atlasQuery]);

  const filteredItems = useMemo(() => {
    const q = itemQuery.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) =>
      `${item.name} ${item.index} ${item.mesh}`.toLowerCase().includes(q),
    );
  }, [items, itemQuery]);

  const validation = useMemo(() => {
    const banned = /spaak|spark|electric|cloud_ice|a_cloud/i.test(effect.texturePath);
    return [
      {
        ok: Boolean(selectedItem),
        text: selectedItem
          ? `Base item #${selectedItem.index} ${selectedItem.name}`
          : "Choose a base racket",
      },
      {
        ok: !banned || effect.allowBannedAtlas,
        text: banned
          ? effect.allowBannedAtlas
            ? "Banned atlas override enabled"
            : "Atlas class is banned"
          : "Atlas class allowed",
      },
      {
        ok: effect.quantity >= 1 && effect.quantity <= 40,
        text: `Quantity ${effect.quantity} in range`,
      },
      {
        ok: Boolean(lastExport.particleArchive),
        text: lastExport.particleArchive
          ? "Verified export ready"
          : "Export not built yet",
      },
      {
        ok: Boolean(installedPath),
        text: installedPath ? "Installed to local client" : "Not installed yet",
      },
    ];
  }, [selectedItem, effect, lastExport, installedPath]);

  const applyPreset = async (presetId: string) => {
    const local = presets.find((preset) => preset.id === presetId);
    if (local?.effect) {
      setEffect({ ...defaultEffect(), ...local.effect });
      setStatus(`Applied preset: ${local.name}`);
      return;
    }
    const remote = await api<{ presets: Array<Preset & { effect: EffectDraft }> }>(
      "/api/presets",
    );
    const found = remote.presets.find((preset) => preset.id === presetId);
    if (found?.effect) {
      setEffect({ ...defaultEffect(), ...found.effect });
      setStatus(`Applied preset: ${found.name}`);
    }
  };

  const buildExport = async () => {
    setBusy(true);
    setError("");
    setStatus(
      effect.includeItemBinding
        ? "Building full binding pack (can take ~1–2 min)…"
        : "Building verified particle pack…",
    );
    try {
      const result = await api<{
        particleArchive?: string;
        itemArchive?: string;
        effectArchive?: string;
        verification?: Record<string, unknown>;
      }>("/api/effects/preview-build", {
        method: "POST",
        body: JSON.stringify(effect),
      });
      setLastExport({
        particleArchive: result.particleArchive,
        itemArchive: result.itemArchive ?? undefined,
        effectArchive: result.effectArchive ?? undefined,
      });
      setVerification(JSON.stringify(result.verification ?? {}, null, 2));
      setStatus("Export verified. Continue to Install.");
      setStep("install");
      pushToast("Effect pack built and verified");
      void refreshExports();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Export failed");
    } finally {
      setBusy(false);
    }
  };

  const requestInstall = () => {
    if (!lastExport.particleArchive) {
      setError("Build an export first");
      return;
    }
    if (!localClient) {
      setError("Local client is not configured");
      return;
    }
    setInstallConfirmOpen(true);
  };

  const installLocal = async () => {
    if (!lastExport.particleArchive) {
      setError("Build an export first");
      return;
    }
    setInstallConfirmOpen(false);
    setBusy(true);
    setError("");
    setStatus("Installing to local client…");
    try {
      const result = await api<{ installed?: { particle?: string } }>(
        "/api/effects/install",
        {
          method: "POST",
          body: JSON.stringify({
            particleArchive: lastExport.particleArchive,
            itemArchive: lastExport.itemArchive,
            effectArchive: lastExport.effectArchive,
            targetClient: localClient,
          }),
        },
      );
      setInstalledPath(result.installed?.particle ?? localClient);
      setStatus("Installed. Continue to Playtest.");
      setStep("playtest");
      pushToast("Installed to local client");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Install failed");
    } finally {
      setBusy(false);
    }
  };

  const savePack = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await api<{ path: string; pack: PackSummary }>("/api/packs", {
        method: "POST",
        body: JSON.stringify({
          name: packName,
          step,
          item: selectedItem,
          effect,
          map: selectedMap,
          stageScript,
          export: lastExport,
          notes,
        }),
      });
      setStatus(`Pack saved: ${result.path}`);
      const packsResponse = await api<{ packs: PackSummary[] }>("/api/packs");
      setPacks(packsResponse.packs);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const loadPack = async (file: string) => {
    setBusy(true);
    setError("");
    try {
      const name = file.replace(/\.json$/i, "");
      const result = await api<{
        pack: {
          item?: Item;
          effect?: EffectDraft;
          map?: MapRow;
          stageScript?: string;
          export?: typeof lastExport;
          notes?: string;
          step?: StepId;
          name?: string;
        };
      }>(`/api/packs/${encodeURIComponent(name)}`);
      const pack = result.pack;
      if (pack.item) setSelectedItem(pack.item);
      if (pack.effect) setEffect({ ...defaultEffect(), ...pack.effect });
      if (pack.map) setSelectedMap(pack.map);
      if (pack.stageScript) setStageScript(pack.stageScript);
      if (pack.export) setLastExport(pack.export);
      if (pack.notes) setNotes(pack.notes);
      if (pack.name) setPackName(pack.name);
      if (pack.step) setStep(pack.step);
      setStatus(`Loaded pack ${file}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const exportMapSql = async () => {
    if (!selectedMap) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<{ path: string }>("/api/maps/export-sql", {
        method: "POST",
        body: JSON.stringify({
          maps: [selectedMap],
          stageByMap: { [String(selectedMap.map)]: stageScript },
        }),
      });
      setMapSqlPath(result.path);
      setStatus(`Map SQL exported: ${result.path}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const selectedAtlas = atlases.find(
    (atlas) => atlas.texturePath === effect.texturePath,
  );

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>JFTSE Content Studio</strong>
          <span>Items · Maps · Meshes · stock-safe export</span>
        </div>
        <nav className="tabs" aria-label="Workspace modes">
          <button
            className="tab"
            type="button"
            aria-selected={workspace === "items"}
            onClick={() => setWorkspace("items")}
          >
            Items
          </button>
          <button
            className="tab"
            type="button"
            aria-selected={workspace === "maps"}
            onClick={() => setWorkspace("maps")}
          >
            Map Studio
          </button>
          <button
            className="tab"
            type="button"
            aria-selected={workspace === "meshes"}
            onClick={() => setWorkspace("meshes")}
          >
            Mesh Studio
          </button>
        </nav>
        {workspace === "items" && (
          <nav className="tabs" aria-label="Workflow steps">
            {STEPS.map((entry) => (
              <button
                key={entry.id}
                className="tab"
                type="button"
                aria-selected={step === entry.id}
                onClick={() => setStep(entry.id)}
                title={entry.detail}
              >
                {entry.title}
              </button>
            ))}
          </nav>
        )}
        <div className={`chip ${healthOk && setup?.ready !== false ? "ok" : "bad"}`} title={healthDetail}>
          {!healthOk
            ? "Bridge down"
            : setup && !setup.ready
              ? "Setup incomplete"
              : "Bridge online"}
        </div>
        <button
          className="btn"
          type="button"
          onClick={() => setShowGettingStarted(true)}
          aria-label="Open getting started guide"
        >
          Getting started
        </button>
      </header>

      {toast && (
        <div className="toast" role="status" aria-live="polite">
          {toast}
        </div>
      )}

      {showGettingStarted && (
        <section className="banner panel-lite" aria-label="Getting started">
          <div className="banner-copy">
            <strong>Day-1 designer path</strong>
            <ol>
              <li>
                <strong>Items</strong> — pick Dragon Slayer → soft wind preset → Build &amp; verify →
                Install to local client → copy launch command and check Equipment.
              </li>
              <li>
                <strong>Map Studio</strong> — open a map → Validate stage assets → Export SQL map pack.
              </li>
              <li>
                <strong>Mesh Studio</strong> — select a court DAT → confirm 3D view → Export OBJ + glTF.
              </li>
            </ol>
            <p className="empty">
              Browser particle preview is approximate. The live game client is the authority for aura look.
              Custom terrain sculpting and Blender-parity mesh editing stay out of scope.
            </p>
          </div>
          <button
            className="btn primary"
            type="button"
            onClick={() => {
              try {
                localStorage.setItem(GS_KEY, "1");
              } catch {
                /* ignore */
              }
              setShowGettingStarted(false);
              pushToast("Getting started dismissed");
            }}
          >
            Dismiss guide
          </button>
        </section>
      )}

      {setup && !setup.ready && (
        <section className="banner panel-lite warn" aria-label="Setup checklist">
          <div className="banner-copy">
            <strong>Finish environment setup</strong>
            <ul className="validation">
              {setup.checklist.map((row) => (
                <li key={row.id} className={row.ok ? "ok" : "bad"}>
                  {row.ok ? "PASS" : "TODO"} — {row.label}
                </li>
              ))}
            </ul>
            <p className="empty">
              Export <code>JFTSE_ROOT</code>, <code>JFTSE_STOCK_CLIENT</code>, and{" "}
              <code>JFTSE_LOCAL_CLIENT</code>, then restart <code>bun run dev</code>.
            </p>
          </div>
        </section>
      )}

      {workspace === "maps" ? (
        <MapStudio />
      ) : workspace === "meshes" ? (
        <MeshStudio />
      ) : (
      <main className="workspace">
        <section className="panel" aria-label="Library">
          <header>
            <h2>
              {step === "item" && "Racket library"}
              {step === "effect" && "Atlases & presets"}
              {step === "export" && "Export checklist"}
              {step === "install" && "Install target"}
              {step === "playtest" && "Playtest kit"}
            </h2>
          </header>
          <div className="body">
            {step === "item" && (
              <>
                <label>
                  Search rackets
                  <input
                    value={itemQuery}
                    onChange={(event) => setItemQuery(event.target.value)}
                    placeholder="dragon, 10728, mesh…"
                  />
                </label>
                <div className="list">
                  {filteredItems.map((item) => (
                    <button
                      key={item.index}
                      type="button"
                      data-active={selectedItem?.index === item.index}
                      onClick={() => {
                        setSelectedItem(item);
                        setStatus(`Selected ${item.name}. Continue to Effect.`);
                      }}
                    >
                      {item.name}
                      <small>
                        #{item.index} · mesh {item.mesh} · effect {item.effect}
                      </small>
                    </button>
                  ))}
                </div>
              </>
            )}

            {step === "effect" && (
              <>
                <div className="list">
                  {presets.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => void applyPreset(preset.id)}
                    >
                      {preset.name}
                      <small>{preset.summary}</small>
                    </button>
                  ))}
                </div>
                <label>
                  Search atlases
                  <input
                    value={atlasQuery}
                    onChange={(event) => setAtlasQuery(event.target.value)}
                    placeholder="feather, wind, soft…"
                  />
                </label>
                <div className="atlas-grid">
                  {atlases.slice(0, 24).map((atlas) => {
                    const src = `/api/atlases/preview?archive=${encodeURIComponent(atlas.archive)}&member=${encodeURIComponent(atlas.member)}`;
                    return (
                      <button
                        key={`${atlas.archive}:${atlas.member}`}
                        type="button"
                        className="atlas-card"
                        data-active={effect.texturePath === atlas.texturePath}
                        onClick={() =>
                          setEffect((prev) => ({
                            ...prev,
                            texturePath: atlas.texturePath,
                          }))
                        }
                      >
                        <img src={src} alt={atlas.member} loading="lazy" />
                        <span>
                          {atlas.member}
                          <small>
                            <span
                              className={`badge ${atlas.banned ? "banned" : atlas.className}`}
                            >
                              {atlas.className}
                            </span>
                          </small>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </>
            )}

            {(step === "export" || step === "install" || step === "playtest") && (
              <ul className="validation">
                {validation.map((row) => (
                  <li key={row.text} className={row.ok ? "ok" : "bad"}>
                    {row.ok ? "PASS" : "TODO"} — {row.text}
                  </li>
                ))}
              </ul>
            )}

            <div>
              <strong>Saved packs</strong>
              <div className="list" style={{ marginTop: "0.5rem" }}>
                {packs.length === 0 && <p className="empty">No packs yet.</p>}
                {packs.map((pack) => (
                  <button
                    key={pack.file}
                    type="button"
                    onClick={() => void loadPack(pack.file)}
                  >
                    {pack.name ?? pack.file}
                    <small>{pack.savedAt ?? pack.file}</small>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="panel" aria-label="Editor">
          <header>
            <h2>
              {step === "item" && "Base item"}
              {step === "effect" && "Emitter"}
              {step === "export" && "Build export"}
              {step === "install" && "Install"}
              {step === "playtest" && "Playtest"}
            </h2>
          </header>
          <div className="body">
            {step === "item" && selectedItem && (
              <>
                <div className="field-grid">
                  <label>
                    Name
                    <input value={selectedItem.name} readOnly />
                  </label>
                  <label>
                    Index
                    <input value={selectedItem.index} readOnly />
                  </label>
                  <label>
                    Mesh
                    <input value={selectedItem.mesh} readOnly />
                  </label>
                  <label>
                    Tex
                    <input value={selectedItem.tex} readOnly />
                  </label>
                  <label>
                    Stock effect id
                    <input value={selectedItem.effect} readOnly />
                  </label>
                  <label>
                    Part
                    <input value={selectedItem.part} readOnly />
                  </label>
                </div>
                <p className="empty">
                  Designers start from a stock racket so mesh/UV contracts stay valid. Effect work
                  is isolated to dormant particle slots; optional Dragon Slayer binding can be
                  enabled in the Effect step.
                </p>
                <div className="actions">
                  <button
                    className="btn primary"
                    type="button"
                    onClick={() => setStep("effect")}
                  >
                    Continue to Effect
                  </button>
                </div>
              </>
            )}

            {step === "effect" && (
              <>
                <div className="field-grid">
                  <label>
                    Texture path
                    <input
                      value={effect.texturePath}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          texturePath: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <label>
                    Color RGB
                    <input
                      value={effect.color}
                      onChange={(event) =>
                        setEffect((prev) => ({ ...prev, color: event.target.value }))
                      }
                    />
                  </label>
                  <label>
                    Quantity
                    <input
                      type="number"
                      value={effect.quantity}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          quantity: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    Speed
                    <input
                      type="number"
                      step="0.01"
                      value={effect.speed}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          speed: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    Life
                    <input
                      type="number"
                      value={effect.life}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          life: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    Size
                    <input
                      type="number"
                      step="0.05"
                      value={effect.size}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          size: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    Off-axis spread
                    <input
                      type="number"
                      value={effect.offAxisSpread}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          offAxisSpread: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    Off-plane spread
                    <input
                      type="number"
                      value={effect.offPlaneSpread}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          offPlaneSpread: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    SubTex size
                    <select
                      value={effect.subTexSize}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          subTexSize: event.target.value,
                        }))
                      }
                    >
                      <option value="STS_32">STS_32</option>
                      <option value="STS_64">STS_64</option>
                      <option value="STS_128">STS_128</option>
                    </select>
                  </label>
                  <label>
                    SubTex count
                    <input
                      type="number"
                      value={effect.subTexCount}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          subTexCount: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                </div>
                <label>
                  <span>
                    <input
                      type="checkbox"
                      checked={effect.allowBannedAtlas}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          allowBannedAtlas: event.target.checked,
                        }))
                      }
                    />{" "}
                    Allow banned atlas classes (dangerous)
                  </span>
                </label>
                <label>
                  <span>
                    <input
                      type="checkbox"
                      checked={effect.includeItemBinding}
                      onChange={(event) =>
                        setEffect((prev) => ({
                          ...prev,
                          includeItemBinding: event.target.checked,
                        }))
                      }
                    />{" "}
                    Include Item/ETC Dragon Slayer binding (~1–2 min)
                  </span>
                </label>
                <div className="actions">
                  <button
                    className="btn primary"
                    type="button"
                    onClick={() => setStep("export")}
                  >
                    Continue to Export
                  </button>
                </div>
              </>
            )}

            {step === "export" && (
              <>
                <p className="empty">
                  Builds a fixed-size `Particle.res` replacing only dormant `Ice_Smoke02.set`.
                  Shared racket glitter scripts stay untouched.
                </p>
                <div className="field-grid">
                  <label>
                    Pack name
                    <input
                      value={packName}
                      onChange={(event) => setPackName(event.target.value)}
                    />
                  </label>
                  <label>
                    Designer notes
                    <input
                      value={notes}
                      onChange={(event) => setNotes(event.target.value)}
                      placeholder="soft cyan aura for DS black"
                    />
                  </label>
                </div>
                <div className="actions">
                  <button
                    className="btn primary"
                    type="button"
                    disabled={busy}
                    onClick={() => void buildExport()}
                  >
                    {busy ? "Working…" : "Build & verify export"}
                  </button>
                  <button
                    className="btn"
                    type="button"
                    disabled={busy}
                    onClick={() => void savePack()}
                  >
                    Save content pack
                  </button>
                </div>
                {lastExport.particleArchive && (
                  <div className="path-row">
                    <div className="mono">{lastExport.particleArchive}</div>
                    <button
                      className="btn"
                      type="button"
                      onClick={() => void copyText(lastExport.particleArchive ?? "", "Export path")}
                    >
                      Copy path
                    </button>
                  </div>
                )}
                <div className="exports-block">
                  <strong>Recent exports</strong>
                  {exportsList.length === 0 ? (
                    <p className="empty">No exports yet — build a pack to populate this library.</p>
                  ) : (
                    <ul className="export-list">
                      {exportsList.slice(0, 6).map((row) => (
                        <li key={`${row.path}-${row.mtimeMs}`}>
                          <button
                            type="button"
                            className="export-item"
                            onClick={() => void copyText(row.path, row.name)}
                            title={row.path}
                          >
                            <span className="chip tiny">{row.kind}</span>
                            <span>{row.relativePath}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}

            {step === "install" && (
              <>
                <p className="empty">
                  Install writes only the allowlisted local client. Stock client installs are
                  rejected by the API.
                </p>
                <div className="path-row">
                  <div className="mono">{localClient || "local client not configured"}</div>
                  {localClient && (
                    <button
                      className="btn"
                      type="button"
                      onClick={() => void copyText(localClient, "Local client path")}
                    >
                      Copy path
                    </button>
                  )}
                </div>
                <div className="actions">
                  <button
                    className="btn primary"
                    type="button"
                    disabled={busy || !lastExport.particleArchive}
                    onClick={requestInstall}
                  >
                    {busy ? "Installing…" : "Install to local client"}
                  </button>
                  <button className="btn" type="button" onClick={() => setStep("export")}>
                    Back to export
                  </button>
                </div>
                {installedPath && (
                  <div className="path-row">
                    <div className="mono">{installedPath}</div>
                    <button
                      className="btn"
                      type="button"
                      onClick={() => void copyText(installedPath, "Installed path")}
                    >
                      Copy path
                    </button>
                  </div>
                )}
                <div className="exports-block" aria-label="Recent exports">
                  <strong>Recent exports</strong>
                  {exportsList.length === 0 ? (
                    <p className="empty">No exports yet.</p>
                  ) : (
                    <ul className="export-list">
                      {exportsList.slice(0, 6).map((row) => (
                        <li key={`install-${row.path}-${row.mtimeMs}`}>
                          <button
                            type="button"
                            className="export-item"
                            onClick={() => void copyText(row.path, row.name)}
                            title={row.path}
                          >
                            <span className="chip tiny">{row.kind}</span>
                            <span>{row.relativePath}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}

            {step === "playtest" && (
              <>
                <p className="empty">
                  Browser preview is approximate. Open Equipment with the +9 Dragon Slayer (or your
                  bound item) and confirm silhouette + aura.
                </p>
                <div className="mono">{launchHint}</div>
                <div className="actions">
                  <button
                    className="btn primary"
                    type="button"
                    onClick={() => void copyText(launchHint, "Launch command")}
                  >
                    Copy launch command
                  </button>
                  <button
                    className="btn"
                    type="button"
                    disabled={busy}
                    onClick={() => void savePack()}
                  >
                    Save final pack
                  </button>
                </div>
                <hr className="divider" />
                <h3 className="subhead">Optional map metadata</h3>
                <div className="field-grid">
                  <label>
                    Map
                    <select
                      value={selectedMap ? String(selectedMap.map) : ""}
                      onChange={(event) => {
                        const next = maps.find(
                          (map) => String(map.map) === event.target.value,
                        );
                        setSelectedMap(next ?? null);
                      }}
                    >
                      {maps.map((map) => (
                        <option key={map.id} value={map.map}>
                          {map.name} ({map.map})
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Stage script
                    <select
                      value={stageScript}
                      onChange={(event) => setStageScript(event.target.value)}
                    >
                      {stageScripts.map((script) => (
                        <option key={script} value={script}>
                          {script}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="actions">
                  <button
                    className="btn"
                    type="button"
                    disabled={busy}
                    onClick={() => void exportMapSql()}
                  >
                    Export map SQL seed
                  </button>
                </div>
                {mapSqlPath && <div className="mono">{mapSqlPath}</div>}
              </>
            )}
          </div>
        </section>

        <section className="panel" aria-label="Preview">
          <header>
            <h2>Preview & status</h2>
          </header>
          <div className="body">
            <ParticlePreview draft={effect} />
            {selectedAtlas && (
              <div className="selected-atlas">
                <img
                  src={`/api/atlases/preview?archive=${encodeURIComponent(selectedAtlas.archive)}&member=${encodeURIComponent(selectedAtlas.member)}`}
                  alt={selectedAtlas.member}
                />
                <div>
                  <strong>{selectedAtlas.member}</strong>
                  <div className="empty">{selectedAtlas.texturePath}</div>
                </div>
              </div>
            )}
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
            {verification && (
              <div>
                <strong>Verification</strong>
                <div className="mono">{verification}</div>
              </div>
            )}
            <ul className="validation">
              {validation.map((row) => (
                <li key={`side-${row.text}`} className={row.ok ? "ok" : "bad"}>
                  {row.ok ? "PASS" : "TODO"} — {row.text}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
      )}

      {installConfirmOpen && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={() => !busy && setInstallConfirmOpen(false)}
        >
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="install-confirm-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 id="install-confirm-title">Install to local client?</h3>
            <p className="empty">
              Writes verified <code>Particle.res</code> into the allowlisted local client only. The
              stock client path is refused by the API.
            </p>
            <div className="mono">{localClient}</div>
            {lastExport.particleArchive && (
              <div className="mono">{lastExport.particleArchive}</div>
            )}
            <div className="actions">
              <button
                className="btn primary"
                type="button"
                disabled={busy}
                onClick={() => void installLocal()}
              >
                Confirm install
              </button>
              <button
                className="btn"
                type="button"
                disabled={busy}
                onClick={() => setInstallConfirmOpen(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className="footer">
        <span>
          {workspace === "maps"
            ? "Map Studio: catalog → stage validate → relational SQL pack (geometry stays stock-bound)"
            : workspace === "meshes"
              ? "Mesh Studio: decode Stage/Sky/Collision DAT → view/transform → export OBJ/glTF"
              : "Items: stock racket → preset → verify export → local install → Equipment QA"}
        </span>
        <span className="mono">{healthDetail}</span>
      </footer>
    </div>
  );
}

const rootElement = document.getElementById("root");
if (rootElement) {
  const existing = (
    rootElement as HTMLElement & { __studioRoot?: ReturnType<typeof createRoot> }
  ).__studioRoot;
  const root = existing ?? createRoot(rootElement);
  (
    rootElement as HTMLElement & { __studioRoot?: ReturnType<typeof createRoot> }
  ).__studioRoot = root;
  root.render(<App />);
}
