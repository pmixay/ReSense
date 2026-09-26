# Open Questions to the Organizers

> **Purpose:** the questions to the organizers that are still unanswered, as one message ready to
> send, and why each matters.
> **Audience:** P1, team (the message: the organizers) · **Owner:** P1 · **Language:** RU message,
> EN rationale
> **Last verified:** 2026-09-25 against `7290873` · **Status:** current

Only the questions that are **still unanswered** are in the message; everything the organizers
have answered (the Q&A session of 22.09, the written answers of 23.09 and 24.09, the experts'
answers on the mount and switches, the hand-outs, the statements and the Q3 answer of 25.09) is
recorded in [`organizers/answers.md`](organizers/answers.md). The text below goes as one message to
the case moderator (Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or to
info.leaders@develop.mos.ru. When an answer comes, record it in `organizers/answers.md`, delete the
question from the message and list it under "Answered" with a link.

Status (25.09): two questions open, Q1–Q2, **sent by the captain on 25.09**; their answers are
awaited and go to [`organizers/answers.md`](organizers/answers.md) when they come. Q1–Q2 come from the organizers' synthetic-obstacle
recording of 24.09 ([`DATASET.md`](DATASET.md) "Synthetic-obstacle recording",
[`P4_AUDIT.md`](P4_AUDIT.md)). Q3 (the bed / envelope floor) was answered on 25.09 and has left the
message (see "Answered" below). Q1 lost its second sentence on 24.09: it assumed the objects move
independently of the train, which is wrong (they stand still in the tunnel), so an older copy of
the message must not be sent. The return-mode and time questions were answered on
24.09 ([`organizers/answers.md`](organizers/answers.md) §3); the question on the length of the talk
and the demo was withdrawn as an organisational matter. Testing on the organizers' stand is not a
question either: on 25.09 they said the team gets no access to it before submission
([`organizers/answers.md`](organizers/answers.md) §6).

---

Здравствуйте! Команда «Молоток» (решение ReSense), кейс 05 (посторонние объекты в тоннеле метро по
3D-лидару). Спасибо за ответы про режим возврата, синхронизацию времени, установку лидара и объект
на полотне. У нас осталось два вопроса — по синтетическому бэгу `cloud_with_fake_obj`.

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
| 1 | new, 24.09 (P4); narrowed by the organizers' mount answer ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md): 1075 mm above the rail head, on the train's centreline, test bags mounted as ours) | [`DATASET.md`](DATASET.md) "Synthetic-obstacle recording", `labels/cloud_with_fake_obj.json` (`in_gauge`), `resense/track.py` | if the envelope is taken from the LiDAR's axis, the corridor near the train should follow the sensor's Y = 0 rather than the rail fit; four of the ten test objects change sides of the edge. (The part about objects moving independently of the train was withdrawn on 24.09: they stand still in the tunnel and the train drives up to them, [`EXPERIMENTS.md`](EXPERIMENTS.md) §9). Measured 26.09 ([`EXPERIMENTS.md`](EXPERIMENTS.md) §1k): from the sensor axis the four edge tests are exactly the intent (#4 inside in 74 of 83 frames, #6 in 93 of 125, #5 and #7 in none), from the rails not (16, 8, 98, 58). Since 26.09 the detector takes the union of both envelopes within 50 m on straight track, so the answer 'from the sensor axis' is covered near the train; the answer 'from the rails' would make it a small false-alarm risk (none measured) |
| 2 | new, 24.09 (P4) | `labels/cloud_with_fake_obj.json` (`big_above`), P4_AUDIT "Organizer synthetic-obstacle recording" | labelled inside now; if it must not alarm, its 12 STOP frames become false alarms and the `elevated` experiment goes the wrong way |

## Answered

Questions of this file that the organizers have answered; the answer and what it changed live in
[`organizers/answers.md`](organizers/answers.md).

| # | question | answered | answer | recorded in |
|---|---|---|---|---|
| Q3 (24.09) | is a 30 × 30 × 10 cm object lying on the bed between the rails (below the rail head) an obstacle; is the envelope floor the rail head or the bed? | 25.09, orally, reported by the captain | no: it is not inside the train's envelope, so it is not an obstacle; the shipped policy (nothing below the envelope floor between the rails) stands and the opt-in near-bed path stays off | [`organizers/answers.md`](organizers/answers.md) §8 |
