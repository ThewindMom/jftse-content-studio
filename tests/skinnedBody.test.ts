import { describe, expect, test } from "bun:test";
import * as THREE from "three";
import {
  buildBoneHierarchy,
  buildSkinnedMesh,
  captureBoneRest,
  driveBonesFromAni,
  resolveDriveMode,
  type SkeletonBoneJson,
  type SkinParsePayload,
} from "../web/skinnedBody";

function restOf(
  bones: THREE.Bone[],
  parentIndex: (number | null)[],
) {
  return captureBoneRest(bones, parentIndex);
}

function bone(
  index: number,
  name: string,
  parentIndex: number | null,
  x: number,
): SkeletonBoneJson {
  const m = new THREE.Matrix4().makeTranslation(x, 0, 0);
  return {
    index,
    name,
    parent: parentIndex === null ? null : `b${parentIndex}`,
    parentIndex,
    position: [x, 0, 0],
    matrix4: m.toArray(),
  };
}

describe("skinnedBody helpers", () => {
  test("buildBoneHierarchy orders bones by index and links parents", () => {
    const palette = [
      bone(0, "root", null, 0),
      bone(1, "child", 0, 1),
      bone(2, "leaf", 1, 2),
    ];
    const { bones, rootBones, byIndex } = buildBoneHierarchy(palette);
    expect(bones.length).toBe(3);
    expect(rootBones.length).toBe(1);
    expect(rootBones[0]!.name).toBe("root");
    expect(byIndex[1]!.parent).toBe(byIndex[0]!);
    expect(byIndex[2]!.parent).toBe(byIndex[1]!);
  });

  test("buildSkinnedMesh produces skeleton matching vertex skin indices", () => {
    const payload: SkinParsePayload = {
      ok: true,
      skeleton: {
        boneCount: 2,
        bones: [bone(0, "root", null, 0), bone(1, "child", 0, 1)],
      },
      vertices: [
        {
          position: [0, 0, 0],
          normal: [0, 1, 0],
          uv: [0, 0],
          weights: [1, 0, 0, 0],
          indices: [0, 0, 0, 0],
        },
        {
          position: [1, 0, 0],
          normal: [0, 1, 0],
          uv: [1, 0],
          weights: [0.5, 0.5, 0, 0],
          indices: [0, 1, 0, 0],
        },
      ],
    };
    const built = buildSkinnedMesh(payload);
    expect(built).not.toBeNull();
    expect(built!.vertexCount).toBe(2);
    expect(built!.boneCount).toBe(2);
    expect(built!.mesh.isSkinnedMesh).toBe(true);
    expect(built!.skeleton.bones.length).toBe(2);
    const skinIndex = built!.mesh.geometry.getAttribute("skinIndex");
    expect(skinIndex.getX(1)).toBe(0);
    expect(skinIndex.getY(1)).toBe(1);
    built!.mesh.geometry.dispose();
    (built!.mesh.material as THREE.Material).dispose();
  });

  test("resolveDriveMode prefers hierarchical-fk when no quats", () => {
    expect(resolveDriveMode(false)).toBe("hierarchical-fk");
    expect(resolveDriveMode(true)).toBe("quat");
    expect(resolveDriveMode(false, { hierarchical: false })).toBe(
      "position-only-fk",
    );
  });

  test("driveBonesFromAni hierarchical-fk applies position deltas (no throw)", () => {
    const palette = [bone(0, "root", null, 0), bone(1, "child", 0, 1)];
    const { bones, parentIndex } = buildBoneHierarchy(palette);
    const rest = restOf(bones, parentIndex);
    const tracks = [
      {
        index: 0,
        name: "root",
        positions: [
          [0, 0, 0],
          [0.5, 0, 0],
        ],
        hasRotations: false,
      },
      {
        index: 1,
        name: "child",
        positions: [
          [1, 0, 0],
          [1, 0.25, 0],
        ],
        hasRotations: false,
      },
    ];
    const mode = driveBonesFromAni(
      bones,
      tracks,
      1,
      "hierarchical-fk",
      rest,
    );
    expect(mode).toBe("hierarchical-fk");
    // delta frame1-frame0 applied on rest local
    expect(bones[0]!.position.x).toBeCloseTo(rest.positions[0]!.x + 0.5, 5);
    expect(bones[1]!.position.y).toBeCloseTo(rest.positions[1]!.y + 0.25, 5);
    // child remains parented
    expect(bones[1]!.parent).toBe(bones[0]!);
  });

  test("hierarchical-fk multi-child look-at derives non-rest local rotation", () => {
    // root with two non-collinear children; raise only the second so average dir tilts
    const palette = [
      bone(0, "root", null, 0),
      bone(1, "a", 0, 1),
      bone(2, "b", 0, 1),
    ];
    const { bones, parentIndex } = buildBoneHierarchy(palette);
    bones[1]!.position.set(1, 0, 0);
    bones[2]!.position.set(0, 1, 0);
    for (const b of bones) b!.updateMatrix();
    bones[0]!.updateMatrixWorld(true);
    const rest = restOf(bones, parentIndex);
    const restQ = rest.quats[0]!.clone();
    const tracks = [
      {
        index: 0,
        name: "root",
        positions: [
          [0, 0, 0],
          [0, 0, 0],
        ],
        hasRotations: false,
      },
      {
        index: 1,
        name: "a",
        positions: [
          [1, 0, 0],
          [1, 0, 0],
        ],
        hasRotations: false,
      },
      {
        index: 2,
        name: "b",
        positions: [
          [0, 1, 0],
          [0, 1, 0.5],
        ],
        hasRotations: false,
      },
    ];
    const mode = driveBonesFromAni(
      bones,
      tracks,
      1,
      "hierarchical-fk",
      rest,
    );
    expect(mode).toBe("hierarchical-fk");
    const angle = restQ.angleTo(bones[0]!.quaternion);
    expect(angle).toBeGreaterThan(1e-4);
  });

  test("driveBonesFromAni applies quats when present", () => {
    const palette = [bone(0, "root", null, 0)];
    const { bones, parentIndex } = buildBoneHierarchy(palette);
    const rest = restOf(bones, parentIndex);
    const q = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(0, 1, 0),
      Math.PI / 2,
    );
    const tracks = [
      {
        index: 0,
        name: "root",
        positions: [[0, 0, 0]],
        rotations: [[q.x, q.y, q.z, q.w]],
        hasRotations: true,
      },
    ];
    const mode = driveBonesFromAni(bones, tracks, 0, "quat", rest);
    expect(mode).toBe("quat");
    expect(bones[0]!.quaternion.y).toBeCloseTo(q.y, 5);
  });

  test("driveBonesFromAni missing quats falls back without throw", () => {
    const palette = [bone(0, "root", null, 0)];
    const { bones, parentIndex } = buildBoneHierarchy(palette);
    const rest = restOf(bones, parentIndex);
    const mode = driveBonesFromAni(
      bones,
      [{ index: 0, name: "root", positions: [[1, 2, 3]], hasRotations: false }],
      0,
      "quat", // requested quat but track has none
      rest,
    );
    expect(mode).toBe("position-only-fk");
    expect(bones[0]!.position.z).toBeCloseTo(3, 5);
  });
});
