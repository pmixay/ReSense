# Architecture

*На русском: [ARCHITECTURE.ru.md](ARCHITECTURE.ru.md).*

> **Purpose:** components, data flow, the ROS node, timing, delivery and CI of ReSense (spec §5
> "Архитектура"). The algorithm itself: [`ALGORITHM.md`](ALGORITHM.md).
> **Audience:** jury, team · **Owner:** P1 · **Language:** EN, summary RU
> **Last verified:** 2026-09-29: the node against `detector_node.py`, `fastcloud.py` and the launch
> file (node change of 29.09, sealed 27.09 detector), timing against the judgement and the VM run
> of 28.09 and the start-up A/B of 29.09, CI against `.github/workflows/` · **Status:** current

**Кратко.** ROS 2-нода `resense_ros` принимает `PointCloud2` от `ros2 bag play` (любая из двух пар
топик / frame id или любой найденный топик), читает облако прямо из сериализованных байтов и
передаёт кадр библиотеке `resense` (numpy / scipy, необязательные ядра на C++, без ROS): модель
пути, габарит 2,1 × 3,0 м, кластеризация, подтверждение по времени. Нода проверяет свежесть входа
и публикует решение GO / CAUTION / STOP / FAULT, расстояние, оценку свободной дистанции, состояние и
JSON-статус. Цепочка жюри на 4 ядрах: 360° — p95 от публикации облака до результата 81–94 мс (кадр
100 мс), 120° — 49–78 мс, до одного ядра CPU, без видеокарты. Образ — архив для `docker load`.

```
ros2 bag play ── PointCloud2, 10 Hz: /lidar_points | /sensing/lidar/hesai128/pointcloud | any found ──┐
                                                                                                      ▼
resense_ros/detector_node (Docker, --net=host)                                    detector_node.py
   input: topic discovery, one input at a time, a new recording → a fresh detector
   queue of 40 frames; start-up burst worked through at 5 Hz, later backlogs 0.3 s apart
   decode from the serialized bytes (fastcloud.py, bit-identical to resense.pointcloud)
   freshness check of every result; watchdog on a silent input
        │ Frame (xyz float32 in the vehicle frame, intensity, ring, stamp)
        ▼
resense.Detector.process(frame, ego_speed=None)            module            ALGORITHM
   1.  sensor → vehicle frame, mount auto-calibration      calibration.py    §2, §2b
   2.  track model: bed, rails 1.59 m apart, axis, curvature from the walls
                                                           track.py          §3.1
   3.  envelope 2.1 × 3.0 m swept along the axis (+0.35 m advisory band);
       union with the sensor-axis envelope within 60 m     gauge.py          §3.2, §3.6
   3b. objects on the rails / across the envelope floor    lowobj.py         §3.3b
   3c. multi-frame accumulation (only with a given speed)  accumulate.py     §3.4
   4.  voxels + range-adaptive DBSCAN, infrastructure filters and signatures,
       thin hanging objects                                clustering.py     §3.3
   5.  tracking, 0.5 s confirmation, learned opinion       tracking.py, opinion.py   §3.5, §3.6
   6.  clear-distance caps, health                         evidence.py, health.py    §4b
        │ FrameResult
        ▼
/resense/decision (GO|CAUTION|STOP|FAULT)  /resense/obstacle_detected  /resense/warning
/resense/nearest_distance  /resense/clear_distance  /resense/health (DiagnosticArray)
/resense/status (JSON)  /resense/detections (Detection3DArray)  /resense/latency_ms  /resense/fps
/resense/markers  /resense/corridor_points (built only while subscribed)  /tf_static
        │
        ▼
train controller (decision, clear_distance, status) · RViz2 · Foxglove (port 8765) · web dashboard
```

## Packages and directories

| path | purpose |
|---|---|
| `resense/` | core library, no ROS dependency: decoding, calibration, track model, gauge, low objects, clustering, tracking, learned opinion (`models/`), health, CLI (`resense run / bench / inject / eval`) |
| `ros2_ws/src/resense_ros/` | ROS 2 Humble `ament_python` package: node, fast decode, launch file, parameter copy, RViz config |
| `native/`, `setup.py` | optional C++ kernels, bit-identical to the numpy code they replace ("Native kernels") |
| `configs/default.yaml` | every detector parameter; the ROS package's copy is kept identical (`scripts/sync_params.sh --check` in CI) |
| `docker/`, `docker-compose.yml`, `scripts/` | image, DDS profiles, entrypoint; build, run, dry run, export / load of the image archive, release |
| `tests/` | pytest on a synthetic ray-cast tunnel (no dataset needed) |
| `web/` | dashboard: replays a `results.jsonl` or shows the live node through rosbridge; not in the image, needs no internet |
| `docs/`, `gitbook/` | documents ([`docs/README.md`](README.md)); the Russian user guide, synced to https://resense.gitbook.io/resense-docs/ |

The detector (the `resense/` sources, the configuration and the build files) is sealed since 27.09
([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)); `scripts/detector_freeze.py verify` checks the seal.

## Data flow and formats

* **Input:** `sensor_msgs/PointCloud2`, fields `x y z intensity ring timestamp`, dual-return layout
  with empty `(0,0,0)` slots ([`DATASET.md`](DATASET.md)), played by `ros2 bag play`; nothing in the
  solution reads bag files (the offline CLI does, as a development tool).
* **Internal `Frame`:** `xyz (N,3) float32` in the vehicle frame, `intensity`, `ring`, `stamp`.
* **Output `FrameResult`** (JSON on `/resense/status` and per line of `resense run --out`):
  `obstacle`, `warning`, `nearest_distance`, `clear_distance`, `detections[]` (id, zone, kind,
  reason, distance, lateral offset, centre, size, points, confidence, age), `track` (bed, axis,
  rail offset, trusted ranges), `health` (level, `decision_level`, messages, monitored range),
  `mount`, the ego speed and its source, `timing_ms`. The node adds a `node` object (`latency_ms`,
  `decode_ms`, `detect_ms`, `fps`, `frames`, `dropped_frames`, `catchup`, `catchup_skipped`,
  `input_topic`, `recording`, `cpu_cores`, `rss_peak_mb`, …), a `freshness` object and
  `snapshot_kind` (frame result, or watchdog / error snapshot).
* **Transport:** Fast DDS over UDP only (`docker/fastdds_udp.xml`, so that a player run by any user
  reaches the root node; `--net=host`), 32 MiB receive buffers. The kernel silently caps them at
  `net.core.rmem_max` (212992 on stock Ubuntu): a stock Fast DDS player still delivered every 24 MB
  360° cloud, a CycloneDDS player 0–1 of 201 (all at 32 MiB), so the jury commands start with
  `sudo sysctl -w net.core.rmem_max=33554432` and the node warns below 32 MiB. Opt-in shared memory
  (`-e RESENSE_DDS=shm --ipc=host`, `docker/dds_transport.sh`) hands the clouds over `/dev/shm` to
  players that support it; the others are served over UDP.
* **Offline tools:** `resense run --bag` (per-frame JSON, renders), `resense bench` (stage timing),
  `resense inject` / `eval` (synthetic objects on real frames). `scripts/make_smoke_bag.py` writes a
  synthetic bag in the organizers' layout; `scripts/check_dry_run.py` checks a captured status
  stream against the bag (decisions, distance, processed and dropped frames, e2e latency over
  current and over all results, playback pace).

## The node

`ros2_ws/src/resense_ros/resense_ros/detector_node.py` on one single-threaded executor; every node
parameter is also a launch argument of `detector.launch.py`.

* **Inputs and recordings.** `input_topic` lists both organizer topics; `auto_discover` also takes
  any other `PointCloud2` topic found on the graph. All subscriptions stay open, one is processed;
  after `input_switch_timeout` = 1 s of silence another is taken. A **new recording** (another topic
  or `frame_id`, stamps jumping back or forward by more than `new_input_gap` = 30 s) gets a fresh
  detector, scene and mount calibration; a forward gap above `hole_reset_gap` = 1 s resets the scene
  only, so bags can be played one after another into one node. `input_reliability: auto` is reliable
  for `ros2 bag play` (a best-effort reader lost 196 of 201 360° clouds), best-effort for a
  sensor-data driver.
* **Decode.** With `raw_input` (default) the clouds arrive as serialized bytes and `fastcloud.py`
  parses them (0.1 ms instead of rclpy's 12.5 ms median conversion of a 24 MB cloud).
  `fastcloud.decode` reads x / y / z with one 12-byte-per-point copy and one index gather: the same
  arrays byte for byte as `resense.pointcloud.pointcloud2_to_arrays` on all 453 frames of both
  original recordings, 20.3 → 16.6 ms median at 360°, 7.4 → 4.8 ms at 120°. Other layouts use the
  reference decode.
* **Backlog and catch-up.** Humble's `ros2 bag play` reads ahead while its clock runs, then sends the
  overdue first frames back to back. The queue holds `input_queue_depth` = 40 frames; a frame waiting
  alone is processed at once. A recording's **first backlog** (the start-up burst) is worked through
  **`catchup_startup_step` = 0.2 s** of recording apart — every other 10 Hz frame, the 5 Hz input the
  detector is validated on — short backlogs included, within `catchup_startup_max_lag` = 20 s (closed
  when that catch-up drains, or after 1 s without one). Later backlogs up to `catchup_step` = 0.3 s
  are processed in full, longer ones 0.3 s of recording apart, none more than `catchup_max_lag` = 5 s
  behind the newest; the chain never has a gap that resets the scene. `catchup_startup_step: 0`
  processes every start-up frame; `catchup_step: 0` only ever the newest.
* **Warm-up and shutdown.** With `warmup` (default) the node runs the decode and a throwaway
  detector on three synthetic frames before logging "listening" (~0.7 s), so the first real frame
  costs ~31 + 42 ms decode + detect instead of 49 + 72 ms. Ctrl+C exits cleanly
  (`rclpy.try_shutdown()`).
* **Publishing.** Decision topics go out first; markers and the corridor cloud are built only while
  subscribed. A static identity TF `resense_lidar → <frame_id>` serves one RViz / Foxglove layout
  for both organizer frame ids. BLAS / OpenMP threads default to 1.
* **Ego speed and mount.** `ego_speed_mps` (if ≥ 0), else `speed_topic` / `odom_topic` younger than
  `speed_timeout` = 1 s, else none (single-frame). `sensor_forward/left/up`, `mount_*_deg` and
  `auto_calibrate` set the mount ([`ALGORITHM.md`](ALGORITHM.md) §2b).

## Freshness contract

Whether a result may be acted on ([registered contract](evidence/results/quality_freshness_2026-09-26_protocol.json)):

* `freshness_mode` **`live`** (the node's default) compares the acquisition stamp with system UTC;
  **`replay`** ages the input from its DDS publication by the player, because recorded stamps are
  the sensor's clock. **The image's default command passes `freshness_mode:=replay`**; a live LiDAR
  passes `live`. An executor adapter (`SourceInfoExecutor`) keeps the publication metadata.
* Source age, queue residence and recording lag must be ≤ `max_result_age` = 0.5 s, future skew ≤
  `future_tolerance` = 0.05 s; a first, resumed or jumped epoch needs progression before `GO`.
  Invalid or stale clocks give `FAULT`, a current result made during a catch-up `CAUTION`; an
  outstanding `STOP` is held until a fresh valid non-STOP result. While the input is invalid
  `clear_distance` is 0; the status `freshness` object gives the ages, the reason and `go_allowed`.
* The watchdog gives `FAULT` / health `STALE` after `stale_timeout` = 0.5 s without a frame and
  `FAULT` / `NO_INPUT` if nothing arrived `startup_grace` = 2 s after start; it shares the executor
  and cannot run during a blocked callback. An exception publishes `FAULT`; after
  `max_consecutive_errors` = 5 in a row the detector is reset.
* A consumer must expire timestamped status on its own synchronized clock: `/resense/decision`
  alone cannot prove current validity. The dashboard does so and keeps `STOP` through invalid input.

Health (`/resense/health`) and the decision rule: [`ALGORITHM.md`](ALGORITHM.md) §4b.

## Why this design

* **Environment prior, no map** (spec §8.4): anything inside the train's envelope that is not rails,
  bed or known infrastructure is a hazard; bed, rails, axis and mount are re-estimated from the data,
  because the check includes a ride beyond the given recordings. No labelled obstacles are needed.
* **Curvature from parallel references:** rails are seen to ~30–40 m, walls and column rows to
  150–200 m; where no boundary is observed the corridor is not trusted and only advisory.
* **Persistence before alarm:** 0.5 s of confirmation (11 m at 80 km/h), nothing extra for an
  object tracked while it approaches; processing is < 15 % of the time to an alarm, so the CPU
  suffices ("GPU: evaluated, not used").

## Real-time budget

The frame period is 100 ms. Jury chain (`docker run` default command → `ros2 bag play --delay 3
--read-ahead-queue-size 10` as uid 1000 → `/resense/*`), image of `464f5bc` (28.09); e2e = the
player publishes a cloud → the result with its stamp ([`SCORECARD.md`](SCORECARD.md),
[`evidence/vm_2026-09-28/`](evidence/vm_2026-09-28/summary.md)):

| | 360° `doubleT_obstacle` (24 MB clouds) | 120° `roundT_doubleT` |
|---|---|---|
| e2e p95, current results | 81–82 ms warm, 88–96 ms cold (team VM, 4 cores); 85–94 ms warm, 87–172 ms cold (4-vCPU sandbox) | 49–78 ms (sandbox) |
| node decode + detect p95 | 63–72 ms (VM); 79–98 ms (sandbox) | 56–75 ms (sandbox) |
| CPU, resident memory (sandbox) | 0.8–1.0 core, 430–740 MB | 0.5–0.8 core, 130–250 MB |
| decode + detect p95 on the numpy fallback (`RESENSE_NATIVE=0`) | 103 ms (VM): not real time | 71 ms (VM) |

**Start-up**, node of 29.09 against the image of `464f5bc`, alternated on one 4-vCPU sandbox
([`evidence/node_startup_2026-09-29/`](evidence/node_startup_2026-09-29/README.md)):

| 360° `doubleT_obstacle` | e2e median, first 3 s | e2e p95, all results | first STOP after the first cloud |
|---|---|---|---|
| bag in page cache | 312–325 → **38–105 ms** | 410–447 → **212–344 ms** | 0.90–0.99 → 0.79–0.98 s |
| page cache dropped | 829–1029 → **120–300 ms** | 864–1084 → **333–599 ms** | 1.16–1.35 → 0.81–1.16 s |

The 120° clear bag's first-3 s p95 fell from 295–340 to 66–123 ms; the decisions and the
steady-state cost are unchanged. **The player and the disk matter:** with Humble's default
read-ahead (no `--read-ahead-queue-size 10`) the player sends the overdue recording in a burst and
every result is stale (57–135 of 201 360° frames processed, queue lag median 11 s, RSS up to 4 GB;
145 of 201 with the 29.09 node); 360° playback reads ~225 MB/s, and on the VM's 79 MB/s network
disk a 1.4 s stall failed the 120° dry run until the bags were pre-read. The organizers' 8-core
i7-9700E was not available for a measurement ([`organizers/answers.md`](organizers/answers.md) §6).

## Native kernels (optional, C++)

`native/resense_native.cpp`, a plain C ABI loaded with ctypes (`resense/_native.py`), does in one
pass each what the numpy code does in several full-cloud masks, gathers and `np.lexsort`s: per-bin
percentiles (`rs_bin_percentile`), bed / axis / corridor coordinates, the selection prologues of
the bed, rail, wall and verification fits, the corridor masks (`rs_select`) and the visibility.

* **Same output, bit for bit:** the same IEEE operations in the same order (no FMA contraction,
  fast-math or `-march=native`), float32 comparisons where numpy makes them; anything unusual takes
  the numpy code, which stays as the fallback. Checked by `tests/test_native.py` and on all 3 998
  cached real frames (identical results and `scripts/output_fingerprint.py`).
* **Faster:** detector stages 24.6 against 55.9 ms mean at 360°, 22.5 against 43.6 ms at 120° (team
  VM, 28.09, [`evidence/bench_2026-09-28/`](evidence/bench_2026-09-28/summary.txt)).
* **DBSCAN on cKDTree** (`resense.clustering.dbscan_labels`) reproduces scikit-learn's labels
  exactly (identical on all 9 240 real calls and on random sets with ties, `tests/test_cpu_savings.py`).
* **Build and switch:** `pip install .` compiles them as an optional extension (without a compiler
  the install succeeds on numpy); the image builds them and the node logs the path at start;
  `RESENSE_NATIVE=0` forces numpy. Not ported on purpose: the mount rotation (BLAS rounding) and the
  health monitor's `arctan2` histogram.

## GPU: evaluated, not used

The stand has an RTX 4070 Ti SUPER ([`organizers/test_stand_software.md`](organizers/test_stand_software.md));
the spec (§3.1) allows the GPU only if the algorithm needs it. A study of 24.09 (estimates from the
measured CPU stages; no GPU in the sandbox or CI): a frame is ~1 160 small array operations, many
feeding Python `if`s, so a CuPy port is dispatch-bound and would save ≤ 30–45 ms per 360° frame
against numpy, 5–15 ms against the native kernels; cuML DBSCAN is slower than the CPU on our
100–1 000-voxel calls. A container that requests the GPU does not start without `nvidia-container-toolkit` (not in
the organizers' package list), the image would grow by 0.3–6 GB, and CI could not test the path.

## Deployment without internet

The test machine has no internet ([`organizers/answers.md`](organizers/answers.md) §7). Only
`docker build` needs the network (base image, ROS / Ubuntu packages, pinned PyPI wheels); at run time
the node, launch file, compose services, RViz and foxglove_bridge use only DDS on the host's
interfaces, and the dashboard's fonts and roslib are bundled.

* **Image:** `docker/Dockerfile` on `ros:humble-ros-base-jammy`, pinned numpy / scipy /
  scikit-learn, kernels compiled at build time; default command `ros2 launch resense_ros
  detector.launch.py freshness_mode:=replay`, run with `--net=host`. A clean build takes 79 s with
  the base image cached (534 s with `--no-cache` on the team VM); `WITH_TOOLS=1` adds the dev tools.
* **Archive:** `scripts/export_image.sh` builds the runtime image from `git archive HEAD` and writes
  `dist/resense-image-<version>.tar.gz` with its `.sha256`; `scripts/load_image.sh` checks the sum,
  loads it and runs it with `--network none` (475 947 817 bytes on the team VM, PASS).
* **Where it comes from:** the image archive is published as the assets of the GitHub release
  `v1.0.0` by `.github/workflows/release.yml` when the tag is pushed; until then it is the CI
  artifact `resense-image-<version>-<short commit>` of a `main` run (Actions → Artifacts, GitHub
  login, kept 30 days) or `scripts/export_image.sh` on any machine with Docker.
* **Offline `docker build`** (best effort): after `docker load`, `chmod -R u+rwX,go+rX,go-w .` in the
  same commit's tree and `docker build --cache-from resense:<version> -t resense -f
  docker/Dockerfile .` takes every step from the archive's inline cache (BuildKit, classic image
  store). CI proves it with Docker Hub blocked; `docker load` stays the documented path.

## CI and release

`.github/workflows/ci.yml` runs on every push, 4 jobs in 2 stages: **`checks`** (ruff, the ROS
parameter copy, `scripts/detector_freeze.py verify`) and then in parallel **`pytest`** (the suite
with `RESENSE_REQUIRE_SYNTHETIC=1`, so a skipped synthetic test fails, and the dashboard in headless
Chromium), **`docker`** (the suite in the `WITH_TOOLS=1` image; the node reached every way the jury
can — synthetic bags with no network, node and player in separate containers, the one-command
wrapper, stock Fast DDS as uid 1000, shared memory, a remote Foxglove viewer — and a cold-disk start
with both original bags) and **`offline-build`** (the release archive made, every image and the
build cache removed, the archive loaded, rebuilt offline from its cache, both smoke bags played
through it on an `--internal` network; on `main` it is uploaded as the run artifact). Tests: 770
passed, 1 deselected (needs the ride's frame cache); CI green on `main`.

**Release:** a pushed tag `v<version>-rcN` / `v<version>` (checked against the package version by
`scripts/release_meta.py`) runs `release.yml`: the tag's tests, the image exported, removed and
loaded back, two synthetic bags through the loaded image on an `--internal` network and in the
jury's form (`--net=host`, stock Fast DDS player as uid 1000), then the GitHub release with the
archive, `.sha256` and `SHA256SUMS`, downloaded again and its sum checked. `scripts/release.sh` is
the same chain by hand (`DRY_RUN=1 SMOKE=1` prints the plan).

## Known limitations

The detector's own: [`ALGORITHM.md`](ALGORITHM.md) §6 and the next section. Node and deployment:
latency at 360° on 4 cores is close to the 100 ms period (e2e p95 81–94 ms warm, up to 172 ms cold;
the numpy fallback is not real time there); results are stale without `--read-ahead-queue-size 10`,
and a disk slower than ~225 MB/s cannot feed 360° playback in real time; at start the player's burst (~0.7 s of recording) is worked
through at 5 Hz and the first STOP comes 0.8–1.2 s after the first cloud; freshness needs
synchronized clocks and a consumer that expires the status itself.

### Limitations of the sealed 27.09 detector (verified 28.09)

The detector is sealed ([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)): these are documented, not
fixed. Figures: the judgement of 28.09 ([`SCORECARD.md`](SCORECARD.md)).

* **A confirmed STOP drops for one frame when its object is missed twice in a row.** On
  `doubleT_obstacle` the object lying across the rail (about 20 points at 56 m, in view the whole
  recording) gets **GO at frame 111** and CAUTION at 117 and 197: in frames 110–111, 116–117 and
  196–197 the low-object stage ([`ALGORITHM.md`](ALGORITHM.md) §3.3b) forms no cluster from it, and
  `tracking.hold_misses` = 1 bridges only the first miss (ALGORITHM §4); the next frame is a STOP again. STOP
  on 123 of the 126 frames after the person leaves it (190 of 201 in all). `clear_distance` stays
  capped at 56.2 m (`health.clear_cap_lost`), but a consumer reading only `/resense/decision` gets
  GO for one 100 ms frame: do not act on a single-frame GO. It reproduces offline and in 4 of the 5
  jury-chain runs (the fifth had its GO at 197): the stages that form the cluster keep state (the
  bed template, the smoothed track model). The candidate fix `tracking.hold_misses` 2 restores those
  frames but failed the strict gate (ride 130 → 150 alarm frames and 32 → 34 events, five empty
  recordings 40 → 46 alarm frames, more set F false detections) and was rejected. Evidence:
  [`evidence/judge_outputs_2026-09-28/`](evidence/judge_outputs_2026-09-28/README.md).
* **Beyond the trusted axis an object on the track is `CAUTION`, not `STOP`.** A real person pasted
  into the other five tunnels gives a sustained STOP at 60 m in 11 of 15 windows, 100 m in 6, 130 m
  in 2, 160 m in 1, 200 m in none; the misses are `beyond_axis` where the trusted axis range is
  short (platforms, double-track sections: 45 m for a whole platform window) or a merge with
  trackside structure into a `column` ([`evidence/judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md)).
* **The learned opinion's delay is counted in processed frames** (ALGORITHM §3.6): at most 10 over a track's
  life, beyond 25 m, not for a body ≥ 1 m tall within 40 m — ~1 s at 10 Hz, ~2 s at 5 Hz, longer in
  recording time during a catch-up. Its positives are synthetic.
* **In-sample.** Every rule and the opinion's negatives were tuned on the six recordings, the ride
  and set O; the only held-out figure is the ride with the opinion cross-fitted (37 events). The
  labels of `doubleT_obstacle` and set O come from the team's own tools
  ([`EVALUATION.md`](EVALUATION.md) §1).
* **`CAUTION` is frequent**: 49 % of the frames of the obstacle-free recordings (35–69 % each), 37 %
  of the ride; an object demoted to it is easy to overlook.
* **Small and edge objects are confirmed late**: set O's 0.3 m cubes from 48–56 m, the edge cube
  from 35 m, the edge 2 m box from 29 m, the 5 cm hanging object from 30 m.
* **`clear_distance` is an estimate, not a guarantee**: it extends past an object inside the
  envelope in 300 of 605 set-O frames (68 of them GO).
