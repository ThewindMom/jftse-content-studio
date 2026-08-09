# JFTSE Content Studio — Product Design Contract

## Product position

JFTSE Content Studio is a local production tool for Fantasy Tennis content
designers. It exposes proven JFTSE/FT-ResTool capabilities as guided workflows
without pretending to be Blender, a terrain sculptor, or the DX9 client.

The studio optimizes for:

1. **Designer language first** — Equipment, Content Pack, Map Studio, Mesh
   Studio, build, install, audit, preflight.
2. **Progressive disclosure** — show the current decision and its required next
   action; keep advanced data available without making it the primary path.
3. **Visible trust boundaries** — distinguish generated exports, read-only
   stock/JFTSE inputs, and the exact configured local client.
4. **Truth over celebration** — PASS/MISS or PASS/TODO describes evidence; no
   browser state claims that gameplay or DX9 rendering passed.
5. **One job per pane** — each workspace retains its draft while inactive, but
   hidden previews stop render loops and release runtime resources.

## Workspace information architecture

The fixed top-level order and labels are:

1. **Equipment**
2. **Content Pack**
3. **Map Studio**
4. **Mesh Studio**

Each top-level control is an ARIA tab linked to a persistent tabpanel.
ArrowLeft/ArrowRight wrap, Home/End jump to boundaries, and only the active tab
is in the tab order.

### Equipment

Five linked workflow tabs:

1. Item — choose a stock racket base.
2. Effect — choose/edit an atlas and emitter.
3. Export — build and verify generated archives.
4. Install — review the exact generated source and configured local target,
   then confirm.
5. Local check — verify files/binaries/launcher, copy the launch command, and
   follow manual login/equip/visual-check instructions.

### Content Pack

Configure equipment, map, stage, and optional FTM inputs; then follow the
receipt-backed sequence:

`Build → Confirm install → SQL dry-run → Confirm live apply (when SQL exists) → Local client preflight`

Any draft edit invalidates the build and every downstream receipt. Preflight
shows PASS/MISS rows plus a manual handoff and never claims gameplay passed.

### Map Studio

The map catalog, design desk, and Stage/FTM evidence pane form one workflow.
Export/create actions require a passing receipt for the currently selected
stage script. Script or map changes invalidate that receipt.

PRJ parsing exposes an explicit child-FTM picker. FTM authoring is tied to the
currently parsed archive/member identity; source edits invalidate loaded data
and authored exports.

### Mesh Studio

The mesh catalog, modeler, and decode evidence remain distinct. The browser
viewport is an inspection surface. OBJ/glTF export is the interoperability path;
DAT transform/new-topology authoring remains clearly marked experimental.

## Layout

### Desktop (1440×900 target)

- Preserve a useful three-column hierarchy:
  catalog/configuration → primary work → evidence/status.
- Keep primary actions near the fields they affect.
- Use bounded panel scrolling instead of clipping the page.

### Narrow (390×844 target)

- One page column and one-column field grids.
- Remove fixed panel minimum heights.
- Workspace/workflow tabs scroll horizontally without body overflow.
- Dialogs, canvases, status details, and primary actions remain reachable.
- Preserve at least a 44px control hit target.

## States and recovery

Every list/workflow distinguishes:

- loading;
- real empty data;
- no search matches;
- actionable API error with retained structured detail;
- Retry using the current draft/source;
- success evidence.

Stale async work must not attach status, errors, receipts, or preflight results
to a newer draft revision.

## Confirmation contract

All local-client installs and live SQL applies use the shared confirmation
dialog. It:

- names the write and exact target;
- focuses Cancel first;
- traps Tab/Shift+Tab while open;
- closes on Escape or Cancel without issuing the write;
- restores focus to the triggering control;
- performs the write only from the explicit confirm action.

## Filesystem and SQL safety

- Sibling JFTSE source and configured stock client are read-only.
- Install sources must be regular, non-symlink files under this repository's
  `exports/` root.
- The destination must be the exact configured local client.
- Only allowlisted `Res/**/*.res` destinations are accepted; traversal,
  executable/DLL writes, and intermediate symlinks are rejected.
- Every successful install returns matching source/installed SHA-256 receipts.
- SQL files must be regular, non-symlink files under `exports/`.
- Server configuration is the only database credential source.
- Dry-run structurally audits allowlisted generated INSERTs; live apply requires
  the matching audit receipt and explicit confirmation.

No temporary-directory exception or caller-selected prefix is accepted.

## Product-truth language

Use:

- “Local client preflight”
- “Ready for manual local-client verification”
- “Browser preview is approximate”
- “Open the local client, log in, equip/select, and visually inspect”

Do not use:

- claims that playtesting is ready before the human client check
- “Gameplay passed”
- “DX9 verified” without a human client check
- “Safe” without naming the validated boundary

## Visual direction

- Dark, utilitarian workbench rather than game launcher chrome.
- Accent color communicates selection and primary action, not decoration.
- Green means a verified check; red means a concrete blocking failure.
- Monospace is reserved for paths, SQL, hashes, and decoded evidence.
- Motion is restrained and stops in hidden workspaces or under reduced motion.
*** End of File
