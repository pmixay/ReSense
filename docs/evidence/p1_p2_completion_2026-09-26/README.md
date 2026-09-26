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

## Follow-up and remaining work

The failure showed that a 20 s startup lag allowance with 0.3 s frame sampling could still let
scene-reset gaps consume the recording. The branch follow-up keeps every observed input-period
frame during the first backlog, even when the preceding recording left a slower period estimate.
After that catch-up drains, live backlog behavior returns to the 0.3 s sampling step and 5 s lag
bound. The 47 node tests and local full suite pass, but the corrected behavior has **not yet passed
the original-bag cold-cache CI replay**. Keep action 21 and C7 open until that test passes; do not
claim the startup issue resolved from unit tests alone.

The remaining human tasks are the physical second-device Foxglove layout import/rehearsal and the
presentation details the team has not supplied: city, team-formation details and a group photo.
The user's supplied names, school and portraits are used only in the local private preview.
