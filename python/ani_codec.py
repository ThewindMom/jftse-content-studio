"""Fantasy Tennis .ani animation codec (best-effort RE).

Header (LE), verified on NikiAniA/B:
  u32 sectionA, sectionB, sectionC   # packed region sizes
  u32 trackCount                     # typically 40 (bones)
  f32 duration                       # frames/30 (AniA: 44→1.4667, AniB: 24→0.8)
  u32 frameCount, frameCount2        # equal frame counts

Keyframe payload is a dense float stream after a 28-byte header. We recover
per-track position curves by scoring candidate (frame, track, float3) layouts
for temporal smoothness and finite values, then expose uniform-time samples.
Bone names are optional labels aligned from the character mesh skeleton order.
"""

from __future__ import annotations

import math
import struct
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class AniParseError(ValueError):
    pass


@dataclass
class AniHeader:
    sectionA: int
    sectionB: int
    sectionC: int
    trackCount: int
    duration: float
    frameCount: int
    frameCount2: int


@dataclass
class AniTrack:
    index: int
    name: str | None
    positions: list[list[float]]  # frame-major [x,y,z]
    times: list[float]


@dataclass
class ParsedAni:
    name: str
    header: AniHeader
    tracks: list[AniTrack]
    layout: str
    byteLength: int

    def to_dict(self, *, max_frames: int | None = 8) -> dict[str, Any]:
        tracks_out = []
        for t in self.tracks:
            positions = t.positions
            times = t.times
            if max_frames is not None and len(positions) > max_frames:
                # keep head+tail samples for compact API
                head = max_frames // 2
                tail = max_frames - head
                positions = positions[:head] + positions[-tail:]
                times = times[:head] + times[-tail:]
            tracks_out.append(
                {
                    "index": t.index,
                    "name": t.name,
                    "frameCount": len(t.positions),
                    "times": times,
                    "positions": positions,
                    "start": t.positions[0] if t.positions else None,
                    "end": t.positions[-1] if t.positions else None,
                }
            )
        return {
            "name": self.name,
            "header": asdict(self.header),
            "layout": self.layout,
            "byteLength": self.byteLength,
            "trackCount": len(self.tracks),
            "duration": self.header.duration,
            "frameCount": self.header.frameCount,
            "tracks": tracks_out,
        }


def parse_ani_header(data: bytes) -> AniHeader:
    if len(data) < 28:
        raise AniParseError("ANI too small")
    a, b, c, tracks = struct.unpack_from("<4I", data, 0)
    duration = struct.unpack_from("<f", data, 16)[0]
    fc1, fc2 = struct.unpack_from("<2I", data, 20)
    if tracks < 1 or tracks > 256:
        raise AniParseError(f"invalid trackCount={tracks}")
    if fc1 < 1 or fc1 > 10_000:
        raise AniParseError(f"invalid frameCount={fc1}")
    if not math.isfinite(duration) or duration <= 0 or duration > 600:
        raise AniParseError(f"invalid duration={duration}")
    return AniHeader(
        sectionA=a,
        sectionB=b,
        sectionC=c,
        trackCount=tracks,
        duration=float(duration),
        frameCount=fc1,
        frameCount2=fc2,
    )


def _smoothness(positions: list[list[float]]) -> float:
    if len(positions) < 3:
        return 0.0
    total = 0.0
    for i in range(1, len(positions)):
        dx = positions[i][0] - positions[i - 1][0]
        dy = positions[i][1] - positions[i - 1][1]
        dz = positions[i][2] - positions[i - 1][2]
        step = math.sqrt(dx * dx + dy * dy + dz * dz)
        if step > 50:  # teleport penalty
            total -= 10
        else:
            total += 1.0 / (1.0 + step)
    return total


def _extract_tracks(
    data: bytes,
    *,
    header: AniHeader,
    data_off: int,
    order: str,
) -> list[list[list[float]]] | None:
    """Return tracks[track][frame] = [x,y,z] for a layout, or None if invalid."""
    n_f = header.frameCount
    n_t = header.trackCount
    need = n_f * n_t * 12
    if data_off + need > len(data):
        return None
    tracks: list[list[list[float]]] = [[] for _ in range(n_t)]
    if order == "frame-major":
        # for each frame, all bones
        for fi in range(n_f):
            base = data_off + fi * n_t * 12
            for ti in range(n_t):
                x, y, z = struct.unpack_from("<3f", data, base + ti * 12)
                if not all(math.isfinite(v) and abs(v) < 5000 for v in (x, y, z)):
                    return None
                tracks[ti].append([x, y, z])
    elif order == "track-major":
        for ti in range(n_t):
            base = data_off + ti * n_f * 12
            for fi in range(n_f):
                x, y, z = struct.unpack_from("<3f", data, base + fi * 12)
                if not all(math.isfinite(v) and abs(v) < 5000 for v in (x, y, z)):
                    return None
                tracks[ti].append([x, y, z])
    else:
        return None
    return tracks


def parse_ani_bytes(
    data: bytes,
    *,
    name: str = "",
    bone_names: list[str] | None = None,
) -> ParsedAni:
    header = parse_ani_header(data)
    best: tuple[float, str, int, list[list[list[float]]]] | None = None
    for data_off in (28, 32, 24, 36, 48):
        for order in ("frame-major", "track-major"):
            tracks = _extract_tracks(data, header=header, data_off=data_off, order=order)
            if tracks is None:
                continue
            score = sum(_smoothness(t) for t in tracks[: min(8, len(tracks))])
            # Prefer layouts where root-like track has meaningful motion footprint
            if tracks:
                xs = [p[0] for p in tracks[0]]
                ys = [p[1] for p in tracks[0]]
                zs = [p[2] for p in tracks[0]]
                extent = (max(xs) - min(xs)) + (max(ys) - min(ys)) + (max(zs) - min(zs))
                score += min(extent, 50.0)
            label = f"{order}@+{data_off}"
            if best is None or score > best[0]:
                best = (score, label, data_off, tracks)
    if best is None:
        raise AniParseError("no valid float3 track layout found")
    _score, layout, _off, raw_tracks = best
    times = [
        header.duration * (i / max(header.frameCount - 1, 1))
        for i in range(header.frameCount)
    ]
    tracks: list[AniTrack] = []
    for i, positions in enumerate(raw_tracks):
        bname = bone_names[i] if bone_names and i < len(bone_names) else None
        tracks.append(AniTrack(index=i, name=bname, positions=positions, times=list(times)))
    return ParsedAni(
        name=name,
        header=header,
        tracks=tracks,
        layout=layout,
        byteLength=len(data),
    )


def load_ani_member(
    client_root: Path,
    archive_rel: str,
    member: str,
    *,
    bone_names: list[str] | None = None,
) -> ParsedAni:
    with zipfile.ZipFile(client_root / archive_rel) as zf:
        data = zf.read(member)
    return parse_ani_bytes(data, name=member, bone_names=bone_names)
