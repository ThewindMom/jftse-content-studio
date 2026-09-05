"""Best-effort Fantasy Tennis Stage/Sky/Collision .dat mesh codec.

Public reverse-engineering notes (2026-08):
- Client packs meshes inside ZIP-like .res archives (e.g. Res/Stage/Mesh01.res).
- Members are proprietary little-endian .dat blobs (no public schema found;
  FantasyTennis.Ghidra exists but does not document mesh layout).
- Observed header: 12 x uint32, then mixed records; dense float3 runs carry
  positions used for court/prop silhouettes. Normals/UVs are interleaved —
  flatness-only scoring picks UV channels (BF_Court01 s20 solidArea≈485).
- Community tooling (ft_restool): RES browser, FTM/DDS/IFL parsers, .tex XOR
  (0xFF) → DDS, AES for .set — no mesh DAT decoder. Discord RE: no color in
  mesh dats; re-texture via related .tex files.
- This codec multi-stride-scores float3 runs (reject cubes, unit-normals, UV
  clouds; reward XZ footprint), recovers uint16 indices, drops degenerates,
  and can write transforms back into the original vertex bytes.
"""

from __future__ import annotations

import json
import math
import struct
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class MeshHeader:
    a: int
    b: int
    c: int
    d: int
    count1: int
    z1: int
    count2: int
    z2: int
    u8: int
    u9: int
    u10: int
    u11: int


@dataclass
class DecodedMesh:
    name: str
    archive: str
    member: str
    byteLength: int
    header: MeshHeader
    vertexOffset: int
    vertexCount: int
    indexCount: int
    positions: list[list[float]]
    indices: list[int]
    bounds: dict[str, list[float]]
    decodeMode: str
    vertexStride: int = 12
    uvs: list[list[float]] | None = None
    uvMode: str = "none"
    texture: dict[str, str] | None = None
    normals: list[list[float]] | None = None
    primitives: list[dict[str, Any]] | None = None
    materialSlots: list[dict[str, Any]] | None = None


def parse_header(data: bytes) -> MeshHeader:
    values = struct.unpack_from("<12I", data, 0)
    return MeshHeader(*values)


def _is_plausible_vertex(x: float, y: float, z: float, *, max_abs: float = 2500.0) -> bool:
    if not all(math.isfinite(v) for v in (x, y, z)):
        return False
    if max(abs(x), abs(y), abs(z)) > max_abs:
        return False
    return abs(x) + abs(y) + abs(z) > 1e-4


def _extent_of(run: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    xs = [v[0] for v in run]
    ys = [v[1] for v in run]
    zs = [v[2] for v in run]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def _unitish_frac(run: list[tuple[float, float, float]]) -> float:
    """Fraction of vertices that look like unit normals (common interleaved channel)."""
    if not run:
        return 0.0
    hits = 0
    for x, y, z in run:
        length = math.sqrt(x * x + y * y + z * z)
        if 0.85 <= length <= 1.15 and max(abs(x), abs(y), abs(z)) <= 1.2:
            hits += 1
    return hits / len(run)


def _uvish_frac(run: list[tuple[float, float, float]]) -> float:
    """Fraction of verts whose XY look like UV in [0,1] (false flat runs)."""
    if not run:
        return 0.0
    hits = 0
    for x, y, _z in run:
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
            hits += 1
    return hits / len(run)


def _footprint_xz(run: list[tuple[float, float, float]]) -> float:
    """Convex-hull area of points projected onto XZ (stage ground plane)."""
    pts = sorted({(round(x, 2), round(z, 2)) for x, _y, z in run})
    if len(pts) < 3:
        return 0.0

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    area = 0.0
    for i, (x1, z1) in enumerate(hull):
        x2, z2 = hull[(i + 1) % len(hull)]
        area += x1 * z2 - x2 * z1
    return abs(area) * 0.5


def _score_vertex_run(run: list[tuple[float, float, float]]) -> float:
    """Prefer real stage geometry over cube noise, unit-normal clouds, and UV channels.

    History: longest float3 run → cubic noise. Flatness-only multi-stride then
    preferred UV/normal s20 runs on BF_Court01 (Y extent ≈ 1, solid area ~485).
    Reward XZ footprint + large-coordinate positions; penalize unit/UV-like verts.
    """
    if len(run) < 32:
        return -1.0
    ext = _extent_of(run)
    max_e = max(ext)
    if max_e < 1.0:
        return -1.0
    ratios = sorted(e / max_e for e in ext)
    unit = _unitish_frac(run)
    uvish = _uvish_frac(run)
    # Unit-normal / UV false positives (restool community: no color in mesh dats;
    # interleaved normals/UVs are the usual contaminators).
    if unit > 0.4:
        return len(run) * 0.02
    cubeish = ratios[0] > 0.85 and ratios[1] > 0.85
    if cubeish:
        return len(run) * 0.05
    flat = 1.0 - ratios[0]
    footprint = _footprint_xz(run)
    fp_term = min(footprint / 5000.0, 6.0)
    big = sum(1 for x, y, z in run if max(abs(x), abs(y), abs(z)) > 2.0) / len(run)
    score = float(len(run)) * (1.0 + 1.5 * flat) * (1.0 + 0.25 * fp_term) * (0.2 + 0.8 * big)
    score *= (1.0 - 0.85 * unit) * (1.0 - 0.7 * uvish)
    # Ultra-flat + UV-like is almost always a wrong channel pick.
    if ratios[0] < 0.02 and uvish > 0.15:
        score *= 0.15
    return score


def _triangle_stats(
    positions: list[list[float]] | list[tuple[float, float, float]],
    indices: list[int],
) -> tuple[int, int, float, list[int]]:
    """Return (valid, degenerate, solid_area, filtered_indices)."""
    valid = 0
    degen = 0
    area = 0.0
    filtered: list[int] = []
    n = len(positions)
    for i in range(0, len(indices) - 2, 3):
        a, b, c = indices[i], indices[i + 1], indices[i + 2]
        if max(a, b, c) >= n:
            degen += 1
            continue
        ax, ay, az = positions[a]
        bx, by, bz = positions[b]
        cx, cy, cz = positions[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        tri_area = math.sqrt(nx * nx + ny * ny + nz * nz) * 0.5
        if tri_area < 1e-8:
            degen += 1
            continue
        valid += 1
        area += tri_area
        filtered.extend([a, b, c])
    return valid, degen, area, filtered


def find_vertex_run(
    data: bytes, start: int = 48
) -> tuple[int, list[tuple[float, float, float]], int]:
    """Return (byte_offset, positions, stride) for the best-scoring float3 run.

    Fantasy Tennis stage DATs often interleave position with other channels
    (normals/UVs). Scanning only tightly packed float3 (stride 12) prefers long
    cubic noise runs. Multi-stride scoring recovers flatter court silhouettes.
    """
    best_offset = start
    best_run: list[tuple[float, float, float]] = []
    best_score = -1.0
    best_stride = 12
    end = len(data) - 12
    # Tight abs cap rejects the huge cubic noise shells seen on some courts.
    for stride in (12, 16, 20, 24, 32):
        for pos_off in range(0, max(1, stride - 11), 4):
            if pos_off + 12 > stride:
                continue
            i = start
            while i <= end:
                run: list[tuple[float, float, float]] = []
                j = i
                while j + pos_off + 12 <= len(data):
                    x, y, z = struct.unpack_from("<fff", data, j + pos_off)
                    if not _is_plausible_vertex(x, y, z, max_abs=1200.0):
                        break
                    run.append((x, y, z))
                    j += stride
                    if len(run) > 80_000:
                        break
                if len(run) >= 48:
                    score = _score_vertex_run(run)
                    if score > best_score:
                        best_score = score
                        best_offset = i + pos_off
                        best_run = run
                        best_stride = stride
                    i = j if j > i else i + 4
                else:
                    i += 4
    return best_offset, best_run, best_stride


def find_u16_indices(
    data: bytes,
    vertex_count: int,
    start: int,
    *,
    positions: list[list[float]] | list[tuple[float, float, float]] | None = None,
) -> list[int]:
    """Recover u16 triangle indices; prefer max solid-area × coverage (RE 2026-08).

    First-long-run heuristic often locks onto a sparse false buffer. Scanning from
    the vertex block and scoring by non-degenerate triangle area recovers denser
    topology (e.g. BF_Court01: 322 → ~580 solid tris, ~15% → ~39% vert coverage).
    """
    if start >= len(data) - 6 or vertex_count < 3:
        return []
    limit = len(data) - 2
    cursor = start if start % 2 == 0 else start + 1
    best: list[int] = []
    best_score = -1.0
    min_len = max(48, vertex_count // 8)
    max_vals = min(vertex_count * 8, 24_000)
    # Coarse then fine: step 4 then refine winners ±8 — full step-2 is O(file*verts).
    candidates: list[tuple[float, int, list[int]]] = []
    while cursor + 6 <= limit:
        values: list[int] = []
        bad = 0
        pos = cursor
        while pos + 2 <= limit and len(values) < max_vals:
            value = struct.unpack_from("<H", data, pos)[0]
            if value >= vertex_count:
                bad += 1
                if bad > 8:
                    break
            else:
                values.append(value)
                bad = 0
            pos += 2
        if len(values) >= min_len:
            tri = values[: len(values) // 3 * 3]
            if positions is not None and len(positions) == vertex_count:
                valid, _degen, area, filtered = _triangle_stats(positions, tri)
                if valid >= 24:
                    used = len(set(filtered))
                    cov = used / max(vertex_count, 1)
                    score = float(area) * (0.35 + 0.65 * cov) * math.log10(valid + 1)
                    if score > best_score:
                        best_score = score
                        best = filtered
                        candidates.append((score, cursor, filtered))
            elif len(tri) > len(best):
                best = tri
        cursor += 4  # coarse stride; refine below
    if positions is not None and candidates:
        # Refine around top coarse hits with step-2.
        top = sorted(candidates, key=lambda t: -t[0])[:6]
        for _sc, off, _filt in top:
            for delta in range(-6, 8, 2):
                c2 = off + delta
                if c2 < start or c2 + 6 > limit:
                    continue
                values = []
                bad = 0
                pos = c2
                while pos + 2 <= limit and len(values) < max_vals:
                    value = struct.unpack_from("<H", data, pos)[0]
                    if value >= vertex_count:
                        bad += 1
                        if bad > 8:
                            break
                    else:
                        values.append(value)
                        bad = 0
                    pos += 2
                if len(values) < min_len:
                    continue
                tri = values[: len(values) // 3 * 3]
                valid, _degen, area, filtered = _triangle_stats(positions, tri)
                if valid < 24:
                    continue
                used = len(set(filtered))
                cov = used / max(vertex_count, 1)
                score = float(area) * (0.35 + 0.65 * cov) * math.log10(valid + 1)
                if score > best_score:
                    best_score = score
                    best = filtered
    if len(best) < 3:
        return []
    return best[: len(best) // 3 * 3]


def decode_mesh_bytes(
    data: bytes,
    *,
    name: str,
    archive: str = "",
    member: str = "",
    max_vertices: int = 40_000,
) -> DecodedMesh:
    header = parse_header(data) if len(data) >= 48 else MeshHeader(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    identity = (member or name).replace("\\", "/").rsplit("/", 1)[-1].lower()
    if identity in ("sv_court.dat", "sv_all.dat"):
        from twinkle_mesh import bounds, parse_twinkle_static

        static = parse_twinkle_static(data)
        if static is not None:
            positions, normals, uvs, indices = [], [], [], []
            for primitive in static["primitives"]:
                base = len(positions)
                primitive["vertexStart"] = base
                primitive["indexStart"] = len(indices)
                positions.extend(primitive["positions"])
                normals.extend(primitive["normals"])
                uvs.extend(primitive["uvs"])
                indices.extend(base + i for i in primitive["indices"])
            # max_vertices limits heuristic previews only. Never truncate a
            # validated static asset or splice triangles across its children.
            return DecodedMesh(
                name=name, archive=archive, member=member, byteLength=len(data),
                header=header, vertexOffset=static["primitives"][0]["vertexOffset"],
                vertexCount=len(positions), indexCount=len(indices),
                positions=positions, indices=indices, bounds=bounds(positions),
                decodeMode="indexed-twinkle-static", vertexStride=0,
                normals=normals, uvs=uvs, uvMode="adu-uv0",
                primitives=static["primitives"], materialSlots=static["materials"],
            )
    offset, run, stride = find_vertex_run(data)
    if not run:
        raise ValueError("NO_VERTEX_RUN")
    # Indices usually trail the vertex block; stride-aware end offset.
    index_start = offset - (offset % 2) + max(len(run) * stride, len(run) * 12)
    positions_probe = [[float(x), float(y), float(z)] for x, y, z in run]
    indices = find_u16_indices(
        data,
        len(run),
        min(index_start, len(data) - 6),
        positions=positions_probe,
    )
    had_indices = bool(indices)
    if not indices:
        indices = []
        capped = min(len(run), max_vertices)
        for i in range(0, capped - 2, 3):
            indices.extend([i, i + 1, i + 2])
    if len(run) > max_vertices:
        run = run[:max_vertices]
        positions_probe = positions_probe[:max_vertices]
        indices = [i for i in indices if i < max_vertices]
        indices = indices[: len(indices) // 3 * 3]
    positions = positions_probe
    _valid, _degen, _area, indices = _triangle_stats(positions, indices)
    mode = f"indexed-s{stride}" if had_indices else f"triangle-soup-s{stride}"
    xs = [v[0] for v in positions]
    ys = [v[1] for v in positions]
    zs = [v[2] for v in positions]
    return DecodedMesh(
        name=name,
        archive=archive,
        member=member,
        byteLength=len(data),
        header=header,
        vertexOffset=offset,
        vertexCount=len(positions),
        indexCount=len(indices),
        positions=positions,
        indices=indices,
        bounds={
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        },
        decodeMode=mode,
        vertexStride=stride,
    )


def compute_vertex_normals(
    positions: list[list[float]], indices: list[int]
) -> list[list[float]]:
    normals = [[0.0, 0.0, 0.0] for _ in positions]
    for i in range(0, len(indices) - 2, 3):
        ia, ib, ic = indices[i], indices[i + 1], indices[i + 2]
        if max(ia, ib, ic) >= len(positions):
            continue
        ax, ay, az = positions[ia]
        bx, by, bz = positions[ib]
        cx, cy, cz = positions[ic]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        for idx in (ia, ib, ic):
            normals[idx][0] += nx
            normals[idx][1] += ny
            normals[idx][2] += nz
    out: list[list[float]] = []
    for nx, ny, nz in normals:
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-12:
            out.append([0.0, 1.0, 0.0])
        else:
            out.append([nx / length, ny / length, nz / length])
    return out


def decode_confidence(mesh: DecodedMesh) -> dict[str, Any]:
    valid, degen, solid_area, _filtered = _triangle_stats(mesh.positions, mesh.indices)
    tri = max(0, mesh.indexCount // 3)
    density = mesh.vertexCount / max(mesh.byteLength, 1)
    score = 0.2
    if mesh.vertexCount >= 3:
        score += 0.25
    has_indices = mesh.decodeMode.startswith("indexed")
    if has_indices and tri >= 1:
        score += 0.35
    elif tri >= 1:
        score += 0.15
    if 0.001 <= density <= 0.2:
        score += 0.1
    bounds = mesh.bounds
    extent = (
        [bounds["max"][i] - bounds["min"][i] for i in range(3)]
        if bounds.get("max") and bounds.get("min")
        else [0, 0, 0]
    )
    if max(extent) > 1.0:
        score += 0.1
    # Reward real solid fill (UV/normal false runs score near zero here).
    if solid_area >= 10_000:
        score += 0.1
    elif solid_area >= 1_000:
        score += 0.05
    return {
        "score": round(min(score, 0.99), 3),
        "triangleCount": tri,
        "nonDegenerateTriangles": valid,
        "degenerateTriangles": degen,
        "solidArea": round(solid_area, 3),
        "bytesPerVertex": round(mesh.byteLength / max(mesh.vertexCount, 1), 3),
        "extent": extent,
        "hasIndices": has_indices,
        "footprintXZ": round(_footprint_xz([tuple(p) for p in mesh.positions]), 3),
    }


def mesh_to_obj(mesh: DecodedMesh) -> str:
    normals = mesh.normals or compute_vertex_normals(mesh.positions, mesh.indices)
    lines = [
        f"# JFTSE Content Studio mesh export: {mesh.name}",
        f"# mode={mesh.decodeMode}",
        f"# confidence={decode_confidence(mesh)['score']}",
    ]
    for x, y, z in mesh.positions:
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
    for nx, ny, nz in normals:
        lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")
    for i in range(0, len(mesh.indices), 3):
        a, b, c = mesh.indices[i], mesh.indices[i + 1], mesh.indices[i + 2]
        lines.append(
            f"f {a + 1}//{a + 1} {b + 1}//{b + 1} {c + 1}//{c + 1}"
        )
    return "\n".join(lines) + "\n"


def mesh_to_gltf(mesh: DecodedMesh) -> dict[str, Any]:
    import base64
    import array

    positions = array.array("f")
    for x, y, z in mesh.positions:
        positions.extend([x, y, z])
    normals = array.array("f")
    for nx, ny, nz in (mesh.normals or compute_vertex_normals(mesh.positions, mesh.indices)):
        normals.extend([nx, ny, nz])
    wide_indices = bool(mesh.primitives) and mesh.vertexCount > 65535
    indices = array.array("I" if wide_indices else "H", [
        i for i in mesh.indices if wide_indices or i < 65535
    ])
    if len(indices) >= 3 and len(indices) % 3:
        indices = indices[: len(indices) // 3 * 3]
    pos_bytes = positions.tobytes()
    nrm_bytes = normals.tobytes()
    idx_bytes = indices.tobytes()
    # Align buffer views to 4-byte boundaries for glTF accessors.
    pad0 = (4 - (len(idx_bytes) % 4)) % 4
    pad1 = (4 - (len(pos_bytes) % 4)) % 4
    blob = idx_bytes + (b"\x00" * pad0) + pos_bytes + (b"\x00" * pad1) + nrm_bytes
    b64 = base64.b64encode(blob).decode("ascii")
    idx_off = 0
    pos_off = len(idx_bytes) + pad0
    nrm_off = pos_off + len(pos_bytes) + pad1
    return {
        "asset": {"version": "2.0", "generator": "jftse-content-studio-mesh"},
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": mesh.name}],
        "meshes": [
            {
                "name": mesh.name,
                "primitives": [
                    {
                        "attributes": {"POSITION": 1, "NORMAL": 2},
                        "indices": 0,
                        "mode": 4,
                    }
                ],
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5125 if wide_indices else 5123,
                "count": len(indices),
                "type": "SCALAR",
            },
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": len(mesh.positions),
                "type": "VEC3",
                "max": mesh.bounds["max"],
                "min": mesh.bounds["min"],
            },
            {
                "bufferView": 2,
                "componentType": 5126,
                "count": len(mesh.positions),
                "type": "VEC3",
            },
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": idx_off,
                "byteLength": len(idx_bytes),
                "target": 34963,
            },
            {
                "buffer": 0,
                "byteOffset": pos_off,
                "byteLength": len(pos_bytes),
                "target": 34962,
            },
            {
                "buffer": 0,
                "byteOffset": nrm_off,
                "byteLength": len(nrm_bytes),
                "target": 34962,
            },
        ],
        "buffers": [
            {
                "byteLength": len(blob),
                "uri": f"data:application/octet-stream;base64,{b64}",
            }
        ],
        "extras": {"jftseConfidence": decode_confidence(mesh)},
    }


def apply_transform(
    positions: list[list[float]],
    *,
    translate: tuple[float, float, float] = (0.0, 0.0, 0.0),
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
    rotate_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> list[list[float]]:
    rx, ry, rz = [math.radians(v) for v in rotate_deg]
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    out: list[list[float]] = []
    for x0, y0, z0 in positions:
        x, y, z = x0 * scale[0], y0 * scale[1], z0 * scale[2]
        y, z = y * cx - z * sx, y * sx + z * cx
        x, z = x * cy + z * sy, -x * sy + z * cy
        x, y = x * cz - y * sz, x * sz + y * cz
        out.append([x + translate[0], y + translate[1], z + translate[2]])
    return out


def write_positions_into_dat(
    data: bytes,
    vertex_offset: int,
    positions: list[list[float]],
    *,
    stride: int = 12,
) -> bytes:
    """Write float3 positions back using the decode stride (not always tightly packed 12).

    Multi-stride courts (s16/s20/s24/s32) interleave normals/UVs between positions.
    Packing at *12 overwrites those channels and desyncs subsequent verts.
    """
    if stride < 12:
        raise ValueError(f"INVALID_VERTEX_STRIDE:{stride}")
    buf = bytearray(data)
    end = len(buf)
    for index, (x, y, z) in enumerate(positions):
        pos = vertex_offset + index * stride
        if pos + 12 > end:
            break
        struct.pack_into("<fff", buf, pos, float(x), float(y), float(z))
    return bytes(buf)


def decrypt_tex_to_dds(tex_data: bytes) -> bytes:
    """ft_restool Crypter: XOR first 128 bytes with 0xFF yields a DDS header/stream.

    Community RE (Discord/HxD): mesh dats have no color; stage/item color lives in
    paired .tex files inside Tex*.res archives. Full-file XOR is also valid DDS.
    """
    out = bytearray(tex_data)
    limit = min(128, len(out))
    for i in range(limit):
        out[i] ^= 0xFF
    return bytes(out)


def decoded_to_dict(mesh: DecodedMesh, *, include_geometry: bool = True) -> dict[str, Any]:
    payload = asdict(mesh)
    payload["header"] = asdict(mesh.header)
    payload["confidence"] = decode_confidence(mesh)
    payload["hasUvs"] = bool(mesh.uvs) and len(mesh.uvs) == mesh.vertexCount
    payload["uvMode"] = mesh.uvMode
    if not include_geometry:
        payload.pop("positions", None)
        payload.pop("indices", None)
        payload.pop("uvs", None)
        payload.pop("normals", None)
        for primitive in payload.get("primitives") or []:
            for field in ("positions", "indices", "uvs", "uv1", "normals"):
                primitive.pop(field, None)
    return payload


def client_dat_path_to_ref(path: str) -> dict[str, str] | None:
    """Convert stage script paths like Res/Stage/Mesh01/BF_Court01.dat to archive/member."""
    cleaned = path.replace("\\", "/").strip().strip('"')
    if not cleaned.lower().endswith(".dat"):
        return None
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) < 2:
        return None
    member = parts[-1]
    parent = "/".join(parts[:-1])
    archive = f"{parent}.res"
    return {"archive": archive, "member": member, "sourcePath": cleaned}


def list_mesh_members(client_root: Path) -> list[dict[str, Any]]:
    roots = [
        client_root / "Res" / "Stage",
        client_root / "Res" / "Sky",
        client_root / "Res",
    ]
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        paths = [root] if root.suffix == ".res" else sorted(root.glob("*.res"))
        if root.name == "Res":
            paths = [root / "Collision.res"] if (root / "Collision.res").exists() else []
        for archive_path in paths:
            if not archive_path.is_file():
                continue
            rel = str(archive_path.relative_to(client_root)).replace("\\", "/")
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    for member in archive.namelist():
                        if not member.lower().endswith(".dat"):
                            continue
                        key = f"{rel}::{member}"
                        if key in seen:
                            continue
                        seen.add(key)
                        info = archive.getinfo(member)
                        items.append(
                            {
                                "archive": rel,
                                "member": member,
                                "bytes": info.file_size,
                                "kind": _kind_for(rel, member),
                            }
                        )
            except zipfile.BadZipFile:
                continue
    items.sort(key=lambda row: (row["kind"], row["archive"], row["member"]))
    return items


def _kind_for(archive: str, member: str) -> str:
    lower = f"{archive} {member}".lower()
    if "collision" in lower or lower.startswith("col"):
        return "collision"
    if "/sky/" in lower or "sky" in member.lower():
        return "sky"
    if "court" in lower:
        return "court"
    if "stage" in lower:
        return "stage"
    return "mesh"


def decode_member(client_root: Path, archive_rel: str, member: str) -> DecodedMesh:
    archive_path = client_root / archive_rel
    with zipfile.ZipFile(archive_path) as archive:
        data = archive.read(member)
    mesh = decode_mesh_bytes(data, name=member, archive=archive_rel, member=member)
    if mesh.primitives is not None:
        # Per-child UV0 and texture bindings are already decoded. A single
        # guessed texture or contiguous UV scan would overwrite valid data.
        return mesh
    # Late import avoids circular import: mesh_texture depends on decrypt_tex_to_dds.
    from mesh_texture import attach_uvs_and_texture_meta

    meta = attach_uvs_and_texture_meta(
        client_root=client_root,
        data=data,
        member=member,
        positions=mesh.positions,
        vertex_offset=mesh.vertexOffset,
        vertex_stride=mesh.vertexStride,
    )
    mesh.uvs = meta["uvs"]
    mesh.uvMode = meta["uvMode"]
    mesh.texture = meta["texture"]
    return mesh
