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

type BoneAttach = {
  ok?: boolean;
  hasAttach?: boolean;
  attachBone?: string;
  attach?: {
    name: string;
    position: number[];
    matrix4: number[];
  } | null;
};

/**
 * Equipment mesh + Bone_Racket attach pose from body skeleton (bind matrix).
 * RE: Rtm00 AttachBone=Bone_Racket; body DAT stores 4×4 bind pose at socket.
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
        const [meshRes, attachRes] = await Promise.all([
          fetch(
            `/api/item-mesh/resolve?meshIndex=${encodeURIComponent(meshIndex)}&char=${encodeURIComponent(char)}`,
          ),
          fetch(
            `/api/bone-attach?char=${encodeURIComponent(char)}&attachBone=Bone_Racket`,
          ),
        ]);
        const data = (await meshRes.json()) as ResolvedMesh & {
          ok?: boolean;
          error?: string;
        };
        const attachBody = (await attachRes.json()) as BoneAttach;
        if (!meshRes.ok || !data.ok) {
          throw new Error(data.error ?? `HTTP ${meshRes.status}`);
        }
        if (cancelled) return;

        const attach = attachBody.hasAttach ? attachBody.attach : null;
        setLabel(
          `${data.resolved.member} · mesh#${data.resolved.index} · ${data.mesh.vertexCount} verts` +
            (attach
              ? ` · attached @ ${attach.name} (${attach.position.map((v) => v.toFixed(2)).join(", ")})`
              : " · no Bone_Racket (origin fallback)") +
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

        // Marker at body origin + socket cross for spatial context
        scene.add(new THREE.AxesHelper(2));
        if (attach?.position) {
          const marker = new THREE.Mesh(
            new THREE.SphereGeometry(0.15, 12, 12),
            new THREE.MeshStandardMaterial({
              color: 0xff6688,
              emissive: 0x441122,
            }),
          );
          marker.position.set(
            attach.position[0]!,
            attach.position[1]!,
            attach.position[2]!,
          );
          scene.add(marker);
        }

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

        const racket = new THREE.Mesh(geometry, material);
        // Apply bind-pose matrix from Bone_Racket when available
        if (attach?.matrix4 && attach.matrix4.length === 16) {
          const m = new THREE.Matrix4().fromArray(attach.matrix4);
          racket.applyMatrix4(m);
        } else if (attach?.position) {
          racket.position.set(
            attach.position[0]!,
            attach.position[1]!,
            attach.position[2]!,
          );
        }
        scene.add(racket);

        // Frame camera on racket after attach transform
        const box = new THREE.Box3().setFromObject(racket);
        const center = new THREE.Vector3();
        const size = new THREE.Vector3();
        box.getCenter(center);
        box.getSize(size);
        const radius = Math.max(size.x, size.y, size.z, 0.5);
        controls.target.copy(center);
        const distance = radius * 2.6;
        camera.position.set(
          center.x + distance * 0.7,
          center.y + distance * 0.45,
          center.z + distance * 0.9,
        );
        camera.near = Math.max(radius / 500, 0.01);
        camera.far = Math.max(radius * 40, 200);
        camera.updateProjectionMatrix();

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
        Equipment mesh positioned via body Bone_Racket bind matrix (AttachBone RE).
      </div>
    </div>
  );
}
