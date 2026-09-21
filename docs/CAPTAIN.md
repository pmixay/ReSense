# Captain (P1) — work map and no-conflict backlog

Companion to [`PLAN.md`](PLAN.md) (roles, sprints) and the organizers' spec
([`organizers/technical_specification_case05.txt`](organizers/technical_specification_case05.txt)).
The captain owns *system analysis + ROS 2 / integration*: everything that turns the pipeline
the others build into a thing the jury can `docker build → docker run → ros2 bag play → see`.

State of the repo this map was written against: v0 prototype, one merged PR, 15 synthetic
tests, CI with a `pytest` job, a parameter-sync check and a Docker job that runs the suite
inside the image.

## 0. Status (16.09, end of day 2) — done and what is left

### Done on branch `claude/captain-member-mapping-6zge0b` (PR #2)

| area | what | where |
|---|---|---|
| CI | Docker job builds with `WITH_TOOLS=1`, runs the 15 tests inside the image (no `\|\| true`), checks the ROS package and launch file; `params-in-sync` job | `.github/workflows/ci.yml` |
| demo & acceptance | `scripts/run_headless.sh` (no-X11 demo), `scripts/dry_run.sh` + `scripts/check_dry_run.py` (build → play → assert), `RVIZ=0` on `run_demo.sh`, one data-path rule (`$RESENSE_DATA` → `/data`, default `/data/for_hackathon`), compose `echo` service | `scripts/`, `docker-compose.yml`, README, `SUBMISSION.md` |
| Docker | runtime image with pinned numpy 1.26 / scipy / scikit-learn / pyyaml, package installed non-editable (jammy pip has no PEP 660 hook), `WITH_TOOLS` build arg, canonical `configs/default.yaml` copied over the ROS copy at build time; first real build is green | `docker/Dockerfile`, `scripts/build.sh` |
| parameters | `scripts/sync_params.sh` (copy / `--check`) | `scripts/` |
| ROS node | `/resense/latency_ms`, `/resense/fps`, dropped-frame estimate, periodic latency mean / p95 / max log, `node` object in the status JSON, `stats_period` parameter | `ros2_ws/.../detector_node.py` |
| docs | `ALGORITHM.md` (spec §5 structure), `EVALUATION.md` (data sets, metrics, procedure, targets), `SUBMISSION.md` (checklists, dry run, upload), `SENSOR.md` (Pandar128 identified from the manual and angle file; specs and their consequences), README topic table, node parameters and organizers' documentation index, this map | `docs/`, `README.md` |
| corrections | the sensor is a Pandar128, not an AT128-class unit (DATASET.md, `sensor.py` docstring); 300 m is beyond the instrumented range for ordinary targets (EVALUATION.md) | |

### Left for the captain (in order)

1. ~~Form the Sprint 0 + sensor questions~~ — drafted in [`QUESTIONS.md`](QUESTIONS.md)
   (21.09); **sending them and recording the answers is the human captain's action.**
2. **Run `scripts/dry_run.sh` on a team machine with Docker and the dataset.** The container
   path now runs in CI on a synthetic bag (item 10) and the offline pipeline has run on every
   real frame; the ROS node on a real bag is still unexecuted (no Docker daemon in the sandbox).
3. ~~Launch arguments for the demo~~ — done (`loop:=`, every parameter as a launch argument,
   plus `ego_speed_mps` / `speed_topic` / `odom_topic` / `publish_tf` / `tf_parent_frame`).
4. ~~Data-path alignment and a headless demo path~~ — done, item 8.
5. ~~Dataset-free ROS smoke test in CI~~ — done, item 10 (`scripts/make_smoke_bag.py`,
   `scripts/smoke_test.sh`, CI docker job).
6. Intermediate submission: cover message drafted in `SUBMISSION.md`; tag on the day once P2's
   recording exists and the organizers name the date (question 6).
7. Sprint 2: ~~ego-speed parameter~~ done (item 14), ~~remote-desktop runbook~~ done (README,
   item 15), bench timing measured on the 4-core sandbox (finding 4 above; the i7 run is still
   owed, item 13), extended-dataset intake recipe in `DATASET.md` (item 16, with P4).
8. Sprint 3: keep `ALGORITHM.md` and `SUBMISSION.md` current, clean-machine dry run on 28.09,
   captain slides (P2 drafted them in `PRESENTATION.md`; the captain edits).

### Findings from the first run on real data (20.09)

The dataset was unpacked and the offline pipeline run on `doubleT_obstacle` and `roundT_doubleT`.
Docker and ROS 2 were not available, so the node itself is still unexecuted.

1. **The demo would have shown nothing.** `doubleT_obstacle` publishes
   `/sensing/lidar/hesai128/pointcloud` with `frame_id = lidar_livox`, not `/lidar_points` /
   `hesai_lidar`. The node's default topic, the RViz layout's topic **and** the RViz fixed frame
   were all wrong for the one bag with a real obstacle. Fixed in the node (candidate topic list
   + auto-discovery of PointCloud2 topics) and the launch file; **the RViz layout is P2's and
   still hard-codes both** — `Topic: /lidar_points`, `Fixed Frame: hesai_lidar`.
2. **The azimuth window is not constant across bags.** `doubleT_obstacle` is a 360° recording
   (921 600 slots, ~347 k valid points); `roundT_doubleT` is the 120° window (~190 k). The
   open question in `SENSOR.md` §4 is already answered by the data, and the wrong way: the
   control bag may use either. Latency on the 347 k-point frames is still fine (mean 52 ms).
3. **The v0 numbers reproduce exactly.** `doubleT_obstacle`, every 5th frame: 41 frames, 12
   alarm frames, 39 warning frames, 55.6 → 56.4 m, mean 52 ms — matching `EXPERIMENTS.md`.
4. **The false-alarm numbers do not, and are optimistic.** `EXPERIMENTS.md` reports
   `roundT_doubleT` as "26 frames (every 5th), 1 gauge alarm". 252 frames / 26 = every **10th**.
   Re-run at every 5th: **8 alarm frames, 3 false-alarm events**. Subsampling interacts with
   `tracking.confirm_hits = 3` — at every 10th a candidate must persist a full second to be
   confirmed, at 10 Hz only 0.3 s — so **every recall and false-alarm number measured on
   subsampled frames understates the false-alarm rate the node will show at 10 Hz**. For P3/P4:
   the evaluation has to run at full rate, or state the subsampling next to every number.
5. **FP events vs FP frames, measured.** Those 8 alarm frames are 3 confirmed track ids
   (5, 2 and 1 frames). The headline number in `EVALUATION.md` §2 should be events, as planned.

### Findings from the first full-rate run and the first container run (21.09)

The sandbox of 21.09 had the dataset (downloaded and unpacked with `scripts/unpack_dataset.py`,
every frame of every bag cached as `*.npy`) but no Docker daemon and no ROS 2; the container
path ran for the first time in GitHub CI through the new dataset-free smoke test.

1. **The image never contained an importable `resense`.** Jammy's pip 22.0.2 builds a
   PEP 621 project into an empty `UNKNOWN-0.0.0` wheel, so `pip3 install --no-deps .` in the
   Dockerfile installed nothing; the in-image `pytest` step passed only because its working
   directory was the source tree, and the ROS node would have died at import on the jury's
   machine. Fixed (pip upgraded before the install, the import verified from `/` at build
   time, the CI pytest step runs with `-w /`). This is why the smoke test exists.
2. **At full rate the v0.3 detector alarms on about half of the frames of the empty bags.**
   `resense run --npy` on every cached frame (4-core sandbox, v0.3 parameters):

   | bag | frames | alarm frames | alarm events (track ids) | advisory frames | alarm distances | ms mean / p95 / max |
   |---|---|---|---|---|---|---|
   | `doubleT_obstacle` | 201 | 76 | 3 | 199 | 17–57 m | 80 / 127 / 154 |
   | `doubleT_platform` | 345 | 178 | 29 | 110 | 19–131 m | 79 / 132 / 173 |
   | `roundT_doubleT` | 252 | 126 | 20 | 140 | 9–147 m | 48 / 84 / 138 |
   | `roundT_pressureGate_roundT` | 268 | 106 | 19 | 135 | 3–77 m | 56 / 89 / 138 |
   | `roundT_squareT_pressureGate_squareT` | 545 | 87 | 19 | 396 | 12–133 m | 61 / 101 / 155 |
   | `squareT_platform_squareT_switch` | 877 | 504 | 105 | 680 | 17–148 m | 83 / 131 / 236 |

   `EXPERIMENTS.md` §1 reports 1 alarm frame on `roundT_doubleT` at every 10th frame. Finding 4
   of 20.09 predicted the direction (a candidate needs 3 *consecutive processed* frames, i.e.
   1 s when subsampled by 10, 0.3 s at 10 Hz) but not the size: **every false-alarm number in
   `EXPERIMENTS.md` is measured on subsampled frames and understates the 10 Hz rate by an order
   of magnitude.** This is the first item for P3 with real data (raw runs:
   `/data/results/v0.3/<bag>.jsonl` on the sandbox, reproducible with `resense run --npy`).
   Obvious levers: persistence measured in seconds rather than processed frames, an axis that
   does not jitter frame to frame, and cluster filters checked at 10 Hz.
3. **All six bags' topics are now known** (metadata read from the archive):
   `doubleT_obstacle` alone publishes `/sensing/lidar/hesai128/pointcloud`; the other five
   publish `/lidar_points`. The azimuth window is ±50° in all bags except `doubleT_obstacle`
   (±125°, 347 k points). `frame_id` is verified for two bags only (the caches carry no
   frame id): `hesai_lidar` / `lidar_livox`.
4. **Bench timing at full rate on real frames**, 4-core sandbox shared with other jobs (the
   i7-9700E has 8 faster cores): `roundT_doubleT` total mean 57 ms, p95 95 ms, max 129 ms
   (track 31 / corridor 16 / cluster 10 ms); `doubleT_obstacle` (347 k points) mean 71 ms,
   p95 114 ms, max 177 ms. p95 is above the 100 ms frame period on this machine; the node
   drops frames rather than queueing, so the dropped-frame counter is the number to watch on
   the bench.

### Left for the team (captain tracks, does not do)

| owner | item | why it matters |
|---|---|---|
| P3 | wall / bed curvature fusion at stations and transitions; GOST gauge polygon; ego-motion + 5–10-frame accumulation; reflectivity > 100 as a sign filter (`SENSOR.md` §3.3) | 49 of 67 false-alarm frames are in the platform-and-switch bag; 150–200 m needs accumulation |
| P4 | `tests/test_core.py` skips the whole module without open3d (a local `pytest -q` says "1 skipped" and looks green); per-km / per-event false-alarm rates in `metrics.py`; label tool format; extended-dataset labelling | `EVALUATION.md` §2 depends on it |
| P2 | **RViz layout hard-codes `Topic: /lidar_points` and `Fixed Frame: hesai_lidar`, so the demo bag shows an empty screen** (finding 1); demo video, Foxglove layout, dashboard reading the new `node` stats, slides 7–11 | spec §5 video and §4 demo are pending |

## 1. Ownership map — who edits what

| Path | Owner | Notes for the captain |
|---|---|---|
| `docker/`, `docker-compose.yml`, `scripts/build.sh`, `scripts/run_demo.sh`, `scripts/run_headless.sh`, `scripts/run_offline.sh`, `scripts/sync_params.sh`, `scripts/dry_run.sh`, `scripts/check_dry_run.py` | **P1** | free to change |
| `ros2_ws/src/resense_ros/` (node, launch, `package.xml`, `setup.py`, `config/`) | **P1** | free to change; `rviz/resense.rviz` is P2's |
| `README.md`, `docs/ARCHITECTURE.md`, `docs/ALGORITHM.md`, `docs/EVALUATION.md`, `docs/SUBMISSION.md`, `docs/SENSOR.md`, `docs/PLAN.md`, `docs/CAPTAIN.md` | **P1** | free to change; README screenshots come from P2; P3 reviews ALGORITHM.md |
| `.github/workflows/ci.yml` | P4 (pytest job) / **P1** (docker job) | edit only the docker job, tell P4 in the PR |
| `configs/default.yaml` | P3 (values) / **P1** (structure, ROS install path) | never retune values; keep `resense:` root key |
| `resense/config.py`, `resense/detector.py` | P3 | `FrameResult.to_dict()` is the JSON that P2's dashboard reads: treat as a frozen schema |
| `resense/frame.py`, `resense/pointcloud.py`, `resense/sensor.py` | P1 / P3 shared | decoding is captain's, geometry is P3's; small, rarely conflicts |
| `resense/track.py`, `gauge.py`, `clustering.py`, `tracking.py` | P3 | do not touch |
| `resense/synthetic.py`, `metrics.py`, `io.py`, `cli.py` (`inject`, `eval`), `tests/`, `scripts/cache_frames.py` | P4 | do not touch |
| `web/`, `ros2_ws/.../rviz/`, `docs/PRESENTATION.md`, video, slides | P2 | do not touch |
| `docs/EXPERIMENTS.md`, `docs/DATASET.md`, `docs/RESEARCH.md` | P3 / P4 | captain appends bench-timing sections only |

Rule of thumb: the captain adds **new** topics, launch arguments, scripts and docs, and does not
change the shape of anything the other three consume (`Frame`, `FrameResult`, the config keys,
the CLI output files).

## 2. Interfaces the captain freezes so the others can work in parallel

These are the contracts. Changing any of them is a team decision, not a captain decision.

| Contract | Where it lives | Consumers |
|---|---|---|
| ROS topics and message types (`/resense/obstacle_detected`, `warning`, `nearest_distance`, `detections`, `status`, `markers`, `corridor_points`) | `detector_node.py` docstring | P2 (RViz, Foxglove, web), jury |
| Status JSON (`FrameResult.to_dict()`: `obstacle`, `warning`, `nearest_distance`, `detections[]`, `track`, `timing_ms`) | `resense/detector.py` | P2 dashboard, `resense run --out` |
| `Frame` (xyz in vehicle frame, intensity, ring, stamp) | `resense/frame.py` | P3 (all stages), P4 (`inject`) |
| One parameter file, `configs/default.yaml`, root key `resense:` | `resense/config.py` | P3 tunes, node loads |
| Offline data formats: `*.npz` + `gt.json` from `inject`, JSONL from `run` | `resense/cli.py` | P4 `eval`, P2 label tool |
| Demo procedure: `scripts/build.sh` → `scripts/run_demo.sh <bag>` | `scripts/` | jury, P2 video |

## 3. Captain work streams mapped to the spec

| Stream | Spec section | Deliverable | Sprint |
|---|---|---|---|
| A. Reproducible build and run | 3.3, 7, 8.6 | image builds from scratch with no manual steps; one-command demo; headless mode | 0–1, re-verified 28.09 |
| B. ROS 2 interface | 3.3.5, 4 | topics above + latency/FPS output; parameters and launch arguments documented | 1 |
| C. Evaluation protocol | 8.1–8.3 | written protocol (metrics, bins, hidden-bag procedure) that P3/P4 build to; bench timing on an i7-class machine | 1–2 |
| D. Documentation and submission package | 5, 7.1, 7.2 | README, architecture, algorithm, experiments index; intermediate and final packages; checklist | 1 (intermediate), 3 (final) |
| E. Integration and liaison | 8.5, 8.7 | PR review / merge discipline, main always green; questions to organizers; extended dataset intake | continuous |
| F. Pitch | 4, 8.7 | captain slides (hypotheses, approach, what failed), live or remote-desktop demo | 3 |

## 4. What the captain can do now without interrupting anyone

All items below live in captain-owned files (section 1). Ordered by value; each says why and what
to touch. None changes a frozen contract. Items marked **done** were implemented on this branch.

### Sprint 0 (now)

1. **Make the Docker CI smoke test real.** — **done.** The Dockerfile now copies `tests/`, the
   CI docker job builds with `WITH_TOOLS=1` and runs `pytest` inside the image without `|| true`,
   and also checks that the ROS package and launch file resolve.
2. **Know that a local `pytest -q` can be silently empty.** `tests/test_core.py` does a
   module-level `importorskip("open3d")`, so without open3d the whole file is one skip and the
   run is "green" (seen while writing this map: `1 skipped` until open3d and its pandas / dash
   dependencies were installed, then `15 passed`). The README quick start now says what to
   expect; item 1 guarantees the suite runs in CI. Changing the test file itself is P4's.
3. **Stop the parameter-file drift.** — **done.** The Dockerfile copies `configs/default.yaml`
   over the ROS package copy before `colcon build`; `scripts/sync_params.sh` copies or `--check`s
   the in-repo copy and CI runs the check on every push.
4. **Send the Sprint 0 questions to the organizers** (extended dataset, submission format,
   intermediate deadline, LiDAR model and mount, topic name and frame id of the control bag).
   Record answers in `docs/DATASET.md` via P4.

### Sprint 1 (17–20.09, intermediate submission)

5. **Publish latency and FPS from the node.** — **done.** `/resense/latency_ms` per frame,
   `/resense/fps` every `stats_period` s, a dropped-frame estimate from input stamp gaps, a
   periodic log line with mean / p95 / max latency, and a `node` object in the status JSON.
   Additive only; P2's dashboard is unaffected.
6. **Slim and pin the jury image.** — **done.** The runtime image installs exact numpy 1.26 /
   scipy / scikit-learn / pyyaml versions and the package with `--no-deps`; `WITH_TOOLS=1` adds
   pinned rosbags / matplotlib / open3d / pytest for CI and offline work. Not built in the
   sandbox this was written in (no Docker daemon): the CI docker job is the first real build.
7. **Launch arguments for the demo.** Add `loop:=true` (`ros2 bag play --loop`) for a
   continuous demo, expose `publish_markers`, `publish_corridor_cloud`, `marker_x_max`,
   `output_frame`, `stats_period` as launch arguments. File: `launch/detector.launch.py`, README.
8. **Align the data path story.** — **done.** One rule: the directory holding the bags is
   mounted at `/data`. The scripts take it from the bag path they are given, `docker compose`
   takes it from `$RESENSE_DATA` (now defaulting to `/data/for_hackathon`, with `$RESENSE_BAG`
   choosing the bag), documented in README "Where the data lives". Headless path added:
   `scripts/run_headless.sh` (one container: detector + playback + distance readout, no X11),
   `RVIZ=0 ./scripts/run_demo.sh` delegates to it, and a compose `echo` service does the same
   across three terminals.
9. **A dry-run script that asserts a detection.** — **written, not yet run on data.**
   `scripts/dry_run.sh` builds `--no-cache`, starts the node, **waits for `/resense/status` to be
   advertised before playing** (the launch file's `bag:=` argument races node startup and loses
   the first frames — found while writing this), captures the status stream and hands it to
   `scripts/check_dry_run.py`, which asserts alarm frames, the distance window, p95 latency and
   dropped frames and exits non-zero otherwise. `--expect-clear` turns it into a false-alarm
   check on an empty bag. The checker is verified against synthetic captures; **the container
   path has never been executed — no Docker and no dataset in the sandbox it was written in.**
   Running it on a team machine is the next captain action, and it is also the first end-to-end
   run of the ROS node on a full bag (all timing numbers so far are the offline CLI on
   subsampled cached frames). Needs the dataset, so it stays out of GitHub CI.
10. **A dataset-free ROS smoke test for CI.** A tiny bag (5–10 frames) written with `rosbags`
    from the synthetic tunnel (P4's generator, called, not modified) plus a launch test in
    `ros2_ws/src/resense_ros/test/` that plays it through the node and checks that `/resense/status`
    arrives and the clear tunnel is not alarmed. Runs inside the Docker CI job. Files:
    `scripts/make_smoke_bag.py`, `ros2_ws/.../test/`, `ci.yml` docker job.
11. **Evaluation protocol document.** — **done**, `docs/EVALUATION.md`: data sets, metrics
    (matching the implementation in `metrics.py`), procedure, regression rule and sprint
    targets. P4 extends `metrics.py` for the per-km / per-event rates; P3 optimises against it.
12. **Package the intermediate submission** (spec 7.1). — checklist **done** in
    `docs/SUBMISSION.md`; the tag and the cover message remain for the day of submission.

### Sprint 2 (21–24.09)

13. **Bench timing on an i7-class machine.** Run `resense bench` and the ROS node with `top`
    on the closest available 8-core machine, record CPU per core and memory, append a section to
    `docs/EXPERIMENTS.md` §3 (append only; P3 owns the rest of the file).
14. **Integrate multi-frame accumulation into the node when P3 lands it.** The `Detector` is
    already stateful, so the node should need nothing more than an ego-speed source; prepare the
    parameter (`ego_speed_mps`, or an odometry topic subscription) and a launch argument now so the
    merge is a one-liner. File: `detector_node.py`, `launch/`.
15. **Remote-desktop real-time demo.** Spec 4 rewards a live demo. Verify the Foxglove bridge
    path (`docker compose --profile viz`) from a second machine and write the runbook into README.
16. **Extended-dataset intake.** When the organizers' extra bags arrive, run `resense info` on
    each, confirm topic and frame id match, add rows to `docs/DATASET.md` (P4 file, coordinate),
    and hand the bags to P4 for labelling.

### Sprint 3 and dry run (25–29.09)

17. **`docs/ALGORITHM.md`.** — **done** for v0 (problem, data, processing, decision rule,
    parameters, limitations). P3 reviews; update when accumulation lands.
18. **Submission checklist with owner and status.** — **done**, `docs/SUBMISSION.md`; keep it
    live, run the dry-run procedure on a clean machine on 28.09.
19. **Captain slides** (hypotheses considered, why the environment prior, what failed) and the
    pitch rehearsal.

## 5. What to leave alone unless asked

- Detector parameter values in `configs/default.yaml` and all of `resense/track.py`, `gauge.py`,
  `clustering.py`, `tracking.py`: P3's quality work; any captain change there costs P3 a merge.
- `tests/`, `resense/synthetic.py`, `resense/metrics.py`: P4's; report findings (like item 2) as
  issues, do not fix them in captain PRs.
- The status JSON schema and the existing topic names: P2's dashboard and RViz config bind to
  them. Add topics or fields, never rename or remove.
- `web/`, RViz layout, presentation template slides 7–11: P2's.

## 6. Merge discipline the captain enforces

- `main` builds in Docker and passes `pytest` (with open3d, so the suite actually runs).
- Every PR reviewed by one other member (the rule from PLAN.md; agreed by hand, no tooling).
- Contract changes (section 2) get a one-line note in the PR title, e.g. `[contract] status JSON:
  add detections[].velocity`, and a heads-up to the consumers before merge.
- Captain merges other members' branches; nobody force-pushes `main`.
