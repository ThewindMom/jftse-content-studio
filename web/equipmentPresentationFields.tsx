import {
  setEquipmentAttachment,
  setEquipmentMetadata,
  type EquipmentDraft,
} from "./equipmentCreator.ts";
import type { DraftChange } from "./equipmentCreatorPanelShared.ts";

export function EquipmentPresentationFields({
  draft,
  onChange,
}: {
  draft: EquipmentDraft;
  onChange: DraftChange;
}) {
  return (
    <>
      <fieldset>
        <legend>Inventory presentation</legend>
        <div className="field-grid">
          <label>
            Item name
            <input
              aria-label="New equipment name"
              value={draft.metadata.name}
              onChange={(event) =>
                onChange(
                  setEquipmentMetadata(draft, {
                    ...draft.metadata,
                    name: event.target.value,
                  }),
                )
              }
            />
          </label>
          <label>
            Item index
            <input
              aria-label="New equipment item index"
              min={1}
              type="number"
              value={draft.metadata.itemIndex || ""}
              onChange={(event) =>
                onChange(
                  setEquipmentMetadata(draft, {
                    ...draft.metadata,
                    itemIndex: Number(event.target.value),
                  }),
                )
              }
            />
          </label>
          <label>
            Character
            <select
              aria-label="New equipment character"
              value={draft.metadata.character}
              onChange={(event) =>
                onChange(
                  setEquipmentMetadata(draft, {
                    ...draft.metadata,
                    character: event.target.value,
                    compatibleCharacters: [event.target.value],
                  }),
                )
              }
            >
              <option>NIKI</option>
              <option>LUCY</option>
              <option>DANPIL</option>
            </select>
          </label>
          <label>
            Price
            <input
              aria-label="New equipment price"
              min={0}
              type="number"
              value={draft.metadata.price}
              onChange={(event) =>
                onChange(
                  setEquipmentMetadata(draft, {
                    ...draft.metadata,
                    price: Number(event.target.value),
                  }),
                )
              }
            />
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Attachment</legend>
        <label>
          Hand bone
          <select
            aria-label="Equipment attachment bone"
            value={draft.attachment?.bone ?? ""}
            onChange={(event) =>
              onChange(
                setEquipmentAttachment(draft, {
                  bone: event.target.value,
                  position: [0, 0, 0],
                  rotation: [0, 0, 0],
                  scale: [1, 1, 1],
                }),
              )
            }
          >
            <option value="">Choose a bone</option>
            <option value="Bone_Racket">Right hand · Bone_Racket</option>
            <option value="Bip01 L Hand">Left hand · Bip01 L Hand</option>
          </select>
        </label>
      </fieldset>
    </>
  );
}
