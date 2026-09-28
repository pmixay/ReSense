# Documentation Index

> **Purpose:** every document of the repository, what it is for, who reads and maintains it, and
> the terms they share.
> **Audience:** jury, team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-29: the rows against the documents after the documentation sweep
> (package 1.0.0: the detector sealed on 27.09, the node of 29.09) · **Status:** current

Start with the root [`README.md`](../README.md): what ReSense is, the jury commands, the results.
The same in Russian, as a user guide: **[resense.gitbook.io/resense-docs](https://resense.gitbook.io/resense-docs/)**
(source [`gitbook/`](../gitbook/SUMMARY.md), synced from `main`).

## 1. Documents

**current** = maintained; **dated record** = one date's evidence or judgement, not rewritten;
**archive** = history in [`archive/`](archive/README.md), not maintained.

| document | purpose | language | owner | status |
|---|---|---|---|---|
| [`README.md`](../README.md) | the project's face: what it is, the jury path, results, build / run / parameters (spec §5 README) | EN + RU jury block | P1 | current |
| [`gitbook/`](../gitbook/SUMMARY.md) | the user guide: image, running on a bag, reading the output, RViz / Foxglove / dashboard, offline stand, acceptance test, parameters, topics, results, the team's approach, troubleshooting | RU | P1 | current |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | components, data flow, the node, freshness, delivery, CI, known limitations (spec §5 «Архитектура») | EN + RU summary | P1 | current |
| [`ALGORITHM.md`](ALGORITHM.md) | how the detector decides, stage by stage, with its maths, parameters and limitations (spec §5 «Описание алгоритма») | EN + RU summary | P1 (structure), P3 (content) | current |
| [`EXPERIMENTS.md`](EXPERIMENTS.md) | measured results: detection, range, false alarms, latency, FPS, hard cases, how quality changed, what was tried and not shipped (spec §5 «Эксперименты») | EN + RU summary | P3 / P4; P1 the node timing | current |
| [`EVALUATION.md`](EVALUATION.md) | evaluation protocol: data sets, metrics, procedure, in-sample vs held out | EN + RU summary | P1 / P4 | current |
| [`DECISIONS.md`](DECISIONS.md) | the key decisions on one page: question, what was measured, decision, evidence | EN + RU summary | P1 | current |
| [`DATASET.md`](DATASET.md) | the organizers' data: recordings, formats, labels, frame cache, unpacking | EN + RU summary | P4 | current |
| [`SENSOR.md`](SENSOR.md) | Hesai Pandar128 facts and what they imply | EN + RU summary | P1 | current |
| [`RESEARCH.md`](RESEARCH.md) | the literature survey behind the approach | EN | P3 | current |
| [`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md) | what is sealed, how CI verifies it, how a change would be accepted | EN | P1 / P3 | current |
| [`SCORECARD.md`](SCORECARD.md) | the independent judgement of 28.09 evening against the eight criteria of spec §8, and what changed since | EN + RU summary | P1 | dated record + current follow-up |
| [`PRESENTATION.md`](PRESENTATION.md) | the pitch: slide requirements, slide plan, speaker text, demo, rehearsals, building the deck and the video | RU | **P2** | current |
| [`VM_GUIDE.md`](VM_GUIDE.md) | runbook for the team's cloud VM: data, dry run, host consoles, bench, gate, export, offline rehearsal | EN | P1 | current |
| [`CAPTAIN.md`](CAPTAIN.md) | captain's board: role, criteria, work left, branches, rules, contracts, ownership, decision log | EN | P1 | current |
| [`PLAN.md`](PLAN.md) | roles, rules, milestones, status, risks | RU | P1 | current |
| [`QUESTIONS.md`](QUESTIONS.md) | questions to the organizers and their status | RU message, EN rationale | P1 | current |
| [`../CHANGELOG.md`](../CHANGELOG.md) | the full history: what changed, newest first, with the figures measured on the day; the dated paragraphs cut from the README | EN | P1 | current |
| [`evidence/README.md`](evidence/README.md) | index of the raw run evidence and result summaries | EN | P1 / P4 | current |
| [`archive/README.md`](archive/README.md) | the full experiment log (§ numbers cited by code), the captain's earlier boards, quality-cycle records, P4's audits | EN | P1 | archive |
| [`../web/README.md`](../web/README.md) | dashboard, RViz / Foxglove layouts, label tool, video recipes | EN | P2 | current |
| [`../web/DEMO_HANDOFF.md`](../web/DEMO_HANDOFF.md) | the live demo on the stand step by step, the second-device Foxglove check, the fallback, the rehearsal record, the private deck build | RU | P2 | current |
| [`images/README.md`](images/README.md) | dashboard screenshots and their provenance | EN | P2 | current |

### Organizers' material ([`organizers/`](organizers))

| file | what | origin |
|---|---|---|
| [`README_organizers.md`](organizers/README_organizers.md) | the case page: task, timeline, criteria, links | organizers, unchanged |
| [`technical_specification_case05.pdf`](organizers/technical_specification_case05.pdf) (+ `.txt`) | the specification (ТЗ) that "spec §" refers to | organizers, unchanged |
| [`QA_session_transcript_ru.md`](organizers/QA_session_transcript_ru.md) | machine transcript of the organizers' Q&A of 22.09 | team transcript |
| [`QA_session.md`](organizers/QA_session.md) | summary of the Q&A and the facts that changed the code | team (P1) |
| [`answers.md`](organizers/answers.md) | every organizer answer, verbatim, and what the team did with it | team (P1) |
| [`mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md) | answers on the LiDAR mount and switches (24.09) | organizers, formatted by the team |
| [`test_stand_software.md`](organizers/test_stand_software.md) | the test stand's hardware and software | organizers + team (P1) |

## 2. Folders

| folder | contents |
|---|---|
| [`img/`](img), [`images/`](images) | real-data renders (read and written by `scripts/build_deck.py`, so they stay in place); dashboard screenshots |
| [`video/`](video) | the 2:50 overview `resense_overview.mp4` (Russian subtitles, also as `.srt`) and its clips (Docker + RViz chain, the bag from the cab, the organizers' objects) |
| [`presentation/`](presentation) | the deck in the organizers' template (pptx + pdf); personal data only in the git-ignored `private/` |
| [`sensor/`](sensor) | the Hesai Pandar128 user manual |
| [`evidence/`](evidence) | raw logs, captures and bench output per run (`<run>_<date>/`), the recordings' `bag_metadata/`, result summaries in `results/` |
| [`archive/`](archive) | history, not maintained |

`extended_dataset_intake.json` stays in `docs/`: scripts read it (`scripts/far_range_eval.py`,
`scripts/eval_real.py`, `scripts/ml_dataset.py`).

## 3. Glossary

| term | meaning |
|---|---|
| envelope, gauge | the organizers' train envelope, 2.1 m wide × 3.0 m high around the track axis above the rail head: the strict zone of `STOP`; the advisory zone adds 0.35 m on each side |
| ride | `new_data`, the organizers' 20-minute, 13 km recording (11 271 frames, no obstacles) |
| set O / set F / set S | the organizers' ray-cast objects (`cloud_with_fake_obj`); the team's synthetic objects on the ride's straight track; the team's synthetic objects in the short recordings ([`EVALUATION.md`](EVALUATION.md) §1) |
| real / organizers' synthetic / team synthetic | the recordings as recorded; objects added by the organizers' tool; objects ray-cast by the team |
| in-sample / held out | measured on data the rules were tuned on / on data a component never saw |
| alarm frame, STOP episode, event | a frame with `STOP`; a run of consecutive `STOP` frames; one confirmed gauge track |
| `CAUTION`, advisory | an object just outside the envelope or beyond the trusted range, known infrastructure or degraded health: informational, not an alarm |
| `clear_distance` | the estimated monitored range, capped at detected objects: an estimate, not a guarantee |
| e2e | end to end: the player publishes a cloud → the node's result for it is received |
| stand, sandbox, team VM | the organizers' test machine (i7-9700E, 8 cores, not available before the upload); the 4-vCPU development sandbox; the team's 4-core cloud VM |

## 4. Conventions

* Every team document starts with the header block (purpose, audience, owner by role P1–P4,
  language, last verified, status); jury-facing ones add a Russian «Кратко».
* One fact, one home: results in [`EXPERIMENTS.md`](EXPERIMENTS.md) (headline in the README), the
  judgement in [`SCORECARD.md`](SCORECARD.md), organizer answers in `organizers/answers.md`, history
  in [`../CHANGELOG.md`](../CHANGELOG.md) and [`archive/`](archive/README.md).
* Every number with its kind (real / synthetic), in-sample or held out, and its evidence path.
* "EXPERIMENTS §x" in code comments and older records refers to the archived full log,
  [`archive/EXPERIMENTS_log_2026-09.md`](archive/EXPERIMENTS_log_2026-09.md).
