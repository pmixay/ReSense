# Exact-count health histogram candidate

Prepared in the isolated `improvement/health-histogram-20260928` branch, based on
`1c2c5397006ecdc0e81da84dacff88aba6c2ecd3`. The [protocol](protocol.json) was committed as
`2539c5b3d7faa158a659a537f42e8efb46f849d3` before implementation and evaluation.

## Combined-source evaluation

The isolated worktree now includes experimental commit
`25a218a0a8b4e10089dfcf73b8d557d4a963290e`, merged at `83bc5d8`.
Its production difference remains only `resense/health.py`; the health implementation
is byte-identical to `7885c6d`. The [combined protocol](combined_protocol.json) registers
the new source/config identities and full-gate/per-frame parity criteria before evaluation.
The package-local native module was rebuilt and matches the accepted `b5a5c2dc...` binary.
Combined-source full-gate and runtime acceptance are pending. The original protocol,
validation and microprobe below remain historical evidence for the earlier score source.

Only `resense/health.py` changes production behavior: the blocked-sector histogram uses
binary search and integer counting instead of NumPy's sorting path. Azimuth calculation,
edge generation, severity rules, configurations, detection/tracking, and timing definitions
are unchanged. The intended result is exact health-output equality for identical inputs,
state, and supplied latency.

## Bounds and parity

The fast path accepts plain one-dimensional native float32/float64 arrays with 2–257 finite,
strictly increasing floating edges. Temporary arrays hold at most 65,536 values; the
accumulator has at most 256 bins. Other shapes, dtypes, edge layouts, and array subclasses
use the original `np.histogram` call, preserving its dispatch and error behavior.

Each interior bin includes its left edge and excludes its right edge; the final edge is
included. Endpoint comparison keeps a one-element array operand, avoiding the previously
rejected float32/scalar-float64 rounding error. That [failure](../continuity/runtime/prototype_failure.json)
is retained and covered by a regression test.

## Current evidence

[Validation record](validation.json): **48 focused tests passed** in 0.85 seconds, including
150 complete health-state dictionary comparisons. Cases cover both floating precisions,
mixed edge/value dtypes, noninteger widths, every edge and neighboring values, signed zero,
NaN/infinities, empty clouds, zero-bin layouts, strided/read-only input, working-block
boundaries, fallback/error cases, subclass dispatch, and latency warnings with both decision
settings. Ruff and whitespace checks pass.

The [histogram-only probe](microprobe.json) reads one original positive cloud: 921,600 slots,
340,888 kept points, float32 azimuths and float64 edges. Candidate and reference return exactly
the same six integer counts. The script and report pin the raw message, source files,
configuration, dtype, NumPy version, and imported module path.

| Loaded-machine microprobe, 12 samples | Mean ms | p95 ms |
|---|---:|---:|
| Existing explicit-edge `np.histogram` | 60.11 | 61.39 |
| Bounded `_sector_counts` | 10.54 | 11.04 |

These timings were collected during the concurrent P3 gate and are **not performance
acceptance**. No full detector or ROS replay was run. This fresh checkout has no local native
library yet; histogram counting is independent of it. Build `scripts/build_native.sh` and
verify the local backend before any full detector/runtime comparison.

Production source SHA-256:
`7740db14b55bb5eade51d053a4463fdb996181c305acb47dd45ccad687aadde0`.
Effective configuration remains
`6a6e5d859a0c1a86adce91edf1e8a46cd35b4bee21c5876406f1071cf2eaa46f`.

## Timing remains a separate correction

`Detector.process` currently records `timing_ms.total` before the health call and passes that
partial duration to the latency monitor. This candidate preserves that calculation.
`node.detect_ms` measures the complete detector call; `node.latency_ms` measures decode plus
detector before publication. The [runtime diagnosis](../continuity/runtime/README.md) records
the discrepancy and the failed quiet positive runs. Full gate/history checks and quiet
positive/clear ROS acceptance remain pending coordination by the parent agent.

## Reproduce the small probe

From the chosen checkout in the development container:

```bash
PYTHONPATH=. python3 -m pytest -q tests/test_health_histogram.py
PYTHONPATH=. python3 scripts/bench_health_histogram.py \
  --bag /data/for_hackathon/doubleT_obstacle --out out/health_histogram.json
```
