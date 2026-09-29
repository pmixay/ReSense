# Compare-count health histogram — gates, parity and reseal (29.09)

Only `resense.health._sector_counts` changes. It counts `values >= edge` per edge instead of a
per-value binary search, and gives the same counts, so the same `health.blocked_sectors`.

## Environment and data

This was a cloud container with 4 cores, running Python 3.11.15, NumPy 1.26.4, SciPy 1.13.1 and
scikit-learn 1.5.2. The native kernels were built by `scripts/build_native.sh`, byte-identically in
every checkout. The caches were built there from the organizers' published archives:

* The six recordings came from `Датасет.zip` (`cache_frames.py --every 1 --int16 --stamps`).
* Set O came from `cloud_with_fake_obj.zst`.
* The ride was built by `scripts/cache_extended_ride.py`: 221 splits and 11 271 frames. The archive
  size and SHA-256 matched the published values ([`ride_cache_intake_manifest.json`](ride_cache_intake_manifest.json)).

Frame counts were 201 / 345 / 252 / 268 / 545 / 877, set O 1 510 and the ride 11 271, as in
[`VM_GUIDE.md`](../../../VM_GUIDE.md) §2.4.

## v1 (`838f45c`, [`protocol.md`](protocol.md)): rejected at step 5

v1 compared float64 copies of the azimuths with the edges.

* **Unit tests:** passed.
* **Control gate** ([`control/`](control/)): the unmodified source `b34e83d` (the sealed `dcaa5db`
  detector) against the seal's validation gate
  [`thin_far_threshold/default_gate.json`](../thin_far_threshold/default_gate.json).
  * Exit 0; all 207 compared metrics unchanged.
  * This environment reproduces the sealed results.
  * The only informational change is `doubleT_obstacle` advisory frames, 91 → 89. It is the same
    in every run here, so it comes from the machine.
* **v1 candidate gate** ([`v1/candidate/`](v1/candidate/)): exit 0, 207 metrics unchanged.
* **Parity** against the control ([`v1/parity.json`](v1/parity.json)): 15 269 frames and set F's
  3 060 rows identical outside timing.
  * The stricter comparator committed with v2 gives the same result
    ([`v1/parity_recheck_strict_comparator.json`](v1/parity_recheck_strict_comparator.json)).
* **Step 5, speed** ([`v1/bench_summary.json`](v1/bench_summary.json)): **failed** in one
  configuration. At 890 k points on NumPy 2.4 with AVX-512 off, v1 took 4.34 ms against
  `np.histogram`'s 3.95 ms. The protocol rejects on any failed step, so v1 is not sealed.
* The control and v1 gates ran at the same time with 2 jobs each, not the registered 4. Their
  outputs do not depend on the job count.

An independent review of v1 found the code and its per-frame outputs clean: no STOP lost, delayed
or shortened. It asked for:

* the reseal claim to wait for the reseal;
* the speed miss to be reported as a failure;
* the history stress to be run;
* four gaps in the comparator to be closed.

v2 answers each of these ([`protocol_v2.md`](protocol_v2.md)).

## v2 (`3eeb106`, [`protocol_v2.md`](protocol_v2.md)): accepted and sealed

v2 compares a float32 cloud with float32 thresholds, giving the same answer as the float64
comparison for every float32 value, so the cloud is not converted. Every registered step passed:

1. **Unit:** 83 health tests passed on NumPy 2.4 and on NumPy 1.26.4 at `3eeb106`. After the
   review, two cases at and beyond float32 max were added: 85 pass on both. The case labelled
   "beyond float32 max" at `3eeb106` was, at 3.3e38, still inside the float32 range.
2. **Control:** the run above, reused.
3. **Candidate gate** ([`candidate/`](candidate/)): run alone with `--jobs 4`. Exit 0; all 207
   compared metrics unchanged; no worse, missing or better gated metric; no waiver.
   * Ride: 130 alarm frames, 32 events, 31 STOP episodes.
   * Five empty recordings: 40 alarm frames, 11 events.
   * Set O: 411 inside STOP frames, 6 outside false STOP frames.
   * `doubleT_obstacle`: person 61 / 61; rail object 126 / 126 from frame 75.
4. **Parity** against the control ([`candidate/parity.json`](candidate/parity.json), strict
   comparator):
   * All 15 269 frames identical outside timing.
   * `blocked_sectors` and `decision_level` identical on every frame.
   * 2 frames differ only in `level`, from one run's latency warning.
   * Set F: 30 sequences and 3 060 rows, identical except wall time.
   * Per-frame outputs: [`candidate/captures/`](candidate/captures/).
5. **History stress** ([`history/`](history/)): 33 histories in each of the control and v2, against
   the frozen [`history_identities.json`](history_identities.json).
   * Each run: 204 STOP frames and 55 events, the figures recorded for the sealed detector.
   * Zero new or removed STOP frames, zero new events and zero detection payload changes
     ([`history/acceptance.json`](history/acceptance.json)).
6. **Speed** ([`bench_summary.json`](bench_summary.json), all runs in [`bench_runs.json`](bench_runs.json);
   medians of 3 runs of 15 calls, in ms): v2 is the fastest in all 12 cells.

| NumPy, CPU features | points | `np.histogram` | binary search (sealed 28.09) | v1 | **v2** |
|---|---:|---:|---:|---:|---:|
| 1.26.4, AVX-512 off (the image's NumPy on the team laptop) | 127 k / 381 k / 890 k | 5.79 / 17.31 / 40.62 | 0.92 / 2.89 / 7.23 | 0.25 / 1.42 / 4.14 | **0.13 / 0.54 / 2.44** |
| 1.26.4, AVX-512 on | 127 k / 381 k / 890 k | 1.08 / 3.61 / 6.59 | 0.95 / 4.05 / 6.99 | 0.22 / 1.83 / 3.89 | **0.12 / 0.85 / 1.92** |
| 2.4.6, AVX-512 off | 127 k / 381 k / 890 k | 0.59 / 1.79 / 4.25 | 0.89 / 2.78 / 6.62 | 0.19 / 1.50 / 3.80 | **0.11 / 0.50 / 2.27** |
| 2.4.6, AVX-512 on | 127 k / 381 k / 890 k | 0.62 / 2.04 / 4.36 | 1.15 / 3.14 / 6.24 | 0.35 / 1.70 / 3.90 | **0.15 / 0.56 / 1.77** |

7. **Independent review of v2: no blocking issue.**
   * About 46 000 fuzz cases per NumPy build and 253 164 threshold checks, with 0 mismatches.
   * Its own diff of all 15 269 gate frames (810 STOP frames) and 12 468 history frames: no
     difference outside timing.
   * Figures in this README, the changelog and the seal document verified.
8. **Reseal**, after the review. [`../../detector_freeze_2026-09-27.json`](../../detector_freeze_2026-09-27.json)
   was created by `scripts/detector_freeze.py create` on [`candidate/gate.json`](candidate/gate.json):
   * 34 files, source SHA-256 `70faef901cb480b31f2f55ff1a28a2f4dc5c83c6bcda41371ee078eb79955a1c`;
   * this equals the candidate identity frozen before the history runs;
   * `verify` passes;
   * the previous seal (`dcaa5db`, `f20dd9e…`) is [`previous_seal.json`](previous_seal.json);
   * the manifest's `decisions.axis_union` text is new: the organizers measure the envelope from the
     rail heads (their answer of 29.09, `docs/organizers/answers.md` §9).

A real 360° frame keeps about 340 k points. Near that size, v2 saves about 2.4 ms per frame against
the sealed binary search, and about 17 ms against `np.histogram`, on the image's NumPy on a CPU
without AVX-512. The timings are indicative, not runtime acceptance.

Not claimed: any change of detections, range, false alarms or ROS end-to-end latency. The seal
manifest's standard `change_policy` text ("Blocker fixes only") predates the user-authorized
improvement cycle recorded in [`DETECTOR_FREEZE.md`](../../../DETECTOR_FREEZE.md).
