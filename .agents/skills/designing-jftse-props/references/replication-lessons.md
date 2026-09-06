# Reference replication: failures and corrections

Use these lessons before another modeling or composition pass. They come from the
Oktoberfest studies, not a claim that every JFTSE asset uses the same construction.

## Establish what similarity means

Matching the object inventory is not matching the design. Our first collection
was too sparse; adding rows of props made it dense but still rigid. The reference
depended on a curved enclosure, deep fabric, rounded flowers and grouped details.

Before building a family, write a short comparison with these columns:

| Read from reference | Measure in current scene | Change at its owner |
| --- | --- | --- |
| Enclosure silhouette and open passages | Fence endpoints, curvature and gaps | Curve builder and composition |
| Fabric volume and broad light/dark folds | Swag depth and scene-scale shading | Cloth mesh, UVs and paint |
| Gate and canopy proportions | Post pitch, crown height and roof outline | Individual builder |
| Rounded flower masses | Bouquet outline and repetition | Flower geometry and grouping |
| Merchandise and crests | Recognizability at court-view size | Identity geometry and contrast |
| Dense but readable perimeter | Negative space, grounding and clearance | Saved layout |

Prototype one foreground fence/drape/bouquet section beside stock geometry before
batch generation. Prioritize silhouette, proportion and negative space over small
detail. A generated concept image guides design; it is not proof of consistent
geometry, recoverable native lighting or achievable pixel-identical framing.

Keep original court/lines, Soldier, both original carriages and costumes unless
the user changes that constraint. Do not add crowds to conceal empty composition.
Fix layout and geometry before adjusting the camera. Compare the same aspect,
direction and renderer; disclose editor-chrome removal instead of presenting a
different crop or lighting setup as an asset improvement.

## Learn the paint, not a generic “low-poly” label

Decoded stock evidence showed purposeful timber/canvas islands, folds, grain,
edge highlights and shadows. A small swatch atlas did not reproduce that language.
A stage material primitive's triangle count is not a whole-prop budget. Reusing
old procedural meshes and exporting them through Blender does not redesign them.

| Observed failure | Correction |
| --- | --- |
| Diagonal beams sampled skinny texture strips | Local per-face UV islands, grain along each beam's length, meaningful end faces |
| Diamonds stretched down curved table cloth | Arc-length fabric UVs rather than world or planar projection |
| Blue recoloring left pale holes in stripe highlights | Continuous chroma remapping while retaining stock fold luminance; inspect pixels as well as previews |
| Curved swags still looked like flat stripes | Broad painted highlight, trough and hem shadow on both blue and cream; emission does not create diffuse fold shading |
| Back-side cloth and flowers became almost black | Diagnose the front-only preview lights and solid diffuse materials; retain the lights, use supported painted cloth and bounded ambient contribution for the new flower family |

The tested paint/emission setup approximates Studio. Do not call it the recovered
DX9 shader or apply it indiscriminately to all assets. Preserve existing stock
paint when authoring dedicated variants, and record source hashes/crops plus the
derived texture hash. Front/rear tests must use the same lights; rear-facing
flowers need outward placement, not merely a dark leafy reverse.

## Model the reference-defining shapes

- **Real curves:** rotating straight bays makes a polygon, not a circular rail.
  Author rail and cloth geometry along the arc. Specify radius, apex origin,
  endpoint positions and tangents, bay count, post height and orientation.
  Test rail vertices against the intended circle and transformed joints in Studio.
- **Natural proportions:** whole-Z fence stretching also stretched medallions and
  flowers. Rebuild post/rail height and swag depth without distorting ornaments.
- **Fabric:** deep layered U-shaped swags need actual front/rear surfaces, readable
  overlap and broad paint. A shallow ribbon or additional triangle count alone
  cannot provide the same volume.
- **Flowers:** rounded, smoothly shaded petals and clustered trailing greens read
  better than spear-like leaf fans. Vary cluster size without losing family colors.
- **Pretzel identity:** disconnected crossed tails collapsed the lower opening,
  making the crest read like infinity. Join the tails to a wider lower lobe and
  thin the dough enough to retain three enclosed holes. Inspect both a close-up
  and the court-view result; increase dough contrast when necessary.
- **Gate and stall:** a broader, lower gate and billowed canopy with larger checks
  matched better than a tall isolated gate and sharp tent peak. Match the outline
  before adding more hanging details.

Use post-center pitch, not foliage AABB width, to connect fence modules. The
tested straight pitch is 2.8 Blender units. Quarter-corner and custom-run contracts
live in `exports/blender-festival/redesign-manifest.json`; read the current values
instead of reconstructing them from rounded screenshots. GLB front is +Z, but
Studio/native reflect Z before placement transforms. Do not compensate twice.

## Compose groups, not a uniform scatter

Use a main bouquet with low hay/barrels and an outward-readable sign to fill a
gap. Alternate larger groups with quiet passages. Keep props within the intended
camera view without making every interval identical. Preserve the arch opening,
playing area and stock landmarks. More placements cannot repair thin cloth.

Ground against actual road triangles. In this scene the raised court-side paving
is around Y=0 while the lower market is around Y=-7.35. A correct asset origin does
not determine the correct placement elevation. Check feet and lower mesh bounds.

Court-rectangle clearance alone missed the fountain basin and carriage horses.
Measure those stock bodies too. The fountain needed a custom bow around its basin;
a chalkboard needed moving after a carriage-AABB check. Bounds checks are useful
for finding candidates, but inspect visible intersections and walkable passages.

## Keep revisions and evidence distinct

Freeze exact per-asset hashes before import. Keep modeling and composition under
disjoint ownership; never import a file while its owner is rerendering it. Refresh
the manifest after any output change and update intended placement identities.
An old GLB with the same filename is still an old asset.

Budget exported vertices per material, including seams and backface duplication.
For the long foreground run, reducing cloth tessellation preserved the silhouette
and flowers while staying under the conservative native budget. Do not reduce the
reference-defining content before looking for redundant geometry.

These are separate acceptance gates:

1. **Editable source:** saved blends reopen with packed images and expected meshes.
2. **Interchange:** the real Studio inspector accepts the exact GLB bytes.
3. **Art:** inspected front/rear and stock-scene images match the intended design.
4. **Composition:** saved layout reloads, protected records survive, grounding and
   clearance are checked in context.
5. **Native files:** generated DAT geometry roundtrips, TEX decodes, SET references
   resolve and unrelated stock resources/collision remain intact.
6. **Runtime:** an authorized native-client test establishes loader, shading,
   gameplay and performance behavior for the actual map.

Material splitting multiplies native placements and draw overhead. ZIP success,
unit tests or a login/lobby visit do not certify that cost, native shader parity
or gameplay acceptance. Imported decorations remain nonblocking in this bridge.
Report which gates passed, and leave runtime claims unverified until exercised.
