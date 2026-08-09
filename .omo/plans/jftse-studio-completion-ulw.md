# JFTSE Content Studio Completion — Executable ULW Plan

## Binding contract

Execute the six waves in order. A wave may parallelize only as shown, and its integration gate must pass before the next wave starts. Do not commit. Do not mutate the stock client, either downloaded ResTool jar, or the sibling JFTSE tree. All installs and destructive QA target a disposable managed profile. Preserve and compare these baselines at every integration gate:

- stock client aggregate: `be1f78f3acdf7ad2b934c393675d9c4b049bd5c61007f901992bfc9f6b948fe3`
- sibling JFTSE status: `2f1ce364c9d6fbc6fb0a7f63198d6fad48c48b1108c23ebd86e72d29aa16dce2`
- ResTool jars (both): `590ccfa6d88e0e7ae5af864af212543ec41342197603fd183f782315e3b0402f`

The two jars are identical Java 21 applications. Treat only FTM `parse/store/fromJson/toJson`, PRJ `read/write`, SET/TEX decrypt/encrypt, and the GUI FTM extract/store/edit actions as proven write operations. There is no proven general DAT mesh writer or `.Eft` writer. Do not invent DAT/EFT support, runtime process spawning, or runtime-authored map spawns. Map spawns remain design-only because JFTSE `chat-server/.../GameManager.java:497-533` hard-codes mode-dependent runtime coordinates. FTM output remains reverse-engineered and requires oracle fixtures plus manual-client validation.

For every new or extracted production module, and every changed extracted module, enforce `<=250` physical lines. A pre-existing god module may exceed 250 only when changed surgically; record its before/after line count, why extraction would widen risk, and the exact touched symbols in `evidence/final/module-exceptions.md`. No new god-module exception is allowed. Never suppress diagnostics or delete/skip tests.

Before Wave 1, create `evidence/{wave-1-security,wave-2-compat,wave-3-equipment,wave-4-map,wave-5-project-architecture,wave-6-final}` and record worktree status, process ownership, open ports, and the three immutable hashes in `evidence/baseline.txt`. Do not kill a process until ownership is established.

## Wave 1 — SQL/security/operations RED -> GREEN (Scenario A)

**Topology and dependencies:** independent security owner handles tasks 1.1-1.3; operations owner handles 1.4 in parallel after RED is captured; lead owns live integration and immutable-tree checks. No dependency on later waves.

1. **Pin SQL behavior and prove injection.** In `tests/api.test.ts`, add/complete `rejects injected equipment part SQL`; exercise the content-pack build and SQL dry-run boundary. In `python/equipment_author.py`, characterize the function that serializes the item `part` into product SQL (record its current symbol in the test/evidence before editing).
2. **Create one SQL-literal boundary.** In `python/equipment_author.py`, add `sql_literal(value: str) -> str` and route the item-part emission through it; do not broaden accepted tables or weaken `sql_policy`. Align direct-Python client-root fallback with the HTTP bridge's stock/local ordering so direct CLI cannot choose stock as writable.
3. **Bound untrusted work.** In `server/index.ts`, apply explicit body-size, parse-size, request-time, and bridge-concurrency limits to content-pack build and SQL apply paths. Return structured 4xx/429 responses; preserve errors rather than swallowing them.
4. **Production operation.** In `server/index.ts` and the existing package scripts, expose a production server mode with bounded bridge scheduling and graceful shutdown; no runtime JFTSE/client spawning.

**RED:** `mkdir -p evidence/wave-1-security && (bun test tests/api.test.ts -t "rejects injected equipment part SQL" 2>&1 | tee evidence/wave-1-security/red.txt); test ${PIPESTATUS[0]} -ne 0`

**GREEN:** `bun test tests/api.test.ts -t "rejects injected equipment part SQL" 2>&1 | tee evidence/wave-1-security/green.txt && bun test tests/api.test.ts 2>&1 | tee evidence/wave-1-security/api-suite.txt`

**Real HTTP:** start the production-mode server on `127.0.0.1:4310`, recording PID/command. Run:

```sh
curl -i -X POST http://127.0.0.1:4310/api/content-pack/build \
  -H 'content-type: application/json' \
  --data '{"equipment":{"part":"Racket'\'' ); INSERT INTO accounts (Username) VALUES ('\''owned'\''); --"}}' \
  | tee evidence/wave-1-security/build-http.txt
curl -i -X POST http://127.0.0.1:4310/api/sql/apply \
  -H 'content-type: application/json' \
  --data '{"dryRun":true,"sql":"'"$(python -c 'import json; print(json.load(open("evidence/wave-1-security/build.json"))["sql"])')"'"}' \
  | tee evidence/wave-1-security/apply-http.txt
```

If the exact build request envelope differs, the test fixture must emit `evidence/wave-1-security/malicious-request.json`, and curl must use `--data @...`; do not hand-edit around validation. PASS only if no injected extra INSERT is accepted. Save generated SQL, response bodies, server log, limits/concurrency test receipts, and before/after immutable hashes.

**Cleanup/rollback:** stop only the recorded server/bridge PIDs; delete the disposable output directory. Roll back only Wave 1 edits if GREEN or live HTTP fails; never relax policy. **Stop condition:** injection test observed RED then GREEN, HTTP build/apply rejects or safely quotes the payload, bounds and production-mode tests pass, diagnostics for changed files are clean, and immutable hashes match.

## Wave 2 — ResTool/JFTSE compatibility fixtures (Scenario F foundation)

**Topology and dependencies:** compatibility owner creates fixture/oracle lane; JFTSE-contract owner creates read-only contract fixtures in parallel; lead integrates the matrix. Depends on Wave 1 GREEN and baseline integrity.

1. **Capability matrix.** Create `docs/references/restool-jftse-capability-matrix.md` with rows for FTM, PRJ, SET, TEX, DAT, EFT, item binding, map spawns, terrain, and stage materials. Each row names read/write/runtime status, oracle, fixture, and product wording. Mark DAT/EFT writers unproven and map runtime spawns unsupported.
2. **Oracle fixtures.** Add immutable samples under `tests/fixtures/compatibility/` derived from disposable copies only: FTM round-trip, PRJ container round-trip, SET/TEX encrypt/decrypt, stock item chain (`Item.res` index 214 -> `Item07.res` -> `Niki_CommonRacket41.dat`; `Mesh.res` -> `Bone_Racket`), and map chain (`Info.res` -> `1_Emerald_Beach.set` -> `BF_Court01.dat`; `FantaCastle.res` -> 50x70 `FantaCastleOutSide.ftm`). Store provenance and hashes in `tests/fixtures/compatibility/README.md`.
3. **Executable contracts.** Create `tests/compatibility.test.ts` to run Studio readers/writers against fixtures and compare normalized semantics plus required byte-for-byte cases. Add an isolated Java oracle harness under `tests/fixtures/compatibility/oracle/` invoking only proven ResTool APIs: `FTMParser.parse/store/fromJson/toJson`, `PRJReader.read/write`, and SET/TEX operations. Never write the downloaded jars or source fixtures.
4. **JFTSE runtime truth fixture.** Encode the consistent item-index contract across server rows, ownership/equipment slots, Item SET tuple `(Index, Char, Part, Mesh, Tex, Effect)`, positional `RacketEffect.set`, and particle resources. Add a fixture asserting authored map spawn coordinates are excluded from runtime receipts.

**RED:** `bun test tests/compatibility.test.ts 2>&1 | tee evidence/wave-2-compat/red.txt; test ${PIPESTATUS[0]} -ne 0`

**GREEN:** `bun test tests/compatibility.test.ts 2>&1 | tee evidence/wave-2-compat/green.txt`

**Real invocation:** run the isolated Java oracle against copies in `evidence/wave-2-compat/oracle-work/`, then run the Studio production HTTP compatibility/preflight endpoint against each generated artifact; save command transcripts, normalized JSON, byte hashes, and HTTP responses. Manual-open generated FTM/PRJ in ResTool from the disposable directory and record an action log/screenshot; this is compatibility evidence, not runtime proof.

**Cleanup/rollback:** remove oracle work copies and generated outputs, leaving committed-intent fixtures/evidence only; verify both jar hashes. Roll back a capability claim if no executable fixture proves it. **Stop condition:** all fixtures pass, matrix and tests agree, no DAT/EFT/runtime-spawn claim exists, and source/stock/sibling hashes match.

## Wave 3 — Equipment effect binding and install/audit/preflight (Scenario B)

**Topology and dependencies:** equipment domain owner handles author/package tasks; workflow owner handles install/audit/preflight and UI in parallel after shared receipt types are fixed; lead runs disposable-profile integration. Depends on Waves 1-2.

1. **Pin product behavior.** Add targeted tests named `writes explicit equipment effect binding`, `reports design-only equipment fields`, and `hands equipment package to install audit preflight` in the existing equipment creator/writer/project suites. Fixtures must use a single item index through every runtime surface.
2. **Bind runtime effects.** In `python/equipment_author.py`, change the equipment authoring path currently using `includeItemBinding: false`/`effect=0` so explicit effect selection writes the Item SET tuple, positional `RacketEffect.set` binding, particle-resource references, and matching server SQL. Preserve explicit `0` only when the user selects no runtime effect.
3. **Separate design and runtime truth.** Extract `src/domain/equipment/runtime-contract.ts` with `classifyEquipmentRuntimeFields()` and `buildEquipmentRuntimeReceipt()`; mark arbitrary DAT topology/material and general EFT authoring as design-only/unwritten. Keep each extracted module <=250 lines.
4. **Complete handoff.** Add `src/domain/equipment/package-workflow.ts` with `buildEquipmentPackage()`, `installEquipmentPackage()`, `auditEquipmentPackage()`, and `preflightEquipmentPackage()`. Bind the creator's explicit runtime-package CTA to this workflow through the shared HTTP API; install only to a disposable managed profile and always emit manifest, SQL/archive hashes, rollback receipt, and PASS/MISS field receipt.
5. **Accessible UI proof.** In the existing equipment creator panel, expose effect binding, design/runtime status, install destination, audit result, and preflight result with keyboard-operable controls and live status semantics.

**RED:** `bun test -t "writes explicit equipment effect binding|reports design-only equipment fields|hands equipment package to install audit preflight" 2>&1 | tee evidence/wave-3-equipment/red.txt; test ${PIPESTATUS[0]} -ne 0`

**GREEN:** `bun test -t "writes explicit equipment effect binding|reports design-only equipment fields|hands equipment package to install audit preflight" 2>&1 | tee evidence/wave-3-equipment/green.txt`

**Real HTTP/browser:** use curl to build, install, SQL-audit, and preflight one sample equipment package against the disposable profile, saving all request/response JSON. Run/create `tests/e2e/equipment-runtime.spec.ts` at 1440x900: load sample glTF and OBJ, set material/attachment/particle/comparisons/effect, invoke the runtime-package CTA, install, audit, and preflight. Save screenshot, action trace, manifest, generated SQL, archive hashes, PASS/MISS receipt, rollback receipt, and server log under `evidence/wave-3-equipment/`.

**Cleanup/rollback:** execute the generated rollback receipt, delete the disposable profile and browser storage, stop owned processes, and prove the profile no longer exists. On failure, revert the disposable install using its receipt before changing code. **Stop condition:** targeted RED->GREEN, effect is nonzero when selected and consistent everywhere, unsupported fields are honest, browser/HTTP handoff passes, cleanup succeeds, and immutable hashes match.

## Wave 4 — Map real dependency verification and honest install/audit/preflight (Scenario C)

**Topology and dependencies:** map compiler owner handles dependency resolver/contracts; workflow/UI owner handles package handoff after receipt shape is fixed; compatibility owner reviews FTM/PRJ oracle use; lead validates manual client and disposable profile. Depends on Waves 1-3.

1. **Reject client assertions.** Add tests named `rejects malformed map dependency`, `rejects missing real map dependency`, `reports unsupported runtime map fields`, and `hands map package to install audit preflight`. Remove the client-local behavior that marks every missing path available.
2. **Resolve on server.** Extract `server/map-dependencies.ts` with `normalizeDependencyPath()`, `resolveMapDependencies()`, and `verifyMapDependencies()`. Resolve only beneath approved read-only roots or the disposable managed profile, reject traversal/malformed input, hash actual files, and ignore client-supplied availability claims.
3. **Honest compiler receipt.** In the existing map compiler/package path, emit explicit unsupported receipts for player spawns, terrain geometry, and stage material binding. Preserve two authored spawns in project/design data but omit runtime-spawn claims. Use only oracle-proven FTM/PRJ/SET/TEX operations; do not synthesize DAT/EFT writers.
4. **Complete workflow.** Add `src/domain/map/package-workflow.ts` with `buildMapPackage()`, `installMapPackage()`, `auditMapPackage()`, and `preflightMapPackage()`. Gate install on server-verified dependencies and compatibility fixtures; emit manifest, hashes, missing/malformed dependency results, unsupported-field receipt, rollback receipt, and reload identity proof.

**RED:** `bun test -t "rejects malformed map dependency|rejects missing real map dependency|reports unsupported runtime map fields|hands map package to install audit preflight" 2>&1 | tee evidence/wave-4-map/red.txt; test ${PIPESTATUS[0]} -ne 0`

**GREEN:** `bun test -t "rejects malformed map dependency|rejects missing real map dependency|reports unsupported runtime map fields|hands map package to install audit preflight" 2>&1 | tee evidence/wave-4-map/green.txt`

**Real HTTP/browser:** curl the dependency endpoint with traversal, malformed, missing, and valid real fixture paths; malformed/missing must fail. Run/create `tests/e2e/map-runtime.spec.ts`: at 1440x900 load a stock-template scene, author two design-only spawns, object and collision, verify real dependencies, package/install/audit/preflight, reload, and compare project JSON. Save HTTP transcript, screenshot, trace, manifest, FTM/PRJ hashes/oracle results, unsupported receipt, reload digest, rollback, and manual-client action log under `evidence/wave-4-map/`.

**Cleanup/rollback:** run rollback, remove disposable profile/project/browser data and oracle copies, stop owned processes. **Stop condition:** targeted RED->GREEN, forged availability cannot pass, unsupported runtime fields remain visible, reload is identical, manual compatibility is recorded, cleanup succeeds, and immutable hashes match.

## Wave 5 — Project ownership plus async/performance/module/API refactors (Scenarios D-E)

**Topology and dependencies:** project-state owner first freezes schema and migrations; after that, UI ownership and API/client owners work in parallel. Performance owner works from characterization tests; lead integrates request ordering and line budgets. Depends on all product workflows in Waves 3-4.

1. **One authoritative document.** Add `src/domain/project/project-document.ts` defining a versioned `ProjectDocument`, migration/validation, and ownership for classic Equipment, Content Pack, map catalog, Mesh/FTM/harness configuration, templates, undo/redo, and persisted diagnostics state. Existing stores become projections; no duplicated writable state.
2. **Project lifecycle tests.** Add integration tests named `owns classic equipment and content pack state`, `invalidates undo on template apply`, `reloads one coherent project document`, and `invalidates derived mesh ftm harness state`. Test deterministic events, never sleeps/polling.
3. **Shared API boundary.** Add `src/api/contracts.ts` and `src/api/client.ts` with typed request/response/error contracts, cancellation, request IDs, size bounds, and stale-response suppression. Route equipment, map, project, install, audit, and preflight calls through it.
4. **Bridge scheduling.** Extract `server/bridge-scheduler.ts` with `BridgeScheduler.enqueue()`, `cancel()`, and `shutdown()`. Enforce configured concurrency and queue/request bounds, propagate cancellation, and test exact completion/cancellation signals with bounded timeouts.
5. **Lifecycle/performance.** In preview owners, cancel WebGL/worker/network work on unmount or replacement; suspend hidden panels; prevent stale responses from overwriting current state. Add indexed export lookup and bounded retention with non-destructive pruning receipts.
6. **Surgical decomposition.** Extract only touched domains into `src/domain/project/`, `src/domain/equipment/`, `src/domain/map/`, `src/api/`, and `server/bridge-scheduler.ts`; enforce <=250 lines. Document only pre-existing surgically touched god-module exceptions in `evidence/final/module-exceptions.md`.

**RED:** `bun test -t "owns classic equipment and content pack state|invalidates undo on template apply|reloads one coherent project document|invalidates derived mesh ftm harness state|drops stale response|cancels WebGL work|bounds bridge concurrency|bounds request size" 2>&1 | tee evidence/wave-5-project-architecture/red.txt; test ${PIPESTATUS[0]} -ne 0`

**GREEN:** `bun test -t "owns classic equipment and content pack state|invalidates undo on template apply|reloads one coherent project document|invalidates derived mesh ftm harness state|drops stale response|cancels WebGL work|bounds bridge concurrency|bounds request size" 2>&1 | tee evidence/wave-5-project-architecture/green.txt && bun run typecheck 2>&1 | tee evidence/wave-5-project-architecture/typecheck.txt && bun run build 2>&1 | tee evidence/wave-5-project-architecture/build.txt`

**Real browser:** run/create `tests/e2e/project-shell.spec.ts` at 1440x900 and 390x844. Edit classic Equipment and Content Pack, map catalog, Mesh/FTM/harness settings; reload; apply template; undo/redo; hide/show preview panels; trigger overlapping requests. Assert one coherent saved document, invalidation rules, latest-request wins, hidden work stops, and diagnostics stay collapsed. Save screenshots, trace/action log, saved/reloaded digest, bridge concurrency trace, cancellation receipt, module line report, production bundle report, and performance measurements.

**Cleanup/rollback:** close browser contexts, cancel bridge queue, prune only QA-tagged exports through retention tooling, remove disposable project/profile, stop owned processes. Roll back schema/API consumers as one unit if migration/reload fails. **Stop condition:** D/E tests RED->GREEN, desktop+narrow flows pass, typecheck/LSP/build/bundle report are clean, hidden work stops, modules meet line policy or exception record, and immutable hashes match.

## Wave 6 — Product truth, E2E, CI, final QA, review, cleanup (Scenario F and final gate)

**Topology and dependencies:** docs owner and CI/E2E owner work in parallel from the frozen capability matrix; QA owner runs real surfaces after merge; independent reviewer receives evidence only after all checks; lead alone fixes criterion-cited blockers and performs cleanup. Depends on Waves 1-5.

1. **Product truth.** Update `README.md`, `DESIGN.md`, onboarding/checklist documents, client-RE references, and `docs/references/restool-jftse-capability-matrix.md`. State proven FTM/PRJ/SET/TEX operations; identical jars; no general DAT/EFT writer; design-only map spawns/terrain/stage materials; explicit equipment effect contract; disposable-profile install/audit/preflight; rollback and retention behavior.
2. **End-to-end suite.** Keep `tests/e2e/equipment-runtime.spec.ts`, `tests/e2e/map-runtime.spec.ts`, and `tests/e2e/project-shell.spec.ts` event-driven with bounded timeouts. Add one production smoke covering launch, HTTP health, creator workflows, reload, and shutdown without runtime client/JFTSE spawning.
3. **CI/release checks.** Update the existing CI workflow to run compatibility fixtures, unit/integration tests, E2E, typecheck, Python diagnostics/compile, production build, bundle report, module line-budget check, and forbidden-mutation/hash checks. CI must not require stock/sibling writes or downloaded jars; use checked-in lawful fixtures/harness stubs preserving the proven contract.
4. **Final QA.** Run scenario A adversarial HTTP; B equipment desktop; C map desktop; D project desktop+narrow; E cancellation/concurrency/build; F compatibility/docs/release. Run the full suite exactly once after targeted checks are green. Capture browser screenshots/traces and curl transcripts.
5. **Independent review.** Give the reviewer this plan, diff, module report, A-F index, RED/GREEN transcripts, browser/HTTP artifacts, hash receipts, and cleanup plan. Approval must be unconditional. Fix only criterion-cited blockers and rerun affected scenarios; if shared code changed, rerun the final full gate.
6. **Final cleanup.** Identify ownership before stopping servers/bridges/browsers. Execute all rollback receipts; remove QA profiles, browser storage, oracle work, generated packages, and QA exports. Verify port 4310 and owned child processes are gone, immutable hashes match, and worktree contains no stock/sibling/jar mutation. Produce `evidence/final/cleanup.txt` and a draft atomic commit sequence, but do not commit.

**RED:** docs/E2E/CI contract checks must fail before updates: `bun test -t "capability matrix matches product|production smoke|forbids external mutation" 2>&1 | tee evidence/wave-6-final/red.txt; test ${PIPESTATUS[0]} -ne 0`

**GREEN/final:** run changed-file LSP diagnostics; then `bun test 2>&1 | tee evidence/wave-6-final/full-suite.txt`, `bun run typecheck`, Python diagnostics/compile through the repository's existing command, `bun run build`, the production bundle report, and `bunx playwright test tests/e2e`. Save every transcript under `evidence/wave-6-final/`; do not claim a validator that was not run. Run production server HTTP health/adversarial calls and browser smoke against its real URL.

**Evidence index:** create `evidence/final/scenarios-a-f.md`, linking A injection RED/GREEN+HTTP; B equipment screenshot/manifest/hashes/rollback; C dependency HTTP/map screenshot/manifest/hashes/unsupported receipt; D desktop+narrow screenshots/action log; E mutation/characterization, cancellation/concurrency, diagnostics/typecheck/build/bundle/line report; F compatibility matrix/fixtures, docs/CI/E2E, immutable hashes, review, and cleanup.

**Stop condition:** scenarios A-F all have linked RED/GREEN and real-surface evidence; full suite, diagnostics, typecheck, Python checks, build, bundle and E2E pass; reviewer approves unconditionally; stock/sibling/jars match baseline; no QA resources remain; no commit exists.

## Risk register

| Risk | Detection | Mitigation | Hard stop |
|---|---|---|---|
| SQL injection or policy bypass | Scenario A unit + live build/apply transcript | one literal boundary, unchanged allowlist, dry-run first | any extra statement accepted |
| Stock/sibling/jar mutation | hash/status at every gate | read-only sources; disposable copies/profiles | any unexplained digest change |
| False external-format claim | fixture/matrix mismatch | only oracle-proven operations; design-only receipt | DAT/EFT/runtime-spawn claim without oracle |
| FTM incompatibility | byte/semantic fixture + ResTool/manual-client check | preserve reverse-engineered status and rollback | artifact cannot reopen/validate |
| Forged map dependency | malformed/missing/valid HTTP tests | server-side rooted resolution and hashes | client assertion bypasses gate |
| Project state divergence | reload/template/undo integration tests | one versioned authoritative document | duplicated writable owner remains |
| Async race/resource leak | stale/cancel/concurrency tests and traces | cancellation, request IDs, hidden suspension | stale UI or work survives teardown |
| Scope-growing refactor | module line report/diff review | <=250 lines; surgical exception record | new oversized module/undocumented exception |
| Cleanup harms another agent | PID ancestry/command ownership log | stop only owned PIDs | ownership unknown |

## Rollback table

| Wave | Rollback unit | Required receipt before rollback is complete |
|---|---|---|
| 1 | SQL/security/server edits and temp outputs | policy restored, owned server stopped, hashes unchanged |
| 2 | fixture/matrix claim and oracle work copies | unsupported claim removed, jars/fixtures unchanged |
| 3 | equipment code plus disposable installation | generated rollback applied, profile removed, SQL/archive hashes recorded |
| 4 | map code plus disposable installation | generated rollback applied, profile/oracle work removed, dependency transcript retained |
| 5 | schema+migrations+all API consumers as one unit | saved baseline project reloads, queue/browser work terminated |
| 6 | docs/CI/E2E edits only; never erase evidence needed for diagnosis | QA resources absent, immutable hashes match, no commit |
