# Thin far scan-line threshold A/B (2026-09-29)

The candidate changes `tracking.thin_far_min_voxels` from 4 to 3. The regression run used source
commit `49bfc70` with that one config override, the native detector, and the archived Sep 28 default
gate as its reference. The gate passed with no gated regressions: 202 metrics were unchanged and two
Set F `box0.5` metrics improved.

| Set F synthetic 0.5 m box | Threshold 4 | Threshold 3 |
| --- | ---: | ---: |
| Sequences detected | 1/6 | 2/6 |
| Median first detection | 51.9 m | 64.4 m |
| Median sustained detection | 55.6 m | 55.6 m |
| False detections | 0 | 0 |

The ride retained 130 STOP frames, 32 alarm events, 31 STOP episodes, and a 127.6 m median monitored
range. Five of 11,271 frames changed from GO to CAUTION (0.044 percentage points); the median clear
distance stayed 120.2 m. The five clear recordings had no added, removed, or changed STOP detections.
Their 33-history replay also matched threshold 4 exactly on STOP frames and STOP detection geometry
(204 STOP frames and 55 events in both runs). The Set O diagnostic remains at 16 GO overclaims.

The Set F objects are synthetic point injections into recorded backgrounds, not newly collected or
independently annotated physical-object trials. The result is a narrow recall improvement, with a
small increase in ride CAUTION output; it does not establish general small-object performance.
Cross-ring sparse admission remains disabled (`weak_min_rings=0`, `far_min_ring_count=0`).
