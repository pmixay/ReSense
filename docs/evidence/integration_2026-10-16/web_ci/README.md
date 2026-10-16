# Browser CI integration — 2026-10-16

Baseline: `3fdc879`, branch `integration/web-ci-20261016`.

## Preregistered investigation (before fixes)

Inspected Actions runs [P4](https://github.com/pmixay/ReSense/actions/runs/38840524998)
and [P2](https://github.com/pmixay/ReSense/actions/runs/38812602461).
P4 has 43/45 browser passes: queue test `Page.reload` waits for `load` for 30 s;
resumable upload test briefly sees unfinished state, then a completed recording instead of
the file picker. P2 has the same failures plus server-folder processing still pending after
the 5 s navigation assertion. Both passed all 169 backend tests.

Reprobes, before relevant fixes:

1. Run the original data module and upload-resume case in Linux/headless Chromium, recording
   navigation/request events around queue reload and upload chunk acknowledgements.
2. Test whether synchronous Python API polling starves Playwright's sync event dispatcher
   (queue poll loops do not pump browser events; upload `wait_until` likewise).
3. Freeze a strict subset of upload chunks at the browser transport boundary, preserving real
   server acknowledgements, compression, offline recovery and cross-tab behavior. Reload must
   stop the original sender and immediately release ownership; resume must send only missing
   chunks, and produce byte-identical results. File size / timeout increases are not a fix.
4. If lifecycle defects are demonstrated, register the exact event ordering as a regression
   before applying its corresponding application patch.

Tools image definition: `Dockerfile.tools` (an investigation-only derivative; production
Dockerfiles are untouched). Source is transferred with `git archive` into a Linux volume.
All browser/backend runs are serial, in a container capped at 3 GiB; frontend test workers
are capped separately. Results and exact commands will be recorded below.

### Navigation reprobe registration

The original data + resume cases passed on Chromium 149 / Playwright 1.61 (12/12).
CI logs identify **Playwright 1.64 / Chromium 156.0.8078.4**, so the tools image was
rebuilt with those versions and pytest 9.1.1 before final validation. The original queue
case also passed in the targeted 1.64 reprobe; its CI-only 30 s load timeout is not evidence
of a demonstrated backend deadlock. Register a controlled slow, non-blocking image during
queue reload: document/queue readiness must not depend on its completion. First run the
regression with the existing `load` wait, then change the queue reload readiness condition
only if that reprobe fails as expected. Keep the actual queue row/error assertions intact.

The original upload also passed once on 1.64. Register an 8 s browser-dispatching delay before
its reload to reproduce a slower assertion / second-tab interleaving: the original test must
fail if the transfer completes in that interval; the chunk-barrier version must still exercise
an actual unfinished transfer and pass, retaining all byte/chunk checks.

Frontend tests run alongside browser work encountered wall-clock timeouts (15 s retry test,
then a 5 s codec test in a focused probe). Final frontend verification will run without a
browser workload; these failures are not attributed to an application defect without evidence.

## Findings and fixes

- **Lost acknowledged progress (application fix):** a completed chunk's confirmed bytes and
  compression were updated after the last XHR progress event, then suppressed by `REPORT_MS`.
  If following requests stalled, the UI could stay stale indefinitely. A frozen-clock unit
  regression failed with `loaded: 0, compression: null` after the server acknowledged a
  compressed chunk (`acknowledged_progress_unit_red.txt`); the corresponding browser failure
  is in `acknowledged_progress_browser_red.txt`. Chunk acknowledgements now force publication
  of their authoritative progress snapshot, while intermediate byte events remain throttled.
- **Upload completion race:** a lower bound of 8 MiB received did not establish that any
  chunks were still missing. Four concurrent, compressed PUTs could finish while the test
  inspected a second tab or reloaded. The 8 s delayed-reload probe reproduces a completed
  `long_ride` recording instead of the unfinished-file prompt (`controlled_red.txt`).
  The test now gates chunk indexes >=2, permits real offline failures, then permits one
  more chunk after recovery. A strict subset remains missing through reload. It waits for
  the first actual PUT acknowledgement before checking speed/compression (routed Blob PUTs
  may not emit intermediate progress), drains the permitted prefix before the pause snapshot,
  asserts the server is still receiving, and verifies
  the actual `beforeunload` dialog. Existing pause, cross-tab ownership, missing-only resume,
  recording processing, byte equality and chunk-log assertions still run.
- **Queue reload readiness:** the CI logs stop at the browser's `load` wait, without enough
  information to identify a particular delayed resource. The controlled non-blocking image
  regression reproduces the same 30 s timeout (`navigation_red.txt`), although document/queue
  readiness is independent of that image. `App.reload()` now waits for `DOMContentLoaded`;
  the real queue test still requires the deleted-recording row, retry error and clear action
  to work. The regression asserts the queue is usable while `readyState` is still `interactive`
  and the image is unfinished. This is a readiness-contract fix, not a claim of a demonstrated
  backend deadlock or a particular missing CI asset.
- **P2 job submission:** the screenshot/log shows the pending submit button. The server-folder
  flow now observes the real POST `/api/jobs` acknowledgement and requires HTTP 201 before
  asserting navigation and persisted preset/every/clouds options.

The controlled two-case probe changed from red to **2 passed** with the same 8 s reload
delay (`controlled_green.txt`). The first red navigation probe had a cleanup error masking
its timeout; `navigation_red.txt` is the clean reprobe after fixing probe cleanup, before
changing the reload readiness condition. Ordinary baseline passes are in `baseline_ci.txt`.

## Reproduction resources retained

- Tools image: `resense:web-ci-tools-pw164-20261016`, image ID
  `sha256:6117980d5dd2e440a21e0f7acefd2c55fe059226d51149bbc6359d9630a99f1b`.
- Base: `resense:p1-combined-tools-7d3d5a05c258`,
  `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`.
- Container: `rs-web-ci-pw164-20261016`; Linux source volume:
  `rs-web-ci-src-20261016` mounted at `/src`. Limits: `--memory=3g --cpus=4 --shm-size=512m`.
- Environment: `WEBAPP_DIST=/src/webapp/frontend/dist`,
  `PYTHONPATH=/src:/src/webapp/backend:/src/docs/evidence/integration_2026-10-16/web_ci`.
- Serial check runner: `run_checks.sh`; raw results in the container at `/tmp/web-ci-final/`.
  Initial runner stdout/exit: `/tmp/web-ci-checks.log`, `/tmp/web-ci-checks.exit` (the first
  full browser run found the pause-snapshot race described below).
  Final browser follow-up runner: `run_browser_followup.sh`, with stdout/exit at
  `/tmp/web-ci-browser-final.log`, `/tmp/web-ci-browser-final.exit`.
  Controlled probe stdout/XML/event streams remain under `/tmp/controlled-*` and
  `/tmp/navigation-red.*`. Original 1.64 baseline probe is `/tmp/baseline-ci.*`.
- Original source archive on the host:
  `C:/Users/alikh/AppData/Local/Temp/opencode/web-ci-baseline-3fdc879.tar` (made with `git archive`).
  The committed final tree is retained as
  `C:/Users/alikh/AppData/Local/Temp/opencode/web-ci-final-20261016.tar`.
  Webapp overlay patch: `C:/Users/alikh/AppData/Local/Temp/opencode/web-ci-source-20261016.patch`.
  The five changed webapp source files were overlaid into that Linux checkout before
  final checks. Their Git blob IDs match between the Windows checkout and Linux volume:

  | File under `webapp/` | Git blob |
  | --- | --- |
  | `e2e/conftest.py` | `1179f401e35c5ffedf4dfefb9eb0f3a5fb3f119c` |
  | `e2e/test_data.py` | `72ae74aa30ced3c5fc6de8feae2292b28a89f8ba` |
  | `e2e/test_upload_resume.py` | `dc421f69cd9c1e2a84082767127cf1a7bbfa4e0f` |
  | `frontend/src/api/upload.ts` | `8a686446e8f1d58a0358d378be8dd881c12e1825` |
  | `frontend/src/api/upload.test.ts` | `f2f5c51fda6eba16f534abab8ee9cccb63aeb0fe` |

Rerun all final checks against the retained source/build environment:

```powershell
docker exec rs-web-ci-pw164-20261016 bash docs/evidence/integration_2026-10-16/web_ci/run_checks.sh
```

Rebuild the tools image (the named base image must be present):

```powershell
docker build -t resense:web-ci-tools-pw164-20261016 -f docs/evidence/integration_2026-10-16/web_ci/Dockerfile.tools docs/evidence/integration_2026-10-16/web_ci
```

A fresh source volume needs `npm ci` in `/src/webapp/frontend` before `run_checks.sh`.
The script runs backend tests, frontend tests with two workers, both TypeScript checks and
the production build, two targeted four-case probes with the delayed reload, then all
original 45 browser cases plus the new readiness regression without injected delays.
`WEB_CI_SEED=1` only seeds the ordinary demo prerequisites for independently selected data
tests; it does not replace the API, worker, detector, upload or browser behavior.

Additional lint check passed with CI's `ruff==0.15.8`:
`python3 -m ruff check webapp/e2e docs/evidence/integration_2026-10-16/web_ci/web_ci_events.py`.
Ruff was installed in the retained container with `python3 -m pip install ruff==0.15.8`.

### Pause-snapshot follow-up (registered before the follow-up patch)

The first full run passed 45 cases and failed the upload's flat pause counter: the snapshot
was 8 MiB, then became 16 MiB. One of the two permitted PUTs had already sent its body and
committed after XHR abort. An abort does not roll back a complete, CRC-checked server chunk.
Reprobe after establishing that both permitted prefix chunks have been acknowledged, before
taking the pause snapshot; retain the exact flat-counter assertion and real offline/recovery
steps. Repeat the final upload case three times (with the 8 s delayed reload), then rerun
all 46 browser cases. Backend/frontend application code is unchanged by this follow-up.
The initial follow-up incorrectly used an async `wait_for_function` predicate, whose returned
Promise was truthy before its result established the prefix. Replace it with two response
waiters registered before sending: both permitted chunk acknowledgements must actually arrive
before the pause snapshot. Keep the flat counter assertion.

### Acknowledged-progress regression registration

The next focused probe exposed an application progress bug: the server held 16 MiB and the UI
showed bytes/s and ETA, but compression remained absent for the entire 20 s assertion. Chunk
acknowledgements update `rawSent`/`wireSent` immediately after an XHR progress report, then call
the throttled `report()`. If that last report falls inside 100 ms and subsequent requests are
held / stalled, no trailing callback publishes the acknowledged state. Register a unit reprobe:
freeze the performance clock within one reporting interval, acknowledge a compressed first
chunk and hold the second. The latest published uploading snapshot must include the confirmed
bytes and compression while the upload remains unfinished. Run it red before changing the
acknowledgement reporting path; then verify frontend tests/build and the browser follow-up.

## Final validation

| Check | Result | Evidence |
| --- | --- | --- |
| Backend (unchanged Python application source) | **169 passed**, zero skips/errors | `results/backend.xml`, `results/backend.txt` |
| Frontend, including acknowledged-progress regression | **306 passed**, zero skips | `results/frontend.txt` |
| Both TypeScript checks and production build | **passed** | `results/build.txt` |
| P2 server-folder + queue + readiness probes | **passed twice** during the initial targeted phase | `results/targeted-{1,2}.xml` |
| Final pause/drop/reload/resume case, 8 s delayed reload | **3 consecutive passes** after the final fixes | `results/upload-{1,2,3}.xml` |
| Entire Linux/headless Chromium suite, production build | **46 passed**, zero skips/failures/errors (all original 45 + readiness regression) | `results/browser.xml`, `results/browser.txt` |
| Ruff 0.15.8 on owned Python code; `git diff --check` | **passed** | commands above / integration transcript |

Final browser runner exit status: **0** (`results/final_exit.txt`). Its JUnit verifier checked
every retained positive XML suite for zero skipped, failed or errored cases. Runtime versions
are in `results/versions.txt`; Chromium is **156.0.8078.4**, Playwright **1.64.0**.
The final frontend checks/build ran after the application fix; after the final e2e-only
acknowledgement-wait refinement, the browser follow-up used `WEB_CI_SKIP_FRONTEND=1` to reuse
those unchanged verified assets. The final source blob IDs are listed above.

The selected red unit probe intentionally selected one test with `-t acknowledged`; its
other 15 cases were not selected. The subsequent complete frontend run passed all 306.
Negative reprobes are retained separately from the final passing results; the first full
pause-counter failure is `full_browser_pause_red.txt`.
Text evidence has trailing whitespace normalized for Git; raw output remains in the retained
container and the local ignored `.log` captures.
