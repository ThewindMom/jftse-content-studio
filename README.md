# JFTSE Content Studio

Designer and reverse-engineering workbench for **Fantasy Tennis / JFTSE** client content.

| Workspace | What it does |
|-----------|----------------|
| **Items** | Racket/effect particle export, verified install to a **local** client only |
| **Map Studio** | Map metadata, stage asset validation, SQL packs, stage mesh preview |
| **Mesh Studio** | Stage/player mesh decode, textures, transforms, OBJ/glTF export |
| **Equipment** | Shop mesh index → racket DAT + **Bone_Racket** bind-matrix attach preview |

Sibling tooling for the [JFTSE](https://github.com/sstokic-tgm/JFTSE) emulator ecosystem. It **never writes the stock client** unless you install into an allowlisted local path.

Deep client format notes: [`docs/client-re.md`](docs/client-re.md).

---

## Quick start

```bash
git clone https://github.com/ThewindMom/jftse-content-studio.git
cd jftse-content-studio
bun install

# Point at a JFTSE checkout that contains client Res/ archives
export JFTSE_ROOT=/path/to/JFTSE
export JFTSE_STOCK_CLIENT=$JFTSE_ROOT/FantaTennis-Local-Client/client   # or .jftse-client-linux/client
export JFTSE_LOCAL_CLIENT=$JFTSE_ROOT/FantaTennis-Local-Client/client   # install target (optional)

bun run dev
# http://127.0.0.1:4310
```

### Requirements

| Tool | Notes |
|------|--------|
| [Bun](https://bun.sh) 1.3+ | App server, UI, tests |
| Python 3.12+ | Asset bridge (`studio_bridge.py`) |
| [uv](https://github.com/astral-sh/uv) | Bridge runs `uv run --with pillow --with cryptography` |
| JFTSE tree + client | `Res/` ZIP archives (Stage, Player, MapSet, Script, …) |

If `JFTSE_ROOT` is unset, the server uses sibling `../JFTSE`. Stock client defaults to `$JFTSE_ROOT/.jftse-client-linux/client`; the Python bridge also accepts `FantaTennis-Local-Client/client` as a fallback.

### Scripts

```bash
bun run dev          # start API + UI on PORT (default 4310)
bun test             # API integration suite (45 tests)
bunx tsc --noEmit    # TypeScript check
```

---

## Architecture

```text
Browser (React + Three.js)
        │  HTTP
        ▼
server/index.ts          Bun HTTP API, static web/
        │
        ▼
python/studio_bridge.py  CLI commands → JSON stdout
        │
        ├── mesh_codec / mesh_meta / mesh_texture
        ├── stage_scene / map_catalog / ftm_codec
        ├── item_mesh / bone_attach / ani_codec
        └── client_crypto (AES .set, XOR .tex)
                │
                ▼
        JFTSE stock/local client Res/*.res
```

- **UI:** React 19 + Three.js 0.185 (`web/`)
- **API:** Bun (`server/`)
- **Assets:** Python codecs; crypto/texture via `cryptography` + Pillow

---

## Workspaces

### 1. Items (effects)

Safe racket-aura pipeline:

1. Pick a stock racket (e.g. Dragon Slayer).
2. Choose effect preset + atlas thumbnails.
3. Build a verified fixed-size `Particle.res` (only dormant `Ice_Smoke02.set` may change).
4. Install to **local** client only (stock path refused).
5. Playtest readiness + launch command for Equipment check.

### 2. Map Studio

Relational map desk + stage preview:

1. Browse `S_Maps` with scenario / guardian links.
2. Bind / validate `Stage/Info.res` scripts (World / Sky / Collision).
3. Preview court geometry with stock textures.
4. Export SQL packs (`S_Maps`, scenarios, guardians).

Also exposes decrypted **map catalogs** (`MapObjRes`, `MapTileRes`, `MapHouseRes`) and full **FTM** placement parsing (see below).

### 3. Mesh Studio

Recovery-grade mesh modeler for proprietary `.dat` members:

1. List Stage / Sky / Collision meshes.
2. Multi-stride vertex recovery + solid-area index scoring.
3. UVs (interleaved or planar XZ) + stage albedo `.tex` → PNG.
4. Translate / rotate / scale with **stride-aware** rewrite (same byte length).
5. Export OBJ + glTF + meta JSON.

### 4. Equipment mesh + attach

1. Resolve shop `mesh` index → player DAT via AES `Info_Item_Mesh.set`.
2. Decode racket geometry + co-located texture when present.
3. Load body skeleton socket **`Bone_Racket`** bind 4×4.
4. Three.js preview places the racket at the socket (pink marker); missing socket falls back to origin.

---

## Client formats (current RE status)

| Format | Status | Module / API |
|--------|--------|----------------|
| `.res` | ZIP containers | — |
| `.set` | AES-128-ECB `TIMOTEI_ZION\0×4` | `client_crypto`, `/api/stage-set/decrypt` |
| `.tex` | XOR first 128 B → DDS | `mesh_codec` / `mesh_texture` |
| Stage `.set` scene | WorldFile + `[Object]` / `[Effect]` | `stage_scene`, `/api/stage-scene` |
| Mesh `.dat` | Multi-stride verts, area-scored u16 indices, materials, bones | `mesh_codec`, `mesh_meta` |
| Equipment materials | 64 B records, count @ `0x64` | `mesh_meta` |
| Item mesh catalog | AES XML Index → Path | `item_mesh`, `/api/item-mesh/resolve` |
| Map catalogs | MapObj / Tile / House | `map_catalog`, `/api/map-catalog` |
| **FTM / PRJ** | Full FT-ResTool schema + **serialize/export** of placement patches | `ftm_codec`, `/api/ftm/parse`, `POST /api/ftm/export` |
| **ANI** | Header + float3 tracks (e.g. 40×44 @ 30 fps) | `ani_codec`, `/api/ani/parse` |
| **Bone attach** | Bind matrix at `Bone_Racket` | `bone_attach`, `/api/bone-attach` |

FTM layout is a port of decompiled **FT-ResTool** (`FTMParser`): scene objects carry `prefabIndex`, `x`, `y`, `scaleHeight`, `scaleWidth`, `rotationY`, `rotationX`.

See [`docs/client-re.md`](docs/client-re.md) for field-level detail and remaining limits (full skinning playback, FTM→3D map scene compositor).

---

## HTTP API

| Area | Endpoints |
|------|-----------|
| Health / setup | `GET /api/health`, `GET /api/workflow` |
| Exports | `GET /api/exports?limit=&kind=` |
| Items / effects | `/api/items`, `/api/atlases`, `/api/atlases/preview`, `/api/presets`, `/api/effects/preview-build`, `/api/effects/install`, `/api/effects/slot-fields` |
| Playtest | `GET /api/playtest/status` |
| Maps | `/api/maps`, `/api/maps/export-sql`, `/api/map-studio/catalog`, `/api/map-studio/validate`, `/api/map-studio/export-pack` |
| Stage RE | `/api/stage-set/decrypt`, `/api/stage-scene`, `/api/map-catalog` |
| FTM / ANI / bones | `/api/ftm/parse`, `POST /api/ftm/export`, `/api/ani/parse`, `/api/bone-attach` |
| Meshes | `/api/mesh-studio/list`, `/parse`, `/meta`, `/texture`, `/export`, `/transform` |
| Equipment | `/api/item-mesh/resolve` |
| Packs | `GET/POST /api/packs`, `GET /api/packs/:name` |

### Bridge CLI (Python)

```bash
export JFTSE_ROOT=... JFTSE_STOCK_CLIENT=...
uv run --with pillow --with cryptography python python/studio_bridge.py <command> ...
```

Examples:

```bash
python python/studio_bridge.py stage-scene --member 1_Emerald_Beach.set
python python/studio_bridge.py ftm-parse --archive Res/MapSet/FantaCastle.res --member FantaCastleOutSide.ftm
python python/studio_bridge.py ani-parse --archive Res/Player/PlayerA/AniA.res --member NikiAniA.ani
python python/studio_bridge.py bone-attach --char NIKI --attach-bone Bone_Racket
python python/studio_bridge.py item-mesh-resolve --mesh-index 214 --char NIKI --meta-only
python python/studio_bridge.py mesh-parse --archive Res/Stage/Mesh01.res --member BF_Court01.dat --meta-only
```

---

## Safety model

- Particle exports verify only `Ice_Smoke02.set` changes; shared racket scripts stay byte-identical.
- **Install refuses `JFTSE_STOCK_CLIENT`.**
- Install allows `JFTSE_LOCAL_CLIENT`, `/tmp/**`, and studio `exports/`.
- Banned particle atlases (spaak/cloud classes) fail closed unless overridden.

Always use an **isolated local client** for installs.

---

## Day-1 runbook

1. **Configure** env vars (above) → `bun run dev` → open `http://127.0.0.1:4310` → confirm Bridge online / setup checklist.
2. **Items** → Dragon Slayer → Soft wind preset → Build & verify → Install to local → Copy launch command.
3. **Map Studio** → Emerald Beach → Validate stage → multi-draw **Stage scene compositor** (World + Object layers) → Export SQL pack.
4. **FTM desk** (Map Studio right panel) → Parse `FantaCastleOutSide.ftm` → select placement → optional **Export patched FTM** to `exports/`.
5. **Mesh Studio** → `BF_Court01.dat` → textured 3D view → Export OBJ/glTF.
6. **Equipment** → mesh index `214` → racket at Bone_Racket → **Load character ANI** → scrub/play live attach.
7. **Artifacts** → `exports/`, `content-packs/`, or `GET /api/exports`.

---

## Project layout

```text
server/                 Bun API + config + bridge runner
web/                    React UI (Items, MapStudio, MeshStudio, EquipmentMeshPreview)
python/
  studio_bridge.py      CLI façade (all commands)
  mesh_codec.py         Geometry decode / rewrite / OBJ-glTF
  mesh_meta.py          Materials, bones, equipment 64 B table
  mesh_texture.py       .tex resolve + PNG
  client_crypto.py      AES .set / key material
  stage_scene.py        Stage Info.res scene graph
  map_catalog.py        MapObj / Tile / House catalogs
  ftm_codec.py          FTM/PRJ parse + serialize (FT-ResTool-compatible)
  char_player.py        Canonical Char → Player* folder map
  ani_codec.py          Character .ani tracks
  item_mesh.py          Info_Item_Mesh resolve
  bone_attach.py        Bone_Racket bind pose
docs/client-re.md       Format RE notes
tests/api.test.ts       Integration suite
exports/                Generated artifacts (local)
content-packs/          Saved designer packs
DESIGN.md               Product / visual language
```

---

## Honest limits

| In scope today | Still limited / out of scope |
|----------------|------------------------------|
| Soft particle export + local install | Pixel-true DX9 Equipment silhouette |
| Stage scene graph + **multi-draw World/Object compositor** (layer toggles, cap 6) | Full multi-material submesh ranges + VFX `.eft` meshing |
| FTM placements + **2D desk** (select/focus) + **patched .ftm export** under `exports/` | Full FT-ResTool tile paint GUI / stock-client FTM install |
| ANI float3 tracks + **scrub/play player** (`maxFrames=0` full samples) | Full quat skinning graph / skinned body mesh |
| Bone_Racket bind matrix + **live ANI delta attach** | Live full hierarchical DX9 skeleton retarget |
| Mesh recovery + stride-aware edit + export | Blender-parity topology authoring |

---

## License / credits

Built for the JFTSE community tooling surface. Fantasy Tennis client assets remain subject to their original rights holders — this repo ships **tools**, not game assets.

Format knowledge draws on in-tree RE, **FT-ResTool** (Crypter / FTMParser), and community notes (e.g. `tools/wind_dragon_slayer` in JFTSE).
