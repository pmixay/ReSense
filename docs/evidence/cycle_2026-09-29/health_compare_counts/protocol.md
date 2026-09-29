# Compare-count health histogram — protocol (registered before any run, 29.09)

**Defect.** `resense.health._sector_counts` (28.09) replaced `np.histogram` with a per-value binary
search. It is exact, but its speed depends on NumPy: with NumPy 1.26 on a CPU without AVX-512 (the
team laptop, the image's pinned stack) it is faster than `np.histogram`'s sorting path, while on
NumPy 2.x it is about twice as slow as `np.histogram` (review of 29.09: 890 k scan-ordered azimuths,
NumPy 2.4: `np.histogram` 4.3 ms, binary search 9.0 ms).

**Change.** Only the body of `_sector_counts`: count `values >= edge` for each edge (float64
comparisons, as `np.histogram` compares float32 data with float64 edges) and difference the counts;
the last bin includes its right edge. The fallback conditions to `np.histogram` are unchanged. No
configuration, detection, tracking or timing definition changes.

**Acceptance, in order; any failure rejects the change.**

1. Unit: the existing exactness tests (`tests/test_health_histogram.py`,
   `tests/test_health_gate_parity.py`) and a new randomised test against `np.histogram` (both value
   and edge precisions, every edge, the next float outside the range, NaN, ±inf, −0.0) pass on
   NumPy 2.4 and NumPy 1.26.4.
2. Control: the full default gate (`scripts/regression_gate.py`, six recordings, set O, the ride in
   8 pieces, set F straight; no `--set`, no `--allow`) on the unmodified source, in the same
   environment as the candidate (Python 3.11, NumPy 1.26.4, SciPy 1.13.1, scikit-learn 1.5.2,
   native kernels, 4 jobs), against the current seal's validation gate
   (`cycle_2026-09-29/thin_far_threshold/default_gate.json`, measured at `dcaa5db`). Expected: exit 0
   with every gated metric the same. If it is not reproduced, the differences are reported and the
   control run itself becomes the candidate's baseline (same machine, unmodified detector).
3. Candidate: the same gate on the committed change against the baseline of step 2: exit 0, no
   worse or missing gated metric, no waiver, and every gated metric the same (a histogram of the
   same counts must not move any metric).
4. Per-frame parity: every frame of the six recordings, set O and the ride, and set F straight,
   identical between control and candidate outside `timing_ms` and the latency-derived health
   fields (`latency_p95_ms`, `latency p95 …` messages, and a level change explained by them).
   `health.blocked_sectors` must be identical on every frame.
5. Speed: on scan-ordered clouds of 127 k–890 k points, the change is no slower than both
   `np.histogram` and the 28.09 binary search on NumPy 1.26.4 with AVX-512 disabled and on NumPy
   2.4 (medians of repeated calls; indicative, not runtime acceptance).
6. Only then: a new seal with `scripts/detector_freeze.py create` on the candidate gate; the
   previous seal is kept next to this protocol.

Not claimed: any change of detections, range or false alarms; ROS end-to-end latency on the
target machine.
