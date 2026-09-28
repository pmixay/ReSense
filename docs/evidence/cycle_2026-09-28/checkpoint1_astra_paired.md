# Same-reviewer paired checkpoint assessment

**Baseline: 66/100. Continuity candidate: 66/100. Within-review delta: 0 points.**

These are GPT-6 Astra’s review judgments under identical current evidence and the same internal weights, not measured performance percentages or organizer scores. The baseline is original detector behavior `4b6f344` / `f5db6d3`; the candidate is `ef1d8f50299d9ccbbf65fc4ad5519764615853f6`.

| Criterion | Weight | Baseline | Candidate |
|---|---:|---:|---:|
| Detection performance | 25 | 17 | 17 |
| Detection range | 15 | 6 | 6 |
| Speed | 10 | 7 | 7 |
| Generalization | 15 | 6 | 6 |
| Technical development | 10 | 9 | 9 |
| Ease of launch | 10 | 8 | 8 |
| Team approach | 10 | 9 | 9 |
| Pitch | 5 | 4 | 4 |
| **Total** | **100** | **66** | **66** |

## What changed

The candidate recovers three raw rail-object frames: **123/126 → 126/126** after frame 75, a **2.38 percentage-point** improvement on that subset. Person detection stays 61/61. This is a measured improvement, but too narrow to change the whole-point detection rating given unchanged real-positive coverage, range and false alarms. Equal rubric scores do not mean identical detector performance.

All 33 history captures are identical. Reserved synthetic outcomes are identical: 14/32 sustained positives with float32 and 13/32 with compact encoding, with zero negative STOP frames out of 64 for each. Both quiet full-speed local runs fail freshness and the 100 ms target. The candidate has 198/201 statuses and p95 decode-plus-detect 125 ms; baseline has 166/201 and 137 ms. This single unrandomized pair does not establish a speed gain.

## Common tooling and evidence

Evaluator/provenance fixes, the physical-label protocol, regression tooling, source freeze, packaging and ROS observer evidence are assessed consistently for both detector variants. These improve measurement and reproducibility; they are not continuity-detector gains. The candidate’s 841 passing image tests and baseline/tooling CI are distinct validation artifacts; this review does not claim identical suites ran on both. The historical baseline is not penalized simply for predating common cycle tooling.

Development integration remains supported by the narrow continuity gain and absence of measured quality regression. Deployment remains provisional because of the shared runtime acceptance gap.

## Relation to the earlier 69

**Do not report this as 69 → 66.** The earlier reviewer’s 69 and this reviewer’s 66/66 use different reviewer judgments and evidence contexts. They cannot be subtracted to infer regression. This paired assessment neither replaces nor retroactively revises the earlier 69.

No new tests or code changes were made. The completed independent review remains untouched. Evidence paths and structured fields are recorded in `checkpoint1_astra_paired.json`; the underlying detailed candidate assessment is `checkpoint1_astra.json`.
