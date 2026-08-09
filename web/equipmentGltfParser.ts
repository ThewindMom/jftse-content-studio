import type { ImportedEquipmentAsset } from "./equipmentTypes.ts";

type GltfAccessor = { count: number };
type GltfPrimitive = {
  attributes: { POSITION?: number };
  indices?: number;
  material?: number;
};
type GltfMesh = { name?: string; primitives: GltfPrimitive[] };
type GltfMaterial = { name?: string };
type ParsedGltf = {
  asset: { version: string };
  accessors: GltfAccessor[];
  meshes: GltfMesh[];
  materials?: GltfMaterial[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseAccessor(value: unknown): GltfAccessor {
  if (
    !isRecord(value) ||
    typeof value.count !== "number" ||
    !Number.isInteger(value.count) ||
    value.count < 0
  ) {
    throw new Error("glTF accessor has an invalid count.");
  }
  return { count: value.count as number };
}

function parsePrimitive(value: unknown): GltfPrimitive {
  if (!isRecord(value) || !isRecord(value.attributes)) {
    throw new Error("glTF mesh primitive is missing attributes.");
  }
  const position = value.attributes.POSITION;
  if (
    typeof position !== "number" ||
    !Number.isInteger(position) ||
    position < 0
  ) {
    throw new Error("glTF mesh primitive is missing POSITION data.");
  }
  const indices = value.indices;
  const material = value.material;
  if (
    indices !== undefined &&
    (typeof indices !== "number" || !Number.isInteger(indices))
  ) {
    throw new Error("glTF mesh primitive has an invalid index accessor.");
  }
  if (
    material !== undefined &&
    (typeof material !== "number" || !Number.isInteger(material))
  ) {
    throw new Error("glTF mesh primitive has an invalid material slot.");
  }
  return {
    attributes: { POSITION: position as number },
    indices: indices as number | undefined,
    material: material as number | undefined,
  };
}

function parseGltf(source: string): ParsedGltf {
  let value: unknown;
  try {
    value = JSON.parse(source);
  } catch {
    throw new Error("glTF file is not valid JSON.");
  }
  if (
    !isRecord(value) ||
    !isRecord(value.asset) ||
    typeof value.asset.version !== "string" ||
    !Array.isArray(value.accessors) ||
    !Array.isArray(value.meshes) ||
    value.meshes.length === 0
  ) {
    throw new Error("glTF mesh data is missing.");
  }
  const meshes = value.meshes.map((mesh) => {
    if (!isRecord(mesh) || !Array.isArray(mesh.primitives)) {
      throw new Error("glTF mesh primitives are missing.");
    }
    return {
      name: typeof mesh.name === "string" ? mesh.name : undefined,
      primitives: mesh.primitives.map(parsePrimitive),
    };
  });
  const materials = Array.isArray(value.materials)
    ? value.materials.map((material) => ({
        name:
          isRecord(material) && typeof material.name === "string"
            ? material.name
            : undefined,
      }))
    : undefined;
  return {
    asset: { version: value.asset.version },
    accessors: value.accessors.map(parseAccessor),
    meshes,
    materials,
  };
}

export function importEquipmentGltf(
  sourceName: string,
  source: string,
  options: { maxVertices?: number } = {},
): ImportedEquipmentAsset {
  const gltf = parseGltf(source);
  if (!gltf.asset.version.startsWith("2.")) {
    throw new Error(`Unsupported glTF version ${gltf.asset.version}.`);
  }
  const mesh = gltf.meshes[0];
  const primitive = mesh.primitives[0];
  const positionAccessor = gltf.accessors[primitive.attributes.POSITION ?? -1];
  if (!positionAccessor) {
    throw new Error("glTF mesh POSITION accessor is missing.");
  }
  const vertexCount = positionAccessor.count;
  const maxVertices = options.maxVertices ?? 250_000;
  if (vertexCount > maxVertices) {
    throw new Error(
      `glTF vertex limit exceeded (${vertexCount} > ${maxVertices}).`,
    );
  }
  const indexCount =
    primitive.indices === undefined
      ? vertexCount
      : gltf.accessors[primitive.indices]?.count;
  if (indexCount === undefined) {
    throw new Error("glTF mesh index accessor is missing.");
  }
  const materialIndexes = [
    ...new Set(
      mesh.primitives
        .map((entry) => entry.material)
        .filter((index): index is number => index !== undefined),
    ),
  ];
  const materials =
    materialIndexes.length > 0
      ? materialIndexes.map((index) => ({
          id: `material-${index}`,
          name: gltf.materials?.[index]?.name ?? `Material ${index + 1}`,
        }))
      : [{ id: "material-0", name: "Material 1" }];
  return {
    sourceName,
    meshName: mesh.name ?? sourceName.replace(/\.[^.]+$/, ""),
    vertexCount,
    indexCount,
    materials,
    warnings: [],
  };
}
