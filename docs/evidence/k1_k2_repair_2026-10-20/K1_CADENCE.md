# K1 revision 2: standstill averaging must count elapsed periods

Registered 2026-10-20 before running the new regression or measuring r2.

Inspection of `estimate_track` found that the stationary floor of the EMA/rate
multiplier is `walls_smoothing_min_k` **per processed frame**, even with
`walls_smoothing_per_period` / `rates_per_period` enabled. Consequently two
10 Hz frames and one 5 Hz frame do not apply the same smoothing over 0.2 s of
standstill. The estimator converges twice as slowly in physical time at 5 Hz.
This is a separate author finding, not an explanation of the 150 m misses.

Candidate r2 scales each minimum by its respective elapsed-period multiplier.
Travel still determines the distance-based exponent above that floor. Unknown
travel, warm-up, disabled K1 and disabled per-period switches retain their old
semantics. No default/threshold change.

Acceptance for this repair: with constant independent rail/wall observations,
two nominal-period standstill updates equal one two-period update in axis shape
and age (EMA-only and active rate-limit cases). Include moving/unknown-travel,
off and per-frame controls. The test must fail on r1 before the production edit.
Run the K1/K2 affected tests afterwards. Real standing-person 100/150 m,
sudden-appearance and platform controls remain required for K1 acceptance;
this cadence identity alone does not satisfy them or authorize enablement.
