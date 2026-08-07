import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type MeshRow = {
  archive: string;
  member: string;
  bytes: number;
  kind: string;
};

type MeshPayload = {
  name: string;
  archive: string;
  member: string;
  vertexCount: number;
  indexCount: number;
  decodeMode: string;
  bounds: { min: number[]; max: number[] };
  positions: number[][];
  indices: number[];
  uvs?: number[][];
  uvMode?: string;
  hasUvs?: boolean;
  texture?: { archive: string; member: string; source: string } | null;
  vertexOffset: number;
  byteLength: number;
  header?: Record<string, number>;
  confidence?: {
    score: number;
    triangleCount: number;
    nonDegenerateTriangles?: number;
    solidArea?: number;
    footprintXZ?: number;
    bytesPerVertex: number;
    extent: number[];
    hasIndices: boolean;
  };
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  const data = (await response.json()) as T & { error?: string };
  if (!response.ok) throw new Error(data.error ?? `HTTP ${response.status}`);
  return data;
}

function MeshViewport({
  mesh,
  wireframe,
}: {
  mesh: MeshPayload | null;
  wireframe: boolean;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const stateRef = useRef<{
    renderer?: THREE.WebGLRenderer;
    scene?: THREE.Scene;
    camera?: THREE.PerspectiveCamera;
    controls?: OrbitControls;
    object?: THREE.Object3D;
    frame?: number;
  }>({});

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1020);
    const camera = new THREE.PerspectiveCamera(
      50,
      mount.clientWidth / Math.max(mount.clientHeight, 1),
      0.1,
      250000,
    );
    camera.position.set(120, 90, 120);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    const hemi = new THREE.HemisphereLight(0xbdd7ff, 0x1a2033, 1.1);
    const dir = new THREE.DirectionalLight(0xffffff, 0.85);
    dir.position.set(40, 80, 20);
    scene.add(
      hemi,
      dir,
      new THREE.GridHelper(200, 20, 0x2a3654, 0x1a243d),
      new THREE.AxesHelper(40),
    );
    stateRef.current = { renderer, scene, camera, controls };
    let frame = 0;
    const tick = () => {
      controls.update();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(tick);
    };
    tick();
    const onResize = () => {
      if (!mount) return;
      camera.aspect = mount.clientWidth / Math.max(mount.clientHeight, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
      stateRef.current = {};
    };
  }, []);

  useEffect(() => {
    const state = stateRef.current;
    if (!state.scene) return;
    let cancelled = false;
    let texture: THREE.Texture | undefined;
    if (state.object) {
      state.scene.remove(state.object);
      state.object.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.dispose();
          if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
          else child.material.dispose();
        }
      });
      state.object = undefined;
    }
    if (!mesh || mesh.positions.length < 3) return;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(mesh.positions.length * 3);
    mesh.positions.forEach((p, i) => {
      positions[i * 3] = p[0]!;
      positions[i * 3 + 1] = p[1]!;
      positions[i * 3 + 2] = p[2]!;
    });
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    if (mesh.uvs && mesh.uvs.length === mesh.positions.length) {
      const uvs = new Float32Array(mesh.uvs.length * 2);
      mesh.uvs.forEach((uv, i) => {
        uvs[i * 2] = uv[0]!;
        uvs[i * 2 + 1] = uv[1]!;
      });
      geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
    }
    if (mesh.indices.length >= 3) {
      geometry.setIndex(mesh.indices);
    }
    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();
    const material = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: 0x0a1520,
      metalness: 0.05,
      roughness: 0.75,
      side: THREE.DoubleSide,
      wireframe,
      transparent: true,
      opacity: wireframe ? 0.98 : 1,
    });
    const object = new THREE.Mesh(geometry, material);
    state.scene.add(object);
    state.object = object;
    geometry.computeBoundingBox();
    if (geometry.boundingBox && state.camera && state.controls) {
      const box = geometry.boundingBox;
      const center = new THREE.Vector3();
      const size = new THREE.Vector3();
      box.getCenter(center);
      box.getSize(size);
      const horiz = Math.max(size.x, size.z, 1);
      const radius = Math.max(horiz, size.y * 0.55, 1);
      state.controls.target.copy(center);
      const distance = radius * 1.45;
      const planar = size.y < Math.max(size.x, size.z) * 0.25;
      if (planar) {
        state.camera.position.set(
          center.x + distance * 0.4,
          center.y + distance * 1.05,
          center.z + distance * 0.4,
        );
      } else {
        state.camera.position.set(
          center.x + distance * 0.85,
          center.y + distance * 0.75,
          center.z + distance * 0.85,
        );
      }
      state.camera.near = Math.max(radius / 1000, 0.1);
      state.camera.far = Math.max(radius * 50, 1000);
      state.camera.updateProjectionMatrix();
      state.controls.update();
    }
    // Stock stage albedo (restool XOR .tex → PNG). Fallback keeps cyan recovery look.
    const texUrl = `/api/mesh-studio/texture?meshMember=${encodeURIComponent(mesh.member)}`;
    const loader = new THREE.TextureLoader();
    loader.load(
      texUrl,
      (map) => {
        if (cancelled) {
          map.dispose();
          return;
        }
        map.colorSpace = THREE.SRGBColorSpace;
        map.wrapS = THREE.RepeatWrapping;
        map.wrapT = THREE.RepeatWrapping;
        texture = map;
        material.map = map;
        material.color.set(0xffffff);
        material.emissive.set(0x000000);
        material.needsUpdate = true;
      },
      undefined,
      () => {
        // Keep untextured cyan when stock albedo missing.
        material.color.set(0x7ad7ff);
        material.emissive.set(0x16324d);
        material.needsUpdate = true;
      },
    );
    return () => {
      cancelled = true;
      texture?.dispose();
    };
  }, [mesh, wireframe]);

  return <div className="mesh-viewport" ref={mountRef} aria-label="Mesh viewport" />;
}

export function MeshStudio({
  focus = null,
}: {
  focus?: { archive: string; member: string } | null;
}) {
  const [rows, setRows] = useState<MeshRow[]>([]);
  const [query, setQuery] = useState("court");
  const [selected, setSelected] = useState<MeshRow | null>(null);
  const [mesh, setMesh] = useState<MeshPayload | null>(null);
  const [wireframe, setWireframe] = useState(false);
  const [status, setStatus] = useState("Loading mesh catalog…");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [exportInfo, setExportInfo] = useState("");
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const [tz, setTz] = useState(0);
  const [sx, setSx] = useState(1);
  const [sy, setSy] = useState(1);
  const [sz, setSz] = useState(1);
  const [rx, setRx] = useState(0);
  const [ry, setRy] = useState(0);
  const [rz, setRz] = useState(0);

  useEffect(() => {
    void api<{ meshes: MeshRow[]; count: number }>("/api/mesh-studio/list")
      .then((data) => {
        setRows(data.meshes);
        setStatus(`Loaded ${data.count} mesh DAT members from stock client`);
        if (focus) {
          const hit =
            data.meshes.find(
              (row) => row.archive === focus.archive && row.member === focus.member,
            ) ?? null;
          if (hit) {
            void loadMesh(hit);
            return;
          }
        }
        const preferred =
          data.meshes.find((row) => row.member === "BF_Court01.dat") ??
          data.meshes.find((row) => /court/i.test(row.member)) ??
          data.meshes[0] ??
          null;
        if (preferred) void loadMesh(preferred);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
        setStatus("Failed to load mesh catalog");
      });
  }, []);

  useEffect(() => {
    if (!focus || rows.length === 0) return;
    const hit =
      rows.find((row) => row.archive === focus.archive && row.member === focus.member) ?? null;
    if (hit) void loadMesh(hit);
  }, [focus?.archive, focus?.member, rows]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      `${row.archive} ${row.member} ${row.kind}`.toLowerCase().includes(q),
    );
  }, [rows, query]);

  const loadMesh = async (row: MeshRow) => {
    setSelected(row);
    setBusy(true);
    setError("");
    setStatus(`Decoding ${row.member}…`);
    try {
      const result = await api<{ mesh: MeshPayload }>(
        `/api/mesh-studio/parse?archive=${encodeURIComponent(row.archive)}&member=${encodeURIComponent(row.member)}`,
      );
      setMesh(result.mesh);
      setStatus(
        `Decoded ${result.mesh.member}: ${result.mesh.vertexCount} verts · ${result.mesh.indexCount} indices · ${result.mesh.decodeMode}`,
      );
    } catch (err) {
      setMesh(null);
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Mesh decode failed");
    } finally {
      setBusy(false);
    }
  };

  const exportMesh = async () => {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<{ obj: string; gltf: string; meta: string }>(
        "/api/mesh-studio/export",
        {
          method: "POST",
          body: JSON.stringify({
            archive: selected.archive,
            member: selected.member,
          }),
        },
      );
      setExportInfo(`${result.obj}\n${result.gltf}\n${result.meta}`);
      setStatus("Exported OBJ + glTF + meta");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const applyTransform = async () => {
    if (!selected) return;
    setBusy(true);
    setError("");
    setStatus("Applying transform and rewriting DAT vertices…");
    try {
      const result = await api<{
        dat: string;
        obj: string;
        sameSize: boolean;
        vertexCount: number;
      }>("/api/mesh-studio/transform", {
        method: "POST",
        body: JSON.stringify({
          archive: selected.archive,
          member: selected.member,
          translate: [tx, ty, tz],
          scale: [sx, sy, sz],
          rotateDeg: [rx, ry, rz],
        }),
      });
      setExportInfo(`${result.dat}\n${result.obj}\nsameSize=${result.sameSize}`);
      setStatus(
        `Transformed ${result.vertexCount} verts · sameSize=${result.sameSize ? "yes" : "no"}`,
      );
      await loadMesh(selected);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("Transform failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="workspace mesh-workspace">
      <section className="panel" aria-label="Mesh catalog">
        <header>
          <h2>Mesh catalog</h2>
        </header>
        <div className="body">
          <label>
            Search meshes
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="court, mesh01, sky, collision…"
            />
          </label>
          <div className="list">
            {filtered.map((row) => (
              <button
                key={`${row.archive}:${row.member}`}
                type="button"
                data-active={
                  selected?.archive === row.archive && selected?.member === row.member
                }
                onClick={() => void loadMesh(row)}
              >
                {row.member}
                <small>
                  {row.kind} · {row.archive} · {row.bytes} B
                </small>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="panel" aria-label="Mesh modeler">
        <header>
          <h2>Mesh modeler</h2>
        </header>
        <div className="body">
          <MeshViewport mesh={mesh} wireframe={wireframe} />
          <div className="field-grid">
            <label>
              Translate X
              <input type="number" step="0.1" value={tx} onChange={(e) => setTx(Number(e.target.value))} />
            </label>
            <label>
              Translate Y
              <input type="number" step="0.1" value={ty} onChange={(e) => setTy(Number(e.target.value))} />
            </label>
            <label>
              Translate Z
              <input type="number" step="0.1" value={tz} onChange={(e) => setTz(Number(e.target.value))} />
            </label>
            <label>
              Scale X
              <input type="number" step="0.05" value={sx} onChange={(e) => setSx(Number(e.target.value))} />
            </label>
            <label>
              Scale Y
              <input type="number" step="0.05" value={sy} onChange={(e) => setSy(Number(e.target.value))} />
            </label>
            <label>
              Scale Z
              <input type="number" step="0.05" value={sz} onChange={(e) => setSz(Number(e.target.value))} />
            </label>
            <label>
              Rotate X°
              <input type="number" step="1" value={rx} onChange={(e) => setRx(Number(e.target.value))} />
            </label>
            <label>
              Rotate Y°
              <input type="number" step="1" value={ry} onChange={(e) => setRy(Number(e.target.value))} />
            </label>
            <label>
              Rotate Z°
              <input type="number" step="1" value={rz} onChange={(e) => setRz(Number(e.target.value))} />
            </label>
          </div>
          <label>
            <span>
              <input
                type="checkbox"
                checked={wireframe}
                onChange={(event) => setWireframe(event.target.checked)}
              />{" "}
              Wireframe
            </span>
          </label>
          <div className="actions">
            <button className="btn primary" type="button" disabled={busy || !selected} onClick={() => void exportMesh()}>
              Export OBJ + glTF
            </button>
            <button className="btn primary" type="button" disabled={busy || !selected} onClick={() => void applyTransform()}>
              Apply transform to DAT
            </button>
          </div>
          <p className="empty">
            Decoder recovers float3 vertex runs from proprietary Fantasy Tennis `.dat` members
            (Stage/Sky/Collision). Topology may be triangle-soup when index buffers are opaque.
            Transformed DATs keep original byte length for safer reintegration experiments.
          </p>
        </div>
      </section>

      <section className="panel" aria-label="Mesh details">
        <header>
          <h2>Decode details</h2>
        </header>
        <div className="body">
          <div>
            <strong>Status</strong>
            <div className="empty">{status}</div>
          </div>
          {error && (
            <div>
              <strong>Error</strong>
              <div className="mono" style={{ color: "var(--danger)" }}>
                {error}
              </div>
            </div>
          )}
          {mesh && (
            <div className="mono">
              {`archive=${mesh.archive}
member=${mesh.member}
verts=${mesh.vertexCount}
indices=${mesh.indexCount}
mode=${mesh.decodeMode}
vertexOffset=${mesh.vertexOffset}
bytes=${mesh.byteLength}
confidence=${mesh.confidence?.score ?? "?"}
triangles=${mesh.confidence?.triangleCount ?? Math.floor(mesh.indexCount / 3)}
solidTris=${mesh.confidence?.nonDegenerateTriangles ?? "?"}
solidArea=${mesh.confidence?.solidArea ?? "?"}
footprintXZ=${mesh.confidence?.footprintXZ ?? "?"}
uvMode=${mesh.uvMode ?? "none"}
hasUvs=${mesh.hasUvs ?? false}
texture=${mesh.texture ? `${mesh.texture.archive}/${mesh.texture.member}` : "n/a"}
boundsMin=${mesh.bounds.min.join(", ")}
boundsMax=${mesh.bounds.max.join(", ")}
header=${mesh.header ? JSON.stringify(mesh.header) : "n/a"}`}
            </div>
          )}
          {exportInfo && (
            <div>
              <strong>Outputs</strong>
              <div className="mono">{exportInfo}</div>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
