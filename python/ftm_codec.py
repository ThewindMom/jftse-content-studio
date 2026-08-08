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
