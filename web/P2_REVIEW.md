# P2 review: organizer requirements, evidence and checks

> **Purpose:** each organizer requirement P2's work covers, its evidence, what is left, and the repeatable P2 checks.
> **Audience:** team, reviewers · **Owner:** P2 · **Language:** EN
> **Last verified:** 2026-09-29: evidence paths, ownership (pitch and video with P2 since 28.09) and the
> committed media hashes checked; numbers point to the independent judgement of 28.09
> **Status:** current

Deliverable state, dates and the rehearsal record: [`P2_STATUS.md`](P2_STATUS.md). How to build,
rehearse and present: [`docs/PRESENTATION.md`](../docs/PRESENTATION.md). Dashboard, layouts and label
tool: [`README.md`](README.md).

## Requirements and evidence

| organizer requirement | P2 work and evidence | left (P2 unless noted) |
|---|---|---|
| §4: Docker → bag → raw cloud → detection → distance; preferably live | RViz layout with both known raw-cloud topics, corridor, boxes and status text; Foxglove layout; archival Docker/RViz chain [`docs/video/docker_chain_rviz.mp4`](../docs/video/docker_chain_rviz.mp4); the browser's bundled roslib tested across subscribe, STOP, expiry, recovery and disconnect; CI on `main` runs the remote-viewer probe in a second container with link pause and recovery (`scripts/p2_viewer_test.sh`) | the live remote demo from a physical second device (visual layout import, link loss and recovery) at both rehearsals |
| §5, §7.2: short video, accessible documentation | 2:50 overview video with Russian subtitles (burned in and `.srt`), 16-slide PPTX/PDF in the organizers' template, interface screenshots, label-tool and replay instructions; every number marked real / our synthetic / organizers' synthetic | optional voice-over; the number differences listed in PRESENTATION «Числа на слайдах и их источники» |
| §8.5: robustness, tests, honest documentation | live validity contract, STOP hold, stale overlays, report schema v2, label import and numeric validation, Foxglove split-advertisement checks; browser tests cannot skip silently in CI | the organizers' stand is not available to the team |
| §8.6: easy launch | [`README.md`](README.md): offline replay, browser validation, live Foxglove; the jury path (`scripts/play_bag.sh`, Docker CI) is P1's | — |
| §8.7–8.8: approach, trade-offs, pitch | public deck with speaker notes in the spec's order; in-sample and held-out figures labelled; misses and false alarms named; no claims of arbitrary mounts, ready braking integration or unmeasured competitor accuracy | private deck, two rehearsals, the defence on 23.10 |
| §8.1–8.4: quality, range, speed, generalization | P2 shows measured numbers and does not produce them: the deck's `N` (27.09 gate, 28.09 node captures) and the independent judgement ([`SCORECARD.md`](../docs/SCORECARD.md)) | keep slides and video in step with accepted measurements; the detector is sealed |

## Client behaviour fixed in the audit

* **Live status.** `valid: true` alone is not enough: a current result needs a frame snapshot, a
  matching mode and clock, `reason: current`, no queue lag or catch-up, age bounds, a non-held status
  and consistent health; contradictions cannot release a held STOP. Cab and plan views both cover
  stale data; the cab range respects the published `clear_distance` cap; replay and live controls
  cannot overwrite each other, including a delayed file read.
* **Report schema v2** counts consecutive STOP runs as `stop_episodes` (not the evaluator's
  `alarm_events`), counts watchdog and error snapshots separately as `status_snapshots`, and exports
  no replay report in live mode.
* **Label tool** requires absolute bag frame indices, treats a new valid results file as a new
  recording, applies file selections in order, rejects invalid numeric edits, keeps imported evaluator
  fields, draws the strict ±1.05 m envelope apart from the ±1.4 m advisory limit.
* **Foxglove** indicators show the last received value (`LAST`) and never expire: read the connection
  and `/resense/status`, or use the expiring web dashboard. Hero renders use the node's
  STOP / FAULT / CAUTION / GO precedence and refuse a missing frame.

## Repeatable checks

```bash
RESENSE_REQUIRE_WEB=1 python -m pytest -q -rs web/demo tests/test_overview_video.py
python scripts/detector_freeze.py verify
ruff check .
python scripts/make_overview_video.py --check
python web/demo/check_status_compatibility.py --out out/p2-review-status-compatibility.json
mkdir -p out
gzip -dc docs/evidence/docker_2026-09-23/obstacle_status.jsonl.gz > out/p2-review-real.jsonl
python web/demo/check_dashboard.py --jsonl out/p2-review-real.jsonl \
  --speed 2 --min-dist 55 --max-dist 57 --screenshot out/p2-review-real.png
```

Last recorded run (28.09, [`demo/evidence/p2_criteria_2026-09-28.json`](demo/evidence/p2_criteria_2026-09-28.json),
which also holds the hashes of the committed PPTX, PDF, MP4, SRT and screenshots): the P2 checks passed
with no skips; the browser validator accepted all 4 760 archived status records in 18 files and all 982
statuses in 4 supported-playback captures; the real replay showed STOP at 56.1 m. These prove UI
compatibility with archived data, not detector recall.

Not checkable in this clone: the organizers' bags (`/data/for_hackathon`), the git-ignored private
deck data, a physical second device and human rehearsals. The CI two-container probe is a protocol
check, not a visual Foxglove import.

## Rebuild of 28.09 evening

* The dense public slides 5 and 15 shortened without changing a measured claim; the 16-slide
  PPTX / PDF and the 170 s video rebuilt from those sources (new hashes in the evidence JSON); PDF
  pages 2, 3, 5, 9, 11, 13–16 inspected at presentation size; `make_overview_video.py --check`:
  7 blocks, 17 shots, 38 cues, 23 cards, 170 s; the `.srt` unchanged.
* Rechecked on these binaries on 29.09 (sandbox, Playwright 1.56 + Chromium 141): the full P2 command
  above, **83 passed, 0 skipped** (`rebuild_recheck` in the evidence JSON).
* `build_deck.py --team` smoke-built with four synthetic portraits and complete example fields (16
  slides, all four names on slide 3, no unfilled field on slides 2–4); the empty example JSON fails
  before the build with the list of missing fields. The team's real data are not in the repository:
  P2 collects them ([`DEMO_HANDOFF.md`](DEMO_HANDOFF.md)).
* [`DEMO_HANDOFF.md`](DEMO_HANDOFF.md): the operator sequence on the stand, the second-device Foxglove
  check, the stale-indicator caution, the offline fallback and what to record at each rehearsal. A
  runbook, not a completed rehearsal.
* The public team cards in `build_deck.py` were changed after this rebuild (P1: submission; P2:
  pitch, deck, video): the committed PPTX / PDF show the old cards until P2's next rebuild.

## Experimental branch evidence

The P3 and health changes integrated on the experimental branch are documented in
[the integration record](../docs/P3_SCORE_SYNC_2026-09-28.md). The independent 61/100 judgement
quoted here remains specific to `464f5bc`; it is not a new score for the combined branch.
