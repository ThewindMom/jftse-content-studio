# ResTool / JFTSE capability matrix (Wave 2)

Source-grounded read/write map for JFTSE Content Studio. This file is the
Wave 2 contract: what Studio can author today, which oracle proves it, which
fixture proves the claim, and the exact product wording designers should see.

Oracle jar (read-only):

```text
/home/thewind/Downloads/ft_restool.jar
SHA-256 590ccfa6d88e0e7ae5af864af212543ec41342197603fd183f782315e3b0402f
```

Sibling trees used as oracles (never mutated by this matrix work):

- JFTSE emulator: `../JFTSE` (chat-server `GameManager`, scripts SQL, tools notes)
- Local/stock client: `../JFTSE/FantaTennis-Local-Client/client` (and the Linux
  install under `../JFTSE/.jftse-client-linux/client` when present)
- Studio codecs: `python/*_codec.py`, `python/*_author.py`, `server/mapSceneCompiler.ts`

Hard limits carried into every row that touches them:

1. **No general DAT writer.** Studio rewrites vertex positions into an existing
   stock DAT layout only. New topology, full material tables, and bone tables
   are not exported as a freestanding AduMesh author.
2. **No general EFT writer.** Studio inspects `.Eft` headers and samples. It
   does not emit particle/emitter binaries.
3. **Map spawn coordinates are design-only.** JFTSE hard-codes player spawn
   ranges in `GameManager`. Scene-document spawns never become runtime packets.

---

## Matrix summary

| # | Capability | Studio read | Studio write | Runtime status |
|---|------------|-------------|--------------|----------------|
| 1 | FTM | Full parse | Full serialize + patch/add/remove/paint/blocked | Installable MapSet member; DX9 visual check required |
| 2 | PRJ | Full parse (child FTM list) | None in Studio | Read-only picker; ResTool can write PRJ, Studio does not |
| 3 | SET | Decrypt + parse stage/catalog XML/INI | Encrypt + stage Info.res rewrite; Item mesh catalog patch | Installable `.set` inside `.res`; size may drift |
| 4 | TEX | XOR decode to DDS | XOR encode from DDS | Round-trip binary; DX9 texture check required |
| 5 | DAT | Best-effort mesh decode + material/bone meta | Position rewrite / stock clone only (**no general writer**) | Experimental transform path; clone path is production-bounded |
| 6 | EFT | Header + position-sample inspect | **None (no general EFT writer)** | Markers only; client owns particles |
| 7 | Item binding | Info_Item_Mesh resolve + mesh/meta | Clone DAT + catalog SET + `S_Product` SQL | Shop row + mesh install; equip in local client |
| 8 | Map spawns | Design-desk read/write in scene JSON | Design only; compiler marks unsupported | **Not runtime.** JFTSE hard-codes spawn ranges |
| 9 | Terrain | Design reference path + FTM tile grids | FTM tile paint / blocked tiles; Blender path not compiled | Tile/collision installable; sculpt geometry not authored |
| 10 | Stage materials | DAT albedo names + equipment 64-byte table + TEX preview | Design material refs only; no DAT material-table rewrite | Preview/bind in browser; stage material compile unsupported |

---

## Row 1. FTM (overworld map chunk)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read:** full LE schema via `parse_ftm_bytes` / `load_ftm_from_res`. **Write:** full rewrite via `serialize_ftm`; authoring through `ftm-author` and content-pack `_write_ftm_bundle` (scene object patch/add/remove, blocked tiles, tile paint). |
| **Oracle** | ResTool `com.ft.restool.parser.ftm.FTMParser` (+ `FTMFile`, `SceneObject`, `TileLayerDefinition`, `BlockedTile`, …). Local client member under `Res/MapSet/*.res`. |
| **Evidence** | Jar classes: `com/ft/restool/parser/ftm/FTMParser.class` (methods/strings: `readFile`, `readByte`, `readString`, `readInt`, `readFloat`, `setSceneObjects`, `setBlockedTiles`, `writeInt`/`writeFloat` binary path, `.ftm.json` Gson dump). Studio port: `python/ftm_codec.py` header comment names `FTMParser`; `serialize_ftm` docstring "FT-ResTool-compatible .ftm bytes (full rewrite)". Bridge: `python/author_cmds.py` `cmd_ftm_author`, `python/content_pack.py` `_write_ftm_bundle`. API: `GET /api/ftm/parse`, bridge `ftm-author`. Docs: `docs/client-re.md` FTM section. |
| **Executable fixture** | Stock: `Res/MapSet/FantaCastle.res` → `FantaCastleOutSide.ftm`. Expected parse: mapPath `Res/MapSet/FantaCastle/FantaCastleOutSide`, grid **50×70**, **1** prefab `CastleOutSide`, **1** scene object, **207** interactables, **1866** blocked. Author fixture: round-trip `serialize_ftm(parse_ftm_bytes(raw))` then re-parse; sceneObjectCount must match (`FTM_ROUNDTRIP_MISMATCH` guard). Export dir pattern: `exports/ftm-author-*`. |
| **Runtime status** | Written MapSet `.res` is installable to the configured local client (`destRelative` = source archive). Presentation and collision need **manual local-client verification**. |
| **Product wording** | "FTM overworld desk can parse, paint tiles, edit placements, and export a MapSet archive. Install writes only the generated archive. Open the local client and visually inspect placement and collision. Browser preview is approximate." |

---

## Row 2. PRJ (FTM project list)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read:** `parse_prj_bytes` / `load_prj_from_res` (`u32 ftmCount` + pascal paths). **Write:** **none.** Studio never serializes `.prj`. UI forces an explicit child-FTM pick after PRJ parse. |
| **Oracle** | ResTool `com.ft.restool.parser.prj.PRJReader` / `PRJFile`. Local client `FantaCastle.prj`. |
| **Evidence** | Jar: `com/ft/restool/parser/prj/PRJReader.class` strings `readFile`, `readInt`, `readString`, `writeInt`, `writeByte`, `write`, `ftmCount`, `setFtmFiles`, `Invalid PRJ file:`, `No FTM files to write in PRJ file:` (ResTool write path exists; Studio does not call it). Studio: `python/ftm_codec.py` `parse_prj_bytes`; `python/studio_bridge.py` FTM parse branch `kind: "prj"`. Tests: `tests/api.test.ts` "PRJ parse lists child FTM paths"; `tests/ftmSelection.test.ts`. Product IA: `DESIGN.md` Map Studio "PRJ parsing exposes an explicit child-FTM picker"; `README.md` Map and FTM workflow steps 5-6. |
| **Executable fixture** | Stock: `Res/MapSet/FantaCastle.res` → `FantaCastle.prj` (**81** bytes). Expected: `ftmCount=2`, paths `Res/MapSet/FantaCastle/FantaCastle` and `Res/MapSet/FantaCastle/FantaCastleOutSide`. Empty PRJ (`ftmCount=0`) is a valid distinct UI state. |
| **Runtime status** | PRJ is a path index only. Runtime map chunks are the child FTM binaries. Studio does not rewrite PRJ membership. |
| **Product wording** | "Parsing a PRJ shows its child FTM paths. Choose one explicitly; the studio resolves its archive member and then loads the placement desk. An empty PRJ and an FTM with zero placements are valid, distinct states." |

---

## Row 3. SET (AES scripts: stage Info + item catalogs)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read:** `decrypt_set_file` then INI/XML parse (`stage_scene`, `map_catalog`, `item_mesh`). **Write:** `encrypt_set_file` via `write_stage_set` (stage fields / append `[Object]`) and `patch_item_mesh_catalog` (`Info_Item_Mesh.set`). |
| **Oracle** | ResTool `com.ft.restool.util.Crypter` (`decryptSetFileInMemory`, `encryptSetFileInMemory`, `decryptSetFile`, `encryptToSetFile`, key string `TIMOTEI_ZION`, cipher `AES/ECB/NoPadding`). Local client `Res/Stage/Info.res`, `Res/Script/Item.res`. |
| **Evidence** | Jar strings on `Crypter.class`: `TIMOTEI_ZION`, `AES/ECB/NoPadding`, `decryptSetFileInMemory`, `encryptSetFileInMemory`, `.set.original`. Studio: `python/client_crypto.py` (`AES_SET_KEY = b"TIMOTEI_ZION\x00\x00\x00\x00"`, layout comment mirrors restool). Authors: `python/stage_set_author.py` `write_stage_set`; `python/equipment_author.py` `patch_item_mesh_catalog`. Bridge cmds: `stage-set-write`. Docs: `docs/client-re.md` Crypto + Stage scene graph. |
| **Executable fixture** | Stage: `Res/Stage/Info.res` → `1_Emerald_Beach.set`. After decrypt, plaintext starts with `[Default]` and includes `WorldFile= "Res/Stage/Mesh01/BF_Court01.dat"`. Write fixture: `stage-set-write` with a field override, re-decrypt export, assert key present; note `sizeMatch` may be false when plaintext length changes. Catalog: `Res/Script/Item.res` → `Info_Item_Mesh.set` entry `Char="NIKI" Index="214"`. Export dirs: `exports/stage-set-*`, equipment catalog under pack out dirs. |
| **Runtime status** | Patched `Info.res` / `Item.res` install under allowlisted `Res/**/*.res`. Stage script must pass `validate_stage_script` before map SQL export. Catalog/SQL shop rows need login + equip checks. |
| **Product wording** | "Stage scripts decrypt, edit, and re-encrypt with the stock AES path. Export builds a replacement Info.res member. Confirm install names the generated source and exact configured local target. Ready for manual local-client verification." |

---

## Row 4. TEX (XOR texture container)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read:** `tex_to_dds` / `mesh_codec.decrypt_tex_to_dds` (XOR first 128 bytes with `0xFF`). **Write:** `dds_to_tex` / `write_tex_from_dds` / bridge `tex-encode`. Round-trip command `tex-roundtrip`. |
| **Oracle** | ResTool `Crypter.decryptTexFile` / `decryptTexFileInMemory` / `encryptTexFile` (`xorKey`, `.tex` ↔ `.dds`). DDS pixel walk: `com.ft.restool.parser.dds.DDSReader`. Local client `Res/Stage/Tex*.res` and player item archives. |
| **Evidence** | Jar `Crypter.class`: `decryptTexFile`, `encryptTexFile`, `xorKey`, `.tex`, `.dds`. Studio: `python/tex_codec.py` (`_XOR_LIMIT = 128`); `python/mesh_codec.py` `decrypt_tex_to_dds` docstring cites ft_restool Crypter. JFTSE tool notes: `JFTSE/tools/wind_dragon_slayer/FORMAT_NOTES.md` "Current TEX codec" encode/decode contract. Bridge: `author_cmds.cmd_tex_encode`, `cmd_tex_roundtrip`. |
| **Executable fixture** | Any stock `.tex` from stage `Tex000.res` (or equipment paired tex). Steps: `tex-roundtrip --tex <path>` expects `ddsMagic == "DDS "` and `roundtripEqual: true`. Encode fixture: known DDS → `tex-encode` → XOR header differs from DDS, body after byte 128 identical. |
| **Runtime status** | Drop-in `.tex` members inside existing `.res` archives are client-loadable when dimensions, FourCC, and mips match the stock contract (`FORMAT_NOTES.md`). Wrong size/atlas looks "exploded" in DX9. |
| **Product wording** | "Textures convert through the stock XOR DDS path. Preserve width, height, compression, and mip chain. Local client preflight checks files only; open the local client and visually inspect the material." |

---

## Row 5. DAT (AduMesh geometry container)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read:** best-effort decode (`mesh_codec.decode_mesh_bytes`), header/meta (`mesh_meta.analyze_mesh_dat`), skin/skeleton (`skin_codec`), bone attach. **Write:** **not a general DAT writer.** Supported writes: (a) `write_positions_into_dat` / `mesh-transform` / `mesh-obj-import` into an **existing** vertex layout; (b) byte-identical or override clone of a stock equipment DAT into a new Item archive (`clone_equipment_mesh`). No freestanding "new mesh from glTF topology" exporter. |
| **Oracle** | Local client stock DATs (`BF_Court01.dat`, `BF_All.dat`, `Niki.dat`, `Niki_CommonRacket41.dat`). Client EXE strings (`AduMesh`, `MeshMaterialList`) in `docs/client-re.md`. ResTool jar has **no** DAT mesh parser package (only ftm/prj/dds/ifl). JFTSE `FORMAT_NOTES.md` DAT constraints. |
| **Evidence** | `python/mesh_codec.py` module doc: "can write transforms back into the original vertex bytes"; `write_positions_into_dat` warns multi-stride overwrite. `python/mesh_obj_import.py` requires equal vertex counts. `python/equipment_author.py` `clone_equipment_mesh` copies stock member bytes. `server/equipmentCreatorPackage.ts` writer mode `"stock-topology-clone"`, limitations: imported glTF/OBJ topology is "preview-spec-only". `DESIGN.md` Mesh Studio: "DAT transform/new-topology authoring remains clearly marked experimental." `README.md` Known limitations: "Some authored DAT paths are experimental". |
| **Executable fixture** | Decode: `Res/Stage/Mesh01.res` → `BF_Court01.dat` (header count1/count2 = 2/2; materials include `BF_Coat00_B`). Equipment clone: mesh index **214** / char **NIKI** → `Res/Player/PlayerA/Item07.res` / `Niki_CommonRacket41.dat`. Transform fixture: export OBJ from decode, reimport same vertex count, assert byte length unchanged and positions differ only at stride slots. **Reject** any claim of "export new DAT topology" without a new oracle. |
| **Runtime status** | Stock clones and catalog-bound paths are the supported production path. Position-patched DATs are experimental until DX9 inspection passes. |
| **Product wording** | "There is no general DAT writer. Mesh Studio recovers geometry for inspection and can rewrite positions inside a stock layout. Equipment export clones a stock racket topology. Imported glTF/OBJ topology is specification and comparison data only. Treat Apply transform to DAT as experimental. Preserve originals and validate results in the local client." |

---

## Row 6. EFT (stage / racket effect binary)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read only:** `parse_eft_bytes` / `load_eft_from_path` / bridge `eft-parse`. **Write: none. No general EFT writer.** Content pack may pass through an existing particle archive path; it does not build `.Eft` bytes. |
| **Oracle** | Local client effect members referenced from stage sets (`[Effect] File= ...`). Stage graph docs in `docs/client-re.md`. ResTool jar has **no** `parser/eft` package. |
| **Evidence** | `python/eft_codec.py`: docstring "Best-effort .Eft parse for studio markers (not full emitter simulation)"; return `note`: "Heuristic .Eft header; full particle simulation remains client-side."; no `write`/`serialize` symbol. Bridge registers `eft-parse` only (`author_cmds.cmd_eft_parse`). `docs/client-re.md` inventory: ".Eft … particle paths not fully schema'd"; honest limits: ".eft effects not meshed". Equipment effects: `FORMAT_NOTES.md` native path reuses stock `EF_Dragon_Racket_Spe.Eft` bytes rather than authoring new emitters. |
| **Executable fixture** | Stage set `1_Emerald_Beach.set` (and siblings) list `[Effect]` paths after decrypt; call `eft-parse --path <File value>`. Expect `ok: true`, `byteLength > 48`, `headerU32` length 12, optional `positionSamples`. **No** encode/round-trip fixture exists, by design. |
| **Runtime status** | Client DX9 owns emitter simulation. Studio markers and browser particle preview are approximate only. |
| **Product wording** | "Effect files can be inspected, not authored. There is no general EFT writer. The browser particle preview is approximate and does not prove DX9 appearance. Particle curves on equipment packs reuse recovered stock envelopes; DX9 client verification remains authoritative." |

---

## Row 7. Item binding (mesh index ↔ DAT ↔ shop SQL)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read:** `Info_Item_Mesh.set` → archive/member (`item_mesh.resolve_item_mesh_path`); equipment material table; optional `Item_Parts` graph from JFTSE notes. **Write:** `clone_equipment_mesh` + `patch_item_mesh_catalog` + `build_item_sql_pack` (`S_Product` / `product` UPSERT). Unified via `equipment-pack` and content-pack equipment part. |
| **Oracle** | Local client `Res/Script/Item.res` + `Res/Player/Player{A-G}/ItemNN.res`. JFTSE SQL product tables. `FORMAT_NOTES.md` resource graph. |
| **Evidence** | `python/item_mesh.py` documents AES decrypt XML shape `Char/Index/Path/Desc`. Verified stock: NIKI index **214** → `Res/Player/PlayerA/Item07/Niki_CommonRacket41.dat`. `python/equipment_author.py` `build_item_sql_pack` emits `INSERT INTO S_Product ... mesh, tex, effect`. `python/mesh_meta.py` `parse_equipment_material_table` (count @ `0x64`, 64-byte records). `server/equipmentCreatorPackage.ts` enforces material slot bounds and stock-topology writer mode. Golden: `reference-projects/equipment-golden.json`. |
| **Executable fixture** | Resolve `meshIndex=214&char=NIKI` → archive `Res/Player/PlayerA/Item07.res`, member `Niki_CommonRacket41.dat`. Pack fixture: `equipment-pack` produces `manifest.json` with installPlan entries for Item*.res and Item.res, plus `item-pack.sql`. Material table fixture: meta on that DAT returns positional stems (`CommonRacket41`, `CommonRacketX0`…). |
| **Runtime status** | After install + SQL apply (when configured), designer must log in, open Equipment, equip the item, and inspect silhouette/aura. Preflight never claims gameplay passed. |
| **Product wording** | "Equipment binding maps a shop mesh index to a player Item archive, patches Info_Item_Mesh, and emits S_Product SQL. Production compatibility is bounded by the automatically selected stock racket topology. Local client preflight. Open the local client, log in, equip, and visually inspect." |

---

## Row 8. Map spawns (player start positions)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Design desk only.** Scene document stores `spawns[]` (`web/mapSceneTypes.ts` `MapSpawn`). UI can add home/away markers. **Compiler does not emit runtime spawn data.** |
| **Oracle** | JFTSE `chat-server/.../GameManager.java` hard-coded `rnd.nextFloat` ranges. Studio `server/mapSceneCompiler.ts` `runtimeUnsupported`. |
| **Evidence** | `GameManager.java` town square join: `spawnX = rnd.nextFloat(40.0f, 46.0f); spawnY = rnd.nextFloat(60.0f, 64.0f);`. Room create mode 0: `(10..21, 15..50)`; mode 2 (else branch): same 40-46 / 60-64 band; mode 1 home levels use fixed floats. Packet: `S2CRoomPlayerInformationPacket(..., spawnX, spawnY, ...)`. Studio: `mapSceneCompiler.ts` lines that `runtimeUnsupported.push("player-spawn compilation")` whenever `validated.spawns.length > 0`, while still cloning spawns into `design`. Tests: `tests/mapSceneCompiler.test.ts` expects `"player-spawn compilation"` in `runtimeUnsupported` and still `design.spawns` length 2. `web/mapSceneManifest.ts` requires ≥2 spawns for a *design* playable map package, not for JFTSE packets. |
| **Executable fixture** | `reference-projects/map-golden.json` and `tests/mapSceneCompiler.test.ts` `authoredScene()` with home `[-4,0,0]` and away `[4,0,0]`. Compile must list `player-spawn compilation` under `runtimeUnsupported` and must **not** place spawn coordinates into `payload.ftm` or SQL. |
| **Runtime status** | **Design-only.** Runtime player coordinates come from JFTSE hard-coded ranges, not from Studio scene JSON or FTM. |
| **Product wording** | "Spawn markers are design documentation only. JFTSE hard-codes runtime spawn ranges in the chat-server GameManager. The map compiler records player-spawn compilation as unsupported. Do not tell designers that court spawns will move players in the live emulator." |

---

## Row 9. Terrain (tile layers, collision, sculpt references)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read:** FTM tile layer defs + `X*Y` index grids; map catalogs `MapTileRes.set` / `MapObjRes.set`; scene `terrainSource` string. **Write:** FTM `paint_tile_layer` and `set_blocked_tiles` through `ftm-author` / content pack. Blender/sculpt path is a preserved reference only. |
| **Oracle** | ResTool FTM tile classes (`TileLayerDefinition`, `TileLayerData`, `TileLayerIndices`, `BlockedTile`). Local client MapSet FTMs + `Res/MapSet/Script.res`. Studio compiler unsupported list. |
| **Evidence** | `python/ftm_codec.py` parse/serialize tile defs, grids, blocked tiles; `paint_tile_layer`, `set_blocked_tiles`. `python/map_catalog.py` `MapTileRes.set` layers Ground/Grass/Hill/Under/Water. `server/mapSceneCompiler.ts`: if `references.terrainSource.trim()` then `runtimeUnsupported.push("terrain geometry compilation")`; blocked cells **do** compile into `payload.ftm.blockedTiles`. `DESIGN.md` / `README.md`: not a terrain sculptor. Tests: compiler fixture with `terrainSource: "roundtrip/compiled-court.blend"` expects `"terrain geometry compilation"` unsupported while `blockedTiles: [{x:2,y:3}]` is present in payload. |
| **Executable fixture** | FTM: `FantaCastleOutSide.ftm` tile grid 50×70 + blocked count 1866. Author: paint one cell via `tilePaint.cells`, re-parse, assert index change; set `blockedTiles` list and assert count. Design package: golden map `terrainSource` ending in `.blend` remains in `design.terrainSource` after compile. |
| **Runtime status** | Tile indices and blocked tiles installed via FTM are client-visible collision/overworld data. Heightmap/sculpt geometry from Blender is **not** compiled into DAT/FTM by Studio. |
| **Product wording** | "Tile paint and blocked cells export through FTM. Terrain sculpt paths stay on the design document; terrain geometry compilation is unsupported. This is not a terrain sculptor. Full Blender-style modeling and terrain sculpting are out of scope." |

---

## Row 10. Stage materials (albedo names, equipment table, scene material refs)

| Field | Value |
|-------|-------|
| **Studio read/write** | **Read:** stage DAT embedded albedo basenames (`mesh_meta.extract_material_names`); equipment positional 64-byte material table; TEX resolve for preview. **Write:** scene-document `references.materials[]` is design-only. **No** rewrite of DAT material tables or stage multi-draw material binding compiler. TEX encode (row 4) can replace a texture member when the stem path is already known. |
| **Oracle** | Local client stage DATs + Tex archives; equipment DAT tail table (`FORMAT_NOTES.md`); Studio mesh-meta + map compiler. |
| **Evidence** | `python/mesh_meta.py` extracts names like `BF_Coat00_B`; `parse_equipment_material_table` verified on `Niki_CommonRacket41.dat` (count @ `0x64`, `file_size - 6 - count×64`, record size 64). `docs/client-re.md` multi-material section. `server/mapSceneCompiler.ts`: materials length > 0 → `runtimeUnsupported.push("stage material binding compilation")`, materials cloned to `design.materials` only. `FORMAT_NOTES.md`: "Material keys are positional; an appended record is not automatically used." Equipment creator keeps stock material stems under stock-topology clone. |
| **Executable fixture** | Stage: mesh-meta on `Mesh01.res` / `BF_Court01.dat` returns ≥2 materials including coat/net stems. Equipment: meta on Dragon-Slayer DAT returns `equipmentMaterialTable.count >= 1` and stems. Map compile: materials `[{slot:"court", texture:"Texture/Court01.tex"}]` appear under `design.materials` and force `"stage material binding compilation"` in `runtimeUnsupported` (`tests/mapSceneCompiler.test.ts`). |
| **Runtime status** | Preview binding in Mesh Studio uses recovered stems → `.tex`. Runtime stage multi-material draw still follows stock DAT + client. Design material slots do not rewrite stage binaries. |
| **Product wording** | "Stage material names are recovered for preview. Scene material slots are design data; stage material binding compilation is unsupported. Equipment materials stay on positional stock stems. Do not promise a freeform material author for court DATs." |

---

## Cross-cutting product language (use as written)

From `DESIGN.md` Product-truth language and `README.md` workflows:

| Use | Do not use |
|-----|------------|
| "Local client preflight" | "Gameplay passed" |
| "Ready for manual local-client verification" | "DX9 verified" without a human client check |
| "Browser preview is approximate" | "Playtesting is ready" before the human client check |
| "Open the local client, log in, equip/select, and visually inspect" | "Safe" without naming the validated boundary |
| "There is no general DAT writer." | "Full mesh export to DAT" |
| "There is no general EFT writer." | "Author new particle systems" |
| "Spawn markers are design documentation only." | "Spawns compile into the emulator" |

Install and SQL boundaries (unchanged by format rows): sibling JFTSE and stock client are read-only; install sources must be regular files under `exports/`; destinations are the configured local client and allowlisted `Res/**/*.res` only; every successful install returns matching SHA-256 receipts.

---

## Evidence index (paths and classes)

| Kind | Path / class |
|------|----------------|
| ResTool jar | `/home/thewind/Downloads/ft_restool.jar` SHA-256 `590ccfa6d88e0e7ae5af864af212543ec41342197603fd183f782315e3b0402f` |
| Crypter | `com.ft.restool.util.Crypter` (`decryptSetFileInMemory`, `encryptSetFileInMemory`, `decryptTexFile*`, `encryptTexFile`) |
| FTM | `com.ft.restool.parser.ftm.FTMParser`, `FTMFile`, `SceneObject`, `TileLayerDefinition`, `BlockedTile`, … |
| PRJ | `com.ft.restool.parser.prj.PRJReader`, `PRJFile` |
| DDS | `com.ft.restool.parser.dds.DDSReader` |
| Studio FTM/PRJ | `python/ftm_codec.py`, `python/author_cmds.py`, `python/content_pack.py` |
| Studio SET/TEX | `python/client_crypto.py`, `python/stage_set_author.py`, `python/tex_codec.py` |
| Studio DAT/EFT | `python/mesh_codec.py`, `python/mesh_meta.py`, `python/mesh_obj_import.py`, `python/eft_codec.py` |
| Item binding | `python/item_mesh.py`, `python/equipment_author.py`, `server/equipmentCreatorPackage.ts` |
| Map design compile | `server/mapSceneCompiler.ts`, `server/mapScenePackage.ts`, `web/mapScene*.ts` |
| JFTSE spawns | `JFTSE/chat-server/src/main/java/com/jftse/emulator/server/core/manager/GameManager.java` |
| JFTSE format notes | `JFTSE/tools/wind_dragon_slayer/FORMAT_NOTES.md` |
| RE notes | `docs/client-re.md` |
| Product copy | `DESIGN.md`, `README.md` |
| Stock fixtures | `FantaTennis-Local-Client/client/Res/MapSet/FantaCastle.res`, `.../Res/Stage/Info.res`, `.../Res/Stage/Mesh01.res`, `.../Res/Script/Item.res` |
| Automated fixtures | `tests/mapSceneCompiler.test.ts`, `tests/api.test.ts` (FTM/PRJ), `reference-projects/*-golden.json` |

---

## Verification notes for this document

Claims of write or runtime capability in rows 1, 3, 4, 5 (clone/position only), 7, and 9 (FTM tiles/blocked only) each name an oracle class or module and a runnable fixture. Rows 2 (PRJ write), 5 (general DAT), 6 (EFT write), 8 (spawn runtime), 9 (terrain sculpt), and 10 (stage material compile) use explicit unsupported wording so product UI cannot over-claim.
