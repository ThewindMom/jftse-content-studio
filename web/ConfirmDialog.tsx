import { useEffect, useId, useRef } from "react";
import { getFocusTrapTarget } from "./focusTrap";

type ConfirmDialogProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel = "Cancel",
  tone = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const cancelHandlerRef = useRef(onCancel);
  cancelHandlerRef.current = onCancel;

  useEffect(() => {
    if (!open) return;
    const previousFocus =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const frame = requestAnimationFrame(() => cancelRef.current?.focus());
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        cancelHandlerRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const controls = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      );
      const currentIndex = controls.indexOf(
        document.activeElement as HTMLElement,
      );
      const target = getFocusTrapTarget(
        currentIndex,
        controls.length,
        event.shiftKey,
      );
      if (target === null) return;
      event.preventDefault();
      controls[target]?.focus();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="confirm-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <section
        aria-describedby={descriptionId}
        aria-labelledby={titleId}
        aria-modal="true"
        className="confirm-dialog"
        ref={dialogRef}
        role="dialog"
      >
        <div className="confirm-dialog-copy">
          <p className="eyebrow">Confirmation required</p>
          <h2 id={titleId}>{title}</h2>
          <p id={descriptionId}>{description}</p>
        </div>
        <div className="confirm-dialog-actions">
          <button ref={cancelRef} type="button" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            className={tone === "danger" ? "danger" : "primary"}
            type="button"
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
