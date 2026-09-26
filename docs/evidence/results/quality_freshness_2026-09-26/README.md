# Freshness and combined candidate runtime evidence

**Combined runtime acceptance: FAIL.** These original-bag runs test the M2 + freshness image,
not the current root branch combination of P3d + freshness. The separate synthetic functional
trials used the earlier P3d image with the new node bound in. The standalone clear replay reported one false STOP at
53 m, violating its registered zero-alarm limit. The failure remains in `original_clear.log`
and `standalone_clear_false_stop.json`. No trial was repeated and no threshold was relaxed.
All captures passed freshness checks and lost zero recorded messages after their settle point.

| Trial | Frames | Raw detector STOP | Decode + detect p95 | Missed after settle | Result |
|---|---:|---:|---:|---:|---|
| Cold obstacle | 149 | 144 | 37.268 ms | 0 | PASS |
| Warm obstacle | 171 | 164 | 36.805 ms | 0 | PASS |
| Standalone clear | 233 | 1 | 25.248 ms | 0 | **FAIL: false STOP** |
| Cold obstacle, bounded reads | 153 | 148 | 37.898 ms | 0 | PASS |
| Stock Fast DDS: clear | 235 | 0 | 25.847 ms | 0 | PASS |
| Stock Fast DDS: obstacle | 169 | 162 | 36.608 ms | 0 | PASS |

`combined_runtime_summary.json` contains the exact metrics, freshness reasons and valid ages.
`combined_runtime_protocol.json` was committed as `fdfe81a` before these trials. The original
freshness contract was committed as `b04e1d3`. `run_combined_runtime.py` is single-use per trial
identifier; each `*_started.json` records the executed command and environment.

The cold runs had **zero resident pages** before replay, measured by file-local eviction and
mincore; no global page-cache drop was used. For the load trial, two direct sequential readers
covered the capture at 63.71 MiB/s each for 35.14 s, with no errors. This is one bounded workload,
not a general overload guarantee. `bounded_reader_source.py` preserves the helper imported by
the runner; its hash is recorded in `combined_runtime_started.json`.

## Source and artifact identity

- Candidate source: `0145cbb8dd26b3777084aedb3945f49dda741caf` (M2 monitoring + freshness).
- Image: `sha256:9919631de63f97b1e4d79699c3f556b40537c2853808c5e3e65902f9dc17b916`.
- Native kernels enabled; installed detector/health, node and harness hashes match the candidate
  in `candidate_source_receipt.json`.
- Local review archive: `resense-image-quality-0145cbb.tar.gz`, **475,753,310 bytes**.
- Archive SHA-256: `5cd6078357217f013a96ab66a8a166dcfaa3940e1124f4682ec2761d73840a25`.
- Archive location on this host:
  `/home/resense/validation/quality_cycle/freshness/archive/` (binary kept outside Git).

`archive_receipt.json` explicitly records `runtime_acceptance_passed: false`. The candidate
image was removed locally before loading the archive; checksum, loaded source hashes and native
kernels then passed with networking disabled. Application version is **1.0.0**, imported from
`resense`; inherited OCI version **22.04** belongs to Ubuntu. The export log's `commit: 25ad3dd`
is the export checkout HEAD, not the image source; the image revision remains **0145cbb**.
The old `a0af9d...` image remains `resense:p3d-reference` and was restored as `resense:latest`.
No release, Git tag, publication or candidate promotion occurred. No offline-build cache claim
is made for this legacy-builder image.

The export log ends with an older default-node example; historical bags require
`ros2 launch resense_ros detector.launch.py freshness_mode:=replay`.
The source export helper's printed example was corrected after this captured export.

## Humble adapter and functional tests

`metadata_capability.json` proves stock Humble Fast DDS publishes valid UTC source timestamps.
Humble's default executor discards this metadata before callbacks; our narrow executor adapter
preserves it for marked LiDAR subscriptions and passes other subscriptions to upstream behavior.

The first real-node functional trial passed 14 checks. Its exact source is
`node_runtime_stock.py`. The separate final metadata trial passed **15/15**, with 45 frames and
7 watchdog snapshots (`runtime_stock_final_result.json`). Its node SHA is
`95d1721d3b3238a0fa0358f98740a83b6069404411767e94bd5dd227d2de9274`, also the combined image node.
Both first callbacks and drained DDS queues carried comparable source ages. Tests cover stalls,
resume, timestamp jumps, input switches, held STOP and fresh recovery.

These functional scenes are **synthetic**, generated with seed 3 by `generate_scenes.py`
(clear tunnel and a 0.6 m box at 40 m). The first executed script's label `real obstacle STOP`
means the actual detector processed this synthetic fixture; it is not an untouched real obstacle
recording. The final script labels this explicitly. Scene generation needs the pinned host
Open3D environment. `scenes.npz` is reproducible input, kept outside this compact packet.

`tests_provenance.log`: 156 targeted node/checker/release tests passed. Earlier development logs
are retained: initial expected assertion changes and a synthetic test-fixture constructor error
were corrected before the final pass. Functional trials ran while other workers were active;
their timings are not performance evidence. The original-bag trials above used the idle window.

## Interpretation

- Replay age measures publisher UTC, not original acquisition age. Live mode requires comparable
  acquisition UTC. Consumer clocks must be synchronized to use `evaluated_at_utc_s` for expiry.
- Validity describes the time of evaluation. The single-threaded watchdog checks every 0.1 s
  when available and cannot publish during a blocked callback. Consumers must expire status
  locally; the `/decision` string alone is insufficient for motion control.
- Held STOP remains visible through invalid input but cannot count as new positive detector
  evidence. Exposed held STOP still counts against clear-run false-alarm criteria.
- Compressed captures and logs retain complete JSONL/log bytes, including original carriage
  returns and trailing spaces. Build and functional/development logs with those bytes use `.gz`. The standalone clear failure remains a
  blocker to claiming that all registered criteria passed; this packet does not authorize release.
