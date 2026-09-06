# Source corpus and pre-query capability data

The authoring input was a local `blender_python_reference_5_2` snapshot, beginning at `index.html`. Collection followed local HTML links across whole pages, including navigation, and reconciled traversal against every source file. A main-article-only traversal would omit 25 shared-enum pages and the search page.

The complete dataset is preserved for offline access to all supplied API material. Task use begins with the [catalog overview](catalog/overview.md), relevant domain and selected cards. Do not open SQLite or draft Blender code before reading that context. Blender knowledge recalled by the model is not an admissible source.

## Source provenance

- 4,397 source files; 974,212,072 original bytes.
- 2,192 HTML pages, all reachable from `index.html` and indexed.
- 26,775 root Sphinx inventory entries: 24,381 Python symbols, 2,161 document entries and 233 labels. Python entries comprise 143 modules, 2,123 classes, 2,906 functions, 7,854 methods, 9,195 attributes and 2,160 data entries.
- HTML/JS identify API 5.2. Root `objects.inv` identifies project `Blender 5.2.1 LTS Python API`, version `5.2`. These labels do not establish a release date, release status, installed executable or build hash.
- A cached `Blender 5.3 Manual` intersphinx inventory is preserved but not merged into API search. An inventory is not the Manual's content.
- The source audit resolved all root inventory targets and local HTML fragments. The missing local target is the downloadable `blender_python_reference_5_2.zip` link on `index.html`, not an API page.
- External Manual, repository, extension and other website links are recorded, not imported as task evidence. The CLI workflow preserves a separately identified authoring-supplied command-line summary.

[api/coverage.json](api/coverage.json) records source counts/categories/gaps; [api/manifest.json](api/manifest.json) records file paths, sizes and SHA-256 values.

## The layer read before SQLite

The generated catalog has 112 authored feature routes across 18 domains, plus a discovery card for every one of the 2,192 source pages. A separate `catalog/symbols.json` preserves all 26,775 root inventory entries so names can be discovered without opening the API database. These counts describe coverage of the supplied source and authored routing, not every possible Blender workflow.

Each authored route contains translated intent aliases, a source-grounded capability summary, choice criteria, explicit limits, cited source excerpts/hashes and exact next queries. The route's `documented_route_runtime_unverified` status means the source describes the feature; it does not establish an implemented recipe or tested CLI support.

Each generated page card retains the source title, introductory source excerpt where available, source hashes and a direct query. `api_discovery_only` requires reading source before claiming behavior. `identifier_only` preserves a missing introductory behavioral description: a class name is not a substitute for that description. Domain assignments are navigation metadata. Aliases are language mappings and do not add Blender behavior.

Read the complete overview, then the relevant domain file. From the skill directory:

```sh
python3 scripts/features.py overview
python3 scripts/features.py match "text strip shadow"
python3 scripts/features.py show sequencer-text-drop-shadow
python3 scripts/features.py pages video-audio --limit 35
python3 scripts/features.py symbols TextStrip
```

These commands read plain Markdown/JSON and work without SQLite, Blender or network access. A match returns candidates to compare, not an automatic implementation verdict. When no route fits, inspect source-derived page cards. If the required fact is still absent, report `insufficient_skill_evidence`, identify it and stop dependent work. Do not translate an unknown request into guessed Blender jargon using model memory.

## Detailed evidence storage and task reads

`api/source-html.zip` preserves every supplied file unchanged, including HTML, images, styles/scripts, inventories, `.doctree` caches and the environment pickle. The tools never execute or unpickle these members. Blender Authors attribution remains in the original files.

`api/api.sqlite3` stores main-article text, inventory symbols, links and 33,696 anchor ranges. Formatting is adapted for terminal display. Original HTML remains available for source comparison when typography, a diagram or whitespace is unclear.

After selecting cards, create a plan and read the refs they supply:

```sh
python3 scripts/features.py plan --request "Text strip shadow" \
  --feature sequencer-text-drop-shadow --output /tmp/blender-plan.json
python3 scripts/docs.py read \
  bpy.types.TextStrip.html#bpy.types.TextStrip.use_shadow \
  --plan /tmp/blender-plan.json
```

`docs.py` records the canonical ref, source hash and displayed line ranges. Continue pagination until every cited passage is complete. Reading an exact anchor can keep a passage small. Follow links actually exposed by completed reads, or select additional catalog cards before expanding scope. Search results and identifier matches are discovery aids, not behavioral evidence. Bare `docs.py` commands are reserved for corpus maintenance/inspection and do not create task receipts.

FTS5 search is lexical and case-insensitive, with title weighting. Multiple terms default to AND; `--any` uses OR. Refine using terminology found in the selected source context. Categories include `bpy.types`, `bpy.ops`, `enum-items`, `guides`, `indices` and `modules`. `read` accepts an exact symbol, page or `page#anchor`; `related` reports main-article links and missing targets. Every Blender operation in the script must still be bound to supporting evidence as described in [evidence-workflow.md](evidence-workflow.md).

Maintenance examples:

```sh
python3 scripts/docs.py stats
python3 scripts/docs.py source _static/documentation_options.js
python3 scripts/docs.py verify
```

`verify` hashes the entire source archive against the manifest and checks database integrity/counts. To inspect HTML or images, extract into a chosen new directory with `python3 -m zipfile -e references/api/source-html.zip /absolute/path/new-reference-directory`. Original HTML retains external links/scripts; the SQLite lookup itself performs no network access. `source` reads UTF-8 archive members only. Archive inspection alone does not produce a task-plan receipt.

## Rebuild and review a replacement snapshot

Routine task use requires no rebuild. For a replacement local Sphinx snapshot, the corpus builder requires host Python and `lxml`:

```sh
python3 scripts/build_corpus.py /absolute/path/new-api-html \
  --output /absolute/path/new-corpus
```

Use a new output directory for review. The builder replaces its own generated artifacts if that destination already contains a corpus. It archives/hashes regular files, traverses from `index.html`, parses articles and signature/definition ranges, indexes root `objects.inv` and reports unresolved targets. It refuses source symlinks and destinations nested inside the source; it does not evaluate scripts or deserialize caches.

Review the replacement version, coverage and differences before placing it in a separate skill staging directory. Re-audit each affected authored `catalog/routes-*.json` claim against the new source. Then build the pre-query catalog for that staging skill:

```sh
python3 scripts/build_catalog.py --skill /absolute/path/staging/blender-cli
```

The catalog builder validates references, embeds source excerpts/hashes, regenerates all page cards, root symbol inventory, domain files and coverage. Reference existence and matching hashes do not establish semantic accuracy; reviewers must compare summaries and choice criteria with the actual passages. Rebuilding raw API data alone does not migrate recipes, helpers or authored feature claims.

Run source verification, skill validation and applicable tests against the staged replacement. New catalog data changes its fingerprint, invalidating prior plans; recreate task selection and reads rather than editing old hashes to force acceptance. Missing facts remain gaps until supported material has been incorporated into the skill with provenance.
