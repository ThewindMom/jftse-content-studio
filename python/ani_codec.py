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
    rotations: list[list[float]] | None = None  # optional [x,y,z,w] if recovered


@dataclass
class ParsedAni:
    name: str
    header: AniHeader
    tracks: list[AniTrack]
    layout: str
    byteLength: int
    sectionProbe: dict[str, Any] | None = None

    def to_dict(self, *, max_frames: int | None = 8) -> dict[str, Any]:
        tracks_out = []
        for t in self.tracks:
            positions = t.positions
            times = t.times
            rotations = t.rotations
            if max_frames is not None and len(positions) > max_frames:
                # keep head+tail samples for compact API
                head = max_frames // 2
                tail = max_frames - head
                positions = positions[:head] + positions[-tail:]
                times = times[:head] + times[-tail:]
                if rotations is not None:
                    rotations = rotations[:head] + rotations[-tail:]
            entry: dict[str, Any] = {
                "index": t.index,
                "name": t.name,
                "frameCount": len(t.positions),
                "times": times,
                "positions": positions,
                "start": t.positions[0] if t.positions else None,
                "end": t.positions[-1] if t.positions else None,
            }
            if rotations is not None:
                entry["rotations"] = rotations
                entry["hasRotations"] = True
            else:
                entry["hasRotations"] = False
            tracks_out.append(entry)
        return {
            "name": self.name,
            "header": asdict(self.header),
            "layout": self.layout,
            "byteLength": self.byteLength,
            "trackCount": len(self.tracks),
            "duration": self.header.duration,
            "frameCount": self.header.frameCount,
            "tracks": tracks_out,
            "sectionProbe": self.sectionProbe,
            "hasRotations": any(t.rotations for t in self.tracks),
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


def _float3_block_size(header: AniHeader) -> int:
    return header.trackCount * header.frameCount * 12


def _discover_float3_clips(
    data: bytes,
    *,
    header: AniHeader,
    section_off: int,
    section_size: int,
    order: str = "track-major",
) -> list[dict[str, Any]]:
    """Find consecutive smooth float3 clips packed inside a section (e.g. A)."""
    block = _float3_block_size(header)
    if block <= 0 or section_size < block:
        return []
    clips: list[dict[str, Any]] = []
    rel = 0
    idx = 0
    while rel + block <= section_size:
        abs_off = section_off + rel
        tracks = _extract_tracks(
            data, header=header, data_off=abs_off, order=order
        )
        if tracks is None:
            break
        score = sum(_smoothness(t) for t in tracks[: min(8, len(tracks))])
        root = tracks[0][0] if tracks and tracks[0] else None
        # Require a minimum smoothness so we don't invent clips from noise
        if score < 50:
            break
        clips.append(
            {
                "index": idx,
                "offset": abs_off,
                "relativeOffset": rel,
                "order": order,
                "score": round(score, 3),
                "rootStart": root,
                "byteLength": block,
            }
        )
        idx += 1
        rel += block
    return clips


def _probe_sections(data: bytes, header: AniHeader) -> dict[str, Any]:
    """Describe section A/B/C packing (evidence for quat/skinning RE)."""
    off = 28
    sections: dict[str, Any] = {}
    for label, size in (
        ("A", header.sectionA),
        ("B", header.sectionB),
        ("C", header.sectionC),
    ):
        chunk = data[off : off + size] if off + size <= len(data) else b""
        n_tf = max(header.trackCount * header.frameCount, 1)
        unit = 0
        total = 0
        # sample up to 2000 float4 groups as quat unit-length candidates
        for i in range(0, min(len(chunk) - 16, 2000 * 16), 16):
            q = struct.unpack_from("<4f", chunk, i)
            if not all(math.isfinite(v) for v in q):
                continue
            length = math.sqrt(sum(v * v for v in q))
            total += 1
            if 0.95 <= length <= 1.05:
                unit += 1
        # u16 stats for section B (index-like?)
        u16_count = len(chunk) // 2
        u16_lt40 = 0
        if u16_count:
            # sample first 20k u16s
            sample_n = min(u16_count, 20_000)
            for i in range(sample_n):
                v = struct.unpack_from("<H", chunk, i * 2)[0]
                if v < 40:
                    u16_lt40 += 1
        sections[label] = {
            "offset": off,
            "size": size,
            "bytesPerTrackFrame": size / n_tf,
            "float3Capacity": size // 12,
            "float4Capacity": size // 16,
            "float3BlockSize": _float3_block_size(header),
            "float3ClipSlots": size // max(_float3_block_size(header), 1),
            "quatUnitSampleRatio": (unit / total) if total else None,
            "quatUnitSamples": unit,
            "quatSamples": total,
            "u16Lt40SampleRatio": (u16_lt40 / sample_n) if u16_count else None,
        }
        off += size
    sections["tail"] = {
        "offset": off,
        "size": max(len(data) - off, 0),
    }
    # Multi-clip discovery in section A (track-major float3 stacks)
    a_off = 28
    clips_tm = _discover_float3_clips(
        data,
        header=header,
        section_off=a_off,
        section_size=header.sectionA,
        order="track-major",
    )
    clips_fm = _discover_float3_clips(
        data,
        header=header,
        section_off=a_off,
        section_size=header.sectionA,
        order="frame-major",
    )
    # Prefer order that finds more high-scoring clips
    clips = clips_tm if len(clips_tm) >= len(clips_fm) else clips_fm
    residual = header.sectionA - (len(clips) * _float3_block_size(header))
    sections["multiClip"] = {
        "section": "A",
        "order": clips[0]["order"] if clips else None,
        "clipCount": len(clips),
        "clips": clips,
        "residualBytes": residual,
        "note": (
            f"Section A packs {len(clips)} consecutive float3 clips "
            f"({_float3_block_size(header)} B each = trackCount×frameCount×12)"
            if clips
            else "No stacked float3 clips detected in section A"
        ),
    }
    # Section B: same size as C on NikiAniA; not bone-index dense
    b_ratio = sections.get("B", {}).get("u16Lt40SampleRatio") or 0.0
    sections["sectionBHypothesis"] = {
        "sameSizeAsC": header.sectionB == header.sectionC,
        "boneIndexLike": b_ratio >= 0.5,
        "note": (
            "Section B is not a dense bone-index u16 stream "
            f"(u16<40 sample ratio={b_ratio:.3f}); encoding still unknown"
        ),
    }
    # Prefer section C as rotation candidate when unit ratio is high
    c_ratio = sections.get("C", {}).get("quatUnitSampleRatio") or 0.0
    sections["rotationHypothesis"] = {
        "preferredSection": "C" if c_ratio >= 0.9 else None,
        "confident": bool(c_ratio >= 0.9),
        "note": (
            "Section C looks like unit quaternions"
            if c_ratio >= 0.9
            else "No section has ≥90% unit-length float4 samples; quats not attached to tracks"
        ),
    }
    return sections


def _extract_quats(
    data: bytes,
    *,
    header: AniHeader,
    data_off: int,
    order: str,
) -> list[list[list[float]]] | None:
    """Return tracks[track][frame] = [x,y,z,w] or None if not unit-ish."""
    n_f = header.frameCount
    n_t = header.trackCount
    need = n_f * n_t * 16
    if data_off + need > len(data):
        return None
    tracks: list[list[list[float]]] = [[] for _ in range(n_t)]
    unit = 0
    total = 0
    if order == "frame-major":
        for fi in range(n_f):
            base = data_off + fi * n_t * 16
            for ti in range(n_t):
                q = list(struct.unpack_from("<4f", data, base + ti * 16))
                if not all(math.isfinite(v) for v in q):
                    return None
                length = math.sqrt(sum(v * v for v in q))
                total += 1
                if 0.95 <= length <= 1.05:
                    unit += 1
                tracks[ti].append(q)
    elif order == "track-major":
        for ti in range(n_t):
            base = data_off + ti * n_f * 16
            for fi in range(n_f):
                q = list(struct.unpack_from("<4f", data, base + fi * 16))
                if not all(math.isfinite(v) for v in q):
                    return None
                length = math.sqrt(sum(v * v for v in q))
                total += 1
                if 0.95 <= length <= 1.05:
                    unit += 1
                tracks[ti].append(q)
    else:
        return None
    if total == 0 or unit / total < 0.9:
        return None
    return tracks


def parse_ani_bytes(
    data: bytes,
    *,
    name: str = "",
    bone_names: list[str] | None = None,
    clip_index: int = 0,
) -> ParsedAni:
    header = parse_ani_header(data)
    probe = _probe_sections(data, header)
    multi = probe.get("multiClip") or {}
    clips: list[dict[str, Any]] = list(multi.get("clips") or [])

    raw_tracks: list[list[list[float]]] | None = None
    layout = ""
    selected_clip: dict[str, Any] | None = None

    if clips:
        # Clamp clip index into discovered multi-clip range
        if clip_index < 0 or clip_index >= len(clips):
            raise AniParseError(
                f"clipIndex {clip_index} out of range (0..{len(clips) - 1})"
            )
        selected_clip = clips[clip_index]
        order = str(selected_clip.get("order") or "track-major")
        data_off = int(selected_clip["offset"])
        raw_tracks = _extract_tracks(
            data, header=header, data_off=data_off, order=order
        )
        if raw_tracks is None:
            raise AniParseError(f"failed to decode multi-clip {clip_index}")
        layout = f"multi-clip[{clip_index}/{len(clips)}] {order}@+{data_off}"
    else:
        best: tuple[float, str, int, list[list[list[float]]]] | None = None
        for data_off in (28, 32, 24, 36, 48, 28 + header.sectionA):
            for order in ("frame-major", "track-major"):
                tracks = _extract_tracks(
                    data, header=header, data_off=data_off, order=order
                )
                if tracks is None:
                    continue
                score = sum(_smoothness(t) for t in tracks[: min(8, len(tracks))])
                if tracks:
                    xs = [p[0] for p in tracks[0]]
                    ys = [p[1] for p in tracks[0]]
                    zs = [p[2] for p in tracks[0]]
                    extent = (
                        (max(xs) - min(xs))
                        + (max(ys) - min(ys))
                        + (max(zs) - min(zs))
                    )
                    score += min(extent, 50.0)
                if data_off == 28:
                    score += 5.0
                label = f"{order}@+{data_off}"
                if best is None or score > best[0]:
                    best = (score, label, data_off, tracks)
        if best is None:
            raise AniParseError("no valid float3 track layout found")
        _score, layout, _pos_off, raw_tracks = best

    # Experimental quat attach: only when section probe is confident
    rot_tracks: list[list[list[float]]] | None = None
    if probe.get("rotationHypothesis", {}).get("confident"):
        c_off = 28 + header.sectionA + header.sectionB
        for order in ("track-major", "frame-major"):
            rot_tracks = _extract_quats(
                data, header=header, data_off=c_off, order=order
            )
            if rot_tracks is not None:
                layout = f"{layout}+quat-{order}@C"
                break

    times = [
        header.duration * (i / max(header.frameCount - 1, 1))
        for i in range(header.frameCount)
    ]
    tracks: list[AniTrack] = []
    for i, positions in enumerate(raw_tracks):
        bname = bone_names[i] if bone_names and i < len(bone_names) else None
        rots = rot_tracks[i] if rot_tracks is not None else None
        tracks.append(
            AniTrack(
                index=i,
                name=bname,
                positions=positions,
                times=list(times),
                rotations=rots,
            )
        )
    # Annotate selected clip on probe for API consumers
    if selected_clip is not None:
        probe = {
            **probe,
            "selectedClip": selected_clip,
            "clipIndex": clip_index,
            "clipCount": len(clips),
        }
    return ParsedAni(
        name=name,
        header=header,
        tracks=tracks,
        layout=layout,
        byteLength=len(data),
        sectionProbe=probe,
    )


def load_ani_member(
    client_root: Path,
    archive_rel: str,
    member: str,
    *,
    bone_names: list[str] | None = None,
    clip_index: int = 0,
) -> ParsedAni:
    with zipfile.ZipFile(client_root / archive_rel) as zf:
        data = zf.read(member)
    return parse_ani_bytes(
        data, name=member, bone_names=bone_names, clip_index=clip_index
    )
