# Cold-bag startup check — PASS, 26 September 2026

GitHub Actions [run 36280434044](https://github.com/pmixay/ReSense/actions/runs/36280434044),
commit `67e456b21a7706ad5ea641e3209044bbed625150`, downloaded and validated the organizer
archive, evicted the runner's page cache, and ran the original `doubleT_obstacle` through the
Docker node. The cold-test player used rate `1.0` and rosbag2 read-ahead queue size `10`.

The exact `scripts/dry_run.sh` gate passed with `--require-freshness`, `--expect-obstacle`,
`--distance 50:62`, `--max-p95-latency 1000`, `--max-dropped 0`, and the original bag comparator.
It reported 201 status messages, a first STOP at +1.1 s in the 55.5–56.6 m band, 78 ms
decode-plus-detect p95 (99 ms maximum), and freshness PASS. The node caught up in 14.0 s with
zero catch-up skips; the checker waited until +16.5 s to score post-settle loss. The database
contains known receive/header-time holes, so the checker compared against its own message stamps.

The archive SHA-256 is `e23166801794cdeb2dcd77a3cc8b40a906b1d9cefab6f26739e368234e9168be`,
metadata SHA-256 is `90f3314528232a912a0a2a1de8e90e1d155a814ab59a130aec3fcf65d76a6c09`, and DB3
SHA-256 is `05f1d7f7d1bbbc5e9453877416cc9f7367c19e31d35a5291271d863fc89c5ad9`. The source archive
and extracted database were removed by the task cleanup trap. The run artifact is
[10918554315](https://github.com/pmixay/ReSense/actions/runs/36280434044/artifacts/10918554315).
[`provenance.txt`](provenance.txt), [`node.log`](node.log), [`result.txt`](result.txt), and the
compressed full [`status.jsonl.gz`](status.jsonl.gz) preserve the replay.
