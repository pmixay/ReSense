# Configuration file

All detector tuning lives in one file,
[`configs/default.yaml`](https://github.com/pmixay/ReSense/blob/main/configs/default.yaml), under
the root key `resense:`. The CLI and the ROS node load the same file; the ROS package carries a
copy (`ros2_ws/src/resense_ros/config/detector.yaml`) that must stay identical.

| section | what it controls |
|---|---|
| `sensor` | axis mapping (`forward: -y`, `left: +x`, `up: +z` for the organizers' mount), range crop, a fixed mount tilt |
| `track` | the track model: bed profile, rail-pair template (gauge 1.52 m), wall fit for yaw and curvature, how far the axis is trusted |
| `gauge` | the envelope: `profile` (the organizers' 2.1 × 3.0 m, i.e. \|dy\| ≤ 1.05 m, 0.12–3.0 m above the rail head), `warning_margin` (0.35 m advisory zone), range |
| `cluster` | range-adaptive DBSCAN (`eps`, `range_scale`, `voxel`) and the infrastructure filters and signatures |
| `tracking` | persistence before an alarm (`confirm_time_s`, `confirm_hits`, `conf_threshold`), holds and the learned track opinion |
| `accumulation` | multi-frame accumulation, only with a known train speed |
| `lowobj` | low objects on the rails |
| `calibration` | the mount auto-calibration |
| `health` | input guards and the monitored-range estimate; they never change a detection |

Every key has a comment in the file with its date and the measurement that decided it. The
parameters that matter most and their effect:
[`docs/ALGORITHM.md` §5](https://github.com/pmixay/ReSense/blob/main/docs/ALGORITHM.md#5-parameters-that-matter-most).

## Use another file

A file you pass is applied on top of the **code defaults** in `resense/config.py`, not on top of
`configs/default.yaml`, and an unknown key is an error. So start from a full copy:

```bash
cp configs/default.yaml my.yaml        # edit my.yaml

resense run --bag <bag> --config my.yaml --out results.jsonl          # offline

docker run --rm -it --net=host --ipc=host -v $PWD/my.yaml:/cfg/my.yaml:ro resense \
  ros2 launch resense_ros detector.launch.py freshness_mode:=replay config_file:=/cfg/my.yaml   # the node
```

The mount can also be set per run without a file: the node's `sensor_forward` / `sensor_left` /
`sensor_up` and `mount_*_deg` launch arguments ([Node parameters](node-parameters.md)).

## Change the defaults (developers)

1. Edit `configs/default.yaml`.
2. `./scripts/sync_params.sh` copies it into the ROS package (`--check` is what CI runs).
3. A change that affects detection goes through the regression gate and a new detector seal:
   [Changing the detector](../development/detector-changes.md).
