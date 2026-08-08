# JFTSE Content Studio: full designer-studio implementation plan

## Outcome

Turn the current local React -> Bun API -> Python bridge workbench into an intuitive, truthful designer workflow without broadening the reverse-engineering claim or modifying any stock client file. The shipped path is:

1. Design equipment, map metadata/stage/FTM, or a combined content pack.
2. Build immutable artifacts under this repo's `exports/` tree.
3. Confirm and install only those artifacts into the one configured local client.
4. Strictly audit generated SQL, optionally confirm a live apply using only the server-configured database URL, and retain the returned apply result in the current workflow state.
5. Run a real preflight that verifies installed bytes, SQL audit, client binaries, and an actually existing launch script.
6. Hand the designer an explicit manual GUI checklist. The studio does not claim that it launched, logged in, equipped an item, or rendered with exact DX9 behavior.

## Non-negotiable boundary

Smallest correct change only:

- Modify only the files named in this plan, inside `jftse-content-studio`.
- Never write, patch, copy over, chmod, rename, or delete anything under `JFTSE_STOCK_CLIENT`.
- Never modify sibling JFTSE source, `FantaTennis.exe`, `jftse.dll`, or any stock `Res/**/*.res` archive.
- All generated client archives remain under `exports/`; installs copy them only into the exact canonical `JFTSE_LOCAL_CLIENT`.
- Do not add automatic GUI launch, login, inventory navigation, equip, or map selection. There is no existing safe automation for those operations.
- Do not claim exact DX9 skinning, full on-disk ANI/EFT parity, or pixel-true client output. Those formats are not sufficiently recovered; browser previews stay explicitly approximate.
- Do not add Redux, a router, a database service layer, a job queue, a manifest database, authentication, or signed capabilities. This is a single-user local tool and those patterns do not pay for themselves here.
- Do not refactor codecs, mesh recovery, animation math, or unrelated authoring endpoints.
- Do not remove or weaken existing tests to accommodate stricter behavior.

## Architecture surveyed

### Current ownership and data flow

- `web/app.tsx` owns the top-level workspace switch and the equipment/effect workflow. `ContentPackDesk`, `MapStudio`, and `MeshStudio` own their own local drafts; the current conditional render unmounts them on workspace changes.
- `web/EquipmentMeshPreview.tsx`, `web/StageMeshPreview.tsx`, and `web/MeshStudio.tsx` own Three.js/browser preview lifecycles.
- `web/MapStudio.tsx` owns map draft, stage validation, SQL export, stage `.set` export, and embeds `FtmDesk`.
- `web/FtmDesk.tsx` parses `.ftm`/`.prj`, edits placements/tile state, exports MapSet artifacts, and calls the generic install API.
- `web/ContentPackDesk.tsx` currently holds loosely related booleans/results. Actions are independently callable and only one of the map/equipment SQL files is retained.
- `server/index.ts` is the HTTP boundary and allocates export and temporary paths. Most payload JSON and mesh texture directories are never removed.
- `server/bridge.ts` spawns `uv ... studio_bridge.py`, has no timeout, and exposes raw process/JSON failures as unstable messages.
- `python/studio_bridge.py` and `python/author_cmds.py` dispatch to focused codecs/authoring modules.
- `python/local_install.py` owns install policy but currently uses string-prefix containment, accepts any `/tmp` substring, follows symlinks, and accepts caller-selected sources/destinations.
- `python/sql_apply.py` owns SQL splitting/audit/apply but currently uses a denylist regex, accepts any path and caller-provided DB URL, and can be bypassed by unrecognized statement shapes.
- `python/content_pack.py` builds equipment, map, stage, and FTM artifacts and an install plan; it does not aggregate all generated SQL.
- `python/studio_bridge.py::cmd_map_studio_export_pack` emits SQL without enforcing its own stage validation.
- `python/author_cmds.py::cmd_content_pack_playtest_full` checks existence only, treats launch readiness as non-blocking, and presents preflight as playtest readiness.
- `tests/api.test.ts` is the real API/asset integration suite; `tests/skinnedBody.test.ts` covers isolated browser math. The API harness currently polls with sleeps and leaves generated repo artifacts behind.

### Blast radius

The changes cross three contracts:

1. **Trust boundary:** server-selected export/temp roots -> Python canonical containment -> configured local client/DB.
2. **Workflow truth:** build/install/audit/apply/preflight receipts -> enabled UI actions and labels.
3. **Workspace lifecycle:** persistent React state -> accessible tab panels -> preview activation/cleanup.

Codec data formats do not need to change. Existing build/install/SQL/playtest APIs remain, but request path freedom is removed and response data becomes more explicit.

## Design options considered

### Option A - localized hardening + explicit local workflow state (recommended)

- Canonicalize and contain filesystem paths in Python, restrict requests at the Bun boundary, and keep generated-path contracts in manifests.
- Add one small pure reducer for content-pack phases and one pure helper for tab keyboard movement.
- Keep each workspace mounted after its first visit, hide inactive tab panels, and pass `active` only to preview loops so drafts survive without running hidden renderers.
- Add a reusable confirmation dialog for the three live-write surfaces.

Trade-offs:

- **Coupling:** Existing modules remain coupled through JSON contracts, but ownership stays where it already is.
- **Testability:** Path/SQL rules and reducers are pure and directly testable; API tests cover integration.
- **Migration cost:** Moderate and incremental; no stored pack migration is required.
- **Failure modes:** A server restart loses in-memory UI phase state, so the user must rebuild/re-audit. That is truthful and safe. Hidden visited panes retain browser memory, but preview loops are explicitly paused/disposed.

### Option B - server-issued manifest IDs + global persisted studio store

- Build endpoints issue opaque artifact IDs; all install/SQL/preflight operations accept IDs only.
- A global store/router persists every workspace and operation receipt across reloads.

Trade-offs:

- **Coupling:** Strong coupling to a manifest registry and app-wide schema.
- **Testability:** Strong centralized invariants, but requires registry lifecycle, migration, reload, and stale-ID tests.
- **Migration cost:** High; every writer and consumer endpoint changes, old saved packs need migration, and restart semantics need durable storage.
- **Failure modes:** Registry loss or stale manifests can strand valid exports; durable storage introduces cleanup and synchronization concerns.

### Decision

Use Option A. Canonical export-root containment and strict statement allowlisting close the actual local attack surface without inventing a service. A small reducer prevents impossible pack sequencing. Preserving visited panes solves draft loss with less migration than hoisting every field or introducing a global store. The accepted risk is that operation receipts are session-local; after reload the safe behavior is to re-run audit/preflight rather than infer success.

## Fixed contracts to implement

These decisions are final; implementers should not redesign them.

### Install policy

`python/local_install.py` must enforce all of the following:

- The target's canonical path equals canonical `JFTSE_LOCAL_CLIENT`; remove `JFTSE_INSTALL_ALLOW_PREFIX` target semantics and every implicit `/tmp` exception.
- The canonical target must not equal the canonical stock client, including through symlink aliases.
- Every source is a regular, non-symlink file canonically contained by `JFTSE_STUDIO_EXPORTS` (set by `server/config.ts::bridgeEnv` to `config.exportsDir`).
- Every destination is a relative POSIX path beginning with `Res/`, ending in `.res`, with no empty, `.`, or `..` segment. This intentionally excludes executable/DLL writes.
- Reject an existing symlink in any destination component and verify the canonical parent remains under the local-client root immediately before replacement.
- Copy to a same-directory temporary file, hash source/temp with SHA-256, then `os.replace`; return a receipt per file with source, destination, byte count, source SHA-256, installed SHA-256, and `matches: true`.
- Stable errors: `REFUSE_STOCK_CLIENT`, `TARGET_NOT_CONFIGURED`, `TARGET_NOT_ALLOWLISTED`, `SOURCE_OUTSIDE_EXPORTS`, `SOURCE_SYMLINK`, `INVALID_DEST_PATH`, `DEST_SYMLINK_ESCAPE`, `SOURCE_MISSING`, `INSTALL_VERIFY_FAILED`.

### SQL policy

`python/sql_apply.py` must fail closed:

- Canonical `.sql` file must be a non-symlink regular file under `JFTSE_STUDIO_EXPORTS`.
- The request body may contain only `path` and `dryRun`; reject `databaseUrl` as `DATABASE_URL_OVERRIDE_FORBIDDEN` and `allowDeletes` as `SQL_DELETE_OVERRIDE_FORBIDDEN` at `server/index.ts` before bridge invocation.
- Live apply may read only `JFTSE_DATABASE_URL`, not caller input and not generic `DATABASE_URL`.
- Replace denylist audit with a quote/comment-aware scanner. Accept only complete `INSERT INTO <allowed_table> ... [ON DUPLICATE KEY UPDATE ...]` statements generated by this repo. Allowed tables, case-insensitive: `S_Product`, `product`, `S_Maps`, `M_Scenarios`, `Map_2_Scenarios`, `Guardian_2_Maps`.
- Reject block comments, MySQL executable comments, unterminated strings/comments, backslash/comment obfuscation, multiple verbs, and every non-INSERT statement as `SQL_STATEMENT_NOT_ALLOWED` or `SQL_PARSE_FAILED`. Do not support DELETE in this scope; no current UI flow requires it.
- The audit response reports statement count, insert count, normalized table names, rejected statement summaries, and `safe`.
- Live apply keeps the existing mysql/mariadb CLI model and timeout, but never echoes the URL/password.

### Bridge contract

`server/bridge.ts` must provide:

- `BridgeError` with stable codes `BRIDGE_TIMEOUT`, `BRIDGE_EXIT_FAILED`, `BRIDGE_INVALID_JSON`, and a bounded sanitized `detail`.
- A process helper with a default 180-second timeout; known long build endpoints may explicitly request 300 seconds. Timeout kills the child and awaits `proc.exited` before rejecting.
- `runBridgeWithPayload(prefix, payload, argsForPath, options?)` that writes one JSON payload and removes it in `finally`.
- `safeBridge` in `server/index.ts` returns `{ok:false,error,detail?}` and maps known request/bridge failures consistently without exposing stack traces, credentials, or unbounded stderr.
- Mesh texture responses read bytes before deleting their one-shot output directory. Atlas previews remain an intentional key-addressed cache and are not part of one-shot cleanup.

### Content-pack workflow and preflight

`python/content_pack.py::build_content_pack` must write one aggregate `content-pack.sql` when any part creates SQL, in deterministic equipment-then-map order, and return `sqlPath` plus `sqlParts` in the manifest. Existing part-specific SQL paths remain for diagnostics.

`web/contentPackWorkflow.ts` is a small reducer, not an app-wide store. Its valid sequence is:

`draft -> built -> installed -> sqlAudited -> sqlApplied -> preflightPassed`

- A pack with no SQL skips `sqlAudited/sqlApplied` when deriving the next action.
- Any draft edit invalidates build and every downstream receipt.
- A new build invalidates install/SQL/preflight.
- Install requires a build and a confirmation.
- Dry-run requires the matching install receipt.
- Live apply requires a successful matching dry-run and a confirmation.
- Preflight requires install plus successful audit; when SQL exists it also requires the current-session successful live-apply result. The UI may clearly offer “Re-run preflight”, but never silently skips a missing phase.
- Errors preserve the last valid prior receipt and expose an explicit retry for the failed action.

Preflight is not play automation. Rename UI language to “Local client preflight” and response fields to `preflightPassed`/`manualHandoff`; retain `ready` only as a temporary API compatibility alias with the same strict value.

The preflight checks are:

- exact configured local target and non-stock identity;
- `FantaTennis.exe` exists and is non-empty;
- `jftse.dll` exists and is non-empty;
- every install-plan destination exists and SHA-256 equals its source artifact;
- aggregate SQL exists under exports and passes strict audit;
- launch script is discovered from `JFTSE_LAUNCH_SCRIPT` if configured, then `<local-client-parent>/START-FANTA-TENNIS.sh`; only an existing regular executable file passes;
- the launch command is built from the actual discovered path, never a hard-coded fallback.

`manualHandoff` must say that the user, not the studio, must run the shown command, log in, open Equipment/map selection, equip/select the authored content, and visually verify it in the DX9 client. Do not execute that command.

### Map/FTM contract

- Extract stage validation into a reusable Python function and call it from `cmd_map_studio_validate`, `cmd_map_studio_export_pack`, `cmd_export_map_sql`, and `author_cmds.cmd_map_create` before writing SQL. Missing/invalid binds return `STAGE_VALIDATION_REQUIRED` with structured failing checks. No export file is created on failure.
- In `MapStudio`, changing stage script invalidates the matching validation receipt. Export/create buttons require a passing validation for that exact script; server enforcement remains authoritative.
- PRJ parsing renders its `ftmPaths` as a real picker. Selecting a child normalizes separators, resolves a matching archive member by basename, sets the member field, and loads it; do not silently auto-pick the first child.
- Editing archive/member invalidates loaded FTM and export/install state. FTM writes require a loaded source identity matching current fields.
- API failures retain structured `detail`; map catalog, stage validation, FTM parse, and FTM author surfaces each show Retry. Empty map search, empty catalog, empty PRJ, and empty placement list have distinct messages.

### Navigation and layout contract

Top-level workspaces are ordered: `Equipment`, `Content Pack`, `Map Studio`, `Mesh Studio`. Rename the existing `items` workspace identifier to `equipment`; do not create a duplicate equipment implementation.

- Render a workspace after first visit and keep it mounted thereafter; inactive wrappers use `hidden`, `role="tabpanel"`, `aria-labelledby`, and stable IDs.
- Pass `active` to Three.js previews. Inactive previews cancel animation, listeners, controls, renderer, textures/materials/geometries, and pending async setup; local React draft state remains mounted.
- Tab containers use `role="tablist"`; buttons use `role="tab"`, `id`, `aria-controls`, `aria-selected`, and roving `tabIndex`.
- ArrowLeft/ArrowRight/Home/End move focus and select the corresponding tab. Apply the same semantics to the Equipment workflow step tabs.
- At <=760 px: top-level tabs horizontally scroll without page overflow, brand/status hierarchy remains first, `.field-grid` is one column, panels have no fixed 520/640 px minimum, action buttons remain usable, canvas/viewport width is bounded, and footer/status stacks. At 1440 px, preserve the useful three-column operational layout.

## Dependency-ordered implementation steps

Every numbered behavior step starts by adding or recording a failing proof before production code changes. Do not combine RED and GREEN into an unobservable edit.

### 0. Baseline, immutable-client receipt, and deterministic test harness

**Owner:** integration lead. **Dependencies:** none. **Files:** `tests/api.test.ts` only for the harness; no production behavior.

1. Capture immutable inputs before any source edit:

   ```bash
   export JFTSE_ROOT="${JFTSE_ROOT:-$(realpath ../JFTSE)}"
   export JFTSE_STOCK_CLIENT="${JFTSE_STOCK_CLIENT:-$JFTSE_ROOT/.jftse-client-linux/client}"
   find "$JFTSE_STOCK_CLIENT" -type f -print0 | sort -z | xargs -0 sha256sum > /tmp/jftse-stock.before.sha256
   git -C "$JFTSE_ROOT" status --short > /tmp/jftse-sibling.before.status
   find .tmp -maxdepth 1 -mindepth 1 -printf '%f\n' | sort > /tmp/jftse-tmp.before.txt
   find exports -maxdepth 1 -mindepth 1 -printf '%f\n' | sort > /tmp/jftse-exports.before.txt
   bun test
   bun run typecheck
   ```

   Pass: tests/typecheck exit 0 and receipt files exist. Do not “clean” pre-existing `.tmp`/`exports` entries.

2. Replace the API suite's `Bun.sleep` startup polling with a promise subscribed to the spawned server's exact `listening on` stdout before spawn output can be missed, plus a bounded timeout that kills the process on failure. In `afterAll`, kill and await `serverProc.exited`; snapshot initial top-level `exports/`, `content-packs/`, and `.tmp/`, then remove only entries created by this test process.
3. RED: temporarily make the startup marker impossible and run `bun test tests/api.test.ts -t "health bridge is online"`; pass for RED is one bounded startup failure with no hang. Revert only the marker, then GREEN:

   ```bash
   bun test tests/api.test.ts -t "health bridge is online"
   ```

   Pass: one run exits 0 with no sleep/poll loop. This harness is required before adding tests below.

### 1. Lock local installs to generated artifacts and the configured client

**Owner:** backend-security agent. **Dependencies:** 0. **Files:** `python/local_install.py`, `python/author_cmds.py`, `server/config.ts`, `tests/api.test.ts`.

1. RED: add API tests named with prefix `install containment` for:
   - target `/var/tmp/looks-like-tmp/client` rejected even though its string contains `/tmp/`;
   - a target sibling sharing a configured-prefix string rejected;
   - symlink alias to stock rejected;
   - `/etc/hosts` and an export-root symlink to `/etc/hosts` rejected as sources;
   - `../FantaTennis.exe`, absolute paths, `FantaTennis.exe`, and `Res/../jftse.dll` rejected as destinations;
   - `local/Res/Script` symlinked outside the local client rejected;
   - a generated equipment install succeeds and each receipt hash matches the resulting file.
2. Run once and retain the failing output:

   ```bash
   bun test tests/api.test.ts -t "install containment"
   ```

   Pass for RED: at least one adversarial case demonstrates current acceptance or missing receipt fields; no stock file changes.
3. GREEN: implement the fixed Install policy above. Add `JFTSE_STUDIO_EXPORTS` in `bridgeEnv`; remove `JFTSE_INSTALL_ALLOW_PREFIX`. Keep `cmd_client_install` as the sole Python adapter and preserve stable `InstallError.code` responses.
4. Run:

   ```bash
   bun test tests/api.test.ts -t "install containment|install refuses stock|install accepts disposable|equipment pack builds|ftm author add"
   ```

   Pass: all selected tests pass; rejected requests are HTTP 400 with the exact stable code; successful receipts have equal 64-hex hashes; `cmp /tmp/jftse-stock.before.sha256 <(find "$JFTSE_STOCK_CLIENT" -type f -print0 | sort -z | xargs -0 sha256sum)` exits 0.

### 2. Replace SQL denylisting with strict generated-SQL allowlisting

**Owner:** backend-security agent. **Dependencies:** 1. **Files:** `python/sql_apply.py`, `python/author_cmds.py`, `server/index.ts`, `tests/api.test.ts`.

1. RED: extend `sql apply` tests with generated equipment/map SQL success and rejection of:
   - SQL outside `exports/` and an in-root symlink to an outside file;
   - caller `databaseUrl` and `allowDeletes`;
   - `UPDATE`, `DELETE`, `DROP`, `DR/**/OP`, `/*!50000 DROP TABLE S_Maps */`, `SELECT`, stacked statements, block comments, unterminated quotes, and an unapproved table;
   - a semicolon and doubled quote inside a product name, which must remain one valid INSERT statement.
2. Run:

   ```bash
   bun test tests/api.test.ts -t "sql apply"
   ```

   Pass for RED: current regex/path behavior fails the new expectations.
3. GREEN: implement the fixed SQL policy in `split_sql_statements`, `audit_statements`, and `apply_sql_file`; remove the `database_url` and `allow_deletes` parameters from the bridge call path. Reject forbidden request keys in `server/index.ts` before writing a payload.
4. For deterministic live-apply coverage, have the test harness prepend a temporary fake `mysql` executable to the server's `PATH` and set a non-secret test `JFTSE_DATABASE_URL`; the fake captures stdin and exits 0. Subscribe to the request result rather than polling a capture file. Assert live apply used generated SQL and never accepted the caller URL.
5. Run:

   ```bash
   bun test tests/api.test.ts -t "sql apply"
   ```

   Pass: all allowed generated statements audit safe; every adversarial form returns the specified 400 code; fake live apply returns `applied:true`; response text contains no database password.

### 3. Give the bridge bounded execution, stable errors, and one-shot temp cleanup

**Owner:** bridge agent. **Dependencies:** 0; merge after step 2 because both touch `server/index.ts`. **Files:** `server/bridge.ts`, `server/index.ts`, new `tests/bridge.test.ts`, `tests/api.test.ts`.

1. RED in `tests/bridge.test.ts`: invoke an exported low-level process helper with a Bun child that never exits and a short explicit timeout (time is the behavior under test); assert `BridgeError.code === "BRIDGE_TIMEOUT"` and that the child exit promise resolves. Add invalid-JSON and nonzero-exit cases.
2. RED in `tests/api.test.ts`: snapshot matching `.tmp/{payload,maps,map-pack,mesh-transform,client-install,stage-set-write,ftm-author,content-pack,sql-apply}-*` entries, complete representative requests, and assert the set is unchanged immediately after each response. Request one mesh texture and assert no new `mesh-tex-*` directory remains.
3. Run:

   ```bash
   bun test tests/bridge.test.ts
   bun test tests/api.test.ts -t "temporary bridge files|mesh texture cleanup|stable bridge error"
   ```

   Pass for RED: timeout support/cleanup assertions fail, without an unbounded test hang.
4. GREEN: add `BridgeError`, the timed process helper, `runBridgeWithPayload`, and stable error serialization. Replace each hand-written payload allocation in `server/index.ts` and `buildEffect` with the helper. Read texture bytes and remove its output directory in `finally` before constructing the response. Preserve atlas cache behavior.
5. Run the same commands. Pass: exact stable codes/details are returned and before/after one-shot temp sets are equal.

### 4. Enforce stage validation at every map SQL writer

**Owner:** map-backend agent. **Dependencies:** 2, 3. **Files:** new `python/stage_validation.py`, `python/studio_bridge.py`, `python/author_cmds.py`, `tests/api.test.ts`.

1. RED: add tests that post an invalid/missing stage bind to `/api/maps/export-sql`, `/api/map-studio/export-pack`, and `/api/map-studio/create`; capture the proposed output directory listing before each call and assert HTTP 400 `STAGE_VALIDATION_REQUIRED`, structured failed checks, and no new SQL file. Keep passing cases for `1_Emerald_Beach.set`.
2. Run:

   ```bash
   bun test tests/api.test.ts -t "map.*stage validation"
   ```

   Pass for RED: at least one writer currently emits SQL.
3. GREEN: move `_stage_scripts`, `_decode_stage_script`, `_resolve_client_asset`, and the reusable validation result into `python/stage_validation.py`. Call it before opening/writing output in all four Python command paths named in the contract. Keep catalog behavior unchanged.
4. Run:

   ```bash
   bun test tests/api.test.ts -t "map.*stage validation|map studio validate|map studio export pack|map studio create|map sql bulk export"
   ```

   Pass: invalid requests create nothing; known-stage exports include `validation.valid:true` and existing SQL assertions remain green.

### 5. Build one complete content-pack SQL artifact

**Owner:** pack-backend agent. **Dependencies:** 2. **Files:** `python/content_pack.py`, `tests/api.test.ts`.

1. RED: update the combined equipment+map pack test to require `pack.sqlPath`, `pack.sqlParts` in equipment-then-map order, both `S_Product` and `S_Maps` in the aggregate file, and a successful strict dry-run of `pack.sqlPath`.
2. Run:

   ```bash
   bun test tests/api.test.ts -t "content pack aggregates SQL"
   ```

   Pass for RED: `sqlPath` is absent or contains only one part.
3. GREEN: collect generated part SQL strings during `build_content_pack`, write `<outDir>/sql/content-pack.sql` once, expose path/part metadata in both response and `manifest.json`, and leave part files intact.
4. Run:

   ```bash
   bun test tests/api.test.ts -t "content pack aggregates SQL|content pack builds equipment"
   ```

   Pass: aggregate order/content and strict audit are correct.

### 6. Replace existence-only “playtest” with exact local-client preflight

**Owner:** preflight-backend agent. **Dependencies:** 1, 2, 5. **Files:** new `python/playtest_preflight.py`, `python/content_pack.py`, `python/author_cmds.py`, `python/studio_bridge.py`, `server/index.ts`, `server/config.ts`, `tests/api.test.ts`.

1. RED: create a disposable local-client fixture containing non-empty placeholder `FantaTennis.exe`, `jftse.dll`, and an executable `START-FANTA-TENNIS.sh` at its actual parent. Add tests for:
   - missing exe, missing DLL, missing/non-executable launch script;
   - installed destination byte mismatch against source;
   - missing/unsafe aggregate SQL;
   - passing files/SQL/binaries/launch returning `preflightPassed:true` and compatibility `ready:true`;
   - `launchCommand` uses only the discovered script and becomes `null` when no script exists;
   - response includes `manualHandoff` and never claims launch/equip occurred.
2. Run:

   ```bash
   bun test tests/api.test.ts -t "content pack preflight|playtest status"
   ```

   Pass for RED: current existence-only/launch-optional logic fails new assertions.
3. GREEN: implement shared hashing, launch discovery, and checklist composition in `playtest_preflight.py`. Make both `/api/playtest/status` and `/api/content-pack/playtest-full` use it. Keep `/api/content-pack/playtest` as a compatibility route returning the same stricter file receipt shape, not a claim of gameplay.
4. Remove hard-coded `launchHint` construction from `buildSetup`, `/api/health`, and `/api/workflow`; return the discovered command/readiness from Python.
5. Run the same command. Pass: readiness is true only when every required check passes, labels distinguish SQL audit from SQL apply, and manual steps are explicit.

### 7. Add pure content-pack phase rules before changing the desk

**Owner:** pack-UI agent. **Dependencies:** 5, 6. **Files:** new `web/contentPackWorkflow.ts`, new `tests/contentPackWorkflow.test.ts`.

1. RED: write reducer/selector tests for all valid transitions, ignored/rejected out-of-order actions, no-SQL skip, draft/build invalidation, retry preserving prior receipts, and matching build revision. Import the not-yet-created module.
2. Run:

   ```bash
   bun test tests/contentPackWorkflow.test.ts
   ```

   Pass for RED: module import fails.
3. GREEN: implement only the discriminated state/events and selectors needed by `ContentPackDesk`; no React and no persistence.
4. Run the same command. Pass: all transitions and disabled-action reasons are deterministic.

### 8. Add one accessible confirmation primitive

**Owner:** UI-primitives agent. **Dependencies:** none. **Files:** new `web/ConfirmDialog.tsx`, `web/styles.css`, new `tests/confirmDialogContract.test.ts` only if logic is extracted.

1. RED browser proof: on the current Content Pack and FTM surfaces, activating install or SQL apply immediately performs/calls the write without a dialog. Record this as the failing observable; cancel any browser request before it reaches the API where possible.
2. GREEN: implement `ConfirmDialog` with title, exact target/source/operation summary, Confirm/Cancel callbacks, initial focus on Cancel, focus restoration, Escape cancel, backdrop cancel, `role="dialog"`, `aria-modal`, and labelled/described IDs. Do not make it a generic modal framework.
3. Use it later for Equipment install (replace the inline dialog in `app.tsx`), Content Pack local install, Content Pack live SQL apply, and FTM local install. Export/build/stage-write actions are repo artifact writes, not live client/DB writes, and do not need confirmation.
4. Typecheck now:

   ```bash
   bun run typecheck
   ```

   Pass: exit 0.

### 9. Make Content Pack a truthful, confirmable state machine

**Owner:** pack-UI agent. **Dependencies:** 7, 8. **Files:** `web/ContentPackDesk.tsx`, `web/styles.css` (pack-specific classes only).

1. RED browser scenarios before editing:
   - click preflight before build;
   - build, edit a field, then observe install still enabled;
   - install then observe live SQL apply enabled before dry-run;
   - observe only one SQL path for a combined pack;
   - click install/SQL apply and observe no confirmation.
   Each is a current failure; do not perform a live SQL apply.
2. GREEN: wire every field/action/result through `contentPackWorkflow`. Consume `manifest.sqlPath`; show numbered step cards with explicit complete/current/blocked labels and a reason beside disabled actions. Confirm install and live apply through `ConfirmDialog`. Preserve the last successful receipt on retryable errors. Show distinct empty, busy, error+Retry, and successful receipt panels.
3. Preflight action calls `/api/content-pack/playtest-full` only at the valid phase. Render `preflightPassed`, every check, actual launch command with Copy, and `manualHandoff`. Use “Run local-client preflight”, never “Run playtest” or “Playtest ready”.
4. GREEN validation:

   ```bash
   bun test tests/contentPackWorkflow.test.ts
   bun run typecheck
   ```

   Pass: commands exit 0. Browser binary observables: out-of-order buttons are disabled with reasons, field edit returns to Build, each live write opens a dialog, Cancel makes no network request, and combined SQL receipt names both parts.

### 10. Make Map validation current and recoverable

**Owner:** map-UI agent. **Dependencies:** 4. **Files:** `web/MapStudio.tsx`.

1. RED browser proof: validate a good script, change script (or force a missing value), and observe export is still callable; search for a nonexistent map and observe no explicit empty state; induce catalog/validation failure and observe no Retry action.
2. GREEN:
   - store validation with its `stageScript` identity and derive `hasCurrentValidStage`;
   - clear it whenever the script changes;
   - disable export/create until exact current validation passes and show why;
   - still display server validation failures, since server is authoritative;
   - add explicit Retry for catalog load and validation, role=alert details, empty catalog, and no-search-result copy;
   - preserve draft fields/status when retries occur.
3. Validate:

   ```bash
   bun test tests/api.test.ts -t "map.*stage validation"
   bun run typecheck
   ```

   Pass: commands exit 0; browser cannot export after a stale/failed validation and can recover without reload.

### 11. Complete PRJ -> FTM continuation and confirm FTM installs

**Owner:** FTM-UI agent. **Dependencies:** 8. **Files:** new `web/ftmSelection.ts`, new `tests/ftmSelection.test.ts`, `web/FtmDesk.tsx`.

1. RED unit tests: given PRJ paths with Windows separators, nested directories, duplicate basenames, and no children, require deterministic picker labels and matching archive-member candidates. Import the missing helper.
2. RED browser proof: parse `FantaCastle.prj`; current UI reports paths but offers no picker and silently changes the member.
3. Run:

   ```bash
   bun test tests/ftmSelection.test.ts
   ```

   Pass for RED: missing module/helper.
4. GREEN: implement the pure normalizer, retain PRJ payload in state, render each child in a labelled select/list, and load only after explicit selection. If a child cannot be matched, retain the path and show a recoverable error rather than guessing.
5. Track `loadedSource = {archive,member}`. Archive/member edits clear loaded FTM, authored export, and install readiness. Add Retry for parse/author errors, distinct empty PRJ/placement states, and `role="alert"` details. Gate every author call on matching source identity.
6. Replace immediate `installAuthored` with `ConfirmDialog`; dialog must name the MapSet `.res` source and destination. Cancel makes no `/api/client/install` request.
7. Validate:

   ```bash
   bun test tests/ftmSelection.test.ts
   bun test tests/api.test.ts -t "PRJ parse|FTM parse|ftm author"
   bun run typecheck
   ```

   Pass: all commands exit 0; PRJ picker opens either child, malformed input shows detail+Retry, and FTM install requires confirmation.

### 12. Promote Equipment and preserve every visited workspace draft

**Owner:** shell-UI agent. **Dependencies:** 8, 9, 10, 11. **Files:** new `web/workspaceNavigation.ts`, new `tests/workspaceNavigation.test.ts`, `web/app.tsx`, `web/MapStudio.tsx`, `web/MeshStudio.tsx`, `web/StageMeshPreview.tsx`, `web/EquipmentMeshPreview.tsx`.

1. RED pure tests: import missing workspace constants/tab-key helper; require order `equipment,packs,maps,meshes` and ArrowLeft/Right/Home/End wrap/selection behavior.
2. RED browser proof:
   - edit a Content Pack field, switch to Map and back, observe reset;
   - edit Map/FTM data, switch away/back, observe reset;
   - observe no top-level Equipment label;
   - inspect workspace/step tabs and observe missing tablist/tab/tabpanel linkage.
3. Run:

   ```bash
   bun test tests/workspaceNavigation.test.ts
   ```

   Pass for RED: missing module/helper.
4. GREEN shell:
   - rename `WorkspaceMode "items"` to `"equipment"` and label it Equipment;
   - maintain a visited set; mount each workspace on first visit and keep it under a native `hidden` tabpanel thereafter;
   - preserve existing `onOpenMesh` behavior and mark Mesh visited before selecting it;
   - implement complete tab ARIA/roving focus and keyboard selection for workspace and Equipment workflow tabs;
   - replace the existing inline Equipment install modal with `ConfirmDialog` without changing its install behavior.
5. GREEN preview lifecycle: add `active` props down to the preview-owning components. Their effects must eagerly register cleanup before awaits, cancel pending setup, and dispose/cancel render resources when inactive; reactivation recreates only rendering resources while component draft state remains.
6. Validate:

   ```bash
   bun test tests/workspaceNavigation.test.ts tests/skinnedBody.test.ts
   bun run typecheck
   ```

   Pass: commands exit 0. Browser observables: all named drafts survive two round trips; hidden WebGL canvases stop drawing (no increasing animation callbacks in Performance panel); Arrow/Home/End focus and select the correct linked panel.

### 13. Normalize responsive hierarchy and remaining recoverable states

**Owner:** shell-UI agent. **Dependencies:** 9-12. **Files:** `web/styles.css`, `web/app.tsx`, `web/EquipmentMeshPreview.tsx` only where loading/error controls are rendered.

1. RED visual proof at 1440x900 and 390x844:
   - capture current screenshots to `/tmp/jftse-studio-before-{desktop,narrow}.png`;
   - in the narrow viewport evaluate `document.documentElement.scrollWidth > window.innerWidth` and record any clipped tabs/actions, fixed-height empty panels, or nested scroll traps;
   - simulate `/api/items` failure and empty search and record missing/inconsistent Retry/empty handling.
2. GREEN CSS using the fixed Navigation/layout contract. Keep desktop three-column density; do not convert the app into marketing cards or hide advanced actions. Add no new color system.
3. GREEN Equipment data states: item/atlas/preset load errors show scoped Retry; empty query is distinct from loading/error; retry does not erase current draft/selection.
4. Run:

   ```bash
   bun run typecheck
   bun build ./web/index.html --outdir /tmp/jftse-content-studio-build
   ```

   Pass: both exit 0. Browser binary observables at 390x844: `scrollWidth === innerWidth`, all four workspace tabs are keyboard/scroll reachable, field grids are one column, no panel has a forced 520/640 px blank minimum, and primary action/status appear in that order. At 1440x900, three useful columns remain with no overlap.

### 14. Update durable product truth

**Owner:** docs agent. **Dependencies:** 6, 9-13. **Files:** `README.md`, `DESIGN.md`.

1. RED documentation search:

   ```bash
   rg -n "Items|Playtest ready|/tmp|JFTSE_INSTALL_ALLOW_PREFIX|SQL apply|launchHint|45 tests|pixel-true|full DX9" README.md DESIGN.md
   ```

   Pass for RED: stale Items/safety/playtest claims are found.
2. GREEN docs:
   - top-level Equipment label and workflow;
   - exact install allowlist and generated-source rule;
   - strict generated-SQL subset and env-only live database URL;
   - preflight versus manual GUI handoff;
   - actual launch discovery (no stale path promise);
   - state continuity/accessibility behavior;
   - current test command without pinning a stale test count;
   - explicit unchanged limits for DX9 skinning, full ANI/EFT, and automatic GUI operations.
3. Re-run the search. Pass: no stale safety/readiness/test-count claim remains; remaining `Items` references refer only to database/item content, not top navigation.

### 15. Full verification and browser QA

**Owner:** integration lead; browser QA must be performed by an agent that did not author the shell CSS. **Dependencies:** all prior steps.

1. Diagnostics before execution:

   ```bash
   bun run typecheck
   ```

   Pass: exit 0 with no diagnostics.

2. One full reliable suite run, then build:

   ```bash
   bun test
   rm -rf /tmp/jftse-content-studio-build
   bun build ./web/index.html --outdir /tmp/jftse-content-studio-build
   test -f /tmp/jftse-content-studio-build/index.html
   ```

   Pass: all commands exit 0 in a single run; no retries.

3. Start the real surface and wait on its stdout marker, not a sleep:

   ```bash
   PORT=4310 bun run dev 2>&1 | tee /tmp/jftse-studio-qa.log
   ```

   Open `http://127.0.0.1:4310` in Chromium. Use 1440x900 and 390x844 viewports. For async interactions, begin observing the exact network response or DOM status before triggering the action, then await it with a bounded browser timeout.

4. Desktop browser scenarios, each binary pass/fail:
   - Top tabs read Equipment / Content Pack / Map Studio / Mesh Studio; ArrowRight/Left/Home/End moves focus and selection; each selected tab's `aria-controls` points to the visible tabpanel.
   - Change an Equipment effect value, a Content Pack name, a Map name/stage validation, and an FTM archive/member; visit all workspaces and return. Every value/result remains.
   - Content Pack: build a combined equipment+map+FTM pack; install is the only next live action; Cancel causes zero install request; Confirm returns hash receipts; SQL apply stays blocked before dry-run; Cancel causes zero live apply; preflight stays blocked until the valid phase.
   - Map: invalid stage cannot export and creates no path; valid Emerald Beach validation enables export; changing the script invalidates it; Retry recovers a forced failure.
   - FTM: parse `FantaCastle.prj`, explicitly choose each child, load it, edit/export, then verify local install opens confirmation and Cancel sends no request.
   - Preflight: check exact local client, exe, DLL, installed hashes, aggregate SQL audit, and actual launch script. Copy command works. The panel says manual launch/login/equip/visual verification and never claims the game ran.
   - Confirm dialogs focus Cancel initially, Escape closes, focus returns to invoker, and target details are visible.
   - Simulated API error and zero-result searches show distinct Error+Retry and Empty states without losing drafts.

5. Narrow browser scenarios, each binary pass/fail:
   - `document.documentElement.scrollWidth === window.innerWidth`.
   - All tabs/actions are reachable by keyboard and horizontal tab scrolling; no body-level horizontal clipping.
   - Fields are one column; status/error precedes secondary detail; dialogs fit; FTM and Three canvases remain within viewport.
   - No panel has an unnecessary fixed minimum-height blank region or nested scroll trap.

6. Capture QA screenshots only under `/tmp`: `/tmp/jftse-studio-final-equipment-desktop.png`, `/tmp/jftse-studio-final-pack-desktop.png`, `/tmp/jftse-studio-final-map-desktop.png`, `/tmp/jftse-studio-final-ftm-prj.png`, and `/tmp/jftse-studio-final-narrow.png`.

7. Cleanup and immutability receipts:

   ```bash
   find "$JFTSE_STOCK_CLIENT" -type f -print0 | sort -z | xargs -0 sha256sum > /tmp/jftse-stock.after.sha256
   cmp /tmp/jftse-stock.before.sha256 /tmp/jftse-stock.after.sha256
   git -C "$JFTSE_ROOT" status --short > /tmp/jftse-sibling.after.status
   cmp /tmp/jftse-sibling.before.status /tmp/jftse-sibling.after.status
   test -z "$(find .tmp -maxdepth 1 \( -type f -o -type d \) \( -name 'payload-*' -o -name 'maps-*' -o -name 'map-pack-*' -o -name 'mesh-transform-*' -o -name 'mesh-tex-*' -o -name 'client-install-*' -o -name 'stage-set-write-*' -o -name 'ftm-author-*' -o -name 'content-pack-*' -o -name 'sql-apply-*' \) -newer /tmp/jftse-stock.before.sha256 -print -quit)"
   git status --short
   ```

   Pass: stock hash trees are byte-identical, sibling status is unchanged, no one-shot temp created during the implementation remains, only intended repo source/docs/tests plus pre-existing untracked evidence are reported, and test-created export/content-pack entries were removed by the harness. Do not delete pre-existing artifacts to force this check.

## Delegation topology

Avoid parallel edits to hotspots even when conceptual work is independent.

### Wave 0 - serial foundation

- Integration lead: step 0 only (`tests/api.test.ts` harness and immutable receipts).

### Wave 1 - parallel isolated backend cores

- Backend-security agent: steps 1 and 2 (`python/local_install.py`, `python/sql_apply.py`, relevant adapters/tests).
- Bridge agent: RED/unit work for step 3 in `server/bridge.ts` and `tests/bridge.test.ts`; do not edit `server/index.ts` until backend-security changes merge.

Merge order: install -> SQL -> bridge `server/index.ts` integration. Integration lead resolves `tests/api.test.ts`; agents must not independently rewrite the same test regions.

### Wave 2 - parallel backend domains after trust contracts are green

- Map-backend agent: step 4.
- Pack-backend agent: step 5.

Then preflight-backend agent performs step 6 after both merge. This ordering ensures preflight consumes final canonical install and strict SQL contracts.

### Wave 3 - UI primitives and pure state

In parallel:

- Pack-UI agent: step 7 only.
- UI-primitives agent: step 8 only.
- FTM-UI agent: RED/helper portion of step 11 only.
- Shell-UI agent: RED/helper portion of step 12 only.

Merge `ConfirmDialog` first.

### Wave 4 - parallel desks with exclusive file ownership

- Pack-UI agent: step 9, owns `ContentPackDesk.tsx`.
- Map-UI agent: step 10, owns `MapStudio.tsx`.
- FTM-UI agent: step 11, owns `FtmDesk.tsx`.

Do not edit `styles.css` in parallel beyond named scoped additions; queue style hunks through the shell-UI agent if they overlap.

### Wave 5 - shell integration, responsive pass, docs

- Shell-UI agent: steps 12 and 13 after all desks merge; owns `app.tsx`, lifecycle prop plumbing, and final `styles.css`.
- Docs agent: step 14 can begin after contracts settle, but merges after shell labels are final.

### Wave 6 - independent verification

- Integration lead: automated commands/cleanup receipts.
- Independent browser-QA agent: desktop/narrow scenarios and screenshots; no production edits unless a reproducible failure is returned to the owning agent with the exact scenario.

## Audit blocker disposition

| Audit blocker | Disposition |
|---|---|
| Equipment missing as top-level workspace | Steps 12-13: rename existing Items workspace to Equipment; no duplicate desk. |
| Workspace switching unmounts local drafts | Step 12: visited panes remain mounted; hidden previews deactivate safely. |
| Content-pack sequencing invalid | Steps 5, 7, 9: aggregate SQL + explicit reducer + phase gating. |
| Map export bypasses validation | Steps 4 and 10: Python enforcement at every writer plus current UI receipt. |
| PRJ has no FTM picker | Step 11: explicit child picker and deterministic normalization. |
| Retry/empty/error inconsistency | Steps 9-11 and 13: scoped state/retry on the affected designer surfaces. |
| ARIA tabs incomplete | Step 12: complete tablist/tab/tabpanel linkage and keyboard behavior. |
| Live writes lack confirmation | Steps 8, 9, 11, 12: shared dialog for all local-client/DB writes. |
| Dense responsive hierarchy | Step 13 plus step 15 desktop/narrow visual QA. |
| Unsafe prefix and `/tmp` substring containment | Step 1: exact configured target only; remove both mechanisms. |
| Symlink escape | Step 1: source/destination symlink rejection and canonical parent recheck. |
| Arbitrary install source/destination | Step 1: generated export sources and `Res/**/*.res` destinations only. |
| Arbitrary SQL path and caller DB URL | Step 2: export-root SQL and env-only `JFTSE_DATABASE_URL`. |
| Regex-bypassable SQL audit | Step 2: quote/comment-aware allowlist parser. |
| “Playtest” is only preflight | Step 6/9: accurately named strict preflight plus explicit manual GUI handoff. Automatic GUI operation is declined because no existing safe code supports it. |
| Temp payload leaks | Step 3 and final cleanup receipt: `finally` removal and byte-buffered texture response. |
| Bridge lacks timeout/stable errors | Step 3: bounded child lifecycle and stable sanitized codes. |
| Exact DX9 skinning/full ANI/EFT unavailable | Explicitly declined: preserve current approximate/honest previews and document limits; format recovery is outside this product-hardening task. |
| Stock client/binaries/archives must remain immutable | Steps 0, 1, 15: full-tree before/after SHA-256 receipt and strict destination policy excluding executables/DLLs. |
| Reported launch script may be stale/missing | Step 6: discover and verify actual script; no fallback string presented as ready. |

## Definition of done

Another engineer may declare completion only when every RED proof was observed before its production edit, every targeted GREEN command and the single full suite run pass, browser QA passes at both viewport sizes, one-shot temp cleanup is proven, and the before/after stock-client hash trees are identical. “Should pass”, an unchecked launch hint, or a browser-only client-side guard is not completion.
