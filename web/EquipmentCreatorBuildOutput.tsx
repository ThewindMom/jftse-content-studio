import { EquipmentManagedWorkflowPanel } from "./EquipmentManagedWorkflowPanel.tsx";
import type { EquipmentBuildWorkflow } from "./useEquipmentManagedWorkflow.ts";

export function EquipmentCreatorBuildOutput({
  manifest,
  workflow,
}: {
  manifest: string;
  workflow: EquipmentBuildWorkflow | null;
}) {
  if (!manifest) return null;
  return (
    <>
      <details className="manifest-output" open>
        <summary>Production package receipt and creator manifest</summary>
        <p className="validation ok">Package built without installing it.</p>
        <pre>{manifest}</pre>
      </details>
      {workflow && <EquipmentManagedWorkflowPanel build={workflow} />}
    </>
  );
}
