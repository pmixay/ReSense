# Revision 4: elapsed-time speed reacquisition for opt-in K1

Registered before the r4 edit and measurements. R3's
[target/travel evidence](travel-diagnostic.json) shows a genuine lockout: the
last accepted 13.24867 m/s sample is used indefinitely to penalize current
deceleration estimates. The confidence multiplier compares frame-to-frame
change to a sample hundreds of frames old. It rejects current 0.73–0.80
correlation observations as half-confidence, preventing reacquisition.

Candidate policy: only when K1's existing `walls_smoothing_distance > 0`, give
the speed estimator the configured nominal `tracking.frame_dt`. Scale its
`speed_max_step` confidence-penalty bound by elapsed time since the last
**accepted** speed (minimum one nominal period). Do not widen the short-step
EMA: a recovered distant value must not blend with an arbitrarily old speed.
Every accepted speed still needs the original current confidence threshold;
unknown/featureless frames remain unknown and never become synthetic zero.
Reset clears the elapsed-time state. K1 off uses the original estimator exactly.

This affects the shared speed estimate and hence accumulation while K1 is on,
not just wall smoothing. It must be measured as a new candidate, not attributed
to r3. No configuration defaults change. K2-only behavior remains r3.

Register failing tests for a measured deceleration after an unknown interval,
fresh outlier rejection, remaining-unknown low confidence, no stale EMA,
elapsed 5/10 Hz periods, reset and moving/off controls, plus Detector wiring.
The tests configure the planned estimator attribute explicitly so unchanged r3
fails on numerical behavior, rather than merely an absent constructor argument.

Then repeat the existing K1 targets with source-participation/plain controls,
empty platform and real crossing/rail obstacle. Preserve r3 results. The r3
gate/X3 work uses immutable checkouts and continues independently. Full original
acceptance is still required; reacquisition alone cannot accept 150 m, fix K2
edge geometry, or authorize enablement. A failed target/control is retained as
a failed candidate rather than compensated by another aggregate gain.
