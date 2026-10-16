# krisikas/MetroLidar2026

## Verdict
Classical geometry, no learned component: C++17 ROS 2 stack with an analytic gauge polygon, marching 3D track spline, single-frame clusters and 2-frame EMA tracking. Prototype maturity. Headline numbers (0 false stops on empty bags, 17.5-35 m detection, 0 % false stops on platforms and switches) are hard-coded strings in `scripts/verify_system.py`, not computed, so they are unverified.

## Pipeline
1. `cloud_parser.cpp`: 26-byte PointCloud2 parse, NaN/zero removal.
2. `dual_rail_tracker.cpp:estimate_slice` near-cab rail/bed slice (2 m steps to 70 m); the per-slice output is computed but not used by the spline (`track_geometry_spline.cpp:26`, `rail_measurements` unused).
3. `track_geometry_spline.cpp:build_trajectory`: 2/4/6 m marching spline to 150 m; rail-crown z (90th pct), single vs double-track flag from lateral spread, wall-centred lateral correction (gain 0.5, keep 1.8 m from walls, heading clamp ±0.6 rad, curvature clamp R >= 160 m), EMA across frames.
4. `dual_rail_tracker.cpp:smooth_profile`: forward/backward 35 permille slope clamp on z, then 3-tap smoothing.
5. `specialized_detectors.cpp:detect_bulk_obstacles`: keep only points inside the SDF envelope (sdf <= -0.02), fixed-grid 0.2 m voxels, BFS clusters with fixed eps 0.6 m, raw-point minimum 6/5/4 by range.
6. Same file: rail-bar (v 0.25-0.48 m, span_x >= 0.7) and suspended-filament (|u| <= 0.5, v 1.5-2.8 m) sub-detectors, single-frame.
7. `classify_threat`: CRITICAL if sdf <= -0.05 and distance < 80 m, else WARNING/CAUTION.
8. `temporal_obstacle_tracker.cpp:update`: ego-shift by train speed, global nearest neighbour (gate 2.5 m), confirm at 2 hits, confidence +0.15/-0.20, max 3 misses.
9. `train_velocity_estimator.cpp`: 1D longitudinal histogram (0.2 m bins), zero-mean correlation to previous frame, parabolic sub-bin peak, rate-limited EMA.
10. `decision_engine.cpp`: braking distance v*0.5 + v^2/2.4 + 10 m; EMERGENCY_BRAKE only if hazard distance <= braking distance, otherwise TRACK_WARNING.

## Candidate ideas (table)
| # | idea | where in code | mechanism (1-2 lines) | have in ReSense? (yes/partial/no, evidence) | expected effect: recall / range / FPR | cost & risk | evidence in repo (measured? held-out?) |
|---|---|---|---|---|---|---|---|
| 1 | Slope-rate clamp on the floor/z profile, forward and backward passes, then 3-tap smoothing | `src/dual_rail_tracker.cpp:smooth_profile` (lines 274-316) | Limits how far the bed height can jump between waypoints, so one bad far rail or floor estimate cannot shift the gauge floor | partial: ReSense absorbs grade in the bed polynomial (`resense/track.py` L3, L68-69) and has bed residual gating (`floor_max_residual`), but no hard Lipschitz clamp found. ReSense notes floor errors of 0.3-0.65 m at 85-105 m (`config.py` L95) | range / recall at 80-150 m (floor error is the failure mode there); FPR small change | trivial. **Set the limit to >= 0.045**: ReSense notes metro grades reach 4 % (`resense/track.py` L3); the repo's 0.035 would be wrong on such grades | Not measured in repo (no ablation) |
| 2 | Double-track flag from the near lateral spread: p98 - p02 of x in 4-16 m > 6.5 m, then no centre-following | `track_geometry_spline.cpp:71-88` (flag), `:212` (centre-following skipped) | Stops the spline from being pulled to a centre column or the neighbouring track in double-track tunnels | partial: ReSense has per-side wall fits and far-support gating (`resense/track.py` `walls_min_far_support`, `_far_supported_side`), no explicit spread test found (grep "double" in track.py: only floor residual hits) | FPR down on doubleT curves (repo's own `WARNING` at 125-145 m on doubleT curves) | cheap; could mis-flag a wide station | Not isolated |
| 3 | Per-step wall-centred track with a keep-off margin from walls and a heading clamp | `track_geometry_spline.cpp:239-256` | Marches a 2/4/6 m centreline, corrects it from wall percentiles | yes/different: ReSense fits the whole boundary polynomial with a curvature clamp (`resense/track.py` L470, L787, `axis_max_curvature_rate` L941). **Repo 1 (igor688-hub) tried stepwise tracking and abandoned it because error accumulated (its docs/experiments.md "Что не сработало")** | — | — | — |
| 4 | Multi-frame EMA of waypoints with a jump gate (|dxy| < 1.5 m, alpha 0.8, yaw alpha 0.75) | `track_geometry_spline.cpp:348-372` | Smooths the path per waypoint across frames, ignoring jumps | yes: `walls_smoothing` 0.6, `rails_smoothing` 0.7 (`resense/config.py` L75, L89); jump gate not checked | small | trivial | — |
| 5 | Velocity from correlating 1D longitudinal wall/overhead histograms between frames, parabolic sub-bin peak | `train_velocity_estimator.cpp:estimate_velocity` | Odometry-free train speed | yes: `resense/egomotion.py` `texture_profiles`, `correlate_lags`, `peak_lag` (parabolic sub-bin, prominence). ReSense also has an ego veto (`config.py` L357-362) | — | — | Measured only in their README claim |
| 6 | Rail-bar sub-detector: points at v 0.25-0.48 m, |u| <= 0.9 m, grouped along s (0.4 m gap), lateral span >= 0.7 m and vertical span <= 0.35 m | `specialized_detectors.cpp:detect_rail_mounted_obstacles` (~L200-270) | Detects a bar across the rails separately from bulk clusters | yes: `resense/lowobj.py` (`low_candidates`, `mark_rail_line`) | — | — | — |
| 7 | Suspended-filament sub-detector: |u| <= 0.5, v 1.5-2.8 m, vertical span >= 0.35 m, width <= 0.35 m | `specialized_detectors.cpp:detect_suspended_filaments` | Hanging cable/wire class | yes: `resense/clustering.py` `find_hanging` (L406), hanging_min_height 1.8 m | — | — | — |
| 8 | Exact signed distance to a gauge polygon, with a buffer band (0 < sdf <= 0.3 m = advisory) | `clearance_envelope_sdf.cpp:compute_signed_distance`, `is_near_gauge_buffer` | Graded distance to the gauge boundary instead of membership | partial: ReSense uses point-in-polygon with a lateral edge margin (`resense/gauge.py` L13-122, `edge_margin_per_100m` `config.py` L146). Repo's exact distance is a graded version, not new | — | — | Not measured |

## Things done worse than ReSense / red flags
- Deleting rules, not downgrades: `specialized_detectors.cpp:307-314` drops spans > 2.8 m, distant flat objects (span_z < 0.25 m at >= 50 m, which would delete the organisers' 10 cm minimum object), and overhead beams.
- Braking and TTC are out of scope per the organisers (`docs/MeetingText.txt`, ~30:44-31:09); `decision_engine.cpp` turns far hazards into WARNING, so '0 CRITICAL on curves' reflects policy, not detection.
- Fixed-scale clustering (eps 0.6 m, raw-point minima 6/5/4) and only 2 hits for confirmation, versus ReSense's range-normalised eps and zone votes.
- Dead computation: `DualRailTracker::estimate_slice` output is ignored by `build_trajectory` (`track_geometry_spline.cpp:26`), contrary to the SOLUTION text.
- Inconsistent numbers: doubleT_obstacle is stated at 17.5-35 m (SOLUTION 5.1, hard-coded print) while Figure 2 shows 48.7 m for an unnamed bag; no held-out set, no per-km FPR.

## Eval/data tooling worth borrowing
- Little. The only reusable piece is the per-dataset scoring idea in `verify_system.py` (a hazard counts only after 2 consecutive matched frames within 3 m), but its output is hard-coded, so take the idea, not the script.
- The `docs/MeetingText.txt` Q&A is useful context: obstacle = anything inside the 2.1 x 3.0 m gauge, max speed 80 km/h, 2.3 m per frame at max speed. Use these to check any distance-gate parameters.
