# Independent corrected regular-dust review

The completed corrected evidence is internally consistent and supports **failure of N3 acceptance**, not a production robustness improvement. I independently parsed all 39 compressed captures: 15,992 baseline rows, 804 dark-object control rows, 804 matching health-observer rows and 1,035 platform health-observer rows, totaling 18,635. [The receipt](independent_corrected_regular_review.json) records exact inputs and the [read-only reviewer](review_corrected_regular.py); no detector was rerun.

Decision counts, STOP episodes, degradation, each label association, per-frame inside/outside/unknown membership, first associated ranges and lost/new inside/outside rows were reconstructed from raw detections and original labels. The reconstruction uses the registered legacy distance/lateral tolerance and one-to-one assignment, without calling the detector's association helper. It agrees with the completed reports.

| Real-obstacle result | Clean | Low | Medium | High |
|---|---:|---:|---:|---:|
| Overall STOP frames | 193 | 170 | 133 | 20 |
| Crossing-person matches inside gauge | 61 | 61 | 0 | 0 |
| Crossing-person matches outside gauge | 6 | 5 | 0 | 0 |
| Rail-object matches inside gauge | 128 | 104 | 0 | 0 |
| First inside crossing-person match | 55.51 m | 55.51 m | none | none |

Low dust passes the narrow crossing-person first-range criterion and retains all 61 inside matches. It still loses 24 of 128 rail-object matches and one outside person association. Medium and high produce 133 and 20 STOP frames respectively, but every such frame has an unmatched detection and neither target has a matched STOP. For example, medium frame 69 reports an unmatched detection at 25.39 m; clean frame 69 associates the crossing person near 56 m. Overall STOP totals must not be described as retained object detection.

The reports correctly keep outside associations separate: medium Set O produces eight matches to `small_outside_near` and zero inside matches to that label. The crossing person's label relation also changes by frame. These are associations under existing development labels, not a surveyed classification of every possible object in the scene.

Empty-recording limits fail: all five medium cases add more than one STOP episode; low `squareT_platform_squareT_switch` adds nine. Across all seven high-density baseline cases, 2,119 GO frames lack degradation. Thus the preserved low crossing range cannot establish overall dust acceptance.

The seven health-observer comparisons match their respective controls exactly for every serialized field except health, clear distance, decision and timing. This includes detections, warnings, tracks, point and candidate counts, accumulation, ego motion, mount state, augmentation and frozen references. Medium/high dark-obstacle frames are all degraded, as are medium/high platform frames, while detections remain unchanged. The observer therefore improves the measured diagnostic response but recovers none of the missed person or rail-object detections and removes none of the unmatched alarms. It remains an offline experiment.

All raw gzip hashes, frame indices and timestamps match their completed reports. Frozen reference identities and proper rotations agree across densities; prescribed densities, attenuation, seed, source/added/removed counts and flat rail-height references are consistent. I independently reconstructed source payload hashes for 15 selected frame/intervention combinations, including dark-label intensity changes, and checked each against the original NPZ and metadata. The recorded full-precision rail reference differs from the serialized rail-offset reconstruction by at most 0.000500 m, consistent with the documented 0.001 m serialization rounding. This is a sample source check; the author's complete-only verifier separately rehashed every source cache file.

Source identities match immutable detector `9b92df5` and corrected harness `b9ad5f4`, with the recorded native library. The generator returns source indices and simulation annotations separately; the detector receives ordinary frame data and count metadata. The harness freezes the clean run's actual applied rotation before each density replay, restores retained real returns exactly and performs label association after detection. No simulation-truth hint enters the runtime observer. The dark intervention deliberately uses label boxes to lower input intensity; it is a declared stress construction, not measured material reflectivity.

These results are **not a new stress evaluation of selected core `cecab1b`**. Placement is a flat cloud anchored at clean `rail_z(20 m)`, not a surveyed graded rail plane. Physical dust scattering, sensor-specific echo behavior and held-out generalization remain unknown; shared-host timing establishes no throughput. The [completed Set F independent review](INDEPENDENT_COMPLETED_SET_F_REVIEW.md) covers its separate synthetic-placement scope. The accepted core manifest and its bound evidence were not modified.
