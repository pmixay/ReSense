# Andreymazo/MetroDetectionV2

Single-commit repo ("1s"), ~6k LOC, much of it commented-out dead code (tracker_v2.py and unified_object_engine.py are largely commented duplicates), plus a Three.js/FastAPI viewer. Emoji-heavy README.

## Verdict
Classical geometry with hard-coded mount constants plus an Open3D-ICP odometry; prototype maturity. No evaluation harness, no labels, no false-alarm-per-km numbers, no held-out data. README "results" are raw counts of detections on recordings that are empty (or whose only obstacle is at ~56 m), presented as successes. Trust: essentially none for performance claims. Nothing here we do not already have or have not already rejected.

## Pipeline
1. `generate_submission_v2.py:process_point_cloud`: axis swap to a fixed frame, "selective load balancer" (decimate background to ~40k points while keeping the far corridor), cone voxel downsample.
2. `extract_floor_with_ransac` (misnomer: no RANSAC): per 5 m range sector, median height of points within |x|<1.5, floor = [median-0.35, median+0.15].
3. `track_vector_module.py:TrackVectorLock`: track vector on 5 m nodes, shifted by odometry, near head (<30 m) refreshed from floor medians, floor Y clamped to [-1.80,-1.35] and default -1.52 (lidar-mount constants). `generate_adaptive_gauge_mask`: half-width 1.35-1.40 m (tunnel) or up to 3.5 m (station), ceiling 3.0-3.3 m (tunnel) or 3.8 m (station).
4. `find_obstacles_adaptive_density`: x,y of points beyond `dynamic_start_z` scaled by `start/|z|` (range compression), DBSCAN eps 0.45 min_samples 2; boxes merged by range-growing gates (`merge_and_filter_raw_obstacles`); size/point-count validator with range-decay thresholds (`validate_and_filter_objects`).
5. `tracker_v2.py:LidarObstacleTrackerV2`: 3D nearest-centroid association, gate 2.5 + 3.5*step + 0.02*d (max 7.5 m), report only after >=8 hits; coasting 15 frames.
6. Odometry `cos_processor_v12.py`: ICP (rails corridor + wall landmark "passports"), weighted fusion 0.75/0.25 with acceleration clamps and inertial fallback; `cold_starter.py` estimates start speed from sleeper density combs.
7. Output: per-frame CSV (nearest object distance, centre, size).

## Candidate ideas
| # | idea | where in code | mechanism | have in ReSense? | expected effect | cost & risk | evidence in repo |
|---|---|---|---|---|---|---|---|
| 1 | Far-field onset from floor-return density: last 5 m range bin where floor returns drop below 150 marks where the far regime (compression/looser thresholds) starts | `generate_submission_v2.py:find_obstacles_adaptive_density` (`dynamic_start_z`, clipped 15-180 m) | histogram of floor points per 5 m bin | **Yes (partial).** `height_valid` vs `axis_valid` in `clustering.py` and the floor-shadow/bed range logic in `track.py` | none new | trivial | none |
| 2 | Perspective compression before DBSCAN: scale x,y by `start/|z|` beyond start range so a constant eps behaves as an angular radius | same function | equals a range-growing neighbour radius | **Yes.** ours is DBSCAN with range-growing radius (`clustering.py`) | none | none | none |
| 3 | Sleeper-comb cold-start of ego speed: density peaks of near-rail points (3.5-15 m) matched across 3 frames by (mass, intensity, shape) | `metro_lidar/cold_starter.py` | periodic near-field texture as landmarks | **No** for sleepers (we use wall/track profile cross-correlation in `egomotion.py`; grep of `resense/` for sleeper hits only fixture-exclusion comments) | speed in a featureless straight tunnel; only the first 3 frames | Low value: tie spacing aliasing at 10 Hz (frame shift 1.3-2.2 m >> tie pitch), shift hard-capped at 1.45 m, hand-set weights 0.1/0.45/0.45 | none (no accuracy numbers) |
| 4 | Own-cabin extent from first frame: max range of corridor points + 0.4 m becomes the near crop | `tracker_v2.py:_calibrate_ego_vehicle_cabin` | self-calibrated blind zone | **Yes** (min range / own-train crop in `frame.py`/config) | none | n/a | none |

No further candidates. Anything else is either ours already or harmful (see below).

## Things done worse than ReSense / red flags
- Hard-coded geometry: floor Y clamp [-1.80,-1.35], rail corridor y in [-1.85,-1.05], x +-0.75, half-width 1.35-1.40 m, axis swaps by recording. Corridor is 2.7-2.8 m wide, so walls/platform edges are removed by a separate "veto filter" rather than by modelling; no calibration, no real rail detection, no wall-based axis extension. It would break on a different mount.
- Station mode widens the corridor to 3.5 m and ceiling to 3.8 m, then deletes boxes with |X|>1.10 m or Y>1.80 m beyond 10 m ("atomic destroy" in README). Deleting is the opposite of our "demote, never delete" rule.
- Intensity gate `MAX_TARGET_INTENSITY = 65000` can never fire (our sensor intensities are 0-255-scale). It is advertised as a feature.
- ICP odometry on the rail corridor is degenerate along the track and is initialised with the predicted shift, so the output largely echoes the prior; the fusion falls back to "inertia" when sources disagree. No speed-vs-truth comparison anywhere.
- Report fabrication-like claims: "322 hazards in doubleT_obstacle = people on the platform at 2.50-2.64 m" (that is the own train / platform near the lidar, min control range is 3.0 m, and the real object at ~56 m is never mentioned); "doubleT_platform 0 -> 2, squareT_switch 0 -> 6, roundT_doubleT 18 -> 15 detections = clairvoyance on hidden targets", but those recordings are empty (all detections are false alarms).
- Report-only-after-8-consecutive-hits quarantine plus 3D centroid gate of up to 7.5 m would lose far/small objects at speed; no recall measurement exists. `dimensions` are clamped to >=0.4 m in output, so reported sizes are not measurements.
- Tracker association mixes lateral/height/range in one 3D distance and extrapolates by an odometry that cannot be trusted; no ego-consistency check.
- Dead code: most of `tracker_v2.py`, `unified_object_engine.py`, three commented versions of the gauge function.

## Eval/data tooling worth borrowing
- Nothing. `convert_simple.py`/`convert_all_bags.py` (sqlite3 bag -> .bin with axis permutation) and `inspect_db.py` are trivial equivalents of what `resense/io.py` does. `test_cloud_with_fake_obj.py` only lists topics and checks whether GT/odometry topics exist (none do). There is no scoring script, no labels and no saved result files.
