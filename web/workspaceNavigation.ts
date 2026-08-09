export const WORKSPACE_ORDER = [
  "equipment",
  "packs",
  "maps",
  "meshes",
] as const;

export type WorkspaceMode = (typeof WORKSPACE_ORDER)[number];

export function moveTab<T extends string>(
  order: readonly T[],
  current: T,
  key: string,
): T {
  const index = order.indexOf(current);
  if (index < 0 || order.length === 0) return current;
  if (key === "Home") return order[0];
  if (key === "End") return order[order.length - 1];
  if (key === "ArrowRight") return order[(index + 1) % order.length];
  if (key === "ArrowLeft") {
    return order[(index - 1 + order.length) % order.length];
  }
  return current;
}
