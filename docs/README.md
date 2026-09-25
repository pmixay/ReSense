# Documentation Index

> **Purpose:** every document of the repository, what it is for, who reads and maintains it, and
> the terms they share.
> **Audience:** jury, team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-24, `537e220` (detector v0.6.3, node v0.6.4) · **Status:** current

Start with the root [`README.md`](../README.md): the jury path, what to look at and the headline
results. Current numbers live in [`EXPERIMENTS.md`](EXPERIMENTS.md) "Current results"; what changed
in each version, in [`CHANGELOG.md`](../CHANGELOG.md).

## 1. Documents

Status: **current** = maintained; **dated record** = an audit or judgement of one date, not
rewritten later; **frozen** = kept for reference, not maintained; **archive** = history in
[`archive/`](archive/).

| document | purpose | audience | language | owner | status |
|---|---|---|---|---|---|
| [`README.md`](../README.md) | jury entry: build, run, what to look at, headline results (spec §5 README) | jury, team | EN + RU «Кратко для жюри» | P1 | current |
| [`CHANGELOG.md`](../CHANGELOG.md) | one entry per version, v0.0 → v0.6.4, with the measured effect | jury, team | EN | P1 | current |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | components, data flow, real-time budget (spec §5 "Архитектура") | jury, team | EN + RU summary | P1 | current |
| [`ALGORITHM.md`](ALGORITHM.md) | how the detector decides, stage by stage; parameters; limitations (spec §5 "Описание алгоритма") | jury, P3 | EN + RU summary | P1 (structure), P3 (content) | current |
| [`EXPERIMENTS.md`](EXPERIMENTS.md) | every measured result: false alarms, range, latency, FPS, hard cases, evolution (spec §5 "Эксперименты") | jury, team | EN + RU summary | P3 / P4 | current |
| [`EVALUATION.md`](EVALUATION.md) | evaluation protocol: data sets, metrics, procedure, targets | team, jury | EN + RU summary | P1 / P4 | current |
| [`DATASET.md`](DATASET.md) | the organizers' data: recordings, formats, labels, frame cache, unpacking | team, jury | EN + RU summary | P4 | current |
| [`SENSOR.md`](SENSOR.md) | Hesai Pandar128 facts and what they imply for the detector | team, jury | EN + RU summary | P1 | current |
| [`SCORECARD.md`](SCORECARD.md) | criteria judgement of 24.09: score per spec §8 criterion, evidence, what is left | team, jury | EN | P1 | dated record |
| [`SUBMISSION.md`](SUBMISSION.md) | deliverables checklist (spec §5, §7), dry run, upload | team | EN, cover message RU | P1 | current |
| [`PRESENTATION.md`](PRESENTATION.md) | slide requirements, drafts, speaker text | P2, P1 | RU | P2 | current |
| [`PLAN.md`](PLAN.md) | roles, sprint calendar, team rules | team | RU | P1 | current |
| [`CAPTAIN.md`](CAPTAIN.md) | captain's board: criteria, work left, ownership map, frozen interfaces | P1, team | EN | P1 | current |
| [`QUESTIONS.md`](QUESTIONS.md) | open questions to the organizers | P1 | RU message, EN rationale | P1 | current |
| [`P4_AUDIT.md`](P4_AUDIT.md) | audit of synthetic placement and evaluation accounting, set O grade | team, jury | EN | P4 | dated record |
| [`RESEARCH.md`](RESEARCH.md) | day-1 literature survey (15.09) | team | EN | P3 | frozen |
| [`evidence/README.md`](evidence/README.md) | index of the raw run evidence and of the result summaries in `evidence/results/` | team, jury | EN | P1 / P4 | current |
| [`images/README.md`](images/README.md) | dashboard UI screenshots and their data provenance | jury, team | EN | P2 | current |
| [`archive/README.md`](archive/README.md) | superseded material kept for the record (captain's log of 16–24.09, day-1 results) | team | EN | P1 | archive |
| [`web/README.md`](../web/README.md) | dashboard, RViz / Foxglove layouts, label tool, headless checks, video recipes | team, jury (demo) | EN | P2 | current |

### Organizers' material ([`organizers/`](organizers/))

| file | what | origin |
|---|---|---|
| [`README_organizers.md`](organizers/README_organizers.md) | the case page: task, timeline, criteria, links | organizers, unchanged |
| [`technical_specification_case05.pdf`](organizers/technical_specification_case05.pdf) (+ `.txt`) | the specification (ТЗ) that "spec §" refers to | organizers, unchanged |
| [`QA_session_transcript_ru.md`](organizers/QA_session_transcript_ru.md) | machine transcript of the organizers' Q&A recording of 22.09 | team transcript, unchanged |
| [`mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md) | answers on the LiDAR mount and switches (24.09) | organizers, formatted by the team |
| [`QA_session.md`](organizers/QA_session.md) | summary of the Q&A session and the facts that changed the code | team (P1) |
| [`answers.md`](organizers/answers.md) | every organizer answer, verbatim, and what the team did with it | team (P1) |
| [`test_stand_software.md`](organizers/test_stand_software.md) | the test stand's hardware and reported software, with team notes | organizers + team (P1) |

## 2. Folders

| folder | contents |
|---|---|
| [`img/`](img/) | real-data renders (views from the cab, top / side renders); `scripts/build_deck.py` and `web/demo/check_dashboard.py` read and write here, so it stays in place |
| [`images/`](images/) | dashboard UI screenshots (P2) |
| [`video/`](video/) | the committed clips: the jury chain in Docker with RViz, the bag from the cab, offline renders, dashboard replay (all silent) |
| [`presentation/`](presentation/) | the deck in the organizers' template (pptx + pdf); personal data only in its git-ignored `private/` subfolder |
| [`sensor/`](sensor/) | the Hesai Pandar128 user manual |
| [`evidence/`](evidence/) | raw logs, captures and bench output per run (`<run>_<date>/`), the recordings' `bag_metadata/`, and `results/` with every `experiments_*.json` summary |
| [`archive/`](archive/) | history, not maintained |
| [`organizers/`](organizers/) | organizer material (above) |

`extended_dataset_intake.json` stays in `docs/`: three scripts read it (`scripts/far_range_eval.py`,
`scripts/eval_real.py`, `scripts/ml_dataset.py`).

## 3. Glossary

| term | meaning |
|---|---|
| sandbox | the team's 4-vCPU development VM, where the offline timings and the Docker rehearsal of 23.09 ran; not the jury's stand |
| stand | the organizers' test machine: Intel Core i7-9700E, 8 cores (spec §3.1, [`organizers/test_stand_software.md`](organizers/test_stand_software.md)); not open to the team before submission (organizers, 25.09: [`organizers/answers.md`](organizers/answers.md) §6), so the team's own 8-core machine, the "8-core analogue", stands in for timing |
| ride | `new_data`, the organizers' extended 20-minute, 13 km recording (11 271 frames, no obstacles) |
| envelope, gauge | the organizers' train envelope, 2.1 m wide × 3.0 m high around the track axis above the rail head: the strict zone of `STOP`; the advisory zone adds 0.35 m on each side |
| alarm frame | a frame with `obstacle = true`, i.e. decision `STOP` |
| event | one confirmed gauge track id: roughly one stop of the train; the headline false-alarm count |
| STOP episode | a run of consecutive `STOP` frames: how often the braking signal switches on |
| advisory, `CAUTION` | a confirmed object just outside the envelope or beyond the verified range, known infrastructure or degraded health; informational, not an alarm |
| verified-clear distance | `clear_distance`: the obstacle distance, else how far the corridor was actually checked |
| first confirmed / held from | for an approaching object: the largest distance at which it is first reported / from which it is reported in ≥ 90 % of the frames |
| set S / E / R / O / F / H | data sets of [`EVALUATION.md`](EVALUATION.md) §1: S our synthetic objects in real empty frames; E the five obstacle-free organizer bags; R real obstacles (`doubleT_obstacle`); O the organizers' synthetic-obstacle recording `cloud_with_fake_obj`; F our synthetic objects approaching through consecutive frames of the moving ride (EXPERIMENTS §2d); H the hidden control bag |
| real / synthetic / organizers' synthetic / timing | kind of a result: the organizers' recordings as recorded; our objects ray-cast into real frames; objects added by the organizers' own tool (set O); a latency measurement, always with its machine |
| legacy / anchored placement | how set F places an object: legacy from the detector's own per-frame far axis (can flatter curves and envelope edges); anchored where a near (≤ 30 m) rail-supported track fit puts it, carried back along the ride (independent of the far axis, not surveyed ground truth); EVALUATION §3, [`P4_AUDIT.md`](P4_AUDIT.md) |
| detector v0.6.3, node v0.6.4 | the current state: the v0.6.3 detector, and the node's v0.6.4 catch-up of the burst at the start of a played bag ([`CHANGELOG.md`](../CHANGELOG.md)) |

## 4. Conventions

* Every team-written document starts with the header block above (purpose, audience, owner by
  role code P1–P4, language, last verified with the commit, status); the jury-facing ones add a
  Russian «Кратко».
* "Last verified" moves only when someone re-checked the document's numbers against that commit.
* One fact, one home: the current numbers in EXPERIMENTS "Current results", version history in
  CHANGELOG, organizer answers in `organizers/answers.md`; other documents give one line and a link.
* Dates `DD.MM` in prose (2026), ISO `YYYY-MM-DD` in header blocks and file names; thousands with a
  space (`13 759`); decimal point in EN, decimal comma in RU; every result with its kind and date.
* Relative links; sections cited by number (`EXPERIMENTS §3b`), no deep anchors into other files.
