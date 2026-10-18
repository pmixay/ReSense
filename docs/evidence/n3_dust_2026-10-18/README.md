# N3 dust stress — complete development measurements

**Generator and registered measurement deliverables are complete. Dust robustness acceptance fails.** All corrected batteries finished and passed completeness, source, frame and raw-result verification: **30,875 evaluated frame-runs**, archived in **159 raw gzip files**. No dust suppression or health-only classifier is enabled in production.

The evaluated detector is immutable **`9b92df5`**, with native acceleration, through immutable harness **`b9ad5f4`**. The matched health-only controls add the explicit offline hook to that same detector source. These results do **not** measure the later production defaults or establish their dust acceptance. No physical dust recording was supplied; this is deterministic volumetric-return and ray-attenuation stress, not measured dust physics.

## Coverage and provenance

| Corrected battery | Coverage | Evaluated frames |
|---|---|---:|
| [Regular baseline](baseline_pose_fixed/RESULTS.md) | Five empty recordings, real obstacle and Set O; clean/low/medium/high | 15,992 |
| [Dimmed positive baseline](dark_baseline_pose_fixed/verified_complete.json) | Real obstacle, labeled returns set to intensity 1; four levels | 804 |
| [Matched dimmed health control](dark_health_pose_fixed/verified_complete.json) | Identical source, intensity and inputs; four levels | 804 |
| [Matched platform health control](health_platform_pose_fixed/verified_complete.json) | Identical source and inputs; clean/medium/high | 1,035 |
| [Fixed-placement Set F](set_f_baseline_pose_fixed/RESULTS.md) | Six ride starts × five object kinds × four levels | 12,240 |

The [execution receipt](corrected_execution_receipt.json) records every raw-file hash, all complete report hashes, exact detached wrapper/status/log bytes and the recorded pause. All 30 frozen Set F placement banks are archived with their manifest. Source, native library, configuration, generator, helper and per-frame reference identities are verified. Measurements shared a single-CPU host and include a pause; their wall timings do not establish throughput.

## Registered acceptance results

Each empty recording may add at most one STOP episode over its own clean run. The corrected counts are:

| Empty recording | Clean | Low | Medium | High | Failing levels |
|---|---:|---:|---:|---:|---|
| doubleT_platform | 0 | 1 | 25 | 3 | medium, high |
| roundT_doubleT | 0 | 0 | 25 | 3 | medium, high |
| roundT_pressureGate_roundT | 1 | 1 | 22 | 1 | medium |
| roundT_squareT_pressureGate_squareT | 0 | 0 | 58 | 13 | medium, high |
| squareT_platform_squareT_switch | 3 | 12 | 71 | 12 | low, medium, high |

The low-density real crossing-person first inside STOP remains **55.51 m → 55.51 m**, passing the registered 90% first-range criterion. All **61/61 inside** person STOP rows remain. The one lost person association is outside the gauge. The nearby rail object retains its first range, **56.13 m → 56.11 m**, but loses **24/128 inside STOP rows**; first distance alone hides that regression.

At medium and high density, **no real crossing-person or rail-object STOP matches remain**, despite 133 and 20 total STOP frames respectively: those alarms are unmatched. Set O loses 9, 126 and 406 clean inside-object STOP rows at low, medium and high density, with new matches reported separately. The [complete object tables](baseline_pose_fixed/RESULTS.md) and [raw-verified report](baseline_pose_fixed/verified_complete.json) retain every first range, exact lost/new frame, and inside/outside/unknown relation.

High-density baseline health also fails: **2,119/3,998 frames report GO without degradation** across the seven recordings. Only 429 frames are degraded; the real-obstacle high run has 163 GO and zero degraded frames. These counts are separate from the false-alarm and object-retention criteria.

## Set F: identical objects across all densities

The bank freezes all object specifications, clean render hashes and clean dust reference transforms before evaluation. The six original starts, five kinds, seed-0 placements, 110-frame maximum and 8 m cutoff remain unchanged. Each density evaluates the same 3,060 source/object rows; clean physical labels remain in the denominator when attenuation removes returns.

| Level | Matched object STOP rows | Lost clean STOP rows | New STOP rows | Unmatched STOP frames / episodes | GO | Degraded |
|---|---:|---:|---:|---:|---:|---:|
| clean | 1064 | 0 | 0 | 23 / 11 | 1501 | 0 |
| low | 1027 | 61 | 24 | 18 / 13 | 1533 | 0 |
| medium | 752 | 392 | 80 | 1480 / 275 | 385 | 0 |
| high | 14 | 1050 | 0 | 183 / 58 | 2311 | 0 |

Low density loses all clean matches for `46_box0.5`; its clean first STOP was 76.94 m. The `68_person` first STOP falls from 144.10 to 117.98 m. High density loses all matches in 21 of the 26 sequences that had clean matches, while four other sequences had no clean detection to retain. Every sequence, including those clean misses, is shown in the [Set F result table](set_f_baseline_pose_fixed/RESULTS.md).

Unmatched detections use the unchanged approximate legacy association. Real ride backgrounds are not exhaustively annotated, so these unmatched counts are **not proof of false obstacles**. Serialized geometry has 1 cm precision; the independent verifier uses explicit 5 mm matching bounds; no boundary-ambiguous rows occurred in [aggregate.json](set_f_baseline_pose_fixed/aggregate.json).

## Matched health-only experiment

The [paired comparison](corrected_health_parity.json) verifies identical augmentation/reference, detections, warnings, obstacle flags, nearest distance, track geometry, point/candidate/accumulation counts, ego speed and mount on all **1,839 paired frames**. There are no added or lost detections. The dimmed intervention is applied to both baseline and health control, so source or intensity differences cannot explain the comparison.

| Matched control | Level | Degraded / all frames | GO | STOP frames / episodes |
|---|---|---:|---:|---:|
| Dimmed real obstacle | medium | 201 / 201 | 0 | 133 / 22 |
| Dimmed real obstacle | high | 201 / 201 | 0 | 20 / 5 |
| Empty platform | medium | 345 / 345 | 0 | 167 / 25 |
| Empty platform | high | 345 / 345 | 0 | 20 / 3 |

The offline health hook correctly exposes reduced visibility in these controls and sets clear range to zero. It cannot recover missed objects or remove false STOP episodes; robustness acceptance still fails. Clean and low positive detections remain identical to their matched baselines. Intensity 1 is a controlled intervention, not a measured reflectivity model; the Pandar-specific intensity ceiling is not assumed valid for Falcon.

## Coordinate correction and retained failed experiments

Independent review found that the original regular harness combined configured-frame points with calibrated rail height. The correction was registered before new runs. The shared helper now captures the actual last clean `MountCalibrator.apply` matrix, including identity shortcuts and startup replay, and anchors a flat cloud at clean `rail_z(20 m)`. Only generated returns are inverse-mapped; retained original XYZ, intensity and ring values are restored exactly. This is an audited clean model frame, not a surveyed or graded rail plane. Thirty focused tests cover the contract.

Historical configured-coordinate captures remain in the [inventory](historical_capture_inventory.json), including the explicitly incomplete original low-density gzip, which is excluded from acceptance. The original Set F attempt had 15 prepared banks and **no evaluated dusty levels**. Its [placement comparison](placement_correction_parity.json) verifies that all 1,570 preserved clean object specifications and render hashes are unchanged by the correction.

The historical post-tracker suppression prototype increased medium-platform episodes from 25 to 33. The pre-tracker candidate `406ffaa` reduced them to 4 and high episodes to 2, still failing the limit. Both remain rejected and are not rerun or promoted by the corrected results. The [historical dark-positive review](DARK_PERSON_REVIEW.md) preserves their separate limitations.

## Review and reproduction

Acceptance, fixed densities/extinction and seed 20261018 were declared in [the protocol](../lidar_adaptation_2026-10-18/PROTOCOL.md). [SET_F_PROTOCOL.md](SET_F_PROTOCOL.md) gives immutable reproduction commands and placement details. The [regular independent review](INDEPENDENT_CORRECTED_REGULAR_REVIEW.md) independently recomputes associations and gauge partitions across all 18,635 rows. The [completed Set F independent review](INDEPENDENT_COMPLETED_SET_F_REVIEW.md) checks all 12,240 raw rows and the 30 placement banks. The [verifier review](INDEPENDENT_REVIEW.md) preserves tamper probes and the coordinate finding.

The remaining performance work is to satisfy the unchanged false-alarm, retained-object and high-density-health criteria, then validate with physical dust data. Harness completion and complete failed measurements do not constitute production dust acceptance.
