# Third-party notices and source provenance

## License scope

The adjacent [MIT License](LICENSE) covers original project code and original documentation. It does **not** replace the licenses or copyright of third-party content. In particular, source excerpts embedded in otherwise original catalog files retain their upstream rights.

| Material | Location | Treatment |
| --- | --- | --- |
| Supplied Blender API snapshot and web assets | `references/api/source-html.zip` | Original bytes and embedded attribution are retained |
| Extracted API text and inventory | `references/api/api.sqlite3` | Derived from the supplied snapshot; not relicensed as original project text |
| Source excerpts and inventory-derived cards | `references/catalog/catalog.json`, `symbols.json` | Upstream content remains subject to its own terms |
| Original helper code and editorial text | `scripts/`, `SKILL.md`, authored workflow descriptions | Project MIT terms, excluding incorporated third-party content |

## Blender documentation

The supplied HTML attributes copyright to **Blender Authors**. Its `documentation_options.js` identifies version `5.2`; root `objects.inv` names `Blender 5.2.1 LTS Python API`. The authoring input was a local snapshot named `blender_python_reference_5_2`, not a freshly downloaded release verified by this project.

The [manifest](references/api/manifest.json) records file paths, byte sizes and SHA-256 values. The [coverage report](references/api/coverage.json) records the inventory header and source scope. An exact upstream source commit/build hash is not established by the current record.

The upstream [Blender license page](https://www.blender.org/about/license/) describes GPL licensing and component-specific terms. The official repository's [API documentation configuration](https://github.com/blender/blender/blob/main/doc/python_api/conf.py) carries a `GPL-2.0-or-later` identifier. These are upstream provenance references, not a complete license determination for every file in this particular supplied HTML snapshot. Do not assign the Blender Manual's license to API documentation merely because both are hosted by Blender.

The archive contains a cached `Blender 5.3 Manual` inventory, not the complete Manual. Linked external pages and their licenses are not automatically included in this corpus.

## Embedded web assets

The following notices were observed in the supplied archive:

| Archive member | Embedded attribution or notice |
| --- | --- |
| `_static/clipboard.min.js` | MIT notice crediting Zeno Rocha |
| `_static/scripts/furo.js.LICENSE.txt` | gumshoejs v5.1.2, patched by `@pradyunsg`; copyright 2019 Chris Ferdinandi; MIT notice |
| `_static/styles/furo.css` | normalize.css v8.0.1; MIT notice |
| HTML footers | Blender Authors copyright and Furo attribution |

This table records observed notices, not an exhaustive component inventory. Other styles, scripts, fonts and images remain in the original archive with their existing content. Preserve embedded notices and obtain any required full license texts when preparing a distribution.

## Redistribution review

The current archive does not supply a complete per-component license record. Before publicly redistributing it or derived source text:

1. Identify the exact source snapshot and applicable terms for API text and bundled assets.
2. Add the required license texts, attribution and source information for those components.
3. Confirm that distribution of original and derived forms meets those terms; do not describe the whole corpus as MIT-licensed.
4. Retain the manifest and original embedded notices. Record any deliberate source changes in provenance and rebuild derived data when needed.

Adding a project MIT License does not complete these upstream checks. This notice deliberately preserves the remaining provenance gap rather than claiming blanket redistribution clearance.

## Attribution and affiliation

Blender and its documentation are created by Blender's contributors. This repository is an independent community project and is not endorsed by or affiliated with the Blender Foundation.
