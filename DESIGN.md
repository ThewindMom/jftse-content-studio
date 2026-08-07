# DESIGN.md — JFTSE Content Studio

## 0. Research Log
- Audience: internal Fanta Tennis designers/modders who already understand rackets and stages.
- Job: author custom items/effects/map metadata and export client-safe archives without hand-editing ZIPs.
- Friction today: raw SET/ZIP surgery, electrical/cloud atlas mistakes, no guided preview.
- References: Linear/Supabase internal-tool calm density; game cyan accent from Fanta Tennis UI; lessons from `docs/custom-content-loading.md`.
- Constraint: fixed-size native archives; never mutate shared `Racket_001/002`; maps V3 is metadata + stock stage bind only.

## 1. Product principles
1. **Safety before spectacle** — banned atlases and shared scripts fail closed.
2. **Export is the product** — every edit ends in a verifiable archive/pack artifact.
3. **Honest preview** — browser particle canvas is approximate; game remains authority.
4. **One job per pane** — Items / Effects / Maps are separate modes, not one overloaded form.

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
- Top nav: Studio title + mode tabs (Items, Effects, Maps) + Export status chip
- Left: library / selectors
- Center: editor
- Right: preview + validation
- Bottom bar: Build pack / Install to disposable out dir

## 4. Components
- ModeTab, FieldGrid, AtlasCard, EmitterSlider, PreviewCanvas, ValidationList, PackList
- Buttons: primary cyan, secondary ghost, danger outline
- Focus rings: 2px cyan offset

## 5. Motion
- Tab switch 160ms ease
- Preview particles continuous but paused under `prefers-reduced-motion`
- No page-load confetti

## 6. Accessibility
- Keyboard tabs and form controls
- Color never sole status signal (icons + text)
- Contrast AA on body text

## 7. Accepted debt
- No full 3D racket attachment preview in V1–V2
- No stage mesh authoring in V3
- Install-to-permanent-client is opt-in path config only; tests use disposable dirs
