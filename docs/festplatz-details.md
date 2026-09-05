# Festplatz decoration pass

The private 45-placement composition is the input, not a replacement starting
map. Twelve additions make 57 placements: one fountain garland, four house
banners, three lane pennant spans, and four welcome flags. The original 45
records and the stock/festival source fingerprint remain unchanged.

## Art direction

The official [Schützen-Festzelt gallery](https://www.oktoberfest.de/bierzelte/grosse-zelte/schuetzen-festzelt)
shows repeated garlands, overhead fabric, timber and ordered communal seating.
Its beer-garden photograph (Sebastian Lehner, `07367`) was inspected as a visual
reference. No photograph or third-party texture is included in the models.

This smaller town uses blue and ivory cloth, green garlands, natural timber and
small pretzel emblems. Decoration marks destinations rather than filling every
empty patch. Market spans bracket the customer aisle; flags mark the entrance
and fountain approach. House banners attach to measured facade intersections,
not aggregate building bounds. The fountain ring fits the measured basin and
leaves its water and statue visible.

## Reproduce

Start the existing Studio with its private stock and festival fixture paths.
Then run from the repository root:

```sh
python python/compose_festplatz_details.py "$STUDIO_URL" \
  /private/oktoberfest-festplatz-layout.json /private/oktoberfest-detailed-layout.json
```

Import the resulting JSON in the Oktoberfest map. Running the composer on its
own output produces the same document. It refuses a changed source fingerprint.
The four new props are also independently editable in the original prop library.
`python/oktoberfest_models.py` generates all geometry, portable models and atlas.

Export stage ZIP includes the generated DAT/TEX files and collision additions.
Use the guarded fresh-copy installer, never overwrite a pristine client.
Hanging banners and fountain trim add no collision; flag poles add narrow solid
proxies, not a wall across their pennant spans.

## Limits

These are static decorations, not cloth simulation. The native exporter passes
structural round-trip checks; native loader behavior, materials and collision
response still require the separate authorized client-lab run.

Characters remain stock. The inspected chicken atlas has feathers/body/face but
no existing clothing regions. The judge atlas mixes clothing and feathers;
texture inspection alone does not establish UV ownership. Costumes need a
separate UV/skin-weight workflow and animated native validation. Static hats
placed above paused actors would not establish working animated costumes.

Stock scene geometry is retained, including the purple referee-chair canopy.
Court and Top are composition previews, not an assertion of native rendering
equivalence. Do not infer a decoding defect merely from an unusual silhouette.

## Experimental court and character study

`python/compose_festplatz_court.py input57.json output78.json` creates a separate
78-placement study from the detailed layout. It groups food stalls and tables,
adds fountain/court/net/judge trim, low corner planters and stock-derived guests.
The rejected primitive-built figures are not used in this composition. The
original court texture is unchanged. The private Codex reference guides grouping;
it is not an implemented screenshot or a source texture.

Ten stock-based Forest/Wine costume variants are experimental. Source DAT
and TEX hashes are allowlisted. Rig/animation payloads remain unchanged;
an extra material group carries clothing and hats. Jjijil uses his original
clothing surface with a bounded tuft refit beneath the hat. The experimental
Soldier costume was cancelled; retain the original `Object02/Soldier00.dat`.
Each garment piece copies weights from a nearby stock anchor. This is an
approximation, not an authored skinning solution: bind-pose rendering and a
parser round trip do not prove animated attachment, culling bounds or loader
compatibility. Do not replace the validated client control with this study
without a separate rollback-capable native test. No new clip meaning is claimed.

The atlas uses DXT1 with all ten mips. The parent lab confirmed that this encoding
reaches login, unlike the earlier uncompressed atlas. That startup check does
not establish in-game material resolution, character deformation or collision
behavior. Private source archives and the concept image are not redistributed
with source code.

The later tailoring pilot replaces the chicken's generic ellipsoid clothing
with a fitted crown, shaped feather, open-leg shorts and curved straps. The
strap samples come from radial intersections with the hash-locked stock body;
the original feather/body/face texture is unchanged. Clothing no longer uses
wood atlas cells. Net dressing replaces the two detached post banners with
blue/ivory tape fitted to the measured stock net sag and ribbons on its posts.
This trim adds no collision and does not change the court albedo.

The stock-derived chicken, Engineer accordionist and Soldier/Pirate/Jjijil
Codex sheets are private construction references, not completed 3D assets.
The remaining generic costumes and original humanoid models have been rejected
as final art and have not yet been rebuilt to match those character references.
Native testing has been stopped by the user. The confirmed 45-placement control
reached login, lobby and two-client waiting-room loading, not gameplay/material/
collision acceptance. This study makes no stronger native claim.

## Court perimeter revision

Run the perimeter composer on the saved court study, not on a new starting map:

```sh
curl --fail "$STUDIO_URL/api/twinkle/scene?map=twinkle" -o /private/stock-scene.json
python python/compose_festplatz_perimeter.py /private/saved-layout.json /private/stock-scene.json /private/perimeter-layout.json
```

Import `perimeter-layout.json` in the Oktoberfest Studio view. The composer is
idempotent and retains the festival source fingerprint. The latest design keeps
only the original cast: all stock NPCs and both original carriages are restored
from the pristine scene, including their exact transforms and animation metadata.
Existing costume choices on those original actors are retained: the chickens,
judge and Forest greeter keep their Oktoberfest variants. Added guests, helpers
and duplicate stock carriages are removed from the layout, not from the library.
Three festival vendor carts remain: pretzels by the tent, gingerbread at the
entrance, and food by the eastern tables, without an added crowd. The stock
court texture is unchanged. Further placement editing is left to the designer.

The private Codex/OpenAI composition study guides the arrangement, not the
coordinates or asset identities. The main maypole marks the tent approach. A
smaller single-crown welcome pole marks the entrance. The delivery wagon uses
the tent-side service space. This arrangement retains the original Soldier and
both stock carts in place alongside the three festival vendors. It follows the
concept's service-area grouping without recreating its populated scene.

The net keeps its original mesh beneath a narrow diamond-pattern binding.
Small wreaths and pretzel knots attach to the posts. Short chair valances expose
the original frame and steps. Four flat blue-white corner inlays replace the
detached ground crests; the original playing lines remain unchanged. None of
these trim meshes adds collision. The two maypole models have narrow pole
collision proxies. Ribbons remain static.

Terrain inspection rejected trial placements on the plaza steps. New scenery
heights include model-space foot offsets on the outer paving; original carriages
retain their authoritative stock transforms. Studio previews and exported archive round trips are not native
gameplay tests. Restored carriage and NPC animation, material resolution and
in-game collision response remain unverified. The generated image also invents
different carts and a replacement judge chair; those inventions are not part
of this revision.
