# LevLobanov/MosHackaton-DepTransport

## Verdict
Classical geometry, no learned component: Rust 2024 + r2r ROS 2 pipeline (greedy tunnel-centre search with a repulsion-spring potential, rectangular gauge, per-frame clustering). Hackathon demo maturity. README claims (path extended to 150 m, 'best of the methods tried') have no numbers, and there is no detection evaluation in the repo.

## Pipeline
1. `src/ros2.rs:parse_point_cloud2_into` (L117): PointCloud2 to `Vec3` array.
2. `src/calibration.rs:calibrate_track` (L46-69): per rail, direction from the top-band centres of the first and last Y bins (`estimate_rail_direction`, L91-128). Track heading is the mean of the two rails; roll from the rail-to-rail delta. Run on every frame (`main.rs` L110-119).
3. `src/calculations.rs:TunnelPathSearcher::search` (L165-306): marches along -Y in 1 m steps, 5 m slices. Per step, a 0.1 m (x, z) grid inside a window around the previous centre and the tunnel corridor (6 m x 7 m). The centre is the grid cell minimising a repulsion-spring potential summed over slice points (`compute.rs:cpu_best_candidate` L135-182: sum of exp(40/(d^2+0.01)) + exp(d^2+0.01)).
4. `smooth_path` (L319-369): triangular-weighted moving average, radius 20, plus a separate height average; 5 end points trimmed (`main.rs` L122-137).
5. `calculations.rs:TrackGeometry::new` (L420-533) and `find_points_in_train_gauge` (L545-592): box gauge along the smoothed path (half-width and half-height from `train.width` and `train.height`), with half-space end caps and a broad-phase radius.
6. `obstacles.rs:cluster_obstacles` (L166-220): spatial hash, union-find, fixed radius 0.35 m, min 3 points; per frame.
7. `main.rs`: publishes `/lidar/obstacles` (JSON), `/lidar/obstacle_detected`, `/lidar/nearest_obstacle_distance`. No state across frames for alerts.

## Candidate ideas (table)
| # | idea | where in code | mechanism (1-2 lines) | have in ReSense? (yes/partial/no, evidence) | expected effect: recall / range / FPR | cost & risk | evidence in repo (measured? held-out?) |
|---|---|---|---|---|---|---|---|
| 1 | Soft centre by balancing a repulsion and a spring term over every slice point (not only percentiles): centre = argmin sum exp(A/(d^2+eps)) + exp(B(d^2+eps)), with A = 40B from the README derivation | `calculations.rs:TunnelPathSearcher::search` (L165-306), `compute.rs:cpu_best_candidate` (L135-182), `settings.tunnel_path.repulsion_factor` 40, `spring_factor` 1 | Smooth centre that uses all wall points, so one-sided occlusion pulls it less than a percentile does | partial: ReSense uses per-bin percentiles of |dy| for walls and a midpoint (`resense/track.py` `estimate_axis_from_walls` L392-436), plus weighted polynomial fits. No exponential potential found (grep `exp\(` in track.py: none relevant) | range on curves where one wall is missing; no direct FPR gain. The obstacle's own points are inside the potential (no exclusion), so it can bias the centre | cheap (a grid search per slice, rayon); runs CPU and GPU | No measurement in repo; README calls it "the most effective of those tried" with no numbers |
| 2 | Gauge end caps by half-space test: a point projecting onto the first or last segment is dropped if it lies behind the path start or beyond the path end along the segment normal | `calculations.rs:find_points_in_train_gauge` L549-566 | Stops points beyond the trusted path from being projected onto an end segment and counted as obstacles | partial: ReSense cuts the trusted range (`resense/config.py` `axis_valid_margin` 15 m, `beyond_axis` demotion, `clustering.py` L344-350). A half-space cap is a different, cheaper geometric form. Not verified as absent (no targeted grep) | FPR at the far end of the trusted path, where the axis is weakest | trivial | Not measured |
| 3 | Per-slice tunnel search restricted to a window around the previous centre and to the tunnel corridor (search window, corridor clamp, break on empty slice) | `calculations.rs` L188-300 (`restrict_points_to_search_window`) | Bounds how far the centre can jump between slices | yes/partial: ReSense has rate limits and per-bin gating (`resense/track.py` `floor_max_residual` L159-177, `axis_max_curvature_rate` L941). Marching search itself is not new: repos 1 and 2 in this batch both tried stepwise marching and reported error build-up on curves | — | — | Not isolated |
| 4 | Triangular-weighted moving average with a radius that shrinks at the path ends | `calculations.rs:smooth_path` (L319-369) | Smooths the path without shrinking the ends | yes: ReSense fits polynomials and uses EMA with explicit smoothing constants (`resense/config.py` L45, L75, L89) | — | — | — |
| 5 | Per-frame rail calibration from two end bins (top-band centres) and a roll from the rail delta | `calibration.rs:estimate_rail_direction` (L91-128) | Cheap heading and roll from two points per rail | no (weaker): ReSense uses a 2-rail histogram pair with polynomial fits (`resense/calibration.py`, `resense/track.py` `estimate_rails` L606-700). Repo's method is less robust to one bad end bin | — | — | — |

## Things done worse than ReSense / red flags
- The gauge is undersized: `settings.json` and the example set `train.width = 2.0`, `train.height = 2.8` (passed to `TrackGeometry::new`, `main.rs` L125-150), versus the organisers' 2.1 x 3.0 m (`krisikas/MetroLidar2026/docs/MeetingText.txt` L197).
- No temporal confirmation: `cluster_obstacles` runs per frame and `main.rs` publishes every frame, so a 3-point cluster within 0.35 m is an alert on its own.
- README and code disagree: the README says 'bilinear spline' that does not penalise curves; the code is a triangular moving average (`calculations.rs` L319-369).
- Rails are recalibrated from scratch every frame from two end bins (`calibration.rs` L91-128), with no state and no robust fit.
- Claims without evidence: 10 unit tests, none on detection performance; no bag list, no metrics file.

## Eval/data tooling worth borrowing
- Nothing reusable for evaluation: there is no metrics script, no ground-truth tooling, and no bag-level test in the repo.
- Per-layer visualization toggles (`settings.json` `visualize.*` flags, `visualize.rs`) make it fast to debug one stage at a time. ReSense already has `viz.py`; the per-stage switch set is a useful addition.
