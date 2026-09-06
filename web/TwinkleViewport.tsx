import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { TransformControls } from "three/examples/jsm/controls/TransformControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { isOriginalModel, type Placement, type StudioAsset, type TwinkleDocument } from "./twinkleDocument.ts";

type MeshPart = {
  positions: number[]; normals: number[]; uvs: number[]; uv1: number[]; indices: number[];
  colors?: number[];
  name: string; slot: number; albedo: string | null; lightmap: string | null;
};
export type CameraView = "court" | "overview" | "top" | "player" | "selection";
type Props = {
  assets: StudioAsset[]; document: TwinkleDocument; selected: string;
  mode: "translate" | "rotate"; snap: number; guides: boolean; lightmaps: boolean; isolate: boolean;
  camera: { view: CameraView; revision: number };
  onSelect: (id: string) => void;
  onTransform: (id: string, patch: Partial<Placement>) => void;
  onThumbnails: (thumbnails: Record<string, string>) => void;
};
export const assetUrl = (name: string) => `/api/twinkle/file?name=${encodeURIComponent(name)}`;

type Runtime = {
  sync: (props: Props) => void;
  view: (view: CameraView, selected: string) => void;
};

export function TwinkleViewport(props: Props) {
  const mount = useRef<HTMLDivElement>(null);
  const runtime = useRef<Runtime | null>(null);
  const latest = useRef(props);
  latest.current = props;
  const [status, setStatus] = useState("Loading stock geometry and materials…");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const host = mount.current;
    if (!host) return;
    let disposed = false;
    const abort = new AbortController();
    const resources = new Set<{ dispose(): void }>();
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    } catch {
      setFailed(true);
      setStatus("WebGL is unavailable. Enable hardware acceleration, then reload this page.");
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.setAttribute("aria-label", "Twinkle Town 3D map viewport");
    renderer.domElement.tabIndex = 0;
    host.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#98baca");
    function previewLighting(target: THREE.Scene) {
      target.add(new THREE.HemisphereLight(0xfff5df, 0x697781, 2));
      const key = new THREE.DirectionalLight(0xffe4bb, 2.5);
      key.position.set(-120, 250, 180);
      target.add(key);
    }
    previewLighting(scene);
    const camera = new THREE.PerspectiveCamera(45, 1, 0.5, 10000);
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    orbit.maxDistance = 5000;
    orbit.minDistance = 3;
    orbit.maxPolarAngle = Math.PI * 0.49;
    const gizmo = new TransformControls(camera, renderer.domElement);
    gizmo.setSize(0.8);
    scene.add(gizmo.getHelper());
    const world = new THREE.Group();
    world.scale.z = -1; // The source stage uses a left-handed coordinate system.
    scene.add(world);
    const templates = new Map<string, THREE.Group>();
    const objects = new Map<string, THREE.Group>();
    const lights = new Map<THREE.MeshBasicMaterial, THREE.Texture | null>();
    const selection = new THREE.Box3Helper(new THREE.Box3(), 0xffcd70);
    selection.visible = false;
    resources.add(selection.geometry);
    if (Array.isArray(selection.material)) selection.material.forEach((m) => resources.add(m));
    else resources.add(selection.material);
    scene.add(selection);
    const overlays = new THREE.Group();
    world.add(overlays);
    const line = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-70, 0.8, -130), new THREE.Vector3(70, 0.8, -130),
      new THREE.Vector3(70, 0.8, 130), new THREE.Vector3(-70, 0.8, 130), new THREE.Vector3(-70, 0.8, -130),
    ]);
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0xffcc66, depthTest: false });
    resources.add(line); resources.add(lineMaterial);
    overlays.add(new THREE.Line(line, lineMaterial));
    const grid = new THREE.GridHelper(600, 60, 0x718ea0, 0x718ea0);
    grid.position.y = -0.8;
    grid.material.transparent = true;
    grid.material.opacity = 0.2;
    overlays.add(grid);
    resources.add(grid.geometry); resources.add(grid.material);
    const placeholderGeometry = new THREE.OctahedronGeometry(3);
    const placeholderMaterial = new THREE.MeshBasicMaterial({ color: 0xebad6c, wireframe: true });
    resources.add(placeholderGeometry); resources.add(placeholderMaterial);

    function selectedBox(id: string) {
      const obj = objects.get(id);
      if (!obj || !obj.visible) { selection.visible = false; return; }
      obj.updateWorldMatrix(true, true);
      selection.box.setFromObject(obj);
      selection.visible = true;
    }
    function sync(p: Props) {
      const wanted = new Set(p.document.objects.map((o) => o.id));
      for (const [id, group] of objects) {
        if (!id.startsWith("fixed-") && !wanted.has(id)) { world.remove(group); objects.delete(id); }
      }
      for (const placement of p.document.objects) {
        let group = objects.get(placement.id);
        if (group && group.userData.file !== placement.file) {
          world.remove(group); objects.delete(placement.id); group = undefined;
        }
        if (!group) {
          group = templates.get(placement.file)?.clone(true) ?? new THREE.Group();
          if (!templates.has(placement.file)) {
            const marker = new THREE.Mesh(placeholderGeometry, placeholderMaterial);
            marker.position.y = 4;
            group.add(marker);
          }
          group.userData.file = placement.file;
          group.traverse((node) => { node.userData.placementId = placement.id; });
          objects.set(placement.id, group);
          world.add(group);
        }
        group.position.fromArray(placement.position);
        group.rotation.set(0, THREE.MathUtils.degToRad(placement.rotation), 0);
        group.scale.setScalar(templates.has(placement.file) ? placement.scale : 1);
        group.visible = placement.visible && (templates.has(placement.file) || p.guides || placement.id === p.selected);
        group.traverse((node) => { if (node.userData.collisionProxy) node.visible = p.guides; });
      }
      const isolated = p.isolate && objects.has(p.selected);
      for (const [id, group] of objects) {
        if (id.startsWith("fixed-")) group.visible = !isolated || id === p.selected;
        else if (isolated && id !== p.selected) group.visible = false;
      }
      overlays.visible = p.guides && !isolated;
      for (const [material, baked] of lights) {
        const next = p.lightmaps ? baked : null;
        if (material.lightMap !== next) { material.lightMap = next; material.needsUpdate = true; }
      }
      const target = objects.get(p.selected);
      if (target && wanted.has(p.selected) && target.visible) {
        gizmo.attach(target);
        gizmo.setMode(p.mode);
        gizmo.showX = p.mode === "translate";
        gizmo.showZ = p.mode === "translate";
        gizmo.setTranslationSnap(p.snap || null);
        gizmo.setRotationSnap(p.snap ? THREE.MathUtils.degToRad(15) : null);
      } else gizmo.detach();
      selectedBox(p.selected);
    }
    function view(preset: CameraView, id: string) {
      if (preset === "selection") {
        const obj = objects.get(id);
        if (!obj) return;
        const box = new THREE.Box3().setFromObject(obj);
        const center = box.getCenter(new THREE.Vector3());
        const size = Math.max(box.getSize(new THREE.Vector3()).length(), 16);
        orbit.target.copy(center);
        camera.position.copy(center).add(new THREE.Vector3(size * 0.8, size * 0.7, size * (isOriginalModel(obj.userData.file ?? "") ? -0.9 : 0.9)));
      } else {
        const presets: Record<Exclude<CameraView, "selection">, [number[], number[]]> = {
          court: [[290, 310, 390], [0, 0, 0]],
          overview: [[1500, 1550, 1750], [100, 80, -250]],
          top: [[0, 650, 0.01], [0, 0, 0]],
          player: [[0, 165, 300], [0, 0, -20]],
        };
        camera.position.fromArray(presets[preset][0]);
        orbit.target.fromArray(presets[preset][1]);
      }
      camera.lookAt(orbit.target);
      orbit.update();
    }
    gizmo.addEventListener("dragging-changed", (event) => { orbit.enabled = !event.value; });
    gizmo.addEventListener("objectChange", () => selectedBox(latest.current.selected));
    gizmo.addEventListener("mouseUp", () => {
      const target = gizmo.object;
      if (!target) return;
      latest.current.onTransform(latest.current.selected, {
        position: [target.position.x, target.position.y, target.position.z],
        rotation: THREE.MathUtils.radToDeg(target.rotation.y),
      });
    });
    let downX = 0, downY = 0, gizmoClick = false;
    function pointerDown(event: PointerEvent) {
      downX = event.clientX; downY = event.clientY; gizmoClick = gizmo.axis !== null;
    }
    function pointerUp(event: PointerEvent) {
      if (event.button !== 0 || gizmoClick || Math.hypot(event.clientX - downX, event.clientY - downY) > 4) return;
      const rect = renderer.domElement.getBoundingClientRect();
      const ray = new THREE.Raycaster();
      ray.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1), camera);
      const hits = ray.intersectObjects([...objects.values()].filter((group) => group.visible), true);
      const first = hits.find((hit) => !hit.object.userData.collisionProxy && typeof hit.object.userData.placementId === "string");
      latest.current.onSelect(first?.object.userData.placementId ?? "");
    }
    renderer.domElement.addEventListener("pointerdown", pointerDown);
    renderer.domElement.addEventListener("pointerup", pointerUp);
    const resize = new ResizeObserver(() => {
      const width = host.clientWidth, height = host.clientHeight;
      renderer.setSize(width, height);
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
    });
    resize.observe(host);
    renderer.setAnimationLoop(() => { orbit.update(); renderer.render(scene, camera); });
    view("court", "");
    const texturePromises = new Map<string, Promise<THREE.Texture>>();
    const loader = new THREE.TextureLoader();
    function texture(name: string, lightmap: boolean) {
      const key = `${name}:${lightmap}`;
      let promise = texturePromises.get(key);
      if (!promise) {
        promise = loader.loadAsync(assetUrl(name)).then((map) => {
          if (disposed) { map.dispose(); throw new Error("Viewport closed"); }
          resources.add(map);
          map.flipY = false;
          map.colorSpace = lightmap ? THREE.LinearSRGBColorSpace : THREE.SRGBColorSpace;
          map.wrapS = map.wrapT = THREE.RepeatWrapping;
          map.channel = lightmap ? 1 : 0;
          map.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
          return map;
        });
        texturePromises.set(key, promise);
      }
      return promise;
    }
    void (async () => {
      try {
        await Promise.all(props.assets.map(async (asset, assetIndex) => {
          const response = await fetch(assetUrl(asset.geometry), { signal: abort.signal });
          if (!response.ok) throw new Error(`Cannot load ${asset.name}`);
          if (asset.category === "imported") {
            const gltf = await new GLTFLoader().parseAsync(await response.arrayBuffer(), "");
            gltf.scene.traverse((node) => {
              if (!(node instanceof THREE.Mesh)) return;
              const owned = new Set<{ dispose(): void }>([node.geometry]);
              const materials = Array.isArray(node.material) ? node.material : [node.material];
              for (const material of materials) {
                owned.add(material);
                for (const value of Object.values(material)) if (value instanceof THREE.Texture) owned.add(value);
              }
              owned.forEach((resource) => disposed ? resource.dispose() : resources.add(resource));
            });
            if (disposed) return;
            const group = new THREE.Group();
            // glTF is right-handed Y-up; cancel the stock world's Z reflection.
            gltf.scene.scale.z *= -1;
            group.add(gltf.scene);
            templates.set(asset.file, group);
            return;
          }
          const parts: MeshPart[] = await response.json();
          const group = new THREE.Group();
          await Promise.all(parts.map(async (part) => {
            const [albedo, lightmap] = await Promise.all([
              part.albedo ? texture(part.albedo, false) : null,
              part.lightmap ? texture(part.lightmap, true) : null,
            ]);
            if (disposed) return;
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute("position", new THREE.Float32BufferAttribute(part.positions, 3));
            geometry.setAttribute("normal", new THREE.Float32BufferAttribute(part.normals, 3));
            geometry.setAttribute("uv", new THREE.Float32BufferAttribute(part.uvs, 2));
            if (part.uv1.length) geometry.setAttribute("uv1", new THREE.Float32BufferAttribute(part.uv1, 2));
            if (part.colors) geometry.setAttribute("color", new THREE.Float32BufferAttribute(part.colors, 3));
            geometry.setIndex(part.indices);
            const material = new THREE.MeshBasicMaterial({ map: albedo, lightMap: lightmap, lightMapIntensity: 2,
              vertexColors: !!part.colors,
              color: albedo ? 0xffffff : 0xc9a4d9, side: THREE.DoubleSide, alphaTest: 0.4 });
            lights.set(material, lightmap); resources.add(geometry); resources.add(material);
            const mesh = new THREE.Mesh(geometry, material);
            mesh.name = part.name;
            if (asset.fixed) {
              const id = `fixed-${assetIndex}-${part.slot}`;
              let slot = objects.get(id);
              if (!slot) { slot = new THREE.Group(); objects.set(id, slot); world.add(slot); }
              mesh.userData.placementId = id;
              slot.name = part.name;
              slot.add(mesh);
            } else group.add(mesh);
          }));
          for (const box of asset.collisionBoxes ?? []) {
            const solid = new THREE.BoxGeometry(...box.size);
            const edges = new THREE.EdgesGeometry(solid);
            solid.dispose();
            const material = new THREE.LineBasicMaterial({ color: 0x68f4cb, depthTest: false });
            const proxy = new THREE.LineSegments(edges, material);
            proxy.position.fromArray(box.center);
            proxy.userData.collisionProxy = true;
            proxy.visible = false;
            group.add(proxy);
            resources.add(edges); resources.add(material);
          }
          if (!asset.fixed) templates.set(asset.file, group);
        }));
        if (disposed) return;
        // Render actual prop thumbnails with the same geometry and texture path.
        const thumbnails: Record<string, string> = {};
        const thumbRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        thumbRenderer.setSize(160, 120);
        thumbRenderer.outputColorSpace = THREE.SRGBColorSpace;
        for (const [file, model] of templates) {
          const thumbScene = new THREE.Scene();
          previewLighting(thumbScene);
          thumbScene.add(model.clone(true));
          const box = new THREE.Box3().setFromObject(model);
          const center = box.getCenter(new THREE.Vector3());
          const size = Math.max(box.getSize(new THREE.Vector3()).length(), 1);
          const cam = new THREE.PerspectiveCamera(40, 4 / 3, 0.01, size * 10);
          cam.position.copy(center).add(new THREE.Vector3(size, size * 0.65, size)); cam.lookAt(center);
          thumbRenderer.render(thumbScene, cam);
          thumbnails[file] = thumbRenderer.domElement.toDataURL();
        }
        thumbRenderer.dispose();
        latest.current.onThumbnails(thumbnails);
        runtime.current = { sync, view };
        sync(latest.current);
        setStatus(`${props.assets.filter((a) => a.fixed).reduce((n, a) => n + a.submeshes, 0)} static submeshes · ${templates.size} placeable props · materials loaded`);
        host.dataset.ready = "true";
      } catch (error) {
        if (!disposed) { setFailed(true); setStatus(String(error)); }
      }
    })();
    return () => {
      disposed = true; abort.abort(); runtime.current = null;
      resize.disconnect(); renderer.setAnimationLoop(null); orbit.dispose(); gizmo.dispose();
      renderer.domElement.removeEventListener("pointerdown", pointerDown);
      renderer.domElement.removeEventListener("pointerup", pointerUp);
      resources.forEach((resource) => resource.dispose());
      renderer.dispose(); renderer.domElement.remove();
    };
  }, [props.assets]);
  useEffect(() => { runtime.current?.sync(props); }, [props.document, props.selected, props.mode, props.snap, props.guides, props.lightmaps, props.isolate]);
  useEffect(() => { runtime.current?.view(props.camera.view, props.selected); }, [props.camera]);
  return <div className="tw-viewport-wrap">
    <div className="tw-viewport" ref={mount} />
    <div className={`tw-render-status ${failed ? "tw-error" : ""}`} role={failed ? "alert" : "status"}>{status}</div>
    <div className="tw-view-hint">Drag to orbit · Right-drag to pan · Scroll to zoom · F to frame selection</div>
  </div>;
}
