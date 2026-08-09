export function getFocusTrapTarget(
  currentIndex: number,
  controlCount: number,
  backward: boolean,
): number | null {
  if (controlCount < 1) return null;
  if (currentIndex < 0) return backward ? controlCount - 1 : 0;
  if (backward && currentIndex === 0) return controlCount - 1;
  if (!backward && currentIndex === controlCount - 1) return 0;
  return null;
}
