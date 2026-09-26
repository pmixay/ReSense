# M2: rate, tilt, startup and raw-data checks

M2 changes monitoring uncertainty; it adds no detection-recall gain. This validation used
candidate `482caab` and the unchanged default config, with Python and the native library both
imported from the isolated monitoring worktree. [Source receipt and commands](receipt.json).

## Detection nonregression

- **18 stress runs:** every second frame, +3° roll, and +3° pitch on all six recordings.
  Every alarm, advisory, event, episode, labelled-result, event-history and mount-status
  metric matches its frozen P3d reference. Results: [half rate](5hz.json),
  [roll](roll_plus_3.json), [pitch](pitch_plus_3.json).
- **30 startup runs:** start frames 0, 10, 20, 30 and 40 on all six recordings. Every output
  summary field, including positive hit counts, matches the archived reference exactly.
  [Results](offsets.json), [comparison](offsets_comparison.json), [run log](offsets.txt).
- **Raw Set O:** all 1,510 frames and timestamps match the archived raw replay. Every
  detection and warning row is identical; all per-object and background scores match.
  The current cache scores also match their own archived reference exactly.
  [Raw comparison and complete scores](raw_comparison.json).

Raw and quantized-cache scores remain different, as they were before M2. The rail cube has
26 raw versus 23 cache STOP frames (first at 48.0 versus 42.7 m); the large outside object
has seven versus six false STOP frames. Background alarms are one raw frame/ID versus three
cache frames/two IDs. Small-edge advisory frames are 25 versus 23. These are existing
representation differences, not M2 improvements or regressions.

Raw fit coefficients differ from the archived raw replay only at numerical precision:
maximum absolute differences are 1.78e-15 for floor coefficients, 1.68e-16 for yaw and
4.77e-18 for curvature. All other track fields match. The numerical cause was not isolated.

## Monitoring effect and limits

| Set O measure | Frozen baseline | M2 |
|---|---:|---:|
| Raw target-envelope range overclaims | 51 | 41 |
| Raw overclaims while GO | 44 | 34 |
| Cache target-envelope range overclaims | 54 | 44 |
| Cache overclaims while GO | 46 | 36 |
| Raw median monitored-range estimate | 97.4 m | 97.3 m |

Raw replay changes 12 GO frames to CAUTION and lengthens no range estimate. M2 leaves many
overclaims unresolved; this result does not establish obstacle-free track or physical
envelope truth. Existing labels and the 0.5 m overclaim tolerance are unchanged.

Across stress runs, the conservative upper bound on additional CAUTION is **1.59 percentage
points**. The conservative lower bound on the median-range ratio is **0.982**. These satisfy
the limits of 5 percentage points and 0.95. [Every recording and calculation method](stress_comparison.json).
Baseline stress archives contain summaries, so pre-M2 ranges are reconstructed from unchanged
serialized monitoring/candidate/detection bounds with a 0.1 m rounding allowance. CAUTION
counts include every thin marker without STOP or advisory, even if another health warning
already existed. These bounds are supplementary to the exact paired observer comparison.

## Artifacts

All 18 stress replay streams are compressed under `stress_frames/`. The complete
[raw stream](seto_raw.jsonl.gz) and [current cache stream](seto_cached.jsonl.gz) are retained.
[Artifact hashes](manifest.json) cover the reports, receipts and replay streams.

These are offline checks. ROS timing and source-freshness acceptance are recorded separately;
no runtime acceptance is inferred from the timing fields in these files.
