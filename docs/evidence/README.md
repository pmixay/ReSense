# Run Evidence

> **Purpose:** index of the raw evidence behind the numbers of
> [`EXPERIMENTS.md`](../EXPERIMENTS.md): the result summaries in `results/`, the logs, captures and
> bench output of each run, and the recordings' original metadata.
> **Audience:** team, jury · **Owner:** P1 (runs, timing), P4 (result summaries) · **Language:** EN
> **Last verified:** 2026-09-25 against `79109f5` (every file is the record of its own date) ·
> **Status:** current

Every file here is the record of one run and is not rewritten: a new run gets a new file or folder
(`results/experiments_<what>.json`, `<run>_<date>/`). Day-1 results that later runs superseded are
in [`../archive/results/`](../archive/results/). `extended_dataset_intake.json` (the ride's
per-file speeds and intake events) stays in `docs/` because scripts read it.

## 1. `results/`: raw summaries of the experiments

One JSON per experiment, each with a `note`, `_meta` or `source` block that names what was run.
"Code" is the commit the file records (where it records none, the version it was run on).

| file | date | code | script | cited by |
|---|---|---|---|---|
| [`scorecard13_p3_2026-09-25.json`](results/scorecard13_p3_2026-09-25.json) | 25.09 | `1c96233` + the robustness flags (candidates as config files; the shipped row with the new `configs/default.yaml`), native path | `scripts/robustness_check.py --cache /data/cache --jobs 1 --config <cfg> --out <out>` as recorded, `--every 2`, `--mount roll_3` / `pitch_3`, on the 4-vCPU dev VM | SCORECARD #13 fixes: every candidate's five-bag counts, per-recording events with first / last frame, mount status changes, `doubleT_obstacle` labelled hits; shipped: five bags 5 Hz 13 → 10, roll 16 → 11, pitch 17 → 16 false events; EXPERIMENTS §1i |
| [`p3_robustness_2026-09-25.json`](results/p3_robustness_2026-09-25.json) | 25.09 | `1c96233` (base), P3 | the pre-registration (20:50 UTC) and three addenda (20:56, 21:01, 21:34 UTC), each before its runs; the 10 Hz gates `scripts/regression_gate.py --cache /data/cache --jobs 1 --set … --baseline results/regression_baseline_2026-09-25_ride_column.json` | the candidates K1 … K3d, ship rule and safety conditions, the gate summaries (K3c FAIL: ride 46 / 39 → 48 / 42 from bursty receive stamps; K3d PASS, 2 gated rows better) and the decision (K3d shipped); EXPERIMENTS §1i |
| [`regression_gate_2026-09-25_robustness.json`](results/regression_gate_2026-09-25_robustness.json) | 25.09 | `ed3affe` + the uncommitted flag code (committed with the defaults on), `--set` the five K3d flags, native path, config sha256 `8b1047af…` | `scripts/regression_gate.py --cache /data/cache --jobs 1 --set … --baseline results/regression_baseline_2026-09-25_ride_column.json` (988 s, dev VM shared with three other runs) | GATE PASS for the shipped robustness flags: `doubleT_obstacle` 185 → 186 labelled hits (object on the rail 127 → 128), STOP episodes 3 → 2; ride 187 / 46 / 39, five bags 58 / 13 / 16, set O and set F straight identical; EXPERIMENTS §1i |
| [`p3_clear_distance_2026-09-25.json`](results/p3_clear_distance_2026-09-25.json) | 25.09 | `3887bf5` (pre-registration 20:42 UTC), `1f1153e` (round 1 results, round 2 pre-registration 21:07 UTC); flag off byte-identical to `1c96233`, native path | one flag-off pass per recording (set O, the five obstacle-free recordings, the ride in 8 pieces) applying `resense.detector.clear_cap_distance` per candidate (agent scratch script), scored with `scripts/score_clear_distance.py`; R1 through `scripts/regression_gate.py --cache /data/cache --jobs 1 --set health.clear_cap=true … --baseline results/regression_baseline_2026-09-25_ride_column.json` | the conservative `clear_distance` (SCORECARD §6 row 6), tried, not shipped: set O overclaim 172 → 46–101 object-frames, no decision changed, but every candidate fails the pre-registered clutter limit (R1–R4: the five recordings' median −5.5 % against 5 %); the gate with R1 on: PASS, 0 gated rows changed (latency rows only); EXPERIMENTS §1i; CHANGELOG |
| [`p3_thin_hanging_2026-09-25.json`](results/p3_thin_hanging_2026-09-25.json) | 25.09 | `e22b41c` (candidate A with `--set cluster.hanging_*`), `c0b4f2f` (new defaults), native path | the pre-registration (20:53 UTC, before any candidate run), then `scripts/regression_gate.py --cache /data/cache --jobs 1 --set … --baseline results/regression_baseline_2026-09-25_ride_column.json` (seven recordings first, then the full gate with the ride in 8 pieces and set F straight) with the stage instrumented; the new defaults on the seven recordings | SCORECARD #11, thin hanging objects: candidates A / B / C, A shipped (set O `thin_hanging` 0 → 15 STOP frames, first STOP 30.1 m, every other gated row the same), the target's points per frame by range, every group the stage kept (the target, 29 single-frame groups in the ride, 28 of them station column tops without a rail pair); EXPERIMENTS §1i; ALGORITHM §3.3 item 8, §6 |
| [`regression_gate_2026-09-25_thin_hanging.json`](results/regression_gate_2026-09-25_thin_hanging.json) | 25.09 | `e22b41c` + `--set cluster.hanging_enabled=true …` (candidate A), native path, config sha256 `d33de125…` | `scripts/regression_gate.py --cache /data/cache --jobs 1 --set … --baseline results/regression_baseline_2026-09-25_ride_column.json` (six recordings, `cloud_with_fake_obj`, the ride in 8 pieces, set F straight; 2 413 s on the shared dev VM) | GATE PASS, 2 gated rows better (`thin_hanging` STOP frames and first STOP), none worse: five bags 58 / 13 / 16, ride 187 / 46 / 39, set O inside STOP frames 303 → 318, set F straight identical; EXPERIMENTS §1i |
| [`p3_signatures_2026-09-25.json`](results/p3_signatures_2026-09-25.json) | 25.09 | `edec4da` (candidate A with `--set cluster.floating_free_*`; the new defaults resolve to the same config, sha256 `3269abf0…`), native path | the pre-registration (20:52 UTC, before any candidate run), the shipped rule instrumented on the six recordings, set O and the ride, `scripts/regression_gate.py --cache /data/cache --jobs 1 --set … --baseline results/regression_baseline_2026-09-25_ride_column.json` (raw gate JSON inside) | the free-hanging exemption of `floating`: set O #2 19 → 30 STOP frames, first STOP 34.0 → 52.5 m; the six recordings and the ride identical frame by frame; GATE PASS, 2 gated rows better; EXPERIMENTS §1i; ALGORITHM §3.3, §6 |
| [`regression_baseline_2026-09-25_ride_p3.json`](results/regression_baseline_2026-09-25_ride_p3.json) | 25.09 | `154db25` (wf7/p3: the four P3 items of 25.09 merged, the rail-shadow rules on with their review fixes, the other three flags off; first cut on `c598cf6`), native path, config sha256 `184ea0e7…` | `scripts/regression_gate.py --cache /data/cache --jobs 3 --baseline results/regression_baseline_2026-09-25_ride_column.json` (six recordings, `cloud_with_fake_obj`, the ride in 8 pieces, set F straight; 332 s, dev VM alone); the comparison block moved to `p3_combined` | the current gate baseline: five bags 58 / 13 / 16, ride 187 / 46 / 39, `doubleT_obstacle` 185 of 246 from frame 11, set O 311 of 801 inside STOP frames (2 × 2 m box 208, plank 49), set F straight person 151.0 m, false detections 24 (26 since the re-cut after the review fixes of the rail-shadow rules, `p3_review_fixes`); PASS against the `_ride_column` one, 5 gated rows better; EXPERIMENTS "Current results", §1h; EVALUATION §3 step 6; CAPTAIN §6 |
| [`p3_review_fixes_2026-09-25.json`](results/p3_review_fixes_2026-09-25.json) | 25.09 | `95ff725` (the fixes), measured on `b718a37` (+ the pre-registration only), native path | the pre-registration (19:47 UTC, before any run of the fixed code on the organizer data), `scripts/regression_gate.py --cache /data/cache --jobs 3 --baseline results/regression_baseline_2026-09-25_ride_column.json`, `target.py` of the rail-shadow item on the gate's set O JSONL, the gate of `8556773` re-run in a scratch dir and compared frame by frame, `far_range_eval.py` of `8556773` | the safety review of the rail-shadow rules: `gauge_distance` on the envelope widened by the axis margin (never beyond the entry), `track.floor_shadow_max_hold` 20, adjacent shadow bins and the face nearest the shadow, health counters; GATE PASS, 5 gated rows better, none worse; decisions and the track model identical in all 15 269 frames, gauge distances only shorter; set O #1 unchanged (largest error 0.46 m); set F straight 1 m box false detections 12 (10 in the first `_ride_p3` cut); the baseline re-cut; EXPERIMENTS §1h |
| [`p3_combined_2026-09-25.json`](results/p3_combined_2026-09-25.json) | 25.09 | `489fef3` (the merges), measured on `c598cf6` (+ the pre-registration only), native path | the pre-registration (19:03 UTC, before any run on the merged code), the full gate above, `target.py` of the rail-shadow item on the gate's set O JSONL, `scripts/eval_real.py --bags cloud_with_fake_obj --set` the three rail-shadow keys off, and a per-frame set O comparison | the combination of the P3 items: GATE PASS, 5 gated rows better, none worse, every gated row equal to `regression_gate_2026-09-25_rail_shadow.json`; set O #1 wrong-distance STOP frames 12 → 0 (largest error 0.46 m); no inside object loses a matched-alarm or STOP frame; EXPERIMENTS §1h |
| [`p3_bed_bin_2026-09-25.json`](results/p3_bed_bin_2026-09-25.json) | 25.09 | `a0f701f` (the pre-registration, 17:50 UTC), `cb733c6` (the flag `track.floor_far_min_width`, off; the candidates with `--set`), native path | `scripts/far_range_eval.py` with the gate's set F straight parameters, `scripts/regression_gate.py --jobs 1 --set track.floor_far_…` on the six recordings and set O (and with the ride for candidate A), against `regression_baseline_2026-09-25_ride_column.json` | the `bed_bin` item (an object far ahead extends the bed fit): the pre-registered candidates and ship rule, the diagnosis of set F's 35 false detections (6 from this mechanism), the far-bin statistics, three candidates (set F 35 → 43 / 36 / 27 false detections, a set O row worse in each), not shipped; EXPERIMENTS §1h, ALGORITHM §6 |
| [`p3_far_switch_2026-09-25.json`](results/p3_far_switch_2026-09-25.json) | 25.09 | `be39362` + the flag (`cluster.far_axis_both_sides`, off; candidates with `--set`), native path | the pre-registration (17:19 UTC) and two addenda (17:32, 17:48 UTC), each before its candidate; `scripts/eval_real.py --bags squareT_platform_squareT_switch`, `scripts/far_range_eval.py` (set F straight with the gate's parameters; six gentle-curve approaches), `scripts/regression_gate.py --jobs 1` on the 4-vCPU dev VM | the 147.5 m switch parts: `far_min_height` 0.8 / 0.9 / 1.0 and `far_axis_both_sides` 1 fail set F straight, mode 2 passes the gate but fails the gentle-curve check (person 124.1 → 122.2 m); not shipped; EXPERIMENTS §1h, §5; ALGORITHM §6 |
| [`regression_gate_2026-09-25_far_axis_both_sides_2.json`](results/regression_gate_2026-09-25_far_axis_both_sides_2.json) | 25.09 | `12a14ea` + the uncommitted flag of `p3_far_switch` (`--set cluster.far_axis_both_sides=2`), native path, config sha256 `93375ac6…` | `scripts/regression_gate.py --cache /data/cache --jobs 1 --set cluster.far_axis_both_sides=2 --baseline results/regression_baseline_2026-09-25_ride_column.json` (dev VM, shared) | GATE PASS, 5 gated rows better: platform 54 / 9 / 15 → 31 / 5 / 11, five bags 58 / 13 / 16 → 35 / 9 / 12, ride 187 / 46 / 39 → 147 / 42 / 33, set F cable false detections 3 → 2; set O, `doubleT_obstacle` and set F detections identical; not shipped (gentle curves); EXPERIMENTS §1h |
| [`p3_platform_end_2026-09-25.json`](results/p3_platform_end_2026-09-25.json) | 25.09 | `692feaf` (round 1), `1ae1952` (round 2 and the far-rail check), flags set with `--set`, native path | the two pre-registrations (16:18 and 16:32 UTC, each before its runs); `scripts/regression_gate.py --cache <cache> --jobs 1 [--set track.walls_min_far_support=… --set track.walls_far_support_frames=…] --baseline results/regression_baseline_2026-09-25_ride_column.json` on the six recordings and set O, the full gate for 0.6 × 10 and for `track.rails_far_check_enabled=true`; per-frame comparisons with the defaults; set F curves and station stops (`far_range_eval.py --placement-mode anchored`) | the 82.9 m platform end: diagnosis (axis ~0.8 m off at 83 m), the far-support rule tried in 6 candidates and not shipped, the far-rail check on the ride; EXPERIMENTS §1h; CHANGELOG |
| [`p3_rail_shadow_2026-09-25.json`](results/p3_rail_shadow_2026-09-25.json) | 25.09 | round 1 `b5d8b14`, round 2 `9f2e2e4` + `cluster.oversize_split_max_distance` (candidates with `--set`), native path | the pre-registration (16:07 UTC, amendment 16:16, round 2 16:32), `scripts/regression_gate.py --jobs 1 --set …` on a cache of the six recordings + set O (`--allow 'ride.*' --allow 'set_F_straight.*'`), then the full gate for the passing candidate; the set O #1 distance error from the gate's per-frame output | the rail shadow of set O #1: round 1 (4 candidates) and A2 fail, B2 ships (shadow start ≤ 30 m, split ≤ 30 m, gauge distance); #1 wrong-distance frames 12 → 0, per-frame rows 200–228; EXPERIMENTS §1h; ALGORITHM §3.1, §3.3, §6 |
| [`regression_gate_2026-09-25_rail_shadow.json`](results/regression_gate_2026-09-25_rail_shadow.json) | 25.09 | `9f2e2e4` + `cluster.oversize_split_max_distance`, `--set` of candidate B2 (= the new defaults), native path | `scripts/regression_gate.py --cache /data/cache --jobs 1 --set … --baseline results/regression_baseline_2026-09-25_ride_column.json` (six recordings, set O, the ride in 8 pieces, set F straight; 1 084 s, dev VM shared with other gates) | GATE PASS, 5 gated rows better, none worse: set O #1 207 → 208, #9 42 → 49 STOP frames, set F straight false detections person 7 → 6, 1 m box 13 → 10, trolley 12 → 5; ride 187 / 46 / 39 and five bags 58 / 13 / 16 unchanged; EXPERIMENTS §1h |
| [`scorecard13_2026-09-25.json`](results/scorecard13_2026-09-25.json) | 25.09 | `7466979` (shipped `configs/default.yaml`, SHA-256 `b7c39359…`), P4 | `scripts/robustness_check.py --cache <cache> --out <out>` with `--every 2` (5 Hz), `--mount roll_3` / `pitch_3`; the held-out suffix with `resense run` + `resense summarize` on frames 804–1 509 of `cloud_with_fake_obj` | SCORECARD #13: the six bags at 10 / 5 Hz and +3° roll / pitch (five empty bags 13 / 16 / 17 false events at 5 Hz / roll / pitch vs 13 as recorded; `roundT_doubleT` 0 → 3 / 2 / 1), `doubleT_obstacle` labelled hits, the rejected `zone_min_fraction` 0.7 trial, 0 false frames in the 706-frame suffix; EXPERIMENTS §1g |
| [`long_rule_bottom_2026-09-25.json`](results/long_rule_bottom_2026-09-25.json) | 25.09 | `3bf6324` (candidates with `--set cluster.floating_long_min_bottom=…`), `0bb1ba3` (new defaults), native path | `scripts/regression_gate.py --cache /data/cache --jobs 3 [--set …] --baseline results/regression_baseline_2026-09-25_ride.json` on the 4-vCPU dev VM, the ride in 8 pieces, set F straight round 3; the shipped rule instrumented in one run | the review fix of the long overhead rule: the pre-registration (11:08 UTC), the bottom heights of every cluster the long branch alone demotes (1.68–2.65 m but one unconfirmed single-frame cluster at 0.89 m), the gate summaries of the shipped run, 2.0 / 1.8 / 1.6 m and the new defaults (1.6 m and the new defaults identical to the baseline), the ride event 2.0 / 1.8 m bring back; EXPERIMENTS §1f; ALGORITHM §3.3 |
| [`regression_baseline_2026-09-25_ride_column.json`](results/regression_baseline_2026-09-25_ride_column.json) | 25.09 | `d117c8c` (`tracking.column_hold` 2, `cluster.floating_long_min_bottom` 1.6), native path, config sha256 `0fd4e64e…` | `scripts/regression_gate.py --cache /data/cache --jobs 3` (six recordings, `cloud_with_fake_obj`, the ride in 8 pieces, set F straight; 348 s, dev VM) | the gate baseline until the `_ride_p3` one (25.09): `roundT_doubleT` 0 / 0 / 0, five bags 58 / 13 / 16, ride 187 / 46 / 39, set F straight person 151.0 m, false detections 35; PASS against the `_ride` one, 7 gated rows better; EXPERIMENTS §3a; EVALUATION §3 step 6 |
| [`column_hold_2026-09-25.json`](results/column_hold_2026-09-25.json) | 25.09 | `8b9f72d` (candidates with `--set tracking.column_hold=…`), native path | the pre-registration (12:18 UTC, before any run), the counts from the 10 `roundT_doubleT` captures of `dry_run_`, `bench_` and `offline_2026-09-25/`, and `scripts/regression_gate.py --cache /data/cache --jobs 3 --set tracking.column_hold=<v> --baseline results/regression_baseline_2026-09-25_ride.json` | the choice of `tracking.column_hold` 2 (3 fails the gate: ride STOP episodes 39 → 40); EXPERIMENTS §3a; CHANGELOG |
| [`rules_decision_2026-09-25.json`](results/rules_decision_2026-09-25.json) | 25.09 | `7290873` (all four runs; flags set with `--set`), native path | `scripts/regression_gate.py --cache /data/cache --jobs 3 [--set …] --baseline <defaults run>` on the 4-vCPU dev VM, the ride (221 split files, streamed split by split as in [`VM_GUIDE.md`](../VM_GUIDE.md) §2.3) in 8 pieces, set F straight with the round-3 parameters | the rules decision: the pre-registered criteria (09:16 UTC), the four raw gate summaries (defaults, long rule, short signatures, both), verdicts (long rule GO, short signatures NO-GO), frames differing per recording, the ride episodes each variant adds or removes; EXPERIMENTS §1f; CAPTAIN action 11 |
| [`regression_baseline_2026-09-25_ride.json`](results/regression_baseline_2026-09-25_ride.json) | 25.09 | `935eecf` (long overhead rule on), native path, config sha256 `14828b70…` | `scripts/regression_gate.py --cache /data/cache --jobs 3` (six recordings, `cloud_with_fake_obj`, the ride in 8 pieces, set F straight; 394 s, dev VM) | the gate baseline until `tracking.column_hold` (superseded by the `_ride_column` one the same day): five bags 60 / 14 / 17, ride 197 / 46 / 39, set F straight person 151.0 m; PASS against the defaults run of the day, 3 gated rows better; EXPERIMENTS "Current results", §1f, §2d; EVALUATION §3 step 6; CAPTAIN §6 |
| [`regression_gate_2026-09-25_column_hold.json`](results/regression_gate_2026-09-25_column_hold.json) | 25.09 | `ead8502` + `tracking.column_hold` (`--set tracking.column_hold=1`; measured before the pre-registration of `column_hold_2026-09-25.json`, which chose 2), native path, config sha256 `c95b5c02…` | `scripts/regression_gate.py --cache /data/cache --jobs 2 --set tracking.column_hold=1 --baseline results/regression_baseline_2026-09-25_ride.json` (dev VM, shared with another gate) | GATE PASS, 10 gated rows better, none worse: `roundT_doubleT` 2 / 1 / 1 → 0 / 0 / 0, five bags 60 / 14 / 17 → 57 / 13 / 15, ride 197 / 46 / 39 → 176 / 45 / 37, set F false detections 56 → 27, detections identical; EXPERIMENTS §3a |
| [`regression_gate_2026-09-25_8932f3a.json`](results/regression_gate_2026-09-25_8932f3a.json) | 25.09 | `8932f3a` (the four merges of 25.09: DBSCAN on cKDTree, the two opt-in flags off), native path, config sha256 `fa64b1be…` (two new keys, both 0) | `scripts/regression_gate.py --baseline results/regression_baseline_2026-09-25.json` (`--jobs 3`, 46 s, dev VM under load; ride and set F not cached) | GATE PASS: all 82 gated rows the same, only latency moved (17–26 ms mean per frame, information only); EXPERIMENTS "Current results"; CAPTAIN §2 |
| [`regression_baseline_2026-09-25.json`](results/regression_baseline_2026-09-25.json) | 25.09 | `ca557cb` (detector as `e3929f2`), native path, config sha256 `05edeae1…` | `scripts/regression_gate.py` (six recordings + `cloud_with_fake_obj`; ride and set F not cached) | the first gate baseline, kept for history (superseded by the `_ride` one the same day); EVALUATION §3 step 6 |
| [`experiments_2026-09-24_train_speed.json`](results/experiments_2026-09-24_train_speed.json) | 24.09 | `537e220` (detector unchanged) + the scripts of `396755f` | `scripts/speed_reference.py`, `speed_accuracy.py`, `eval_real.py --nominal-stamps --speed-ref`, `score_fake_objects.py`, `speed_setf.py`, `speed_static_check.py`, `speed_timing.py` | EXPERIMENTS §9; CHANGELOG; SCORECARD §8 |
| [`experiments_2026-09-24_remeasure.json`](results/experiments_2026-09-24_remeasure.json) | 24.09 | `4cd32d6` (current) against `1210580` (v0.6.3) | `scripts/eval_real.py`, `start_offsets.py`, `far_range_eval.py`, `lying_person_eval.py`, `resense bench` | EXPERIMENTS "Re-measurement", §2d round 3; SCORECARD §1 |
| [`experiments_p4_fake_labelled.json`](results/experiments_p4_fake_labelled.json) | 24.09 | `07b5e0c` + P4's evaluation fixes of 24.09 (detector unchanged) | `resense run`, `scripts/score_fake_objects.py`, `resense summarize --gt`, `scripts/eval_real.py`, `short_signature_experiment.py` | EXPERIMENTS §1e, §2e; P4_AUDIT; DATASET |
| [`experiments_p4_fake_unlabelled.json`](results/experiments_p4_fake_unlabelled.json) | 24.09 | not recorded (P4's first, unlabelled pass) | `resense run` + `resense summarize` | EXPERIMENTS §2e; P4_AUDIT; DATASET |
| [`experiments_p4_setf_straight_paired.json`](results/experiments_p4_setf_straight_paired.json) | 24.09 | not recorded (current code; config SHA-256 in the file) | `scripts/far_range_eval.py` legacy / anchored, `scripts/compare_setf.py` | EXPERIMENTS §2d round 4; P4_AUDIT |
| [`experiments_p4_setf_paired.json`](results/experiments_p4_setf_paired.json) | 24.09 | not recorded (config SHA-256 in the file) | same | EXPERIMENTS §2d round 4; P4_AUDIT |
| [`experiments_v0.6.3_real_fullrate.json`](results/experiments_v0.6.3_real_fullrate.json) | 23.09 | `c1c2b6a` (v0.6.3, merged as `1210580`) | `scripts/eval_real.py`, `consistency_check.py` | EXPERIMENTS §0 |
| [`experiments_v0.6.3_start_offsets.json`](results/experiments_v0.6.3_start_offsets.json) | 23.09 | v0.6.3 | `scripts/start_offsets.py` | EXPERIMENTS §0 |
| [`experiments_v0.6.2_real_fullrate.json`](results/experiments_v0.6.2_real_fullrate.json) | 23.09 | v0.6.1 and the v0.6.2 steps a–d | `scripts/eval_real.py`, `consistency_check.py` | EXPERIMENTS §0 |
| [`experiments_v0.6.2_margins_lying.json`](results/experiments_v0.6.2_margins_lying.json) | 23.09 | v0.6.2 | `scripts/eval_real.py`, `consistency_check.py`, `far_range_eval.py`, `lying_person_eval.py` | EXPERIMENTS §0; `scripts/lying_person_eval.py` |
| [`experiments_v0.6.2_setF.json`](results/experiments_v0.6.2_setF.json) | 23.09 | config of `a777403` (v0.6.2) | `scripts/far_range_eval.py` | EXPERIMENTS §2d round 2 |
| [`experiments_v0.6.1_real_fullrate.json`](results/experiments_v0.6.1_real_fullrate.json) | 22–23.09 | `8689bf6` (detection code identical at `70910c9`) | `scripts/eval_real.py` | EXPERIMENTS §0a, §2d |
| [`experiments_v0.6.1_setF.json`](results/experiments_v0.6.1_setF.json) | 22.09 | v0.6.1 | `scripts/far_range_eval.py` | EXPERIMENTS §2d round 1 |
| [`experiments_v0.5_real_fullrate.json`](results/experiments_v0.5_real_fullrate.json) | 22.09 | `b67c5c1` (final defaults), `9b56bdf` (first cut, ablations) | `resense run`, `resense bench` | EXPERIMENTS §1, §1b, §3 |
| [`experiments_v0.4_real_fullrate.json`](results/experiments_v0.4_real_fullrate.json) | 21.09 | `f2c57e5` (v0.3) and `f4e311f` (v0.4) | `resense run`, `resense summarize` | EVALUATION §3 |
| [`experiments_v0.4_synthetic_on_real.json`](results/experiments_v0.4_synthetic_on_real.json) | 21.09 | `f4e311f` | `resense inject`, `resense eval` (set S) | EVALUATION §3; DATASET |

## 2. Run folders

### `docker_2026-09-23/`: the ROS 2 node in Docker on the real frames (EXPERIMENTS §3b)

These runs used Docker on the sandbox (the team's 4-vCPU dev VM). The recordings were rebuilt
from the frame cache by `scripts/cache_to_bag.py`: same topic, `frame_id`, PointCloud2 layout,
scan order and receive times as the originals, coordinates quantised to 5 mm. `checks.txt` is the
output of `scripts/check_dry_run.py` on each capture. For each run the folder has the node log
(`*_node.log`) and the status stream (`*_status.jsonl.gz`).

| run | how | result |
|---|---|---|
| `clear` | `scripts/dry_run.sh roundT_doubleT --expect-clear --max-alarm-frames 2`; node and player in one container, root | 237 of 252 frames, 10 fps, p95 76 ms; the recording's 2 known alarm frames at 128–130 m (the offline evaluation has the same two) — PASS |
| `obstacle` | `scripts/dry_run.sh doubleT_obstacle`, one container, root | person and object at 55.9–56.5 m; at 360° the sandbox runs at the frame period, so the p95 ≤ 100 ms and "no dropped frame" criteria fail here |
| `ct_smoke` | `scripts/console_test.sh`, with the node in its own container on the image's default command and the player **as uid 1000** in a second container; two synthetic bags, both topic / frame pairs | PASS; input switched, detector restarted |
| `ct_real` | the same procedure on `roundT_doubleT` and then `doubleT_obstacle` | both recordings; obstacle at 56.1 m; the only out-of-window distances are the 2 known frames at 128–130 m of the first recording; `ct_real_docker_stats.txt` shows the node container at ~100 % of one core while frames arrive (busy median), 186 MB |
| `rviz_chain` | the node with `rviz:=true` on a virtual display, `ros2 topic echo /resense/decision` and the player (uid 1000, bag at 0.5×) in separate containers; screen recorded: [`../video/docker_chain_rviz.mp4`](../video/docker_chain_rviz.mp4) | OBSTACLE at 55.7–56.3 m, `FAULT` before the first cloud and 0.5 s after the last; `rviz_chain_node.log` |

The `clear` and `obstacle` runs predate the image's UDP-only DDS profile
(`docker/fastdds_udp.xml`); the `ct_*` and `rviz_chain` runs use it. The runs are v0.6.2 (the
first four) and v0.6.3 (`rviz_chain`).

### `timing_2026-09-23/` and `mount_check_2026-09-23/`: v0.6.3 timing and the re-mount check

`bench_v063.txt` is the output of `resense bench --npy <recording>` on every recording, back to
back on the idle sandbox (EXPERIMENTS §3: 42–64 ms mean, p95 53–78 ms). The `v062_*` / `v063_*`
files are `scripts/calib_check.py` on three recordings before and after the v0.6.3 calibration
change (EXPERIMENTS §6): every supported mount gives the same residuals.
`scripts/record_rviz_chain.sh` re-records `../video/docker_chain_rviz.mp4`.

### `regression_gate_2026-09-25/`: the gate against the baseline

`scripts/regression_gate.py --from-json <run> --baseline results/regression_baseline_2026-09-25.json
--changed-only` for three runs of 25.09 (4-vCPU dev VM, `--jobs 2`):

| file | run | result |
|---|---|---|
| `pass_native.txt` | the same code | exit 0 |
| `pass_numpy.txt` | the same code with `RESENSE_NATIVE=0` | exit 0; every gated metric identical, only latency differs |
| `fail_cluster_min_points_8.txt` | `--set cluster.min_points=8` | exit 1 |

In the failing run `squareT_platform_squareT_switch` goes from 15 to 19 events and from 25 to 29
STOP episodes; the 0.3 m floating cube goes from 19 to 18 STOP frames, with the first STOP at
32.3 m instead of 34.0 m. The run on the merged `8932f3a` (GATE PASS) is
[`regression_gate_2026-09-25_8932f3a.json`](results/regression_gate_2026-09-25_8932f3a.json) in
`results/`.

### `bench_<date>/`: the 8-core bench (C7 / C8; written when the kit is run)

`scripts/bench_8core.sh <bags>/doubleT_obstacle <bags>/roundT_doubleT` writes one folder:
`system.txt` / `facts.txt` (machine, Docker, commit), `build/`,
`dry_{obstacle,clear}_{native,numpy}/` and `ct_{image,stock}/` (each: `run.txt` with the check,
`status.jsonl.gz`, `node_log.txt`, `docker_stats.tsv`; `ct_stock` also `player_log.txt` /
`listener_log.txt`), `offline/` (`bench_node_path.py` and `resense bench`, native and numpy, peak
RSS), `runs.tsv`, and `summary.txt` / `summary.json` (`scripts/bench_summary.py`). The first one is
`bench_2026-09-25/` (below), from a VM with 4 physical cores; the 8-core run is still owed
([`../CAPTAIN.md`](../CAPTAIN.md) action 7).

### `*_2026-09-25/`: the VM kit on a team VM (`scripts/vm/`, AGENT_BRIEF.md)

One Yandex Cloud VM (Intel Xeon Icelake 2.0 GHz, 8 vCPU = 4 physical cores × 2 threads, 15.6 GiB,
Ubuntu 22.04, Docker 29.8.1, stock ROS 2 Humble on the host), code `7290873`, the organizers' data
fetched on the VM (the ride's cache complete, 221 of 221 split files, archive sha256 as published).
The two dry-run bags were played from a RAM tmpfs (`DATA_DIR=/mnt/ramdata`): the VM disk reads 64
MB/s. Written by `scripts/vm/run_plan.sh <step>` and staged by `run_plan.sh collect --to-repo`
(`*.log` renamed `*_log.txt`, `*.jsonl` gzipped, gate work directories left out); the VPC's DNS
address in `offline_2026-09-25/blocked_attempts.txt` is replaced by `<vpc-dns>`.

| folder | run | result |
|---|---|---|
| `vm_2026-09-25/` | `setup_vm.sh`, `fetch_data.sh`, `summary.md` of `collect` | READY; DATA READY (every cache, the ride 221 of 221) |
| `dry_run_2026-09-25/` | `run_plan.sh dryrun`: `--no-cache` build + `dry_run.sh` on both original bags, `console_test.sh` (image's and stock DDS), the host console with `rmw_fastrtps_cpp` and `rmw_cyclonedds_cpp`; `diag_cyclonedds_buffers/`: the CycloneDDS host console once more at the default and at 32 MB socket buffers (its `README.txt`) | FAIL: `dry_obstacle` (drops after 5 s), `dry_clear` (3 alarm frames at 111–115 m), `host_cyclonedds` (360° clouds lost); PASS: `original_bags`, both console tests, `host_fastdds` |
| `bench_2026-09-25/` | `run_plan.sh bench` → `scripts/bench_8core.sh` (`vm_result.txt`: the kit's notes) | FAIL on the four `dry_run.sh` runs, PASS on both console tests; numbers in EXPERIMENTS §3a |
| `gate_2026-09-25/` | `run_plan.sh gate`: `regression_gate.py` with the ride and set F straight against `regression_baseline_2026-09-25.json`; `variants/<name>/`: the same with `--set` for the long rule, the short rule, both, and the near-bed path, each against the HEAD run (`variant.txt`) | HEAD PASS (81 rows the same); long PASS; short, both and near-bed FAIL (CAPTAIN action 11) |
| `export_2026-09-25/` | `run_plan.sh export`: `export_image.sh` (`--no-cache`, gzip -6) + `load_image.sh` | PASS: 475 489 127 bytes, sha256 in `archive.txt` (the archive is not committed) |
| `offline_2026-09-25/` | `run_plan.sh offline --minutes 30`: outbound blocked (`rules.txt`), images deleted, the archive loaded, `OFFLINE=1 dry_run.sh` on both bags, the README jury commands from the host console | FAIL: the two `dry_run.sh` runs (as online); PASS: block verified, load, `jury_console`; `blocked_attempts.txt`: only the kit's own probes; restored after 4 min (`window.txt`) |

### `*_2026-09-25_2/`: the confirmation re-run on a second team VM (VM_GUIDE §4.0)

25.09 afternoon, a second VM of the same type (Xeon Icelake 2.0 GHz, 8 vCPU = 4 physical cores, 15.6
GiB, Ubuntu 22.04, Docker 29.8.1, stock ROS 2 Humble on the host), code `76bf24e`, every step as
[`../VM_GUIDE.md`](../VM_GUIDE.md) writes it (§1 setup, §2 data with the ride's cache complete, §4.0
runs, §6 collection; the `_2` suffix because the first run's folders carry the same date). The two
bags were played from a RAM tmpfs copy, checked byte-identical to the originals. No archive, bag,
cache or `out/` is committed; the personal-data scan of §6 found package versions, public DNS
resolvers and multicast / loopback addresses only.

| folder | run | result |
|---|---|---|
| `vm_2026-09-25_2/` | §3 machine facts (`lscpu`, `vmstat`, `rmem`, commit) | 4 cores, steal 0, `rmem_max` 212992 |
| `dry_run_2026-09-25_2/` | §4.1 (`dry_obstacle.txt` with the `--no-cache` build, `dry_clear.txt`, `replay_dry_clear.txt`), §4.2 (`ct_stock.txt`; `host_console_fastdds.txt`, `host_console_cyclonedds.txt` at `rmem_max` 32 MiB), node logs and gzipped captures; `diag_host_fastdds/`: the stock Fast DDS host console repeated, at 32 MiB and with the 25.09 8 MiB profile mounted over the image's (its `README.txt`, the script `g_runs.sh`) | PASS: `dry_obstacle`, `dry_clear` (0 alarm frames; replay equal), `ct_stock`, CycloneDDS at 32 MiB; FAIL: the host console labelled Fast DDS at 212992 (5 of 5), PASS at 32 MiB; corrected 25.09 evening: those players were CycloneDDS (no Fast DDS RMW on that host; the files carry a CORRECTION line) |
| `bench_2026-09-25_2/` | §4.3, `scripts/bench_8core.sh` (its `build/run.txt` force-added past `.gitignore`'s `build/`) | PASS but `dry_obstacle_numpy` (p95 119 ms) |
| `gate_2026-09-25_2/` | §4.4, `regression_gate.py --jobs 4` against `regression_baseline_2026-09-25_ride_column.json` | PASS: 105 gated rows the same, ride 187 / 46 / 39 |
| `export_2026-09-25_2/` | §4.5, `export_image.sh` + `load_image.sh` | PASS: 475 515 293 bytes, sha256 in `archive.txt` |
| `offline_2026-09-25_2/` | §5 steps 1–7 (no host allowed): `steps.txt`, `check_no_network.txt`, both `OFFLINE=1` dry runs, `jury_console.txt` (README steps 2–5 from the host), `rules_ipv4.txt` / `rules_ipv6.txt` (packet counters) | PASS: block, both dry runs; FAIL: `jury_console` (6 of 201 clouds: the host buffer, as online); restored after 4 min |

### `*_2026-09-25_3/`: the transport fixes on a third team VM (25.09 evening)

Code `d4b396e` (README jury step 0 and the opt-in `RESENSE_DDS=shm` of `be39362`), the same VM type
(4 physical cores, Ubuntu 22.04), the image built by `dry_run.sh --no-cache` as the VM's first build,
the two original bags from a RAM tmpfs. `dry_run_2026-09-25_3/README.txt` has the table of every run
and the host-ROS note: installed as VM_GUIDE §1 then said, the host had no Fast DDS RMW and its first
two host runs were CycloneDDS players (renamed `*_cyclonedds*`, with a CORRECTION line); after
`ros-humble-rmw-fastrtps-cpp` was added, each host run records the RMW its player loaded
(`*_console4.txt`). `g_fix.sh` is the script that ran them.

| folder | run | result |
|---|---|---|
| `vm_2026-09-25_3/` | machine facts | 4 cores, `rmem_max` 212992 |
| `dry_run_2026-09-25_3/` | `dry_run.sh` on both bags; host consoles: the node UDP or `RESENSE_DDS=shm`, the player stock Fast DDS or CycloneDDS, `rmem_max` 212992 or 32 MiB (README step 0); `NODE_DDS=shm console_test.sh` | PASS: both dry runs; stock Fast DDS at 212992 over UDP (2 of 2) and in shm mode (2 of 2, the player maps the node's `root 666` port); step 0 with either player; CycloneDDS in shm mode at 32 MiB; the Docker shm test. FAIL: CycloneDDS at 212992 (shm mode) |

### `bag_metadata/`: the original `metadata.yaml` of the six recordings

These files are copied unchanged from the organizers' dataset. Every recording was made with
`reliability: 1`, which is RELIABLE in rosbag2's QoS encoding (`history: 1` is keep-last,
`depth: 10`, `durability: 2` is volatile). `ros2 bag play` publishes with these recorded
profiles. This is why the node's `input_reliability: auto` subscribes reliable to such a player
(EXPERIMENTS §3b). A best-effort subscription lost 196 of the 201 clouds of `doubleT_obstacle`.

## 3. Quoted but not committed

These runs are quoted in the documents as [team record, unverified]: their raw output is not in
the repository.

| run | date | quoted in | what is missing |
|---|---|---|---|
| v0.6.4 node start-up in the Docker chain (catch-up of the player's burst; first STOP 4.02 → 1.59 s, peak RSS 403–434 MB) | 24.09 | EXPERIMENTS §3b; CHANGELOG | node logs, status captures, `docker stats` |
| the opt-in near-bed path on all 13 759 frames and on set F (five bags 20 → 145 events, ride 47 → 667) | 24.09 | EXPERIMENTS §1e; SCORECARD §3 | the per-frame outputs and summaries of the criteria review of 24.09 |
| the opt-in near-bed path with the gates of `537e220` and of the fix `7df1796` on the six recordings and set O (five bags 141 / 28 / 33 and 459 / 107 / 72) | 24.09 | EXPERIMENTS §1e; ALGORITHM §3.3b, §6; CHANGELOG | the per-frame outputs and summaries of the fix's runs |
| the GPU study and the C++ kernels' A/B timing and identity runs (3 998 frames) | 24.09 | ARCHITECTURE "Native kernels", "GPU: evaluated, not used"; EXPERIMENTS §3 | the profiles, A/B logs and per-frame diffs |
| the judges' own runs (bench under load, 5 Hz and tilt stress tests, `clear_distance` audit) | 24.09 | [`../SCORECARD.md`](../SCORECARD.md) §1–§3 | their outputs (the judges' VM only) |
| the late candidates of 25.09: DBSCAN on cKDTree (identity on 9 240 real calls and 3 998 frames × 2 paths, interleaved A/B timing), the forward crop and `zf` reuse, the first gate runs of the two flags (`short_signature_max_length`, `floating_long_min_length`; six recordings and set O, `--jobs 2`) and of `far_min_height` 1.0, the far-rail check probe | 25.09 | EXPERIMENTS §1f, §3, §7; ARCHITECTURE "Native kernels"; ALGORITHM §3.3, §6; CHANGELOG | the per-frame dumps, A/B logs and gate JSONs (agent scratch space); the two flags' figures on the six recordings and set O recur in the committed [`rules_decision_2026-09-25.json`](results/rules_decision_2026-09-25.json) |
| the stock-Fast-DDS console mode and the 8-core bench kit against a mock `docker` (fail-fast paths, file layout, summary) | 25.09 | CHANGELOG | the mock harness; the real proof is CI (stock mode) and the first run of the kit |
