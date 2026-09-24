# Вопросы организаторам (кейс 05, команда ReSense) — открытые

Owner: P1 (captain). Only the questions that are **still unanswered** are here; everything the
organizers have answered (the Q&A session of 22.09, the written answers of 23.09, the hand-outs)
is recorded in [`organizers/answers.md`](organizers/answers.md). The text below is ready to send
as one message to the case moderator (Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or to
info.leaders@develop.mos.ru. When an answer comes, move it to `organizers/answers.md` and delete
the question here.

Status (24.09): five questions open. Questions 1–3 are what is left of our questions 3, 4 and 7
of 21.09 after the two rounds of answers (nothing about them was said in the Q&A session or in
writing). Questions 4 and 5 come from the organizers' synthetic-obstacle recording of 24.09
([`DATASET.md`](DATASET.md) "Synthetic-obstacle recording", [`P4_AUDIT.md`](P4_AUDIT.md)).

---

Здравствуйте! Команда «Молоток» (решение ReSense), кейс 05 (посторонние объекты в тоннеле метро по 3D-лидару).
Спасибо за сессию вопросов и за письменные ответы от 23.09 — они закрыли почти всё. Остались
несколько вопросов, на которые мы не нашли ответа:

1. **Настройки лидара в контрольных данных.** Какой режим двойного возврата включён в записях?
   По данным это похоже на *Last and First* (у лучей с одним отражением точка записана дважды),
   хотя по умолчанию у Pandar128 стоит *Last and Strongest*. Будут ли в контрольных данных тот
   же режим возврата, режим High Resolution (0,1°) и то же окно по азимуту? В выданных записях
   пара `/lidar_points` + `hesai_lidar` — это окно 120°, а пара
   `/sensing/lidar/hesai128/pointcloud` + `lidar_livox` — полный оборот 360°: сохранится ли это
   соответствие в контрольных данных?
2. **Время.** Будет ли на поезде синхронизация лидара по PTP/GNSS? Во всех записях и
   `header.stamp`, и поле `timestamp` точек идут в эпохе 2000 года (часы лидара не
   синхронизированы), поэтому мы опираемся на время записи бэга и на разность штампов между
   кадрами.
3. **Защита.** Сколько минут отводится на выступление и на демонстрацию?
4. **Система координат габарита в синтетической проверке.** В бэге `cloud_with_fake_obj`
   объекты поставлены от оси лидара (Y = 0), а рельсы в этой записи идут под углом 0,24° к
   ней: на 25 м расхождение 0,1 м, на 100 м — 0,4 м. Из-за этого «0,3 м за пределами габарита,
   но близко» по рельсам оказывается внутри габарита, а «2х2 скраю в пределах габарита» —
   снаружи. Относительно чего задан габарит в контрольной проверке: оси лидара или оси пути
   (рельсов)? Будут ли в контрольных данных объекты двигаться независимо от поезда, как в этом
   бэге (подъезжают со скоростью 14–20 м/с, пока поезд стоит или сдаёт назад)?
5. **«2х2 сверху габарита».** Низ этого объекта — на 2,4–2,9 м над головкой рельса, то есть
   он на 0,1–0,6 м заходит в габарит высотой 3,0 м. Это препятствие (должен быть STOP) или
   объект вне габарита (тревоги быть не должно)?

Спасибо!

---

## Why each question matters (for the team)

| # | was | answer goes to | consequence for the code / plan |
|---|---|---|---|
| 1 | 21.09 item 3 (the mount part is answered: variable, set in the launch parameters) | [`SENSOR.md`](SENSOR.md) §2 (dual return, defaults), `resense/sensor.py`, `resense inject`, [`DATASET.md`](DATASET.md) "Point budget" | the return mode decides how duplicate points are merged and the point budget at range; another resolution or window changes the points per object by up to 2× per axis, i.e. the long-range numbers of EXPERIMENTS.md §2d; the node already handles both layouts |
| 2 | 21.09 item 4 | [`SENSOR.md`](SENSOR.md) §2 (clock), `resense/io.py`, `detector_node.py` "Input handling" | with synchronised per-point time an intra-frame deskew becomes possible; the node's detection of a new recording relies on jumps of `header.stamp`, which a synchronised clock would change (not break) |
| 3 | 21.09 item 7 (the demo part is answered: remote demo acceptable, the organizers run every solution themselves) | [`PRESENTATION.md`](PRESENTATION.md), [`SUBMISSION.md`](SUBMISSION.md) | slide count and how long the live demo segment can be |
| 4 | new, 24.09 (P4) | [`DATASET.md`](DATASET.md) "Synthetic-obstacle recording", `labels/cloud_with_fake_obj.json` (`in_gauge`), `resense/track.py` | if the envelope is taken from the LiDAR's axis, the corridor near the train should follow the sensor's Y = 0 rather than the rail fit; four of the ten test objects change sides of the edge. Objects that move independently of the train also rule out testing accumulation on their data |
| 5 | new, 24.09 (P4) | `labels/cloud_with_fake_obj.json` (`big_above`), P4_AUDIT "Organizer synthetic-obstacle recording" | labelled inside now; if it must not alarm, its 12 STOP frames become false alarms and the `elevated` experiment goes the wrong way |
