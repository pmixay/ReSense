# N1/N4: gauge display and interactive multi-bag playback

The node draws the configured 2.1 m gauge width, 0.12–3.0 m above the fitted rail head, as four longitudinal edges with closed end rings. Stable marker identities avoid clearing/recreating the whole scene every frame. The same centerline and range are published in `status.gauge` and consumed by the web cab view.

The box describes supported rail geometry. `clear_distance` separately describes the selected obstacle/range policy; a STOP can therefore retain its supported box. Solid range never exceeds `min(track.axis_valid, health.monitored_range, marker_max_range)`. Smoothing is display-only: 9 m travel-distance decay with 1.6 s stationary settling, or an explicit 0.8 s temporal fallback when speed is unavailable. New range must persist for two frames and grows at most 5 m per frame; loss of support shrinks it immediately. The displayed 3D centerline must stay within 0.25 m of the current fitted axis/rail height; disagreement shortens the box. This causes a measured coverage loss and does not constitute better detector accuracy.

Invalid input holds a grey outline for at most three missing updates, with `solid_range_m=0`; frame/watchdog updates also expire it once its age reaches 0.5 s. RViz markers have a separate 0.5 s lifetime from receipt (grey holds use their remaining budget), so a blocked node executor cannot leave an indefinite green outline. Refresh below 2 Hz can produce gaps, an intentional freshness limit. The web live-input guard also removes expired geometry. The next valid fit seeds new display state. `gauge.valid`, `held`, `reason`, `drawn_range_m`, `solid_range_m`, `axis_valid_m`, 3D/lateral/vertical lag, and `centerline` expose these distinctions. No detector model, detection, warning or decision is fed back from the display.

## Play two bags through one node

On this development machine, the independently verified selected-default image is
`resense:lidar-cecab1b`; use that value for `IMAGE` to run the measured revision.
[Its acceptance record](../lidar_adaptation_2026-10-18/default_off/README.md) identifies
the exact image and source. No image was published as a new release.

Use the validated image on this machine:

```bash
IMAGE=resense:lidar-cecab1b scripts/play_bag.sh --interactive --rate 0.5 \
  --clear-range-policy conservative \
  --sensor-profile pandar128 /data/PANDAR_BAG \
  --sensor-profile falcon_ros /data/FALCON_ROS_BAG
```

On another machine, build this source checkout and substitute the local image tag.

`--sensor-profile` applies to bags that follow it. `manual` preserves explicitly configured axes, `pandar128` selects -Y/+X/+Z, `falcon_ros` selects +X/+Y/+Z for the supplied `/iv_points` recording, and `falcon_native` selects +Z/-Y/+X for native sensor coordinates. Named profiles reset fixed mount angles, calibration prior and range model. The Falcon recording must use `falcon_ros`; a topic name alone does not identify coordinates. The conservative range profile remains explicit; Falcon has no calibrated Pandar small-object density prior, so its `monitored_small` is null and conservative `clear_distance` is zero.

The initial candidate topic list includes `/lidar_points`, `/sensing/lidar/hesai128/pointcloud`, and `/iv_points`. Subscribing to known topics before playback avoids the initial frames lost while waiting for periodic discovery. Unknown PointCloud2 topics still use discovery; explicitly configure a new topic before playback when complete startup capture matters. Topic subscription never selects a coordinate or range profile.

Space pauses/resumes, Right steps one message while paused, and Up/Down changes the native rosbag2 playback rate. `--interactive` requires a terminal and attaches Docker with `-it`; omit it for unattended batch playback. The initial rate applies independently to every bag. The wrapper prints the node container name for a second console and leaves that node running across all supplied bags.

Between players the wrapper waits for input silence, atomically selects the next profile, and calls `/resense/reset_input`. This flushes subscriptions/pending callbacks, freshness epochs, detector/tracker/calibration/display state, speed and prior STOP latch. The first new frame must confirm its own epoch. Profile changes or reset requests while input is still active/pending are rejected; stop the player first. The reset service is an explicit recording boundary, not a way to suppress a live obstacle alarm.

## Graphics

```bash
IMAGE=resense:lidar-cecab1b scripts/run_demo.sh --interactive --rate 0.5 \
  --sensor-profile pandar128 /data/PANDAR_BAG
# Software OpenGL fallback, including headless review:
IMAGE=resense:lidar-cecab1b xvfb-run -a scripts/run_demo.sh --software-rendering \
  --rate 0.5 --sensor-profile pandar128 /data/PANDAR_BAG
```

X11 socket and the caller's XAUTHORITY are passed to the container; no global `xhost +` is used. `LIBGL_ALWAYS_SOFTWARE=1` also selects software rendering through `run_demo.sh`. Input/result freshness remains enforced during pause, slow rendering and backlog; a stale view cannot remain green. This 1-vCPU host's simultaneous software RViz and quality jobs produced source-stale FAULT frames, so those screenshots are graphics evidence rather than a throughput claim.

## Reproduce checks

```bash
python scripts/make_profile_smoke_bags.py /tmp/profile-bags
# Actual DDS + native keyboard controls, one node and two distinct sensor profiles:
docker run --rm --net=host --ipc=host \
  -v /tmp/profile-bags:/bags:ro -v /tmp/profile-check:/out \
  resense:lidar-cecab1b python3 scripts/check_interactive_replay.py /bags --out /out
# Add -v /path/to/actual-falcon-bag:/falcon:ro to the same Docker command,
# then --falcon-bag /falcon to exercise the actual second recording.
# The harness requires every PointCloud2 message counted in each bag's metadata.
# Local overlay when the runtime image predates the current working-tree source:
docker build -f docs/evidence/n1_n4_2026-10-18/Dockerfile.check -t resense:n1n4-check .
# Full decoded-frame quality replay; NOT a ROS latency/throughput measurement:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_CORETYPE=Haswell \
  python docs/evidence/n1_n4_2026-10-18/replay_gauge.py \
  --reports /tmp/gauge-reports --rows /tmp/gauge-rows \
  cloud_with_fake_obj doubleT_obstacle roundT_doubleT doubleT_platform
```

The CI wrapper check now plays two bags through one node, followed by the real PTY/profile integration harness. These changes are locally testable; hosted GitHub CI remains a separate deferred issue.

RViz lifetime semantics were checked against the [ROS2 Humble MarkerBase implementation](https://github.com/ros2/rviz/blob/humble/rviz_default_plugins/src/rviz_default_plugins/displays/marker/markers/marker_base.cpp): each received update establishes an expiry on the RViz clock, and later rendering updates remove expired markers. The supplied launch uses the normal advancing clock; a paused simulation clock is outside this check.
