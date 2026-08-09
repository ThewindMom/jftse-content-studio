import type { ImportedEquipmentAsset } from "./equipmentTypes.ts";

function cleanName(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

export function importEquipmentObj(
  sourceName: string,
  source: string,
  options: { maxVertices?: number } = {},
): ImportedEquipmentAsset {
  let vertexCount = 0;
  let indexCount = 0;
  let meshName = sourceName.replace(/\.[^.]+$/, "");
  const materialNames: string[] = [];

  for (const rawLine of source.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const separator = line.search(/\s/);
    const keyword = separator < 0 ? line : line.slice(0, separator);
    const rest = separator < 0 ? "" : line.slice(separator + 1).trim();
    if (keyword === "v") {
      const coordinates = rest.split(/\s+/).map(Number);
      if (coordinates.length < 3 || coordinates.slice(0, 3).some((n) => !Number.isFinite(n))) {
        throw new Error("OBJ vertex has invalid coordinates.");
      }
      vertexCount += 1;
    } else if (keyword === "f") {
      const vertices = rest.split(/\s+/).filter(Boolean);
      if (vertices.length < 3 || vertices.some((entry) => !/^-?\d+(?:\/[^\s]*)?$/.test(entry))) {
        throw new Error("OBJ face has invalid vertex references.");
      }
      indexCount += (vertices.length - 2) * 3;
    } else if ((keyword === "o" || keyword === "g") && rest && meshName === sourceName.replace(/\.[^.]+$/, "")) {
      meshName = cleanName(rest);
    } else if (keyword === "usemtl" && rest) {
      const name = cleanName(rest);
      if (!materialNames.includes(name)) materialNames.push(name);
    }
  }

  if (vertexCount === 0 || indexCount === 0) {
    throw new Error("OBJ mesh data is missing vertices or faces.");
  }
  const maxVertices = options.maxVertices ?? 250_000;
  if (vertexCount > maxVertices) {
    throw new Error(`OBJ vertex limit exceeded (${vertexCount} > ${maxVertices}).`);
  }
  const names = materialNames.length > 0 ? materialNames : ["Material 1"];
  return {
    sourceName,
    meshName,
    vertexCount,
    indexCount,
    materials: names.map((name, index) => ({ id: `material-${index}`, name })),
    warnings: [
      "Imported OBJ topology is preview/spec-only; production uses the selected stock racket topology.",
    ],
  };
}
