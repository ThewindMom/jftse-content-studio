# Design a Twinkle Town layout

Use `/map-studio` to choose the original Twinkle Town or the authored Oktoberfest variation, then arrange scenery without starting the client. These are separate Studio designs, not separate game map IDs.

## Start the workspace

1. Install Bun and uv, then run `bun install` in this repository.
2. Keep the official client resources outside this repository. Set `JFTSE_STOCK_CLIENT` to the directory containing `Res/`.
3. Provide `Res/Stage/Info.res`, `Res/Stage/Mesh02.res`, the stock `Res/Stage/Tex*.res` archives, and `Res/MapRes/DecoRes/Mesh00.res` plus its `Tex*.res` archives. The fixture validation used Stage Tex000 through Tex010 and DecoRes Tex00 and Tex01.
   Provide `Res/StageObj/Object01.res`, `Object02.res`, `Object03.res`, and `Extra.res` for the stock character and prop previews. Native original-model export also requires the fingerprinted pristine `Res/Collision.res` and DecoRes barrel template; modified or missing templates fail closed.
4. Start the server:

```sh
JFTSE_ROOT=/path/to/workspace JFTSE_STOCK_CLIENT=/path/to/private/client bun run start
```

`JFTSE_ROOT` is required by the existing configuration. The Twinkle workspace does not require the sibling Java server checkout. Other Studio workspaces may require it.

Open `/map-studio` on the server address printed at startup. In an Amp orb, start a supervised service instead:

```sh
amp orb service start map-studio --command 'env JFTSE_ROOT=/path/to/workspace JFTSE_STOCK_CLIENT=/path/to/private/client bun run /path/to/repo/server/index.ts' --portal
```

Use the service's Amp portal and open `/map-studio`. Do not expose private resources through a public static host.

## Open the Oktoberfest design

Set `JFTSE_FESTIVAL_RESOURCES` to a private directory containing the latest authored `FestivalHall.res`, `FestivalPretzel.res`, `FestivalHeart.res`, `FestivalFood.res`, `Tex009.res`, `Tex010.res`, and `festival-placements.tsv`. These assets are not shipped in the repository.

Use the authored Tex009/Tex010 archives, not the pristine inputs or the earlier blanket-recoloring prototype. The latest design changes only the signboard, stall sign, and two tent fabrics. Keep these archives separate from stock.

Restart the server with that environment variable, then choose **Oktoberfest** from **All maps**. Its starting layout removes the two original carriage placements and adds the 30 TSV placements, retaining the other 11 stock placements. Animation index and phase metadata are retained but not played in the preview. A changed preset or authored resource fingerprint rejects stale festival drafts rather than overwriting them.

## Arrange scenery

1. Choose a prop from the library. Each thumbnail renders the actual decoded geometry.
2. Select the object in the scene or sidebar. Drag its gizmo, or enter position, Y rotation, and uniform scale in the inspector.
3. Use **Court**, **Overview**, **Top**, or **Match study** to review the arrangement. Press **F** to frame the selection. Orbit with the left mouse button, pan with the right, and zoom with the wheel.
   If nearby scenery obstructs a character or cart, enable **Isolate selection**. This affects the preview only, not export.
4. Use **Undo**, **Redo**, **Duplicate**, or **Delete object** as needed. An excluded object remains in the document but does not enter the exported SET.
5. Click **Save layout** to persist `exports/twinkle-layout.json` or `exports/oktoberfest-layout.json`. Reloading restores that design's saved document. Unsaved edits trigger a navigation warning. **Restore starting layout** is undoable and does not save automatically.
6. Use **Download layout JSON** and **Import layout JSON** to transfer editable layouts. A layout is bound to the original stage hash; a changed source is rejected.
7. Click **Export stage ZIP** to download a cloned `Res/Stage/Info.res`, the layout JSON, the decrypted revised SET, and installation instructions. Referenced Festival archives are included. The Oktoberfest design also includes its two authored stage-texture archives. The exporter checks the encrypted SET round trip and never installs or changes stock files.

Keep generated archives and screenshots private: they contain or depict official-client content.

## Install directly into a test copy

The Linux Studio server can prepare a test copy without manual archive copying. Set `JFTSE_STUDIO_TEST_ROOT` to a separate empty directory, outside `JFTSE_STOCK_CLIENT`. The installer refuses to adopt an existing nonempty directory or an alias of the source. This setting is server-controlled; the browser cannot choose an arbitrary destination.

```sh
JFTSE_ROOT=/path/to/workspace \
JFTSE_STOCK_CLIENT=/path/to/pristine-client \
JFTSE_FESTIVAL_RESOURCES=/path/to/private/festival \
JFTSE_STUDIO_TEST_ROOT=/path/to/studio-test-copies \
bun run start
```

1. Open **Install in a test client** in the left sidebar.
2. Click **Install in fresh test copy**. Studio exports the current layout, copies the pristine source, installs every exported `Res/` archive, and verifies source, backup and installed file hashes.
3. Read the resulting client folder and download the hash receipt. No executable or launcher is started. A resources-only fixture is labeled as such.
4. In the native lab, close any previous client and run `FantaTennis.exe` directly with the displayed folder as its working directory. Local auth, game, chat, relay and AC services must already be configured. Inspect actual sockets and test the map; installation success is not native acceptance.
5. To undo, close the client and click **Restore pristine test copy**. Use the newly displayed `/backup` folder. This selects a verified baseline snapshot with local endpoints, not the original source or the previous edited layout.

Each installation has a unique directory containing `client/`, `backup/`, and `receipt.json`. The store's `active.json` selects the directory and copy. Only this small pointer is replaced atomically, after the complete copy passes validation. Failed writes or interrupted preparation cannot expose a partially installed client through the pointer. A process lock rejects simultaneous operations. Existing generations remain untouched, so a process using an older directory is not modified in place.

Each install needs approximately twice the pristine client's disk space. Older generations are retained for review rather than deleted automatically. Close clients before manually removing obsolete, inactive generations. Do not change `active.json` by hand. A crash before publication can leave an unselected generation; the previous pointer remains authoritative. This is a process-failure guarantee, not a power-loss durability claim for every client file.

The installer requires the observed single-area `ServerInfo.ini` schema, including `[Default].AreaCount=1`, `[Area0].Name=Ini3`, `Count=1`, `IP_1`, and `Port_1`. It rejects missing or additional sections/keys and writes CRLF with `IP_1=127.0.0.1` and `Port_1=5894` in both copies. The source remains byte-identical. No updater is run; if one is run outside Studio, reapply and verify these settings before launch. ServerInfo.ini is the only endpoint text input observed for this direct-executable fixture, not a guarantee about all client builds. Downstream routing comes from the local services; outbound guards and socket inspection remain required.

Automation uses `GET /api/twinkle/client` for status, `POST /api/twinkle/client?action=install` with the current layout JSON, and `POST /api/twinkle/client?action=restore`. `GET /api/twinkle/client?receipt=1` downloads full source/before/after SHA-256 maps. On a lost HTTP response, read status before retrying. The equivalent Python bridge command is `twinkle-client --action status|install|restore`; install also takes `--payload layout.json` and the same server environment variables. The desktop/native lab remains responsible for launch and in-game checks.

## Load an export into a test client

1. Close the game. Create a separate pristine client copy and back up its `Res` folder. Do not use your pristine source or working client.
2. Extract the ZIP to a staging directory and review its `README.txt` and archive inventory.
3. Copy the ZIP's entire `Res` folder into that separate test client's `Res` folder. Include the supplied `StageObj/Festival*.res` and `Stage/Tex*.res` dependencies, not just `Info.res`.
4. Start that test copy through your existing JFTSE setup and select **Twinkle Town**. Both designs replace map 2; they do not register another selectable game map.
5. To undo, restore the test copy's backup. Start from pristine resources when switching designs so festival texture overrides do not survive unintentionally.

The export replaces the test copy's Info.res with a clone of the configured stock archive. Other custom edits already in that test client's Info.res would be lost. Client loading, material resolution, animation, and gameplay compatibility still require a separate authorized native test.

## Limits

- The court and town render all 96 static submeshes with material bindings and lightmaps. This is not a native DX9 fidelity claim.
- With the supplied archives, the scene has two fixed environment assets and 33 placeable library assets: eight Deco props, eight stock character/cart meshes, three Extra static props, four stock-based Oktoberfest variants, and ten original Oktoberfest models. All six distinct meshes used by the 13 stock Twinkle placements render as complete rest poses. Missing or unsupported resources stay explicit guides, never heuristic partial meshes.
- Skinned geometry uses the stored model-space bind pose. Skin palettes and animation-track boundaries are validated, but playback, animation-frame selection, effects, and runtime shadows are not simulated. Opaque trailing animation descriptors are not interpreted.
- The match-study camera is approximate. The court-clearance guide is advisory, not a collision check.
- Terrain, stock topology/materials/collision, and stock cameras are locked. Original-model collision proxies follow placement transforms and appear with **Court & collision guides**; they are coarse solid boxes, not detailed or editable collision meshes. The workspace edits SET placements, not arbitrary vertices or maps.
- Client installation and gameplay compatibility remain untested. Exported layouts still need a separate authorized client check before release.
- Each design has its own server-side draft, shared by browser sessions; there is no concurrent-edit merge.
- Generated geometry and converted textures are cached under `.tmp/twinkle-assets`. Restart the server after replacing stock resources. Drafts referencing an older source are preserved and refused, not silently reset.

## Original Oktoberfest models

Choose **New Oktoberfest models** in the prop library. These are newly constructed meshes, not renamed or recolored stock assets:

- `Oktoberfest_BrewersPavilion.glb`
- `Oktoberfest_PretzelStand.glb`
- `Oktoberfest_GingerbreadStand.glb`
- `Oktoberfest_FoodStand.glb`
- `Oktoberfest_BeerGarden.glb`
- `Oktoberfest_FestivalArch.glb`
- `Oktoberfest_Festzelt.glb`
- `Oktoberfest_Maypole.glb`
- `Oktoberfest_BarrelWagon.glb`
- `Oktoberfest_Bandstand.glb`
- `Oktoberfest_HouseBanner.glb`
- `Oktoberfest_FlagLine.glb`
- `Oktoberfest_FlagPost.glb`
- `Oktoberfest_FountainGarland.glb`

The deterministic source is `python/oktoberfest_models.py`. It builds beveled timber, cloth roofs, sculpted pretzels and biscuits, mugs, furniture and bunting, with an original procedural surface atlas. No client model or texture bytes are used by this generator. The style is a low-poly interpretation, not a claim of exact original art-direction fidelity.

Click a library model to place it. **Isolate selection** and **Frame object** let you inspect it. Move, rotate, scale, duplicate and save work as for other props. On the Oktoberfest map, **Use original festival props** replaces the four stock-based festival anchors in the current document; positions and scales are retained, animation metadata is removed. This action is undoable and does not automatically overwrite your saved layout.

**Download GLB / OBJ pack** includes all generated meshes, embedded GLB textures, shared OBJ material/PNG files and a README. Import GLB into Blender or another glTF editor for vertex-level work. Generate the pack without any private fixtures:

```sh
PYTHONPATH=python uv run --with pillow python -c 'from pathlib import Path; from oktoberfest_models import prepare_originals; prepare_originals(Path(".tmp/original-models"))'
```

Native atlas export requires Pillow 11.2.1 or newer for DXT1 compression. The
opaque 512×512 atlas has all ten mip levels through 1×1 and the same DDS header
fields as observed stock tent textures. The earlier uncompressed A8R8G8B8 atlas
caused a splash-screen hang in the parent's isolated native control; standard
DX9 format support does not imply support by this client's loader. Compressed
output still needs independent native validation. Existing archive members are
preserved byte-for-byte; only the new atlas member is added.

Stage export now converts active original placements to newly generated static AduMesh DATs in `Res/StageObj/Oktoberfest.res`, writes the original atlas as DDS/TEX, and appends transformed solid proxies to both stock Twinkle match/chat collision meshes in `Res/Collision.res`. The stock geometry and unrelated archive payloads are preserved. The exported SET uses native DAT references while the editable layout retains GLB identities. Excluded originals contribute neither geometry nor collision.

This is **experimental native-format authoring, not verified client support**. Export requires exact pristine template fingerprints and a byte-identical stock static round trip. The writer retains an opaque 304-byte stock node; its loader semantics remain unknown. Texture lookup order is also unknown: packaging the atlas alongside DATs and in Stage/Tex010 is a compatibility candidate, not resolution proof. `native-export.json` records `nativeRuntimeVerified: false`. Native loading, shading, collision response and clearance require a separately authorized client test. No client was executed or modified during implementation. Studio edits placements, not vertices; the portable pack is not a whole-map scene export.

### Visual references

The improved timber framing, greenery, warm lamps, communal seating and larger tent use official photographic references: [Augustiner Festhalle](https://www.oktoberfest.de/en/beer-tents/big-tents/augustiner-festhalle) and [Festhalle Schottenhamel](https://www.oktoberfest.de/en/tents/big-tents/festhalle-schottenhamel), inspected September 2026. These informed original low-poly forms; no photograph, brewery logo or client texture was copied into the generated atlas. The assets remain stylized scenery rather than architectural replicas.

## Check the implementation

```sh
bun run typecheck
bun test tests/twinkleDocument.test.ts
PYTHONPATH=python uv run --with pillow --with cryptography python -m unittest discover -s python -p 'test_*.py' -v
git diff --check
```

These tests use synthetic resources, not committed client binaries. The repository-wide Bun suite also needs the sibling JFTSE environment and runtime fixtures.
