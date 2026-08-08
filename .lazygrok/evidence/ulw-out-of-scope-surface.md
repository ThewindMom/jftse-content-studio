# SURFACE evidence — out-of-scope desks

Date: 2026-08-08
Server: http://127.0.0.1:4319 (cleaned)

## API (PASS)
- GET /api/stage-scene?member=1_Emerald_Beach.set → ok, objectCount=2, world=BF_Court01.dat
- GET /api/ftm/parse FantaCastleOutSide.ftm → sceneObjectCount=1, placement (50,12) CastleOutSide
- GET /api/ani/parse maxFrames=0 → sampled=false, 44 positions
- UI shell HTTP 200

## Tests
- bun test: 47 pass / 0 fail (includes ANI full frames + stage-scene compositor layers)

## Bundle strings (client JS)
- Stage scene compositor / FTM overworld / Load character ANI present in served bundle

## Playwright
- Chromium headless shell not installed in environment; skipped browser screenshot
