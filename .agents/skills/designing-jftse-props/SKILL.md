---
name: designing-jftse-props
description: "Designs Fantasy Tennis props in Blender from original JFTSE client asset evidence and imports them into Content Studio. Use for Oktoberfest stalls, carts, furniture, banners, arches, map dressing, or fixing assets that look foreign to the game."
---

# Designing JFTSE props

Build recognizable, editable props that belong beside the original game assets.
Treat successful export, artistic similarity and native compatibility as separate
acceptance criteria. Never substitute one for another.

## Start with the requested scene

1. Read the user's individual construction references and overall court reference.
   Enumerate every supplied asset, including alternate versions. Identify duplicates
   explicitly; do not silently omit a reference or treat every image as a new placement.
2. Read `docs/oktoberfest-asset-studies.md` and the current saved layout. Record the
   source fingerprint, object IDs and transforms before changing anything.
3. Use the overall court reference to set the shared design language: burgundy
   playing surface, blue/cream festival fabric, warm painted timber, restrained
   dark metal, flowers and readable perimeter silhouettes. A collection of isolated
   product renders does not establish a coherent map.
4. Preserve protected scene elements. For the established Oktoberfest design these
   include court/line geometry, original Soldier, both original carriages and the
   original character costumes. Do not add crowds or move stock actors merely to
   match an invented detail in a concept render. Current user instructions take
   precedence over this historical baseline.

## Establish stock evidence before modeling

Run these from the repository root against private pristine client resources:

```sh
PYTHONPATH=python uv run --with pillow --with cryptography python python/audit_stock_cart.py
PYTHONPATH=python uv run --with pillow python python/prepare_beer_cart_paint.py
```

The paint extractor accepts `--stock-root`; its default is the sibling JFTSE
client directory. The earlier bounded stage audit is `python/audit_twinkle_style.py`.
Read their input contracts before using different fixtures.

- Inspect decoded texture sheets, UV overlays, material channels, mesh bounds and
  silhouettes. Record exact archive/member hashes and crop rectangles for reused
  paint. A filename alone is not provenance.
- `Carriage00a/c` provide painted timber/canvas evidence. `SV_Stall01a_B` provides
  stall timber and `SV_Stall01b_B` painted stripe cloth. The carriage includes an
  animal and rig; it is not a ready-made vendor cart.
- Stage stall/tent primitives can share a second lightmap channel; audited carriage
  parts do not all use that setup. Do not infer one universal client shader.
- Count comparable objects. A material primitive in a combined stage mesh is not
  necessarily a whole prop. Polygon count alone is not the game's design language.
- Keep source archives pristine. Do not mistake authored festival Tex009/Tex010
  copies for pristine stock. Store extracted images and model outputs privately in
  ignored `.amp/tmp/` and `exports/`, never in the skill or tracked source.

## Design from silhouette to paint

Use the concept image for construction and stock assets for surface treatment.
Match these in order:

1. **Silhouette and proportions:** roof pitch/arch, counter height, wheel size,
   supports and clearance. The prop must read from the approximate match camera,
   not only from a close-up product camera.
2. **Construction:** supports meet beams; wheels share an axle; hoops follow the
   barrel axis; lanterns have hangers; fabric rests on its frame. Check rear and
   underside views. Close exposed canopy ends when the design calls for them.
3. **Large material areas:** timber panels, canvas and dark hardware. Prefer broad
   painted islands to repeated tiny swatches. Preserve painted folds, grain,
   edge highlights and contact shadows rather than burying them under PBR lighting.
4. **Identity details:** pretzel/heart signs, recognizable merchandise, checked
   cloth, ribbons and flowers. Do not simplify away the feature that distinguishes
   a food stall from a gingerbread stall.
5. **Small detail:** spend geometry on the visible outline. Use paint for small
   seams, grain, icing and hardware where possible. Reduce density only after
   checking that the reference's character and hierarchy survive.

Do not equate stock style with generic low-poly geometry, glossy orange wood,
neon-blue fabric, cylindrical lantern cages or an arbitrary color-swatch atlas.
Keep blue/cream values consistent across the entire asset family.

### UV and material rules learned from the cart

- Normalize meaningful faces into the intended paint island. Mapping every piece
  using absolute object coordinates samples narrow strips and stretches the paint.
- Follow the longest timber axis for grain, but do not collapse side/end-face UVs.
  Give curved canvas arc-based coordinates rather than mirrored planar projection.
- Remap rose cloth to blue continuously. A hard saturation threshold can turn blue
  stripe highlights into conspicuous white patches. Preserve source light/dark folds.
- Diamond patterns should follow the cloth and retain painted fold shading; a flat
  procedural checker is not equivalent to the reference's fabric.
- Avoid lighting the painted highlights twice. The refined cart uses a black
  diffuse surface plus its stock paint in the emission channel at 0.8, roughness 1,
  metallic 0, with reduced lantern emission. This is a measured Studio approximation,
  **not recovered native shader behavior** and not a universal recipe for every prop.
- Compare changes under the same camera and renderer. Do not make an imported prop
  look integrated by quietly recoloring the stock scene or changing all its lights.

## Build genuinely in Blender

Load `running-blender` before writing Blender code. Its supplied API catalog,
source reads, runtime probes and sealed evidence plan are required. This design
skill supplies artistic decisions, not undocumented Blender API knowledge.

- Read `python/blender_beer_cart.py` for the cart experiment and
  `python/blender_festival/` for the coordinated family. `common.py` owns mesh,
  paint and export helpers; individual builders own each prop's construction.
  `references.json` records the supplied construction references.
- Give each prop or deliberate variant its own builder and editable `.blend` file.
  Shared material and construction helpers are appropriate; cloning the same kiosk
  and changing its name is not a complete design for a different reference.
- Name components by role. Keep preview ground, camera and lights out of the asset
  selection. Pack the image resources needed to reopen the source.
- Save a preview PNG and a static GLB with embedded PNG textures alongside the source.
  Follow the live import contract in `server/importedProps.ts`: it deliberately does
  not accept arbitrary glTF features or external texture paths.
- Reopen important saved sources and inspect outputs. A `.blend` suffix or successful
  exporter process does not prove that the file contains the requested model.
- The festival builders use Blender Z-up, ground at Z=0, and front toward -Y.
  Exported GLBs use Y-up and front toward +Z. Normalize the ground using actual
  vertices, and account for the front-axis convention when replacing older assets.
- Use arc-length UVs for bent fabric so diamonds keep their proportions. Use
  local per-face UV islands for diagonal timber, rather than world projection.

## Import and compose in Studio

Use **Import Blender GLB**, then select the imported library entry to place it.
The equivalent local API is `POST /api/twinkle/import?name=...` with raw GLB bytes.
The returned identity is content-addressed; use that response rather than inventing
asset paths. Save via the Studio layout API/UI, not by rewriting a fingerprint.

- Layout JSON contains references, not model bytes. Back up `exports/imported-props/`
  with the saved layout. Changed GLBs get new identities; imports do not silently
  replace existing placements.
- Replace only the intended asset identity and explicitly approved transforms.
  Compare whole placement records before/after. Blender units and stock game units
  differ: measure bounds and match the intended footprint, not an arbitrary default
  scale. Preserve the unequal maypoles and clear passage through an entrance arch.
- Put unused variants in the library rather than placing duplicates on the court.
- Review the family together: canopy heights, fabric pattern scale, wood values,
  visual density, sightlines, court clearance and repetition. Use the overall
  reference to guide composition, not to justify rearranging unrelated objects.
- Native export/install is blocked while imported placements remain, even hidden.
  GLB import currently proves Studio display/save, not DAT/TEX conversion, collision,
  animation or native-client acceptance. Never bypass that guard to claim completion.

## Acceptance and handoff

Run the bundled checker from the repository root before importing:

```sh
bun .agents/skills/designing-jftse-props/scripts/verify-glbs.ts exports/blender-festival/*/*.glb
bun test tests/importedProps.test.ts tests/twinkleDocument.test.ts
```

The checker applies the real Studio import contract, rejects named preview objects
and measures transformed mesh vertices instead of trusting accessor bounds. Save
its JSON report privately with the render evidence. It does not judge art quality.

For every asset, record:

- Reference and role; source builder, `.blend`, GLB and evidence-plan paths.
- Paint provenance, exported bounds, triangle count and materials.
- Checks for finite positions, valid indices/UVs, embedded textures, correct scene
  selection and absence of preview cameras/lights/geometry in the GLB.
- Inspected close-up/front/rear views and at least one in-context Studio view.
  Fix obvious gaps, intersections, UV streaks or unreadable identity details, then
  inspect a new render. A contact sheet must be readable enough to assess each prop.
- Saved-layout reload result and a comparison of protected placements/transforms.

Run the current import/layout tests and relevant model checks. Inspect screenshots
with `view_media`; taking a screenshot alone verifies nothing. Prefer actual
browser input/DOM button activation to synthetic canvas pointer events, which can
trigger pointer-capture errors. Selection gizmos are not model geometry; disclose
them if shown, or capture without them using a supported interaction.

Show an inspected representative render or before/after comparison in the handoff.
State what changed and what remains unproven. Do not label a style study “100% game
matched,” equate unit tests with art approval, or stop at export success while the
render still visibly contradicts the reference.
