"""Stage texture + UV helpers for Fantasy Tennis Content Studio.

Community RE (ft_restool Crypter, 3D Object Converter, Discord):
- .tex files are DDS with the first 128 bytes XOR'd with 0xFF (full-file XOR also works).
- Mesh DATs hold geometry only — no embedded color; stage color lives in Tex*.res.
- DX9 FVF often interleaves pos/normal/UV (32 B) but multi-stride recovery may
  only recover pos at s16; when real UVs are absent we planar-map from XZ.

See: https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dfvf
"""

from __future__ import annotations

import io
import math
import struct
import zipfile
from pathlib import Path
from typing import Any

from mesh_codec import decrypt_tex_to_dds


# Member prefix → preferred stock stage albedo (lawn / court coat).
_MEMBER_TEXTURE_HINTS: list[tuple[str, str, str]] = [
    ("BF_", "Res/Stage/Tex005.res", "BF_Lawn00_A.tex"),
    ("TU_", "Res/Stage/Tex005.res", "BF_Lawn00_A.tex"),  # fallback lawn until TU-specific found
    ("SV_", "Res/Stage/Tex005.res", "BF_Lawn00_A.tex"),
    ("AS_", "Res/Stage/Tex002.res", "AS_Coat00_D.tex"),
    ("SM_", "Res/Stage/Tex005.res", "BF_Lawn00_A.tex"),
]


def generate_planar_uvs(
    positions: list[list[float]],
) -> tuple[list[list[float]], str]:
    """Project positions onto XZ as UVs in [0,1] (stage ground plane)."""
    if not positions:
        return [], "empty"
    xs = [p[0] for p in positions]
    zs = [p[2] for p in positions]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    span_x = max(max_x - min_x, 1e-6)
    span_z = max(max_z - min_z, 1e-6)
    uvs = [[(p[0] - min_x) / span_x, (p[2] - min_z) / span_z] for p in positions]
    return uvs, "planar-xz"


def try_recover_interleaved_uvs(
    data: bytes,
    *,
    vertex_offset: int,
    vertex_stride: int,
    vertex_count: int,
) -> tuple[list[list[float]], str] | None:
    """Best-effort UV recovery from pos+… interleaved records (DX9-style)."""
    if vertex_stride < 20 or vertex_count < 3:
        return None
    best: tuple[float, int, list[list[float]]] | None = None
    # UV usually sits after position (and often after normals): try common offsets.
    for uv_off in range(12, vertex_stride - 7, 4):
        uvs: list[list[float]] = []
        in01 = 0
        for i in range(vertex_count):
            base = vertex_offset + i * vertex_stride
            if base + uv_off + 8 > len(data):
                break
            u, v = struct.unpack_from("<ff", data, base + uv_off)
            if not (math.isfinite(u) and math.isfinite(v)):
                break
            if abs(u) > 20 or abs(v) > 20:
                break
            uvs.append([float(u), float(v)])
            if -0.05 <= u <= 1.05 and -0.05 <= v <= 1.05:
                in01 += 1
        if len(uvs) < vertex_count * 0.9:
            continue
        ratio = in01 / len(uvs)
        if ratio < 0.55:
            continue
        score = ratio * len(uvs)
        if best is None or score > best[0]:
            best = (score, uv_off, uvs)
    if best is None:
        return None
    return best[2], f"interleaved-s{vertex_stride}-uv{best[1]}"


def resolve_material_texture(
    client_root: Path, material_name: str
) -> dict[str, str] | None:
    """Resolve a DAT-embedded material basename (e.g. BF_Lawn00_A) to a .tex member."""
    candidates = [material_name]
    if not material_name.lower().endswith(".tex"):
        candidates.append(f"{material_name}.tex")
    # Prefer non-SM/LM albedo when material list has shadowmap variants
    base = material_name
    for suffix in ("_SM", "_LM", "_MI"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            candidates.insert(0, f"{base}.tex")
            candidates.insert(0, base)
    stage = client_root / "Res" / "Stage"
    if not stage.is_dir():
        return None
    for res_path in sorted(stage.glob("Tex*.res")):
        try:
            with zipfile.ZipFile(res_path) as zf:
                names = set(zf.namelist())
        except zipfile.BadZipFile:
            continue
        for cand in candidates:
            tex = cand if cand.lower().endswith(".tex") else f"{cand}.tex"
            if tex in names:
                rel = str(res_path.relative_to(client_root)).replace("\\", "/")
                return {"archive": rel, "member": tex, "material": material_name}
    return None


def resolve_stage_texture(
    client_root: Path, member: str
) -> dict[str, str] | None:
    """Pick a stock stage albedo tex for a mesh member name."""
    # Prefer DAT-embedded multi-material names when the mesh is on disk.
    try:
        from mesh_meta import extract_material_names

        # Caller may pass member only — try common Mesh*.res
        stage = client_root / "Res" / "Stage"
        if stage.is_dir() and member.lower().endswith(".dat"):
            for res_path in sorted(stage.glob("Mesh*.res")):
                try:
                    with zipfile.ZipFile(res_path) as zf:
                        if member not in zf.namelist():
                            continue
                        data = zf.read(member)
                except zipfile.BadZipFile:
                    continue
                mats = extract_material_names(data)
                # Prefer lawn/coat/ground albedo over net/SM
                preferred = sorted(
                    mats,
                    key=lambda m: (
                        0
                        if any(k in m["name"] for k in ("Lawn", "Coat00", "Land", "Court", "Ground"))
                        and not m["name"].endswith(("_SM", "_LM"))
                        else 1
                        if not m["name"].endswith(("_SM", "_LM"))
                        else 2
                    ),
                )
                for mat in preferred:
                    hit = resolve_material_texture(client_root, mat["name"])
                    if hit:
                        hit["source"] = "dat-material"
                        return hit
    except Exception:
        pass

    upper = member.upper()
    for prefix, archive, tex_member in _MEMBER_TEXTURE_HINTS:
        if not upper.startswith(prefix):
            continue
        archive_path = client_root / archive
        if not archive_path.is_file():
            continue
        try:
            with zipfile.ZipFile(archive_path) as handle:
                if tex_member not in handle.namelist():
                    # fuzzy: first matching prefix in archive
                    candidates = [
                        n
                        for n in handle.namelist()
                        if n.upper().startswith(prefix.rstrip("_"))
                        and n.lower().endswith(".tex")
                    ]
                    if not candidates:
                        continue
                    tex_member = candidates[0]
        except zipfile.BadZipFile:
            continue
        return {
            "archive": archive.replace("\\", "/"),
            "member": tex_member,
            "source": "stage-prefix-hint",
        }
    # Broad search: any Tex*.res member sharing 2-letter stage code
    code = member[:2].upper() if len(member) >= 2 else ""
    stage = client_root / "Res" / "Stage"
    if not stage.is_dir() or not code:
        return None
    for archive_path in sorted(stage.glob("Tex*.res")):
        try:
            with zipfile.ZipFile(archive_path) as handle:
                for name in handle.namelist():
                    if name.upper().startswith(code + "_") and name.lower().endswith(
                        ".tex"
                    ):
                        rel = str(archive_path.relative_to(client_root)).replace(
                            "\\", "/"
                        )
                        return {
                            "archive": rel,
                            "member": name,
                            "source": "stage-code-scan",
                        }
        except zipfile.BadZipFile:
            continue
    return None


def tex_to_png_bytes(tex_data: bytes) -> bytes:
    """Decrypt .tex → DDS (restool XOR) then rasterize to PNG via Pillow."""
    from PIL import Image

    dds = decrypt_tex_to_dds(tex_data)
    image = Image.open(io.BytesIO(dds))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def load_stage_texture_png(
    client_root: Path, archive: str, member: str
) -> bytes:
    with zipfile.ZipFile(client_root / archive) as handle:
        raw = handle.read(member)
    return tex_to_png_bytes(raw)


def attach_uvs_and_texture_meta(
    *,
    client_root: Path,
    data: bytes,
    member: str,
    positions: list[list[float]],
    vertex_offset: int,
    vertex_stride: int,
) -> dict[str, Any]:
    """Return uvs, uvMode, and optional texture ref for a decoded mesh."""
    recovered = try_recover_interleaved_uvs(
        data,
        vertex_offset=vertex_offset,
        vertex_stride=vertex_stride,
        vertex_count=len(positions),
    )
    if recovered is not None:
        uvs, uv_mode = recovered
    else:
        uvs, uv_mode = generate_planar_uvs(positions)
    texture = resolve_stage_texture(client_root, member)
    return {
        "uvs": uvs,
        "uvMode": uv_mode,
        "uvCount": len(uvs),
        "texture": texture,
    }
