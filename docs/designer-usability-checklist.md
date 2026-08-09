# Designer usability validation

Use this checklist against `bun run dev` at 1440×900 and 390×844. Record the
date, tester, browser, result, and evidence path for every run. A milestone is
not accepted when a required step needs a raw archive path, SQL identifier, or
mesh index unless the step is explicitly under Advanced diagnostics.

## Session setup

- Start from a clean browser context.
- Confirm the stock client tree hash before testing.
- Confirm the setup checklist is collapsed and accurately reports unavailable
  real-client automation.
- Keep the browser console, page-error buffer, and network-failure buffer open.

## Project shell

1. Create a named project from each template.
2. Change workspace and equipment workflow step.
3. Use Undo and Redo by button and `Ctrl/Cmd+Z`.
4. Reload and confirm project name, workspace, and editor state recover.
5. Corrupt the primary autosave while keeping a valid backup; confirm recovery
   reports `recovered-from-backup`.
6. Load a newer schema; confirm the studio reports `newer-version` and starts a
   safe empty project without overwriting the newer payload.
7. Navigate workspace tabs with Left, Right, Home, and End.
8. Confirm Advanced diagnostics is collapsed by default.

Pass: no horizontal page overflow, no lost project state, and no hidden primary
action.

## Equipment Creator

1. Import a new glTF file or load the built-in sample.
2. Assign a texture and tint to every material.
3. Select `Bone_Racket`, enter item name/index/character/price, and adjust
   particle color, rate, lifetime, size, and curve.
4. Resolve every actionable validation message.
5. Build the equipment manifest.
6. Load browser and DX9 screenshots into the comparison slots.

Pass: the manifest includes source counts, materials, attachment, metadata,
particle values, comparison names, and the explicit DX9 verification warning.

## Map Creator

1. Start from **New empty map**.
2. Name the court, place net/scenery, add both player spawns, and paint
   collision.
3. Select, translate, rotate, scale, snap, duplicate, hide, and show an object.
4. Select a Blender round-trip source and court texture.
5. Resolve the dependency graph and export the complete map package.
6. Reload and confirm name, objects, spawns, collision, and references recover.

Pass: the API receipt path exists, its SHA-256 matches the published file, and
the scene embedded in the package equals the saved scene.

## Managed client harness

1. Create and run **designer-safe-pass**.
2. Confirm profile, snapshot, exit 0, readiness, capture, logs, and process
   cleanup.
3. Create and run **designer-rollback-demo**.
4. Confirm exit 9, no readiness, partial capture marked `DISCARDED`, rollback
   marked `RESTORED`, and before/after tree hashes match.
5. Confirm the UI says real DX9 login/content selection remain manual.

Pass: no process remains, the disposable client has the expected final tree,
and the stock client hash is unchanged.

## Responsive and accessibility

- At 390×844, assert
  `document.documentElement.scrollWidth === window.innerWidth`.
- Confirm every form control has an accessible name and 44px touch target.
- Confirm tab/tabpanel relationships, visible focus, dialog focus trapping,
  status live regions, and keyboard reachability.
- Confirm each pane owns its scrolling and all primary actions remain reachable.

## Required evidence

- Desktop and narrow screenshots.
- Equipment manifest and comparison screenshot.
- Map package manifest, receipt, and independent hash command.
- Safe/failure harness API JSON, logs, screenshots, before/after hashes.
- Full `bun test`, `bun run typecheck`, production build, and changed-file LSP
  diagnostics.
- Final stock/sibling integrity hashes and QA resource teardown receipt.
