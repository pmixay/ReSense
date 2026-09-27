# P1/P2 completion checks — 26 September 2026

This record covers the original-bag startup check and the live viewer/dashboard work on
`claude/p1-p2-completion-20260926`. It does not change detector quality, close the detector
freeze/release hold, or revise the independent score.

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

The same workflow's cold-cache replay **failed** its message-count criterion. It downloaded the
original `doubleT_obstacle` bag, evicted the runner page cache, and processed 85 of 201 messages.
The detector's first STOP was at +1.4 s in the target range, but startup catch-up skipped 110
frames, reported 118 total drops, and left 84 messages unprocessed after +5 s. The full logs,
compressed status stream, hashes and command provenance are in
[`cold_bag_failed_run_36274548282/`](cold_bag_failed_run_36274548282/); the raw archive and database
were removed by CI and are not committed.

Run [36277608569](https://github.com/pmixay/ReSense/actions/runs/36277608569) tested the
cadence-preserving code on the original bag but still failed freshness and post-+5 s accounting:
91/201 frames were processed, first STOP was +0.8 s, and five messages remained after +5 s. The
default rosbag2 read-ahead had preloaded a backlog before the node's first result. A follow-up with
read-ahead set to one downloaded and verified the same bag but delivered no LiDAR input during a
12-minute wait; it was cancelled as an invalid playback setup. Its 1,380 no-input watchdog rows are
preserved in [`cold_bag_cancelled_run_36278988540/`](cold_bag_cancelled_run_36278988540/). The
Run [36280434044](https://github.com/pmixay/ReSense/actions/runs/36280434044) passed the original
360-degree `doubleT_obstacle` cold replay with read-ahead ten: 201 status messages, STOP +1.1 s,
55.5–56.6 m, 78 ms decode-plus-detect p95, freshness PASS, and zero original bag messages
unprocessed after catch-up ([preserved evidence](cold_bag_passed_run_36280434044/)). Its player
read-ahead is explicit because the default 1,000-message setting preloads all 201 original-bag
messages before publishing. The 120-degree `roundT_doubleT` cold clear replay is being added;
keep C5/C7 partial until that check also passes. The default-read-ahead cold run still has no fresh
result, so this does not claim support for an unbounded overdue burst.

## Follow-up and remaining work

The failure showed that a 20 s startup lag allowance with 0.3 s frame sampling could still let
scene-reset gaps consume the recording. The branch follow-up keeps every observed input-period
frame during the first backlog, even when the preceding recording left a slower period estimate.
After that catch-up drains, live backlog behavior returns to the 0.3 s sampling step and 5 s lag
bound. Run 362804 passed the bounded-prefetch cold `doubleT_obstacle` replay, but the
default-read-ahead whole-bag burst remains stale and the matching cold clear-bag run is pending.
Keep action 21 and C7 partial until both original recordings pass and the captain accepts the
bounded-prefetch procedure; do not claim support for an unbounded overdue burst.

The remaining human tasks are the physical second-device Foxglove layout import/rehearsal and the
presentation details the team has not supplied: city, team-formation details and a group photo.
The user's supplied names, school and portraits are used only in the local private preview.
