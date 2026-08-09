import type {
  EquipmentDraft,
  EquipmentValidation,
} from "./equipmentCreator.ts";
import { SAMPLE_GLTF } from "./equipmentCreatorPanelShared.ts";

export function EquipmentCreatorHeader({
  importSource,
}: {
  importSource: (name: string, source: string) => void;
}) {
  return (
    <header className="creator-heading">
      <div>
        <p className="eyebrow">New equipment</p>
        <h3>Equipment Creator</h3>
        <p className="muted">
          Import glTF or OBJ metadata, assign presentation and attachment, then
          build from the selected stock racket. Imported topology is preview/spec-only;
          stock topology is the production compatibility boundary. DX9 client
          verification remains authoritative.
        </p>
      </div>
      <div className="actions">
        <label className="btn file-button">
          Import glTF
          <input
            accept=".gltf,.json,model/gltf+json"
            aria-label="Import equipment glTF"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (file) importSource(file.name, await file.text());
            }}
            type="file"
          />
        </label>
        <label className="btn file-button">
          Import OBJ
          <input
            accept=".obj,model/obj,text/plain"
            aria-label="Import equipment OBJ"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (file) importSource(file.name, await file.text());
            }}
            type="file"
          />
        </label>
        <button
          className="btn"
          onClick={() => importSource("studio-sample.gltf", SAMPLE_GLTF)}
          type="button"
        >
          Load sample
        </button>
      </div>
    </header>
  );
}

export function EquipmentCreatorEmpty() {
  return (
    <div className="creator-empty">
      <strong>Start with a glTF 2.0 or OBJ model</strong>
      <span>
        Materials become visual slots. Imported topology is preview/spec-only;
        no archive path or mesh-index entry is required.
      </span>
    </div>
  );
}

export function EquipmentPreview({ draft }: { draft: EquipmentDraft }) {
  return (
    <div className="creator-preview" aria-label="Imported model summary">
      <div
        className="racket-swatch"
        style={{
          background:
            draft.materials[draft.asset.materials[0]?.id]?.color ?? "#57d7ff",
        }}
      />
      <strong>{draft.asset.meshName}</strong>
      <span>
        {draft.asset.vertexCount} vertices · {draft.asset.indexCount} indices
      </span>
      <span>{draft.asset.sourceName}</span>
    </div>
  );
}

export function EquipmentValidationSummary({
  issues,
}: {
  issues: EquipmentValidation[];
}) {
  return (
    <div className="creator-validation" aria-live="polite">
      <strong>
        {issues.length === 0
          ? "Ready to build"
          : `${issues.length} decision${issues.length === 1 ? "" : "s"} remaining`}
      </strong>
      {issues.map((issue) => (
        <span key={issue.field}>{issue.message}</span>
      ))}
    </div>
  );
}
