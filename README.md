# ReSense — LiDAR obstacle detection inside the metro clearance gauge

> ЛЦТ 2026 · Кейс 05 · «Обнаружение посторонних объектов в тоннеле метро по данным 3D-лидара»
> (Московский транспорт / ГУП «Московский метрополитен»). Organizers' materials: [`docs/organizers/`](docs/organizers/).

ReSense answers one question for a driverless metro train, 10 times a second:
**"Is there anything on my path that should not be there — and how far is it?"**

It builds a geometric model of the *normal* tunnel from the LiDAR stream (track bed, rail head,
track axis and its curvature from the tunnel walls), cuts out the corridor that the train's
clearance gauge sweeps, and reports every persistent cluster inside it with its distance along
the track, lateral offset, size and confidence. No labelled obstacle classes are required.

```
ROS 2 bag ─▶ PointCloud2 ─▶ resense_ros/detector_node ─▶ /resense/obstacle_detected (Bool)
                                                         ├▶ /resense/nearest_distance (Float32)
                                                         ├▶ /resense/detections (vision_msgs/Detection3DArray)
                                                         ├▶ /resense/markers (RViz)  ─▶ RViz2 / Foxglove / web/
                                                         └▶ /resense/status (JSON)
```

Status: **v0.5 (21.09, Sprint 2, measured on real data at full rate)**. On every frame of the
five obstacle-free organizer bags (2 287 frames: round / rectangular / double-track tunnels,
pressure gates, a platform stop, a switch) the detector raises **96 alarm frames / 32 alarm
events** (v0.3: 1 001 / 192) and runs at 43–55 ms per frame mean, 51–60 ms p95 on the tunnel
bags of a 4-core sandbox (v0.3: 56–71 / 71–76 ms). The person crossing the track in `doubleT_obstacle` is reported at
55.5–56.6 m in 66 of the 71 labelled in-gauge frames, the first alarm 0.5 s after he enters the
gauge, distance error under 1 cm, and nothing else alarms on that bag. Multi-frame accumulation
for 150 m and beyond runs with a given train speed (node parameter or odometry; synthetic:
person confirmed at 189 m); the LiDAR-only speed estimator is off by default. The container
chain (`docker build → run → bag play → result`) is verified in CI on a synthetic bag on every
push. Numbers, hard cases and what did not work: [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md).

![doubleT_obstacle frame 30: the person crossing the track is reported at 55.7 m (red box); the track axis (green) and the side structures (advisory, blue)](docs/img/doubleT_obstacle_0030_v05.png)
*Real data, v0.5: `doubleT_obstacle` frame 30, the person on the track at 55.7 m. Videos: [offline renders of the whole bag](docs/video/doubleT_obstacle_offline.mp4) (20 s) and [the dashboard replaying the same run](docs/video/dashboard_doubleT_obstacle.mp4).*

## Repository layout

| Path | What |
|---|---|
| [`resense/`](resense/) | core library (numpy / scipy / scikit-learn, no ROS): PointCloud2 decoding, track model, gauge corridor, clustering, tracking, detector, synthetic obstacle injection, metrics, CLI |
| [`ros2_ws/src/resense_ros/`](ros2_ws/src/resense_ros/) | ROS 2 Humble node, launch file, parameters, RViz layout |
| [`docker/`](docker/), [`docker-compose.yml`](docker-compose.yml), [`scripts/`](scripts/) | reproducible build and demo |
| [`configs/default.yaml`](configs/default.yaml) | every tunable parameter (also installed as the ROS parameter file) |
| [`tests/`](tests/) | pytest on a synthetic ray-cast tunnel — runs without the dataset |
| [`web/`](web/) | browser dashboard (live via rosbridge or offline replay of a `resense run` JSONL), Foxglove layout, label tool, headless checks |
| [`docs/`](docs/) | [ARCHITECTURE](docs/ARCHITECTURE.md) · [ALGORITHM](docs/ALGORITHM.md) · [EXPERIMENTS](docs/EXPERIMENTS.md) · [EVALUATION](docs/EVALUATION.md) · [DATASET](docs/DATASET.md) · [SENSOR](docs/SENSOR.md) · [RESEARCH](docs/RESEARCH.md) · [PLAN](docs/PLAN.md) · [CAPTAIN](docs/CAPTAIN.md) · [SUBMISSION](docs/SUBMISSION.md) · [PRESENTATION](docs/PRESENTATION.md) · [QUESTIONS](docs/QUESTIONS.md) · organizers' README / ТЗ · [test-stand software](docs/organizers/test_stand_software.md) · sensor manual ([`docs/sensor/`](docs/sensor/)) |

## Quick start (no ROS needed)

```bash
pip install -e ".[dev]"                       # numpy scipy scikit-learn pyyaml + rosbags matplotlib open3d pytest
pytest -q                                     # expect no skips: "skipped" means open3d is missing (RESENSE_REQUIRE_SYNTHETIC=1 makes that fail, as in CI)

# unpack the dataset (see docs/DATASET.md), then:
resense info  /data/for_hackathon/roundT_doubleT
resense run   --bag /data/for_hackathon/doubleT_obstacle --out results.jsonl --render out/   # PNG per frame
resense bench --bag /data/for_hackathon/roundT_doubleT --every 5                             # per-stage timing

# synthetic obstacles ray-cast into real empty frames + evaluation
resense inject --bag /data/for_hackathon/roundT_doubleT --every 10 --out data/synth --distances 10:250 --kinds person,box,plank
resense eval data/synth
```

## ROS 2 / Docker (the way the jury runs it)

```bash
./scripts/build.sh                                   # docker build -t resense -f docker/Dockerfile .
./scripts/run_demo.sh /data/for_hackathon/roundT_doubleT   # detector + RViz + bag playback in one container
./scripts/run_headless.sh /data/for_hackathon/doubleT_obstacle   # same, no X11: prints the distance
./scripts/dry_run.sh /data/for_hackathon/doubleT_obstacle        # acceptance test, exits non-zero on failure
WITH_TOOLS=1 ./scripts/build.sh                      # + rosbags / matplotlib / open3d / pytest inside the image
docker run --rm resense python3 -m pytest -q /opt/resense/tests   # the test suite inside the image (CI does this)

# or step by step
docker run --rm -it --net=host -v /data/for_hackathon:/data resense \
    ros2 launch resense_ros detector.launch.py            # terminal 1: detector
docker run --rm -it --net=host -v /data/for_hackathon:/data resense \
    ros2 bag play /data/roundT_doubleT --clock            # terminal 2: playback
ros2 topic echo /resense/nearest_distance                 # terminal 3 (any ROS 2 Humble host)
```

Launch arguments: `input_topic:=...` (comma-separated candidates, default
`/lidar_points,/sensing/lidar/hesai128/pointcloud`), `auto_discover:=true|false`,
`config_file:=/path/to/detector.yaml`, `rviz:=true|false`, `bag:=/data/<bag>`, `rate:=1.0`,
`loop:=true|false`, `delay:=3.0` (seconds the player waits before the first message, so that DDS
discovery completes: without it the first 1–3 s of a bag are lost), plus `publish_markers`,
`publish_corridor_cloud`, `marker_x_max`,
`output_frame`, `stats_period`, `discover_period`. For multi-frame accumulation the node needs
the train speed: `ego_speed_mps:=22.0`, or `speed_topic:=/vehicle/speed` (`std_msgs/Float32`,
m/s), or `odom_topic:=/odom` (`nav_msgs/Odometry`, `twist.linear.x`); with none of them the
detector uses its own estimate. `publish_tf:=true|false` and `tf_parent_frame:=resense_lidar`
control the static TF that lets one RViz / Foxglove layout serve every bag.

**The bags disagree on the topic name** — `roundT_doubleT` publishes `/lidar_points`,
`doubleT_obstacle` publishes `/sensing/lidar/hesai128/pointcloud` — so the node takes a list of
candidates and, unless `auto_discover:=false`, subscribes to any other `PointCloud2` topic that
appears on the graph. The first topic to deliver a frame wins and is logged; the others are
dropped. The control bag therefore needs no argument. `docker compose --profile viz up` starts
RViz and a Foxglove bridge (port 8765) next to the detector.

### Where the data lives

The bags are never copied into the image. **The directory that holds them is mounted at `/data`
inside the container**, and there is exactly one way to name it per entry point:

| entry point | how the directory is chosen |
|---|---|
| `scripts/run_demo.sh <bag>`, `run_headless.sh <bag>`, `dry_run.sh <bag>` | the parent of the bag path you pass |
| `docker compose` | `$RESENSE_DATA` (default `/data/for_hackathon`); `$RESENSE_BAG` picks the bag the `player` and `echo` services use |
| plain `docker run` | your own `-v <host dir>:/data:ro` |

```bash
RESENSE_DATA=/mnt/bags RESENSE_BAG=doubleT_obstacle docker compose --profile tools up
```

The organizers' download is a zip inside a zip around a 4 GB zstd tar; unpacking it by hand
needs ~30 GB of scratch space. `scripts/unpack_dataset.py` streams zip → zip → zstd → tar and
writes only the bags you ask for:

```bash
python scripts/unpack_dataset.py Датасет.zip --list
python scripts/unpack_dataset.py Датасет.zip --out /data --only doubleT_obstacle,roundT_doubleT
python scripts/unpack_dataset.py https://disk.yandex.ru/d/N8IUpAyd7jyvow --out /data   # extended dataset (17 GB, streamed from the link)
```

### Demo without a display

Every step of the jury scenario works over ssh, with no X11 and no RViz — the detector prints
`fps`, latency mean / p95 / max and dropped frames, and the distance readout comes from the topic:

```bash
./scripts/run_headless.sh /data/for_hackathon/doubleT_obstacle      # one container, prints "OBSTACLE 55.7 m"
docker compose up detector                                          # or: detector alone,
docker compose --profile tools up player                            #     bag in a second terminal,
docker compose --profile tools run --rm echo                        #     distance in a third
```

### Remote real-time demo (spec §4)

Two ways to show the chain tunnel → cloud → detection → distance to a jury that is not in the room:

1. **Screen share of RViz**: `./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle` on the
   demo machine and share the RViz window; for a continuous replay use the launch file directly
   with `loop:=true`:
   `docker run --rm -it --net=host -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v /data/for_hackathon:/data:ro resense ros2 launch resense_ros detector.launch.py bag:=/data/doubleT_obstacle loop:=true rviz:=true`.
2. **Foxglove over the network**, nothing graphical on the demo machine:
   ```bash
   docker compose --profile viz up detector foxglove                      # detector + foxglove_bridge :8765
   RESENSE_BAG=doubleT_obstacle docker compose --profile tools up player   # second terminal
   ```
   On any laptop open Foxglove (desktop app or app.foxglove.dev) → Open connection →
   `ws://<demo-host>:8765` (`ssh -L 8765:localhost:8765 <demo-host>` first if only ssh is open) →
   Layout → Import → [`web/foxglove_layout.json`](web/foxglove_layout.json): raw cloud, corridor
   points, boxes, status text and the distance / latency / fps plots. Details and limits in
   [`web/README.md`](web/README.md). Over a slow link switch the raw-cloud panel off and keep
   `/resense/corridor_points` (a few thousand points): the detections and the status text do not
   depend on it.

### Acceptance test (`scripts/dry_run.sh`)

The 28.09 dry run is a script, not a checklist. It builds the image with `--no-cache`, waits for
the node to advertise before playing the bag (the launch file's own `bag:=` races startup and
loses the first frames), captures `/resense/status` and checks it:

```bash
./scripts/dry_run.sh /data/for_hackathon/doubleT_obstacle
# == checking out/dry_run/status.jsonl ==
# status messages / alarm frames / obstacle distance / latency mean,p95,max / dropped frames / fps
# PASS: all dry-run criteria met

SKIP_BUILD=1 ./scripts/dry_run.sh /data/for_hackathon/roundT_doubleT --expect-clear   # false-alarm check
```

Defaults for `doubleT_obstacle`: the person is reported in 50–62 m, p95 of decode + detect is
≤ 100 ms (the 10 Hz frame period) and no input frame is dropped. Any argument after the bag path
is forwarded to `scripts/check_dry_run.py`, which holds the thresholds (`--expect-obstacle`,
`--expect-clear`, `--distance LO:HI`, `--first-clear N`, `--max-p95-latency`, `--max-dropped`,
...) and can also run on a capture someone else recorded. Raw output stays in `$OUT` (default
`out/dry_run/`): `status.jsonl` and `node.log`.

### Dataset-free smoke test (what CI runs)

The same procedure runs on every push without the dataset. `scripts/make_smoke_bag.py` writes a
40-frame bag of the synthetic tunnel (15 clear frames, then a person on the track at 60 m) in the
organizers' exact bag layout (sqlite3, `/lidar_points`, `hesai_lidar`, dual-return empty slots),
`scripts/smoke_test.sh` plays it through the node inside the image, and the checker asserts a
clear lead-in, the alarm at 55–66 m and no dropped frames:

```bash
WITH_TOOLS=1 ./scripts/build.sh                    # the generator needs open3d
docker run --rm resense:latest bash -lc "python3 scripts/make_smoke_bag.py /tmp/smoke_bag && scripts/smoke_test.sh /tmp/smoke_bag"
```

The image contains only what the node needs (pinned numpy / scipy / scikit-learn / pyyaml, ROS 2
packages, RViz, rosbag2, Foxglove bridge). `configs/default.yaml` is copied into the ROS package
at build time, so the node always runs the committed parameters; `./scripts/sync_params.sh`
keeps the in-repo copy identical (CI checks it).

### Topics published by the node

| topic | type | meaning |
|---|---|---|
| `/resense/obstacle_detected` | `std_msgs/Bool` | confirmed object inside the clearance gauge |
| `/resense/warning` | `std_msgs/Bool` | confirmed object in the advisory zone only |
| `/resense/nearest_distance` | `std_msgs/Float32` | m along the track to the nearest gauge obstacle, −1 if none |
| `/resense/detections` | `vision_msgs/Detection3DArray` | boxes in the sensor frame, `class_id` = `gauge_obstacle` / `warning_obstacle`, score = confidence |
| `/resense/status` | `std_msgs/String` | JSON: full per-frame result (detections, track model, per-stage timing) plus `node` = `{latency_ms, fps, frames, dropped_frames, input_period_ms, ego_speed_mps, ego_speed_source}` |
| `/resense/latency_ms` | `std_msgs/Float32` | per frame: decode + detect + publish, ms |
| `/resense/fps` | `std_msgs/Float32` | frames processed per second, every `stats_period` s (default 2) |
| `/resense/markers`, `/resense/corridor_points` | `MarkerArray`, `PointCloud2` | RViz: boxes, labels, corridor outline, status text; points inside the corridor |
| `/tf_static` | `tf2_msgs/TFMessage` | identity transform `resense_lidar` → the input cloud's `frame_id`, sent once per frame id: the layouts keep `resense_lidar` as the fixed frame whether the bag says `hesai_lidar` or `lidar_livox` |

Node parameters: `input_topic`, `auto_discover`, `discover_period`, `config_file`,
`publish_markers`, `publish_corridor_cloud`, `marker_x_max`, `output_frame`, `stats_period`,
`ego_speed_mps`, `speed_topic`, `odom_topic`, `speed_timeout`, `publish_tf`, `tf_parent_frame`
(all of them are launch arguments too). Every `stats_period` seconds the node logs
`fps`, latency mean / p95 / max, the measured input period and the number of frames the
input queue dropped (estimated from gaps in the header stamps).

## Parameters worth knowing (`configs/default.yaml`)

| key | default | meaning |
|---|---|---|
| `sensor.forward/left/up` | `-y/+x/+z` | sensor → vehicle axis mapping (hackathon Hesai frame) |
| `track.rails_*` | | rail-ridge template (gauge 1.52 m) for the track axis and rail-head level |
| `track.walls_*` | band 1.6–2.8 m | tunnel-boundary fit for yaw / curvature; `axis_valid_*` = how far the corridor is trusted |
| `gauge.profile` | ±1.4 m, 0.12/0.55–3.5 m | clearance-gauge polygon (dy, h above rail head); `warning_margin` = advisory zone |
| `cluster.eps / range_scale / voxel` | 0.35 / 40 / 0.05 | range-adaptive DBSCAN: ε(r) = eps·(1 + r/40 m) |
| `cluster.*_max_*` | | infrastructure filters (thin hardware, low hardware, wall-like, overhead) |
| `tracking.confirm_hits / conf_threshold` | 3 / 0.6 | persistence before an alarm |

## Documentation required by the organizers (spec §5, §7)

| requirement | where |
|---|---|
| project description | this README (top) |
| build the Docker image | "ROS 2 / Docker" above, `scripts/build.sh` |
| run, process a bag | "ROS 2 / Docker" (`run_demo.sh`, launch arguments), "Quick start" (offline `resense run`) |
| parameters and configuration | "Parameters worth knowing", [`docs/ALGORITHM.md`](docs/ALGORITHM.md) §5, `configs/default.yaml` |
| architecture (components, data flow) | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| algorithm (problem, data, processing, decision, parameters, limitations) | [`docs/ALGORITHM.md`](docs/ALGORITHM.md) |
| experiments (range, latency, FPS, false alarms, hard cases, evolution) | [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md), protocol in [`docs/EVALUATION.md`](docs/EVALUATION.md) |
| input data format, sensor | [`docs/DATASET.md`](docs/DATASET.md), [`docs/SENSOR.md`](docs/SENSOR.md) (Hesai Pandar128 specs and what they imply) |
| video | [`docs/video/doubleT_obstacle_offline.mp4`](docs/video/doubleT_obstacle_offline.mp4) (top-down and side renders of every frame of the real bag, v0.5) and [`docs/video/dashboard_doubleT_obstacle.mp4`](docs/video/dashboard_doubleT_obstacle.mp4) (the web dashboard replaying the same run); recipe in [`web/README.md`](web/README.md); the RViz screen recording on the jury chain is still to be made on a machine with Docker |
| submission status | [`docs/SUBMISSION.md`](docs/SUBMISSION.md) |

## Team

Four people, mapped onto the five roles the organizers suggest (system analyst, computer-vision
engineer, ROS 2 robotics developer, data specialist, C++/Python software developer):

| # | who | organizers' roles | owns |
|---|---|---|---|
| P1 | captain / lead | system analyst + ROS 2 robotics developer | requirements, architecture, ROS 2 node & Docker, evaluation protocol, submission, pitch lead |
| P2 | frontend | software developer (Python/JS tooling & UI) | RViz / Foxglove / web dashboard, label tool, video, presentation (mandatory slides 7–11) |
| P3 | member 3 | computer-vision engineer | track model, gauge corridor, clustering, tracking, long range, false-positive suppression, performance |
| P4 | member 4 | data specialist | dataset tooling, synthetic obstacles & augmentation, labelling, metrics, tests, CI |

Detailed plan and sprint calendar to the 29 September deadline: [`docs/PLAN.md`](docs/PLAN.md).
