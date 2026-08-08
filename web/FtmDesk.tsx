import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

type SceneObject = {
  readonly prefabIndex: number;
  readonly x: number;
  readonly y: number;
  readonly scaleHeight: number;
  readonly scaleWidth: number;
  readonly rotationY: number;
  readonly rotationX: number;
  readonly prefabName?: string | null;
  readonly prefabObjId?: string | null;
};

type FtmPayload = {
  readonly mapPath?: string;
  readonly tileCountX: number;
  readonly tileCountY: number;
  readonly indoorMode?: number;
  readonly prefabs?: Array<{ name: string; objId: string }>;
  readonly sceneObjects?: SceneObject[];
  readonly sceneObjectCount?: number;
  readonly prefabCount?: number;
  readonly interactableTileCount?: number;
  readonly blockedTileCount?: number;
  readonly tileLayerDefinitions?: Array<{ name: string; visible?: number }>;
  readonly tileLayers?: Array<{
    layerName?: string;
    tileCountX?: number;
    tileCountY?: number;
  }>;
  readonly blockedTiles?: Array<{ x: number; y: number }>;
};

async function apiJson<T>(path: string): Promise<{ status: number; body: T }> {
  const response = await fetch(path);
  const body = (await response.json()) as T;
  return { status: response.status, body };
}

/**
 * Interactive FTM overworld desk (FT-ResTool FTMEditor-inspired, read-first).
 * 2D tile grid + placement markers; select rows to inspect transforms.
 */
export function FtmDesk() {
  const [archive, setArchive] = useState("Res/MapSet/FantaCastle.res");
  const [member, setMember] = useState("FantaCastleOutSide.ftm");
  const [status, setStatus] = useState("Load an FTM/PRJ member to inspect placements");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [ftm, setFtm] = useState<FtmPayload | null>(null);
  const [kind, setKind] = useState<string>("");
  const [selected, setSelected] = useState<number | null>(null);
  const [draftX, setDraftX] = useState("");
  const [draftY, setDraftY] = useState("");
  const [draftScaleH, setDraftScaleH] = useState("");
  const [draftScaleW, setDraftScaleW] = useState("");
  const [draftRotY, setDraftRotY] = useState("");
  const [draftRotX, setDraftRotX] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [copyHint, setCopyHint] = useState("");
  const [paintBlocked, setPaintBlocked] = useState(false);
  const [paintTile, setPaintTile] = useState(false);
  const [tilePaintValue, setTilePaintValue] = useState("1");
  const [tileLayerIndex, setTileLayerIndex] = useState(0);
  const [tilePaintCells, setTilePaintCells] = useState<
    Array<{ x: number; y: number; value: number }>
  >([]);
  const [blockedDraft, setBlockedDraft] = useState<Array<{ x: number; y: number }>>(
    [],
  );
  const [draftPrefab, setDraftPrefab] = useState("0");
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const exportPanelRef = useRef<HTMLDivElement | null>(null);

  const objects = ftm?.sceneObjects ?? [];
  const selectedObj = selected != null ? objects[selected] ?? null : null;

  useEffect(() => {
    if (!selectedObj) {
      setDraftX("");
      setDraftY("");
      setDraftScaleH("");
      setDraftScaleW("");
      setDraftRotY("");
      setDraftRotX("");
      return;
    }
    setDraftX(String(selectedObj.x));
    setDraftY(String(selectedObj.y));
    setDraftScaleH(String(selectedObj.scaleHeight));
    setDraftScaleW(String(selectedObj.scaleWidth));
    setDraftRotY(String(selectedObj.rotationY));
    setDraftRotX(String(selectedObj.rotationX));
    setDraftPrefab(String(selectedObj.prefabIndex));
    // Bring export panel into view after select (select → edit → export path)
    window.requestAnimationFrame(() => {
      exportPanelRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    });
  }, [selectedObj]);

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    setSelected(null);
    setExportPath("");
    setCopyHint("");
    setStatus("Parsing FTM…");
    try {
      const qs = new URLSearchParams();
      if (archive.trim()) qs.set("archive", archive.trim());
      qs.set("member", member.trim());
      const { status: http, body } = await apiJson<{
        ok?: boolean;
        kind?: string;
        ftm?: FtmPayload;
        prj?: { ftmCount: number; ftmPaths: string[] };
        error?: string;
        detail?: string;
      }>(`/api/ftm/parse?${qs.toString()}`);

      if (!body.ok) {
        const msg = body.detail ?? body.error ?? `HTTP ${http}`;
        setFtm(null);
        setKind("");
        setError(msg);
        setStatus("FTM parse failed");
        return;
      }
      if (body.kind === "prj" && body.prj) {
        setFtm(null);
        setKind("prj");
        setStatus(
          `PRJ · ${body.prj.ftmCount} FTM paths — pick a .ftm member to open the placement desk`,
        );
        setError("");
        if (body.prj.ftmPaths[0]) {
          const path = body.prj.ftmPaths[0].replace(/\\/g, "/");
          const base = path.split("/").pop() ?? path;
          setMember(base.endsWith(".ftm") ? base : `${base}.ftm`);
        }
        return;
      }
      if (!body.ftm) {
        setError("Unexpected FTM payload");
        setFtm(null);
        return;
      }
      setKind("ftm");
      setFtm(body.ftm);
      setBlockedDraft(body.ftm.blockedTiles ?? []);
      setTilePaintCells([]);
      const count = body.ftm.sceneObjectCount ?? body.ftm.sceneObjects?.length ?? 0;
      // Auto-select first placement so export path is one edit away
      if ((body.ftm.sceneObjects?.length ?? 0) > 0) {
        setSelected(0);
      }
      setStatus(
        `${member} · ${body.ftm.tileCountX}×${body.ftm.tileCountY} · ${count} placements · ${body.ftm.blockedTileCount ?? 0} blocked · ${body.ftm.interactableTileCount ?? 0} interactables` +
          (count > 0 ? " · placement #0 selected — edit & export below" : ""),
      );
    } catch (err) {
      setFtm(null);
      setError(err instanceof Error ? err.message : String(err));
      setStatus("FTM request failed");    } finally {
      setBusy(false);
    }
  }, [archive, member, objects.length]);

  // 2D canvas: grid + blocked sample + placements
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !ftm) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#0d1426";
    ctx.fillRect(0, 0, w, h);

    const cols = Math.max(ftm.tileCountX, 1);
    const rows = Math.max(ftm.tileCountY, 1);
    const pad = 12;
    const cell = Math.min((w - pad * 2) / cols, (h - pad * 2) / rows);
    const ox = pad + (w - pad * 2 - cell * cols) / 2;
    const oy = pad + (h - pad * 2 - cell * rows) / 2;

    // grid
    ctx.strokeStyle = "rgba(42, 54, 84, 0.9)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= cols; x++) {
      const px = ox + x * cell;
      ctx.beginPath();
      ctx.moveTo(px, oy);
      ctx.lineTo(px, oy + rows * cell);
      ctx.stroke();
    }
    for (let y = 0; y <= rows; y++) {
      const py = oy + y * cell;
      ctx.beginPath();
      ctx.moveTo(ox, py);
      ctx.lineTo(ox + cols * cell, py);
      ctx.stroke();
    }

    // blocked tiles (draft for paint mode; sample first 2000)
    const blocked = blockedDraft.length ? blockedDraft : (ftm.blockedTiles ?? []);
    ctx.fillStyle = "rgba(255, 107, 122, 0.28)";
    for (const tile of blocked.slice(0, 2000)) {
      ctx.fillRect(ox + tile.x * cell, oy + tile.y * cell, cell, cell);
    }

    // placements
    objects.forEach((obj, i) => {
      const cx = ox + (obj.x + 0.5) * cell;
      const cy = oy + (obj.y + 0.5) * cell;
      const active = i === selected;
      ctx.fillStyle = active ? "#5fd0ff" : "#3ddc97";
      ctx.strokeStyle = active ? "#e8eef9" : "rgba(232, 238, 249, 0.4)";
      ctx.lineWidth = active ? 2 : 1;
      const r = Math.max(cell * 0.35, 3);
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      if (active || objects.length < 24) {
        ctx.fillStyle = "#e8eef9";
        ctx.font = "10px ui-sans-serif, system-ui";
        ctx.fillText(obj.prefabName ?? `#${obj.prefabIndex}`, cx + r + 2, cy + 3);
      }
    });

    ctx.fillStyle = "#93a0bf";
    ctx.font = "11px ui-sans-serif, system-ui";
    ctx.fillText(
      `${cols}×${rows} tiles · green = placement · red tint = blocked (sample)`,
      pad,
      h - 6,
    );
  }, [ftm, objects, selected, blockedDraft]);

  const onCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!ftm || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = canvasRef.current.width / rect.width;
    const scaleY = canvasRef.current.height / rect.height;
    const mx = (event.clientX - rect.left) * scaleX;
    const my = (event.clientY - rect.top) * scaleY;
    const cols = Math.max(ftm.tileCountX, 1);
    const rows = Math.max(ftm.tileCountY, 1);
    const pad = 12;
    const w = canvasRef.current.width;
    const h = canvasRef.current.height;
    const cell = Math.min((w - pad * 2) / cols, (h - pad * 2) / rows);
    const ox = pad + (w - pad * 2 - cell * cols) / 2;
    const oy = pad + (h - pad * 2 - cell * rows) / 2;

    const tx = Math.floor((mx - ox) / cell);
    const ty = Math.floor((my - oy) / cell);

    if (paintBlocked) {
      if (tx < 0 || ty < 0 || tx >= cols || ty >= rows) return;
      setBlockedDraft((prev) => {
        const exists = prev.some((t) => t.x === tx && t.y === ty);
        if (exists) return prev.filter((t) => !(t.x === tx && t.y === ty));
        return [...prev, { x: tx, y: ty }];
      });
      setStatus(`Blocked paint · tile (${tx},${ty}) · count will update on export`);
      return;
    }

    if (paintTile) {
      if (tx < 0 || ty < 0 || tx >= cols || ty >= rows) return;
      const value = Number(tilePaintValue);
      if (!Number.isFinite(value)) {
        setError("tile paint value must be a number");
        return;
      }
      setTilePaintCells((prev) => {
        const rest = prev.filter((c) => !(c.x === tx && c.y === ty));
        return [...rest, { x: tx, y: ty, value: Math.trunc(value) }];
      });
      setStatus(`Tile layer #${tileLayerIndex} paint · (${tx},${ty})=${Math.trunc(value)}`);
      return;
    }

    // Drag placement mode: if clicking near selected placement, start drag
    let best = -1;
    let bestDist = Infinity;
    objects.forEach((obj, i) => {
      const cx = ox + (obj.x + 0.5) * cell;
      const cy = oy + (obj.y + 0.5) * cell;
      const d = (cx - mx) ** 2 + (cy - my) ** 2;
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    });
    if (best >= 0 && bestDist < (Math.max(cell, 8) * 2) ** 2) {
      setSelected(best);
      setDragIndex(best);
    }
  };

  const onCanvasMouseUp = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (dragIndex == null || !ftm || !canvasRef.current || paintBlocked || paintTile) {
      setDragIndex(null);
      return;
    }
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = canvasRef.current.width / rect.width;
    const scaleY = canvasRef.current.height / rect.height;
    const mx = (event.clientX - rect.left) * scaleX;
    const my = (event.clientY - rect.top) * scaleY;
    const cols = Math.max(ftm.tileCountX, 1);
    const rows = Math.max(ftm.tileCountY, 1);
    const pad = 12;
    const w = canvasRef.current.width;
    const h = canvasRef.current.height;
    const cell = Math.min((w - pad * 2) / cols, (h - pad * 2) / rows);
    const ox = pad + (w - pad * 2 - cell * cols) / 2;
    const oy = pad + (h - pad * 2 - cell * rows) / 2;
    const tx = Math.max(0, Math.min(cols - 1, Math.floor((mx - ox) / cell)));
    const ty = Math.max(0, Math.min(rows - 1, Math.floor((my - oy) / cell)));
    setDraftX(String(tx));
    setDraftY(String(ty));
    setStatus(`Dragged placement #${dragIndex} → (${tx},${ty}) — export to apply`);
    setDragIndex(null);
  };

  const exportBlockedPaint = async () => {
    if (!ftm) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/ftm/author", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          archive: archive.trim(),
          member: member.trim(),
          blockedTiles: blockedDraft,
          tilePaint:
            tilePaintCells.length > 0
              ? { layerIndex: tileLayerIndex, cells: tilePaintCells }
              : undefined,
        }),
      });
      const body = (await response.json()) as {
        ok?: boolean;
        path?: string;
        archive?: string;
        blockedTileCount?: number;
        error?: string;
        detail?: string;
      };
      if (!response.ok || !body.ok) {
        throw new Error(body.detail ?? body.error ?? `HTTP ${response.status}`);
      }
      setExportPath(body.path ?? body.archive ?? "");
      setStatus(
        `Exported map paint · blocked ${body.blockedTileCount ?? blockedDraft.length}` +
          (tilePaintCells.length ? ` · tile cells ${tilePaintCells.length}` : "") +
          ` → ${body.path}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Map paint export failed");
    } finally {
      setBusy(false);
    }
  };

  const layers = useMemo(
    () => ftm?.tileLayerDefinitions?.map((l) => l.name).join(", ") ?? "—",
    [ftm],
  );

  const exportPatched = async () => {
    if (!ftm || selected == null || !selectedObj) {
      setError("Select a placement to export a patch");
      return;
    }
    setBusy(true);
    setError("");
    setExportPath("");
    setCopyHint("");
    try {
      const x = Number(draftX);
      const y = Number(draftY);
      const scaleHeight = Number(draftScaleH);
      const scaleWidth = Number(draftScaleW);
      const rotationY = Number(draftRotY);
      const rotationX = Number(draftRotX);
      if (![x, y, scaleHeight, scaleWidth, rotationY, rotationX].every(Number.isFinite)) {
        throw new Error("placement fields must be finite numbers");
      }
      const response = await fetch("/api/ftm/author", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          archive: archive.trim(),
          member: member.trim(),
          patches: [
            {
              index: selected,
              prefabIndex: Math.trunc(Number(draftPrefab)) || selectedObj.prefabIndex,
              x: Math.trunc(x),
              y: Math.trunc(y),
              scaleHeight,
              scaleWidth,
              rotationY,
              rotationX,
            },
          ],
        }),
      });
      const body = (await response.json()) as {
        ok?: boolean;
        path?: string;
        archive?: string;
        error?: string;
        detail?: string;
        sceneObjectCount?: number;
      };
      if (!response.ok || !body.ok) {
        throw new Error(body.detail ?? body.error ?? `HTTP ${response.status}`);
      }
      setExportPath(body.path ?? body.archive ?? "");
      setStatus(
        `Exported authored FTM · placement #${selected} → ${body.path} (+ MapSet RES)`,
      );
      const prefabIndex = Math.trunc(Number(draftPrefab)) || selectedObj.prefabIndex;
      setFtm({
        ...ftm,
        sceneObjects: objects.map((obj, i) =>
          i === selected
            ? {
                ...obj,
                prefabIndex,
                x: Math.trunc(x),
                y: Math.trunc(y),
                scaleHeight,
                scaleWidth,
                rotationY,
                rotationX,
              }
            : obj,
        ),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("FTM export failed");
    } finally {
      setBusy(false);
    }
  };

  const addPlacement = async () => {
    if (!ftm) {
      setError("Parse an FTM first");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const prefabIndex =
        Number(draftPrefab) >= 0
          ? Math.trunc(Number(draftPrefab))
          : (selectedObj?.prefabIndex ?? 0);
      const response = await fetch("/api/ftm/author", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          archive: archive.trim(),
          member: member.trim(),
          add: [
            {
              prefabIndex,
              x: Number(draftX) || 0,
              y: Number(draftY) || 0,
              scaleHeight: Number(draftScaleH) || 1,
              scaleWidth: Number(draftScaleW) || 1,
              rotationY: Number(draftRotY) || 0,
              rotationX: Number(draftRotX) || 0,
            },
          ],
        }),
      });
      const body = (await response.json()) as {
        ok?: boolean;
        path?: string;
        archive?: string;
        sceneObjectCount?: number;
        error?: string;
        detail?: string;
      };
      if (!response.ok || !body.ok) {
        throw new Error(body.detail ?? body.error ?? `HTTP ${response.status}`);
      }
      setExportPath(body.path ?? body.archive ?? "");
      setStatus(`Added placement · count ${body.sceneObjectCount} → ${body.path}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("FTM add failed");
    } finally {
      setBusy(false);
    }
  };

  const removePlacement = async () => {
    if (!ftm || selected == null) {
      setError("Select a placement to remove");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/ftm/author", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          archive: archive.trim(),
          member: member.trim(),
          remove: [selected],
        }),
      });
      const body = (await response.json()) as {
        ok?: boolean;
        path?: string;
        archive?: string;
        sceneObjectCount?: number;
        error?: string;
        detail?: string;
      };
      if (!response.ok || !body.ok) {
        throw new Error(body.detail ?? body.error ?? `HTTP ${response.status}`);
      }
      setExportPath(body.path ?? body.archive ?? "");
      setStatus(`Removed #${selected} · count ${body.sceneObjectCount}`);
      setSelected(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("FTM remove failed");
    } finally {
      setBusy(false);
    }
  };

  const installAuthored = async () => {
    if (!exportPath) {
      setError("Export an FTM first");
      return;
    }
    // Prefer MapSet .res sibling if export path is .ftm
    const archiveSource = exportPath.endsWith(".ftm")
      ? exportPath.replace(/[^/]+$/, archive.split("/").pop() || "Map.res")
      : exportPath;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/client/install", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          files: [
            {
              source: archiveSource,
              destRelative: archive.trim().replace(/\\/g, "/"),
            },
          ],
        }),
      });
      const body = (await response.json()) as {
        ok?: boolean;
        error?: string;
        installed?: Record<string, string>;
      };
      if (!response.ok || !body.ok) {
        throw new Error(body.error ?? `HTTP ${response.status}`);
      }
      setStatus(`Installed to local client · ${Object.keys(body.installed ?? {}).join(", ")}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("FTM install failed");
    } finally {
      setBusy(false);
    }
  };

  const copyExportPath = async () => {
    if (!exportPath) return;
    try {
      await navigator.clipboard.writeText(exportPath);
      setCopyHint("Copied path");
    } catch {
      setCopyHint("Copy failed — select path manually");
    }
  };

  return (
    <div className="ftm-desk">
      <div className="field-grid">
        <label>
          Archive
          <input
            value={archive}
            onChange={(e) => setArchive(e.target.value)}
            spellCheck={false}
            aria-label="FTM archive path"
          />
        </label>
        <label>
          Member (.ftm / .prj)
          <input
            value={member}
            onChange={(e) => setMember(e.target.value)}
            spellCheck={false}
            aria-label="FTM member name"
          />
        </label>
      </div>
      <div className="actions">
        <button className="btn primary" type="button" disabled={busy} onClick={() => void load()}>
          {busy ? "Parsing…" : "Parse FTM"}
        </button>
        <button
          className="btn"
          type="button"
          disabled={busy || !ftm}
          data-active={paintBlocked}
          onClick={() => {
            setPaintBlocked((v) => !v);
            setPaintTile(false);
          }}
        >
          {paintBlocked ? "Paint blocked: ON" : "Paint blocked tiles"}
        </button>
        <button
          className="btn"
          type="button"
          disabled={busy || !ftm}
          data-active={paintTile}
          onClick={() => {
            setPaintTile((v) => !v);
            setPaintBlocked(false);
          }}
        >
          {paintTile ? "Paint tile layer: ON" : "Paint tile layer"}
        </button>
        <button
          className="btn primary"
          type="button"
          disabled={busy || !ftm}
          onClick={() => void exportBlockedPaint()}
        >
          Export map paint
        </button>
      </div>
      {ftm && paintTile && (
        <div className="field-grid">
          <label>
            Layer index
            <input
              type="number"
              min={0}
              value={tileLayerIndex}
              onChange={(e) => setTileLayerIndex(Number(e.target.value) || 0)}
            />
          </label>
          <label>
            Tile value
            <input
              value={tilePaintValue}
              onChange={(e) => setTilePaintValue(e.target.value)}
              inputMode="numeric"
            />
          </label>
          <div className="empty mono">
            layers: {(ftm.tileLayerDefinitions ?? []).map((l) => l.name).join(", ") || "—"} ·
            painted cells {tilePaintCells.length}
          </div>
        </div>
      )}
      <div className="empty">{status}</div>
      {error && (
        <div className="mono" style={{ color: "var(--danger)" }} role="alert">
          {error}
        </div>
      )}
      {kind === "ftm" && ftm && (
        <>
          <div className="mono empty">
            mapPath={ftm.mapPath ?? "—"} · layers={layers} · indoor=
            {ftm.indoorMode ?? 0}
          </div>
          <canvas
            ref={canvasRef}
            className="ftm-canvas"
            width={640}
            height={360}
            aria-label="FTM placement map"
            onClick={onCanvasClick}
            onMouseUp={onCanvasMouseUp}
            onMouseLeave={() => setDragIndex(null)}
          />
          <div className="list ftm-object-list" role="listbox" aria-label="Scene placements">
            {objects.length === 0 && <p className="empty">No scene objects in this FTM.</p>}
            {objects.map((obj, i) => (
              <button
                key={`${obj.prefabIndex}-${obj.x}-${obj.y}-${i}`}
                type="button"
                data-active={selected === i}
                onClick={() => setSelected(i)}
              >
                {obj.prefabName ?? `prefab#${obj.prefabIndex}`} @ ({obj.x}, {obj.y})
                <small>
                  scale H{obj.scaleHeight.toFixed(2)} W{obj.scaleWidth.toFixed(2)} · rot Y
                  {obj.rotationY.toFixed(2)} X{obj.rotationX.toFixed(2)}
                </small>
              </button>
            ))}
          </div>
          {selectedObj && (
            <div className="ftm-export-panel" ref={exportPanelRef}>
              <strong>Export path · placement #{selected}</strong>
              <div className="mono empty">
                prefabIndex={selectedObj.prefabIndex}
                {selectedObj.prefabName ? ` · ${selectedObj.prefabName}` : ""}
                {selectedObj.prefabObjId ? ` · objId=${selectedObj.prefabObjId}` : ""}
              </div>
              <div className="field-grid">
                <label>
                  Prefab
                  <select
                    value={draftPrefab}
                    onChange={(e) => setDraftPrefab(e.target.value)}
                    aria-label="Prefab index"
                  >
                    {(ftm.prefabs ?? []).map((p, i) => (
                      <option key={`${p.name}-${i}`} value={String(i)}>
                        #{i} {p.name}
                      </option>
                    ))}
                    {!(ftm.prefabs?.length) && (
                      <option value={draftPrefab}>#{draftPrefab}</option>
                    )}
                  </select>
                </label>
                <label>
                  x (tile)
                  <input
                    value={draftX}
                    onChange={(e) => setDraftX(e.target.value)}
                    inputMode="numeric"
                    aria-label="Placement tile X"
                  />
                </label>
                <label>
                  y (tile)
                  <input
                    value={draftY}
                    onChange={(e) => setDraftY(e.target.value)}
                    inputMode="numeric"
                    aria-label="Placement tile Y"
                  />
                </label>
                <label>
                  scaleHeight
                  <input
                    value={draftScaleH}
                    onChange={(e) => setDraftScaleH(e.target.value)}
                    inputMode="decimal"
                    aria-label="Scale height"
                  />
                </label>
                <label>
                  scaleWidth
                  <input
                    value={draftScaleW}
                    onChange={(e) => setDraftScaleW(e.target.value)}
                    inputMode="decimal"
                    aria-label="Scale width"
                  />
                </label>
                <label>
                  rotationY
                  <input
                    value={draftRotY}
                    onChange={(e) => setDraftRotY(e.target.value)}
                    inputMode="decimal"
                    aria-label="Rotation Y"
                  />
                </label>
                <label>
                  rotationX
                  <input
                    value={draftRotX}
                    onChange={(e) => setDraftRotX(e.target.value)}
                    inputMode="decimal"
                    aria-label="Rotation X"
                  />
                </label>
              </div>
              <div className="actions">
                <button
                  className="btn primary"
                  type="button"
                  disabled={busy}
                  onClick={() => void exportPatched()}
                >
                  {busy ? "Exporting…" : "Export patched FTM + MapSet RES"}
                </button>
                <button
                  className="btn"
                  type="button"
                  disabled={busy}
                  onClick={() => void addPlacement()}
                >
                  Add placement
                </button>
                <button
                  className="btn"
                  type="button"
                  disabled={busy || selected == null}
                  onClick={() => void removePlacement()}
                >
                  Remove selected
                </button>
                <button
                  className="btn primary"
                  type="button"
                  disabled={busy || !exportPath}
                  onClick={() => void installAuthored()}
                >
                  Install to local client
                </button>
                {exportPath && (
                  <button className="btn" type="button" onClick={() => void copyExportPath()}>
                    Copy export path
                  </button>
                )}
              </div>
              {exportPath && (
                <div className="mono empty" role="status">
                  Wrote {exportPath}
                  {copyHint ? ` · ${copyHint}` : ""}
                </div>
              )}
              <p className="empty">
                Flow: Parse → edit/add/remove placements → export MapSet RES → install local only
                (stock refused).
              </p>
            </div>
          )}
          {!selectedObj && objects.length > 0 && (
            <p className="empty">Select a placement marker or list row to open the export panel.</p>
          )}
        </>
      )}
    </div>
  );
}
