# Thin far scan-line threshold A/B (2026-09-29)

The shipped default changes `tracking.thin_far_min_voxels` from 4 to 3. The full regression gate was
run on commit `dcaa5db` with the default config and no overrides, using the archived Sep 28 default
gate as its reference. It passed with no gated regressions: 202 metrics were unchanged and two Set F
`box0.5` metrics improved. The full gate, paired monitoring acceptance, and history reports are
archived alongside this note.

| Set F synthetic 0.5 m box | Threshold 4 | Threshold 3 |
| --- | ---: | ---: |
| Sequences detected | 1/6 | 2/6 |
| Median first detection | 51.9 m | 64.4 m |
| Median sustained detection | 55.6 m | 55.6 m |
| False detections | 0 | 0 |

The first-detection median is calculated over successful sequences. Since the successful set changes
from one sequence to two, 64.4 m is not a paired 12.5 m gain on the same object approach. The 50–100 m
box0.5 recall row increases from 2/133 to 5/133.

The ride retained 130 STOP frames, 32 alarm events, 31 STOP episodes, and a 127.6 m median monitored
range. Five of 11,271 frames changed from GO to CAUTION (0.044 percentage points); the median clear
distance stayed 120.2 m. No STOP frames changed. The 69 changed ride detection payloads differed only
by track ID. The five clear recordings had no added, removed, or changed STOP detections. In the
current 33-history replay, all STOP-frame lists and non-ID detection fields match the threshold-4
control (204 STOP frames and 55 events in both runs); 18 of 12,468 history rows differ only by track
ID. The Set O diagnostic remains at 16 GO overclaims.

The Set F objects are synthetic point injections into recorded backgrounds, not newly collected or
independently annotated physical-object trials. The result is a narrow recall improvement, with a
small increase in ride CAUTION output; it does not establish general small-object performance.
Cross-ring sparse admission remains disabled (`weak_min_rings=0`, `far_min_ring_count=0`).

The archived result files are `thin_far_threshold/default_gate.json`,
`thin_far_threshold/default_acceptance.json`, and the threshold-3/threshold-4 history reports with
their per-frame captures.
