# scripts/ index

Tools and evidence helpers of the repository. This page indexes the files that no test, CI file,
Dockerfile, other script or current document named until the hygiene pass of 22.10
([`docs/evidence/hygiene_2026-10-22/`](../docs/evidence/hygiene_2026-10-22/README.md)). Every
entry says what the file is for, where its measurement is recorded and how it is covered now.
Dated records under `docs/evidence/` keep the commands they were run with; they are history, not
instructions.

Conventions that hold for all of them:

* Python tools run from the repository root (`python scripts/<name>.py ...`) or from anywhere by path;
  `--help` prints the arguments. `tests/test_unreferenced_scripts.py` starts every entry below with
  `--help` from outside the repository.
* Recorded data is found under `$RESENSE_CACHE` (default `/data/cache`), as in `bench_8core.sh`; a test
  that needs it carries `@pytest.mark.realdata(path)` and is deselected, with the path named in the
  summary, where it is absent (`tests/conftest.py`).
* Evaluation and judging runs never modify detector code; these tools only read it.

## Recorded-data tools (reusable)

| File | Purpose | Record | Covered by |
|---|---|---|---|
| `cache_to_bag.py` | Rebuild a ROS 2 bag from a frame cache (`cache_frames.py --int16 --stamps`, plain or `--zstd`) to replay a recording through the real node when the bag is gone. | [`EXPERIMENTS_log_2026-09`](../docs/archive/EXPERIMENTS_log_2026-09.md), [`CAPTAIN.md`](../docs/CAPTAIN.md) | round-trip test, both cache encodings |
| `run_offline.sh` | `resense run` on a bag without ROS (pure-Python `rosbags` reader), optional render directory. | none (wrapper) | argument test with a stub CLI |
| `consistency_check.py` | Is a change's gain spread over the recordings or carried by one? Leave-one-subset-out comparison of two `eval_real.py` runs. | [`EXPERIMENTS_log_2026-09`](../docs/archive/EXPERIMENTS_log_2026-09.md) | counts test on built run folders |
| `compare_history_stress.py` | Strict paired acceptance of two detector runs on the 33 clear-recording history-stress cases. | [`cycle_2026-09-28/continuity/history`](../docs/evidence/cycle_2026-09-28/continuity/history/README.md), [`health_compare_counts/protocol_v2.md`](../docs/evidence/cycle_2026-09-29/health_compare_counts/protocol_v2.md) | `--help` |
| `startup_census.py` | What a fresh detector reports in the first seconds of each bag (false STOP paid once per bag). | [`p4_full_data_2026-09-28`](../docs/evidence/results/p4_full_data_2026-09-28/README.md) | `--help` |
| `start_offsets.py` | False alarms and detections against the frame the processing starts from (DDS start-up loses 2-4 s). | [`p4_full_data_2026-09-28`](../docs/evidence/results/p4_full_data_2026-09-28/README.md) | `--help` |
| `robustness_check.py` | Replay cached bags at 10/5 Hz or with a known sensor re-mount. | [`P4_AUDIT`](../docs/archive/P4_AUDIT.md), [`p4_full_data_2026-09-28`](../docs/evidence/results/p4_full_data_2026-09-28/README.md) | `--help` |
| `mount_survey.py` | How stable the per-frame roll/pitch measurement is along a recording. | [`EXPERIMENTS_log_2026-09`](../docs/archive/EXPERIMENTS_log_2026-09.md) (section 6) | `--help` |
| `orientation_battery.py` | B4: the 24 axis-aligned sensor orientations through the node replica with auto-calibration on. | [`orientation_2026-10-18`](../docs/evidence/orientation_2026-10-18/README.md), [`b4_orientation_fix_2026-10-18`](../docs/evidence/b4_orientation_fix_2026-10-18/PROTOCOL.md) | `--help` |
| `dust_battery.py` | Clean/dust paired measurements on complete node-decoded recordings. | [`n3_dust_fix_2026-10-19`](../docs/evidence/n3_dust_fix_2026-10-19/PROTOCOL.md) | `--help` |
| `track_opinion_pipeline.py` | The track opinion (`tracking.doubt_model`) end to end: collect, train, cross-fit. | [`track_opinion_2026-10-21`](../docs/evidence/track_opinion_2026-10-21/README.md) | `--help` |

## Set F and speed experiments (synthetic objects on the moving ride)

| File | Purpose | Record | Covered by |
|---|---|---|---|
| `lying_person_eval.py` | Set F with a person lying on the track: a 0.5 x 1.8 x 0.35 m box across or along it; thin wrapper of `far_range_eval.py` (not a duplicate: it registers the objects and the bed depth). | [`EXPERIMENTS_log_2026-09`](../docs/archive/EXPERIMENTS_log_2026-09.md) (section 2d) | `--help` |
| `speed_setf.py` | Set F with the train speed from the ICP reference: what the LiDAR-only estimate and a given speed add at long range. | [`EXPERIMENTS_log_2026-09`](../docs/archive/EXPERIMENTS_log_2026-09.md) | `--help` |
| `speed_static_check.py` | Would a "static-world" rule (obstacle approaches at exactly the train speed) remove false alarms? | [`EXPERIMENTS_log_2026-09`](../docs/archive/EXPERIMENTS_log_2026-09.md) | `--help` |
| `speed_timing.py` | Latency of the speed paths, interleaved on the same frames in one process. | [`EXPERIMENTS_log_2026-09`](../docs/archive/EXPERIMENTS_log_2026-09.md) | `--help` |
| `ml_second_opinion.py` | Learned second opinion on the geometric candidates (experiment, v0.6; `ml_dataset.py` output). | [`EXPERIMENTS_log_2026-09`](../docs/archive/EXPERIMENTS_log_2026-09.md) | `--help` |

## Evidence helpers (run once for a dated record; kept so the record can be repeated)

| File | Purpose | Record | Covered by |
|---|---|---|---|
| `bench_health_histogram.py` | Histogram-only parity/timing probe on one original PointCloud2 message. | [`cycle_2026-09-28/health_histogram`](../docs/evidence/cycle_2026-09-28/health_histogram/README.md) | `--help` |
| `check_synth_labels.py` | Independent checks of `label_marked_objects.py` labels against the exact reference, from the raw points. | [`synthetic_labels_2026-10-17`](../docs/evidence/synthetic_labels_2026-10-17/README.md) | `--help` |
| `p4_data_intake.py` | H0 local inventory: gate stamps, raw headers, float32 node caches. | [`p4_start_2026-10-15/CHECKS.md`](../docs/evidence/p4_start_2026-10-15/CHECKS.md) | `--help` |
| `p4_linux_intake.py` | Prove a Linux node-decoded cache equals the committed Windows H0/X3 inputs. | [`p4_eval_1.1.0_2026-10-16`](../docs/evidence/p4_eval_1.1.0_2026-10-16/README.md) | `--help` |
| `p2_draft_deck.py` | P2's prerelease draft deck from the immutable P4 export, without rescoring (needs `python-pptx`, the `presentation` extra). | [`p2_execution_2026-10-16/CHECKS.md`](../docs/evidence/p2_execution_2026-10-16/CHECKS.md) | `--help` (skipped without `pptx`) |
| `render_false_targets.py` | Render exact false-target supports from `trace_false_targets.py`; no inference labels. | [`P4_FALSE_TARGET_DIAGNOSIS`](../docs/archive/P4_FALSE_TARGET_DIAGNOSIS.md) | `--help` |
| `summarize_oracle_accumulation.py` | Summarize retained oracle diagnostics without re-running geometry or clustering. | [`oracle_accumulation_2026-09-28`](../docs/evidence/results/oracle_accumulation_2026-09-28/README.md) | `--help` |
| `summarize_synthetic_sensitivity.py` | Summarize paired `synthetic_sensitivity.py` reports with the v1 physical-label caveats kept apart. No record names it. | companion of `synthetic_sensitivity.py` ([`cycle_2026-09-28/evaluation`](../docs/evidence/cycle_2026-09-28/evaluation/README.md)) | `--help` |

Nothing was removed: no entry is an exact duplicate (`lying_person_eval.py` and `far_range_eval.py`
differ) or superseded by a maintained tool.
