# P4 Data and Evaluation Audit

> **Purpose:** P4's audit of synthetic placement, evaluation accounting and the organizers'
> synthetic-obstacle recording, with the corrections made and what they change.
> **Audience:** team, jury (spec §8.7) · **Owner:** P4 · **Language:** EN
> **Last verified:** 2026-09-26 against inherited P3d detector commit `fa18832` ·
> **Status:** historical audit plus the current P3d addendum below

Initial audit base: `a81108f` (v0.6.3, 23.09); integrated on `4cd32d6` (`main`, 24.09); merged as
`4b5786b` (PR #9, 24.09).

**Current-result addendum (26.09).** This audit preserves its 24.09 measurements. The current
[`_ride_p3d` regression baseline](evidence/results/regression_baseline_2026-09-26_ride_p3d.json)
records 125/126 rail-object hits after frame 75, the archived ride result of 45 false events in
13 km, 13 false events in five empty bags, and STOP for all 8 in-envelope organizers' objects
(384/801 visible object-frames). The inherited P3d STOP-keep rule raises the top box from
22/124 to 51/124 STOP frames; it first stops at 101.3 m and is held from 111.4 m. The P3c figures
and P4 reruns against P3c below remain historical. The P3d available-data results, candidate
decisions and completion checklist are linked in the next section. The 25.09 report of zero alarms
in the empty suffix of `cloud_with_fake_obj` is superseded: both original bag and quantized cache
have one false STOP frame / event in frames 804–1509, frame 1131 at 140.72 m; this is inspected
data, not unseen validation.

P4 did not change detector code or shipped defaults. The latest work-branch P3d detector was
merged only so that P4's evidence could be checked against the current baseline. All six original
bags and set O are verified at every frame. The `new_data` ride and set F remain unavailable here:
at the latest capacity check, the ride cache estimate plus the required 3 GiB reserve need at least
5.3 GB more free space. Do not infer ride or set F results from the six-bag rerun.

## P4 follow-up for score improvement

The P3d completion snapshot below is the current reference for this branch. The older P3c
available-data run later in this document is retained as dated history.

## P3d reference, bounded candidates, and completion (26.09)

The strict P3d reference gate ran without `--allow`. All six original recordings and set O match
the frozen P3d baseline with no worse gated rows; the gate exits 1 because 3 ride and 15 set F
straight rows are missing. Set O scores 384/801 inside STOP frames, 6 outside-object false STOP
frames, and 3 background alarm frames. Object #8 gets 51/124 STOP frames (first 101.3 m, held-from
111.4 m); #4 gets 2/83 and #6 gets 6/125. Its `clear_distance` audit has 54 overclaims in 505
target-envelope object-frames and 223 in 801 intent object-frames; 150 GO-judge overclaims include
62 target-envelope frames. The raw bag differs from its quantized cache (387/7/1 versus 384/6/3
inside/outside/background); the regression baseline remains cache-based. Full object, bin, missed
interval, and clear-distance data are in the
[`P3d available reference`](evidence/results/p4_p3d_available_reference_2026-09-26.json).

The five empty recordings produce 58 alarm frames, 13 events, and 16 STOP episodes over 2,287
frames and 229.776 s: 5.658 events and 6.963 episodes per 100 s. At 5 Hz they produce 38 / 10 / 10
over 229.574 s (4.356 / 4.356 events and episodes per 100 s); +3° roll gives 55 / 14 / 16
(6.093 / 6.963 per 100 s), and +3° pitch gives 44 / 17 / 18 (7.399 / 7.834 per 100 s). Five
start offsets produce 13/16, 13/14, 13/12, 10/11, and 7/11 events/episodes at offsets 0, 10, 20,
30, and 40. Rates use summed measured stamp spans. The startup census covers 7 available starts,
with 3 STOP starts, 6 track events and 3 STOP episodes; no ride starts were available.

The paired set S replay used the same 108 sample identities and trajectories as its P3c run and
the opposite P3d placement. Bed placement detected 22/67 visible in-gauge objects and legacy
placement 30/68; among 65 visible in both, eight were legacy-only and none bed-only. The extra
legacy trolley at 77.7 m has no isolated cause. This small synthetic sample is not surveyed ground
truth; see the [`P3d paired set S report`](evidence/results/p4_p3d_setS_paired_2026-09-26.json).

P3d candidate A (`tracking.near_escalate_distance` 35→40 m) leaves #8 unchanged at 51/124 and was
rejected at the set O screen. Candidate B (`tracking.near_escalate_voxels` 10→8) moves #4 from
2/83 to 3/83 STOP frames and from 5.2 to 7.1 m held-from. All other set O object scores,
outside/background false alarms, clear-distance overclaims, and six-original metrics stay equal.
Its strict gate has six better set O rows and zero worse rows, but 3 ride and 15 set F rows remain
missing, so B is **not accepted** and candidate-specific stress, offset, and paired-placement
checks were not run. Candidate C (`cluster.wall_keep_gauge_voxels` 10→8) leaves #6 unchanged at
6/125 and was rejected at the set O screen. No combined candidate or P4 detector change was
shipped. The short-signature relaxation remains rejected for increasing outside-object false STOPs.
Exact decisions and output hashes are in the
[`P3d candidate report`](evidence/results/p4_p3d_candidate_decisions_2026-09-26.json).

The current **67/100 provisional internal assessment** uses the repository's eight criterion
maxima, not published organizer weights. The inherited P3d gain is attributed to upstream detector
work, not P4; the independent 65/100 judgement remains on its original commit. See the
[`P3d scorecard`](SCORECARD.md), [`completion checklist`](evidence/results/p4_completion_checklist_p3d_2026-09-26.json),
[`independent review packet`](evidence/results/p4_review_packet_p3d_2026-09-26.json), and
[`P3d validation record`](evidence/results/p4_validation_p3d_2026-09-26.json). The software checks
pass (585 tests passed), but the ride-dependent rail-start test is deselected while the ride cache
is absent; the strict gate therefore remains incomplete.

The regression gate now protects set O's per-object held-from STOP distance, longest consecutive
missed interval, and each object's visible-frame denominator and STOP count in every distance bin.
The scorer also lists each contiguous visible interval without a STOP, with its frame and distance
limits. This prevents a gain in total STOP frames from hiding a regression at a particular range.
Existing false-alarm, outside-object and background checks remain in place; startup and mount/rate stress continue to use
[`startup_census.py`](../scripts/startup_census.py) and
[`robustness_check.py`](../scripts/robustness_check.py).

The P3c replay matched every previously recorded set O value exactly. The longest consecutive
visible misses are #4: 77 frames / 138.7 m of approach, #6: 110 / 210.3 m, and #8: 73 / 144.8 m.
These intervals explain why a binary “8 of 8” detection count overstates reliability.
A fresh-start replay of the first 40 set O frames reports one STOP from frame 5, matched to the
large centre box, and zero background alarms. It does not replace the 221-start ride census.

The remaining data-dependent work is to cache the `new_data` ride, reproduce the ride and set F
rows, and finish all acceptance checks for candidates A and B. Candidate C did not change its
target result. The known detector opportunities remain sustained detection of edge objects #4 and
#6 and the box at the top (#8), fewer false STOPs on the ride, and stronger unseen-condition
evidence. The axis-union candidate remains off: its earlier safety review found regressions when
widened envelope membership joined long edge structures to real objects. No detector parameters
were changed. The last independent judgement remains **65/100** on its original dated head; a
separate **66.5/100 provisional internal assessment** is recorded in the scorecard and is not an
independent organizer score.

## P4 available-data snapshot against P3c (26.09; historical)

The intake manifest records source URLs, archive/raw/cache hashes, frame identities, timestamp
coverage, and local paths. The six original bags contain 2,488/2,488 verified frames; set O has
1,510/1,510 frames. The full gate was run without `--allow` against the frozen P3c baseline. It
exited 1 because 3 ride and 15 set F straight metrics are missing; every locally available
recording and set O metric matched or improved on that baseline. No new baseline was made.
See [`p4_data_intake_2026-09-26.json`](evidence/results/p4_data_intake_2026-09-26.json),
[`p4_available_reference_2026-09-26.json`](evidence/results/p4_available_reference_2026-09-26.json),
and the preserved
[`artifact manifest`](evidence/results/p4_artifacts_2026-09-26/manifest.json).

The five empty original recordings produced 58 alarm frames, 13 alarm events, and 16 STOP
episodes over 2,287 frames and 229.776 seconds: 5.658 events and 6.963 episodes per 100 seconds.
By recording, `doubleT_platform` had 4/4/1 (alarm frames/events/episodes),
`squareT_platform_squareT_switch` 54/9/15, and the other three had none. These are repeated
frames on five recordings, not independent encounters. The frame intervals, track IDs, distances,
reason codes, and explicitly uncertain causes are in the
[`false-alarm inventory`](evidence/results/p4_false_alarm_inventory_2026-09-26.json).
On `doubleT_obstacle`, the labelled results are 58/61 person frames, 128/185 rail-object frames,
and 125/126 rail-object frames after frame 75; maximum reported distance error is 0.23 m and no
false event matched neither label. This agrees with the gate baseline.

Reference stress checks on the six recordings used timestamp-based elapsed-time rates. As
recorded: 13 events / 16 episodes in 229.776 s (5.658 / 6.963 per 100 s); 5 Hz: 10 / 10 in
229.574 s (4.356 / 4.356 per 100 s); +3° roll: 14 / 16 (6.093 / 6.963 per 100 s); +3° pitch:
17 / 18 (7.399 / 7.834 per 100 s). Across start offsets 0, 10, 20, 30, 40, the five empty
recordings produced 13/16, 13/14, 13/12, 10/11, and 7/11 events/episodes. The available startup
census covers only seven starts (six original recordings plus set O): 3 had STOP, with 6 track
events and 3 STOP episodes. It does not replace the 221-start ride census.

The cached set O replay reproduces 355 STOP frames over its 801 visible in-envelope object-frames;
objects #4, #6 and #8 receive 2/83, 6/125 and 22/124 STOP frames. The 0–50, 50–100 and
100–150 m bins, held-from distances, missed intervals, and clear-distance checks are in the
available reference JSON. Clear-distance overclaim totals were unchanged in the A/B/C screens:
56 target frames, 505 target frames considered, 225 intent frames, and 62 in-envelope GO-judge
frames. Set O's empty suffix (frames 804–1509) has one background STOP at frame 1131, 140.72 m;
it is previously inspected data, not unseen validation.

The original float bag and 5 mm-quantized int16 cache are **not score-identical** under the same
configuration and timestamps: cache 355 inside STOP frames / 6 outside / 3 background frames in
2 IDs; raw bag 357 / 7 / 1 in 1 ID. The regression baseline is cache-based, so candidate screening
used the cache. See the
[`raw/cache comparison`](evidence/results/p4_seto_raw_cache_comparison_2026-09-26.json).

The paired set S run reused 108 sampled objects and matching labels, kind, distance, lateral,
yaw, size and reflectivity. Bed placement matched 22/67 visible in-gauge objects; legacy placement
matched 30/68. Eight of 65 objects visible in both were legacy-only, none bed-only. One additional
legacy-only trolley hit at 77.7 m was not isolated as a cause and is not credited as a detector
gain. Anchored placement remains an estimate, not surveyed ground truth. See the
[`paired set S report`](evidence/results/p4_setS_paired_2026-09-26.json).

Candidate A (`tracking.near_escalate_distance` 35→40) raised object #8 from 22 to 24 STOP frames
and extended its sustained held-from range from 23.9 to 27.5 m. Candidate B
(`tracking.near_escalate_voxels` 10→8) raised object #4 from 2 to 3 STOP frames and extended its
held-from range from 5.2 to 7.1 m. Neither had a gated regression on available recordings and
set O, but both full gates miss the ride/set F rows and their candidate-specific stress, offset,
and paired-placement checks were not completed. They are **not accepted and not shipped**.
Candidate C (`cluster.wall_keep_gauge_voxels` 10→8) made no change to object #6 and was rejected
at the set O screen. The short-signature relaxation was rejected: inside STOP frames rose 355→381,
but outside false STOP frames rose 6→9, including object #5 from 0→3. Decisions and score
details are in the
[`candidate record`](evidence/results/p4_candidate_decisions_2026-09-26.json).

### Historical P3c completion snapshot (26.09; superseded by P3d above)

- **Completed:** six original caches and set O verified; cache-based reference gate, startup,
  stress, start-offset, per-object/set O, clear-distance, false-alarm, and paired set S evidence
  recorded; A/B/C pre-registered and each screened; rejected signature relaxation recorded;
  provisional score and independent-review packet prepared. Pinned Ruff, parameter sync,
  pytest, browser-backed web checks, JSON/hash validation and `git diff --check` are recorded in
  [`p4_validation_2026-09-26.json`](evidence/results/p4_validation_2026-09-26.json).
- **Rejected or not accepted:** short signatures rejected for outside-object false STOPs; C rejected
  for no target improvement; A and B remain unaccepted because required data-dependent checks are
  unavailable. Shipped detector and historical baseline stay unchanged.
- **Open external/resource dependency at this P3c snapshot:** the initial capacity check estimated
  at least 4.1 GB of additional free storage to cache `new_data` while preserving the 3 GiB
  headroom. The latest P3d check estimates at least 5.3 GB. Ride and set F straight, 221 ride starts,
  paired set F curve/edge, and candidate acceptance checks remain open. The ride has no real
  obstacles; synthetic positives cannot establish real long-range recall or material robustness.

## Findings and corrections

| P4 criterion | Finding | Correction | What has been verified |
|---|---|---|---|
| Set S placement | `place_on_bed` existed but `resense inject` never called it. Ground objects were placed at rail head − 0.15 m even where the real bed was lower, and the far model could place them under the bed. | Injection now defaults to the local bed or rail head − 0.25 m plus measured vault drift and stores `base_z` in `gt.json`. `--placement legacy` reproduces the old height under the new paired-run RNG protocol. | Synthetic bed/vault cases and paired runs on 108 frames of three real empty bags: 22/67 visible in-gauge hits with bed placement versus 29/68 with legacy height. Corrected placement lowers the apparent recall; see below. |
| Set F independence (review of 24.09: set F placement must not come from the detector's own far axis) | The object's Y position was recomputed from the detector's own far axis every frame, reducing the apparent cost of axis errors on curves and near the envelope edge. Missing or invalid timestamps also silently fell back to a 0.1-second motion step. | `scripts/far_range_eval.py --placement-mode anchored`: a rail-supported track fit when the object is within 30 m defines its location; near track fits in consecutive empty frames transport that location back through the sequence. `--placement-mode legacy` reproduces the old placement. Recording gaps over 5 m, missing near references, and missing or invalid timestamps are reported as skipped. `--placement-mode independent` also remains available for externally surveyed fixed references. | Known rigid-transform and wrong far-axis regressions, then a paired run on seven organizer sequences: one skip due to a 24.5 m recording gap; see below. Anchoring uses estimated speed and near-track registration, not surveyed ground truth. |
| Set S / sequence evaluation | `resense eval` carried tracker state from one unrelated injected background or approach sequence into the next. | The tracker resets at each injected `seq` boundary. | A two-sequence injected run shows no alarm on either sequence's first frame. |
| False-alarm events | Tracker IDs restart at a sequence boundary, but the evaluator counted raw IDs globally. A false event in one sequence could disappear if the same ID matched ground truth in another. | Event identity is `(sequence, track ID)`; `eval --out` includes `seq` so `summarize` reproduces the count. | An ID-reuse regression and the JSONL round trip. |
| Sequence time/distance | Synthetic approach sequences are independent, but the evaluator integrated timestamp gaps between them as travelled time and kilometres, producing spurious rate denominators. | For scoped `seq` rows, only within-sequence elapsed time and distance are accumulated. Continuous real bags retain their original span accounting. | A two-sequence regression with a 9.9 s inter-sequence gap and a missing-stamp case. |
| Multiple real objects | First-fit matching could give a detection shared by two objects to the wrong one and report a false miss. This matters where the person and rail object overlap. | Maximum-cardinality one-to-one matching, with position error breaking ties. | An ambiguous two-object regression. The six-bag rerun reproduces the published real counts: crossing person 58/61, rail object 127/185. |
| Label and protocol accuracy | The label metadata said the current `gauge_margin` used 1.4 m, while all current rows and the code use 1.05 m. The injector used another stale 1.3 m lateral cutoff for `in_gauge`. Dataset and evaluation notes described the old 3-hit and 1.4 m protocol as current, and described `new_data` as if it might contain positives. The real-evaluation script also hard-coded 3 hits for stride accounting. | Corrected the metadata and current protocol notes; injected labels now use the rotated object footprint against the strict 1.05 m width. The real-evaluation script takes confirmation and frame interval from the selected config. Historical v0.4 numbers are explicitly marked as such. | All committed margin values agree with the 1.05 m rule within their rounding, the crossing person is in-gauge on frames 8–68, and rotated edge-object cases are tested. |
| Reflectivity calibration | The catalogue's person and rail-object intervals do not fully cover the observed per-frame mean intensities in the committed labels. The extended ride contains no obstacles, so it cannot supply more positive materials. | Documented the real-label percentiles and added `--reflectivity` to the injector and set F for paired material sensitivity runs; kept the historical catalogue defaults intact. | A fixed-reflectivity run keeps the same seeded object geometry. Long-range dropout remains an assumption. |
| Paired-run reproducibility | `resense inject` used one random stream for object selection, background augmentation and ray-cast dropout/noise. A placement or reflectivity change could alter the next frame's sampled object despite an identical seed. Set F also carried ray-cast RNG state across frames. | Set S planning now has its own stream; augmentation and ray casting use per-background/per-step streams. Set F ray casting is likewise seeded per frame. The GT metadata names the set S RNG protocol. | A two-background reflectivity regression and the real 108-object height pair check identical catalogue choices, positions and yaw. Old and new sets must be regenerated under one protocol before a paired comparison. |

The current real labels contain repeated views of one crossing person, one walking person and
one rail object. Their 5th / median / 95th percentile mean intensities (rows with at least 15
points) are 35.7 / 59.8 / 68.2, 39.1 / 74.4 / 96.1 and 13.6 / 15.4 / 22.5 respectively.
These are not independent samples of clothing or materials, and all are near 55 m. They cannot
justify replacing the catalogue ranges for long-range tests. See [`DATASET.md`](DATASET.md).

## New original-bag measurements

The full-rate rerun of all six original bags reproduces the v0.6.3 counts: **107 alarm frames / 20
events on 2 287 empty-bag frames**, and on `doubleT_obstacle` **58/61 crossing-person frames,
first alarm frame 11, plus 127/185 visible rail-object frames**. This checks the P4 matching
change against the committed real labels; it does not validate synthetic long-range placement.
These runs overlapped archive extraction and other jobs on this workstation, so their latency
figures are not comparable to the repository's controlled timing measurements.

**Integration on `4cd32d6` (24.09):** a full-rate rerun on the local six-bag cache again
produced 107 alarm frames / 20 events on the five empty bags and 185/246 matched labelled
obstacle-frames on `doubleT_obstacle`, first alarm frame 11. The cache and config were those
selected by `scripts/eval_real.py --cache /data/cache --bags
doubleT_obstacle,doubleT_platform,roundT_doubleT,roundT_pressureGate_roundT,roundT_squareT_pressureGate_squareT,squareT_platform_squareT_switch`.
Latency and health warnings from that concurrent, uncalibrated workstation run are not
benchmarks.

For set S, the same seed and new separated RNG protocol placed exactly the same 108 sampled
objects in three empty backgrounds (`roundT_doubleT`, `roundT_pressureGate_roundT`,
`roundT_squareT_pressureGate_squareT`, every 10th frame) for both height modes. There were 91
in-gauge objects; 65 were visible in both. The numbers below are confirmed matches among
*visible* in-gauge objects (fully occluded objects are excluded by the evaluation protocol):

| Object or distance | Bed (current default) | Legacy rail-height placement |
|---|---:|---:|
| All classes | **22/67** | **29/68** |
| Person | 8/9 | 8/9 |
| Box 0.5 m | 0/13 | 0/13 |
| Box 1.0 m | 5/14 | 5/14 |
| Plank | 0/13 | 4/14 |
| Trolley | 9/18 | 12/18 |
| 0–50 m | 13/18 | 16/18 |
| 50–100 m | 9/23 | 11/24 |
| 100–150 m | 0/16 | 2/17 |
| 150–250 m | 0/10 | 0/9 |

On the 65 objects visible in *both* runs, bed placement matched 22 and legacy placement 29:
seven legacy-only hits, no bed-only hits (four planks and three trolleys). This is evidence that
the old, higher placement flattered set S for low objects, not evidence that the detector
became worse. These are small synthetic samples on real backgrounds, not a new 150–250 m
capability claim. The 0.5 m boxes in this seed fell in sparse/poor-visibility scenes; do not
generalise the 0/13 result to every box. Static set S repeats one frame to satisfy the
five-hit rule; its false-event rates and wall-clock latency are not operational metrics.

An initial extended-ride smoke test (51 frames from split file 30) with a
paired **near-range smoke test** with `--files 30 --start 40 --frames 45 --kinds
person,box1.0 --lateral=0:0 --seed 1 --jobs 1` and `--placement-mode legacy` / `anchored`
completed without skips. Each mode saw 31/35 visible hits for both synthetic objects, first
confirmed at 36.3 m. The anchored near reference came from frame 11; the modes differed by at
most 0.23 m in object Y, so this slice barely tests the axis-bias problem. The box had two
versus four unmatched detections under legacy versus anchored placement. These counts are
synthetic positives on a single short approach **below 40 m**, not long-range recall, and
cannot replace the extended curve and gauge-edge comparison below.

## Paired extended-ride range audit (24.09, selected curve and edge scenes)

The organizer archive (SHA-256 in [`DATASET.md`](DATASET.md)) was downloaded and verified.
Selected contiguous full-rate split files 127–135, 160–168 and 175–181 were cached with real
receive timestamps. Both modes used the **same seed, config, sampled lateral/reflectivity and
frame selection**; `scripts/compare_setf.py` checks these and excludes a skipped trajectory
from *both* denominators. The raw configurations, per-frame truth, visibility and detection
rows are reproducible with the commands below; the compact per-sequence report, config and
timestamp hashes are committed in
[`experiments_p4_setf_paired.json`](evidence/results/experiments_p4_setf_paired.json).

```bash
python scripts/far_range_eval.py --cache /data/cache/new_data --files 127,129,131,160,164,175,177 \
  --kinds person,box1.0 --start 160 --frames 220 --lateral=-1.0:1.0 --seed 0 \
  --placement-mode legacy --out out/setf-frame.json
python scripts/far_range_eval.py --cache /data/cache/new_data --files 127,129,131,160,164,175,177 \
  --kinds person,box1.0 --start 160 --frames 220 --lateral=-1.0:1.0 --seed 0 \
  --placement-mode anchored --out out/setf-anchored.json
python scripts/compare_setf.py out/setf-frame.json out/setf-anchored.json --out out/setf-paired.json
```

| Synthetic object | Paired approaches / skips | Legacy visible hits / returns | Anchored visible hits / returns | First confirmed, legacy → anchored (paired medians) |
|---|---:|---:|---:|---:|
| Person | 6 / 1 | 224/495 | 214/476 | 73.7 → 67.5 m |
| Box 1.0 m | 6 / 1 | 266/492 | 274/484 | 74.7 → 79.6 m |

In the 50–100 m visible bin, the person matched 82/199 (legacy) versus 69/204 (anchored),
and the box matched 98/202 versus 106/208. These are per-frame synthetic hits, not
independent physical objects or operating recall; the same six approaches per kind contribute
to both columns.

The recording gap in file 164 implies a **24.5 m motion step**: anchored placement skipped
both objects there, and the paired summary excludes that file's legacy result too. All six
paired approaches in each class have a first confirmed hit, but **neither mode matched any
visible object at 100–150 m** in these particular curve/edge samples (legacy person 0/116,
box 0/116; anchored person 0/102, box 0/103). The 50–100 m visible denominators and placement
geometry also differ between modes. The largest per-frame Y difference is 17.1 m on the curve
starting at file 127; even the earlier 110 m edge run at file 133 moved the person first hit
from 85.1 m (legacy) to 51.9 m (anchored). Differences are **sensitivity to assumed object
placement**, not independent surveyed recall. Near-rail fits and per-file speed estimates can
accumulate lateral error over a moving curve; no physical survey or real long-range positive
validates either trajectory. These selected scenes cannot support the historical 148 m median
person claim for the *current* code. The published set F numbers were produced on older code,
config and sampling and should only be quoted as dated self-referential results.

`far_range_eval.py` now stops at a missing split/frame rather than jumping to an unrelated
piece of the ride (a cache strided by `cache_frames.py --every N` is followed at its own step);
in anchored mode it rejects missing stamps or a near reference. A zero-return object cannot be
marked a hit. Since 24.09, a detection where it stands on such a frame (its own held
or accumulated track) is not counted as a false detection either. The curve/edge `false
detections` above were counted the older way and include such frames.

## Paired straight-track range audit (24.09)

The straight set of set F round 3 was re-run in pairs on the current code:

* files 46, 68, 98, 140, 168 and 172, 110 frames each, objects from 220 m;
* lateral −0.6…0.6 m, seed 0, the five kinds of round 3;
* `legacy` (the detector's per-frame far axis) against `anchored` (the object fixed where the
  near rails put it, then carried back through the approach).

18 split files were streamed from the organizers' link and cached at every frame with their
stamps. File 168 has a recording gap (a 65.4 m motion step), so anchored mode skips it, and the
paired summary drops it from both modes. Anchored placement differs from legacy by 0.4–1.1 m
in Y at the far end of the person approaches. Raw report:
[`experiments_p4_setf_straight_paired.json`](evidence/results/experiments_p4_setf_straight_paired.json).

```bash
python scripts/far_range_eval.py --cache /data/cache/new_data --files 46,68,98,140,168,172 --frames 110 \
  --kinds person,box1.0,box0.5,trolley,cable --start 220 --lateral=-0.6:0.6 --seed 0 --placement-mode legacy --out out/straight-legacy.json
python scripts/far_range_eval.py ... --placement-mode anchored --out out/straight-anchored.json
python scripts/compare_setf.py out/straight-legacy.json out/straight-anchored.json --out out/straight-paired.json
```

| synthetic object (5 paired approaches) | detected (both modes) | first confirmed, paired median: legacy → anchored | visible hits 100–150 m: legacy → anchored |
|---|---:|---:|---:|
| person 0.4 × 0.5 × 1.7 m | 5 / 5 | 149.9 → **154.1 m** | 94/125 → 97/125 |
| trolley | 5 / 5 | 148.1 → 148.1 m | 34/125 → 32/125 |
| crate 1.0 m | 5 / 5 | 116.1 → 109.9 m | 26/125 → 28/125 |
| cable 3 cm hanging to 1.0 m | 5 / 5 | 103.9 → 101.7 m | 12/80 → 5/87 |
| box 0.5 m in the bed | 1 / 5 | 51.9 → 51.9 m | 0 → 0 |

**On straight track the range does not depend on the detector's own far axis.** A person placed
from the near rails is first confirmed at a median 154 m (150–180 m). This supports the
historical ~148 m straight-track figure for the current code, unlike the curve and edge scenes
above, where neither mode matched anything beyond 100 m. It is still synthetic: the anchoring
uses the ride's rail fits and estimated speed, not a survey. The 0.5 m box on the bed stays at
1 of 5, as in round 3. The legacy person median over all six attempted sequences, 151.0 m,
differs from round 3's 148 m because set F now seeds the ray casting per frame (the dropout
draws differ), not because the detector changed.

## Organizer synthetic-obstacle recording (`cloud_with_fake_obj`, labelled 24.09)

The organizers' folder added `cloud_with_fake_obj.zst` on 24.09
([Yandex Disk](https://disk.yandex.ru/d/KpkG_yKoGk-vHQ), SHA-256 in [`DATASET.md`](DATASET.md)).
The first P4 pass scored it unlabelled on all **1 510 frames**: 342 alarm frames, 9 alarm track
IDs, 459 advisory frames
([`experiments_p4_fake_unlabelled.json`](evidence/results/experiments_p4_fake_unlabelled.json)).
The organizers then described the ten obstacles and their order. The object points turned out
to be recoverable exactly: every message is the organizers' real scan followed by the object
points (intensity 1). So the recording is now labelled: `scripts/label_fake_objects.py` →
[`labels/cloud_with_fake_obj.json`](../labels/cloud_with_fake_obj.json), 1 206 object-frames of
ten objects in frames 0–803. How the labels are made, and three properties that limit how they
can be read, are in [`DATASET.md`](DATASET.md) "Synthetic-obstacle recording". In short:

* the objects stand still in the tunnel and the train drives up to them at 1.4–20 m/s (corrected
  24.09: an earlier ICP had the train backing up; [`EXPERIMENTS.md`](EXPERIMENTS.md) §9);
* they are placed from the sensor's axis, which runs at −0.24° to the rails here, so the edge
  tests sit within ±0.1–0.4 m of the envelope edge;
* beyond ~100 m their path leaves the tunnel. Those rows are graded out (`plausible`).

**Grade of the shipped detector (default config, every frame, no speed given).** Produced by
`scripts/score_fake_objects.py`. "Visible" counts plausible frames with at least one return;
"in measured envelope" counts frames with a point inside the envelope measured from the rails.
STOP is an alarm frame (`detections`), advisory is `warnings` only.

| # | object (organizers' intent) | visible frames (from) | in measured envelope | STOP frames | advisory only | first STOP | STOP held from | verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | 2×2 m, centre (inside) | 213 (98.7 m) | 213 | 207 | 0 | 98.0 m | 98.7 m | detected at first sight |
| 2 | 0.3 m, centre, floating 1.0–1.4 m up (inside) | 79 (128.9 m) | 63 | 19 | 11 | 34.0 m | 37.4 m | detected late |
| 3 | 0.3 m, on the left rail (inside) | 49 (237.3 m) | 33 | 23 | 0 | 42.7 m | 46.2 m | detected |
| 4 | 0.3 m, at the edge (inside) | 83 (154.7 m) | 16 | 0 | 25 | — | — | advisory only |
| 5 | 0.3 m, just outside (outside) | 112 (238.4 m) | 101 | 0 | 24 | — | — | correct: no STOP |
| 6 | 2×2 m, at the edge (inside) | 125 (248.6 m) | 8 | 0 | 0 | — | — | missed |
| 7 | 2×2 m, outside (outside) | 104 (249.4 m) | 52 | 6 | 44 | 142.3 m | — | 6 false STOP frames |
| 8 | 2×2 m, top of the envelope (inside) | 124 (248.2 m) | 75 | 12 | 37 | 101.3 m | — | mostly advisory |
| 9 | 2 × 0.2 m, across the rails (inside) | 86 (248.5 m) | 77 | 42 | 0 | 82.2 m | 58.6 m | detected |
| 10 | 0.05 m, hanging from the roof (inside) | 42 (199.7 m) | 20 | 0 | 0 | — | — | missed |

Alarm tracks that never match a labelled object (counted like `fp_events`): 2 IDs in 3 frames,
at 129–141 m in frames 666–667 and 1131. Six more IDs are unmatched in some frames and matched
to an object in others:

* three pass within 2.5 m of the sensor after their labels end;
* one is the inner edge of #7, just beyond the 1 m lateral match tolerance;
* one is #9, whose 4 m-long low cluster starts 4 m in front of it at 65 m;
* one (frames 213–226, reported at 3.0 m) is caused by the 2 × 2 m box. While the box is
  10–20 m ahead, its shadow hides the rails, the rail-height fit drifts by ~0.5 m and the bed
  2.5–8 m ahead reads as an obstacle. The STOP is right, but the distance is wrong. *(25.09: fixed
  since the rail-shadow rules of wf7/p3, kept by their review fixes `95ff725`: every STOP on #1 now
  reports the box at its own distance, largest error 0.46 m, none more than 1 m off; EXPERIMENTS
  §1h.)*

Standard metrics
(`resense summarize --gt`): recall 0.378 of visible in-gauge object-frames (0–50 m 113/227,
50–100 m 189/338, beyond 100 m 1/236). These are 1 206 frames of ten synthetic objects, not an
operating recall.

What the grade says, by cause:

* **Big objects in the corridor are found at first sight** (#1 at 98 m). The plank across the
  rails (#9) is found from 82 m and held from 59 m.
* **0.3 m objects are found at 34–43 m.** At 60–115 m the organizers' 0.3 m cube returns 2–4
  points a frame; the clustering needs 5 voxels within 100 m. A single frame cannot confirm a
  0.3 m object much beyond 50 m with this sensor. Accumulation needs an ego speed; with the
  train's measured speed it makes the 0.3 m cubes visible from 57–59 m instead of 43–51 m, but as
  advisories (the `floating` signature), and no first STOP comes earlier (one comes 3.4 m later;
  [`EXPERIMENTS.md`](EXPERIMENTS.md) §9).
  Lowering the minimums (`min_points 3`, `min_points_far 2` or `gauge_min_points 2`) changed
  nothing for them.
* **Two infrastructure signatures demote real test obstacles.** `floating` makes #2 advisory at
  47–52 m (lateral 0.70–0.78 m > `signature_min_lateral` 0.6), and #4 always. `elevated` makes
  #8 advisory in 36 frames: a 2 m wide cluster with its bottom above 1.2 m, although that bottom
  is 2.2–2.9 m above the rail head, inside the envelope.
* **The thin hanging object never becomes a candidate.** Only its lowest 0.2–0.36 m is inside
  the 3.0 m envelope, 1–4 points a frame. With `min_points 3` it alarms in 3 frames at 10 m.
* **Edge tests (#4–#7) depend on the reference frame.** Measured from the rails, #6 is outside
  in 117 of 125 frames and #5 inside in 101 of 112. The detector follows the rails. The
  organizers followed the sensor's axis. Setting `edge_margin_per_100m` to 0 only added false
  STOPs on #7 (6 → 40 frames) and in the background (3 → 8 frames).

**Improvement experiments.** All run on the fake-object bag and, for the false-alarm cost, on
all six original bags at every frame. The default reproduces 107 alarm frames / 20 events on the
five empty bags and 185/246 labelled frames, first alarm 11, on `doubleT_obstacle`. Raw numbers:
[`experiments_p4_fake_labelled.json`](evidence/results/experiments_p4_fake_labelled.json).

| variant | fake bag: STOP frames on inside objects | fake bag: STOP frames on outside objects | fake bag: background alarm frames / IDs (never matched to an object) | five empty bags: alarm frames / events | `doubleT_obstacle` |
|---|---:|---:|---:|---:|---|
| default | 303 | 6 | 3 / 2 | 107 / 20 | 185/246, frame 11 |
| `edge_margin_per_100m: 0` | 303 | 40 | 8 / 4 | — | — |
| `min_points 3, min_points_far 2` | 306 (#10: 3 at 10 m) | 6 | 3 / 2 | — | — |
| `gauge_min_points 2` | 303 | 9 | 3 / 2 | — | — |
| `lowobj.near_enabled` | 303 | 6 | 466 / 106 | — | — |
| `signature_min_lateral: 0.9` | 314 (#2 from 52.5 m) | 6 | 3 / 2 | 168 / 26 | unchanged |
| `elevated` off | 334 (#8: 43 frames) | 6 | 3 / 2 | 139 / 23 | unchanged |
| both | 345 | 6 | 3 / 2 | 186 / 26 | unchanged |
| **short signatures** (experiment) | **352** | 9 | 3 / 2 | **113 / 22** | unchanged |

The extra false alarms of the two blanket relaxations all come from
`squareT_platform_squareT_switch`: one structure ~104 m ahead of the stopped train, 3.9–5.7 m
long, bottom 2.0–2.5 m above the rail head, near the end of the height reference. The organizers'
test objects are 0.3–2.2 m long. `scripts/short_signature_experiment.py` keeps both signatures
for clusters longer than 3 m or farther than 100 m. This moves #2's first STOP from 34.0 to
52.5 m, gives #4 a STOP from 14.5 m and gives #8 43 STOP frames (held from 31 m). The cost is
+6 alarm frames and +2 events on the five empty bags, plus 3 STOP frames on #5, which is inside
the envelope measured from the rails in those frames. **Not shipped:** the rule belongs to P3
(`resense/clustering.py`), and the 20-minute ride, where most infrastructure lives, has not been
re-run with it.

**What the organizers' set implies for the open bed question** (whether a bed object below the
rail head counts; asked as Q3 in [`QUESTIONS.md`](QUESTIONS.md)): none of
their ten test objects lies on the bed between the rails. The small ones float mid-envelope, stand
on a rail or sit at the edge, and the low one lies across both rails. The shipped policy
(nothing below the envelope floor between the rails) is not tested by this set.

## Original-bag reproduction recipe

The original-bag paired run above used this recipe (repeat for the three named empty bags);
the new `gt.json` records both the placement and RNG protocol:

```bash
resense inject --npy /data/cache/roundT_doubleT --every 10 --out data/S_roundT_doubleT \
  --kinds person,box0.5,box1.0,plank,trolley --distances 10:250 --negative-fraction 0.2 --seed 1
resense inject --npy /data/cache/roundT_doubleT --every 10 --out data/S_roundT_doubleT_legacy \
  --kinds person,box0.5,box1.0,plank,trolley --distances 10:250 --negative-fraction 0.2 --seed 1 \
  --placement legacy
resense eval data/S_roundT_doubleT --text
resense eval data/S_roundT_doubleT_legacy --text
resense eval --npy /data/cache/doubleT_obstacle --gt labels/doubleT_obstacle.json --repeat 1 --text
python scripts/eval_real.py --cache /data/cache --out out/p4-real --bags \
  doubleT_obstacle,doubleT_platform,roundT_doubleT,roundT_pressureGate_roundT,roundT_squareT_pressureGate_squareT,squareT_platform_squareT_switch
```

The published range numbers in the README and EXPERIMENTS §2d use the old set F placement;
the paired sensitivity check above changes their interpretation, but cannot replace them with
surveyed long-range detection range. The original-bag rerun shows that the P4 accounting
changes did not alter the published real-object or empty-bag counts.

Initial audit verification on `a81108f`: 166 dataset-free Python tests, Ruff and the
parameter-sync check passed. After merging `main` of 24.09 (`de98266`) and adding the
synthetic-obstacle labels: 235 tests (`RESENSE_REQUIRE_SYNTHETIC=1`, no skips), Ruff and the
parameter-sync check pass, and a fresh full-rate run of the six original bags reproduces
107 alarm frames / 20 events and 185/246 labelled frames (first alarm frame 11).
