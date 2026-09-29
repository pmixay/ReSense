# Candidate CI cold-recording evidence

[CI run 36467904812](https://github.com/pmixay/ReSense/actions/runs/36467904812)
passes checks, pytest, Docker and offline-build at source
`854700995ac93f1314d1c62e94c7b00c89ddd986`. Its production files match measured
continuity candidate `ef1d8f5`; later score-branch changes are documentation only.
The downloaded original-bag artifact is retained here, with hashes.

The original CI checker passes. A local recount of its saved captures additionally
requires all 201 positive and 252 clear recording frames, retaining the original
100 ms decode-plus-detect threshold, zero post-settle drops, and freshness check.
Both pass. Header stamps align one-to-one with every original positive frame.

| CI original recording | Frames | Detector alarm frames | Decode + detect p95 | Current-result end-to-end p95 | Freshness |
|---|---:|---:|---:|---:|---|
| 360° positive | 201/201 | 193 | 78 ms | 96 ms over 165 current results | PASS |
| 120° clear | 252/252 | 0 | 51 ms | 58 ms over 247 current results | PASS |

Existing label matching on exact positive header stamps finds person 61/61 and
rail 128/185 overall, **126/126 after frame 75**. Those are actual detector outputs,
not an assertion that all startup results are fresh. Startup catch-up ends at
+3.6 seconds; current-result counts above remain separate. The four missing
messages within the positive recording are recorder gaps, not processing drops.

This is CI-runner evidence, not an organizer-stand measurement. The retained quiet
laptop failures remain valid for that machine. It does not validate the newer
P3 merge. `timing_ms.total` in captures excludes later health computation; the
runtime numbers above use node decode-plus-detect and current-result end-to-end.
