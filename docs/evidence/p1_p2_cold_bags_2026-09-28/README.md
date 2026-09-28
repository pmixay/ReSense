# Original-bag cold-start and input-path evidence — 2026-09-28

GitHub Actions [run 36432860933](https://github.com/pmixay/ReSense/actions/runs/36432860933)
passed all four jobs on `testovaya-gpt` at tested source commit
`9086cd123316739065568220aeddcda035c42836`. The Docker job restored the two original bags from
the checksum-verified Actions cache, dropped the Linux page cache before each replay, and ran
`scripts/p1_cold_bag_test.sh` with 10-message rosbag2 read-ahead. This is a cold-cache CI replay;
it is not a physical jury-stand run.

| Recording | Bag frames | Alarm frames | End-to-end current-result latency | Startup / source accounting | Result |
|---|---:|---:|---|---|---|
| `doubleT_obstacle` | 201 | 190 | median 55 ms, p95 62 ms, max 144 ms (183 current results) | catch-up settled at +1.8 s; first STOP +0.8 s; 4 timestamp gaps belong to the source bag and 0 source messages were left unprocessed | PASS, person range 55.5–56.6 m |
| `roundT_doubleT` | 252 | 0 | median 32 ms, p95 38 ms, max 69 ms (245 current results) | catch-up settled at +0.7 s; 0 source gaps and 0 source messages left unprocessed | PASS, clear path |

The byte-level node input check also passed on every frame: 201/201 obstacle frames (921,600
points each) and 252/252 clear-bag frames (307,200 points each) were identical to the reference
decoder. The remote-viewer check in the same run was a separate-container simulation: all 11
layout topics appeared, live detector topics arrived, a deliberately interrupted link was
detected, and the viewer recovered. It does not replace importing the Foxglove layout on a
physical second device.

The retained files contain 216 obstacle-bag and 266 clear-bag JSON status records, including
watchdog snapshots around playback; literal `---` lines are delimiters. The CI dry-run scorer
counted the 201 and 252 recording messages shown in the table.

The run's CI artifact is named `p1-cold-dry-run-9086cd123316739065568220aeddcda035c42836`,
artifact ID `10974507564`, uploaded size 108,113 bytes, SHA-256
`e489c80acb7ff9ab2b7ebcb3f2b40238255f783403f6a53b0d9ed0dd2fc19e58` (GitHub retains it for 30
days). This directory keeps the status streams, node logs, frame-identity output, provenance, and
result locally in the repository; `SHA256SUMS` covers those files.

The fixture bag hashes and full raw logs are in `provenance.txt` and the two node logs. The
summaries above are from the CI job log, not inferred from the status captures. Run the same test
with:

```bash
IMAGE=resense:ci scripts/p1_cold_bag_test.sh
```

On the merged local branch, with `/data/cache/new_data` restored, the required full suite also
passed: `RESENSE_REQUIRE_SYNTHETIC=1 python -m pytest -q -rs` → 765 passed, six subtests, no
skips or deselections (five Python `tarfile` deprecation warnings). The ride-cache-dependent test
therefore ran locally; the hosted CI's single deselection is specific to its missing data cache.
