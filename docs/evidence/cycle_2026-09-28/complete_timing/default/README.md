# Complete detector timing: full native validation

Measured commit: `bc75abe04a0b13c29c555a7baf64b4745603c02a`. Baseline: accepted health histogram production
`ef71c9dc4f88147327dcb41ea79358dfc690ba77`, as archived in `health_histogram/default`.
The [protocol](../protocol.json) was committed before this full gate; the timing contract was
registered in `c9db941` before production changes.

The gate passes with all **208 non-latency metrics identical**, including **146 enforced
metrics**, no waivers and no missing rows. Sixteen additional timing metrics are informational.
Exact comparison covers **15,269 frames across 15 captures**: **0 changed non-timing
payloads** and **0 invalid timing contracts**. This includes detections, warnings,
track/mount state, monitored and clear distance, every non-latency health field, and every
unknown field. Set F matches exactly except its elapsed wall time: all **30 cases / 3,060
actual rows**; 110 is the configured maximum per sequence.

`timing_ms.stages` preserves the former total through tracking. The new `total` includes
health and result construction. The comparison validates both stage sums and the new
`stages + health + result` sum within the registered rounding bounds. Health p95 is verified
against the previous completed totals in its configured window, with the exact declared
basis and sample age, a null/zero first sample and the ten-completed-sample warning threshold.
The evaluator creates a fresh detector at each capture's index 0; it has no internal resets.

All 15,269 changed health payloads are retained in
`parity/health_timing_differences.jsonl.gz`; 2,272 frames change overall health level
through the validated latency-only rule. Default `decision_level` and all non-latency
outputs match. `latency_affects_decision: true`, reset, exceptions and numeric direct health
callers are covered by the focused tests; the opt-in policy deliberately observes the fuller
interval one result later. `total` ends after result construction; final timing assignments
and return remain outside the internal timer. `node.detect_ms` includes that final overhead;
node decode and capture end-to-end measurements remain separate.

Native timing/health/comparator tests: **128 passed**. Existing calibration/node policy and
input-reset checks: **11 passed**, NumPy backend. No skips. Ruff passes on all changed Python
files. Exact commands and backend limitations are in `validation.json`; logs are retained.

Source SHA-256: `506a1e05d19b99bae936188bfed4f2015a0cc0d562dec0251457022f6668f194`.
Effective config: `22a30ff265035e06358a21696cfb8bc61b598d16e5a64aa3536abfefbc4bd5fb`.
Native library: `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534` (the accepted B5 binary).
Only `resense/detector.py` and `resense/health.py` changed in production scope. `run_identity.json`
and `completion.json` bind clean source, observer files and actual native file hashes before
and after the gate. `run_gate.py` preserves the executed wrapper and absolute paths as provenance.

Reproduce parity with `scripts/compare_complete_timing.py --reference` pointing to the archived
health baseline, `--candidate` to this directory, `--protocol ../protocol.json`,
`--freeze run_identity.json`, `--source-root` to this candidate's production source, and a new
`--out` directory. The captures are losslessly compressed; archived hashes refer to archived
bytes. Original paths in comparison records identify the measured external files.

This corrects an incomplete measurement. Shared-load gate timing establishes **no execution
speed gain, score increase or ROS runtime acceptance** for this candidate. The prior runtime
and source evidence retain their original scope.
