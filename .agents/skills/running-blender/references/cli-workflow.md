# Blender CLI and runtime evidence

This workflow begins after reading the complete [catalog overview](catalog/overview.md), the relevant domain file and selected feature cards. The catalog supplies the Blender context before any database query. Missing Blender semantics must remain `insufficient_skill_evidence`; runtime inspection cannot supply an undocumented conceptual recipe.

Use host Python for `scripts/run_blender.py`; the task imports `bpy` inside the installed Blender process. The bundled `info_advanced_blender_as_bpy.html` describes a separate module execution mode. Success in that mode would not establish that this CLI workflow was tested.

## Locate and inspect the selected runtime

Choose names from the selected cards and sources, then ask the bundled probe to inspect those names. Example from the skill directory, after selecting source entries for these identifiers:

```sh
python3 scripts/run_blender.py --blender /path/to/blender \
  --script scripts/probe_blender.py -- \
  --output /tmp/blender-runtime.json \
  --type GeometryNodeTree --operator wm.save_as_mainfile \
  --property RenderSettings.engine
```

The wrapper's local implementation gives `--blender` precedence over `BLENDER_BIN`, then searches PATH and conventional macOS app locations. It also accepts a `.app` path. It does not install Blender. Inspect the actual executable's `--help` when a CLI switch needs confirmation for that runtime.

Only the exact bundled `probe_blender.py` path is exempt from `--plan`. A copied probe or any other task script requires a reviewed plan. The exemption authorizes inspection through the supplied helper; it does not make arbitrary operations supported by the source.

Read the saved report. The helper records version/build, background context, build options, requested RNA types/properties, operator registration and `poll()` results. Missing symbols appear as `exists: false`; a false poll records the condition in that particular context. Operator context limitations are described by `info_gotchas_operators.html`. Version equality alone does not establish that all APIs match the snapshot, and a build-option flag does not establish available hardware or successful execution.

The helper writes JSON with `--output`. Stdout also emits `BLENDER_PROBE_JSON=...` amid Blender logs. A zero process status only means the helper completed: inspect `all_requested_symbols_exist` and individual checks. Additional `--type`, `--operator` and `--property` requests must come from supplied source context. The helper accepts `bpy.types.`/`bpy.ops.` prefixes and a `--doc-version major.minor` comparison target.

Keep the report as task evidence. For a dynamic value, cite its documented contract and record the observed value; do not describe it as part of the static API snapshot. The current plan validator verifies static passage hashes, not arbitrary runtime logs. Direct inspection of runtime evidence remains required.

## Read, bind and seal a task

Create the plan from cards already read. `features.py plan` takes repeated `--feature` arguments for combined work. Its source refs come from those cards. Read the necessary refs through `docs.py read REF --plan ...`; continue pagination until each cited passage is complete. Plain `docs.py` reads are maintenance tools and do not record task evidence.

Use [evidence-workflow.md](evidence-workflow.md) for the exact `bindings` schema. Each Blender operation needs a source ref and a statement of the fact that the passage supports. Node sockets, operator requirements, enums and renderer effects must not be filled from Blender knowledge recalled by the model. Keep uncertain facts in `unresolved` and stop dependent implementation until the skill data supports them.

```sh
python3 scripts/evidence.py inspect --script /absolute/path/task.py
python3 scripts/evidence.py seal \
  --plan /absolute/path/plan.json --script /absolute/path/task.py
python3 scripts/evidence.py check \
  --plan /absolute/path/plan.json --script /absolute/path/task.py
python3 scripts/run_blender.py --script /absolute/path/task.py \
  --plan /absolute/path/plan.json \
  --blend /absolute/path/input.blend --timeout 900 -- \
  --output /absolute/path/result.blend
```

The output argument above is only forwarded to the task script. The script must parse it and perform any documented saving operation itself. This wrapper does not save, constrain or roll back task writes. Choose the output and overwrite behavior from the user's task; a plan is not extra authorization.

Sealing checks recorded source reads, source hashes, selected feature seeds, bindings and unresolved facts, then records the exact script hash. A changed script requires review and resealing; additional reads clear the seal. The runner repeats validation before launching, including for `--dry-run`. Passing these checks proves traceability of the supplied records, not that every claim is semantically supported or the result will render correctly.

## Wrapper behavior and its provenance

The wrapper builds an argument array and does not invoke a shell:

```text
blender --background --factory-startup --disable-autoexec [input.blend]
        --python-exit-code 1 --python task.py -- [task arguments]
```

This sequence is part of the bundled wrapper implementation. The existing authoring-supplied CLI summary below is its supplemental source: load the optional `.blend` before running the script and set the Python failure exit code before execution. If no input file is supplied, the wrapper uses factory startup; it does not promise an empty scene. A task needing an empty scene must select and read the relevant documented operation instead of importing a remembered setup snippet.

The authoring summary describes `--disable-autoexec` as suppressing automatic embedded scripts and Python drivers while allowing the explicitly supplied task script. If the user's file depends on those behaviors, record the compatibility issue and investigate through supplied sources/runtime. Do not bypass the evidence workflow to make an unsupported project appear successful.

`--dry-run` prints resolved arguments without launching the child. Output otherwise streams to the terminal. The local wrapper propagates the child's status, returns 124 on timeout and 130 on interruption, and defaults to 300 seconds. Its POSIX timeout handling stops the new process group; its Windows branch stops the Blender process. Set an appropriate timeout for the task; fake-executable tests cover wrapper process behavior only.

## Source-specific decisions and result checks

When needed, select the following source cards before reading the corresponding pages with the plan:

| Decision or limitation | Bundled source |
|---|---|
| Operator context and failed poll | `info_gotchas_operators.html`, `bpy.ops.html` |
| Edit Mode mesh ownership and synchronization | `info_gotchas_meshes.html`, `bmesh.html` |
| Evaluated geometry and temporary meshes | `bpy.types.Depsgraph.html`, `bpy.types.Object.html#bpy.types.Object.to_mesh` |
| Python references after internal data changes | `info_gotchas_internal_data_and_python_objects.html` |
| Blender access and Python threading limitations | `info_gotchas_threading.html` |
| Background scripts and output checks | `info_tips_and_tricks.html` |
| Separate `bpy` module mode | `info_advanced_blender_as_bpy.html` |

Do not replace a context-dependent operator with a remembered API. Discover the alternative through source cards, read its contract and bind its actual use. If the supplied data does not establish a workable alternative, retain the gap.

Check the result against the user's concrete requirements: data values for data tasks, persisted content when saving matters, and rendered output for visual tasks. These are task acceptance checks, not extra Blender capabilities inferred from the catalog. Report exactly which checks ran. File existence, process success or an evidence seal alone does not establish visual fidelity, a completed simulation or correct exported content.

## Authoring record and current proof limits

Supplemental CLI provenance is an **authoring-supplied local summary**, separate from the supplied API corpus. The previous authoring record says the [Blender 5.1 command-line reference](https://docs.blender.org/manual/en/5.1/advanced/command_line/arguments.html) was consulted on 2026-09-05 for background mode, factory startup, auto-execution suppression, Python failure exit codes, argument forwarding and ordered processing. It also records that the equivalent 5.2 page could not be fetched. This document preserves that provenance; it does not claim a fresh retrieval or bundle the full Manual page. Confirm compatibility with the installed executable's help and actual execution.

No Blender executable was available in the standard locations inspected during authoring. Therefore there is no actual Blender/render validation from that environment. Fake-executable runner tests and simulated RNA tests establish only their named helper behavior. The evidence gate is a traceability tool, not a security sandbox or proof about a model's internal knowledge. Reject unsupported Blender claims even if mechanical validation accepts the plan.
