import {
  setEquipmentComparison,
  setEquipmentParticle,
  setEquipmentRuntimeEffect,
  type EquipmentDraft,
} from "./equipmentCreator.ts";
import type { DraftChange } from "./equipmentCreatorPanelShared.ts";

export function EquipmentParticleFields({
  draft,
  onChange,
}: {
  draft: EquipmentDraft;
  onChange: DraftChange;
}) {
  return (
    <fieldset>
      <legend>Particle timeline</legend>
      <div className="field-grid">
        <label>
          Runtime effect
          <select
            aria-label="Equipment runtime effect"
            value={draft.runtimeEffect.effectId}
            onChange={(event) =>
              onChange(
                setEquipmentRuntimeEffect(
                  draft,
                  event.target.value === "15"
                    ? { effectId: 15, sourceItemIndex: 10728 }
                    : { effectId: 0, sourceItemIndex: null },
                ),
              )
            }
          >
            <option value={0}>None</option>
            <option value={15}>Effect 15 - Wind Dragon</option>
          </select>
        </label>
        <label>
          Color
          <input
            aria-label="Equipment particle color"
            type="color"
            value={draft.particle.color}
            onChange={(event) =>
              onChange(
                setEquipmentParticle(draft, {
                  ...draft.particle,
                  color: event.target.value,
                }),
              )
            }
          />
        </label>
        {(
          [
            ["rate", 1, 40, 1],
            ["lifetime", 0.1, 5, 0.1],
            ["size", 0.05, 3, 0.05],
          ] as const
        ).map(([field, min, max, step]) => (
          <label key={field}>
            {field} {draft.particle[field]}
            <input
              aria-label={`Equipment particle ${field}`}
              max={max}
              min={min}
              step={step}
              type="range"
              value={draft.particle[field]}
              onChange={(event) =>
                onChange(
                  setEquipmentParticle(draft, {
                    ...draft.particle,
                    [field]: Number(event.target.value),
                  }),
                )
              }
            />
          </label>
        ))}
      </div>
      <div className="particle-curve" aria-label="Particle size curve">
        {draft.particle.curve.map(([time, value]) => (
          <span
            key={time}
            style={{ left: `${time * 100}%`, bottom: `${value * 80}%` }}
          />
        ))}
      </div>
    </fieldset>
  );
}

export function EquipmentComparisonFields({
  draft,
  onChange,
  browserCaptureUrl,
  setBrowserCaptureUrl,
  clientCaptureUrl,
  setClientCaptureUrl,
}: {
  draft: EquipmentDraft;
  onChange: DraftChange;
  browserCaptureUrl: string;
  setBrowserCaptureUrl: (url: string) => void;
  clientCaptureUrl: string;
  setClientCaptureUrl: (url: string) => void;
}) {
  return (
    <fieldset>
      <legend>Browser ↔ client comparison</legend>
      <div className="comparison-grid">
        <label className="comparison-slot">
          Browser preview
          <input
            accept="image/png,image/jpeg"
            aria-label="Browser preview screenshot"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              setBrowserCaptureUrl(URL.createObjectURL(file));
              onChange(
                setEquipmentComparison(draft, {
                  ...draft.comparison,
                  browserScreenshot: file.name,
                }),
              );
            }}
            type="file"
          />
          {browserCaptureUrl ? (
            <img alt="Browser preview capture" src={browserCaptureUrl} />
          ) : (
            <span>No browser capture</span>
          )}
        </label>
        <label className="comparison-slot">
          DX9 client
          <input
            accept="image/png,image/jpeg"
            aria-label="DX9 client screenshot"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              setClientCaptureUrl(URL.createObjectURL(file));
              onChange(
                setEquipmentComparison(draft, {
                  ...draft.comparison,
                  clientScreenshot: file.name,
                }),
              );
            }}
            type="file"
          />
          {clientCaptureUrl ? (
            <img alt="DX9 client capture" src={clientCaptureUrl} />
          ) : (
            <span>No client capture</span>
          )}
        </label>
      </div>
      <p className="status">
        {draft.comparison.browserScreenshot &&
        draft.comparison.clientScreenshot
          ? "Both captures loaded · inspect silhouette, attachment, material, and aura."
          : "Load both captures for side-by-side visual review."}
      </p>
    </fieldset>
  );
}
