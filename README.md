# JFTSE Content Studio

Designer web platform for Fanta Tennis custom **items**, **effects**, and a full **Map Studio**.

Built as a sibling of the JFTSE monorepo.

### Items workflow
1. Pick a stock racket base  
2. Choose a preset + atlas + emitter  
3. Build a verified fixed-size particle export  
4. Install only to the local client  
5. Copy the launch command and playtest in Equipment  

### Map Studio
1. Browse `S_Maps` with scenario links + guardian counts  
2. Bind/infer `Stage/Info.res` scripts per map byte  
3. Validate World/Sky/Collision assets inside stock `.res` archives  
4. Export relational SQL packs (`S_Maps` + `Map_2_Scenarios` + `Guardian_2_Maps`)  
5. Save map drafts as content packs  

Map Studio is intentionally **metadata + stage-binding**. It does not invent court meshes.

## Run

```bash
cd /home/thewind/Projects/00_Random_Coding/260705_fanta_tennis/jftse-content-studio
bun install
bun run dev
```

Open `http://127.0.0.1:4310`.

Optional env:

```bash
export JFTSE_ROOT=/path/to/JFTSE
export JFTSE_STOCK_CLIENT=$JFTSE_ROOT/.jftse-client-linux/client
export JFTSE_LOCAL_CLIENT=$JFTSE_ROOT/FantaTennis-Local-Client/client
export PORT=4310
```

If unset, the studio discovers sibling `../JFTSE`.

## Designer workflow

| Step | What you do | What studio does |
|---|---|---|
| **Item** | Search/select a stock racket | Shows mesh/tex/effect binding; prefers Dragon Slayer `#10728` |
| **Effect** | Apply preset, browse atlas thumbnails, tune emitter | Soft-wind defaults; bans spaak/cloud classes unless overridden |
| **Export** | Build & verify | Replaces only dormant `Ice_Smoke02.set`; proves `Racket_001/002` unchanged |
| **Install** | Confirm local install | Refuses stock client; writes allowlisted local client only |
| **Playtest** | Copy launch command | Optional map SQL seed export for metadata-only map work |

Content packs can be saved/loaded so designers resume mid-flow.

## API

- `GET /api/health`
- `GET /api/workflow`
- `GET /api/presets`
- `GET /api/items?part=RACKET&q=`
- `GET /api/atlases?q=`
- `GET /api/atlases/preview?archive=&member=`
- `GET /api/maps`
- `POST /api/maps/export-sql`
- `GET /api/map-studio/catalog`
- `POST /api/map-studio/validate`
- `POST /api/map-studio/export-pack`
- `POST /api/effects/preview-build`
- `POST /api/effects/install`
- `GET|POST /api/packs`
- `GET /api/packs/:name`

## Tests

```bash
bun test
bunx tsc --noEmit
```

## Production safety

- Export verification: only `Ice_Smoke02.set` changes, shared racket scripts identical, archive size unchanged  
- Install refuses `JFTSE_STOCK_CLIENT`  
- Install allows `JFTSE_LOCAL_CLIENT`, `/tmp/**`, and studio exports  
- Default build is particle-only (seconds). Optional Item/ETC Dragon Slayer binding is slower (~1–2 min)

## Honest limits

- Browser particle preview is approximate; Equipment is authority  
- Item step starts from stock rackets (safe mesh/UV). It is not a full free-form mesh authoring DCC  
- Map desk exports metadata SQL + stock stage script suggestions, not custom stage geometry  
- Always point `JFTSE_LOCAL_CLIENT` at an isolated client

## Design

See `DESIGN.md`.
