# P1/P2 completion checks — updated 27 September 2026

This record covers the original-bag startup check and the live viewer/dashboard work on
`claude/p1-p2-completion-20260926`. It does not change detector quality, close the detector
freeze/release hold, or revise the independent score.

**Operating decision, 27.09:** the proven ten-message rosbag2 read-ahead limit is now the
supported jury, dry-run, and demo playback setting. The cold results below were obtained with
that exact setting, so they are acceptance evidence for the procedure; no new detector result is
implied. Humble's 1,000-message default still fails the cold whole-bag burst and remains outside
the supported procedure. PR #12 has since been merged into `main`; the dated branch references
below identify the source of these measurements.

## Local verification

After merging the latest shared quality-evidence branch, commit `a7789f7`,
`RESENSE_REQUIRE_SYNTHETIC=1 /tmp/resense-p4-venv/bin/python -m pytest -q -rs` completed on this
host with **667 passed, 1 deselected, 6 subtests passed**. The deselected test is
`tests/test_rail_start.py::test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop`,
which requires `/data/cache/new_data`, absent here. All 47 `tests/test_node.py` cases pass. The
browser suite passed all 16 Chromium tests, and the 60-frame dashboard smoke check passed.

The public 16-slide deck and PDF were rebuilt after the test-count card changed to `667+`. The
private 16-slide preview uses the four supplied portraits; city and team-formation details are
marked pending, and the group-photo area is empty. Private deck outputs and photos remain in the
Git-ignored `docs/presentation/private/` directory and are not part of this evidence commit.

## Branch CI

GitHub Actions [run 36274548282](https://github.com/pmixay/ReSense/actions/runs/36274548282),
commit `446e0aded9f57e49abfff31516a728bd25e5e123`, passed pytest, browser, lint, parameter-sync,
offline-build and the two-container viewer checks. The viewer test detected a paused server and
confirmed that the stream resumed after the server recovered. This simulates a separate viewing
device; a human still needs to import the layout and rehearse on a physical second device.

Run [36274548282](https://github.com/pmixay/ReSense/actions/runs/36274548282) cold-cache replay
**failed** its message-count criterion: 85 of 201 messages processed and 84 left after +5 s. The
detector's first STOP was at +1.4 s in the target range, but startup catch-up skipped 110 frames.
The logs and compressed status stream are in
[`cold_bag_failed_run_36274548282/`](cold_bag_failed_run_36274548282/); the raw archive and database
were removed by CI and are not committed.

Run [36277608569](https://github.com/pmixay/ReSense/actions/runs/36277608569) tested the
cadence-preserving code on the original bag but still failed freshness and post-+5 s accounting:
91/201 frames were processed, first STOP was +0.8 s, and five messages remained after +5 s. The
default rosbag2 read-ahead had preloaded a backlog before the node's first result. A follow-up with
read-ahead set to one downloaded and verified the same bag but delivered no LiDAR input during a
12-minute wait; it was cancelled as an invalid playback setup. Its 1,380 no-input watchdog rows are
preserved in [`cold_bag_cancelled_run_36278988540/`](cold_bag_cancelled_run_36278988540/). Run
[36280434044](https://github.com/pmixay/ReSense/actions/runs/36280434044) then passed the 360-degree
`doubleT_obstacle` cold replay with read-ahead ten. The current-source run
[36281462241](https://github.com/pmixay/ReSense/actions/runs/36281462241) passes **both** original
recordings cold at playback rate 1.0 and read-ahead ten. The obstacle check saw 201 status messages,
first STOP +1.1 s at 55.5–56.6 m, 78 ms decode-plus-detect p95, freshness PASS, and zero of 113
source messages unprocessed after the +8.8 s catch-up; four missing frames are absent from the
recording itself. The clear `roundT_doubleT` check saw 252 status messages, zero alarm frames, 48 ms
p95, freshness PASS, and zero of 201 source messages unprocessed after settle. Preserved output,
compressed status streams and hashes are in
[`cold_bags_passed_run_36281462241/`](cold_bags_passed_run_36281462241/). All jobs in run 362814
passed, including 673 pytest cases with zero skips, the Chromium suite, transport and remote-viewer
recovery checks, and offline image delivery.

The cold checks use explicit ten-message read-ahead because the default 1,000-message prefetch
still releases the original recording as an overdue burst and run 362776 had no valid fresh result.
The first obstacle STOP in run 362814 is fail-safe while the source is stale; a current result is
established after startup catch-up. This does not claim that the default-read-ahead path supports an
unbounded overdue burst. Keep C5/C7 and captain action 21 partial pending a decision to adopt a
bounded-prefetch/prewarm operating procedure or separately change and retest the default.

## Follow-up and remaining work

The failure showed that a 20 s startup lag allowance with 0.3 s frame sampling could still let
scene-reset gaps consume the recording. The branch follow-up keeps every observed input-period
frame during the first backlog, even when the preceding recording left a slower period estimate.
After that catch-up drains, live backlog behavior returns to the 0.3 s sampling step and 5 s lag
bound. Both source recordings now pass the cold check with read-ahead ten; the default-read-ahead
whole-bag burst remains stale. Keep action 21 and C5/C7 partial until the captain accepts the
bounded-prefetch procedure or a separately tested default change; do not claim support for an
unbounded overdue burst.

The remaining human tasks are the physical second-device Foxglove layout import/rehearsal and the
presentation details the team has not supplied: city, team-formation details and a group photo.
The user's supplied names, school and portraits are used only in the local private preview.
