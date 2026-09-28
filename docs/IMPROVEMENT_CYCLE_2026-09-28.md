# Improvement cycle — 28 September 2026

The user authorized further implementation, synthetic evaluation and fresh-context
GPT-6 Astra checkpoints on `gpt-score-push-20260928`. Each detector candidate must
pass its stated acceptance checks before it becomes the default. The existing
regression thresholds remain in force. GitHub release publication is a separate
workflow; commits here are development and validation checkpoints.

## Starting assessment

The lead review at `f5db6d3` is **69/100**. A fresh-context Astra review of the same
behavior is **68/100** using the same internal weights. Neither is an organizer
score. The reviewer encountered earlier scores while reading evidence, so it was
not numerically blind. These are individual judgments, not a measured one-point
regression or a new averaged score.

[Checkpoint 0](evidence/cycle_2026-09-28/checkpoint0_astra.json) records the category
scores, observed failures, next actions and a correction to its use of an older
presentation manifest. The most valuable gains remain detection continuity,
small and edge objects, sustained range and false alarms on real recordings.

## Acceptance sequence

1. Record the defect and acceptance conditions before implementing a candidate.
2. Test the causal behavior and removal, ambiguity, timing and false-positive controls.
3. Replay the original positive bag and compare individual detections, including
   unrelated STOPs, against the default implementation.
4. Run the complete strict regression gate: six recordings, all 1,510 organizer
   object frames, all 11,271 ride frames and the existing synthetic set F.
5. Compare monitoring costs and processing-history stress. Preserve adverse findings.
6. Freeze candidate source/config hashes before the reserved synthetic evaluation.
   Compare baseline and candidate on identical float clouds and their quantized pairs.
7. Run the gate on committed proposed defaults in the isolated candidate checkout.
   Review the evidence, integrate those exact measured files and replace the source
   seal. Run the final image and branch CI checks.
8. Request a fresh-context checkpoint review; score only demonstrated improvements.

The [synthetic protocol](evidence/cycle_2026-09-28/evaluation/protocol.json) was
committed before this cycle's candidate results. Generated arrays remain outside
Git; reports retain provenance and per-frame results. Previously examined real
recordings and synthetic cases are development data. Synthetic evaluation cannot
establish performance on an unseen real route.

The [v2 amendment](evidence/cycle_2026-09-28/evaluation/protocol_v2.json) corrects
physical-envelope placement before any v2 generation: both low shapes penetrate
the envelope in each split, and a below-rail negative control is added. The
[geometry audit](evidence/cycle_2026-09-28/evaluation/diagnosis-v1.md) preserves v1
results and explains why boundary-only cases cannot be counted as demonstrated
intrusion misses. V2 reserved clouds were generated only after the identities were frozen and the
full real gate passed. The split is now spent; both variants have identical outputs
and weak absolute recall, documented in the reserved comparison.

## Reproducibility repair

Rebuilding the full ride exposed that the tools Docker image pinned a bag reader
without standalone `.db3` support. The pin and minimum dependency are corrected,
and a real SQLite/CDR test covers directory and metadata-free split reads.
[Repair and focused checks](evidence/cycle_2026-09-28/tooling/README.md).

The score branch now enables the existing full Docker checks and offline image
artifact retention. The workflow must finish successfully before its outputs count
as evidence; merely enabling the checks does not improve detection quality.


## Checkpoint 1 — evening

The [fresh-context Astra review](CHECKPOINT1_REVIEW_2026-09-28.md) gives **66/100**
without reading prior scores. This is an independent assessment, not a same-reviewer
three-point regression from the earlier 69. It supports development integration of
exact measured candidate `ef1d8f5`, integrated as `84763cf`, with deployment provisional.

- Raw rail STOP coverage improves 123 to 126/126 after frame 75; person remains 61/61.
- The complete gate has two enforced improvements and 144 unchanged metrics, no waivers.
- All 33 history captures are byte-identical; false events remain 32 on the ride.
- Reserved synthetic outputs are identical for both variants: sustained positives
  14/32 float32 and 13/32 compact16; no synthetic improvement is claimed.
- The installed image passes 841 tests. The quiet local positive ROS run fails
  freshness and 100 ms decode-plus-detect p95 for both variants; the candidate's
  clear run passes. Full candidate CI is pending.

P3's new experimental branch `experiment/cross-ring-sparse-evidence`, commit
`290c337`, separately reports 32 to 27 false ride events with fresh STOP-onset
support, disabled by default pending the missing six-bag validation. It has not
been merged or included in this score. Its onset rule and this continuation rule
may complement each other; their joint recall/false-alarm behavior needs a new
registered comparison. Weak low continuation must never be counted as fresh
onset evidence when combining them.


### Score reporting correction

Keep **69/100 as the established earlier baseline assessment** and retain the
independent **66/100** as a separate review. The initial checkpoint headline
incorrectly implied that a different reviewer established a decrease from 69.
There is no such paired measurement. The actual quality pair improves continuity
and preserves the other enforced metrics. A same-reviewer comparison is being
recorded before assigning any score change. No code or evidence is rolled back,
and neither review is hidden or relabeled as an automated test result.
