# P4 data and evaluation audit — 23 September 2026

Initial audit base: `a81108f` (v0.6.3); integrated on `4cd32d6` (`main`, 24 September).
The detector, ROS node and default detection parameters were not changed in this P4 pass.
The original six organizer bags were downloaded from the
public link, unpacked and cached at every frame; the new measurements on them are below.
The 20-minute extended ride and its set F range claims are separate and must not be inferred
from this six-bag rerun.

## Findings and corrections

| P4 criterion | Finding | Correction | What has been verified |
|---|---|---|---|
| Set S placement | `place_on_bed` existed but `resense inject` never called it. Ground objects were placed at rail head − 0.15 m even where the real bed was lower, and the far model could place them under the bed. | Injection now defaults to the local bed or rail head − 0.25 m plus measured vault drift and stores `base_z` in `gt.json`. `--placement legacy` reproduces the old height under the new paired-run RNG protocol. | Synthetic bed/vault cases and paired runs on 108 frames of three real empty bags: 22/67 visible in-gauge hits with bed placement versus 29/68 with legacy height. Corrected placement lowers the apparent recall; see below. |
| Set F independence (SCORECARD 24.09, improvement 7) | The object's Y position was recomputed from the detector's own far axis every frame, reducing the apparent cost of axis errors on curves and near the envelope edge. Missing or invalid timestamps also silently fell back to a 0.1-second motion step. | `scripts/far_range_eval.py --placement-mode anchored`: a rail-supported track fit when the object is within 30 m defines its location; near track fits in consecutive empty frames transport that location back through the sequence. `--placement-mode legacy` reproduces the old placement. Recording gaps over 5 m, missing near references, and missing or invalid timestamps are reported as skipped. `--placement-mode independent` also remains available for externally surveyed fixed references. | Known rigid-transform and wrong far-axis regressions, then a paired run on seven organizer sequences: one skip due to a 24.5 m recording gap; see below. Anchoring uses estimated speed and near-track registration, not surveyed ground truth. |
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
events on 2,287 empty-bag frames**, and on `doubleT_obstacle` **58/61 crossing-person frames,
first alarm frame 11, plus 127/185 visible rail-object frames**. This checks the P4 matching
change against the committed real labels; it does not validate synthetic long-range placement.
These runs overlapped archive extraction and other jobs on this workstation, so their latency
figures are not comparable to the repository's controlled timing measurements.

**Integration on `4cd32d6` (24.09):** a full-rate rerun on the local six-bag cache again
produced 107 alarm frames / 20 events on the five empty bags and 185/246 matched labelled
obstacle-frames on `doubleT_obstacle`, first alarm frame 11. The cache and config were those
selected by `scripts/eval_real.py --cache /home/likikikpa/ReSense-p4-data/cache --bags
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
timestamp hashes are committed in [`experiments_p4_setf_paired.json`](experiments_p4_setf_paired.json).

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
piece of the ride; in anchored mode it rejects missing stamps or a near reference. A
zero-return object cannot be marked a hit by an unrelated background detection.

## New unlabelled positive bag

The public organizer folder also now includes `cloud_with_fake_obj.zst`. Its checksum, bag
layout and absent labels are recorded in [`DATASET.md`](DATASET.md). A full-rate offline run
on all **1,510 frames** reported 342 alarm frames, 9 alarm track IDs and 459 advisory frames;
the summary is [`experiments_p4_fake_unlabelled.json`](experiments_p4_fake_unlabelled.json).
The object injection manifest/ground truth was **not supplied**, so those nine tracks cannot
be divided into true and false events or attributed to particular obstacle classes. The
new `resense summarize --unlabelled` option reports false-alarm fields as `null` rather than
incorrectly treating every positive-bag alarm as false. P1 should request the organizers'
per-frame synthetic object positions (vehicle coordinates, dimensions, labels and visibility)
to allow independent recall-by-range scoring; the test stand does not block this P4 request.

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
parameter-sync check passed. Integration checks on current `main` are recorded separately.
