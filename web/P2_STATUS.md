# P2 status: interface, and the pitch hand-over

> **Purpose:** the state of P2's deliverables and of the pitch material P2 handed over, before the upload
> (29.09) and the pitch (23.10).
> **Audience:** team · **Owner:** P2 for the interface; the pitch, deck, demo and rehearsals are the
> captain's (P1) since 29.09 evening · **Language:** EN
> **Last verified:** 2026-09-29 evening: the deck against `scripts/build_deck.py` (rebuilt, all 16 PDF
> pages inspected), the demo steps against [`docs/PRESENTATION.md`](../docs/PRESENTATION.md)
> **Status:** current; the deck's detector numbers are provisional until the final gate

**P2 declined the pitch on 29.09 evening.** The captain owns the pitch, the deck, the live demo and the
rehearsals, with agent help; P2 keeps the dashboard, the label tool and the RViz / Foxglove layouts. P2
delivered the deck layout with the team's photos and names (slides 2–3), which the build now reproduces
with `--team`. How to present, speech, Q&A and build: [`docs/PRESENTATION.md`](../docs/PRESENTATION.md);
demo runbook: [`DEMO_HANDOFF.md`](DEMO_HANDOFF.md); interface evidence: [`P2_REVIEW.md`](P2_REVIEW.md).

Dates: upload 29.09 by 23:59 MSK; technical expertise 30.09–14.10; pitch 23.10 (online); awards 30.10.

## Deliverables

| deliverable | state | owner / left |
|---|---|---|
| Web dashboard, label tool, RViz and Foxglove layouts | done; `web/demo` checks in CI | P2 |
| Public deck `docs/presentation/ReSense_LCT2026.pptx` + PDF, 16 slides (roles, no names) | rebuilt 29.09 evening: the rules of 29.09 (two on, `shell` off), 193 of 201 with no gap, 126 of 126, 81–82 ms, 1 279 tests; every number the gate measures in one `GATE` block, provisional (`r_1e2ed82`) | coordinator: final gate values, rebuild |
| Named deck (P2's photos and names on slides 2–3) | built by `build_deck.py --team`; the team approved committing it in place of the public one | captain runs the build (team data stay out of git) |
| Overview video `docs/video/resense_overview.mp4` + `.srt` | being re-rendered for the current numbers ([`docs/video/README.md`](../docs/video/README.md)) | video agent |
| Fallback demo `docs/video/docker_chain_rviz.mp4` | committed: 69 s archival recording of the jury chain (23.09) | — |
| Live demo | RViz in Docker on the captain's laptop, shared screen; Foxglove optional ([`DEMO_HANDOFF.md`](DEMO_HANDOFF.md)) | captain, at both rehearsals |
| Rehearsals | none held yet | captain and team; record them below |

## Rehearsals

None held yet. For each rehearsal add one line here: date; demo commit and image ID; total time and the
slides that ran over; live demo pass or fail (STOP and distance in RViz); whether the switch to the
fallback video was tried and how long it took.
