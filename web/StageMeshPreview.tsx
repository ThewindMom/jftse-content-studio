import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

async function api<T>(path: string): Promise<T> {
  const response = await fetch(path);
  const data = (await response.json()) as T & { error?: string };
  if (!response.ok) throw new Error(data.error ?? `HTTP ${response.status}`);
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

export function StageMeshPreview({
  worldPath,
  onOpenMesh,
}: {
  worldPath: string;
  onOpenMesh?: (archive: string, member: string) => void;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [info, setInfo] = useState("Loading stage geometry…");
  const [ref, setRef] = useState<{ archive: string; member: string } | null>(null);

  useEffect(() => {
    const parsed = clientDatPathToRef(worldPath);
    setRef(parsed);
    if (!parsed) {
      setInfo("Could not map stage path to mesh archive");
      return;
    }
    let cancelled = false;
    let cleanup: (() => void) | undefined;
    void (async () => {
      try {
        const result = await api<{
          mesh: {
            positions: number[][];
            indices: number[];
            vertexCount: number;
            confidence?: { score: number };
          };
        }>(
          `/api/mesh-studio/parse?archive=${encodeURIComponent(parsed.archive)}&member=${encodeURIComponent(parsed.member)}`,
        );
        if (cancelled) return;
        setInfo(
          `${parsed.member} · ${result.mesh.vertexCount} verts · conf ${result.mesh.confidence?.score ?? "?"}`,
        );
        const mount = mountRef.current;
        if (!mount) return;
        mount.replaceChildren();
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0b1020);
        const camera = new THREE.PerspectiveCamera(
          50,
          mount.clientWidth / Math.max(mount.clientHeight, 1),
          0.1,
          250000,
        );
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(window.devicePixelRatio || 1);
        renderer.setSize(mount.clientWidth, mount.clientHeight);
        mount.appendChild(renderer.domElement);
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        scene.add(new THREE.HemisphereLight(0xbdd7ff, 0x1a2033, 1.1));
        const dir = new THREE.DirectionalLight(0xffffff, 0.9);
        dir.position.set(40, 80, 20);
        scene.add(dir, new THREE.AxesHelper(30));
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(result.mesh.positions.length * 3);
        result.mesh.positions.forEach((p, i) => {
          positions[i * 3] = p[0]!;
          positions[i * 3 + 1] = p[1]!;
          positions[i * 3 + 2] = p[2]!;
        });
        geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        if (result.mesh.indices.length >= 3) geometry.setIndex(result.mesh.indices);
        geometry.computeVertexNormals();
        geometry.computeBoundingBox();
        const material = new THREE.MeshStandardMaterial({
          color: 0x7ad7ff,
          emissive: 0x10263d,
          metalness: 0.05,
          roughness: 0.55,
          side: THREE.DoubleSide,
        });
        scene.add(new THREE.Mesh(geometry, material));
        if (geometry.boundingBox) {
          const center = new THREE.Vector3();
          const size = new THREE.Vector3();
          geometry.boundingBox.getCenter(center);
          geometry.boundingBox.getSize(size);
          const radius = Math.max(size.x, size.y, size.z, 1);
          controls.target.copy(center);
          const distance = radius * 1.8;
          const planar = size.y < Math.max(size.x, size.z) * 0.2;
          if (planar) {
            camera.position.set(
              center.x + distance * 0.35,
              center.y + distance * 1.15,
              center.z + distance * 0.35,
            );
          } else {
            camera.position.set(
              center.x + distance,
              center.y + distance * 0.6,
              center.z + distance,
            );
          }
          camera.near = Math.max(radius / 1000, 0.1);
          camera.far = Math.max(radius * 50, 1000);
          camera.updateProjectionMatrix();
        }
        let frame = 0;
        const tick = () => {
          controls.update();
          renderer.render(scene, camera);
          frame = requestAnimationFrame(tick);
        };
        tick();
        cleanup = () => {
          cancelAnimationFrame(frame);
          controls.dispose();
          renderer.dispose();
          geometry.dispose();
          material.dispose();
          mount.replaceChildren();
        };
      } catch (err) {
        if (!cancelled) setInfo(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [worldPath]);

  return (
    <div className="stage-preview">
      <div
        className="mesh-viewport stage-viewport"
        ref={mountRef}
        aria-label="Stage geometry preview"
      />
      <div className="path-row">
        <div className="empty">{info}</div>
        {ref && onOpenMesh && (
          <button className="btn" type="button" onClick={() => onOpenMesh(ref.archive, ref.member)}>
            Open in Mesh Studio
          </button>
        )}
      </div>
    </div>
  );
}
