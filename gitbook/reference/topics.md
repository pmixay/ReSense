# Topics and status JSON

## Published topics

| topic | type | meaning |
|---|---|---|
| `/resense/decision` | `std_msgs/String` | `GO` / `CAUTION` / `STOP` / `FAULT` ([Read the output](../getting-started/read-the-output.md)) |
| `/resense/obstacle_detected` | `std_msgs/Bool` | a confirmed object inside the clearance envelope |
| `/resense/warning` | `std_msgs/Bool` | a confirmed object in the advisory zone only |
| `/resense/nearest_distance` | `std_msgs/Float32` | m along the track to the nearest envelope obstacle, −1 if none |
| `/resense/clear_distance` | `std_msgs/Float32` | estimated monitored range in m, capped at detected obstacles and eligible clusters; 0 on a fault |
| `/resense/health` | `diagnostic_msgs/DiagnosticArray` | OK / WARN / ERROR / STALE with messages and values: points, window dirt, blocked sectors, visibility, rail lock, latency p95, monitored range, mount calibration |
| `/resense/detections` | `vision_msgs/Detection3DArray` | boxes in the sensor frame; `class_id` = `gauge_obstacle` / `warning_obstacle`, score = confidence |
| `/resense/status` | `std_msgs/String` | the full per-frame result as JSON (below) |
| `/resense/latency_ms`, `/resense/fps` | `std_msgs/Float32` | decode + detect + publish time per frame; frames per second every `stats_period` s |
| `/resense/markers`, `/resense/corridor_points` | `visualization_msgs/MarkerArray`, `sensor_msgs/PointCloud2` | for RViz / Foxglove: boxes, labels, corridor outline, status text; points inside the corridor |
| `/tf_static` | `tf2_msgs/TFMessage` | identity `resense_lidar` → the input cloud's frame id |

## Subscribed

* `sensor_msgs/PointCloud2` on `input_topic` (both known names by default) and, with
  `auto_discover`, any other `PointCloud2` topic on the graph; one input is processed at a time.
* Optional speed: `speed_topic` (`std_msgs/Float32`) or `odom_topic` (`nav_msgs/Odometry`).

## The status JSON

One object per processed frame (and per watchdog tick when the input is silent). The same object,
without `node`, is what `resense run --out` writes per line.

| key | content |
|---|---|
| `stamp` | the frame's time, s |
| `decision` | `GO` / `CAUTION` / `STOP` / `FAULT` |
| `obstacle`, `warning` | booleans as on the topics |
| `nearest_distance` | m to the nearest envelope obstacle, `null` if none |
| `clear_distance`, `detector_clear_distance` | the published monitored range (0 when monitoring is invalid) and the detector's raw estimate |
| `detections[]`, `warnings[]` | envelope obstacles and advisory objects: `id`, `zone`, `distance` (along the track), `lateral`, `center` [x, y, z], `size` (extents along x, y, z), `n_points`, `confidence`, `age` (frames), `height_min`, `intensity`, `reason`, `kind` |
| `track` | the track model: `center`, `yaw`, `curvature`, `axis_valid` (trusted range), `floor_coef`, `floor_range`, `rail_offset`, `rail_score`, `wall_quality`, … |
| `health` | `level`, `decision_level`, `messages[]`, `points`, `visibility`, `blocked_sectors`, `rail_lock`, `monitored_range`, `latency_p95_ms`, freshness fields, … |
| `mount` | the auto-calibration: `status`, `orientation`, `roll_deg`, `pitch_deg`, `yaw_deg`, `height`, `lateral`, `drift_deg`, `frames_used`, `message` |
| `timing_ms` | per stage: `track`, `corridor`, `egomotion`, `accumulate`, `cluster`, `tracking`, `total` |
| `freshness` | `mode`, `clock_reference`, `valid`, `reason`, `go_allowed`, the ages (`source_age_s`, `acquisition_age_s`, `publication_age_s`, `residence_age_s`, `queue_lag_s`), `evaluated_at_utc_s`, `max_result_age_s`, `future_tolerance_s` |
| `stop_held` | a previous STOP kept visible through invalid input |
| `snapshot_kind` | `frame`, `watchdog` or `processing_error` |
| `ego_speed`, `ego_speed_source`, `ego_speed_estimate`, `ego_speed_confidence`, `n_accumulated` | the speed used, if any, and the accumulation |
| `n_points`, `n_corridor`, `n_candidates` | points in the frame, in the corridor, candidate clusters |
| `node` | added by the node: `latency_ms`, `fps`, `frames`, `dropped_frames`, `catchup_skipped`, `catchup`, `input_period_ms`, `ego_speed_mps`, `ego_speed_source`, `input_topic`, `recording` |

The producer is `FrameResult.to_dict()` in
[`resense/detector.py`](https://github.com/pmixay/ReSense/blob/main/resense/detector.py); keys are
only ever added, never renamed or removed.

## Coordinate frames

The detector works in a vehicle frame: X forward along the track, Y left, Z up, origin at the
sensor. `distance` is measured along the track axis, `lateral` across it. Published boxes and
markers are in the input cloud's frame (or `output_frame`).
