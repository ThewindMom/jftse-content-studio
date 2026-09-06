# Blender–JFTSE pipeline runbook

Run commands from the repository root. Read the current implementation before
changing a contract; this document records the tested static-decoration route.

## Format and ownership map

| Artifact | Role and source of truth |
| --- | --- |
| Client `.res` archives | ZIP containers for the observed resources; preserve unrelated members. `python/twinkle_studio.py` owns stage packaging. |
| Static `.dat` | Observed AduMesh family, with material primitives and triangle strips. `python/twinkle_mesh.py` parses it; `python/oktoberfest_native.py` rebuilds verified templates. Not all DAT families share this layout. |
| `.tex` | DDS payload with the first 128 bytes XOR-encoded in this route. Use `python/tex_codec.py`, not renaming PNGs. Native exports use opaque DXT1 and a complete mip chain. |
| `.set` | Encrypted placement script in `Res/Stage/Info.res`. Use `python/client_crypto.py`; preserve source sections and transforms through `compile_layout`. |
| `.blend` | Editable authoring source with packed paint. One source per prop or deliberate variant. |
| `.glb` | Bounded static interchange, not a native game resource. `server/importedProps.ts` owns Studio upload validation. |
| Layout JSON | Content-addressed asset references and placements. It is not a model bundle. |
| Native ZIP | Expanded SET plus resource additions, export report and installation instructions. An export is not an installation or gameplay test. |

## 1. Prepare private inputs and establish a baseline

- Inspect repository configuration and the existing server before starting another
  instance. Default port is 4310; an isolated preview may use another port.
- `JFTSE_STOCK_CLIENT` identifies pristine client resources. Use
  `JFTSE_FESTIVAL_RESOURCES` for the authored festival resource directory when the
  layout depends on it. Never overwrite pristine archives with festival copies.
- Save the current layout, its sourceHash, protected records and the imported
  registry before a new composition pass. Compare complete records afterward.
- If sourceHash differs, inspect `source_text` and `initial_document`, the stock
  Info.res/decrypted SET, and the festival inputs actually used by the server.
  Reconcile a separate fixture copy or reopen from the correct source. Never edit
  only sourceHash to force acceptance.
- Imported bytes live in `exports/imported-props/`; the server passes that registry
  to Python via `JFTSE_IMPORTED_PROPS`. A CLI export must use the same registry.
- Keep extracted paint, reference images, `.blend`/GLB outputs, client archives and
  generated ZIPs private/ignored. Commit reproducible source and text provenance
  instructions, not proprietary client bytes. Check Git status before staging.

## 2. Research and author

Use the stock audit/paint commands in SKILL.md. Useful owners:

- `python/audit_twinkle_style.py`: stage primitive/material evidence.
- `python/audit_stock_cart.py`, `python/prepare_beer_cart_paint.py`: carriage paint
  and geometry evidence; inspect crop/hash provenance, not just rendered colors.
- `python/blender_festival/reference_shapes.py`: rounded flowers, deep swags,
  shaped crests and curved runs.
- `python/blender_festival/common.py`: shared materials, mesh/UV construction,
  packed sources, previews, GLB output and reopen checks.
- `python/blender_festival/run_asset.py`: one builder per Blender invocation.

Load `running-blender`, read its complete catalog overview and selected sources,
record bindings, then seal the entry script and all changed helpers. A remembered
API, an old seal or a successful process is not evidence for a new operation.
Review source changes before using `seal_plans.py`; do not use it as a citation
rubber stamp. Resolve the actual Blender executable rather than assuming a version.

After establishing the reviewed entry plan and helper evidence:

```sh
python3 .agents/skills/running-blender/scripts/run_blender.py \
  --script "$PWD/python/blender_festival/run_asset.py" \
  --plan "$REVIEWED_ENTRY_PLAN" --timeout 900 -- "$SLUG"
```

The builder determines output locations. Reopen the saved source and inspect
front/rear/three-quarter views. Freeze a manifest containing exact GLB hashes,
builder/helper provenance, bounds, triangles, materials and reopened mesh counts.
Do not import while a model worker is still changing that asset's bytes.

## 3. Budget the actual exported geometry

Read both validators: passing Studio import does not guarantee native conversion.
Current native limits include 16 MiB GLB, 200,000 triangles, 32 materials,
16 images, 32 textures, 4096 pixels per image dimension, 32 million decoded pixels
in aggregate and 12 million accessor components. These are implementation limits,
not art targets or native runtime capacity claims.

Use opaque embedded PNGs or supported solid materials, finite static geometry,
normals and UV0 for textured meshes. Avoid unsupported extensions, external files,
skin/animation, extra material channels and transparency. Fail closed instead of
silently losing a requested feature.

Count exported vertices summed across primitives/nodes for each material, not
Blender's unique vertex count. UV seams, normal splits and optional backface
duplication matter. The decoder caps a material group at 32,768 vertices before
duplication; keep the final native count below 32,768 as the conservative authoring
target used by this family. Leave headroom. Reduce redundant tessellation before
removing reference-defining silhouettes or flowers.

```sh
bun .agents/skills/designing-jftse-props/scripts/verify-glbs.ts \
  "exports/blender-festival/$SLUG/$SLUG.glb"
```

Save the report privately. It checks the real import contract, preview leakage and
transformed bounds, not artistic fidelity or collision.

## 4. Upload, compose and save

Prefer the Studio's **Import Blender GLB** action for a single asset. The equivalent
local API accepts raw GLB bytes, not multipart form data:

```sh
STUDIO_URL="${STUDIO_URL:-http://127.0.0.1:4310}"
curl --fail-with-body --silent --show-error \
  -H 'Content-Type: model/gltf-binary' \
  --data-binary "@exports/blender-festival/$SLUG/$SLUG.glb" \
  "$STUDIO_URL/api/twinkle/import?name=$SLUG"
```

Use a URL-safe slug. Retain the returned JSON. Its `file` is
`Studio/Imported/<sha256>.glb`; never invent that identity or edit a registry file
in place. Reimporting changed bytes creates a new identity. Update only intended
placements, and retain old bytes while saved layouts still reference them.

Blender Z-up/front -Y becomes GLB Y-up/front +Z. Studio and the native converter
reflect GLB Z. Apply the placement's Y rotation and uniform scale after that
reflection. Do not reflect twice. Measure feet, endpoint positions and actual mesh
bounds rather than assuming the AABB center is the authored origin.

For this festival, `compose_blender_festival.py` accepts a fingerprinted baseline,
an object mapping slugs to actual upload responses, and an output layout path:

```sh
python3 python/compose_blender_festival.py "$BASELINE" "$ASSETS_JSON" "$LAYOUT"
curl --fail-with-body --silent --show-error -X PUT \
  -H 'Content-Type: application/json' --data-binary "@$LAYOUT" \
  "$STUDIO_URL/api/twinkle/draft?map=oktoberfest"
```

Only save after the requested composition and imports are ready. Reload Studio,
verify the saved design, and compare protected records. Geometry edits should be
single-writer; a separate layout worker can proceed against frozen contracts.

## 5. Inspect and export

Use the workspace-owned browser/hidden desktop, not the user's host desktop.
Inspect actual screenshots, including non-default views and both sides of props.
For side-by-side reference comparisons, match aspect, camera direction and scale.
If hiding editor chrome for a capture, disclose it and do not alter scene content.
Use real browser input for export; synthetic canvas events can fail pointer capture.
Check that a running server serves the current code before interpreting stale UI.

```sh
PYTHONPATH=python uv run --with pillow --with cryptography --with numpy \
  python -m unittest test_imported_native test_oktoberfest_native \
  test_twinkle_studio test_compose_blender_festival
bun test tests/importedProps.test.ts tests/twinkleDocument.test.ts
bun run typecheck
```

Exercise **Export stage ZIP** and inspect the actual result. API equivalent:

```sh
curl --fail-with-body --silent --show-error \
  -H 'Content-Type: application/json' --data-binary "@$LAYOUT" \
  "$STUDIO_URL/api/twinkle/export" -o "$PRIVATE_ZIP"
```

Validate ZIP CRC, parse every generated DAT, decode every TEX and verify opacity,
resolve expanded SET names, and compare placement transforms. Imported materials
are split into `Res/StageObj/Imported.res`; matching TEX bytes must also appear in
`Res/Stage/Tex010.res`. Compare original collision and unrelated archive members.
Report material-part draw overhead separately from the number of Studio objects.

Never convert earlier login/lobby success into a gameplay claim. Native loader
capacity, lighting, shader equivalence, collision response and performance need
explicitly authorized native tests. Imports remain nonblocking in this route.
Export verification does not authorize client installation, launch, commit or push.

## Handoff

Provide the saved layout plus registry location, editable sources, frozen manifest,
inspected in-context image, native ZIP/report, checks run and concrete limitations.
Keep source/resource hashes private where appropriate. State local versus pushed
status. Stop owned preview workspaces when finished; preserve evidence and backups.
