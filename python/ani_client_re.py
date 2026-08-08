"""Client-backed ANI decoder reverse-engineering notes (read-only on FantaTennis.exe).

Evidence is static disassembly of PE32 `FantaTennis.exe` (image base 0x400000).
Stock client is never modified.

Key VAs (Local-Client / .jftse-client-linux FantaTennis.exe):
  - 0x5de920  .ani/.Ani/.ANI extension gate (strcmp-style), then stream open
  - 0x5dd8e0  serialize bone track: name[0x80] + flag + channels
  - 0x5dd620  read float3×N into buffer (via 0x608f10)
  - 0x5dd640  read float4×N  ← runtime rotation channel
  - 0x5dd680  read float7×N
  - 0x5dd660  read float1×N
  - 0x5dd6a0  read float2×N
  - 0x5e08d0  dense per-track load of f3/f4/f7/f1/f2 × frameCount
  - 0x5e0fa0  parse after 0x608e70 buffer bind (frameCount @+0x114, tracks @+0x36c)
  - 0x5e0ee0 / 0x5e11d0  read 3×u32 then bulk n0 dwords; bind mid/end ptrs
  - 0x608e70  bind stream cursor (start, mid, end)
  - 0x608f00  read u32 advancing cursor
  - 0x608f10  memcpy count×4 bytes from cursor

File-size identity (NikiAniA): n0*4 + 12 == len(file) when first three LE u32
are treated as dword counts (not the older “section byte sizes” reading).
Difference n0−n1 == 1290 matches the historic A−B invariant.
"""

from __future__ import annotations

import struct
from typing import Any, Final

# Client VA map (documentation + API surface)
CLIENT_VAS: Final[dict[str, int]] = {
    "aniExtensionGate": 0x5DE920,
    "serializeBoneTrack": 0x5DD8E0,
    "readFloat3xn": 0x5DD620,
    "readFloat4xn": 0x5DD640,
    "readFloat7xn": 0x5DD680,
    "readFloat1xn": 0x5DD660,
    "readFloat2xn": 0x5DD6A0,
    "denseTrackLoad": 0x5E08D0,
    "parseAfterBufferBind": 0x5E0FA0,
    "streamThreeU32BulkLoad": 0x5E0EE0,
    "bindStreamCursors": 0x608E70,
    "readU32": 0x608F00,
    "readFloats": 0x608F10,
}

RUNTIME_CHANNELS: Final[tuple[dict[str, Any], ...]] = (
    {"name": "float3", "floatsPerSample": 3, "role": "position", "readerVa": 0x5DD620},
    {"name": "float4", "floatsPerSample": 4, "role": "rotation", "readerVa": 0x5DD640},
    {"name": "float7", "floatsPerSample": 7, "role": "unknown", "readerVa": 0x5DD680},
    {"name": "float1", "floatsPerSample": 1, "role": "unknown", "readerVa": 0x5DD660},
    {"name": "float2", "floatsPerSample": 2, "role": "unknown", "readerVa": 0x5DD6A0},
)


def probe_client_stream_header(data: bytes) -> dict[str, Any]:
    """Score the 12-byte dword-count stream header against file length."""
    if len(data) < 28:
        return {
            "viable": False,
            "note": "ANI shorter than 28 bytes",
            "fileBytes": len(data),
        }
    n0, n1, n2 = struct.unpack_from("<3I", data, 0)
    expected = n0 * 4 + 12
    size_match = expected == len(data)
    tail_dwords = max(0, n0 - n1) if n0 >= n1 else None
    # Mini-header inside bulk (trackCount, duration, frameCount, frameCount2)
    bulk = data[12 : 12 + min(n0 * 4, max(0, len(data) - 12))]
    mini: dict[str, Any] | None = None
    if len(bulk) >= 16:
        track_count = struct.unpack_from("<I", bulk, 0)[0]
        duration = struct.unpack_from("<f", bulk, 4)[0]
        fc1, fc2 = struct.unpack_from("<2I", bulk, 8)
        mini = {
            "trackCount": track_count,
            "duration": duration,
            "frameCount": fc1,
            "frameCount2": fc2,
            "plausible": (
                1 <= track_count <= 256
                and 1 <= fc1 <= 10_000
                and fc1 == fc2
                and 0.0 < duration < 600.0
            ),
        }
    return {
        "name": "stream-header-12b-dword-counts",
        "n0": n0,
        "n1": n1,
        "n2": n2,
        "fileBytes": len(data),
        "expectedFileBytes": expected,
        "sizeMatch": size_match,
        "tailDwords": tail_dwords,
        "tailBytes": (tail_dwords * 4) if tail_dwords is not None else None,
        "n0MinusN1": (n0 - n1) if n0 >= n1 else None,
        "bulkMiniHeader": mini,
        "viable": bool(size_match and mini and mini.get("plausible")),
        "note": (
            "First three LE u32 are dword counts: bulk = n0×4 after 12-byte header; "
            "n0×4+12 equals file size on NikiAniA. Historic A−B=1290 is n0−n1."
        ),
    }


def build_client_decoder_hypothesis(data: bytes) -> dict[str, Any]:
    """API sectionProbe.clientDecoderHypothesis payload."""
    stream = probe_client_stream_header(data)
    return {
        "source": "FantaTennis.exe static RE (read-only)",
        "imageBase": 0x400000,
        "vas": {k: f"0x{v:08X}" for k, v in CLIENT_VAS.items()},
        "runtimeChannels": list(RUNTIME_CHANNELS),
        "streamHeader": stream,
        "rotationChannel": {
            "encoding": "float4",
            "readerVa": "0x5DD640",
            "denseLoadVa": "0x5E08D0",
            "confidentExtract": False,
            "note": (
                "Client runtime stores per-track float4 rotations (dense frameCount×16). "
                "On-disk Niki packing is not yet walked to unit-quat confidence ≥0.9; "
                "keep hierarchical-fk until extract succeeds."
            ),
        },
        "viableRotationEncoding": None,
        "recommendedDriveMode": "hierarchical-fk",
        "note": (
            "Client proves a float4 rotation channel at runtime. File stream header is "
            "12-byte dword counts (size-matched on Niki). Sparse/dense on-disk mapping "
            "to unit quats remains open; no stock client writes."
        ),
    }
