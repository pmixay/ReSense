# P2 status: work toward the 23.10 defence

## Current execution — 21.10

User requested local P2 work. Public URL supplied by the user:
https://resense.arbuz.lol/; no deployment performed for this asset/document work.
The 20.10 publication statement below is a historical receipt, not a current URL check.

- [x] ~~Short Falcon bag~~: original 280–330 s window, 499 CDR messages, metadata,
  archive/raw hashes, `ros2 bag info`, actual DDS/RViz playback. Person STOP in 3.79 s
  after command; independent raw-person trajectory check. [Receipt](../docs/evidence/p2_defence_2026-10-21/falcon_playback.json).
- [ ] Fallback + second device: new local 1.2.0 capture prepared; P1 image selection,
  physical second-device test and forced switch ≤30 s still required.
  - [x] ~~Local clip~~: 105.667 s, full decode PASS; both raw DDS streams checked;
    cloud, gauge, STOP and distance visually inspected.
- [ ] PT1: source-labelled review PPTX/PDF prepared; final J1 and P1 approval pending.
  - [x] ~~Visual draft~~: 16 slides, 1,020 words, max 80; chart values match their
    dated sources, PDF inspected, title/team slide XML preserved.
- [ ] D1: current handoff and source-labelled figures prepared; final numerical pass
  in documents/GitBook awaits J1.
  - [x] ~~Local preparation handoff and dated corrections~~: linked to actual
    receipts; historical pitch text explicitly superseded; new local links checked.
- [ ] Two team rehearsals: no completion claimed.

Detailed per-subtask acceptance: [checklist](../docs/evidence/p2_defence_2026-10-21/README.md).
Start here: [P1/P2 handoff](../docs/evidence/p2_defence_2026-10-21/HANDOFF.md).

## Previous dated status

**20.10 code handoff:** [execution plan](../docs/evidence/p2_2026-10-20/PLAN.md)
and [verification receipt](../docs/evidence/p2_2026-10-20/README.md). The UI/main
integration and scoped rendering/navigation/live-replay fixes are verified locally.
Preview publication is complete at [resense.arbuz.lol](https://resense.arbuz.lol/) (22.10: the earlier preview host now serves another app);
the [publication receipt](../docs/evidence/p2_2026-10-20/PUBLISH.md) records the public checks.
**Asset cleanup, 20.10:** all five unused root reference images deleted at the
user's request; the P0 photo item is complete. Remaining non-code deliverables
are recordings, visuals, documents and device/rehearsal work. The dated queue
below retains its historical verification dates.

> **Purpose:** P2's queue and acceptance state, through the 23.10 defence; the current work and priorities of P2 are in
> [`docs/BACKLOG.md`](../docs/BACKLOG.md) "Current plan" (P2 table).
> **Audience:** team · **Owner:** P2 for the interface; the pitch, deck, demo and rehearsals are the
> captain's (P1) since 29.09 evening · **Language:** EN
> **Last verified:** 2026-10-23: version statements only (version-state pass: v1.2.0 is the published release, 1.3.0 an unreleased candidate, 66/100 is v1.0.0's); 2026-10-22: the receipts and figures of the 21.10 block (clip length, message counts, first-STOP times, 16 slides / 1 020 words), file names and links re-checked against the repository at 1.3.0 (`f24d939`); the queue itself is still the state of 16.10 / 19.10, and the preview host and rehearsals are not re-verified; earlier: 2026-10-16: fetched integration `b0c9c17`, participant handoffs and active P4
> protocol `058a451`; local 1.1.0 seal verification PASS. Review:
> [`p2_plan_2026-10-16`](../docs/evidence/p2_plan_2026-10-16/README.md).
> **Status:** the queue below is the state of 16.10 (statuses of 19.10: 1.1.0 will not be released, J1 and G3 run on the final
> 1.2.0 seal; P2's UI branch was merged by PR #47 on 20.10 as `8453458`; the branch no longer exists). Execution receipt:
> [`p2_execution_2026-10-16`](../docs/evidence/p2_execution_2026-10-16/README.md).
> **Clean-up 19.10:** only stale version/seal statements were corrected, from `DECISIONS.md` rows 35–42; the queue itself is P2's.

16.10 update: all 47 webapp E2E tests pass on the frozen build. P4 `6d6aaca`
export/archive verified and accepted; a draft PPTX/PDF and charts (folder removed 19.10)
prepared with corrected prerelease captions. Final release J1 and P1 approval
remain pending; no new score or held-out claim.

**Execution plan of 16.10 (archived, superseded by BACKLOG "Current plan"):** [`docs/archive/ROLE_2_PLAN.md`](../docs/archive/ROLE_2_PLAN.md).
Checkpoint reconciliation and C1 consumer implementation are prepared for review. Package 1.1.0 is
sealed but will not be released (captain, 19.10); at that time (16.10 / 19.10) published v1.0.0 and its 13.10 score **66/100** were the release/score
reference; v1.2.0 was published on 20.10 and is now the current release (the 66/100 belongs to v1.0.0 only, v1.2.0 was not scored by our judge). H1 free-top and S1 were withdrawn, runtime C1 v2 rejected; shared v1 and its additive
reason contract are available. Final charts/media follow P4's J1 on the final 1.2.0 seal and P1's O1/E1 decisions.

P1 owns the pitch, speech, demo and rehearsals since 29.09 evening. P2 supports the deck visuals,
range chart, video cards and fallback, and owns the dashboard, label tool and RViz / Foxglove layouts.
The new named deck preserves the four names and photos; the template's required slides 7–11 keep
their structure. Speech/Q&A and final approval: [`PRESENTATION.md`](../docs/PRESENTATION.md).

Dates: upload 29.09 by 23:59 MSK; technical expertise 30.09–14.10; pitch 23.10 (online); awards 30.10.

## Queue and acceptance

| item | state reconciled 19.10 | next input / acceptance |
|---|---|---|
| **D1 / P2-01** | current version/source, older measurements and open acceptances reconciled; ffprobe confirms 180 s; [receipt](../docs/evidence/p2_d1_2026-10-19/README.md) | P1 shared-document approval; final numerical pass after J1 |
| **PT1 task 2: slide cuts** | 16-slide PPTX + PDF rebuilt; detail moved to notes; build enforces ≤80 words/slide and ≤1,100 total, counting chart labels | counts, PDF inspection and gate check in evidence; P1 final sign-off pending |
| **C1 display** | producer/consumers implemented; [18.10 N1/N4](../docs/evidence/n1_n4_2026-10-18/README.md) adds actual DDS/graphics/marker expiry on named earlier sources | final merged-image RViz/Foxglove, all reason cases and physical-device acceptance remain open; runtime v2 rejected |
| **PT1 range chart / final numbers** | historical cache graph clearly labelled as preparation; context from 13.10 is labelled separately | P4 J1 on the final 1.2.0 seal (the 1.1.0 target is dropped): first STOP by straight, curve, double-track, platform × person/1 m/0.3 m; P2 renders ≥3 geometries; P1 chooses the version under O1 |
| **PT2 fallback / second device** | runbook prepared; existing 69 s clip is explicitly the 23.09 archive | P1-selected permitted release image/checksum (v1.0.0 fallback if O1/E1 pending, as planned on 16.10; v1.2.0 has been published since 20.10), captain's machine + second device; record commit/image ID, STOP/distance and forced switch ≤30 s |
| **D1 pass 2 / S5 / video cards** | after the reseal, the final image and J1 (P1 priority); available hardware accepted by captain 17.10 | S5 measures selected runtime even if S1/S2 remain unshipped; 2–4 cores acceptable, separate four-condition matrix; identify source versus release runs and render cards from accepted results |
| Dashboard / label tool / layouts | C1 reason display and boundary regressions implemented; legacy label compatibility covered by web suite | actual viewer/device checks and P1 marker-text approval |
| **D2 archival cleanup** | the documents were moved on 19.10 (documentation clean-up); open: tests with personal paths, orphan scripts (P2, after 23.10) | P1 approval, P4-lane coordination |

S5 hardware check recorded 16.10: that workstation exposed **4 physical cores / 8 threads**
(`lscpu -e`). The captain removed the 8-core prerequisite on 17.10: proceed on available
hardware with topology/quota and measured results recorded. CI billing/quota is the captain's
task; release waits until CI is fixed, while development and source measurements continue.

## Final PDF sign-off

Pending P1 after O1/J1 and the range-chart replacement. The 15.10 PDF is the **slide-cut preparation**,
not a claim that PT1 as a whole has passed. The original 29.09 speech in PRESENTATION is labelled
historical and must be updated before rehearsal.

## Rehearsals

None recorded here. (22.10: no rehearsal outcome is recorded in the repository, so none is stated; rehearsal 1 of 20.10 and rehearsal 2 of 22.10 are filled in from the template below only after they have taken place and been checked.)

Planned by the captain on 19.10 (roles, pass criteria and the speech:
[`PRESENTATION.md`](../docs/PRESENTATION.md) «Репетиции»). The live demo is 1.2.0 (an image built from
the final 1.2.0 commit, P1's choice): Pandar `doubleT_obstacle`, then the Falcon recording in the same node.

| # | date | scope | P2's part |
|---|---|---|---|
| 1 | **20.10** | full talk with a per-slide stopwatch; live demo (choose `--rate`; the short Falcon demo bag exists, 432 frames; play it at `--rate 1.0`, see PRESENTATION); first Q&A drill | second device: join the call as a viewer, confirm the shared RViz is readable, keep the fallback clip [`docker_chain_rviz.mp4`](../docs/video/docker_chain_rviz.mp4) open and start it on the captain's cue |
| 2 | **22.10** | dress rehearsal on the final deck and image; **forced** switch to the fallback clip; full Q&A drill | the same; perform the forced switch and time it |

Pass criteria: total ≤ 5:00; Pandar STOP visible ≤ 30 s after playback starts; switch to the fallback
clip ≤ 30 s; answers only with the numbers of PRESENTATION's table. Copy the template below for each
rehearsal **after** it has taken place; an empty template is not a rehearsal.

```text
### Rehearsal N — DD.10, start HH:MM
- Present and roles: P1 speaks and drives the demo; P2 second device and fallback clip; P3, P4 mock jury and stopwatch
- Deck: commit …; PPTX / PDF
- Image: tag …; `docker image inspect` ID …; source commit …; `detector_freeze.py verify` …
- Bags: Pandar doubleT_obstacle (sha256 …); Falcon … (sha256 …); --rate …
- Time per slide (plan / actual): 1 0:08/… 2–3 0:15/… 4 0:13/… 5 0:20/… 6 0:13/… 7 0:15/… 8 0:15/…
  9 0:22/… 10 0:55/… 11 0:25/… 12 0:15/… 13 0:08/… 14 0:25/… 15 0:15/… 16 0:12/…
- Total: m:ss (≤ 5:00 yes/no); slides that ran over: …
- Demo: Pandar STOP after … s of playback, distance … m; Falcon: profile …, first STOP … m after … s;
  FAULT or stale results after the first frame: …
- Fallback: switch tried yes/no; … s (≤ 30 s yes/no)
- Q&A: who asked, question number, answer within 30 s yes/no, what to fix
- Result per criterion: pass / fail; what to fix before the next one
```
