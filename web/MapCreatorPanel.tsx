import { useEffect, useMemo, useState } from "react";
import { MapCreatorInspector } from "./MapCreatorInspector.tsx";
import { MapCreatorPackagePanel } from "./MapCreatorPackagePanel.tsx";
import { MapCreatorToolbox } from "./MapCreatorToolbox.tsx";
import { MapCreatorViewport } from "./MapCreatorViewport.tsx";
import {
  addMapObject,
  buildMapManifest,
  parseMapScene,
  serializeMapScene,
  transformMapObject,
  validateMapDependencies,
  type MapObject,
  type MapSceneDocument,
} from "./mapSceneDocument.ts";
import type { MapTransformMode } from "./mapSceneTransform.ts";
import { createStockMapScene } from "./projectEditors.ts";

const MAP_SCENE_STORAGE_KEY = "jftse-content-studio.map-scene";

export function mapSceneAcknowledgementKey(
  scene: MapSceneDocument,
): string {
  return serializeMapScene(scene);
}

function loadMapScene(): MapSceneDocument {
  try {
    const stored = localStorage.getItem(MAP_SCENE_STORAGE_KEY);
    return stored
      ? parseMapScene(stored)
      : createStockMapScene("Untitled Court");
  } catch {
    return createStockMapScene("Untitled Court");
  }
}

export type MapCreatorPanelProps = {
  value?: MapSceneDocument;
  onChange?: (scene: MapSceneDocument) => void;
};

export function MapCreatorPanel({ value, onChange }: MapCreatorPanelProps = {}) {
  const controlled = value !== undefined;
  const [standaloneScene, setStandaloneScene] = useState(() =>
    value ?? loadMapScene(),
  );
  const scene = value ?? standaloneScene;
  const acknowledgementKey = mapSceneAcknowledgementKey(scene);
  const [selectedId, setSelectedId] = useState("");
  const [mode, setMode] = useState<MapTransformMode>("translate");
  const [snap, setSnap] = useState(0.5);
  const [available, setAvailable] = useState<Set<string>>(new Set());
  const [manifest, setManifest] = useState("");
  const [packageStatus, setPackageStatus] = useState("");
  const missing = useMemo(
    () => validateMapDependencies(scene, available),
    [available, scene],
  );

  useEffect(() => {
    if (!controlled) {
      localStorage.setItem(MAP_SCENE_STORAGE_KEY, serializeMapScene(scene));
    }
    setManifest("");
    setPackageStatus("");
  }, [controlled, scene]);

  useEffect(() => {
    if (controlled) setAvailable(new Set());
  }, [acknowledgementKey, controlled]);

  const changeScene = (next: MapSceneDocument) => {
    if (!controlled) setStandaloneScene(next);
    onChange?.(next);
  };

  const createEmpty = (name: string) => {
    changeScene(createStockMapScene(name));
    setSelectedId("");
    setAvailable(new Set());
    setManifest("");
  };

  const addObject = (assetId: string, name: string) => {
    const next = addMapObject(scene, {
      assetId,
      name,
      layer: "objects",
      position: [0, 0, 0],
      rotation: [0, 0, 0],
      scale: [1, 1, 1],
    });
    changeScene(next);
    setSelectedId(next.objects.at(-1)?.id ?? "");
  };

  const transform = (object: MapObject, patch: Partial<MapObject>) => {
    changeScene(
      transformMapObject(scene, object.id, {
        position: patch.position ?? object.position,
        rotation: patch.rotation ?? object.rotation,
        scale: patch.scale ?? object.scale,
        snap,
      }),
    );
  };

  const exportPackage = async () => {
    setPackageStatus("Building SQL, stock-template stage, FTM and collision…");
    try {
      const response = await fetch("/api/map-scene/package", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ scene, availableDependencies: [...available] }),
      });
      const receipt = (await response.json()) as Record<string, unknown>;
      if (!response.ok || receipt.ok !== true) {
        setPackageStatus(String(receipt.error ?? "Map package failed."));
        return;
      }
      setManifest(
        JSON.stringify(
          { receipt, manifest: buildMapManifest(scene, available) },
          null,
          2,
        ),
      );
      setPackageStatus(
        `Verified runtime pack · ${String(
          (receipt.contentPack as { installPlan?: unknown[] } | undefined)
            ?.installPlan?.length ?? 0,
        )} install files · SHA-256 ${String(receipt.hash).slice(0, 12)}…`,
      );
    } catch (error) {
      setPackageStatus(
        error instanceof Error ? error.message : "Map package failed.",
      );
    }
  };

  return (
    <section className="map-creator" aria-label="Visual Map Creator">
      <header className="creator-heading">
        <div>
          <p className="eyebrow">Empty project → playable court</p>
          <h3>Visual Map Creator</h3>
          <p className="muted">
            Place scenery, spawns and collision in a canonical scene document;
            build writes SQL plus bounded stock-template SET/FTM artifacts while
            preserving unsupported Blender, spawn and material data explicitly.
          </p>
        </div>
        <button
          className="btn"
          onClick={() => createEmpty("Untitled Court")}
          type="button"
        >
          New empty map
        </button>
      </header>

      <div className="map-creator-shell">
        <MapCreatorToolbox
          scene={scene}
          onSceneChange={changeScene}
          onAddObject={addObject}
        />
        <MapCreatorViewport
          scene={scene}
          selectedId={selectedId}
          mode={mode}
          snap={snap}
          onModeChange={setMode}
          onSnapChange={setSnap}
          onSelect={setSelectedId}
        />
        <MapCreatorInspector
          scene={scene}
          selectedId={selectedId}
          mode={mode}
          snap={snap}
          onSelect={setSelectedId}
          onSceneChange={changeScene}
          onTransform={transform}
        />
      </div>

      <MapCreatorPackagePanel
        missing={missing}
        spawnCount={scene.spawns.length}
        packageStatus={packageStatus}
        manifest={manifest}
        onResolve={() =>
          setAvailable(
            new Set(validateMapDependencies(scene, new Set<string>())),
          )
        }
        onExport={() => void exportPackage()}
      />
    </section>
  );
}
