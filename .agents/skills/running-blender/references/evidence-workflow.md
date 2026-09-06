# Evidence plan for Blender-specific decisions

The catalog provides the initial Blender context. It must be read before API lookup. Ordinary language interpretation and Python programming are available reasoning tools; recalled Blender facts are not an evidence source. Every chosen feature must have a source-backed description or remain explicitly a discovery-only item. A strict traceability workflow cannot remove knowledge from model weights; it can reject unsupported claims and task execution without recorded evidence.

## Where facts come from

| Fact | Admissible source | What it does not prove |
|---|---|---|
| What a feature is for | Catalog evidence with a source excerpt and precise ref | A name alone does not establish purpose |
| API signature, owner, property type/range | Full relevant passage in packaged API | Runtime availability or undocumented effects |
| Which value a user wants | User request or a stated artistic choice | That a Blender enum/property exists |
| Runtime version, available RNA, dynamic values | Recorded output of the bundled probe/authorized source-driven inspection | A complete workflow or render appearance |
| Result correctness | Task-specific output inspection, fresh reopen, actual render | General support for every feature |

The old broad capability map is replaced by the generated overview/domain cards. Earlier examples in repository reports are historical evidence and are not approved recipes for new tasks.

## Discovery before database

`features.py overview`, `match`, `show`, `pages` and `symbols` read only bundled plain files. `match` returns candidates with matched aliases and choice criteria, not an automatic implementation verdict. No match means `insufficient_skill_evidence`; inspect the relevant domain catalog or request the missing source/intent details. A `pages` entry supplies exact source wording, so the agent can discover unfamiliar APIs without remembering their names.

An authored route has a Vietnamese/English label, aliases, capability summary, `choose_when`, `do_not_assume`, cited facts and `next_queries`. All source HTML pages also have generated `api:...` cards. This provides full source discovery coverage while distinguishing pages whose intros offer no sufficient behavioral description. Do not label every class as a supported end-to-end feature.

## Make a plan

Use `features.py plan` after reading the selected cards. It writes schema version 2, catalog digest, user request, selected features, source-derived seed refs, recorded reads, script digest, operation bindings and unresolved facts. It does not execute Blender. The exact seeds are verified against catalog data, so manually appending a guessed seed invalidates the plan.

Read source with:

```sh
python3 scripts/docs.py read 'PAGE.html#ANCHOR' --plan /absolute/path/plan.json
```

The resolved canonical ref and hashes are recorded. Pagination is part of evidence: a partial read is not complete until all displayed lines for that selected page/anchor have been read. Empty anchors cannot count as evidence; read their full page or a nonempty section instead. Prefer precise anchors to loading large classes. Links from a fully read passage permit opening those source pages; arbitrary unrelated pages require selecting the relevant catalog card. Original archive/text tools remain available for human inspection and maintenance, but bare `docs.py` reads do not count as task-plan receipts.

## Bind code to the evidence actually read

Write the script, then run `evidence.py inspect --script /absolute/path/task.py`. It conservatively lists attribute/dynamic operations that require review and follows simple assignments/iteration over known Blender values. `requires_source: false` means the object type is unknown, not that the operation is general Python; review helper parameters and other aliases manually. Edit `bindings` in the plan to identify source-backed lines and explain the fact used. For example, after reading the `api:bpy.app` card and `bpy.app.html#bpy.app.version_string`, this script:

```python
import bpy
print(bpy.app.version_string)
```

can bind line 2 as:

```json
{
  "lines": [2],
  "basis": "source",
  "refs": ["bpy.app.html#bpy.app.version_string"],
  "reason": "The supplied source documents this runtime version string; this line only reads and prints it."
}
```

Bindings may contain several refs when a line composes multiple supported operations. Use `basis: general_python` only for non-Blender helpers such as a list append or `Path.write_text`, with a reason; explicit Blender/dynamic accesses cannot use this basis. A remembered Blender operation cannot be relabeled general Python. Planned colors, positions and artistic values can be chosen from the user's output requirements; their assignment API and allowed value contracts still require source evidence.

Keep unresolved Blender facts as nonempty strings in `unresolved`. Do not clear them without new evidence. If an observed runtime enum/socket is needed, save that probe/inspection output, cite the relevant source contract and explain the observed selection in the binding reason; do not assert that the static source contained it. This version's automatic validator hashes static passages, not arbitrary runtime logs, so the agent must inspect runtime evidence and its provenance directly. If the source has no supporting contract, preserve the gap.

```sh
python3 scripts/evidence.py seal --plan /absolute/path/plan.json --script /absolute/path/task.py
python3 scripts/evidence.py check --plan /absolute/path/plan.json --script /absolute/path/task.py
python3 scripts/run_blender.py --script /absolute/path/task.py --plan /absolute/path/plan.json
```

Sealing validates complete recorded source reads, selected catalog seeds, matching source hashes, bindings and unresolved facts; it binds the exact script bytes. Script changes require review and resealing. New source reads clear the seal. The CLI runner repeats these checks and refuses task scripts without a valid plan. The installed `probe_blender.py` path is the sole exception because it is the skill's provided runtime-inspection helper.

## Limits of the checks

The validator cannot prove the semantic relevance of an arbitrary human/model-written `reason`, infer all Python aliases, verify arbitrary dynamic code, or inspect the model's internal knowledge. It is not a security sandbox. The strict skill contract requires the agent to check every Blender-specific line and reject unsupported inferences even when mechanical validation passes. Do not generate dynamic code, import unreviewed task helpers or launch another Blender process to bypass evidence bindings. If semantic support is uncertain, retain an unresolved entry and stop the dependent implementation.

At task completion report the chosen feature IDs, source refs that establish the implementation, actual runtime/output checks and remaining gaps. A successful catalog lookup or seal is not a render, test of all Blender features, or proof of visual quality.
