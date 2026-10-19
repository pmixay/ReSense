# Open Questions to the Organizers

> **Purpose:** the questions to the organizers that are still unanswered, as messages ready to send, and why each matters.
> **Audience:** P1, team (the message: the organizers) · **Owner:** P1 · **Language:** RU message, EN rationale
> **Last verified:** 2026-10-19 (evening): against [`organizers/answers.md`](organizers/answers.md) §12; the messages below were
> sent by the captain (reported 19.10, send date not recorded) · **Status:** current

**Status (19.10, evening): partly answered.** The organizers answered on 19.10 ([`organizers/answers.md`](organizers/answers.md)
§12): everything inside the train's gauge is an obstacle (closes Q1 for in-gauge objects); objects may move, even chaotically (Q2
in part); no labels, but an order of appearance (`obstacles.md`) and marked bags, and dust in every new synthetic bag (Q4).
**Still open: Q3 (the filter), Q5 (how the bags are played) and O1 (pitch format, whether an updated version counts).** Q1 and Q2 of
25.09 were answered on 29.09 ([`answers.md`](organizers/answers.md) §9). Record each reply in
[`answers.md`](organizers/answers.md) §11–§12. The five-question message of 16.10 (open form, RU), the earlier status paragraphs and
the rationale rows of Q1, Q2 and Q4 are in [`archive/QUESTIONS_history_2026-10-19.md`](archive/QUESTIONS_history_2026-10-19.md).
Channel: the case moderator (Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or info.leaders@develop.mos.ru.

## Open: Q3 (the filter) and Q5 (how the bags are played), sent 16.10, no reply

Spoken form, most important first; each question can be asked as is (numbering as in the sent message of five questions).

3. **Что вы называете «работой фильтра»?** Фильтрацию ложных срабатываний, фильтр сопровождения (подтверждение
   объекта по нескольким кадрам) или фильтр пыли?

5. **Как вы будете проигрывать бэги?** Какая команда, скорость, нужны ли пауза и замедление из консоли, сколько
   ядер процессора будет доступно.

| # | why it matters (EN) | what changes with the answer |
|---|---|---|
| 3 | criterion 7 of the experts' list is not defined | whether N3 (dust), the tracker, or the false-alarm work is what is meant |
| 5 | the player's flags decide the stale-result problem (the literal `ros2 bag play` gives stale results; S1 failed); pause and slow need the player's keyboard controls (N4, done locally); the core count bounds 360° speed (S5) | the launch notes, S5 |

Not asked again, answered in §10 of [`organizers/answers.md`](organizers/answers.md): how the result is scored,
how false alarms count against misses (equally), the hidden set's mix (real and synthetic), the range (300 m in the
ideal), ground truth (not available), the results' explanation (promised, to be confirmed).

## O1 · Sent, awaiting answer (prepared 15.10)

> Добрый день! Команда «Молоток», кейс 05, решение ReSense. Подскажите, пожалуйста, по защите 23 октября:
>
> 1. Сколько времени отведено на выступление и вопросы жюри? Будет ли демонстрация экрана и ожидается ли живая демонстрация решения?
> 2. После сдачи 29 сентября мы нашли и исправляем ошибки обнаружения высоких узких объектов и объектов на кривых. Можно ли показать на защите обновлённую версию 1.1.x или передать её на повторный прогон? Может ли такая версия повлиять на оценку, либо оценивается только сданная v1.0.0?
> 3. Будут ли до 23 октября доступны результаты скрытых прогонов или экспертные баллы? Можно ли повторно проверить обновлённый архив, и если да — куда и до какого срока его передать?
>
> Спасибо!

Why these questions matter: (1) fixes PT1/PT2's talk/demo budget; (2) decides whether
post-submission detector work may count; (3) fixes the evidence and delivery path.
The captain records the actual dispatch date and the reply verbatim in
[`organizers/answers.md`](organizers/answers.md) §11, then updates
[`PRESENTATION.md`](PRESENTATION.md). Preparing this text does not close O1 or authorize
a new submission. Until a reply, the five-minute talk remains a planning assumption. The message was written when 1.1.x was the plan; 1.1.0 will not
be released (19.10), so "the updated version" now means 1.2.0.

## Answered

| # | question | answer | what it settled | recorded in |
|---|---|---|---|---|
| 16.10 Q1 | how is `CAUTION` read | «всё, что попадает в габарит поезда — препятствие» (19.10) | an in-gauge object must be a `STOP`; `CAUTION` on it is a miss | [`organizers/answers.md`](organizers/answers.md) §12 |
| 16.10 Q2 (part) | which objects and scenes | objects may move, even chaotically; this must not confuse detection (19.10); the hidden set's object list not given | rules assuming static or approaching objects are reviewed (BACKLOG §9f) | §12 |
| 16.10 Q4 | what the new data look like | no labels; `obstacles.md` (order of appearance) and the synthetic bags with markers; dust at least twice in every synthetic bag (19.10) | intake of the marked bags; N5 labels re-checked; organizers' dust used for N3 | §12, [`organizers/obstacles_2026-10-19.md`](organizers/obstacles_2026-10-19.md) |
| Q1 | in the synthetic check, is the envelope measured from the LiDAR's (train's) axis or from the rails? (`cloud_with_fake_obj`: rails at 0.24° to the LiDAR's axis, so the edge tests change sides along the track) | from the **rail heads**; the rails may run at any angle to the LiDAR; the synthetic objects are placed approximately and may drift relative to the envelope along the track, and the organizers correct for that when checking (29.09) | the organizers' envelope is the rails' one, as the detector builds it. `gauge.reference` 3 (the union with the sensor-axis envelope within 60 m on straight track, at most 0.2 m wider, never narrower) stays: it costs no measured false alarm and keeps measured recall ([`DECISIONS.md`](DECISIONS.md) row 18); `gauge.axis_union` stays off. Set O's edge-test labels keep the organizers' intent, within their stated tolerance | [`organizers/answers.md`](organizers/answers.md) §9 |
| Q2 | is «2х2 сверху габарита» (bottom 2.4–2.9 m above the rail head, 0.1–0.6 m inside the 3.0 m envelope) an obstacle? | follows from Q1: the envelope's top is 3.0 m above the rail head, so the object reaches into it (29.09; not answered separately) | an obstacle: the label `in_gauge: true` and its STOPs (from ~111 m) stand | [`organizers/answers.md`](organizers/answers.md) §9 |
| Q3 | is a 30 × 30 × 10 cm object on the bed between the rails (below the rail head) an obstacle? | no, it is not inside the train's envelope (25.09); the shipped policy stands and the opt-in near-bed path stays off | — | [`organizers/answers.md`](organizers/answers.md) §8 |
| — | return mode, time synchronisation, LiDAR mount, switches, stand access, internet on the stand | answered 22–25.09 | — | [`organizers/answers.md`](organizers/answers.md) §1–§7 |

The message of 25.09 (Q1, Q2) is in this file's git history.
