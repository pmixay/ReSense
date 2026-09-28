# P2 verification and handoff — 27 September 2026

> **Purpose:** completed frontend work, verification and the next role dependencies.
> **Audience:** team, P1 · **Owner:** P2 · **Language:** EN
> **Last verified:** 2026-09-27, local changes on base `09629f5a981fa7e9ab5a789abecb13e8544c99d0`
> **Status:** dated first-pass record; superseded by the [full P2 review](P2_REVIEW.md)

P2 owns the dashboard, label tool, RViz/Foxglove layouts, presentation tooling and demo assets
([ownership map](../docs/CAPTAIN.md), §8). The current public presentation and video pass their
existing checks against the committed detector baseline.

## Completed in this pass

- Prevented replay controls, shortcuts and playback callbacks from displaying an old file in
  live mode after connecting to ROS. Live panels remain covered while waiting for current data.
- Cleared old distances, decision details, plots and boxes when loading an empty/invalid replay
  or changing sources.
- Added shared result-shape validation for the dashboard and label tool. Invalid records are
  rejected before rendering or updating the live receipt timer. Legacy optional fields remain
  supported; live status requires an explicit recognized decision.
- Fixed STOP rendering/logging when distance is unknown; report minima no longer coerce `null`
  to zero. FAULT hides the old monitoring distance, and invalid live messages keep the stale veil.
- Made label imports atomic and frame-replacing: importing `[]` removes old obstacles on that
  frame; malformed data cannot silently become a verified negative.
- Preserved explicit imported `in_gauge` values through later geometry edits. Quotes and angle
  brackets in label text now survive rendering and export unchanged. Frame indices are validated
  and sorted numerically.
- Added six browser regressions in `demo/test_frontend_boundaries.py`. The original five tests
  were run before the fixes and all five failed on the cloned source.

## Verification

Python 3.12, Playwright 1.63.0 / Chromium 153 on this Linux checkout:

```bash
python -m pytest -q -rs web/demo tests/test_overview_video.py
# 59 passed, zero skipped:
#   16 existing dashboard/layout/deck checks
#   31 Foxglove probe cases
#    6 new browser regressions
#    6 overview-video checks
ruff check .
# All checks passed
python web/demo/make_demo_run.py --out out/p2-demo-run.jsonl
python web/demo/check_dashboard.py --jsonl out/p2-demo-run.jsonl \
  --screenshot out/p2-dashboard-synthetic.png
# PASS: 60-frame generated replay, no browser errors
git diff --check
```

The shared validator also accepted **4,760 / 4,760** status records from **18** compressed capture
files under `docs/evidence/docker_2026-09-23/`, `docs/evidence/p1_p2_completion_2026-09-26/` and
`docs/evidence/results/quality_freshness_2026-09-26/`. This checks format compatibility, including
older recordings and watchdog/freshness snapshots. The local scan report is
`out/p2-status-compatibility.json`.

The browser checks include recorded real-node replay, desktop/mobile layouts, keyboard controls,
freshness expiry, STOP retention, reconnect behavior and `gt.json` compatibility with the Python
evaluator. The Foxglove cases check the probe/protocol; this pass did not run a live ROS bridge or
visually import the layout in Foxglove.

## Next dependencies

| Deliverable | Needed from | Exact handoff |
|---|---|---|
| Final private presentation | P1 / captain and team | Supply `private/team.json` and the four portraits to this checkout, including confirmed city and team-formation details. The prior checkout's private preview was Git-ignored and is absent here. Confirm whether to include a group photo. Then P2 can build the private PPTX/PDF using the documented `--team` path. |
| Final results slides/video refresh | P3 + P4, coordinated by P1 | Provide the accepted detector revision, updated regression baseline and validated measurements. The quality cycle still has open acceptance failures; the current public artifacts describe the existing baseline. |
| Physical remote demo and pitch | P1 / captain and team | Run the deployment on the demo machine, import `web/foxglove_layout.json` on the actual second device, and perform the two timed rehearsals in `docs/PRESENTATION.md`. |
| Optional narration | Captain / speaker | Supply recorded narration aligned to `docs/video/resense_overview.ru.srt`; P2's muxing recipe is in the presentation guide. |

Final quality acceptance, publication and submission remain with P1 after the detector/evaluation
handoff. See [the quality-cycle record](../docs/QUALITY_CYCLE_2026-09-26.md) for those dependencies.
