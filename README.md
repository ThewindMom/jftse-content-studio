# JFTSE Content Studio

Designer web platform for creating and exporting Fanta Tennis custom **items**, **effects**, and **map metadata**.

Sibling of the JFTSE monorepo. It does **not** rewrite the stock client unless you deliberately point exports at an install target.

## Versions

| Lane | Status | Capability |
|---|---|---|
| **V1** | Shipped | Item catalog browser, effect emitter editor, atlas library, fixed-size particle export via JFTSE `wind_dragon_slayer` tooling |
| **V2** | Shipped | Approximate particle canvas preview, content-pack save/load, banned-atlas + shared-script safety rails |
| **V3** | Shipped (metadata) | Map desk from `scripts/sql/maps.sql` + stock `Stage/Info.res` script listing. No full custom stage geometry exporter yet |

## Requirements

- Bun 1.3+
- Python 3.12+ with `uv` (uses JFTSE tooling + Pillow for atlas decode)
- Local checkout of JFTSE with stock client assets under `.jftse-client-linux/client`

## Configure

```bash
export JFTSE_ROOT=/path/to/JFTSE
export JFTSE_STOCK_CLIENT=$JFTSE_ROOT/.jftse-client-linux/client
export PORT=4310
```

Defaults point at:

```text
/home/thewind/Projects/00_Random_Coding/260705_fanta_tennis/JFTSE
```

## Run

```bash
cd jftse-content-studio
bun install
bun run dev
```

Open `http://127.0.0.1:4310`.

## API

- `GET /api/health`
- `GET /api/items?part=RACKET`
- `GET /api/atlases`
- `GET /api/maps`
- `POST /api/effects/preview-build`
- `GET|POST /api/packs`

### Effect build safety

Rejected by default:

- texture paths containing `spaak` / cloud-electric markers (`BANNED_ATLAS`)
- references to shared `Racket_001` / `Racket_002` scripts
- quantity outside 1–40

Successful builds write under `exports/` and only replace dormant `Ice_Smoke02.set` inside a copied `Particle.res`.

## Tests

```bash
bun test
```

## Design

See `DESIGN.md`.

## Production safety

Verified before an export is returned:

- only `Ice_Smoke02.set` changed
- `Racket_001.set` / `Racket_002.set` byte-identical to stock
- member order preserved
- archive size unchanged
- decoded TexturePath / quantity / color fields match the request

Install endpoint:

```bash
POST /api/effects/install
```

- **refuses** `JFTSE_STOCK_CLIENT`
- **allows** `JFTSE_LOCAL_CLIENT`, `/tmp/**`, and `exports/`

Default UI build is particle-only (fast). Optional Item/ETC Dragon Slayer binding archives take ~1–2 minutes because they rebuild encrypted catalogs.

## Honest limits

- Browser particle preview is approximate.
- Final racket look must be checked in Equipment via the game client.
- Item library is currently read/browse + proven Dragon Slayer binding export, not a full free-form new-mesh authoring suite.
- Custom map **geometry** is not authored here yet — only server map metadata + stock stage script binding.
- Treat permanent-client install as deliberate: point `JFTSE_LOCAL_CLIENT` at your isolated client only.
