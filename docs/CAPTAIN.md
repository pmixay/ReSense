# Captain (P1) — work map and no-conflict backlog

Companion to [`PLAN.md`](PLAN.md) (roles, sprints) and the organizers' spec
([`organizers/technical_specification_case05.txt`](organizers/technical_specification_case05.txt)).
The captain owns *system analysis + ROS 2 / integration*: everything that turns the pipeline
the others build into a thing the jury can `docker build → docker run → ros2 bag play → see`.

State of the repo this map was written against: v0 prototype, one merged PR, 15 synthetic
tests, CI with a `pytest` job, a parameter-sync check and a Docker job that runs the suite
inside the image.

## 0. Status — done and what is left (started 16.09, last updated 24.09)

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

### Done on branch `claude/festive-thompson-f9w2qu` (21.09)

| area | what | where |
|---|---|---|
| organizers | Sprint 0 + sensor questions drafted, ready to send (human captain sends) | `docs/QUESTIONS.md` |
| ROS node | `ego_speed_mps` / `speed_topic` / `odom_topic` → `Detector.process(frame, ego_speed=...)`; static TF `resense_lidar → <input frame_id>` so one RViz / Foxglove layout serves every bag; all parameters as launch arguments; `delay:=` for playback | `detector_node.py`, `launch/`, `package.xml` |
| CI / container | dataset-free ROS smoke test (synthetic bag in the organizers' exact layout played through the node inside the image, checker asserts the result) on every push; found and fixed the empty-wheel install (the node never imported `resense`) and the DDS-discovery frame loss; `web` job (dashboard in headless Chromium); in-image tests with the skip guard | `scripts/make_smoke_bag.py`, `scripts/smoke_test.sh`, `docker/Dockerfile`, `.github/workflows/ci.yml` |
| data | streaming unpacker for the nested archive; all six bags cached at full rate and run at 10 Hz (finding 2 below); six-bag topic table | `scripts/unpack_dataset.py`, `DATASET.md` |
| docs | remote-demo runbook, cover message, architecture (ego speed, TF, verification), submission status | README, `SUBMISSION.md`, `ARCHITECTURE.md` |
| integration | round 1 (synthetic): P2, P3 and P4 branches reviewed by independent reviewers and merged with their fixes; round 2 (real data, 21–22.09): P4 (real labels, set S on real frames, offline given-speed path, `summarize --compare`) and P3 v0.5 (axis from the rails, 1/R curvature, height-reference range, infrastructure signatures, persistence in time) reviewed on the six bags and merged; P2's real-data deliverables (renders, two videos, presentation numbers) done by the captain after P2's agent was cut off by the session limit | this file §0, `EXPERIMENTS.md` |
| results | v0.5 at full rate: five obstacle-free bags 1 001 / 192 → **96 alarm frames / 32 events** (2 287 frames), person of `doubleT_obstacle` 66/71 labelled frames (v0.3 63/71), first alarm frame 7, 0 false events on that bag; 43–55 ms mean / 51–60 ms p95 on the tunnel bags (v0.3 56–71 / 71–76, same machine back to back); ablations of every lever group; raw files `experiments_v0.4_*.json`, `experiments_v0.5_real_fullrate.json`, labels in `labels/` | `EXPERIMENTS.md` §1, §1b, §3 |

### Left for the captain (in order)

1. ~~Form the Sprint 0 + sensor questions~~ — drafted in [`QUESTIONS.md`](QUESTIONS.md)
   (21.09); **sending them and recording the answers is the human captain's action.**
2. **Run `scripts/dry_run.sh` on the i7 stand with the original bags.** Rehearsed on 23.09 in
   the sandbox (a Docker daemon runs there after all; recordings rebuilt from the frame cache;
   EXPERIMENTS.md §3b): the node container plus `ros2 bag play` from another container, both
   topic pairs, two recordings into one node — detections as offline, `roundT_doubleT` PASS
   with `--max-alarm-frames 2`; it found and fixed the best-effort transport bug (v0.6.2
   `input_reliability`). What is left for the stand: the original bags (not rebuilt ones) and
   the i7 timing — at 360° the 4-vCPU sandbox runs at 7–10 fps in steady state; the first seconds of a played bag, lost until v0.6.4, are now worked through (EXPERIMENTS §3b).
3. ~~Launch arguments for the demo~~ — done (`loop:=`, every parameter as a launch argument,
   plus `ego_speed_mps` / `speed_topic` / `odom_topic` / `publish_tf` / `tf_parent_frame`).
4. ~~Data-path alignment and a headless demo path~~ — done, item 8.
5. ~~Dataset-free ROS smoke test in CI~~ — done, item 10 (`scripts/make_smoke_bag.py`,
   `scripts/smoke_test.sh`, CI docker job).
6. Intermediate submission: cover message drafted in `SUBMISSION.md`. **Tagging a release is
   deferred (24.09): the system is still being developed**; no tag exists yet.
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
   `tracking.confirm_hits = 3` — the three hits are 1 s apart at every 10th frame (3 s of
   persistence), 0.5 s apart at every 5th (1.5 s), 0.1 s apart at 10 Hz (0.3 s) — so **every recall and false-alarm number measured on
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
   With the fix, CI run 20 (commit `7eee82b`) is the **first end-to-end run of the ROS node**:
   inside the image, `ros2 launch` started the node on the default command, it auto-selected
   `/lidar_points` (`frame_id hesai_lidar`), broadcast the static TF, processed the 40-frame
   synthetic bag at rate 0.5 with 0 dropped frames and reported the person at 59.9 m in 23
   frames; decode + detect latency on the GitHub runner: mean 63 / p95 65 / max 71 ms;
   `check_dry_run.py` PASS. `ros2 topic echo --field data` output parses as the checker expects.
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
   of 20.09 predicted the direction (a candidate needs `confirm_hits` = 3 *consecutive processed*
   frames, which are N × 0.1 s apart when every N-th frame is used: 3 s of persistence at every
   10th, 1.5 s at every 5th, 0.3 s at 10 Hz) but not the size: **every false-alarm number in
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
4. **The first seconds of a bag are lost to DDS discovery** (the diagnosis of 21.09; corrected on
   24.09, item 19: the player preloads the bag and then bursts). `ros2 bag play` publishes as soon
   as it opens the bag; the node's subscription needs a discovery round trip first. CI run 20
   lost 2 frames, run 21 lost 13 (the whole clear lead-in), the jury's demo would lose the same.
   Every playback path now passes `--delay 3` (smoke test, `dry_run.sh`, `run_headless.sh`, the
   compose player, the launch file's `delay:=`).
5. **v0.5 on real data (21–22.09).** P3's real-data round (its agent was interrupted twice by the
   session limit; the captain committed its draft, measured every number and had the code
   reviewed independently): false alarms on the five obstacle-free bags 1 001 frames / 192
   events → 96 / 32 (`roundT_doubleT` 126 → 0), the person 66/71 with the first alarm two
   frames earlier, per-frame time 25 % lower than v0.3 back to back. The review found and the
   captain fixed: a person on a platform edge demoted by the new wall-face / floating
   signatures (thresholds 2.0 / 1.2 m, +7 alarm frames), the yaw clip nearly binding on
   `roundT_doubleT` (0.06 → 0.09), the tracker's gate widened by the nominal instead of the
   measured frame interval (dropped frames could lose a 17 m/s approach). Documented, not
   changed: an object first tracked as advisory needs six in-gauge hits (0.6 s) before the
   alarm, and the LiDAR-only speed estimator is off by default (it merged frames at 0 m/s on a
   stopped train and added 31 false-alarm frames); accumulation runs with the node's given
   speed only. The single largest remaining source is the platform-end structure at 81–83 m
   while the train stands at the platform (20 of the 32 events).
6. **Bench timing at full rate on real frames**, 4-core sandbox shared with other jobs (the
   i7-9700E has 8 faster cores): `roundT_doubleT` total mean 57 ms, p95 95 ms, max 129 ms
   (track 31 / corridor 16 / cluster 10 ms); `doubleT_obstacle` (347 k points) mean 71 ms,
   p95 114 ms, max 177 ms. p95 is above the 100 ms frame period on this machine; the node
   drops frames rather than queueing, so the dropped-frame counter is the number to watch on
   the bench.

### Findings from the organizers' hand-outs (22.09)

7. **Extended dataset received and read end to end** (`DATASET.md` "Extended dataset"): one
   20-minute bag of 221 split files (90 GB unpacked, 17 GB archive on Yandex Disk), same
   topic / frame id / 120° window as five of the six bags, seven stops, 77 km/h top speed,
   curves to R ≈ 350 m, stations and a switch, recording holes of up to 7 s in the last third.
   Streamed through v0.5 at full rate in the sandbox (no disk for the bag itself): 358 alarm
   frames / 102 events in 11 271 frames — 306 events per hour against ≈ 500 on the six bags —
   with the left gauge edge (contact-rail brackets at 40–100 m) as the largest family and the
   unlocked track model at stations / switches as the second. **No obstacles in it** — the
   Q&A session (22.09) and the organizers' written answer of 23.09 (`organizers/answers.md`): every
   alarm on it is a false alarm. The full-bag replay
   (`ros2 bag play /data/new_data`) is the closest thing to the control run and should be the
   dry-run input once the stand has 90 GB free. `scripts/unpack_dataset.py` now streams the
   archive from the link; `scripts/cache_frames.py` and `resense run` take a single split file.
   **Decision (team lead, 22.09): train-speed data is not technically possible for this case —
   the solution operates without it.** The deliverable is the no-speed path (single-frame
   detection + persistence in time, the v0.5 numbers above); `ego_speed_mps` / `speed_topic` /
   `odom_topic` stay optional inputs and the multi-frame accumulation stays off unless a speed
   is given. The same round closed the tuning question (using the given recordings for
   parameter tuning is acceptable) and the slides question (own slides after the template's
   7–11 are acceptable); the submission / stand logistics are the team's own.
8. **Sensor manual and test-stand software** (`SENSOR.md`, `organizers/test_stand_software.md`):
   the Pandar128E3X manual the organizers handed out is the 2024-07 document, not the
   "rev. 2025-11" cited earlier — every number re-checked; new facts that matter: the
   duplicate points in the bags match the *Last and First* return mode, not the default,
   High Resolution 0.1° applies to channels 26–89 only, and every packet carries an IMU
   (asked whether the driver publishes it). The stand runs driver 580 / CUDA 13 with a 12.9
   toolkit; ReSense is CPU-only, so nothing changes for the image.

### v0.6 (22.09 evening) — the organizers' Q&A answers implemented and measured

9. **Q&A session transcribed** (Whisper, Russian) and summarised with the facts that change the
   code: [`organizers/QA_session.md`](organizers/QA_session.md) (transcript next to it). The
   envelope is 2.1 × 3.0 m, the size criterion 30 × 30 × 10 cm, hanging cables are obstacles,
   the LiDAR mount is not fixed between trains, the hidden check uses rides through other
   tunnels plus synthetic obstacles, `doubleT_obstacle` also holds an object on the rail, and the
   answer the train needs is "can we go / what / how far".
10. **What v0.6 changed** (ALGORITHM.md §2b, §3.3b, §3.3c, §4b): the organizers' envelope with a
    0.35 m advisory zone; a low-object stage at the rail heads; hanging cables no longer demoted
    as columns near the axis; a far-field rule for tall grounded objects to the trusted axis
    range; **mount auto-calibration** (8 orientations with the spin axis vertical, from the rail pair; roll from the rail
    cant, pitch from the bed slope, yaw; launch arguments for a known mount); **production
    guards** (health monitor, `GO / CAUTION / STOP / FAULT` on `/resense/decision`, verified-clear
    distance, `DiagnosticArray`, watchdog, exception guard with detector reset).
11. **Measured on every real frame** (13 759: six bags + the 20-minute ride; EXPERIMENTS §0,
    §1d, v0.6.1): five empty bags 104 alarm frames / 30 events (v0.5 logic 116 / 32), ride 289 / 82
    events (6.3 per km; v0.5 448 / 93), person 58 of 61 envelope frames from frame 11; a health
    warning on 1.4 % of the frames after the calibration fix of v0.6.1 (42 % before it). Long range on the
    moving ride (set F, §2d, v0.6.1): person first confirmed at 150 m median on straight track,
    trolley 146 m, crate 111 m, cable 95 m; with a train speed 177 / 190 / 183 m and fewer ride false
    alarms (274 / 75); in R ≈ 350 m curves 1 of 2 approaches detected, at 74–82 m (sightline). The farthest
    return in all data is 210 m (every recording stops at 209.2–210.0 m), so 300 m is out of the sensor's reach.
12. **Tests**: 152 on 23.09, 198 on 24.09, 199 with v0.6.4 (the node's decision / fault / watchdog / mount-parameter / input-switching
    logic runs against ROS stand-ins in `tests/test_node.py`, so a node bug no longer waits for
    the Docker job). Criteria judgement and the remaining work: [`SCORECARD.md`](SCORECARD.md).
13. **Written answers of the organizers (23.09)** to our questions 1, 2 and 6, recorded
    verbatim in [`organizers/answers.md`](organizers/answers.md) next to the Q&A-session answers
    ([`QUESTIONS.md`](QUESTIONS.md) now holds only the three questions still open): `new_data` has no obstacles; the control data
    may use **either (topic, frame) pair** (`/lidar_points` + `hesai_lidar`,
    `/sensing/lidar/hesai128/pointcloud` + `lidar_livox`), all from the same LiDAR, and will most
    likely be **played from the console** — describe the pipeline if the code reads bags; the
    outputs are ours to choose but must be fully described. Done: the node keeps every
    subscription, switches inputs between recordings and restarts the detector per recording
    (v0.6.1, launch arguments `input_switch_timeout`, `new_input_gap`, `hole_reset_gap`); README
    "How a bag is processed" (the solution does not read bags; `--ipc=host` added to the
    step-by-step `docker run` lines, without which Fast DDS shared memory could swallow the 5–8 MB
    clouds of a player on the same machine; superseded on 23.09: the image now runs DDS over UDP
    only, so `--ipc=host` is harmless and kept only for compatibility).
14. **v0.6.2 (23.09), after the criteria review** (EXPERIMENTS §0; the review reports of 23.09
    are in the git history): the organizers' object lying across the rail is found in **118 of the 126 frames** after
    the person leaves it (v0.6.1: 2) — it straddled the envelope floor and fell between the two
    detection stages, now it is clustered whole; confirmation 0.5 s instead of 0.3 s; without a
    rail lock (stations) the corridor beyond 40 m is advisory. All 13 759 frames: five empty bags
    **81 / 20** alarm frames / events (v0.6.1 104 / 30), ride **164 / 47 = 3.6 per km** (289 / 82),
    person 58 of 61 from frame 11 as before; fewer events in 12 of 13 subsets of the data and more
    in none (`scripts/consistency_check.py`). Slides in the organizers' template:
    [`presentation/ReSense_LCT2026.pptx`](presentation/ReSense_LCT2026.pptx) (built by
    `scripts/build_deck.py`; the captain fills the `<…>` personal data and photos on slides 2–4);
    the main shot from the cab: `scripts/hero_view.py` → `img/hero_person.png`, video
    `video/doubleT_obstacle_cab.mp4`. Set F round 2 (EXPERIMENTS §2d): a person on straight track
    first confirmed at 148 m, held in ≥ 90 % of the frames from 135 m (every 10 m band from 115 m; 167 m with a train speed), curves
    6 of 7 approaches, station stops 6 of 6, 30 cm objects on a rail head 6 of 6 from 42–44 m.
    The organizers' procedure ran in Docker on the real frames (EXPERIMENTS §3b) and found a
    transport bug, fixed (`input_reliability`).
15. **Code health (23.09, after the second review)**: `Detector.process` is one method per stage
    (`_fit_track`, `_corridor`, `_low_stage`, `_speed`, `_accumulate`, `_cluster`, `_confirm`) and
    `find_clusters` delegates to `_low_cluster`, `_corridor_cluster`, `_is_infrastructure`,
    `_advisory_reason`, `_is_retro`; every output was compared before and after on 2 930 real frames
    (the obstacle recording, a given-speed run with accumulation, an estimator run, 1 600 ride frames):
    identical. A `lint` CI job runs ruff (pinned) over the package, the node, the scripts and the tests.
    The jury chain is on screen (`video/docker_chain_rviz.mp4`), which found the RViz config reading
    the played clouds best-effort (fixed). The straddle thresholds' margins were measured (EXPERIMENTS
    §0: false alarms −1…+2 of 67 events, the object 91–127 of 185 frames) and the low-object width
    cap follows the envelope (2.2 m): a person lying across the track on a shallow bed 2 → 6 of 6,
    identical on every real frame.
16. **v0.6.3 (23.09), after the second review** (EXPERIMENTS §0): a reported STOP is held over one
    missed frame (STOP episodes 88 → 66 on the obstacle-free data, events unchanged, the object on
    the rail 124 of 126 frames after the person leaves); the mount calibration measures every 10th
    frame only (10–15 ms per frame less for the first 20 s) and applies a tilt from 0.75° — identical
    on every real frame; false alarms measured with processing starting 0–40 frames late, as a
    played bag does through ROS (`scripts/start_offsets.py`: 14–20 events on the five bags); clean
    timing re-measured (42–64 ms mean, p95 53–78 ms); the dry-run checker ignores the transport's
    start-up hole (`--settle-s`) and takes `--obstacle-in`; a jury quick path heads the README.
17. **Re-measurement on the current code (24.09)** (EXPERIMENTS "Re-measurement", raw
    `experiments_2026-09-24_remeasure.json`): the organizers' data downloaded again and cached
    (13 759 frames); `main` (after `a92625e` changed the detector without data) against v0.6.3:
    **identical output on every real frame**, the start-offset check identical row for row, timing
    unchanged back to back. Set F had never been re-run after v0.6.3's hold over one missed frame:
    round 3 (§2d) keeps every first confirmation (person 148 m, 167 m with a speed) and moves the
    held ranges (a person held from 149 m instead of 135 m). Numbers that disagreed between the docs
    were aligned (distance error ≤ 0.23 m, 7–10 fps at 360° through ROS, 198 tests, `CAUTION` on
    27–68 % of empty-recording frames, 16 of 47 ride events first confirmed beyond 100 m, the
    v0.6.3 timing table in ARCHITECTURE). Release tagging is deferred while development continues.
18. **Independent review of 24.09** (commit `d58567e`; [`SCORECARD.md`](SCORECARD.md), full report
    [`reviews/2026-09-24_review.md`](reviews/2026-09-24_review.md)) replaces all earlier
    evaluations. It reproduced every real-data headline number and measured the opt-in near-bed
    path on all 13 759 frames: 667 ride events with it on against 47 with the defaults.
19. **v0.6.4 (24.09): the lost start of a played bag fixed on the node's side** (EXPERIMENTS §3b).
    Root cause measured with a packet capture: `ros2 bag play` (Humble) preloads min(1000 messages,
    the whole recording) while its clock runs and then sends the overdue first seconds back to
    back; the keep-last-1 input kept the newest of them only. The node now holds 40 frames and
    works through a backlog one frame every 0.3 s of recording (`catchup_step`) from the first frame:
    3 runs each on `doubleT_obstacle` from a uid-1000 player, the largest gap in the first 5 s
    2.07 → 0.40 s, the first STOP 4.02 → 1.59 s of recording time, no scene reset (1–2 per run
    before); `roundT_doubleT` 223 → 241 of 252 frames. What remains is the player's preload itself
    (`NO_INPUT` for 2.6–4 s) and ~0.25 GB more memory at 360°.

### Left for the team (captain tracks, does not do)

| owner | item | why it matters |
|---|---|---|
| P1 | `scripts/dry_run.sh` on the i7 stand with the original bags (rehearsed in the sandbox on 23.09 on rebuilt ones, EXPERIMENTS §3b; the person at 55.9–56.6 m, `--distance 50:62` holds); the i7-9700E timing | spec §4, §8.3 |
| P3 | v0.6 follow-ups: a lining-anchored far height reference (vault drift measurable to ~200 m, EXPERIMENTS §2d); a bed bin must span the bed to extend the fit (an object far ahead lengthens it, §2d); cant-aware roll; the platform-end structure at 82–84 m | `EXPERIMENTS.md` §2d, ALGORITHM §6 |
| P3 | the zone-history fast path (alarm when the last three hits are inside, measured on the five bags), the edge-margin variants, re-classifying the 96 residual alarm frames by cause, the platform-end structure at 81–83 m (20 of 32 events), accumulation on a moving bag with an obstacle (none exists yet), the injector's height reference beyond 80 m (with P4) | `EXPERIMENTS.md` §1b ablations and §5 |
| P3 | from the organizers' synthetic-obstacle recording (P4_AUDIT "Organizer synthetic-obstacle recording"): (a) `elevated` / `floating` should not demote short clusters within 100 m. The experiment `scripts/short_signature_experiment.py` gives +49 STOP frames on the inside test objects for +2 events on the five empty bags; re-run the 20-minute ride before shipping. (b) A hanging object that dips only 0.2–0.4 m into the envelope never becomes a candidate: cluster it with its points above the envelope top. (c) A large object 10–20 m ahead shadows the rails and moves the rail-height fit by ~0.5 m | spec §8.1, §8.2 |
| P4 | done: extended-dataset intake; the injector's bed placement, set F axis anchoring and evaluation accounting corrected; paired set S on 108 original empty-bag frames; the full-rate six-bag R/E check; the paired curve/edge set F. **The organizers' 1,510-frame synthetic-obstacle bag is now labelled exactly** (`labels/cloud_with_fake_obj.json`) and graded per object, and the config sweeps and the signature experiment have been measured against the six original bags. Left: re-run the 20-minute ride for the P3 signature change; keep set O in every regression. Real reflectivity evidence is limited to the original person and rail object | `P4_AUDIT.md`, `DATASET.md` "Synthetic-obstacle recording", `EVALUATION.md` set O |
| P1 | send questions 4–5 of `QUESTIONS.md`: is the envelope in the organizers' check taken from the LiDAR's axis or from the rails (0.24° apart in their bag), and is "2х2 сверху габарита" an obstacle | four of the ten test objects change sides of the envelope edge between the two frames |
| P1 | personal data and photos on slides 2–4 of `presentation/ReSense_LCT2026.pptx` (`PRESENTATION.md`: the captain fills them) | spec §8.8 pitch |
| P2 | the dashboard card for `ego_speed` / `n_accumulated` / alarm events | spec §4 demo |

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
| `resense/track.py`, `gauge.py`, `clustering.py`, `tracking.py`, `accumulate.py`, `egomotion.py`, `tests/test_algorithm.py` | P3 | do not touch |
| `resense/synthetic.py`, `metrics.py`, `io.py`, `cli.py` (`inject`, `eval`, `summarize`), `tests/` (except `test_algorithm.py`), `scripts/cache_frames.py`, `labels/`, `docs/experiments_*.json` | P4 | do not touch |
| `web/` (dashboard, Foxglove layout, label tool, `web/demo/` checks), `ros2_ws/.../rviz/`, `docs/PRESENTATION.md`, `docs/video/`, README screenshots | P2 | do not touch |
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
    `scripts/smoke_test.sh` that plays it through the node and checks that `/resense/status`
    arrives and the clear tunnel is not alarmed. Runs inside the Docker CI job. Files:
    `scripts/make_smoke_bag.py`, `scripts/smoke_test.sh`, `scripts/check_dry_run.py`, `ci.yml` docker job.
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
