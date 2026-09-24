# Run Evidence

> **Purpose:** index of the raw evidence behind the numbers of
> [`EXPERIMENTS.md`](../EXPERIMENTS.md): the result summaries in `results/`, the logs, captures and
> bench output of each run, and the recordings' original metadata.
> **Audience:** team, jury · **Owner:** P1 (runs, timing), P4 (result summaries) · **Language:** EN
> **Last verified:** 2026-09-24 against `537e220` (every file is the record of its own date) ·
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
