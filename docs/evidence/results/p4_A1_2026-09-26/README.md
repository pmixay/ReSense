# A1 result: rejected

The directional association change reduced some false-alarm exposure, but failed the registered
requirement that every novel-placement case avoid regression. **Do not merge this candidate.**
The full gate and aggregate improvements do not override that failure. No threshold was retuned.

| Measure | Sealed baseline | A1 |
| --- | ---: | ---: |
| Ride false events | 45 | 44 |
| Ride alarm frames | 183 | 180 |
| Ride STOP episodes | 38 | 38 |
| Five empty-recording events | 13 | 13 |
| Five empty-recording alarm frames | 58 | 56 |
| Novel target matches / visible frames | 544 / 2,458 | 556 / 2,458 |
| Novel cases with a match | 45 / 72 | 45 / 72 |
| Paired-control target matches | 0 | 0 |

## Rejection

`roundT_squareT_pressureGate_squareT / big_above / lateral -0.65 m` lost a target-matched frame:
2 → 1. Its farthest matched sensor X decreased from 18.407 m to 16.598 m. Both target-matched and
injection-only counts regressed. The [per-case comparison](novel_comparison.json) retains all
72 cases and explicitly fails acceptance. Aggregate gains cannot cancel this loss.

These placements use seen backgrounds and organizer source shapes. They are a sensitivity
experiment, not independent real-obstacle recall or surveyed envelope truth. Their limitations
are unchanged from the original study. Rejecting A1 follows the registered engineering rule;
it does not turn these synthetic cases into independent real ground truth.

## Other checks

- Full regression gate: PASS, one gated row improved, no worse or missing gated rows, no waivers.
  All existing positive/background gate metrics were preserved. Three ride STOP frames and two
  empty-platform STOP frames were removed; no frame newly became STOP. The exact changed frames
  are in [changed_alarm_frames.json](changed_alarm_frames.json).
- All 72 cases retained identical frame/source identities, point counts, windows, configuration
  and input hashes. The code receipt changed only `resense/tracking.py` among detector/evaluator
  source hashes. The original placement plan remains untouched.
- Monitoring cost: PASS. Extra CAUTION exposure was 0.290 percentage points on `doubleT_platform`,
  0.0177 points on the ride, and zero on the other empty recordings. Median estimated clear range
  was unchanged for each recording and the ride.
- Known-target monitoring overclaims remained 54 / 505 object-frames, including 46 with GO.
  A1 does not resolve the separate uncertainty problem.
- Tests: 158 passed across `test_directional_association.py`, `test_modules.py`,
  `test_stop_keep.py`, `test_reseed_safety.py`, `test_near_escalation.py` and `test_algorithm.py`.
  Ruff passed for the changed source and new tests. These tests cannot override the failed
  72-case acceptance check.

## Audit trail

1. `a62b5b8`: exact A1 protocol committed before implementation.
2. `d95eacf`: before evaluation, specified how to repeat identical planned data with a new code
   receipt while keeping the evaluator's hash checks enabled.
3. `6d5bc56`: one candidate implementation and focused tests.
4. `c5e0db4`: immutable A1 study receipt committed before the 72-case repetition.

The original total 3D bound is preserved. An additional capsule bound confines the existing ego
approach allowance to X. Normal and thin-continuation paths share the helper; Euclidean matching
rank, all configuration values, confirmation and lifetime rules remain unchanged. The isolated
branch is retained for audit, not integrated into the accepted detector.

Artifacts:

- [Protocol](../../../archive/P4_ASSOCIATION_A1_PROTOCOL.md) and
  [identical-input code receipt](../p4_A1_novel_plan_2026-09-26.json).
- [Full gate](gate.json), [gate log](gate.log), [Set F details](setF_straight.json).
- `gate_frames/`: all 15 per-frame captures, compressed without changing their JSONL contents.
- [Novel results](novel.json), [per-case comparison](novel_comparison.json),
  [aligned monitoring comparison](monitoring.json).
- [Provenance and artifact hashes](provenance.json).

The broad objective of at most 30 ride events remains open. Release and detector freeze remain
on hold; there is no accepted detector change from A1.
