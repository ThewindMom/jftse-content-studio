# Oktoberfest asset studies — Blender handoff

These are editable modeling studies, not approved final Fantasy Tennis art.
The user's target is the supplied densely decorated Twinkle Town court reference,
while preserving the original game's visual identity and clear playing surface.
The user rejected the procedural props as foreign-looking. Passing export tests
does not resolve that artistic criticism.

## Source ownership

`python/oktoberfest_assets/` gives each detailed prop its own builder and collision
definition: `festzelt`, `pretzel_stand`, `food_stand`, `gingerbread_stand`,
`beer_garden`, `maypole`, `festival_arch`, `barrel_display`, and `pretzel_display`.
`common.py` contains shared cloth, diamond panels and small decorations.
The pretzel kiosk reuses the Festzelt pavilion structure with its own merchandise.
`python/oktoberfest_models.py` dispatches to these builders and owns the shared
mesh primitives, atlas, GLB/OBJ packaging and remaining earlier props.

The Festzelt is now a peaked serving kiosk, not the earlier rectangular hall.
This follows the user's subsequent kiosk reference. The nine study assets are
available in the library. Existing map transforms are unchanged; the two new
display assets are not automatically added to the saved layout.

## Stock evidence

Run the bounded static reader against private pristine fixtures:

```sh
PYTHONPATH=python uv run --with pillow --with cryptography python \
  python/audit_twinkle_style.py /private/fixtures .amp/in/artifacts/stock-style-audit
```

Required inputs: `SV_All.dat`, `Tex009.res`, `Tex010.res`. The output records exact
resource hashes, primitive counts, UV bounds and material texture channels,
and creates a private decoded texture contact sheet. Do not commit the output.

Observed material primitives in the supplied pristine `SV_All.dat`:

| Albedo | Vertices | Triangles | Texture dimensions |
| --- | ---: | ---: | --- |
| SV_Stall01b_B | 116 | 144 | 256 × 512 |
| SV_Stall01a_B | 2,122 | 1,318 | 512 × 512 |
| SV_Tent00_A | 322 | 346 | 512 × 512 |
| SV_Tent01_A | 312 | 310 | 512 × 512 |

These are material primitives, not necessarily complete individual props. Their
bounds can span several pieces. Do not compare these counts with an entire
generated kiosk as if they were equivalent assets.

All four also reference `SV_Stall00_all_B_LM` through a second texture channel.
The inspected albedos contain purposeful UV islands, broad painted fabric folds,
wood end-grain, edge shading and integrated lantern/flower details. The stock
rendering pipeline therefore cannot be characterized as flat color on geometry.

## Design consequences and remaining gaps

- Use geometry for silhouette and construction; do not model every salt grain,
  flower petal and fastener as a dense rounded solid. The study already reduces
  pretzel salt and small Festzelt decorations to simpler geometry.
- Preserve chunky supports and deliberately shaped canvas. Remove accidental
  frame protrusions rather than covering them with more decoration.
- The shared 16-swatch procedural atlas remains a limitation. The studies have
  warmer timber, quieter grain and less cyan blue, but this is not equivalent
  to stock-style per-part UV painting or stock baked lightmaps.
- Blender work should prioritize silhouette, UV islands, painted highlights,
  cloth folds and contact shading before increasing detail density.
- Several study components still have thin cloth, repeated construction and
  simplified merchandise. Do not describe them as matching the supplied renders.
- Keep the burgundy court and original line geometry. Do not automatically
  reproduce tight clearances or extra people invented by reference images.

## Portable reproduction

```sh
PYTHONPATH=python uv run --with pillow python -c \
  'from pathlib import Path; from oktoberfest_models import prepare_originals; prepare_originals(Path(".amp/tmp/original-models"))'
```

The ZIP contains separately named GLB and OBJ files with the atlas. Import these
as construction studies in Blender, not as finished meshes to merely re-export.
Arbitrary edited Blender GLBs are not accepted by the current bounded native
writer. That importer/conversion boundary needs implementation before claiming
that Blender edits flow through the current one-click client installer.

## Verification and non-claims

Python checks cover finite geometry, nondegenerate triangles, normal/UV data,
u16 vertex/index bounds, collision dimensions, portable packaging and bounded
native round trips. Studio inspection covers the nine props and the saved map.
These checks do not establish artistic parity, native gameplay visibility,
animated attachment or collision response.

Current native atlas output is mipmapped DXT1. Do not revive older notes claiming
uncompressed A8R8G8B8 support: the parent lab disproved that at startup. The prior
45-placement DXT1 control reached login, lobby and two-client waiting-room
loading, not gameplay acceptance. Native client testing remains stopped by the
user. No client execution or installation is part of this handoff.

## Blender → Studio experiment

The beer vendor cart now has a genuine Blender source and a separate static GLB
import path. This path supports Studio placement and layout persistence, **not
native DAT/TEX conversion or collision**. Layouts containing imported placements
are rejected by native export/install, even if those placements are hidden.

1. Open `exports/blender-beer-cart/beer-cart.blend` in Blender. The named cart
   components and packed paint images are editable; preview objects are separate.
2. Export selected cart components as GLB with materials and embedded PNG images,
   Y-up, without cameras, lights, animations, skins, morphs or compression.
3. In the Studio prop library, click **Import Blender GLB** and select the file.
   Select its library entry to add a placement, adjust its transform, then click
   **Save layout**. Reloading retains both the imported asset and the placement.
4. Back up `exports/imported-props/` together with the layout JSON. The JSON
   contains asset references, not meshes. Changed GLBs receive new hash identities;
   importing a revision does not automatically replace existing placements.

The import contract allows up to 16 MiB, 200,000 triangles, 600,000 vertices and
2,000 scene nodes, with additional validation-work limits. Textures must be
embedded PNGs no larger than 4096 × 4096. Only the unlit and emissive-strength
material extensions are supported. Studio uses approximate PBR preview lighting;
this is not the original game's DX9 shader or baked-lightmap pipeline.

### Stock-derived painting, not a generic palette

`python/audit_stock_cart.py` reads private stock carriage and stall DAT/TEX
resources and produces material/UV measurements, texture sheets and UV overlays.
`python/prepare_beer_cart_paint.py` checks exact source-member SHA-256 hashes before
extracting five inspected paint islands. It records crop rectangles, output
hashes and transformations in private `provenance.json`:

| Source | Reused paint |
| --- | --- |
| `Carriage00a.tex` | Warm timber panel and folded canvas |
| `Carriage00c.tex` | Tall wood-plank island |
| `SV_Stall01a_B.tex` | Stall timber |
| `SV_Stall01b_B.tex` | Painted canopy stripes, rose hue remapped to blue |

The stock carriage is a tall skinned coach with an animal, not the reference's
two-wheel vendor cart. Its cart-only bounds are approximately 28 × 46 × 61.2 game
units. Its painted 512 × 512 atlases have no second UV channel in this audit;
the stall/tent material groups use a shared lightmap. Preserve those distinctions
instead of assuming that every game prop uses the same shading setup.

The new geometry uses stock paint crops, but still has simplified UV projection,
thin canopy surfaces and more separate detail meshes than desirable for final
game art. Purposeful per-part UV painting, contact shading, silhouette review
alongside stock props and native material tests remain necessary. Reusing stock
pixels alone does not establish near-100% visual parity.

### Reproduction and inspected checkpoint

```sh
PYTHONPATH=python uv run --with pillow --with cryptography python \
  python/audit_stock_cart.py
PYTHONPATH=python uv run --with pillow python python/prepare_beer_cart_paint.py
```

The default stock root is `../JFTSE/.jftse-client-linux/client`; the paint extractor
also accepts `--stock-root`. Follow the installed `running-blender` skill to read
the API evidence and seal/run `python/blender_beer_cart.py`. This workspace's
recorded plan is `.amp/tmp/beer-cart/stock-paint-plan.json`. The builder saves
`beer-cart.blend`, `beer-cart.glb` and `preview.png` in `exports/blender-beer-cart/`.
Stock-derived images, GLBs, blend files and decoded audit output remain private;
do not commit them with the source scripts.

The refined experiment has 6,417 triangles, 15 materials and 147 mesh parts
(previously 7,823 triangles and 168 parts). Refinement replaces strip-sampled UVs
with bounded paint islands, gives the canopy an arc-based unwrap and closed
canvas ends, thickens timber supports/spokes and reduces scallops and bunting.
Rose-to-blue recoloring is continuous so stripe highlights do not become white
patches. Stock-painted surfaces use black diffuse plus texture emission at 0.8
to approximate the stock preview's painted shading without a second orange light
wash; this is an art-directed preview choice, not recovered native shader logic.
Metal is matte and lantern emission is reduced. The revised GLB was checked for
bounded UVs, paint material factors and both canopy end meshes, then inspected
beside the stock carriage and court in Studio.
The saved Oktoberfest layout adds one `Blender beer cart` at `[132, -7, 152]`,
rotation 0, scale 12. All 69 prior placements are unchanged. The Studio preview
was inspected after importing and reloading the saved layout. No native client
was installed or launched; this is a pipeline and art study, not final acceptance.

## Coordinated Blender festival family

The next checkpoint adds nine individually authored Blender props and variants.
Each builder is in `python/blender_festival/`; `common.py`, `stall.py` and
`picnic.py` share construction and painted-material helpers. The existing beer
cart remains separate and unchanged. `references.json` identifies the supplied
construction images, including the overall court composition target.

| Asset slug | Triangles | Studio use |
| --- | ---: | --- |
| `pretzel-stand` | 11,386 | Replaces the festival pretzel carriage |
| `food-stand` | 6,232 | Replaces the festival food carriage |
| `gingerbread-stand` | 17,926 | Replaces the festival gingerbread carriage |
| `gingerbread-heart` | 13,768 | Alternate in the library |
| `beer-garden` | 7,482 | Two existing table slots |
| `beer-garden-festive` | 8,718 | Two existing table slots |
| `barrel-display` | 6,765 | Library display, not an extra saved placement |
| `maypole` | 6,419 | Existing large and small maypole slots |
| `festival-arch` | 11,881 | Existing entrance slot |

Private outputs are in `exports/blender-festival/<slug>/`: editable `.blend`,
embedded-texture `.glb`, three rendered views, model report and evidence plan.
`exports/blender-festival/manifest.json` records exact GLB hashes and measured
bounds. All nine saved Blender files were reopened. Their exports have ground at
Y=0, front toward +Z, and three to six embedded PNG images each.

The family uses stock timber/canvas paint with a derived blue/cream diamond cloth.
The cloth provenance is beside the earlier cart paint provenance. Refinement
corrected crossed pretzel dough, local beam UV islands, arc-length table drapes,
food-rail mounts, ground origins and maypole ribbon widths. Small flowers, icing,
beer pictograms and sausage ends remain simplified; signs have no lettering.

The saved layout still has 70 placements. Ten festival records changed; the other
60 complete records are identical to the pre-import snapshot. Both original
carriages, Soldier, costumes, barrel wagon, court and lines remain untouched.
Replacement origins remain at the manual anchors. Stalls face inward, table
widths match their prior slots, and the two maypoles retain unequal heights.
The entrance is widened to 64 game units to read more clearly against the court.
This is a composition checkpoint, not a match for all density and dressing in
the final court concept.

Verification used the real GLB import boundary, transformed vertex bounds,
front/rear/three-quarter renders, individual Studio views and a saved-layout
reload. Both unused variants were temporarily placed for display inspection and
discarded without saving. The final court view shows the complete entrance and
no new props on the playing surface. Private evidence is in `.amp/tmp/festival/`,
including `placement-changes.json`, `glb-validation.json`,
`studio-detail-sheet.jpg`, `studio-extra-sheet.jpg` and `festival-court-final.jpg`.
The import/layout tests pass: 14 tests, 68 assertions. TypeScript checking passes.

The project skill `.agents/skills/designing-jftse-props/SKILL.md` documents the
stock audit, design process, Blender evidence workflow, Studio composition and
acceptance checks. Run its bundled `scripts/verify-glbs.ts` before import. Follow
`running-blender` to review and bind source operations before rerunning a builder;
the private plans are under `.amp/tmp/festival/`. Paint extracts and generated
models stay private and are not included in tracked source.

At this checkpoint, native conversion was blocked. The following dense-dressing
checkpoint supersedes that restriction; native-client acceptance remains unverified.

## Dense dressing and native export

Nine additional Blender assets provide connected fences, vertical banners, flower
barrels, hay bales, three chalkboard variants, suspended pennants and a leafy gate.
Their individual builders and editable sources follow the same stock-paint workflow.
The final fence is 1.6 times its initial height, with unchanged 2.8-unit post pitch.
Private hashes and render evidence are in `exports/blender-festival/dressing-manifest.json`.

`python/compose_blender_festival.py` reproducibly composes the saved baseline with
actual registry identities. The resulting layout contains 119 placements, including
62 imported placements. Protected stock records remain unchanged. The Festival
camera frames the gate at the far end, with inward-facing stalls, connected fences
and clustered perimeter dressing. Imported bounds stay outside the playing surface.
This is a denser interpretation of the reference, not a claim of exact art parity.

The Studio export action now converts supported static GLBs through
`python/imported_native.py`, using the server's `JFTSE_IMPORTED_PROPS` registry.
It verifies SHA-256 identities, transforms hierarchy geometry and normals, reflects
Z with corrected winding, and splits materials into stock-template DATs. Opaque
paint is baked into DXT1 TEX mip chains and registered in Tex010. Unsupported
features and over-budget inputs fail closed; overlapping buffer views share memory.

The saved layout exports to 712 native placements: 669 imported material parts
from 18 unique imports, backed by 196 DATs and 196 TEXs. Every generated DAT was
parsed and every TEX decoded; SET names and texture registration bytes resolve.
Original collision geometry and unrelated archive members are preserved. Existing
legacy collision proxies remain, but imported props add no blocking collision.

Private evidence is in `.amp/tmp/dense-festival/`: `exported-final.jpg`,
`native-validation.json` and the native ZIP. The deliverable copy is
`exports/oktoberfest-native.zip`, alongside the saved `oktoberfest-layout.json`.
Back up `exports/imported-props/` with that layout; JSON alone contains no meshes.

No native client was installed or launched. Native loader limits, 712-part draw
cost, lighting, specular and bloom equivalence remain unverified. Emission is baked
to SDR color and scalar specularity is flattened, not reproduced as a DX9 shader.

## Curved enclosure and composed prop groups

The next refinement replaces rigid silhouettes rather than increasing prop count.
`reference_shapes.py` supplies softened joinery, substantial gathered drapes,
rounded foliage and three-opening pretzel crests. The gate is broader and lower;
the pretzel canopy billows. Dedicated blue/cream paint carries broad fold shading
so emission-treated materials retain volume under the unchanged Studio lights.

Three genuinely curved Blender models now shape the enclosure: quarter-circle
corners, a five-bay foreground sweep, and a three-bay inward bow around the stock
fountain. Their ground origins and exact post-center contracts are recorded in
`exports/blender-festival/redesign-manifest.json`. Layout tests verify corner
connections, fountain centerline clearance and pennant endpoints. These are
static mesh exports, not runtime curves or added collision.

The dressing is composed into small groups inside the enclosure: corner flower
barrels and hay, chalkboards beside the stalls and judge-side walk, inset foreground
banners, and low barrel displays between bouquets along the front. Ground heights
were checked against the actual road triangles. Both stock carriage records and
their openings remain intact; imported bounds remain outside the playing rectangle.
The Festival camera frames the result; comparison captures hide only editor chrome.

The layout still contains 119 placements, now with 76 imported placements using
21 distinct GLBs. Native export produces 734 SET placements and 232 DAT/TEX pairs.
Private current evidence is in `.amp/tmp/curved-festival/`, including
`clearance.json`, `native-validation.json` and `grouped-final.jpg`. The exported
ZIP remains `exports/oktoberfest-native.zip`. Native rendering/performance and
shader equivalence are still unverified; no client installation or launch occurred.
