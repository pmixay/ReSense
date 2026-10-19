# H1 follow-up: absolute rail anchor and far collision cores

P3 development candidate **D**, detector source **`8fce584106809cd04d6932ee129d8bd7d128b4da`**,
branch `det/h1-positive-core`, relative to C / `f47a090`.
**H1 overall remains OPEN.** Independent P4 review and P1 selection/reseal are pending.
The [previous C evidence](../h1_core_2026-10-19/README.md) retains its original scope and verdict.

**Full gate, X3 and critical preservation checks pass.** The final full pytest
has2179 passes +17 subtests and one independently reproduced base failure;
it is not an all-green suite. [Machine-readable receipt](author-acceptance.json).

## 1. Diagnosis and implementation

The C predicate trace identifies two actual failures, with plain/traced equality
on all **364 serialized frame results** (18 standing x14, two approaches x56):

* At109 m left, all33/36 candidate returns are removed by the additional0.30 m
  erosion plus the range-growing margin and the boundary interval. The observed
  body is present; the final robust mask is empty.
* At137 m both sides, sparse local wall bins fail the four-return threshold.
* A constant model-axis displacement disappears from the local-minus-near wall
  differences. C's wall consistency check therefore does not measure that error.

[Registered protocol](PROTOCOL.md), [D geometry](CANDIDATE_D.md),
[additional validation registration](STRESS_D.md).

`FrameRays.collision_axis_anchor` now re-measures current raw near-rail ridges,
before smoothing. At least two paired slabs and ordinary ridge prominence are
required. Their midpoint residual range against the final model, expanded by one
configured lateral bin, anchors every wall-continuation hypothesis absolutely.
The original fitted axis remains in the hull. Missing support or a held floor
supplies no exemption. This uses the ordinary rail finder and floor reference;
it is **an observed consistency hull, not a calibrated true-axis uncertainty bound**.

The extra body erosion is0.05 m after that check, retaining the ordinary growing
gauge margin. Wall bins require two returns spanning at least0.15 m vertically,
still with at least four near and two local stations in every side/height profile.
Repeated copies of one hit cannot supply that vertical span. Confirmation and
the fresh uninterrupted core-run from C continue to apply.

## 2. Physical results

These are deterministic ray/AABB scenes, not recorded target detections. The
full detector estimates its floor, rails, orientation and axis from the scene.
The same32 standing inputs are compared by saved detection positions, checking
all448 candidate rows against the448 retained C rows:

| Check | C | D |
|---|---:|---:|
| Standing matched rows |230|**293**, zero previous matches lost|
| Entirely missed standing cases |9|**0** in the fixed14-scan window|
| Outside cases, with and without actual rail returns, errors0/+-0.3/+-0.6 m |original no-rail larger-error sweep had5 false cores/STOP|**0/160** false cores/STOP|

**Three left137 m opaque cases have only1/14 matched scans.** Eliminating an
entirely missed case does not establish stable stationary detection at137 m.

Opaque4.12 m body approaching at22 m/s /10 Hz,155->34 m:

| Body lateral | C first STOP | D first STOP | D uninterrupted STOP through34 m |
|---|---:|---:|---:|
| -0.68 m |71.4 m|**126.4 m**|**126.4 m**,43/56 total matched|
| +0.68 m |60.4 m|**130.8 m**|**130.8 m**,45/56 total matched|

Both preserve every former matched scan. Pooled held90 is135.2/141.8 m; those
larger values include pre-onset misses and **are not continuous detection range**.

Ten additional physical scenes vary scan phase, asymmetric wall widths and rail
centres+-0.25 m. Continuous detection starts at**115.4..135.2 m**, with no missed
scan at or below100 m in those scenes. Phase0 has first STOP146.2 m followed by
gaps until115.4 m: the early first STOP is not the stable range. All120 sampled
interval checks contain the independently specified true axis after mount rotation.
[Full stress rows](stress-d.json), [inspected raw examples](raw-examples-d.png).

### What was independently checked

* Grouped raw wall points with a separate Python/NumPy implementation on20
  distance/offset/yaw cases: interval endpoints agree within1e-12 m and contain
  the known physical axis. Raw labelled rail-head hits independently locate the
  pair centre within0.04 m of its specified position in each sampled slab.
* Every outside scene checks the physical body's inner face and all returned
  object points against the true1.05 m edge. A known in-gauge body makes a core
  and a confirmed STOP using the same tools.
* Actual return-branch tracing covers all five former larger-error failures,
  both without rails and with actual rails, plus a positive control. Without
  rails the executed branch has no interval; with rails all five have zero
  robust points after the absolute-axis hypotheses. Every cluster field is equal
  between plain and traced calls. [Branch snapshots](outside-trace-d.json).
* A manufactured coherent wall displacement changes the interval as expected.
* The original no-rail case45 XYZ hash,84 object returns,80 gauge voxels and20
  rings are retained. **That raw no-rail scene now abstains from the absolute
  collision proof.** With physical rails it is again STOP-eligible. Its supplied
  oracle coordinate model alone is no longer accepted as fresh rail evidence.

Complete physical outputs and both predicate traces are in `raw-evidence.tar.gz`.

## 3. Preservation on recordings and injected critical objects

* **Full gate PASS**, no overrides/waivers/missing metrics. All208 non-timing
  metrics and all**15,269 ordinary +3,060 Set F rows** equal C outside timing.
  Every former detection, warning and track field is retained. No added STOP on
  empty bags or the complete11,271-frame ride.
* **Falcon:** all4443 non-timing node rows equal C, preserving1372 STOP rows.
* **X3 PASS:**40 cases /29,765 raw rows, every non-timing node row equal C.
  All worker completions, identities, raw hashes and re-derived summaries were
  checked. [Full X3 row audit](audit-d2-x3.json).
* **A-axis:**105->109/177 matched visible rows, none lost; four additions at
  k303/304/305/329, no added unmatched decision relative to C. The first remains
  218.38 m and pooled held90 is only**11.02 m**. These injected placements follow
  the baseline detector axis and cannot validate real-world axis accuracy.
* **C-person:**55 matched rows /82.77 m first STOP retained.
  **R3 E6:**34 /86.25 m first /61.28 m held retained.
* All**948** critical-probe hit labels are recomputed from captured full-precision
  detection positions. A-axis additionally has340 raw FrameResult fingerprints
  equal between plain and actual assignment-traced runs outside timing.
  [Raw critical trace](trace-ranges-d.json), [probe audit](audit-d-probes.json).
* The raw-row comparator detects a planted deleted positive STOP/payload, added
  empty STOP, and changed axis field. [Gate audit](audit-d-gate.json).

## 4. Tests, retained failures and reproduction

128 geometric/core tests passed; after isolating the historical free-top test,
the combined follow-up set has129 passing tests. The first broader affected run
had255 passes and one timing failure (p95=281.5 ms during concurrent long runs).
A later isolated timing run passes at p95=16.7 ms. No speedup is inferred.

The first full suite has2178 passes +17 subtests and two failures, eight
external-data deselections, no skips. One failure expects the retired free-top
experiment's extra one-frame delay, while D correctly accepts that body by its
observed core. The test now explicitly disables the new core to isolate the old
free-top behavior; its assertions pass without changing its expected timings.
The other is the proxy-hook error-message assertion, independently reproduced
on the exact C reference checkout. The final full-suite recheck ran after X3:
**2179 passed +17 subtests, one inherited proxy-hook assertion failure, eight
external-data deselections, zero skips**. All timing tests pass in that full run.
The earlier failures are retained separately; the full suite remains non-green.

The first X3 launch refused all workers before processing data because the
candidate detector was not committed. That error report and all worker logs are
retained. The user then authorized a local candidate commit; the fresh `d2` run
uses that committed source. Earlier gate/probe receipts contain a dirty diff;
their exact source bytes are checked against the committed detector, rather than
presented as originally committed runs.
The protocol files were created before their respective implementation/validation
steps and committed with the source after that authorization; the Git commit is
not claimed to predate the initial physical measurements.

Runtime: Python3.12.3, NumPy1.26.4, existing native binary. Set `RESENSE_REPO`,
`PYTHONPATH`, `OPENBLAS_CORETYPE=Haswell`, `OPENBLAS_NUM_THREADS=1`,
`OMP_NUM_THREADS=1`, and the library path in the execution receipts. Drivers reuse
the existing B4 decoded caches and registered R3 placement/ICP caches. Use a clean
checkout and fresh output/revision names; the portable source/raw archives and
their member manifests are produced by `package_results.py`, reopened and hashed
member by member. The previous C archives supply the comparison rows.

## 5. Remaining H1 work

* Establish a measured near/far axis-error budget on real recordings. The rail
  finder can share a wrong-pair/route or floor-reference error with the model;
  a plausible wrong pair is **not validated by these controls**.
* Missing fresh rails give no new tall-column exemption. The original no-rail
  fixture and the weak left137 m stationary results remain explicit limits.
* Improve real-background sustained detection; A-axis still has substantial gaps.
* Independent P4 review, then P1 selection/reseal.

The physical100 m results establish neither a calibrated real-world100 m range
nor braking sufficiency. **Overall H1 / inherited High remains OPEN.**
