# Checkpoint 2 — independent source and priority review

Reviewed 28 September 2026: `/home/likikikpa/ReSense-p3-sync`, branch `experiment/cross-ring-sparse-evidence`, commit `25a218a0a8b4e10089dfcf73b8d557d4a963290e`.

## Assessment: 67/100

This is a fresh-context, evidence-informed internal judgment, not a blinded review, organizer award, measured percentage, or new paired comparison. I read the official §8 rubric, SCORECARD, CURRENT_REVIEW and CHECKPOINT1_REVIEW, inspected production code and newer evidence, and checked source/archive hashes. I ran no detector jobs, tests, or internet searches. GitHub was used only to read CI status.

Preserve the established **69/100 lead assessment** and the independent same-reviewer **baseline 66 / candidate 66, delta 0** as separate records. My 67 is neither a one-point measured code gain nor a two-point regression from 69. New CI evidence justifies slightly more confidence in runtime and launch; detection gains beyond the accepted continuity change remain unproved.

| Criterion | Score / maximum | Current basis |
|---|---:|---|
| Functionality | 17/25 | Raw person 61/61 and rail 126/126 after frame 75; rail only 128/185 overall. Current ride still 32 false events / 31 STOP episodes. |
| Range | 6/15 | Real positives remain around 56 m; small/edge synthetic cases remain weak. No reliable real 100–300 m evidence. |
| Speed | 7.5/10 | Accepted continuity-source CI processes all positive frames with decode-plus-detect p95 78 ms and fresh results. Quiet laptop p95 125 ms and no fresh results remain valid; current merged-source CI and health runtime validation are pending. |
| Generalization | 6/15 | Reserved synthetic sustained positives remain 14/32 float and 13/32 compact. No unseen real-positive route. More known-recording checks do not close that gap. |
| Technical quality | 9/10 | Strong source provenance, retained failures, strict gates and bounded continuity. Full-call timing remains omitted from detector `total`; monitoring can overstate useful range. |
| Launch | 8.5/10 | Archived cold CI positive 201/201 and clear 252/252 pass; original-bag output is retained and label checked. New merged-source CI is still running and physical rehearsal remains unverified. |
| Approach | 9/10 | Rejected hypotheses and comparison limitations are recorded. |
| Pitch | 4/5 | Existing presentation artifacts; no new human-delivery evidence reviewed. |
| **Total** | **67/100** | No credit for unaccepted health or opt-in detector candidates. |

## Evidence that changes the picture

1. `docs/evidence/cycle_2026-09-28/p3_sync/default/gate.json` passes against `ef1d8f5`: 146 enforced metrics unchanged, with 208 unchanged comparison rows including informational rows. It covers six short recordings, 11,271 ride frames, O and 30 F cases. Recorded wall time is 820 seconds with four workers, native backend, one numerical thread per worker. Timing under shared load is not performance acceptance.
2. The four-config header-clock comparison independently establishes raw continuity and onset parity. I recomputed all five capture/report hashes and compared all 33 measured source inventory files with the reviewed checkout: every hash matches. All variants retain person 61/61; continuation restores rail frames 111/117/197, producing 128/185 overall and 126/126 after frame 75. All variants have six unmatched detection frames. Earlier rail coverage remains only 2/59 visible frames before frame 75. Fresh onset alone changes no public non-timing output on this recording.
3. Archived CI `36467904812` at `8547009` supplies stronger runtime evidence than checkpoint 1 had: positive 201/201, p95 decode+detect 78 ms, current-result end-to-end 96 ms; clear 252/252, zero alarms, 51/58 ms respectively. Positive current results number 165; startup catch-up ends at +3.6 seconds. This is continuity-source CI, not exact P3 merged-source runtime proof.
4. Exact reviewed HEAD run `36471997066` was in progress when checked. No pass is assumed. The histogram candidate in `/home/likikikpa/ReSense-health` is merged with the experimental source at `83bc5d8`, preserves `7885c6d`'s health implementation, and has 48 focused passing tests; combined gate/runtime acceptance remains pending. Its microprobe cannot support an accepted speed gain.

## Ranked next improvements beyond the histogram

Score ranges below are conditional reviewer estimates, not promised or additive points. Engineering time excludes queue delays. Compute budgets use the measured 820-second full native gate as a planning reference, not a guaranteed runtime.

### 1. Finish fresh STOP onset acceptance and resolve its near-escalation conflict

**Potential: 0.5–1.5 points, mainly functionality. Cost: roughly 2–4 engineer hours; one native gate about 15–30 minutes, followed by required histories/ROS only if the candidate survives.**

This is the only pending detector mechanism with a material measured event reduction: inspected Windows/NumPy ride 32→27 events, 31→26 STOP episodes, 130→117 STOP frames. Existing O metrics and limited F synthetic comparisons are unchanged; the new header-clock positive comparison also passes. These are development data, not independent generalization evidence.

The concrete obstacle is `tests/test_fresh_stop_evidence.py:186`: the candidate vetoes an otherwise accepted near escalation when the current cluster is advisory. `resense/tracking.py:410` applies the onset gate; `_fresh_stop_ok` at line 642 requires current strict gauge. `start_clean` at line 404 explicitly exempts near escalation, so these two policies conflict. Also, already earned STOP state can be reset after demotion, making re-entry relevant; inspect the four lost post-gap STOP frames and one-frame delayed onset reported for surviving ride tracks.

**Next action:** freeze a combined continuation+onset candidate and use the existing near-escalation cases to settle the intended safety policy before promotion. Do not simply exempt all advisory clusters or relax hit counts. If the rule changes, register that changed mechanism and discard any assumption that the earlier 5-event gain transfers. Run the full native gate, then paired processing histories and ROS raw replay with actual header stamps. Require retained person/rail coverage, first and sustained O/F distances, unmatched detections, monitoring range, and no new fragmentation. Keep the flag off if the conflict cannot be resolved without losing the benefit. Untouched positive data would strengthen confidence, but is not needed to identify and fix this policy conflict.

### 2. Correct full detector timing, then bound startup recovery if the optimized node still falls behind

**Potential: 0.5–1 point across technical quality/runtime/launch. Cost: approximately 1–3 engineer hours plus 30–60 minutes of quiet paired runtime and focused history validation; a broader gate is needed if processing history changes.**

`resense/detector.py:277–290` records `total` before health and passes that partial duration into the latency monitor. The histogram optimization deliberately leaves this measurement defect unchanged. Add an explicit health duration and unambiguous full-call duration; preserve the historical stage field or version its meaning so old results remain interpretable. Node `detect_ms` and decode-plus-detect remain the acceptance measurements. Changing latency warning inputs can change output when `latency_affects_decision` is enabled, so account for that contract explicitly.

The separate recovery flaw is in `ros2_ws/src/resense_ros/resense_ros/detector_node.py:743–757`: startup preservation expires only while `catchup is None`. Persistent overload can therefore keep startup handling active, with source-period sampling instead of normal thinning. The retained quiet traces show rising age and zero fresh results. Faster health computation may make this disappear on the tested laptop, but does not remove the condition.

**Next action:** finish the already-running histogram acceptance, then perform a quiet matched positive/clear ROS comparison. Correct telemetry regardless. Only if overload recovery remains an actual requirement, implement a finite startup-preservation deadline/backlog limit using the existing catch-up planner. Keep the freshness bound and STOP retention; report skipped original frames and detector history. A recovery policy that skips positive evidence is not an improvement merely because latency falls. Target hardware is unavailable, but this local state-machine defect is addressable without it.

### 3. Add conservative stationary sparse-evidence monitoring, with physical labels and coverage bounds

**Potential: 0–1 point, principally technical quality/functionality; no range or generalization credit from monitoring alone. Cost: 3–6 engineer hours, a small diagnostic screen, then one full native gate and per-frame coverage comparison if promising. Highest uncertainty of these three.**

`resense/evidence.py:111–143` chains sparse strict-envelope returns only through positive per-frame X displacement. `configs/default.yaml:375` requires 0.5–3.0 m per frame. A stationary box with two persistent strict returns cannot form that chain, even though `docs/evidence/cycle_2026-09-28/evaluation/diagnosis-v1.md` identifies two-voxel far boxes rejected by DBSCAN. `resense/detector.py:716–732` already has a monitoring-only integration point. This is a declared limitation, not an accidental implementation bug.

**Next action:** register a bounded stationary exception using current strict-envelope evidence and stable physical support; first confirm the mechanism on the existing v2 development captures. Require point-level physical envelope labels, low/background exclusions and an explicit limit on lost useful range in empty recordings. The old all-point cap lost 15–50% of useful range, so a global minimum-distance cap is not acceptable. Reduce genuine overclaims without creating an always-short estimate. Do not tune on reserved v2 outcomes or equate a capped estimate with detection. Existing 16 O flags use historical fitted geometry and need independent label validation before claiming a physical safety gain.

## Work that should not consume the next compute budget

- **Two-ring filtering:** only one fewer ride STOP frame, zero event reduction; synthetic coverage loss; O has fabricated/absent ring provenance. Most far events have multiple rings already.
- **Current low-local-support rule:** measured no false-event reduction and was rejected. More threshold sweeps do not supply a new mechanism.
- **Longer or simply translated accumulation:** the full-return oracle follow-up has zero pure-source >100 m candidates; three-frame recomputed membership produces 121 background gauge candidates, including 98 ordinary candidates. These are candidates, not STOP events. A source-only oracle result is not a production range gain.

Range work needs trustworthy vehicle pose/cloud registration and a way to distinguish small objects from nearby tunnel surfaces. See `resense/accumulate.py:20`, `resense/detector.py:485`, and the full-return oracle report. This is a larger research task with new evidence requirements, not a credible quick path to several points.

## Barriers versus fixable issues

- **Fixable locally:** partial latency telemetry; startup recovery condition; onset/near-escalation policy conflict; source/config acceptance of the existing candidate; bounded monitoring experiments.
- **Data barrier:** no untouched real-obstacle route, especially small/edge approaches beyond 100 m. Synthetic holdouts measure sensitivity and cannot establish that transfer.
- **Measurement barrier:** no early organizer-stand access or surveyed physical envelope labels. Missing stand access is uncertainty, not a failed mandatory test.
- **Human/delivery barrier:** physical second-device and timed human rehearsal. More automated documentation cannot establish either.

A score near 100 is not supported by the present observations. The next practical step is to finish histogram runtime acceptance, then prioritize the fresh-onset policy/acceptance work; defer large accumulation experiments until the pose and background-separation requirements are concrete.

## Follow-up: minimal near-escalation preservation candidate

After the parent requested a precise policy review, I inspected `_near`, `near_escalated`, `_continue_thin`, `_note`, `_qualifies`, `rule_zone`, and final opinion handling. **Support a guarded current-evidence exception for development evaluation**, with the following semantics:

1. In `_fresh_stop_ok`, first require `t.misses == 0`, `t.last is not None`, and a nonempty `evidence_hist`.
2. Before rejecting `last.zone != 'gauge'`, accept an already satisfied `t.near_escalated` only if `self._near(t.last)` and the latest provenance is `ordinary` or `off_gauge`.
3. Preserve the existing path for other evidence and the outer `q` / `rule_zone == 'gauge'` guard. The ordinary advisory path is recorded as `off_gauge`, so accepting only `ordinary` would leave the demonstrated conflict unresolved.

This is narrower than bypassing the entire fresh gate whenever `near_escalated` is true. `_continue_thin` at tracking line 613 can append a true near-history entry; a blanket bypass could let the current continuation supply a new onset. The latest-source guard excludes current `keep_thin`, `keep_low`, and `far_thin`. `_near` already excludes low-kind clusters, column demotions and untrusted axis/height demotions. Confirmation thresholds, column/approach precedence, calibration handling and subsequent opinion withholding should remain intact; the exception does not set a STOP directly.

**Hidden history limitation:** prior `keep_thin` matches can still contribute to `near_hist`. A current ordinary near match after such history can use the exception. That preserves the default near-history policy for a current ordinary match; it does not prove that all recent near hits came from ordinary evidence. Requiring all N prior hits to have noncontinuation provenance would be a separate stricter policy, could require storing at least `near_hits` provenance entries, and could introduce recall regressions. Do not silently combine it with this minimal correction.

The meaningful boundary cases are current advisory ordinary near support; current continuation rejected despite a true near history; mixed prior-thin/current-ordinary history with the preservation semantics explicit; and column/untrusted geometry/approach/opinion withholding retaining precedence. After those mechanism checks, the full gate must establish that false-event reduction survives and raw/synthetic recall and history behavior remain acceptable. No such result is presumed here.

The parent reports histogram evaluation source `ef71c9d` has started its full gate. I did not rerun or independently verify that ongoing job; the review's pending status is unchanged.
