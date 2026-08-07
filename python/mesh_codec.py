"""Best-effort Fantasy Tennis Stage/Sky/Collision .dat mesh codec.

Public reverse-engineering notes (2026-08):
- Client packs meshes inside ZIP-like .res archives (e.g. Res/Stage/Mesh01.res).
- Members are proprietary little-endian .dat blobs (no public schema found;
  FantasyTennis.Ghidra exists but does not document mesh layout).
- Observed header: 12 x uint32, then mixed records; dense float3 runs carry
  positions used for court/prop silhouettes.
- This codec recovers the longest plausible float3 run, builds a triangle soup
  (or recovered uint16 indices when present), and can write transforms back into
  the original vertex bytes for same-size round trips.
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


def parse_header(data: bytes) -> MeshHeader:
    values = struct.unpack_from("<12I", data, 0)
    return MeshHeader(*values)


def _is_plausible_vertex(x: float, y: float, z: float) -> bool:
    if not all(math.isfinite(v) for v in (x, y, z)):
        return False
    if max(abs(x), abs(y), abs(z)) > 5000:
        return False
    return abs(x) + abs(y) + abs(z) > 1e-4


def find_vertex_run(data: bytes, start: int = 48) -> tuple[int, list[tuple[float, float, float]]]:
    best_offset = start
    best_run: list[tuple[float, float, float]] = []
    i = start
    end = len(data) - 12
    while i <= end:
        run: list[tuple[float, float, float]] = []
        j = i
        while j <= end:
            x, y, z = struct.unpack_from("<fff", data, j)
            if not _is_plausible_vertex(x, y, z):
                break
            run.append((x, y, z))
            j += 12
            if len(run) > 120_000:
                break
        if len(run) >= 32:
            xs = [v[0] for v in run]
            ys = [v[1] for v in run]
            zs = [v[2] for v in run]
            span = (max(xs) - min(xs)) + (max(ys) - min(ys)) + (max(zs) - min(zs))
            if span > 0.5 and len(run) > len(best_run):
                best_offset = i
                best_run = run
            i = j if j > i else i + 4
        else:
            i += 4
    return best_offset, best_run


def find_u16_indices(data: bytes, vertex_count: int, start: int) -> list[int]:
    if start >= len(data) - 6 or vertex_count < 3:
        return []
    best: list[int] = []
    limit = min(len(data) - 2, start + min(2_000_000, vertex_count * 12 + 200_000))
    cursor = start if start % 2 == 0 else start + 1
    while cursor + 6 <= limit:
        values: list[int] = []
        bad = 0
        pos = cursor
        while pos + 2 <= limit and len(values) < vertex_count * 6:
            value = struct.unpack_from("<H", data, pos)[0]
            if value >= vertex_count:
                bad += 1
                if bad > 8:
                    break
            else:
                values.append(value)
                bad = 0
            pos += 2
        if len(values) >= max(96, vertex_count // 4) and len(values) > len(best):
            best = values
            break
        cursor += 2
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
    offset, run = find_vertex_run(data)
    if not run:
        raise ValueError("NO_VERTEX_RUN")
    indices = find_u16_indices(data, len(run), offset + len(run) * 12)
    mode = "indexed" if indices else "triangle-soup"
    if not indices:
        indices = []
        capped = min(len(run), max_vertices)
        for i in range(0, capped - 2, 3):
            indices.extend([i, i + 1, i + 2])
    if len(run) > max_vertices:
        run = run[:max_vertices]
        indices = [i for i in indices if i < max_vertices]
        indices = indices[: len(indices) // 3 * 3]
    xs = [v[0] for v in run]
    ys = [v[1] for v in run]
    zs = [v[2] for v in run]
    return DecodedMesh(
        name=name,
        archive=archive,
        member=member,
        byteLength=len(data),
        header=header,
        vertexOffset=offset,
        vertexCount=len(run),
        indexCount=len(indices),
        positions=[[float(x), float(y), float(z)] for x, y, z in run],
        indices=indices,
        bounds={
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        },
        decodeMode=mode,
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
    tri = max(0, mesh.indexCount // 3)
    density = mesh.vertexCount / max(mesh.byteLength, 1)
    score = 0.2
    if mesh.vertexCount >= 3:
        score += 0.25
    if mesh.decodeMode == "indexed" and tri >= 1:
        score += 0.35
    elif tri >= 1:
        score += 0.15
    if 0.001 <= density <= 0.2:
        score += 0.1
    bounds = mesh.bounds
    extent = [
        bounds["max"][i] - bounds["min"][i] for i in range(3)
    ] if bounds.get("max") and bounds.get("min") else [0, 0, 0]
    if max(extent) > 1.0:
        score += 0.1
    return {
        "score": round(min(score, 0.99), 3),
        "triangleCount": tri,
        "bytesPerVertex": round(mesh.byteLength / max(mesh.vertexCount, 1), 3),
        "extent": extent,
        "hasIndices": mesh.decodeMode == "indexed",
    }


def mesh_to_obj(mesh: DecodedMesh) -> str:
    normals = compute_vertex_normals(mesh.positions, mesh.indices)
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
    for nx, ny, nz in compute_vertex_normals(mesh.positions, mesh.indices):
        normals.extend([nx, ny, nz])
    indices = array.array("H", [i for i in mesh.indices if i < 65535])
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
                "componentType": 5123,
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


def write_positions_into_dat(data: bytes, vertex_offset: int, positions: list[list[float]]) -> bytes:
    buf = bytearray(data)
    for index, (x, y, z) in enumerate(positions):
        struct.pack_into("<fff", buf, vertex_offset + index * 12, float(x), float(y), float(z))
    return bytes(buf)


def decoded_to_dict(mesh: DecodedMesh, *, include_geometry: bool = True) -> dict[str, Any]:
    payload = asdict(mesh)
    payload["header"] = asdict(mesh.header)
    payload["confidence"] = decode_confidence(mesh)
    if not include_geometry:
        payload.pop("positions", None)
        payload.pop("indices", None)
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
    return decode_mesh_bytes(data, name=member, archive=archive_rel, member=member)
