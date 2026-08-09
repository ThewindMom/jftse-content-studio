import {
  duplicateMapObject,
  setMapReferences,
  type MapObject,
  type MapSceneDocument,
  type Vec3,
} from "./mapSceneDocument.ts";
import {
  mapTransformPatch,
  type MapTransformMode,
} from "./mapSceneTransform.ts";

function updateAxis(value: Vec3, axis: number, next: number): Vec3 {
  const copy: Vec3 = [...value];
  copy[axis] = next;
  return copy;
}

type MapCreatorInspectorProps = {
  scene: MapSceneDocument;
  selectedId: string;
  mode: MapTransformMode;
  snap: number;
  onSelect: (id: string) => void;
  onSceneChange: (scene: MapSceneDocument) => void;
  onTransform: (object: MapObject, patch: Partial<MapObject>) => void;
};

export function MapCreatorInspector({
  scene,
  selectedId,
  mode,
  snap,
  onSelect,
  onSceneChange,
  onTransform,
}: MapCreatorInspectorProps) {
  const selected = scene.objects.find((object) => object.id === selectedId);
  const source = selected
    ? mode === "translate"
      ? selected.position
      : mode === "rotate"
        ? selected.rotation
        : selected.scale
    : undefined;

  return (
    <aside className="map-inspector" aria-label="Map object inspector">
      <strong>Scene hierarchy</strong>
      {scene.objects.map((object) => (
        <button
          className="hierarchy-row"
          data-active={selectedId === object.id}
          key={object.id}
          onClick={() => onSelect(object.id)}
          type="button"
        >
          {object.name}
        </button>
      ))}
      {selected && source ? (
        <>
          <strong>{selected.name}</strong>
          <div className="gizmo-axis" aria-label={`${mode} controls`}>
            {([0, 1, 2] as const).map((axis) => (
              <label key={axis}>
                {"XYZ"[axis]}
                <input
                  aria-label={`${mode} ${"XYZ"[axis]}`}
                  step={mode === "rotate" ? 15 : snap || 0.1}
                  type="number"
                  value={source[axis]}
                  onChange={(event) =>
                    onTransform(
                      selected,
                      mapTransformPatch(
                        mode,
                        updateAxis(source, axis, Number(event.target.value)),
                      ),
                    )
                  }
                />
              </label>
            ))}
          </div>
          <button
            className="btn"
            onClick={() =>
              onSceneChange(duplicateMapObject(scene, selected.id))
            }
            type="button"
          >
            Duplicate
          </button>
        </>
      ) : (
        <p className="empty">Select an object in the viewport.</p>
      )}
      <label className="btn file-button">
        Blender terrain
        <input
          accept=".blend,.obj,.gltf,.glb"
          aria-label="Blender terrain round-trip file"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            onSceneChange(
              setMapReferences(scene, {
                ...scene.references,
                terrainSource: file.name,
              }),
            );
          }}
          type="file"
        />
      </label>
      <label className="btn file-button">
        Court texture
        <input
          accept="image/*"
          aria-label="Map material texture"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            onSceneChange(
              setMapReferences(scene, {
                ...scene.references,
                materials: [{ slot: "court", texture: file.name }],
              }),
            );
          }}
          type="file"
        />
      </label>
    </aside>
  );
}
