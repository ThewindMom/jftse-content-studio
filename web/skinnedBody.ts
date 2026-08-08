/**
 * Build a Three.js SkinnedMesh from /api/skin/parse (+ skeleton palette).
 * Bone indices 0..N match skeleton.bones[i] from the 304-byte body table.
 */
import * as THREE from "three";

export type SkeletonBoneJson = {
  readonly index: number;
  readonly name: string;
  readonly parent: string | null;
  readonly parentIndex: number | null;
  readonly position: readonly number[];
  readonly matrix4: readonly number[];
  readonly worldMatrix4?: readonly number[];
  readonly socket?: boolean;
};

export type SkinVertexJson = {
  readonly weights: readonly number[];
  readonly indices: readonly number[];
  readonly position: readonly number[];
  readonly normal?: readonly number[];
  readonly uv?: readonly number[];
};

export type SkinParsePayload = {
  readonly ok?: boolean;
  readonly vertices?: readonly SkinVertexJson[];
  readonly skeleton?: {
    readonly boneCount: number;
    readonly bones: readonly SkeletonBoneJson[];
    readonly matrixLayout?: string;
  };
  readonly skeletonCoversSkin?: boolean;
  readonly skin?: {
    readonly vertexCount?: number;
    readonly boneIndexMax?: number;
    readonly boneIndexCount?: number;
  };
};

export type AniTrackJson = {
  readonly index: number;
  readonly name: string | null;
  readonly positions: readonly (readonly number[])[];
  readonly rotations?: readonly (readonly number[])[] | null;
  readonly hasRotations?: boolean;
  readonly start?: readonly number[] | null;
};

export type DriveMode =
  | "bind"
  | "position-only-fk"
  | "hierarchical-fk"
  | "quat";

export type BoneRestState = {
  readonly positions: readonly THREE.Vector3[];
  readonly quats: readonly THREE.Quaternion[];
  readonly worldPositions: readonly THREE.Vector3[];
  readonly parentIndex: readonly (number | null)[];
  readonly children: readonly (readonly number[])[];
  readonly topoOrder: readonly number[];
};

export function buildBoneHierarchy(
  palette: readonly SkeletonBoneJson[],
): {
  bones: THREE.Bone[];
  rootBones: THREE.Bone[];
  byIndex: THREE.Bone[];
  parentIndex: (number | null)[];
} {
  const byIndex: THREE.Bone[] = [];
  const parentIndex: (number | null)[] = [];
  for (const entry of palette) {
    const bone = new THREE.Bone();
    bone.name = entry.name;
    bone.matrixAutoUpdate = false;
    if (entry.matrix4.length === 16) {
      bone.matrix.fromArray(entry.matrix4 as number[]);
      bone.matrix.decompose(bone.position, bone.quaternion, bone.scale);
    } else {
      bone.position.set(
        entry.position[0] ?? 0,
        entry.position[1] ?? 0,
        entry.position[2] ?? 0,
      );
    }
    bone.updateMatrix();
    byIndex[entry.index] = bone;
    parentIndex[entry.index] = entry.parentIndex;
  }
  const rootBones: THREE.Bone[] = [];
  for (const entry of palette) {
    const bone = byIndex[entry.index];
    if (!bone) continue;
    const parentIdx = entry.parentIndex;
    if (
      parentIdx !== null &&
      parentIdx !== undefined &&
      parentIdx >= 0 &&
      byIndex[parentIdx]
    ) {
      byIndex[parentIdx]!.add(bone);
    } else {
      rootBones.push(bone);
      parentIndex[entry.index] = null;
    }
  }
  return {
    bones: byIndex.filter(Boolean),
    rootBones,
    byIndex,
    parentIndex,
  };
}

function buildChildren(
  parentIndex: readonly (number | null)[],
  boneCount: number,
): number[][] {
  const children: number[][] = Array.from({ length: boneCount }, () => []);
  for (let i = 0; i < boneCount; i++) {
    const p = parentIndex[i];
    if (p !== null && p !== undefined && p >= 0 && p < boneCount) {
      children[p]!.push(i);
    }
  }
  return children;
}

function topologicalOrder(
  parentIndex: readonly (number | null)[],
  boneCount: number,
): number[] {
  const children = buildChildren(parentIndex, boneCount);
  const order: number[] = [];
  const visit = (i: number) => {
    order.push(i);
    for (const c of children[i] ?? []) visit(c);
  };
  for (let i = 0; i < boneCount; i++) {
    const p = parentIndex[i];
    if (p === null || p === undefined || p < 0) visit(i);
  }
  return order;
}

export function buildSkinnedGeometry(
  vertices: readonly SkinVertexJson[],
  boneCount: number,
): THREE.BufferGeometry {
  const n = vertices.length;
  const positions = new Float32Array(n * 3);
  const normals = new Float32Array(n * 3);
  const uvs = new Float32Array(n * 2);
  const skinIndex = new Uint16Array(n * 4);
  const skinWeight = new Float32Array(n * 4);
  const maxBone = Math.max(boneCount - 1, 0);

  for (let i = 0; i < n; i++) {
    const v = vertices[i]!;
    positions[i * 3] = v.position[0] ?? 0;
    positions[i * 3 + 1] = v.position[1] ?? 0;
    positions[i * 3 + 2] = v.position[2] ?? 0;
    const nrm = v.normal;
    if (nrm && nrm.length >= 3) {
      normals[i * 3] = nrm[0] ?? 0;
      normals[i * 3 + 1] = nrm[1] ?? 0;
      normals[i * 3 + 2] = nrm[2] ?? 0;
    } else {
      normals[i * 3 + 1] = 1;
    }
    const uv = v.uv;
    uvs[i * 2] = uv?.[0] ?? 0;
    uvs[i * 2 + 1] = uv?.[1] ?? 0;
    for (let k = 0; k < 4; k++) {
      const idx = Math.min(Math.max(v.indices[k] ?? 0, 0), maxBone);
      skinIndex[i * 4 + k] = idx;
      skinWeight[i * 4 + k] = v.weights[k] ?? 0;
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
  geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
  geometry.setAttribute("skinIndex", new THREE.BufferAttribute(skinIndex, 4));
  geometry.setAttribute("skinWeight", new THREE.BufferAttribute(skinWeight, 4));
  return geometry;
}

export function buildSkinnedMesh(
  payload: SkinParsePayload,
  material?: THREE.Material,
): {
  mesh: THREE.SkinnedMesh;
  skeleton: THREE.Skeleton;
  bones: THREE.Bone[];
  root: THREE.Object3D;
  parentIndex: (number | null)[];
  vertexCount: number;
  boneCount: number;
} | null {
  const verts = payload.vertices;
  const palette = payload.skeleton?.bones;
  if (!verts?.length || !palette?.length) return null;

  const { rootBones, byIndex, parentIndex } = buildBoneHierarchy(palette);
  const geometry = buildSkinnedGeometry(verts, palette.length);
  // Three r152+: mesh type drives GPU weights; material flags are unused.
  let mat: THREE.Material;
  if (material) {
    mat = material;
  } else {
    const std = new THREE.MeshStandardMaterial();
    std.color.setHex(0xb8c4d8);
    std.metalness = 0.15;
    std.roughness = 0.55;
    std.side = THREE.DoubleSide;
    mat = std;
  }
  const mesh = new THREE.SkinnedMesh(geometry, mat);
  mesh.frustumCulled = false;
  mesh.castShadow = false;

  const root = new THREE.Object3D();
  root.name = "SkeletonRoot";
  for (const rb of rootBones) root.add(rb);

  // Bind with current pose as bind pose (local matrices already applied)
  const bones = byIndex.filter(Boolean);
  const skeleton = new THREE.Skeleton(bones);
  mesh.add(root);
  mesh.bind(skeleton);
  skeleton.calculateInverses();

  return {
    mesh,
    skeleton,
    bones,
    root,
    parentIndex,
    vertexCount: verts.length,
    boneCount: palette.length,
  };
}

export function captureBoneRest(
  bones: readonly THREE.Bone[],
  parentIndex: readonly (number | null)[],
): BoneRestState {
  const positions: THREE.Vector3[] = [];
  const quats: THREE.Quaternion[] = [];
  const worldPositions: THREE.Vector3[] = [];
  for (const bone of bones) {
    bone.updateMatrixWorld(true);
  }
  for (const bone of bones) {
    positions.push(bone.position.clone());
    quats.push(bone.quaternion.clone());
    worldPositions.push(new THREE.Vector3().setFromMatrixPosition(bone.matrixWorld));
  }
  const n = bones.length;
  const parents = parentIndex.slice(0, n);
  while (parents.length < n) parents.push(null);
  const children = buildChildren(parents, n);
  const topoOrder = topologicalOrder(parents, n);
  return {
    positions,
    quats,
    worldPositions,
    parentIndex: parents,
    children,
    topoOrder,
  };
}

// Drive implementation lives in boneDrive.ts (keeps this module under LOC budget).
export { driveBonesFromAni, resolveDriveMode } from "./boneDrive";
