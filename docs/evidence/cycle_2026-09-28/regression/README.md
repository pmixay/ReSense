# Full regression — 28 September improvement cycle

## Fresh baseline

[`baseline/gate.json`](baseline/gate.json) measures clean commit `4b6f344`, original
detector defaults and the repaired tooling dependency. It passes against
`regression_baseline_2026-09-27_quality.json` with no overrides, waivers, missing
rows or worse enforced metrics. It processed every cached frame: six recordings,
1,510 organizer-object frames and all 11,271 extended-ride frames, followed by the
registered set F straight approaches. The complete fresh cache intake is retained
in the adjacent [`intake`](../intake/README.md) packet.

All 146 enforced metrics are unchanged. The report's `same: 208` also includes 62
unchanged informational metrics; it does not mean 208 enforced checks. Sixteen
informational timing metrics differ. The 1,564.1-second run shared the machine
with other workers, so those timings are not a runtime latency benchmark.

Five obstacle-free bags retain 40 alarm frames, 11 track events and 13 STOP
episodes. The extended ride retains 130 alarm frames, 32 events and 31 episodes.
These are cached-input results; raw replay counts differ and remain separately
reported. This baseline reproduction does not claim improved detection quality.

The packet includes the gate log, effective YAML, deterministic gzip copies of
all 15 per-frame captures and the full set F report. `artifact_manifest.json`
records every artifact hash. The source seal references the complete gate and
verifies that its measured commit has the exact current detector/build inputs.

The candidate full gate, aligned output comparison and processing-history stress
are still running. The candidate has not replaced the score branch's detector.
