# Вопросы организаторам (кейс 05, команда ReSense)

Owner: P1 (captain). Sprint 0 item 4 of [`CAPTAIN.md`](CAPTAIN.md) plus the sensor questions from
[`SENSOR.md`](SENSOR.md) §4. The text below is ready to send as one message to the case moderator
(Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or to info.leaders@develop.mos.ru; the
English notes after each block say why we ask and where the answer goes. Record the answers in
[`DATASET.md`](DATASET.md) (data), [`SUBMISSION.md`](SUBMISSION.md) (submission), [`SENSOR.md`](SENSOR.md)
(sensor) and move the question to the "Closed" table at the end of this file.

Status: **sent; answered 22.09 by the organizers' recorded Q&A session** — questions 1, 2, 3,
5, 6 and 7 are answered there (transcript and summary:
[`organizers/QA_session.md`](organizers/QA_session.md), table "Answers to the questions in
docs/QUESTIONS.md"); question 4 (PTP / GNSS time sync) was not addressed and stays open. The
answers are recorded in the "Closed (22.09, Q&A session)" table below; the message text is kept
for the record.

---

Здравствуйте! Команда ReSense, кейс 05 (посторонние объекты в тоннеле метро по 3D-лидару).
Спасибо за руководство по лидару, данные о стенде и новую запись `new_data` — мы их
разобрали. Осталось несколько вопросов по данным и оценке; если получится ответить только на
часть — самые важные для нас **1, 2 и 6**.

**Данные и контрольная запись**

1. Запись `new_data` (20 минут, 221 файл): есть ли в ней постановочные препятствия? Если да —
   какие объекты, в каких файлах `new_data_<N>.db3` / на каких секундах записи и на каком
   расстоянии они появляются; будет ли разметка и в каком формате? Если это только фон
   (поездка без препятствий) — планируется ли запись с препятствиями до контрольной? В
   выданных записях внутри габарита препятствий нет (только человек, переходящий путь в
   `doubleT_obstacle`), поэтому пока все положительные примеры у нас синтетические.
2. Контрольная запись: верно ли, что она будет такой же, как `new_data` и пять из шести первых
   записей — топик `/lidar_points`, `frame_id` `hesai_lidar`, окно 120° (1200 столбцов),
   хранение sqlite3 (при необходимости разбитое на файлы)? Одна из выданных записей
   (`doubleT_obstacle`) отличается: `/sensing/lidar/hesai128/pointcloud`, `lidar_livox`,
   полный оборот 360° — стоит ли ожидать и такой вариант?
3. Настройки лидара и установка: какой режим возврата включён в записях — по данным
   (дублирующиеся точки у лучей с одним отражением) похоже на dual *Last and First*, хотя по
   умолчанию у Pandar128 *Last and Strongest*; будет ли контрольная запись в том же режиме
   (High Resolution, 0.1°, то же окно)? Какова высота и наклон установки на поезде и смещение
   относительно оси пути? В выданных записях два разных крепления (полотно на 1.5 м и на
   2.0 м ниже сенсора) — мы самокалибруемся по рельсам, но число поможет для синтетики.
4. Время: будет ли на поезде PTP/GNSS-синхронизация лидара? Во всех записях, включая
   `new_data`, поле `timestamp` в точках — эпоха 2000 года (не синхронизировано), поэтому мы
   используем время записи bag-файла.
5. Сценарии контрольных данных: `new_data` — это поездка с семью остановками, станциями,
   стрелкой и кривыми; контрольная запись будет похожей? Какие препятствия ожидаются
   (человек, ящик, инструмент, тележка, …) и на каких дальностях; считается ли препятствием
   человек на платформе или рядом с путём вне габарита?

**Оценка и демонстрация**

6. Как оценивается результат: по топикам (какие сообщения удобнее вашему пайплайну —
   `vision_msgs/Detection3DArray`, флаг + расстояние, свой тип), по логам или по
   визуализации? Как измеряются дальность обнаружения и ложные срабатывания — по кадрам,
   по событиям, по времени? В какой системе координат ожидается положение препятствия?
7. Демонстрация в реальном времени через удалённый рабочий стол: чей стенд и какая
   платформа (наш экран через Zoom/Meet, или доступ к вашему стенду)? Сколько минут на
   выступление и демо?

Спасибо!

---

## Why each question matters (for the team)

| # | answer goes to | consequence for the code / plan |
|---|---|---|
| 1 | `DATASET.md` "Extended dataset", `labels/`, P4 labelling | decides whether real recall numbers exist by 29.09 or synthetic stays the only positive set; the 102 v0.5 events on `new_data` are false alarms only if nothing was staged |
| 2 | `DATASET.md` "Topic and sensor", `detector_node.py` defaults | the node auto-discovers PointCloud2 topics and the RViz layout must not hard-code the frame; a confirmed name lets us pin it |
| 3 | `SENSOR.md` §2 (dual return, defaults), `resense/sensor.py`, `resense inject` | return mode decides how duplicates are merged and the point budget; mount height/pitch calibrates the synthetic injector and the expected-point prior |
| 4 | `SENSOR.md` §2 (clock), `resense/io.py` | with synchronised per-point time an intra-frame deskew from the detector's own motion estimate becomes possible; without it the bag time stays the only clock |
| 5 | `EVALUATION.md` §1 (set H), `EXPERIMENTS.md` hard cases | tells P3 which false-alarm classes to prioritise (platforms vs gates vs curves) |
| 6 | `detector_node.py` topics (frozen contract in `CAPTAIN.md` §2) | add a message type if they name one; never rename the existing topics |
| 7 | `PRESENTATION.md`, README "remote demo" runbook | Foxglove-bridge path vs screen share |

## Closed (22.09)

| was asked | how it closed | recorded in |
|---|---|---|
| lidar model and specifications | organizers' hand-out: the Pandar128E3X user manual (Hesai doc 128-en-240710) — model confirmed, every number re-checked | [`SENSOR.md`](SENSOR.md), the PDF in [`sensor/`](sensor/) |
| will there be an extended dataset, when, how many recordings | organizers' hand-out: `new_data.zst`, one 20-minute recording, 221 split files, no labels | [`DATASET.md`](DATASET.md) "Extended dataset", `extended_dataset_intake.json` |
| GPU / CUDA on the test stand | organizers' hand-out: `nvidia-smi` and `dpkg` state of the stand (driver 580, CUDA 13 runtime, toolkit 12.9); ReSense does not use it | [`organizers/test_stand_software.md`](organizers/test_stand_software.md) |
| train speed, odometry or IMU topic on the train | **team decision: train-speed data is not technically possible for this case — the solution operates without it.** The deliverable is the no-speed path (single-frame detection + persistence in time); the node's `ego_speed_mps` / `speed_topic` / `odom_topic` inputs stay as optional extras and the multi-frame accumulation stays off unless a speed is given | [`SENSOR.md`](SENSOR.md) §4, [`CAPTAIN.md`](CAPTAIN.md) finding 7, `ARCHITECTURE.md` |
| intermediate submission (date, form, where), final submission (image vs Dockerfile, size, video), test-stand procedure (launch, internet at build, bag playback, disk) | organisational — the team handles these itself, not a question to the organizers | [`SUBMISSION.md`](SUBMISSION.md), README "Where the data lives" / demo runbook |
| may the given recordings be used for tuning parameters | answered 22.09: yes, acceptable | — |
| own slides after the template's 7–11 | answered 22.09: yes, acceptable | [`PRESENTATION.md`](PRESENTATION.md) |

## Closed (22.09, the organizers' Q&A session)

Source: [`organizers/QA_session.md`](organizers/QA_session.md) (timestamps there).

| was asked | answer | recorded in / consequence |
|---|---|---|
| 1. staged obstacles in `new_data`, labels | none: "all we can give is more empty tunnel"; no labels exist; the hidden check adds the organizers' own **synthetic obstacles** | `DATASET.md` "Extended dataset"; every `new_data` alarm is a false alarm; synthetic evaluation (set F) |
| 2. control-bag format | same conditions as the provided data, the LiDAR mount of the empty-tunnel rides; **full-ride recordings** in other tunnels too | node keeps topic auto-discovery; no map-based logic |
| 3. return mode, mount height / pitch / offset | the LiDAR position "is not fixed, differs even in the provided clouds, not yet approved — count on a variable position, set it in the launch parameters" | `resense/calibration.py` + mount launch arguments |
| 5. which obstacles, which ranges, person on a platform | anything inside the **2.1 m × 3.0 m train envelope**, at least **30 × 30 × 10 cm**; **broken hanging cables must be detected**; a person on a platform is not an obstacle unless inside the envelope; range: < 100 m rated poorly, farther is better, the visible limit in a curve is acceptable | `gauge.profile`, `resense/lowobj.py`, signature changes (ALGORITHM.md §3.2–3.3c) |
| 6. evaluation format | "can we go / obstacle or not / distance", any ROS topic, per-frame yes/no is enough, extra logic must be described | `/resense/decision`, `/resense/clear_distance`, README "What to look at" |
| 7. remote demo | acceptable, but the organizers run every solution themselves | README demo sections unchanged |
| (new) speed | 80 km/h regulated; plan for 85 km/h = 2.3 m between frames | tracker gate 25 m/s covers it |
| (new) the obstacle recording | besides the person, **an object lies on the rails** where the person stands | labelled (`labels/doubleT_obstacle.json`, `object_on_rail`) |
| 4. PTP / GNSS time sync | not answered | open; bag receive time remains the clock |
