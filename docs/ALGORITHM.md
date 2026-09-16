# Algorithm

Structured after spec §5 ("description of the algorithm"): problem → input data → point-cloud
processing → decision rule → parameters → limitations. The code path is
`resense.Detector.process()` (`resense/detector.py`); each stage below names its module and
its parameter section in `configs/default.yaml`. Component diagram and topics:
[`ARCHITECTURE.md`](ARCHITECTURE.md). Numbers: [`EXPERIMENTS.md`](EXPERIMENTS.md).

## 1. Problem

A driverless metro train has a forward-looking 3D LiDAR. Ten times a second the system must
answer: **is there a foreign object inside the space the train is about to sweep, and how far
ahead is it?** The object classes are unknown (a person, a box, a plank, a trolley, a fallen
sign); the environment is known: a tunnel with two rails, a track bed, walls, columns, cable
ducts, platforms, pressure gates and switches. Points come from a Hesai-class sensor with
~190 000 valid returns per frame, usable to ~200 m ([`DATASET.md`](DATASET.md)).

We therefore model the *environment*, not the objects (spec §8.4): anything inside the
clearance gauge that is not track, bed or known infrastructure is reported, whatever it looks
like. No training data and no object classes are required.

## 2. Input and coordinate frames

* `sensor_msgs/PointCloud2` on `/lidar_points`, fields `x y z intensity ring timestamp`,
  `frame_id = hesai_lidar`, dual-return layout with empty `(0,0,0)` slots.
* Decoding (`resense/pointcloud.py`) is zero-copy into a structured numpy array; empty slots
  and returns closer than `sensor.min_range` (2.5 m, the train's own nose) or beyond
  `sensor.max_range` (250 m) are dropped.
* The sensor frame is mapped onto the **vehicle frame** X forward, Y left, Z up by three axis
  strings (`sensor.forward/left/up`, default `-y/+x/+z` for the hackathon mount). Everything
  downstream is in the vehicle frame; the ROS node maps detections back to the sensor frame for
  RViz.

No calibration of sensor height, pitch or lateral position is needed: the track model below
re-estimates them every frame.

## 3. Processing pipeline

### 3.1 Track model (`resense/track.py`, section `track`)

Three quantities describe the track ahead as functions of the along-track coordinate X:

| quantity | how it is estimated | range it is trusted |
|---|---|---|
| bed height `z_floor(X)` | per-bin (2 m, 5 m beyond 40 m) 20th percentile of Z in a ±1 m band around the axis; robust line through the near bins, far bins kept only within 0.35 m of it; a quadratic only if ≥ 4 consistent far bins exist and it bends less than a 1500 m vertical curve; linear extrapolation beyond the fitted range; EMA across frames (`floor_smoothing`) | fitted range + `floor_valid_margin` (60 m) |
| rail-head level and lateral axis `center` | lateral height profile at 4–30 m in 5 cm bins (85th percentile per bin); the two rail ridges are found as a pair of local maxima `rails_spacing` = 1.59 m apart with a plausible head height (0.08–0.5 m above bed); the midpoint is the axis, the mean ridge height the rail head; EMA `rails_smoothing` | 4–30 m, then extended by the yaw/curvature model |
| yaw and curvature of the axis | per 4 m bin between 6 and 160 m, in a height band 1.6–2.8 m above the rail head (above platforms, below the roof), the boundary of each side is the 90th percentile of \|dy\|; a robust quadratic per side gives `tan(yaw)` and curvature; if the two sides disagree, the **nearer** boundary wins (near structures are constrained to be parallel to the track, far walls are not); clipped to \|yaw\| ≤ 2° and R ≥ 150 m; EMA `walls_smoothing` | `axis_valid` = last observed boundary bin + 15 m (+50 m when straight and well fitted); shrinks by 20 m per frame without a fit |

The axis is `y_c(X) = center + tan(yaw)·X + ½·curvature·X²`; the rail head is
`z_rail(X) = z_floor(X) + rail_offset`. Every later stage uses the *corridor coordinates*
`dy = y − y_c(X)` and `h = z − z_rail(X)`.

### 3.2 Clearance-gauge corridor (`resense/gauge.py`, section `gauge`)

The gauge is a closed polygon in `(dy, h)`, i.e. a cross-section swept along the axis:
half-width 1.40 m from 0.55 m above the rail head (above the contact-rail cover) to 3.50 m, plus
a lower zone \|dy\| ≤ 0.95 m from 0.12 m up (between the rails). A second, **advisory** polygon
is the same profile widened by `warning_margin` = 0.35 m on the outside only.

Points between `range_min` (3 m) and `range_max` (250 m) are tested against both polygons
with a vectorised even-odd test. Points inside the advisory polygon are the *candidates*;
membership in the strict polygon is remembered per point.

### 3.3 Candidate clustering and infrastructure filters (`resense/clustering.py`, section `cluster`)

Everything is **range-adaptive**, because a 0.5 m object gives ~500 returns at 20 m and ~7 at
100 m (`resense/sensor.py`):

1. coordinates are scaled by `1 / (1 + r / range_scale)` with `range_scale` = 40 m, so a fixed
   voxel (`voxel` = 5 cm) and a fixed DBSCAN radius (`eps` = 0.35 m) grow linearly with range:
   `eps(r) = 0.35·(1 + r/40)`;
2. candidates are voxel-downsampled in that space (merges dual returns; the voxel count is a
   proxy for distinct rays) and clustered with DBSCAN (`min_samples` = 3);
3. each cluster gets a bounding box, along-track distance of its nearest point, lateral offset
   of its centroid, lowest and highest point above the rail head and mean intensity;
4. clusters that describe infrastructure rather than obstacles are removed, in this order:

| filter | rule (defaults) | what it removes |
|---|---|---|
| size | extent > 8 m or height < 0.08 m | walls, floor noise |
| point count | < 5 voxels (< 3 beyond 100 m) | noise |
| thin linear | length > 3 m, width < 0.35 m, height < 0.25 m | rails, pipes, cables, duct edges |
| low hardware | top < 0.35 m, width < 0.4 m, height < 0.3 m | clamps, joint bars, cables on the sleepers |
| wall-like | height > 1.9 m and \|lateral\| > 1.2 m, or height > 1.9 m, length > 4 m, width < 1.5 m | columns, gate frames, platform walls, wall segments pulled in by a bad axis |
| linear side structure | aspect > 5, height < 0.8 m, \|lateral\| > 0.8 m | platform edges, ducts, cabinet rows |

5. the surviving cluster is assigned a **zone**: `gauge` if ≥ `gauge_min_points` (3) voxels lie
   inside the strict polygon, otherwise `warning`; it is demoted to `warning` when it lies beyond
   `axis_valid` (the corridor is not trusted there) or entirely above `overhead_min_height`
   (2.4 m: cables, lamps);
6. a **visibility score** compares the voxel count with the number of returns a target of that
   width and height should give at that range (`expected_points`); the score saturates at
   `visibility_ratio` = 15 % of the expectation and feeds the tracker's confidence.

### 3.4 Temporal persistence (`resense/tracking.py`, section `tracking`)

Clusters are associated frame to frame by greedy nearest neighbour on predicted centroids
(constant velocity per track). The gate is `gate_base + gate_per_m · distance`
(1.5 m + 2 cm/m), widened along X by `ego_speed_max · frame_dt` (25 m/s × 0.1 s = 2.5 m)
towards the vehicle, because without odometry a static obstacle approaches at the train's speed.
Confidence rises by `conf_gain · score` per hit and falls by `conf_decay` per miss; a track is
dropped after `max_misses` = 3. The zone of a track is the majority zone of its last 5 hits.

## 4. Decision rule

A frame reports `obstacle = true` when at least one track is **confirmed**:

* seen in ≥ `confirm_hits` = 3 consecutive frames (0.3 s at 10 Hz),
* confidence ≥ `conf_threshold` = 0.6,
* matched in the current frame (no miss),
* zone = `gauge`.

`nearest_distance` is the along-track distance of the nearest confirmed gauge track (m from
the sensor, measured to the object's nearest point). Confirmed tracks in the advisory zone set
`warning = true` but not `obstacle`. Outputs and their ROS topics are listed in
[`ARCHITECTURE.md`](ARCHITECTURE.md); the full per-frame result (all confirmed tracks with
distance, lateral offset, size, confidence, age, the track model and per-stage timing) is the
status JSON.

Cost of the rule: three frames of latency (0.3 s, 6.7 m at 80 km/h) in exchange for
suppressing single-frame noise. Persistence is applied before the alarm, not after, so the
first alarm is already a confirmed object.

## 5. Parameters that matter most

All parameters live in one file, `configs/default.yaml` (`resense:` root key), loaded by both
the CLI and the ROS node. The ones that change behaviour visibly:

| parameter | default | effect |
|---|---|---|
| `sensor.forward/left/up` | `-y/+x/+z` | sensor → vehicle axes; wrong values break everything |
| `gauge.profile`, `gauge.warning_margin` | ±1.40 m, 0.12/0.55–3.5 m; 0.35 m | what counts as "in the way"; widen for safety, narrow to cut platform-edge false alarms |
| `gauge.range_max` | 250 m | how far the corridor is evaluated |
| `track.walls_*`, `track.axis_valid_margin` | band 1.6–2.8 m, +15 m | how far the curved corridor is trusted; beyond it only warnings |
| `cluster.eps`, `cluster.range_scale`, `cluster.voxel` | 0.35 m, 40 m, 5 cm | cluster granularity vs range |
| `cluster.min_points`, `cluster.min_points_far`, `cluster.far_range` | 5, 3, 100 m | sensitivity at range vs noise |
| `cluster.hardware_*`, `cluster.thin_*`, `cluster.wall_*`, `cluster.linear_*` | see table above | infrastructure suppression; the `hardware` rule also hides objects below 35 cm on the sleepers |
| `cluster.overhead_min_height` | 2.4 m | overhead fixtures are advisory only |
| `tracking.confirm_hits`, `tracking.conf_threshold` | 3, 0.6 | latency vs false alarms |
| `tracking.ego_speed_max` | 25 m/s | association slack without odometry |

## 6. Limitations (v0)

1. **Curvature is only known where walls or column rows are visible.** Stations, switch caverns
   and tunnel-type transitions (walls diverge) weaken the estimate; detections there are demoted
   to warnings and remain noisy. The platform-and-switch bag holds 49 of the 67 residual
   false-alarm frames.
2. **Height reference beyond ~80 m** is a linear extrapolation of the bed; where the bed is
   hidden it drifts by 1–2 m at 120 m, producing phantom overhead objects or hiding low ones.
3. **Single-frame evidence beyond ~150 m is 1–5 points.** The physical point budget
   (0.5 m object ≈ 7 returns at 100 m, 1.6 at 200 m) means 150–300 m needs multi-frame
   accumulation with ego-motion, which v0 does not have; the tracker only widens its gate.
4. **Objects lower than 35 cm on the sleepers are filtered by design** (the low-hardware rule).
5. **Filters are hand-tuned on six bags**; the extended dataset is needed to calibrate them and
   to measure real recall.
6. **Pure Python**: 40–75 ms per frame on 4 cores, so a 10 Hz stream is processed in real time
   with limited headroom; accumulation may double the cost (Numba/C++ fallback planned).
7. **No semantics**: a legitimately parked train, a maintenance trolley or a worker on the track
   are all "obstacles", which is the intended behaviour for a safety function.
