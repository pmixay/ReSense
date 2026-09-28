# Direct Fresh STOP provenance and local-body support — 28 September 2026

**Decision: no new detector rule.** An instrumented replay now captures actual Fresh STOP
confirmation sources, descriptor inputs, current point indices, effective strict/rail masks, voxel
memberships and fitted references. The same fixed, label-blind local decomposition rescues resolved
synthetic person/cable subsets, but a retained false event passes the identical ordinary descriptor.

## Direct replay and parity

[`scripts/trace_fresh_support.py`](../scripts/trace_fresh_support.py) warms each selected ride piece
from its original detector reset. It hashes every processed raw cache frame against the audited
manifest. An independent plain detector and the instrumented detector both match the **saved fresh
configuration's semantic output** on every processed frame; only runtime-dependent latency/health
diagnostics are excluded. Source-default traces are used solely to schedule selected windows, not
to assign fresh hit provenance. The audited residual inventory selects **all 27 remaining event
identities** across eight reset-separated pieces. Replaying prefixes through their last selected
observation covers **9,255 paired frames** of the 11,271-frame ride and all **133 STOP track-frames**;
there are **671 observed track rows**, **494 actual matched rows**, and **467 consecutive matched-pair
comparisons**. Unioning overlapping track alarms by piece gives exactly **117 node STOP frames and
26 episodes**. This covers all remaining event identities, but is not a new full-ride replay: the
unselected tails of some pieces are not processed. A timed-out parallel run wrote seven verified
pieces; `--resume` validated their frame manifests/semantic parity and finished the last piece.

Per matched row, the trace stores the actual `_note` input route and before/after bounded evidence,
`_fresh_stop_ok` calls, tracker state, exact descriptor component and output membership, current
point indices, observed channels (never invented rings), effective strict/rail membership, voxel
IDs and unrounded `TrackModel` plus mount rotation. A missed row has **no current support**.
The [analyzer](../scripts/analyze_fresh_support.py) replays **439 actual accepted corridor
descriptors** using their original intensity, gauge, ring, wall/reference and far-height parameters;
all match their original emitted descriptors. Low-stage eligibility is explicitly separate from
strict polygon membership.

The large raw trace (including frame-local points and manifest hashes) is kept at
`C:/Users/alikh/AppData/Local/Temp/opencode/direct-fresh-support-all/`; the compact, reproducible
comparison is [`evidence/results/fresh_local_support_2026-09-28.json`](evidence/results/fresh_local_support_2026-09-28.json).
Both output artifacts include SHA-256 provenance. The full data capture is local, not committed.

## What the Fresh histories show

At the first STOP of **all 27** captured events, the **actual** fresh gate returned true: 18 ordinary
and nine low onsets. Nine illustrative histories, including mixed low/ordinary support and compact
strict bodies, have these last bounded provenance entries:

| Event suffix | First STOP | Bounded onset provenance | Exact local ordinary body at onset |
|---|---|---|---|
| `1:74` | 1847 | ordinary / off-gauge / ordinary | none; local strict body demoted beyond height reference |
| `1:286` | 2668 | ordinary × 3 | low-stage onset; corridor-body test inapplicable |
| `1:292` | 2671 | ordinary × 3 | low-stage onset; corridor-body test inapplicable |
| `1:293` | 2673 | ordinary × 3 | none; local strict body demoted beyond height reference |
| `1:298` | 2671 | off-gauge / ordinary / ordinary | none; local strict body demoted beyond height reference |
| `1:310` | 2675 | ordinary × 3 | none under the fixed 0.45 m local split |
| `1:306` | 2676 | ordinary × 3 | low-stage onset; corridor-body test inapplicable |
| `5:330` | 7859 | ordinary × 3 | one in corridor mode, none in strict mode |
| `6:331` | 9263 | ordinary × 3 | **one in both modes** |

These are nine selected examples from 27, not nine independent physical surfaces. `ordinary` is
the tracker's input route; it includes low-object candidates. The full event catalog remains in
[the inventory](RESIDUAL_EVENTS_2026-09-28.md).

The most informative local-distance counterexample is `1:74`: the emitted full cluster reaches
**155.44 m** (inside the **160 m** effective height-reference limit), while its isolated strict
body begins at **160.54 m**, has **10 strict voxels**, and is demoted by the existing descriptor as
`beyond_height_ref`. `1:298` similarly has an emitted near point of **82.54 m** inside its **85 m**
reference, but its **10-voxel** local body begins at **89.25 m** and is demoted. In the earlier
crop/proxy study, validity limits were unavailable, so those two local bodies appeared ordinary;
the exact descriptor corrects that interpretation. This result does not license a component-size
veto: a connected background point can be part of a real person, and no selector has been tested
against all positives.

For `6:331`, splitting retains a **19-voxel, 19-strict-voxel** local body with an existing ordinary
gauge result, in both corridor and strict modes; it overlaps the actual false track on this empty
ride. `5:330` also retains an ordinary corridor-local body. Compactness, local separation and
ordinary status therefore do not distinguish real from false by themselves.

## Common-reference test

Consecutive matched current-support points are reprojected under one **current mount rotation and
fitted rail/axis model**, alongside their original-reference gaps. This removes fitted-reference
changes from the comparison. It does **not** compensate the vehicle's translation, register a scene
by odometry, establish ray/point correspondence across frames or prove object identity. Synthetic
same-points tests confirm the transform eliminates an artificial axis/height gap; separate tests
retain genuine gaps and forbid stale missed-row support.

In `1:293` from fresh direct support, low `2671` → ordinary `2673` has a raw sensor-Y support gap
**0.560 m**, own-model rail-lateral gap **0.635 m**, and common-reference gap **0.575 m**. The
preceding low `2668` → low `2671` also leaves **0.558 m** under the common model. Reference motion
accounts for some of the descriptor gap but does not erase the visible support separation. It does
not prove that any of these returns belong to distinct physical objects. Conversely, `1:74` has
later own-model gaps **0.290 m** and **0.913 m** where the common-reference support gap is **zero**;
these occur *after* its first STOP, so they do not explain that onset.

The injected positive replay includes separately identified person/cable/edge/plank point subsets
for evaluation only. Applying the same transform to visible injected subsets shows zero >0.25 m
common-reference gaps on the two centre-person and two centre-cable sequences, but **two plank,
three edge-cube (split 47) and several rail-object** comparisons have larger gaps. Missing ray
support and changing visible patches remain counterexamples to a blanket temporal gap veto.

## Exact local-body comparison

Both centre and edge set F stress reports were **rerun with the fresh-onset configuration**, with
an independent uninstrumented detector on each of **12 sequences / 714 frames**. Every evaluation
row matches its saved fresh row and saved baseline row. The scripted local split has fixed XY
0.45 m voxel-neighbour radius and unchanged `min_samples=3`; injection IDs enter *only after*
runtime subsets are finalized. This is a point/descriptor counterfactual, not a detection replay
of a proposed selector; instrumented timing is not measured latency.

| Direct-fresh local subset | Exact existing ordinary result |
|---|---:|
| Missed centre-person, split 47, 114.8–77.7 m | **11/11** oracle-known target subsets recoverable |
| Missed centre-cable, split 47, 98.4 m | **1/1** recoverable |
| Fresh false `1:74`, `1:298` | **0/2** ordinary; both `beyond_height_ref` |
| Fresh false `6:331` | **ordinary in both local modes** |
| Fresh false `5:330` | **ordinary in corridor mode** |

These 12 recoveries show that a *candidate geometry subset* exists; they do not establish an
implementable target selector, automatic new STOP, range improvement, event reduction or recall
parity. A connected background component might contain a real obstruction even where its nearest
background point changes the descriptor's trust range. In the sparse edge cube/rail cases, local
separation cannot create the missing height or point count. The set F draws use frame-derived
synthetic placement on partial approaches; they do not replace surveyed real positives.

**Conclusion:** retain the original default-off Fresh STOP candidate and these read-only
diagnostics. No new production filter, thresholds, defaults, detector seal or release decision
follows from this evidence. A future narrow selector must first distinguish `6:331` from resolved
person/cable support with a runtime observable other than local compactness, then demonstrate full
paired ride/set O/stress replay, first/sustained positive range and uninstrumented latency.

## Reproduce

From the repository root (the temporary output parent must already exist):

```powershell
$py = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe'
$tmp = 'C:/Users/alikh/AppData/Local/Temp/opencode'
$measurement = 'D:/Datasets/ReSense/cross_ring_2026-09-28_measurement'
$stress = "$tmp/fresh-stop-positive-stress"
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'

& $py -m scripts.trace_fresh_support --measurement $measurement --cache 'D:/Datasets/ReSense/new_data' --out "$tmp/direct-fresh-support-all" --all-retained --jobs 4
# If a long run is interrupted after complete pieces, add --resume to validate and reuse those files.
& $py tests/test_range_shape_support.py replay "$stress/setF_fresh.json" "$tmp/range-shape-centre-direct-fresh.json" --paired-report "$stress/setF_base.json" --config 'configs/experimental_fresh_stop_evidence.yaml'
& $py tests/test_range_shape_support.py replay "$stress/setF_edge_fresh.json" "$tmp/range-shape-edge-direct-fresh.json" --paired-report "$stress/setF_edge_base.json" --config 'configs/experimental_fresh_stop_evidence.yaml'
& $py -m scripts.analyze_fresh_support --fresh-trace "$tmp/direct-fresh-support-all" --positive "$tmp/range-shape-centre-direct-fresh.json" --positive "$tmp/range-shape-edge-direct-fresh.json" --out 'docs/evidence/results/fresh_local_support_2026-09-28.json' --summary-only
& $py -m pytest -q -p no:cacheprovider tests/test_fresh_support_trace.py tests/test_fresh_support_analysis.py tests/test_stage_trace.py tests/test_range_shape_support.py tests/test_local_body_support.py
ruff check --no-cache .
```

Final integrated check after all trace and analyzer changes: **247 passed, 1 deselected,
6 subtests passed**; repository-wide Ruff and `git diff --check` passed. The deselected test requires
Windows symlink privileges unavailable in this environment. The diagnostic replay itself is
single-threaded within each worker; its overhead is not a candidate latency measurement.

The negative direct trace includes all 27 retained identities, but only prefixes through their
selected windows; it does not include every rejected component elsewhere. The synthetic
oracle labels cannot be used by a runtime detector. Full Linux acceptance still needs the absent
organizer recordings.
