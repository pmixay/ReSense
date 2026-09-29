# Open Questions to the Organizers

> **Purpose:** the questions to the organizers that are still unanswered, as one message ready to
> send, and why each matters.
> **Audience:** P1, team (the message: the organizers) · **Owner:** P1 · **Language:** RU message,
> EN rationale
> **Last verified:** 2026-09-29: against [`organizers/answers.md`](organizers/answers.md) §9 and the
> sealed detector · **Status:** current

**Status: no open question.** Q1 and Q2 (sent on 25.09) were answered on 29.09: the envelope is
measured from the rail heads, the rails may run at any angle to the LiDAR, and the synthetic objects
are placed approximately; the organizers correct for that when checking
([`organizers/answers.md`](organizers/answers.md) §9). Every answered question is recorded in
[`organizers/answers.md`](organizers/answers.md); a new question goes here as a message ready to
send, with why it matters. Channel: the case moderator (Telegram
[@gorbatovaol](https://t.me/gorbatovaol)) or info.leaders@develop.mos.ru.

## Answered

| # | question | answer | what it settled | recorded in |
|---|---|---|---|---|
| Q1 | in the synthetic check, is the envelope measured from the LiDAR's (train's) axis or from the rails? (`cloud_with_fake_obj`: rails at 0.24° to the LiDAR's axis, so the edge tests change sides along the track) | from the **rail heads**; the rails may run at any angle to the LiDAR; the synthetic objects are placed approximately and may drift relative to the envelope along the track, and the organizers correct for that when checking (29.09) | the organizers' envelope is the rails' one, as the detector builds it. `gauge.reference` 3 (the union with the sensor-axis envelope within 60 m on straight track, at most 0.2 m wider, never narrower) stays: it costs no measured false alarm and keeps measured recall ([`DECISIONS.md`](DECISIONS.md) row 18); `gauge.axis_union` stays off. Set O's edge-test labels keep the organizers' intent, within their stated tolerance | [`organizers/answers.md`](organizers/answers.md) §9 |
| Q2 | is «2х2 сверху габарита» (bottom 2.4–2.9 m above the rail head, 0.1–0.6 m inside the 3.0 m envelope) an obstacle? | follows from Q1: the envelope's top is 3.0 m above the rail head, so the object reaches into it (29.09; not answered separately) | an obstacle: the label `in_gauge: true` and its STOPs (from ~111 m) stand | [`organizers/answers.md`](organizers/answers.md) §9 |
| Q3 | is a 30 × 30 × 10 cm object on the bed between the rails (below the rail head) an obstacle? | no, it is not inside the train's envelope (25.09); the shipped policy stands and the opt-in near-bed path stays off | — | [`organizers/answers.md`](organizers/answers.md) §8 |
| — | return mode, time synchronisation, LiDAR mount, switches, stand access, internet on the stand | answered 22–25.09 | — | [`organizers/answers.md`](organizers/answers.md) §1–§7 |

The message of 25.09 (Q1, Q2) is in this file's git history.
