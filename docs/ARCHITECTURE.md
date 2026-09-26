# Architecture

> **Purpose:** components, data flow and real-time budget of ReSense (spec §5 "Архитектура").
> **Audience:** jury, team · **Owner:** P1 · **Language:** EN, summary RU
> **Last verified:** 2026-09-25, `8932f3a` (detector v0.6.3, node v0.6.4) · **Status:** current

**Кратко.** ROS 2-нода `resense_ros` принимает облако `PointCloud2` от `ros2 bag play` (любая из
двух пар топик / frame id) и передаёт каждый кадр библиотеке `resense` (Python: numpy / scipy /
scikit-learn и необязательные ядра на C++, без ROS). Библиотека переводит точки в систему поезда и
сама находит крепление LiDAR, строит модель пути (полотно, рельсы, ось и кривизна по стенам),
вырезает коридор габарита 2,1 × 3,0 м, ищет низкие объекты, кластеризует и подтверждает кандидатов
по времени. Нода публикует решение GO / CAUTION / STOP / FAULT, расстояние до препятствия,
проверенную свободную дальность, состояние входа и JSON-статус. Кадр обрабатывается за 42–64 мс в
среднем на одном ядре (23.09, numpy, без монитора состояния) при периоде датчика 100 мс; ядра на C++
(24.09) сокращают время детектора на 38–57 %, DBSCAN на cKDTree (25.09) — ещё на 1–3 мс, выход тот
же. Видеокарта не используется, скорость поезда не нужна (заданная учитывается).

```
ros2 bag play ──/lidar_points or /sensing/lidar/hesai128/pointcloud (PointCloud2, 10 Hz)──▶ resense_ros/detector_node
                                                                  │
                                                                  ▼
                              resense.Detector.process(Frame)  (numpy / scipy / sklearn; optional C++ kernels)
                                                                  │
   1. sensor → vehicle frame (X fwd, Y left, Z up), range crop     │  frame.py
   1b. mount auto-calibration (v0.6): orientation from the rail     │  calibration.py
        pair (8 candidates, spin axis vertical), roll from the rail heads, pitch from the bed
        slope, large yaw; provisional after 5 frames for a clearly tilted rig, final median of
        20 observations over 20 s, drift = median of the last 10 checks (every 50 frames)
   2. track model per frame                                       │  track.py
        • bed profile z(X): per-bin percentile, robust line + optional quadratic; height
          reference trusted 20 m beyond the fit or as far as the side-structure base verifies it
        • rail head level, track centre and yaw: two-ridge template (gauge 1.52 m) in three
          slabs of the 4–30 m range, profile built in the previous axis' coordinates
        • curvature 1/R: fit of the left/right tunnel boundaries (walls, column rows) with the
          rail tangent fixed; rate limits per frame; nearer side wins; axis trusted only up to
          the last observed boundary bin (+15 m), less when the two sides disagree
   3. clearance-gauge corridor                                     │  gauge.py
        • v0.6: the organizers' train envelope, polygon (dy, h) relative to axis and rail head:
          |dy| ≤ 1.05 m, h 0.12–3.0 m; advisory zone +0.35 m (= the v0.5 polygon, 1.40 m);
          edge margin 0.15 m per 100 m for the strict decision
        • v0.6.2: no rail pair in the near range → the corridor beyond 40 m is advisory
   3a. low objects (v0.6): bumps above the learned bed cross-section │  lowobj.py
        that reach the rail-head plane, within the observed bed (≤ 60 m); v0.6.2: an object
        straddling the envelope floor (across a rail) clustered whole
   3b. multi-frame accumulation beyond 40 m (only with a given train speed)  │  accumulate.py
   4. candidates → voxels (range-normalised) → DBSCAN (eps ∝ 1 + r/40 m; cKDTree)  │  clustering.py
        • filters: max extent, thin linear hardware, low track hardware, wall-like side
          structures, overhead-only clusters, expected-point visibility prior, and the
          infrastructure signatures (column, elevated, floating, corridor edge, wall face;
          v0.6: thin objects hanging near the axis are never demoted); far field (v0.6):
          beyond the height reference only tall, grounded, short clusters alarm
   5. persistence tracker (greedy NN, gate ∝ range, ego-speed slack)  │  tracking.py
        • confirmed after 3 hits spanning ≥ 0.5 s (v0.6.2), ≥ 60 % of the last 10 frames matched and
          ≥ 60 % of the last 10 hits inside the strict gauge; confidence ↑ per hit ↓ per miss;
          a reported obstacle is held over one missed frame (hold_misses 1, v0.6.3)
   5b. health (v0.6): input sanity, blocked view, visibility,       │  health.py
        rail lock, latency, calibration → level + monitored range + clear distance;
        decision_level (26.09) = level without the latency warning: what CAUTION reads
   6. FrameResult → topics                                          │  detector_node.py
        /resense/obstacle_detected (Bool)   /resense/nearest_distance (Float32)
        /resense/warning (Bool)             /resense/detections (vision_msgs/Detection3DArray)
        /resense/status (String JSON)       /resense/markers (MarkerArray)  /resense/corridor_points
        /resense/latency_ms (Float32)       /resense/fps (Float32)
        /resense/decision (String GO|CAUTION|STOP|FAULT)   /resense/clear_distance (Float32)
        /resense/health (diagnostic_msgs/DiagnosticArray) + watchdog on a silent input
        /tf_static: resense_lidar → <input frame_id> (identity, once per frame id)
        in: ego speed from ego_speed_mps / speed_topic (Float32) / odom_topic (Odometry), optional
                                                                  │
                                              RViz2 / Foxglove / web dashboard (web/)
```

## Packages and directories

| Path | Purpose |
|---|---|
| `resense/` | core library (no ROS dependency): decoding, track model, gauge, clustering, tracking, detector, synthetic data, metrics, CLI, plots |
| `ros2_ws/src/resense_ros/` | ROS 2 Humble `ament_python` package: node, launch, params, RViz config |
| `docker/`, `docker-compose.yml`, `scripts/` | reproducible build/run: `docker build → docker run → ros2 bag play → result`; on the stand, which has no internet, `docker load` of the image archive replaces the build ("Deployment without internet" below) |
| `configs/default.yaml` | all detector parameters; copied over the ROS package copy at Docker build time, `scripts/sync_params.sh --check` in CI keeps the two identical |
| `native/`, `setup.py` | optional C++ kernels for the per-frame hot spots, bit-identical to the numpy code they replace ("Native kernels" below); compiled by `pip install`, `RESENSE_NATIVE=0` forces numpy |
| `tests/` | pytest on a synthetic ray-cast tunnel (no dataset needed) |
| `docs/` | every document, its purpose and owner: [`docs/README.md`](README.md) |
| `web/` | the dashboard: replays a `results.jsonl`, or shows the live node through rosbridge — not in the image (`web/README.md`); roslib is bundled (`web/assets/vendor/`, 25.09), so the page needs no internet; live view without rosbridge: Foxglove |

## Data flow and formats

* Input: `sensor_msgs/PointCloud2` with fields `x y z intensity ring timestamp`
  ([`DATASET.md`](DATASET.md)), on either of the two (topic, frame) pairs the organizers use (23.09:
  the control data may have both, one LiDAR) or any other PointCloud2 topic found on the graph. One
  input at a time; a new recording (another topic or frame id, or a jump of the header stamps) gets
  a fresh detector (`detector_node.py` "Input handling"). The bag is played by `ros2 bag play`;
  nothing in the solution reads bag files (the offline CLI does, as a development tool). The node
  decodes it zero-copy into a numpy structured array (`pointcloud.py`), drops the `(0,0,0)` slots of
  the dual-return layout and points closer than 2.5 m.
* Internal `Frame`: `xyz (N,3) float32` in the vehicle frame, `intensity`, `ring`, `stamp`.
* Output `FrameResult` (also serialised as JSON on `/resense/status` and by `resense run --out`):
  `obstacle`, `warning`, `nearest_distance`, `detections[]` (id, zone, distance along track,
  lateral offset, centre, size, n_points, confidence, age, height_min, intensity), `track`
  (floor polynomial, axis centre/yaw/curvature, rail offset, quality flags), `timing_ms`;
  since v0.6 also `clear_distance`, `health` (level, messages, points, near fraction, blocked
  sectors, visibility, rail lock, latency p95, monitored range; since 26.09 `decision_level`, the
  level `/resense/decision` reads: without the latency warning unless
  `health.latency_affects_decision`) and `mount` (calibration status,
  orientation, roll / pitch / yaw, height, drift), and `detections[].kind` (`low` for a bed-level
  object). All older keys are unchanged.
  The ROS node adds a `node` object: `latency_ms` (decode + detect of this frame), `fps`,
  `frames`, `dropped_frames` (estimated from gaps in the input stamps, any cause),
  `catchup_skipped` (25.09: the part of them the node received and skipped while catching up),
  `catchup` (25.09: this frame was processed while behind), `input_period_ms`, `ego_speed_mps`,
  `ego_speed_source`, `input_topic`, `recording` (recordings seen); a fault snapshot has no `node`
  object.
* Node runtime statistics (spec §8.3): `/resense/latency_ms` per frame (decode + detect + publish),
  `/resense/fps` and a log line with latency mean / p95 / max and dropped frames every
  `stats_period` seconds. A frame that waits alone is processed at once, so if a frame takes longer
  than the sensor period the frames behind it are skipped rather than queued: the node works on the
  freshest data and the drop count makes overload visible. Several waiting frames (the burst at the
  start of a played bag: `ros2 bag play` preloads the recording and then sends its first seconds
  back to back) are worked through one every `catchup_step` = 0.3 s of recording from the first
  frame on, until the node is back on the newest (v0.6.4; `input_queue_depth` 40). Its reliability
  follows the publishers (`input_reliability: auto`, v0.6.2): reliable for `ros2 bag play` of the
  organizers' recordings — a best-effort reader lost 196 of the 201 10 MB clouds of
  `doubleT_obstacle` in Docker ([`EXPERIMENTS.md`](EXPERIMENTS.md) §3b) — and best-effort when a
  publisher is (a live sensor-data driver). The shipped RViz config subscribes to the raw clouds
  reliable too (a live best-effort driver needs the display's Reliability Policy switched in RViz).
* Transport: the image runs Fast DDS over UDP only (`docker/fastdds_udp.xml`, so that a player of
  any user reaches the root node) and sets 32 MiB socket receive buffers (8 MiB until 25.09); the
  kernel caps them at `net.core.rmem_max`, 212992 on a stock Ubuntu, silently, and Fast DDS 2.6
  keeps going with the capped buffer (`rmem_default` does not matter to a buffer set explicitly).
  At that a CycloneDDS player delivered none of the 24 MB 360° clouds, all of them at `rmem_max`
  32 MiB, and a stock Fast DDS player (`rmw_fastrtps_cpp`, fastrtps 2.6.12) all of them at 212992 on
  the first and third team VMs (25.09, EXPERIMENTS §3b; the second VM's "Fast DDS" host runs were
  CycloneDDS players, its host had no Fast DDS RMW); the 120° clouds arrive either way. So the jury commands start with
  `sudo sysctl -w net.core.rmem_max=33554432` (README step 0), and the node logs a WARN at start
  when `rmem_max` is below 32 MiB. **Opt-in shared memory** (`docker run … -e
  RESENSE_DDS=shm`, default off; the VM run of [`VM_GUIDE.md`](VM_GUIDE.md) §4.6 passed on 25.09
  evening, but so did the UDP default with a genuine Fast DDS player, so it stays opt-in until the
  captain decides): the
  entrypoint switches to shared memory + UDPv4 (`docker/dds_transport.sh`,
  `docker/fastdds_shm_udp.xml`), so a stock Fast DDS player on the host hands the clouds over
  `/dev/shm`, whatever `rmem_max` is. Fast DDS 2.6 creates its segments 0644 with no option to
  change that, so `docker/fastdds_shm_share.py` sets the node's own port and data segments to 0666
  for a player of another uid. It needs `--ipc=host` (without it the entrypoint stays on UDP with a
  WARN); players without shared memory (CycloneDDS, the image's profile, another machine) are
  served over UDP as before. One INFO line at start names the mode.
* Ego speed for multi-frame accumulation: the node passes `Detector.process(frame, ego_speed=v)`
  the value of the `ego_speed_mps` parameter, else the latest `speed_topic` / `odom_topic`
  message younger than `speed_timeout`, else `None` (single-frame path); the status JSON reports
  `node.ego_speed_mps` and `node.ego_speed_source`. The organizers' recordings carry no odometry
  and some trains have none (Q&A fact 6), so the no-speed path is the deliverable. The LiDAR-only
  estimator (`accumulation.estimate_speed`) stays off: measured on 24.09 it is accurate, but even a
  perfect speed does not improve the organizers' check ([`EXPERIMENTS.md`](EXPERIMENTS.md) §9).
* One fixed frame for every bag: the organizers' recordings carry different `frame_id`s
  (`hesai_lidar`, `lidar_livox`), so the node broadcasts a static identity transform
  `resense_lidar → <input frame_id>` when the first frame arrives and the RViz / Foxglove layouts
  use `resense_lidar` as their fixed frame.
* Verification without the dataset: `scripts/make_smoke_bag.py` writes a 40-frame synthetic bag in
  the organizers' exact layout (clear tunnel, then a person at 60 m), `scripts/smoke_test.sh`
  plays it through the node inside the Docker image and `scripts/check_dry_run.py` asserts the
  status stream; the CI docker job runs this on every push. The same checker scores the real
  dry run (`scripts/dry_run.sh`) on `doubleT_obstacle`; on 23.09 it ran in Docker on the real
  frames (bags rebuilt from the cache by `scripts/cache_to_bag.py`), with the node and the player
  in separate containers and two recordings into one node (EXPERIMENTS §3b).
* `resense inject` writes `*.npz` (xyz, intensity, per-point labels) + `gt.json`;
  `resense eval` consumes them and prints recall by range, FP rates, latency.

## Why this design

* **Environment prior instead of object classes** (spec §8.4): the tunnel is a corridor with
  rails; anything inside the clearance gauge that is not rails/bed/known hardware is a hazard,
  whatever it looks like. No labelled obstacle classes are needed.
* **Self-calibration**: bed level, rail level and track axis are re-estimated every frame from the
  rails, and (v0.6) the mount itself — which axis looks forward, roll, pitch — is found from the
  rails and the bed in the first frames, so a different mount (the organizers, 22.09: "the LiDAR
  position is not fixed") needs no manual calibration; the launch file still accepts it. 24.09:
  the test bags use the mounts of the provided ones, the LiDAR 1 075 mm above the rail head on the
  train's centreline ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md)),
  so the calibration stays as a safeguard.
* **The customer's envelope** (v0.6): the strict decision uses the 2.1 × 3.0 m cross-section the
  organizers gave; the wider v0.5 polygon became the advisory zone.
* **Fail-safe outputs** (v0.6): `clear_distance` shrinks to what was actually checked and to 0 on
  any input fault; the decision topic says `FAULT` instead of staying silent, and since 24.09 a
  fault is published on every output at once (no earlier `STOP` stays latched;
  [`README.md`](../README.md) "Topics published by the node").
* **Curvature from parallel references**: rails are visible only to ~30–40 m, walls/column rows
  to 150–200 m (Shen et al. 2024). This is what makes a corridor at 100+ m meaningful; where no
  boundary is observed the corridor is explicitly *not trusted* and only warnings are raised.
* **Range-adaptive everything**: voxel size, DBSCAN radius, minimum cluster size and the
  expected-point prior all scale with range, so a 5-point cluster at 150 m is treated as
  seriously as a 500-point cluster at 20 m.
* **Persistence before alarm**: ≥ 3 hits spanning ≥ 0.5 s — five frames at 10 Hz (v0.6.2; 0.3 s
  before) — suppress single-frame noise and flickering edge structures; the cost is 0.5 s of latency
  for an object that appears inside the envelope — 11 m of travel at 80 km/h — and none for one
  tracked while it approaches (EXPERIMENTS §0: −35 % false-alarm events on the empty bags, −27 % on
  the ride).
* **No rails, no far alarm** (v0.6.2): without the rail pair in the near range (stations, switch
  caverns) the corridor beyond 40 m is advisory and the verified-clear distance says 40 m.

## Real-time budget (v0.6.3, 23.09: every frame of the real bags, idle 4-core sandbox, numpy path)

| stage | `roundT_doubleT` (189 k pts) mean | `doubleT_obstacle` (347 k pts, 360°) mean |
|---|---|---|
| track model (bed, rails, walls, verification, calibration) | 27.4 ms | 39.9 ms |
| corridor mask + low-object stage | 12.6 ms | 16.7 ms |
| voxel + DBSCAN + filters | 10.0 ms | 6.7 ms |
| tracking | 0.2 ms | 0.2 ms |
| **total** (mean / p95 / max; health monitor not included) | **50.2 / 63.4 / 76.1 ms** | **63.6 / 77.8 / 119.2 ms** |

Source: [`EXPERIMENTS.md`](EXPERIMENTS.md) §3, raw output in
[`evidence/timing_2026-09-23/`](evidence/timing_2026-09-23/). Re-measured 24.09 on another idle VM:
36.5–52.2 ms mean, p95 50.3–67.1 ms (EXPERIMENTS "Re-measurement"); the 23.09 figures stay quoted.
`total` (`timing_ms["total"]`, what `resense bench` prints) ends after tracking: the health monitor
runs after it and adds 7–14 ms per frame on the sandbox; the node's `/resense/latency_ms` includes
it. "360°" is `doubleT_obstacle`, about −124…+118° of azimuth in the vehicle frame.

The frame period is 100 ms; p95 is inside it on all six bags and on a station section of the
ride (v0.6.3: 42–64 ms mean, p95 53–78 ms, EXPERIMENTS §3). **Resources:** one CPU core per
stream (47–65 ms of CPU time per frame = 47–65 % of a core at 10 Hz with single-threaded BLAS, set
in the image), about 160–180 MB resident, no GPU. **Through ROS in Docker** (23–24.09,
v0.6.2–v0.6.4, EXPERIMENTS §3b): the 120° recording at the full 10 Hz (p95 76 ms), the 360° one at
7–10 fps in steady state (~96 ms mean: the node skips frames rather than lagging), the node
container at ~100 % of one core while frames arrive, 186 MB (v0.6.3); the v0.6.4 catch-up queue
raises the peak to 403–434 MB at 360°. The jury's i7-9700E (8 faster cores) is not open to the
team before submission ([`organizers/answers.md`](organizers/answers.md) §6); the 8-core figures
come from the team's own 8-core machine ([`CAPTAIN.md`](CAPTAIN.md) action 7). The table is the
numpy path; the optional native kernels (next section) roughly halve it.

## Native kernels (optional, C++; 24.09)

Most of a frame's time went into full-cloud numpy passes of the track stage and the corridor /
low-object selection (a mask, a gather and a float64 temporary per step over 190–350 k points)
and into ten `np.lexsort` calls per frame for the per-bin percentiles. `native/resense_native.cpp`
does the same work in one pass each, as a plain C ABI loaded with ctypes by `resense/_native.py`:

| kernel | replaces |
|---|---|
| `rs_bin_percentile` | `track.bin_percentile` (bed, rails, walls, bed template, low objects): counting sort + selection instead of `np.lexsort` |
| `rs_floor_z`, `rs_center_y`, `rs_corridor_coordinates` | `TrackModel.floor_z` / `center_y` and `gauge.corridor_coordinates` over the whole cloud |
| `rs_floor_band`, `rs_rails_band`, `rs_walls_band`, `rs_verify_profile` | the selection prologues of `_fit_floor`, `estimate_rails`, `estimate_axis_from_walls`, `verify_floor_extrapolation` |
| `rs_select` | the mask chains of the bed template, the low-object band and the corridor range / bounding box |
| `rs_visibility` | `health.visibility_along_track` |

**Same output, bit for bit.** Every kernel performs the numpy expression's IEEE operations in the
same order (compiled without FMA contraction, fast-math or `-march=native`), a float32 coordinate
is compared with a threshold in float32 as numpy does, and a selection returns the element a
stable sort puts at that rank. Anything else (a numpy float64 threshold, an unusual dtype, a small
array) takes the numpy code, which stays in place as the fallback. Checked by
`tests/test_native.py` (every kernel against its numpy code, the detector on the synthetic tunnel)
and on real data: all 3 998 cached frames (six recordings and the organizers' fake-object ride)
give identical per-frame results with and without the kernels, and `scripts/output_fingerprint.py`
(unrounded candidate values, the given-speed and estimator paths) is identical too; the same holds
with the image's numpy 1.26 / scipy 1.13 / scikit-learn 1.5.

**Faster.** Interleaved A/B on the same frames (medians; both detectors see every frame, the
order alternates), one pinned core, single-threaded BLAS, 120 frames × 3, this 4-vCPU sandbox at
load ~3 on 24.09 (it is slower than the idle one of the budget above: the numpy path measures
62 instead of 50 ms on `roundT_doubleT`); separate processes, ABAB × 3, give the same −46 % and
−58 %:

| recording | numpy: track / corridor / total | native: track / corridor / total | `process()` wall incl. health |
|---|---|---|---|
| `roundT_doubleT` (190 k points, 120°) | 31.1 / 17.3 / **62.4 ms** | 11.8 / 6.8 / **33.5 ms** (−46 %) | 70.4 → 37.7 ms (p95 93.8 → 54.6) |
| `doubleT_obstacle` (341 k points, 360°) | 49.1 / 22.3 / **81.3 ms** | 17.6 / 7.7 / **34.6 ms** (−57 %) | 94.8 → 41.3 ms (p95 123.4 → 57.8) |
| `squareT_platform_squareT_switch` (179 k) | 29.5 / 13.8 / **52.4 ms** | 11.5 / 6.4 / **26.9 ms** (−49 %) | 60.1 → 30.9 ms |
| `doubleT_platform` (164 k, the platform approach) | 27.7 / 14.4 / **66.7 ms** | 10.8 / 7.2 / **41.3 ms** (−38 %) | 74.0 → 45.2 ms |
| `roundT_doubleT`, speed given (8 m/s: accumulation) | 31.5 / 17.6 / **70.7 ms** | 11.8 / 7.0 / **41.1 ms** (−42 %) | 78.6 → 45.2 ms |

**DBSCAN on cKDTree (25.09, `508b04a`).** With the kernels the clustering stage became the largest
on the 120° recordings, and it no longer calls scikit-learn. `resense.clustering.dbscan_labels`
builds scipy's `cKDTree` and keeps a neighbour pair when the float64 squared distance, summed
x → y → z, is `<= eps²`: scikit-learn's KD-tree test. It joins the core points into connected
components numbered by their lowest core index, and gives a border point the lowest-numbered
neighbouring cluster, as scikit-learn's seed loop does. The labels are identical to
`sklearn.cluster.DBSCAN` on all 9 240 real calls of the seven cached recordings and on random
sets with distance ties, with the dev VM's libraries and with the image's (numpy 1.26.4 / scipy
1.13.1 / scikit-learn 1.5.2; `tests/test_cpu_savings.py` runs the comparison in the CI image). The
detector's per-frame output is identical on all 3 998 frames, on both paths, and the regression
gate passes on the merged code with every gated metric the same. It costs 0.77 ms per call
instead of 1.5–1.8 ms, which saves 1.3–2.6 ms per frame (5–10 %) with the image's libraries on the
native path (interleaved A/B, one pinned core; EXPERIMENTS §3). scikit-learn stays a dependency
for tests and scripts.

Not ported on purpose: the mount rotation (a float32 BLAS product, whose rounding depends on the
BLAS kernel) and the health monitor's azimuth histogram (`arctan2` of libm and numpy's SIMD code
can differ in the last bit at a sector edge). Two more output-identical savings from the GPU study
were measured on 25.09 and not shipped (EXPERIMENTS §7):

- reusing the track stage's per-point bed height in `corridor_coordinates` is bit-identical, but
  slower on the native path (0.98 → 1.74 ms at 360°), because `rs_corridor_coordinates` already
  does it in one pass;
- cropping the detection stages to X ≥ 2.9 m (41 % of the points at 360°, 11 % at 120°; the
  calibrator and the health monitor keep the whole cloud) is identical on all 3 998 frames on both
  paths; it saves 8 ms at 360° on the numpy path, but nothing on the native path
  (+0.05…+0.65 ms): the gather costs what the cheaper passes save.

**Build and switch.** `pip install .` / `pip install -e .` compile the kernels (`setup.py`, an
optional extension: without a C++ compiler the install still succeeds and the detector runs on
numpy with the same results, slower); `scripts/build_native.sh` builds them in a source checkout
used with `PYTHONPATH=.`. The Docker image installs `g++` and prints the path it took at build
time; the node logs it at start (`per-frame kernels: native (...)`). `RESENSE_NATIVE=0` forces
the numpy code. The test suite passes on both paths (289 tests on 25.09; 587 on 26.09, the whole suite green on
the native path in the 26.09 re-judgement; the release and video tests do not touch the kernels). **Docker:** proven by CI run 36058665640 (24.09,
commit `d1a2d0c`): the image built the kernels, the in-image suite passed with
`RESENSE_REQUIRE_SYNTHETIC=1` (a missing library would have failed it), and both ROS smoke tests
passed (synthetic bags, decode + detect 35 ms mean); every docker job since does the same (run
36123184213 on `79109f5`, 25.09: 344 passed in the image, which has no `docs/`). Neither path can
be run on the i7-9700E before submission (no stand access); the team's 8-core machine stands in
for both (`scripts/bench_8core.sh` times both, EXPERIMENTS §3).

## GPU: evaluated, not used (24.09)

The stand has an RTX 4070 Ti SUPER
([`organizers/test_stand_software.md`](organizers/test_stand_software.md)). The spec (§3.1) allows
the GPU only if the algorithm needs it («если это необходимо для его работы»); ReSense does not, and
a study of 24.09 found no reason to add it before 29.09 [estimates from measured CPU stage times
and published per-operation costs; no GPU in the sandbox]:

* **Small upside.** A frame is ~1 160 array operations (about 108 boolean-mask gathers and 83
  reductions that feed Python `if`s), so a straight CuPy port is dispatch- and sync-bound: it would
  save ≤ 30–45 ms per 360° frame against numpy and 5–15 ms against fused CPU code such as the
  native kernels above. Transfer is not the problem (5.4 MB per 360° frame), but the i7-9700E has
  PCIe 3.0 only. cuML DBSCAN is slower than scikit-learn on our 100–1 000-voxel calls.
* **Real costs.** A container that requests the GPU does not start at all when the host lacks
  `nvidia-container-toolkit` (not in the organizers' package list), so the default launch could not
  request it; CuPy compiles its kernels at first use (seconds of warm-up in a fresh container); the
  image grows by 0.3–6 GB; the GPU path cannot be tested on the sandbox or in CI (no GPU on the
  runners).
* **Latency is not the limit.** An alarm needs ≥ 3 hits over ≥ 0.5 s; processing is < 15 % of the
  time to alarm.

CPU savings the same study measured as prototypes, identical decisions on 1 701 real frames, not
merged: an exact cKDTree DBSCAN (−4…−6 ms per frame), float32 corridor coordinates (−3…−6 ms), a
forward crop at X ≥ 2.9 m inside the detector (−17 ms at 360°: 42 % of its points lie at X < 3 m)
and a single-pass C++ decode in the node (−11…−20 ms at 360°). They were measured on the numpy
path, before the native kernels. With them the expected mean node latency on the i7-9700E at
360° is 48–56 ms [estimate; it assumes that numpy path]. 25.09: of these, the cKDTree DBSCAN
shipped; the in-detector forward crop was identical but brought no gain on the native path, and
the bed-height reuse was slower there ("Native kernels" above).

## Deployment without internet (25.09)

The test machine has no internet ([`organizers/answers.md`](organizers/answers.md) §7). Audit of
25.09, everything the jury path touches:

| stage | needs the network for | source |
|---|---|---|
| `docker build` (`docker/Dockerfile`) | base image `ros:humble-ros-base-jammy` | Docker Hub |
| | `apt-get`: the ROS 2 packages (vision / nav msgs, tf2, RViz, rosbag2 with sqlite3 and mcap, foxglove_bridge), `python3-pip`, `g++` | packages.ros.org, Ubuntu archive |
| | `pip`: pip ≥ 24, pinned numpy / scipy / scikit-learn / pyyaml (their dependencies joblib and threadpoolctl unpinned), setuptools for `pip install .`; `WITH_TOOLS=1`: rosbags, zstandard, matplotlib, open3d, pytest | PyPI |
| run time: node, launch file, entrypoint, compose services, RViz, foxglove_bridge | nothing: DDS over UDP on the host's interfaces (the loopback alone is enough), foxglove_bridge serves `ws://…:8765` itself, RViz is local | — |
| dashboard `web/index.html`, label tool | nothing: fonts local, roslib bundled since 25.09 (it came from a CDN); its live mode needs rosbridge, which is not in the image | — |
| Foxglove viewer (remote demo) | the desktop app works offline; app.foxglove.dev is a web page on the viewer's laptop | — |
| overview video `scripts/make_overview_video.py` | nothing: clips, renders, deck and fonts are in the repository; Pillow, PyMuPDF and an ffmpeg with libx264 (`imageio-ffmpeg`) installed once | — |
| not on the jury path | `scripts/unpack_dataset.py` (Yandex Disk), `scripts/build_deck.py` (template), CI | — |

**Delivery.** `scripts/export_image.sh` builds the runtime image from `git archive HEAD`, tags
`resense:<version>` and `resense:latest`, and writes `dist/resense-image-<version>.tar.gz` (gzip:
`docker load` reads it on any Docker; zstd would be ~10–20 % smaller but not every Docker reads it)
with its `.sha256`; `scripts/load_image.sh` checks the sum, loads the archive and runs the image
with `--network none`. The runtime image keeps `g++` (the C++ kernels are compiled at build time)
and RViz: a multi-stage build without the compiler would be smaller but changes every layer, so it
waits until after the freeze. The CI `docker` job proves the chain on the `WITH_TOOLS=1` image:
`docker save` → `docker rmi` → `docker load`, then the synthetic bags through the loaded image with
`--network none` (only the loopback: Fast DDS joins its discovery multicast group on the loopback
and sends through a loopback-bound socket, so the processes find each other with no network
interface up) and in separate containers on a `docker network create --internal` network (no way
out). The CI `offline-build` job does it with the jury's own image: it makes the runtime archive as
`export_image.sh` makes the release, removes every image and the build cache, loads the archive,
and plays both synthetic bags through `resense:<version>` exactly as loaded. It first checks that
this is the archive's image (the built layers, the version and commit labels) and the runtime one
(no open3d / rosbags, so the bags are made on the runner), with rosbag2 and its sqlite3 plugin.
The playback runs on an `--internal` network: `check_no_network.py`, the node on its default
command, a `/resense/status` recorder, a uid-1000 player of the same image, `check_dry_run.py
--expect-obstacle --expect-inputs 2`. First green on `5a15c7c` (run 36122640174, 25.09): 78 status
messages, 42 alarm frames at 44.9–59.9 m, p95 26 ms, both recordings, `PASS`.

**Download from CI (26.09).** On a push to `claude/nifty-pascal-lzgl78` or `main` (not on other
branches or tags), and only when every step of `offline-build` passed, the job uploads that very
archive (`actions/upload-artifact@v4`, kept 30 days, stored as is: it is gzip already) as the run
artifact `resense-image-<version>-<short commit>`: `resense-image-<version>-<short
commit>.tar.gz`, a hard link to the archive that was loaded, rebuilt offline and played through,
and its `.sha256`, written for that name as `export_image.sh` writes it and checked against the
sum `load_image.sh` verified, so `scripts/load_image.sh` and `sha256sum -c` take the pair as
they take an exported one. The stand has no internet and the archive of the frozen commit no
longer needs a machine with Docker: Actions → the `ci` run of that commit → Artifacts (a GitHub
login is needed), or `gh run download <run id> -n resense-image-<version>-<short commit>`. It is
the `GZIP_LEVEL=1` archive (0.49 GiB; `export_image.sh`'s default level 6 gave 0.44 GiB on the
team VM, 25.09) with the base image's tag, and `load_image.sh` prints its commit label.

**Offline `docker build` (best effort).** If the jury insists on building, after `docker load`:

```bash
chmod -R u+rwX,go+rX,go-w .                         # in the source tree of the same tag
docker build --cache-from resense:<version> -t resense -f docker/Dockerfile .
```

The archive's image was built with `BUILDKIT_INLINE_CACHE=1` on a base image resolved from the local
store, and the base image's tag is in the archive (its layers are the image's lowest ones, a few KB
more), so BuildKit resolves `FROM` locally and finds every step in the loaded image's cache;
nothing is downloaded. Caveats: (1) BuildKit (default since Docker 23; `DOCKER_BUILDKIT=1` on
20.10–22) with the classic image store; the containerd image store (the default of fresh Docker 29
installs) is untested; (2) the stand's Docker must turn the Dockerfile into the same build graph as
the Docker that made the archive: another release may change it and miss the cache, and the
stand's version is unknown; (3) the context must be the tag's tree with the same permission bits
(they are part of the cache key: a checkout under `umask 002` differs until the `chmod` above);
(4) no `--pull`, `--no-cache`, `--network` or `WITH_TOOLS` (each changes the cache key); (5) any
miss makes the build try `apt-get` and fail, and then the loaded image is untouched, so `docker run`
still works. The CI job `offline-build` runs exactly this on the runner's Docker with Docker Hub
blocked, as a gate since 25.09 (it passed on all four runs made with continue-on-error:
36109782167, 36112092652, 36113989932, 36116178404); for the jury it stays best effort because the
stand's Docker is unknown. Its first result, run 36109782167 (25.09, `2b3cbd0`): the runtime
archive is 521 185 902 bytes (0.49 GiB at `GZIP_LEVEL=1`; the image 1.34 GiB unpacked, the base
image included), and after all images and the build cache were removed and the archive loaded,
all 18 steps came from the cache ("every layer identical to the archive's, no step ran"); every
later run repeated it (version 1.0.0 on `5a15c7c`: 521 306 060 bytes). The documented path stays
`docker load`.

**Release.** `.github/workflows/release.yml` turns a pushed tag `v<version>-rcN` / `v<version>`
into a GitHub release (the tag must name the version the four declarations agree on,
`scripts/release_meta.py`; now `v1.0.0-rcN` / `v1.0.0`). It builds the runtime image with
`scripts/export_image.sh` (gzip -6), removes it and the build cache, loads the archive back with
`scripts/load_image.sh`, and plays two synthetic bags through the loaded image on an `--internal`
network (`scripts/internal_net_test.sh`) and with `--net=host` and a stock Fast DDS player
(`scripts/console_test.sh`). It then publishes `resense-image-<tag>.tar.gz`, its `.sha256` and
`SHA256SUMS` (`scripts/publish_release.sh`; a re-run replaces them) and re-downloads the archive
to check the sum (`scripts/verify_release.sh`). `scripts/release.sh` is the same chain by hand.
No tag or release is planned now (deferred by the captain on 25.09: the system is still in
development), so the workflow is inert and has never run; the same runtime image is built,
archived, loaded back and played through on every push by the `offline-build` job, and on the
working branch and `main` offered for download (above).

## Known limitations

Details: [`ALGORITHM.md`](ALGORITHM.md) §6 and [`EXPERIMENTS.md`](EXPERIMENTS.md) §4.

* Curvature is only observed where tunnel boundaries are visible; stations and switch caverns
  weaken the estimate → detections there are demoted to warnings and `health` reports it.
* Infrastructure filters are hand-tuned on six bags and checked on the 20-minute ride.
* A low object lying on the bed below the rail head is not an alarm by default (bed fixtures of
  the same size); an object on a rail is.
* Without a train speed the tracker uses a range-dependent gate with a 25 m/s slack and the
  pipeline is single-frame; beyond ~150 m a person returns 3–10 points per frame.
