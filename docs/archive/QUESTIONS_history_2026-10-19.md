# QUESTIONS: the five-question message and the status paragraphs, cut on 19.10.2026

> **Purpose:** passages cut from [`QUESTIONS.md`](../QUESTIONS.md) when it was compacted on 19.10 (documentation clean-up), word
> for word: the header, the three stacked status paragraphs, and the section "Sent, awaiting answers: the five open questions" of 16.10
> with the questions that are answered now (Q1, Q2, Q4; the open Q3 and Q5 stay in the live file). The heading "the five open
> questions" and "awaiting answers" are those of 16.10: three of the five have been answered since. **Language:** RU message, EN
> rationale · **Status:** archive

## Header and status paragraphs (19.10 and earlier)
<!-- QUESTIONS.md lines 3-30 before the clean-up of 19.10 -->

> **Purpose:** the questions to the organizers that are still unanswered, as one message ready to
> send, and why each matters.
> **Audience:** P1, team (the message: the organizers) · **Owner:** P1 · **Language:** RU message,
> EN rationale
> **Last verified:** 2026-10-19: both messages below were sent by the captain (reported 19.10), no reply yet;
> 2026-10-16: against [`organizers/answers.md`](../organizers/answers.md) §10 and the experts'
> message; 2026-09-29: against [`organizers/answers.md`](../organizers/answers.md) §9 and the
> sealed detector · **Status:** current

**Status (19.10, evening): partly answered.** The organizers answered on 19.10
([`organizers/answers.md`](../organizers/answers.md) §12): everything inside the train's gauge is an obstacle (closes
Q1 for in-gauge objects); objects may move, even chaotically (Q2 in part); no labels, but an order of appearance
(`obstacles.md`) and marked bags, and dust in every new synthetic bag (Q4). **Still open: Q3 (the filter), Q5 (how the
bags are played) and O1 (pitch format, whether an updated version counts).**
Earlier: five questions and O1 sent, awaiting answers (19.10). The captain reported on 19.10 that the
messages below were sent; the exact send date is not recorded. Record each reply in
[`organizers/answers.md`](../organizers/answers.md) §11.
Earlier status, five questions open (16.10): Q1 and Q2 (sent on 25.09) were answered on 29.09: the envelope is
measured from the rail heads, the rails may run at any angle to the LiDAR, and the synthetic objects are placed
approximately; the organizers correct for that when checking
([`organizers/answers.md`](../organizers/answers.md) §9). The live Q&A of 16.10 left two questions without an answer
(how `CAUTION` is read; which objects and scenes the hidden set has), and the experts' message of the same day
([`FINALS_BRIEF_2026-10-16.md`](../FINALS_BRIEF_2026-10-16.md)) raises three more (what "the filter" is, what the new
data look like, how the bags will be played). Every answered question is recorded in
[`organizers/answers.md`](../organizers/answers.md); a new question goes here as a message ready to send, with why it
matters. Channel: the case moderator (Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or
info.leaders@develop.mos.ru.

## Sent, awaiting answers: the five open questions (16.10)
<!-- QUESTIONS.md lines 31-55 before the clean-up of 19.10 -->

## Sent, awaiting answers: the five open questions (16.10, RU, open form for a live conversation)

Spoken form, most important first; each question can be asked as is.

1. **Как вы относитесь к уровню «осторожно» в нашем ответе?** У нас есть «тревога» и «осторожно» (подсказка: объект у
   границы габарита или известная инфраструктура). Что для вас считается ответом «препятствие есть», а что нет?
2. **Какие объекты и какие участки будут в проверке?** Какие размеры и формы, есть ли тонкие висящие, движущиеся
   (человек идёт), как выглядит пыль. Будут ли станции, платформы, стрелки, повороты, двухпутные участки; бывают ли
   моменты, когда поезд стоит или едет очень медленно?
3. **Что вы называете «работой фильтра»?** Фильтрацию ложных срабатываний, фильтр сопровождения (подтверждение
   объекта по нескольким кадрам) или фильтр пыли?
4. **Что будет в новых данных?** Когда их выдадут; для записи с другого лидара: модель, поля облака (есть ли номер
   луча), число лучей, угол обзора, как направлены оси; объекты в новой синтетике закреплены в тоннеле, как в
   `cloud_with_fake_obj`, или иначе?
5. **Как вы будете проигрывать бэги?** Какая команда, скорость, нужны ли пауза и замедление из консоли, сколько
   ядер процессора будет доступно.

| # | why it matters (EN) | what changes with the answer |
|---|---|---|
| 1 | `CAUTION` is on 43 % of empty frames (judge, 13.10); if it counts as an alarm, false positives (scored like misses) multiply | the output mapping and the `CAUTION` policy (C1) |
| 2 | N3 (dust), the small-object and thin-cable cards (R1, R3), and the standing-train rules (K1) depend on what the hidden set contains | priorities between R, K, F cards; the dust generator's parameters |
| 3 | criterion 7 of the experts' list is not defined | whether N3, the tracker, or the false-alarm work is what is meant |
| 4 | N2 (second lidar): the orientation search is limited to 8 rotations with the up axis vertical, and the far multi-ring rules assume 128 elevation channels; the objects' placement decides whether `ego_veto` is safe | N2's battery and the jury README for the second lidar; whether to keep `ego_veto` as it is |
| 5 | the player's flags decide the stale-result problem (S1); pause and slow need the player's keyboard controls (N4); the core count bounds 360° speed (S5) | S1, N4, the launch notes |

## O1 message and its closing paragraph (original wording)
<!-- QUESTIONS.md lines 60-76 before the clean-up of 19.10 -->

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
[`organizers/answers.md`](../organizers/answers.md) §11, then updates
[`PRESENTATION.md`](../PRESENTATION.md). Preparing this text does not close O1 or authorize
a new submission. Until a reply, the five-minute talk remains a planning assumption.
