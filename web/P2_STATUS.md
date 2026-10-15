# P2 status: work toward the 23.10 defence

> **Purpose:** P2's queue and acceptance state under `docs/BACKLOG.md` §5, through the 23.10 defence.
> **Audience:** team · **Owner:** P2 for the interface; the pitch, deck, demo and rehearsals are the
> captain's (P1) since 29.09 evening · **Language:** EN
> **Last verified:** 2026-10-15: current backlog, release refs/metadata, judgement 13.10, C1 contract
> availability and rebuilt deck. Commands and evidence: [`p2_2026-10-15`](../docs/evidence/p2_2026-10-15/README.md).
> **Status:** D1 pass 1 and PT1 slide cuts delivered; dependent items remain explicitly open.

P1 owns the pitch, speech, demo and rehearsals since 29.09 evening. P2 supports the deck visuals,
range chart, video cards and fallback, and owns the dashboard, label tool and RViz / Foxglove layouts.
The new named deck preserves the four names and photos; the template's required slides 7–11 keep
their structure. Speech/Q&A and final approval: [`PRESENTATION.md`](../docs/PRESENTATION.md).

Dates: upload 29.09 by 23:59 MSK; technical expertise 30.09–14.10; pitch 23.10 (online); awards 30.10.

## Queue and acceptance

| item | state on 15.10 | next input / acceptance |
|---|---|---|
| **D1 pass 1** | corrected release/tag, current 66/100 score, gate baseline, ownership, dual-return claim, range/pipeline labels and stale branch state; decision log preserved | P1 review/merge; no score gain claimed |
| **PT1 task 2: slide cuts** | 16-slide PPTX + PDF rebuilt; detail moved to notes; build enforces ≤80 words/slide and ≤1,100 total, counting chart labels | counts, PDF inspection and gate check in evidence; P1 final sign-off pending |
| **C1 display** | waiting: no `decision_policy.py` or `caution_reason` producer contract in current `main` | P1's additive `[contract]` status payload and examples; then P2 updates RViz/web display and consumer checks |
| **PT1 range chart / final numbers** | historical cache graph clearly labelled as preparation; context from 13.10 is labelled separately | P4 J1 on released v1.1.0 / final seal: first STOP by straight, curve, double-track, platform × person/1 m/0.3 m; P2 renders ≥3 geometries; P1 chooses version under O1 |
| **PT2 fallback / second device** | runbook prepared; existing 69 s clip is explicitly the 23.09 archive | released v1.1.0 image and checksum, captain's demo machine + second device; record commit/image ID, STOP/distance and forced switch ≤30 s |
| **D1 pass 2 / S5 / video cards (21.10)** | waiting for final shipped image, S1/S2 and J1 | rerun docs/deck checks; S5 on idle ≥8 physical cores with four S1 chain conditions; render cards from final numbers |
| Dashboard / label tool / layouts | existing P2 deliverables, checked by `web/demo` | consumer display work resumes when C1 lands |
| **D2 archival cleanup** | scheduled after 23.10 in BACKLOG; not brought forward | after D1 and the session's docs commits; P1 approval, P4-lane coordination |

S5 hardware check: this workstation exposes **4 physical cores / 8 threads** (`lscpu -e`),
so it does not meet the ≥8-physical-core requirement, regardless of `nproc` reporting 8.

## Final PDF sign-off

Pending P1 after O1/J1 and the range-chart replacement. The 15.10 PDF is the **slide-cut preparation**,
not a claim that PT1 as a whole has passed. The original 29.09 speech in PRESENTATION is labelled
historical and must be updated before rehearsal.

## Rehearsals

None held yet. For each rehearsal add one line here: date; demo commit and image ID; total time and the
slides that ran over; live demo pass or fail (STOP and distance in RViz); whether the switch to the
fallback video was tried and how long it took.
