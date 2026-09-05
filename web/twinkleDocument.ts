export type Point3 = [number, number, number];
export type MapDesign = "twinkle" | "oktoberfest";
export function parseMapDesign(value: unknown): MapDesign {
  if (value === undefined || value === null || value === "twinkle") return "twinkle";
  if (value === "oktoberfest") return value;
  throw new Error("Unknown map design.");
}
export type Placement = {
  id: string;
  name: string;
  file: string;
  position: Point3;
  rotation: number;
  scale: number;
  level: number;
  visible: boolean;
  animation?: number;
  phase?: number;
};
export type TwinkleDocument = {
  version: 1;
  mapId?: MapDesign;
  name: string;
  sourceHash: string;
  objects: Placement[];
};
export type StudioAsset = {
  file: string;
  name: string;
  fixed: boolean;
  geometry: string;
  vertices: number;
  triangles: number;
  submeshes: number;
  thumbnail: string | null;
  category: "world" | "scenery" | "stock" | "festival" | "original";
  pose: "static" | "bind";
  collisionBoxes?: { center: Point3; size: Point3 }[];
};
export type TwinkleManifest = {
  assets: StudioAsset[];
  document: TwinkleDocument;
  warnings: string[];
};

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Expected a layout object.");
  return Object.fromEntries(Object.entries(value));
}
function text(value: unknown, max: number): string {
  if (typeof value !== "string" || !value.trim() || value.length > max || /[\x00-\x1f]/.test(value)) {
    throw new Error("Invalid layout text.");
  }
  return value;
}
function numeric(value: unknown, min: number, max: number): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max) {
    throw new Error(`Transform must be between ${min} and ${max}.`);
  }
  return value;
}
export function parseTwinkleDocument(value: unknown): TwinkleDocument {
  const doc = object(value);
  if (doc.version !== 1 || !Array.isArray(doc.objects) || doc.objects.length > 500) {
    throw new Error("Unsupported layout version or too many objects (maximum 500).");
  }
  const sourceHash = text(doc.sourceHash, 64);
  if (!/^[a-f0-9]{64}$/.test(sourceHash)) throw new Error("Invalid stock fingerprint.");
  const ids = new Set<string>();
  const objects = doc.objects.map((raw): Placement => {
    const entry = object(raw);
    const id = text(entry.id, 80);
    if (!/^[a-zA-Z0-9-]+$/.test(id) || id.startsWith("fixed-") || ids.has(id)) throw new Error("Duplicate or invalid object ID.");
    ids.add(id);
    const file = text(entry.file, 200);
    if (!/^Res\/(?:[A-Za-z0-9_]+\/)+[A-Za-z0-9_]+\.dat$/.test(file) && !isOriginalModel(file)) throw new Error("Invalid asset path.");
    if (!Array.isArray(entry.position) || entry.position.length !== 3 || typeof entry.visible !== "boolean") {
      throw new Error("Invalid position or visibility.");
    }
    const level = numeric(entry.level, 0, 2);
    if (!Number.isInteger(level)) throw new Error("Level must be 0, 1 or 2.");
    const animation = entry.animation === undefined ? undefined : numeric(entry.animation, -1, 127);
    if (animation !== undefined && !Number.isInteger(animation)) throw new Error("Animation index must be an integer.");
    return {
      id, name: text(entry.name, 80), file,
      position: [numeric(entry.position[0], -10000, 10000), numeric(entry.position[1], -10000, 10000), numeric(entry.position[2], -10000, 10000)],
      rotation: numeric(entry.rotation, -36000, 36000), scale: numeric(entry.scale, 0.01, 100),
      level, visible: entry.visible,
      ...(animation === undefined ? {} : { animation, phase: numeric(entry.phase ?? 0, -1, 100000) }),
    };
  });
  const mapId = parseMapDesign(doc.mapId);
  return { version: 1, ...(doc.mapId === undefined ? {} : { mapId }), name: text(doc.name, 100), sourceHash, objects };
}

export function courtClearance(placement: Placement): boolean {
  return placement.visible && Math.abs(placement.position[0]) < 70 && Math.abs(placement.position[2]) < 130;
}

export function isOriginalModel(file: string): boolean {
  return /^Studio\/Oktoberfest\/Oktoberfest_(BrewersPavilion|PretzelStand|GingerbreadStand|FoodStand|BeerGarden|FestivalArch|Festzelt|Maypole|BarrelWagon|Bandstand)\.glb$/.test(file);
}

export function assetLabel(file: string): string {
  if (isOriginalModel(file)) return file.split("/").at(-1)!.replace("Oktoberfest_", "").replace(".glb", "").replace(/([a-z])([A-Z])/g, "$1 $2");
  const archive = file.split("/").at(-2);
  if (archive === "FestivalHall") return "Brewers’ pavilion";
  if (archive === "FestivalPretzel") return "Pretzel cart";
  if (archive === "FestivalHeart") return "Gingerbread cart";
  if (archive === "FestivalFood") return "Food cart";
  const member = file.split("/").at(-1) ?? file;
  const labels: Record<string, string> = {
    "P0_Barrel01_C01.dat": "Wooden barrel", "P0_Log00_B.dat": "Log seating",
    "P0_Flower00a.dat": "Flower bed · white", "P0_Flower00b.dat": "Flower bed · blue",
    "P0_Flower00c.dat": "Flower bed · yellow", "P0_Flower01.dat": "Tall flowers",
    "P0_Flower03d.dat": "Flower bed · violet", "P0_Leaf00_00.dat": "Leafy shrub",
  };
  return labels[member] ?? member.replace(/\.dat$/, "");
}
