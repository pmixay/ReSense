# Captain (P1) — work map and no-conflict backlog

Companion to [`PLAN.md`](PLAN.md) (roles, sprints) and the organizers' spec
([`organizers/technical_specification_case05.txt`](organizers/technical_specification_case05.txt)).
The captain owns *system analysis + ROS 2 / integration*: everything that turns the pipeline
the others build into a thing the jury can `docker build → docker run → ros2 bag play → see`.

State of the repo this map was written against: v0 prototype, one merged PR, 15 synthetic
tests, CI with a `pytest` job and a Docker build job.

## 1. Ownership map — who edits what

| Path | Owner | Notes for the captain |
|---|---|---|
| `docker/`, `docker-compose.yml`, `scripts/build.sh`, `scripts/run_demo.sh`, `scripts/run_offline.sh` | **P1** | free to change |
| `ros2_ws/src/resense_ros/` (node, launch, `package.xml`, `setup.py`, `config/`) | **P1** | free to change; `rviz/resense.rviz` is P2's |
| `README.md`, `docs/ARCHITECTURE.md`, `docs/PLAN.md`, `docs/CAPTAIN.md` | **P1** | free to change; README screenshots come from P2 |
| `.github/workflows/ci.yml` | P4 (pytest job) / **P1** (docker job) | edit only the docker job, tell P4 in the PR |
| `.github/CODEOWNERS`, PR template, branch protection | **P1** | does not exist yet |
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
to touch. None changes a frozen contract.

### Sprint 0 (now)

1. **Make the Docker CI smoke test real.** `docker/Dockerfile` never copies `tests/`, so the
   CI step `docker run resense:ci python3 -m pytest /opt/resense/tests || true` runs on a missing
   directory and is masked by `|| true`. Add `COPY tests ./tests` and drop `|| true`. This is the
   only place the suite runs *with* open3d guaranteed, which matters because of item 2.
   Files: `docker/Dockerfile`, docker job of `.github/workflows/ci.yml`.
2. **Know that a local `pytest -q` can be silently empty.** `tests/test_core.py` does a
   module-level `importorskip("open3d")`, so without open3d the whole file is one skip and the
   run is "green" (seen while writing this map: `1 skipped` until open3d and its pandas / dash
   dependencies were installed, then `15 passed`). Captain action: say it in the README quick
   start ("expect 15 passed, not 1 skipped") and rely on item 1. Changing the test file itself
   is P4's.
3. **Stop the parameter-file drift.** `ros2_ws/src/resense_ros/config/detector.yaml` is a
   byte-identical copy of `configs/default.yaml`. P3 will tune the latter and the node will run
   the former. Fix inside captain territory: in the Dockerfile copy `configs/default.yaml` over
   the ROS copy before `colcon build`, and add a CI `diff -q` so a PR that changes one and not the
   other fails. Files: `docker/Dockerfile`, `ci.yml` docker job, optionally
   `scripts/sync_params.sh`.
4. **CODEOWNERS and a PR template.** Encode the ownership table above in
   `.github/CODEOWNERS` so the "every PR reviewed by another member" rule from PLAN.md is enforced
   by GitHub, and add `.github/pull_request_template.md` with the three checks (pytest green,
   Docker builds, contracts unchanged). Turn on branch protection for `main`.
5. **Send the Sprint 0 questions to the organizers** (extended dataset, submission format,
   intermediate deadline, LiDAR model and mount, topic name and frame id of the control bag).
   Record answers in `docs/DATASET.md` via P4.

### Sprint 1 (17–20.09, intermediate submission)

6. **Publish latency and FPS from the node.** Spec 8.3 scores latency, frame rate and
   real-time stability explicitly. Today timing is only inside the status JSON and a log line
   every 2 s. Add `/resense/latency_ms` (Float32, decode + process + publish per frame), a
   dropped-frame counter (subscription depth is 5 with best-effort QoS, so a slow frame silently
   drops the next ones) and a periodic FPS line. New topics only, so P2 is not affected.
   File: `detector_node.py`.
7. **Slim and pin the jury image.** The image installs `open3d`, `matplotlib`, `rosbags` and
   `pytest` with pip, none of which the node needs; open3d alone is a large wheel and a build
   risk on the bench. Split into a runtime stage and a `tools` target (or a `WITH_TOOLS` build
   arg), pin pip versions, and keep RViz + Foxglove bridge in the runtime image for the demo.
   Files: `docker/Dockerfile`, `scripts/build.sh`.
8. **Launch arguments for the demo.** Add `loop:=true` (`ros2 bag play --loop`) for a
   continuous demo, expose `publish_markers`, `publish_corridor_cloud`, `marker_x_max`,
   `output_frame` as launch arguments, and document every argument in README. File:
   `launch/detector.launch.py`, README.
9. **Align the data path story.** `docker-compose.yml` defaults `RESENSE_DATA` to `./data`,
   README and scripts assume `/data/for_hackathon`. Pick one, document `RESENSE_DATA`, and add a
   headless demo path that needs no X11: detector + player + `ros2 topic echo
   /resense/nearest_distance`. Files: `docker-compose.yml`, `scripts/run_demo.sh`, README.
10. **A dry-run script that asserts a detection.** `scripts/dry_run.sh`: build from scratch, run
    the container, play `doubleT_obstacle` (the only bag with a known obstacle), subscribe to
    `/resense/obstacle_detected` and exit non-zero if it never goes true within the bag length
    or if p95 latency exceeds 100 ms. This is the 28.09 acceptance test and the intermediate
    "minimal demonstration". Needs the dataset, so it runs on a team machine, not in GitHub CI.
11. **A dataset-free ROS smoke test for CI.** A tiny bag (5–10 frames) written with `rosbags`
    from the synthetic tunnel (P4's generator, called, not modified) plus a launch test in
    `ros2_ws/src/resense_ros/test/` that plays it through the node and checks that `/resense/status`
    arrives and the clear tunnel is not alarmed. Runs inside the Docker CI job. Files:
    `scripts/make_smoke_bag.py`, `ros2_ws/.../test/`, `ci.yml` docker job.
12. **Evaluation protocol document.** `docs/EVALUATION.md`: recall per range bin (0–50, 50–100,
    100–150, 150–200, 200–300 m), first-detection distance per object class, FP per km and per hour
    on empty bags grouped by cause, latency p50/p95, FPS, and the procedure for the hidden
    control bag. P4 implements it in `metrics.py`; P3 optimises against it. Writing the document
    touches nobody's code.
13. **Package the intermediate submission** (spec 7.1): Dockerfile, prototype, one-page approach
    description (from README + ARCHITECTURE), mini demo (P2 video or the dry-run log), first
    experiments (EXPERIMENTS.md). Captain assembles; only README wording changes.

### Sprint 2 (21–24.09)

14. **Bench timing on an i7-class machine.** Run `resense bench` and the ROS node with `top`
    on the closest available 8-core machine, record CPU per core and memory, append a section to
    `docs/EXPERIMENTS.md` §3 (append only; P3 owns the rest of the file).
15. **Integrate multi-frame accumulation into the node when P3 lands it.** The `Detector` is
    already stateful, so the node should need nothing more than an ego-speed source; prepare the
    parameter (`ego_speed_mps`, or an odometry topic subscription) and a launch argument now so the
    merge is a one-liner. File: `detector_node.py`, `launch/`.
16. **Remote-desktop real-time demo.** Spec 4 rewards a live demo. Verify the Foxglove bridge
    path (`docker compose --profile viz`) from a second machine and write the runbook into README.
17. **Extended-dataset intake.** When the organizers' extra bags arrive, run `resense info` on
    each, confirm topic and frame id match, add rows to `docs/DATASET.md` (P4 file, coordinate),
    and hand the bags to P4 for labelling.

### Sprint 3 and dry run (25–29.09)

18. **`docs/ALGORITHM.md`.** Spec 5 asks for a separate algorithm description (problem, data,
    processing, decision rule, parameters, limitations). It is currently spread across README,
    ARCHITECTURE and EXPERIMENTS. Captain drafts it as system analyst; P3 reviews.
19. **Submission checklist with owner and status**, `docs/SUBMISSION.md`, copied from PLAN.md and
    kept live; the final tarball / registry image list; from-scratch build on a clean machine.
20. **Captain slides** (hypotheses considered, why the environment prior, what failed) and the
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
- Every PR reviewed by one other member; CODEOWNERS routes it automatically.
- Contract changes (section 2) get a one-line note in the PR title, e.g. `[contract] status JSON:
  add detections[].velocity`, and a heads-up to the consumers before merge.
- Captain merges other members' branches; nobody force-pushes `main`.
