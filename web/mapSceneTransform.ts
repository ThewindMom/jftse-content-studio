import type { MapObject, Vec3 } from "./mapSceneTypes.ts";

export type MapTransformMode = "translate" | "rotate" | "scale";

export function mapTransformPatch(
  mode: MapTransformMode,
  value: Vec3,
): Partial<MapObject> {
  switch (mode) {
    case "translate":
      return { position: value };
    case "rotate":
      return { rotation: value };
    case "scale":
      return { scale: value };
  }
}
