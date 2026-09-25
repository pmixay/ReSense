# Organizers' Q&A session (case 05) — transcript summary and what it changes

Source: recording of the case-05 Q&A session, "Город 5. Департамент транспорта.mp4"
([Google Drive](https://drive.google.com/file/d/1Py6Ptq5HFu8Y0vj-m2R5zIQv7dFVZ6Ax/view), 58 min,
1920×1080). Participants from the organizers' side: the moderator (Ольга Горбатова), the case
mentor (Григорий Сидников), Константин Петрикин (senior project manager, ГУП «Московский
метрополитен»), Андрей Новиков and Георгий Зинченко (chief specialists, ГУП «Московский
метрополитен»).

Transcribed on 22.09 with Whisper large-v3-turbo (CTranslate2, int8, CPU, Russian, beam 2, VAD):
[`QA_session_transcript_ru.md`](QA_session_transcript_ru.md) holds the full text in one-minute
paragraphs with timestamps. It is a machine transcript: names and a few technical words are
garbled ("адеметрия" = одометрия, "Hensai" = Hesai), numbers were checked against the audio
context. Timestamps below are `mm:ss` of the recording.

## 1. Critical facts (these decide the design)

| # | fact (organizers' words, translated) | when | consequence for ReSense |
|---|---|---|---|
| 1 | **An obstacle is anything inside the train envelope: 2.1 m wide × 3.0 m high, all protruding elements included** (cross-section only; the train's length is irrelevant). A person on a platform or beside the track is *not* an obstacle unless inside that envelope. | 23:15–24:50, 40:49–41:35 | the default gauge polygon becomes \|dy\| ≤ 1.05 m, 0.12–3.0 m above the rail head (v0.5 used 2.8 × 3.5 m); the old polygon (1.40 m) is now the advisory zone |
| 2 | **Size criterion: 300 × 300 × 100 mm** ("anything in the envelope, at least 30×30×10 cm, is an obstacle"); smaller is a bonus; estimating the size is an optional extra | 23:59, 49:56 | a 10 cm object lying on the track is below the rail head: new **low-object stage** (bumps above the learned bed cross-section, `resense/lowobj.py`) |
| 3 | **Broken cables hanging into the envelope must be detected — "this is very important"** | 24:27 | the `column` / `floating` / `overhead` demotions no longer apply near the track axis (`cluster.signature_min_lateral`, `overhead_min_height` = envelope top) |
| 4 | **The hidden test set: rides through the same and other tunnels, plus the organizers' own tool that generates synthetic obstacles** — "we will also check solutions with it" | 07:19–07:43 | synthetic objects are part of the evaluation: our injector (`resense inject`) and the envelope follow the organizers' definitions; no dependence on object appearance |
| 5 | **No labels exist, no more data with obstacles** — "all we can give is more empty tunnel"; nothing staged in `new_data` | 03:46–06:58 | positives remain synthetic (ray-cast into real frames) plus the one real scene; every alarm in `new_data` is a false alarm |
| 6 | **No odometry** in the recordings, and some trains will have none: "you have a LiDAR cloud and, without auxiliary means, find the obstacles" | 07:46–08:33 | the detector must work without speed (the default path); speed stays an optional input |
| 7 | **The LiDAR position is not fixed** — it differs between the provided recordings and is not yet approved; "count on a variable position, set it in the launch parameters". The control data will use the mount of the empty-tunnel rides (not the `doubleT_obstacle` mount) | 21:45–22:40 | mount auto-calibration (`resense/calibration.py`) + launch parameters `sensor_forward/left/up`, `mount_roll/pitch/yaw_deg`, `auto_calibrate` |
| 8 | In `doubleT_obstacle` **an object lies on the rails where the person stands** (besides the person) | 49:14–49:30 | labelled in `labels/doubleT_obstacle.json` (see DATASET.md "Real labels") |
| 9 | **Output:** "can we go / obstacle or not / distance to it", any extra information welcome; format free, a ROS topic expected; **per-frame obstacle yes/no is sufficient**, extra decision logic is a bonus but must be described ("tell us clearly what to look at") | 13:53–14:59, 17:01–20:24 | new `/resense/decision` (GO / CAUTION / STOP / FAULT) and `/resense/clear_distance`; README says which topic to read |
| 10 | **Launch:** everything inside the Docker container, "the less magic the better — ideally `docker run`, then `ros2 launch`, and check". Must work **offline** | 10:24–10:44, 15:05–15:26 | unchanged: `docker run … ros2 launch resense_ros detector.launch.py`; no network at run time |
| 11 | **Real time:** frames arrive at 10 Hz (as in the data); the closer to 10 Hz the better. Multi-frame confirmation is allowed but costs reaction time, which must stay adequate | 20:28–21:16, 32:40–33:30 | persistence 0.3 s (3 frames) kept; latency budget 100 ms |
| 12 | **Speed:** regulated maximum 80 km/h; plan for 85 km/h → **up to 2.3 m between consecutive frames** | 31:11–32:12 | tracker gate `tracking.ego_speed_max` 25 m/s covers it |
| 13 | **Braking decisions are out of scope**; concentrate on obstacle yes/no, distance, optional extras | 30:22–31:10 | no braking model in the product |
| 14 | **Range:** "farther is better; a kilometre would be magic"; 100 m good / 200 m very good / 300 m excellent as in the spec; **under 100 m is rated poorly**. But **if the tunnel is not visible farther (a curve), detecting at the visible limit (e.g. 60 m) is fine** — "no worse than a train driver" | 42:17–43:40, 55:40–57:40 | report the monitored (verified-clear) range next to every detection; a sightline limit is not a failure |
| 15 | **Generalisation:** memorising the clean tunnel from the given rides is allowed, but the check includes a **full ride through the tunnel** beyond the given data: a map-dependent solution "will not fully work on our data" | 33:40–34:50 | no map: the tunnel model is re-estimated every frame from the cloud itself |
| 16 | Tunnel types in the data cover all there are: round, rectangular, double-track, **pressure gates (the rails are flush with the gate floor — no rail relief)**, station approaches, switches | 36:45–38:20 | rail lock is lost in gates: the track model runs on its prior there (health `rail_lock`), gauge from the walls |
| 17 | Reflective surfaces exist (stop signs, visible in the data); **puddles in the trough between the rails** give LiDAR artefacts; no LiDAR interference observed | 26:10–28:20 | the low-object stage ignores returns below the bed (mirror images of puddles); retro-reflector rule stays off by default |
| 18 | The LiDAR is **not switched off at stations** | 22:44–23:10 | stations are part of every ride: platform false alarms matter |
| 19 | Evaluation hardware = the test stand of the spec (i7-9700E, RTX 4070 Ti SUPER); compute / memory are secondary criteria (tie-breakers only). No public leaderboard; the metrics are the spec's (§8: detection, range, speed, generalisation) | 16:26–16:53, 53:40–55:30 | CPU-only Python stays; latency and FPS reported |
| 20 | Organizers' own solution is **purely algorithmic, no neural networks** | 52:03 | our geometric approach is aligned with what they consider workable |
| 21 | Use of any external data / models is allowed if everything ships with the solution and runs offline; closed-source model weights are acceptable if the solution runs | 08:43–13:15, 38:20–40:40 | nothing external needed |
| 22 | **No changes after the 29.09 deadline**; upload the link early (platform overload near the deadline) | 02:26–03:07, 50:22–51:10 | SUBMISSION.md: upload by 18:00 on 29.09 |
| 23 | A live remote-desktop demo is fine, but the organizers will run every solution themselves | 15:34–16:22 | the jury path (`docker build → run → ros2 launch`) is primary |

## 2. Answers to our questions

The session answered most of our questions. On 23.09 the organizers also answered questions 1,
2 and 6 in writing, and on 24.09 questions 3 (return mode) and 4 (time); question 7's duration
part was withdrawn by the team as organisational. All of it is consolidated, with the written
answers verbatim, in
[`answers.md`](answers.md); [`../QUESTIONS.md`](../QUESTIONS.md) keeps only the questions still open.

| our question | answer from the session (22.09) | written answer (23.09) |
|---|---|---|
| 1. staged obstacles in `new_data`? | no — only empty tunnel; no labels; the evaluation adds synthetic obstacles (facts 4, 5) | "В new_data препятствий нет" — none |
| 2. control bag format like `new_data` / five of six bags? | control data: same conditions as the provided data, LiDAR mount of the empty-tunnel rides (fact 7); full-ride recordings included (fact 15). Topic / frame id not stated | **either (topic, frame) pair may occur; all data from the same LiDAR; the bag will most likely be played from the console; describe the launch pipeline if the code reads bags directly** → node input switching and per-recording restart (v0.6.1), README "How a bag is processed" |
| 3. return mode, mount height / pitch / lateral offset | not fixed, varies, set it in the launch parameters (fact 7) | 24.09: **Last and Strongest now; the recordings are old and may differ; the control data use the same settings** → nothing changes: one echo is stored twice in every recording and the detector counts voxels (SENSOR.md §4) |
| 4. PTP / GNSS time sync | not answered | 24.09: **will exist on the train, but not within this hackathon** → the bag receive time and stamp differences stay the clocks |
| 5. which obstacles, which ranges, person on a platform? | anything ≥ 30×30×10 cm in the 2.1 × 3 m envelope; broken cables; people / animals / objects thrown on the track; a person on a platform is not an obstacle (facts 1–3) | — |
| 6. how is the result evaluated, which messages? | per-frame obstacle yes/no + distance, any ROS topic, extras welcome if described (fact 9) | **outputs are the participants' choice; everything needed must be stated in the algorithm and launch descriptions** → README "What to look at", ALGORITHM.md §4 / §4b |
| 7. remote demo, duration | remote demo acceptable, organizers run the solution themselves (fact 23) | the duration was withdrawn by the team on 24.09 (organisational) |

## 3. What changed in the code because of this session (v0.6)

* gauge = the 2.1 × 3.0 m envelope, advisory zone 0.35 m wider (fact 1);
* low-object stage for objects down to 10 cm on the bed (fact 2);
* no shape-based demotion of objects hanging near the track axis (fact 3);
* synthetic catalogue: `lowbox` (0.3×0.3×0.1 m), `box0.3`, `cable`, `cable_low` (facts 2–4);
* mount auto-calibration + mount launch parameters (fact 7);
* `/resense/decision`, `/resense/clear_distance`, `/resense/health` (facts 9, 14);
* the object on the rails of `doubleT_obstacle` labelled (fact 8);
* after the written answers of 23.09 (v0.6.1): the node takes either (topic, frame) pair, switches
  between recordings played one after another and restarts the detector for each; the README
  describes the launch pipeline (`ros2 bag play` from a console → the node → the topics).
