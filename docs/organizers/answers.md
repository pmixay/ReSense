# Organizers' answers to our questions (case 05)

Everything the organizers answered to the questions of [`../QUESTIONS.md`](../QUESTIONS.md),
from three sources: the recorded **Q&A session of 22.09** (summary with timestamps:
[`QA_session.md`](QA_session.md), transcript: [`QA_session_transcript_ru.md`](QA_session_transcript_ru.md)),
the **written answers of 23.09** (verbatim below) and the **hand-outs of 22.09** (sensor manual,
extended dataset, test-stand software). The questions that are still open are the only ones
left in [`../QUESTIONS.md`](../QUESTIONS.md).

## 1. Answers by question (Q&A session 22.09 + written answers 23.09)

| # | our question | Q&A session, 22.09 ([`QA_session.md`](QA_session.md)) | written answer, 23.09 | status | consequence in ReSense |
|---|---|---|---|---|---|
| 1 | staged obstacles in `new_data`, labels, a recording with obstacles before the control run? | none: "all we can give is more empty tunnel"; no labels exist; no more data with obstacles; the hidden check adds the organizers' own **synthetic obstacles** | **"В new_data препятствий нет"** — no obstacles | **closed** | every `new_data` alarm is a false alarm; synthetic positives ray-cast into the moving ride (set F); the injector follows the organizers' definitions |
| 2 | control-bag format: topic, frame id, 120° window, sqlite3 — or also the `doubleT_obstacle` variant? | same conditions as the provided data, the LiDAR mount of the empty-tunnel rides; **full rides** through other tunnels too | **both (topic, frame) pairs may occur; one and the same LiDAR; the bag will most likely be played from the console; describe the pipeline if the code reads bags directly** | **closed** | input switching between recordings and per-recording restart (v0.6.1); "How a bag is processed" in the README; no map-based logic |
| 3 | return mode; mount height / pitch / offset | the LiDAR position "is not fixed, differs even in the provided clouds, not yet approved — count on a variable position, set it in the launch parameters" | — | closed for the mount; the return mode / resolution / window not answered — **asked again** ([`../QUESTIONS.md`](../QUESTIONS.md) item 1) | `resense/calibration.py` (orientation + tilt from rails and bed) and the mount launch arguments; dual-return duplicates handled either way |
| 4 | PTP / GNSS time sync on the train | not answered | — | **open — asked again** ([`../QUESTIONS.md`](../QUESTIONS.md) item 2) | the header stamps (sensor clock, year-2000 epoch) and the bag receive time remain the clocks |
| 5 | which obstacles, which ranges, a person on a platform | anything inside the **2.1 m × 3.0 m train envelope**, at least **30 × 30 × 10 cm**; **broken hanging cables must be detected**; people, animals, objects thrown on the track; a person on a platform is not an obstacle unless inside the envelope; range: < 100 m rated poorly, farther is better, the visible limit in a curve is acceptable | — | **closed** | `gauge.profile` = the envelope, `resense/lowobj.py`, signature changes, far-field rule (ALGORITHM.md §3.2–3.3c) |
| 6 | how is the result evaluated, which messages, which frame | "can we go / obstacle or not / distance", any ROS topic, per-frame yes/no is enough, extra logic must be described | **outputs are the participants' choice; state everything in the algorithm and launch descriptions** | **closed** | `/resense/decision`, `/resense/obstacle_detected`, `/resense/nearest_distance`, `/resense/clear_distance`, `/resense/status`, `/resense/health`, all in README "What to look at" and ALGORITHM.md §4b |
| 7 | remote demo, duration | acceptable, but the organizers run every solution themselves | — | closed for the demo; the duration not answered — **asked again** ([`../QUESTIONS.md`](../QUESTIONS.md) item 3) | README demo sections unchanged |
| — | (new, Q&A) train speed | regulated 80 km/h; plan for 85 km/h = 2.3 m between frames; some trains have no odometry | — | noted | tracker gate 25 m/s; the no-speed path is the default, a speed input is optional (EXPERIMENTS.md §2d: 177 m with it) |
| — | (new, Q&A) the obstacle recording | besides the person, **an object lies on the rails** where the person stands | — | noted | labelled (`labels/doubleT_obstacle.json`, `object_on_rail`) |
| — | (new, Q&A) evaluation environment, run conditions | the spec's test stand (i7-9700E, RTX 4070 Ti SUPER); offline; "the less magic the better — `docker run`, `ros2 launch`, check"; compute is a tie-breaker | — | noted | CPU-only image, no network at run time, one launch command |

## 2. Written answers (23.09)

Verbatim, numbered as our questions of 21.09 (the original message is in the git history of
`docs/QUESTIONS.md`: 1 = staged obstacles in `new_data`, 2 = control-bag format, 6 = evaluation format):

> 1\) В new_data препятствий нет.
>
> 2\) В контрольных данных могут быть оба набора (имя_топика; имя_фрейма). Все данные были
> записаны с одного и того же лидара. Формат хранения не столь важен, мы, вероятнее всего, будем
> проверять работу вашего алгоритма, проигрывая бэг через консоль. Однако, если ваше решение
> подразумевает работу кода с бэг файлом напрямую, то вам следует описать предполагаемый вами
> пайплайн запуска вашего решения.
>
> 6\) Участники вольны сами выбирать, какими будут выходные данные их алгоритма. Дополнительно
> отмечу, что участникам следует указать всю необходимую информацию в описании работы алгоритма
> и в описании запуска их решения.

What they mean and what we did:

| # | answer (English) | consequence | where |
|---|---|---|---|
| 1 | `new_data` contains **no obstacles** (confirms the Q&A session) | every alarm on the ride is a false alarm, as counted in EXPERIMENTS.md §0 / §1d (82 events, 6.3 per km); the 11 person-like ride tracks we checked by eye are infrastructure; positives stay synthetic (set F) plus the person and the object on the rail of `doubleT_obstacle` | [`DATASET.md`](../DATASET.md) "Extended dataset", [`EXPERIMENTS.md`](../EXPERIMENTS.md) §1d, `labels/new_data_objects.json` |
| 2 | the control data **may contain both (topic, frame) pairs** — `/lidar_points` + `hesai_lidar` and `/sensing/lidar/hesai128/pointcloud` + `lidar_livox`; **all data were recorded with the same LiDAR**; the storage format matters little — they will most likely **play the bag from the console**; a solution that reads bag files directly must describe its launch pipeline | (a) the node already listened to both names and auto-discovers others; **v0.6.1 also switches between them when one recording follows another in the same running node**, restarts the detector (scene state and mount calibration) for every new recording — a new topic, a new frame id, or header stamps that jump — and keeps discovering topics while the input is silent (`tests/test_node.py`); (b) the one physical LiDAR is why the `doubleT_obstacle` full turn and the 120° window of the other bags are the same sensor settings seen through two drivers / mounts — the auto-calibration handles the mount; (c) **our solution does not read bag files**: it subscribes to the topic, so `ros2 bag play <bag>` from any console on the same ROS 2 network (or inside our image, which has the sqlite3 and mcap storage plugins) is the whole pipeline; the offline CLI that does read `.db3` files is a development tool, described separately | [`README.md`](../../README.md) "How a bag is processed", `detector_node.py` "Input handling", [`DATASET.md`](../DATASET.md) "Topic and sensor" |
| 6 | **the outputs are ours to choose**; everything needed must be stated in the algorithm description and in the launch description | the outputs are specified in one place for the jury (README "What to look at": decision, obstacle flag, distance, verified-clear distance, full JSON status, health) and in ALGORITHM.md §4 / §4b (how each is computed); the launch description names every topic and parameter | [`README.md`](../../README.md) "What to look at", "Topics published by the node"; [`ALGORITHM.md`](../ALGORITHM.md) §4, §4b |

## 3. Closed by hand-outs and team decisions (22.09)

| was asked | how it closed | recorded in |
|---|---|---|
| lidar model and specifications | organizers' hand-out: the Pandar128E3X user manual (Hesai doc 128-en-240710) — model confirmed, every number re-checked | [`SENSOR.md`](../SENSOR.md), the PDF in [`sensor/`](../sensor/) |
| will there be an extended dataset, when, how many recordings | organizers' hand-out: `new_data.zst`, one 20-minute recording, 221 split files, no labels | [`DATASET.md`](../DATASET.md) "Extended dataset", `extended_dataset_intake.json` |
| GPU / CUDA on the test stand | organizers' hand-out: `nvidia-smi` and `dpkg` state of the stand (driver 580, CUDA 13 runtime, toolkit 12.9); ReSense does not use it | [`organizers/test_stand_software.md`](test_stand_software.md) |
| train speed, odometry or IMU topic on the train | **team decision: train-speed data is not technically possible for this case — the solution operates without it.** The deliverable is the no-speed path (single-frame detection + persistence in time); the node's `ego_speed_mps` / `speed_topic` / `odom_topic` inputs stay as optional extras and the multi-frame accumulation stays off unless a speed is given | [`SENSOR.md`](../SENSOR.md) §4, [`CAPTAIN.md`](../CAPTAIN.md) finding 7, `ARCHITECTURE.md` |
| intermediate submission (date, form, where), final submission (image vs Dockerfile, size, video), test-stand procedure (launch, internet at build, bag playback, disk) | organisational — the team handles these itself, not a question to the organizers | [`SUBMISSION.md`](../SUBMISSION.md), README "Where the data lives" / demo runbook |
| may the given recordings be used for tuning parameters | answered 22.09: yes, acceptable | — |
| own slides after the template's 7–11 | answered 22.09: yes, acceptable | [`PRESENTATION.md`](../PRESENTATION.md) |
