# H1 completion: real-sequence reference and remaining misses

P3 development; starting HEAD `19ffbe4`, detector source `8fce584`. Previous
evidence and its OPEN verdict remain intact. No G3, judging or release run.

## Reference, before detector changes

Use the existing raw decoded A (roundT_squareT_pressureGate_squareT, frames0..339)
and C (roundT_pressureGate_roundT, frames0..267) sequences. Estimate full SE(3)
current-to-previous poses from raw static side/bed points, without a fitted track,
detector candidates or injected objects. Existing forward-only odometry is a
comparison/initialization source, not a six-degree reference.

Independently extract near rail-pair observations from raw height ridges, with
known physical spacing1.59 m, positive prominence, multiple near slabs and an
unambiguous pair near the vehicle. Do not use the evaluated detector's axis,
floor or wall fit to select the reference. Preserve the returned point support
and all competing pairs, not just a fitted centre.

Map later near-rail observations into earlier frames using the measured poses;
this observes a far station again from close range. Compare an alternate
registration resolution/range and direct skipped-frame registration against
composed poses. Report support, method disagreement, closure and raw examples.
This is an independently checked reference estimate, not surveyed ground truth.
Abstain from quantitative truth claims where validation does not support them.

## Controls

* Same raw cloud registered to itself: identity; a manufactured nonzero rigid
  transform must be recovered (translation within0.02 m, yaw within0.01 degree).
* Independent ray/AABB physical rails: the extracted near axis must agree with
  specified geometry, including offsets, yaw and asymmetric walls. Flat bed,
  one rail and wrong spacing must not supply an accepted pair.
* Positive rail and nonzero displacement controls accompany every absence/no-
  difference result. Inspect raw point/profile plots and check physical speeds.
* For real rows, preserve actual support snapshots and exclude reference points
  that cannot be resolved into an unambiguous continuation from the near track.

## Repair and acceptance

Trace remaining D standing137m cold starts and all68 A-axis visible unmatched
rows; labels must come from the executed branches and complete snapshots. Trace
and equal-input plain outputs must agree outside timing before attribution.
Repair only demonstrated errors; do not relax confirmation to hide geometric
uncertainty or use the evaluated axis as the placement truth.

A retained candidate must preserve previous critical matched sets and reject
outside/ambiguous-reference controls; run the existing full gate, X3 and physical
stress on frozen source bytes. Report continuous detection separately from first
or pooled coverage. Independent P4 and P1 selection remain separate steps.
If a required reference/scene cannot be established, identify the exact evidence
gap and keep that part of H1 OPEN instead of claiming universal closure.
