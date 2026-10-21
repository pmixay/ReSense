# K1 / K2 1.3 candidate "K2 union": acceptance protocol (pre-registered)

> Written and committed **before any acceptance measurement** of the candidate (21.10, author lane on branch
> `claude/k1-k2-1.3`). Author evidence: an independent reviewer checks it afterwards. G3 (held-out) is not touched.
> The rows of the earlier protocols are reused where they exist ([`../k1_k2_gauge_2026-10-19/PROTOCOL.md`](../k1_k2_gauge_2026-10-19/PROTOCOL.md)
> §3/§7, v5c revision 2 in [`../k2_v5c_2026-10-20/README.md`](../k2_v5c_2026-10-20/README.md) §4, the review
> [`../k1_k2_review_2026-10-20/README.md`](../k1_k2_review_2026-10-20/README.md) R1–R5 and the repair
> [`../k1_k2_repair_2026-10-20/README.md`](../k1_k2_repair_2026-10-20/README.md)). Their thresholds are not changed.

## 1. The candidate

**Idea.** Every earlier variant (v3, v4, v5a/b/c, r1–r5a) replaced the axis that the detector's other stages read on
curve frames. Each replacement moved some true object out of some stage (the low stage clipped the tunnels cube, the
reach cap demoted the Falcon person, the mount calibration read the joint axis, the strict voxels of `small_center`
fell from 4 to 2). This candidate does not replace anything the detector reads:

* the track model every stage reads (bed, rails, low objects, ego speed, mount calibration, clear distance, health)
  stays **v1.2.0's estimator, frame for frame** (the v5 machinery runs it on its own carried state);
* on a curve frame (v1.2.0's own curvature |k| ≥ 1e-4, the v5 threshold) the joint rail + boundary shape of K2
  (`joint_axis_fit`, its own EMA and rate limits, unchanged since v5) is carried as `TrackModel.curve`, trusted as far
  as a tunnel boundary follows it (`_followed_reach` + `axis_valid_margin`; held over a hidden boundary for at most
  the previous curve frame's range less 20 m per period);
* `Detector._curve_clusters`: the corridor and the above-rail clustering run a second time in the curve's coordinates
  on this frame's points; each of its obstacles (zone `gauge`, no reason) that overlaps no v1.2.0 obstacle is added
  (in place of the v1.2.0 advisory clusters it overlaps). **Nothing v1.2.0 reports as an obstacle is changed or
  removed;** the tracker then confirms as usual;
* the result's `track` (display, records, the judge harness's own-axis placement) is the curve's shape and trusted
  range on curve frames (`joint_used: true`), v1.2.0's model elsewhere.

**Switch** `track.axis_joint_union` (default false). The candidate configuration is
`axis_joint_fit: true`, `axis_joint_range: false`, `axis_joint_min_curvature: 0.0001`, `axis_joint_union: true`; every
other key at its v1.2.0 value (K1 `walls_smoothing_distance` stays 0: K1 is not switched; its rows are measured under
this candidate). `axis_joint_reach_cap` / `axis_joint_reach_dual` are not read in this mode.

**Code under test:** commit `0c39158` (`resense/track.py`, `resense/detector.py`, `resense/config.py`, both YAMLs;
tests `tests/test_k2_union.py`, 8 tests). If the detector code changes after this commit, everything below is re-run
and the change registered as a revision of this file first.

## 2. Trees and environment

| tree | what |
|---|---|
| **control** | v1.2.0 `3b73bbe` (`detector_freeze verify` PASS, digest `6d091081…`), detached worktree, fresh runs |
| **off** | `0c39158` with its committed defaults (switch off), detached worktree |
| **cand** | `0c39158` + the four YAML values above in **both** YAML copies (`scripts/make_cand.sh`; one local evaluation commit, nothing else changed) |

Python 3.12 venv, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, rosbags 0.11.5, open3d 0.19.0, native kernels built
in every tree; `RESENSE_REPO=<tree> PYTHONPATH=<tree>:<tree>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell
OMP_NUM_THREADS=1`. No commit to the tree under test during an X3 run.

## 3. Acceptance: every row in this table must pass for the switch to be turned on

"Lost" always means a frame-level set difference, not an aggregate: a gain elsewhere never compensates a loss.

| # | row (data, tool) | PASS if |
|---|---|---|
| **ID** | off vs control: full gate per frame (`f1_false_alarms_2026-10-19/scripts/cmp_frames.py`, set F included), the whole Falcon recording (4,443 rows), the three marked bags (1,667 rows) | 0 differing non-timing rows (latency-only health fields excluded as in that tool) |
| **G-1** | cand full regression gate, `--baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json`, no `--allow` | exit 0 |
| **G-1b** | cand vs control gate, per frame (`cmp_frames.py`) | every differing row listed and explained; no STOP frame of control lost on any recording; no new STOP frame on the five object-free recordings and the ride (the gate counts every ride STOP as false) |
| **G-1c** | set O `small_center` (the v5x gate failure) from the gate per-frame rows | STOP frames ⊇ control's; first STOP and held-from not later |
| **G-1d** | `doubleT_platform` (K1's added false STOP) | no STOP frame added vs control |
| **G-2** | X3 battery `scripts/robustness_battery.py` (protocol `p4_start_2026-10-15/PROTOCOL.md`), cand vs a fresh control battery as `--reference` | PASS: 0 failing of 260 comparisons, no worker error |
| **F-1** | Falcon, all 4,443 frames, `falcon_trace.py` (one stream teed to control / off / cand) | (a) every control person STOP frame (control STOP frames with index > 2900 minus the attributed false set {159, 2312–2314, 4394–4401} of `score_falcon_pos.py`) is a cand STOP frame: **0 lost**; (b) first person STOP frame ≤ control's (control: 2972 at 124.84 m); (c) every new STOP frame has a cand STOP detection within 1.5 m in distance and 1.0 m in vehicle Y of a control detection or warning in the same frame (an object v1.2.0 already saw, now upgraded), else it counts as a false STOP and fails |
| **M-1** | three marked synthetic bags, per marked object (`n5_markers_2026-10-20/scripts/per_object.py`, markers of `synth_markers_2026-10-19/out`) | every marked non-dust object: STOP frame set ⊇ control's and first STOP not later (tunnels id 19: control's 29 frames, 54.99 m, all kept); every new STOP frame of cand matches a marked object |
| **K1-150** (R4) | standing person 150 m, `S_person_150` (`k1_k2_gauge_2026-10-19/tools/range_test.py --obj 0.5,0.5,1.75 --start 360 --d0 150 --end 620` on `squareT_platform_squareT_switch`), at **control's placement** (cand run with control's object-free baseline file) | cand STOP frames ⊇ control's (control: 90/259) |
| **K1-100** | `S_person_100` (same, `--d0 100`), own-axis placement and at control's placement | both ≥ control's own-axis count (82/260) |
| **R-1** | every job of `tools/prebuild_range.py` (the J1 matrix: A/B/C/D person, cubes, lateral/dropout variants, standing, E1–E6), cand run at **control's placement** | per job: STOP frame set ⊇ control's (0 lost frames); first STOP not later |
| **K2-G** | the gains, own-axis placement (the judge's method) and B6 | (i) B person (`roundT_doubleT --start 50 --d0 230`) first STOP > control's; (ii) C person (`roundT_pressureGate_roundT --start 0 --d0 230`) first STOP and held-from ≥ control's; (iii) B6 `roundT_doubleT` off-track p50, 80–100 m bin within the reported trusted range (`scripts/gauge_stability.py measure`, committed B6 poses) < control's |
| **T** | `pytest` of `tests/test_k2_union.py`, `tests/test_k1_k2_axis.py` and the track / gauge / native / node suites, numpy and native | all pass |

## 4. Reported against the historical targets (not switch criteria; pass/fail stated per row)

The original K1/K2 rows of [`../k1_k2_gauge_2026-10-19/PROTOCOL.md`](../k1_k2_gauge_2026-10-19/PROTOCOL.md) §3 / §7
with their thresholds: K2-1 (C wall-referenced axis error 80–120 m ≤ 0.5 m, `scripts/k2_wall_error.py` with
`results/k2wall/true_left.json`), K2-2 (C person first ≥ 110, held ≥ 100), K2-3 (B person first ≥ 90, 60–100 m ≥ 80 %),
K2-4 (A person 218.0 / 221.0), K2-5 (ride episodes near 6867 / 7859 / 7868 / 3753), B6-1 (honesty > 1.05 m ≤ 5 % on
every recording with a driven path), B6-2 (`roundT_doubleT` 80–100 m p50 ≤ 0.5 m), B6-3 (blinks ≤ control on every
recording), K1-1 (`S_person_100` ≥ 200/260), K1-2 (`S_person_150` ≥ 150/259, own-axis), K1-3 (`probe.py`
squareT_platform ≤ 1 false-STOP episode), K1-4 (`doubleT_obstacle` 193), K1-5 (appearance at 100 m: first STOP within
5 frames). B6 runs on the recordings whose decoded caches this lane holds (the six Pandar recordings, set O, and the
three synthetic scenes if their decoded caches are built); the rest are reported as not measured.

**Prediction stated before measuring:** K1-2 own-axis fails (≈ 0/260). On the development run (§6) the candidate places
the 150 m person on the curve shape at Y ≈ −1.0 m, where it merges with the 147.5 m switch structure (beyond the height
reference, `beyond_height_ref`) or lies beyond the curve's trusted range; v1.2.0 placed it at Y ≈ +2.2 m on its bent
axis, and at the candidate's placement v1.2.0 also gives 0/260. K1-150 above (the same world position for both) is the
no-loss criterion; K1-2 is reported as the historical row.

Also reported: published curvature on `roundT_doubleT` frames 140–170 against the independent R ≈ 400 m (−0.0025 1/m,
B6 README three witnesses); the lateral error against the driven path at 60 / 90 / 120 m on curve frames; trusted
range p50 on curve frames; latency per frame (mean / p95, control vs cand, same machine).

## 5. Decision rule

* Every row of §3 passes → the final commit turns the four values on in `resense/config.py` and both YAMLs (tests that
  pin the defaults updated), and reports §4 as it stands.
* Any row of §3 fails → the switch stays off; the failing rows are reported with their frames. A repair is registered
  as a revision of this file before it is measured, and the failed rows stay in the record.

## 6. Development done before this commit (declared)

On the six Pandar decoded recordings only (no gate, ride, set O, Falcon, marked-bag or X3 run of any draft):
synthetic scene checks; `trace_decoded.py` of drafts against control on all six (0 changed decisions or detections on
the final draft); B6 `track`/`measure` on `roundT_doubleT`; range probes B / C person and the three standing probes
(`S_person_100`, `S_person_150`, appearance) at own and swapped placements. Draft changes driven by them: the published
model follows the curve (to place the judge's object on the curve), the 20 m-per-period hold of the curve range
(C person frames 91–94 lost their votes when the reach jittered 115 → 87 → 115 m). The control values seen there
(B 51.8 / 57.1 m, C 82.77 / 91.63 m, S_person_100 82/260, S_person_150 90/259) reproduce the historical ones exactly.

## 7. Revision 1 (21.10, after measuring F-1 and M-1 on `0c39158`; before any measurement of `eb8b7aa`)

**Measured on the first candidate `0c39158` (kept in the record, raw outputs under `runs/r0/`):**
* ID: Falcon 4,443 rows and the three marked bags 1,667 rows, off = control in every non-timing field. **PASS.**
* F-1: 0 of 1,360 person STOP frames lost; first person STOP frame 2966 at 125.53 m (control 2972, 124.84 m);
  34 new STOP frames (2966–3058), each at a control warning of the person. **PASS.**
* M-1: tunnels id 19 kept (29 → 29, 54.99 m); tunnels id 0 +3, switch ids 0 / 12 / 13 +7 / +10 / +5 STOP frames, all
  new STOP frames on marked objects. **FAIL: platform id 23 loses STOP frames 106–112** (38 → 31, first STOP
  86.76 → 76.44 m), the same frames v5c-30 lost.
* The range matrix of the candidate was stopped after its first jobs (not used); the control matrix is complete.

**Traced cause** (`/opt/cand` and `/opt/base` replays of the decoded `synthetic_platform`, frames 95–110, track 64:
its observation record, `withheld`, the opinion probability per frame): in frames 98–100 the curve gauge added the
object's cluster with its lateral measured from the curve axis (−0.55 m against the base's −0.97 … −1.11 m); the track
reached its STOP onset at frame 103 (control: 106), when the track opinion was 0.008 (below `doubt_threshold` 0.015),
and the sticky doubt rule (`doubt_sticky`: the onset decides) withheld it for its 10 extra frames although the opinion
rose to 0.06–0.93 by frames 106–110 (control: 0.36 at its onset 106, released). Found on the way: the overlap test of
`_curve_clusters` compared laterals measured from different axes (`detector._overlap`), so an added curve cluster
could fail to recognise the base cluster of the same object.

**Revision 1 = commit `eb8b7aa`** (`resense/detector.py`, `resense/tracking.py`; 3 new tests, the first two failing on
`0c39158`'s logic):
1. the curve gauge's clusters are compared with the base ones in the vehicle frame (`_overlap_xy`: X and Y extents);
2. an added cluster carries, for the tracker's record and the report, the lateral and the opinion record of the base
   advisory cluster it replaces (or, replacing none, its own record with the base lateral of its points);
3. a track that matched a curve-gauge cluster (`Track.curve_seen`) is asked the opinion on every withheld frame (the
   non-sticky rule) instead of being held by its onset; every other track keeps the sticky rule.

The rows, tools and thresholds of §3–§5 are unchanged and are measured again on `eb8b7aa` + the same four YAML values
(new evaluation tree from `make_cand.sh`). Dev checks of `eb8b7aa` before this revision, on the six Pandar decoded
recordings only: 0 changed decisions or detections against control on all six; B / C person 71.19 / 94.58 m first,
C held 104.98 m; `S_person_100` 255/260.

## 8. Revision 2 (21.10, after measuring every §3 row on `eb8b7aa`; before any measurement of `cc703d1`)

**Measured on revision 1 `eb8b7aa` (raw outputs under `runs/r1/`):**

| row | result |
|---|---|
| ID | gate 15,269 rows 0 different (set F equal; 7 latency-only health rows), Falcon 4,443 and marked bags 1,667 rows 0 different: **PASS** |
| G-1 | **FAIL**: exit 1, `ride.alarm_events` 27 → 31, `ride.stop_episodes` 30 → 35 (every other gated row equal to control) |
| G-1b | **FAIL**: 0 control STOP frames lost on any recording; new STOP frames only on the ride (pieces 2, 3, 4, 5: 32 frames); none on set O, the six recordings or set F |
| G-1c / G-1d | PASS (`small_center` and `doubleT_platform` frame for frame equal to control) |
| G-2 | PASS: 0 of 260 comparisons failing; per frame 0 STOP frames lost or gained in all 40 cases |
| F-1 | PASS: 0 of 1,360 lost; first person STOP 2958 at 126.36 m (control 2972, 124.84 m); 33 new STOP frames, all at the person |
| M-1 | PASS: tunnels 19 29 → 29; platform 23 38 → 41 (first 86.76 → 90.54 m); every new STOP frame on a marked object |
| K1-150 / K1-100 / R-1 / K2-G | PASS (at control's placement 0 lost frames in all 37 jobs; `S_person_150` 90 → 90; `S_person_100` 82 → 255 own / 248 at control's placement; B person first 51.8 → 71.19 m; C person 82.77 / 91.63 → 94.58 / 104.98 m; B6 `roundT_doubleT` 80–100 m p50 1.78 → 0.534 m) |

**Traced cause of G-1** (`scripts/gate_pairs.py` on the two gate work directories; `scripts/ride_piece.py` /
`scripts/ride_topview.py` replays of ride piece 2 with the curve model and the clusters added; pictures
`ride2_1062.png`, `ride2_1297.png`, `ride2_1317.png`): (a) in open sections the joint fit follows a diagonal low
structure while a column row still runs parallel to the base axis (frame 1317: the column row at +1.3 m straight to
140 m, the curve bent 2.5 m right at 100 m); the second gauge then admits low trackside clusters; (b) the curve's
clustering re-judged objects that the base gauge had already seen inside its strict envelope and demoted (`doubt`,
`beyond_height_ref`; frames 1062–1072 at 102–124 m, piece 5 frames 310–314), and a track once matched to a curve
cluster lost the sticky opinion rule.

**Revision 2 = commit `cc703d1`** (`resense/track.py`, `resense/detector.py`; 2 new tests). Two restrictions, no new
parameter; each only removes additions of revision 1, so the base gauge's own detections stay untouched:
1. `curve.curve_from` = the farthest X to which a tunnel boundary still follows the **base** axis
   (`_followed_reach` along the base model); the curve gauge adds nothing nearer than that (the base is not
   contradicted there);
2. an object with any return inside the base strict envelope within the base trusted range (`valid` of the base
   corridor) was judged by the base gauge: its verdict stands and the curve does not add it.

Dev checks before this revision (six Pandar decoded recordings only): 0 changed decisions or detections on all six;
B / C person 71.19 / 94.58 m first, C held 104.98 m, `S_person_100` 255/260 (as revision 1). The ride diagnosis replay
of piece 2 (the frames listed above) was made with the draft of rule 1 only, to see the mechanism; the full gate of
revision 2 is the measurement. Rows, tools and thresholds of §3–§5 are unchanged; every row is measured again on
`cc703d1` + the four YAML values, except that the B6 rows are re-measured only if the published model differs from
revision 1's (revision 2 does not change it; checked per frame on the B6 track outputs before reuse).

## 9. Revision 3 (21.10, after the gate of `cc703d1`; before any measurement of `b88d759`)

**Measured on revision 2 `cc703d1`** (`runs/r2/gate/`): ID gate 15,269 rows 0 different (PASS); **G-1 FAIL**: exit 1,
`ride.stop_episodes` 30 → 31 (`ride.alarm_events` 27 → 27 now equal); new STOP frames only on the ride: piece 2
frames 1062–1072, 1297–1298, 1317–1318 and piece 5 frames 310–314; 0 control STOP frames lost anywhere. The other rows
were not measured on `cc703d1`.

**Traced** (`ride_trk.py`-style replay of piece 2 frames 1040–1072 on the `cc703d1` evaluation tree: per frame the
curve clusters added and every track that matched one, with its zone and `withheld`): at 1058 and 1062–1063 a curve
cluster is added (the object's returns lie outside the base strict envelope, so rule 2 of revision 2 does not apply)
and joins track 447, which control withholds by the track opinion; revision 1's non-sticky rule then re-asks the
opinion for the curve-matched track and releases it (STOP 1062–1072 while it continues on base clusters). Piece 5
310–314 is the same release. The remaining new STOPs (1297–1298, 1317–1318) are curve additions of low clusters
beyond `curve_from` (52 m / 36 m: the base's followed reach on a boundary that mixes a wall, a column row and far
structures); they are expected to stay.

**Revision 3 = commit `b88d759`** (`resense/tracking.py`, test): revision 1's third change is withdrawn: a
curve-matched track keeps the sticky opinion like every other track (`Track.curve_seen` stays as a record only).
Revision 1's base-coordinate observation record and lateral stay, so the opinion of a curve-matched track reads the
same features as control's track. Prediction stated before measuring: G-1 still fails by the frames 1297–1298 and
1317–1318 unless the gate's episode count absorbs them; M-1 platform id 23 may lose frames again if a curve match
moves its onset to a frame where the opinion is below its threshold. Every §3 row is measured on `b88d759` + the four
YAML values, the gate first.
