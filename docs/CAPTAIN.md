# Captain (P1) — work map and no-conflict backlog

Companion to [`PLAN.md`](PLAN.md) (roles, sprints) and the organizers' spec
([`organizers/technical_specification_case05.txt`](organizers/technical_specification_case05.txt)).
The captain owns *system analysis + ROS 2 / integration*: everything that turns the pipeline
the others build into a thing the jury can `docker build → docker run → ros2 bag play → see`.

State of the repo this map was written against: v0 prototype, one merged PR, 15 synthetic
tests, CI with a `pytest` job, a parameter-sync check and a Docker job that runs the suite
inside the image.

## 1. Ownership map — who edits what

| Path | Owner | Notes for the captain |
|---|---|---|
| `docker/`, `docker-compose.yml`, `scripts/build.sh`, `scripts/run_demo.sh`, `scripts/run_offline.sh`, `scripts/sync_params.sh` | **P1** | free to change |
| `ros2_ws/src/resense_ros/` (node, launch, `package.xml`, `setup.py`, `config/`) | **P1** | free to change; `rviz/resense.rviz` is P2's |
| `README.md`, `docs/ARCHITECTURE.md`, `docs/ALGORITHM.md`, `docs/EVALUATION.md`, `docs/SUBMISSION.md`, `docs/PLAN.md`, `docs/CAPTAIN.md` | **P1** | free to change; README screenshots come from P2; P3 reviews ALGORITHM.md |
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
8. **Align the data path story.** `docker-compose.yml` defaults `RESENSE_DATA` to `./data`,
   README and scripts assume `/data/for_hackathon`. Pick one, document `RESENSE_DATA`, and add a
   headless demo path that needs no X11: detector + player + `ros2 topic echo
   /resense/nearest_distance`. Files: `docker-compose.yml`, `scripts/run_demo.sh`, README.
9. **A dry-run script that asserts a detection.** `scripts/dry_run.sh`: build from scratch, run
   the container, play `doubleT_obstacle` (the only bag with a known obstacle), subscribe to
   `/resense/obstacle_detected` and exit non-zero if it never goes true within the bag length
   or if p95 latency exceeds 100 ms. This is the 28.09 acceptance test (procedure written in
   `docs/SUBMISSION.md`). Needs the dataset, so it runs on a team machine, not in GitHub CI.
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
