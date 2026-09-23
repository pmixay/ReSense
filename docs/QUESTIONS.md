# Вопросы организаторам (кейс 05, команда ReSense) — открытые

Owner: P1 (captain). Only the questions that are **still unanswered** are here; everything the
organizers have answered (the Q&A session of 22.09, the written answers of 23.09, the hand-outs)
is recorded in [`organizers/answers.md`](organizers/answers.md). The text below is ready to send
as one message to the case moderator (Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or to
info.leaders@develop.mos.ru. When an answer comes, move it to `organizers/answers.md` and delete
the question here.

Status (23.09): three questions open — what is left of our questions 3, 4 and 7 of 21.09 after
the two rounds of answers (nothing about them was said in the Q&A session or in writing).

---

Здравствуйте! Команда ReSense, кейс 05 (посторонние объекты в тоннеле метро по 3D-лидару).
Спасибо за сессию вопросов и за письменные ответы от 23.09 — они закрыли почти всё. Остались
три вопроса, на которые мы не нашли ответа:

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

Спасибо!

---

## Why each question matters (for the team)

| # | was | answer goes to | consequence for the code / plan |
|---|---|---|---|
| 1 | 21.09 item 3 (the mount part is answered: variable, set in the launch parameters) | [`SENSOR.md`](SENSOR.md) §2 (dual return, defaults), `resense/sensor.py`, `resense inject`, [`DATASET.md`](DATASET.md) "Point budget" | the return mode decides how duplicate points are merged and the point budget at range; another resolution or window changes the points per object by up to 2× per axis, i.e. the long-range numbers of EXPERIMENTS.md §2d; the node already handles both layouts |
| 2 | 21.09 item 4 | [`SENSOR.md`](SENSOR.md) §2 (clock), `resense/io.py`, `detector_node.py` "Input handling" | with synchronised per-point time an intra-frame deskew becomes possible; the node's detection of a new recording relies on jumps of `header.stamp`, which a synchronised clock would change (not break) |
| 3 | 21.09 item 7 (the demo part is answered: remote demo acceptable, the organizers run every solution themselves) | [`PRESENTATION.md`](PRESENTATION.md), [`SUBMISSION.md`](SUBMISSION.md) | slide count and how long the live demo segment can be |
