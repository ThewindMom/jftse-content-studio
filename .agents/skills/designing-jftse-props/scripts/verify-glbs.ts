import { createHash } from "node:crypto";
import { Box3, Matrix4, Quaternion, Vector3 } from "three";
import { inspectStaticGlb } from "../../../../server/importedProps.ts";

// Fields consumed here have been checked by the Studio import boundary first.
type StaticGlb = {
  scene?: number;
  scenes: { nodes: number[] }[];
  nodes: { name?: unknown; mesh?: number; children?: number[]; matrix?: number[]; translation?: number[]; rotation?: number[]; scale?: number[] }[];
  meshes: { name?: unknown; primitives: { attributes: Record<string, number> }[] }[];
  accessors: { bufferView: number; byteOffset?: number; count: number }[];
  bufferViews: { byteOffset?: number; byteStride?: number }[];
  images?: unknown[];
  materials?: unknown[];
};

export function measureStaticProp(bytes: Uint8Array) {
  const counts = inspectStaticGlb(bytes);
  const data = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const jsonLength = data.getUint32(12, true);
  const gltf = JSON.parse(new TextDecoder().decode(bytes.subarray(20, 20 + jsonLength))) as StaticGlb;
  const bounds = new Box3();
  const point = new Vector3();
  const names: string[] = [];
  function visit(index: number, parent: Matrix4) {
    const node = gltf.nodes[index]!;
    if (typeof node.name === "string") names.push(node.name);
    const local = node.matrix ? new Matrix4().fromArray(node.matrix) : new Matrix4().compose(
      new Vector3().fromArray(node.translation ?? [0, 0, 0]),
      new Quaternion().fromArray(node.rotation ?? [0, 0, 0, 1]),
      new Vector3().fromArray(node.scale ?? [1, 1, 1]),
    );
    const world = new Matrix4().multiplyMatrices(parent, local);
    if (node.mesh !== undefined) {
      const mesh = gltf.meshes[node.mesh]!;
      if (typeof mesh.name === "string") names.push(mesh.name);
      for (const part of mesh.primitives) {
        const accessor = gltf.accessors[part.attributes.POSITION!]!;
        const view = gltf.bufferViews[accessor.bufferView]!;
        const start = 28 + jsonLength + (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
        for (let i = 0; i < accessor.count; i++) {
          const address = start + i * (view.byteStride ?? 12);
          point.set(data.getFloat32(address, true), data.getFloat32(address + 4, true), data.getFloat32(address + 8, true));
          bounds.expandByPoint(point.applyMatrix4(world));
        }
      }
    }
    for (const child of node.children ?? []) visit(child, world);
  }
  for (const index of gltf.scenes[gltf.scene ?? 0]!.nodes) visit(index, new Matrix4());
  if (names.some((name) => /^PREVIEW[_-]/i.test(name))) throw new Error("Preview objects leaked into the exported asset.");
  const size = bounds.getSize(new Vector3());
  if (bounds.isEmpty() || [...bounds.min, ...bounds.max].some((n) => !Number.isFinite(n)) || size.length() === 0) throw new Error("Invalid transformed prop bounds.");
  return {
    sha256: createHash("sha256").update(bytes).digest("hex"), bytes: bytes.length, ...counts,
    images: gltf.images?.length ?? 0, materials: gltf.materials?.length ?? 0,
    bounds: { min: bounds.min.toArray(), max: bounds.max.toArray(), size: size.toArray() },
  };
}

if (import.meta.main) {
  const paths = Bun.argv.slice(2);
  if (!paths.length) throw new Error("Usage: bun verify-glbs.ts <asset.glb> [...]");
  const reports = [];
  for (const path of paths) reports.push({ path, ...measureStaticProp(await Bun.file(path).bytes()) });
  process.stdout.write(`${JSON.stringify(reports, null, 2)}\n`);
}
