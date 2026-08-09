import type {
  EquipmentDraft,
  MaterialAssignment,
} from "./equipmentCreator.ts";
import { DEFAULT_MATERIAL } from "./equipmentCreatorPanelShared.ts";

export function EquipmentMaterialFields({
  draft,
  updateMaterial,
}: {
  draft: EquipmentDraft;
  updateMaterial: (slot: string, patch: Partial<MaterialAssignment>) => void;
}) {
  return draft.asset.materials.map((material) => {
    const assignment = draft.materials[material.id] ?? DEFAULT_MATERIAL;
    return (
      <fieldset key={material.id}>
        <legend>{material.name} material</legend>
        <div className="field-grid">
          <label className="btn file-button">
            Choose texture
            <input
              accept="image/png,image/jpeg,image/bmp"
              aria-label={`Texture for ${material.name}`}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  updateMaterial(material.id, { textureName: file.name });
                }
              }}
              type="file"
            />
          </label>
          <label>
            Tint
            <input
              aria-label={`Tint for ${material.name}`}
              type="color"
              value={assignment.color}
              onChange={(event) =>
                updateMaterial(material.id, { color: event.target.value })
              }
            />
          </label>
          <label>
            Metallic {assignment.metallic.toFixed(2)}
            <input
              aria-label={`Metallic for ${material.name}`}
              max={1}
              min={0}
              step={0.05}
              type="range"
              value={assignment.metallic}
              onChange={(event) =>
                updateMaterial(material.id, {
                  metallic: Number(event.target.value),
                })
              }
            />
          </label>
          <label>
            Roughness {assignment.roughness.toFixed(2)}
            <input
              aria-label={`Roughness for ${material.name}`}
              max={1}
              min={0}
              step={0.05}
              type="range"
              value={assignment.roughness}
              onChange={(event) =>
                updateMaterial(material.id, {
                  roughness: Number(event.target.value),
                })
              }
            />
          </label>
        </div>
        <p className="status">
          {assignment.textureName || "No texture selected"}
        </p>
      </fieldset>
    );
  });
}
