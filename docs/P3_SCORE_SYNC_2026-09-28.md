# P3 and score-branch synchronization — 28 September 2026

The user requested synchronization of code and communication with P3.

## Sources and communication

- P3: `experiment/cross-ring-sparse-evidence`, `6385ff9`, including the fresh
  STOP-onset candidate and measurements at `290c337`.
- Score checkpoint: `gpt-score-push-20260928`, `8547009`; its bounded low-height
  continuation was measured at `ef1d8f5` and integrated at `84763cf`.
- Combined work: `integration/p3-score-sync-20260928`, based on P3's branch with
  the complete score-branch history merged in. [PR #24](https://github.com/pmixay/ReSense/pull/24)
  was merged as `f41d20a`; ongoing work is on `experiment/cross-ring-sparse-evidence`.
- [Handoff to P3's commit author](https://github.com/pmixay/ReSense/commit/290c33737662c91095a8d33de19f20122fe38ec5#commitcomment-202461504).
  A reply has not yet been received. The integration PR is the shared
  review channel; the separate P3 agent process is not visible on this app server.

No force push or rewrite of P3 history is part of this synchronization.

## What each candidate establishes

| Candidate | Measured benefit | Remaining acceptance |
|---|---|---|
| P3 fresh STOP onset | Reported empty-ride events 32 to 27; frames 130 to 117; episodes 31 to 26 | Default-off; six short real bags and full Linux acceptance missing; underlying A/B files need portable publication |
| Bounded low-height continuation | Raw rail STOP coverage 123 to 126/126 after frame 75; person stays 61/61 | Quality/history/reserved and merged-source CI passed; cold-start fresh coverage is incomplete; local positive runtime failures remain recorded |

Neither result establishes overall superiority. The established earlier score remains
69/100. A separate reviewer rated both the earlier baseline and `ef1d8f5` at
66/100 under one rubric: zero whole-point regression. These are reviewer judgments,
not automated test scores. A later independent review scores the combined source 67 and the health optimization
67.5 under the same rubric (+0.5 speed); see [current scorecard](SCORECARD.md).
The enabled P3 experiment has not yet received acceptance or score credit.

## Integration rules

Keep the validated continuation default at 0.3 seconds. Keep fresh STOP evidence,
cross-ring filtering, and local bed support disabled in the default configuration.
Preserve P3's opt-in configurations and experiment history.

Weak low-object continuation must have explicit `keep_low` provenance. It cannot
count as fresh evidence or start a STOP. Update the earned-STOP state only after
all continuation limits and opinion decisions have been applied. Cover the
near-escalation and long-gap reacquisition interactions explicitly; a measured
recall loss must remain visible rather than being hidden in aggregate parity.

The combined source `b84ea8f` passed its full native default gate on 28 September:
all 146 enforced rows unchanged, no waivers or missing rows. The new 34-file seal
binds that source to the [archived evidence](evidence/cycle_2026-09-28/p3_sync/default/README.md).
Per-frame negative alarms and monitoring coverage are unchanged. This accepts
the merged defaults for development; the experimental onset rule stays opt-in.

The user explicitly requested merging PR #24 and continuing work directly on
`experiment/cross-ring-sparse-evidence`. That branch is the ongoing work branch.
CI now runs the original-bag and offline-image checks on it. The earlier
`gpt-score-push-20260928` branch is a preserved checkpoint. CI on the score source
passed full-rate positive and clear bags; local positive runtime failures remain
recorded, and merged-source CI is tracked separately.

## Completed CI checkpoint and cold-start availability

All four jobs passed for both the [merged experimental head `25a218a`](https://github.com/pmixay/ReSense/actions/runs/36471997066)
and [PR head `f577a7c`](https://github.com/pmixay/ReSense/actions/runs/36471632628).
This includes the source seal, unit/browser tests, offline runtime image, transport
checks and original-bag cold-start regression. The [archived capture audit](evidence/cycle_2026-09-28/p3_sync/ci_25a218a/README.md)
retains exact run identities and lossless status captures; these links certify
those heads, not later commits.

Both runs processed all 201 positive and 252 clear source header stamps, and both
had zero freshness-contract violations. Availability is a separate result:

| CI head | Positive strict-current frames | Clear strict-current frames | Raw person matches | Fresh person matches |
|---|---:|---:|---:|---:|
| `25a218a` | 165/201 | 241/252 | 61/61 | 33/61 |
| `f577a7c` | 145/201 | 244/252 | 61/61 | 13/61 |

The experimental positive capture is stale or catching up through frame 35;
first sustained fresh person STOP begins at frame 36 (five consecutive source
frames), with fresh matches through frame 68. The PR capture becomes fresh later,
at frame 56. Invalid results restrict GO correctly, so contract compliance does
not imply full fresh-result recall. These CI timings are separate machine runs,
not a controlled performance comparison.

Rail matches are 128/185 overall and 126/126 from frame 75 onward, both raw and
fresh in both runs. First sustained fresh rail STOP is frame 73. Early rail
coverage remains only 2/59 visible frames before frame 75. Cold-start availability
and early rail misses remain work items; green CI does not remove them.

## Joint comparison

Use one common combined source with four declared configurations: both features
off, continuation only, fresh onset only, and both on. Keep the other experimental
flags off. Bind every result to source, effective config, input and tool hashes.

The [completed four-config raw positive comparison](evidence/cycle_2026-09-28/evaluation/p3_sync_raw_positive/README.md)
replayed all 201 original header-stamped frames per configuration. Continuation
restored rail frames 111, 117 and 197. Fresh onset caused no additional recall or
unmatched-detection change on this known recording; its broader acceptance stays
open.

1. Check onset, weak continuation, removal, long timestamp gaps, reacquisition,
   near escalation, and calibration-hold behavior.
2. Replay the original positive bag with exact frame/timestamp alignment. Retain
   target recall, unmatched detections, onset and missed intervals.
3. Run all six short bags, complete ride, set O and set F; compare the new defaults
   against the committed score-candidate gate and compare each opt-in variant.
4. Run paired history checks for any configuration proposed for default use;
   reject newly introduced false STOP frames/events and recall/range regressions.
5. Measure the final installed image's ROS behavior and freshness under matched
   conditions. Preserve the current failures and distinguish internal stage
   timing from full process and end-to-end timing.

The cycle's reserved synthetic split is spent. Reusing it provides a regression
check only; a fresh claim of generalization needs genuinely unseen evidence.
