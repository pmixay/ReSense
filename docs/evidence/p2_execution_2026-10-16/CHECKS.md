# Verification — 16 October 2026

Draft chart/deck follow-up: `scripts/p2_draft_deck.py` built the 18-slide draft
from immutable P4 commit `6d6aaca`, verified direct numeric references/hashes,
and retained all exported rows. Conservative budget including raster labels:
**1,086 words total, maximum 80 per slide**. Chart-source tests: **3 passed**;
Ruff on both P2 chart scripts and `git diff --check`: PASS. Changed Markdown
relative links rechecked: zero missing. LibreOffice PDF exported; contact sheet
and individual new slides reviewed, inherited-background collisions corrected.
PPTX/PDF hashes and source snapshots accompany the draft. Existing broad suite
receipts below remain applicable; only draft-generation/docs changed afterward.

These checks cover the working-tree implementation based on
`cfae4ba9334df6912c9e2c336dea4eb1c1865935`. They do not certify a released image.
Logs in `checks/` are captured command output; screenshots use contract fixtures,
not real sensor observations. See [scope and pending acceptance](README.md).

| Check | Result | Receipt |
|---|---|---|
| Frontend `npm --prefix webapp/frontend test` | PASS: 322 tests | `checks/role2-frontend-final.txt` |
| Frontend `npm --prefix webapp/frontend run build` | PASS, including final Live CSS | `checks/role2-build.txt` |
| Node, shared policy, chart sources, complete backend suite | PASS: 360 tests; one dependency deprecation warning | `checks/role2-python-final.txt` |
| `web/demo` and `tests/test_overview_video.py` | PASS: 94 tests, no skips | `checks/role2-static-final.txt` |
| Static boundary follow-up after mobile canvas correction | PASS | `checks/role2-static-followup.txt` |
| Full webapp browser suite | PASS: 47 tests on frozen final frontend build | `checks/role2-e2e-frozen.txt` |
| C1 browser transition and viewport-width check | PASS on final responsive build: 1 test, 8 deselected | `checks/role2-c1-browser.txt` |
| Ruff on changed Python code and tests | PASS | command below |
| `git diff --check` | PASS at review | rerun before handoff |
| Changed Markdown relative links | PASS: 305 links, zero missing before this receipt | local-path check; public availability not tested |
| Existing PPTX audit | PASS: 16 slides, 963 words, max 80 | `build_deck.py --audit docs/presentation/ReSense_LCT2026.pptx` |
| Historical deck gate parity | PASS | `build_deck.py --check-gate docs/evidence/results/regression_baseline_2026-09-29_shell_off.json` |
| Seal / parameter synchronization | PASS: 36 files, digest in README | no selected detector parameters changed |
| Actual selected-image viewer, second device and S5 | PENDING | owner inputs in `HANDOFFS.md` |

## Reproduction

Container: `resense-role2-checks`; source mounted at `/source`, compiled current core
and configurations at `/work`. See README for environment setup and initial failures.

```sh
npm --prefix webapp/frontend test
npm --prefix webapp/frontend run build
docker exec -e PYTHONPATH=/source/webapp/backend:/work \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 \
  -e RESENSE_REQUIRE_SYNTHETIC=1 -w /tmp resense-role2-checks \
  python3 -c 'import resense,sys,pytest; sys.path.insert(0,"/source"); raise SystemExit(pytest.main(["-q","-rs","/source/tests/test_node.py","/source/tests/test_decision_policy.py","/source/tests/test_p2_chart_sources.py","/source/webapp/backend/tests"]))'
docker exec -e PYTHONPATH=/work -e RESENSE_REQUIRE_WEB=1 \
  -e RESENSE_REQUIRE_SYNTHETIC=1 -w /source resense-role2-checks \
  python3 -m pytest -q -rs web/demo tests/test_overview_video.py
docker exec -e PYTHONPATH=/source/webapp/backend:/work \
  -e WEBAPP_DIST=/tmp/role2-final-dist \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -w /tmp resense-role2-checks \
  python3 -m pytest -q -rs /source/webapp/e2e
git diff --check
```

Ruff was run on the changed scripts, node source, backend source, and their changed
Python tests. The required browser/synthetic flags prevent silently crediting skips.
For the final browser run, the completed frontend `dist` directory was copied to
`/tmp/role2-final-dist` inside the container before testing. An earlier run overlapped
frontend rebuilding and returned missing-bundle/server errors (45 passed, 2 failed);
the frozen-build run passed all 47 tests in 406.11 seconds.

## Visual evidence

`screenshots/dashboard-*.png`: local static dashboard, manually supplied C1 CAUTION
contract frame, both known reasons. `screenshots/live-caution-*.png`: built React app,
fake rosbridge publisher from the E2E harness, both known reasons and a fixture-only
health message. Captures cover 1280×720, 1920×1080 and 390×844 browser viewports;
full-page captures can be taller than the viewport. They are not second-device proof.

Reviewed desktop and mobile captures exposed canvas clipping and a Live card height
problem. Subsequent mobile review also exposed shared navigation overflow and rail
label collisions; responsive header, navigation and rail rules now contain them.
Final captures follow those fixes; the focused browser check asserts viewport-width
containment at all three sizes as well as reason display and GO/stale transitions.
Actual ROS/RViz/Foxglove visual sign-off,
release-matched media and P1 approval remain open. Producer examples in
`checks/role2-node-examples.json` come from node fixtures, not a real recording.
