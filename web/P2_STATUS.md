# P2 status: work toward the 23.10 defence

> **Purpose:** P2's queue and acceptance state under `docs/BACKLOG.md` §5, through the 23.10 defence.
> **Audience:** team · **Owner:** P2 for the interface; the pitch, deck, demo and rehearsals are the
> captain's (P1) since 29.09 evening · **Language:** EN
> **Last verified:** 2026-10-16: fetched integration `b0c9c17`, participant handoffs and active P4
> protocol `058a451`; local 1.1.0 seal verification PASS. Review:
> [`p2_plan_2026-10-16`](../docs/evidence/p2_plan_2026-10-16/README.md).
> **Status:** Role 2 implementation in review; completion remains blocked on external inputs.
> Execution receipt: [`p2_execution_2026-10-16`](../docs/evidence/p2_execution_2026-10-16/README.md).

16.10 update: all 47 webapp E2E tests pass on the frozen build. P4 `6d6aaca`
export/archive verified and accepted; [draft PPTX/PDF and charts](../docs/presentation/draft_2026-10-16/README.md)
prepared with corrected prerelease captions. Final release J1 and P1 approval
remain pending; no new score or held-out claim.

**Current execution plan:** [`docs/ROLE_2_PLAN.md`](../docs/ROLE_2_PLAN.md).
Checkpoint reconciliation and C1 consumer implementation are prepared for review. Package 1.1.0 is
sealed but unreleased; published v1.0.0 and its 13.10 score **66/100** remain the release/score
reference. H1 free-top and S1 were withdrawn, runtime C1 v2 rejected; shared v1 and its additive
reason contract are available. Final charts/media follow P4's release J1 and P1's O1/E1 decisions.

P1 owns the pitch, speech, demo and rehearsals since 29.09 evening. P2 supports the deck visuals,
range chart, video cards and fallback, and owns the dashboard, label tool and RViz / Foxglove layouts.
The new named deck preserves the four names and photos; the template's required slides 7–11 keep
their structure. Speech/Q&A and final approval: [`PRESENTATION.md`](../docs/PRESENTATION.md).

Dates: upload 29.09 by 23:59 MSK; technical expertise 30.09–14.10; pitch 23.10 (online); awards 30.10.

## Queue and acceptance

| item | state on 16.10 | next input / acceptance |
|---|---|---|
| **D1 pass 1** | corrections integrated; decision log preserved | P2-01 reconciles the newer selected scope; numerical pass after J1; no score gain claimed |
| **PT1 task 2: slide cuts** | 16-slide PPTX + PDF rebuilt; detail moved to notes; build enforces ≤80 words/slide and ≤1,100 total, counting chart labels | counts, PDF inspection and gate check in evidence; P1 final sign-off pending |
| **C1 display** | implemented for P1 review in both clients, backend metadata flow and marker text; consumer verification in execution receipt | actual selected-image ROS/RViz/Foxglove and visual acceptance remain open; runtime v2 remains rejected |
| **PT1 range chart / final numbers** | historical cache graph clearly labelled as preparation; context from 13.10 is labelled separately | P4 J1 on released v1.1.0 / final seal: first STOP by straight, curve, double-track, platform × person/1 m/0.3 m; P2 renders ≥3 geometries; P1 chooses version under O1 |
| **PT2 fallback / second device** | runbook prepared; existing 69 s clip is explicitly the 23.09 archive | P1-selected permitted release image/checksum (v1.0.0 fallback if O1/E1 pending), captain's machine + second device; record commit/image ID, STOP/distance and forced switch ≤30 s |
| **D1 pass 2 / S5 / video cards (21.10)** | final shipped image/J1 pending; available hardware accepted by captain 17.10 | S5 measures selected runtime even if S1/S2 remain unshipped; 2–4 cores acceptable, separate four-condition matrix; identify source versus release runs and render cards from accepted results |
| Dashboard / label tool / layouts | C1 reason display and boundary regressions implemented; legacy label compatibility covered by web suite | actual viewer/device checks and P1 marker-text approval |
| **D2 archival cleanup** | scheduled after 23.10 in BACKLOG; not brought forward | after D1 and the session's docs commits; P1 approval, P4-lane coordination |

S5 hardware check recorded 16.10: that workstation exposed **4 physical cores / 8 threads**
(`lscpu -e`). The captain removed the 8-core prerequisite on 17.10: proceed on available
hardware with topology/quota and measured results recorded. CI billing/quota is the captain's
task; release waits until CI is fixed, while development and source measurements continue.

## Final PDF sign-off

Pending P1 after O1/J1 and the range-chart replacement. The 15.10 PDF is the **slide-cut preparation**,
not a claim that PT1 as a whole has passed. The original 29.09 speech in PRESENTATION is labelled
historical and must be updated before rehearsal.

## Rehearsals

None held yet. For each rehearsal add one line here: date; demo commit and image ID; total time and the
slides that ran over; live demo pass or fail (STOP and distance in RViz); whether the switch to the
fallback video was tried and how long it took.
