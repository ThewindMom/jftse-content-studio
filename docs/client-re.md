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

Dense float3 tracks after header; layout scored as frame-major or track-major. Bone
names optional from body skeleton order. Not a full quat/skinning graph yet — positions
+ timing are recovered.

API: `GET /api/ani/parse?archive=Res/Player/PlayerA/AniA.res&member=NikiAniA.ani`  
Module: `python/ani_codec.py`

### Bone attach (DX9 Equipment socket)

Body mesh DAT embeds bind 4×4 matrices next to bone names. `Bone_Racket` on Niki:

- position ≈ `(5.86, 7.87, 4.16)`
- full `matrix4` row-major for Three.js `applyMatrix4`

Runtime script proof (`Rtm00.set`): `AttachBone=Bone_Racket`, `AttachPath=…/Niki_prop02.dat`.

API: `GET /api/bone-attach?char=NIKI&attachBone=Bone_Racket`  
UI: `EquipmentMeshPreview` places racket mesh via attach matrix (pink socket marker).  
Module: `python/bone_attach.py`

## Honest remaining limits

- Not a full Ghidra/DX9 renderer; topology still best-effort index recovery
- Submesh **index ranges** per material not fully table-parsed (names + counts known)
- Racket/equip preview is mesh decode, not live bone-attached Equipment matrix
- Animation (`.ani`) and FTM scene binary layouts not fully decoded
- Multi-draw court composition uses stage scene graph + multi-material names; studio UI still draws single primary mesh + one albedo by default

## Evidence paths (session)

- Stage graphs dump: `/tmp/ulw-client-re-stage-graphs.json`
- Modules: `python/stage_scene.py`, `mesh_meta.py`, `map_catalog.py`
