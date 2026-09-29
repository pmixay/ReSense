# Timestamp-aware sparse evidence: acceptance protocol

**Status: validated monitoring-only change.** This changes only the persistent sparse-evidence contribution to
`clear_distance`; it must not change detections, STOP/GO/CAUTION, or `monitored_range`. A smaller
`clear_distance` is a monitoring estimate improvement, not an object-detection gain.

## Defect and candidate

`PersistentEvidence` keeps the shipped frame-based chain and adds a second chain that matches a
sparse blob by apparent speed using actual sensor stamp intervals. The timestamp-aware chain resets
on invalid stamps or intervals longer than 0.3 s. Four observations must span at least three nominal
periods. The result is the nearer of the two caps, so timestamp jitter or a lost timestamp cannot
increase `clear_distance` relative to the shipped behavior.

Two timestamp-only variants were rejected. The first passed the detector regression gate but failed
paired set O acceptance: labelled in-envelope GO overclaims rose from 16 to 36. A second variant
snapped near-nominal intervals to one scan but still lengthened `clear_distance` on 15 bursty ride
frames by up to 61.2 m. Both are retained under `failed_actual_interval_scaling/` and
`failed_timed_only/`. The additive design below preserves the prior cap on every frame.

## Development fixture already observed

The fixed-seed full-detector fixture in `tests/test_clear_cap_persist.py` uses a 0.3 m box with
physical intrusion into the synthetic rail envelope, moving at 16 m/s in an 8-frame, 5 Hz approach
from 100 m. With the old cap disabled, `clear_distance` stays near the 200 m visibility estimate
even as the box approaches 77.6 m. With the candidate, it caps at the box on the fourth supported
observation. Both runs emit identical detections, decisions, health levels and `monitored_range`.
This is a constructed development case, not a real-object or held-out result.

## Acceptance gates

1. Focused fixtures preserve the nominal 10 Hz chain and cover 5 Hz, one dropped frame, irregular
   intervals, fast replay, varying apparent speed, stationary clutter and overlong/invalid gaps.
2. The full-detector development approach must reduce a final `clear_distance` overclaim while
   preserving every detection and decision. Module-only cap outputs do not count.
3. Run the complete strict regression gate against the exact pre-candidate gate at
   `docs/evidence/cycle_2026-09-28/complete_timing/default/gate.json`. Require no worse gated
   detection metric, including all six short recordings, set O, ride and Set F.
4. Compare per-frame `clear_distance` on every empty recording and ride, and count overclaims on
   set O. Require no candidate frame to lengthen `clear_distance` over the baseline, no increase in
   positive overclaim frames under the existing label contract, no
   more than 1% loss in each empty recording's median clear distance, and no more than a 0.1
   percentage-point increase in empty frames capped below 60 m. Inspect every changed cap frame.
5. Verify default config, native and NumPy paths, processing-history tests and the ROS output
   contract. Report timing separately; do not credit a score increase for synthetic-only behavior.
6. Only after the source and configuration are fixed may a new synthetic reserve be generated.
   New seeds on the same round-tunnel simulator remain synthetic evidence, not a real-route
   holdout.

Any failed gate rejects default promotion. Rejected results remain evidence and do not justify
relaxing the observation count, envelope, isolation, gap bound or speed consistency after review.

## Final additive candidate result

The additive candidate passed all checks on 2026-09-29:

- The strict regression gate passed with all 146 gated detection metrics equal to the baseline.
- Paired monitoring acceptance covered all 15,269 frames. No `clear_distance` frame lengthened;
  the five empty recordings and ride had no new uncertain decisions or negative alarm changes.
- Set O retained 16 GO overclaims, equal to the baseline. The zero-overclaim diagnostic remains
  false because those pre-existing overclaims remain; no increase is claimed.
- Eleven frames received shorter range estimates: three on `roundT_doubleT`, eight on the ride.
  The worst empty-recording median fraction was 0.993 on `roundT_doubleT` (0.65% lower).
- The 0.3 m box at 5 Hz full-detector synthetic fixture still gains a cap on its fourth supported
  observation, while detections and decisions stay identical. This is synthetic development
  evidence, not a real-route or held-out detection result.

See [`gate.json`](gate.json), [`monitoring_acceptance.json`](monitoring_acceptance.json), and
[`clearance_review.json`](clearance_review.json) for the recorded comparisons. The independent
project score remains 65/100: this change earns no detector score credit.
