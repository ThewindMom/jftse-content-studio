import { createHash } from "node:crypto";
import { mkdir, readdir, rename, rm } from "node:fs/promises";
import { join } from "node:path";
import { config } from "./config.ts";
import type { StudioAsset, TwinkleDocument } from "../web/twinkleDocument.ts";
import { isImportedModel } from "../web/twinkleDocument.ts";

export const importedPropDirectory = join(config.exportsDir, "imported-props");
export const MAX_GLB_BYTES = 16 * 1024 * 1024;

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid GLB object.");
  return Object.fromEntries(Object.entries(value));
}
function records(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) throw new Error("Invalid GLB array.");
  return value.map(record);
}
function integer(value: unknown, max: number): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0 || value > max) throw new Error("Invalid GLB count or reference.");
  return value;
}
function reference<T>(items: T[], value: unknown): T {
  const item = items[integer(value, items.length - 1)];
  if (item === undefined) throw new Error("Missing GLB reference.");
  return item;
}

// This is a deliberately bounded static-prop contract, not a general glTF validator.
export function inspectStaticGlb(bytes: Uint8Array): { vertices: number; triangles: number; submeshes: number } {
  if (bytes.length < 28 || bytes.length > MAX_GLB_BYTES) throw new Error("GLB must be between 28 bytes and 16 MiB.");
  const data = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (data.getUint32(0, true) !== 0x46546c67 || data.getUint32(4, true) !== 2 || data.getUint32(8, true) !== bytes.length) throw new Error("Expected a complete glTF 2.0 GLB.");
  const jsonLength = data.getUint32(12, true);
  const binHeader = 20 + jsonLength;
  if (jsonLength > 2_000_000 || jsonLength % 4 || binHeader + 8 > bytes.length || data.getUint32(16, true) !== 0x4e4f534a) throw new Error("Invalid GLB JSON chunk.");
  const binLength = data.getUint32(binHeader, true);
  if (data.getUint32(binHeader + 4, true) !== 0x004e4942 || binLength % 4 || binHeader + 8 + binLength !== bytes.length) throw new Error("Expected one embedded binary chunk.");
  const gltf = record(JSON.parse(new TextDecoder().decode(bytes.subarray(20, binHeader))));
  function portable(value: unknown, depth = 0): void {
    if (depth > 32) throw new Error("GLB metadata is too deeply nested.");
    if (Array.isArray(value)) { value.forEach((entry) => portable(entry, depth + 1)); return; }
    if (value && typeof value === "object") {
      for (const [key, entry] of Object.entries(value)) {
        if (key === "uri") throw new Error("External and data URIs are unsupported. Embed all textures in the GLB.");
        if (key === "extensions") {
          for (const extension of Object.keys(record(entry))) {
            if (!["KHR_materials_emissive_strength", "KHR_materials_unlit"].includes(extension)) throw new Error(`Unsupported GLB extension: ${extension}`);
          }
        }
        portable(entry, depth + 1);
      }
    }
  }
  portable(gltf);
  if (record(gltf.asset).version !== "2.0") throw new Error("Expected glTF 2.0.");
  for (const field of ["animations", "skins", "cameras"]) {
    if (records(gltf[field] ?? []).length) throw new Error("Import static props only; exclude animation, skinning, lights and cameras.");
  }
  const buffers = records(gltf.buffers);
  if (buffers.length !== 1) throw new Error("Expected one embedded buffer.");
  const bufferLength = integer(buffers[0]?.byteLength, binLength);
  if (binLength - bufferLength > 3) throw new Error("Invalid GLB buffer padding.");
  const views = records(gltf.bufferViews).map((view) => {
    if (view.buffer !== 0) throw new Error("Invalid GLB buffer.");
    const offset = integer(view.byteOffset ?? 0, bufferLength);
    const length = integer(view.byteLength, bufferLength - offset);
    const stride = view.byteStride === undefined ? 0 : integer(view.byteStride, 252);
    if (stride && (stride < 4 || stride % 4)) throw new Error("Invalid vertex stride.");
    return { offset, length, stride };
  });
  const accessors = records(gltf.accessors).map((accessor) => {
    if (accessor.sparse) throw new Error("Sparse accessors are unsupported.");
    const view = reference(views, accessor.bufferView);
    const count = integer(accessor.count, 600_000);
    const component = integer(accessor.componentType, 5126);
    const width = ({ 5121: 1, 5123: 2, 5125: 4, 5126: 4 })[component];
    const size = typeof accessor.type === "string" ? ({ SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 })[accessor.type] : undefined;
    if (!width || !size || !count) throw new Error("Unsupported GLB accessor.");
    const offset = integer(accessor.byteOffset ?? 0, view.length);
    const stride = view.stride || width * size;
    if (stride < width * size || offset % width || offset + (count - 1) * stride + width * size > view.length) throw new Error("GLB accessor exceeds its buffer view.");
    const read = (index: number, channel = 0) => {
      const address = binHeader + 8 + view.offset + offset + index * stride + channel * width;
      return component === 5126 ? data.getFloat32(address, true) : width === 1 ? data.getUint8(address) : width === 2 ? data.getUint16(address, true) : data.getUint32(address, true);
    };
    return { count, component, size, read };
  });
  for (const image of records(gltf.images ?? [])) {
    const view = reference(views, image.bufferView);
    const start = binHeader + 8 + view.offset;
    if (image.mimeType !== "image/png" || view.length < 24 || data.getUint32(start) !== 0x89504e47 || data.getUint32(start + 4) !== 0x0d0a1a0a) throw new Error("Use embedded PNG textures.");
    for (const offset of [16, 20]) {
      const dimension = data.getUint32(start + offset);
      if (!dimension || dimension > 4096) throw new Error("Texture dimensions must be 1–4096 pixels.");
    }
  }
  const images = records(gltf.images ?? []);
  const textures = records(gltf.textures ?? []);
  textures.forEach((texture) => reference(images, texture.source));
  const materials = records(gltf.materials ?? []);
  for (const material of materials) {
    const pbr = record(material.pbrMetallicRoughness ?? {});
    for (const texture of [pbr.baseColorTexture, pbr.metallicRoughnessTexture, material.normalTexture, material.occlusionTexture, material.emissiveTexture]) {
      if (texture !== undefined) reference(textures, record(texture).index);
    }
  }
  let inspectedComponents = 0;
  const meshes = records(gltf.meshes).map((mesh) => {
    let vertices = 0, triangles = 0;
    const parts = records(mesh.primitives);
    if (mesh.weights) throw new Error("Morph targets are unsupported.");
    for (const part of parts) {
      if ((part.mode ?? 4) !== 4 || part.targets) throw new Error("Export static triangle meshes without morph targets.");
      if (part.material !== undefined) reference(materials, part.material);
      const attributes = record(part.attributes);
      const position = reference(accessors, attributes.POSITION);
      if (position.component !== 5126 || position.size !== 3) throw new Error("Expected float3 positions.");
      for (const value of Object.values(attributes)) {
        const accessor = reference(accessors, value);
        if (accessor.count !== position.count) throw new Error("Vertex attribute counts differ.");
        inspectedComponents += accessor.count * accessor.size;
        if (inspectedComponents > 12_000_000) throw new Error("GLB vertex validation budget exceeded.");
        for (let i = 0; i < accessor.count; i++) for (let c = 0; c < accessor.size; c++) {
          if (!Number.isFinite(accessor.read(i, c))) throw new Error("Nonfinite vertex data.");
        }
      }
      const indices = part.indices === undefined ? null : reference(accessors, part.indices);
      if (indices && (indices.component === 5126 || indices.size !== 1)) throw new Error("Expected unsigned indices.");
      const count = indices?.count ?? position.count;
      if (count % 3) throw new Error("Incomplete triangles.");
      if (indices) for (let i = 0; i < count; i++) if (indices.read(i) >= position.count) throw new Error("Index exceeds vertex count.");
      vertices += position.count; triangles += count / 3;
    }
    return { vertices, triangles, submeshes: parts.length };
  });
  const nodes = records(gltf.nodes);
  if (nodes.length > 2000) throw new Error("Maximum 2000 nodes per prop.");
  const visited = new Set<number>();
  let vertices = 0, triangles = 0, submeshes = 0;
  function visit(index: unknown, depth = 0): void {
    const id = integer(index, nodes.length - 1);
    if (depth > 64 || visited.has(id)) throw new Error("GLB scene must be an acyclic tree.");
    visited.add(id);
    const node = reference(nodes, id);
    if (node.skin !== undefined || node.camera !== undefined || node.weights) throw new Error("Unsupported animated or camera node.");
    for (const [key, count] of [["matrix", 16], ["translation", 3], ["rotation", 4], ["scale", 3]] as const) {
      const value = node[key];
      if (value !== undefined && (!Array.isArray(value) || value.length !== count || value.some((v) => typeof v !== "number" || !Number.isFinite(v) || Math.abs(v) > 10_000))) throw new Error("Invalid node transform.");
    }
    if (node.mesh !== undefined) {
      const mesh = reference(meshes, node.mesh);
      vertices += mesh.vertices; triangles += mesh.triangles; submeshes += mesh.submeshes;
    }
    if (node.children !== undefined) {
      if (!Array.isArray(node.children)) throw new Error("Invalid node children.");
      node.children.forEach((child) => visit(child, depth + 1));
    }
  }
  const scene = reference(records(gltf.scenes), gltf.scene ?? 0);
  if (!Array.isArray(scene.nodes)) throw new Error("Missing default scene.");
  scene.nodes.forEach((node) => visit(node));
  if (!triangles || triangles > 200_000 || vertices > 600_000) throw new Error("Prop must have 1–200,000 triangles and at most 600,000 vertices.");
  return { vertices, triangles, submeshes };
}

export async function importedProps(): Promise<StudioAsset[]> {
  await mkdir(importedPropDirectory, { recursive: true });
  const names = (await readdir(importedPropDirectory)).filter((name) => /^[a-f0-9]{64}\.json$/.test(name));
  return Promise.all(names.sort().map((name) => Bun.file(join(importedPropDirectory, name)).json()));
}

export async function importProp(req: Request): Promise<Response> {
  try {
    const name = new URL(req.url).searchParams.get("name")?.trim();
    if (!name || name.length > 80 || /[\x00-\x1f]/.test(name)) throw new Error("Give the prop a name of 1–80 characters.");
    if (Number(req.headers.get("content-length")) > MAX_GLB_BYTES) throw new Error("Maximum GLB upload is 16 MiB.");
    const reader = req.body?.getReader();
    if (!reader) throw new Error("Missing GLB upload.");
    const chunks: Uint8Array[] = [];
    let length = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        length += value.length;
        if (length > MAX_GLB_BYTES) { await reader.cancel(); throw new Error("Maximum GLB upload is 16 MiB."); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    const bytes = Buffer.concat(chunks);
    const stats = inspectStaticGlb(bytes);
    const hash = createHash("sha256").update(bytes).digest("hex");
    const asset: StudioAsset = { file: `Studio/Imported/${hash}.glb`, geometry: `import-${hash}.glb`,
      name, fixed: false, category: "imported", pose: "static", thumbnail: null, ...stats };
    await mkdir(importedPropDirectory, { recursive: true });
    const glbPath = join(importedPropDirectory, `${hash}.glb`);
    const glbTemporary = `${glbPath}.${crypto.randomUUID()}.tmp`;
    try {
      await Bun.write(glbTemporary, bytes);
      await rename(glbTemporary, glbPath);
    } finally { await rm(glbTemporary, { force: true }); }
    const path = join(importedPropDirectory, `${hash}.json`);
    const temporary = `${path}.${crypto.randomUUID()}.tmp`;
    try {
      await Bun.write(temporary, JSON.stringify(asset, null, 2));
      await rename(temporary, path);
    } finally { await rm(temporary, { force: true }); }
    return Response.json(asset);
  } catch (error) { return Response.json({ error: String(error) }, { status: 400 }); }
}

export function rejectImportedNativeExport(doc: TwinkleDocument): void {
  if (doc.objects.some((obj) => isImportedModel(obj.file))) throw new Error("Blender imports are Studio-only. Remove imported placements before native export/install; DAT conversion and collision are not implemented.");
}
