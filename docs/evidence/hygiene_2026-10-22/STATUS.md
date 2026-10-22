# Status of the hygiene lane (paused)

Branch `claude/hygiene-scripts-1.3`, base `f24d939`. See README.md in this folder for method and counts.

## Done
* Item 2 (personal paths): replaced by `$RESENSE_CACHE` (default `/data/cache`) + `realdata` marker in
  `scripts/analyze_local_body_support.py`, `scripts/analyze_residual_events.py`, `tests/test_evidence_coherence.py`,
  `tests/test_far_structure.py`, `tests/test_fresh_support_analysis.py`. Guard test `tests/test_data_paths.py`
  (its scan finds exactly the 7 old lines on `f24d939`; 15 of 22 collected / 7 deselected without data, 22 with stub folders).
* Item 1: `scripts/README.md` index; `tests/test_unreferenced_scripts.py`; `cache_to_bag.py` fixed for `.npy.zst`
  (output identical on plain caches).
* Full suite on the last tree (before this commit): **2,585 passed, 8 deselected**, exit 0 (venv with `.[dev]` and
  `open3d-cpu`; an earlier run had 1 failure, my guard test matching its own text, fixed). Lint (ruff 0.15.8) and
  `detector_freeze.py verify` PASS at the previous push. Not re-run after this commit.

## In progress / not done
* Item 3 (`test_rail_start.py::test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop`): not diagnosed.
  The dataset download was refused by the permission classifier; not retried. Needs `/data/Датасет.zip`, then
  `cache_extended_ride.py` (integration_1.3 README section 8), then run the test and read which of its four assertions fails.
* README section "Verification of the suite" is not filled in; CI on the head was not awaited (no CI run recorded).

## Next steps
1. Get the dataset (foreground `curl -fL -C -`, check sha256), build the ride cache, run the test, decide stale expectation vs defect.
2. Re-run ruff 0.15.8 check, `detector_freeze.py verify`, full suite; push; record CI job conclusions.

## Blockers
Dataset access (item 3). No other.

## The 24 unreferenced scripts (no test/CI/Docker/script/live doc names them)
All 23 Python ones print `usage:` for `--help` from outside the repo; their `resense` imports (85 names) exist.
Evidence links are in `scripts/README.md`.

| Script | Origin | Found |
|---|---|---|
| bench_health_histogram.py | 44b462e | help OK; evidence cycle_2026-09-28/health_histogram; not run further |
| cache_to_bag.py | 44b462e | BROKEN for .npy.zst, fixed; round-trip test |
| check_synth_labels.py | d9603e0 | help OK; synthetic_labels_2026-10-17; not run further |
| compare_history_stress.py | 44b462e | help OK; cycle_2026-09-28/continuity/history |
| consistency_check.py | 44b462e | works; counts test |
| dust_battery.py | e9d8fc6 | help OK; n3_dust_fix_2026-10-19 |
| lying_person_eval.py | 44b462e | help OK; thin wrapper of far_range_eval.py, not a duplicate |
| ml_second_opinion.py | 44b462e | help OK; archive EXPERIMENTS log |
| mount_survey.py | 44b462e | runs on 130 synthetic frames; fails on inputs shorter than its windows (not a regression) |
| orientation_battery.py | ddf5b63 | help OK; needs judge helpers; orientation_2026-10-18 |
| p2_draft_deck.py | 3486ad9 | needs python-pptx (optional extra); compiles |
| p4_data_intake.py | 44b462e | help OK; p4_start_2026-10-15 |
| p4_linux_intake.py | d9603e0 | help OK; p4_eval_1.1.0_2026-10-16 |
| render_false_targets.py | 44b462e | help OK; archive P4_FALSE_TARGET_DIAGNOSIS |
| robustness_check.py | 44b462e | runs on synthetic frames (plain .npy only) |
| run_offline.sh | 44b462e | wrapper of `resense run`; stub-CLI argument test |
| speed_setf.py | 44b462e | help OK; plain .npy only |
| speed_static_check.py | 44b462e | help OK |
| speed_timing.py | 44b462e | runs on synthetic frames |
| start_offsets.py | 44b462e | runs (synthetic, known bag names only) |
| startup_census.py | 44b462e | runs (synthetic) |
| summarize_oracle_accumulation.py | 44b462e | help OK; oracle_accumulation_2026-09-28 |
| summarize_synthetic_sensitivity.py | 44b462e | help OK; no record names it |
| track_opinion_pipeline.py | f671a62 | help OK; track_opinion_2026-10-21 |

Nothing removed. Unverified beyond start-up: the scripts marked "help OK" only.
