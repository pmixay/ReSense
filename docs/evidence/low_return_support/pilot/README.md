# Low-return support pilot

This is a development screen, not full acceptance. The paired runs used clean source `75ef4e2`,
the same native B5 library, default config, and v2 cache. The full identities and frame records are
in [`baseline_clean75.json`](baseline_clean75.json) and [`candidate_clean75.json`](candidate_clean75.json).

On the edge-position compact 30 cm target at 50 m, the candidate changes matched STOP from **0/16
to 12/16** frames in both float32 and compact16 inputs, starting on frame 4. The other three positive
controls remain at 12/16 in both versions. Clear, outside-left, outside-right, and below-rail controls
remain at 0 STOP frames. The candidate does not lower the existing point-count, DBSCAN, width, or
height thresholds; it retries rejected low-stage points grouped by distinct acquisition rays.

These are synthetic target results. The candidate has not yet passed the full real-recording gate;
that preregistered run is defined in [`../full_gate/protocol.json`](../full_gate/protocol.json).
