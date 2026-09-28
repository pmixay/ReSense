# P2 status: pitch, video, deck and demo

> **Purpose:** P2's deliverables, their state and what is left before the upload (29.09) and the pitch (23.10).
> **Audience:** P2, team · **Owner:** P2 · **Language:** EN
> **Last verified:** 2026-09-29: deliverables checked against `docs/presentation/`, `docs/video/`, the
> hashes in [`demo/evidence/p2_criteria_2026-09-28.json`](demo/evidence/p2_criteria_2026-09-28.json) and the
> independent judgement of 28.09 ([`SCORECARD.md`](../docs/SCORECARD.md))
> **Status:** current

Since 28.09 P2 (frontend) also owns the pitch and the video: P2 leads the defence on 23.10 and owns the
overview video and its optional voice-over, the public and the private deck, the two rehearsals and the
live remote demo (Foxglove from a second device). The captain (P1) sends the submission. How to build,
rehearse and present: [`docs/PRESENTATION.md`](../docs/PRESENTATION.md); requirement-by-requirement
evidence and checks: [`P2_REVIEW.md`](P2_REVIEW.md).

Dates: upload 29.09 by 23:59 (target 18:00); technical expertise 30.09–14.10; pitch 23.10; awards 30.10.

## Deliverables

| deliverable | state | left (P2) |
|---|---|---|
| Web dashboard, label tool, RViz and Foxglove layouts | done; `web/demo` checks in CI job `pytest`; the remote-viewer probe (`scripts/p2_viewer_test.sh`, second container, link pause and recovery) in CI job `docker` on `main` | visual Foxglove import on a physical second device (rehearsals) |
| Public deck `docs/presentation/ReSense_LCT2026.pptx` + PDF, 16 slides | built 28.09 by `scripts/build_deck.py`; committed files match the recorded hashes | decide on the differences from the independent judgement (PRESENTATION «Числа на слайдах и их источники»: latency, set O cubes and edge box, slide 3 still gives P1 the pitch): rebuild before the upload or state them in the talk |
| Private deck (`--team`) | not built; `docs/presentation/private/` is git-ignored and empty in this clone | names, nicknames, place of study, city, how the team formed, four portraits from the team; build; never commit |
| Overview video `docs/video/resense_overview.mp4` + `.srt` | 2:50, 1920×1080, 25 fps, no audio track, Russian subtitles burned in and as `.srt` | the same number differences in its cards and subtitles; optional voice-over read from the `.srt` and muxed without re-editing (fix the numbers first) |
| Fallback demo `docs/video/docker_chain_rviz.mp4` | committed: 69 s archival recording of the jury chain (v0.6.3, 23.09) | play it once on the pitch laptop |
| Live remote demo | runbook [`DEMO_HANDOFF.md`](DEMO_HANDOFF.md); PRESENTATION «Демонстрация» and [`README.md`](README.md) «Remote demo with Foxglove» | run it on the demo machine with a second device at both rehearsals |
| Rehearsals | none held yet | two timed rehearsals (PRESENTATION «Репетиции»); record them below |
| Submission links | public deck PDF and video in `main` | hand the final links to the captain by 18:00 on 29.09 |

## Rehearsals

None held yet. For each rehearsal add one line here: date; demo commit and image ID; the two devices
and the connection address; total time and the slides that ran over; live demo pass or fail (decision,
distance and corridor change during playback, a paused player is not shown as current, recovery after
resume); whether the switch to the fallback video was tried.
