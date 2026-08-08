# Fantasy Tennis client reverse-engineering notes

Captured 2026-08 during Content Studio work. Source of truth is the stock Linux /
local client under `JFTSE/FantaTennis-Local-Client/client` (or `.jftse-client-linux/client`).

## Binaries

| File | Notes |
|------|--------|
| `FantaTennis.exe` | PE32 GUI ~3.7 MB, Direct3D9 fixed-function + VS/PS 2.x; engine RTTI `AduMesh`, `AduObject`, `AduEngine`, … |
| `jftse.dll` | PE32 DLL (emulator companion) |
| `FT_Launcher.exe` | .NET launcher |

DX9 / mesh-related strings in the EXE: `MeshMaterialList`, `nMaterials`, `MeshNormals`,
`MeshTextureCoords`, `AttachBone`, `AttachPath`, `Bone_Racket`, `xof 0302bin 0064`
(X-file token remnants — on-disk DATs are proprietary AduMesh, not raw `.x`).

## Crypto (ft_restool Crypter)

| Format | Algorithm |
|--------|-----------|
| `.set` scripts | AES-128-ECB, key `TIMOTEI_ZION\0\0\0\0`, first byte = pad/null identifier |
| `.tex` textures | XOR `0xFF` on first 128 bytes (full-file XOR also yields valid DDS) |

Implementation: `python/client_crypto.py`, `mesh_codec.decrypt_tex_to_dds`.

## Stage scene graph (`Res/Stage/Info.res` → `*.set`)

After AES decrypt, INI-like text. Example `1_Emerald_Beach.set`:

```ini
[Default]
WorldFile= "Res/Stage/Mesh01/BF_Court01.dat"
World_Chat= "Res/Stage/Mesh01/BF_Court01.dat"
Collision= "…"
SkyFile= "…"
FogNear= …
Cam_Intro= "CAM_STAGE_…"

[Object]
File= "Res/Stage/Mesh01/BF_All.dat"
Level= 0

[Object]
File= "Res/ad/BF_Advert.dat"
Level= 0

[Effect]
File= "Res/Effect/EftA/EF_Flower00.eft"
Position= 0.0, 0.0, 0.0
Head= 0.0, 0.0, 1.0
Level= 1
```

- **WorldFile** = primary court mesh (what Mesh Studio first recovered).
- **[Object]** layers = props / full stage shell / ads (e.g. `BF_All.dat`, `AT_Side.dat`).
- **[Effect]** layers = particle/VFX paths with position + heading.
- All 17 stage sets parse cleanly; object/effect counts vary (Atlantis: 4 objs + 3 efts).

API: `GET /api/stage-scene?member=1_Emerald_Beach.set`  
API: `GET /api/stage-set/decrypt?member=1_Emerald_Beach.set`  
Bridge: `stage-scene`, `stage-set-decrypt`  
Module: `python/stage_scene.py`

## Mesh DAT (`Res/Stage/MeshNN.res`, StageObj, Deco, Player, …)

### Header (12 × uint32 LE)

Observed layout (heuristic names):

| Index | Role |
|-------|------|
| 0–2 | Section byte sizes (often ~vertex/index/aux) |
| 3 | Always `2` on sampled assets (version/flags) |
| 4 / 6 | `count1` / `count2` — frequently equal → **submesh / material slot count** (BF_Court01=2, BF_All=74, Niki body count1=64 count2=7) |
| 5,7 | zeros |
| 8–11 | flags / extras |

### Geometry recovery (best-effort)

- Dense float3 runs (interleaved pos/normal/UV at stride 12–32)
- Vertex recovery: multi-stride score (reject cube noise, unit normals, UV false runs)
- Index recovery: **score u16 runs by solid triangle area × coverage**
  - BF_Court01: ~582 solid tris, ~39% vertex coverage (was ~322 / 15%)
- UVs: interleaved when stride ≥20, else planar XZ projection

### Multi-material texture names (embedded ASCII)

DATs store **albedo basenames** (no extension) used as material ids, often near the tail:

- `BF_Court01.dat` → `BF_Coat00_B`, `BF_Net00_B`, `A_BF_CoatMark00_A`, `A_BF_CoatDirt01_B`, …
- `BF_All.dat` → 100+ names (`BF_Lawn00_A`, trees, houses, sea, …)

`_SM` / `_LM` suffixes = shadowmap / lightmap variants. Content Studio now:

1. Extracts material list via `mesh_meta.extract_material_names`
2. Resolves first preferred albedo to a real `Tex*.res` `.tex` member

API: `GET /api/mesh-studio/meta?archive=Res/Stage/Mesh01.res&member=BF_Court01.dat`  
Bridge: `mesh-meta` (also attached on `mesh-parse`)  
Module: `python/mesh_meta.py`

### Bones / equipment sockets

Character body meshes (e.g. `Res/Player/PlayerA/Mesh.res` → `Niki.dat`, ~9.8 MB) embed a
**Bip01 / Bone*** skeleton table, including equipment sockets:

| Socket | Role |
|--------|------|
| `Bone_Racket` | Racket attach (confirmed @ ~offset 9021128 in Niki.dat) |
| `Bone_ball` | Ball attach |
| `Bone_bag` | Bag / accessory |

Runtime scripts (`Res/Script/Rtmovie.res` Cam/RTM sets) use fields:

- `AttachPath` — resource path for attached mesh
- `AttachBone` — bone name on parent
- `AttachTime` — attach timing
- `ShadowBone` — shadow projection bone (often `Bip01`)

Concrete example (`Rtm00.set`):

```ini
AttachPath  = "Res/Player/PlayerA/Item00/Niki_prop02.dat"
AttachBone  = "Bone_Racket"
AttachTime  = 2.7, 5.0
ShadowBone  = "Bip01"
```

Racket **preview** in studio is still mesh decode + optional co-located tex; full DX9
bone-matrix skinning/attach is not simulated in Three.js.

### Stage shell decode (scene Object layer)

`1_Emerald_Beach` Object layer `BF_All.dat` (Mesh01.res) recovers cleanly with the
same multi-stride codec as the court:

| Mesh | verts | solid tris | solidArea | header count1/2 |
|------|------:|----------:|----------:|-----------------|
| `BF_Court01.dat` | 2402 | 582 | ~380k | 2 / 2 |
| `BF_All.dat` | 3041 | 4645 | ~2.3M | 74 / 74 |

## Map world catalogs (`Res/MapSet/Script.res`)

AES → INI/XML:

| Member | Content |
|--------|---------|
| `MapObjRes.set` | Obj_Number / Obj_ID / Obj_Path → StageObj & Deco DATs (~66 objects) |
| `MapTileRes.set` | Tile layers: Ground/Grass/Hill/Under/Water → `P0_L{n}` tiles |
| `MapHouseRes.set` | House interiors / castle inside meshes |
| `MapEnemyInfo.set` | XML enemy stats |
| `NPC_List.set` | XML localized NPC names |
| `RandMapInfo00.set` | Dungeon random-map layer paths + room `.rom` |

API: `GET /api/map-catalog`  
Module: `python/map_catalog.py`

## Equipment mesh catalog (`Res/Script/Item.res` → `Info_Item_Mesh.set`)

AES → UTF-8 XML:

```xml
<Item Char="NIKI" Index="214" Path="Res/Player/PlayerA/Item07/Niki_CommonRacket41.dat" Desc="드래곤 슬레이어"/>
```

Shop item `mesh` field is this `Index`. 1921 entries across characters.

Resource graph (also `tools/wind_dragon_slayer/FORMAT_NOTES.md`):

1. `Item_Parts.set` → `(Char, Part, Mesh, Tex, Effect)`
2. `(Char, Mesh)` → DAT via `Info_Item_Mesh`
3. **`Tex` selects a positional 64-byte material record** in the DAT tail
4. Material stem → `.tex` or `.ifl` in the same RES archive
5. `Effect` is a separate racket-effect path (not the material animation)

### Equipment DAT material table (verified `Niki_CommonRacket41.dat`)

| Field | Value |
|-------|--------|
| Count | `uint32le` @ **0x64** (e.g. 4) |
| Table start | `file_size - 6 - count×64` |
| Record size | **64 bytes** |
| Record layout | null-terminated stem (`CommonRacket41`, `CommonRacketX0`…`X2`) + pad/params |

Material keys are **positional** — do not insert/remove records without a full dependent-offset parser. Studio exposes this via `mesh-meta` → `equipmentMaterialTable`.

API: `GET /api/item-mesh/resolve?meshIndex=214&char=NIKI`  
API: `GET /api/mesh-studio/meta?archive=Res/Player/PlayerA/Item07.res&member=Niki_CommonRacket41.dat`

Player archives: `Res/Player/Player{A-G}/ItemNN.res` + `Mesh.res` body meshes + `Ani*.res` / `FtmAni*.res` animations.

D3D9 skinning note (EXE / FVF): fixed-function supports `XYZBn` + `LASTBETA_UBYTE4` blend weights — full bone-matrix skinning is still not simulated in Content Studio Three.js previews.

## Other formats (inventory)

| Ext / path | Notes |
|------------|--------|
| `.res` | ZIP containers for almost all assets |
| `.dat` | Proprietary AduMesh binary (geometry + materials + optional bones) |
| `.tex` | XOR→DDS textures |
| `.set` | AES scripts/XML |
| `.ani` | Character animation packs (`NikiAniA.ani`, …) — binary, 12×u32-style header (e.g. three section sizes then records); not fully decoded |
| `.Eft` | Effect definitions — same family of 3× section-size u32 header + binary payload (~650 KB for Atlantis bubbles); particle paths not fully schema'd |
| `.ftm` / `.prj` | Map/furniture scene sets (`MapSet/*.res`) |
| `.rom` | Room templates for random maps |
| `.ifl` | Animated texture frame lists (ocean swell, …) |
| `.wav` / `.ogg` | Sound / BGM |

### FTM / PRJ (overworld map chunks) — full schema (FT-ResTool)

Ported from decompiled `com.ft.restool.parser.ftm.FTMParser` in `~/Downloads/ft_restool.jar`.

**PRJ:** `u32 ftmCount` + pascal (u8 len + ASCII) FTM base paths.

**FTM parse order (LE):**

1. `mapPath` (pascal)
2. `tileCountX`, `tileCountY`, `unkI2`, `indoorMode` (u8), `unkI3`, `unkI4`
3. **Tile layers** — count, then each: name, layerIndex, usesWater, zIndex, height (f32), visible, resource path list
4. **Layer grids** — for each layer: `X`, `Y`, then `X*Y` int tile indices
5. **Prefabs** — count, then each: `name`, `objId`, + 2 pad bytes
6. **Scene objects (placements)** — count, then each:
   - `prefabIndex` (i32), `x`, `y` (i32 tile coords)
   - `scaleHeight`, `scaleWidth`, `rotationY`, `rotationX` (f32)
7. **Interactable tiles** — NPC event triggers + command strings
8. **Blocked tiles** — (x, y) pairs
9. Trailing unknown bytes

Verified `FantaCastleOutSide.ftm`: grid 50×70, 1 prefab `CastleOutSide`, 1 scene object at (50,12), 207 interactables, 1866 blocked.

API: `GET /api/ftm/parse?archive=Res/MapSet/FantaCastle.res&member=FantaCastleOutSide.ftm`  
Module: `python/ftm_codec.py`

### ANI character animation

Header (28 B LE), verified NikiAniA/B:

| Field | AniA | AniB |
|-------|-----:|-----:|
| trackCount | 40 | 40 |
| duration | 1.4667 (=44/30) | 0.800 (=24/30) |
| frameCount | 44 | 24 |
| sectionA/B/C | 356699 / 355409 / 355409 | 404635 / 403345 / 403345 |
| file size | 1 426 808 | 1 618 552 |
| A+B+C+28 | 1 067 545 (tail ~359 KB) | 1 211 353 (tail ~407 KB) |

**Section probe (2026-08 session, deeper pass):**

| Region | Structure |
|--------|-----------|
| **A** | **Primary multi-clip float3 stack** — block = `trackCount×frameCount×12` (NikiAniA: 21120 B). **16** high-smoothness track-major clips + residual. clip0 root ≈ `(0, 6.37, 0)`. |
| **B** | **Same byte length as C** on NikiAniA/B; invariant **A−B = 1290**. All of A/B/C are **odd-sized**. Exhaustive probe (`ani_rotation_probe.py`): not float3/float4/s16-quat/f16/zlib-raw/48-bit; phase-1 float4 stream ~56% unit (medn=1) but first-clip ≤42%; no contiguous unit float4 block ≥90%. Custom bitstream still **unknown**. |
| **C** | **Secondary float3-shaped multi-clip stack** (same block size, lower smoothness than A). Bulk float4 unit-length ≈ 58–60% — **not** ≥90%, so **not** auto-promoted to quaternions. Possible euler/aux channel — unproven. |
| **Tail** | Large residual after A\|B\|C (~359 KB AniA, high entropy ~7.5). Phase-3 float4 ~56% unit; not zlib; not float3 multi-clip; first-clip unit ~57% < 0.9. Encoding **unknown**. `tailHypothesis.encodingProbe` scores candidates. |

Studio API:
- `sectionProbe.multiClip` (channel A), `multiClipC` (channel C)
- `sectionProbe.sectionBHypothesis`, `tailHypothesis`, `rotationHypothesis`
- `?clipIndex=N&channel=A|C` selects stack + clip

**Still blocked for full runtime parity:** confident quat graph in ANI; section B bitstream; exact submesh index buffers linking skin runs to material groups.

API: `GET /api/ani/parse?archive=…&member=…&maxFrames=0&clipIndex=0&channel=A`  
Module: `python/ani_codec.py`

## Skinned body vertices (56 B records) — verified

Body DATs (e.g. `Niki.dat`) embed DX9-style skinned vertices in **multiple contiguous runs**:

| Offset | Type | Field |
|-------:|------|--------|
| 0 | float4 | blend weights (sum ≈ 1) |
| 16 | uint16×4 | blend bone indices |
| 24 | float3 | position |
| 36 | float3 | normal (unit) |
| 48 | float2 | UV |
| **56** | | **record size** |

Niki recovers **~20k+** skinned verts across many submesh runs; bone indices are small integers (≪ 128).

API: `GET /api/skin/parse?char=NIKI` (+ `includeVertices=1&maxVertices=2000`)  
Module: `python/skin_codec.py`  
Response includes **`skeleton`**: ordered palette `bones[i]` with `name`, `parent`/`parentIndex`, local `matrix4` (@+96), `worldMatrix4` (@+224), `auxMatrix4` (@+160). Niki: **64** bones, skin `boneIndexMax=24` → `skeletonCoversSkin=true`.

### Skeleton table (304 B records) — verified

Body DAT stores a fixed-stride hierarchy starting at root `Bip01` (parent `None`):

| Offset | Field |
|-------:|--------|
| 0 | `name[32]` |
| 32 | `parent[32]` |
| 96 | local bind 4×4 (column-major) |
| 160 | aux 4×4 |
| 224 | world bind 4×4 |
| **304** | **record size** |

Index order = skin blend indices / Three.js `Skeleton.bones[i]`.

UI: `EquipmentMeshPreview` builds `THREE.SkinnedMesh` from skin vertices + palette (`web/skinnedBody.ts`).

### Bone attach (DX9 Equipment socket)

Body mesh DAT embeds bind 4×4 matrices next to bone names. `Bone_Racket` on Niki is palette index **52** (parent `Bip01_R_Hand`):

- local `matrix4` translation ≈ `(5.03, 8.19, -0.25)` (column-major @ 12–14)
- full `matrix4` is **D3D/Three column-major** — pass to `Matrix4.fromArray` (**do not transpose**)

Runtime script proof (`Rtm00.set`): `AttachBone=Bone_Racket`, `AttachPath=…/Niki_prop02.dat`.

API: `GET /api/bone-attach?char=NIKI&attachBone=Bone_Racket` (also returns full `skeleton`)  
UI: racket at attach matrix + pink marker; body SkinnedMesh alongside.  
Module: `python/bone_attach.py`

### ANI → bone drive

- Dense **unit float4 quats not found** on NikiAniA/B after exhaustive probe:
  - A/C ≈ 55–60% unit samples as float4 noise; B phase0 ≈ 0% as float4
  - Section B candidates: float3, float4, s16×4, s16 xyz-compress, f16, zlib-raw, odd-pad, byte-phase float4 (phase1 ~56% unit), first-clip phases (≤42%), 48-bit 3×15 bitstream, contiguous float4-in-B — **none ≥ 0.9 unit**
  - Tail probe: phase3 ~56% unit, not zlib/float3 multi-clip, first-clip ~57% — **not confident**
  - Multi-clip C float3 is **not** a ≥90% xyz-compressed-quat channel either
- API: `sectionBHypothesis.encodingProbe` + `tailHypothesis.encodingProbe` carry score tables
- `driveMode` / `rotationHypothesis.recommendedDriveMode`:
  - `quat` only when extract confirms dense unit float4 (`rotationHypothesis.confident`)
  - else **`hierarchical-fk`** (default): parent chain + look-at swing from float3 position deltas
  - `position-only-fk` remains available as a flat/legacy experiment
- Track labels optional via `?char=NIKI` (skeleton name order)
- UI: Equipment preview uses hierarchical-fk when `hasRotations` is false. No throw on missing quats.

## Honest remaining limits

- Not a full Ghidra/DX9 renderer; topology still best-effort index recovery
- Submesh **index ranges** per material not fully table-parsed (names + counts known)
- Body SkinnedMesh bind pose works; animation uses **hierarchical-fk** (position deltas + look-at) until a true ANI rotation channel is decoded
- Hierarchical-fk is better than flat position dumps but is **not** full DX9 local-quat retarget parity
- `.ani` section B bitstream still unknown; section C multi-clip float3 not proven as euler or compressed quats
- FTM binary **read** is complete (FT-ResTool schema); studio ships a 2D inspect desk, not binary rewrite
- Stage multi-draw compositor loads World + Object DATs with visibility toggles (draw cap); sky/collision optional; `.eft` effects not meshed

## Evidence paths (session)

- Stage graphs dump: `/tmp/ulw-client-re-stage-graphs.json`
- Modules: `python/stage_scene.py`, `mesh_meta.py`, `map_catalog.py`
