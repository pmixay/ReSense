# Run Evidence

> **Purpose:** index of the raw evidence behind the documented numbers: the result summaries in
> `results/`, the logs, captures and bench output of each run, and the recordings' original
> metadata. One line per file or folder: what it is, date, commit, result.
> **Audience:** team, jury · **Owner:** P1 (runs, timing), P4 (result summaries) · **Language:** EN
> **Last verified:** 2026-09-29: every link of this index; rows added for the 28.09 team VM run
> and the independent judgement of 28.09 evening; each file remains the record of its own date ·
> **Status:** current

Every file here is the record of one run and is not rewritten: a new run gets a new file or folder
(`results/<what>_<date>.json`, `<run>_<date>/`). "Log §…" refers to the full experiment log
[`../archive/EXPERIMENTS_log_2026-09.md`](../archive/EXPERIMENTS_log_2026-09.md); the current
results are in [`../EXPERIMENTS.md`](../EXPERIMENTS.md) and the criteria judgement in
[`../SCORECARD.md`](../SCORECARD.md). Day-1 results that later runs superseded are in
[`../archive/results/`](../archive/results). `docs/extended_dataset_intake.json` (the ride's
per-file speeds and intake events) stays in `docs/` because scripts read it.

**Start here** (the sealed detector and the runs of 28.09):

| what | where |
|---|---|
| the detector seal and its full gate | [`detector_freeze_2026-09-27.json`](detector_freeze_2026-09-27.json), [`results/regression_gate_2026-09-27_quality.json`](results/regression_gate_2026-09-27_quality.json) (= [the current baseline](results/regression_baseline_2026-09-27_quality.json)) |
| the independent judgement of 28.09 evening (`464f5bc`), basis of the SCORECARD | [`judgement_2026-09-28/`](judgement_2026-09-28/README.md) |
| per-frame outputs of the sealed detector with a recount script | [`judge_outputs_2026-09-28/`](judge_outputs_2026-09-28/README.md) |
| the full team VM run of 28.09 (`464f5bc`) | [`vm_2026-09-28/summary.md`](vm_2026-09-28/summary.md) |
| the node's input path and end-to-end latency through ROS (28.09) | [`node_input_2026-09-28/`](node_input_2026-09-28/README.md) |

## 1. `results/`: summaries of the experiments

One JSON (or folder) per experiment, each with a `note`, `_meta` or `source` block that names what
was run; "code" is the commit it records.

| file | date | code | what it is, result |
|---|---|---|---|
| [`cycle_2026-09-29/competitor_rules/`](cycle_2026-09-29/competitor_rules/gate_table.md), [`detector_freeze_2026-09-29_competitor_rules.json`](detector_freeze_2026-09-29_competitor_rules.json) | 29.09 evening | `ee7b920`, `f67e4fb` | full gates of every rule taken from other case 5 repositories on the locally cached organizer data (the sealed gate reproduced exactly); the sealing gate of the three shipped rules: PASS, ride 32 / 31 → 26 / 28 events / STOP episodes, nothing worse; veto latency A/B `latency_ab.json` ([record](../COMPETITOR_REVIEW_2026-09-29.md) §6) |
| [`competitor_rule_screen_2026-09-29.json`](results/competitor_rule_screen_2026-09-29.json) | 29.09 | sealed detector (`70faef90…`) | two rules of another repository screened as post-filters on the sealed detector's saved outputs (empty recordings, `doubleT_obstacle`, set O, the ride's residual false events) and one advisory-promotion screen; recomputed by `scripts/screen_competitor_rules.py` and a test ([record](../COMPETITOR_REVIEW_2026-09-29.md)): neither rule adopted |
| [`regression_gate_2026-09-27_quality.json`](results/regression_gate_2026-09-27_quality.json), [`regression_baseline_2026-09-27_quality.json`](results/regression_baseline_2026-09-27_quality.json) | 27.09 | `d572807` (detector `352ca13`) | full gate of the sealed detector against `_ride_p3d`: PASS, no waivers; the current baseline |
| [`quality_cycle_2026-09-27/`](results/quality_cycle_2026-09-27) | 27.09 | `352ca13` | raw material of the 27.09 cycle ([record](../archive/QUALITY_CYCLE_2026-09-27.md)): screens, review fixes, ablations, acceptance, history stress, the 72-case [plan](results/quality_cycle_2026-09-27/novel_plan.json) and [results](results/quality_cycle_2026-09-27/novel_results.json.gz), [side-symmetry check](results/quality_cycle_2026-09-27/side_person_check.json), the opinion's [cross-fitted ride](results/quality_cycle_2026-09-27/opinion_crossfit_2x_margin.json) ([zero margin](results/quality_cycle_2026-09-27/opinion_crossfit_zero_margin.json)) |
| [`branch_integration_2026-09-27/`](results/branch_integration_2026-09-27) | 27.09 | integration head | test logs and receipts of the branch integration ([record](../archive/BRANCH_INTEGRATION_2026-09-27.md)) |
| [`p1_p2_merge_docs_2026-09-27.json`](results/p1_p2_merge_docs_2026-09-27.json) | 27.09 | P1/P2 merge | receipt of the P1/P2 documentation merge: changes, validation, unchanged evidence |
| [`regression_gate_2026-09-26_freeze.json`](results/regression_gate_2026-09-26_freeze.json) | 26.09 night | P3d | fresh complete gate of the P3d seal: 183 gated rows unchanged, no waivers |
| [`regression_gate_2026-09-26_comment_correction.json`](results/regression_gate_2026-09-26_comment_correction.json), [`quality_comment_baseline_2026-09-26/`](results/quality_comment_baseline_2026-09-26/README.md) | 26.09 | `cc834fc` | comment-only correction of the P3d sources: full gate, every enforced metric unchanged |
| `quality_cycle_2026-09-26_*`, `quality_monitoring_*`, `quality_combined_runtime_2026-09-26_protocol.json`, [`quality_freshness_2026-09-26/`](results/quality_freshness_2026-09-26/README.md), [`quality_delivery_2026-09-26/`](results/quality_delivery_2026-09-26/README.md), [`quality_root_checks_2026-09-26/`](results/quality_root_checks_2026-09-26/README.md) | 26.09 | P3d base | the 26.09 quality cycle ([record](../archive/QUALITY_CYCLE_2026-09-26.md)), each protocol registered before its runs: node freshness shipped; candidates M1, M2, D1, T1 rejected; the combined runtime run FAIL (one false STOP at 53 m) |
| [`p4_A1_2026-09-26/`](results/p4_A1_2026-09-26/README.md), [`p4_A1_novel_plan_2026-09-26.json`](results/p4_A1_novel_plan_2026-09-26.json) | 26.09 | P3d base | A1, directional association allowance ([protocol](../archive/P4_ASSOCIATION_A1_PROTOCOL.md)): rejected (one placement case regresses) |
| [`p4_false_targets_2026-09-26/`](results/p4_false_targets_2026-09-26/README.md) | 26.09 | P3d | exact trace of all 45 ride false-event identities ([diagnosis](../archive/P4_FALSE_TARGET_DIAGNOSIS.md)) |
| [`p4_ride_scenes_2026-09-26/`](results/p4_ride_scenes_2026-09-26/README.md) | 26.09 | P3d | all 45 ride false events with a scene review |
| [`p4_novel_plan_2026-09-26.json`](results/p4_novel_plan_2026-09-26.json), [`p4_novel_protocol_2026-09-26.json`](results/p4_novel_protocol_2026-09-26.json), [`p4_novel_results_2026-09-26.json`](results/p4_novel_results_2026-09-26.json), [`p4_novel_source_2026-09-26/`](results/p4_novel_source_2026-09-26/README.md) | 26.09 | P3d | fixed 72-case placement sensitivity study of the organizers' objects (not recall) |
| [`p3_p4_prereg_2026-09-26_evening.json`](results/p3_p4_prereg_2026-09-26_evening.json), [`regression_gate_2026-09-26_head_fresh_machine.json`](results/regression_gate_2026-09-26_head_fresh_machine.json), [`regression_gate_2026-09-26_p4_candidate_B_full.json`](results/regression_gate_2026-09-26_p4_candidate_B_full.json), [`regression_gate_2026-09-26_axis_union_fixed_full.json`](results/regression_gate_2026-09-26_axis_union_fixed_full.json), [`p4_census_p3d_2026-09-26.json`](results/p4_census_p3d_2026-09-26.json), [`p4_robustness_2026-09-26_evening/`](results/p4_robustness_2026-09-26_evening), [`p4_completion_2026-09-26_evening.json`](results/p4_completion_2026-09-26_evening.json) | 26.09 evening | `53b75d4` (detector `fa18832`) | P3d reproduced on a second machine: strict gate identical incl. the ride and set F; candidate B and the envelope union pass, not shipped; stress and start-up census (log §1p) |
| [`p4_candidates_2026-09-26-prereg.json`](results/p4_candidates_2026-09-26-prereg.json), [`p4_candidate_decisions_2026-09-26.json`](results/p4_candidate_decisions_2026-09-26.json), [`p4_candidates_p3d_prereg_2026-09-26.json`](results/p4_candidates_p3d_prereg_2026-09-26.json), [`p4_p3d_candidate_decisions_2026-09-26.json`](results/p4_p3d_candidate_decisions_2026-09-26.json), [`p4_candidate_B_checks_2026-09-26/`](results/p4_candidate_B_checks_2026-09-26) | 26.09 | `dcf7f90`, P3d `fa18832` | P4 candidates A / B / C, pre-registered: A and C change nothing on their targets; B one extra STOP frame, not shipped |
| [`p4_available_reference_2026-09-26.json`](results/p4_available_reference_2026-09-26.json), [`p4_artifacts_2026-09-26/`](results/p4_artifacts_2026-09-26/manifest.json), [`p4_p3d_available_reference_2026-09-26.json`](results/p4_p3d_available_reference_2026-09-26.json), [`p4_p3d_artifacts_2026-09-26/`](results/p4_p3d_artifacts_2026-09-26/manifest.json) | 26.09 | `dcf7f90`, P3d `fa18832` | P4 reference runs on the data then available (no ride / set F cache): gate, stress, start-up, set O audit, output hashes |
| [`p4_false_alarm_inventory_2026-09-26.json`](results/p4_false_alarm_inventory_2026-09-26.json), [`p4_p3d_false_alarm_inventory_2026-09-26.json`](results/p4_p3d_false_alarm_inventory_2026-09-26.json) | 26.09 | `dcf7f90`, P3d | false STOP intervals of the empty recordings with distances and reasons |
| [`p4_seto_raw_cache_comparison_2026-09-26.json`](results/p4_seto_raw_cache_comparison_2026-09-26.json), [`p4_p3d_seto_raw_cache_comparison_2026-09-26.json`](results/p4_p3d_seto_raw_cache_comparison_2026-09-26.json) | 26.09 | `dcf7f90`, P3d | set O from the raw bag vs the int16 cache: small differences from 5 mm quantisation; the cache is the gate reference |
| [`p4_setS_paired_2026-09-26.json`](results/p4_setS_paired_2026-09-26.json), [`p4_p3d_setS_paired_2026-09-26.json`](results/p4_p3d_setS_paired_2026-09-26.json) | 26.09 | `dcf7f90`, P3d | set S, bed vs legacy placement of the same 108 objects |
| [`p4_seto_startup_2026-09-26.json`](results/p4_seto_startup_2026-09-26.json), [`p4_data_intake_2026-09-26.json`](results/p4_data_intake_2026-09-26.json), [`p4_validation_2026-09-26.json`](results/p4_validation_2026-09-26.json), [`p4_validation_p3d_2026-09-26.json`](results/p4_validation_p3d_2026-09-26.json), [`p4_completion_checklist_p3d_2026-09-26.json`](results/p4_completion_checklist_p3d_2026-09-26.json) | 26.09 | `ed03bc2`, `dcf7f90`, P3d | set O fresh-start census; data intake checks; P4's software checks and completion checklist |
| [`seto_suffix_p3c_2026-09-26.json`](results/seto_suffix_p3c_2026-09-26.json), [`seto_suffix_2026-09-26.json`](results/seto_suffix_2026-09-26.json) | 26.09 | `ed03bc2`, `11c50a7` | set O replayed from frame 0: 1 false STOP frame (140.7 m) in the 706-frame suffix (log §1g) |
| [`regression_baseline_2026-09-26_ride_p3d.json`](results/regression_baseline_2026-09-26_ride_p3d.json), [`regression_gate_2026-09-26_range_final.json`](results/regression_gate_2026-09-26_range_final.json) | 26.09 | `fa18832` | the P3d baseline (STOP keep with its 10 s cap): PASS against `_ride_p3c` (log §1o) |
| [`p3_range_2026-09-26.json`](results/p3_range_2026-09-26.json), [`regression_gate_2026-09-26_range.json`](results/regression_gate_2026-09-26_range.json), [`regression_gate_2026-09-26_range_b10.json`](results/regression_gate_2026-09-26_range_b10.json) | 26.09 | `5dfc679`, `ffb3fe7` | what limits range on set O; the B10 STOP keep shipped, A / B / C not (log §1o) |
| [`regression_baseline_2026-09-26_ride_p3c.json`](results/regression_baseline_2026-09-26_ride_p3c.json), [`regression_gate_2026-09-26_p3_integrated.json`](results/regression_gate_2026-09-26_p3_integrated.json), [`p3_integration_2026-09-26.json`](results/p3_integration_2026-09-26.json) | 26.09 | `ed03bc2` | the P3 items of 26.09 combined: gate PASS; the envelope union blocked by the safety review (log §1n) |
| [`p3_rail_start_2026-09-26.json`](results/p3_rail_start_2026-09-26.json), [`regression_gate_2026-09-26_rail_start.json`](results/regression_gate_2026-09-26_rail_start.json) | 26.09 | `16c4cac` | rail heads ahead of a standing train at a fresh start: rule shipped (log §1k) |
| [`p3_near_escalation_2026-09-26.json`](results/p3_near_escalation_2026-09-26.json) | 26.09 | `2797929`, `33860bc` | near-field escalation A and wall keep D: shipped (log §1l) |
| [`p3_edge_axis_2026-09-26.json`](results/p3_edge_axis_2026-09-26.json), [`regression_gate_2026-09-26_edge_axis.json`](results/regression_gate_2026-09-26_edge_axis.json) | 26.09 | `f48ec89` | envelope also from the sensor axis: gate PASS, not shipped (safety review) (log §1m) |
| [`p3_startup_2026-09-26.json`](results/p3_startup_2026-09-26.json) | 26.09 | `867bb8a`, `c1d3010` | start-up of a fresh bag: census; three rules tried, none shipped (log §1j) |
| [`regression_baseline_2026-09-25_ride_p3b.json`](results/regression_baseline_2026-09-25_ride_p3b.json), [`p3_round2_review_fixes_2026-09-26.json`](results/p3_round2_review_fixes_2026-09-26.json), [`p3_round2_combined_2026-09-25.json`](results/p3_round2_combined_2026-09-25.json) | 25–26.09 | `0c8f8e1` | the round-2 P3 items with their safety review: gate PASS, the refinement off (log §1i) |
| [`p3_robustness_2026-09-25.json`](results/p3_robustness_2026-09-25.json), [`regression_gate_2026-09-25_robustness.json`](results/regression_gate_2026-09-25_robustness.json), [`scorecard13_p3_2026-09-25.json`](results/scorecard13_p3_2026-09-25.json) | 25.09 | `1c96233`, `ed3affe` | robustness at 5 Hz and +3° roll / pitch: flags K3d shipped (log §1i) |
| [`p3_clear_distance_2026-09-25.json`](results/p3_clear_distance_2026-09-25.json) | 25.09 | `1f1153e` | conservative `clear_distance`: cap R1 shipped although it missed its clutter limit by 0.5 pp (log §1i) |
| [`p3_thin_hanging_2026-09-25.json`](results/p3_thin_hanging_2026-09-25.json), [`regression_gate_2026-09-25_thin_hanging.json`](results/regression_gate_2026-09-25_thin_hanging.json) | 25.09 | `e22b41c`, `c0b4f2f` | thin hanging objects: candidate A and the rail lock shipped (log §1i) |
| [`p3_signatures_2026-09-25.json`](results/p3_signatures_2026-09-25.json) | 25.09 | `edec4da` | free-hanging exemption of `floating`: shipped (log §1i) |
| [`regression_baseline_2026-09-25_ride_p3.json`](results/regression_baseline_2026-09-25_ride_p3.json), [`p3_review_fixes_2026-09-25.json`](results/p3_review_fixes_2026-09-25.json), [`p3_combined_2026-09-25.json`](results/p3_combined_2026-09-25.json) | 25.09 | `154db25`, `95ff725` | the P3 items of 25.09 combined, the rail-shadow review fixes: gate PASS (log §1h) |
| [`p3_rail_shadow_2026-09-25.json`](results/p3_rail_shadow_2026-09-25.json), [`regression_gate_2026-09-25_rail_shadow.json`](results/regression_gate_2026-09-25_rail_shadow.json) | 25.09 | `9f2e2e4` | the rail shadow of set O #1: B2 shipped (log §1h) |
| [`p3_bed_bin_2026-09-25.json`](results/p3_bed_bin_2026-09-25.json), [`p3_far_switch_2026-09-25.json`](results/p3_far_switch_2026-09-25.json), [`regression_gate_2026-09-25_far_axis_both_sides_2.json`](results/regression_gate_2026-09-25_far_axis_both_sides_2.json), [`p3_platform_end_2026-09-25.json`](results/p3_platform_end_2026-09-25.json) | 25.09 | `cb733c6`, `be39362`, `1ae1952` | far bed bin, far switch parts, platform end: every candidate not shipped (log §1h) |
| [`scorecard13_2026-09-25.json`](results/scorecard13_2026-09-25.json) | 25.09 | `7466979` | the six bags at 5 Hz and +3° roll / pitch; the set O suffix (superseded by the continuous replay above) (log §1g) |
| [`long_rule_bottom_2026-09-25.json`](results/long_rule_bottom_2026-09-25.json) | 25.09 | `0bb1ba3` | review fix of the long overhead rule: bottom above 1.6 m (log §1f) |
| [`rules_decision_2026-09-25.json`](results/rules_decision_2026-09-25.json) | 25.09 | `7290873` | long overhead rule GO, short signatures NO-GO (log §1f) |
| [`regression_baseline_2026-09-25_ride_column.json`](results/regression_baseline_2026-09-25_ride_column.json), [`column_hold_2026-09-25.json`](results/column_hold_2026-09-25.json), [`regression_gate_2026-09-25_column_hold.json`](results/regression_gate_2026-09-25_column_hold.json) | 25.09 | `d117c8c`, `8b9f72d` | `tracking.column_hold` 2 chosen and shipped (log §3a) |
| [`regression_baseline_2026-09-25_ride.json`](results/regression_baseline_2026-09-25_ride.json), [`regression_baseline_2026-09-25.json`](results/regression_baseline_2026-09-25.json), [`regression_gate_2026-09-25_8932f3a.json`](results/regression_gate_2026-09-25_8932f3a.json) | 25.09 | `935eecf`, `ca557cb`, `8932f3a` | the first gate baselines (superseded) and the gate on the merges of 25.09 |
| [`experiments_2026-09-24_train_speed.json`](results/experiments_2026-09-24_train_speed.json) | 24.09 | `537e220` | train speed from the LiDAR alone (log §9) |
| [`experiments_2026-09-24_remeasure.json`](results/experiments_2026-09-24_remeasure.json) | 24.09 | `4cd32d6` vs `1210580` | re-measurement of the then-current code (log "Re-measurement", §2d) |
| [`experiments_p4_fake_labelled.json`](results/experiments_p4_fake_labelled.json), [`experiments_p4_fake_unlabelled.json`](results/experiments_p4_fake_unlabelled.json) | 24.09 | `07b5e0c` | set O scored with P4's labels, and the first unlabelled pass (log §1e, §2e) |
| [`experiments_p4_setf_straight_paired.json`](results/experiments_p4_setf_straight_paired.json), [`experiments_p4_setf_paired.json`](results/experiments_p4_setf_paired.json) | 24.09 | config hash in the file | set F, legacy vs anchored placement (log §2d) |
| [`experiments_v0.6.3_real_fullrate.json`](results/experiments_v0.6.3_real_fullrate.json), [`experiments_v0.6.3_start_offsets.json`](results/experiments_v0.6.3_start_offsets.json), [`experiments_v0.6.2_real_fullrate.json`](results/experiments_v0.6.2_real_fullrate.json), [`experiments_v0.6.2_margins_lying.json`](results/experiments_v0.6.2_margins_lying.json), [`experiments_v0.6.2_setF.json`](results/experiments_v0.6.2_setF.json) | 23.09 | v0.6.2, v0.6.3 | real bags at full rate, start offsets, margins, lying person, set F (log §0, §2d) |
| [`experiments_v0.6.1_real_fullrate.json`](results/experiments_v0.6.1_real_fullrate.json), [`experiments_v0.6.1_setF.json`](results/experiments_v0.6.1_setF.json) | 22–23.09 | `8689bf6` | v0.6.1 on the real bags and set F (log §0a, §2d) |
| [`experiments_v0.5_real_fullrate.json`](results/experiments_v0.5_real_fullrate.json) | 22.09 | `b67c5c1` | v0.5 on every frame, ablations, timing (log §1, §1b, §3) |
| [`experiments_v0.4_real_fullrate.json`](results/experiments_v0.4_real_fullrate.json), [`experiments_v0.4_synthetic_on_real.json`](results/experiments_v0.4_synthetic_on_real.json) | 21.09 | `f2c57e5`, `f4e311f` | v0.3 / v0.4 on the real bags; set S |

## 2. Run folders

| folder | date | code | what ran, result |
|---|---|---|---|
| [`judgement_2026-09-28/`](judgement_2026-09-28/README.md) | 28.09 evening | `464f5bc` | the independent judgement behind [`../SCORECARD.md`](../SCORECARD.md): 11 jury-chain captures with the judge's own listener, offline per-frame outputs of all recordings, set O and the whole ride, the range test (a real person pasted into five tunnels), every script that produced and scored them |
| [`vm_2026-09-28/`](vm_2026-09-28/summary.md) | 28.09 | `464f5bc` | the full [VM guide](../VM_GUIDE.md) on a team VM (4 physical cores, 79 MB/s disk): machine facts, data logs, 754 tests passed, `summary.md` (every run and the findings), `scripts/` |
| [`dry_run_2026-09-28/`](dry_run_2026-09-28/e2e_vm.txt) | 28.09 | `464f5bc` | `--no-cache` build; dry runs of both original bags, cold and warm twice each; host consoles (README jury steps, stock Fast DDS at 212992, CycloneDDS at 32 MiB, shm mode); fast input identity: all PASS, 453 of 453 frames |
| [`bench_2026-09-28/`](bench_2026-09-28/summary.txt) | 28.09 | `464f5bc` | `dry_obstacle_native` PASS (10.0 fps, p95 63 ms), every native run and both console tests PASS; numpy FAIL at 360° (exit 1) |
| [`gate_2026-09-28/`](gate_2026-09-28/gate_table.txt) | 28.09 | `464f5bc` | gate with the ride and set F against `regression_baseline_2026-09-27_quality.json`: PASS, identical but informational latency rows |
| [`export_2026-09-28/`](export_2026-09-28/archive.txt) | 28.09 | `464f5bc` | `export_image.sh` + `load_image.sh`: PASS, 475 947 817 bytes, sha256 in `archive.txt` |
| [`offline_2026-09-28/`](offline_2026-09-28/steps.txt) | 28.09 | `464f5bc` | offline rehearsal, nothing allowed out: pass 1 `dry_clear` FAIL after a 1.4 s storage stall, the rest PASS; `warm_bags/` (bags pre-read): all PASS |
| [`judge_outputs_2026-09-28/`](judge_outputs_2026-09-28/README.md) | 28.09 | `806b6c4` (detector = the seal) | per-frame outputs of the sealed detector by an independent judge (six recordings, set O offline and through the node, two ride segments, set F) with `recompute.py` |
| [`node_input_2026-09-28/`](node_input_2026-09-28/README.md) | 28.09 | before / after the node's input change | dry runs of both recordings through ROS, end-to-end latency and CPU (`e2e_all_frames.py`), the detector's input identical frame by frame (`fast_input.json`) |
| [`detector_freeze_2026-09-27.json`](detector_freeze_2026-09-27.json) | 27.09 | `d572807` | the current detector seal ([`../DETECTOR_FREEZE.md`](../DETECTOR_FREEZE.md)) |
| [`p1_p2_supported_playback_2026-09-27/`](p1_p2_supported_playback_2026-09-27/README.md) | 27.09 | `5a27c66`, `2f23719` | CI cold replays of both original bags at read-ahead 10: PASS; [verified-bag cache run](p1_p2_supported_playback_2026-09-27/cached_bags_run_36319767736/README.md) PASS |
| [`p1_p2_completion_2026-09-26/`](p1_p2_completion_2026-09-26/README.md) | 26–27.09 | branch heads | the earlier CI cold-bag runs (failed, cancelled, passed) and the viewer / dashboard checks |
| [`freeze_2026-09-26/`](freeze_2026-09-26/README.md) | 26.09 night | P3d, node `0f808fe` | node checks of the P3d freeze (cold / warm / clear / stock console), 621 tests, [hash manifest](freeze_2026-09-26/manifest.json) |
| [`detector_freeze_2026-09-26.json`](detector_freeze_2026-09-26.json), [`detector_freeze_2026-09-26_before_comment_correction.json`](detector_freeze_2026-09-26_before_comment_correction.json) | 26.09 | P3d | the superseded P3d seals |
| [`presentation_2026-09-26/`](presentation_2026-09-26/manifest.json) | 26.09 | — | presentation output and source hashes, dashboard and overview build logs |
| [`rejudge_2026-09-26/`](rejudge_2026-09-26/README.txt) | 26.09 evening | `be5f5fc` | raw runs of a superseded re-judgement: tests, offline dry runs (cold and warm), stock console, set O, full gate, bench |
| [`dry_run_2026-09-25_3/`](dry_run_2026-09-25_3/README.txt), [`vm_2026-09-25_3/`](vm_2026-09-25_3/machine.txt) | 25.09 evening | `d4b396e` | third team VM, transport fixes: stock Fast DDS at 212992 PASS over UDP and in shm mode; CycloneDDS needs 32 MiB |
| `vm_`, `dry_run_`, `bench_`, `gate_`, `export_`, `offline_2026-09-25_2/` | 25.09 | `76bf24e` | second team VM, confirmation run: dry runs, bench (native), gate, export and offline dry runs PASS; the offline jury console FAIL (host buffer); its "Fast DDS" host console was a CycloneDDS player (files carry a CORRECTION line) |
| `vm_`, `dry_run_`, `bench_`, `gate_`, `export_`, `offline_2026-09-25/` ([summary](vm_2026-09-25/summary.md)) | 25.09 | `7290873` | first team VM (bags from a RAM tmpfs): dry runs FAIL online, offline and in the bench (drops, 3 alarm frames), CycloneDDS host FAIL; console tests, gate and export PASS; fixed the same day (log §3a) |
| [`regression_gate_2026-09-25/`](regression_gate_2026-09-25) | 25.09 | dev VM | the gate demonstrated: same code native and numpy PASS, `--set cluster.min_points=8` FAIL |
| [`timing_2026-09-23/`](timing_2026-09-23), [`mount_check_2026-09-23/`](mount_check_2026-09-23) | 23.09 | v0.6.3 | `resense bench` on every recording; mount calibration check before / after v0.6.3 (log §3, §6) |
| [`docker_2026-09-23/`](docker_2026-09-23) | 23.09 | v0.6.2, v0.6.3 | the node in Docker on bags rebuilt from the frame cache, console tests, the RViz chain ([video](../video/docker_chain_rviz.mp4)) (log §3b) |
| [`bag_metadata/`](bag_metadata) | — | — | the organizers' original `metadata.yaml` of the six recordings (RELIABLE QoS: why the node subscribes reliable) |

`bench_<date>/` folders are written by `scripts/bench_8core.sh` itself (`system.txt`, `facts.txt`,
`build/`, `dry_*_{native,numpy}/`, `ct_{image,stock}/`, `offline/`, `runs.tsv`, `summary.txt`).
A new VM run adds its folders here as the [VM guide](../VM_GUIDE.md) §6 says.

## 3. Quoted but not committed

These runs are quoted in dated records as [team record, unverified]: their raw output is not in
the repository.

| run | date | quoted in | what is missing |
|---|---|---|---|
| v0.6.4 node start-up in the Docker chain (catch-up of the player's burst) | 24.09 | log §3b; archived changelog | node logs, status captures, `docker stats` |
| the opt-in near-bed path on all frames, on set F and with the gates of `537e220` / `7df1796` | 24.09 | log §1e; ALGORITHM §3.3b, §6 | per-frame outputs and summaries |
| the GPU study and the C++ kernels' A/B timing and identity runs (3 998 frames) | 24.09 | ARCHITECTURE "Native kernels", "GPU: evaluated, not used"; log §3 | profiles, A/B logs, per-frame diffs |
| the judges' own runs of 24.09 (bench under load, stress tests, `clear_distance` audit) | 24.09 | the archived captain board and log | their outputs (the judges' VM only) |
| the late candidates of 25.09 (DBSCAN on cKDTree, forward crop, the first gate runs of two flags, `far_min_height` 1.0, the far-rail probe) | 25.09 | log §1f, §3, §7; ARCHITECTURE; ALGORITHM §3.3, §6 | per-frame dumps, A/B logs, gate JSONs; the two flags' figures recur in [`rules_decision_2026-09-25.json`](results/rules_decision_2026-09-25.json) |
| the stock-Fast-DDS console mode and the bench kit against a mock `docker` | 25.09 | archived changelog | the mock harness; the real proof is CI and the VM runs |

## Experimental branch acceptance, 28.09

* [P3 integration](../P3_SCORE_SYNC_2026-09-28.md) records accepted branch changes and the scope of
  each assessment.
* [Health histogram evidence](cycle_2026-09-28/health_histogram/README.md) contains the full
  native gate, parity comparison and runtime capture provenance. These runtime captures use
  the earlier node and do not validate the subsequent node changes.
* [Node startup A/B](node_startup_2026-09-29/README.md) is main branch evidence with startup
  thinning at 0.2 s; the experimental branch keeps startup thinning disabled by default.
