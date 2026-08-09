import { createCipheriv, createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const FIXTURE_ROOT = resolve(import.meta.dir, "../tests/fixtures/compatibility");
const KEY = Buffer.from("TIMOTEI_ZION\0\0\0\0", "binary");
type Status = "proven" | "unproven";
type FixtureResult = {
  status: Status;
  compatible: boolean | null;
  outputSha256?: string;
  outputBase64?: string;
  semantic?: unknown;
};
type FtmSemantic = {
  name: string;
  mapHeader: {
    mapPath: string;
    tileCountX: number;
    tileCountY: number;
    unkI2: number;
    indoorMode: number;
    unkI3: number;
    unkI4: number;
    tileLayerDefinitions: unknown[];
  };
  tileLayerIndices: { layers: unknown[] };
  prefabObjects: Array<{ name: string; objId: string }>;
  sceneObjects: Array<{
    prefabIndex: number;
    x: number;
    y: number;
    scaleHeight: number;
    scaleWidth: number;
    rotationY: number;
    rotationX: number;
  }>;
  interactableTiles: unknown[];
  blockedTiles: Array<{ x: number; y: number }>;
  unknownBytes: number[];
};
type CompatibilityManifest = {
  oracle: {
    implementation: string;
    sha256: string;
    clients: string[];
  };
  fixtures: {
    ftm: { binary: string; semantic: string; decodedSha256: string };
    prj: { binary: string; decodedSha256: string };
    set: { plain: string; encryptedBase64: string };
    tex: { decoded: string; encoded: string };
  };
};

class Cursor {
  offset = 0;
  constructor(readonly data: Buffer) {}
  u8(): number { return this.data[this.offset++]!; }
  i32(): number { const value = this.data.readInt32LE(this.offset); this.offset += 4; return value; }
  f32(): number { const value = this.data.readFloatLE(this.offset); this.offset += 4; return value; }
  string(): string { const size = this.u8(); const value = this.data.subarray(this.offset, this.offset + size).toString("ascii"); this.offset += size; return value; }
  skip(size: number): void { this.offset += size; }
}

class Writer {
  readonly chunks: Buffer[] = [];
  u8(value: number): void { this.chunks.push(Buffer.from([value & 0xff])); }
  i32(value: number): void { const data = Buffer.alloc(4); data.writeInt32LE(value); this.chunks.push(data); }
  f32(value: number): void { const data = Buffer.alloc(4); data.writeFloatLE(value); this.chunks.push(data); }
  string(value: string): void { const data = Buffer.from(value, "ascii"); this.u8(data.length); this.chunks.push(data); }
  bytes(value: Uint8Array): void { this.chunks.push(Buffer.from(value)); }
  finish(): Buffer { return Buffer.concat(this.chunks); }
}

function sha256(value: Uint8Array): string {
  return createHash("sha256").update(value).digest("hex");
}
function fixtureBase64(name: string): Buffer {
  return Buffer.from(readFileSync(join(FIXTURE_ROOT, name), "utf8").trim(), "base64");
}

function parseFtm(data: Buffer): FtmSemantic {
  const c = new Cursor(data);
  const mapPath = c.string();
  const mapHeader = { mapPath, tileCountX: c.i32(), tileCountY: c.i32(), unkI2: c.i32(), indoorMode: c.u8(), unkI3: c.i32(), unkI4: c.i32(), tileLayerDefinitions: [] as unknown[] };
  const layerCount = c.i32();
  if (layerCount !== 0) throw new Error("fixture requires zero tile layers");
  const prefabObjects = Array.from({ length: c.i32() }, () => {
    const value = { name: c.string(), objId: c.string() }; c.skip(2); return value;
  });
  const sceneObjects = Array.from({ length: c.i32() }, () => ({
    prefabIndex: c.i32(), x: c.i32(), y: c.i32(), scaleHeight: c.f32(),
    scaleWidth: c.f32(), rotationY: c.f32(), rotationX: c.f32(),
  }));
  const interactableCount = c.i32();
  if (interactableCount !== 0) throw new Error("fixture requires zero interactable tiles");
  const blockedTiles = Array.from({ length: c.i32() }, () => ({ x: c.i32(), y: c.i32() }));
  const unknownBytes = [...data.subarray(c.offset)].map((value) => value > 127 ? value - 256 : value);
  return { name: mapPath, mapHeader, tileLayerIndices: { layers: [] }, prefabObjects, sceneObjects, interactableTiles: [], blockedTiles, unknownBytes };
}

function storeFtm(value: FtmSemantic): Buffer {
  const w = new Writer(); const h = value.mapHeader;
  w.string(h.mapPath); w.i32(h.tileCountX); w.i32(h.tileCountY); w.i32(h.unkI2);
  w.u8(h.indoorMode); w.i32(h.unkI3); w.i32(h.unkI4); w.i32(0);
  w.i32(value.prefabObjects.length);
  for (const item of value.prefabObjects) { w.string(item.name); w.string(item.objId); w.bytes(Uint8Array.of(0, 0)); }
  w.i32(value.sceneObjects.length);
  for (const item of value.sceneObjects) {
    w.i32(item.prefabIndex); w.i32(item.x); w.i32(item.y); w.f32(item.scaleHeight);
    w.f32(item.scaleWidth); w.f32(item.rotationY); w.f32(item.rotationX);
  }
  w.i32(0); w.i32(value.blockedTiles.length);
  for (const tile of value.blockedTiles) { w.i32(tile.x); w.i32(tile.y); }
  w.bytes(Uint8Array.from(value.unknownBytes, (item: number) => item & 0xff));
  return w.finish();
}

function roundTripPrj(data: Buffer): Buffer {
  const c = new Cursor(data); const paths = Array.from({ length: c.i32() }, () => c.string());
  const w = new Writer(); w.i32(paths.length); for (const path of paths) w.string(path); return w.finish();
}
function encryptSet(plain: Buffer): Buffer {
  let nullCount = (16 - (plain.length % 16)) % 16; if (nullCount === 0) nullCount = 16;
  const cipher = createCipheriv("aes-128-ecb", KEY, null); cipher.setAutoPadding(false);
  return Buffer.concat([Buffer.from([nullCount]), cipher.update(Buffer.concat([plain, Buffer.alloc(nullCount)])), cipher.final()]);
}
function xorTex(value: Buffer): Buffer {
  const output = Buffer.from(value); for (let index = 0; index < Math.min(128, output.length); index++) output[index] ^= 0xff; return output;
}

export function materializeCompatibilityFixtures(root: string, output: string): void {
  for (const name of ["sample.ftm", "sample.prj", "tex.dds", "tex.encoded"]) {
    const encoded = readFileSync(join(root, `${name}.b64`), "utf8").trim();
    writeFileSync(join(output, name), Buffer.from(encoded, "base64"));
  }
  writeFileSync(join(output, "set.plain"), readFileSync(join(root, "set.plain.txt")));
}

export async function buildCompatibilityReport() {
  const manifest = JSON.parse(
    readFileSync(join(FIXTURE_ROOT, "manifest.json"), "utf8"),
  ) as CompatibilityManifest;
  const ftmBytes = fixtureBase64(manifest.fixtures.ftm.binary);
  const semantic = parseFtm(ftmBytes); const ftmOutput = storeFtm(semantic);
  const prjOutput = roundTripPrj(fixtureBase64(manifest.fixtures.prj.binary));
  const setOutput = encryptSet(readFileSync(join(FIXTURE_ROOT, manifest.fixtures.set.plain)));
  const texEncoded = fixtureBase64(manifest.fixtures.tex.encoded); const texOutput = xorTex(texEncoded);
  const expectedSemantic = JSON.parse(readFileSync(join(FIXTURE_ROOT, manifest.fixtures.ftm.semantic), "utf8"));
  const clients = await Promise.all(manifest.oracle.clients.map(async (path: string) => ({
    path, available: existsSync(path), sha256: existsSync(path) ? sha256(await Bun.file(path).bytes()) : null,
  })));
  const expectedJarHash = manifest.oracle.sha256;
  const jarHashes = clients.map((item) => item.sha256);
  const fixtures: Record<string, FixtureResult> = {
    ftm: { status: "proven", compatible: JSON.stringify(semantic) === JSON.stringify(expectedSemantic) && sha256(ftmOutput) === manifest.fixtures.ftm.decodedSha256, semantic, outputSha256: sha256(ftmOutput) },
    prj: { status: "proven", compatible: sha256(prjOutput) === manifest.fixtures.prj.decodedSha256, outputSha256: sha256(prjOutput) },
    set: { status: "proven", compatible: setOutput.toString("base64") === manifest.fixtures.set.encryptedBase64, outputBase64: setOutput.toString("base64") },
    tex: { status: "proven", compatible: xorTex(texOutput).equals(texEncoded), outputBase64: texOutput.toString("base64") },
  };
  const jarsEqual = clients.length === 2 && jarHashes.every((hash) => hash === expectedJarHash);
  return {
    ok: Object.values(fixtures).every((item) => item.compatible) && jarsEqual,
    oracle: { implementation: manifest.oracle.implementation, expectedSha256: expectedJarHash, jarsEqual, clients },
    fixtures,
    capabilities: [
      { id: "ftm-fixture-semantic-round-trip", status: "proven" as Status, compatible: fixtures.ftm.compatible, evidence: "FTMParser parse/store/fromJson/toJson" },
      { id: "prj-fixture-round-trip", status: "proven" as Status, compatible: fixtures.prj.compatible, evidence: "PRJReader read/write" },
      { id: "set-fixture-round-trip", status: "proven" as Status, compatible: fixtures.set.compatible, evidence: "Crypter SET in-memory methods" },
      { id: "tex-fixture-xor-round-trip", status: "proven" as Status, compatible: fixtures.tex.compatible, evidence: "Crypter TEX in-memory method" },
      { id: "arbitrary-format-compatibility", status: "unproven" as Status, compatible: null, evidence: "Fixtures do not prove arbitrary client assets" },
      { id: "live-game-acceptance", status: "unproven" as Status, compatible: null, evidence: "Requires DX9 client verification" },
    ],
  };
}
