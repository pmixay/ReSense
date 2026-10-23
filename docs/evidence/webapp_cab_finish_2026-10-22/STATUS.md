# Status: paused 2026-10-22 (usage limits)

## Fixed (pushed, commits f4655bbe and 53a3d4b6 on claude/webapp-cab-finish-1.3, base f24d939)
* Links to the removed `trainInterior.ts`: DESIGN.md, interior-restored, metro-2020 (player-workspace already marked);
  capture.json untouched, note beside it (`docs/images/interior-restored/capture.note.md`).
* Superseded banners (22.10 -> `player-cab/`): interior-restored, metro-2020, glossy-materials, ui-improvement; partial on d1-controls-journey.
* Review video: no capture script exists; reference removed, regeneration recipe in README.md (recipe not run).

## Test counts (local)
backend 179 passed; frontend 371 passed (46 files) + build OK; web/demo 81 passed; e2e shards 16+26+30+6 = 78 passed, 0 skipped, 0 failed;
ruff 0.15.8 PASS; detector_freeze verify PASS. No flaky test seen, no test changed.

## Remains
* CI on the head: run 861 (head 53a3d4b6) was pending when paused. Record each job's conclusion (webapp, webapp-e2e shards 1-4)
  in README.md. Not verified: whether CI runs those jobs on this docs-only head.
* If this WIP commit becomes the head, re-check CI on it, and re-run lint/freeze before any further push.
* Final report (SHAs, CI run) once CI is read.
