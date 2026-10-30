# Experts' message to the finalists (16.10): criteria, new data, launch requests, and what we have

> **Purpose:** the experts' general message to the finalists, verbatim (§1), and the state of each of their requests: the nine
> criteria (§2), the new requests (§3) and the cards N1–N4 (§4). The 16.10 analysis of each against the code, with the code
> lines, is in [`archive/FINALS_BRIEF_history_2026-10-19.md`](archive/FINALS_BRIEF_history_2026-10-19.md).
> **Audience:** P1 (to distribute), P2 (RViz, visuals), P3, P4 · **Owner:** P1 · **Language:** EN, the message in RU
> **Last verified:** 2026-10-23, version-state pass: only the version statements were checked, against the git tags `v1.0.0`, `v1.2.0` (`git ls-remote --tags origin`; no `v1.3.0`) and the version fact sheet; §2–§4 are still the 19.10 state (see the note under the Status line). 2026-10-19 (evening): §2–§4 against [`BACKLOG.md`](BACKLOG.md) §9b and "Current plan" and the evidence of
> 18–19.10; §1 is the message as relayed on 16.10 (unchanged).
> **Status:** current state per criterion and card in §2–§4 (N1 and N4 done locally; N2 measured and complete; N3 measured,
> acceptance fails, the guard is off; gauge stability and curves: K1/K2 switched on, numbers pending)

> **Version note (23.10).** The "state on 19.10" columns describe the tree of 19.10, not the current release. Since then `v1.2.0` was published (20.10, the current published release; the team reports the jury reviewed it, no jury score is in the repository), K1 was left **off** in 1.2.0 (not on, as row 3 below says; `DECISIONS.md` rows 44 and 48), and the release image exists. 1.3.0 is an unreleased, untagged candidate. "Judge method, v1.0.0" and "judge 13.10 (v1.0.0)" below are measurements of v1.0.0 only.

## 1. The message (verbatim, as relayed by the team)

> Общее сообщение от экспертов финалистам
>
> «Основные критерии оценки:
> 1. Дальность детекции (как далеко случается первый детект препятствия);
> 2. Дальность габарита (как далеко простраивается габарит);
> 3. Устойчивость габарита (бокс габарита не моргает, не исчезает, не уходит с путей);
> 4. Отсутствие ложноположительных срабатываний;
> 5. Отсутствие ложноотрицательных срабатываний;
> 6. Работа алгоритма в реальном времени (частота 10 Гц);
> 7. Работа фильтра;
> 8. Дополнительные фичи;
> 9. Удобство запуска.
>
> Напомним, что нами будет расширен датасет: будет выдана дополнительная синтетика со схожими лидарными облаками и
> дополнительными препятствиями (в т.ч. человек и симуляция пыли/взвеси) и реальная запись с другого лидара для
> дополнительной оценки. Уточним, что нужно учесть отличия в направлении осей на другом лидаре.
>
> Отметим дополнительные запросы по упрощению запуска:
> - Запуск docker container с графикой;
> - Наличие rviz в докер контейнере;
> - Возможность останавливать/замедлять бэги (функционал есть во встроенном проигрывателе ros2 bag play, он должен
>   быть доступен при запуске контейнера, из консоли);
> - Возможность быстро переключать разные бэги (желательно без перезапуска контейнера).»

Together with the live Q&A of the same day ([`organizers/answers.md`](organizers/answers.md) §10): a false positive
counts the same as a miss, 300 m is the ideal range, the check mixes real and synthetic data, and the team's own
project needs "a more stable gauge and the gauge synchronised with turns (it does not match well)".

**What is new against [`BACKLOG.md`](BACKLOG.md):** it is organised by ТЗ §8 (eight criteria, the judge's weights).
The experts' list is different: it names the **gauge** twice (range, stability) as criteria of their own, and adds
dust, a second lidar and four launch requests. The backlog covers the axis (K1, K2), false alarms (F1, F2), range
(R1–R3), CAUTION (C1), the player's start-up (S1) and speed (S2, S5); it does not cover the gauge as a displayed
object, dust, the second lidar, or the interactive launch.

## 2. The nine criteria: state on 19.10

Per-criterion state with evidence and the owner of the next step: [`BACKLOG.md`](BACKLOG.md) §9b ("The jury's comments and
criteria"). In short:

| # | criterion | state on 19.10 | next |
|---|---|---|---|
| 1 | detection range (first detect) | Pandar (judge method, v1.0.0): person-size box ~220 m straight, 52–83 m on curves, 1 m cube ~150 m, 0.3 m ~45–56 m; Falcon real person: first STOP ~125 m, visible from ~249 m; no 300 m claim | K2 (on), R1/R2 (P2) |
| 2 | gauge range | `axis_valid` and `clear_distance` are in the status; N1 draws only the supported part (on the curve a median 52 m of 142 m); the Falcon trusted range is ~123 m | K1/K2, N7 off |
| 3 | gauge stability | N1: stable box (visible-edge jitter p90 at 40/80/120 m within 0.05/0.08/0.15 m); the detector's own axis still jitters; K1 (distance-based smoothing) switched on, variant on 20.10 | K1/K2 |
| 4 | no false positives | judge 13.10 (v1.0.0): ~91 false `STOP` episodes per hour of empty tunnel, ~2.5 per km, CAUTION on 43 % of empty frames; F1a and H′ switched on (numbers pending) | F1, F2 |
| 5 | no false negatives | all 8 in-gauge organizer objects and the real person reach `STOP`; tall narrow objects (H1) and curves are the open misses; an in-gauge object in `CAUTION` counts as a miss (organizers, 19.10) | H1, K2, M1 |
| 6 | real time at 10 Hz | 120° real-time with margin; 360° p95 106–119 ms on 4 vCPU; Falcon decode+detect ~17–21 ms | S2, S5 |
| 7 | "the filter" | not defined; the question is sent and **unanswered** ([`QUESTIONS.md`](QUESTIONS.md)) | wait |
| 8 | extra features | N1 box, N4 interactive launch, Falcon profiles, web prototype, N5 labels | PT1 |
| 9 | ease of launch | N4 done locally; no published 1.2.0 image on 19.10 (CI red; the `v1.2.0` image was published 20.10) | E1 |

## 3. The new requests: state on 19.10

| request | state |
|---|---|
| Docker container with graphics; RViz in the container | done locally (N4): documented command, `scripts/run_demo.sh`, software-rendering fallback (`LIBGL_ALWAYS_SOFTWARE=1`); [HOWTO](evidence/n1_n4_2026-10-18/HOWTO.md); not part of the CI acceptance |
| pause or slow a bag; switch bags without restarting the container | done locally (N4): `scripts/play_bag.sh --interactive` (Space, Right, Up/Down, `--rate`), several bags in one node with an explicit reset, Pandar → Falcon switch ([evidence](evidence/n1_n4_2026-10-18/README.md)) |
| another lidar: different axis directions | done (N2): profiles `falcon_ros` / `falcon_native`, automatic orientation with an explicit readiness check (unconfirmed → `CAUTION`, not a silent `GO`), L16/S3 for ring-free lidars ([evidence](evidence/n2_falcon_2026-10-18/README.md), [L16/S3](evidence/l16_s3_2026-10-19/README.md)) |
| dust / suspension in the synthetic data | the organizers' dust located (11 bursts, 1–14 points; 1.1.0 gives no `STOP` or `CAUTION` on it); our generator and measurement complete (acceptance FAILS); the dust guard exists and is **off** ([N3](evidence/n3_dust_2026-10-18/README.md), [handoff](evidence/n3_dust_fix_2026-10-19/HANDOFF.md)) |

## 4. Cards

Format and roles as in [`BACKLOG.md`](BACKLOG.md) §1; the full text of N1–N4 as written on 16.10 is in the archive.

* **N1 · The gauge as a stable, honest box in RViz (criteria 2 and 3)** — done locally 18.10 (P2 with P1, no seal): a rail-relative box
  bounded by supported geometry, stable marker identities, grey invalid hold; all 2,308 replay frames pass the jitter and bounds
  checks; improved stability costs far-range availability ([evidence](evidence/n1_n4_2026-10-18/README.md)).
* **N2 · Second lidar: axis directions, channels, fields** — compatibility and characterization complete (P3 + P4); the
  ring-free orientation (L16/S3) is done by P3, on, P4 review pending.
* **N3 · Dust / suspension** — measurement complete, robustness acceptance FAILS, guard off; the re-check of the organizers' dust
  on the final configuration is P0 in "Current plan".
* **N4 · Interactive launch: pause, slow, switch bags, graphics** — done locally 18.10 (P1, no seal); the release image waited for CI on 19.10 (published 20.10 as `v1.2.0`).

Order and the detector-side work: [`BACKLOG.md`](BACKLOG.md) "Current plan", with the [survey's](COMPETITOR_SURVEY_2026-10.md)
shortlist attached to K2, F2 and H2.
