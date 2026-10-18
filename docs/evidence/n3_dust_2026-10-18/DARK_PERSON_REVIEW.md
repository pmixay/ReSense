# Complete dark-object control

**Historical pre-coordinate experiment; not final N3 acceptance.** Independent
review found that the original augmentation mixed pre-calibration XYZ with a
post-calibration rail height. The coverage and association checks below remain
reproducible, but these measurements do not establish the registered rail-relative
dust geometry. Corrected measurements must use a separately frozen applied
transform and rail reference and a new output directory. Original captures are
preserved without alteration.

The separate `406ffaa` pre-tracker experiment completed all **804 frames**:
201 original real-person frames at clean, low, medium and high density. Original
returns inside the frozen legacy object boxes were set to intensity 1 before
augmentation. The exact same intervention is applied to its own clean control.
The preserved [historical verifier](historical_summarize_regular_dust.py) checked source hashes,
compressed capture hashes, every frame index and timestamp, decision counts and
independently reconstructed object associations. Its result is
[verified_complete.json](candidate_dark_person/verified_complete.json).

| Density | STOP | CAUTION | GO | Degraded | Crossing inside / outside matches | Lost clean crossing inside / outside / unknown |
|---|---:|---:|---:|---:|---|---|
| clean | 193 | 0 | 8 | 0 | 61 / 6 | reference |
| low | 169 | 0 | 32 | 0 | 61 / 5 | 0 / 1 / 0 |
| medium | 26 | 175 | 0 | 201 | 4 / 0 | 57 / 6 / 0 |
| high | 14 | 187 | 0 | 201 | 0 / 0 | 61 / 6 / 0 |

The one low-density crossing association lost at frame **74 is outside** the
gauge in that frame's label. All **61 inside crossing matches are retained**.
The crossing's temporal first matched STOP stays **55.51 m** at low density;
medium first is 55.57 m, despite losing 57 inside matches. First range alone
therefore conceals the substantial medium-density retention failure. High has
no crossing match. No unknown-gauge loss is present in these legacy labels.

| Density | Inside rail-object matches | Lost clean inside rail-object matches | Temporal first STOP |
|---|---:|---:|---:|
| clean | 128 | reference | 56.13 m |
| low | 103 | 25 | 56.11 m |
| medium | 2 | 128 | 56.37 m |
| high | 0 | 128 | none |

The two medium rail-object matches occur at new frames, so all 128 clean matches
are still lost. The outside walkway person has no matched STOP at any density.
Every lost and newly matched row is retained in the verified report, split by
its per-frame inside, outside or unknown relation.

This is a separate dark-object experiment, **not a controlled causal comparison
against the original-intensity `9b92df5` battery**: both detector source and
object intensity differ. Each dusty level is compared against its own clean
source/intensity control. No paired dimmed `9b92df5` replay is implied. The
candidate was already rejected by the empty-scene episode criterion; these
positive controls give an additional reason not to enable suppression. Medium
and high explicitly degrade visibility, but that does not restore missed STOPs.

The box intervention, legacy labels and approximate association are development
controls, not measured reflectivity or physical-dust certification. Concurrent
and paused wall timings are informational only. No production dust candidate is
enabled by this report.
