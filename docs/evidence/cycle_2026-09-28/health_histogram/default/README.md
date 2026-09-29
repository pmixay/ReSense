# Combined-source health histogram: full native gate

Measured commit: `ef71c9dc4f88147327dcb41ea79358dfc690ba77`.
Baseline: combined P3/score defaults `b84ea8f`, whose production source is unchanged in experimental `25a218a`.

Full gate passes without waivers or missing rows. Exact per-frame comparison covers all 15,269 real-recording frames across 15 captures, with 0 changed non-timing payloads. This includes detections, warnings, track/mount state, clear distance and all non-latency health fields. Set F semantic output matches exactly: all 30 sequences and 3,060 actual rows; only the recorded summary.wall_s differs. The 110-frame argument is a maximum: the generator stops an approach when d < 8 m.

Health timing differs on 15,252 frames; 2,333 frames change overall health level solely through the validated latency warning rule. Complete before/after health payloads are retained in `parity/health_timing_differences.jsonl.gz`. The comparator keeps every non-latency field and message, validates the exact latency message grammar, budget and rounding, and allows the derived overall level to differ only with `latency_affects_decision=false`. Stage timings remain in all captures. Shared-load timing is diagnostic only.

Source SHA-256: `c0273a13a67ab4872dab00154caa75f6b30f50416775062c591fbb47906a0fa4`.
Effective config: `22a30ff265035e06358a21696cfb8bc61b598d16e5a64aa3536abfefbc4bd5fb`.
Native library: `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
The startup and completion records verify clean frozen source and unchanged source after evaluation. Only `resense/health.py` differs from the baseline production scope.

`run_identity.json` preserves the exact four-worker gate command. Reproduce parity using `scripts/compare_health_gate.py`, the archived combined-default baseline, this directory as candidate, `combined_protocol.json`, this directory's `run_identity.json`, `--source-root` pointing to the frozen candidate checkout and `--reference-manifest-sha256 87ad31f65f05b83baa40542681db45cec04d7e2ce8ac8fb96704d0f11cadd687`.

The registered 48 histogram/full-health tests passed, including 150 complete state dictionaries. The comparator guard tests separately cover unexplained levels, malformed latency warnings, source identity, detection drift and incomplete set F. No additional processing-history replay was run: this stateless health-count change preserves the measured output history; no new history-test acceptance is claimed. Quiet installed-image positive/clear ROS runtime remains separate and pending.

Captures are losslessly compressed; artifact hashes describe archived bytes. Original absolute paths in the comparison remain provenance for the measured files, with corresponding basenames retained here.
