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
