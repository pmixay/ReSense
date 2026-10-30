# K1 / K2 toward 1.3.0: "K2 union", the curve gauge as a second gauge that only adds obstacles

> **Author evidence, not acceptance.** Branch `claude/k1-k2-1.3`, 21.10, from `6ee469c` (detector bytes = v1.2.0
> `3b73bbe`). An independent reviewer checks this afterwards; the captain decides. G3 (held-out) not touched.
> **Result: the switch `track.axis_joint_union` stays OFF.** The final candidate (revision 3, `b88d759`) passes
> every pre-registered row but two: **G-1b** (8 new STOP frames on the ride against a fresh v1.2.0 run; the gate
> against the seal baseline passes) and **R-1** (one STOP frame, D_cube05 frame 330, lost at v1.2.0's placement).
> `scripts/detector_freeze.py verify` **fails on this branch** (expected: `resense/` changed; the captain reseals).
>
> **Amendment 1 (the captain's priority change: range first, false-alarm bound +25 %), received after these
> measurements:** re-scored on the same outputs, revision 3 passes every row (3 added false STOP episodes against a
> bound of +11; no object loses its STOP). The switch is still left off on this branch for the captain's integration
> decision; [PROTOCOL.md](PROTOCOL.md) §11–§12 give the terms, the listed false episodes with pictures, the per-frame
> time table and the exact change that turns it on.

## 1. What was built

Every earlier K2 variant (v3–v5c, r1–r5a) **replaced** the axis that the other stages read on curve frames, and
each replacement moved a true object out of some stage. This candidate replaces nothing the detector reads:

* the track model of every stage (bed, rails, low objects, ego speed, mount calibration, clear distance, health) is
  v1.2.0's estimator, frame for frame (the v5 machinery runs it on its own carried state);
* on a curve frame (v1.2.0's |k| ≥ 1e-4) the K2 joint rail + boundary shape rides along as `TrackModel.curve`,
  trusted as far as a boundary follows it (`_followed_reach` + margin, held over a hidden boundary with a 20 m per
  period decay);
* `Detector._curve_clusters` runs the corridor and the above-rail clustering again in the curve's coordinates
  (current frame only) and **adds** its obstacles that v1.2.0's gauge does not report; nothing v1.2.0 reports is
  changed or removed; the result's `track` (display, records, the judge's own-axis placement) is the curve shape and
  its trusted range on curve frames (`joint_used: true`).

Revisions (each registered in [PROTOCOL.md](PROTOCOL.md) **before** it was measured; failed rows stay in the record):

| rev | commit | change | measured, decisive row |
|---|---|---|---|
| r0 | `0c39158` | the design above | **M-1 FAIL**: marked platform id 23 lost frames 106–112 (curve laterals in the track history; sticky opinion) |
| r1 | `eb8b7aa` | overlap in the vehicle frame; added clusters carry the base lateral and opinion record; opinion re-asked for curve-matched tracks | **G-1 / G-1b FAIL**: ride 27 → 31 events, 30 → 35 episodes vs the seal baseline (32 new ride STOP frames); every other row PASS |
| r2 | `cc703d1` | adds only beyond the farthest X a boundary still follows the base axis (`curve_from`), and only objects with no return in the base strict envelope within the base trusted range | **G-1 FAIL**: ride episodes 30 → 31 (doubt-withheld base tracks released by r1's non-sticky rule) |
| **r3** | **`b88d759`** | r1's non-sticky opinion rule withdrawn (curve-matched tracks keep the sticky rule) | gate PASS; **G-1b FAIL** (ride +8 STOP frames vs v1.2.0), **R-1 FAIL** (1 frame) |

Code diff against v1.2.0 (r3): `resense/track.py` +32 −2, `resense/detector.py` +79 −1, `resense/tracking.py` +5 −2,
`resense/config.py` +1, both YAMLs +1 (switch off, synchronised); tests `tests/test_k2_union.py` (13 tests).

## 2. Result table (final candidate r3 = `b88d759` + the four YAML values; control = fresh v1.2.0 runs)

Candidate values: `axis_joint_fit: true`, `axis_joint_range: false`, `axis_joint_min_curvature: 0.0001`,
`axis_joint_union: true` in both YAML copies ([cand_eval_commit.patch](cand_eval_commit.patch)); K1
`walls_smoothing_distance` stays 0.

| # | pre-registered row | control (v1.2.0) | candidate r3 | verdict |
|---|---|---|---|---|
| ID | switch off = v1.2.0 per frame | — | gate 15,269 rows 0 different (set F equal), Falcon 4,443 rows 0, marked bags 1,667 rows 0 | **PASS** |
| G-1 | full gate vs seal baseline, no `--allow` | exit 0 | exit 0 | **PASS** |
| G-1b | no control STOP lost; no new STOP on the empty recordings and the ride | ride 23 events / 26 episodes / 111 frames | 0 lost anywhere; **ride 25 / 29 / 119**: new STOP frames piece 2 1066–1069, 1071–1072, 1317–1318 | **FAIL** |
| G-1c | set O `small_center` | 32 frames, 55.8 / 60.8 m | identical frame for frame | **PASS** |
| G-1d | `doubleT_platform` no added STOP | 0 STOP | 0 STOP, identical | **PASS** |
| G-2 | X3, 260 comparisons vs fresh control battery | — | 0 failing; per frame 0 changed rows in all 40 cases | **PASS** |
| F-1 | Falcon, 4,443 frames | 1,360 person STOP frames; first 2972 at 124.84 m | **0 lost**; first 2958 at **126.36 m**; 33 new STOP frames, all at the person | **PASS** |
| M-1 | three marked bags per object | tunnels id 19: 29 frames, 54.99 m; platform id 23: 38 frames, 86.76 m | every marked object's STOP frames identical (tunnels 19: 29, 54.99 m; platform 23: 38, 86.76 m); no new STOP frame | **PASS** |
| K1-150 (R4) | `S_person_150` at control's placement | 90/259 | 90/259, same frames | **PASS** |
| K1-100 | `S_person_100` own / at control's placement ≥ 82 | 82/260 | **255/260** own; 82/260 at control's placement | **PASS** |
| R-1 | 37 range jobs at control's placement: no STOP frame lost, first STOP not later | — | 36 jobs identical; **D_cube05 loses frame 330** (of 121; first STOP equal) | **FAIL** |
| K2-G | gains (own-axis placement, B6) | B person 51.8 m; C person 82.77 / 91.63 m; B6 `roundT_doubleT` 80–100 m 1.78 m | **71.19 m; 94.58 / 104.98 m; 0.534 m** | **PASS** |
| T | tests | — | `tests/test_k2_union.py` 13, K1/K2 + opinion + track/gauge/native/node suites pass, numpy and native (one native-only test skipped under `RESENSE_NATIVE=0`); lint PASS | **PASS** |

### 2a. M-1 (marked bags) on r3

All 1,667 frames: the candidate's STOP frames equal control's on all three bags (126 / 185 / 142 STOP frames), every
marked object the same frames and first STOP; off = control in every non-timing field (`runs/r3/markers`). Revision 1
had **gained** frames here (switch ids 0 / 12 / 13 +7 / +10 / +5, platform 23 +3, tunnels 0 +3, all on marked
objects; `runs/r1/markers`); revision 2's rule 2 (the base gauge's verdict stands where it saw the object) removed
those gains along with the ride's false STOPs.

### 2b. The two failing rows, traced

* **G-1b, ride piece 2 frames 1066–1072** (`runs/r3/gate/pairs_cand3.json`; replay `scripts/ride_trk.py`): a curve
  cluster is added at 1058 and 1062–1063 (a 7 m long, 2.4 m wide, 2.8 m tall structure at 102–124 m; its returns lie
  outside the base strict envelope, so revision 2's rule 2 does not stop it) and joins track 447, which v1.2.0
  withholds by the track opinion. The opinion keeps it withheld (r3) for its 10 extra frames, but the two curve hits
  keep the track's zone votes "gauge" through 1066–1072, where v1.2.0's own clusters are `beyond_axis` / advisory, so
  it is released as a STOP. **Frames 1317–1318**: a low cluster (0.5 m tall, at rail level, 69 m) added by the curve;
  the picture [`ride2_1317.png`](ride2_1317.png) shows the joint fit following a diagonal low structure on the right
  while the column row on the left runs parallel to the base axis to 140 m; `curve_from` (the base's followed reach)
  is only 36 m because that boundary mixes a wall, the column row and far structures ([`ride2_1297.png`](ride2_1297.png),
  [`ride2_1062.png`](ride2_1062.png) for the other cases of r1/r2). The ride has no ground truth: by the gate's rule every
  ride STOP is false.
* **R-1, D_cube05 frame 330** (`runs/r3/range/D_cube05_trace_*.txt`): at v1.2.0's placement the 0.5 m cube sits next
  to the 82.9 m static platform-end structure; v1.2.0's track 175 dies at frame 322 and a fresh track 182 is a STOP at
  330; in the candidate the curve adds the cube's own cluster at 322, which keeps track 175 alive with its misses, and
  that track becomes a STOP one frame later (331). The matched "hit" is the static structure (the cube has 9 returns).

## 3. Gains (reported against the historical K1/K2 targets; not switch criteria)

| historical row | target | control | r3 | |
|---|---|---|---|---|
| K2-2 C person first / held | ≥ 110 / ≥ 100 m | 82.77 / 91.63 | 94.58 / **104.98** | first FAIL, held PASS |
| K2-3 B person first; 60–100 m | ≥ 90 m; ≥ 80 % | 51.8; 0/23 | 71.19; 7/17 (41 %) | FAIL (the object on the curve is visible with ≥ 20 returns only from 78 m: [§4](#4-what-was-checked-and-how)) |
| K2-4 A person | 218.0 / 221.0 | 218.38 / 221.78 | 218.38 / 221.78 | PASS |
| B6-1 honesty > 1.05 m (B6 truth) | ≤ 5 % on every recording | 1.6–40.4 % | 0.4–39.5 %, never worse | FAIL (≤ 5 % on 4 of 9) |
| B6-2 `roundT_doubleT` 80–100 m p50 | ≤ 0.5 m | 1.78 | 0.534 | FAIL (narrowly) |
| B6-3 blinks ≤ control | every recording | — | fewer or equal on 9 of 10; `synthetic_platform` 5 → 9 | FAIL |
| K1-1 `S_person_100` | ≥ 200/260 | 82 | **255** | PASS |
| K1-2 `S_person_150` own axis | ≥ 150/259 | 90 | 0 (predicted in the protocol: the candidate places the person on the curve at Y ≈ −1.0 m, where v1.2.0 also gives 0/260) | FAIL |
| K1-3 squareT false-STOP episodes | ≤ 1 | 3 | 3 | FAIL (= control) |
| K1-4 `doubleT_obstacle` | 193 | 193 | 193 | PASS |
| K1-5 appearance at 100 m | first STOP ≤ 5 frames | 28 frames | **5 frames** | PASS |

Curve geometry on `roundT_doubleT` (R ≈ 400 m, three independent witnesses in the B6 README), frames 140–170:
published curvature median **−2.55e-3** (control −6.89e-4: 0.28× → **1.02×** of −2.5e-3); lateral error against the
driven path at 60 / 90 / 120 m **0.22 / 0.40 / 0.21 m** (control 1.67 / 4.69 / 7.97 m). Picture:
[`curve_roundT_doubleT.png`](curve_roundT_doubleT.png). Published trusted range on curve frames is the curve's honest
reach, often shorter than v1.2.0's range along its wrong axis (B6 p50 `roundT_doubleT` 157 → 131 m, `squareT_platform`
151 → 127 m, `doubleT_obstacle` 151 → 127 m); detection never loses range for it (the base gauge keeps detecting to
its own range: R-1 / M-1 / F-1). Latency (gate, shared machine): `doubleT_obstacle` mean 51.7 → 64.4 ms, p95 77 →
98 ms; the curve pass and the joint fit run every curve frame.

## 4. What was checked and how

* **Controls reproduce history:** v1.2.0 Falcon 1,360 / 2972 / 124.84 m; range B 51.8 / 57.11, C 82.77 / 91.63,
  `S_person_100` 82/260, `S_person_150` 90/259, appearance 28 frames; B6 honesty equals the B6 README on all nine; ICP
  of A equals the committed P4 file in all 544 steps (`dx` max difference 0).
* **Scorers fail closed and have planted controls:** `score_falcon_f1.py` (alignment by index, stamp, bag time; a
  planted lost person frame found), `score_markers.py` (alignment; planted loss found), `score_range.py`,
  `x3_frames.py`, `gate_pairs.py`; control-vs-itself gives 0.
* **Every changed row looked at:** all new STOP frames listed with their detections (Falcon: 33, all at the person,
  e.g. 2966 125.53 m lateral 0.12; marked bags: every new STOP on a marked object; ride: §2b with pictures); the
  removed X3 differences of r1 were looked at frame by frame (r3 has none).
* **Instrumentation:** the debug range harness and replays read detector state after `process`; the r1 X3, gate and
  range outputs used for attribution are plain runs. Traced runs were not compared field by field with plain runs
  (unverified for `ride_trk.py` / `range_test_dbg.py`; they were used only to name mechanisms).
* **B6 for r2/r3** was not re-run on all ten recordings: the published model of r3 equals r1's frame for frame on
  `roundT_doubleT` and `squareT_platform` (checked); the B6 rows are r1's (`runs/r1/b6`).
* **Not done / unverified:** the display (ROS `GaugeDisplay`) was not run; the K2-1 wall-referenced error and K2-5
  ride-episode rows were not measured; truth for the ride and for Falcon's curve gauge is not available; the
  latency rows are from a shared 4-vCPU container.

## 5. Reproduce

Environment: Python 3.12 venv, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, rosbags 0.11.5, open3d 0.19.0
(`apt-get install libegl1 libgl1 libgomp1`), native built per tree; `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`,
`RESENSE_REPO` / `PYTHONPATH` per tree (`scripts/env.sh`). Trees: control `git worktree add --detach /opt/base 3b73bbe`;
off `… /opt/off3 b88d759`; candidate `scripts/make_cand.sh b88d759 /opt/cand3`. Data per `docs/VM_GUIDE.md` §2
(six Pandar bags → gate and decoded caches; set O; ride via `scripts/cache_extended_ride.py`); ICP
`k1_k2_gauge_2026-10-19/tools/icp_odometry.py` per decoded recording; B6 poses from
`gauge_stability_2026-10-18/b6_raw.tar.xz`. Commands: gate `scripts/gate.sh <tag> <tree>`; Falcon
`scripts/falcon3.sh` (one stream teed to the trees) + `score_falcon_f1.py`; marked bags `scripts/markers.sh` +
`score_markers.py`; X3 `scripts/x3.sh`; range `k1_k2_gauge_2026-10-19/tools/prebuild_range.py --repo <tree> --tag
cand|candatctl` (candatctl = the candidate with control's object-free baseline files copied into its cache folder) +
`score_range.py`; B6 `scripts/b6.sh`, `honrun.sh`, `b6_honesty.py`; paired gate diff `gate_pairs.py` and
`f1_false_alarms_2026-10-19/scripts/cmp_frames.py`. Raw outputs: `runs/r0` … `runs/r3` (xz; the gate work
directories, X3 raw records, Falcon records, range job rows).

## 6. For the reviewer and the captain

* The approach holds on every no-loss row tied to real objects (Falcon person, marked objects incl. tunnels 19 and
  platform 23, `small_center`, X3, the standing 150 m person at a fixed world position) and gives the curve gains
  above; the remaining cost is on the ride (+3 STOP episodes vs v1.2.0, all on curve/open-area frames where the
  joint fit itself is unreliable) and one frame of a static structure in a range job.
* The remaining defect is the joint fit's trust in open areas (it follows a diagonal low structure while another
  boundary follows the base axis) and that `_followed_reach` cannot see a parallel column row behind mixed
  structures. A next revision would need a robust per-side "which axis does this boundary follow" test before the
  curve gauge is used; that is not attempted here (no further revision is registered).
* K1's own switch (`walls_smoothing_distance`) was not changed; the standing-train 100 m flicker and the 100 m
  appearance are solved by the candidate (K1-1, K1-5); the 150 m target is not.
