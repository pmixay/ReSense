# Rejected timestamp-only cap candidate

This implementation replaced the existing frame-based persistence chain with a timestamp-only
chain. The detector regression gate passed, and paired median/decision costs passed, but frame-level
review found 15 longer `clear_distance` estimates in `new_data_7`, up to 61.2 m longer than the
baseline. These occurred in bursty 20–30 ms intervals, with no detector alarm or warning change.

The per-frame lengthening was rejected even though aggregate monitoring costs passed. The final
candidate retains the shipped frame-based chain and only lets timestamp-aware evidence add a nearer
cap. `gate.json`, `monitoring_acceptance.json`, and `clearance_review.json` preserve this attempt.
Its per-frame inputs remain in `/cycle/work/timestamped-jitter-candidate` and are not committed.
