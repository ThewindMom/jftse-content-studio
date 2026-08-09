import type { MapSceneDocument } from "./mapSceneDocument.ts";
import type { MapTransformMode } from "./mapSceneTransform.ts";

type MapCreatorViewportProps = {
  scene: MapSceneDocument;
  selectedId: string;
  mode: MapTransformMode;
  snap: number;
  onModeChange: (mode: MapTransformMode) => void;
  onSnapChange: (snap: number) => void;
  onSelect: (id: string) => void;
};

export function MapCreatorViewport({
  scene,
  selectedId,
  mode,
  snap,
  onModeChange,
  onSnapChange,
  onSelect,
}: MapCreatorViewportProps) {
  return (
    <div className="map-scene-column">
      <div className="gizmo-toolbar" role="toolbar" aria-label="Transform gizmo">
        {(["translate", "rotate", "scale"] as const).map((entry) => (
          <button
            aria-pressed={mode === entry}
            className="btn"
            key={entry}
            onClick={() => onModeChange(entry)}
            type="button"
          >
            {entry}
          </button>
        ))}
        <label>
          Snap
          <select
            aria-label="Map transform snap"
            value={snap}
            onChange={(event) => onSnapChange(Number(event.target.value))}
          >
            <option value={0}>off</option>
            <option value={0.25}>0.25</option>
            <option value={0.5}>0.5</option>
            <option value={1}>1</option>
          </select>
        </label>
      </div>
      <div className="map-scene-viewport" aria-label="Editable map viewport">
        <div className="court-plane" />
        {scene.layers.find(({ id }) => id === "objects")?.visible &&
          scene.objects.map((object) => (
            <button
              aria-label={`Select ${object.name}`}
              className="scene-object"
              data-selected={selectedId === object.id}
              key={object.id}
              onClick={() => onSelect(object.id)}
              style={{
                left: `${50 + object.position[0] * 4}%`,
                top: `${50 + object.position[2] * 4}%`,
                rotate: `${object.rotation[1]}deg`,
                scale: `${object.scale[0]}`,
              }}
              type="button"
            >
              {object.name.includes("net") ? "NET" : "TREE"}
            </button>
          ))}
        {scene.layers.find(({ id }) => id === "spawns")?.visible &&
          scene.spawns.map((spawn) => (
            <span
              className={`scene-spawn ${spawn.team}`}
              key={spawn.id}
              style={{
                left: `${50 + spawn.position[0] * 4}%`,
                top: `${50 + spawn.position[2] * 4}%`,
              }}
            >
              {spawn.team === "home" ? "H" : "A"}
            </span>
          ))}
        {scene.layers.find(({ id }) => id === "collision")?.visible &&
          scene.collision.blockedCells.map(([x, y]) => (
            <span
              className="collision-cell"
              key={`${x}-${y}`}
              style={{ left: `${x * 5}%`, top: `${y * 5}%` }}
            />
          ))}
      </div>
    </div>
  );
}
