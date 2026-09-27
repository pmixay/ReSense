# Detector freeze and final node checks — 26 September 2026

Fresh local validation on a 4-vCPU AMD Ryzen 9 7950X3D VM with 15 GiB RAM. This is not the
organizers' i7-9700E stand. Source/runtime libraries: [environment.json](environment.json).
The detector is unchanged from `_ride_p3d`; the reviewed node changes are in `0f808fe`.

## Original recordings through ROS

The runtime image was built from `docker/Dockerfile`. Every isolated run used
`SKIP_BUILD=1 OFFLINE=1 scripts/dry_run.sh <original-bag>`: the container had no network.
For the cold run, `fsync` then `POSIX_FADV_DONTNEED` evicted the bag's pages; `mincore`
confirmed 0 of 1,177,063 pages resident immediately before playback
([cold proof](cold_idle/cache_before.json)). No global kernel cache was dropped.

| Capture | Processed frames | Alarm frames | Decode+detect p95 | First STOP after first processed cloud | Post-settle recorded messages unprocessed |
|---|---:|---:|---:|---:|---:|
| [Cold obstacle](cold_idle/check.txt) |148|143|36 ms|0.4 s|0|
| [Warm obstacle](warm_final/check.txt) |169|166|36 ms|0.4 s|0|
| [Clear tunnel](clear_final/check.txt) |234|0|24 ms|—|0|
| [Stock console: clear](console_stock/clear_check.txt) |243|1|26 ms|15.8 s (false alarm)|0|
| [Stock console: obstacle](console_stock/obstacle_check.txt) |165|161|37 ms|0.9 s|0|

Cold catch-up ends at +7.4 s of recording; warm at +4.7 s. These are not zero-loss claims for
startup: the policy deliberately samples a large initial backlog. Distance on the actual obstacle
was 55.5–56.6 m. The stock-console clear frame is at 53 m; it meets the existing allowance of at
most 2 alarm frames, but fails a stricter zero-alarm probe retained as
[clear_zero_alarm_check.txt](console_stock/clear_zero_alarm_check.txt).

[The stock console](console_stock/check.txt) runs the node, player and listener in separate
containers. Player/listener uid 1000, stock Fast DDS 2.6.12 with shared memory enabled and no XML
profile; node UDP mode. Both plays exited 0; listener received 451 decisions, 162 STOP. Its combined
checker uses broad drop tolerance for the input-switch test, as before. The two per-record
captures above were additionally checked with `--bag` and `--max-dropped 0`, using actual header
stamps and accounting for the four gaps already present in the obstacle recording.

## Final node under bounded read load

One protocol-fixed cold trial on `498f280` also **PASSes**:
[summary](cold_load_final/summary.json), [protocol](cold_load_final/protocol.json),
[checker](cold_load_final/check.txt), [source/capture hashes](cold_load_final/manifest.json).
Two direct sequential readers of separate ride DB files each sustained 63.69 MiB/s throughout
playback. The obstacle bag had zero resident pages before the run. With the same acceptance
limits: 152 processed frames, 145 alarms at 55.5–56.5 m, p95 36.37 ms, first STOP +0.7 s,
catch-up ends +7.3 s, no scene resets and 0 of 124 post-settle recorded messages unprocessed.
There was one trial, no retry or tuning. This measures a bounded read workload; it does not
establish a maximum load or reproduce the earlier mix of downloads, cache writes and installation.

## Failures retained and what changed

[cold_under_load/check.txt](cold_under_load/check.txt) is the first startup 20 s candidate before
its short-backlog correction, while dataset downloads/cache writes and package installation
shared the machine: 138 frames, 134 alarms, first STOP 1.1 s, p95 44 ms, 20 recorded messages unprocessed
after settling. This remains FAIL. Several losses never reached the node; it also coalesced
short queues unnecessarily. The final node preserves queues spanning at most `catchup_step`.
The final idle and bounded-read-load measurements above validate that change under their
recorded conditions; the earlier mixed load was not reproduced. Do not attribute the earlier failure to a test
of the final code, or infer overload tolerance from low compute latency.

[warm_before_short_fix/check.txt](warm_before_short_fix/check.txt) preserves the earlier warm
PASS. Initial normal-user console setup also failed because the extracted archive directories
were mode 700; applying the documented `chmod -R a+rX` before replay fixed access. That failed
setup produced no detector frames and is not a transport measurement.

## Checker and reproducibility

[setO_checker_header_match.txt](setO_checker_header_match.txt) regrades the committed historical
set O ROS capture against the newly downloaded original recording: 0 post-settle messages lost.
The old receive-time-offset assumption incorrectly reported 132; the checker now reads every
CDR header stamp. Clock-drift and genuine-loss tests enforce the distinction.

Raw JSONL captures are retained with each run (compressed copies are committed). Recorder
separators and watchdog snapshots are excluded by `check_dry_run.py`; this accounting does not
remove processed obstacle/clear frames. See [DETECTOR_FREEZE](../../DETECTOR_FREEZE.md) for the
source seal and [SCORECARD](../../SCORECARD.md) for the final assessment.
