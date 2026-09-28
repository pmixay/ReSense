# Open Questions to the Organizers

> **Purpose:** the questions to the organizers that are still unanswered, as one message ready to
> send, and why each matters.
> **Audience:** P1, team (the message: the organizers) · **Owner:** P1 · **Language:** RU message,
> EN rationale
> **Last verified:** 2026-09-29: against [`organizers/answers.md`](organizers/answers.md) and the
> sealed detector · **Status:** current

**Status: Q1 and Q2 were sent on 25.09 and are unanswered.** Both come from the organizers'
synthetic-obstacle recording ([`DATASET.md`](DATASET.md) "Synthetic-obstacle recording"). Every
answered question is recorded in [`organizers/answers.md`](organizers/answers.md); when an answer
comes, record it there and move the question to "Answered". Channel: the case moderator
(Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or info.leaders@develop.mos.ru.

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

## Why each question matters

| # | answer goes to | consequence |
|---|---|---|
| 1 | `labels/cloud_with_fake_obj.json` (`in_gauge`), `gauge.reference` | measured from the sensor axis the four edge tests are exactly the organizers' intent, from the rails they are not ([experiment log](archive/EXPERIMENTS_log_2026-09.md) §1m). The sealed detector takes the union of both envelopes within 60 m on straight track (`gauge.reference` 3, [`DECISIONS.md`](DECISIONS.md) row 18): an object inside either is inside, so "from the sensor axis" is covered there, while beyond 60 m and on curves the envelope follows the rails; with "from the rails" the union can add STOPs on objects just outside the rails' envelope (it never removes one) |
| 2 | `labels/cloud_with_fake_obj.json` (`big_above`) | labelled inside; the sealed detector STOPs on it from ~111 m ([`SCORECARD.md`](SCORECARD.md)); if it must not alarm, those STOP frames become false alarms |

## Answered

| # | question | answer | recorded in |
|---|---|---|---|
| Q3 | is a 30 × 30 × 10 cm object on the bed between the rails (below the rail head) an obstacle? | no, it is not inside the train's envelope (25.09); the shipped policy stands and the opt-in near-bed path stays off | [`organizers/answers.md`](organizers/answers.md) §8 |
| — | return mode, time synchronisation, LiDAR mount, switches, stand access, internet on the stand | answered 22–25.09 | [`organizers/answers.md`](organizers/answers.md) §1–§7 |
