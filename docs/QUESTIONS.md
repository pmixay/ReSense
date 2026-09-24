# Вопросы организаторам (кейс 05, команда ReSense) — открытые

Owner: P1 (captain). Only the questions that are **still unanswered** are here; everything the
organizers have answered (the Q&A session of 22.09, the written answers of 23.09 and 24.09, the hand-outs)
is recorded in [`organizers/answers.md`](organizers/answers.md). The text below is ready to send
as one message to the case moderator (Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or to
info.leaders@develop.mos.ru. When an answer comes, move it to `organizers/answers.md` and delete
the question here.

Status (24.09, evening): two questions open, both from the organizers' synthetic-obstacle
recording of 24.09 ([`DATASET.md`](DATASET.md) "Synthetic-obstacle recording",
[`P4_AUDIT.md`](P4_AUDIT.md)). The return-mode and time questions were answered on 24.09
([`organizers/answers.md`](organizers/answers.md) §3). The question on the length of the talk
and the demo was withdrawn as an organisational matter.

---

Здравствуйте! Команда «Молоток» (решение ReSense), кейс 05 (посторонние объекты в тоннеле метро по 3D-лидару).
Спасибо за ответы про режим возврата и синхронизацию времени. По синтетическому бэгу
`cloud_with_fake_obj` у нас осталось два вопроса:

1. **Система координат габарита в синтетической проверке.** Вы ответили, что лидар стоит на
   1075 мм над головкой рельса ровно посередине состава, и в бэге `cloud_with_fake_obj` объекты
   действительно поставлены от оси лидара (Y = 0). Но рельсы в этой записи идут под углом 0,24°
   к оси лидара: на 25 м расхождение 0,1 м, на 100 м — 0,4 м. Из-за этого «0,3 м за пределами
   габарита, но близко» по рельсам оказывается внутри габарита, а «2х2 скраю в пределах
   габарита» — снаружи. В контрольной проверке габарит отсчитывается от оси лидара (то есть
   поезда) или от оси пути (рельсов)?
2. **«2х2 сверху габарита».** Низ этого объекта — на 2,4–2,9 м над головкой рельса, то есть
   он на 0,1–0,6 м заходит в габарит высотой 3,0 м. Это препятствие (должен быть STOP) или
   объект вне габарита (тревоги быть не должно)?

Спасибо!

---

## Why each question matters (for the team)

| # | was | answer goes to | consequence for the code / plan |
|---|---|---|---|
| 1 | new, 24.09 (P4); narrowed by the organizers' mount answer ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md): 1075 mm above the rail head, on the train's centreline, test bags mounted as ours) | [`DATASET.md`](DATASET.md) "Synthetic-obstacle recording", `labels/cloud_with_fake_obj.json` (`in_gauge`), `resense/track.py` | if the envelope is taken from the LiDAR's axis, the corridor near the train should follow the sensor's Y = 0 rather than the rail fit; four of the ten test objects change sides of the edge. (The part about objects moving independently of the train was withdrawn on 24.09: they stand still in the tunnel, EXPERIMENTS.md "Train speed") |
| 2 | new, 24.09 (P4) | `labels/cloud_with_fake_obj.json` (`big_above`), P4_AUDIT "Organizer synthetic-obstacle recording" | labelled inside now; if it must not alarm, its 12 STOP frames become false alarms and the `elevated` experiment goes the wrong way |
