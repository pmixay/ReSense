# Low object height continuity candidate — 28 September

Status: **provisional, disabled by default**. The candidate needs the strict full regression gate
and the independent reserved evaluation before acceptance. This work uses a previously inspected
organizer recording and generated development scenes; it is not holdout evidence.

## Cause

A read-only observer around the production low-object stage found that the real rail object
continues returning 10–15 points during the three STOP gaps. Its straddle blob still satisfies the
point-count and shape requirements. The blob is discarded because its observed top falls just
below `lowobj.straddle_min_top = 0.10 m` for two consecutive frames. The existing one-frame miss
hold then expires. Association does not cause these gaps.

| Lost STOP frame | Observed top on preceding frame | Observed top on lost frame |
|---|---:|---:|
| 111 | 0.09773 m | 0.09265 m |
| 117 | 0.08185 m | 0.09621 m |
| 197 | 0.09421 m | 0.09394 m |

The diagnostic ROI is the spatial window documented by the existing rail-object labels. It is
only passed to the observer. The algorithm receives no recording, frame index, label, or target
location. The paired replay stores the actual low-stage return conditions and point counts in
`raw/height_trace.jsonl.gz`, with code, original bag, config, labels, and output hashes in
`raw/summary.json`.

## Candidate

The [candidate config](candidate.yaml) enables `tracking.stop_keep_low_s = 0.3` and uses a
`lowobj.straddle_keep_height_margin = 0.03 m` height margin. Its rules are:

- A current straddle blob may narrowly fail the top-height threshold. The existing bed anomaly,
  point-count, width, length, tall-object foot, and duplicate filters still apply.
- Such a blob is separate from normal candidates. It cannot seed a track or confirm a new STOP.
- It can continue only an unmatched, already reported gauge track whose last hit was low.
  The observed centre must be within 0.25 m of the prediction and its shape must stay within
  half to twice the last clean shape, with small allowances for zero observed extents.
- A blob agreeing with more than one track is unused. Marked rail geometry is unused.
- Weak observations gain no confidence, never replace the clean shape reference, and never
  reset time since the last clean hit. Continuation expires after 0.3 seconds of measured
  sensor time. The ordinary missed-frame hold cannot extend a weak continuation past that cap.
- A first weak observation arriving after the cap is rejected; the existing first-miss hold
  still applies to the preceding clean observation. This does not add persistence.

The [registered acceptance criteria](acceptance.json) require 126/126 target STOP frames after
frame 75, 61/61 person hits, no new raw unmatched detections, no full-gate regression, and safe
removal/transient behavior. A global two-frame hold was already rejected for false detections;
this candidate requires current object evidence.

## Checks

The initial raw replay restores 126/126 rail-object hits after frame 75 (from 123/126), keeps the
person at 61/61, and leaves the same six unmatched detections at frames 69–74. Total visible
rail-object hits rise from 125/185 to 128/185.

Focused tests cover weak evidence passed through either tracker API path, new-track prevention,
0.05/0.1/0.2/0.3-second intervals, expiry and ordinary hold, clean-hit recovery, removal,
ambiguous tracks, mismatched shape, drift from the clean shape, corridor tracks, rail geometry,
and moving low objects. Explicit sparse-return scenes at 18, 28, and 42 m exercise the corridor,
bed, clustering, and tracker stages together. Two-frame height jitter is bridged; removal clears;
weak-only and short transient objects never become STOPs; permanent weak evidence expires.
These scenes describe returns directly and do not measure ray-cast sensor recall.

The paired raw controls retain original timestamps. All four schedules have zero new labelled
misses and zero new unmatched detections:

| Input schedule | Rail object after frame 75, baseline → candidate | Person, both |
|---|---:|---:|
| Every frame | 123 → 126 / 126 | 61 / 61 |
| Every second frame | 63 → 63 / 63 | 29 / 31 |
| Bursts, indices modulo six in `{0, 1, 2, 5}` | 84 → 84 / 84 | 40 / 41 |
| Fresh detector at frame 75 | 110 → 113 / 126 | no visible person labels |

The reduced-rate person misses and fresh-start warm-up misses remain limitations of the existing
system. The disabled candidate matches all checked decision, clear-distance, candidate, and mount
fields of the archived raw baseline exactly. Counts, original input timestamps, and the comparison
are in [raw/summary.json](raw/summary.json). Instrumented and concurrent replay timings are not
latency evidence.

Relevant existing and new tests passed: 118 tests without ray casting or recorded-data inputs;
the recorded rail-start check passed separately on the freshly cached original segment. A first
attempt at that check failed because the historical cache directory lacked its required frame,
before the complete cache was supplied. The full detector suite and regression gate remain the
integration lane's acceptance checks.

## Reproduce

From the repository with its Python dependencies and native kernel built:

```bash
python scripts/evaluate_low_height_keep.py \
  --bag /data/for_hackathon/doubleT_obstacle \
  --candidate docs/evidence/cycle_2026-09-28/continuity/candidate.yaml \
  --out out/continuity_replay

python -m pytest -q tests/test_low_height_keep.py tests/test_stage_trace.py \
  -m 'not synthetic'
```

The default full schedule compares the disabled candidate's decisions with the archived raw
replay. Unrounded fitted track coefficients are excluded from exact cross-environment comparison:
they differ at approximately machine precision between numerical-library versions. Reported
obstacles, warnings, distances, candidates, clear distance, and mount state are compared exactly.
