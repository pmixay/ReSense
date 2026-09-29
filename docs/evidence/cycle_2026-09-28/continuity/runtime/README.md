# Quiet positive runtime diagnosis

Read-only diagnosis of the preserved original-bag quiet positive captures. Frozen production
files were not changed. Both runs failed the 100 ms decode-plus-detect target and produced
no fresh valid frame result. The baseline failure remains relevant when assessing the candidate.

[diagnosis.json](diagnosis.json) contains exact aggregates and hashes of both status captures
and node logs. Percentiles interpolate linearly over the recorded per-frame values.

## The missing processing time

| Metric, mean / p95 ms | Baseline, 166 frames | Candidate, 198 frames |
|---|---:|---:|
| `node.decode_ms`, including axis transform | 32.00 / 39.63 | 26.19 / 32.50 |
| `node.detect_ms`, complete `Detector.process` call | 87.44 / 103.69 | 77.21 / 93.31 |
| `node.latency_ms`, decode plus detector, before publication | 119.44 / 137.16 | 103.41 / 125.02 |
| Post-timer tail, mean | 45.62 | 40.83 |

`timing_ms.total` averages only 41.83 ms baseline and 36.39 ms candidate because
`resense/detector.py:267` takes its final timestamp **before** `HealthMonitor.update`.
The health call and result construction are therefore excluded. The health latency monitor
also receives that partial value. The full detector wall time is `node.detect_ms`.
Publication and transport costs are additional to `node.latency_ms`.

The dominant actionable health operation is `resense/health.py:118`:
`np.histogram(az, bins=edges)` over approximately 340,000 kept points. NumPy 1.26.4 uses its
cumulative histogram path for an explicit edge array, sorting input chunks before counting.
The existing native visibility kernel is already active; blocked-sector counting has no
native kernel.

## Isolated check

After the quiet ROS runs completed, [probe.py.txt](probe.py.txt) read one original positive
PointCloud2 message in the frozen candidate image, used two warmup iterations and 12 measured
iterations, and timed the existing functions. [probe.json](probe.json) pins the raw message
and records all samples; `diagnosis.json` pins the image, script, and report.

| Existing operation | Mean ms | p95 ms |
|---|---:|---:|
| Health update | 26.56 | 27.68 |
| Histogram within health | 19.15 | 19.62 |
| Native visibility within health | 1.02 | 1.19 |
| PointCloud2 array decode | 17.29 | 18.40 |
| Configured axis matrix multiply | 1.33 | 1.37 |

On the same saved azimuth array, explicit-edge `searchsorted` plus integer `bincount`
took 2.68 ms mean versus 18.72 ms for `np.histogram`, with identical integer counts.
This is a repeated, warm fixed-cloud microprobe. It does not establish a ROS runtime gain
or show that the 100 ms target will pass.

An initial endpoint adjustment failed a boundary case: comparing a float32 array with a
float64 scalar endpoint rounded the endpoint, moving a count between bins for 0.3-degree
sectors. [prototype_failure.json](prototype_failure.json) preserves the mismatch.
Using an array endpoint preserves comparison precision. The corrected isolated helper
matches the real cloud plus six adversarial sets: float32/float64, sector sizes 10/7/0.3
degrees, exact edges, immediate floating neighbors, signed zero, NaN, and infinities.
No helper was installed into production.

## Why freshness never recovered

Every frame result is explicitly `source_stale`: 198 candidate and 166 baseline. Candidate
publisher age grows from 0.587 to 3.476 seconds; baseline grows from 0.605 to 6.607 seconds.
Both stay in catchup for the entire capture and skip zero frames through catchup.

`detector_node.py:743–755` preserves the first backlog with a 20-second allowance and
reduces the catchup step to the observed sensor period, approximately 0.1 seconds. The
startup allowance ends when the backlog drains, or its initial window expires **while no
catchup is active**. Once catchup starts and processing stays slower than 10 Hz, that exit
does not occur. The normal 0.3-second thinning policy never starts. This explains the
growing residence time without a clock fault. Raising the 0.5-second freshness limit would
not correct the growing backlog.

## Minimal next phase

1. Replace only histogram counting after the existing azimuth calculation, preserving the
   exact edge array, integer counts, last-bin inclusion, and dtype comparison semantics.
   Test full health outputs and boundary cases, then paired real captures and quiet ROS
   timing. Add explicit health/full-call timing so the partial `total` cannot conceal cost.
2. Reassess freshness after that optimization. If startup still cannot recover, bound the
   startup preservation interval or backlog explicitly, then invoke the existing thinning
   policy. This changes processing history and needs separate temporal detection, startup,
   and frame-drop acceptance; retain the current freshness deadline and STOP hold behavior.
3. Only if decode remains limiting, evaluate a guarded fused native range/decode path for
   the known float32 layout. The current path already has raw CDR parsing, a zero-copy
   structured view, and vectorized range masks; it still makes several strided passes and
   field gathers. Preserve field order, float32 arithmetic order, range boundaries,
   intensity/ring values, and raw/near counts with fallback for unsupported layouts.
   The measured 1.33 ms axis transform has lower priority. Combining configured and
   calibration rotations would require new rounding-parity evidence.

## Reproduce the isolated probe

Run on an idle machine; this script reads one message and writes only its JSON result.

```bash
docker run --rm --entrypoint python3 \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 \
  -v "$PWD/docs/evidence/cycle_2026-09-28/continuity/runtime/probe.py.txt:/probe.py:ro" \
  -v /home/likikikpa/ReSense-p4-data/for_hackathon/doubleT_obstacle:/bag:ro \
  resense:cycle-candidate /probe.py > /tmp/resense_runtime_probe.json
```
