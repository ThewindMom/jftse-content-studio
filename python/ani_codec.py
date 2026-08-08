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
    min_score: float = 50.0,
    max_clips: int = 64,
) -> list[dict[str, Any]]:
    """Find consecutive float3 clips packed inside a section (e.g. A or C)."""
    block = _float3_block_size(header)
    if block <= 0 or section_size < block:
        return []
    clips: list[dict[str, Any]] = []
    rel = 0
    idx = 0
    while rel + block <= section_size and idx < max_clips:
        abs_off = section_off + rel
        tracks = _extract_tracks(
            data, header=header, data_off=abs_off, order=order
        )
        if tracks is None:
            break
        score = sum(_smoothness(t) for t in tracks[: min(8, len(tracks))])
        root = tracks[0][0] if tracks and tracks[0] else None
        # Require a minimum smoothness so we don't invent clips from noise
        if score < min_score:
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
        sample_n = 0
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
            "sizeParity": size % 2,
            "sizeMod4": size % 4,
            "bytesPerTrackFrame": size / n_tf,
            "float3Capacity": size // 12,
            "float4Capacity": size // 16,
            "float3BlockSize": _float3_block_size(header),
            "float3ClipSlots": size // max(_float3_block_size(header), 1),
            "quatUnitSampleRatio": (unit / total) if total else None,
            "quatUnitSamples": unit,
            "quatSamples": total,
            "u16Lt40SampleRatio": (u16_lt40 / sample_n) if sample_n else None,
        }
        off += size
    tail_off = off
    tail_size = max(len(data) - off, 0)
    sections["tail"] = {
        "offset": tail_off,
        "size": tail_size,
        "sizeParity": tail_size % 2,
        "float3ClipSlots": tail_size // max(_float3_block_size(header), 1),
    }
    # Multi-clip discovery in section A (primary positions; high smoothness)
    a_off = 28
    clips_tm = _discover_float3_clips(
        data,
        header=header,
        section_off=a_off,
        section_size=header.sectionA,
        order="track-major",
        min_score=50.0,
    )
    clips_fm = _discover_float3_clips(
        data,
        header=header,
        section_off=a_off,
        section_size=header.sectionA,
        order="frame-major",
        min_score=50.0,
    )
    clips = clips_tm if len(clips_tm) >= len(clips_fm) else clips_fm
    residual = header.sectionA - (len(clips) * _float3_block_size(header))
    sections["multiClip"] = {
        "section": "A",
        "channel": "primary",
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
    # Section C often mirrors A’s clip count with lower smoothness (secondary channel)
    c_off = 28 + header.sectionA + header.sectionB
    c_tm = _discover_float3_clips(
        data,
        header=header,
        section_off=c_off,
        section_size=header.sectionC,
        order="track-major",
        min_score=15.0,
    )
    c_residual = header.sectionC - (len(c_tm) * _float3_block_size(header))
    sections["multiClipC"] = {
        "section": "C",
        "channel": "secondary",
        "order": c_tm[0]["order"] if c_tm else None,
        "clipCount": len(c_tm),
        "clips": c_tm[:32],  # bound payload size
        "residualBytes": c_residual,
        "note": (
            f"Section C packs {len(c_tm)} float3-shaped clips at lower smoothness "
            "(possible euler/aux channel; not proven quaternions)"
            if c_tm
            else "No float3 clip stack in section C"
        ),
    }
    # Section B: exhaustive encoding probe (see ani_rotation_probe)
    from ani_rotation_probe import probe_section_b

    b_ratio = sections.get("B", {}).get("u16Lt40SampleRatio") or 0.0
    b_probe = probe_section_b(
        data,
        section_a=header.sectionA,
        section_b=header.sectionB,
        section_c=header.sectionC,
        track_count=header.trackCount,
        frame_count=header.frameCount,
    )
    sections["sectionBHypothesis"] = {
        "sameSizeAsC": header.sectionB == header.sectionC,
        "sectionAMinusB": header.sectionA - header.sectionB,
        "oddSized": header.sectionB % 2 == 1,
        "allSectionsOdd": (
            header.sectionA % 2 == 1
            and header.sectionB % 2 == 1
            and header.sectionC % 2 == 1
        ),
        "boneIndexLike": b_ratio >= 0.5,
        "encodingProbe": b_probe,
        "viableRotationEncoding": b_probe.get("viableRotationEncoding"),
        "note": b_probe.get("note")
        or (
            "Section B matches C’s byte length (AniA/B: A−B=1290) but is odd-sized "
            f"and not a dense bone-index u16 stream (u16<40 sample ratio={b_ratio:.3f})."
        ),
    }
    # Tail after A|B|C: large residual; encoding probe (see ani_rotation_probe.probe_tail)
    from ani_rotation_probe import probe_tail

    tail_clips = _discover_float3_clips(
        data,
        header=header,
        section_off=tail_off,
        section_size=min(tail_size, _float3_block_size(header) * 2),
        order="track-major",
        min_score=50.0,
        max_clips=2,
    )
    tail_probe = probe_tail(
        data,
        section_a=header.sectionA,
        section_b=header.sectionB,
        section_c=header.sectionC,
        track_count=header.trackCount,
        frame_count=header.frameCount,
    )
    sections["tailHypothesis"] = {
        "size": tail_size,
        "leadingFloat3Clips": len(tail_clips),
        "encodingProbe": tail_probe,
        "viableRotationEncoding": tail_probe.get("viableRotationEncoding"),
        "note": tail_probe.get("note")
        or (
            "Tail does not begin with a high-smoothness float3 multi-clip; "
            "likely compressed/other payload or unparsed channel"
            if not tail_clips
            else f"Tail starts with {len(tail_clips)} float3 clip(s)"
        ),
    }
    # Client-decoder RE (static FantaTennis.exe); never writes stock client
    from ani_client_re import build_client_decoder_hypothesis

    client_hyp = build_client_decoder_hypothesis(data)
    sections["clientDecoderHypothesis"] = client_hyp
    # Candidate confidence from sample ratios / B probe; parse_ani_bytes confirms via extract
    c_ratio = sections.get("C", {}).get("quatUnitSampleRatio") or 0.0
    a_ratio = sections.get("A", {}).get("quatUnitSampleRatio") or 0.0
    b_viable = sections.get("sectionBHypothesis", {}).get("viableRotationEncoding")
    candidate = bool(c_ratio >= 0.9 or b_viable)
    sections["rotationHypothesis"] = {
        "preferredSection": (
            "C" if c_ratio >= 0.9 else ("B" if b_viable else None)
        ),
        "confident": False,  # set true only after successful extract in parse_ani_bytes
        "candidateConfident": candidate,
        "sectionAUnitRatio": a_ratio,
        "sectionCUnitRatio": c_ratio,
        "sectionBViableEncoding": b_viable,
        "recommendedDriveMode": "hierarchical-fk",
        "clientRuntimeRotation": "float4",
        "note": (
            "Rotation candidate present; awaiting extract confirmation"
            if candidate
            else (
                "No dense unit float4 quat graph extractable from A/B/C/tail on Niki-class "
                f"ANI (A≈{a_ratio:.0%} C≈{c_ratio:.0%} unit samples; B sparse/delta probes "
                "non-viable). Client runtime uses float4 rotations (see "
                "clientDecoderHypothesis); hierarchical-fk until on-disk→unit extract "
                "reaches confidence ≥0.9."
            )
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
    channel: str = "A",
) -> ParsedAni:
    header = parse_ani_header(data)
    probe = _probe_sections(data, header)
    channel_u = (channel or "A").strip().upper()
    if channel_u not in ("A", "C"):
        raise AniParseError(f"channel must be A or C, got {channel!r}")
    multi = probe.get("multiClipC" if channel_u == "C" else "multiClip") or {}
    clips: list[dict[str, Any]] = list(multi.get("clips") or [])

    raw_tracks: list[list[list[float]]] | None = None
    layout = ""
    selected_clip: dict[str, Any] | None = None

    if clips:
        # Clamp clip index into discovered multi-clip range
        if clip_index < 0 or clip_index >= len(clips):
            raise AniParseError(
                f"clipIndex {clip_index} out of range (0..{len(clips) - 1}) for channel {channel_u}"
            )
        selected_clip = clips[clip_index]
        order = str(selected_clip.get("order") or "track-major")
        data_off = int(selected_clip["offset"])
        raw_tracks = _extract_tracks(
            data, header=header, data_off=data_off, order=order
        )
        if raw_tracks is None:
            raise AniParseError(f"failed to decode multi-clip {clip_index}")
        layout = (
            f"multi-clip-{channel_u}[{clip_index}/{len(clips)}] {order}@+{data_off}"
        )
    else:
        best: tuple[float, str, int, list[list[list[float]]]] | None = None
        for data_off in (28, 32, 24, 36, 48, 28 + header.sectionA):
            for order in ("frame-major", "track-major"):
                pos_tracks = _extract_tracks(
                    data, header=header, data_off=data_off, order=order
                )
                if pos_tracks is None:
                    continue
                score = sum(
                    _smoothness(t) for t in pos_tracks[: min(8, len(pos_tracks))]
                )
                if pos_tracks:
                    xs = [p[0] for p in pos_tracks[0]]
                    ys = [p[1] for p in pos_tracks[0]]
                    zs = [p[2] for p in pos_tracks[0]]
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
                    best = (score, label, data_off, pos_tracks)
        if best is None:
            raise AniParseError("no valid float3 track layout found")
        _score, layout, _pos_off, raw_tracks = best

    # Experimental quat attach: only when extract yields unit ratio ≥ 0.9
    rot_tracks: list[list[list[float]]] | None = None
    rot_meta: dict[str, Any] | None = None
    from ani_client_re import try_extract_from_client_walk
    from ani_rotation_probe import try_extract_confident_quats

    # Prefer client bulk-walk extract (dense float4 scan of main region)
    rot_tracks, rot_meta = try_extract_from_client_walk(
        data,
        track_count=header.trackCount,
        frame_count=header.frameCount,
    )
    if not (rot_meta or {}).get("confident"):
        b_probe = (probe.get("sectionBHypothesis") or {}).get("encodingProbe")
        hyp = probe.get("rotationHypothesis") or {}
        t_probe = (probe.get("tailHypothesis") or {}).get("encodingProbe")
        if hyp.get("candidateConfident") or (
            b_probe and b_probe.get("viableRotationEncoding")
        ) or (t_probe and t_probe.get("viableRotationEncoding")):
            rot_tracks, rot_meta = try_extract_confident_quats(
                data,
                track_count=header.trackCount,
                frame_count=header.frameCount,
                section_a=header.sectionA,
                section_b=header.sectionB,
                section_c=header.sectionC,
                b_probe=b_probe,
            )
        elif rot_meta is None:
            rot_meta = {
                "selectedOffset": None,
                "selectedUnitRatio": None,
                "confident": False,
                "skipped": True,
                "note": "extract skipped: no rotation candidate from walk/B/C/tail",
            }

    if rot_tracks is not None and rot_meta.get("confident"):
        order = rot_meta.get("order") or "track-major"
        off = rot_meta.get("selectedOffset")
        layout = f"{layout}+quat-{order}@+{off}"
        probe = {
            **probe,
            "rotationHypothesis": {
                **probe.get("rotationHypothesis", {}),
                "confident": True,
                "recommendedDriveMode": "quat",
                "note": (
                    f"Dense unit quaternions at +{off} ({order}, "
                    f"ratio={rot_meta.get('decodeUnitRatio')})"
                ),
            },
            "rotationExtract": rot_meta,
        }
    else:
        probe = {**probe, "rotationExtract": rot_meta or {}}

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
    # Attach motion names from client name table onto multi-clip entries
    client_hyp = probe.get("clientDecoderHypothesis") or {}
    bulk_walk = client_hyp.get("bulkWalk") or {}
    motion_names = list(bulk_walk.get("motionNames") or [])
    if motion_names and clips:
        named_clips: list[dict[str, Any]] = []
        for c in clips:
            idx = int(c.get("index") or 0)
            entry = dict(c)
            if idx < len(motion_names):
                entry["motionName"] = motion_names[idx].get("name")
            named_clips.append(entry)
        clips = named_clips
        multi_key = "multiClipC" if channel_u == "C" else "multiClip"
        if multi_key in probe and isinstance(probe[multi_key], dict):
            probe = {
                **probe,
                multi_key: {**probe[multi_key], "clips": clips[:32]},
            }
        if selected_clip is not None:
            sc = dict(selected_clip)
            si = int(sc.get("index") or clip_index)
            if si < len(motion_names):
                sc["motionName"] = motion_names[si].get("name")
            selected_clip = sc
    # Motion catalog (name → clipIndex) from client name table + sequential clips
    from ani_client_re import build_motion_catalog

    motion_catalog = build_motion_catalog(data)
    # Annotate selected clip on probe for API consumers
    probe = {
        **probe,
        "selectedClip": selected_clip,
        "clipIndex": clip_index,
        "clipCount": len(clips),
        "channel": channel_u,
        "motionNames": motion_names,
        "motionCatalog": motion_catalog,
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
    channel: str = "A",
) -> ParsedAni:
    with zipfile.ZipFile(client_root / archive_rel) as zf:
        data = zf.read(member)
    return parse_ani_bytes(
        data,
        name=member,
        bone_names=bone_names,
        clip_index=clip_index,
        channel=channel,
    )
