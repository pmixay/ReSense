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

**For the jury: build, run, play, read** (details: "ROS 2 / Docker" and "What to look at" below)

```bash
docker build -t resense -f docker/Dockerfile .              # once; needs the network for apt / pip
docker run --rm -it --net=host --ipc=host resense           # console 1: the node (the image's default command)
ros2 bag play <control bag> --delay 3                       # console 2: any console on the same ROS 2 network
ros2 topic echo /resense/decision --field data              # console 3: GO | CAUTION | STOP | FAULT
ros2 topic echo /resense/nearest_distance                   # distance along the track to the nearest obstacle, m
```

Expected on the organizers' `doubleT_obstacle`: `STOP` at 55.5–56.6 m (the person crossing, then
the object lying across the rail). No ROS on the host: play from a second container,
`docker run --rm --net=host --ipc=host -v <bag dir>:/data:ro resense ros2 bag play /data/<bag> --delay 3`.
Worth knowing: `ros2 bag play` (Humble) reads up to 1000 messages — all of a short recording —
before its first publish while its clock runs, then sends the overdue first seconds back to back;
the decision is `FAULT` (no input) until then (2.6–4 s for a 1.9 GB recording already in the page
cache, longer from a slow disk). The node then works through that burst from the recording's first
frame, one frame every 0.3 s of recording (`catchup_step`), and is back in real time within ~2 s:
on `doubleT_obstacle` the first `STOP` comes 1.3–1.6 s into the recording, as offline (v0.6.4,
EXPERIMENTS.md §3b; before it the first 2–5 s were lost). `STOP` is the alarm; `CAUTION` is advisory — something next to
the envelope or beyond the verified range (columns, platform edges, far clusters) — and is common
in a normal tunnel. `/resense/obstacle_detected` answers for the last processed frame; the
go / no-go signal is `/resense/decision`, which also says `FAULT` when no frame is arriving.

Status: **v0.6.4 (24.09)** — the detector of v0.6.3; the ROS node now works through the burst of
the first seconds that `ros2 bag play` sends after preloading a bag instead of losing them (first
`STOP` on `doubleT_obstacle` 1.3–1.6 s into the recording through ROS, was 3.2–4.5 s). Before it:
v0.6.1 rebuilt the detector around the organizers' Q&A answers;
v0.6.2 finds the organizers' object lying across a rail and cuts the false stops on the ride by 43 %
after an independent criteria review; v0.6.3, after a second one, holds a STOP over a single missed
frame (25 % fewer on/off episodes), keeps a person lying across the track and makes the first
20 s of a recording 10–15 ms per frame faster. The current judgement against the organizers'
criteria is an independent review of 24.09: [`docs/SCORECARD.md`](docs/SCORECARD.md). What v0.6.1
(22.09) changed after the Q&A session ([`docs/organizers/QA_session.md`](docs/organizers/QA_session.md):
the recorded session, transcribed and summarised): The strict decision now uses **the train envelope the organizers
gave (2.1 m wide × 3.0 m high)**; objects **hanging** into it (broken cables) are obstacles
whatever their shape; **low objects lying on a rail** are found by a bed-anomaly stage (v0.6.2:
also when they straddle the envelope floor, like the organizers' object); tall
objects are reported out to the trusted axis range (~200 m on straight track) instead of the
height-reference range; the **LiDAR mount is found from the data** (orientation, roll, pitch)
because "the LiDAR position is not fixed"; and every frame says **how far the path was
verified clear** and whether the input can be trusted (`/resense/decision`
GO / CAUTION / STOP / FAULT, `/resense/clear_distance`, `/resense/health`).

Measured on **all 13 759 real frames** of the organizers' data at 10 Hz
([`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) §0; v0.6.3, re-run on the current code on 24.09 with
identical output on every frame): false alarms on the five obstacle-free
bags **20 events** (107 alarm frames, 27 STOP episodes; v0.6.1: 30 events, v0.5 logic: 32) and on
the 20-minute, 13 km ride **47 events, 3.6 per km** (204 frames, 39 episodes; v0.6.1: 82, v0.5:
93); v0.6.2 had fewer events than v0.6.1 in 12 of 13 subsets of the data and more in none, so
the gain is not carried by one recording (leave-one-out check, §0), and starting the recordings
0–40 frames later, as a played bag does through ROS, gives 14–20 events (§0); a health warning on 1.4 % of the frames (stations,
switches); the person crossing the track in `doubleT_obstacle` is reported in 58 of the 61
frames in which the person is inside the envelope, the first alarm 0.3 s after entering it,
distance error ≤ 0.23 m; the **object lying across the rail** (0.45 × 0.6 × 0.3 m) in **124 of
the 126 frames** after the person leaves it (v0.6.1: 2). Long range on the
moving ride (**synthetic objects with legacy detector-derived placement** ray-cast into consecutive real frames, no speed input, §2d round 3: the current code, 24.09): a
person on straight track is **held from 115 m inward** (median of 6 approaches, per approach
20–160 m: detected in ≥ 90 % of the frames of every 10 m band from there; in ≥ 90 % of all
frames from 149 m) and first confirmed at 148 m median (110–169 m, 6 of 6); a trolley first at
144 m, a 1 m crate at 111 m, a 3 cm hanging cable first at 95 m but held only from ~50 m (4 of
6); with a train speed given (odometry or a speed topic: 5-frame accumulation) the person first
at **167 m**, the crate at 182 m — reach bought with steadiness: the crate is then held only
from 79 m instead of 119 m and the person's 50–100 m recall drops from 94 to 83 %; in R ≈ 350 m curves 6 of 7 approaches
are detected, from 58–86 m (the sightline past the inner wall); at station stops a person 6 of
6 from 113 m; 30 cm objects lying on a rail head 6 of 6 from 42–49 m; a person lying across the
rails 6 of 6 from ~64 m (between the rails: where the body rises above the rail head, §2d). 300 m is beyond this
sensor: no return in any of the 13 759 frames lies beyond 210 m (every recording stops at 209.2–210.0 m). Other LiDAR mounts (upside down, `+x` forward, backwards, rolled /
pitched) are recovered from the rails and the bed: orientation found and tilt within 0.5° on
re-mounted real frames of three recordings (§6). Clean timing: 42–64 ms mean, p95 53–78 ms per
frame on every recording (4-core sandbox, pure Python, §3; the node adds ~20–25 ms at 360°).
The long-range figures above are from an earlier synthetic set F, which placed each object
using that frame's estimated axis; this can flatter curve and envelope-edge results. A P4
paired rerun on seven organizer curve/edge scenes with the current code found **0 matches
beyond 100 m** in the six usable sequences of either mode and skipped one sequence after a
recording gap. Near anchoring used the real ride's rail fits and estimated speed, **not surveyed
ground truth**, so neither result establishes real-positive long-range recall. See
[`docs/P4_AUDIT.md`](docs/P4_AUDIT.md) and the paired counts there.
The same audit reran set S on 108 real empty backgrounds: corrected bed placement matched
22/67 visible in-gauge synthetic objects, versus 29/68 with the old, higher placement.
Those small samples are not an operational recall estimate.
The container chain (`docker build → run → bag play → result`) is verified in CI on synthetic
bags on every push, and was rehearsed on 23.09 on the real frames in Docker — the node in one
container, `ros2 bag play` in another, both topic / frame pairs, two recordings into one node
(EXPERIMENTS.md §3b: the 120° recording at 10 fps, p95 76 ms; the 360° one at 7–10 fps in steady
state on the 4-vCPU sandbox; since v0.6.4 the burst of the player's first seconds is worked through, not lost; the node container
at ~100 % of one core while frames arrive, 186 MB). The bag may be played by any user: the image
runs DDS over UDP (a normal user's player cannot write into a root node's shared memory). Judgement against every criterion and what is left (independent review, 24.09): [`docs/SCORECARD.md`](docs/SCORECARD.md).

![doubleT_obstacle frame 24 seen from the cab: the train envelope (green) swept along the track axis, the points inside it (yellow), the person on the track reported at 55.8 m (STOP) and a close-up of the person's points](docs/img/hero_person.png)
*Real data, v0.6.2: `doubleT_obstacle` frame 24 from the driver's seat (`scripts/hero_view.py`), the person on the track at 55.8 m. Videos: [the jury chain in Docker with RViz](docs/video/docker_chain_rviz.mp4), [the whole bag from the cab](docs/video/doubleT_obstacle_cab.mp4), [offline renders, top and side view](docs/video/doubleT_obstacle_offline.mp4) and [the dashboard replaying the same run](docs/video/dashboard_doubleT_obstacle.mp4). Slides in the organizers' template: [`docs/presentation/ReSense_LCT2026.pptx`](docs/presentation/ReSense_LCT2026.pptx).*

### Dashboard UI

![ReSense dashboard showing a STOP decision, the cab view with the confirmed obstacle, health data, top-down view, timeline and run summary](docs/images/dashboard-stop.png)

The browser dashboard also has dedicated [GO](docs/images/dashboard-clear.png) and
[CAUTION](docs/images/dashboard-caution.png) states. These three captures use the built-in
synthetic UI demo so anyone can reproduce them without ROS or a dataset; they are interface
examples, not evaluation evidence. Its cab view on the node's real `doubleT_obstacle` stream:
[`dashboard-cab-real.png`](docs/images/dashboard-cab-real.png). See the complete [`docs/images` gallery](docs/images/README.md).

## What to look at (for the jury)

The organizers asked that every team "say clearly what to look at". One line per question:

| question | topic | values |
|---|---|---|
| can the train go? | **`/resense/decision`** (`std_msgs/String`) | `GO` (clear), `CAUTION` (advisory: a confirmed object in the band just outside the envelope, a far cluster beyond the verified range, known infrastructure, or degraded health — on 27–68 % of the frames of the obstacle-free recordings and 41 % of the ride, so it is not an alarm), `STOP` (obstacle inside the 2.1 × 3.0 m envelope), `FAULT` (input cannot be trusted or stopped arriving, and before the first frame) |
| is there an obstacle? | **`/resense/obstacle_detected`** (`std_msgs/Bool`) | per processed frame, confirmed over 0.5 s, held over one missed frame; `false` while no frame arrives (then `decision` says `FAULT`) |
| how far is it? | **`/resense/nearest_distance`** (`std_msgs/Float32`) | m along the track, −1 if none |
| how far is the path verified clear? | **`/resense/clear_distance`** (`std_msgs/Float32`) | the obstacle distance, else how far the corridor was actually checked (sightline, trusted track model); 0 on a fault |
| everything else | `/resense/detections` (`vision_msgs/Detection3DArray`), `/resense/status` (JSON: every object with distance, lateral offset, size, confidence, kind; track model; health; mount calibration; timing) | |

Decision logic, thresholds and their measured effect: [`docs/ALGORITHM.md`](docs/ALGORITHM.md) §4, §4b.
The organizers left the choice of outputs to the teams and asked that everything needed be stated
in the algorithm and launch descriptions (23.09): this table, "Topics published by the node" below
and ALGORITHM.md §4 / §4b are that statement; how to run it is "How a bag is processed".

## Repository layout

| Path | What |
|---|---|
| [`resense/`](resense/) | core library (numpy / scipy / scikit-learn, no ROS): PointCloud2 decoding, mount calibration, track model, gauge corridor, low-object stage, clustering, tracking, health, detector, synthetic obstacle injection, metrics, CLI |
| [`ros2_ws/src/resense_ros/`](ros2_ws/src/resense_ros/) | ROS 2 Humble node, launch file, parameters, RViz layout |
| [`docker/`](docker/), [`docker-compose.yml`](docker-compose.yml), [`scripts/`](scripts/) | reproducible build and demo |
| [`configs/default.yaml`](configs/default.yaml) | every tunable parameter (also installed as the ROS parameter file) |
| [`tests/`](tests/) | pytest on a synthetic ray-cast tunnel — runs without the dataset (algorithm, envelope, calibration, guards, and the ROS node against stand-ins: `test_node.py`) |
| [`web/`](web/) | browser dashboard (offline replay of a `resense run` JSONL; live via rosbridge, installed separately and with roslib from a CDN), Foxglove layout (the image has the Foxglove bridge), label tool, headless checks |
| [`docs/`](docs/) | [ARCHITECTURE](docs/ARCHITECTURE.md) · [ALGORITHM](docs/ALGORITHM.md) · [EXPERIMENTS](docs/EXPERIMENTS.md) · [SCORECARD](docs/SCORECARD.md) · [EVALUATION](docs/EVALUATION.md) · [DATASET](docs/DATASET.md) · [SENSOR](docs/SENSOR.md) · [RESEARCH](docs/RESEARCH.md) · [PLAN](docs/PLAN.md) · [CAPTAIN](docs/CAPTAIN.md) · [SUBMISSION](docs/SUBMISSION.md) · [PRESENTATION](docs/PRESENTATION.md) · [QUESTIONS](docs/QUESTIONS.md) · [UI screenshots](docs/images/README.md) · organizers' README / ТЗ / [**Q&A session**](docs/organizers/QA_session.md) ([transcript](docs/organizers/QA_session_transcript_ru.md)) · [organizers' answers](docs/organizers/answers.md) · [test-stand software](docs/organizers/test_stand_software.md) · sensor manual ([`docs/sensor/`](docs/sensor/)) |
| [`labels/`](labels/) | real labels: `doubleT_obstacle.json` (the crossing person, the object on the rail, the walking person), `new_data_objects.json` (every object the detector confirmed on the 20-minute ride, with cause class) |

## Quick start (no ROS needed)

```bash
pip install -e ".[dev]"                       # numpy scipy scikit-learn pyyaml + rosbags matplotlib open3d pytest
pytest -q                                     # expect no skips: "skipped" means open3d is missing (RESENSE_REQUIRE_SYNTHETIC=1 makes that fail, as in CI)
ruff check .                                  # lint, as the CI job "lint" (pip install ruff)

# unpack the dataset (see docs/DATASET.md), then:
resense info  /data/for_hackathon/roundT_doubleT
resense run   --bag /data/for_hackathon/doubleT_obstacle --out results.jsonl --render out/   # PNG per frame
resense bench --bag /data/for_hackathon/roundT_doubleT --every 5                             # per-stage timing

# synthetic obstacles ray-cast into real empty frames + evaluation
resense inject --bag /data/for_hackathon/roundT_doubleT --every 10 --out data/synth --distances 10:250 --kinds person,box,plank
resense eval data/synth

# the real-data report card over every recording (frames cached once, docs/DATASET.md "Cached frames")
for b in /data/for_hackathon/*/; do python scripts/cache_frames.py $b /data/cache/$(basename $b) --every 1 --int16 --stamps; done
python scripts/eval_real.py --cache /data/cache --out out/eval          # false alarms, the labelled person / object, latency
python scripts/far_range_eval.py --cache /data/cache/new_data --files 46,68,98 --kinds person,box1.0,cable \
    --start 220 --out out/far.json                                    # set F: synthetic positives, legacy placement by default
python scripts/mine_objects.py out/eval --bag new_data                  # every confirmed object of a ride, by cause
```

## ROS 2 / Docker (the way the jury runs it)

```bash
./scripts/build.sh                                   # docker build -t resense -f docker/Dockerfile .
./scripts/run_demo.sh /data/for_hackathon/roundT_doubleT   # detector + RViz + bag playback in one container
./scripts/run_headless.sh /data/for_hackathon/doubleT_obstacle   # same, no X11: prints the distance
./scripts/dry_run.sh /data/for_hackathon/doubleT_obstacle        # acceptance test, exits non-zero on failure
WITH_TOOLS=1 ./scripts/build.sh                      # + rosbags / matplotlib / open3d / pytest inside the image
PULL=1 ./scripts/build.sh                            # refresh the ros:humble base first (an old cached one fails apt-get update)
docker run --rm resense python3 -m pytest -q /opt/resense/tests   # the test suite inside the image (needs the WITH_TOOLS=1 image; CI does this)

# or step by step
docker run --rm -it --net=host --ipc=host -v /data/for_hackathon:/data resense \
    ros2 launch resense_ros detector.launch.py            # terminal 1: detector
docker run --rm -it --net=host --ipc=host -v /data/for_hackathon:/data resense \
    ros2 bag play /data/roundT_doubleT --clock --delay 3  # terminal 2: playback (--delay: DDS discovery first)
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
detector runs the single-frame path (no accumulation: the LiDAR-only speed estimator is off by
default, EXPERIMENTS.md §1b). `publish_tf:=true|false` and `tf_parent_frame:=resense_lidar`
control the static TF that lets one RViz / Foxglove layout serve every bag.

**The bags disagree on the topic name and frame id** — `roundT_doubleT` and four more publish
`/lidar_points` in `hesai_lidar`, `doubleT_obstacle` publishes `/sensing/lidar/hesai128/pointcloud`
in `lidar_livox` — and the organizers confirmed (23.09) that **the control data may use either
pair, all recorded with the same LiDAR**. The node therefore listens to both names and, unless
`auto_discover:=false`, to any other `PointCloud2` topic that appears on the graph (discovery
keeps running whenever the input is silent). One input is processed at a time; when it has been
silent for `input_switch_timeout` (1 s) and another topic delivers, the node switches to it. Every
**new recording** — another topic, another frame id, or header stamps that jump back (the bag
played again) or forward by more than `new_input_gap` (30 s) — starts with a fresh detector, so
the scene state and the mount calibration of one bag never carry into the next; a shorter hole
in a recording (> `hole_reset_gap`, 1 s) resets the scene only. The control bags therefore need
no argument and can be played one after another into one running node. `docker compose
--profile viz up` starts RViz and a Foxglove bridge (port 8765) next to the detector.

### How a bag is processed (the pipeline we expect)

The organizers will most likely play the control bag from a console (their answer of 23.09). That
is the whole pipeline — **ReSense does not read bag files**; it subscribes to the point cloud:

```text
ros2 bag play <bag>  ──PointCloud2 (either topic / frame pair), 10 Hz──▶  resense_detector node
(any console on the same ROS 2 network,        (docker run --net=host --ipc=host … ros2 launch …)
 or inside our image: sqlite3 + mcap plugins)        │
                                                     ├─▶ /resense/decision        GO / CAUTION / STOP / FAULT
                                                     ├─▶ /resense/obstacle_detected, /resense/nearest_distance
                                                     ├─▶ /resense/clear_distance, /resense/health
                                                     └─▶ /resense/detections, /resense/status (JSON), RViz markers
```

1. start the detector: `docker run --rm -it --net=host --ipc=host resense ros2 launch resense_ros detector.launch.py`
   (the same image and command for every bag; mount / topic arguments are optional; the image
   runs DDS over UDP (`docker/fastdds_udp.xml`), so a player on the same machine needs no shared
   memory and may run as any user — `--ipc=host` is harmless and kept for older images);
2. play the bag from any console: `ros2 bag play <bag> --delay 3` (the delay lets DDS discovery
   finish; the player preloads the bag and then sends its first seconds back to back, which the
   node works through `catchup_step` s of recording apart, EXPERIMENTS.md §3b; same `ROS_DOMAIN_ID`
   as the node, default 0;
   or `ros2 launch … bag:=/data/<bag>` to
   let the launch file play it inside the container; the image has the sqlite3 and mcap storage
   plugins, so the storage format does not matter);
3. read the answer on the topics of "What to look at" above; `ros2 topic echo /resense/decision`.

Several bags can be played one after another into the same node (see the paragraph above). The
offline command-line tool (`python -m resense.cli run --bag <dir>`, Quick start) *does* read a
rosbag2 directory directly (the pure-Python `rosbags` reader, no ROS needed) — it is our
development and evaluation tool and produces the same per-frame JSON as `/resense/status`, but it
is not the way the solution is meant to be run.

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

The organizers' extended recording (`new_data`, one 20-minute bag of 221 split files, 90 GB
unpacked — [`docs/DATASET.md`](docs/DATASET.md) "Extended dataset") is used the same way once
unpacked next to the six bags: `scripts/run_headless.sh /data/new_data`, or
`RESENSE_DATA=/data RESENSE_BAG=new_data docker compose up`.

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
   `docker run --rm -it --net=host --ipc=host -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v /data/for_hackathon:/data:ro resense ros2 launch resense_ros detector.launch.py bag:=/data/doubleT_obstacle loop:=true rviz:=true`.
   What this looks like, with the bag played from a second container as the jury would:
   [`docs/video/docker_chain_rviz.mp4`](docs/video/docker_chain_rviz.mp4). RViz subscribes to the
   raw clouds reliable, as the node does; a best-effort RViz display shows almost none of the
   5–10 MB clouds that `ros2 bag play` publishes (EXPERIMENTS.md §3b).
2. **Foxglove over the network**, nothing graphical on the demo machine:
   ```bash
   docker compose --profile viz up detector foxglove                      # detector + foxglove_bridge :8765
   RESENSE_BAG=doubleT_obstacle docker compose --profile tools up player   # second terminal
   ```
   On any laptop open Foxglove (desktop app or app.foxglove.dev) → Open connection →
   `ws://<demo-host>:8765` (`ssh -L 8765:localhost:8765 <demo-host>` first if only ssh is open) →
   Layout → Import → [`web/foxglove_layout.json`](web/foxglove_layout.json): raw cloud, corridor
   points, boxes, the GO / CAUTION / STOP / FAULT indicator, status text and the distance /
   clear-distance / latency / fps plots. Details and limits in
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

SKIP_BUILD=1 ./scripts/dry_run.sh /data/for_hackathon/roundT_doubleT --expect-clear --max-alarm-frames 2   # false-alarm check
```

**Run on 23.09** (Docker in the development sandbox, 4 vCPU; the recordings rebuilt from the
frame cache by `scripts/cache_to_bag.py`, same topic / `frame_id` / layout / receive times;
EXPERIMENTS.md §3b): `roundT_doubleT` 237 of 252 frames at 10 fps, p95 76 ms, and 2 alarm
frames at 128–130 m — PASS with `--max-alarm-frames 2` (the offline evaluation from frame 0 has
the same two; which frame processing starts from matters: a trackside device at 48–54 m is
confirmed from some start frames, so a run gives 1–4 alarm frames, EXPERIMENTS.md §0); `doubleT_obstacle` the
person and the object at 55.9–56.6 m, 88–118 alarm frames, but at 360° this sandbox is at the
frame period (96 ms mean, p95 112–130 ms) and the node skips frames (7–10 fps in steady state), so the
default `--max-p95-latency 100 --max-dropped 0` fail there (drops are counted after the first 5 s,
`--settle-s`: the player's start-up burst); the jury's i7-9700E is the
reference for those two. The organizers' way — node container, `ros2 bag play` from another
container, `roundT_doubleT` then `doubleT_obstacle` into the same running node — switched the
input and restarted the detector as designed (`--expect-inputs 2`). That first run also found
that a best-effort subscription lost 196 of the 201 ten-megabyte clouds (the node now matches
the publishers' reliability, `input_reliability`, below), and a review found that a player run
by a **normal user** reached the root node not at all through shared memory: the image now runs
DDS over UDP (`docker/fastdds_udp.xml`), and `scripts/console_test.sh` — node container, player
as uid 1000 in another container — runs in CI. The first seconds of a played recording were
lost until v0.6.4: the player preloads the bag and sends them back to back, and the node kept the
newest frame only; it now works through them (EXPERIMENTS.md §3b).

Defaults for `doubleT_obstacle`: the person is reported in 50–62 m, p95 of decode + detect is
≤ 100 ms (the 10 Hz frame period) and no input frame is dropped after the first 5 s. Any argument after the bag path
is forwarded to `scripts/check_dry_run.py`, which holds the thresholds (`--expect-obstacle`,
`--expect-clear`, `--distance LO:HI`, `--first-clear N`, `--max-p95-latency`, `--max-dropped`,
...) and can also run on a capture someone else recorded. Raw output stays in `$OUT` (default
`out/dry_run/`): `status.jsonl` and `node.log`.

**Sprint 4 acceptance availability.** `dry_run.sh`, `console_test.sh`, `build.sh` and the demo
wrappers require both the Docker CLI and a reachable Docker daemon; they fail fast with the daemon
diagnostic and exit 3 when that prerequisite is absent. `smoke_test.sh` is an in-image ROS check
and reports when it is accidentally invoked on a host without `ros2`. A missing bag/cache is also
reported before an acceptance run. In an environment without the daemon and recordings, no ROS
FPS or latency result is produced; the dated historical measurements in `docs/EXPERIMENTS.md` are
not a result of the current run. Offline `resense bench --npy <cache>` remains available when a
cache is supplied and gives a clear error for an empty cache.

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
| `/resense/decision` | `std_msgs/String` | v0.6: `GO` / `CAUTION` / `STOP` / `FAULT` (see "What to look at") |
| `/resense/clear_distance` | `std_msgs/Float32` | v0.6: m of track verified clear (the obstacle, else the monitored range; 0 on a fault or a silent input) |
| `/resense/health` | `diagnostic_msgs/DiagnosticArray` | v0.6: OK / WARN / ERROR / STALE with messages and values: points, window dirt, blocked sectors, visibility, rail lock, latency p95, monitored range, mount calibration |
| `/resense/markers`, `/resense/corridor_points` | `MarkerArray`, `PointCloud2` | RViz: boxes, labels, corridor outline, status text; points inside the corridor |
| `/tf_static` | `tf2_msgs/TFMessage` | identity transform `resense_lidar` → the input cloud's `frame_id`, sent once per frame id: the layouts keep `resense_lidar` as the fixed frame whether the bag says `hesai_lidar` or `lidar_livox` |

Node parameters: `input_topic`, `auto_discover`, `discover_period`, `config_file`,
`publish_markers`, `publish_corridor_cloud`, `marker_x_max`, `output_frame`, `stats_period`,
`ego_speed_mps`, `speed_topic`, `odom_topic`, `speed_timeout`, `publish_tf`, `tf_parent_frame`,
and since v0.6 the **sensor mount** — `sensor_forward` / `sensor_left` / `sensor_up` (axis
mapping, e.g. `sensor_forward:=+x`), `mount_roll_deg` / `mount_pitch_deg` / `mount_yaw_deg`
(fixed tilt), `auto_calibrate` (default `true`: orientation, roll and pitch found from the rails
and the bed in the first frames, reported in `/resense/status` → `mount`) — and the **guards**
`stale_timeout` (s without a frame before `FAULT`, default 0.5) and `max_consecutive_errors`
(processing exceptions before the detector is reset, default 5); since v0.6.1 the **input
handling** — `input_switch_timeout` (1 s), `new_input_gap` (30 s), `hole_reset_gap` (1 s), see
"How a bag is processed" — and `input_queue_depth` (40 since v0.6.4; a frame that waits alone is
processed at once, so the node skips rather than lags behind the sensor), `catchup_step` (0.3 s:
while several frames wait — the burst at the start of a played bag — one every 0.3 s of recording
is processed from the first frame on until the node is back on the newest; 0 = the newest only)
and `catchup_max_lag` (5 s); since v0.6.2 `input_reliability` (`auto`: the input
subscription matches its publishers — reliable for `ros2 bag play` of the organizers'
recordings, best-effort for a best-effort driver; `reliable` / `best_effort` force it). All of
them are launch arguments too. Every `stats_period` seconds the node logs
`fps`, latency mean / p95 / max, the measured input period and the number of frames the
input queue dropped (estimated from gaps in the header stamps).

## Parameters worth knowing (`configs/default.yaml`)

| key | default | meaning |
|---|---|---|
| `sensor.forward/left/up`, `sensor.roll_deg/pitch_deg/yaw_deg` | `-y/+x/+z`, 0 | sensor → vehicle axis mapping (hackathon Hesai frame) and a fixed mount tilt |
| `calibration.*` | on, 20 observations every 10 frames | automatic mount calibration (orientation, roll, pitch, yaw > 3°); a tilt is applied from 0.75° |
| `track.rails_*` | | rail-ridge template (track gauge 1.52 m, rail-head centres `rails_spacing` 1.59 m apart) for the track axis and rail-head level |
| `track.walls_*` | band 1.6–2.8 m | tunnel-boundary fit for yaw / curvature; `axis_valid_*` = how far the corridor is trusted |
| `track.rails_far_check_enabled` | false | Sprint 1 experimental far-rail cross-check; opt-in pending real-recording A/B and timing |
| `gauge.profile` | \|dy\| ≤ 1.05 m, 0.12–3.0 m | **the organizers' 2.1 × 3.0 m train envelope**; `warning_margin` 0.35 m = advisory zone; `edge_margin_per_100m` 0.15 m |
| `lowobj.*` | on, ≤ 60 m | low objects on the rails (bumps above the learned bed that rise ≥ 3 cm above the rail head) |
| `lowobj.near_enabled` | false | experimental central near-bed path; measured on 24.09 it raises the ride's false events from 47 to 667, so it stays off (ALGORITHM.md §6) |
| `accumulation.estimate_speed` | false | LiDAR-only speed estimation opt-in; without a supplied speed, use single-frame detection |
| `cluster.far_*` | 0.6 m tall, ≤ 3 m long | what may alarm beyond the height reference (far field of straight track) |
| `cluster.eps / range_scale / voxel` | 0.35 / 40 / 0.05 | range-adaptive DBSCAN: ε(r) = eps·(1 + r/40 m) |
| `cluster.*_max_*`, signatures | | infrastructure filters (thin hardware, low hardware, wall-like, column, floating, edge, wall face); thin objects hanging near the axis are never demoted |
| `tracking.confirm_time_s / confirm_hits / conf_threshold` | 0.5 s / 3 / 0.6 | persistence before an alarm (low objects: 5 hits); `hold_misses` 1 keeps a reported obstacle over one missed frame |
| `health.*` | | thresholds of the production guards |

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
| video | [`docs/video/doubleT_obstacle_cab.mp4`](docs/video/doubleT_obstacle_cab.mp4) (the real bag from the cab: envelope, obstacle, decision and distance; `scripts/hero_view.py --sequence`), [`docs/video/doubleT_obstacle_offline.mp4`](docs/video/doubleT_obstacle_offline.mp4) (top-down and side renders of every frame) and [`docs/video/dashboard_doubleT_obstacle.mp4`](docs/video/dashboard_doubleT_obstacle.mp4) (the web dashboard replaying the same run), all v0.6.2; recipe in [`web/README.md`](web/README.md); **the jury chain on screen**: [`docs/video/docker_chain_rviz.mp4`](docs/video/docker_chain_rviz.mp4) (69 s: `docker run` of the node with RViz, `ros2 bag play` as a normal user from another container, `/resense/decision`; sandbox, bag at 0.5×) |
| submission status | [`docs/SUBMISSION.md`](docs/SUBMISSION.md) |

## Team

Team «Молоток» (Molotok; ReSense is the name of the solution): four people, mapped onto the five roles the organizers suggest (system analyst, computer-vision
engineer, ROS 2 robotics developer, data specialist, C++/Python software developer):

| # | who | organizers' roles | owns |
|---|---|---|---|
| P1 | captain / lead | system analyst + ROS 2 robotics developer | requirements, architecture, ROS 2 node & Docker, evaluation protocol, submission, pitch lead |
| P2 | frontend | software developer (Python/JS tooling & UI) | RViz / Foxglove / web dashboard, label tool, video, presentation (mandatory slides 7–11) |
| P3 | member 3 | computer-vision engineer | track model, gauge corridor, clustering, tracking, long range, false-positive suppression, performance |
| P4 | member 4 | data specialist | dataset tooling, synthetic obstacles & augmentation, labelling, metrics, tests, CI |

Detailed plan and sprint calendar to the 29 September deadline: [`docs/PLAN.md`](docs/PLAN.md).
