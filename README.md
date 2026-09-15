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
ROS 2 bag ─▶ /lidar_points ─▶ resense_ros/detector_node ─▶ /resense/obstacle_detected (Bool)
                                                         ├▶ /resense/nearest_distance (Float32)
                                                         ├▶ /resense/detections (vision_msgs/Detection3DArray)
                                                         ├▶ /resense/markers (RViz)  ─▶ RViz2 / Foxglove / web/
                                                         └▶ /resense/status (JSON)
```

Status: **v0 prototype (day 1)**. Works on the six organizer bags (round / rectangular /
double-track tunnels, pressure gates, platform, switch), detects the real person on the track at
55 m in `doubleT_obstacle` and ray-cast synthetic obstacles at 30 / 80 / 150 m; runs at 40–75 ms
per frame in pure Python. Known false-positive sources and next steps: [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md).

## Repository layout

| Path | What |
|---|---|
| [`resense/`](resense/) | core library (numpy / scipy / scikit-learn, no ROS): PointCloud2 decoding, track model, gauge corridor, clustering, tracking, detector, synthetic obstacle injection, metrics, CLI |
| [`ros2_ws/src/resense_ros/`](ros2_ws/src/resense_ros/) | ROS 2 Humble node, launch file, parameters, RViz layout |
| [`docker/`](docker/), [`docker-compose.yml`](docker-compose.yml), [`scripts/`](scripts/) | reproducible build and demo |
| [`configs/default.yaml`](configs/default.yaml) | every tunable parameter (also installed as the ROS parameter file) |
| [`tests/`](tests/) | pytest on a synthetic ray-cast tunnel — runs without the dataset |
| [`web/`](web/) | browser dashboard scaffold (frontend track) |
| [`docs/`](docs/) | [PLAN](docs/PLAN.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) · [DATASET](docs/DATASET.md) · [RESEARCH](docs/RESEARCH.md) · [EXPERIMENTS](docs/EXPERIMENTS.md) · [PRESENTATION](docs/PRESENTATION.md) · organizers' README / ТЗ |

## Quick start (no ROS needed)

```bash
pip install -e ".[dev]"                       # numpy scipy scikit-learn pyyaml + rosbags matplotlib open3d pytest
pytest -q                                     # 15 tests on a synthetic tunnel

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

# or step by step
docker run --rm -it --net=host -v /data/for_hackathon:/data resense \
    ros2 launch resense_ros detector.launch.py            # terminal 1: detector
docker run --rm -it --net=host -v /data/for_hackathon:/data resense \
    ros2 bag play /data/roundT_doubleT --clock            # terminal 2: playback
ros2 topic echo /resense/nearest_distance                 # terminal 3 (any ROS 2 Humble host)
```

Launch arguments: `input_topic:=/lidar_points`, `config_file:=/path/to/detector.yaml`,
`rviz:=true|false`, `bag:=/data/<bag>`, `rate:=1.0`. `docker compose --profile viz up` starts
RViz and a Foxglove bridge (port 8765) next to the detector.

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

## Team

Four people — captain/lead (architecture, ROS 2, Docker, submission), frontend (visualisation,
dashboard, video, presentation), algorithms (track model, corridor, tracking, long range),
data & evaluation (synthetic obstacles, metrics, tests). Detailed plan and sprint calendar to the
29 September deadline: [`docs/PLAN.md`](docs/PLAN.md).
