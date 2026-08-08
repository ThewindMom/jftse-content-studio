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

export type DriveMode = "bind" | "position-only-fk" | "quat";

export function buildBoneHierarchy(
  palette: readonly SkeletonBoneJson[],
): { bones: THREE.Bone[]; rootBones: THREE.Bone[]; byIndex: THREE.Bone[] } {
  const byIndex: THREE.Bone[] = [];
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
    }
  }
  return { bones: byIndex.filter(Boolean), rootBones, byIndex };
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
  vertexCount: number;
  boneCount: number;
} | null {
  const verts = payload.vertices;
  const palette = payload.skeleton?.bones;
  if (!verts?.length || !palette?.length) return null;

  const { bones, rootBones, byIndex } = buildBoneHierarchy(palette);
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
  const skeleton = new THREE.Skeleton(byIndex.filter(Boolean));
  mesh.add(root);
  mesh.bind(skeleton);
  skeleton.calculateInverses();

  return {
    mesh,
    skeleton,
    bones: byIndex.filter(Boolean),
    root,
    vertexCount: verts.length,
    boneCount: palette.length,
  };
}

function sampleVec3(
  series: readonly (readonly number[])[] | null | undefined,
  frame: number,
): THREE.Vector3 | null {
  if (!series?.length) return null;
  const i = Math.max(0, Math.min(series.length - 1, frame));
  const p = series[i];
  if (!p || p.length < 3) return null;
  return new THREE.Vector3(p[0] ?? 0, p[1] ?? 0, p[2] ?? 0);
}

function sampleQuat(
  series: readonly (readonly number[])[] | null | undefined,
  frame: number,
): THREE.Quaternion | null {
  if (!series?.length) return null;
  const i = Math.max(0, Math.min(series.length - 1, frame));
  const q = series[i];
  if (!q || q.length < 4) return null;
  const quat = new THREE.Quaternion(q[0] ?? 0, q[1] ?? 0, q[2] ?? 0, q[3] ?? 1);
  if (quat.lengthSq() < 1e-8) return null;
  quat.normalize();
  return quat;
}

/**
 * Drive skeleton bones from ANI tracks.
 * - quat mode: apply track.rotations when present
 * - position-only-fk: set bone.position from track positions (experiment)
 * Never throws on missing quats / short tracks.
 */
export function driveBonesFromAni(
  bones: readonly THREE.Bone[],
  tracks: readonly AniTrackJson[],
  frame: number,
  mode: DriveMode,
  restPositions: readonly THREE.Vector3[],
  restQuats: readonly THREE.Quaternion[],
): DriveMode {
  if (mode === "bind") {
    for (let i = 0; i < bones.length; i++) {
      const bone = bones[i];
      const rp = restPositions[i];
      const rq = restQuats[i];
      if (!bone || !rp || !rq) continue;
      bone.position.copy(rp);
      bone.quaternion.copy(rq);
      bone.updateMatrix();
    }
    return "bind";
  }

  const n = Math.min(bones.length, tracks.length);
  let appliedQuat = false;
  let appliedPos = false;

  for (let i = 0; i < n; i++) {
    const bone = bones[i];
    const track = tracks[i];
    if (!bone || !track) continue;
    const restP = restPositions[i];
    const restQ = restQuats[i];

    if (mode === "quat" && track.hasRotations && track.rotations) {
      const q = sampleQuat(track.rotations, frame);
      if (q) {
        bone.quaternion.copy(q);
        appliedQuat = true;
      } else if (restQ) {
        bone.quaternion.copy(restQ);
      }
      // Still apply positions if present as local translation experiment
      const p = sampleVec3(track.positions, frame);
      if (p) {
        bone.position.copy(p);
        appliedPos = true;
      } else if (restP) {
        bone.position.copy(restP);
      }
    } else {
      // position-only FK experiment
      const p = sampleVec3(track.positions, frame);
      if (p) {
        bone.position.copy(p);
        appliedPos = true;
      } else if (restP) {
        bone.position.copy(restP);
      }
      if (restQ) bone.quaternion.copy(restQ);
    }
    bone.updateMatrix();
  }

  // Bones beyond track count stay at rest
  for (let i = n; i < bones.length; i++) {
    const bone = bones[i];
    const rp = restPositions[i];
    const rq = restQuats[i];
    if (!bone || !rp || !rq) continue;
    bone.position.copy(rp);
    bone.quaternion.copy(rq);
    bone.updateMatrix();
  }

  if (mode === "quat" && appliedQuat) return "quat";
  if (appliedPos) return "position-only-fk";
  return "bind";
}

export function captureBoneRest(
  bones: readonly THREE.Bone[],
): { positions: THREE.Vector3[]; quats: THREE.Quaternion[] } {
  const positions: THREE.Vector3[] = [];
  const quats: THREE.Quaternion[] = [];
  for (const bone of bones) {
    positions.push(bone.position.clone());
    quats.push(bone.quaternion.clone());
  }
  return { positions, quats };
}

export function resolveDriveMode(hasRotations: boolean | undefined): DriveMode {
  return hasRotations ? "quat" : "position-only-fk";
}
