import { useEffect, useMemo, useRef, useState } from "react";
import {
  assignEquipmentMaterial,
  createEquipmentDraft,
  importEquipmentGltf,
  importEquipmentObj,
  validateEquipmentDraft,
  type EquipmentDraft,
  type MaterialAssignment,
} from "./equipmentCreator.ts";
import { EquipmentComparisonFields, EquipmentParticleFields } from "./equipmentEffectsFields.tsx";
import { EquipmentMaterialFields } from "./equipmentMaterialFields.tsx";
import { EquipmentPresentationFields } from "./equipmentPresentationFields.tsx";
import { EquipmentCreatorEmpty, EquipmentCreatorHeader, EquipmentPreview,
  EquipmentValidationSummary } from "./equipmentCreatorPanelParts.tsx";
import {
  type CapturePreview,
  DEFAULT_MATERIAL,
  matchingCapturePreview,
} from "./equipmentCreatorPanelShared.ts";
import { EquipmentCreatorBuildOutput } from "./EquipmentCreatorBuildOutput.tsx";
import {
  readEquipmentBuildWorkflow,
  type EquipmentBuildWorkflow,
} from "./useEquipmentManagedWorkflow.ts";

export type EquipmentCreatorPanelProps = {
  value?: EquipmentDraft | null;
  stockMeshIndex?: number | null;
  onChange?: (draft: EquipmentDraft | null) => void;
};

export { type CapturePreview, matchingCapturePreview } from "./equipmentCreatorPanelShared.ts";

export function EquipmentCreatorPanel({
  value,
  stockMeshIndex = null,
  onChange,
}: EquipmentCreatorPanelProps = {}) {
  const [uncontrolledDraft, setUncontrolledDraft] = useState<EquipmentDraft | null>(null);
  const [manifest, setManifest] = useState("");
  const [buildWorkflow, setBuildWorkflow] = useState<EquipmentBuildWorkflow | null>(null);
  const [importError, setImportError] = useState("");
  const [buildError, setBuildError] = useState("");
  const [building, setBuilding] = useState(false);
  const [browserCaptureState, setBrowserCapture] = useState<CapturePreview | null>(null);
  const [clientCaptureState, setClientCapture] = useState<CapturePreview | null>(null);
  const pendingBrowserUrl = useRef("");
  const pendingClientUrl = useRef("");
  const draft = value === undefined ? uncontrolledDraft : value;
  const browserCapture = matchingCapturePreview(
    browserCaptureState, draft?.comparison.browserScreenshot ?? null,
  );
  const clientCapture = matchingCapturePreview(
    clientCaptureState, draft?.comparison.clientScreenshot ?? null,
  );
  const issues = useMemo(() => (draft ? validateEquipmentDraft(draft) : []), [draft]);
  useEffect(
    () => () => {
      if (browserCapture?.url) URL.revokeObjectURL(browserCapture.url);
    },
    [browserCapture?.url],
  );
  useEffect(
    () => () => {
      if (clientCapture?.url) URL.revokeObjectURL(clientCapture.url);
    },
    [clientCapture?.url],
  );

  useEffect(() => setBrowserCapture((current) => matchingCapturePreview(
    current, draft?.comparison.browserScreenshot ?? null,
  )), [draft?.comparison.browserScreenshot]);
  useEffect(() => setClientCapture((current) => matchingCapturePreview(
    current, draft?.comparison.clientScreenshot ?? null,
  )), [draft?.comparison.clientScreenshot]);
  useEffect(
    () => () => {
      if (pendingBrowserUrl.current) URL.revokeObjectURL(pendingBrowserUrl.current);
      if (pendingClientUrl.current) URL.revokeObjectURL(pendingClientUrl.current);
    },
    [],
  );

  const changeDraft = (nextDraft: EquipmentDraft | null) => {
    if (value === undefined) setUncontrolledDraft(nextDraft);
    onChange?.(nextDraft);
  };

  const changeComparison = (nextDraft: EquipmentDraft | null) => {
    if (!draft || !nextDraft) {
      changeDraft(nextDraft);
      return;
    }
    const shownBrowser = browserCapture?.filename ?? null;
    const shownClient = clientCapture?.filename ?? null;
    const browserChanged = Boolean(pendingBrowserUrl.current) ||
      nextDraft.comparison.browserScreenshot !== shownBrowser;
    const clientChanged = Boolean(pendingClientUrl.current) ||
      nextDraft.comparison.clientScreenshot !== shownClient;
    if (browserChanged && pendingBrowserUrl.current) {
      setBrowserCapture({
        filename: nextDraft.comparison.browserScreenshot ?? "",
        url: pendingBrowserUrl.current,
      });
      pendingBrowserUrl.current = "";
    }
    if (clientChanged && pendingClientUrl.current) {
      setClientCapture({
        filename: nextDraft.comparison.clientScreenshot ?? "",
        url: pendingClientUrl.current,
      });
      pendingClientUrl.current = "";
    }
    changeDraft({
      ...nextDraft,
      comparison: {
        browserScreenshot: browserChanged
          ? nextDraft.comparison.browserScreenshot
          : draft.comparison.browserScreenshot,
        clientScreenshot: clientChanged
          ? nextDraft.comparison.clientScreenshot
          : draft.comparison.clientScreenshot,
      },
    });
  };

  const importSource = (name: string, source: string) => {
    try {
      const asset = name.toLowerCase().endsWith(".obj")
        ? importEquipmentObj(name, source)
        : importEquipmentGltf(name, source);
      changeDraft(createEquipmentDraft(asset));
      setManifest("");
      setBuildWorkflow(null);
      setImportError("");
      setBuildError("");
    } catch (error) {
      setImportError(error instanceof Error ? error.message : String(error));
    }
  };

  const buildPackage = async () => {
    if (!draft || stockMeshIndex === null) return;
    setBuilding(true);
    setBuildError("");
    setManifest("");
    setBuildWorkflow(null);
    try {
      const response = await fetch("/api/equipment-creator/package", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ draft, stockMeshIndex }),
      });
      const result: unknown = await response.json();
      if (!response.ok) {
        throw new Error(
          result &&
            typeof result === "object" &&
            "error" in result
            ? String(result.error)
            : "PACKAGE_BUILD_FAILED",
        );
      }
      const workflow = readEquipmentBuildWorkflow(result);
      setBuildWorkflow(workflow);
      setManifest(JSON.stringify(result, null, 2));
    } catch (error) {
      setBuildError(error instanceof Error ? error.message : String(error));
    } finally {
      setBuilding(false);
    }
  };

  const updateMaterial = (
    slot: string,
    patch: Partial<MaterialAssignment>,
  ) => {
    if (!draft) return;
    changeDraft(
      assignEquipmentMaterial(draft, slot, {
        ...(draft.materials[slot] ?? DEFAULT_MATERIAL),
        ...patch,
      }),
    );
  };

  return (
    <section className="equipment-creator" aria-label="Equipment Creator">
      <EquipmentCreatorHeader importSource={importSource} />
      {importError && (
        <p className="validation bad" role="alert">
          {importError}
        </p>
      )}

      {!draft ? (
        <EquipmentCreatorEmpty />
      ) : (
        <div className="creator-grid">
          <EquipmentPreview draft={draft} />
          <div className="creator-fields">
            <EquipmentPresentationFields
              draft={draft}
              onChange={changeDraft}
            />
            <EquipmentMaterialFields
              draft={draft}
              updateMaterial={updateMaterial}
            />
            <EquipmentParticleFields draft={draft} onChange={changeDraft} />
            <EquipmentComparisonFields
              browserCaptureUrl={browserCapture?.url ?? ""}
              clientCaptureUrl={clientCapture?.url ?? ""}
              draft={{
                ...draft,
                comparison: {
                  browserScreenshot: browserCapture?.filename ?? null,
                  clientScreenshot: clientCapture?.filename ?? null,
                },
              }}
              onChange={changeComparison}
              setBrowserCaptureUrl={(url) => {
                if (pendingBrowserUrl.current) {
                  URL.revokeObjectURL(pendingBrowserUrl.current);
                }
                pendingBrowserUrl.current = url;
              }}
              setClientCaptureUrl={(url) => {
                if (pendingClientUrl.current) {
                  URL.revokeObjectURL(pendingClientUrl.current);
                }
                pendingClientUrl.current = url;
              }}
            />
            <EquipmentValidationSummary issues={issues} />
            {stockMeshIndex === null && (
              <p className="validation bad">
                Select a stock racket; its mesh topology is the production compatibility boundary.
              </p>
            )}
            {buildError && <p className="validation bad" role="alert">Build failed: {buildError}</p>}
            <button
              className="btn primary"
              disabled={issues.length > 0 || stockMeshIndex === null || building}
              onClick={() => void buildPackage()}
              type="button"
            >
              {building ? "Building production package…" : "Build production package"}
            </button>
          </div>
        </div>
      )}

      <EquipmentCreatorBuildOutput
        manifest={manifest}
        workflow={buildWorkflow}
      />
    </section>
  );
}
