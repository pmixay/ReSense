# Timestamp-aware sparse clearance evidence

This change adds a time-aware sparse-evidence cap to `clear_distance`, while retaining the shipped
frame-based cap. The reported estimate is the nearer of the two, so timestamp variation cannot
lengthen the prior estimate. It does not change detections or decisions.

Validation passed on 2026-09-29:

- All 146 gated regression metrics match the baseline on the six organizer recordings, set O, the
  ride and set F.
- The frame-paired review covered 15,269 frames. No range estimate lengthened, no new negative
  alarm frames appeared, and every negative detection payload was identical.
- Set O GO overclaims stayed at 16. The empty-recording median range was at least 99.3% of baseline;
  no newly uncertain decisions appeared.
- `tests/test_clear_cap_persist.py`: 23 passed with native kernels enabled and 23 passed with
  `RESENSE_NATIVE=0`.

The 5 Hz full-detector fixture shows an earlier clearance cap for a sparse 0.3 m object. That result
is synthetic development evidence. No object detection improved on the frozen recordings, so the
current independent project score remains **65/100**.

The first two timestamp-only attempts were rejected and retained in [`failed_actual_interval_scaling`](failed_actual_interval_scaling/)
and [`failed_timed_only`](failed_timed_only/). Their paired frame results exposed regressions that
the aggregate gate alone missed.
