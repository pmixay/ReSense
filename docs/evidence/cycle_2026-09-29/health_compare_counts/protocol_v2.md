# Compare-count health histogram — protocol amendment v2 (registered before any v2 run, 29.09)

**Why v2.** v1 (`838f45c`) passed the control, candidate gate and parity steps of
[`protocol.md`](protocol.md). It failed step 5 in one configuration and is rejected
([`README.md`](README.md)): at 890 k points, NumPy 2.4 with AVX-512 off, v1 took 4.34 ms against
`np.histogram`'s 3.95 ms. The independent review of v1 also asked for:

* the history stress runs named by the acceptance rule;
* a stricter parity comparator;
* the reseal to be claimed only once it exists.

**Change.** Only `resense.health._sector_counts`. A float32 cloud whose outer edges lie within the
float32 range is compared with float32 thresholds, not converted to float64:

* for each edge, the smallest float32 at least that edge;
* for the right-closed last bin, the smallest float32 above the last edge.

For every float32 value this gives the same answer as the float64 comparison `np.histogram` makes,
so the counts are unchanged. Float64 clouds and other edge ranges keep the v1 float64 comparison.
The fallback conditions are unchanged.

**Acceptance, in order; any failure rejects v2.**

1. **Unit.** `tests/test_health_histogram.py` and `tests/test_health_gate_parity.py` pass on NumPy
   2.4 and 1.26.4. This includes new cases for edges float32 cannot represent, tiny ranges and
   edges beyond float32.
2. **Control.** The control run of `protocol.md` is reused: the same machine and caches, the
   unmodified `b34e83d`, exit 0, 207 metrics unchanged.
3. **Candidate gate.** The full default gate on the committed v2, run alone with `--jobs 4`, against
   `thin_far_threshold/default_gate.json`. Exit 0, no worse or missing gated metric, no waiver, and
   every gated metric the same.
4. **Per-frame parity** against the control, with the stricter
   [`compare_outputs.py`](compare_outputs.py) committed here:
   * both runs hold exactly the 15 expected, non-empty capture files;
   * `decision_level` always matches;
   * only `level` may differ where one run has a latency warning;
   * set F holds its 30 sequences with rows.
   Every frame must match outside timing, and `blocked_sectors` must match on every frame.
5. **History stress.** `scripts/history_stress.py --jobs 4` runs for the control (`--source-root`
   of the `b34e83d` worktree) and for v2, with the same runner, caches and original `roundT_doubleT`
   bag. They are compared with `scripts/compare_history_stress.py` against
   [`history_identities.json`](history_identities.json), whose source and config hashes were frozen
   before the runs. Every history must have zero new false STOP frames and zero unmatched false STOP
   events.
6. **Speed.** [`bench_sector_counts.py`](bench_sector_counts.py), three runs per configuration, on
   NumPy 1.26.4 and 2.4, each with AVX-512 on and off, at 127 k, 381 k and 890 k points. v2 must be no
   slower (median) than `np.histogram`, the 28.09 binary search and v1 in every one of the 12 cells.
7. **Only then** a new seal is created with `scripts/detector_freeze.py create` on the v2 gate. The
   previous seal is kept as [`previous_seal.json`](previous_seal.json).

Not claimed: any change of detections, range, false alarms or ROS end-to-end latency.
