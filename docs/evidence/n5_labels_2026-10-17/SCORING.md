# N5 annotation scoring and independent review

These scores use the team's frozen raw-point annotations against the complete archived
v1.0.0 and v1.1.0 runs. They measure the annotated development recordings. They do not
turn uncertain gauge placement into a negative label, claim organizer intent, or establish
held-out recall. The scorer was written separately from the annotation builders; neither
detections nor decisions supplied object locations or gauge truth to those builders.

From the repository root:

```sh
python docs/evidence/n5_labels_2026-10-17/reproduce_scores.py
python -m pytest -q tests/test_score_team_labels.py
```

The reproducer reads the committed `detector_runs.tar.xz`, verifies complete frame alignment
through the scorer, and writes six per-run reports plus `scoring_summary.json`. Each report
records the archive, member, annotation and scorer hashes. The input archive has full runs
of 386 platform, 736 switch and 545 tunnels frames; partial runs cannot substitute for them.
The standalone CLI also supports a JSONL or compressed JSONL input:

```sh
python scripts/score_team_labels.py run.jsonl --gt labels.json --out score.json
```

## Coordinate and matching contract

Annotations use forward = -sensor Y, left = sensor X and up = sensor Z. Archived detection
centres use the calibrated vehicle frame. Independently inspected calibration code starts
with the identity rotation, applies nonzero tilt with a `provisional` status, and freezes
with `identity` only when the final matrix is identity. All six complete archived runs have
190 `pending` frames followed only by `identity`; no alternate orientation can persist and
produce that final identity. The raw mapped and calibrated vehicle frames therefore agree
for these captures. Track-relative `lateral` is deliberately ignored by this scorer.

The protocol was fixed before scoring the new labels. A detection matches an annotation
when its nearest-forward distance differs by at most `max(2 m, 3% of distance) + half observed
object length`, their sensor/vehicle lateral bbox centres differ by at most 1 m, and the
gap between their observed vertical extents is at most 0.5 m. This last condition prevents
matching an overhead feature to a ground object merely because range and lateral agree.
This is a separately named protocol, not a silent replacement for the old track-relative
`score_fake_objects.py` metric.

Only positive-return rows in the forward hemisphere through 250 m enter object recall.
The decoder's 2.5 m **radial** filter is not reapplied as a forward-distance filter; supported
near-pass labels at 1.8–2.4 m forward remain eligible. Rows with no return or outside the
forward range are counted as exclusions. Sparse support and uncertain gauge placement
remain explicit in the annotation and score population.

## What the bounds mean

Matching is one-to-one and maximizes the number of matched objects. One detection cannot
count as two true positives. For a selected object subset S, with maximum matching size K,
its matched-count lower bound is `K - max_matching(not S)` and its upper bound is
`max_matching(S)`. Tests independently enumerate every 3-by-3 bipartite graph and valid
assignment to verify these bounds. Per-object bounds can be wider than the aggregate
count; summing their upper bounds would double-count assignment ambiguity.

- `inside` is a certain positive, `outside` a certain negative, and `boundary_uncertain`
  or `unknown` may be either. The latter require `in_gauge: null`; false or missing values
  are rejected. Original detector-measured gauge fields are retained only as provenance.
- True STOP lower bounds count certain-inside matches unavoidable in maximum assignments.
  Upper bounds allow ambiguous gauge rows to be inside. The corresponding false bounds
  allow those rows to be outside.
- All three annotation sets declare `exhaustive_obstacles: false`: their scope is the
  reviewed synthetic objects. A STOP with no matching label is **unresolved**, not an
  automatic false positive. Its false bound is 0–1. Full frame coverage is distinct from
  exhaustive point segmentation and exhaustive scene truth.
- First STOP and warning matches are reported for every supported object regardless of
  gauge certainty. Certain-inside recall is reported separately. The held-from statistic
  means at least 90% of supported rows at that distance or nearer have a certain assignment;
  it can lie beyond the first actual STOP because it permits up to 10% misses.

These are conservative assignment/classification bounds conditional on the annotations
and matching protocol, not statistical confidence intervals. False-alarm totals count
detections, not scan frames. Per-object observation rows and STOP-frame summaries allow
each bound to be inspected.
`true_stop_detections_bounds` covers matches to the annotated objects; it does not classify
the unmatched detections as true or false. With non-exhaustive labels these two intervals
are not a partition of every STOP into a known true/false outcome.

## Frozen results

The final files cover **1,667 frame keys and 12 object tracks**, with 1,684 supported object
rows. All three v1.0.0/v1.1.0 semantic score reports are identical. This is a comparison of
the archived runs against new annotations, not a new detector replay or an improvement claim.

| Recording | Frames | Objects / supported rows | Certain-inside STOP matches | False STOP detection bounds | Unmatched STOP detections |
| --- | ---: | ---: | ---: | ---: | ---: |
| Platform | 386 | 3 / 696 | 147 / 171 (85.96%) | 0–38 | 0 |
| Switch | 736 | 5 / 692 | 36 / 36 (100%) | 0–106 | 12 |
| Tunnels | 545 | 4 / 296 | 61 / 63 (96.83%) | 0–67 | 10 |

All certain-inside rows are at **60 m or nearer**. The percentages are conditional on that
population, not all-range recall. The nonzero upper false bounds retain ambiguous rail-edge
alarms and unresolved background matches; a zero lower bound is not proof of zero false alarms.
Switch has 109 frames with uncertain object support, tunnels 36; complete frame keys preserve
these periods explicitly instead of silently counting them as certain empty scenes.

| Recording / object | Supported rows | Matched STOP rows | First matched STOP distance | Matched warning rows |
| --- | ---: | ---: | ---: | ---: |
| Platform `obj01` rail-edge box | 177 | 38 | 86.76 m | 41 |
| Platform `obj02` outside object | 190 | 0 | — | 30 |
| Platform `obj03` person | 329 | 147 | 44.01 m | 127 |
| Switch `box_right_1` | 256 | 11 | 110.59 m | 101 |
| Switch `box_left_2` | 102 | 32 | 51.38 m | 9 |
| Switch `hanging_3` | 139 | 42 | 69.13 m | 5 |
| Switch `box_left_4` | 54 | 4 | 23.38 m | 0 |
| Switch `box_right_5` | 141 | 41 | 104.02 m | 31 |
| Tunnels `box_right_1` | 102 | 30 | 55.00 m | 0 |
| Tunnels `panel_2` | 102 | 51 | 96.83 m | 13 |
| Tunnels `flat_crossrail_3` | 42 | 37 | 70.39 m | 0 |
| Tunnels `box_left_4` (newly found) | 50 | 0 | — | 7 |

First-match distances and warning counts above include uncertain-gauge rows. They identify
object matches, not necessarily true alarms under a certain gauge label. All actual per-object
assignment bounds collapse to the displayed counts on these captures, while gauge uncertainty
remains. Warning counts can overlap STOP matches and are not additive recall denominators.

Frozen annotation SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `labels_synthetic_platform.json` | `03578bd979d5a10d1067f4b83759d0863ccfa20e7e01c5c809d790d69e210ad7` |
| `labels_synthetic_switch.json` | `b6307eb801525ad5da4ac89cc3425ff337a02569effa0608b137e7e836fc49e6` |
| `labels_synthetic_tunnels.json` | `b1e7c5b081914f6bd480b83bafbc551be338dccb93f4615c1a44f5d95da3bc7b` |

The scorer's focused suite passed **18 tests**, including malformed/partial evidence,
null-label handling, unresolved alarms, coordinate mismatch, duplicate assignment and exhaustive
small-graph bounds. Both pinned CI Ruff 0.15.8 and local Ruff 0.17.1 passed the scorer, tests and
reproduction script. The root independently reviewed the scorer before final scoring.

## Independent annotation checks

The reviewer inspected the raw seed views, complete trajectory plots and far/mid/near
contact sheets separately from the labeller. This confirmed distinct geometric shapes
for boxes, the central hanging obstruction, the cross-corridor panel and flat object.
Rail-edge boxes retain boundary uncertainty; curved distant placements and sparse shape
support do not acquire certain gauge labels from a detector track axis.

The review caught a near-pass trajectory error in switch `box_left_4`: from frame 548 the
provisional tracker had followed sparse background in front of the actual dense box face.
The labeller replaced those points using the raw planar geometry before freezing labels.
The root review also found a fourth tunnels box absent from the old three-object inventory;
it was added before final scoring. These corrections are part of annotation review, not
detector tuning. Small stray returns in reviewed boxes remain possible; the annotations
do not claim exact point segmentation without a reference cloud.

Platform's exact-reference portion supplies a useful positive control for the extension
procedure, but cannot establish the precision of all switch/tunnels boxes or prove that
no unannotated structure could be an obstacle. The labels, explicit unknown periods and
non-exhaustive scope preserve that limit.
