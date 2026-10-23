# Role 2 — 20 October code handoff

**Status:** today's Role 2 code work is verified and published at
resense.amdm.life (22.10: that host now serves another app; the preview is https://resense.arbuz.lol). The user supplied the corrected
domain after the initial blocked attempt below; [PUBLISH.md](PUBLISH.md) records
the successful push, deployment and public checks. Stop at the non-code handoff
in [PLAN.md](PLAN.md); final release acceptance remains with the captain/P3/P4.

## Plan correspondence

| Planned acceptance | Result |
|---|---|
| Integrate main `2a5836922ad90faf50ba3f4a88740b1c6c129d65` into UI parent `b36c21c8a955924a19517edbd8b7ca08ecb21b47` | Resolved integration retains desktop UI and current main ownership/release facts. The completion commit joins these two parents. |
| Detector/configuration/ROS sources equal pinned main | `git diff 2a583692 --exit-code -- resense configs native ros2_ws setup.py pyproject.toml` exits 0. K1/K2 remain off. |
| Piecewise track consistency | CPU/dashboard track support integrated; both point materials now receive curvature step/knot; actual WebGL transform-feedback regression checks rail colors before/at/after the knot, both step signs and legacy zero step. |
| Track input boundaries | Both web clients reject malformed new coefficients and accept legacy absent/null coefficients. Dashboard import/live rejection and frontend boundary tests pass. |
| Navigation recovery | A queued readiness callback cannot restart a watchdog-expired journey. Cancelled snapshot warm-up cannot mark a later journey ready. Timer regression failed before the fix and passes after it. |
| Paused live replay | Optional `paused=true` establishes pause on the server before delayed browser startup handling. Delayed-client backend regression failed before the fix and passes after it; browser replay deliberately delays `onopen` by one second at 10×. Frame-zero reconnect is covered. |
| Browser checks match their intended scenarios | Stale-row 404, active-upload navigation and native-resize tests now synchronize their setup; real backend assertions and desktop layout checks remain. |
| Commit, deploy and public identity check | Code committed and pushed as `c1a7614`; the corrected target `resense.amdm.life` is deployed with matching public identity. [Publication receipt](PUBLISH.md). |

## Verification

Host: Python 3.12.3, Node 22.23.3, Chromium 1248, software WebGL, **one CPU core**.
Only desktop viewports (1280 px and wider) were used.

| Check | Result |
|---|---|
| Frontend `npm test` | **362 passed**, 45 files |
| Frontend `npm run build` | PASS: both TypeScript projects and Vite production build |
| Backend `python -m pytest -q` | **179 passed**, no skips |
| Dashboard `python -m pytest -q -rs web/demo` | **81 passed**, no skips |
| Browser analysis | 13 passed in the module run; the remaining timeline flow passed in its focused run with the host timeout adjustment |
| Browser navigation | 18 passed in the module run; resize regression passed after synchronization repair |
| Browser data | **12 passed** in the final module run |
| Browser Player | All **15 cases passed** across batches: first six in the original run, four in the middle batch, fullscreen/layout two in the next batch, final three in the final batch |
| Browser system | **13 passed** in the final module run, including delayed paused reconnect |
| Browser upload-resume and GPU shader | **2 passed** |
| Archive integrity + pinned Ruff 0.15.8 | PASS: 141 immutable files, 40 exact exclusions, 378 live files audited |
| `scripts/sync_params.sh --check` | PASS |
| `git diff --check` | PASS for the execution changes |
| Whole incoming merge `git diff --cached --check` | Whitespace findings in 27 inherited archive/evidence files; each verified byte-identical to pinned main |
| `scripts/detector_freeze.py verify` | **Inherited FAIL**: two added and twelve changed detector files against the old seal, plus config/validation mismatch; agrees with pinned main's backlog |

Browser coverage is **75 cases across split runs**, not a claim of one clean
uninterrupted suite. The initial combined suite and two large Player batches hit
process timeouts on this host. Successful cases were retained; remaining cases
were run in smaller batches. The last app change affects live replay only; its
entire system browser module, backend suite, frontend suite and build were rerun.

Other unsuccessful attempts are accounted for:

- Temporary disk pressure caused HTTP 507 in test setup. Disposable pip cache and
  this execution's abandoned test data were removed before continuing.
- Running the dashboard and webapp suites in one pytest process caused their
  independent Playwright/asyncio fixtures to conflict. Separate suite processes
  pass; the combined attempt is not counted as acceptance.
- Five/30-second default assertions expired on slow rendering. The local runner
  sets default expectations/actions to 60 seconds; explicit test deadlines,
  animation checks and layout assertions remain. The runner is not an app change.
- The navigation state race and live replay pause race were reproduced and fixed;
  the stale-row/upload/resize test setup defects were repaired as registered in
  the plan. Early failed reports are not represented as passing reports.

### Commands and local receipts

For the Python checks:

```bash
export PYTHONPATH=/tmp/opencode/p2-deps:/root/resenseui:/root/resenseui/webapp/backend:/root/resenseui/ros2_ws/src/resense_ros
export WEBAPP_DIST=/root/resenseui/webapp/frontend/dist
export PW_CHROMIUM=/root/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome
```

Working directory `webapp/frontend`:

```bash
PATH=/tmp/opencode/node-v22.23.3-linux-x64/bin:$PATH npm test
PATH=/tmp/opencode/node-v22.23.3-linux-x64/bin:$PATH npm run build
```

Working directory `webapp/backend`:

```bash
/home/resense/.venv/bin/python -m pytest -q --junitxml=/tmp/opencode/p2-backend-final.xml
```

Working directory repository root:

```bash
RESENSE_REQUIRE_WEB=1 /home/resense/.venv/bin/python -m pytest -q -rs web/demo --junitxml=/tmp/opencode/p2-dashboard-only-final.xml
/home/resense/.venv/bin/python scripts/check_archived_lint.py --lint --ruff /home/resense/.tools/ruff0158/bin/ruff
scripts/sync_params.sh --check
/home/resense/.venv/bin/python scripts/detector_freeze.py verify
git diff 2a583692 --exit-code -- resense configs native ros2_ws setup.py pyproject.toml
```

Browser command prefix:
`/home/resense/.venv/bin/python /tmp/opencode/p2_browser_runner.py`.
The runner calls `pytest.main` with a `pytest_runtest_call` hook setting
`playwright.sync_api.expect.set_options(timeout=60_000)` and, when the `app`
fixture is present, `app.page.set_default_timeout(60_000)`.

| Arguments after the prefix | Local JUnit receipt / observed output |
|---|---|
| `-q webapp/e2e/test_analysis.py --junitxml=/tmp/opencode/p2-analysis-final.xml` | 13 pass, one timeout; focused case below supersedes that failure |
| `-q webapp/e2e/test_analysis.py::test_run_page_timeline_chart_events_and_downloads --junitxml=/tmp/opencode/p2-analysis-timeline-final.xml` | 1 pass |
| `-q webapp/e2e/test_navigation.py --junitxml=/tmp/opencode/p2-navigation-final.xml` | 18 pass, one resize failure; focused case below supersedes it |
| `-q webapp/e2e/test_navigation.py::test_resize_finishes_travel_without_leaving_a_stale_strip --junitxml=/tmp/opencode/p2-navigation-resize-final.xml` | 1 pass |
| `-q webapp/e2e/test_data.py --junitxml=/tmp/opencode/p2-data-final.xml` | 12 pass |
| `-q webapp/e2e/test_player.py --junitxml=/tmp/opencode/p2-player-final.xml` | Six passing cases printed before the process timeout; no completed XML |
| `-vv webapp/e2e/test_player.py -k 'run_menu or schematic or loading_and_backend or lost_3d' --junitxml=/tmp/opencode/p2-player-middle-final.xml` | 4 pass |
| `-vv webapp/e2e/test_player.py -k 'fullscreen_orbit or workspace_resizes or taller_display or telemetry_button or pointer_pressure' --junitxml=/tmp/opencode/p2-player-layout-final.xml` | Fullscreen and workspace passed before timeout; no completed XML |
| `-vv webapp/e2e/test_player.py -k 'taller_display or telemetry_button or pointer_pressure' --junitxml=/tmp/opencode/p2-player-last-final.xml` | 3 pass |
| `-q webapp/e2e/test_system.py --junitxml=/tmp/opencode/p2-system-final.xml` | 13 pass |
| `-q webapp/e2e/test_upload_resume.py webapp/e2e/test_track_shader.py --junitxml=/tmp/opencode/p2-upload-shader-final.xml` | 2 pass |

JUnit files are local execution artifacts in `/tmp/opencode`; they are not
release evidence or a hosted CI result.

## Initial publication attempt (superseded) and stopping point

The following records the first attempt using the former documented host. The
subsequent successful publication is recorded in [PUBLISH.md](PUBLISH.md).

`scripts/deploy_webapp.sh` exits 2:

```text
Runtime missing. Run scripts/deploy_webapp.sh --install first.
```

The deploying user's `~/.config/resense/deploy.env` and the expected dedicated
runtime are absent. Both `curl -fsS --max-time 20` checks of
`https://hack.amdm.life/api/health` and
`https://hack.amdm.life/deployment.json` fail to connect to port 443 (exit 7).
The documented preview URL is **https://hack.amdm.life/**; this execution has
**not published or verified a new live version**. Restoring the configured preview
environment is required to finish publication.

Remaining Role 2 deliverables for today/defence are the photo asset decision,
Falcon demo-bag preparation, second-device checks, fallback recording, chart/slide
visuals, final documentation numbers and rehearsals. Their ordering/dependencies
are in [PLAN.md](PLAN.md). Code clean-up D2 remains deferred until after 23 October.
Stop here as requested; the media/documentation deliverables are not executed.
