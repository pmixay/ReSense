# T1: persistent boundary contradiction — rejected

**Do not merge T1.** [Recorded decision](decision.json). Its registered coverage gate failed: on ride segment `new_data_4`,
the median `clear_distance` estimate fell from **120 m to 60 m**. The required ratio was
at least 0.95; the measured ratio was **0.50**. The separate `health.monitored_range`
median fell from 120 m to 107 m. A second recording,
`squareT_platform_squareT_switch`, fell from 88.9 m to 83.0 m (ratio **0.9336**).
Both failures apply against M2 and the frozen baseline.
[All coverage results](full_comparison.json), [ride diagnosis](coverage_failure_diagnosis.json),
[independent final review](independent_rejection_review.json).

The source remains isolated on `work/trust-quality-20260926`, commit `0ea660f`.
The experiment was [registered](protocol.json) before source changes. The
[independent source review](source_review.json) permitted measurement, not acceptance.
[Source and unchanged native-library receipt](source_receipt.json),
[exact source and test diff](source.diff.txt.gz).

## What changed

The detector retained an observed disagreement between two boundary fits until a fresh
pair agreed or the scene reset. Losing one boundary, failing a fit, or reseeding mount
calibration could not clear that state. Existing thresholds and geometry fitting stayed
unchanged. The cap limited the downstream trusted range; it did not filter output STOPs.

The state was too persistent for the coverage budget. On `new_data_4`, 648 of 1,409
frames carried a cap. One uninterrupted run held 47 m for **403 frames / 40.21 seconds**.
Fitted geometry remained identical. This demonstrates the cost of this specific memory
rule; it does not establish the true safe range of that scene.

## Exact clear-run reproduction

| Original processed subset | Frames | M2 STOP frames | T1 STOP frames |
|---|---:|---:|---:|
| Failed standalone trial | 233 | 1 | 0 |
| Historical stock-DDS trial | 243 | 1 | 0 |
| Historical passing trial | 234 | 0 | 0 |

All 710 frame pairs retained identical raw input counts, fitted track geometry and mount
state. The median range estimate was unchanged in these short subsets. Newly uncertain
frames were 0.43, 0.41 and 0 percentage points, respectively.
[Comparison](target_comparison.json), [key frames](target_key_frames.json),
[full traces and raw-message hashes](target/report.json.gz).

This was broader than removing one erroneous history vote. In the failed sequence the
cap entered at raw frame 131 at 60 m, tightened to 51 m at 134 and 47 m at 139, and stayed
through frame 165. The target at 65.19 m in frame 152 became advisory despite a raw fitted
axis range of 120 m. At frame 159, the same 53.00 m target and 78 voxels had zero gauge
votes in its recent history, versus six in M2. Fresh agreement released the cap at 166.

The initial comparison script mistakenly required `n_corridor` equality. That field
counts candidates after the low-object stage, whose trusted range T1 intentionally
changes. Eight counts differed in each subset. Independent review confirmed the
mistake; the [original report](target_comparison_initial_observer_error.json) and
[original script](compare_target_initial_observer_error.py.txt) are retained. The correction
changed only that extra observer condition and added mount equality; no registered gate
or candidate source changed.

## Other validation

- **112 relevant unit/regression tests passed**, including 12 new trust-state tests.
  [Log](units.txt).
- **All 72 placement cases were retained exactly:** 544 matched frames across 45 cases,
  no lost matched frame and unchanged paired-control alarms. [Comparison](novel_comparison.json),
  [complete result](novel_result.json.gz), [immutable plan](novel_plan.json.gz).
- **Full detection gate passed:** 199 comparison rows, 146 gated, no missing or worse
  gated rows against either reference. Ride false-alarm events fell from 45 to 43,
  and STOP episodes from 38 to 32. All positive, Set F, outside-object and five-empty
  recording gates stayed unchanged; the five empties retain 13 events / 16 episodes.
  [Complete comparison](full_comparison.json), [gate result](gate_result.json),
  [gate log](gate.txt). Every raw gate stream is under `gate/`.
- Both range-cost failures above reject T1 despite the detection gate passing. No
  recording exceeded the five-percentage-point uncertainty budget.

The already-running full gate was completed after rejection. Further rate, mount,
startup-offset, raw Set O and ROS timing runs were not started for this rejected source.
The failed combined-image clear trial remains failed; this diagnostic cannot replace it.

Experiment scripts are archived byte-for-byte as `.py.txt`; copy them to their original
`.py` filenames to replay the documented commands.

No detection-recall improvement, accepted freeze, release, or 75/100 score is claimed.
[Artifact hashes](manifest.json) cover this packet.
