# J1 on release day — runbook (pre-built 16.10)

The release J1 (BACKLOG J1) runs on the accepted 1.1.0 release: tag, archive, image. Everything that does
not need the release image is already run on the sealed 1.1.0 tree and on 707ea9c as a control
([prebuild/](prebuild/)). On release day, only the identity check and the steps marked **left** remain.
Use one runtime throughout and pin `OPENBLAS_CORETYPE=Haswell`
([P4 amendment 1](../p4_eval_1.1.0_2026-10-16/PROTOCOL.md)); always set `RESENSE_REPO` to the evaluated checkout.

| J1 deliverable | state | how |
|---|---|---|
| identity: release tag / commit / image = sealed tree `db3f588d…`; `detector_freeze.py verify` PASS in the run log | **left** | `git ls-tree -r <tag> -- resense native configs setup.py pyproject.toml ros2_ws/src/resense_ros/config` must equal the measured tree; image ID and archive SHA-256 from the release |
| 8 per-recording CSVs: six bags | **pre-built** (pre-release) on `492e407` | [dryrun/dryrun.json](dryrun/dryrun.json): 0 decisions differ from 707ea9c; the 707ea9c dry run reproduces the judge |
| 8 per-recording CSVs: Set O | **left** (cheap) | `judge_runner.py --bag <cloud_with_fake_obj> --out …` (~1,510 frames), then `score_objects.py`. The X3 nominal Set O metrics are already identical between versions |
| 8 per-recording CSVs: ride `new_data` | **left** (~1–2 h, ~14 GB peak disk) | `stream_new_data.py` streams the 17 GB archive from Yandex Disk |
| range summaries | **pre-built**: all 37 jobs of `run_range_matrix.sh` + `run_range_extra.sh`, both versions | [prebuild/range_table.md](prebuild/range_table.md), `prebuild_range.py`; re-run on the release checkout only if the identity check fails |
| perturbation table | **done** | X3 on 1.1.0, PASS, identical to v1.0.0 ([P4 report](../p4_eval_1.1.0_2026-10-16/README.md)) |
| 4 Docker chain summaries | **left** (needs the release image) | `scripts/docker/chain.sh <image> <bag dir> <bag> <label> [play options]` for the 13.10 conditions (its table has five runs: 360° and 120° each with README flags and with the literal default `ros2 bag play`, plus a renamed topic; the card asks for four summaries) |
| `scores.json`, `delta.md` | **left** | a fresh-context agent scores against the 13.10 rubric; S1 stays FAIL; the selected runtime is measured |

## Pre-built range result (16.10)

* **707ea9c reproduces the judge's 13.10 range table** (first STOP / held, metres): A person 218 / 222,
  with dropout 209 / 204, ±0.5 m 218 / 222; 1 m 151 / 163; 0.5 m 135 / 83; 0.3 m and the low box 45 / 49;
  B 52 / 50 / 50 / 41; C 74 / 74 / 75 / 42; D 106 / 106. Probes: crossing at 130 m, receding 96–97 m,
  pole off axis never STOP, cable 60 / 43 m. S at 100 / 150 m: the judge's 83 / 92 are STOP *decisions* while visible;
  matched STOP frames are 82 / 90. Both counts appear in the summaries.
* **1.1.0 changes 2 of 37 jobs, both on recording C:** person first STOP 73.9 → **82.8 m** (STOP frames
  49 → 55, held 81.3 → 91.6 m) and 1 m cube 73.9 → **85.7 m** (49 → 57). These match the H5-era probe
  C-person 82.77 m / 55 STOP. The pole on the axis stays 82 / 177 STOP frames in both, as the handoff's A-axis 82/177.
* Per job: [prebuild/range_table.md](prebuild/range_table.md). Summaries `prebuild/summary_<tag>.json`
  (also in the P4 numeric export as stage `J1-range`). Every job output is in `prebuild/range_raw.tar.xz`
  (SHA-256 in `prebuild/SHA256SUMS`). Each version took ≈ 7.7 min at 2 workers on this container.

These are **pre-release** numbers; the judge score remains v1.0.0's 66/100 until the release J1 is scored.
