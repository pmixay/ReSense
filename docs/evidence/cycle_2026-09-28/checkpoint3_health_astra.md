# Checkpoint 3 — independent paired health histogram review

Reviewed 28 September 2026. **Accept the health histogram optimization. Paired internal assessment: baseline 67/100 → candidate 67.5/100, delta +0.5, entirely in speed.**

This review independently applies the same eight official §8 criteria and the established internal weights to both versions. The organizers do not publish these numerical weights. It is an evidence-informed judgment, not a blinded review, organizer score, or measured percentage. The historical lead **69/100**, prior paired **66 → 66**, and checkpoint 2's fresh **67/100** remain separate records. This review does not claim that the historical 69 dropped. No score is credited to the unaccepted fresh-onset candidate.

## Exact scope and recommendation

- Baseline source: `25a218a0a8b4e10089dfcf73b8d557d4a963290e`; baseline documentation checkout `abab723`.
- Candidate measured source: `ef71c9dc4f88147327dcb41ea79358dfc690ba77`; health evidence archive `5fa978f59d4e787bce04da3ab9b4257f5474d772`.
- Only production difference: `resense/health.py`, replacing explicit-edge NumPy histogram sorting with bounded binary-search bin counting. The final-edge inclusion, mixed float precision, nonfinite values and fallback dispatch are handled explicitly. I found no correctness blocker in the diff or test coverage.
- Recommendation applies to this optimization with existing defaults. Deployment performance remains provisional: evidence comprises one fixed-order, warm-disk local pair per recording, plus separate baseline CI. It does not establish cold candidate performance, target-hardware timing, universal speedup or complete fresh recall.

## Same-rubric paired scores

| Official criterion | Maximum | Baseline | Candidate | Delta | Basis and remaining limit |
|---|---:|---:|---:|---:|---|
| 8.1 Functionality | 25 | 17 | 17 | 0 | Identical detections; raw person 61/61, rail 128/185 overall and 126/126 after frame 75. Ride remains 32 false events / 31 STOP episodes. Fresh availability improvement is credited once under speed. |
| 8.2 Range | 15 | 6 | 6 | 0 | Known real positives around 56 m; small/edge weaknesses and no reliable real 100–300 m coverage persist. |
| 8.3 Speed | 10 | 7.5 | 8 | +0.5 | Positive processing p95 105.15 → 76.32 ms; current results 0 → 170/201. Clear p95 77.328 → 60.513 ms. One local pair, incomplete fresh coverage and positive current E2E p95 167.852 ms limit credit. |
| 8.4 Generalization | 15 | 6 | 6 | 0 | Reserved synthetic sustained positives remain 14/32 float and 13/32 compact. No untouched real-positive route. |
| 8.5 Technical quality | 10 | 9 | 9 | 0 | Strong provenance, bounded optimization, strict parity checks and retained failures. Partial detector timing and optimistic monitoring range remain. |
| 8.6 Ease of launch | 10 | 8.5 | 8.5 | 0 | Baseline exact-source CI passes all four jobs; installed candidate starts and completes both local bags. Launch procedure is unchanged; physical rehearsal and cold candidate acceptance remain unverified. |
| 8.7 Team approach | 10 | 9 | 9 | 0 | Registered mechanism, preserved failed prototype/baseline run, source identities and limitations. |
| 8.8 Pitch | 5 | 4 | 4 | 0 | Presentation artifacts unchanged; no new human delivery evidence. |
| **Total** | **100** | **67** | **67.5** | **+0.5** | Modest paired credit for a measured runtime improvement. |

The +0.5 is reviewer judgment about the evidence's strength. The measured observations are the latency, availability and unchanged-output figures below. Half-point precision does not imply measurement accuracy of the score.

## Evidence and independent checks

The full native gate passes with **208 identical comparison metrics, including 146 enforced metrics**, no waivers and no missing rows. Recorded exact semantic comparison covers **15,269 real/organizer frames** and **30 set F sequences / 3,060 actual frames**. No non-timing detection, warning, track/mount, clear-distance or non-latency health payload changes were found. The set F generator stops some approaches before its 110-frame maximum; 3,300 is not the actual row count.

Timing is deliberately separate: 15,252 frames change health timing and 2,333 change derived health level solely through the validated latency-warning rule, with `latency_affects_decision=false`. This is not byte-for-byte equality of every field. Shared-load gate timings are not performance acceptance. The retained test results report **48 passing focused tests / 150 complete health-state comparisons**, plus 27 passing comparator guard tests. I read their coverage and results; I ran no tests or detector jobs.

I independently verified **25 runtime/audit/capture file hashes**, both **34-file source maps against their exact Git commits**, the candidate gate's **34-file frozen source map**, and gate/freeze report hashes. Both installed-image maps differ only at `resense/health.py`; config, native library, packages and node hashes match. I reread the captures, recomputed processing p95 and current counts, and compared the recorded semantic fields on **all 453 paired original frames**: zero differences.

Source inventory hashes are baseline `2fd88d8ba35c62d17a9c5cfa49c73652ba849cbbf36d8691734363d3c062d0eb` and candidate `c0273a13a67ab4872dab00154caa75f6b30f50416775062c591fbb47906a0fa4`. Installed paired native hash `dc549d0583f92c3acd93c455bf94bab4bbedae35a9580d82ad24786473661d5c` differs from the in-place gate build `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`. The build routes differ; C++ source is unchanged. The runtime comparison itself uses identical installed native binaries.

| Local run | Processed | Decode+detect p95 | Strict current | Current E2E p95 | Checker |
|---|---:|---:|---:|---:|---|
| Baseline positive | 201/201 | 105.150 ms | 0/201 | Undefined | FAIL |
| Candidate positive | 201/201 | 76.320 ms | 170/201 | 167.852 ms | PASS |
| Baseline clear | 252/252 | 77.328 ms | 245/252 | 86.758 ms | PASS |
| Candidate clear | 252/252 | 60.513 ms | 250/252 | 73.777 ms | PASS |

Both clear runs have zero STOPs. Positive baseline freshness failures are retained. Candidate positive has 28 catchup, two source-stale and one epoch-unconfirmed result. Its fresh person recall is **49/61**, first fresh STOP at frame 16 and first five-frame sustained interval at 18. Fresh rail recall is **117/185**, including **115/126 after frame 75**, with first and sustained onset at 73. These counts exclude held STOPs and retain every visible source label in denominators. The four nominal missing time slots in the positive bag are intrinsic header gaps; both images process all 201 stored messages.

Archived exact-baseline CI `36471997066` passes all four jobs and supplies separate cold evidence, but fresh person recall is only **33/61** despite raw 61/61. Its host timing must not be compared directly with the local candidate to estimate a gain. The measured candidate has no cold or target-hardware result here.

## Next two specific code fixes

1. **Correct full-call timing first.** In `resense/detector.py:279–290`, `timing_ms.total` is captured before `health.update`; the health latency history receives that partial duration. Add an explicit health duration and clearly named complete processing duration, preserving or versioning the old stage field so historical reports remain interpretable. Keep node `detect_ms` as the complete-call observer and `node.latency_ms` as decode plus detect. Decide explicitly whether the health warning should consume a previous complete-call sample or remain a documented stage metric; changing its input can affect output when `latency_affects_decision=true`. Validate the timing contract and both latency-policy settings. This is a confirmed instrumentation defect with a smaller behavioral scope than queue-policy work.
2. **Bound startup preservation and diagnose remaining catchup gaps before changing sampling.** In `ros2_ws/src/resense_ros/resense_ros/detector_node.py:743–757`, the startup deadline expires only when `catchup is None`; persistent overload can retain the startup allowance indefinitely. Make that allowance obey an explicit finite deadline/backlog policy using the existing planner. First localize the candidate's late invalid positive frames against arrival, source, residence and queue age: the observed late gaps do not by themselves prove this startup condition caused them. Require a replay/history acceptance that reports every skipped source frame, first/sustained fresh STOP and raw/fresh target recall; reject a latency improvement purchased by losing positive evidence. Preserve bounded freshness and STOP handling. No unconditional thinning increase is supported.

The fresh-onset policy work remains a separate unaccepted detector candidate; this report neither promotes it nor assumes its earlier false-event reduction survives. Range/generalization still require new evidence. More score documentation cannot close those gaps.

## Evidence locations and review method

Read-only review of repositories and archived results; only this Markdown report and its JSON companion were written outside the repositories. No heavy work, tests, benchmarks, detector replay, internet search or external mutation was performed.

- Official rubric: `ReSense-health/docs/organizers/technical_specification_case05.txt`, §8.
- Prior review: `ReSense-cycle-data/checkpoint2_priority_astra.md` and `.json`.
- Gate: `ReSense-health/docs/evidence/cycle_2026-09-28/health_histogram/default/`.
- Runtime protocol, execution and audit: `ReSense-cycle-data/health_histogram/runtime/`.
- Exact-baseline CI: `ReSense-p3-sync/docs/evidence/cycle_2026-09-28/p3_sync/ci_25a218a/`.

The gate archive's README still says quiet runtime is pending. The later external execution/audit completes that evidence; its completion must be carried into any integrated acceptance summary.
