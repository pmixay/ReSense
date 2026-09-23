# Architecture

```
ros2 bag play ──/lidar_points or /sensing/lidar/hesai128/pointcloud (PointCloud2, 10 Hz)──▶ resense_ros/detector_node
                                                                  │
                                                                  ▼
                              resense.Detector.process(Frame)  (pure numpy / scipy / sklearn)
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
   4. candidates → voxels (range-normalised) → DBSCAN (eps ∝ 1 + r/40 m)  │  clustering.py
        • filters: max extent, thin linear hardware, low track hardware, wall-like side
          structures, overhead-only clusters, expected-point visibility prior, and the
          infrastructure signatures (column, elevated, floating, corridor edge, wall face;
          v0.6: thin objects hanging near the axis are never demoted); far field (v0.6):
          beyond the height reference only tall, grounded, short clusters alarm
   5. persistence tracker (greedy NN, gate ∝ range, ego-speed slack)  │  tracking.py
        • confirmed after 3 hits spanning ≥ 0.5 s (v0.6.2), ≥ 60 % of the last 10 frames matched and
          ≥ 60 % of the last 10 hits inside the strict gauge; confidence ↑ per hit ↓ per miss
   5b. health (v0.6): input sanity, blocked view, visibility,       │  health.py
        rail lock, latency, calibration → level + monitored range + clear distance
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
| `docker/`, `docker-compose.yml`, `scripts/` | reproducible build/run: `docker build → docker run → ros2 bag play → result` |
| `configs/default.yaml` | all detector parameters; copied over the ROS package copy at Docker build time, `scripts/sync_params.sh --check` in CI keeps the two identical |
| `tests/` | pytest on a synthetic ray-cast tunnel (no dataset needed) |
| `docs/` | organizers' materials, dataset and sensor notes, algorithm, evaluation protocol, research, plan, experiments, submission checklist, presentation notes |
| `web/` | the dashboard: replays a `results.jsonl` or shows the live node through rosbridge (`web/README.md`) |

## Data flow and formats

* Input: `sensor_msgs/PointCloud2` with fields `x y z intensity ring timestamp` (see DATASET.md),
  on either of the two (topic, frame) pairs the organizers use (23.09: the control data may have
  both, one LiDAR) or any other PointCloud2 topic found on the graph. One input at a time; a new
  recording (another topic or frame id, or a jump of the header stamps) gets a fresh detector
  (`detector_node.py` "Input handling"). The bag is played by `ros2 bag play`; nothing in the
  solution reads bag files (the offline CLI does, as a development tool).
  The node decodes it zero-copy into a numpy structured array (`pointcloud.py`), drops the
  `(0,0,0)` slots of the dual-return layout and points closer than 2.5 m.
* Internal `Frame`: `xyz (N,3) float32` in the vehicle frame, `intensity`, `ring`, `stamp`.
* Output `FrameResult` (also serialised as JSON on `/resense/status` and by `resense run --out`):
  `obstacle`, `warning`, `nearest_distance`, `detections[]` (id, zone, distance along track,
  lateral offset, centre, size, n_points, confidence, age, height_min, intensity), `track`
  (floor polynomial, axis centre/yaw/curvature, rail offset, quality flags), `timing_ms`;
  since v0.6 also `clear_distance`, `health` (level, messages, points, near fraction, blocked
  sectors, visibility, rail lock, latency p95, monitored range) and `mount` (calibration status,
  orientation, roll / pitch / yaw, height, drift), and `detections[].kind` (`low` for a bed-level
  object). All older keys are unchanged.
  The ROS node adds a `node` object: `latency_ms` (decode + detect of this frame), `fps`,
  `frames`, `dropped_frames` (estimated from gaps in the input stamps), `input_period_ms`.
* Node runtime statistics (spec §8.3): `/resense/latency_ms` per frame (decode + detect +
  publish), `/resense/fps` and a log line with latency mean / p95 / max and dropped frames every
  `stats_period` seconds. The input subscription keeps one frame (`input_queue_depth`, keep-last),
  so if a frame takes longer than the sensor period the older frames are dropped rather than
  queued: the node always works on the freshest data and the drop count makes overload visible.
  Its reliability follows the publishers (`input_reliability: auto`, v0.6.2): reliable for
  `ros2 bag play` of the organizers' recordings — a best-effort reader lost 196 of the 201
  10 MB clouds of `doubleT_obstacle` in Docker (EXPERIMENTS.md §3b) — and best-effort when a
  publisher is (a live sensor-data driver).
* Ego speed for multi-frame accumulation: the node passes `Detector.process(frame, ego_speed=v)`
  the value of the `ego_speed_mps` parameter, else the latest `speed_topic` / `odom_topic`
  message younger than `speed_timeout`, else `None` (single-frame path: the LiDAR-only speed estimator is off by default, `accumulation.estimate_speed`); the
  status JSON reports `node.ego_speed_mps` and `node.ego_speed_source`.
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
  in separate containers and two recordings into one node (EXPERIMENTS.md §3b).
* `resense inject` writes `*.npz` (xyz, intensity, per-point labels) + `gt.json`;
  `resense eval` consumes them and prints recall by range, FP rates, latency.

## Why this design

* **Environment prior instead of object classes** (spec §8.4): the tunnel is a corridor with
  rails; anything inside the clearance gauge that is not rails/bed/known hardware is a hazard,
  whatever it looks like. No labelled obstacle classes are needed.
* **Self-calibration**: bed level, rail level and track axis are re-estimated every frame from the
  rails, and (v0.6) the mount itself — which axis looks forward, roll, pitch — is found from the
  rails and the bed in the first frames, so a different mount (the organizers: "the LiDAR
  position is not fixed") needs no manual calibration; the launch file still accepts it.
* **The customer's envelope** (v0.6): the strict decision uses the 2.1 × 3.0 m cross-section the
  organizers gave; the wider v0.5 polygon became the advisory zone.
* **Fail-safe outputs** (v0.6): `clear_distance` shrinks to what was actually checked and to 0 on
  any input fault; the decision topic says `FAULT` instead of staying silent.
* **Curvature from parallel references**: rails are visible only to ~30–40 m, walls/column rows
  to 150–200 m (Shen et al. 2024). This is what makes a corridor at 100+ m meaningful; where no
  boundary is observed the corridor is explicitly *not trusted* and only warnings are raised.
* **Range-adaptive everything**: voxel size, DBSCAN radius, minimum cluster size and the
  expected-point prior all scale with range, so a 5-point cluster at 150 m is treated as
  seriously as a 500-point cluster at 20 m.
* **Persistence before alarm**: ≥ 3 hits spanning ≥ 0.5 s — five frames at 10 Hz (v0.6.2; 0.3 s before) — suppress
  single-frame noise and flickering edge structures; the cost is 0.5 s of latency for an object
  that appears inside the envelope — 11 m of travel at 80 km/h — and none for one tracked while it
  approaches (EXPERIMENTS.md §0: −35 % false-alarm events on the empty bags, −27 % on the ride).
* **No rails, no far alarm** (v0.6.2): without the rail pair in the near range (stations, switch
  caverns) the corridor beyond 40 m is advisory and the verified-clear distance says 40 m.

## Real-time budget (v0.6.1, every frame of the real bags, quiet 4-core sandbox, Python)

| stage | `roundT_doubleT` (189 k pts) mean | `doubleT_obstacle` (347 k pts, 360°) mean |
|---|---|---|
| track model (bed, rails, walls, verification, calibration) | 26.8 ms | 37.1 ms |
| corridor mask + low-object stage | 11.6 ms | 16.4 ms |
| voxel + DBSCAN + filters | 6.7 ms | 4.3 ms |
| tracking | 0.1 ms | 0.1 ms |
| **total** (mean / p95 / max) | **45.3 / 55.9 / 93.4 ms** | **57.9 / 69.1 / 109.6 ms** |

The frame period is 100 ms; p95 is inside it on all six bags and on a station section of the
ride (42–58 ms mean, p95 52–69 ms, EXPERIMENTS.md §3). **Resources:** one CPU core per stream
(47–65 ms of CPU time per frame = 47–65 % of a core at 10 Hz with single-threaded BLAS, set in
the image), about 160–180 MB resident, no GPU. **Through ROS in Docker** (v0.6.2, §3b of
EXPERIMENTS.md): the 120° recording at the full 10 Hz (p95 76 ms), the 360° one at 8–10 fps in
steady state (~96 ms mean: the node skips frames rather than lagging), the node container at
~100 % of one core while frames arrive, 186 MB. The jury's i7-9700E (8 faster cores) has not been measured.

## Known limitations (see ALGORITHM.md §6 and EXPERIMENTS.md)

* Curvature is only observed where tunnel boundaries are visible; stations and switch caverns
  weaken the estimate → detections there are demoted to warnings and `health` reports it.
* Infrastructure filters are hand-tuned on six bags and checked on the 20-minute ride.
* A low object lying on the bed below the rail head is not an alarm by default (bed fixtures of
  the same size); an object on a rail is.
* Without a train speed the tracker uses a range-dependent gate with a 25 m/s slack and the
  pipeline is single-frame; beyond ~150 m a person returns 3–10 points per frame.
