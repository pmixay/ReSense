# Node parameters

Every node parameter is a launch argument of `resense_ros detector.launch.py`:

```bash
docker run --rm -it --net=host --ipc=host resense \
  ros2 launch resense_ros detector.launch.py freshness_mode:=replay auto_discover:=false input_topic:=/my/points
```

The defaults below are those of the launch file
([`detector.launch.py`](https://github.com/pmixay/ReSense/blob/main/ros2_ws/src/resense_ros/launch/detector.launch.py)).
Detector tuning is not a launch argument; it lives in the [configuration file](configuration.md).

## Input

| argument | default | meaning |
|---|---|---|
| `input_topic` | `/lidar_points,/sensing/lidar/hesai128/pointcloud` | comma-separated candidate input topics |
| `auto_discover` | `true` | also subscribe to `PointCloud2` topics found on the graph |
| `discover_period` | `2.0` | s between discovery scans while the input is silent |
| `input_switch_timeout` | `1.0` | s the active input must be silent before another topic is taken |
| `new_input_gap` | `30.0` | s of forward stamp jump taken as a new recording (detector restarted) |
| `hole_reset_gap` | `1.0` | s of forward stamp jump that resets the scene state (calibration kept) |
| `input_reliability` | `auto` | input QoS: `auto` matches the publishers, or `reliable`, `best_effort` |
| `input_queue_depth` | `40` | frames the subscription may hold between two processed frames |
| `catchup_step` | `0.3` | s of recording between processed frames while frames wait; `0` = newest only |
| `catchup_max_lag` | `5.0` | s: waiting frames older than the newest by more than this are dropped |
| `catchup_startup_max_lag` | `20.0` | s of backlog allowed for a new recording's first catch-up |

## Sensor mount

| argument | default | meaning |
|---|---|---|
| `sensor_forward`, `sensor_left`, `sensor_up` | empty (config file: `-y`, `+x`, `+z`) | which sensor axis points forward / left / up, e.g. `+x` |
| `mount_roll_deg`, `mount_pitch_deg`, `mount_yaw_deg` | `-999` (= config file) | a fixed tilt correction in degrees |
| `auto_calibrate` | `true` | find the orientation, roll and pitch from the rails and the bed in the first frames; reported in the status JSON under `mount` |

## Freshness and guards

| argument | default | meaning |
|---|---|---|
| `freshness_mode` | `live` | `live` = acquisition time vs system UTC; **`replay` for recorded bags** |
| `max_result_age` | `0.5` | s: maximum source age, Python residence and recording queue lag |
| `future_tolerance` | `0.05` | s of tolerated future clock skew |
| `stale_timeout` | `0.5` | s without an input frame before the decision becomes `FAULT` |
| `startup_grace` | `2.0` | s after start before "no LiDAR frame received yet" is published as `FAULT` |
| `max_consecutive_errors` | `5` | processing exceptions in a row before the detector is reset |

## Train speed (optional)

Without a speed the detector runs single-frame; with one it accumulates frames beyond 40 m.

| argument | default | meaning |
|---|---|---|
| `ego_speed_mps` | `-1.0` | a constant train speed in m/s; < 0 = unknown |
| `speed_topic` | empty | `std_msgs/Float32` topic with the speed in m/s |
| `odom_topic` | empty | `nav_msgs/Odometry` topic; `twist.linear.x` is taken as the speed |
| `speed_timeout` | `1.0` | s after which a speed message no longer counts |

## Output

| argument | default | meaning |
|---|---|---|
| `publish_markers` | `true` | RViz `MarkerArray` |
| `publish_corridor_cloud` | `true` | points inside the corridor |
| `marker_x_max` | `250.0` | m, how far the corridor outline is drawn |
| `output_frame` | empty | frame id of markers / detections; empty = the input's |
| `stats_period` | `2.0` | s between fps / latency statistics |
| `publish_tf` | `true` | broadcast a static identity transform `tf_parent_frame` → input frame |
| `tf_parent_frame` | `resense_lidar` | the fixed frame of the RViz / Foxglove layouts |

## Launch-file only

| argument | default | meaning |
|---|---|---|
| `config_file` | the package's `config/detector.yaml` | the detector parameter file |
| `rviz` | `false` | also start RViz with the ReSense layout |
| `bag` | empty | a bag to play from the launch file |
| `rate` | `1.0` | its playback rate |
| `loop` | `false` | replay the bag forever |
| `delay` | `3.0` | s before the player starts, so discovery completes |

Playing from the launch file races the node's startup; the scripts start the node first and wait
for `/resense/status` before playing.

## Environment variables of the image

| variable | meaning |
|---|---|
| `RESENSE_NATIVE=0` | use the numpy path instead of the C++ kernels (same output, slower) |
| `RESENSE_DDS=shm` | opt-in: add shared-memory transport (with `--ipc=host`) so a stock Fast DDS player on the host delivers clouds through `/dev/shm` |
| `ROS_DOMAIN_ID` | must match the player's (default 0) |
