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
intrusion misses. V2 reserved clouds remain untouched until the candidate identities
are fixed and the full real gate passes.

## Reproducibility repair

Rebuilding the full ride exposed that the tools Docker image pinned a bag reader
without standalone `.db3` support. The pin and minimum dependency are corrected,
and a real SQLite/CDR test covers directory and metadata-free split reads.
[Repair and focused checks](evidence/cycle_2026-09-28/tooling/README.md).

The score branch now enables the existing full Docker checks and offline image
artifact retention. The workflow must finish successfully before its outputs count
as evidence; merely enabling the checks does not improve detection quality.
