# N1/N4 evidence — 18 October 2026

Implementation and operator instructions are in [HOWTO.md](HOWTO.md). This directory preserves successful checks, rejected display settings, complete display replays and actual DDS results with their separate source versions.

## Display development and honest range cost

`unbounded_display_v1/` records the rejected initial smoother: visually low jitter but as much as 3.49 m lateral lag. `lag_bounded_v2/` adds a 0.25 m lateral agreement cap with 6 m smoothing distance; curve at 40 m p90 remained 0.0615 m, above the 0.05 m target. Both are rejected as the final display contract.

The selected display uses 9 m smoothing distance and bounds the combined lateral/vertical displacement to 0.25 m. `display_v3_projection.json` reprojects complete saved, rounded detector rows without rerunning or changing the detector. The exact source rows are retained in `lag_bounded_v2/rows/` and can be reprojected with `project_saved.py`. It is a development comparison, not the final combined-core acceptance run. The rows were captured on the initial implementation before later N2/N6 core changes; the earlier replay script hashed disk source at completion, so its core hashes do not authenticate the loaded Python modules after concurrent source edits. The final replay script now records all core source hashes at startup/end and reports any drift.

| Complete recording | Frames | Visible 3D jitter p90,40/80/120 m | Visible adjacent pairs,40/80/120 m | Median displayed/support range |
|---|---:|---|---|---|
| Set O |1510|0.0181 / 0.0297 / 0.0402 m|1394 / 842 / 255 of 1509|86.0 /130.15 m|
| Person `doubleT_obstacle` |201|0.0039 / 0.0124 / 0.0218 m|188 /180 /143 of 200|139.0 /151.0 m|
| Curve `roundT_doubleT` |252|0.0325 / 0.0305 / 0.0284 m|161 /44 /11 of 251|52.0 /141.9 m|

All nine visible-jitter measurements meet 0.05/0.08/0.15 m. The far curve denominator is only 11/251, and the median range loss is substantial. The report also retains all-state jitter (including geometry that is not drawn), which exceeds the target in some cases. No claim is made that hidden, unsupported geometry became accurate. None of these saved rows lost its GO/STOP outline; maximum drawn 3D lag was at most 0.25 m. Display projection never mutates detector results.

## Actual Docker and graphics checks

`preliminary_dds_report.json` records a real ROS2/Humble node, DDS messages and PTY rosbag2 player: 80/80 synthetic frames across Pandar/Falcon profiles in one unchanged process; Space pause/resume, no incoming frames during pause, stale monitoring after pause, and Down changing rate 0.5→0.4. These preliminary checks used legacy range policy and the intermediate runtime image; final conservative-profile checks must be distinguished from this result.

`preliminary_graphics/curve_rviz.png` is an unedited actual RViz screenshot on Xvfb/llvmpipe OpenGL4.5, reached through `scripts/run_demo.sh`. The bag contains preserved decoded curve points from original `roundT_doubleT` frames 130–199, reserialized for this visual check; `curve_preview_receipt.json` identifies that transformation. It is not quality or throughput input. The screenshot shows the real green gauge in a CAUTION frame. Most frames under concurrent one-core quality workloads were correctly invalidated as source-stale; retained logs disclose this. It demonstrates graphics/software rendering, not 10 Hz capability or isolated performance.

Final measurements, source hashes and local tests are added below as they complete. Hosted CI and a release remain deferred by the user.

## Final local transport and graphics checks

The detector core for these measurements is `f5ff15f`, with bounded orientation replay enabled (four frames) and N6 rail extension explicitly **off**. The matched curve runs use image `a018d39a2369`; the later node intake correction is commit `00ee76f`, image `3ddf27362e5d`, with the same detector core. `final_core_f5ff15f/runtime.json` and the follow-up receipt distinguish these versions. The later corrected-core transport check is recorded below.

Heavy quality jobs were paused on the actual one-CPU host for the local checks. The unchanged accumulation timing test passed: mean 8.2 ms, p95 10.4 ms, maximum 10.6 ms over 19 measured synthetic frames. The earlier contended full-suite p95 was 289.8 ms; the 150 ms limit was not relaxed. This short synthetic test is not a full ROS throughput claim.

The conservative profile passed actual ROS2/Humble DDS plus PTY controls with 40/40 Pandar and 40/40 synthetic Falcon frames in one process. The strict final run then passed 40/40 Pandar followed by **100/100 actual Falcon frames**, also in one process. Space pause/resume and the native Down key (0.5→0.4) worked. Start/resume epoch faults and pause/end-of-bag expiry remained active, with no application drops or catch-up skips. Falcon retained `monitored_small=null` and `clear_distance=0`; the actual recording is not assigned synthetic obstacle truth. Its node decode/detect latency p95 was 17.0 ms, source-age p95 34.1 ms, and reported peak node RSS 120.1 MB.

The independent [100-frame comparison](../n2_falcon_2026-10-18/actual_dds_prefix_comparison.json) found zero mismatches in shared detection/warning payloads, point counts, stamps, flags and post-first decisions against the full Falcon offline capture. Its four STOP frames (indices 25–28) are the same 115 m static-support alarms; none is a held Pandar alarm. The first epoch FAULT and conservative Falcon null/zero range are recorded intentional differences.

Two real failures were found and fixed before accepting that final run. The retained Falcon subset initially had empty SQLite schema metadata, so Humble could not open it; N2 reconstructed the schema row and verified every CDR payload, message ID, stamp and QoS unchanged. The next run received only 94/100 frames: the six initial frames preceded `/iv_points` discovery. Commit `00ee76f` pre-subscribes that known topic, preserves explicit sensor-profile selection, and makes the integration harness require the exact metadata frame count. The failed and incomplete attempts remain recorded. All 146 node tests passed after the correction; pinned Ruff and parameter-copy checks passed.

The documented wrapper also played the same 70 preserved curve frames at rate 0.5 with and without software RViz/Xvfb:

| Measurement | Headless | Software RViz |
|---|---:|---:|
| Frames received |70/70|70/70|
| Fresh frames |69 + initial epoch fault|69 + initial epoch fault|
| Node latency p95 |54.5 ms|99.8 ms|
| Source age p95 / maximum |61.8 /74.5 ms|132.3 /239.4 ms|
| Dropped / catch-up skipped |0 /0|0 /0|
| Detector container mean CPU cores |0.16|0.67|
| Detector container peak memory |156 MiB|478 MiB|

The RViz container includes the renderer; cgroup values exclude the player, observer, Xvfb and screenshot capture. These are single local runs with quality jobs paused, not a multi-core extrapolation. All 70 corresponding decisions, detections, warnings, track fields, clear ranges and gauge fields were exactly equal between the two modes. Every published solid gauge stayed within axis support. The retained screenshot is the actual unedited window. Rate 0.5 (about five input frames per second for this bag) is demonstrated on this host; no 10 Hz claim is made.

## Corrected-core transport confirmation

Independent N2 review found that copied nested metadata could exceed the startup
history memory estimate. The correction is core commit `7b7b02c`; node, gauge,
configuration and thresholds are unchanged. Image `acbd890efa86` overlays only
`calibration.py` onto the accepted `3ddf27362e5d` image. The
[image receipt](final_core_7b7b02c/image_receipt.json) verifies all 43 relevant
source files and the identical native Python 3.10 extension in the node import
context.

With nine heavy quality process groups paused, the corrected image passed the
[strict same-node run](final_core_7b7b02c/report.json): 40/40 Pandar plus 100/100
actual Falcon frames, zero restarts/drops/catch-up skips, pause/resume, rate
0.5→0.4 and explicit profile/reset boundaries. The
[independent comparison](final_core_7b7b02c/payload_comparison.json) matches all
140 frame payloads against the earlier accepted run with **zero semantic
mismatches**. It includes every decision, range, health severity/message,
freshness validity/reason, detector payload, gauge state and reset generation;
only enumerated measured time/rate/resource values are excluded. Nonframe
reset/stale transitions also match. The comparator detects deliberate changes
to decision, clear range, generation and solid gauge range.

Raw logs, compressed status, exact command and counters are retained under
`final_core_7b7b02c/`. The container was stopped before the corrected-source host
suite. This narrow confirmation does not relabel the earlier software-RViz,
2,308-frame display or full-suite measurements as the new source version.

## Final full-precision display replay

`final_core_f5ff15f/` contains complete immutable-core reports and gzip rows for all four recordings, with source hashes at start/end. Display calculations use the actual shared `GaugeDisplay` and full-precision detector models. All 2,308 input frames are accounted for; source hashes are unchanged, detector results are unmodified, no GO/STOP outline disappears, every solid range stays within axis support, and maximum drawn 3D lag is at most 0.25 m.

| Complete recording | Frames | Visible 3D jitter p90,40/80/120 m | Visible / raw-supported / all adjacent pairs,40/80/120 m | Median displayed/support range |
|---|---:|---|---|---|
| Set O |1510|0.01817 /0.02975 /0.04029 m|1394/1498/1509;842/1262/1509;255/856/1509|86.0 /130.15 m|
| Person |201|0.00391 /0.01244 /0.02187 m|188/200/200;180/200/200;143/198/200|139.0 /151.0 m|
| Curve |252|0.03253 /0.03055 /0.02846 m|161/251/251;44/202/251;11/157/251|52.0 /141.9 m|
| Platform |345|0.01955 /0.01364 /0.02013 m|256/338/344;115/201/344;64/193/344|45.0 /120.0 m|

All twelve **visible-edge** measurements pass the registered 0.05/0.08/0.15 m limits. Same-pair raw Set O jitter is 0.04227/0.11435/0.13271 m, so the reported reduction also exists on identical frame pairs. Availability is a separate cost: only 11 of 251 curve pairs show the 120 m edge, and median curve/platform display ranges contract sharply. The all-state diagnostics, including geometry that is deliberately not drawn, still exceed the targets in several cases. This is a stable supported display, not an improvement in far detector geometry or obstacle-free range.

The replay's tool wrapper returned exit143 when collected; every report and complete gzip stream is present. The exit status is recorded rather than presented as exit0. `replay_artifact_integrity.json` independently verifies every row count, saved hash and per-recording numeric check. The replay was paused during the isolated hardware window, so its elapsed wall times are not performance measurements. The final whole-project local suite separately passed 1,884 tests plus 12 subtests, with seven unavailable historical-fixture deselections; see the [final JUnit report](../lidar_adaptation_2026-10-18/junit-core-final.xml).

## Development checks

`development_validation.json` records runtime hashes and the image identity. The real Chromium suite passed 83 tests with 0 skips. Final affected gauge/readiness/decoder tests passed 9 tests with 0 skips. The initial focused run had 158 passes plus one decoder-parity failure caused by different real processing clocks; the parity test now uses identical deterministic clocks, while dedicated freshness/expiry tests and real DDS keep their separate timing coverage. Earlier failed reports remain explicitly named. Pinned Ruff, shell syntax, and parameter-copy checks pass.

## Independent RViz marker expiration

`marker_expiry/report.json` and the unedited before/after screenshots test actual ROS messages produced by `DetectorNode.gauge_markers` in real RViz/Xvfb/llvmpipe. After four seconds of updates the publisher remains alive but sends no further messages, DELETE commands or watchdog output. Green pixels in the viewport fall from 2,850 to 0 in the screenshot 1.52 s after publishing stops. The targeted unit test verifies the actual message lifetime is 0.5 s and grey republishing uses only the original remaining hold budget; the screenshot is not a sub-second timing measurement. The normal advancing RViz clock therefore removes old geometry independently of a blocked detector executor. An initial probe with `--network none` could not authenticate the X11 display; the successful probe uses the same `--net=host`/XAUTHORITY setup as the documented wrapper.
