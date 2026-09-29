# Current available-data gate — 28 September 2026

This is a fresh per-frame replay of the sealed 27.09 detector on the six original recordings and
the organizers' `cloud_with_fake_obj` set. It was run from `testovaya-gpt` at commit `2583e0d`
against the current full baseline `regression_baseline_2026-09-27_quality.json`. The detector and
configuration match that baseline; the source detector seal is checked separately.

All comparable gated metrics match the baseline: **159 same, zero worse**. The six original
recordings contain 2,488 frames; five empty recordings have 11 alarm events and 13 STOP episodes
in 2,287 frames. Set O has 411 STOP object-frames of 801 visible in-envelope object-frames across
all eight objects, six outside-object STOP frames, and zero background alarm frames. The labelled
person is detected in 61/61 frames; the labelled rail object after frame 75 is detected in 125/126
frames in the cache-based evaluator.

This is a **partial gate**, not a full-gate pass. `/data/cache/new_data` was absent, so the run
explicitly allowed the 3 ride rows and 15 set F straight rows from the baseline to be missing.
Those 18 metrics are listed in `gate.json`; nothing here establishes a current ride result. The
ride has no real obstacles in any case, and set F uses synthetic positives. Latency is informational
and reflects this shared host.

`frames/*.jsonl.gz` contains the actual per-frame outputs, `effective_config.yaml` records the
configuration used, and `manifest.json` records the command, hashes, frame counts, baseline and
the missing-data scope. Cache source and timestamp verification are recorded in
[`p4_data_intake_2026-09-26.json`](../p4_data_intake_2026-09-26.json).

Reproduce the run with the command in `manifest.json` after restoring the seven caches under
`/data/cache`. Remove the two `--allow` arguments only after restoring `new_data`; otherwise the
comparison must fail on the missing ride and set F rows.
