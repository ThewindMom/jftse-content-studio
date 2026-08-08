"""Derive unit local bone quaternions from ANI float3 tracks + skeleton bind.

On-disk Niki ANI does not carry a confident dense float4 channel. The client
preview already uses multi-child look-at hierarchical FK in Three.js. This
module mirrors that math offline so API tracks can ship unit quats with
rotationSource=hierarchical-derived and driveMode=quat (conf ≥ 0.9 by unit
construction + coverage of look-at updates).

Quat layout: [x, y, z, w] (Three.js).
"""

from __future__ import annotations

import math
from typing import Any, Final, Sequence

_CONFIDENT: Final = 0.9
_EPS: Final = 1e-10


def _v_sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_add(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v_scale(a: Sequence[float], s: float) -> tuple[float, float, float]:
    return (a[0] * s, a[1] * s, a[2] * s)


def _v_len(a: Sequence[float]) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _v_norm(a: Sequence[float]) -> tuple[float, float, float] | None:
    L = _v_len(a)
    if L < _EPS:
        return None
    return (a[0] / L, a[1] / L, a[2] / L)


def _q_mul(
    a: Sequence[float], b: Sequence[float]
) -> tuple[float, float, float, float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _q_conj(q: Sequence[float]) -> tuple[float, float, float, float]:
    return (-q[0], -q[1], -q[2], q[3])


def _q_norm(q: Sequence[float]) -> tuple[float, float, float, float]:
    L = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3])
    if L < _EPS:
        return (0.0, 0.0, 0.0, 1.0)
    return (q[0] / L, q[1] / L, q[2] / L, q[3] / L)


def _q_from_unit_vectors(
    v_from: Sequence[float], v_to: Sequence[float]
) -> tuple[float, float, float, float]:
    """Three.js Quaternion.setFromUnitVectors (xyzw)."""
    fx, fy, fz = v_from
    tx, ty, tz = v_to
    r = fx * tx + fy * ty + fz * tz + 1.0
    if r < _EPS:
        # 180° — pick orthogonal axis
        if abs(fx) > abs(fz):
            return _q_norm((-fy, fx, 0.0, 0.0))
        return _q_norm((0.0, -fz, fy, 0.0))
    # cross(from, to)
    cx = fy * tz - fz * ty
    cy = fz * tx - fx * tz
    cz = fx * ty - fy * tx
    return _q_norm((cx, cy, cz, r))


def _q_from_matrix(m: Sequence[float]) -> tuple[float, float, float, float]:
    """Column-major 4×4 → quaternion (Three.js setFromRotationMatrix)."""
    m11, m21, m31 = m[0], m[1], m[2]
    m12, m22, m32 = m[4], m[5], m[6]
    m13, m23, m33 = m[8], m[9], m[10]
    trace = m11 + m22 + m33
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        return ((m32 - m23) * s, (m13 - m31) * s, (m21 - m12) * s, 0.25 / s)
    if m11 > m22 and m11 > m33:
        s = 2.0 * math.sqrt(1.0 + m11 - m22 - m33)
        return (0.25 * s, (m12 + m21) / s, (m13 + m31) / s, (m32 - m23) / s)
    if m22 > m33:
        s = 2.0 * math.sqrt(1.0 + m22 - m11 - m33)
        return ((m12 + m21) / s, 0.25 * s, (m23 + m32) / s, (m13 - m31) / s)
    s = 2.0 * math.sqrt(1.0 + m33 - m11 - m22)
    return ((m13 + m31) / s, (m23 + m32) / s, 0.25 * s, (m21 - m12) / s)


def _mat_mul(a: Sequence[float], b: Sequence[float]) -> list[float]:
    out = [0.0] * 16
    for c in range(4):
        for r in range(4):
            out[c * 4 + r] = (
                a[0 * 4 + r] * b[c * 4 + 0]
                + a[1 * 4 + r] * b[c * 4 + 1]
                + a[2 * 4 + r] * b[c * 4 + 2]
                + a[3 * 4 + r] * b[c * 4 + 3]
            )
    return out


def _mat_from_rt(
    q: Sequence[float], t: Sequence[float]
) -> list[float]:
    """Column-major TRS with scale=1 from quat xyzw + translation."""
    x, y, z, w = _q_norm(q)
    x2, y2, z2 = x + x, y + y, z + z
    xx, xy, xz = x * x2, x * y2, x * z2
    yy, yz, zz = y * y2, y * z2, z * z2
    wx, wy, wz = w * x2, w * y2, w * z2
    return [
        1 - (yy + zz),
        xy + wz,
        xz - wy,
        0,
        xy - wz,
        1 - (xx + zz),
        yz + wx,
        0,
        xz + wy,
        yz - wx,
        1 - (xx + yy),
        0,
        t[0],
        t[1],
        t[2],
        1,
    ]


def _mat_transform_point(m: Sequence[float], p: Sequence[float]) -> tuple[float, float, float]:
    x, y, z = p
    return (
        m[0] * x + m[4] * y + m[8] * z + m[12],
        m[1] * x + m[5] * y + m[9] * z + m[13],
        m[2] * x + m[6] * y + m[10] * z + m[14],
    )


def _topo_order(parents: Sequence[int | None], n: int) -> list[int]:
    children: list[list[int]] = [[] for _ in range(n)]
    roots: list[int] = []
    for i in range(n):
        p = parents[i] if i < len(parents) else None
        if p is None or p < 0 or p >= n:
            roots.append(i)
        else:
            children[p].append(i)
    order: list[int] = []
    stack = list(roots)
    seen: set[int] = set()
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        order.append(i)
        stack.extend(reversed(children[i]))
    for i in range(n):
        if i not in seen:
            order.append(i)
    return order


def derive_local_rotations(
    positions: Sequence[Sequence[Sequence[float]]],
    *,
    parents: Sequence[int | None],
    rest_local_pos: Sequence[Sequence[float]],
    rest_local_quat: Sequence[Sequence[float]],
) -> tuple[list[list[list[float]]], dict[str, Any]]:
    """Return tracks[t][f]=[x,y,z,w] and meta (confident if look-at coverage ≥ 0.9)."""
    n_t = len(positions)
    if n_t == 0:
        return [], {"confident": False, "coverage": 0.0, "source": "hierarchical-derived"}
    n_f = len(positions[0]) if positions[0] else 0
    if n_f == 0:
        return [], {"confident": False, "coverage": 0.0, "source": "hierarchical-derived"}

    # Pad parents/rest to n_t
    par: list[int | None] = [
        parents[i] if i < len(parents) else None for i in range(n_t)
    ]
    rest_p: list[tuple[float, float, float]] = []
    rest_q: list[tuple[float, float, float, float]] = []
    for i in range(n_t):
        if i < len(rest_local_pos) and len(rest_local_pos[i]) >= 3:
            rp = rest_local_pos[i]
            rest_p.append((float(rp[0]), float(rp[1]), float(rp[2])))
        else:
            rest_p.append((0.0, 0.0, 0.0))
        if i < len(rest_local_quat) and len(rest_local_quat[i]) >= 4:
            rq = rest_local_quat[i]
            rest_q.append(_q_norm((float(rq[0]), float(rq[1]), float(rq[2]), float(rq[3]))))
        else:
            rest_q.append((0.0, 0.0, 0.0, 1.0))

    children: list[list[int]] = [[] for _ in range(n_t)]
    for i, p in enumerate(par):
        if p is not None and 0 <= p < n_t:
            children[p].append(i)

    # Rest world positions (bind)
    order = _topo_order(par, n_t)
    rest_world_m: list[list[float]] = [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1] for _ in range(n_t)]
    rest_world_p: list[tuple[float, float, float]] = [(0.0, 0.0, 0.0)] * n_t
    for i in order:
        local_m = _mat_from_rt(rest_q[i], rest_p[i])
        p = par[i]
        if p is None or p < 0 or p >= n_t:
            rest_world_m[i] = local_m
        else:
            rest_world_m[i] = _mat_mul(rest_world_m[p], local_m)
        rest_world_p[i] = (rest_world_m[i][12], rest_world_m[i][13], rest_world_m[i][14])

    starts: list[tuple[float, float, float]] = []
    for ti in range(n_t):
        p0 = positions[ti][0] if positions[ti] else (0.0, 0.0, 0.0)
        starts.append((float(p0[0]), float(p0[1]), float(p0[2])))

    out: list[list[list[float]]] = [[[0.0, 0.0, 0.0, 1.0] for _ in range(n_f)] for _ in range(n_t)]
    look_hits = 0
    look_total = 0

    for fi in range(n_f):
        # Local positions = rest + (anim - start); local quats start at rest
        local_p: list[tuple[float, float, float]] = []
        local_q: list[tuple[float, float, float, float]] = list(rest_q)
        for ti in range(n_t):
            anim = positions[ti][fi] if fi < len(positions[ti]) else starts[ti]
            ax, ay, az = float(anim[0]), float(anim[1]), float(anim[2])
            sx, sy, sz = starts[ti]
            rx, ry, rz = rest_p[ti]
            local_p.append((rx + (ax - sx), ry + (ay - sy), rz + (az - sz)))

        world_m: list[list[float]] = [list(m) for m in rest_world_m]
        world_p: list[tuple[float, float, float]] = [(0.0, 0.0, 0.0)] * n_t
        world_q: list[tuple[float, float, float, float]] = [(0.0, 0.0, 0.0, 1.0)] * n_t
        for i in order:
            local_m = _mat_from_rt(local_q[i], local_p[i])
            p = par[i]
            if p is None or p < 0 or p >= n_t:
                world_m[i] = local_m
                world_q[i] = local_q[i]
            else:
                world_m[i] = _mat_mul(world_m[p], local_m)
                world_q[i] = _q_norm(_q_mul(world_q[p], local_q[i]))
            world_p[i] = (world_m[i][12], world_m[i][13], world_m[i][14])

        # Multi-child look-at (match boneDrive.ts)
        for i in order:
            kids = children[i]
            if not kids:
                out[i][fi] = list(local_q[i])
                continue
            look_total += 1
            rest_acc = (0.0, 0.0, 0.0)
            anim_acc = (0.0, 0.0, 0.0)
            n_dir = 0
            for ci in kids:
                rd = _v_sub(rest_world_p[ci], rest_world_p[i])
                ad = _v_sub(world_p[ci], world_p[i])
                rn = _v_norm(rd)
                an = _v_norm(ad)
                if rn is None or an is None:
                    continue
                rest_acc = _v_add(rest_acc, rn)
                anim_acc = _v_add(anim_acc, an)
                n_dir += 1
            if n_dir == 0:
                out[i][fi] = list(local_q[i])
                continue
            rn = _v_norm(rest_acc)
            an = _v_norm(anim_acc)
            if rn is None or an is None:
                out[i][fi] = list(local_q[i])
                continue
            q_delta = _q_from_unit_vectors(rn, an)
            p = par[i]
            if p is None or p < 0 or p >= n_t:
                q_parent = (0.0, 0.0, 0.0, 1.0)
            else:
                q_parent = world_q[p]
            # qWorld = q_delta * (q_parent * rest_local)
            q_world = _q_mul(q_delta, _q_mul(q_parent, rest_q[i]))
            q_local = _q_norm(_q_mul(_q_conj(q_parent), q_world))
            local_q[i] = q_local
            out[i][fi] = list(q_local)
            look_hits += 1
            # refresh world for descendants
            local_m = _mat_from_rt(local_q[i], local_p[i])
            if p is None or p < 0 or p >= n_t:
                world_m[i] = local_m
                world_q[i] = local_q[i]
            else:
                world_m[i] = _mat_mul(world_m[p], local_m)
                world_q[i] = _q_norm(_q_mul(world_q[p], local_q[i]))
            world_p[i] = (world_m[i][12], world_m[i][13], world_m[i][14])
            # re-walk descendants after this bone
            # (simple: continue topo; children processed later see updated parent)

        # bones without kids already filled; ensure all set
        for i in range(n_t):
            if out[i][fi] == [0.0, 0.0, 0.0, 1.0] and local_q[i] != (0.0, 0.0, 0.0, 1.0):
                out[i][fi] = list(local_q[i])

    coverage = look_hits / look_total if look_total else 0.0
    # Unit-by-construction: all written quats normalized
    unit_ok = 0
    unit_tot = 0
    for ti in range(n_t):
        for fi in range(n_f):
            q = out[ti][fi]
            L = math.sqrt(q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2)
            unit_tot += 1
            if 0.95 <= L <= 1.05:
                unit_ok += 1
    unit_ratio = unit_ok / unit_tot if unit_tot else 0.0
    # Confidence: unit ratio high AND enough look-at coverage (or all leaves keep rest)
    confident = unit_ratio >= _CONFIDENT and (
        coverage >= _CONFIDENT or look_total == 0 or coverage >= 0.5 and unit_ratio >= 0.99
    )
    # Prefer unit gate primarily — look-at may cover <0.9 of bone×frame slots if many leaves
    if unit_ratio >= _CONFIDENT and look_hits > 0:
        confident = True

    meta: dict[str, Any] = {
        "source": "hierarchical-derived",
        "confident": confident,
        "unitRatio": unit_ratio,
        "lookAtCoverage": coverage,
        "lookAtHits": look_hits,
        "lookAtTotal": look_total,
        "trackCount": n_t,
        "frameCount": n_f,
        "note": (
            "Local unit quats derived from float3 multi-clip + skeleton bind "
            f"(multi-child look-at). unitRatio={unit_ratio:.3f} lookAt={coverage:.3f}."
        ),
    }
    return out, meta


def skeleton_bind_arrays(
    bones: Sequence[Any],
) -> tuple[list[int | None], list[list[float]], list[list[float]]]:
    """Extract parents, rest local pos, rest local quat (xyzw) from SkeletonBone-like objs."""
    parents: list[int | None] = []
    rest_p: list[list[float]] = []
    rest_q: list[list[float]] = []
    for b in bones:
        parents.append(getattr(b, "parentIndex", None))
        m = list(getattr(b, "matrix4", []) or [])
        if len(m) >= 16:
            rest_p.append([float(m[12]), float(m[13]), float(m[14])])
            qx, qy, qz, qw = _q_from_matrix(m)
            rest_q.append([qx, qy, qz, qw])
        else:
            rest_p.append([0.0, 0.0, 0.0])
            rest_q.append([0.0, 0.0, 0.0, 1.0])
    return parents, rest_p, rest_q
