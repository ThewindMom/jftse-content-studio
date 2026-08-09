import {
  addMapSpawn,
  paintCollisionCell,
  setMapLayerVisibility,
  type MapSceneDocument,
} from "./mapSceneDocument.ts";

type MapCreatorToolboxProps = {
  scene: MapSceneDocument;
  onSceneChange: (scene: MapSceneDocument) => void;
  onAddObject: (assetId: string, name: string) => void;
};

export function MapCreatorToolbox({
  scene,
  onSceneChange,
  onAddObject,
}: MapCreatorToolboxProps) {
  return (
    <aside className="map-toolbox" aria-label="Map assets and layers">
      <label>
        Map name
        <input
          aria-label="New map name"
          value={scene.name}
          onChange={(event) =>
            onSceneChange({ ...scene, name: event.target.value })
          }
        />
      </label>
      <strong>Asset palette</strong>
      <button
        className="btn"
        onClick={() => onAddObject("court/net.glb", "Center net")}
        type="button"
      >
        + Center net
      </button>
      <button
        className="btn"
        onClick={() => onAddObject("court/tree.glb", "Scenery tree")}
        type="button"
      >
        + Scenery tree
      </button>
      <button
        className="btn"
        onClick={() =>
          onSceneChange(
            addMapSpawn(scene, {
              team: scene.spawns.some(({ team }) => team === "home")
                ? "away"
                : "home",
              position: scene.spawns.length === 0 ? [-4, 0, 0] : [4, 0, 0],
              facing: scene.spawns.length === 0 ? 90 : -90,
            }),
          )
        }
        type="button"
      >
        + Player spawn
      </button>
      <button
        className="btn"
        onClick={() =>
          onSceneChange(
            paintCollisionCell(
              scene,
              [2 + scene.collision.blockedCells.length, 2],
              true,
            ),
          )
        }
        type="button"
      >
        Paint collision
      </button>
      <strong>Layers</strong>
      {scene.layers.map((layer) => (
        <label className="inline-label" key={layer.id}>
          <input
            checked={layer.visible}
            onChange={(event) =>
              onSceneChange(
                setMapLayerVisibility(scene, layer.id, event.target.checked),
              )
            }
            type="checkbox"
          />
          {layer.name}
        </label>
      ))}
    </aside>
  );
}
