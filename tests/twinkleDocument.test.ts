import { describe, expect, test } from "bun:test";
import { courtClearance, parseTwinkleDocument, type TwinkleDocument } from "../web/twinkleDocument.ts";

function layout(): TwinkleDocument {
  return { version: 1, name: "Twinkle test", sourceHash: "a".repeat(64), objects: [{
    id: "barrel-1", name: "Barrel", file: "Res/MapRes/DecoRes/Mesh00/P0_Barrel01_C01.dat",
    position: [90, 0, 20], rotation: 0, scale: 1, level: 0, visible: true,
  }] };
}
describe("Twinkle layout boundary", () => {
  test("round-trips real placement transforms", () => {
    const doc = layout();
    expect(parseTwinkleDocument(JSON.parse(JSON.stringify(doc)))).toEqual(doc);
  });
  test("accepts named original GLB models, not arbitrary portable paths", () => {
    const doc = layout();
    doc.objects[0]!.file = "Studio/Oktoberfest/Oktoberfest_FestivalArch.glb";
    expect(parseTwinkleDocument(doc)).toEqual(doc);
    for (const file of ["Studio/Oktoberfest/../../secret.glb", "Studio/Oktoberfest/Unknown.glb", "Studio/Oktoberfest/Oktoberfest_FestivalArch.dat"]) {
      expect(() => parseTwinkleDocument({ ...doc, objects: [{ ...doc.objects[0], file }] })).toThrow();
    }
  });
  test("rejects duplicate and reserved IDs, path escapes, and malformed vectors", () => {
    const doc = layout();
    const item = doc.objects[0]!;
    for (const changed of [
      { ...item, id: "fixed-0-0" }, { ...item, file: "../../secret.dat" },
      { ...item, position: [0, 0] }, { ...item, position: [0, Infinity, 0] },
      { ...item, scale: 0 }, { ...item, scale: 101 }, { ...item, level: 1.5 },
      { ...item, rotation: NaN }, { ...item, visible: "yes" }, { ...item, name: "" },
    ]) expect(() => parseTwinkleDocument({ ...doc, objects: [changed] })).toThrow();
    expect(() => parseTwinkleDocument({ ...doc, objects: [item, item] })).toThrow();
    expect(() => parseTwinkleDocument({ ...doc, objects: Array(501).fill(item) })).toThrow();
    expect(() => parseTwinkleDocument({ ...doc, sourceHash: "old" })).toThrow();
  });
  test("clearance is a placement warning, respecting excluded objects", () => {
    const object = layout().objects[0]!;
    expect(courtClearance(object)).toBe(false);
    expect(courtClearance({ ...object, position: [0, 0, 0] })).toBe(true);
    expect(courtClearance({ ...object, position: [0, 0, 0], visible: false })).toBe(false);
  });
  test("map designs and animation metadata survive round trip", () => {
    const doc = { ...layout(), mapId: "oktoberfest", objects: [{ ...layout().objects[0]!, animation: 0, phase: -1 }] } satisfies TwinkleDocument;
    expect(parseTwinkleDocument(doc)).toEqual(doc);
    expect(() => parseTwinkleDocument({ ...doc, mapId: "../stock" })).toThrow();
    expect(() => parseTwinkleDocument({ ...doc, objects: [{ ...doc.objects[0], animation: 0.5 }] })).toThrow();
    expect(() => parseTwinkleDocument({ ...doc, objects: [{ ...doc.objects[0], phase: Infinity }] })).toThrow();
  });
});
