# Architecture

```
ROS 2 bag ──/lidar_points (PointCloud2, 10 Hz, ~190k pts)──▶ resense_ros/detector_node
                                                                  │
                                                                  ▼
                              resense.Detector.process(Frame)  (pure numpy / scipy / sklearn)
                                                                  │
   1. sensor → vehicle frame (X fwd, Y left, Z up), range crop     │  frame.py
   2. track model per frame                                       │  track.py
        • bed profile z(X): per-bin percentile, robust line + optional quadratic
        • rail head level + track axis: two-ridge template (gauge 1.52 m) in 4–30 m
        • yaw / curvature: quadratic fit of the left/right tunnel boundaries
          (walls, column rows) in the band 1.8–2.6 m above rail head; nearer side wins;
          axis trusted only up to the last observed boundary bin (+15 m)
   3. clearance-gauge corridor                                     │  gauge.py
        • polygon (dy, h) relative to axis and rail head: |dy| ≤ 1.4 m, h 0.55–3.5 m,
          plus the low zone |dy| ≤ 0.95 m from h = 0.12 m; advisory zone +0.35 m
   4. candidates → voxels (range-normalised) → DBSCAN (eps ∝ 1 + r/40 m)  │  clustering.py
        • filters: max extent, thin linear hardware, low track hardware, wall-like side
          structures, overhead-only clusters, expected-point visibility prior
   5. persistence tracker (greedy NN, gate ∝ range, ego-speed slack)  │  tracking.py
        • confirmed after 3 hits, confidence ↑ per hit ↓ per miss
   6. FrameResult → topics                                          │  detector_node.py
        /resense/obstacle_detected (Bool)   /resense/nearest_distance (Float32)
        /resense/warning (Bool)             /resense/detections (vision_msgs/Detection3DArray)
        /resense/status (String JSON)       /resense/markers (MarkerArray)  /resense/corridor_points
        /resense/latency_ms (Float32)       /resense/fps (Float32)
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
| `web/` | dashboard scaffold for the frontend member |

## Data flow and formats

* Input: `sensor_msgs/PointCloud2` with fields `x y z intensity ring timestamp` (see DATASET.md).
  The node decodes it zero-copy into a numpy structured array (`pointcloud.py`), drops the
  `(0,0,0)` slots of the dual-return layout and points closer than 2.5 m.
* Internal `Frame`: `xyz (N,3) float32` in the vehicle frame, `intensity`, `ring`, `stamp`.
* Output `FrameResult` (also serialised as JSON on `/resense/status` and by `resense run --out`):
  `obstacle`, `warning`, `nearest_distance`, `detections[]` (id, zone, distance along track,
  lateral offset, centre, size, n_points, confidence, age, height_min, intensity), `track`
  (floor polynomial, axis centre/yaw/curvature, rail offset, quality flags), `timing_ms`.
  The ROS node adds a `node` object: `latency_ms` (decode + detect of this frame), `fps`,
  `frames`, `dropped_frames` (estimated from gaps in the input stamps), `input_period_ms`.
* Node runtime statistics (spec §8.3): `/resense/latency_ms` per frame (decode + detect +
  publish), `/resense/fps` and a log line with latency mean / p95 / max and dropped frames every
  `stats_period` seconds. The input subscription is best-effort with a queue of 5, so if a frame
  takes longer than the sensor period the following frames are dropped rather than queued: the
  node always works on the freshest data and the drop count makes overload visible.
* Ego speed for multi-frame accumulation: the node passes `Detector.process(frame, ego_speed=v)`
  the value of the `ego_speed_mps` parameter, else the latest `speed_topic` / `odom_topic`
  message younger than `speed_timeout`, else `None` (the detector estimates it itself); the
  status JSON reports `node.ego_speed_mps` and `node.ego_speed_source`.
* One fixed frame for every bag: the organizers' recordings carry different `frame_id`s
  (`hesai_lidar`, `lidar_livox`), so the node broadcasts a static identity transform
  `resense_lidar → <input frame_id>` when the first frame arrives and the RViz / Foxglove layouts
  use `resense_lidar` as their fixed frame.
* Verification without the dataset: `scripts/make_smoke_bag.py` writes a 40-frame synthetic bag in
  the organizers' exact layout (clear tunnel, then a person at 60 m), `scripts/smoke_test.sh`
  plays it through the node inside the Docker image and `scripts/check_dry_run.py` asserts the
  status stream; the CI docker job runs this on every push. The same checker scores the real
  dry run (`scripts/dry_run.sh`) on `doubleT_obstacle`.
* `resense inject` writes `*.npz` (xyz, intensity, per-point labels) + `gt.json`;
  `resense eval` consumes them and prints recall by range, FP rates, latency.

## Why this design

* **Environment prior instead of object classes** (spec §8.4): the tunnel is a corridor with
  rails; anything inside the clearance gauge that is not rails/bed/known hardware is a hazard,
  whatever it looks like. No labelled obstacle classes are needed.
* **Self-calibration**: bed level, rail level and track axis are re-estimated every frame from the
  rails, so different sensor mounts (the bags come from at least two) need no manual calibration.
* **Curvature from parallel references**: rails are visible only to ~30–40 m, walls/column rows
  to 150–200 m (Shen et al. 2024). This is what makes a corridor at 100+ m meaningful; where no
  boundary is observed the corridor is explicitly *not trusted* and only warnings are raised.
* **Range-adaptive everything**: voxel size, DBSCAN radius, minimum cluster size and the
  expected-point prior all scale with range, so a 5-point cluster at 150 m is treated as
  seriously as a 500-point cluster at 20 m.
* **Persistence before alarm**: three consecutive frames (0.3 s) suppress single-frame noise; the
  cost is 0.3 s of latency — at 80 km/h that is 6.7 m of travel.

## Real-time budget (4-core sandbox, Python)

| stage | mean | p95 |
|---|---|---|
| track model | ~15 ms | 25 ms |
| corridor mask | ~8 ms | 12 ms |
| voxel + DBSCAN + filters | ~15 ms | 40 ms |
| tracking | <1 ms | 1 ms |
| **total** | **40–75 ms** | **~120 ms** |

The frame period is 100 ms; on the test bench (i7-9700E, 8 cores) the pipeline runs in real
time with headroom for multi-frame accumulation.

## Known limitations of v0 (see EXPERIMENTS.md)

* Curvature is only observed where tunnel boundaries are visible; stations and switch caverns
  weaken the estimate → detections there are demoted to warnings but still noisy.
* Track hardware / infrastructure filters are hand-tuned on six bags; a 20–30 cm object lying
  on the rail is filtered out with the "low hardware" rule.
* No ego-motion estimate yet: the tracker uses a range-dependent gate with a 25 m/s slack.
* Single-frame evidence beyond ~150 m is 1–5 points; accumulation is required for 200–300 m.
