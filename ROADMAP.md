# JFTSE Content Studio continuation roadmap

## Checkpoint

This roadmap continues from implementation checkpoint:

- `34df9cf feat: harden studio production workflows`
- Date: 2026-08-09
- Branch: `main`
- Detailed execution plan: `.omo/plans/jftse-studio-completion-ulw.md`
- Original designer-product plan: `.omo/plans/jftse-full-designer-content-studio.md`

The explicit checkpoint request superseded the detailed plan's temporary
“do not commit” instruction. Its technical constraints, wave ordering, QA
requirements, rollback rules, and integrity boundaries still apply.

## Product objective

Deliver JFTSE Content Studio as a truthful designer-facing workflow for:

1. authoring and packaging equipment;
2. authoring and packaging playable map projects;
3. installing only into disposable managed client profiles;
4. auditing generated SQL before any optional apply;
5. preserving one coherent project document across reload, templates,
   undo/redo, previews, and harness state;
6. shipping production checks, browser E2E coverage, evidence, and cleanup.

Do not claim general DAT/EFT writing, runtime-authored map spawns, terrain
compilation, or stage-material compilation until executable compatibility
evidence exists.

## Immutable boundaries

- Stock client aggregate baseline:
  `be1f78f3acdf7ad2b934c393675d9c4b049bd5c61007f901992bfc9f6b948fe3`
- Sibling JFTSE status baseline:
  `2f1ce364c9d6fbc6fb0a7f63198d6fad48c48b1108c23ebd86e72d29aa16dce2`
- Both downloaded ResTool jars:
  `590ccfa6d88e0e7ae5af864af212543ec41342197603fd183f782315e3b0402f`

All destructive QA must use disposable managed profiles. Never revert
unrelated shared-worktree or local-client changes.

## Completed work

### Wave 1: security and operations

- [x] Add failing SQL injection API regression
- [x] Implement escaped item `part` SQL literal
- [x] Bound HTTP parsing and bridge concurrency
- [x] Add production server mode and graceful shutdown
- [x] Verify focused tests and live HTTP behavior
- [x] Clean QA resources and record integrity hashes

Evidence: `evidence/wave-1-security/`

### Wave 2: external compatibility

- [x] Document the ResTool/JFTSE capability matrix
- [x] Add ResTool oracle compatibility fixtures
- [x] Encode external writer compatibility contracts
- [x] Add the JFTSE runtime-truth fixture
- [x] Verify oracle parity and immutable boundaries
- [x] Clean temporary oracle resources

Evidence: `evidence/wave-2-compat/`

### Wave 3: equipment production workflow

- [x] Add failing Equipment runtime-workflow tests
- [x] Bind the authored effect to generated equipment
- [x] Separate Equipment design evidence from runtime truth
- [x] Add managed install, SQL audit, and preflight handoff
- [x] Prove the accessible desktop and narrow browser workflow
- [x] Verify focused tests, diagnostics, typecheck, and build
- [x] Clean managed profiles, browsers, servers, and generated packages

Evidence: `evidence/wave-3-equipment/`

## Immediate continuation point

Start Wave 4 test-first with:

> Add failing forged Map dependency tests.

Primary seams:

- `tests/mapScenePackage.test.ts`
- `tests/mapSceneCompiler.test.ts`
- `server/mapScenePackage.ts`
- `server/mapSceneCompiler.ts`
- `web/MapCreatorPanel.tsx`
- `web/MapCreatorPackagePanel.tsx`

The first RED must prove that malformed, traversal, or missing dependencies
cannot become installable merely because the browser labels them available.

## Remaining roadmap

### Wave 4: Map workflow

- [ ] Add failing forged Map dependency tests
- [ ] Resolve Map dependencies server-side
- [ ] Surface an honest Map compiler runtime receipt
- [ ] Add Map managed install, SQL audit, and preflight workflow
- [ ] Prove Map browser and HTTP workflow
- [ ] Verify Wave 4 artifacts and focused tests
- [ ] Clean Wave 4 profiles, browsers, servers, oracle copies, and outputs

Wave 4 is complete only when forged availability cannot pass; valid
dependencies are rooted and hashed server-side; unsupported player-spawn,
terrain, and stage-material fields remain explicit; save/reload identity is
proven; manual compatibility is recorded; rollback succeeds; and immutable
boundaries remain accounted for.

### Wave 5: Project architecture

- [ ] Extend the authoritative versioned project-document schema
- [ ] Add project lifecycle integration regressions
- [ ] Consolidate the shared typed API boundary
- [ ] Add the bounded bridge scheduler and cancellation tests
- [ ] Fix preview lifecycle and stale-request races
- [ ] Split oversized touched domain modules
- [ ] Prove desktop and narrow project lifecycle in a real browser
- [ ] Verify Wave 5 diagnostics, tests, typecheck, and build
- [ ] Clean Wave 5 browser, server, profile, and generated resources

Wave 5 is complete only when one document owns all writable project state;
migrations, reload, templates, and undo/redo are deterministic; latest
requests win; hidden preview work stops; bridge work is bounded and
cancellable; and touched production modules remain at or below 250 physical
lines unless a documented pre-existing exception is unavoidable.

### Wave 6: Release verification

- [ ] Align product documentation, onboarding, and compatibility references
- [ ] Add event-driven browser end-to-end coverage
- [ ] Add CI and production release checks
- [ ] Run final full-surface QA
- [ ] Complete the independent reviewer loop
- [ ] Clean all QA resources and verify immutable boundaries
- [ ] Prepare the final atomic commit sequence

Wave 6 is complete only when scenarios A-F have linked RED/GREEN and
real-surface evidence; the full test suite, diagnostics, typecheck, Python
checks, production build, bundle report, and E2E suite pass; independent
review is unconditional; rollback/cleanup receipts are present; and no owned
QA process, profile, browser state, or generated package remains.

## Standard continuation gate

Before each new wave:

1. Re-read this roadmap and the detailed execution plan.
2. Confirm the worktree and process ownership before cleanup.
3. Record the relevant immutable hashes/status.
4. Capture the named failing test or scenario before production edits.

Before each wave is closed:

```sh
bun test
bun run typecheck
python3 -m compileall -q python
bun build web/index.html --outdir /tmp/jftse-content-studio-build
git diff --check
```

Behavioral work additionally requires fresh HTTP/browser/manual-surface
evidence and an explicit cleanup receipt. A green unit suite alone is not a
completion signal.

## Known shared-state notes

- Wave 3 preserved the stock-client aggregate exactly.
- Concurrent local-client runtime/crash files and sibling `ac-server`
  Eclipse metadata were observed during cleanup. They were not created or
  reverted by the managed Equipment workflow.
- Live SQL apply remains optional and was intentionally not exercised during
  Wave 3 browser QA.
- Real DX9 visual inspection remains manual and authoritative.
