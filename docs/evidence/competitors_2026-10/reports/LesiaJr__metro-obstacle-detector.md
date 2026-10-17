# LesiaJr/metro-obstacle-detector

## Verdict
Classical hybrid: a spherical range-image change detector (`src/dynamic_gate.py`) gated by a per-frame 2.1 m wall-based tube (`src/bend_tube.py`, `src/gate_tube.py`). Hackathon prototype, console-only; the only evidence is one printed run on the synthetic `cloud_with_fake_obj_0` (in-sample by construction), with no FP/FN numbers and no empty-tunnel run. Its range-image stage is the model that `docs/RESEARCH.md:53` already rejected.

## Pipeline
1. `src/gate_tube.py:run` reads the .db3 (rosbag2 SequentialReader), PointCloud2 to xyz (`cloud_to_xyz`).
2. Rotates the cloud about z by `--gate-rotate-deg` (README uses 90 for "forward = -Y"). The forward axis is a CLI flag, not estimated.
3. `src/dynamic_gate.py:DynamicGate._points_to_range_image`: 7200 azimuth x 128 elevation bins (0.05 deg by 1.41 deg), per-cell minimum range; forward sector ±45 deg; sensor-frame z in [-1, 2] m.
4. `DynamicGate.process`, ego-motion: median of (prev - current) over cells > 20 m, clipped to [-1, 5] m/frame; 0 if fewer than 200 samples.
5. Per-cell drop = predicted - current. Strong if > 2.5 m; weak in (1.5, 2.5] m, needing >= 3 neighbours in radius 2.
6. N-of-M: a cell is an anomaly if it was a candidate in >= 4 of the last 6 frames. Candidate cells freeze the baseline for up to 3 frames.
7. `src/bend_tube.py:process_one_frame` (only on frames with anomalies): wall columns in Y-slices (|x| <= 40 m, z-span >= 1 m), PCA lines, colinear merge, bend path theta(Y) from the single "longest reliable" wall, extruded to a 2.1 m tube from x = 0.
8. `gate_tube.py` tests anomaly points against `points_in_tube` (train_fwd range, z in [-1, 2]). Note: `bend_tube`'s `~wall_mask & ~safe_mask` exclusion is not applied on this path.
9. Alarm: 5 consecutive frames with >= 1 in-tube anomaly and XY centroid jump <= 8 m (`OBSTACLE_CONFIRM_FRAMES`, `--obstacle-streak`).

## Candidate ideas
| # | idea | where in code | mechanism | have in ReSense? | expected effect: recall / range / FPR | cost & risk | evidence in repo |
|---|---|---|---|---|---|---|---|
| 1 | Spherical range-image, per-cell min, one-frame change detection with ego-compensated baseline | `dynamic_gate.py:DynamicGate.process`, `_points_to_range_image` | Flags cells whose range falls faster than the ego-predicted baseline | no, and rejected: `docs/RESEARCH.md:53` "expected-range image / range-image anomaly model ... fires on cables, signs, wet patches; not built"; brief lists "range-image anomaly" as tried | Unmeasured here. Structure suggests recall for newly visible returns, FPR on cables, poles and wet patches | medium; do not re-propose without new evidence | none quantitative |
| 2 | Ego-speed from median range change of far cells | `dynamic_gate.py:process` (motion block) | Per-frame radial speed without odometry | yes, stronger: `resense/egomotion.py` cue 1 (profile xcorr with confidence; `speed=None` when unsure) | none | none | none |
| 3 | Per-cell baseline freeze (`max_freeze_frames=3`) | `dynamic_gate.py:process` (freeze_counter) | Stops a new return being absorbed into the baseline for 3 frames | no direct analogue (ReSense holds STOP through one missed frame, brief item 5) | As coded, a static return that appears in one step gives at most 3 candidate frames, below N=4, so it is not confirmed. Unverified by running | low | none |
| 4 | Wall-angle bend path with rms, mean-x and rate gates; tube from one side's wall | `bend_tube.py:build_bend_path`, `build_bend_tube` | Tube orientation from tunnel wall angle | yes: `resense/track.py:estimate_axis_from_walls` (Shen-style parallel references, rate-limited, temporal). Missing here: lateral centre (tube starts at x = 0, no offset from walls) | none; ReSense is stronger on curvature and centring | none | none |
| 5 | Floor-to-ceiling wall test (`z_filter='edges'`) | `bend_tube.py:find_columns_in_slice` | A wall column must occupy both lowest and highest z-bins of the slice | partial: `resense/clustering.py:_is_infrastructure` (wall height, linear-aspect rules). Not used here (default is `span`, `gate_tube.py:make_tube_args`) | Could reject low side structures (benches, platform edges) from wall lines. Platform false STOP not measured | low | none |
| 6 | Diagnostics: per-mode accounting (OK/SHORT/FALLBACK/NONE) and drop percentiles | `gate_tube.py:run` (mode_counter), `dynamic_gate.py:process` (debug print) | Tooling, not detection | no equivalent print in ReSense | none | trivial | none |

Only item 6 is worth borrowing as tooling. Items 1 and 3 are already covered by ReSense's rejected range-image idea.

## Things done worse than ReSense / red flags
- Reported range and XY come from `prev_range` (`dynamic_gate.py:anomaly_info`, `anomalies_to_xyz`), i.e. the baseline. For cells still inside the freeze window that is the pre-appearance (background) value, not the measured return. The console ranges (e.g. 56.6-76.5 m in the README) may be biased long. Not checked by running.
- `gate_tube.py` ignores `bend_tube`'s wall and safe-zone exclusion, so any anomaly within 1.05 m of the sensor-centred axis counts. Confirmation is one in-tube point per frame for 5 frames, with no size, height or shape test.
- README and code disagree: README cites `OBSTACLE_N = 4`, `OBSTACLE_M = 6`, `OBSTACLE_MIN_PTS = 1` in `gate_tube.py`; these do not exist. Code uses 5 consecutive frames and `--obstacle-streak`. docker-compose mounts `./bags`, README says `./data`.
- Frame and axis assumptions are hand-set: `--gate-rotate-deg 90`, `forward_sign=-1` and the 1.05 m half width are not estimated; a wrong flag breaks both stages silently. Temporal smoothing of the bend path exists but is off (`bend_temporal_off=True`, `make_tube_args`), so the tube is recomputed per frame.
- Range image is coarse in elevation: 1.41 deg per bin, while ReSense measures ~0.125 deg ring spacing in the ROI (`resense/sensor.py` header), so one cell spans about 10 rings. Azimuth 0.05 deg is finer than the sensor's 0.1 deg step.

## Eval/data tooling worth borrowing
- Per-frame debug line with drop mean/median/p95/p99/max and n_fwd (`dynamic_gate.py:process`): a cheap way to watch ego-compensation bias on real bags. The README sample shows median drop ~ -0.10 m/frame with v_est ~ +0.12 m/frame. The speed matches ReSense's ~1.4 m/s at the start of `cloud_with_fake_obj` (`docs/DATASET.md`), but the residual is not zero-centred: the estimator has no cos(az)cos(el) projection while the predictor does. Cause not established.
- Tube-mode counters per anomalous frame (OK/SHORT/FALLBACK/NONE, anomalies in tube by mode) in `gate_tube.py:run`: useful for separating "tube failed" from "no obstacle".
- `src/db3_inspect.py` lists topics and message counts (trivial; ReSense has an equivalent `resense info`).
