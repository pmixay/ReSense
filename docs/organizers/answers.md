# Organizers' Answers

> **Purpose:** every answer the organizers gave to our questions (case 05), verbatim where it was
> written, and what each answer changed in ReSense.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN, the answers verbatim in RU
> **Last verified:** 2026-10-19: §11 — the open questions and O1 were sent by the captain (reported 19.10), no reply yet;
> 2026-10-16: §10 added (live Q&A and the experts' message of 16.10, as relayed by the team);
> 2026-09-29: §9 against the sealed detector's `gauge.*` settings and the labels
> of `cloud_with_fake_obj` · **Status:** current

Everything the organizers answered to the questions of [`../QUESTIONS.md`](../QUESTIONS.md),
from these sources:

* the recorded **Q&A session of 22.09**: summary with timestamps in
  [`QA_session.md`](QA_session.md), transcript in
  [`QA_session_transcript_ru.md`](QA_session_transcript_ru.md);
* the **written answers of 23.09 and 24.09**, verbatim below;
* the experts' answers on the LiDAR mount and switches in
  [`mount_and_switch_qa.md`](mount_and_switch_qa.md), recorded 24.09, consolidated in §5;
* the **hand-outs of 22.09**: sensor manual, extended dataset, test-stand software;
* the **organizers' statement of 25.09** on access to the test stand, reported by the captain, §6;
* the **organizers' statement of 25.09** that the test machine has no internet access, reported
  by the captain, §7;
* the **organizers' statement of 25.09** that the upload form takes links and has no file-size
  limit, reported by the captain, §8;
* the **organizers' answer of 25.09** to our Q3 (a 30 × 30 × 10 cm object lying on the bed between
  the rails is not an obstacle), reported by the captain, §8;
* the **organizers' written answer of 29.09** to our Q1 and Q2 (the envelope's reference and the
  accuracy of the synthetic objects), passed on by the team, §9.
* the **live Q&A of 16.10** and the **experts' general message to the finalists** of the same day, both relayed by
  the team (not recorded verbatim by us), §10.

The questions that are still open are in [`../QUESTIONS.md`](../QUESTIONS.md)
(five since 16.10: how `CAUTION` is read, the object types and scenes of the hidden set, what "the filter" is,
what the new data look like, how the bags will be played). They and the O1 pitch/update/re-run message were
**sent by the captain** (reported 19.10; the exact send date was not recorded); no reply yet (§11).

## 1. Answers by question (Q&A session 22.09 + written answers 23.09)

| # | our question | Q&A session, 22.09 ([`QA_session.md`](QA_session.md)) | written answer, 23.09 | status | consequence in ReSense |
|---|---|---|---|---|---|
| 1 | staged obstacles in `new_data`, labels, a recording with obstacles before the control run? | none: "all we can give is more empty tunnel"; no labels exist; no more data with obstacles; the hidden check adds the organizers' own **synthetic obstacles** | **"В new_data препятствий нет"** — no obstacles | **closed** | every `new_data` alarm is a false alarm; synthetic positives ray-cast into the moving ride (set F); the injector follows the organizers' definitions |
| 2 | control-bag format: topic, frame id, 120° window, sqlite3 — or also the `doubleT_obstacle` variant? | same conditions as the provided data, the LiDAR mount of the empty-tunnel rides; **full rides** through other tunnels too | **both (topic, frame) pairs may occur; one and the same LiDAR; the bag will most likely be played from the console; describe the pipeline if the code reads bags directly** | **closed** | input switching between recordings and per-recording restart (v0.6.1); "How a bag is processed" in the README; no map-based logic |
| 3 | return mode; mount height / pitch / offset | the LiDAR position "is not fixed, differs even in the provided clouds, not yet approved — count on a variable position, set it in the launch parameters" | 24.09: **Last and Strongest now**; the provided recordings (especially the one with people) are old and may have used another mode; **the control data will have all the same settings**; mount (experts, recorded 24.09, §5): **the test bags use the same positions as the provided ones; the LiDAR is 1075 mm above the rail head, on the train's centreline** | **closed** (§3, §5) | `resense/calibration.py` (orientation + tilt from rails and bed) and the mount launch arguments; the detector counts occupied voxels, so duplicated returns change no decision |
| 4 | PTP / GNSS time sync on the train | not answered | 24.09: **there will be, but not within this hackathon**; work with what there is | **closed** (§3) | the header stamps (sensor clock, year-2000 epoch) and the bag receive time remain the clocks; no deskew |
| 5 | which obstacles, which ranges, a person on a platform | anything inside the **2.1 m × 3.0 m train envelope**, at least **30 × 30 × 10 cm**; **broken hanging cables must be detected**; people, animals, objects thrown on the track; a person on a platform is not an obstacle unless inside the envelope; range: < 100 m rated poorly, farther is better, the visible limit in a curve is acceptable | — | **closed** | `gauge.profile` = the envelope, `resense/lowobj.py`, signature changes, far-field rule (ALGORITHM.md §3.2–3.3c) |
| 6 | how is the result evaluated, which messages, which frame | "can we go / obstacle or not / distance", any ROS topic, per-frame yes/no is enough, extra logic must be described | **outputs are the participants' choice; state everything in the algorithm and launch descriptions** | **closed** | `/resense/decision`, `/resense/obstacle_detected`, `/resense/nearest_distance`, `/resense/clear_distance`, `/resense/status`, `/resense/health`, all in README "What to look at" and ALGORITHM.md §4b |
| 7 | remote demo, duration | acceptable, but the organizers run every solution themselves | — | closed for the demo; the duration was **withdrawn by the team on 24.09** as an organisational matter, not a question for the case experts | README demo sections unchanged |
| — | (new, Q&A) train speed | regulated 80 km/h; plan for 85 km/h = 2.3 m between frames; some trains have no odometry | — | noted | tracker gate 25 m/s; the no-speed path is the default, a speed input is optional (EXPERIMENTS.md §2d: 167 m with it in v0.6.2, 177 m in v0.6.1); our LiDAR-only estimate, measured 24.09, is accurate but buys nothing on the organizers' check (EXPERIMENTS.md §9) |
| — | (new, Q&A) the obstacle recording | besides the person, **an object lies on the rails** where the person stands | — | noted | labelled (`labels/doubleT_obstacle.json`, `object_on_rail`) |
| — | (new, Q&A) evaluation environment, run conditions | the spec's test stand (i7-9700E, RTX 4070 Ti SUPER); offline; "the less magic the better — `docker run`, `ros2 launch`, check"; compute is a tie-breaker | — | noted | CPU-only image, no network at run time, one launch command |

## 2. Written answers (23.09)

Verbatim, numbered as our questions of 21.09 (the original message is in the git history of
`docs/QUESTIONS.md`: 1 = staged obstacles in `new_data`, 2 = control-bag format, 6 = evaluation
format):

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
| 1 | `new_data` contains **no obstacles** (confirms the Q&A session) | every alarm on the ride is a false alarm, as counted in EXPERIMENTS.md §0 (v0.6.2: 47 events, 3.6 per km; v0.6.1: 82, 6.3 per km); the person-like ride tracks we checked by eye (v0.6) are infrastructure; positives stay synthetic (set F) plus the person and the object on the rail of `doubleT_obstacle` | [`DATASET.md`](../DATASET.md) "Extended dataset", [`EXPERIMENTS.md`](../archive/EXPERIMENTS_log_2026-09.md) §1d, `labels/new_data_objects.json` |
| 2 | the control data **may contain both (topic, frame) pairs** — `/lidar_points` + `hesai_lidar` and `/sensing/lidar/hesai128/pointcloud` + `lidar_livox`; **all data were recorded with the same LiDAR**; the storage format matters little — they will most likely **play the bag from the console**; a solution that reads bag files directly must describe its launch pipeline | (a) the node already listened to both names and auto-discovers others; **v0.6.1 also switches between them when one recording follows another in the same running node**, restarts the detector (scene state and mount calibration) for every new recording — a new topic, a new frame id, or header stamps that jump — and keeps discovering topics while the input is silent (`tests/test_node.py`); (b) the one physical LiDAR is why the `doubleT_obstacle` full turn and the 120° window of the other bags are the same sensor settings seen through two drivers / mounts — the auto-calibration handles the mount; (c) **our solution does not read bag files**: it subscribes to the topic, so `ros2 bag play <bag>` from any console on the same ROS 2 network (or inside our image, which has the sqlite3 and mcap storage plugins) is the whole pipeline; the offline CLI that does read `.db3` files is a development tool, described separately | [`README.md`](../../README.md) "How a bag is processed", `detector_node.py` "Input handling", [`DATASET.md`](../DATASET.md) "Topic and sensor" |
| 6 | **the outputs are ours to choose**; everything needed must be stated in the algorithm description and in the launch description | the outputs are specified in one place for the jury (README "What to look at": decision, obstacle flag, distance, verified-clear distance, full JSON status, health) and in ALGORITHM.md §4 / §4b (how each is computed); the launch description names every topic and parameter | [`README.md`](../../README.md) "What to look at", "Topics published by the node"; [`ALGORITHM.md`](../ALGORITHM.md) §4, §4b |

## 3. Written answers (24.09)

Verbatim, numbered as items 1 and 2 of the message in [`../QUESTIONS.md`](../QUESTIONS.md) at
that time (item 1 = return mode, resolution and azimuth window of the control data; item 2 = PTP
/ GNSS time on the train). Item 3 of that message (the length of the talk and the demo) was
withdrawn by the team as an organisational matter.

> 1\) Сейчас стоит Last And Strongest, но записи с бэгов (особенно та, на которой ходят люди)
> были сделаны давно и режим мог быть другой. В контрольных данных будут все те же настройки
>
> 2\) Будет, но не в рамках задачи на этот хакатон. Сейчас работаем с тем, что есть

| # | answer (English) | consequence | where |
|---|---|---|---|
| 1 | the LiDAR is set to **Last and Strongest now**. The provided recordings, **especially the one with people walking** (`doubleT_obstacle`), were made long ago and may have used another mode. **The control data will have all the same settings.** | Measured on 24.09 (P4), 12 frames per recording: in all six original bags and in the newest one (`cloud_with_fake_obj`), 96–98 % of the points come in identical pairs, i.e. ~49 % of the points are copies and a frame holds 85–95 k distinct points (175 k in the 360° `doubleT_obstacle`). The return blocks of those recordings hold one echo twice, whatever the mode was called. A true Last and Strongest recording would add second echoes where a ray has two (dust, edges, thin objects); it cannot remove any. The detector's point bars count occupied voxels, not points (`cluster.min_points`, `gauge_min_points` against `n_vox`), so copies change no decision. The control data use the same settings, so nothing changes in the code | [`../SENSOR.md`](../SENSOR.md) §2, [`../DATASET.md`](../DATASET.md) "Topic and sensor" |
| 2 | PTP / GNSS time **will exist on the train, but not for this hackathon**; work with what there is | the clocks stay as they are: the bag receive time and the differences of `header.stamp` between frames (year-2000 sensor clock); no intra-frame deskew | [`../SENSOR.md`](../SENSOR.md) §2 and §3 item 4, `resense/io.py`, `detector_node.py` "Input handling" |

## 4. Closed by hand-outs and team decisions (22.09)

| was asked | how it closed | recorded in |
|---|---|---|
| lidar model and specifications | organizers' hand-out: the Pandar128E3X user manual (Hesai doc 128-en-240710) — model confirmed, every number re-checked | [`SENSOR.md`](../SENSOR.md), the PDF in [`sensor/`](../sensor) |
| will there be an extended dataset, when, how many recordings | organizers' hand-out: `new_data.zst`, one 20-minute recording, 221 split files, no labels | [`DATASET.md`](../DATASET.md) "Extended dataset", `extended_dataset_intake.json` |
| GPU / CUDA on the test stand | organizers' hand-out: `nvidia-smi` and `dpkg` state of the stand (driver 580, CUDA 13 runtime, toolkit 12.9); ReSense does not use it (evaluated 24.09 and rejected: ARCHITECTURE.md "GPU: evaluated, not used") | [`organizers/test_stand_software.md`](test_stand_software.md) |
| train speed, odometry or IMU topic on the train | **organizers' fact** (Q&A 22.09, fact 6): no odometry in the recordings, some trains have none. **Team decision** (22.09): "train-speed data is not technically possible for this case", so the solution operates without it. The deliverable is the no-speed path (single-frame detection + persistence in time); the node's `ego_speed_mps` / `speed_topic` / `odom_topic` inputs stay as optional extras and the multi-frame accumulation stays off unless a speed is given. 24.09: the LiDAR-only estimator was measured accurate, but even a perfect speed does not improve the organizers' check, so it stays opt-in ([`EXPERIMENTS.md`](../archive/EXPERIMENTS_log_2026-09.md) §9) | [`SENSOR.md`](../SENSOR.md) §4, [`CAPTAIN_log_2026-09.md`](../archive/CAPTAIN_log_2026-09.md) finding 7, `ARCHITECTURE.md` |
| intermediate submission (date, form, where), final submission (image vs Dockerfile, size, video), test-stand procedure (launch, internet at build, bag playback, disk) | organisational — the team handles these itself, not a question to the organizers; 25.09: the team gets no run on the stand before submission (§6), the stand has no internet, so the image goes as a `docker load` archive (§7), and the upload form takes links with no size limit (§8); the organizers' timeline has no intermediate stage ([`README_organizers.md`](README_organizers.md) "Ключевые этапы конкурса"), so no separate intermediate upload is made ([`../archive/CAPTAIN_board_2026-09-28.md`](../archive/CAPTAIN_board_2026-09-28.md) C14); the submission itself is handled by the captain personally (25.09, C12) | [`../archive/CAPTAIN_board_2026-09-28.md`](../archive/CAPTAIN_board_2026-09-28.md) C12, C14, README "Where the data lives" / demo runbook |
| may the given recordings be used for tuning parameters | answered 22.09: yes, acceptable | — |
| own slides after the template's 7–11 | answered 22.09: yes, acceptable | [`PRESENTATION.md`](../PRESENTATION.md) |

## 5. Experts' answers on the LiDAR mount and switches (recorded 24.09)

Verbatim from [`mount_and_switch_qa.md`](mount_and_switch_qa.md) (questions as the team passed them
on; the date of the answers is not given; recorded in `41b7ae7`, 24.09).

| # | our question | answer (verbatim) | answer (English) | consequence in ReSense |
|---|---|---|---|---|
| 1 | will the mount position be passed to the algorithm, or found from the cloud every time? | «Лучше, если позиция будет определяться автоматически. Если нет - то в конфиг мы всё, что надо пропишем.» | automatic detection is preferred; otherwise the organizers write what is needed into the config | mount auto-calibration stays on (`calibration.enabled`); the mount launch arguments stay (`sensor_forward/left/up`, `mount_roll/pitch/yaw_deg`, `auto_calibrate`) |
| 2 | the range of possible positions and orientations (x, y, z, roll, pitch, yaw)? | «В тестовых бэгах позиции такие же, как в тех, что мы предоставили вам.» | the test bags use the same positions as the provided ones | the two mounts in the data (the empty-tunnel rides and `doubleT_obstacle`) cover the test bags; the calibration stays as a safeguard |
| 3 | will the LiDAR height above the rail head be known? | «Я же уже писал, что лидар установлен в 1075 мм над головкой рельса и ровно посередине состава.» (common answer to questions 3–4) | 1075 mm above the rail head, exactly on the train's centreline | the calibration measures 1.12 m and −0.02 m lateral on `roundT_doubleT` (4.5 cm from the answer) and 1.51 m on the older `doubleT_obstacle` mount; whether the envelope follows the LiDAR's axis or the rails was our Q1, answered 29.09: the rails (§9) |
| 4 | will the orientation relative to the train's longitudinal axis be known? | the common answer to questions 3–4 above; no numeric orientation is given | no orientation value | roll, pitch and yaw keep coming from the calibration |
| 5 | switches: without the switch state, is an obstacle on only one branch an obstacle (union of the possible paths or the chosen branch)? | «Сейчас состояния стрелок неизвестны, поэтому если решение будет глючить на стрелках - то мы не будем учитывать это как минус.» | switch states are unknown; glitches at switches will not count against the solution | station and platform false STOPs come before switch ones in P3's work ([`../CAPTAIN.md`](../CAPTAIN.md) §9) |

## 6. Access to the test stand (25.09, reported by the captain)

The captain reported on 25.09 what the organizers said: the team will **not** be able to test on
the organizers' machine, the test stand of spec §3.1 (i7-9700E, RTX 4070 Ti SUPER,
[`test_stand_software.md`](test_stand_software.md)), before submitting the solution. No written
text; the captain's instruction was to remove the stand from the questions and the requirements.

| date | reported by | organizers' statement | status | consequence in ReSense |
|---|---|---|---|---|
| 25.09 | the captain (P1) | no access to the test stand before submission: nothing can be built, run or timed on the organizers' machine by the team | **closed** | every stand run is dropped from the plan ([`../archive/CAPTAIN_board_2026-09-28.md`](../archive/CAPTAIN_board_2026-09-28.md) C8, actions 7 and 15; README "Acceptance test and CI"); the substitute is the team's own 8-core machine (the "8-core analogue": timing on the native and numpy paths, the dry run with the latency and drop criteria) and CI (the `docker` job builds the image and plays synthetic bags through the node as the organizers will); the stand's hardware stays the machine the jury will use, so its facts and the estimates made for it stay in the docs, labelled as such; no stand question is left in [`../QUESTIONS.md`](../QUESTIONS.md) |

## 7. No internet on the test machine (25.09, reported by the captain)

The captain reported on 25.09 what the organizers said: **the test machine has no internet
access**. No written text. The Q&A of 22.09 had said that the system "must work offline"
([`QA_session.md`](QA_session.md) fact 10), which we had read as run time only; this statement
covers the whole machine, the image build included. With §6 we cannot try anything on it first.

| date | reported by | organizers' statement | status | consequence in ReSense |
|---|---|---|---|---|
| 25.09 | the captain (P1) | the test machine, the stand of spec §3.1, has no internet access | **closed** | `docker build` cannot work there: it pulls `ros:humble-ros-base-jammy` from Docker Hub, installs ROS and Ubuntu packages with `apt-get` and the pinned wheels (and the build backend) from PyPI. The image is therefore delivered as an archive: `scripts/export_image.sh` → `resense-image-<version>.tar.gz` with its `.sha256`, loaded with `docker load -i` (step 1 of README "Кратко для жюри"; `scripts/load_image.sh` checks the sum and runs the image with `--network none`); the archive is what the jury runs ([`../archive/CAPTAIN_board_2026-09-28.md`](../archive/CAPTAIN_board_2026-09-28.md) C25; the upload is the captain's, C12). Nothing in the node, the launch file, the entrypoint or the compose services uses the network at run time; the dashboard's roslib is now bundled (`web/assets/vendor/`). CI proves the chain: the built image goes through `docker save` → `docker rmi` → `docker load`, then the synthetic bags are played through the node with `--network none` and on an internal Docker network with no way out. An offline `docker build --cache-from` from the archive is a best-effort extra with caveats ([`../ARCHITECTURE.md`](../ARCHITECTURE.md) "Deployment without internet"); the offline dry run, part of the later deployment (CAPTAIN C7, action 15), loads the archive with the network disconnected (`IMAGE_TAR=… OFFLINE=1 scripts/dry_run.sh`) |

## 8. Upload form and the bed object (25.09, reported by the captain)

The captain reported on 25.09 two things the organizers said. No written text. (a) is about the
upload form of i.moscow; (b) answers Q3 of [`../QUESTIONS.md`](../QUESTIONS.md) (the bed / envelope
floor question of the criteria review of 24.09). The captain's words for (b), typos corrected: "no,
this small object isn't in the train's sizes, so it isn't an obstacle"; "the train's sizes" is the
train's clearance envelope (габарит), 2.1 m wide × 3.0 m high ([`QA_session.md`](QA_session.md)
facts 1–2, §1 #5), which the detector measures from the rail head.

| date | reported by | organizers' statement | status | consequence in ReSense |
|---|---|---|---|---|
| 25.09 | the captain (P1) | (a) the upload form has **no file-size limit**: the team types **links** into the form | **closed** | nothing is uploaded as a file: the form gets links — the repository with its commit hash, the image archive `resense-image-<version>.tar.gz` and its `.sha256` (§7), the video and the presentation. Which links, and when, is the captain's: he sends the submission himself (25.09, [`../archive/CAPTAIN_board_2026-09-28.md`](../archive/CAPTAIN_board_2026-09-28.md) C12); GitHub releases are deferred (C13). The archive's size (0.49 GiB at gzip -1 in CI) is no longer a constraint on the form; a GitHub release asset holds up to 2 GB per file. Each link must open for a logged-out visitor, and the archive is loaded once on a second machine before submitting ([`../CAPTAIN.md`](../CAPTAIN.md) action 1b) |
| 25.09 | the captain (P1) | (b) a **30 × 30 × 10 cm object lying on the bed between the rails** (below the rail head) is **not an obstacle**: it is not inside the train's clearance envelope | **closed** | the shipped bed policy is the organizers' own: nothing below the envelope floor (0.12 m above the rail head) between the rails is reported ([`../ALGORITHM.md`](../ALGORITHM.md) §3.3b, `gauge.profile`, `lowobj.*` unchanged). The opt-in central near-bed path (`lowobj.near_enabled`, off; [`../EXPERIMENTS.md`](../archive/EXPERIMENTS_log_2026-09.md) §1e) stays off and is no longer an open question: it is not needed for the organizers' check, and its ride and set F re-run is dropped. The criteria judgement's 8.1 hold-down "the 30 × 30 × 10 cm object below the rail head is not detected by default" is answered by the organizers ([`../SCORECARD.md`](../SCORECARD.md) §8; no re-score). Objects that reach the envelope — across a rail, straddling the floor, on a rail head, taller than the floor — are reported as before |

## 9. The envelope's reference and the synthetic objects (written answer, 29.09)

Our Q1 and Q2 of 25.09 (the message is in the git history of [`../QUESTIONS.md`](../QUESTIONS.md))
asked, for the organizers' synthetic-obstacle recording `cloud_with_fake_obj`: (Q1) is the envelope
measured from the LiDAR's (the train's) axis or from the track's (the rails'), given that the rails
of that recording run at 0.24° to the LiDAR's axis; (Q2) is «2х2 сверху габарита», whose bottom is
2.4–2.9 m above the rail head, an obstacle. The answer, verbatim, as the team received it on 29.09:

> Доброе утро!
> Габарит поезда отсчитывается от головки рельсов. Рельсы могут быть под любым углом к лидару.
> Синтетика расставлена условно-приблизительно и может плавать по отношению к габариту вдоль путей.
> Над её точностью мы данный момент работаем и при проверке решенй иучастников будем делать
> поправку на точность синтетики

| # | answer (English) | status | consequence in ReSense |
|---|---|---|---|
| Q1 | the train's envelope is **measured from the rail heads**; the rails **may run at any angle to the LiDAR** | **closed** | the organizers' envelope is the one the detector builds from the rails (`gauge.profile`: \|dy\| ≤ 1.05 m from the fitted track axis, 0.12–3.0 m above the rail-head plane); nothing is measured from the sensor axis in their definition. The shipped `gauge.reference` 3 stays: it is the union of the rails' envelope and the sensor-axis one, so it never narrows the organizers' envelope, and it only widens it within 60 m on straight track by at most `reference_max_offset` = 0.2 m, inside the 0.35 m advisory band, whatever the rail angle (the offset is clipped). Taking it off (`reference` 0) loses measured recall for no measured false-alarm gain: in the matched quality-cycle screens ([`review_fix_d`](../evidence/results/quality_cycle_2026-09-27/screens/review_fix_d.json) vs [`ablation_reference_off`](../evidence/results/quality_cycle_2026-09-27/screens/ablation_reference_off.json)) the real person drops 61 → 58 of 61 frames and set O's edge cube 18 → 2 STOP frames (first STOP 35.0 → 5.2 m), while the ride, the five empty recordings and set O's outside-object false STOPs (6) are identical ([`../DECISIONS.md`](../DECISIONS.md) row 18). The cost the answer defines: an object up to 0.2 m outside the rails' envelope, within 60 m on straight track, can be a STOP. `gauge.axis_union` (off) loses its reason (the sensor-axis frame) and stays off. "Any angle" is what the mount calibration and the per-frame track axis already assume: the envelope follows the fitted rails, not the LiDAR's X axis |
| Q2 | not answered in so many words; it follows from Q1: the envelope's top is 3.0 m **above the rail head** | **closed** (by Q1) | the bottom of #8 «2х2 сверху габарита» is 2.4–2.9 m above the rail head, 0.1–0.6 m inside the 3.0 m envelope: an obstacle. Its label stays `in_gauge: true` and its STOPs (from ~111 m) stay counted as detections. If the organizers meant "must not alarm", the answer's allowance below covers a placement that far from the top edge only loosely; nothing changes in the detector either way |
| — | the synthetic objects are **placed approximately** and **may drift relative to the envelope along the track**; the organizers are improving their accuracy and **will correct for it when checking the solutions** | noted | set O's edge tests (#4 `small_edge_inside`, #5 `small_outside_near`, #6 `big_edge_inside`, #7 `big_outside`) sit within ±0.1–0.4 m of the rails' envelope edge and cross it along the track ([`../DATASET.md`](../DATASET.md) "Synthetic-obstacle recording"). Their labels keep the organizers' intent (`in_gauge`); their in/out results are within the organizers' stated tolerance and are reported, not tuned further. The hidden check's synthetic objects may be placed as loosely: no rule is fitted to an exact synthetic placement |

## 10. Live Q&A and the experts' message to the finalists (16.10, relayed by the team)

On 16.10 the team put ten questions to the organizers live (the list was prepared in the session of 16.10: how
the result is scored, how false alarms are counted, how `CAUTION` is read, how the synthetic objects are inserted,
what the hidden set contains, at what range, which objects, how the solution is launched and measured, whether
ground truth and more data can be had, whether the results will be explained). The answers below are **the
team's short relay in Russian, not the organizers' wording**: treat them as what the team understood, and confirm
anything that matters before relying on it. The experts' general message of the same day is recorded verbatim in
[`../FINALS_BRIEF_2026-10-16.md`](../FINALS_BRIEF_2026-10-16.md) §1.

**What the organizers said about how they scored and what our project needs** (relayed, Russian):
«смотрели на дальность детекции, первый успешный детект препятствия, насколько габарит был устойчивый, количество
ложноположительных / отрицательных срабатываний, совпадает ли с realtime скорость работы алгоритма, насколько хорошо
справлялся фильтр. Удобство запуска тоже важно. Нам в проект: надо улучшить устойчивость габарита, синхронизацию
габарита с поворотом отдельно, не очень хорошо совпадает.»

| # | our question (short) | answer as relayed | status | consequence in ReSense |
|---|---|---|---|---|
| 1 | how is the result scored | «отвечено»: detection range, first successful detect, gauge stability, false positives and false negatives, real-time speed, the filter, ease of launch; feedback: improve gauge stability and the gauge's synchronisation with turns | **closed** | the gauge is a scored object, not only a decision input: [`../FINALS_BRIEF_2026-10-16.md`](../FINALS_BRIEF_2026-10-16.md) (criteria 2–3, card N1); curves: BACKLOG K2; measured: [`../evidence/axis_profile_2026-10-16/`](../evidence/axis_profile_2026-10-16/README.md) |
| 2 | how are false alarms counted against misses | «одинаково с пропущенным»: a false alarm costs the same as a miss | **closed** | a false `STOP` episode is as costly as a missed obstacle: false-alarm work (F1, F2, C1) is as valuable as range work |
| 3 | how is `CAUTION` read (alarm or hint) | «не дали чёткого ответа» | **open** | unchanged: `CAUTION` stays a hint; it is on 43 % of empty frames (judge), so C1 matters whichever way it is read; asked again in [`../QUESTIONS.md`](../QUESTIONS.md) |
| 4 | how are the synthetic objects inserted (fixed in the tunnel or riding with the train; shadow behind them) | no answer: «исследуй по датасету» | investigated | in `cloud_with_fake_obj` the objects stand still in the tunnel and the train approaches them (about 15–20 m/s), so `ego_veto` does not suppress them; the file stops at 250 m, the judge found points up to ~298 m: [`../evidence/axis_profile_2026-10-16/`](../evidence/axis_profile_2026-10-16/README.md) §1; whether the hidden set is the same is not confirmed |
| 5 | what is in the hidden set | «смесь»: real and synthetic | **closed** | both count; we have one real positive, so G3 (held-out battery) matters |
| 6 | at what range | «300 м в идеале» | **closed** | 300 m is the ideal; only large objects have enough returns that far (a 0.3 m cube: 1–2 returns beyond 80 m), and it needs a right axis (K2): [`../evidence/axis_profile_2026-10-16/`](../evidence/axis_profile_2026-10-16/README.md) §2 |
| 7 | which objects and scenes | «нет ответа» | **open** | unchanged; asked again in [`../QUESTIONS.md`](../QUESTIONS.md) |
| 8 | how the solution is launched and measured | not asked (the team judged it unimportant at the time) | not asked | the experts' message of the same day lists four launch requests: [`../FINALS_BRIEF_2026-10-16.md`](../FINALS_BRIEF_2026-10-16.md) §3, card N4 |
| 9 | can ground truth and more data be had | «нельзя» | **closed** | no organizers' labels: our own labels (`labels/`) stay the reference; the extended data they announce (synthetic with a person and dust, a real recording from another lidar) comes by their schedule |
| 10 | will the results be explained afterwards | «сказал» (they said so; the exact promise was not recorded) | **closed, unverified** | confirm what is promised (a per-recording breakdown, or only scores) |

**The experts' message of 16.10** (verbatim in the brief) adds, beyond the criteria: an **extended dataset** with extra
synthetic (a person, simulated dust or suspension) and a **real recording from another lidar** ("account for the
different axis directions"); four launch requests (Docker with graphics, RViz in the container, pause or slow bags from
the console, switch bags without restarting the container). What the shipped system does for each, and the cards that
follow, are in [`../FINALS_BRIEF_2026-10-16.md`](../FINALS_BRIEF_2026-10-16.md) §2–§4.

## 11. O1 and the open questions: pitch format, post-submission updates, results (prepared 15–16.10, sent)

**Sent by the captain; reported in the team session of 19.10.** The exact send date and channel were not
recorded here (add them). **No organizer answer has been received or inferred** as of 19.10.
The messages are in [`../QUESTIONS.md`](../QUESTIONS.md): O1 asks for the pitch/Q&A/demo format, whether
1.1.x may be shown or re-run and affect scores, and whether hidden-check/expert results or another
archive submission are available before 23.10; the five open questions of 16.10 ask how `CAUTION` is read,
which objects and scenes the hidden set has, what "the filter" is, what the new data look like and how the
bags will be played. Since 19.10 the team develops **1.2.0** and will not release 1.1.0 (captain's decision,
[`../DECISIONS.md`](../DECISIONS.md)): an answer about "1.1.x" is read as applying to the updated version.

When a reply arrives, append its dated verbatim text and the resulting decisions here; update
`PRESENTATION.md` and the backlog (§9 of [`../BACKLOG.md`](../BACKLOG.md)).
The current five-minute preparation budget and the submitted v1.0.0 are unchanged assumptions,
not a new answer from the organizers.

