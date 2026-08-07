import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type ResolvedMesh = {
  resolved: {
    archive: string;
    member: string;
    path: string;
    char: string;
    index: string;
    desc: string;
  };
  mesh: {
    positions: number[][];
    indices: number[];
    uvs?: number[][];
    vertexCount: number;
    decodeMode: string;
    confidence?: { solidArea?: number; score?: number };
  };
};

/**
 * RE: Info_Item_Mesh.set (AES) maps shop mesh index → Res/Player/.../Racket.dat
 * Preview decodes that DAT with the stage mesh codec (not DX9 Equipment view).
 */
export function EquipmentMeshPreview({
  meshIndex,
  char = "NIKI",
}: {
  meshIndex: string;
  char?: string;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [label, setLabel] = useState("Resolving equipment mesh…");

  useEffect(() => {
    let cancelled = false;
    let cleanup: (() => void) | undefined;
    void (async () => {
      try {
        const response = await fetch(
          `/api/item-mesh/resolve?meshIndex=${encodeURIComponent(meshIndex)}&char=${encodeURIComponent(char)}`,
        );
        const data = (await response.json()) as ResolvedMesh & {
          ok?: boolean;
          error?: string;
        };
        if (!response.ok || !data.ok) {
          throw new Error(data.error ?? `HTTP ${response.status}`);
        }
        if (cancelled) return;
        setLabel(
          `${data.resolved.member} · mesh#${data.resolved.index} · ${data.mesh.vertexCount} verts · ${data.mesh.decodeMode}` +
            (data.resolved.desc ? ` · ${data.resolved.desc}` : ""),
        );
        const mount = mountRef.current;
        if (!mount) return;
        mount.replaceChildren();
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0b1020);
        const camera = new THREE.PerspectiveCamera(
          45,
          mount.clientWidth / Math.max(mount.clientHeight, 1),
          0.01,
          5000,
        );
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(window.devicePixelRatio || 1);
        renderer.setSize(mount.clientWidth, mount.clientHeight);
        mount.appendChild(renderer.domElement);
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 1.1));
        const dir = new THREE.DirectionalLight(0xffffff, 0.85);
        dir.position.set(4, 8, 3);
        scene.add(dir);
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(data.mesh.positions.length * 3);
        data.mesh.positions.forEach((p, i) => {
          positions[i * 3] = p[0]!;
          positions[i * 3 + 1] = p[1]!;
          positions[i * 3 + 2] = p[2]!;
        });
        geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        if (data.mesh.uvs && data.mesh.uvs.length === data.mesh.positions.length) {
          const uvs = new Float32Array(data.mesh.uvs.length * 2);
          data.mesh.uvs.forEach((uv, i) => {
            uvs[i * 2] = uv[0]!;
            uvs[i * 2 + 1] = uv[1]!;
          });
          geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
        }
        if (data.mesh.indices.length >= 3) geometry.setIndex(data.mesh.indices);
        geometry.computeVertexNormals();
        geometry.computeBoundingBox();
        const material = new THREE.MeshStandardMaterial({
          color: 0xc0c8d8,
          metalness: 0.35,
          roughness: 0.4,
          side: THREE.DoubleSide,
        });
        const stem = data.resolved.member.replace(/\.dat$/i, "");
        // Prefer co-located .tex with same stem in the same archive.
        new THREE.TextureLoader().load(
          `/api/mesh-studio/texture?archive=${encodeURIComponent(data.resolved.archive)}&member=${encodeURIComponent(stem + "00.tex")}`,
          (map) => {
            if (cancelled) {
              map.dispose();
              return;
            }
            map.colorSpace = THREE.SRGBColorSpace;
            material.map = map;
            material.color.set(0xffffff);
            material.needsUpdate = true;
          },
          undefined,
          () => {
            /* keep metallic grey */
          },
        );
        scene.add(new THREE.Mesh(geometry, material));
        if (geometry.boundingBox) {
          const center = new THREE.Vector3();
          const size = new THREE.Vector3();
          geometry.boundingBox.getCenter(center);
          geometry.boundingBox.getSize(size);
          const radius = Math.max(size.x, size.y, size.z, 0.1);
          controls.target.copy(center);
          const distance = radius * 2.4;
          camera.position.set(
            center.x + distance * 0.7,
            center.y + distance * 0.45,
            center.z + distance * 0.9,
          );
          camera.near = Math.max(radius / 500, 0.01);
          camera.far = Math.max(radius * 40, 100);
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
        if (!cancelled) {
          setLabel(err instanceof Error ? err.message : String(err));
        }
      }
    })();
    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [meshIndex, char]);

  return (
    <div className="equipment-preview">
      <div
        className="mesh-viewport equipment-viewport"
        ref={mountRef}
        aria-label="Equipment mesh preview"
        style={{ minHeight: 220 }}
      />
      <div className="mono empty">{label}</div>
      <div className="empty">
        Equipment mesh from AES-decrypted Info_Item_Mesh (recovery, not in-game DX9 attach).
      </div>
    </div>
  );
}
