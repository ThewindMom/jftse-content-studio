import { describe, expect, test } from "bun:test";
import { inspectStaticGlb, rejectImportedNativeExport, MAX_GLB_BYTES } from "../server/importedProps.ts";
import { parseTwinkleDocument } from "../web/twinkleDocument.ts";
import { twinkleExport, twinkleClient, twinkleFile } from "../server/twinkleStudio.ts";
import { measureStaticProp } from "../.agents/skills/designing-jftse-props/scripts/verify-glbs.ts";

function fixture(change: (doc: ReturnType<typeof document>) => void = () => {}, binaryChange?: (bin: Buffer) => void) {
  const doc = document(); change(doc);
  const text = JSON.stringify(doc);
  const json = Buffer.from(text.padEnd(Math.ceil(text.length / 4) * 4, " "));
  const bin = Buffer.alloc(36);
  [0, 0, 0, 1, 0, 0, 0, 1, 0].forEach((n, i) => bin.writeFloatLE(n, i * 4));
  binaryChange?.(bin);
  const header = Buffer.alloc(20);
  header.writeUInt32LE(0x46546c67, 0); header.writeUInt32LE(2, 4);
  header.writeUInt32LE(28 + json.length + bin.length, 8);
  header.writeUInt32LE(json.length, 12); header.writeUInt32LE(0x4e4f534a, 16);
  const bh = Buffer.alloc(8); bh.writeUInt32LE(bin.length); bh.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([header, json, bh, bin]);
}
function document() {
  return {
    asset: { version: "2.0" }, buffers: [{ byteLength: 36, uri: undefined as string | undefined }],
    bufferViews: [{ buffer: 0, byteLength: 36 }],
    accessors: [{ bufferView: 0, componentType: 5126, type: "VEC3", count: 3 }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0 }, mode: 4 }] }],
    nodes: [{ mesh: 0, children: [] as number[] }], scenes: [{ nodes: [0] }], scene: 0,
    animations: [] as object[], extensions: {} as Record<string, object>,
  };
}
const importedLayout = () => parseTwinkleDocument({ version: 1, mapId: "oktoberfest", name: "Import test", sourceHash: "a".repeat(64), objects: [{
  id: "import-test", name: "Cart", file: `Studio/Imported/${"b".repeat(64)}.glb`, position: [150, 0, 20], rotation: 90, scale: 20, visible: true, level: 1,
}] });

describe("bounded Blender prop import", () => {
  test("reads default-scene geometry counts", () => {
    expect(inspectStaticGlb(fixture())).toEqual({ vertices: 3, triangles: 1, submeshes: 1 });
  });
  test("rejects truncated, oversized and invalid containers", () => {
    const raw = fixture();
    for (const length of [0, 12, 19, 27, raw.length - 1]) expect(() => inspectStaticGlb(raw.subarray(0, length))).toThrow();
    expect(() => inspectStaticGlb(new Uint8Array(MAX_GLB_BYTES + 1))).toThrow();
    raw.writeUInt32LE(1, 4); expect(() => inspectStaticGlb(raw)).toThrow();
  });
  test("rejects external files, animations and extensions before loading", () => {
    for (const uri of ["https://example.com/private.png", "../../secret", "data:image/png;base64,AAAA"]) {
      expect(() => inspectStaticGlb(fixture((d) => { d.buffers[0]!.uri = uri; }))).toThrow("URIs");
    }
    expect(() => inspectStaticGlb(fixture((d) => { d.animations.push({}); }))).toThrow("static props");
    expect(() => inspectStaticGlb(fixture((d) => { d.extensions.KHR_lights_punctual = {}; }))).toThrow("extension");
  });
  test("rejects unsafe geometry and scene trees", () => {
    expect(() => inspectStaticGlb(fixture((d) => { d.accessors[0]!.count = 100; }))).toThrow();
    expect(() => inspectStaticGlb(fixture((d) => { d.nodes[0]!.children = [0]; }))).toThrow("acyclic");
    expect(() => inspectStaticGlb(fixture((d) => { d.nodes[0]!.mesh = 99; }))).toThrow();
    expect(() => inspectStaticGlb(fixture((d) => { d.meshes[0]!.primitives[0]!.mode = 0; }))).toThrow("triangle");
    expect(() => inspectStaticGlb(fixture(undefined, (bin) => bin.writeFloatLE(NaN)))).toThrow("Nonfinite");
  });
  test("layout preserves imported identity and transform, rejecting path escapes", () => {
    const doc = importedLayout();
    expect(parseTwinkleDocument(JSON.parse(JSON.stringify(doc)))).toEqual(doc);
    for (const file of ["Studio/Imported/cart.glb", "Studio/Imported/../secret.glb", `Studio/Imported/${"b".repeat(64)}.dat`]) {
      expect(() => parseTwinkleDocument({ ...doc, objects: [{ ...doc.objects[0], file }] })).toThrow();
    }
  });
  test("native export and install fail closed, including invisible imports", async () => {
    const doc = importedLayout();
    expect(() => rejectImportedNativeExport(doc)).toThrow("Studio-only");
    doc.objects[0]!.visible = false;
    expect(() => rejectImportedNativeExport(doc)).toThrow("Studio-only");
    for (const handler of [twinkleExport, twinkleClient]) {
      const result = await handler(new Request("http://localhost/api/twinkle/client?action=install", { method: "POST", body: JSON.stringify(doc) }));
      expect(result.status).toBe(400);
      expect((await result.json()).error).toContain("Studio-only");
    }
  });
  test("asset serving does not accept paths or arbitrary files", async () => {
    for (const name of ["import-../../secret.glb", "beer-cart.blend", "import-file.glb"]) {
      expect((await twinkleFile(new Request(`http://localhost/api/twinkle/file?name=${encodeURIComponent(name)}`))).status).toBe(400);
    }
  });
  test("skill verification measures transformed geometry rather than untrusted bounds metadata", () => {
    const report = measureStaticProp(fixture((doc) => {
      Object.assign(doc.nodes[0]!, { translation: [5, 2, -3], scale: [2, 3, 1] });
      Object.assign(doc.accessors[0]!, { min: [-999, -999, -999], max: [999, 999, 999] });
    }));
    expect(report.bounds).toEqual({ min: [5, 2, -3], max: [7, 5, -3], size: [2, 3, 0] });
    expect(report.triangles).toBe(1);
    expect(report.sha256).toHaveLength(64);
  });
  test("skill verification rejects named preview objects", () => {
    expect(() => measureStaticProp(fixture((doc) => {
      Object.assign(doc.nodes[0]!, { name: "PREVIEW_Floor" });
    }))).toThrow("Preview objects");
  });
});
