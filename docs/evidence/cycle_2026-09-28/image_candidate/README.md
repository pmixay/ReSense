# Proposed candidate image checks — 28 September 2026

Image `resense:cycle-candidate` has ID
`sha256:ca5ce7502cca717f581ea7de09306b0e00e3bbe78fc138dfc9ae79632fdeebb6`.
It was built from `6104122bccce0ef4800533016774690ede5218f0` in an isolated
checkout. All 31 frozen detector, config and native build inputs exactly match
the full-gate candidate `ef1d8f50299d9ccbbf65fc4ad5519764615853f6`; see
[source.json](source.json). This image measures the continuity candidate now integrated into the development
branch. Deployment acceptance remains provisional.

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


## Quiet original-recording checks

All experimental CPU workers finished before these runs. Same playback wrapper,
1.0 rate, queue 10, `--network none`, installed native package, and no global cache
flush. Host: Intel Core i7-8565U, four physical cores/eight logical CPUs. This is
not the organizers' target stand. Runs were sequential, candidate then baseline;
this single pair does not establish a speed improvement.

| Original bag / image | Status frames | Decode + detect p95 | Freshness | Checker |
|---|---:|---:|---|---|
| 360° positive / candidate | 198/201 | 125 ms | FAIL: no fresh valid result | FAIL |
| 360° positive / baseline | 166/201 | 137 ms | FAIL: no fresh valid result | FAIL |
| 120° clear / candidate | 252/252 | 93 ms | PASS | PASS |

The candidate positive instrumented detector-stage p95 is 53 ms; baseline is
58 ms. These internal stage totals exclude the subsequent health computation;
they are not the full `Detector.process` wall time. Both
positive runs exceed the 100 ms decode-plus-detect threshold. Their post-settle
processed intervals contain no missing recording messages, but startup/end
coverage and freshness fail; zero in-interval drops does not establish full
recording coverage. Baseline image ID is
`sha256:a3da7c28771a8ce2eb32f5e13e55c01ca59a12ad15719b40b3ba2cb7115b57f4`.

The clear run has zero alarms and drops. Its current-result end-to-end p95 is
105 ms, distinct from its passing 93 ms decode-plus-detect result. The checker did
not impose an end-to-end threshold. No runtime or deployment improvement is
claimed. The independent reviewer supports development integration based on the
quality evidence while retaining these deployment limitations.

Captured checker results: [candidate positive](quiet_candidate_positive.txt),
[baseline positive](quiet_baseline_positive.txt), [candidate clear](quiet_candidate_clear.txt).
Each has a matching `_node.txt` and `_status.jsonl.gz` file in this directory.


Integration verification after the later observer/wrapper additions: 89 focused
tests and six subtests passed, Ruff passed, parameter copies matched, and the
31-file source seal verified. The 841-test image result above retains its exact
image source identity rather than claiming these later tools were in that image.


## Subsequent CI verification

The complete [candidate CI at `8547009`](ci_8547009/README.md) passes all four
jobs, including original cold recordings and offline build. Retained captures
also pass an all-frame recount: positive 201/201, clear 252/252, freshness valid,
zero post-settle dropped recording messages. Decode-plus-detect p95 is 78 ms
positive / 51 ms clear; current-result end-to-end p95 is 96 / 58 ms. Actual CI
positive detections recover 126/126 rail frames after frame 75, with person 61/61.
This addresses candidate CI, not the laptop's remaining runtime problem or the
organizers' unmeasured stand. The new combined P3 source needs its own validation.
