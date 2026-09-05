# JFTSE Content Studio

A local, stock-safe authoring studio for Fantasy Tennis designers working with
the sibling JFTSE repository and a separate runnable client copy.

The studio turns known JFTSE formats and database contracts into four guided
workspaces:

- **Equipment** — start from a stock racket, author an effect, build verified
  archives, install to a local client, and prepare a manual Equipment check.
- **Content Pack** — build one equipment + map + stage + optional FTM content pack,
  install its files, audit/apply its aggregate SQL, and run local-client
  preflight.
- **Map Studio** — edit map metadata, validate the selected stage asset graph, export
  relational SQL, inspect PRJ/FTM placement data, and author bounded FTM edits.
- **Mesh Studio** — inspect decoded Stage/Sky/Collision DAT geometry, transform it,
  export OBJ/glTF, and run experimental authored-DAT workflows.

The [3D map-design workspace](docs/twinkle-studio.md) at `/map-studio` offers
Twinkle Town and an authored Oktoberfest variation with separate saved layouts,
textured scenery, character/cart rest-pose previews, and dependency-inclusive
stage archive export. Both designs target Twinkle Town in a separate test client.

This is not a replacement for Blender, a terrain sculptor, or an automated game
client. Browser previews are inspection aids; the DX9 client is the visual
authority.

## Safety model

The repository intentionally separates four locations:

| Location | Purpose | Write policy |
| --- | --- | --- |
| This repository | Studio code and generated `exports/` | Writable |
| Sibling JFTSE source | Parsers, format knowledge, helper tools | Read-only |
| Stock Fantasy Tennis client | Source archives and binaries | Read-only |
| Local client copy | Explicit designer install/playtest target | Writable after confirmation |

The server rejects:

- installs aimed at the configured stock client;
- destinations outside the configured local client;
- destinations outside `Res/…/*.res`, including traversal, absolute paths, and
  symlink escapes;
- source files outside this repository's `exports/` tree;
- SQL paths outside `exports/`;
- unsafe generated SQL or live apply without configured credentials.

Keep the stock `FantaTennis.exe`, `jftse.dll`, and `Res/` archives untouched.

## Prerequisites

- [Bun](https://bun.sh/) installed.
- [`uv`](https://docs.astral.sh/uv/) installed; the server runs the Python
  bridge through `uv run`.
- This repository beside the JFTSE checkout, or `JFTSE_ROOT` set explicitly.
- A readable stock client for source archives.
- A separate local client copy containing `FantaTennis.exe` and `jftse.dll`.
- An executable `START-FANTA-TENNIS.sh` beside the local client directory for
  full preflight, or an explicit `JFTSE_LAUNCH_SCRIPT`.
- Optional: a MySQL-compatible client and disposable/local Fantasy Tennis
  database for live SQL apply.

Expected default layout:

```text
parent/
├── JFTSE/
│   ├── src/
│   ├── tools/
│   └── .jftse-client-linux/
│       └── client/                  # stock/read-only
└── jftse-content-studio/
```

The runnable designer client should be a different directory.

## Setup

```bash
bun install

export JFTSE_ROOT=/absolute/path/to/JFTSE
export JFTSE_STOCK_CLIENT=/absolute/path/to/stock/client
export JFTSE_LOCAL_CLIENT=/absolute/path/to/designer-client/client

# Optional: required only for live SQL apply.
export JFTSE_DATABASE_URL='mysql://user:password@127.0.0.1:3306/fantasytennis'

bun run dev
```

Open `http://127.0.0.1:4310`.

The health/setup banners show the resolved paths and any missing requirement.
Do not continue to install until the local target is visibly distinct from the
stock target.

## Equipment workflow

1. Open **Equipment** and choose a stock racket base.
2. Continue to **Effect** and choose a preset/atlas or edit the exposed emitter
   fields.
3. Continue to **Export** and run **Build & verify export**.
4. Review the PASS/TODO checklist. Fix every TODO before continuing.
5. In **Install**, choose **Install to local client**.
6. Review the confirmation dialog's source and exact configured target, then
   confirm.
7. In **Local Check**, copy the launch command.
8. Launch the game yourself, log in, open Equipment, equip the authored racket,
   and visually inspect the silhouette and aura.

The browser particle preview is approximate and does not prove DX9 appearance.

## Content Pack workflow

1. Open **Content Pack** and configure equipment, map, stage script, and optional FTM
   input.
2. **Build pack**. Any draft edit after this invalidates the build and all
   downstream receipts.
3. **Confirm install** to write only the generated install plan into the
   configured local client.
4. **Audit SQL**. This dry-run validates the aggregate SQL without a database
   connection.
5. If a local database is configured, **Confirm SQL apply**. Live apply is
   unavailable until the matching dry-run passes.
6. Run **Local client preflight**.
7. Read every PASS/MISS row and follow the manual handoff. Preflight verifies
   files, SQL receipts, binaries, and launcher; it never claims gameplay passed.

## Map and FTM workflow

1. Open **Map Studio** and select a catalog entry.
2. Choose the exact stage script and run **Validate stage assets**.
3. Export/create actions remain disabled until the currently selected script
   has a passing validation receipt. Changing the script invalidates that
   receipt.
4. Use **Export SQL map pack** or **Create new map SQL** as appropriate.
5. In **FTM overworld desk**, enter a MapSet archive and `.ftm` or `.prj`
   member.
6. Parsing a PRJ shows its child FTM paths. Choose one explicitly; the studio
   resolves its archive member and then loads the placement desk.
7. Inspect placements and tile layers before using bounded paint/add/remove
   authoring actions.
8. Export the authored FTM + MapSet archive.
9. Review the explicit install confirmation before writing to the local client.
10. Launch manually and inspect map selection, placement, collision, and
    presentation in the DX9 client.

An empty PRJ and an FTM with zero placements are valid, distinct states. API
errors retain their detail and expose Retry without discarding the current
draft.

## Mesh workflow

1. Open **Mesh Studio** or use **Open World in Mesh Studio** from a validated map.
2. Select a Stage/Sky/Collision DAT member.
3. Inspect decoder confidence, bounds, triangle counts, UV mode, and texture
   resolution.
4. Adjust translation, rotation, scale, or wireframe view.
5. Export OBJ + glTF for external inspection.
6. Treat **Apply transform to DAT** and OBJ-to-DAT authoring as experimental.
   Preserve originals and validate results in the local client.

The decoder can recover useful geometry from known DAT layouts, but opaque
index/topology cases may fall back to triangle-soup interpretation.

## SQL and database behavior

- Map and Content Pack SQL is generated under `exports/`.
- Content Pack produces one ordered aggregate SQL file.
- Dry-run rejects unsupported INSERT shapes, dangerous verbs, unknown tables,
  malformed comments, and parse failures.
- Live apply invokes the configured MySQL client without exposing the password
  in the command line or API response.
- No database URL means no live apply; file builds, installs, and dry-run remain
  usable.

Use a disposable/local database first. The studio does not migrate, back up, or
restore a production database for you.

## Generated outputs

Generated binary and SQL artifacts are written beneath:

```text
exports/
```

Typical directories include:

- `effect-*`
- `content-pack-*`
- `equipment-pack-*`
- `stage-set-*`
- `ftm-author-*`
- `ftm-*`
- `mesh-edit-*`
- `mesh-new-*`
- top-level `map-pack-*.sql`, `map-create-*.sql`, and `maps-*.sql`

Reusable saved-pack metadata is stored separately under `content-packs/`.

Do not treat generated artifacts as validated game content until both server
checks and the manual client handoff pass.

## Day-one smoke checklist

Run this after setup or before handing the studio to a designer:

1. `bun install`
2. `bun run typecheck`
3. `bun test`
4. `bun run dev`
5. Open the studio and confirm **Bridge online**.
6. Confirm the setup checklist points to the intended stock and local clients.
7. Equipment: select Dragon Slayer, apply **Soft full-racket wind**, build,
   confirm install, and verify the local-check checklist.
8. Content Pack: build once, confirm install, dry-run SQL, and verify preflight. Apply
   SQL only when using a disposable configured database.
9. Map Studio: validate a stage, change scripts to confirm validation is invalidated,
   then parse `FantaCastle.prj` and explicitly open each child FTM.
10. Mesh Studio: open a World DAT from Map Studio, confirm the 3D viewport, switch away and
    back, and verify the selected mesh and draft controls persist.
11. At both 1440×900 and 390×844, visit all four workspaces and confirm there
    is no horizontal page overflow or clipped primary action.
12. Launch the local client manually and perform the Equipment/map visual
    checks. Record any DX9-only issue separately from browser preflight.

## Verification commands

```bash
bun run typecheck
bun test
bun build ./web/index.html --outdir /tmp/jftse-content-studio-build
```

## Known limitations

- The studio does not launch, log into, or control Fantasy Tennis.
- Browser particle rendering is not DX9-equivalent.
- Full Blender-style modeling, rig authoring, terrain sculpting, and arbitrary
  topology editing are out of scope.
- Stage/FTM/Mesh authoring is bounded by the format knowledge currently proven
  in JFTSE and FT-ResTool.
- Some authored DAT paths are experimental and require careful local-client
  validation.
- Live SQL apply requires an installed MySQL-compatible CLI and explicit
  credentials.

## License and credits

Built for the JFTSE community tooling surface. Fantasy Tennis client assets
remain subject to their original rights holders; this repository ships tools,
not game assets.

Format knowledge draws on the sibling JFTSE source, FT-ResTool
(Crypter/FTMParser), and community reverse-engineering notes.
