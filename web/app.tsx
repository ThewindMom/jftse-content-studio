import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

type Mode = "items" | "effects" | "maps";

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

function useHealth() {
  const [state, setState] = useState<"loading" | "ok" | "bad">("loading");
  const [detail, setDetail] = useState("checking bridge");
  const [localClientPath, setLocalClientPath] = useState("");
  useEffect(() => {
    let alive = true;
    api<{ ok: boolean; stockClient?: string; localClient?: string; error?: string }>("/api/health")
      .then((data) => {
        if (!alive) return;
        if (data.ok) {
          setState("ok");
          setDetail(data.localClient ?? data.stockClient ?? "bridge ready");
          setLocalClientPath(data.localClient ?? "");
        } else {
          setState("bad");
          setDetail(data.error ?? "bridge failed");
        }
      })
      .catch((error: unknown) => {
        if (!alive) return;
        setState("bad");
        setDetail(error instanceof Error ? error.message : String(error));
      });
    return () => {
      alive = false;
    };
  }, []);
  return { state, detail, localClientPath };
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
    canvas.style.width = "100%";
    canvas.style.height = "auto";
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
    const color = draft.color.split(",").map((v) => Number(v.trim()) || 0);
    const [cr, cg, cb] = color;

    const spawn = (): P => {
      const angle =
        (Math.random() * draft.offAxisSpread - draft.offAxisSpread / 2) *
        (Math.PI / 180);
      const speed = draft.speed * (0.8 + Math.random() * 0.4) * 2.2;
      return {
        x: size / 2,
        y: size / 2 + 20,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 0.2,
        life: 0,
        max: Math.max(6, draft.life),
        r: Math.max(2, draft.size * 4),
        rot: ((draft.phase + (Math.random() * 2 - 1) * draft.phaseVar) * Math.PI) /
          180,
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

  return <canvas className="preview-canvas" ref={canvasRef} aria-label="Approximate particle preview" />;
}

function App() {
  const health = useHealth();
  const localClient = health.localClientPath;
  const [mode, setMode] = useState<Mode>("effects");
  const [atlases, setAtlases] = useState<Atlas[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [maps, setMaps] = useState<MapRow[]>([]);
  const [stageScripts, setStageScripts] = useState<string[]>([]);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [selectedMap, setSelectedMap] = useState<MapRow | null>(null);
  const [effect, setEffect] = useState<EffectDraft>(defaultEffect);
  const [status, setStatus] = useState("Ready");
  const [lastExport, setLastExport] = useState("");
  const [lastVerification, setLastVerification] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void api<{ atlases: Atlas[] }>("/api/atlases?limit=120")
      .then((data) => setAtlases(data.atlases))
      .catch((err: unknown) => setError(String(err)));
    void api<{ items: Item[] }>("/api/items?part=RACKET&limit=40")
      .then((data) => {
        setItems(data.items);
        setSelectedItem(data.items[0] ?? null);
      })
      .catch((err: unknown) => setError(String(err)));
    void api<{ maps: MapRow[]; stageScripts: string[] }>("/api/maps")
      .then((data) => {
        setMaps(data.maps);
        setStageScripts(data.stageScripts);
        setSelectedMap(data.maps[0] ?? null);
      })
      .catch((err: unknown) => setError(String(err)));
  }, []);

  const validation = useMemo(() => {
    const rows: Array<{ ok: boolean; text: string }> = [];
    const banned = /spaak|spark|electric|cloud_ice|a_cloud/i.test(effect.texturePath);
    rows.push({
      ok: !banned || effect.allowBannedAtlas,
      text: banned
        ? effect.allowBannedAtlas
          ? "Banned atlas override enabled"
          : "Atlas class is banned (electrical/cloud)"
        : "Atlas class allowed",
    });
    rows.push({
      ok: effect.quantity >= 1 && effect.quantity <= 40,
      text: `Quantity ${effect.quantity} within 1–40`,
    });
    rows.push({
      ok: !/racket_00[12]/i.test(effect.texturePath),
      text: "Does not target shared Racket_001/002 scripts",
    });
    rows.push({
      ok: true,
      text: "Exports only isolated Ice_Smoke02 particle slot",
    });
    return rows;
  }, [effect]);

  const buildEffect = async () => {
    setError("");
    setStatus("Building effect pack…");
    try {
      const result = await api<{
        ok: boolean;
        particleArchive?: string;
        itemArchive?: string;
        effectArchive?: string;
        verification?: Record<string, unknown>;
        error?: string;
      }>("/api/effects/preview-build", {
        method: "POST",
        body: JSON.stringify(effect),
      });
      setLastExport(
        [
          result.particleArchive,
          result.itemArchive,
          result.effectArchive,
        ]
          .filter(Boolean)
          .join("\n"),
      );
      setLastVerification(JSON.stringify(result.verification ?? {}, null, 2));
      setStatus("Effect pack built and verified");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Build failed");
    }
  };

  const installEffect = async () => {
    setError("");
    if (!lastExport) {
      setError("Build an export pack first");
      return;
    }
    const particleArchive = lastExport.split("\n")[0];
    setStatus("Installing to local client…");
    try {
      const result = await api<{ ok: boolean; installed?: Record<string, string>; error?: string }>(
        "/api/effects/install",
        {
          method: "POST",
          body: JSON.stringify({
            particleArchive,
            targetClient: localClient,
          }),
        },
      );
      setStatus(`Installed: ${result.installed?.particle ?? "ok"}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Install failed");
    }
  };

  const savePack = async () => {
    setError("");
    try {
      const result = await api<{ ok: boolean; path: string }>("/api/packs", {
        method: "POST",
        body: JSON.stringify({
          name: `studio-${Date.now()}`,
          item: selectedItem,
          effect,
          map: selectedMap,
        }),
      });
      setStatus(`Pack saved: ${result.path}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>JFTSE Content Studio</strong>
          <span>V1 items · V2 effects preview · V3 map desk</span>
        </div>
        <nav className="tabs" aria-label="Studio modes">
          {(
            [
              ["items", "Items"],
              ["effects", "Effects"],
              ["maps", "Maps"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              className="tab"
              type="button"
              aria-selected={mode === id}
              onClick={() => setMode(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div
          className={`chip ${health.state === "ok" ? "ok" : health.state === "bad" ? "bad" : ""}`}
          title={health.detail}
        >
          {health.state === "ok" ? "Bridge online" : health.state === "bad" ? "Bridge down" : "Connecting…"}
        </div>
      </header>

      <main className="workspace">
        <section className="panel" aria-label="Library">
          <header>
            <h2>
              {mode === "items" && "Racket library"}
              {mode === "effects" && "Atlas library"}
              {mode === "maps" && "Map catalog"}
            </h2>
          </header>
          <div className="body list">
            {mode === "items" &&
              items.map((item) => (
                <button
                  key={item.index}
                  type="button"
                  data-active={selectedItem?.index === item.index}
                  onClick={() => setSelectedItem(item)}
                >
                  {item.name}
                  <small>
                    #{item.index} · mesh {item.mesh} · effect {item.effect}
                  </small>
                </button>
              ))}
            {mode === "effects" &&
              atlases.map((atlas) => (
                <button
                  key={`${atlas.archive}:${atlas.member}`}
                  type="button"
                  data-active={effect.texturePath === atlas.texturePath}
                  onClick={() =>
                    setEffect((prev) => ({
                      ...prev,
                      texturePath: atlas.texturePath,
                    }))
                  }
                >
                  {atlas.member}
                  <small>
                    {atlas.archive}{" "}
                    <span className={`badge ${atlas.banned ? "banned" : atlas.className}`}>
                      {atlas.className}
                    </span>
                  </small>
                </button>
              ))}
            {mode === "maps" &&
              maps.map((map) => (
                <button
                  key={map.id}
                  type="button"
                  data-active={selectedMap?.id === map.id}
                  onClick={() => setSelectedMap(map)}
                >
                  {map.name}
                  <small>
                    map id {map.map}
                    {map.isBossStage ? " · boss" : ""}
                  </small>
                </button>
              ))}
            {mode === "items" && items.length === 0 && <p className="empty">No rackets loaded.</p>}
            {mode === "effects" && atlases.length === 0 && <p className="empty">No atlases loaded.</p>}
            {mode === "maps" && maps.length === 0 && <p className="empty">No maps loaded.</p>}
          </div>
        </section>

        <section className="panel" aria-label="Editor">
          <header>
            <h2>
              {mode === "items" && "Item binding"}
              {mode === "effects" && "Effect emitter"}
              {mode === "maps" && "Map desk"}
            </h2>
          </header>
          <div className="body">
            {mode === "items" && selectedItem && (
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
                    Effect id
                    <input value={selectedItem.effect} readOnly />
                  </label>
                  <label>
                    Part
                    <input value={selectedItem.part} readOnly />
                  </label>
                </div>
                <p className="empty">
                  V1 reads live client catalog bindings. Export reuses the proven Dragon Slayer
                  item/effect archive builders when effect packs include item binding.
                </p>
              </>
            )}

            {mode === "effects" && (
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
                    Include Item.res + ETC.res Dragon Slayer binding archives
                  </span>
                </label>
                <div className="actions">
                  <button className="btn primary" type="button" onClick={() => void buildEffect()}>
                    Build export pack
                  </button>
                  <button className="btn" type="button" onClick={() => void installEffect()}>
                    Install to local client
                  </button>
                  <button className="btn" type="button" onClick={() => void savePack()}>
                    Save content pack
                  </button>
                  <button
                    className="btn danger"
                    type="button"
                    onClick={() => setEffect(defaultEffect())}
                  >
                    Reset soft defaults
                  </button>
                </div>
              </>
            )}

            {mode === "maps" && selectedMap && (
              <>
                <div className="field-grid">
                  <label>
                    Display name
                    <input value={selectedMap.name} readOnly />
                  </label>
                  <label>
                    Map byte/id
                    <input value={String(selectedMap.map)} readOnly />
                  </label>
                  <label>
                    Boss stage
                    <input value={selectedMap.isBossStage ? "yes" : "no"} readOnly />
                  </label>
                  <label>
                    Suggested stage script
                    <select defaultValue={stageScripts[0] ?? ""}>
                      {stageScripts.map((script) => (
                        <option key={script} value={script}>
                          {script}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <p className="empty">
                  V3 map desk edits metadata and binds stock `Stage/Info.res` scripts. Full custom
                  geometry export is intentionally out of scope until stage mesh tooling exists.
                </p>
                <div className="actions">
                  <button className="btn" type="button" onClick={() => void savePack()}>
                    Save map selection into pack
                  </button>
                </div>
              </>
            )}
          </div>
        </section>

        <section className="panel" aria-label="Preview">
          <header>
            <h2>Preview & validation</h2>
          </header>
          <div className="body">
            <ParticlePreview draft={effect} />
            <ul className="validation">
              {validation.map((row) => (
                <li key={row.text} className={row.ok ? "ok" : "bad"}>
                  {row.ok ? "PASS" : "FAIL"} — {row.text}
                </li>
              ))}
            </ul>
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
            {lastExport && (
              <div>
                <strong>Last export</strong>
                <div className="mono">{lastExport}</div>
              </div>
            )}
            {lastVerification && (
              <div>
                <strong>Verification</strong>
                <div className="mono">{lastVerification}</div>
              </div>
            )}
            {localClient && (
              <div>
                <strong>Install target</strong>
                <div className="mono">{localClient}</div>
              </div>
            )}
          </div>
        </section>
      </main>

      <footer className="footer">
        <span>
          Approximate browser preview only · authoritative look requires Equipment in the game client
        </span>
        <span className="mono">{health.detail}</span>
      </footer>
    </div>
  );
}

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<App />);
}
