# Independent review of the bounded mapping results

The completed 2,984-row capture passes the registered **explicit-mapping**
comparison. The independent [checker](review_results_independent.py) reads all
eight raw files, checks their hashes and consecutive frame inventories, verifies
the 38 source hashes against Git, and independently recounts decisions and STOP
intervals. Its [receipt](independent_result_review.json) binds the protocol,
harness, registration, summary and raw bytes. It executes no detector.

| Input and mapping | Frames | STOP frames | STOP intervals | Shared non-timing changes versus upright |
|---|---:|---:|---|---:|
| Empty, upright | 545 | 0 | None | 0 |
| Empty, explicit case 4 | 545 | 0 | None | 0 |
| Empty, explicit case 5 | 545 | 0 | None | 0 |
| Real obstacle, upright | 201 | 193 | 8–200 | 0 |
| Real obstacle, explicit case 4 | 201 | 193 | 8–200 | 0 |
| Real obstacle, explicit case 5 | 201 | 193 | 8–200 | 0 |

The comparison preserves every captured field except the protocol's explicit
runtime timing and latency-only health presentation. It retains decision health,
mount readiness, rotation, track geometry, detections, warnings, ranges, stamps
and every STOP endpoint. The [harness review](HARNESS_REVIEW.md) separately checks
the transform algebra and the per-frame assertion that corrected vehicle input
is byte-identical to upright input. This result review checks the saved captures,
not a new physical remount or independently rerun point transformation.

The wrong automatic-mapping control remains a failure. The empty recording has
**509 STOP frames, all orientation-confirmed**, with **327 at mount status `ok`**.
Its GO frames **311 and 316** are also confirmed with status `ok`. The real-obstacle
control has 190 STOP frames in intervals **5–188 and 195–200**: it loses upright
STOP frames **189–194** and adds **5–7**. These results show why merely suppressing
outputs while orientation is unconfirmed does not resolve the side-mount defect.

The accepted finding is a configuration workaround for these two known mappings
on these two recordings, at candidate source `e9d8fc6`. It is not universal
automatic orientation, an actual ROS/DDS or physical mounting test, J1, final P4
acceptance, or permission to publish. No production algorithm was changed here.
