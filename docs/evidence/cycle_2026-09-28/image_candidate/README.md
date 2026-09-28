# Proposed candidate image checks — 28 September 2026

Image `resense:cycle-candidate` has ID
`sha256:ca5ce7502cca717f581ea7de09306b0e00e3bbe78fc138dfc9ae79632fdeebb6`.
It was built from `6104122bccce0ef4800533016774690ede5218f0` in an isolated
checkout. All 31 frozen detector, config and native build inputs exactly match
the full-gate candidate `ef1d8f50299d9ccbbf65fc4ad5519764615853f6`; see
[source.json](source.json). This is a proposed image, pending runtime acceptance.

## Installed package

The complete image suite passed **841 tests**, with zero failures, errors, skips
or deselections, in 464.93 seconds. The container had no network, used the
installed package and native extension, and had the complete original rail-start
cache available. See [tests.txt](tests.txt) and [junit.xml](junit.xml).
Observer tooling added after image commit `6104122` is covered by its separate
focused tests; this run does not claim to test those later files.

The offline synthetic ROS smoke also passed: 80 frames across both supported
topic/frame pairs, no drops, valid freshness, playback at 0.5 times recording
speed. See [smoke.txt](smoke.txt), [node log](smoke_node.txt), and
[status capture](smoke_status.jsonl.gz). This is functional integration evidence,
not a full-rate original-recording latency result.

## Original recording under concurrent load — failed

The first full-rate offline replay of `doubleT_obstacle` ran concurrently with
the image suite, two history replays, and reserved-scene generation on this
four-physical-core host. It failed: only 69 of 201 recording frames were
processed, decode-plus-detect p95 was approximately 345 ms, startup catch-up did
not settle, and freshness failed. The threshold was 100 ms with no post-settle
drops; it was not relaxed. See [check output](loaded_raw_positive.txt),
[node log](loaded_raw_positive_node.txt), and
[status capture](loaded_raw_positive_status.jsonl.gz).

Concurrent work is a confounder, not proof of the cause. This failure is retained.
A repeat with experiment workers finished, and a matched baseline if needed,
must resolve runtime acceptance before promoting the candidate. Neither this
run nor its planned repeat is described as a cold-cache benchmark.
