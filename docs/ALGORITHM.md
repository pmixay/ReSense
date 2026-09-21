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

* `sensor_msgs/PointCloud2` on `/lidar_points` (`frame_id = hesai_lidar`) in five of the six
  organizer bags and on `/sensing/lidar/hesai128/pointcloud` (`frame_id = lidar_livox`, full-turn
  recording) in `doubleT_obstacle`; fields `x y z intensity ring timestamp`, dual-return layout
  with empty `(0,0,0)` slots. The node subscribes to both names and auto-discovers any other
  PointCloud2 topic; the frame id is bridged to `resense_lidar` by a static transform.
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
| bed height `z_floor(X)` | per-bin (2 m, 5 m beyond 40 m) 20th percentile of Z in a ±1 m band around the axis; robust line through the near bins, far bins kept only within 0.35 m of it; a quadratic only if ≥ 4 consistent far bins exist and it bends less than a 1500 m vertical curve; linear extrapolation beyond the fitted range; EMA across frames (`floor_smoothing`) | fitted range + `floor_valid_margin` (20 m since v0.5, 60 m in v0.3), **or as far as the extrapolation is verified** (next row) |
| verified extrapolation `floor_verified` (v0.4, second height anchor) | the bed vanishes beyond ~100 m but the walls, benches and ducts beside the track are seen to the end of the range and their foot runs at a constant height above the rail head. Per 5 m bin the lowest point in the side band \|dy\| 1.6–3.5 m (minus half a ring spacing, since the lowest sample of a vertical face lies up to one ring above its foot) is compared with the extrapolated bed; the offset measured in the near bins where the bed fit is supported is the reference; walking outward, the extrapolation stays verified while the median deviation over the last 30 m of populated bins is within `floor_verify_tolerance` (0.5 m). A vertical curve, a platform or a transition breaks the agreement and the range stops there | `floor_verified`; the corridor is trusted to `max(fit + 20 m, floor_verified)` (v0.4: fit + 60 m, which on its own promoted advisory clusters at 135–142 m to alarms on `roundT_squareT_pressureGate_squareT`); on the six bags the verification reaches 105–145 m (p10–p90 of the per-frame value, v0.4 full-rate runs) against bed fits ending at 50–110 m |
| rail-head level, lateral axis `center` and **yaw** (v0.5) | lateral height profile at 4–30 m in 5 cm bins (85th percentile per bin), built in the lateral coordinate of the previous axis (its yaw and curvature removed, so that in a curve the rails are straight lines in the profile — in absolute Y they smeared by up to 0.6 m and the centre was off by 0.9 m on a hand-made R = 800 m scene); the two rail ridges are found as a pair of local maxima `rails_spacing` = 1.59 m apart with a plausible head height (0.08–0.5 m above bed). The pair is then located again in `rails_yaw_slabs` = 3 along-track slabs; a line through the slab midpoints (the previous curvature held fixed) gives the axis at X = 0 and its tangent `tan(yaw)`: the rails are the sharpest parallel reference there is (±2 cm per ridge over a 26 m baseline ≈ 0.1°). EMA `rails_smoothing` | 4–30 m, then extended by the curvature |
| curvature of the axis (yaw only when the rails give none) | per 4 m bin between 6 and 160 m, in a height band 1.6–2.8 m above the rail head (above platforms, below the roof), the boundary of each side is the 90th percentile of \|dy\|; a robust quadratic per side **with the tangent fixed by the rails** gives the curvature 1/R (v0.3 stored the quadratic coefficient 1/2R as the curvature and applied it as 1/R: the axis bent half as much as the tunnel, 2.4 m off at 100 m on R = 800 m; and its free quadratic traded yaw against curvature — the yaw was 0.8–1.0° off the rail direction on curve frames of the organizer bags and saturated at the ±2° clip in every moving bag). A boundary that cannot be fitted with that tangent (a diverging tunnel, a platform hall wall) is rejected instead of bending the axis; if both sides fit but disagree by more than `axis_sides_max_disagreement` (R 1500 m), the **nearer** boundary wins (near structures are constrained to be parallel to the track, far walls are not). Clipped to \|tan yaw\| ≤ 0.06 and R ≥ 150 m; EMA `walls_smoothing`; yaw and curvature are **rate-limited** to `axis_max_yaw_rate` = 0.17° and `axis_max_curvature_rate` = 1e-4 m⁻¹ per frame (a train at 15 m/s on R = 700 m yaws 0.12° per frame; the v0.3 estimate jumped by 0.5–1.2° between frames on the moving bags, i.e. ±0.5 m at 55 m) | `axis_valid` = last observed boundary bin + 15 m; +50 m only when straight, well fitted and both sides agree; capped at `axis_one_side_range` = 120 m with one boundary and at `axis_disagree_range` = 60 m when the two disagree; shrinks by 20 m per frame without a fit |

The axis is `y_c(X) = center + tan(yaw)·X + ½·curvature·X²`; the rail head is
`z_rail(X) = z_floor(X) + rail_offset`. Every later stage uses the *corridor coordinates*
`dy = y − y_c(X)` and `h = z − z_rail(X)`. The height reference is trusted to
`max(fit end + floor_valid_margin, floor_verified)`; v0.5 cuts `floor_valid_margin` from 60 to
20 m because on the platform bags the extrapolated bed was 0.3–0.65 m off at 85–105 m
(`squareT_platform_squareT_switch` frames 400–650: run model −1.69 m vs bed −2.34 m at 85 m),
which pulled the roof (h ≈ 4 m) into the polygon top and the far rails into its bottom
(EXPERIMENTS.md §1b: 503 of the 1001 v0.3 false-alarm frames lay beyond the fit + 20 m); the
verification of §3.1 is what extends the corridor beyond that, where the side structures
confirm the extrapolation.

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
with a vectorised even-odd test (after a bounding-box prefilter, v0.5: the polygon test on the
few thousand points inside the box instead of the whole frame). Points inside the advisory
polygon are the *candidates*; membership in the strict polygon is remembered per point. An
optional **edge margin** (`gauge.edge_margin` + `edge_margin_per_100m` × X/100, v0.5, 0 by
default) counts a point as inside the strict gauge only when it lies that far inside the
polygon's lateral edge: the axis is uncertain by ~0.1° (0.1 m per 60 m), so a return a few
centimetres inside the edge at range is not evidence of an object in the gauge; the
candidates and the advisory zone are unaffected. Its measured effect (side structures at
\|dy\| 1.5–1.6 m vs the crossing person) is in EXPERIMENTS.md §1b.

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
5b. **infrastructure signatures** (v0.5, measured on the six organizer bags at full rate,
   EXPERIMENTS.md §1b; each demotes a gauge cluster to `warning` and records its name in the
   status JSON as `detections[].reason` / `warnings[].reason`; a value of 0 switches a rule off):

   | signature | rule (defaults) | what it is on the bags | why no listed object matches |
   |---|---|---|---|
   | `column` | height > 2.2 m and width < 1.0 m | columns of the double-track tunnel, posts, gate legs pulled in by the axis (`roundT_doubleT` frames 114–251: 94 v0.3 alarm frames) | a person is 1.7 m; a train or trolley is wider |
   | `elevated` | lowest point > 1.2 m above the rail head and width > 2.0 m | roof strips and beams across the tunnel read 0.3–0.65 m too low by the extrapolated bed (`squareT_platform_squareT_switch` 104–130 m: 356 frames) | every listed object stands on the bed; a train ahead reaches the polygon bottom |
   | `floating` | lowest point > 0.7 m, height < 1.5 m, width < 1.0 m | signs, lamps and brackets on the wall (`doubleT_platform` 46–73 m: 109 frames) | an object on the track touches the ground; a person cut by the 0.55 m polygon step has its lowest point *at* 0.55 m |
   | `edge` | \|lateral\| > 1.2 m, length > 2.5 × width, height < 1.0 m | duct / bench / platform-edge fragments along the corridor edge (`roundT_pressureGate_roundT` 3–35 m: 90 frames) | the spec's plank is filtered by the hardware rule anyway; boxes and persons are not elongated |
   | `wall_face` | height > 1.5 m, top above 2.4 m, and the part below 2.4 m has \|dy\| ≥ 0.3 m everywhere and > 1.6 m somewhere | the platform-hall end wall / portal jamb at 72–78 m of the stopped train (206 frames) | a train ahead fills the corridor centre (\|dy\| ≈ 0 below 2.4 m); a person is lower than 2.4 m |

   The rules never drop a cluster: it stays an advisory warning with its reason, and a
   persistent object that stops matching a signature (a person stepping away from a column)
   flips back to `gauge` through the tracker's zone history (§3.5);
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
`accumulation.smear_max_length` (2 m) along the track — or, since v0.5, wider than
`smear_max_width` (1 m) across it (a person walking across the track, merged over 0.5 s) —
can only be a static object shifted by the wrong amount or a moving one, so it is re-described
from its current-frame points with single-frame thresholds — a wrong speed then degrades to
v0.3 behaviour instead of stretching the object past `max_extent` and losing it.

### 3.4 Ego speed and multi-frame accumulation (`resense/egomotion.py`, `resense/accumulate.py`, section `accumulation`) — v0.4

Beyond ~150 m a person returns 3–5 points per frame and a 0.5 m box 1–3 (DATASET.md), so the
single-frame clusterer hits its `min_samples` = 3 floor unpredictably. The detector therefore
merges the corridor candidates of the last `n_frames` = 5 frames (0.5 s), compensated for the
train's motion, before clustering. **Default since v0.5: the merge runs only with a speed the
caller gives** (`ego_speed_mps` parameter or odometry in the node, the rows' speed in `eval`
sequences); the LiDAR-only estimator is off (`estimate_speed: false`) because its
estimated-speed merging added 31 false-alarm frames on the five empty bags at full rate (119
vs 88) without a real-data recall gain and costs 7–8 ms per frame (EXPERIMENTS.md §1b). Without
a given speed the pipeline is single-frame. Only candidates beyond `min_range` = 40 m are merged: there
the single frame is what limits detection, while a person walking at 5 m from the train must
not be smeared over half a second and is dense enough anyway.

**Ego speed.** `Detector.process(frame, ego_speed=None)` takes the train speed in m/s when the
caller knows it (the ROS node's parameter or odometry topic); a given speed always wins and is
reported as `ego_speed_source = "given"` (the estimator is then skipped, saving 7–12 ms per
real frame, so `ego_speed_estimate` is null). Without it the detector estimates the speed from the
LiDAR stream alone (`"estimated"`), or declares it unknown (`"none"`), in which case **nothing is
merged**: a wrong shift smears, and the v0.3 single-frame pipeline is the safe fallback. Below
`accumulation.min_speed` (1 m/s, given or estimated) nothing is merged either (v0.5): a stopped
train gains no density from identical frames (the union lands on the same voxels) but loses
marginal objects to the scaled count thresholds, and in v0.4 the tracks cue (≥ 3 persistent
static tracks with ≈ 0 velocity) reported 0 m/s with confidence 0.6 on the stationary
`doubleT_obstacle` and merged 5 frames at v = 0, which smeared the person walking across the
track laterally (width 1.06 m vs 0.57 m single-frame). The tracks cue now reports nothing below
`tracks_min_speed` (1 m/s) and the smear guard also acts across the track (§3.3). ICP
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
`conf_decay` per miss; a track is dropped after `max_misses` = 3.

Persistence is measured in **time** since v0.5: besides `confirm_hits` = 3 hits a track must
have been observed for `confirm_time_s` = 0.3 s of sensor time (frames × the measured frame
interval, the first frame included — 3 frames at 10 Hz, the v0.3 persistence, and still 3
frames when the node runs at a lower rate; 0.5 s would be 5 frames, measured in EXPERIMENTS.md
§1b), it must have been matched in `min_hit_fraction` = 60 % of its last `hit_window` = 10
frames (a structure that flickers into the corridor every other frame is never reported), and
it must be matched now. The zone of a track is decided over its last `zone_window` = 10 hits:
`gauge` when `zone_min_fraction` = 60 % of them were inside the strict polygon (v0.3: the
majority of the last 5) — an object first seen beyond the trusted corridor, or a corridor-edge
structure whose gauge membership flickers with the axis, is advisory until the history is
clear. Accumulation changes what the tracker sees (denser clusters), not the persistence
semantics.

## 4. Decision rule

A frame reports `obstacle = true` when at least one track is **confirmed**:

* seen in ≥ `confirm_hits` = 3 frames and observed for ≥ `confirm_time_s` = 0.3 s (3 frames
  at 10 Hz), matched in ≥ 60 % of its last 10 frames,
* confidence ≥ `conf_threshold` = 0.6,
* matched in the current frame (no miss),
* zone = `gauge`: ≥ 60 % of its last 10 hits had ≥ `gauge_min_points` voxels inside the strict
  polygon and matched none of the infrastructure signatures of §3.3 (column, elevated,
  floating, edge, wall face), were within `axis_valid` and the trusted height-reference range,
  and were not entirely overhead or retro-reflective.

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
suppressing single-frame noise; `confirm_time_s: 0.5` would make it five frames (0.5 s,
11 m at 80 km/h). Persistence is applied before the alarm, not after, so the first alarm is
already a confirmed object. On `doubleT_obstacle` the person enters the strict gauge at frame 2
and is reported from frame 7 (v0.3: frame 9; the axis no longer jitters, so the zone history
fills faster).

## 5. Parameters that matter most

All parameters live in one file, `configs/default.yaml` (`resense:` root key), loaded by both
the CLI and the ROS node. The ones that change behaviour visibly:

| parameter | default | effect |
|---|---|---|
| `sensor.forward/left/up` | `-y/+x/+z` | sensor → vehicle axes; wrong values break everything |
| `gauge.profile`, `gauge.warning_margin` | ±1.40 m, 0.12/0.55–3.5 m; 0.35 m | what counts as "in the way"; widen for safety, narrow to cut platform-edge false alarms |
| `gauge.range_max` | 250 m | how far the corridor is evaluated |
| `track.walls_*`, `track.axis_valid_margin` | band 1.6–2.8 m, +15 m | how far the curved corridor is trusted; beyond it only warnings |
| `track.rails_yaw_enabled`, `rails_yaw_slabs` | true, 3 | yaw of the axis from the rail pair (off = free quadratic through the walls, the v0.3 way: 0.8–1.0° yaw error on curve frames) |
| `track.axis_max_yaw_rate`, `axis_max_curvature_rate` | 0.003 rad, 1e-4 m⁻¹ per frame | how fast the corridor may swing between frames; 0 = unlimited |
| `track.axis_sides_max_disagreement`, `axis_disagree_range`, `axis_one_side_range` | 6.7e-4 m⁻¹, 60 m, 120 m | trusted range when the two boundaries disagree or only one is seen |
| `track.floor_valid_margin` | 20 m (60 in v0.3) | how far beyond the fitted bed the height reference is trusted without verification |
| `cluster.column_*`, `elevated_*`, `floating_*`, `edge_*`, `wall_face_*` | see §3.3 | infrastructure signatures (advisory only); 0 switches a rule off |
| `gauge.edge_margin`, `edge_margin_per_100m` | 0, 0 | lateral margin inside the polygon edge required for the strict decision (option, EXPERIMENTS.md §1b) |
| `tracking.confirm_time_s`, `min_hit_fraction`, `zone_window`, `zone_min_fraction` | 0.3 s, 0.6, 10, 0.6 | persistence in seconds and over the track's history |
| `accumulation.min_speed`, `tracks_min_speed` | 1 m/s, 1 m/s | no merging and no tracks-cue estimate for a stopped train |
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

## 6. Limitations (v0.5)

1. **The corridor edge is where the remaining false alarms live.** Cable ducts, benches and
   platform-edge fittings run 1.5–1.6 m from the axis; the strict gauge is 1.40 m wide at that
   height, so a 0.1–0.2 m axis error at 40–80 m puts a sliver of them inside. With the rails
   pinning the yaw the near axis is good to a few centimetres, but at 60–80 m the curvature
   from the walls (R ≈ 1000 m in the organizer bags) still leaves ~0.1–0.3 m of uncertainty.
   The edge margin of §3.2 trades those alarms against the last borderline frames of an object
   leaving the gauge; the trade-off is measured in EXPERIMENTS.md §1b and the default keeps
   the polygon exact (margin 0).
2. **Curvature is only known where a boundary parallel to the track is visible.** Stations,
   switch caverns and tunnel-type transitions (walls diverge) leave the curvature to the
   previous frames (it decays towards straight) and the corridor is trusted only to
   60–120 m (`axis_disagree_range`, `axis_one_side_range`); detections beyond are advisory.
   The bed-trough axis as a second opinion is designed, not implemented (EXPERIMENTS.md §5).
3. **Height reference beyond the bed fit.** The bed fit ends at 50–110 m on the bags (median
   ~70–90 m) and its linear extrapolation was 0.3–0.65 m off at 85–105 m in the platform
   bags, which is why roof strips and far rails alarmed in v0.3 (§3.1). v0.5 trusts the
   extrapolation 20 m beyond the fit and as far as the side structures verify it (105–145 m on
   the bags), and demotes wide elevated clusters; it still does not *correct* the bed, so a
   0.5 m box beyond the verified range is advisory, not an alarm, and the far bins of the
   synthetic-on-real sets are limited by the same reference (their objects are placed on the
   extrapolated bed and are often fully occluded by the real one, EXPERIMENTS.md §2c).
4. **Accumulation multiplies returns, not resolution.** A distant object is sampled by the same
   rings and columns frame after frame, so the merged cluster is denser but not larger: a
   0.5 m box beyond ~118 m is one ring high and fails the 8 cm flatness rule with or without
   accumulation. Nothing is merged below 1 m/s (a stopped train) and nothing without a
   trustworthy speed; the measured effect on the real bags and on the injected sets is in
   EXPERIMENTS.md §1 and §2c, and the default is set from those numbers.
5. **Ego speed without odometry depends on wall texture.** The estimator reports a speed on
   40–60 % of the frames of the moving bags and "unknown" on the rest, so accumulation is
   intermittent without a given speed; a given speed (parameter or odometry) is the reliable
   path, and a wrong given speed is caught by the smear guards at the cost of the accumulation
   gain.
6. **Objects lower than 35 cm on the sleepers are filtered by design** (the low-hardware rule);
   a plank lying on the sleepers is invisible whatever its reflectivity.
7. **Tall narrow things and small floating things are advisory by design** (§3.3): a ladder
   standing on the track (> 2.2 m, < 1 m wide) or a sign hanging inside the gauge would be a
   warning, not an alarm; both are infrastructure signatures on the six bags, and the extended
   dataset is the place to revisit them. Retro-reflective small objects are advisory too (a
   reflective 0.5 m cube reads as a marker); a person, a train, a trolley or a crate keep
   their zone.
8. **Filters are hand-tuned on six bags**; every signature threshold was chosen from the
   per-track tables of the v0.3 full-rate runs (EXPERIMENTS.md §1b) and checked on the same
   bags, so the numbers on the hidden bag will be worse than on these. The extended dataset
   is needed to calibrate them and to measure real recall beyond one person at 55 m.
9. **Pure Python**: per-frame cost on the 4-core sandbox is in EXPERIMENTS.md §3 (v0.5 is not
   slower than v0.3 there after vectorising the rail and wall binning); the i7-9700E bench is
   still owed.
10. **No semantics**: a legitimately parked train, a maintenance trolley or a worker on the
    track are all "obstacles", which is the intended behaviour for a safety function.
