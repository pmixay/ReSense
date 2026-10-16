# Kate-vsn/lidar_detector

## Verdict
Classical ROS 2 sketch ("First attempt" commit): wall-histogram ego-speed plus a per-frame moving-object detector. Real logic, but no gauge, no metrics and no result files; the README lists run steps only.

## Pipeline
1. `lidar_processor.py:TunnelAnalyzer.discover_topic`: subscribes to the first PointCloud2 topic found (BEST_EFFORT QoS), republishes `/filtered_points`.
2. `lidar_processor.py:lidar_callback`: per-voxel mean downsampling, voxel size 0.05 + 0.007·|y| m.
3. `lidar_processor.py:calculate_ego_motion`: 0.1 m histogram along y of wall points (|x|>1.5 m, z in (-0.5, 1.0)), np.correlate argmax between frame t and t-2; speed = shift / dt, with dt from wall-clock `time.time()`.
4. Publishes `/train_speed` (m/s).
5. `motion_detector.py:MotionDetector.pc_callback`: shifts the previous cloud by -v·dt in y, cKDTree distance; points > 0.40 m from the shifted past are "seeds".
6. DBSCAN(eps=0.8, min_samples=5) on the whole current cloud (only z > -0.5 applied).
7. Cluster kept if >= 10 points, >= 5 seeds, and x-range < 3 m and y-range < 3 m; published on `/moving_anomalies` with a warning log.
8. No gauge or envelope, no track, no temporal confirmation: each frame stands alone. Dockerfile installs open3d and opencv, which the code never imports.

## Candidate ideas
| # | idea | where in code | mechanism | have in ReSense? | expected effect: recall / range / FPR | cost & risk | evidence in repo |
|---|---|---|---|---|---|---|---|
| 1 | Distance-adaptive voxel (0.05 + 0.007·\|y\|) | `lidar_processor.py:lidar_callback` | Voxel grows with range to even out point density | yes: `resense/clustering.py:_scaled` and `voxelize` (range-normalised voxels); `docs/ALGORITHM.md:115` (range-dependent DBSCAN eps) | none new | trivial | none |
| 2 | 1-D wall-histogram cross-correlation for ego speed | `lidar_processor.py:calculate_ego_motion` | argmax of correlation of wall-point histograms at t and t-2 | yes, stronger: `resense/egomotion.py` cue 1 (running-background subtraction, normalised profile, sub-bin parabola, confidence, `speed=None` when unsure) | none | none | none (no accuracy measured) |
| 3 | Ego-compensated "newly appeared" seeds (points > 0.4 m from the shifted previous frame) | `motion_detector.py:pc_callback` | One-frame differencing: only points absent from the previous frame survive | partial: `resense/accumulate.py` (ego-shifted buffer); a fresh-STOP provenance rule of the same kind was measured and not adopted (`docs/EXPERIMENT_FRESH_STOP_EVIDENCE.md`) | Recall loss: a target is flagged only on the frame it appears, then absorbed. FPR: unknown, wall-texture changes at curves would seed | low cost, high FP risk | none |
| 4 | Cluster bbox gate (< 3 m in both horizontal axes) to reject long walls | `motion_detector.py:pc_callback` | Removes long wall-like clusters | yes: `resense/clustering.py:_is_infrastructure` (thin, wall-at-side and linear shape rules) | none | none | none |

Nothing here is worth porting.

## Things done worse than ReSense / red flags
- No evaluation of any kind: no result file, no logs, no per-bag counts. README describes run steps only.
- Ego-speed `dt` comes from wall-clock arrival time (`time.time()` in `lidar_callback`), not from message stamps; `fps = 30` is set and unused. Under `ros2 bag play` the arrival jitter feeds straight into the shift used by `motion_detector.py`.
- Sign consistency between the two nodes is not shown. By my reading of `np.correlate` indexing, a positive published speed means motion toward -y, while `motion_detector.py` shifts past points by -v·dt, which compensates motion toward +y. This is unverified (not run). If inverted, static wall points become seeds, and only the bbox gate hides them.
- Full-cloud DBSCAN every frame with no ROI and no timing data.

## Eval/data tooling worth borrowing
None. Only an RViz config and `ros2 bag play` commands.
