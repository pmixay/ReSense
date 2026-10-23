# Falcon clear distance (P4 review 20.10, findings 1, 2, 4): author evidence, lane `claude/falcon-clear-distance-1.3`

Post-release (1.3.0) work from `6ee469c` (detector bytes = v1.2.0). **Author evidence: an independent reviewer checks it afterwards.**
Detector files changed, so `scripts/detector_freeze.py verify` FAILS on this branch (`config.py`, `detector.py`, `health.py`, `detector.yaml`
listed as changed; expected, the captain reseals). Nothing outside `resense/`, both YAML copies, `tests/` and this directory is changed.
The held-out G3 set was not touched. English, as asked; PROTOCOL.md is the pre-registration (+ one amendment).

## Result

| | v1.2.0 (control) | final (`d85e265`, defaults) |
|---|---|---|
| Falcon, 38 non-STOP frames that report a clear distance beyond the person-like object (P4's 38; 4373-4414 minus 4379) | 38 | **4** (4411-4414: object nearer than `gauge.range_min` 3.0 m, bed model recovered; **not fixed**) |
| Falcon, 145 STOP frames of the node's conservative path with clear > STOP distance (detector alone: 575 of 1,364 STOP frames) | 145 (575) | **0 (0)**, small_candidate path too |
| Pandar: STOP rows (791) with clear > the nearest detection | 257 (max excess 0.050 m) | **0** |
| Falcon decisions / detections / warnings / nearest / health level+messages, 4,443 rows; node decision, both policies | | **0 rows differ** (detector), **0 rows differ** (node path) |
| Falcon `clear` rows changed (every one listed) | | 1,006: 52 `lost_bed` (-> 0), 649 `round_down_obstacle`, 305 `round_down_candidate` (-0.1 m); 0 raised |
| Pandar (six recordings, set O, ride: 15,269 rows): fields other than `clear` | | **0 rows differ**; 1,553 `clear` lowered (317 obstacle, 1,236 candidate round-down, all -0.1 m), **0 `lost_bed`**, 0 raised |
| Regression gate, no `--allow`, vs `regression_baseline_2026-09-29_shell_off.json` | exit 0 | **exit 0**; against the control run only the 16 latency rows differ |
| X3 paired against the fresh control (40 cases, 29,765 rows) | | **PASS**, `battery comparison: 0 failed of 260`, 40 of 40 cases with every row's decision/detections/warnings equal; the only differing field is `clear`: 5,303 rows, all -0.1 m |

**Switch state in the final commit** (`HealthConfig`, class default = `configs/default.yaml` = `ros2_ws/src/resense_ros/config/detector.yaml`, checked equal by a test):
`clear_lost_bed` **on**, `clear_round_down` **on**, `clear_lost_model` **off**.

Pre-registered criteria (PROTOCOL.md, amendment 1 for `clear_lost_bed`):

| criterion | `clear_round_down` | `clear_lost_bed` | `clear_lost_model` (first candidate) |
|---|---|---|---|
| F1 only `clear` moves (Falcon, both paths) | pass | pass | pass |
| F2 rows changed only where the traced rule fired, lowered, listed; F5 trace = changed rows exactly | pass | pass | pass |
| F3 / F3b the 39 / the bed-lost person rows report 0 | n/a | **pass** (35 of 35 bed-lost rows; 4 residual rows listed) | pass (39 of 39) |
| F4 clear <= STOP distance (Falcon detector 575 -> 0, node 145 -> 0) | pass | n/a | n/a |
| G1 gate without `--allow` | pass | pass | pass |
| G2 paired per-row diff, sample vs raw points | pass | pass | pass |
| G3 / G3b cost | n/a | **pass** (0 rows of 15,269) | **FAIL**: `doubleT_platform` 23 rows = 6.67 % of its frames (limit 3 %); ride 1.53 % |
| X1 X3 paired | pass | pass | not run (stopped at G3) |

## What was done, in order

Commits (all on this branch): `1608b15` acceptance tests + PROTOCOL.md + replay scripts (before any run of a candidate; 12 of the 13
tests fail on v1.2.0, `tests_on_v1.2.0.txt`); `53fb331` implementation of `clear_lost_model` and `clear_round_down` (off);
`5c11b84`/`f853747` Pandar results of that candidate and **amendment 1** (`clear_lost_bed`) with its tests before its implementation
(`tests_before_amendment1.txt`); `be93c5d` implementation of `clear_lost_bed` (off); `d85e265` the defaults of the two passing switches on (the final detector commit).
The control for every paired comparison is a fresh `git worktree` of `6ee469c`, native build, `detector_freeze verify` PASS (digest `6d091081…`),
`resense.__file__` asserted inside the checkout by every script.

### 1. The defect, reproduced from the raw Falcon stream
The recording was streamed from the archive (published sha256 `90dea27d…`, not recomputed over my stream; 4,443 PointCloud2 messages, 0 lost, 0 duplicates,
0 order violations, the same count as P4's stream) into a local cache (`scripts/cache_falcon_raw.py`) and replayed through the node replica (`scripts/run_falcon.py`: the judge's
`NodeReplica`, i.e. node decode, continuity rules, decision rule). **The control equals P4's committed shipped record `l16.jsonl.xz` in every non-timing field of all 4,443 rows.**
* Finding 1: 38 non-STOP frames in 4373-4414 with `clear` 3.0-40.0 m beyond the nearest return (39 non-STOP frames carry a clear > 0; frame 4379's 4.7 m is not beyond its nearest return 4.75 m).
  Counted again without the track model (`scripts/person_check.py`: returns with X >= 2.4 m, |Y| < 0.9 m, 0.2-1.6 m above the mount plane): 38 frames, plus 4415, 4416
  (88 and 11 returns left of the object at 2.4 m, clear 40.0 m) and 4421 (one stray return at 36.5 m), 41 in 4360-4430.
* Finding 2: 575 of 1,364 STOP frames of the detector's own `clear_distance` exceed the nearest detection by up to 0.05 m (clear rounded to 0.1 m, detections to 0.01 m; 145 of them under the node's min(·, 48.2 m)).
* Looked at: `results/png/person_trace_f43xx.png` (side and top view from the dumped clouds, the model rail head, the mount plane, the gauge floor, `gauge.range_min`) and P4's own pictures. In 4396 the model's rail head runs at the tunnel ceiling (+2 m) while the object is 0.9-1.6 m over the mount plane at 4.3 m.

### 2. Where `clear_distance` comes from, traced on the frames
`resense/health.py` `HealthMonitor.update`: `monitored = min(visibility, trusted range, gauge range[, wall drift])`; `clear = min(obstacle_distance, monitored)`, then
`min(clear, candidate_distance)` (clear cap); `round(clear, 1)`. The terms were recorded per frame (`results/falcon/*.x.jsonl.xz`: `monitored`, `candidate_distance`, `clear_raw`, track state):
* In 4 of the 38 frames (4375, 4385, 4386: 21.0 m; 4414: 40.0 m) the clear is the monitored range. In the other 34 it is the clear-cap candidate distance, 3.0-37.6 m
  (5.5-6.6 m in 4373-4384, 9.2-9.7 m in 4387-4404, 3.0-37.6 m in 4405-4413; the 9.4-9.7 m cluster is not the object, which is in no corridor cluster there, `HANDOFF_not_stop.md`).
* Why the object is no candidate: the track model has no rail pair in all 42 frames (`rail_score` -1, rail lock 0 %) and its bed leaves the calibrated mount plane by 1.3-4.2 m, so the object is below the model's gauge floor in 4373-4375 and 4383-4409 (0 of 905-1,159 returns in the corridor, from the detector's own `corridor_idx`), see `HANDOFF_not_stop.md`.
* The rounding: `round(clear, 1)` against 0.01 m detections.
The documented meaning (`docs/ALGORITHM.md` §4b): metres estimated free, to the nearest confirmed obstacle, else the monitored range; **"a lost track model ... make it equal to 0"**. The code implements that for health errors only (level 2 or unconfirmed orientation: clear 0 even with a confirmed obstacle), not for a lost bed.

### 3. Acceptance tests first (`tests/test_clear_lost_model.py`, `tests/test_clear_lost_bed.py`)
(a) the bed lost, a person-like cluster at 3.0-3.5 m on the track, no confirmed obstacle or candidate: the clear distance is **0** (not "the distance of the nearest in-corridor return"), plus never beyond the nearest return; **0 because that is the documented value**, and
because with the bed lost no return is "in the corridor" in a defined sense (the corridor is cut against the bed model; in frames 4383-4398 none of the object's returns is in it). It is also the convention of a health error.
(b) the clear distance never exceeds a STOP or candidate distance (property test over 350 random distances, the examples 48.06, 47.97, 115.16, 124.09 and a synthetic-tunnel detector test). Detector-level: `Detector.process` with the switches on changes no detection, warning, level, decision input, `nearest_distance`.
On v1.2.0: 12 of 13 fail (the 13th is the "only lowers" property); the detector-level test fails on the real defect (clear 17.4 m against a STOP at 17.3925 m). On the final code: all 17 tests of both files pass; the full suite (2,488 passed) has 1 failure,
`tests/test_rail_start.py::test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop`, which **also fails on the control** (v1.2.0 worktree: 1 failed, 2,471 passed; `results/tests/pytest_control_v1.2.0_full.log`).
One existing test needed a tolerance: `tests/test_clear_cap.py` compared `health.candidate_distance` (rounded to nearest, informational, unchanged) with `clear_distance` within 0.1 m; under round-down they differ by exactly 0.1 (45.0 / 44.9), tolerance 0.1 + 1e-6, with a comment.

### 4. The fix (three switches in `HealthConfig`; the rule that fired is kept in `HealthMonitor.last_clear_rule`, a trace, not a reconstruction; it is named only when it changed the reported value)
* `clear_round_down` (**on**): a clear distance computed with a confirmed obstacle distance or a candidate distance is rounded down to 0.1 m (`math.floor`), not to nearest. Where neither is present it is unchanged.
* `clear_lost_bed` (**on**, amendment 1): the bed is lost when the track model's rail head differs from the calibrated mount plane (`z = -mount height`, final `ok`/`identity` calibration required) by more than `cluster.mount_cross_tol` + `mount_cross_grade` · X at some X = 5, 10, …, `mount_cross_range` (30) m: **H''s own criterion applied to the bed**, parameters unchanged. `clear_distance` = 0 then, whatever the lock and a confirmed obstacle. H' off (`mount_cross_tol` 0) disables it. `bed_off_mount_plane` is evaluated only with the switch on.
* `clear_lost_model` (**off**, the first candidate): `clear_distance` 0 while the monitor's own "track model on its prior" condition holds (rail pair found in < 30 % of the last 20 frames, ≥ 5 frames of history). It covers all 39 Falcon rows but is blunt: it also zeroes 23 frames of `doubleT_platform` (6.67 %, limit 3 %) and 173 of the ride (1.53 %) where the bed is right.
Why a second candidate was added after the first was measured (disclosed in PROTOCOL.md, amendment 1): `clear_lost_model` failed its pre-registered cost limit. A read-only diagnostic of the same Pandar data showed that in all 15,269 frames, including all 196 lost-model rows, the model's bed is within the H' tolerance of the mount plane, while on the Falcon it is not in 4359-4410. The amendment is therefore informed by the first results; it uses H''s tolerance as it is and no fitted threshold.
`clear_lost_bed` costs one comparison per frame. Detections, warnings, decision, `monitored_range`, level, messages: untouched (tests, and the paired runs below).

### 5. Verification
* **Falcon, whole recording, control vs final defaults** (`results/falcon/compare_falcon_final_d85e265.json`, `scripts/compare_falcon.py`): F1: other record fields, extra terms and the node decision (conservative and small_candidate) differ in 0 of 4,443 rows. `clear` changed in 1,006 rows (`results/falcon/clear_changes_falcon_final_d85e265.tsv.xz`, every row with its rule), 0 raised.
  `lost_bed`: the single run 4359-4410, 52 rows (35 CAUTION, 17 STOP: 4359-4372 and 4380-4382, clear 4.6-7.7 m -> 0; the decision stays STOP, the distance stays in `nearest`/detections). In 34 of P4's 38 frames the clear is 0 (all 35 bed-lost non-STOP rows incl. 4379). Node path: 224 rows changed in each policy, none raised.
  The same numbers were measured with the switches set by `--set` at `be93c5d` and with the defaults at `d85e265`: the two runs are row-for-row equal (`compare_falcon_v2_be93c5d_set.json`).
* **Positive controls.** The comparer was fed a copy of the candidate with a decision, a detection list, a node decision flipped and a `clear` raised: it reports 2 / 1 / 1 and 1 raised rows (`results/falcon/positive_control_compare_falcon.json`). The control counts 575 / 145 / 39 on the same script (39 = P4's 38 + frame 4379). The first Pandar comparison reported 147 rows with other differing fields: the machine-speed latency warning (`health.messages`/`level`, 57 rows differ in `level`, `decision_level` equal); the comparer now treats the latency message as timing and says so, and checks that every `level` difference carries a latency message difference (it does, 57 of 57).
* **Pandar, gate and paired rows** (`results/pandar/`): the gate at the final commit with the defaults and no `--allow` is exit 0, "8 gated better" against the 29.09 baseline exactly as the control (`gate_control_v1.2.0.json`: same 8); gate JSON final vs control differ only in 16 latency rows. 15,269 per-frame rows (`gate_rows_*.tar.xz`, the gate's own `--work` rows): 0 differ outside `clear`; 1,553 lowered, 0 raised, each with its rule from `run_cache_trace.py` (the gate's machinery plus the rule trace); the trace's clear equals the gate row's in all 15,269 rows (instrumentation = plain run), 3 times (first, amended and final configuration).
  Per recording (`g3_and_stop_check.txt`): median `clear` unchanged in all (set O 92.8 -> 92.7 m, -0.05 %); `lost_bed` rows 0 everywhere.
  **Sample check against raw points** (`scripts/raw_check.py`, `raw_check_sample_v2set.*`): per recording and rule the first 10, last 10 and 10 random (seed 1) changed rows, 289 rows; the frame is replayed and the bound re-derived from the raw returns of the frame. 229 rows have a cluster as the bound: 0 violations (the cluster's distance is never nearer than its nearest raw return; the new clear is never beyond it; 204 of them where the bound limits are within 0.1 m under it; in 201 the old value was beyond it; 210 have distance == nearest raw X, 19 are farther because `cluster.gauge_distance` measures where the cluster reaches the gauge). **60 rows have no cluster as the bound** (a predicted track, a thin or persistent-evidence cap, held detections): 51 of them checked against the cap value (new <= cap in 51, old > cap in 47), 9 only against the record. My first version of this script reported 14-25 "violations": the assumption "distance = nearest raw return" was wrong (gauge-reach distance); corrected, documented in the script.
* **Falcon raw points for `lost_bed`** (`person_check_final_d85e265.tsv.xz`): in 4360-4430 the control has 41 non-STOP frames beyond the nearest person-like return, the final configuration 7 (4411-4416 and the stray return of 4421); none inside 4373-4410.
* **X3** (`scripts/robustness_battery.py`, protocol `p4_start_2026-10-15`, `-j 2`, control `--judge-reference`, final `--reference <control>`, no commit during the run, decoded caches by `cache_decoded.py`): control MEASURED, final PASS; 40 of 40 cases with every row's decision/detections/warnings equal; raw rows (`results/x3/x3_raw_row_diff.txt`): 29,765 rows, the only field that differs is `clear` (5,303 rows, all exactly -0.1 m, none to 0: no `lost_bed` row in any variant incl. pitch ±2°, roll +2°, 5 Hz, dropout, dedup).
* **Disk and data**: Falcon cache 6.7 GB (zstd of the raw 20.3 GB), six Pandar caches, set O, ride (`cache_extended_ride.py`, archive size and SHA-256 verified; my first ride cache via the VM-guide `tar` recipe lacked the intake manifest the gate requires and was discarded and rebuilt), node-decoded caches of the four X3 recordings: all under `/data`, none committed.

### 6. Why the object is not STOP in 4373-4414: **finding only**, `HANDOFF_not_stop.md`
The bed model leaves the mount plane (no rail pair), the object lies below the model's gauge floor (0 corridor returns in 4372-4375, 4382-4409), in 4411-4416 every return is nearer than `gauge.range_min` = 3.0 m, and in 4376-4381 a new track needs 5 hits.
H' is not the deciding rule for this object (it demotes a different cluster at 9.4-9.7 m in 4394-4401). From the raw points it is a compact vertical object 0.5-0.9 m wide, top 1.53-1.61 m over the mount plane, inside the strict gauge by the detector's own coordinates; only its upper part is in the returns (the Falcon's lowest beam is -9.5 to -11.5°; at 2.5-3 m nothing below 1.2 m over the plane is visible). By the organizers' rule (everything inside the gauge is an obstacle) it is an obstacle; STOP in 10 of the 49 frames 4366-4414. Identity is unverified (no surveyed ground truth).

### 7. Corrected wording for the BACKLOG row of the clear-distance model (finding 4) and rows for this lane (the captain edits BACKLOG)
| Falcon clear-distance model (`small_target_limit`, `range_sensor_model: falcon_prime`) | **on in the code, but it acts only in the node's non-default `clear_range_policy` (`conservative` / `small_candidate`)**; the default `legacy` path never calls it | in those two policies it caps the reported clear distance at min(detector clear distance, 48.2 m) from the measured Falcon raster (density model); in the same policies without a sensor model the range is 0 | P4 review 20.10: 48.2 m reproduced, 0 decision changes in 4,443 frames; the model only passes the detector's own clear distance through (it never raises it), which was wrong in 38 frames at the recording's end: 34 repaired by `health.clear_lost_bed`, 4 remain (21.10 lane, [record](evidence/falcon_clear_distance_2026-10-21/README.md)) |
| Clear distance: lost bed (`health.clear_lost_bed`) | **on** (21.10, awaiting independent review and reseal) | `clear_distance` is 0 while the track model's rail head is outside the H' tolerance of the calibrated mount plane | Falcon 52 frames (4359-4410), Pandar 0 of 15,269 rows, X3 0 of 29,765; decisions, detections, warnings unchanged |
| Clear distance: round down (`health.clear_round_down`) | **on** (21.10) | a clear distance bounded by a confirmed obstacle or candidate is rounded down to 0.1 m | clear > STOP distance: 575 -> 0 (Falcon detector), 257 -> 0 (Pandar), 145 -> 0 (node path) |
| Clear distance: lost rail lock (`health.clear_lost_model`) | **off** | 0 while the rail pair is lost (monitor's "track model on its prior") | covers all 39 Falcon rows but fails its pre-registered cost limit (`doubleT_platform` 6.7 % of frames, limit 3 %); available as a switch |

## What failed, what was corrected, what is unverified
* **Failed:** `clear_lost_model` G3 (above); 4 of P4's 38 frames (4411-4414, plus 4415, 4416 outside P4's count) still overstate after the final configuration: the object is nearer than `gauge.range_min` 3.0 m and the bed model has recovered; no rule of this lane covers them (they belong to the finding in `HANDOFF_not_stop.md`).
* **Corrected on the way:** the raw-point check design (above); the first Pandar comparison (latency warning); `out/` is git-ignored in this repository, so the committed outputs are in `results/` (other evidence directories force-add `out/`); the Falcon cache was first written uncompressed (20 GB, then recompressed to 6.7 GB) and a second attempt to write it uncompressed was killed within seconds (disk).
* **Unverified:** the identity of the object; `clear_lost_bed` on any sensor or mount other than the Pandar recordings, set O, the ride and the Falcon (a wrong stored mount height, B4, would make it 0, i.e. conservative, not tested); rows whose bound is not a cluster (60 of 289 sampled) only against the record/cap value; the ROS graph itself (node path = offline replay of `candidate_ranges`, as P4); consumers of `clear_distance` = 0 other than `decision_policy` (the decision is unchanged in all rows, both policies); the held-out G3 set (not run by design); no other-lane code (farrange, lowobj/F1a, K1/K2) was touched.
* `docs/ALGORITHM.md` §4b already says a lost track model makes the clear distance 0; it is now true for a lost bed; docs, BACKLOG, CHANGELOG are left to the captain.

## Reproduce (commands, in this order; `RESENSE_REPO=<tree> PYTHONPATH=<tree>:<tree>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`)
```
python scripts/cache_falcon_raw.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out /data/falcon/raw.bin.zst           # 6.7 GB, 5-6 min
python scripts/run_falcon.py /data/falcon/raw.bin.zst --out OUT/ctl            # in the v1.2.0 worktree (6ee469c); candidate: the same in the branch tree, --dump 4360,...,4430
python scripts/compare_falcon.py OUT/ctl OUT/cand --out OUT/cmp ; python scripts/person_check.py OUT/ctl OUT/cand OUT/cand_dump --out OUT/pc.tsv ; python scripts/person_trace.py OUT/ctl OUT/cand_dump --out-tsv OUT/pt.tsv --png-dir OUT/png
python scripts/regression_gate.py --cache /data/cache --jobs 4 --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json --work OUT/gate --out OUT/gate.json   # control tree and branch tree
python scripts/run_cache_trace.py --cache /data/cache --out OUT/trace --jobs 4 ; python scripts/compare_gate_rows.py OUT/gate_ctl OUT/gate OUT/trace --out OUT/cmp_pandar
python scripts/raw_check.py --cache /data/cache --changes clear_changes_pandar_final.tsv --ctl-work OUT/gate_ctl --out OUT/raw_check.tsv --set health.clear_lost_bed=true --set health.clear_round_down=true
python scripts/robustness_battery.py --repo <tree> --cache /data/decoded --out OUT/x3/summary.json -j 2 [--judge-reference | --reference <control summary.json>]
```
(scripts are under `docs/evidence/falcon_clear_distance_2026-10-21/scripts/`; `results/` holds the raw outputs compressed, about 7 MB: Falcon records of control, v1 candidate and final (`*.jsonl.xz`, `*.x.jsonl.xz` terms and rule, `*.c.jsonl.xz` node path), every changed row, the gate JSONs of the four runs, the gate's per-frame rows of control and final, the rule traces, the X3 summaries and raw rows.
The decoded Falcon dumps (117 MB) are not committed: regenerate with `run_falcon.py --dump`.)
