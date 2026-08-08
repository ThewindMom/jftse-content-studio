import React, { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

async function api<T>(path: string): Promise<T> {
  const response = await fetch(path);
  const data = (await response.json()) as T & { error?: string; detail?: string };
  if (!response.ok) {
    throw new Error(data.error ?? data.detail ?? `HTTP ${response.status}`);
  }
  return data;
}

export function clientDatPathToRef(
  path: string,
): { archive: string; member: string } | null {
  const cleaned = path.replace(/\\/g, "/").trim().replace(/^"|"$/g, "");
  if (!cleaned.toLowerCase().endsWith(".dat")) return null;
  const parts = cleaned.split("/").filter(Boolean);
  if (parts.length < 2) return null;
  const member = parts[parts.length - 1]!;
  const parent = parts.slice(0, -1).join("/");
  return { archive: `${parent}.res`, member };
}

type MeshLayer = {
  readonly id: string;
  readonly role: "world" | "object" | "sky" | "collision";
  readonly label: string;
  readonly archive: string;
  readonly member: string;
  readonly level?: number | string | null;
};

type ParsedMesh = {
  mesh: {
    positions: number[][];
    indices: number[];
    uvs?: number[][];
    uvMode?: string;
    vertexCount: number;
    confidence?: { score: number };
  };
};

const MAX_DRAW_LAYERS = 6;

function layerKey(layer: MeshLayer): string {
  return `${layer.archive}::${layer.member}`;
}

/**
 * Stage multi-draw compositor.
 * Loads stage-scene when `stageScript` is set, otherwise falls back to a single WorldFile path.
 */
export function StageMeshPreview({
  worldPath,
  stageScript,
  onOpenMesh,
}: {
  worldPath?: string;
  stageScript?: string;
  onOpenMesh?: (archive: string, member: string) => void;
}) {
  const mountRef = React.useRef<HTMLDivElement | null>(null);
  const [info, setInfo] = useState("Loading stage geometry…");
  const [layers, setLayers] = useState<MeshLayer[]>([]);
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Resolve layer catalog from stage-scene or single world path
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setError("");
      setBusy(true);
      try {
        const next: MeshLayer[] = [];
        if (stageScript) {
          const body = await api<{
            ok?: boolean;
            scene?: {
              world?: { archive?: string; member?: string; sourcePath?: string };
              worldFile?: string;
              skyFile?: string;
              collision?: string;
              objects?: Array<{
                file?: string;
                level?: number | string;
                archive?: string;
                member?: string;
              }>;
              objectCount?: number;
              effectCount?: number;
            };
          }>(`/api/stage-scene?member=${encodeURIComponent(stageScript)}`);
          const scene = body.scene;
          if (!scene) throw new Error("Stage scene empty");
          if (scene.world?.archive && scene.world.member) {
            next.push({
              id: "world",
              role: "world",
              label: `World · ${scene.world.member}`,
              archive: scene.world.archive,
              member: scene.world.member,
            });
          } else if (scene.worldFile) {
            const ref = clientDatPathToRef(scene.worldFile);
            if (ref) {
              next.push({
                id: "world",
                role: "world",
                label: `World · ${ref.member}`,
                archive: ref.archive,
                member: ref.member,
              });
            }
          }
          (scene.objects ?? []).forEach((obj, i) => {
            const ref =
              obj.archive && obj.member
                ? { archive: obj.archive, member: obj.member }
                : clientDatPathToRef(obj.file ?? "");
            if (!ref) return;
            next.push({
              id: `object-${i}`,
              role: "object",
              label: `Object · ${ref.member}`,
              archive: ref.archive,
              member: ref.member,
              level: obj.level ?? null,
            });
          });
          // Sky/collision optional — off by default (often noisy / heavy)
          if (scene.skyFile) {
            const ref = clientDatPathToRef(scene.skyFile);
            if (ref) {
              next.push({
                id: "sky",
                role: "sky",
                label: `Sky · ${ref.member}`,
                archive: ref.archive,
                member: ref.member,
              });
            }
          }
          if (scene.collision) {
            const ref = clientDatPathToRef(scene.collision);
            if (ref) {
              next.push({
                id: "collision",
                role: "collision",
                label: `Collision · ${ref.member}`,
                archive: ref.archive,
                member: ref.member,
              });
            }
          }
          if (!cancelled) {
            setLayers(next);
            const vis: Record<string, boolean> = {};
            next.forEach((layer, idx) => {
              // Default on: world + first few objects; sky/collision off
              if (layer.role === "sky" || layer.role === "collision") {
                vis[layer.id] = false;
              } else {
                vis[layer.id] = idx < MAX_DRAW_LAYERS;
              }
            });
            setVisible(vis);
            setInfo(
              `${stageScript} · ${scene.objectCount ?? 0} objects · ${scene.effectCount ?? 0} effects · drawing up to ${MAX_DRAW_LAYERS} meshes`,
            );
          }
        } else if (worldPath) {
          const ref = clientDatPathToRef(worldPath);
          if (!ref) throw new Error("Could not map stage path to mesh archive");
          const layer: MeshLayer = {
            id: "world",
            role: "world",
            label: `World · ${ref.member}`,
            archive: ref.archive,
            member: ref.member,
          };
          if (!cancelled) {
            setLayers([layer]);
            setVisible({ world: true });
            setInfo(`${ref.member} · single WorldFile`);
          }
        } else if (!cancelled) {
          setLayers([]);
          setInfo("Validate a stage script to load the multi-draw scene");
        }
      } catch (err) {
        if (!cancelled) {
          setLayers([]);
          setError(err instanceof Error ? err.message : String(err));
          setInfo("Stage scene load failed");
        }
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [stageScript, worldPath]);

  const drawList = useMemo(() => {
    return layers.filter((layer) => visible[layer.id]).slice(0, MAX_DRAW_LAYERS);
  }, [layers, visible]);

  // Three.js multi-draw
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || drawList.length === 0) return;
    let cancelled = false;
    let frame = 0;
    let controls: OrbitControls | null = null;
    let renderer: THREE.WebGLRenderer | null = null;
    const disposables: Array<{ dispose: () => void }> = [];

    const disposeAll = () => {
      cancelAnimationFrame(frame);
      controls?.dispose();
      controls = null;
      if (renderer) {
        renderer.dispose();
        renderer = null;
      }
      for (const d of disposables.splice(0)) {
        try {
          d.dispose();
        } catch {
          /* ignore double-dispose */
        }
      }
      mount.replaceChildren();
    };

    void (async () => {
      try {
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0b1020);
        const camera = new THREE.PerspectiveCamera(
          50,
          mount.clientWidth / Math.max(mount.clientHeight, 1),
          0.1,
          250000,
        );
        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(window.devicePixelRatio || 1);
        renderer.setSize(mount.clientWidth, mount.clientHeight);
        if (cancelled) {
          disposeAll();
          return;
        }
        mount.replaceChildren();
        mount.appendChild(renderer.domElement);
        controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        scene.add(new THREE.HemisphereLight(0xbdd7ff, 0x1a2033, 1.1));
        const dir = new THREE.DirectionalLight(0xffffff, 0.9);
        dir.position.set(40, 80, 20);
        scene.add(dir, new THREE.AxesHelper(30));

        const group = new THREE.Group();
        scene.add(group);
        const unionBox = new THREE.Box3();
        let anyMesh = false;
        const roleColor: Record<MeshLayer["role"], number> = {
          world: 0xffffff,
          object: 0xd0e8ff,
          sky: 0x88aadd,
          collision: 0xff8899,
        };

        for (const layer of drawList) {
          if (cancelled) {
            disposeAll();
            return;
          }
          const result = await api<ParsedMesh>(
            `/api/mesh-studio/parse?archive=${encodeURIComponent(layer.archive)}&member=${encodeURIComponent(layer.member)}`,
          );
          if (cancelled) {
            disposeAll();
            return;
          }
          const geometry = new THREE.BufferGeometry();
          const positions = new Float32Array(result.mesh.positions.length * 3);
          result.mesh.positions.forEach((p, i) => {
            positions[i * 3] = p[0]!;
            positions[i * 3 + 1] = p[1]!;
            positions[i * 3 + 2] = p[2]!;
          });
          geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
          if (result.mesh.uvs && result.mesh.uvs.length === result.mesh.positions.length) {
            const uvs = new Float32Array(result.mesh.uvs.length * 2);
            result.mesh.uvs.forEach((uv, i) => {
              uvs[i * 2] = uv[0]!;
              uvs[i * 2 + 1] = uv[1]!;
            });
            geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
          }
          if (result.mesh.indices.length >= 3) geometry.setIndex(result.mesh.indices);
          geometry.computeVertexNormals();
          geometry.computeBoundingBox();
          const material = new THREE.MeshStandardMaterial({
            color: roleColor[layer.role],
            emissive: layer.role === "collision" ? 0x331018 : 0x0a1520,
            metalness: 0.05,
            roughness: 0.75,
            side: THREE.DoubleSide,
            transparent: layer.role === "collision",
            opacity: layer.role === "collision" ? 0.35 : 1,
            wireframe: layer.role === "collision",
          });
          new THREE.TextureLoader().load(
            `/api/mesh-studio/texture?meshMember=${encodeURIComponent(layer.member)}`,
            (map) => {
              if (cancelled) {
                map.dispose();
                return;
              }
              map.colorSpace = THREE.SRGBColorSpace;
              map.wrapS = THREE.RepeatWrapping;
              map.wrapT = THREE.RepeatWrapping;
              material.map = map;
              material.color.set(0xffffff);
              material.needsUpdate = true;
              disposables.push(map);
            },
            undefined,
            () => {
              /* keep role color */
            },
          );
          const mesh = new THREE.Mesh(geometry, material);
          mesh.name = layerKey(layer);
          group.add(mesh);
          disposables.push(geometry, material);
          if (geometry.boundingBox) {
            const box = geometry.boundingBox.clone();
            unionBox.union(box);
            anyMesh = true;
          }
        }

        if (anyMesh && !unionBox.isEmpty()) {
          const center = new THREE.Vector3();
          const size = new THREE.Vector3();
          unionBox.getCenter(center);
          unionBox.getSize(size);
          const horiz = Math.max(size.x, size.z, 1);
          const radius = Math.max(horiz, size.y * 0.55, 1);
          controls.target.copy(center);
          const distance = radius * 1.45;
          const planar = size.y < Math.max(size.x, size.z) * 0.25;
          if (planar) {
            camera.position.set(
              center.x + distance * 0.4,
              center.y + distance * 1.05,
              center.z + distance * 0.4,
            );
          } else {
            camera.position.set(
              center.x + distance * 0.85,
              center.y + distance * 0.75,
              center.z + distance * 0.85,
            );
          }
          camera.near = Math.max(radius / 1000, 0.1);
          camera.far = Math.max(radius * 50, 1000);
          camera.updateProjectionMatrix();
        }

        if (!cancelled) {
          setInfo(
            (prev) =>
              `${prev.split(" · drawing")[0] ?? prev} · drawing ${drawList.length} mesh${drawList.length === 1 ? "" : "es"}`,
          );
        }

        if (cancelled) {
          disposeAll();
          return;
        }
        const liveControls = controls;
        const liveRenderer = renderer;
        if (!liveControls || !liveRenderer) return;
        const tick = () => {
          liveControls.update();
          liveRenderer.render(scene, camera);
          frame = requestAnimationFrame(tick);
        };
        tick();
      } catch (err) {
        disposeAll();
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    })();

    return () => {
      cancelled = true;
      disposeAll();
    };
  }, [drawList]);

  const toggleLayer = (id: string) => {
    setVisible((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const primaryRef = layers[0]
    ? { archive: layers[0].archive, member: layers[0].member }
    : null;

  return (
    <div className="stage-preview">
      <div
        className="mesh-viewport stage-viewport"
        ref={mountRef}
        aria-label="Stage multi-draw geometry preview"
      />
      {layers.length > 0 && (
        <div className="layer-list" role="group" aria-label="Stage draw layers">
          {layers.map((layer) => {
            const on = Boolean(visible[layer.id]);
            const wouldExceed =
              !on &&
              layers.filter((l) => visible[l.id]).length >= MAX_DRAW_LAYERS;
            return (
              <label key={layer.id} className="layer-row">
                <span>
                  <input
                    type="checkbox"
                    checked={on}
                    disabled={wouldExceed}
                    onChange={() => toggleLayer(layer.id)}
                  />{" "}
                  {layer.label}
                  {layer.level != null ? ` · L${layer.level}` : ""}
                </span>
                <small className="mono muted">
                  {layer.role}
                  {wouldExceed && !on ? " · cap" : ""}
                </small>
              </label>
            );
          })}
        </div>
      )}
      <div className="path-row">
        <div className="empty">
          {busy ? "Resolving stage scene…" : info}
          {error ? ` — ${error}` : ""}
        </div>
        {primaryRef && onOpenMesh && (
          <button
            className="btn"
            type="button"
            onClick={() => onOpenMesh(primaryRef.archive, primaryRef.member)}
          >
            Open World in Mesh Studio
          </button>
        )}
      </div>
      <p className="empty">
        Multi-draw stage compositor (World + Object layers). Effects/VFX paths are listed in the
        scene graph only — not meshed. Cap {MAX_DRAW_LAYERS} simultaneous draws for responsiveness.
      </p>
    </div>
  );
}
