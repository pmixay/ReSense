# Durable archive of the P4 16.10 raw outputs

`p4_raw_2026-10-16.tar.xz` (2,775,260 bytes, SHA-256 in [SHA256SUMS](SHA256SUMS)) holds every raw
output of this evaluation that used to live only in the ephemeral cloud container (`/home/user/rs-data`):

| path in the archive | content |
|---|---|
| `p4out/` | X3 batteries (Prescott control, Haswell control, 1.1.0) with all 120 `probe.jsonl` raw rows, job plans, logs, completion sidecars; Linux intake and runtime comparisons |
| `j1/` | J1 dry run: `judge_runner.py` `.jsonl/.csv/.meta.json`, `.empty.json`, both tags |
| `blas/coretype/` | OpenBLAS kernel calibration runs (amendment 1) |
| `x1/707ea9c`, `x1/1.1.0` | X1 run 5: hooks-on / hooks-off judge outputs, `.attrib.json`, logs, track-model baselines |
| `x1/check_*` | label-check re-runs with full frame snapshots and `check.json` |
| `x1/icp*` | ICP odometry used (Haswell) and the first Prescott ICP |
| `x1/superseded/` | X1 runs 1–4 and their checks (evidence of the label fixes) |
| `logs/`, `*.sh`, `dl/dataset.sha256`, `seto_zst.*` | intake queue scripts and logs, archive hashes |

Verified after packing: extracted, every file of
[../raw_sha256.json](../raw_sha256.json) and [../../range_attribution_2026-10-16/raw_sha256.json](../../range_attribution_2026-10-16/raw_sha256.json)
present with the indexed SHA-256 (819 files, 0 mismatches). Paths inside the JSONs still name the
container (`/home/user/rs-data/...`); strip that prefix to locate a file in the archive.

Not included, being reproducible and verified: the organizer bags (public archives, hashes in
[../../p4_start_2026-10-15/provenance.json](../../p4_start_2026-10-15/provenance.json)) and the node-decoded caches
(rebuilt with judge `cache_decoded.py`; per-frame identity in [../linux_intake.json](../linux_intake.json)).

    tar -xJf p4_raw_2026-10-16.tar.xz -C <dir>
