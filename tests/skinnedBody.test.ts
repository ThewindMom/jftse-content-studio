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

  test("driveBonesFromAni uses position-only FK when no quats (no throw)", () => {
    const palette = [bone(0, "root", null, 0), bone(1, "child", 0, 1)];
    const { bones } = buildBoneHierarchy(palette);
    const rest = captureBoneRest(bones);
    const tracks = [
      {
        index: 0,
        name: "root",
        positions: [
          [0, 0, 0],
          [3, 0, 0],
        ],
        hasRotations: false,
      },
      {
        index: 1,
        name: "child",
        positions: [
          [1, 0, 0],
          [1, 2, 0],
        ],
        hasRotations: false,
      },
    ];
    expect(resolveDriveMode(false)).toBe("position-only-fk");
    const mode = driveBonesFromAni(
      bones,
      tracks,
      1,
      "position-only-fk",
      rest.positions,
      rest.quats,
    );
    expect(mode).toBe("position-only-fk");
    expect(bones[0]!.position.x).toBeCloseTo(3, 5);
    expect(bones[1]!.position.y).toBeCloseTo(2, 5);
  });

  test("driveBonesFromAni applies quats when present", () => {
    const palette = [bone(0, "root", null, 0)];
    const { bones } = buildBoneHierarchy(palette);
    const rest = captureBoneRest(bones);
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
    const mode = driveBonesFromAni(
      bones,
      tracks,
      0,
      "quat",
      rest.positions,
      rest.quats,
    );
    expect(mode).toBe("quat");
    expect(bones[0]!.quaternion.y).toBeCloseTo(q.y, 5);
  });

  test("driveBonesFromAni missing quats falls back without throw", () => {
    const palette = [bone(0, "root", null, 0)];
    const { bones } = buildBoneHierarchy(palette);
    const rest = captureBoneRest(bones);
    const mode = driveBonesFromAni(
      bones,
      [{ index: 0, name: "root", positions: [[1, 2, 3]], hasRotations: false }],
      0,
      "quat", // requested quat but track has none
      rest.positions,
      rest.quats,
    );
    expect(mode).toBe("position-only-fk");
    expect(bones[0]!.position.z).toBeCloseTo(3, 5);
  });
});
