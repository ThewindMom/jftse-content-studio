"""Fantasy Tennis FTM/PRJ map codec — port of FT-ResTool FTMParser/PRJReader.

Source of truth: decompiled com.ft.restool.parser.ftm.FTMParser (ft_restool.jar).
Little-endian; length-prefixed strings are u8 length + ASCII bytes (no NUL).

Layout (parse order):
  mapPath, tileCountX/Y, unkI2, indoorMode, unkI3, unkI4
  tile layers (defs + X*Y index grids)
  prefab catalog (name, objId) + scene placements (prefabIndex, x, y, scale, rot)
  interactable tiles (NPC triggers) + blocked tiles + trailing unknown bytes
"""

from __future__ import annotations

import struct
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class FtmParseError(ValueError):
    pass


class _Cursor:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.off = 0

    def remaining(self) -> int:
        return len(self.data) - self.off

    def _need(self, n: int) -> None:
        if self.off + n > len(self.data):
            raise FtmParseError(f"FTM truncated at offset {self.off}, need {n} more bytes")

    def u8(self) -> int:
        self._need(1)
        v = self.data[self.off]
        self.off += 1
        return v

    def i32(self) -> int:
        self._need(4)
        v = struct.unpack_from("<i", self.data, self.off)[0]
        self.off += 4
        return v

    def f32(self) -> float:
        self._need(4)
        v = struct.unpack_from("<f", self.data, self.off)[0]
        self.off += 4
        return float(v)

    def string(self) -> str:
        n = self.u8()
        self._need(n)
        s = self.data[self.off : self.off + n].decode("ascii", errors="replace")
        self.off += n
        return s

    def skip(self, n: int) -> None:
        self._need(n)
        self.off += n


@dataclass
class TileLayerDefinition:
    name: str
    tileLayerIndex: int
    usesWater: int
    tileLayerZIndex: int
    tileLayerHeight: float
    visible: int
    tileResourcePaths: list[str]


@dataclass
class TileLayerData:
    layerName: str
    tileCountX: int
    tileCountY: int
    indices: list[int]


@dataclass
class PrefabObject:
    name: str
    objId: str


@dataclass
class SceneObject:
    """Placement instance — FT-ResTool SceneObject."""

    prefabIndex: int
    x: int
    y: int
    scaleHeight: float
    scaleWidth: float
    rotationY: float
    rotationX: float
    prefabName: str | None = None
    prefabObjId: str | None = None


@dataclass
class NpcEventTrigger:
    unkB1: int
    unkB2: int
    unkB3: int
    unkB4: int
    unkB5: int
    unkB6: int
    unkI0: int
    unkI1: int
    unkI2: int
    unkI3: int
    objNumber: int
    scale: float
    unkI4: int
    heightOffset: float
    rotation: float
    params: list[str]
    unkB7: int
    unkI6: int
    commands: list[str]


@dataclass
class InteractableTile:
    unkB0: int
    x: int
    y: int
    triggers: list[NpcEventTrigger]


@dataclass
class BlockedTile:
    x: int
    y: int


@dataclass
class ParsedFtm:
    mapPath: str
    tileCountX: int
    tileCountY: int
    unkI2: int
    indoorMode: int
    unkI3: int
    unkI4: int
    tileLayerDefinitions: list[TileLayerDefinition] = field(default_factory=list)
    tileLayers: list[TileLayerData] = field(default_factory=list)
    prefabs: list[PrefabObject] = field(default_factory=list)
    sceneObjects: list[SceneObject] = field(default_factory=list)
    interactableTiles: list[InteractableTile] = field(default_factory=list)
    blockedTiles: list[BlockedTile] = field(default_factory=list)
    unknownBytes: bytes = b""
    byteLength: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["unknownBytes"] = list(self.unknownBytes)
        d["unknownByteCount"] = len(self.unknownBytes)
        d["prefabCount"] = len(self.prefabs)
        d["sceneObjectCount"] = len(self.sceneObjects)
        d["interactableTileCount"] = len(self.interactableTiles)
        d["blockedTileCount"] = len(self.blockedTiles)
        return d


def parse_ftm_bytes(data: bytes) -> ParsedFtm:
    """Parse a complete .ftm / .rom blob (FT-ResTool compatible)."""
    if not data:
        raise FtmParseError("empty FTM")
    c = _Cursor(data)
    map_path = c.string()
    tile_count_x = c.i32()
    tile_count_y = c.i32()
    unk_i2 = c.i32()
    indoor_mode = c.u8()
    unk_i3 = c.i32()
    unk_i4 = c.i32()

    layer_count = c.i32()
    if layer_count < 0 or layer_count > 64:
        raise FtmParseError(f"invalid tileLayerCount={layer_count}")
    layer_defs: list[TileLayerDefinition] = []
    for _ in range(layer_count):
        name = c.string()
        tile_layer_index = c.u8()
        uses_water = c.u8()
        z_index = c.i32()
        height = c.f32()
        visible = c.u8()
        res_count = c.i32()
        if res_count < 0 or res_count > 10_000:
            raise FtmParseError(f"invalid tileResourceCount={res_count}")
        paths = [c.string() for _ in range(res_count)]
        layer_defs.append(
            TileLayerDefinition(
                name=name,
                tileLayerIndex=tile_layer_index,
                usesWater=uses_water,
                tileLayerZIndex=z_index,
                tileLayerHeight=height,
                visible=visible,
                tileResourcePaths=paths,
            )
        )

    tile_layers: list[TileLayerData] = []
    for layer_def in layer_defs:
        lx = c.i32()
        ly = c.i32()
        if lx < 0 or ly < 0 or lx * ly > 2_000_000:
            raise FtmParseError(f"invalid layer grid {lx}x{ly}")
        indices = [c.i32() for _ in range(lx * ly)]
        tile_layers.append(
            TileLayerData(
                layerName=layer_def.name,
                tileCountX=lx,
                tileCountY=ly,
                indices=indices,
            )
        )

    prefab_count = c.i32()
    if prefab_count < 0 or prefab_count > 50_000:
        raise FtmParseError(f"invalid prefabObjectCount={prefab_count}")
    prefabs: list[PrefabObject] = []
    for _ in range(prefab_count):
        name = c.string()
        obj_id = c.string()
        c.skip(2)  # FT-ResTool: offset.getAndAdd(2) after each prefab
        prefabs.append(PrefabObject(name=name, objId=obj_id))

    scene_count = c.i32()
    if scene_count < 0 or scene_count > 200_000:
        raise FtmParseError(f"invalid sceneObjectCount={scene_count}")
    scenes: list[SceneObject] = []
    for _ in range(scene_count):
        prefab_index = c.i32()
        x = c.i32()
        y = c.i32()
        scale_h = c.f32()
        scale_w = c.f32()
        rot_y = c.f32()
        rot_x = c.f32()
        prefab_name = prefabs[prefab_index].name if 0 <= prefab_index < len(prefabs) else None
        prefab_obj = prefabs[prefab_index].objId if 0 <= prefab_index < len(prefabs) else None
        scenes.append(
            SceneObject(
                prefabIndex=prefab_index,
                x=x,
                y=y,
                scaleHeight=scale_h,
                scaleWidth=scale_w,
                rotationY=rot_y,
                rotationX=rot_x,
                prefabName=prefab_name,
                prefabObjId=prefab_obj,
            )
        )

    interactable_count = c.i32()
    if interactable_count < 0 or interactable_count > 50_000:
        raise FtmParseError(f"invalid interactableTileCount={interactable_count}")
    interactables: list[InteractableTile] = []
    for _ in range(interactable_count):
        unk_b0 = c.u8()
        ix = c.i32()
        iy = c.i32()
        trigger_count = c.i32()
        triggers: list[NpcEventTrigger] = []
        for _ in range(trigger_count):
            triggers.append(
                NpcEventTrigger(
                    unkB1=c.u8(),
                    unkB2=c.u8(),
                    unkB3=c.u8(),
                    unkB4=c.u8(),
                    unkB5=c.u8(),
                    unkB6=c.u8(),
                    unkI0=c.i32(),
                    unkI1=c.i32(),
                    unkI2=c.i32(),
                    unkI3=c.i32(),
                    objNumber=c.i32(),
                    scale=c.f32(),
                    unkI4=c.i32(),
                    heightOffset=c.f32(),
                    rotation=c.f32(),
                    params=[c.string() for _ in range(c.i32())],
                    unkB7=c.u8(),
                    unkI6=c.i32(),
                    commands=[c.string() for _ in range(c.i32())],
                )
            )
        interactables.append(InteractableTile(unkB0=unk_b0, x=ix, y=iy, triggers=triggers))

    blocked_count = c.i32()
    if blocked_count < 0 or blocked_count > 200_000:
        raise FtmParseError(f"invalid blockedTileCount={blocked_count}")
    blocked = [BlockedTile(x=c.i32(), y=c.i32()) for _ in range(blocked_count)]
    unknown = data[c.off :]

    return ParsedFtm(
        mapPath=map_path,
        tileCountX=tile_count_x,
        tileCountY=tile_count_y,
        unkI2=unk_i2,
        indoorMode=indoor_mode,
        unkI3=unk_i3,
        unkI4=unk_i4,
        tileLayerDefinitions=layer_defs,
        tileLayers=tile_layers,
        prefabs=prefabs,
        sceneObjects=scenes,
        interactableTiles=interactables,
        blockedTiles=blocked,
        unknownBytes=unknown,
        byteLength=len(data),
    )


def parse_prj_bytes(data: bytes) -> dict[str, Any]:
    """PRJ: u32 ftmCount + pascal strings of FTM base paths."""
    if len(data) < 4:
        raise FtmParseError("PRJ too small")
    count = struct.unpack_from("<i", data, 0)[0]
    if count < 0 or count > 256:
        raise FtmParseError(f"invalid prj ftmCount={count}")
    c = _Cursor(data)
    c.skip(4)
    paths = [c.string() for _ in range(count)]
    return {"ftmCount": count, "ftmPaths": paths, "byteLength": len(data)}


def load_ftm_from_res(
    client_root: Path, archive_rel: str, member: str
) -> ParsedFtm:
    with zipfile.ZipFile(client_root / archive_rel) as zf:
        return parse_ftm_bytes(zf.read(member))


def load_prj_from_res(
    client_root: Path, archive_rel: str, member: str
) -> dict[str, Any]:
    with zipfile.ZipFile(client_root / archive_rel) as zf:
        return parse_prj_bytes(zf.read(member))


class _Writer:
    def __init__(self) -> None:
        self.buf = bytearray()

    def u8(self, v: int) -> None:
        self.buf.append(v & 0xFF)

    def i32(self, v: int) -> None:
        self.buf.extend(struct.pack("<i", int(v)))

    def f32(self, v: float) -> None:
        self.buf.extend(struct.pack("<f", float(v)))

    def string(self, s: str) -> None:
        raw = (s or "").encode("ascii", errors="replace")
        if len(raw) > 255:
            raise FtmParseError(f"string too long for pascal u8 ({len(raw)})")
        self.u8(len(raw))
        self.buf.extend(raw)

    def raw(self, data: bytes) -> None:
        self.buf.extend(data)


def serialize_ftm(ftm: ParsedFtm) -> bytes:
    """Serialize ParsedFtm to FT-ResTool-compatible .ftm bytes (full rewrite)."""
    w = _Writer()
    w.string(ftm.mapPath)
    w.i32(ftm.tileCountX)
    w.i32(ftm.tileCountY)
    w.i32(ftm.unkI2)
    w.u8(ftm.indoorMode)
    w.i32(ftm.unkI3)
    w.i32(ftm.unkI4)

    w.i32(len(ftm.tileLayerDefinitions))
    for layer_def in ftm.tileLayerDefinitions:
        w.string(layer_def.name)
        w.u8(layer_def.tileLayerIndex)
        w.u8(layer_def.usesWater)
        w.i32(layer_def.tileLayerZIndex)
        w.f32(layer_def.tileLayerHeight)
        w.u8(layer_def.visible)
        w.i32(len(layer_def.tileResourcePaths))
        for path in layer_def.tileResourcePaths:
            w.string(path)

    if len(ftm.tileLayers) != len(ftm.tileLayerDefinitions):
        raise FtmParseError(
            f"tileLayers count {len(ftm.tileLayers)} != defs {len(ftm.tileLayerDefinitions)}"
        )
    for layer in ftm.tileLayers:
        w.i32(layer.tileCountX)
        w.i32(layer.tileCountY)
        need = layer.tileCountX * layer.tileCountY
        if len(layer.indices) != need:
            raise FtmParseError(
                f"layer {layer.layerName} indices {len(layer.indices)} != {need}"
            )
        for idx in layer.indices:
            w.i32(idx)

    w.i32(len(ftm.prefabs))
    for prefab in ftm.prefabs:
        w.string(prefab.name)
        w.string(prefab.objId)
        w.buf.extend(b"\x00\x00")  # 2 pad bytes

    w.i32(len(ftm.sceneObjects))
    for obj in ftm.sceneObjects:
        w.i32(obj.prefabIndex)
        w.i32(obj.x)
        w.i32(obj.y)
        w.f32(obj.scaleHeight)
        w.f32(obj.scaleWidth)
        w.f32(obj.rotationY)
        w.f32(obj.rotationX)

    w.i32(len(ftm.interactableTiles))
    for tile in ftm.interactableTiles:
        w.u8(tile.unkB0)
        w.i32(tile.x)
        w.i32(tile.y)
        w.i32(len(tile.triggers))
        for tr in tile.triggers:
            w.u8(tr.unkB1)
            w.u8(tr.unkB2)
            w.u8(tr.unkB3)
            w.u8(tr.unkB4)
            w.u8(tr.unkB5)
            w.u8(tr.unkB6)
            w.i32(tr.unkI0)
            w.i32(tr.unkI1)
            w.i32(tr.unkI2)
            w.i32(tr.unkI3)
            w.i32(tr.objNumber)
            w.f32(tr.scale)
            w.i32(tr.unkI4)
            w.f32(tr.heightOffset)
            w.f32(tr.rotation)
            w.i32(len(tr.params))
            for p in tr.params:
                w.string(p)
            w.u8(tr.unkB7)
            w.i32(tr.unkI6)
            w.i32(len(tr.commands))
            for cmd in tr.commands:
                w.string(cmd)

    w.i32(len(ftm.blockedTiles))
    for tile in ftm.blockedTiles:
        w.i32(tile.x)
        w.i32(tile.y)

    w.raw(ftm.unknownBytes or b"")
    return bytes(w.buf)


def patch_scene_objects(
    ftm: ParsedFtm,
    patches: list[dict[str, Any]],
) -> ParsedFtm:
    """Return a copy of ftm with sceneObjects updated by index.

    Each patch: {index, prefabIndex?, x?, y?, scaleHeight?, scaleWidth?,
    rotationY?, rotationX?}
    """
    objects = list(ftm.sceneObjects)
    for patch in patches:
        try:
            idx = int(patch["index"])
        except (KeyError, TypeError, ValueError) as exc:
            raise FtmParseError(f"patch missing integer index: {patch!r}") from exc
        if idx < 0 or idx >= len(objects):
            raise FtmParseError(
                f"scene object index {idx} out of range (0..{len(objects) - 1})"
            )
        cur = objects[idx]
        objects[idx] = SceneObject(
            prefabIndex=int(patch.get("prefabIndex", cur.prefabIndex)),
            x=int(patch.get("x", cur.x)),
            y=int(patch.get("y", cur.y)),
            scaleHeight=float(patch.get("scaleHeight", cur.scaleHeight)),
            scaleWidth=float(patch.get("scaleWidth", cur.scaleWidth)),
            rotationY=float(patch.get("rotationY", cur.rotationY)),
            rotationX=float(patch.get("rotationX", cur.rotationX)),
            prefabName=cur.prefabName,
            prefabObjId=cur.prefabObjId,
        )
        # refresh prefab names if index changed
        pi = objects[idx].prefabIndex
        if 0 <= pi < len(ftm.prefabs):
            objects[idx].prefabName = ftm.prefabs[pi].name
            objects[idx].prefabObjId = ftm.prefabs[pi].objId
        else:
            objects[idx].prefabName = None
            objects[idx].prefabObjId = None

    return _copy_ftm(ftm, scene_objects=objects)


def _copy_ftm(
    ftm: ParsedFtm,
    *,
    scene_objects: list[SceneObject] | None = None,
    blocked_tiles: list[Any] | None = None,
) -> ParsedFtm:
    return ParsedFtm(
        mapPath=ftm.mapPath,
        tileCountX=ftm.tileCountX,
        tileCountY=ftm.tileCountY,
        unkI2=ftm.unkI2,
        indoorMode=ftm.indoorMode,
        unkI3=ftm.unkI3,
        unkI4=ftm.unkI4,
        tileLayerDefinitions=list(ftm.tileLayerDefinitions),
        tileLayers=list(ftm.tileLayers),
        prefabs=list(ftm.prefabs),
        sceneObjects=list(scene_objects if scene_objects is not None else ftm.sceneObjects),
        interactableTiles=list(ftm.interactableTiles),
        blockedTiles=list(blocked_tiles if blocked_tiles is not None else ftm.blockedTiles),
        unknownBytes=ftm.unknownBytes,
        byteLength=ftm.byteLength,
    )


def add_scene_object(ftm: ParsedFtm, obj: dict[str, Any]) -> ParsedFtm:
    """Append a placement. Required: prefabIndex, x, y."""
    pi = int(obj["prefabIndex"])
    name = None
    oid = None
    if 0 <= pi < len(ftm.prefabs):
        name = ftm.prefabs[pi].name
        oid = ftm.prefabs[pi].objId
    objects = list(ftm.sceneObjects)
    objects.append(
        SceneObject(
            prefabIndex=pi,
            x=int(obj.get("x", 0)),
            y=int(obj.get("y", 0)),
            scaleHeight=float(obj.get("scaleHeight", 1.0)),
            scaleWidth=float(obj.get("scaleWidth", 1.0)),
            rotationY=float(obj.get("rotationY", 0.0)),
            rotationX=float(obj.get("rotationX", 0.0)),
            prefabName=name,
            prefabObjId=oid,
        )
    )
    return _copy_ftm(ftm, scene_objects=objects)


def remove_scene_object(ftm: ParsedFtm, index: int) -> ParsedFtm:
    objects = list(ftm.sceneObjects)
    if index < 0 or index >= len(objects):
        raise FtmParseError(
            f"scene object index {index} out of range (0..{len(objects) - 1})"
        )
    del objects[index]
    return _copy_ftm(ftm, scene_objects=objects)


def set_blocked_tiles(
    ftm: ParsedFtm,
    tiles: list[dict[str, int]],
) -> ParsedFtm:
    blocked = [BlockedTile(x=int(t["x"]), y=int(t["y"])) for t in tiles]
    return _copy_ftm(ftm, blocked_tiles=blocked)

