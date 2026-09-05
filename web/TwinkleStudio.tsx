import { useEffect, useRef, useState } from "react";
import { TwinkleViewport, type CameraView } from "./TwinkleViewport.tsx";
import { assetLabel, courtClearance, isOriginalModel, parseMapDesign, parseTwinkleDocument, type MapDesign, type Placement, type TwinkleDocument, type TwinkleManifest } from "./twinkleDocument.ts";

async function request(path: string, init?: RequestInit) {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = await response.json();
    throw new Error(body.error ?? `Request failed (${response.status})`);
  }
  return response;
}
function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function NumberField({ label, value, onCommit, min = -10000, max = 10000, step = 1 }: {
  label: string; value: number; onCommit: (n: number) => void; min?: number; max?: number; step?: number;
}) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(Math.round(value * 1000) / 1000)), [value]);
  const commit = () => {
    const number = Number(draft);
    if (draft.trim() && Number.isFinite(number) && number >= min && number <= max) onCommit(number);
    else setDraft(String(value));
  };
  return <label>{label}<input aria-label={label} type="number" min={min} max={max} step={step}
    value={draft} onChange={(e) => setDraft(e.target.value)} onBlur={commit}
    onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }} /></label>;
}

type History = { past: TwinkleDocument[]; current: TwinkleDocument; future: TwinkleDocument[] };
export function TwinkleStudio({ mapId = "twinkle" }: { mapId?: MapDesign }) {
  const [manifest, setManifest] = useState<TwinkleManifest | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const [libraryQuery, setLibraryQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [mode, setMode] = useState<"translate" | "rotate">("translate");
  const [camera, setCamera] = useState<{ view: CameraView; revision: number }>({ view: "court", revision: 0 });
  const [snap, setSnap] = useState(1);
  const [guides, setGuides] = useState(false);
  const [isolate, setIsolate] = useState(false);
  const [lightmaps, setLightmaps] = useState(true);
  const [thumbnails, setThumbnails] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("Opening Twinkle Town…");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState("");
  const [retry, setRetry] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const doc = history?.current;
  const hasOriginals = doc?.objects.some((obj) => obj.visible && isOriginalModel(obj.file));
  const chosen = doc?.objects.find((o) => o.id === selected);
  const chosenAsset = manifest?.assets.find((a) => a.file === chosen?.file);
  const supported = new Set(manifest?.assets.filter((asset) => !asset.fixed).map((asset) => asset.file));
  const changed = doc && JSON.stringify(doc) !== saved;
  const frame = (view: CameraView) => setCamera((old) => ({ view, revision: old.revision + 1 }));
  const commit = (next: TwinkleDocument) => {
    try {
      const checked = parseTwinkleDocument(next);
      setHistory((old) => !old || JSON.stringify(old.current) === JSON.stringify(checked) ? old : {
        past: [...old.past.slice(-49), old.current], current: checked, future: [],
      });
      setError("");
    } catch (error) { setError(String(error)); }
  };
  const transform = (id: string, patch: Partial<Placement>) => {
    if (doc) commit({ ...doc, objects: doc.objects.map((obj) => obj.id === id ? { ...obj, ...patch } : obj) });
  };
  function undo() {
    setHistory((old) => {
      const previous = old?.past.at(-1);
      return old && previous ? { past: old.past.slice(0, -1), current: previous, future: [old.current, ...old.future] } : old;
    });
  }
  function redo() {
    setHistory((old) => {
      const next = old?.future[0];
      return old && next ? { past: [...old.past, old.current], current: next, future: old.future.slice(1) } : old;
    });
  }
  function duplicate() {
    if (!doc || !chosen) return;
    const copy = { ...chosen, id: crypto.randomUUID(), name: `${chosen.name.slice(0, 70)} copy`,
      position: [chosen.position[0] + 10, chosen.position[1], chosen.position[2]] satisfies [number, number, number] };
    commit({ ...doc, objects: [...doc.objects, copy] }); setSelected(copy.id);
  }
  function remove() {
    if (doc && chosen) { commit({ ...doc, objects: doc.objects.filter((o) => o.id !== chosen.id) }); setSelected(""); }
  }
  async function save() {
    if (!doc) return;
    setBusy(true);
    try {
      await request(`/api/twinkle/draft?map=${mapId}`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(doc) });
      setSaved(JSON.stringify(doc)); setStatus("Layout saved to Studio. Stock files unchanged."); setError("");
    } catch (error) { setError(String(error)); }
    finally { setBusy(false); }
  }
  async function exportPack() {
    if (!doc) return;
    setBusy(true); setStatus("Building and checking the encrypted stage archive…");
    try {
      const response = await request("/api/twinkle/export", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(doc) });
      download(await response.blob(), `${mapId}-layout.zip`);
      setStatus("ZIP checked. Installation steps are in README.txt. Copy its Res folder to a separate test client; select Twinkle Town.");
      setError("");
    } catch (error) { setError(String(error)); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const [sceneResponse, draftResponse] = await Promise.all([
          request(`/api/twinkle/scene?map=${mapId}`, { signal: controller.signal }),
          request(`/api/twinkle/draft?map=${mapId}`, { signal: controller.signal }),
        ]);
        const scene: TwinkleManifest = await sceneResponse.json();
        const stored: unknown = await draftResponse.json();
        let current = parseTwinkleDocument(scene.document);
        if (stored !== null) {
          const candidate = parseTwinkleDocument(stored);
          if (candidate.sourceHash === current.sourceHash && parseMapDesign(candidate.mapId) === mapId) {
            current = { ...candidate, objects: candidate.objects.map((obj) => ({
              ...scene.document.objects.find((original) => original.id === obj.id), ...obj,
            })) };
          }
          else throw new Error(`Source design changed. Your saved exports/${mapId}-layout.json is preserved. Back it up before starting a layout for this source.`);
        }
        if (controller.signal.aborted) return;
        setManifest(scene); setHistory({ past: [], current, future: [] });
        window.document.title = `${current.name} · Map Studio`;
        setSaved(JSON.stringify(current)); setStatus(stored ? "Saved layout opened." : `${scene.document.name} starting layout opened. Stock files stay intact.`);
      } catch (error) { if (!controller.signal.aborted) setError(String(error)); }
    })();
    return () => controller.abort();
  }, [retry, mapId]);
  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => { if (changed) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [changed]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLTextAreaElement) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); void save(); }
      else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") { event.preventDefault(); event.shiftKey ? redo() : undo(); }
      else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "d") { event.preventDefault(); duplicate(); }
      else if (event.key.toLowerCase() === "f") frame("selection");
      else if (event.key.toLowerCase() === "w") setMode("translate");
      else if (event.key.toLowerCase() === "e") setMode("rotate");
      else if (event.key === "Delete") remove();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });

  return <main className="tw-studio">
    <header className="tw-header">
      <a className="tw-brand" href="/" aria-label="Back to Content Studio"><span>FT</span> CONTENT STUDIO</a>
      <div className="tw-project"><a className="tw-pill" href="/map-studio">All maps</a><h1>{doc?.name ?? (mapId === "oktoberfest" ? "Oktoberfest" : "Twinkle Town")}</h1><span className="tw-save-state">{changed ? "Unsaved changes" : "Saved"}</span></div>
      <div className="tw-actions"><button disabled={!history?.past.length} onClick={undo} title="Undo · Ctrl Z">Undo</button>
        <button disabled={!history?.future.length} onClick={redo} title="Redo · Ctrl Shift Z">Redo</button>
        <button disabled={busy || !doc} onClick={() => void save()}>Save layout</button>
        <button className="tw-primary" disabled={busy || !doc} title={hasOriginals ? "Build DAT/TEX and collision additions for a separate test client. Native compatibility remains unverified." : undefined} onClick={() => void exportPack()}>{busy ? "Working…" : "Export stage ZIP"}</button></div>
    </header>
    {error && <div className="tw-error tw-banner" role="alert">{error} {!doc && <button onClick={() => { setError(""); setRetry((n) => n + 1); }}>Retry loading</button>}</div>}
    {!doc || !manifest ? <div className="tw-loading" role="status">{status}<p>Preparing private stock meshes and textures. No game client is required.</p></div> : <>
      <div className="tw-body">
        <aside className="tw-sidebar" aria-label="Scene objects">
          <div className="tw-section-title">Scene <span>{doc.objects.length} placements</span></div>
          <div className="tw-world"><span className="tw-dot" />Twinkle Town <small>Stock geometry · locked</small></div>
          <label className="tw-search"><span className="sr-only">Search scene objects</span><input placeholder="Find an object…" value={query} onChange={(e) => setQuery(e.target.value)} /></label>
          <div className="tw-object-list">
            <div className="tw-list-caption">YOUR SCENERY</div>
            {doc.objects.filter((obj) => !obj.id.startsWith("stock-") && obj.name.toLowerCase().includes(query.toLowerCase())).map((obj) =>
              <button className="tw-object" aria-pressed={selected === obj.id} key={obj.id} onClick={() => setSelected(obj.id)}><span>{obj.visible ? "◇" : "○"}</span>{obj.name}</button>)}
            {!doc.objects.some((obj) => !obj.id.startsWith("stock-")) && <p className="tw-empty">Choose a prop below the viewport to add your first object.</p>}
            <details open><summary>Stock placements · {doc.objects.filter((o) => o.id.startsWith("stock-")).length}</summary>
              <p className="tw-empty">Complete rest-pose previews. Animation is not played.</p>
              {doc.objects.filter((obj) => obj.id.startsWith("stock-") && obj.name.toLowerCase().includes(query.toLowerCase())).map((obj) =>
                <button className="tw-object" aria-pressed={selected === obj.id} key={obj.id} onClick={() => setSelected(obj.id)}>{obj.name}<small>{supported.has(obj.file) ? "rest pose" : "unavailable"}</small></button>)}
            </details>
          </div>
          <div className="tw-sidebar-foot"><strong>Stock stays intact</strong><p>Layout edits are separate from the original client. Export creates a new archive, never an installation.</p>
            {hasOriginals && <p className="tw-notice">Export builds native DAT/TEX files and coarse collision additions for original props. Requires pristine Collision.res. Use a separate test client: loading, shading and collision response are not yet verified in-game.</p>}
            <button onClick={() => download(new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" }), "twinkle-layout.json")}>Download layout JSON</button>
            <button onClick={() => input.current?.click()}>Import layout JSON</button>
            <button onClick={() => { commit(manifest.document); setSelected(""); setStatus("Starting layout restored. Undo is available; save to keep it."); }}>Restore starting layout</button>
            <details><summary>Load the ZIP in a client</summary><p>Close the game and back up a separate pristine test copy. Extract the ZIP elsewhere, then copy its entire Res folder into that test copy. Keep all supplied Festival and texture archives. Start your existing JFTSE setup and select Twinkle Town. Restore the backup to undo.</p><p>This replaces map 2, not a new game map. Never overwrite the pristine or working client. Native compatibility is untested.</p></details>
            <input hidden ref={input} type="file" accept=".json" onChange={async (e) => {
              const file = e.target.files?.[0]; if (!file) return;
              try {
                if (file.size > 256_000) throw new Error("Layout JSON must be smaller than 256 KB.");
                const next = parseTwinkleDocument(JSON.parse(await file.text()));
                if (next.sourceHash !== manifest.document.sourceHash || parseMapDesign(next.mapId) !== mapId) throw new Error("This layout belongs to a different map design. Open that design from All maps.");
                commit(next); setSelected(""); setStatus("Layout imported. Save to keep it in Studio.");
              } catch (error) { setError(String(error)); }
              e.target.value = "";
            }} />
          </div>
        </aside>
        <section className="tw-center" aria-label="Map design workspace">
          <div className="tw-toolbar" role="toolbar" aria-label="Viewport controls">
            <div><button aria-pressed={mode === "translate"} onClick={() => setMode("translate")}>Move <kbd>W</kbd></button><button aria-pressed={mode === "rotate"} onClick={() => setMode("rotate")}>Rotate <kbd>E</kbd></button></div>
            <label>Snap <select aria-label="Transform snap" value={snap} onChange={(e) => setSnap(Number(e.target.value))}><option value={0}>Off</option><option value={1}>1 unit</option><option value={5}>5 units</option></select></label>
            <div className="tw-camera-controls">{(["court", "overview", "top", "player"] as const).map((view) => <button key={view} aria-pressed={camera.view === view} onClick={() => frame(view)}>{view === "player" ? "Match study" : view[0].toUpperCase() + view.slice(1)}</button>)}</div>
          </div>
          <TwinkleViewport assets={manifest.assets} document={doc} selected={selected} mode={mode} snap={snap} guides={guides}
            lightmaps={lightmaps} isolate={isolate} camera={camera} onSelect={setSelected} onTransform={transform} onThumbnails={setThumbnails} />
          <div className="tw-viewport-options"><label><input type="checkbox" checked={guides} onChange={(e) => setGuides(e.target.checked)} /> Court & collision guides</label>
            <label><input type="checkbox" checked={lightmaps} onChange={(e) => setLightmaps(e.target.checked)} /> Baked lightmaps</label>
            <label><input type="checkbox" checked={isolate} onChange={(e) => { setIsolate(e.target.checked); if (e.target.checked) frame("selection"); }} /> Isolate selection</label><span>Match camera is approximate</span></div>
          <section className="tw-library" aria-label="Prop library"><div className="tw-section-title">Prop library <span>Actual geometry · animation paused</span></div>
            {category === "original" && <div className="tw-original-actions"><span>10 original models · DAT/TEX + collision export · native test required</span>{mapId === "oktoberfest" && <button onClick={() => {
              const replacements: Record<string, string> = {
                "Res/StageObj/FestivalHall/BlackSmith_Shop.dat": "BrewersPavilion",
                "Res/StageObj/FestivalPretzel/Carriage00.dat": "PretzelStand",
                "Res/StageObj/FestivalHeart/Carriage00.dat": "GingerbreadStand",
                "Res/StageObj/FestivalFood/Carriage00.dat": "FoodStand",
              };
              commit({ ...doc, objects: doc.objects.map((obj) => replacements[obj.file] ? {
                ...obj, file: `Studio/Oktoberfest/Oktoberfest_${replacements[obj.file]}.glb`, animation: -1, phase: 0,
              } : obj) });
              setSelected(""); setIsolate(false); frame("court");
              setStatus("Four festival anchors now use original geometry. Undo restores them; save explicitly to keep this design. Export includes native meshes, textures and collision proxies.");
            }}>Use original festival props</button>}</div>}
            <div className="tw-library-filters"><input aria-label="Search prop library" placeholder="Find a prop or character…" value={libraryQuery} onChange={(e) => setLibraryQuery(e.target.value)} /><select aria-label="Prop category" value={category} onChange={(e) => setCategory(e.target.value)}><option value="all">All assets</option><option value="original">New Oktoberfest models</option><option value="scenery">Scenery</option><option value="stock">Stock characters & props</option><option value="festival">Oktoberfest · stock-based</option></select>
              <a href="/api/twinkle/file?name=oktoberfest-original-models.zip" download>Download GLB / OBJ pack</a></div>
            <div className="tw-assets">{manifest.assets.filter((asset) => !asset.fixed && (category === "all" || category === asset.category) && assetLabel(asset.file).toLowerCase().includes(libraryQuery.toLowerCase())).map((asset) => <button key={asset.file} aria-label={`Add ${assetLabel(asset.file)}`} onClick={() => {
              const obj: Placement = { id: crypto.randomUUID(), name: assetLabel(asset.file), file: asset.file,
                position: [90, 0, 20], rotation: 0, scale: 1, level: 1, visible: true,
                animation: asset.pose === "bind" ? 0 : -1, phase: 0 };
              commit({ ...doc, objects: [...doc.objects, obj] }); setSelected(obj.id); setStatus(`${obj.name} added beside the court. Drag its gizmo or edit the inspector.`);
            }}><div className="tw-asset-image">{thumbnails[asset.file] ? <img src={thumbnails[asset.file]} alt="" /> : <span>Loading…</span>}</div><span>{assetLabel(asset.file)}</span></button>)}</div>
          </section>
        </section>
        <aside className="tw-inspector" aria-label="Object inspector"><div className="tw-section-title">Inspector <span>{chosen ? "Placement" : "Scene"}</span></div>
          {chosen ? <div className="tw-inspector-body" key={chosen.id}>
            <label>Object name<input aria-label="Object name" defaultValue={chosen.name} onBlur={(e) => transform(chosen.id, { name: e.target.value })} /></label>
            <p className="tw-asset-source">{assetLabel(chosen.file)}<small>{chosen.file}</small></p>
            {chosenAsset?.category === "original" && <p className="tw-notice">Original geometry and texture atlas. Export converts this placement to DAT/TEX and adds coarse solid collision proxies. Doorways remain open; fine detail is nonblocking. Native compatibility needs a client test. GLB / OBJ remains available for mesh editing.</p>}
            {!supported.has(chosen.file) && <p className="tw-notice">Resource missing or unsupported. Only a guide is shown, not a partial mesh. Placement edits still export.</p>}
            {chosenAsset?.pose === "bind" && <p className="tw-notice">Complete rest pose, not an animation frame. Move, rotate and scale this placement; animation metadata is preserved for export. Native pose and shading still need a client check.</p>}
            <h2>Transform</h2><div className="tw-coordinates">{([0, 1, 2] as const).map((axis) => <NumberField key={axis} label={`Position ${["X", "Y", "Z"][axis]}`} value={chosen.position[axis]} onCommit={(n) => {
              const position: [number, number, number] = [...chosen.position]; position[axis] = n; transform(chosen.id, { position });
            }} />)}</div>
            <NumberField label="Rotation Y" value={chosen.rotation} min={-36000} max={36000} step={15} onCommit={(rotation) => transform(chosen.id, { rotation })} />
            <NumberField label="Uniform scale" value={chosen.scale} min={0.01} max={100} step={0.1} onCommit={(scale) => transform(chosen.id, { scale })} />
            <label className="tw-check"><input type="checkbox" checked={chosen.visible} onChange={(e) => transform(chosen.id, { visible: e.target.checked })} /> Include in scene & export</label>
            <label>Client detail level<select aria-label="Client detail level" value={chosen.level} onChange={(e) => transform(chosen.id, { level: Number(e.target.value) })}><option value={0}>Level 0 · default</option><option value={1}>Level 1</option><option value={2}>Level 2</option></select></label>
            {courtClearance(chosen) && <p className="tw-notice" role="status">Inside the court clearance guide. Check play space before export. This is not a collision test.</p>}
            <div className="tw-inspector-buttons"><button onClick={() => frame("selection")}>Frame object <kbd>F</kbd></button><button onClick={duplicate}>Duplicate</button><button className="tw-danger" onClick={remove}>Delete object</button></div>
          </div> : <div className="tw-inspector-body"><h2>{selected.startsWith("fixed-") ? "Stock environment" : "Design in the scene"}</h2><p>Select a placed object to move, rotate or scale it. Add barrels, seating and flowers from the library.</p>
            <div className="tw-facts"><span>Static geometry<strong>{manifest.assets.filter((asset) => asset.fixed).reduce((total, asset) => total + asset.submeshes, 0)} submeshes</strong></span><span>Source map<strong>Twinkle Town · 02</strong></span><span>Layout format<strong>Editable SET placements</strong></span></div>
            <p className="tw-notice">Court, town topology and cameras stay stock. Original props add coarse collision proxies on export. NPCs and carts render in rest pose; animation and effects are not simulated. Both designs replace Twinkle Town.</p>
            <button onClick={() => frame("court")}>Frame the court</button>
          </div>}
          {manifest.warnings.length > 0 && <details className="tw-warnings"><summary>{manifest.warnings.length} asset warnings</summary>{manifest.warnings.map((w) => <p key={w}>{w}</p>)}</details>}
        </aside>
      </div>
      <footer className="tw-footer"><span role="status">{status}</span><span>{doc.objects.filter((o) => o.visible).length} active placements · {changed ? "● Modified" : "✓ Saved"}</span></footer>
    </>}
  </main>;
}
