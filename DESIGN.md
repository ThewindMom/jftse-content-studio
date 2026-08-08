# DESIGN.md — JFTSE Content Studio

## 0. Research Log
- Audience: Fantasy Tennis / JFTSE **modders and designers** who already know rackets, stages, `Res/` paths, and playtest loops.
- Job: author custom items/effects/map metadata, inspect recovered client formats, and export client-safe archives without hand-editing ZIPs.
- Friction today: siloed single-mesh stage view; FTM/ANI APIs with no desk; Equipment bind-pose only; RE power buried behind JSON.
- External references: FT-ResTool `FTMEditor` (2D pan/zoom tile canvas + layer tree + placements — not a 3D DCC); Linear/Supabase operational density; Fanta Tennis cyan accent.
- Constraint: fixed-size native archives; never mutate shared `Racket_001/002`; stock client writes refused; browser is approximate — game remains authority.
- Out of product scope (honest): Blender-parity topology authoring; full DX9 FVF skinning parity; pixel-true Equipment silhouette.

## 1. Product principles
1. **Safety before spectacle** — banned atlases and shared scripts fail closed.
2. **Export is the product** — every edit ends in a verifiable archive/pack artifact when writing.
3. **Honest preview** — label recovery confidence; game remains authority.
4. **One job per pane** — Items / Maps / Meshes modes stay separate; deepen desks inside modes, do not explode top-level tabs.
5. **Progressive RE power** — default path is the day-1 job; advanced layers (FTM, ANI scrub, multi-draw objects) are opt-in panels with clear labels.

## 2. Visual language
- Background: deep ink `#0B1020`
- Surface: `#121A2F` / elevated `#18233B`
- Border: `#2A3654`
- Text: `#E8EEF9` / muted `#93A0BF`
- Accent: cyan `#5FD0FF`
- Danger: `#FF6B7A`
- Success: `#3DDC97`
- Font: Inter / system UI sans
- Radius: 12px cards, 8px controls
- Density: comfortable operational (not marketing hero)

## 3. Information architecture
- Top nav: Studio title + mode tabs (**Items**, **Maps**, **Meshes**) + bridge/export chip
- **Items**: library → effect editor → export/install → Equipment preview (mesh + Bone_Racket + optional ANI scrub)
- **Maps**: catalog → stage design desk (validate/SQL) → **Stage compositor** (World + Object layers) → **FTM overworld desk** (2D placements)
- **Meshes**: catalog → single DAT recovery/transform/export (material name list when present)
- Bottom bar: mode-specific next action copy

### Map Studio sub-desks (same workspace, progressive)
1. **Metadata** — name, stage script bind, SQL pack (primary job)
2. **Stage scene** — multi-draw World + Object layers with visibility toggles (after validate)
3. **FTM overworld** — parse FTM/PRJ, 2D grid + placement table (inspect/select; write binary later)

### Equipment desk (Items right rail)
1. Resolve shop mesh → DAT + texture
2. Place at Bone_Racket bind matrix (pink socket marker)
3. Optional: load character ANI → scrub/play → drive socket sample live

## 4. Components
- ModeTab, FieldGrid, AtlasCard, EmitterSlider, PreviewCanvas, ValidationList, PackList
- **StageSceneCompositor** — layer checklist + multi-mesh Three.js viewport
- **FtmDesk** — archive/member fields, 2D canvas, placement table, structured errors
- **AniScrubber** — play/pause, range input, time readout, track pick
- Buttons: primary cyan, secondary ghost, danger outline
- Focus rings: 2px cyan offset
- Badges: `bind pose` / `live scrub` / `recovery` for honesty

## 5. Motion
- Tab switch 160ms ease
- Preview particles continuous but paused under `prefers-reduced-motion`
- ANI play uses rAF; respect reduced-motion → scrub only
- No page-load confetti

## 6. Accessibility
- Keyboard tabs and form controls
- Color never sole status signal (icons + text + PASS/MISS labels)
- Contrast AA on body text
- Viewport regions have `aria-label`
- Layer toggles are real checkboxes with names

## 7. Accepted debt
- Submesh index ranges per material not fully table-parsed (names + single albedo draw common)
- ANI uses hierarchical-derived unit quats when skeleton present; on-disk float4 still unknown
- FTM desk supports patch/add/remove + MapSet install; not full tile-paint GUI
- Equipment pack clones stock mesh slots + catalog index; not freeform topology authoring
- Install-to-permanent-client is allowlist only (`JFTSE_LOCAL_CLIENT` / `/tmp`); stock refused
- `.eft` stage effects listed in scene graph but not meshed/authored
