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
