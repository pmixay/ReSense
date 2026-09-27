# Current-source cold original-bag checks — 27 September 2026

GitHub Actions [run 36281462241](https://github.com/pmixay/ReSense/actions/runs/36281462241)
tested commit `43b679352a151a53473fc2221a246bec725ccf66`. The full workflow passed, including
pytest with no skips, Chromium, lint, parameter synchronization, Docker/ROS transport and viewer
recovery checks, offline image export/load, and both cold original-bag replays.

The P1/P2 cold step downloaded the organizer archive, verified the committed metadata for both
recordings, recorded the archive/metadata/database SHA256 values in [`provenance.txt`](provenance.txt),
removed the archive, dropped the runner page cache before each replay, and used
`BAG_READ_AHEAD_QUEUE_SIZE=10` at playback rate 1.0. The raw archive and extracted SQLite bags were
removed by the CI cleanup trap. The Actions artifact is
[10918089542](https://github.com/pmixay/ReSense/actions/runs/36281462241/artifacts/10918089542)
(ZIP digest `736e699d10f8f2f7b3616c39f2b9c179053a80d3734fecb137b2341fb0e7cbda`).

| Cold replay | Result | Evidence |
|---|---|---|
| `doubleT_obstacle` (360°, obstacle) | **PASS**: 201 status messages, 187 detector alarm frames, first STOP +1.1 s at 55.5–56.6 m, decode+detect p95 78 ms (mean 68, max 124), freshness contract passed. The startup catch-up ended at +8.8 s; all 113 source messages after that point were processed. Four missing frames are gaps in the source recording, not node losses. | [`doubleT_obstacle_node.log`](doubleT_obstacle_node.log), [`doubleT_obstacle_status.jsonl.gz`](doubleT_obstacle_status.jsonl.gz) |
| `roundT_doubleT` (120°, clear) | **PASS**: 252 status messages, zero alarm frames, decode+detect p95 48 ms (mean 41, max 63), freshness contract passed, and zero of 201 source messages after the settle point left unprocessed. | [`roundT_doubleT_node.log`](roundT_doubleT_node.log), [`roundT_doubleT_status.jsonl.gz`](roundT_doubleT_status.jsonl.gz) |

The first obstacle STOP appears while its input is still marked stale, so the node remains
fail-safe. A current result is established after startup catch-up; the clear recording remains
alarm-free throughout. These checks use the explicit ten-message read-ahead. They do **not** close
the separate default-setting issue: the default 1,000-message prefetch still releases the whole
recording as an overdue burst and has a stale-result failure (run 362776). Keep C5/C7 and captain
action 21 partial until the captain accepts the bounded-prefetch/prewarm operating procedure or a
separate change makes the default path pass.
