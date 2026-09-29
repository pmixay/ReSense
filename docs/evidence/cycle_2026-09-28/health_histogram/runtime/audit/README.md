# Quiet health histogram runtime audit

Four sequential, registered, warm-disk local runs. This is one matched pair per
recording, not cold-start or target-hardware acceptance. The baseline positive
failure is retained. Auditing happened after all captures ended and did not
influence their timings.

## Identity and exact raw outputs

Baseline image/source: `25a218a` / `2fd88d8b…`; candidate: `ef71c9d` /
`c0273a13…`. Both installed/source file maps differ only at `resense/health.py`.
The effective config, installed native binary, package versions and node code
are identical. Exact complete identities/hashes are in `summary.json`, which
also binds the registered protocol and execution record.

Both variants processed every original header stamp: 201/201 positive and
252/252 clear, in exact order, with zero unprocessed bag messages. At every paired
frame, detections, warnings, detector obstacle, detector clear distance, point/
candidate/corridor counts, track and mount outputs are exactly equal. No production
code was changed by the auditor.

The positive recordings have two intrinsic header gaps, approximately 0.2 s after
index 138 and 0.4 s after index 164: four missing nominal 10 Hz slots already absent
from the bag. Both nodes' `dropped_frames=4` counter reflects those slots, not
unprocessed stored messages. Clear bags have no such gaps and counters stay zero.

## Runtime and availability

| Recording / variant | Decode p95 | Detect p95 | Decode+detect p95 | Current E2E p95 | Strict current frames |
|---|---:|---:|---:|---:|---:|
| Positive baseline | 30.30 ms | 79.94 ms | 105.15 ms | undefined (no current results) | 0/201 |
| Positive candidate | 27.46 ms | 52.96 ms | 76.32 ms | 167.85 ms | 170/201 |
| Clear baseline | 17.645 ms | 63.051 ms | 77.328 ms | 86.758 ms | 245/252 |
| Clear candidate | 19.435 ms | 47.584 ms | 60.513 ms | 73.777 ms | 250/252 |

The component p95 values must not be added: each comes from its own sample
ordering. Reports preserve count, mean, min/max, p50/p90/p95/p99, every frame's
decode/detect/latency/ages, and all actual current-result E2E samples. Stage
`timing_ms.total` is not substituted for full node latency.

Baseline positive has 200 source_stale and one queue_stale result and fails the
freshness contract's requirement for at least one valid result. Candidate positive
has one epoch_unconfirmed, 28 catchup and two source_stale results; its contract
passes but its availability remains incomplete, including later catch-up gaps.
Clear baseline has one epoch_unconfirmed and six catchup results; candidate has
one of each. Both clear runs have zero STOPs and pass the contract.

## Raw and fresh target recall

Raw detector matching is unchanged: person 61/61, rail 128/185 overall and
126/126 from frame 75. Earlier raw rail coverage remains 2/59 visible frames before
75. Fresh matching requires an actual current detector STOP, not held, plus a
frame snapshot with valid/current freshness, no catchup, registered source,
residence and queue-age bounds, and the freshness contract. Every original
visible label remains in the denominator, including any missing capture frames.

- Baseline positive: 0/61 fresh person and 0/185 fresh rail matches; no fresh onset.
- Candidate person: 49/61 fresh matches. First fresh STOP at frame 16; first run of
  five consecutive fresh STOPs starts at frame 18. Fresh misses: 8–15, 17, 42, 44, 46.
- Candidate rail: 117/185 fresh matches, with 115/126 from frame 75. First fresh
  STOP and first five-frame sustained interval start at frame 73. Earlier misses
  remain 1–11 and 27–72; later fresh misses are 137, 153, 157, 161, 163, 172, 177,
  181, 183, 187 and 189.

This supports a measured local processing improvement while retaining the
remaining availability gaps. It does not establish full fresh recall, a general
hardware speedup, or a score increase by itself.

## Files

`baseline_positive.json`, `candidate_positive.json`, `baseline_clear.json`, and
`candidate_clear.json` contain full audit rows/distributions and source/label/
checker hashes. `audit_fresh_capture.py` is the exact observer executed for all
four. `summary.json` binds capture hashes, audits, image/protocol/execution
provenance and exact paired raw-output comparison. `summarize.py` independently
checked those identities and generated the summary. Original runtime captures,
image identities and execution logs remain one directory above, unchanged.
