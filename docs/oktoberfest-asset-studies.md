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
