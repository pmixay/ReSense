# Dashboard fast replay CI repair

Baseline: `b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1`, Actions run
`38897519801`, pytest job `116961605720`.

## Registered before the patch

CI passed 1649 core tests (8 existing external-data deselections), but dashboard tests
had 1 failure / 73 passes. The 14-frame synthetic replay had five alarm frames,
first distance 53.917877 m; at speed 10 the checker observed only 37.9 m, outside
its unchanged [40, 72] m acceptance window. The independent 60-frame smoke passed.

The UI advances every 10 ms at speed 10. The checker sleeps 20 ms between Python
polls and obtains frame index and banner text in separate browser round trips.
Both omissions and mismatched frame/text pairs are possible; seeking for the
screenshot must not substitute for observing the actual playback.

Deterministic preregistered repro: play a small JSONL at speed 10 through the real
file input and Play button, but keep Python inside the click wrapper until playback
finishes. Require every displayed frame/title pair to be captured, including a
single in-window alarm and subsequent 37.9 m alarm. Also suppress only the actual
rendered alarm titles in a negative control: input alarm flags alone must not pass.
Run these against the existing checker before replacing polling with in-browser
DOM transition observation. Keep the distance window, replay speed and timeout.

Verification: focused red/green repro, original synthetic tiny-run test repeatedly,
full `web/demo` suite with required browser coverage, original 60-frame smoke;
inspect the completed webapp CI job independently. Source, native library and Python
imports must come from the pinned Linux source checkout.

## Result

The original checker failed the deterministic positive control with **no alarm observed**;
the suppressed-title negative control correctly failed the playback acceptance (`red.txt`).
After the patch both controls pass (`green.txt`). The checker registers a `MutationObserver`
on `#banner-title` before Play, captures index/title together at the mutation checkpoint
after each replay timer task, and retrieves the sequence after playback completes. It
disconnects before the nearest-obstacle screenshot seek. The report uses actual DOM text,
not JSONL obstacle flags or a reconstructed alarm sequence. Replay timing, accepted distance
bounds and failure criteria are unchanged. No dashboard UI or detector changes were needed.

| Validation | Result |
| --- | --- |
| Original 14-frame synthetic test + both deterministic controls | 3 passes per run, **three consecutive runs** |
| Complete `web/demo` suite, `RESENSE_REQUIRE_WEB=1` | **76 passed**, zero skips/failures/errors |
| Original default 60-frame CLI smoke, screenshot | **PASS**, 144,774-byte PNG |
| Ruff 0.15.8, owned Python files | **PASS** |

`checks.txt` records all commands' output; `full.xml` preserves the full-suite JUnit and
`exit.txt` records runner exit **0**. The focused `-k` probes deliberately deselect unrelated
tests; the full suite deselects none. Text log trailing whitespace is normalized for Git.

### Exact reproduction

Retained container: `rs-web-ci-pw164-20261016` (3 GiB / 4 CPUs), tools image
`resense:web-ci-tools-pw164-20261016`, Playwright **1.64.0**, Chromium **156.0.8078.4**.
Python **3.10.12**, Open3D **0.19.0**, NumPy **1.26.4**; these latter versions differ from
the hosted runner and are explicitly recorded rather than claimed identical.

Source: `git -c core.autocrlf=false archive b0c9c17` extracted into a fresh Linux directory
`/dashboard-ci-b0c9c17` in that container. Host archive retained at
`C:/Users/alikh/AppData/Local/Temp/opencode/dashboard-ci-b0c9c17.tar`.
Only the two patched web/demo files were overlaid; their Git blob IDs match host/container:

- `check_dashboard.py`: `b2f8e7a79848c65e283103cbadf6f54b94d25b2b`
- `test_web.py`: `719738a3b412ece2974f1abdb4330fecd807b201`

The native library was rebuilt there with `bash scripts/build_native.sh`; both Python imports
and the enabled native kernel resolve to this pinned directory (`checks.txt` identity).
Raw outputs, JUnit files, synthetic JSONL and screenshot remain at
`/tmp/dashboard-ci-b0c9c17-results`; initial red/green logs and XML remain at
`/tmp/dashboard-{red,green}.{txt,xml}`. The runnable copy of `run.sh` is `/tmp/dashboard-run.sh`:

```powershell
docker exec -w /dashboard-ci-b0c9c17 -e PYTHONPATH=/dashboard-ci-b0c9c17 -e RESENSE_REQUIRE_WEB=1 rs-web-ci-pw164-20261016 bash /tmp/dashboard-run.sh
```

## Completed webapp job follow-up (preregistered)

Job `116961605775` completed with 44/46 browser passes: downloads absent after the
player-to-run history navigation (`test_analysis.py:294`) and a queue reload timeout
even at `DOMContentLoaded` (`test_data.py:408`). Backend 168/169 passes: its one failure
is a stale literal detector-version assertion (`1.0.0` versus actual `1.1.0`), reported
to the parent separately. Frontend unit/type/build step passed.

Before additional browser patches, run both existing failed cases on pinned current
source with real backend and production build, request/navigation diagnostics and
controlled CPU throttling. Inspect whether the requests or renderer are blocked before
selecting a fix; do not widen assertion windows or replace missing UI with API claims.

The 4x CPU-throttled baseline reproduces the analysis navigation race (detached chart
during scroll). Event evidence shows Back at 60318.960 before the lazy player chunk
finished at 60318.977; the next Back happened only 30 ms after the player URL changed,
while frame/cloud requests for that player arrived later. `player_pos` currently checks
only the browser URL, so the test reverses a transition before the destination view
commits and can then interact with the old run DOM. Register a readiness regression:
delay the player destination's real asset/API transport, ensure the helper does not
return on URL alone. Require the actual player scrubber and its frame position before
going Back, and the player view to detach before interacting with the returned run.

Readiness-only strengthening exposed an application navigation problem: the player
scrubber remained attached after Back changed the URL, failing twice at the original
5 s assertion budget under 4x CPU throttle. Instrumented blocking WebGL calls were empty;
the outgoing route is retained by the opt-in router `v7_startTransition` scheduling.
Test a synchronous route-commit configuration (React Router 6's supported default) so
route departure cannot remain behind ongoing player updates. Keep the rendered-player
and detach checks as regressions, and rerun the same throttled case before accepting it.

The first combined follow-up was interrupted after the new readiness test's blanket
500 ms network latency exhausted its 5 s UI assertion budget (many lazy assets + API
round trips); its missing finally-cleanup then contaminated two later empty/filter tests.
The final regression uses 100 ms transport latency, still starts at document commit,
and always removes its recording/run in `finally`. Recheck the original URL-only helper
against this final repro before the complete rerun; no existing timeout changes.

The full rerun passed 46/47, including queue reload, analysis downloads and upload resume.
It exposed a real delete lifecycle race: `test_run_page_preset_rename_and_delete` reports
a console 404; backend access log lines 519/522 show DELETE run `h5yqsjrm8s` -> 204,
then GET of the same deleted run -> 404. `useDeleteRun` evicts cached queries before its
dialog's `onDeleted` callback disables the detail query. Register the existing failed
case before the fix: disable the run detail's query while its delete dialog owns the
operation, so cache eviction cannot trigger a refetch of deleted data. Cancellation or
failure must still leave the page usable. Retain the zero-console-error assertion.

### Follow-up reproduction and interpretation

The exact queue timeout did **not** reproduce locally in the baseline or subsequent
throttled probes. The CI log has no navigation commit or resource diagnostics for that
timeout, so it is not assigned a confirmed root cause here. No further reload timeout
or readiness relaxation was applied. The final full-suite result below is local validation,
not a claim that the original remote queue timeout has been independently reproduced.

The production changes are synchronous route commits in `src/App.tsx` and disabling the
run-detail query while its delete dialog owns the operation. The browser helper now checks
the actual rendered player's scrubber position and waits for that view to detach on Back.
The new readiness test is red with the old URL-only helper even at the final 100 ms
transport latency (`player-readiness-final-red.txt`).

Raw diagnostic records: `webapp-probe.txt` / `webapp-events.txt` (baseline),
`webapp-ready.txt` / `webapp-ready-events.txt` (readiness-only attempt),
`webapp-gl.txt` / `webapp-gl-events.txt` (instrumented attempt), `webapp-sync.txt`
(synchronous route commits), `webapp-interrupted.txt` (new-test setup failure), and
`webapp-delete-red.txt` / `webapp-backend.txt` (actual post-delete GET). Unlike the initial
dashboard red excerpt, these raw logs retain diagnostic whitespace.

`run_webapp.sh` reproduces frontend tests/build, two 4x CPU-throttled targeted runs
(readiness, analysis links/downloads, rename/delete, queue cancel/retry/reload), then
the full browser suite without throttling or the diagnostic plugin. Both final targeted
runs passed **4/4** at unchanged assertion timeouts; frontend passed **306/306**, type
checks and build passed. Raw outputs are at `/tmp/webapp-ci-b0c9c17-results` in the
retained container; `/tmp/webapp_probe.py` is the diagnostic helper copy.

```powershell
docker exec -w /dashboard-ci-b0c9c17 -e PYTHONPATH=/dashboard-ci-b0c9c17:/dashboard-ci-b0c9c17/webapp/backend:/dashboard-ci-b0c9c17/ros2_ws/src/resense_ros:/tmp -e WEBAPP_DIST=/dashboard-ci-b0c9c17/webapp/frontend/dist rs-web-ci-pw164-20261016 bash /tmp/webapp-run.sh
```

Final overlay Git blob IDs (identical host/container):

| File under `webapp/` | Git blob |
| --- | --- |
| `frontend/src/App.tsx` | `85927dba8140c849baf4920e0e0690c9c49bcde7` |
| `frontend/src/pages/RunDetail/index.tsx` | `46195f21a13aa710dd866b45b52521621f4b27c3` |
| `frontend/src/pages/RunDetail/RunDetail.test.tsx` | `60b1a003c4d802aae613975c5fa8a4ba9ed1bc8e` |
| `e2e/test_analysis.py` | `a85aade5ae435d8d4b7ee34f1545dbf1aaa07021` |

### Simulation pause follow-up, registered before patch

The next full run passed the previous failures, but found `test_live_simulation_transport`
at pause: after the UI published `paused`, an already-in-flight WebSocket frame advanced
the slider from 30 to 31. The simulation store publishes pause immediately but its receive
path still consumes ordinary frames. Register a deterministic store regression: pause at
30, deliver a late frame 31, assert snapshot/sample history remain at 30; an explicit seek
while paused must accept its target once, ignore later unsolicited frames, and play must
resume accepting updates. Apply this only to the simulation transport, never real ROS
status. Keep the browser's exact paused-position equality assertion.

The unit repro failed with `paused: true` but `count: 2, pos: 31` instead of
`count: 1, pos: 30` (`live-pause-unit-red.txt`). The final receive guard applies only
to paused simulation with no pending explicit seek. The same regression checks a paused
seek accepts its target, rejects a later unsolicited frame, and Play accepts new frames.

## Final browser follow-up results

- Frontend **307 passed**, zero skipped; TypeScript checks and production build passed.
- Previous analysis/rename/queue/readiness controls: two **4/4** runs at 4x CPU throttle.
- Final simulation transport case: **two consecutive passes**, actual pause/seek/resume.
- Entire production-build Linux/headless Chromium suite: **47 passed**, zero skips,
  failures or errors, including all original 46 cases plus the new readiness regression.
- Ruff 0.15.8 passed for owned Python helpers. Application-source whitespace check passed.

Final proof: `webapp-live-checks.txt`, `webapp-final.txt`, `webapp-full.xml`,
`webapp-exit.txt` (**0**). `webapp-checks.txt` / `webapp-pause-red.txt` retain the preceding
46/47 pause-failure run; `webapp-delete-red.txt` retains the prior delete-race failure.
Negative artifacts are not substituted for the final passing JUnit.

The final follow-up runner is `run_live_followup.sh` (container copy
`/tmp/webapp-live-run.sh`), with raw stdout/exit at `/tmp/webapp-live-checks.{txt,exit}`.
It repeats frontend checks/build after the simulation fix, runs the two transport checks,
then the full suite with no fault injection or diagnostic plugin. All final source files
match the pinned Linux overlay; additional blob IDs:

- `webapp/frontend/src/pages/Live/feed.ts`: `4df975f629ba0186d663f2ac4b8161d1836d49d5`
- `webapp/frontend/src/pages/Live/feed.test.ts`: `f4262dae2b8e969fdd429867506375892d0174b4`

The stale backend literal at `webapp/backend/tests/test_server_files.py:128` is unchanged
in this browser-owned repair and needs the parent's version-test correction. The remote
run also has the parent's separate artifact-quota failure. No remote CI rerun or push was
performed here; the exact original queue timeout remains unreproduced locally as stated
above, despite passing all local queue checks and the final full suite.
