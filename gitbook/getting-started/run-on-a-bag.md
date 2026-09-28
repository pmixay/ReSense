# Run on a bag

ReSense never opens bag files itself on the ROS path: the node subscribes to the point clouds that
`ros2 bag play` publishes, exactly as it would to a live LiDAR driver.

```text
ros2 bag play <bag>  ──PointCloud2, 10 Hz──▶  resense_detector node (docker run --net=host … resense)
                                                ├─▶ /resense/decision        GO / CAUTION / STOP / FAULT
                                                ├─▶ /resense/nearest_distance, /resense/obstacle_detected
                                                ├─▶ /resense/clear_distance, /resense/health
                                                └─▶ /resense/detections, /resense/status (JSON), RViz markers
```

## One command

Needs only Docker and the image (loaded, or pass the archive):

```bash
scripts/play_bag.sh <bag directory>
scripts/play_bag.sh <bag directory> --archive resense-image-<version>.tar.gz
```

It raises the UDP buffer if it can, loads the archive, starts the node, starts a listener, plays the
bag as the calling user from the same image and prints every change of the decision:

```text
== doubleT_obstacle: playing as uid:gid 1000:1000; decision changes (time since start, decision, nearest distance):
    2.1 s  FAULT   -
    5.3 s  GO      -
    6.9 s  STOP    55.6 m
   ...
== doubleT_obstacle played; node stopped
```

(Timings in the example are illustrative.) Exit code 2 means a bad argument, 3 means no Docker,
no image or a node that did not start.

## Step by step (the organizers' console)

Three consoles on the same machine.

**0. Once per boot** — the UDP receive buffer for 360° clouds (needed with a CycloneDDS player,
harmless otherwise):

```bash
sudo sysctl -w net.core.rmem_max=33554432
```

**1. The node** (console 1):

```bash
docker run --rm -it --net=host --ipc=host resense \
  ros2 launch resense_ros detector.launch.py freshness_mode:=replay
```

* `--net=host` is required: the image runs DDS over UDP only; in Docker's bridge network the
  player and the node never discover each other.
* `freshness_mode:=replay` is required for recorded bags; the default `live` mode compares frame
  stamps with the system clock.

**2. The player** (console 2, any user, ROS 2 Humble on the host):

```bash
ros2 bag play <bag> --delay 3 --read-ahead-queue-size 10
```

Without ROS 2 on the host, use the player in the image:

```bash
docker run --rm --net=host -v <folder with bags>:/data:ro resense \
  ros2 bag play /data/<bag> --delay 3 --read-ahead-queue-size 10
```

* `--delay 3` lets DDS discovery complete before the first cloud.
* `--read-ahead-queue-size 10` is the supported playback mode. Humble's default (1 000 messages)
  preloads a short recording while its clock runs and then sends the overdue start in one burst;
  the first seconds of output are then stale.
* The player and the node must use the same `ROS_DOMAIN_ID` (default 0).

**3. The answer** (console 3):

```bash
ros2 topic echo /resense/decision --field data          # GO | CAUTION | STOP | FAULT
ros2 topic echo /resense/nearest_distance --field data  # m along the track, −1 = none
```

What the values mean: [Read the output](read-the-output.md).

## Several bags into one node

The node listens to both known topic / frame pairs (`/lidar_points` in `hesai_lidar`,
`/sensing/lidar/hesai128/pointcloud` in `lidar_livox`) and, unless `auto_discover:=false`, to any
other `PointCloud2` topic. A new recording (another topic or frame id, or stamps that jump by more
than `new_input_gap`, 30 s) gets a fresh detector, so bags can be played one after another into one
running node without restarting it.

## With docker compose

The bags' folder is `$RESENSE_DATA` (default `/data/for_hackathon`), the bag inside it
`$RESENSE_BAG`:

```bash
docker compose up detector                        # the node, headless
docker compose --profile tools up player          # plays $RESENSE_BAG into it
docker compose --profile tools run --rm echo      # prints /resense/decision
RESENSE_DATA=/mnt/bags RESENSE_BAG=doubleT_obstacle docker compose --profile tools up
```

With `resense:latest` already loaded, compose never builds or pulls; do not pass `--build` on a
machine without internet.

## Other wrappers

```bash
./scripts/run_demo.sh /data/for_hackathon/roundT_doubleT         # node + RViz + playback in one container (X11)
./scripts/run_headless.sh /data/for_hackathon/doubleT_obstacle   # the same without X11, prints "OBSTACLE 55.7 m"
```
