"""Fantasy Tennis .tex ↔ DDS (XOR first 128 bytes with 0xFF)."""

from __future__ import annotations

from pathlib import Path

# Symmetric with mesh_codec.decrypt_tex_to_dds
_XOR_LIMIT = 128


def xor_tex_header(data: bytes) -> bytes:
    out = bytearray(data)
    for i in range(min(_XOR_LIMIT, len(out))):
        out[i] ^= 0xFF
    return bytes(out)


def dds_to_tex(dds: bytes) -> bytes:
    """Encode DDS bytes as client .tex (same XOR as decrypt)."""
    if len(dds) < 4 or dds[:4] not in (b"DDS ", b"\xbb\xbb\xac\xdf"):
        # Accept already-XOR'd or raw; if magic is DDS space, XOR once.
        if dds[:4] == b"DDS ":
            return xor_tex_header(dds)
        # Already tex-like: leave as-is if re-XOR would make DDS
        trial = xor_tex_header(dds)
        if trial[:4] == b"DDS ":
            return dds
        return xor_tex_header(dds)
    return xor_tex_header(dds)


def tex_to_dds(tex: bytes) -> bytes:
    return xor_tex_header(tex)


def write_tex_from_dds(dds_path: Path, tex_path: Path) -> dict[str, int | str]:
    dds = dds_path.read_bytes()
    tex = dds_to_tex(dds)
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_bytes(tex)
    return {"ok": True, "path": str(tex_path), "bytes": len(tex)}
