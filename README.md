# JFTSE Content Studio

Public designer platform for **Fantasy Tennis / JFTSE** content:

- **Items** — racket/effect workflow with verified particle export  
- **Map Studio** — relational map metadata + stage asset validation  
- **Mesh Studio** — reverse-engineered Stage/Sky/Collision `.dat` mesh decode, 3D view, transform, OBJ/glTF export  

Sibling tooling for the [JFTSE](https://github.com/jftse) emulator ecosystem. It never writes the stock client unless you explicitly install into an allowlisted local client path.

---

## Quick start

```bash
git clone https://github.com/ThewindMom/jftse-content-studio.git
cd jftse-content-studio
bun install

# Point at a JFTSE checkout that contains the stock client assets
export JFTSE_ROOT=/path/to/JFTSE
export JFTSE_STOCK_CLIENT=$JFTSE_ROOT/.jftse-client-linux/client
export JFTSE_LOCAL_CLIENT=$JFTSE_ROOT/FantaTennis-Local-Client/client   # optional install target

bun run dev
# http://127.0.0.1:4310
```

Requirements:

- [Bun](https://bun.sh) 1.3+
- Python 3.12+ with `uv` (bridge uses JFTSE `wind_dragon_slayer` + Pillow on demand)
- A local JFTSE tree with client `Res/` archives

If `JFTSE_ROOT` is unset, the server tries sibling `../JFTSE`.

---

## Workspaces

### 1) Items
Designer path for racket auras:

1. Pick a stock racket (Dragon Slayer preferred)  
2. Choose effect preset + atlas thumbnails  
3. Build verified fixed-size `Particle.res` (only dormant `Ice_Smoke02.set`)  
4. Install to **local** client only (stock path refused)  
5. Copy launch command and playtest in Equipment  

### 2) Map Studio
Metadata + binding desk (not a full terrain DCC):

1. Browse `S_Maps` with scenario links and guardian counts  
2. Bind/infer `Stage/Info.res` scripts  
3. Validate World/Sky/Collision assets inside stock `.res` archives  
4. Export relational SQL packs (`S_Maps`, `Map_2_Scenarios`, `Guardian_2_Maps`)  

### 3) Mesh Studio
Best-effort proprietary mesh modeler:

1. Catalog Stage/Sky/Collision `.dat` members  
2. Decode float3 vertex runs from Fantasy Tennis `.dat` blobs  
3. Inspect in a Three.js viewport (orbit, wireframe)  
4. Apply translate / rotate / scale and rewrite same-size `.dat`  
5. Export **OBJ + glTF + meta JSON** for DCC pipelines  

#### Mesh format research notes
Public documentation for Fantasy Tennis mesh binaries is effectively nonexistent. Related public work:

- Emulator/server ecosystem around JFTSE  
- [alexandru-bagu/FantasyTennis.Ghidra](https://github.com/alexandru-bagu/FantasyTennis.Ghidra) (client reverse engineering, not a mesh schema dump)

This studio’s codec (`python/mesh_codec.py`) is evidence-driven:

- `.res` containers are ZIP archives  
- mesh members are little-endian proprietary `.dat` files  
- a 12×`uint32` header is followed by dense `float3` position runs  
- index buffers are recovered when contiguous `uint16` triangles exist; otherwise a triangle-soup fallback is used  
- transforms rewrite vertex floats in-place so byte length stays identical for safer reintegration experiments  

Topology/materials/UVs are **not** fully solved. Treat Mesh Studio as a production-ready **recovery + edit + export** workbench, not Blender feature-parity.

---

## API surface

| Area | Endpoints |
|---|---|
| Health | `GET /api/health` (includes `setup` checklist) |
| Exports library | `GET /api/exports?limit=&kind=` |
| Items/effects | `/api/items`, `/api/atlases`, `/api/presets`, `/api/effects/preview-build`, `/api/effects/install` |
| Maps | `/api/map-studio/catalog`, `/api/map-studio/validate`, `/api/map-studio/export-pack` |
| Meshes | `/api/mesh-studio/list`, `/api/mesh-studio/parse`, `/api/mesh-studio/export`, `/api/mesh-studio/transform` |
| Packs | `GET/POST /api/packs`, `GET /api/packs/:name` |

---

## Safety model

- Particle exports verify only `Ice_Smoke02.set` changes and shared `Racket_001/002` stay byte-identical  
- Install refuses `JFTSE_STOCK_CLIENT`  
- Install allows `JFTSE_LOCAL_CLIENT`, `/tmp/**`, and studio `exports/`  
- Banned particle atlases (spaak/cloud classes) fail closed unless explicitly overridden  

---

## Day-1 designer runbook

1. **Configure**
   ```bash
   export JFTSE_ROOT=/path/to/JFTSE
   export JFTSE_STOCK_CLIENT=$JFTSE_ROOT/.jftse-client-linux/client
   export JFTSE_LOCAL_CLIENT=$JFTSE_ROOT/FantaTennis-Local-Client/client
   bun run dev
   ```
   Open `http://127.0.0.1:4310`. Confirm **Bridge online** and that the setup checklist is green (or expand **Setup incomplete** and fix env paths).

2. **Items → aura**
   - Items workspace → pick **Dragon Slayer(Black)** (or any stock racket)
   - Effect → **Soft full-racket wind** (or another preset) + atlas thumbs
   - Export → **Build & verify export** (only `Ice_Smoke02.set` may change)
   - Install → **Install to local client** → **Confirm install**
   - Playtest → **Copy launch command** → run the local client and check Equipment

3. **Map Studio**
   - Open a map (e.g. Emerald Beach) → **Validate stage assets** → **Export SQL map pack** → optional **Save map pack**

4. **Mesh Studio**
   - Select a court `.dat` → confirm the 3D viewport is not blank → **Export OBJ + glTF**

5. **Find artifacts**
   - Items Export step lists **Recent exports** (also `GET /api/exports`)
   - Files land under `exports/` and `content-packs/`

The in-app **Getting started** banner repeats this path and can be dismissed (stored in `localStorage`).

## Development

```bash
bun test
bunx tsc --noEmit
bun run dev
```

Project layout:

```text
server/           Bun API + static UI host
web/              React workspaces (Items, Maps, Meshes)
python/           Asset bridge + mesh_codec + studio_bridge
exports/          Generated packs (gitignored artifacts)
content-packs/    Saved designer packs
DESIGN.md         Visual/product language
```

---

## Honest limits / intentionally out of scope

| In scope now | Out of scope (for now) |
|---|---|
| Soft particle export + local install | Pixel-true in-browser game renderer |
| Map metadata + stage validation + SQL packs | Full terrain/sculpt DCC |
| Mesh DAT decode, transform, OBJ/glTF | Blender-parity materials/UVs/skinning |
| Setup checklist, exports library, guided day-1 UX | Multi-user auth / cloud collab |

- Browser particle preview ≠ final Equipment look  
- Always use an isolated local client for installs  
- Stock client writes are refused by design  

---

## License / credits

Built for the JFTSE community tooling surface. Fantasy Tennis client assets remain subject to their original rights holders — this repo ships **tools**, not game assets.
