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

## Exact proposed-default candidate

[`candidate/gate.json`](candidate/gate.json) measures clean `ef1d8f5` with the
committed proposed defaults and no overrides. The full gate **passes**: two
enforced rail-object recall metrics improve and the other 144 enforced metrics
are unchanged, with no waivers, worse rows or missing rows. Cached rail-object
hits rise from 128 to 129 of 185 overall and from 125 to 126 of 126 after frame 75;
person hits remain 61/61. The separately retained raw replay improves 123 to
126/126 after frame 75 and 125 to 128/185 overall.

[`monitoring_acceptance.json`](candidate/monitoring_acceptance.json) aligns every
frame and timestamp in all 15 captures. Every alarm flag and detection payload
is identical on the five empty bags and eight ride pieces. Monitoring coverage
costs pass. The existing 16 set O GO clearance-overclaim flags remain unchanged;
this diagnostic does **not** pass a zero-overclaim requirement, and its labels
inherit an earlier fitted envelope rather than an independent survey.

The candidate run took 1,905.4 seconds while sharing the machine. Its larger
latency-warning count is not a clean runtime comparison; decision-level coverage
and detection results above are the relevant paired checks. All full captures,
the set F report, log, config and artifact hashes are retained with the gate.

The subsequent frozen reserved comparison passed without gains or regressions.
All 33 processing histories have identical paired captures, and the installed
candidate image passed 841 tests. The exact measured detector was integrated into
the score development branch at `84763cf` after independent review. Local positive
ROS runtime/freshness fails for candidate and baseline; the clear-bag check passes.
Deployment remains provisional and final candidate branch CI is pending.
