/**
 * ANI → skeleton drive modes for Fantasy Tennis previews.
 * Quats when recovered; otherwise hierarchical look-at FK from float3.
 */
import * as THREE from "three";
import type { AniTrackJson, BoneRestState, DriveMode } from "./skinnedBody";

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

const _wpA = new THREE.Vector3();
const _wpB = new THREE.Vector3();
const _restDir = new THREE.Vector3();
const _animDir = new THREE.Vector3();
const _qDelta = new THREE.Quaternion();
const _qWorld = new THREE.Quaternion();
const _qParent = new THREE.Quaternion();
const _qLocal = new THREE.Quaternion();

/**
 * Drive skeleton bones from ANI tracks.
 * - quat: apply track.rotations when present (local space)
 * - hierarchical-fk: parent chain + look-at child orientation from float3 positions
 * - position-only-fk: independent local positions (legacy experiment)
 */
export function driveBonesFromAni(
  bones: readonly THREE.Bone[],
  tracks: readonly AniTrackJson[],
  frame: number,
  mode: DriveMode,
  rest: BoneRestState,
): DriveMode {
  const restPositions = rest.positions;
  const restQuats = rest.quats;

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

  if (mode === "hierarchical-fk") {
    return driveHierarchical(bones, tracks, frame, rest);
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
      const p = sampleVec3(track.positions, frame);
      if (p) {
        bone.position.copy(p);
        appliedPos = true;
      } else if (restP) {
        bone.position.copy(restP);
      }
    } else {
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

function driveHierarchical(
  bones: readonly THREE.Bone[],
  tracks: readonly AniTrackJson[],
  frame: number,
  rest: BoneRestState,
): DriveMode {
  const { positions: restP, quats: restQ, worldPositions: restW, children, topoOrder } =
    rest;
  let appliedPos = false;

  for (let i = 0; i < bones.length; i++) {
    const bone = bones[i];
    const rq = restQ[i];
    const rp = restP[i];
    if (!bone || !rq || !rp) continue;
    bone.quaternion.copy(rq);
    const track = tracks[i];
    if (track?.positions?.length) {
      const pos = sampleVec3(track.positions, frame);
      const start =
        sampleVec3(track.positions, 0) ??
        (track.start && track.start.length >= 3
          ? new THREE.Vector3(
              track.start[0] ?? 0,
              track.start[1] ?? 0,
              track.start[2] ?? 0,
            )
          : null);
      if (pos && start) {
        bone.position.set(
          rp.x + (pos.x - start.x),
          rp.y + (pos.y - start.y),
          rp.z + (pos.z - start.z),
        );
        appliedPos = true;
      } else if (pos) {
        bone.position.copy(pos);
        appliedPos = true;
      } else {
        bone.position.copy(rp);
      }
    } else {
      bone.position.copy(rp);
    }
    bone.updateMatrix();
  }

  for (const i of topoOrder) {
    bones[i]?.updateMatrixWorld(true);
  }

  let appliedLook = false;
  for (const i of topoOrder) {
    const bone = bones[i];
    const kids = children[i];
    if (!bone || !kids?.length) continue;
    const ci = kids[0]!;
    const child = bones[ci];
    const restParent = restW[i];
    const restChild = restW[ci];
    if (!child || !restParent || !restChild) continue;

    _restDir.subVectors(restChild, restParent);
    if (_restDir.lengthSq() < 1e-10) continue;
    _restDir.normalize();

    bone.getWorldPosition(_wpA);
    child.getWorldPosition(_wpB);
    _animDir.subVectors(_wpB, _wpA);
    if (_animDir.lengthSq() < 1e-10) continue;
    _animDir.normalize();

    _qDelta.setFromUnitVectors(_restDir, _animDir);
    if (bone.parent && (bone.parent as THREE.Object3D).isObject3D) {
      bone.parent.getWorldQuaternion(_qParent);
    } else {
      _qParent.identity();
    }
    _qWorld.copy(_qParent).multiply(restQ[i]!);
    _qWorld.premultiply(_qDelta);
    _qLocal.copy(_qParent).invert().multiply(_qWorld);
    bone.quaternion.copy(_qLocal);
    bone.updateMatrix();
    bone.updateMatrixWorld(true);
    appliedLook = true;
  }

  if (appliedLook || appliedPos) return "hierarchical-fk";
  return "bind";
}

/** Prefer quat when ANI recovered rotations; else hierarchical FK. */
export function resolveDriveMode(
  hasRotations: boolean | undefined,
  options?: { hierarchical?: boolean },
): DriveMode {
  if (hasRotations) return "quat";
  if (options?.hierarchical !== false) return "hierarchical-fk";
  return "position-only-fk";
}
