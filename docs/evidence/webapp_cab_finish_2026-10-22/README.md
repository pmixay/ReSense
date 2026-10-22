# Web player, metro cab: loose ends closed (2026-10-22)

Base `f24d939` (sealed 1.3.0 detector). Branch `claude/webapp-cab-finish-1.3`. No detector file touched.

## What changed

* **Links to the removed `trainInterior.ts`** (removed in `7017a02`): `DESIGN.md:324` now points to `cabEntry.ts` / `cockpit.ts`;
  `interior-restored/` and `metro-2020/` READMEs mark the file as removed and the gallery as historical;
  `player-workspace/` already said so (banner dated 22.10). `interior-restored/capture.json` is unchanged; a note sits beside it
  (`capture.note.md`). Checked: `grep -rn trainInterior` leaves only statements that the file is removed, plus `capture.json` itself.
* **Superseded galleries**: one-line banner (22.10, replacement `docs/images/player-cab/`) on `interior-restored`, `metro-2020`,
  `glossy-materials`, `ui-improvement`; `d1-controls-journey` has a "partly superseded" banner (only its Player captures are old).
  `player-workspace` already had one. Judgement call, unverified by anyone else: `moskva-doors`, `directional-travel`,
  `travel-stability`, `slide-performance` document section-navigation transitions (`TrainDoors.tsx` still exists), so were left alone.
* **Review video**: the only reference was `docs/images/player-cab/README.md` ("8.4 s review video … not committed"). No capture
  script for it exists in the repository (searched the tree and `git log -S walk-0-page`: only the commit that added the stills).
  So the reference was replaced by a pointer to the procedure below; no video was committed.

## Regenerating the review video

The stills `docs/images/player-cab/{walk-0..5,boot-1..4}` were rendered frame by frame on Playwright's controlled clock
(`page.clock.install()`, `pause_at`, then `run_for(40)` per frame, as in `webapp/e2e/test_navigation.py`), CSS animations pinned to the
same clock, 1440×900, Chromium/SwiftShader, on a build with demo runs `demo_approach`/`demo_crossing`: click a run's play link on
Прогоны, screenshot after every 40 ms step through the walk and the boot (about 210 frames = 8.4 s), then
`ffmpeg -framerate 25 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p out.mp4`. The result must stay under 20 MB. This is a
description, not a tested script; the exact frame count is unverified.

## Test counts (local, Python 3.13 / Node 22; CI uses 3.10 / 24)

| check | result |
|---|---|
| `webapp/backend` pytest | 179 passed (needed `libegl1 libgl1 libgomp1 libusb-1.0-0`; before installing them: 168 passed, 11 errors, open3d import) |
| frontend `npm ci && npm test && npm run build` | 46 files, 371 tests passed; build OK |
| `web/demo` pytest | 81 passed |
| e2e shards 1–4 | pending when this was written |
| ruff 0.15.8 `check_archived_lint.py --lint` | PASS (141 immutable, 392 audited) |
| `detector_freeze.py verify` | PASS (42 files) |
