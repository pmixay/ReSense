# Changelog

> **Purpose:** what changed in ReSense, one entry per version or merge, newest first; the numbers
> are those measured when the change landed.
> **Audience:** jury (spec §5 "как менялось качество"), team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-24 against `537e220` · **Status:** current

Versions are the team's labels. The package metadata (`pyproject.toml`) says 0.1.0 up to PR #4 and
0.6.3 from PR #5 (`1210580`). No git tag exists yet; the release plan is in
[`docs/CAPTAIN.md`](docs/CAPTAIN.md) §5. Results: [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md);
counts are "alarm frames / events (/ STOP episodes)" at full rate unless said. "Five bags" = the
five obstacle-free recordings (2 287 frames); "ride" = the 20-minute recording `new_data` (11 271
frames, 13 km, no obstacles).

## Unreleased (after v0.6.4)

The package version stays 0.6.3 (node v0.6.4). Tests: 235 → 266 (+28 native kernels, +3 speed
evaluation helpers) in `tests/`, 11 in `web/demo`.

- **Train-speed evaluation (`396755f`, `93c6eaa`, 24.09):** tooling and measurements, no detector
  change. `scripts/eval_real.py --nominal-stamps` (stamps snapped to the 10 Hz rotation, as the
  node's header clock) and `--speed-ref` (a per-frame reference speed handed in as odometry);
  `scripts/speed_reference.py` (frame-to-frame ICP reference), `speed_accuracy.py`,
  `speed_setf.py`, `speed_static_check.py`, `speed_timing.py`; 3 tests. The LiDAR-only estimator
  is accurate (median error 0.06–0.08 m/s, p90 ≤ 0.20 m/s on 55–96 % of the moving frames,
  +6.6–6.8 ms per frame), but even a perfect speed does not improve the organizers' check: five
  bags 103 / 18 → 111 / 16, no earlier first STOP on set O, 6 → 17 false STOP frames on the box
  outside. `accumulation.estimate_speed` stays `false`; a given speed is still honoured. Raw:
  [`experiments_2026-09-24_train_speed.json`](docs/evidence/results/experiments_2026-09-24_train_speed.json);
  [EXPERIMENTS §9](docs/EXPERIMENTS.md).
- **`cloud_with_fake_obj` corrected (24.09):** the organizers' objects stand still in the tunnel
  and the train drives forward ~2.0 km at 1.4–20 m/s; the docs had said the objects move on their
  own while the train backs up. Fixed in DATASET, P4_AUDIT, EXPERIMENTS §2e, QUESTIONS (Q1 lost
  the sentence built on it) and `scripts/label_fake_objects.py`.
- **C++ kernels (merge `d1a2d0c`, 24.09):** optional `native/resense_native.cpp`, a C ABI loaded
  with ctypes by `resense/_native.py`, built as an optional setuptools extension
  (`RESENSE_NATIVE=0` forces numpy): per-bin percentiles, the full-cloud passes of the track and
  corridor stages, the health visibility. Detector time −38…−57 % (`roundT_doubleT`
  62.4 → 33.5 ms, `doubleT_obstacle` 81.3 → 34.6 ms, p95 at 360° 107 → 51 ms; sandbox under load),
  0 differing frames of 3 998 real frames with numpy 1.26 and 2.4; 28 tests. DBSCAN, the mount
  rotation and the health azimuth histogram are not ported. The Docker build with the kernels is
  proven by CI run 36058665640 (`d1a2d0c`: in-image tests and both ROS smoke tests green).
  [ARCHITECTURE "Native kernels"](docs/ARCHITECTURE.md).
- **`7df1796` (merged `7415495`, 24.09): near-bed gate fix, `main` green again once this branch
  is merged.** `537e220` made the opt-in near-bed path miss the synthetic 30 × 30 × 10 cm bed box
  at 12–28 m (3 failing tests in `tests/test_envelope.py`): `near_min_points` 10 → 5,
  `near_min_length` 0.18 → 0.0, the other gates kept, the per-bin loop vectorised with identical
  output. Five bags with the path on: 459 / 107 / 72 (`4b5786b` gates 1 035 / 145 / 42, `537e220`
  141 / 28 / 33); defaults unchanged.
  [EXPERIMENTS §1e](docs/EXPERIMENTS.md).
- **`194b3e7` (24.09): criteria judgement and documentation revision.** New
  [`docs/SCORECARD.md`](docs/SCORECARD.md) (two independent judges, 60 / 100, judged at
  `4b5786b`); one format for every team-written document (header block, RU summary, dated
  numbers), [`docs/README.md`](docs/README.md) index, this changelog, `docs/archive/`,
  `docs/evidence/results/`; the separate review files removed (superseded by SCORECARD). Later on
  24.09: the train-speed and GPU studies (EXPERIMENTS §9,
  [ARCHITECTURE "GPU: evaluated, not used"](docs/ARCHITECTURE.md)).
- **`537e220` (24.09, P3):** the opt-in central near-bed path gets stricter gates
  (`lowobj.near_min_excess` 0.05, `near_max_width`, `near_min_length`, `near_min_height`,
  `near_min_bed_lateral_bins`, `near_min_points` 10). `lowobj.near_enabled` stays `false`; the new
  shipped key `lowobj.min_length` defaults to 0, so the default path is unchanged. It turned
  `main` red (the bed box, fixed by `7df1796` above).
- **`4b5786b` (PR #9, 24.09, P4):** evaluation, not detector: set S objects placed on the local bed
  (22 of 67 visible hits against 29 of 68 with the old height), tracker reset per injected
  sequence, event identity `(seq, track id)`, per-sequence time and distance, one-to-one matching,
  `--reflectivity`, separate random streams; set F `--placement-mode anchored` and
  `scripts/compare_setf.py` (straight track: person 154 m anchored against 150 m legacy); the
  organizers' `cloud_with_fake_obj` labelled exactly (`labels/cloud_with_fake_obj.json`) and graded
  per object (`scripts/score_fake_objects.py`: 2 × 2 m box from 98 m, plank from 82 m, 0.3 m cubes
  from 34–43 m); tests 199 → 235. Record: [`docs/P4_AUDIT.md`](docs/P4_AUDIT.md).
- **`41b7ae7` (24.09):** the organizers' experts' answers on the LiDAR mount and switches
  ([`docs/organizers/mount_and_switch_qa.md`](docs/organizers/mount_and_switch_qa.md)).

## v0.6.4 — 24.09 (`de98266`, PR #10)

- Node: the input holds 40 frames (`input_queue_depth`) and works through a backlog one frame every
  `catchup_step` = 0.3 s of recording, from the recording's first frame. Through ROS in Docker the
  first STOP on `doubleT_obstacle` comes at 1.59 s of recording time instead of 4.02 s, the largest
  gap in the first 5 s is 0.40 s instead of 2.07 s, no scene reset (1–2 per run before);
  `roundT_doubleT` 241 of 252 frames processed (223 before); ~0.25 GB more memory at 360°
  ([EXPERIMENTS §3b](docs/EXPERIMENTS.md); raw captures not committed).
- Every number re-measured on the current code: per-frame output identical to v0.6.3 on all
  13 759 real frames; set F round 3 on the moving ride.

## 24.09 (`a92625e`, direct push, P3)

- Node: `FAULT` publishes a complete snapshot (no obstacle, distance −1, no detections, markers
  cleared, health `error`), so no stale STOP stays latched.
- Two opt-in stages, both off: the central near-bed path (`lowobj.near_enabled`) and the
  station-wall axis check (`track.rails_far_check_enabled`). Output identical to v0.6.3 on all 13
  759 frames (re-measured in `de98266`).
- `scripts/far_range_eval.py --placement-mode independent`; `scripts/require_docker.sh`: the Docker
  scripts exit 3 without a daemon; `smoke_test.sh` runs only inside the image.

## Dashboard — 23–24.09 (PRs #6–#8, P2)

- `web/index.html`: Russian UI in the Moscow Transport style, flat cards, Montserrat bundled in
  `web/assets/fonts/`, cab view, built-in 60-frame demo, run-summary card, «Отчёт» report download,
  drag-and-drop replay; screenshots in [`docs/images/`](docs/images/README.md); 11 web tests.
- CI repair `36ed07c`: `lowobj.near_min_width` 0.25 → 0.24, web-test distance window 36–72 m.

## v0.6.3 — 23.09 (measured on `c1c2b6a`, merged in PR #5 as `1210580`)

- A reported obstacle is held over one missed frame (`tracking.hold_misses` 1): STOP episodes on
  the obstacle-free data 88 → 66, events unchanged.
- Mount calibration measures every 10th frame only and applies a tilt from 0.75° (was 0.5°).
- Low-object width cap 1.6 → 2.2 m (a person lying across the track is kept).
- Also in PR #5: `Detector.process` split into one method per stage (identical output on 2 930
  frames); CI `lint` job (ruff); the RViz layout subscribes the clouds reliable;
  `scripts/start_offsets.py`; dry-run checker `--settle-s`, `--obstacle-in`.
- Five bags 107 / 20 / 27; ride 204 / 47 / 39; person 58 of 61 frames from frame 11; object on the
  rail 124 of the 126 frames after the person leaves (127 of 185 by its own detection); timing
  42–64 ms mean, p95 53–78 ms (4-vCPU dev VM, 23.09).

## v0.6.2 — 23.09 (PR #5)

- Objects straddling the envelope floor are clustered whole (≥ 0.35 m across, ≤ 0.8 m along):
  the organizers' object on the rail 2 → 121 of 185 frames (118 of 126 after the person leaves).
- Confirmation 0.5 s instead of 0.3 s (`tracking.confirm_time_s`).
- Without a rail pair in the near range, clusters beyond 40 m are advisory (`gauge.no_rail_range`).
- Node: `input_reliability: auto` (reliable subscription); the image runs Fast DDS over UDP only;
  `FAULT` / `NO_INPUT` before the first frame; cloud decoding 40 → 9 ms.
- Five bags 81 / 20; ride 164 / 47 (3.6 per km).

## v0.6.1 — 22–23.09 (PR #5)

- Mount tilt from the median of 20 observations instead of the first 5 frames: health warnings on
  42 % → 1.4 % of the frames.
- Node (after the organizers' written answers of 23.09): either topic / frame pair, input switching
  between recordings, detector restart per recording (`input_switch_timeout`, `new_input_gap`,
  `hole_reset_gap`).
- Five bags 104 / 30; ride 289 / 82 (6.3 per km); person 58 of 61 frames from frame 11.

## v0.6 — 22.09 (PR #5)

- The organizers' Q&A answers: envelope 2.1 × 3.0 m from 0.12 m above the rail head with a 0.35 m
  advisory zone; low-object stage at the rail heads (`resense/lowobj.py`); hanging cables near the
  axis no longer demoted; far-field rule for tall grounded objects; mount auto-calibration
  (`resense/calibration.py`); health monitor, `GO / CAUTION / STOP / FAULT` on `/resense/decision`,
  verified-clear distance, `DiagnosticArray`, watchdog.
- Five bags 83 / 25; ride 258 / 74.

## v0.5 — 21–22.09 (PR #4, merged as `0267281`)

- Track axis yaw from the rails, curvature 1/R from the walls, rate limits and side-agreement caps;
  height reference trusted 20 m beyond the bed fit or as verified; five infrastructure signatures
  (column, elevated, floating, edge, wall face); persistence in seconds; the LiDAR-only speed
  estimator off by default.
- Five bags 1 001 / 192 (v0.3) → 96 / 32; person 66 of 71 labelled frames, first alarm frame 7.

## v0.4 — 21.09 (PR #4, branch commit `f4e311f`)

- Ego-speed estimate and 5-frame accumulation beyond 40 m, verified bed extrapolation,
  retro-reflector rule, lateral smear guard. Five bags 1 016 / 187.

## 16–21.09 (PRs #2–#3, `cd50f42`, `f2c57e5`) — no detector change

- Node latency / FPS topics and status, parameter sync check, Docker CI job, dry-run script and
  checker, headless demo, launch arguments, one data-path rule.

## v0.0–v0.3 — 15.09 (PR #1, `f64f881`)

- Day 1 on subsampled frames (231 frames of the five bags): v0.0 box corridor and raw DBSCAN, 149
  alarm frames → v0.1 rail self-calibration, voxelised range-normalised DBSCAN, 92 → v0.2
  wall-based yaw and curvature, 76 → v0.3 nearer-boundary rule, 1.4 m gauge, hardware / linear /
  wall filters, 67. At full rate (21.09) v0.3 gives 1 001 / 192.
