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
ducts, platforms, pressure gates and switches. Points come from a Hesai Pandar128 with
~190 000 valid returns per frame, instrumented to 200 m on its 64 fine channels
([`DATASET.md`](DATASET.md), [`SENSOR.md`](SENSOR.md)).

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
| bed height `z_floor(X)` | per-bin (2 m, 5 m beyond 40 m) 20th percentile of Z in a ±1 m band around the axis; robust line through the near bins, far bins kept only within 0.35 m of it; a quadratic only if ≥ 4 consistent far bins exist and it bends less than a 1500 m vertical curve; linear extrapolation beyond the fitted range; EMA across frames (`floor_smoothing`) | fitted range + `floor_valid_margin` (60 m), **or as far as the extrapolation is verified** (next row) |
| verified extrapolation `floor_verified` (v0.4, second height anchor) | the bed vanishes beyond ~100 m but the walls, benches and ducts beside the track are seen to the end of the range and their foot runs at a constant height above the rail head. Per 5 m bin the lowest point in the side band \|dy\| 1.6–3.5 m (minus half a ring spacing, since the lowest sample of a vertical face lies up to one ring above its foot) is compared with the extrapolated bed; the offset measured in the near bins where the bed fit is supported is the reference; walking outward, the extrapolation stays verified while the median deviation over the last 30 m of populated bins is within `floor_verify_tolerance` (0.5 m). A vertical curve, a platform or a transition breaks the agreement and the range stops there | `floor_verified`; the corridor is trusted to `max(fit + 60 m, floor_verified)`, so the check only extends the v0.3 range; a longer trusted corridor also promotes advisory clusters there to alarms (21.09, full rate: +7 alarm frames on `roundT_squareT_pressureGate_squareT`, +1 on `roundT_doubleT`) |
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

**Source of the numbers and what is still to verify against GOST 23961-80** ("Метрополитены.
Габариты приближения строений, оборудования и подвижного состава", 1520 mm gauge; the rolling
stock gauge is drawings 6 and 7 of the standard). The text of the standard is online
(files.stroyinf.ru, meganorm.ru, docs.cntd.ru, dnaop.com — checked 21.09), but the profile
dimensions exist only in the drawings, which none of the mirrors transcribes, so the polygon
could **not** be set from the standard and stays as designed on day 1. What the text does give,
and what the profile is consistent with: track gauge 1520 mm, 1600 mm between the wheel
rolling circles, platform edge at 1450–1600 mm from the track axis (table 3, straight track
to curves) at 1100 mm above the rail head — so the half-width at platform height must be
< 1.45 m and our 1.40 m keeps a ≥ 5 cm margin to the platform edge, while the organizer bags
show the edge at ~1.6 m ([`DATASET.md`](DATASET.md)); 137 mm maximum height of the
train-control inductor above the rail head under the car, which is why nothing below 0.12 m
between the rails is looked at. Assumptions to check on the drawings: car body half-width
1.35 m (2.7 m body) + dynamic margin = 1.40 m; the 0.55 m step for the contact-rail zone; the
3.5 m top (the car is ~3.7 m above the rail head, the polygon top only needs to cover what a
train can hit); a platform notch is not modelled. The synthetic benches at 1.95 m and the
tests do not constrain the half-width between 1.40 and 1.5 m.

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
6. **retro-reflector rule** (v0.4, [`SENSOR.md`](SENSOR.md) §3.3: intensity is reflectivity in
   %, values above 100 come only from retro-reflective material — signs, markers, reflective
   tape, rail-head polish). A cluster is demoted to `warning` and flagged `retro` when
   **all three** hold: at least `retro_min_fraction` (50 %) of its returns have intensity ≥
   `retro_intensity` (100); its height is below `retro_max_height` (1.2 m); its lateral width
   is below `retro_max_width` (0.8 m). The size rule is what keeps real objects: a person is
   taller than 1.2 m even in a hi-vis vest (the vest also covers less than half of the returns),
   a train or a trolley is wider than 0.8 m and taller, a large crate is wider. What the rule
   deliberately demotes: plates and posts up to 0.8 × 1.2 m that are retro-reflective over
   most of their surface — signs, kilometre and speed markers, reflectors on the tunnel wall,
   and also a small fully retro-reflective object (a 0.5 m reflective cube is treated as a
   marker; documented, see EXPERIMENTS.md §2b). The visible depth of an object is not used
   (from the front every object is thin). `retro_intensity: 0` switches the rule off;
7. a **visibility score** compares the voxel count with the number of returns a target of that
   width and height should give at that range (`expected_points`); the score saturates at
   `visibility_ratio` = 15 % of the expectation and feeds the tracker's confidence.

When several frames are merged (§3.4) the voxel-count thresholds `min_points`,
`min_points_far` and `gauge_min_points` are raised by `1 + n_merged · min_points_scale`
(×1.5 for 5 frames, `accumulation.min_points_scale` = 0.3) for clusters beyond the
accumulation range, so that merged noise does not pass a single-frame bar. The factor is
deliberately far below ×5: the voxel grid (5 cm in range-normalised space, i.e. 0.3 m at 200 m)
merges returns that land on the same spot, so the union of 5 frames of a small far object holds
only slightly more *voxels* than one frame — 6 voxels for a 0.5 m box at 120 m, 6–12 for a
person at 190 m — and a ×3 factor was measured to lose the box (EXPERIMENTS.md §2b). A
**smear guard** protects against a wrong ego speed: a merged cluster longer than
`accumulation.smear_max_length` (2 m) along the track can only be a static object shifted by the
wrong amount (or a fast-moving one), so it is re-described from its current-frame points with
single-frame thresholds — a wrong speed then degrades to v0.3 behaviour instead of stretching
the object past `max_extent` and losing it.

### 3.4 Ego speed and multi-frame accumulation (`resense/egomotion.py`, `resense/accumulate.py`, section `accumulation`) — v0.4

Beyond ~150 m a person returns 3–5 points per frame and a 0.5 m box 1–3 (DATASET.md), so the
single-frame clusterer hits its `min_samples` = 3 floor unpredictably. The detector therefore
merges the corridor candidates of the last `n_frames` = 5 frames (0.5 s), compensated for the
train's motion, before clustering. Only candidates beyond `min_range` = 40 m are merged: there
the single frame is what limits detection, while a person walking at 5 m from the train must
not be smeared over half a second and is dense enough anyway.

**Ego speed.** `Detector.process(frame, ego_speed=None)` takes the train speed in m/s when the
caller knows it (the ROS node's parameter or odometry topic); a given speed always wins and is
reported as `ego_speed_source = "given"` (the estimator is then skipped, saving 7–12 ms per
real frame, so `ego_speed_estimate` is null). Without it the detector estimates the speed from the
LiDAR stream alone (`"estimated"`), or declares it unknown (`"none"`), in which case **nothing is
merged**: a wrong shift smears, and the v0.3 single-frame pipeline is the safe fallback. On real
data a *stopped* train is not "unknown": the tracks cue (≥ 3 persistent static tracks with
≈ 0 velocity) reports 0 m/s with confidence 0.6 and 5 frames are merged at v = 0, which smears
a person walking across the track laterally (`doubleT_obstacle`, 21.09: width 1.06 m vs 0.57 m
single-frame; distance unaffected). A lateral smear guard is pending (EXPERIMENTS.md §2b). ICP
would be the textbook estimator, but a straight tunnel is translation-invariant along its axis
and ICP is degenerate in exactly that direction ([`RESEARCH.md`](RESEARCH.md) §2). What is
observable is the *texture* of the walls along the track — brackets, cable hangers, lamps,
signs, cabinets, niches, column edges at irregular positions — which slides towards the
sensor by `v · dt` per frame:

* per side, a histogram of returns over X in 0.1 m bins between 4 and 25 m, restricted to
  1.3–3.0 m above the rail head (vertical surfaces only: the bed, the walkway tops and platforms
  are sampled in ring stripes that are fixed in the sensor frame and would vote for "no
  motion"); normalised by a running 2 m mean (density falls with range), clipped, zero-mean;
* a temporal background (EMA over frames, weight 0.7) of that profile is subtracted: even a
  smooth lining leaves a faint pattern of where the ring/column grid lands, fixed in the sensor
  frame, and in a featureless tunnel a moving and a stopped train produce the same data — so
  whatever does not move is discarded and a featureless stretch yields "unknown" rather than a
  confident 0 m/s (which was the first version's failure, EXPERIMENTS.md §2b). The estimator
  reports nothing during the first `speed_warmup_frames` = 3 frames;
* normalised cross-correlation between the previous and the current residual profile over
  lags 0 … `speed_max` (30 m/s) × dt, the peak refined to sub-bin accuracy by a parabola;
  `speed = lag / dt`. Confidence = peak correlation × prominence over the best peak more than
  0.3 m away (periodic texture — sleepers, ring joints — gives competing peaks and honestly low
  confidence), halved when the value jumps by more than `speed_max_step` = 3 m/s from the
  previous estimate. Below `speed_min_confidence` = 0.5 the estimate is not used;
* a second cue cross-checks the first: the median along-track velocity of persistent tracks
  (≥ 3 hits; static infrastructure approaches at the ego speed). Disagreement by more than
  max(1.5 m/s, 15 %) halves the confidence; three or more consistent tracks replace a silent
  profile cue with confidence 0.6.

The frame interval `dt` is the header-stamp difference when it is sane
(`stamp_dt_range` = 0.02–0.5 s), else `tracking.frame_dt`.

**Accumulation.** The candidates beyond 40 m of each frame are stored in *track coordinates*
(X along the axis, dy from the axis, h above the rail head — these follow the curve, because
the track model re-estimates yaw and curvature every frame) with their intensity and strict-gauge
flag. Each new frame shifts every stored point by `v · dt` towards the vehicle, re-embeds the
union into the current vehicle frame with the current track model (`y = y_c(X) + dy`,
`z = z_rail(X) + h`) and hands it to the clusterer together with the current frame's
candidates, marked so that only current-frame points enter `points_idx`. The voxel grid merges
returns from different frames that land on the same spot, so a static near object is denser,
not double-counted (a person at 60 m: 55 voxels from 5 frames vs 56 from one). The result
reports `n_accumulated` (1 when accumulation is off, unknown speed, or the first frame). The
per-frame cost is bounded: only a few thousand far candidates per frame are stored
(`max_points_per_frame` = 20 000 cap), the clusterer never sees the full frame.

### 3.5 Temporal persistence (`resense/tracking.py`, section `tracking`)

Clusters are associated frame to frame by greedy nearest neighbour on predicted centroids
(constant velocity per track). The gate is `gate_base + gate_per_m · distance`
(1.5 m + 2 cm/m), widened along X by `ego_speed_max · frame_dt` (25 m/s × 0.1 s = 2.5 m)
towards the vehicle, because without odometry a static obstacle approaches at the train's speed.
When the ego speed is known, a track seen only once (no velocity yet) is predicted as a static
object approaching by `v · dt`. Confidence rises by `conf_gain · score` per hit and falls by
`conf_decay` per miss; a track is dropped after `max_misses` = 3. The zone of a track is the
majority zone of its last 5 hits — an object first seen beyond the trusted corridor is advisory
for its first frames and needs 2–3 frames inside the corridor before the majority flips.
Accumulation changes what the tracker sees (denser clusters), not the persistence semantics:
`confirm_hits` frames are still needed.

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
status JSON. Since v0.4 it also carries `ego_speed` (the value used, or null),
`ego_speed_source` (`given` / `estimated` / `none`), `n_accumulated`, and for diagnostics
`ego_speed_estimate` / `ego_speed_confidence` (the estimator's own opinion, also when a speed
is given) and `track.floor_verified`; all existing keys are unchanged.

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
| `track.floor_verify_tolerance`, `track.floor_verify_band` | 0.5 m, \|dy\| 1.6–3.5 m | how far the bed extrapolation is trusted beyond the fit: looser = longer corridor, more phantom objects where the bed bends |
| `cluster.retro_intensity`, `retro_max_height`, `retro_max_width` | 100, 1.2 m, 0.8 m | which bright clusters are signs (advisory) rather than obstacles; 0 disables the rule |
| `accumulation.enabled`, `n_frames`, `min_range` | true, 5, 40 m | how many frames are merged beyond which range; off = v0.3 single-frame behaviour |
| `accumulation.min_points_scale`, `smear_max_length` | 0.3, 2 m | noise bar of merged clusters; length beyond which a merged cluster is taken as smeared |
| `accumulation.speed_min_confidence` | 0.5 | how sure the ego-speed estimate must be before frames are merged without a given speed |

## 6. Limitations (v0.4)

1. **Curvature is only known where walls or column rows are visible.** Stations, switch caverns
   and tunnel-type transitions (walls diverge) weaken the estimate; detections there are demoted
   to warnings and remain noisy. The platform-and-switch bag holds 49 of the 67 residual
   false-alarm frames (v0.3 numbers; v0.4 has not been run on the bags yet). The bed-trough
   axis as a second opinion is designed, not implemented (EXPERIMENTS.md §5).
2. **Height reference beyond ~80 m** is still a linear extrapolation of the bed; v0.4 only
   *verifies* it against the side-structure base and trusts the corridor as far as they agree
   (±0.5 m — a vertical curve of 1500 m is caught ~60 m beyond the fit, i.e. at ~1 m error).
   It does not correct the bed, so a platform, a transition or a vertical curve still ends the
   trusted corridor there.
3. **Accumulation multiplies returns, not resolution.** A distant object is sampled by the same
   rings and columns frame after frame (the pattern moves ≈ 2 cm per frame on the object), so
   the merged cluster is denser but not larger: a 0.5 m box beyond ~118 m is one ring high and
   fails the 8 cm flatness rule with or without accumulation. The Sprint 2 ranges hold on the
   synthetic tunnel (person 189–191 m, box 114–116 m); on the bags they are unmeasured.
4. **Ego speed without odometry depends on wall texture.** In a featureless stretch the
   estimator says "unknown" and the detector falls back to single frames; whether real tunnels
   carry enough texture for the profile cue is unmeasured. A given speed (parameter or
   odometry) is the reliable path; a wrong given speed is caught by the smear guard at the
   cost of the accumulation gain.
5. **Objects lower than 35 cm on the sleepers are filtered by design** (the low-hardware rule);
   a plank lying on the sleepers is invisible whatever its reflectivity.
6. **Retro-reflective small objects are advisory by design** (a reflective 0.5 m cube reads as
   a marker); a person, a train, a trolley or a crate keep their zone.
7. **Filters are hand-tuned on six bags**; the extended dataset is needed to calibrate them and
   to measure real recall.
8. **Pure Python**: 40–75 ms per frame on 4 cores for v0.3 on real frames; v0.4 adds ≈ 5 ms on
   the synthetic frame (profile 3 ms, verification 1.5 ms, accumulation < 1 ms) but +17–23 ms
   mean on real frames (estimator 7–11 ms, now skipped when a speed is given; bed verification
   5–7 ms; clustering of the merged cloud +8 ms), with p95 above the 100 ms period on the moving
   bags on the 4-core sandbox (21.09, EXPERIMENTS.md §2b) — to be
   re-measured on real frames and on the i7-9700E (Numba/C++ fallback planned).
9. **No semantics**: a legitimately parked train, a maintenance trolley or a worker on the track
   are all "obstacles", which is the intended behaviour for a safety function.
