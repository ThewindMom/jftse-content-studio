import { mkdirSync, renameSync, rmSync } from "node:fs";
import { join } from "node:path";
import { config } from "./config.ts";
import { BridgeError, runBridge, runBridgeWithPayload } from "./bridge.ts";
import { readJsonObject } from "./requestPolicy.ts";
import { isImportedModel, parseMapDesign, parseTwinkleDocument, type MapDesign } from "../web/twinkleDocument.ts";
import { importedProps, importedPropDirectory, rejectImportedNativeExport } from "./importedProps.ts";

const assets = join(config.tmpDir, "twinkle-assets");
const preparations = new Map<MapDesign, Promise<unknown>>();
const draftPath = (map: MapDesign) => join(config.exportsDir, `${map}-layout.json`);

export async function twinkleScene(req: Request): Promise<Response> {
  try {
    const map = parseMapDesign(new URL(req.url).searchParams.get("map"));
    let preparation = preparations.get(map);
    if (!preparation) {
      preparation = runBridge(["twinkle-prepare", "--out-dir", assets, "--map", map]).catch((error) => {
        preparations.delete(map);
        throw error;
      });
      preparations.set(map, preparation);
    }
    await preparation;
    const manifest = await Bun.file(join(assets, `manifest-${map}.json`)).json();
    manifest.assets.push(...await importedProps());
    return Response.json(manifest, {
      headers: { "content-type": "application/json", "cache-control": "private, no-store" },
    });
  } catch (error) {
    return Response.json({ error: `Cannot load stock Twinkle resources. ${String(error)}` }, { status: 503 });
  }
}

export async function twinkleFile(req: Request): Promise<Response> {
  const name = new URL(req.url).searchParams.get("name") ?? "";
  if (/^import-[a-f0-9]{64}\.glb$/.test(name)) {
    const file = Bun.file(join(importedPropDirectory, name.slice(7)));
    if (!await file.exists()) return new Response("Imported prop not found", { status: 404 });
    return new Response(file, { headers: { "content-type": "model/gltf-binary", "cache-control": "private, max-age=3600" } });
  }
  if (name === "oktoberfest-original-models.zip") {
    const file = Bun.file(join(assets, name));
    if (!await file.exists()) return new Response("Open a map first", { status: 404 });
    return new Response(file, { headers: { "content-type": "application/zip", "cache-control": "private, no-store",
      "content-disposition": 'attachment; filename="oktoberfest-original-models.zip"' } });
  }
  if (!/^[a-f0-9]{24}\.(json|png)$/.test(name)) return new Response("Invalid asset", { status: 400 });
  const file = Bun.file(join(assets, name));
  if (!await file.exists()) return new Response("Asset not prepared", { status: 404 });
  return new Response(file, { headers: { "cache-control": "private, max-age=3600" } });
}

export async function twinkleDraft(req: Request): Promise<Response> {
  try {
    const map = parseMapDesign(new URL(req.url).searchParams.get("map"));
    const draft = draftPath(map);
    if (req.method === "GET") {
      const file = Bun.file(draft);
      return Response.json(await file.exists() ? await file.json() : null, {
        headers: { "cache-control": "private, no-store" },
      });
    }
    const doc = parseTwinkleDocument(await readJsonObject(req, 256_000));
    if (parseMapDesign(doc.mapId) !== map) throw new Error("Layout belongs to another map design.");
    for (const obj of doc.objects) {
      if (isImportedModel(obj.file) && !await Bun.file(join(importedPropDirectory, obj.file.split("/").at(-1)!)).exists()) {
        throw new Error(`Import the missing Blender GLB before saving: ${obj.name}`);
      }
    }
    mkdirSync(config.exportsDir, { recursive: true });
    const temporary = `${draft}.${crypto.randomUUID()}.tmp`;
    try {
      await Bun.write(temporary, JSON.stringify(doc, null, 2));
      renameSync(temporary, draft);
    } finally {
      rmSync(temporary, { force: true });
    }
    return Response.json({ ok: true });
  } catch (error) {
    return Response.json({ error: String(error) }, { status: 400 });
  }
}

export async function twinkleExport(req: Request): Promise<Response> {
  const out = join(config.tmpDir, `twinkle-export-${crypto.randomUUID()}`);
  try {
    const doc = parseTwinkleDocument(await readJsonObject(req, 256_000));
    rejectImportedNativeExport(doc);
    await runBridgeWithPayload("twinkle-layout", doc, (payload) => [
      "twinkle-export", "--payload", payload, "--out-dir", out,
    ]);
    const bytes = await Bun.file(join(out, "twinkle-layout.zip")).arrayBuffer();
    return new Response(bytes, { headers: {
      "content-type": "application/zip", "cache-control": "private, no-store",
      "content-disposition": 'attachment; filename="twinkle-layout.zip"',
    } });
  } catch (error) {
    return Response.json({ error: String(error) }, { status: 400 });
  } finally {
    rmSync(out, { recursive: true, force: true });
  }
}

export async function twinkleClient(req: Request): Promise<Response> {
  try {
    const action = req.method === "GET" ? "status" : new URL(req.url).searchParams.get("action");
    if (action !== "status" && action !== "install" && action !== "restore") throw new Error("Invalid test-client action");
    const doc = action === "install" ? parseTwinkleDocument(await readJsonObject(req, 256_000)) : null;
    if (doc) rejectImportedNativeExport(doc);
    const result = doc
      ? await runBridgeWithPayload("twinkle-test-client", doc,
          (payload) => ["twinkle-client", "--action", "install", "--payload", payload])
      : await runBridge(["twinkle-client", "--action", action]);
    if (req.method === "GET" && new URL(req.url).searchParams.has("receipt")) {
      const receipt = result.receipt as { receiptPath?: string } | null;
      if (!receipt?.receiptPath) return new Response("No installation receipt", { status: 404 });
      return new Response(Bun.file(receipt.receiptPath), { headers: {
        "content-type": "application/json", "cache-control": "private, no-store",
        "content-disposition": 'attachment; filename="test-client-receipt.json"',
      } });
    }
    return Response.json(result, { headers: { "cache-control": "private, no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof BridgeError ? error.detail : String(error) }, { status: 400 });
  }
}
