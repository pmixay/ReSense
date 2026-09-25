# Algorithm

> **Purpose:** how ReSense decides that the path ahead is blocked, stage by stage, structured
> after spec §5 "Описание алгоритма": problem → input data → point-cloud processing → decision
> rule → parameters → limitations.
> **Audience:** jury, P3 · **Owner:** P1 (structure), P3 (content) · **Language:** EN, summary RU
> **Last verified:** 2026-09-25 against `8932f3a` (detector v0.6.3, node v0.6.4) · **Status:** current

**Кратко.** ReSense описывает не объекты, а окружение: в каждом кадре лидара заново строится
модель пути (полотно, рельсы, ось с кривизной по стенам), вдоль оси откладывается габарит поезда
организаторов 2,1 × 3,0 м, и препятствием считается всё, что внутри габарита и не похоже на путь
или известную инфраструктуру. Кандидаты кластеризуются с параметрами, растущими с дальностью,
отдельные стадии ищут низкие предметы на рельсах, объект подтверждается за 0,5 с (5 кадров при
10 Гц). Выход — решение GO / CAUTION / STOP / FAULT, расстояние до препятствия, проверенная
свободная дистанция и состояние датчика. Обучающие данные не нужны; параметры — §5, ограничения
(в том числе найденные на объектах организаторов) — §6.

The code path is `resense.Detector.process()` (`resense/detector.py`), one method per stage
(`_fit_track`, `_corridor`, `_low_stage`, `_speed`, `_accumulate`, `_cluster`, `_confirm`); each
stage below names its module and its parameter section in `configs/default.yaml`. Component
diagram and topics: [`ARCHITECTURE.md`](ARCHITECTURE.md). Numbers:
[`EXPERIMENTS.md`](EXPERIMENTS.md).

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
  recording) in `doubleT_obstacle`; fields `x y z intensity ring timestamp`, dual-return layout with
  empty `(0,0,0)` slots. The organizers confirmed (23.09) that the control data may use either
  (topic, frame) pair and that all recordings come from the same LiDAR. The node subscribes to both
  names and auto-discovers any other PointCloud2 topic; it processes one input at a time, switches
  when the active one falls silent, and restarts the detector (scene state and mount calibration)
  for every new recording — a new topic, frame id or a jump of the header stamps
  ([`README.md`](../README.md) "How a bag is processed"). The frame id is bridged to `resense_lidar`
  by a static transform.
* Decoding (`resense/pointcloud.py`) is zero-copy into a structured numpy array; empty slots
  and returns closer than `sensor.min_range` (2.5 m, the train's own nose) or beyond
  `sensor.max_range` (250 m) are dropped.
* The sensor frame is mapped onto the **vehicle frame** X forward, Y left, Z up by three axis
  strings (`sensor.forward/left/up`, default `-y/+x/+z` for the hackathon mount). Everything
  downstream is in the vehicle frame; the ROS node maps detections back to the sensor frame for
  RViz.

The sensor height, the lateral offset and the yaw of the track are re-estimated every frame
by the track model (§3.1). What the per-frame model cannot absorb — a different mount — is
found once from the data (§2b); the organizers confirmed that the LiDAR position is not fixed
between trains and differs even between the provided recordings
([`organizers/QA_session.md`](organizers/QA_session.md) fact 7). On 24.09 they added that the
test recordings use the mounts of the provided ones and that the LiDAR is 1 075 mm above the rail
head on the train's centreline, with no numeric orientation
([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md)). The provided
recordings hold two rigs: the calibration measures 1.12 m above the rail head and −0.02 m lateral
on `roundT_doubleT` (4.5 cm from the answer) and 1.51 m with a +3.0° roll on the older
`doubleT_obstacle` rig [real, 24.09], so it stays on as the safeguard; a known mount can still be
frozen in the configuration (§2b).

### 2b. Mount auto-calibration (`resense/calibration.py`, section `calibration`) — v0.6

`sensor.forward/left/up` (plus the fixed tilt `sensor.roll_deg/pitch_deg/yaw_deg`) map the
sensor onto the vehicle frame; the calibrator checks and corrects that mapping from the data in
the first frames and hands the detector a rotation `R` (`p_processed = R · p_configured`):

1. **orientation** — only if the configured mapping shows no rail pair ahead (or more far returns
   behind than ahead), the 8 axis-aligned proper rotations that keep the spin axis vertical (upright
   or inverted; `keep_up_axis`, all 24 when false) are scored by the rail pair they reveal: two
   ridges 1.59 m apart, 0.08–0.5 m above a bed that lies below the sensor, running along +X, with
   the tunnel visible ahead. A candidate is adopted when it wins on `orientation_votes` = 2 frames
   and the configured mapping never passed, so a platform or a switch (no rails) cannot flip the
   mount. Tested: upside down, `+x` forward (the ROS convention), mounted backwards, `+x` forward
   and rolled 2° — all recovered to < 0.5° on the synthetic tunnel (`tests/test_calibration.py`) and
   to 0.0–0.5° of tilt on re-mounted real frames of three recordings
   ([`EXPERIMENTS.md`](EXPERIMENTS.md) §6). The sideways candidates are off by default: on the
   square tunnel a flat side wall with two cable trays passed for the bed (§6); a sensor really
   mounted on its side must be configured;
2. **roll** from the rail pair: the height difference of the two rail heads over their spacing
   (the gauge is defined in the rail plane, so this is the roll that matters);
3. **pitch** from the slope of the bed fit at the vehicle (the train rides on the track, so the
   bed slope at X = 0 in the sensor frame is the mount pitch whatever the grade);
4. **yaw** from the rail-slab tangent, applied only above `min_yaw_deg` = 3° (the per-frame
   model follows smaller and dynamic yaw; the rails' tangent at the sensor includes the chord
   angle of the car in a curve).

**Two stages for the tilt (v0.6.1).** On a moving train the per-frame roll swings by ±1° with
the cant transitions and the body's lean — over the 20-minute ride the estimate has a median
of −0.1° and a 10–90 % range of −1.0…+0.7° at any curvature — and neighbouring frames see
the same stretch of rail, so the median of 5 consecutive frames (v0.6) was off by up to
1.6–2.2°: eight fresh detectors on the ride froze eight different "mount rolls" (−1.0…+1.6°)
for one sensor, and the drift monitor then flagged half of the ride. Now: a **provisional**
correction from the first `provisional_frames` = 5 observations, applied only for a clearly
tilted rig (`provisional_min_deg` = 2.5°: the ~3° of the `doubleT_obstacle` rig is corrected
after half a second as before); the **final** correction is the median of `frames` = 20
observations taken every `obs_spacing` = 10 frames (20 s; p90 error 0.5° on the ride, max
1.0°), applied above `apply_min_deg` = 0.75° (1.5× that noise; 0.5° until 23.09, when a ride
piece applied a noise-level +0.51° roll and gained 6 false events), then frozen. Between two
spaced observations the frame is not measured (v0.6.2, second review: measuring every frame
cost 10–15 ms per frame for the first 20 s). Tilts above `max_tilt_deg` = 15° are
rejected (configured mapping kept, status `fallback`); without a rail pair in `max_frames` =
400 frames the calibrator gives up (`fallback`). A change re-seeds the track model and clears
the accumulation buffer; the tracker is reset only for a change above 1° (a new orientation),
so the final refinement does not drop confirmed tracks. After freezing, the same measurement
runs every `monitor_period` = 50 frames on the corrected cloud and the **median of the last
`drift_window` = 10 checks** (50 s) above `drift_warn_deg` = 1.5° — a lasting change, a mount
knocked loose, not a curve — is reported in the health status, never silently re-applied. The
result is in the status JSON as `mount` (`status` pending / provisional / ok / identity /
fallback, `orientation`, `roll_deg`, `pitch_deg`, `yaw_deg`, `height`, `lateral`, `drift_deg`,
`message`); the frozen values can be copied into `sensor.roll_deg/pitch_deg/yaw_deg` or given
to the node as the launch arguments `mount_roll_deg/…` and `sensor_forward/left/up`. Real frames
rotated by known mounts (roll 3°, pitch −4°, the four orientation changes) are recovered to
the recorded mount (EXPERIMENTS §6). Cost: one extra rail/bed measurement every 10th frame
during the first ~20 s and every 50th frame afterwards.

The track model is seeded again after the correction; since v0.6 its rate limits
(§3.1) apply only after `track.axis_warmup_frames` = 5 frames, so a wrong first-frame
estimate (a cold start mid-ride) is not locked in for 30+ frames.

**Input rate and re-mount (25.09, SCORECARD #13).** The spacing, the drift-check period and the
give-up limit count nominal periods of the input rate (`time_cadence`: the median of the last 9
stamp intervals over `tracking.frame_dt`, 1 at 10 Hz, 2 at 5 Hz; single intervals are not used,
recorded receive stamps come in bursts), and so do the axis rate limits, the warm-up and the
yaw / curvature EMA (`track.rates_per_period`, `walls_smoothing_per_period`; the bed and rail EMA
average noise and stay per frame). While a provisional tilt is applied, the spaced observations
replace it once there are 5 of them and the tilt they give differs by ≥ `refine_min_deg` = 0.5°, and a final
within `keep_within_deg` = 0.25° of it keeps it (no re-seed) (EXPERIMENTS §1i).

## 3. Processing pipeline

### 3.1 Track model (`resense/track.py`, section `track`)

Three quantities describe the track ahead as functions of the along-track coordinate X:

| quantity | how it is estimated | range it is trusted |
|---|---|---|
| bed height `z_floor(X)` | per-bin (2 m, 5 m beyond 40 m) 20th percentile of Z in a ±1 m band around the axis; robust line through the near bins, far bins kept only within 0.35 m of it; a quadratic only if ≥ 4 consistent far bins exist and it bends less than a 1500 m vertical curve; linear extrapolation beyond the fitted range; EMA across frames (`floor_smoothing`). **Shadow of a large near object** (25.09, `floor_shadow_height` 1.0): two adjacent bins (no empty bin between them, since the review of 25.09) more than 1 m above the previous frame's bed, the first within `floor_shadow_range` = 30 m, mean the bed behind an object is hidden (only the roof is left there); then only bins within 0.35 m of the previous bed are fitted, never the object's face (the first bin of the off-bed run nearest the shadow, not a nearer switch part or low object), the rail pair below is searched in front of the face, and with fewer than 5 bed bins (10 m) in front the previous bed and rail model are held (set O: the rail head at 20 m 0.8–3.5 m off without it); at most `floor_shadow_max_hold` = 20 frames in a row (review 25.09: a held bed is the next frame's reference, and a 3.4° pitch step held it for good), then the rule is released until no shadow is found | fitted range + `floor_valid_margin` (20 m since v0.5, 60 m in v0.3), **or as far as the extrapolation is verified** (next row) |
| verified extrapolation `floor_verified` (v0.4, second height anchor) | the bed vanishes beyond ~100 m but the walls, benches and ducts beside the track are seen to the end of the range and their foot runs at a constant height above the rail head. Per 5 m bin the lowest point in the side band \|dy\| 1.6–3.5 m (minus half a ring spacing, since the lowest sample of a vertical face lies up to one ring above its foot) is compared with the extrapolated bed; the offset measured in the near bins where the bed fit is supported is the reference; walking outward, the extrapolation stays verified while the median deviation over the last 30 m of populated bins is within `floor_verify_tolerance` (0.5 m). A vertical curve, a platform or a transition breaks the agreement and the range stops there | `floor_verified`; the corridor is trusted to `max(fit + 20 m, floor_verified)` (v0.4: fit + 60 m, which on its own promoted advisory clusters at 135–142 m to alarms on `roundT_squareT_pressureGate_squareT`); on the six bags the verification reaches 105–145 m (p10–p90 of the per-frame value, v0.4 full-rate runs) against bed fits ending at 50–110 m |
| rail-head level, lateral axis `center` and **yaw** (v0.5) | lateral height profile at 4–30 m in 5 cm bins (85th percentile per bin), built in the lateral coordinate of the previous axis (its yaw and curvature removed, so that in a curve the rails are straight lines in the profile — in absolute Y they smeared by up to 0.6 m and the centre was off by 0.9 m on a hand-made R = 800 m scene); the two rail ridges are found as a pair of local maxima `rails_spacing` = 1.59 m apart with a plausible head height (0.08–0.5 m above bed). The pair is then located again in `rails_yaw_slabs` = 3 along-track slabs; a line through the slab midpoints (the previous curvature held fixed) gives the axis at X = 0 and its tangent `tan(yaw)`: the rails are the sharpest parallel reference there is (±2 cm per ridge over a 26 m baseline ≈ 0.1°). EMA `rails_smoothing` | 4–30 m, then extended by the curvature |
| curvature of the axis (yaw only when the rails give none) | per 4 m bin between 6 and 160 m, in a height band 1.6–2.8 m above the rail head (above platforms, below the roof), the boundary of each side is the 90th percentile of \|dy\|; a robust quadratic per side **with the tangent fixed by the rails** gives the curvature 1/R (v0.3 stored the quadratic coefficient 1/2R as the curvature and applied it as 1/R: the axis bent half as much as the tunnel, 2.4 m off at 100 m on R = 800 m; and its free quadratic traded yaw against curvature — the yaw was 0.8–1.0° off the rail direction on curve frames of the organizer bags and saturated at the ±2° clip in every moving bag). A boundary that cannot be fitted with that tangent (a diverging tunnel, a platform hall wall) is rejected instead of bending the axis; if both sides fit but disagree by more than `axis_sides_max_disagreement` (R 1500 m), the **nearer** boundary wins (near structures are constrained to be parallel to the track, far walls are not). Clipped to \|tan yaw\| ≤ 0.09 (5°; 0.06 was within 0.6° of binding on `roundT_doubleT` frames 120–180) and R ≥ 150 m; EMA `walls_smoothing`; yaw and curvature are **rate-limited** to `axis_max_yaw_rate` = 0.17° and `axis_max_curvature_rate` = 1e-4 m⁻¹ per frame (a train at 15 m/s on R = 700 m yaws 0.12° per frame; the v0.3 estimate jumped by 0.5–1.2° between frames on the moving bags, i.e. ±0.5 m at 55 m) | `axis_valid` = last observed boundary bin + 15 m; +50 m only when straight, well fitted and both sides agree; capped at `axis_one_side_range` = 120 m with one boundary and at `axis_disagree_range` = 60 m when the two disagree; shrinks by 20 m per frame without a fit |

The axis is `y_c(X) = center + tan(yaw)·X + ½·curvature·X²`; the rail head is
`z_rail(X) = z_floor(X) + rail_offset`. Every later stage uses the *corridor coordinates*
`dy = y − y_c(X)` and `h = z − z_rail(X)`. The height reference is trusted to
`max(fit end + floor_valid_margin, floor_verified)`; v0.5 cuts `floor_valid_margin` from 60 to
20 m because on the platform bags the extrapolated bed was 0.3–0.65 m off at 85–105 m
(`squareT_platform_squareT_switch` frames 400–650: run model −1.69 m vs bed −2.34 m at 85 m),
which pulled the roof (h ≈ 4 m) into the polygon top and the far rails into its bottom
([`EXPERIMENTS.md`](EXPERIMENTS.md) §1b: 503 of the 1 001 v0.3 false-alarm frames lay beyond the
fit + 20 m); the
verification of §3.1 is what extends the corridor beyond that, where the side structures
confirm the extrapolation.

**Experimental far-rail cross-check (off by default, 24.09).** With
`track.rails_far_check_enabled: true`, a wall-derived bend that would move the corridor
appreciably is compared with rail-pair midpoints in two further slabs beyond the near
4–30 m rail fit (up to 82 m with the default rail range). Both sides must have rail-head
returns near the end of that range; if the far pair contradicts the wall-derived axis in
the same direction in both slabs, a quadratic through the near and far rail midpoints
replaces the estimated centre, yaw and curvature. The trusted axis then ends 15 m beyond
the far rail range: beyond it the corridor is advisory. Without the far pair this check
does nothing; without a near rail pair `gauge.no_rail_range` still limits the far corridor
to advisory at 40 m. This option is supported by a hand-built station/edge regression
only. **No full real-recording A/B or per-frame latency measurement exists** for it, so
the CLI and ROS configurations both ship with the option off and retain the baseline
axis model. It needs real-data false-event, obstacle-recall and runtime evaluation before
activation.

### 3.2 Clearance-gauge corridor (`resense/gauge.py`, section `gauge`)

The gauge is a closed polygon in `(dy, h)`, i.e. a cross-section swept along the axis. **Since
v0.6 it is the train envelope the organizers gave in the Q&A session: 2.1 m wide × 3.0 m high,
all protruding elements included** ([`organizers/QA_session.md`](organizers/QA_session.md)
fact 1): \|dy\| ≤ 1.05 m, from 0.12 m above the rail head (the rail heads, fastenings and joint
bars stay out; lower objects on the track are the low-object stage's, §3.3b) to 3.0 m. A
second, **advisory** polygon is the same profile widened by `warning_margin` = 0.35 m, i.e. to
\|dy\| ≤ 1.40 m — the strict polygon of v0.5. A confirmed object there is a `warning`
(decision `CAUTION`), not an alarm: the organizers stated that a person on a platform or
beside the track is not an obstacle unless inside the envelope.

v0.5 used a polygon designed on day 1 from the car body (half-width 1.40 m from 0.55 m up,
0.95 m between the rails from 0.12 m, top 3.5 m); the GOST 23961-80 profile drawings could not
be transcribed (only the text is online: platform edge 1.45–1.6 m from the axis at 1.1 m above
the rail head, 137 mm maximum height of the train-control inductor). The organizers' envelope
replaces that assumption; the narrower polygon also takes the corridor edge (the ducts,
benches, platform edges and column rows at 1.5–1.7 m that caused most v0.5 false alarms)
0.45 m further away from the strict decision.

Points between `range_min` (3 m) and `range_max` (250 m) are tested against both polygons with a
vectorised even-odd test (after a bounding-box prefilter, v0.5: the polygon test on the few thousand
points inside the box instead of the whole frame). Points inside the advisory polygon are the
*candidates*; membership in the strict polygon is remembered per point. An **edge margin**
(`gauge.edge_margin` + `edge_margin_per_100m` × X/100; v0.5 option, **on since v0.6 with 0.15 m per
100 m**) counts a point as inside the strict gauge only when it lies that far inside the polygon's
lateral edge: the axis is uncertain by ~0.1° (0.1 m per 60 m), so a return a few centimetres inside
the edge at range is not evidence of an object in the gauge; the candidates and the advisory zone
are unaffected. Its measured effect (side structures at \|dy\| 1.5–1.6 m vs the crossing person) is
in EXPERIMENTS §1b.

**Without rails the far corridor is advisory (v0.6.2, `gauge.no_rail_range` = 40 m).** In a frame
in which the track model found no rail pair in the near range (`rail_slabs` = 0: a station with
the rails in shadow, a switch cavern), the axis rests on the walls alone, and at stations the
"walls" are platform edges and end structures. Clusters beyond 40 m in such a frame are
advisory (reason `beyond_axis`, decision `CAUTION`), and the verified-clear distance is capped
at 40 m, so a braking controller sees a short clear distance rather than a confident one; the
tracker's zone vote over the last ten hits smooths frames in which the rails flicker. Nearer
than 40 m the strict decision is kept, so an object close ahead still stops the train (at
40 m a lateral error of 0.1° is 7 cm). Measured on all real data (EXPERIMENTS §0): the
platform-end structure of `squareT_platform_squareT_switch` and the station ends of the ride.

### 3.3 Candidate clustering and infrastructure filters (`resense/clustering.py`, section `cluster`)

Everything is **range-adaptive**, because a 0.5 m object gives ~500 returns at 20 m and ~7 at
100 m (`resense/sensor.py`):

1. coordinates are scaled by `1 / (1 + r / range_scale)` with `range_scale` = 40 m, so a fixed
   voxel (`voxel` = 5 cm) and a fixed DBSCAN radius (`eps` = 0.35 m) grow linearly with range:
   `eps(r) = 0.35·(1 + r/40)`;
2. candidates are voxel-downsampled in that space (merges dual returns; the voxel count is a
   proxy for distinct rays) and clustered with DBSCAN (`min_samples` = 3; since 25.09 on scipy's
   `cKDTree` with scikit-learn's exact labels, `resense.clustering.dbscan_labels`,
   [`ARCHITECTURE.md`](ARCHITECTURE.md) "Native kernels");
3. each cluster gets a bounding box, along-track distance of its nearest point (since 25.09, for a
   cluster in the strict gauge, of its nearest point inside the envelope: `gauge_distance`, not a
   margin point it touches; since the review of 25.09 the envelope widened by the axis-uncertainty
   margin of §3.2, 0.15 m per 100 m, so the distance is never beyond where the object enters the
   envelope, while the strict decision uses the envelope shrunk by that margin), lateral offset of its centroid, lowest and highest point above the
   rail head and mean intensity;
4. clusters that describe infrastructure rather than obstacles are removed, in this order:

| filter | rule (defaults) | what it removes |
|---|---|---|
| size | extent > 8 m or height < 0.08 m; since 25.09 a cluster > 8 m whose part inside the strict gauge is ≤ 3 m long and starts within 30 m is kept as that part (`oversize_split_max_length` / `_distance`: an object touching a long line at the corridor edge) | walls, floor noise |
| point count | < 5 voxels (< 3 beyond 100 m) | noise |
| thin linear | length > 3 m, width < 0.35 m, height < 0.25 m | rails, pipes, cables, duct edges |
| low hardware | top < 0.35 m, width < 0.4 m, height < 0.3 m | clamps, joint bars, cables on the sleepers |
| wall-like | height > 1.9 m and \|lateral\| > 1.2 m, or height > 1.9 m, length > 4 m, width < 1.5 m | columns, gate frames, platform walls, wall segments pulled in by a bad axis |
| linear side structure | aspect > 5, height < 0.8 m, \|lateral\| > 0.8 m | platform edges, ducts, cabinet rows |

5. the surviving cluster is assigned a **zone**: `gauge` if ≥ `gauge_min_points` (3) voxels lie
   inside the strict polygon, otherwise `warning`; it is demoted to `warning` when it lies beyond
   `axis_valid` (the corridor is not trusted there) or entirely above `overhead_min_height`
   (v0.6: 3.0 m, the envelope top; 2.4 m in v0.5);
5b. **infrastructure signatures** (v0.5, measured on the six organizer bags at full rate,
   EXPERIMENTS §1b; each demotes a gauge cluster to `warning` and records its name in the
   status JSON as `detections[].reason` / `warnings[].reason`; a value of 0 switches a rule off):

   | signature | rule (defaults) | what it is on the bags | why no listed object matches |
   |---|---|---|---|
   | `column` | height > 2.2 m and width < 1.0 m, and (v0.6) either off the track centre (\|lateral\| > `signature_min_lateral` = 0.6 m) or at least `column_min_width` = 0.25 m wide | columns of the double-track tunnel, posts, gate legs pulled in by the axis (`roundT_doubleT` frames 114–251: 94 v0.3 alarm frames) | a person is 1.7 m; a train or trolley is wider; **a broken cable hanging near the axis is thinner than 0.25 m and stays an obstacle** (organizers' Q&A: "cables must be detected, this is very important") |
   | `elevated` | lowest point > 1.2 m above the rail head and width > 2.0 m | roof strips and beams across the tunnel read 0.3–0.65 m too low by the extrapolated bed (`squareT_platform_squareT_switch` 104–130 m: 356 frames) | every listed object stands on the bed; a train ahead reaches the polygon bottom |
   | `floating` | lowest point > 0.7 m, height < 1.2 m, width < 1.0 m, and (v0.6) off the track centre (\|lateral\| > 0.6 m); near the axis only (25.09) when longer than 3.0 m along the track with the lowest point above 1.6 m | signs, lamps and brackets on the wall (`doubleT_platform` 46–73 m: 109 frames) | an object on the track touches the ground; **an object hanging into the envelope near the axis stays an obstacle** (v0.6) |
   | `edge` | \|lateral\| > `edge_min_lateral` (v0.6: 1.0 m for the 1.05 m envelope; 1.2 m with the 1.40 m polygon), length > 2.5 × width, height < 1.0 m | duct / bench / platform-edge fragments along the corridor edge (`roundT_pressureGate_roundT` 3–35 m: 90 frames) | the spec's plank is filtered by the hardware rule anyway; boxes and persons are not elongated |
   | `wall_face` | height > 2.0 m (taller than a person), top above `wall_face_min_top` (v0.6: 2.8 m, under the 3.0 m envelope top; 2.4 m in v0.5), and the part below it has \|dy\| ≥ 0.3 m everywhere and > `wall_face_edge` somewhere (v0.6: 1.3 m, the advisory zone ends at 1.40 m; 1.6 m in v0.5) | the platform-hall end wall / portal jamb at 72–78 m of the stopped train (206 frames) | a train ahead fills the corridor centre (\|dy\| ≈ 0 below 2.4 m); a person is lower than 2.0 m. The first cut used 1.5 m and demoted a person standing on a 1.1 m platform edge with the body 15–25 cm inside the gauge (top at 2.8 m) — found by the review of 22.09 on hand-built clusters and fixed; the same review moved `floating_max_height` from 1.5 to 1.2 m for the same case |

   The rules never drop a cluster: it stays an advisory warning with its reason, and a
   persistent object that stops matching a signature (a person stepping away from a column)
   flips back to `gauge` through the tracker's zone history (§3.5).

   Refinements of 25.09, decided on the ride ([`EXPERIMENTS.md`](EXPERIMENTS.md) §1f, §1i):

   - `short_signature_max_length` / `short_signature_max_distance`: the `elevated` and `floating`
     shapes do not demote a cluster at most that long along the track and that far away (later
     rules are not tried). At 3.0 m / 100 m the organizers' 0.3 m floating cube gets a STOP from
     52.5 m instead of 34 m and the box at the envelope top 43 STOP frames instead of 12; wall
     signs and lamps up to 3 m long within 100 m then alarm too (five bags 107 / 20 / 27 →
     113 / 22 / 29 alarm frames / events / STOP episodes). Off (tried, not shipped, 25.09): on
     the ride it adds 6 STOP episodes on top of the long rule (a 1.8 m fixture at 96.8 m and a
     wall object at 55.8 m);
   - `floating_long_min_length` with `floating_long_min_bottom`: the `floating` shape also
     applies near the axis to a cluster longer than `floating_long_min_length` along the track
     **whose lowest point is above `floating_long_min_bottom`**: a duct, tray or beam running
     along the track overhead. A cable hanging from the vault is short along the track or taller
     than 1.2 m, and keeps its STOP. On (3.0 m) since 25.09: the ~104 m structure of the platform
     recording is advisory (five bags 107 / 20 / 27 → 60 / 14 / 17; ride 204 / 47 / 39 →
     197 / 46 / 39), every organizer object and set F straight unchanged. The bottom condition
     (1.6 m) came from the review of the same day: without it the branch skipped the
     `signature_min_lateral` guard, so a cable tray, duct or pipe fallen onto the axis (e.g.
     4.0 × 0.3 × 0.5 m with its bottom 1.0 m above the rail at 60 m) was advisory (`CAUTION`)
     instead of a STOP. Everything the branch demotes on the six recordings, set O and the ride has
     its bottom at 1.68–2.65 m (the ~104 m structure 1.69–2.42 m, median 2.21 m), except one
     single-frame cluster at 0.89 m that never confirmed; of the pre-registered 2.0 / 1.8 /
     1.6 m, 2.0 and 1.8 m bring back the ride event at 105–110 m (bottom 1.68–1.92 m), and 1.6 m
     leaves every recording, the ride, set O and set F straight identical frame by frame. A long
     object near the axis whose bottom is above 1.6 m is still advisory (§6).
   - `floating_free_max_size` with `floating_free_max_dy` / `floating_free_max_top` (25.09,
     round 2): the `floating` shape does not demote a compact cluster hanging free inside the
     envelope: every extent ≤ 0.5 m, its outermost point ≤ 0.95 m off the axis and its top
     ≤ 2.5 m. The signs, lamps and brackets `floating` is for are fixed to the wall or the vault,
     so their clusters reach the wall side of the corridor or its top (or are longer). On since
     25.09: the organizers' 0.3 m cube hanging 1.0–1.4 m up gets a STOP from 52.5 m instead of
     34.0 m; the six recordings and the ride are identical frame by frame (EXPERIMENTS §1i).

   [`EXPERIMENTS.md`](EXPERIMENTS.md) §1f has the numbers;
6. **retro-reflector rule** (v0.4, [`SENSOR.md`](SENSOR.md) §3.3: intensity is reflectivity in
   %, values above 100 come only from retro-reflective material — signs, markers, reflective
   tape, rail-head polish). A cluster is demoted to `warning` and flagged `retro` when
   **all three** hold: at least `retro_min_fraction` (50 %) of its returns have intensity ≥
   `retro_intensity` (0 by default: the rule is off, it never fired on the six bags; 100 when
   on); its height is below `retro_max_height` (1.2 m); its lateral width is below
   `retro_max_width` (0.8 m). The size rule is what keeps real objects: a person is
   taller than 1.2 m even in a hi-vis vest (the vest also covers less than half of the returns),
   a train or a trolley is wider than 0.8 m and taller, a large crate is wider. What the rule
   deliberately demotes: plates and posts up to 0.8 × 1.2 m that are retro-reflective over
   most of their surface — signs, kilometre and speed markers, reflectors on the tunnel wall,
   and also a small fully retro-reflective object (a 0.5 m reflective cube is treated as a
   marker; documented, see EXPERIMENTS §2b). The visible depth of an object is not used
   (from the front every object is thin). `retro_intensity: 0` switches the rule off;
7. a **visibility score** compares the voxel count with the number of returns a target of that
   width and height should give at that range (`expected_points`); the score saturates at
   `visibility_ratio` = 15 % of the expectation and feeds the tracker's confidence;
8. **thin objects hanging from above** (`hanging_*`, on since 25.09, `clustering.find_hanging`,
   [`EXPERIMENTS.md`](EXPERIMENTS.md) §1i): a cable or rod that dips only 0.2–0.4 m below the
   envelope top gives 1–3 returns there, below the 5-voxel minimum. The frame's points near the
   axis (\|dy\| < 0.8 m) from 1.8 m up to 0.6 m above the top are linked at the corridor radius;
   a group with at least one voxel inside the strict envelope and one above its top, at most
   0.5 m along and across the track and at most 60 m away (and within the trusted corridor), is
   a gauge cluster of kind `hanging`. It is dropped when it overlaps a cluster of the other
   stages, and it is confirmed like any track (5 frames). Since 25.09, round 2
   (`hanging_needs_rails`, on) the stage runs only on frames whose track model found the rail
   pair in the near range (`track.rail_slabs` > 0): 28 of the 29 groups it took on the ride were
   tops of station columns in frames without one. The organizers' 5 cm object STOPs from
   30.1 m with and without the guard; the ride and the empty recordings are unchanged.

When several frames are merged (§3.4) the voxel-count thresholds `min_points`, `min_points_far` and
`gauge_min_points` are raised by `1 + n_merged · min_points_scale` (×1.5 for 5 frames,
`accumulation.min_points_scale` = 0.3) for clusters beyond the accumulation range, so that merged
noise does not pass a single-frame bar. The factor is deliberately far below ×5: the voxel grid (5
cm in range-normalised space, i.e. 0.3 m at 200 m) merges returns that land on the same spot, so the
union of 5 frames of a small far object holds only slightly more *voxels* than one frame — 6 voxels
for a 0.5 m box at 120 m, 6–12 for a person at 190 m — and a ×3 factor was measured to lose the box
(EXPERIMENTS §2b). A **smear guard** protects against a wrong ego speed: a merged cluster longer
than `accumulation.smear_max_length` (2 m) along the track — or, since v0.5, wider than
`smear_max_width` (1 m) across it (a person walking across the track, merged over 0.5 s; the same
guard makes the merge single-frame for anything wider than 1 m — a train, a 1.2 m trolley — which is
harmless, such objects are seen in one frame) — can only be a static object shifted by the wrong
amount or a moving one, so it is re-described from its current-frame points with single-frame
thresholds — a wrong speed then degrades to v0.3 behaviour instead of stretching the object past
`max_extent` and losing it.

### 3.3b Low objects on the track (`resense/lowobj.py`, section `lowobj`) — v0.6

The organizers' size criterion is **300 × 300 × 100 mm** (Q&A fact 2). Such an object is lower
than the polygon bottom (0.12 m above the rail head), so the corridor stage cannot see it by
construction. It is, however, an anomaly of the *track bed*, whose cross-section (rails,
fastenings, bed, drainage trough) repeats every metre:

1. the **bed template** `h_bed(dy)` — the height of the bed surface above the rail head at
   lateral offset `dy` — is learned every frame from the dense near range (4–30 m) as the 30th
   percentile per 2.5 cm lateral bin, dilated by ±5 cm (the rail heads and their flanks belong
   to the template), smoothed over frames (EMA 0.8), updated only while the rail pair is locked;
2. per 2 m along-track bin the **local offset** of the bed returns from the template (the
   height reference drifts by centimetres with range) is the median residual of the points that
   look like bed (residual −0.15…+0.05 m); bins without bed returns end the stage's range
   (the bed is seen at grazing incidence: ~50–80 m, `range_max` = 60 m);
3. a point inside the envelope (\|dy\| ≤ 1.05 m), below the polygon bottom, whose residual
   exceeds `min_excess` = 5 cm **and which is itself at least `min_point_top` = 3 cm above the
   rail head** is a **low candidate**;
4. the low candidates are clustered **on their own** with a tighter radius (`lowobj.eps` = 0.2,
   range-normalised like the corridor's: 0.25 m at 10 m, 0.48 m at 56 m — the corridor radius,
   0.84 m at 56 m, merged the object of `doubleT_obstacle` with the bed fixtures around it into a
   2 × 1.6 m cluster). A low cluster must be ≤ 1.5 m long along the track (rails, guard rails,
   cables, ducts are longer), ≤ 2.2 m across (the envelope's width; 1.6 m until the second
   review of 23.09 rejected a person lying across the track — identical on all real frames,
   EXPERIMENTS §0), ≥ `min_width` = 0.15 m across (rail-head slivers and fastenings
   are narrower), have 3 voxels and its top must reach the rail-head plane (`min_top` = 0); it is
   a gauge obstacle with `kind = "low"`;
5. a low cluster is dropped when corridor candidates higher than `foot_max_top` = 0.35 m stand
   in its footprint (it is the foot of a sign, a column or a person: the corridor stage decides,
   including its signature demotions) or when a corridor cluster overlaps it (the lower part of
   an object the corridor stage already reports: one detection, not two).

**What decided the thresholds (measured, EXPERIMENTS §1d).** (a) Reporting every bump above
the bed alarmed **1 350 times on the 20-minute ride**: the metro bed carries fixtures 5–40 cm
tall and 0.3–1 m wide every few tens of metres (train-control inductors, drain covers, cable
crossings), geometrically the same as a 30 × 30 × 10 cm box — and they stay below the rail head
by design, because the train passes over them. The envelope of the train starts at the rail
head, so an object lying on the bed between the rails is below it. (b) Requiring only the
cluster's *top* to reach the rail-head plane still left **~800 false events**: the rail area
itself (guard rails in curves, joints, fastenings, check rails at switches) produces clusters
whose top is 1–8 cm above the rail head, and no single-frame threshold on height, width, excess
or voxel count separates them from a small object. (c) Requiring every candidate point to be
≥ 3 cm above the rail head leaves **2 false events on the 13 worst files of the ride** and still
finds a 10 cm box lying on a rail head at 10–25 m (synthetic tunnel, `tests/test_envelope.py`).
The rail-head path keeps (c): a safety function that stops the train every 1.5 s on a clean
track is not usable. The opt-in central near-bed path below is off in the shipped
configuration: with its first gates it raised the ride's false events from 47 to 667, and with the
current gates the five obstacle-free recordings give 107 events instead of 20 (the ride not re-run;
§6, EXPERIMENTS §1e). The organizers confirmed the policy on 25.09: a 30 × 30 × 10 cm object on the
bed between the rails is not inside the train's envelope, so it is not an obstacle
([`organizers/answers.md`](organizers/answers.md) §8).
`min_top: -1` and `min_point_top: -1` restore the unrestricted bed-level policy for a line
with a clean bed.

**Objects straddling the envelope floor (v0.6.2, `lowobj.straddle_*`).** The organizers' object
lying across the right rail of `doubleT_obstacle` (0.45 × 0.6 × 0.3 m, 56 m) returns ~21 points,
~16 of them below the rail head and ~3 above the 0.12 m envelope floor; its top is 0.10–0.15 m
(median 0.13 m) above the detector's rail-head plane after the mount calibration (the labels,
measured against the per-frame track model before it, give 0.07–0.22 m, median 0.17 m). In
v0.6.1 it fell *between* the stages: the corridor stage saw 0–3 points above the floor (below its
cluster minimum), the low-object stage — whose every candidate must be 3 cm above the rail head —
a 3-point sliver, and neither confirmed it (2 of its 185 frames by its own detection, both after
the person left it). v0.6.2 adds a third clustering:

1. `low_candidates` also returns every bed anomaly **without** the per-point `min_point_top`
   rule (step 3);
2. those, together with the corridor points less than `straddle_band` = 0.30 m above the
   envelope floor inside the envelope's width and the bed's observed range, are clustered with
   the low-object radius;
3. a cluster is reported (`kind = "low"`, the 5-hit confirmation of low objects) when its **top
   reaches `straddle_min_top` = 0.10 m above the rail head** — the rail fittings reach 1–8 cm —
   and it is **≥ `straddle_min_width` = 0.35 m across the track and ≤ `straddle_max_length` =
   0.8 m along it**: trackside devices beside the rails (train stops, lubricators, signalling)
   reach 0.2–0.35 m but are mounted along the rail, 0.2–0.3 m across and 0.5–1.4 m long, and
   without the shape rule added 49 false events on the ride;
4. a straddling cluster replaces the low-stage slivers it overlaps, and yields only to a
   corridor cluster that is itself reported (one detection per object).

Result (EXPERIMENTS §0): the object in **124 of the 126 frames after the person leaves it** and
127 of its 185 visible frames by its own detection (v0.6.3, with the hold over one missed frame;
v0.6.2: 118 / 121; v0.6.1: 2), for +1 event on the five empty bags and +1 on the ride (v0.6.2).
The thresholds sit close to this one real object — its top 0.11–0.16 m against 0.10, its width
0.38–0.50 m against 0.35 (a review found 45 of 126 frames with a 0.13 m minimum and 95 with a
0.45 m width) — because the rail fittings reach 8 cm and the trackside devices are 0.2–0.3 m
across: there is no wider margin on geometry alone. Moving each threshold by 20–25 % over all
13 759 frames (v0.6.2, EXPERIMENTS §0) changes the false alarms by −1…+2 events of 67 but the
object's frames from 121 to 91–127: the thin margin is on the object's side. An object of that shape
lying across a rail is found at 25, 40 and 50 m in the synthetic tunnel
(`tests/test_envelope.py`); beyond ~50–60 m the bed stops returning (grazing incidence) and a
0.3 m-high object has one or two rings above the rail head, which is where the stage ends.

**Central near-bed objects (experimental, off by default; 24.09).** Not needed for the organizers'
check (such an object is not an obstacle, 25.09, [`organizers/answers.md`](organizers/answers.md)
§8): the path stays off and is kept as a measured experiment. Set
`lowobj.near_enabled: true` explicitly to test a separate low path for compact objects lying on
the bed between the rails, below the rail head. It accepts bed anomalies entirely within
`near_half_width` = 0.55 m of the axis (the rail heads and their fastenings at ±0.8 m stay out)
and within `near_range` = 30 m, only while the rail pair is locked and the *central* bed has at
least `local_min_points` = 5 returns in the same 2 m bin, with returns in at least
`near_min_bed_lateral_bins` = 20 of the 45 lateral template bins (2.5 cm each; the bins are
counted, they need not be contiguous), so an object cannot create its own local reference across a
missing-bed gap. The excess over the locally offset bed template must exceed `near_min_excess` =
0.05 m; clustering uses the existing tight low radius and needs ≥ `near_min_points` = 5 voxels, an
observed width of `near_min_width`–`near_max_width` = 0.24–0.55 m and ≤ `near_max_length` = 0.75 m
along the track. Neither a vertical extent (`near_min_height` = 0) nor an along-track extent
(`near_min_length` = 0) is required: at 12–28 m a 30 × 30 × 10 cm box returns a single scan line,
5–10 voxels and ~0.03 m along the track, and the 10-voxel / 0.18 m gates tried on 24.09
(`537e220`) rejected it (fixed in `7df1796`). The width and maximum-length gates exclude long
drain covers and linear hardware; the rail-head point-height rule and the straddle rules are
unchanged, and the 5-hit low-object confirmation and the foot-of-corridor suppression apply.
Against the first gates of `a92625e` (excess 0.08 m, ≥ 5 voxels, no maximum width, no lateral
bed-support rule), the width and bed-support gates halve the alarm frames on the five
obstacle-free recordings (1 035 → 459) but remove only a quarter of the events (145 → 107): most of
the remaining false events are central bed fixtures returning the same single scan line as the box
(EXPERIMENTS §1e). A compact inductor or short raised cover with the same 3-D returns as a foreign
object cannot be told apart by this geometry alone; the ride has not been re-run with these gates.

Puddles in the trough (Q&A fact 17) return nothing or mirror images *below* the bed (negative
residuals) and are ignored by construction. Cost: 3–5 ms per frame.

### 3.3c The far field of a straight tunnel — v0.6

The corridor is trusted to `min(axis_valid, height_valid)` in v0.5, and on a straight tunnel the
height reference is the limit: the bed stops returning at ~100 m (grazing incidence), its fit
ends at 70–90 m, and the side-base verification reaches 100–145 m, while the walls confirm the
axis to ~200 m (`axis_valid` 197–217 m on the straight sections of the ride). Measured against
the tunnel vault, the extrapolated rail level runs 0.1 m low at 85 m, 0.25 m at 100 m and
0.4–0.5 m at 150–200 m (EXPERIMENTS §2d). A 0.5 m error does not change whether a person,
a crate or a train ahead is inside a 3 m tall envelope; it only lifts flat far-bed returns into
the polygon bottom. v0.6 therefore trusts the axis to `axis_valid` and, **between the height
reference and the axis range, reports a cluster as an obstacle only if it is at least
`far_min_height` = 0.6 m tall, at most `far_max_length` = 3 m long along the track and reaches
below `far_max_bottom` = 1.0 m** — a face seen head-on that stands on the track, not a surface
at grazing incidence nor a sign hanging above the corridor (`reason = "beyond_height_ref"`
otherwise). The edge margin grows to 0.3 m at 200 m there, for the lateral uncertainty.

### 3.4 Ego speed and multi-frame accumulation (`resense/egomotion.py`, `resense/accumulate.py`, section `accumulation`) — v0.4

Beyond ~150 m a person returns 3–5 points per frame and a 0.5 m box 1–3
([`DATASET.md`](DATASET.md)), so the single-frame clusterer hits its `min_samples` = 3 floor
unpredictably. The detector therefore merges the corridor candidates of the last `n_frames` = 5
frames (0.5 s), compensated for the train's motion, before clustering. **Default since v0.5: the
merge runs only with a speed the caller gives** (`ego_speed_mps` parameter or odometry in the node,
the rows' speed in `eval` sequences); the LiDAR-only estimator is off (`estimate_speed: false`)
because its estimated-speed merging added 31 false-alarm frames on the five empty bags at full rate
(119 vs 88) without a real-data recall gain and costs 7–8 ms per frame (EXPERIMENTS §1b). Without a
given speed the pipeline is single-frame. **Re-measured on 24.09** against an ICP reference
(EXPERIMENTS §9): the estimate is accurate (median error 0.06–0.08 m/s, p90 ≤ 0.20 m/s on 55–96 %
of the moving frames, +6.6–6.8 ms per frame), but neither it nor a perfect speed improves the
organizers' check (no earlier first STOP on their objects, more false STOP frames on the box
outside), so the default stays; the organizers' recordings carry no odometry (Q&A fact 6), and a
given speed is honoured. Only candidates beyond `min_range` = 40 m are merged:
there the single frame is what limits detection, while a person walking at 5 m from the train must
not be smeared over half a second and is dense enough anyway.

**Ego speed.** `Detector.process(frame, ego_speed=None)` takes the train speed in m/s when the
caller knows it (the ROS node's parameter or odometry topic); a given speed always wins and is
reported as `ego_speed_source = "given"` (the estimator is then skipped, saving 7–12 ms per real
frame, so `ego_speed_estimate` is null). Without it and with the shipped
`accumulation.estimate_speed: false`, the source is `"none"` and **nothing is merged**. Opting in to
the LiDAR estimator may instead yield `"estimated"` when confident, or `"none"` when it is
uncertain: a wrong shift smears, and the single-frame pipeline is the safe fallback. Below
`accumulation.min_speed` (1 m/s, given or estimated) nothing is merged either (v0.5): a stopped
train gains no density from identical frames (the union lands on the same voxels) but loses marginal
objects to the scaled count thresholds, and in v0.4 the tracks cue (≥ 3 persistent static tracks
with ≈ 0 velocity) reported 0 m/s with confidence 0.6 on the stationary `doubleT_obstacle` and
merged 5 frames at v = 0, which smeared the person walking across the track laterally (width 1.06 m
vs 0.57 m single-frame). The tracks cue now reports nothing below `tracks_min_speed` (1 m/s) and the
smear guard also acts across the track (§3.3). ICP would be the textbook estimator, but a straight
tunnel is translation-invariant along its axis and ICP is degenerate in exactly that direction
([`RESEARCH.md`](RESEARCH.md) §2). What is observable is the *texture* of the walls along the track
— brackets, cable hangers, lamps, signs, cabinets, niches, column edges at irregular positions —
which slides towards the sensor by `v · dt` per frame:

* per side, a histogram of returns over X in 0.1 m bins between 4 and 25 m, restricted to
  1.3–3.0 m above the rail head (vertical surfaces only: the bed, the walkway tops and platforms
  are sampled in ring stripes that are fixed in the sensor frame and would vote for "no
  motion"); normalised by a running 2 m mean (density falls with range), clipped, zero-mean;
* a temporal background (EMA over frames, weight 0.7) of that profile is subtracted: even a
  smooth lining leaves a faint pattern of where the ring/column grid lands, fixed in the sensor
  frame, and in a featureless tunnel a moving and a stopped train produce the same data — so
  whatever does not move is discarded and a featureless stretch yields "unknown" rather than a
  confident 0 m/s (which was the first version's failure, EXPERIMENTS §2b). The estimator
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

Persistence is measured in **time** since v0.5: besides `confirm_hits` = 3 hits a track must have
been observed for `confirm_time_s` = 0.5 s of sensor time (frames × the measured frame interval, the
first frame included — 5 frames at 10 Hz, 3 frames at 5 Hz; v0.3–v0.6.1 used 0.3 s = 3 frames;
v0.6.2 took 0.5 s after it removed 27–35 % of the false-alarm events on all real data without
delaying the real person, EXPERIMENTS §0), it must have been matched in `min_hit_fraction` = 60 % of
its last `hit_window` = 10 frames (a structure that flickers into the corridor every other frame is
never reported), and it must be matched now. The zone of a track is decided over its last
`zone_window` = 10 hits: `gauge` when `zone_min_fraction` = 60 % of them were inside the strict
polygon (v0.3: the majority of the last 5) — an object first seen beyond the trusted corridor, or a
corridor-edge structure whose gauge membership flickers with the axis, is advisory until the history
is clear; it also stays advisory while `tracking.column_hold` = 2 of those hits were demoted as a
column (25.09: a column far away shows more than 2.2 m of itself in some frames only, EXPERIMENTS
§3a). Accumulation changes what the tracker sees (denser clusters), not the persistence semantics.

## 4. Decision rule

A frame reports `obstacle = true` when at least one track is **confirmed**:

* seen in ≥ `confirm_hits` = 3 frames and observed for ≥ `confirm_time_s` = 0.5 s (5 frames
  at 10 Hz, v0.6.2; 0.3 s before), matched in ≥ 60 % of its last 10 frames,
* confidence ≥ `conf_threshold` = 0.6,
* matched in the current frame (no miss) — or reported in the previous frame and missed for at
  most `hold_misses` = 1 frame (v0.6.3), then at its predicted distance: one missed frame no
  longer switches a STOP off and on (−25 % STOP episodes, events unchanged,
  [`EXPERIMENTS.md`](EXPERIMENTS.md) §0),
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
`ego_speed_estimate` / `ego_speed_confidence` (the estimator's own opinion only when explicitly
enabled and no speed is given) and `track.floor_verified`; all existing keys are unchanged.

**Cost of the rule.** An object that appears inside the strict gauge is reported after five frames
(0.5 s, 11 m at 80 km/h; three frames and 6.7 m before v0.6.2). One that was already tracked while
it approached — a person stepping in from the side, or a far object beyond the trusted range that
the train then nears — costs nothing extra: the persistence clock runs while the track is advisory,
and the zone history, which needs 60 % of the last ten hits inside, then decides (six frames, 0.6 s,
when the track was advisory for five or more hits first). The alarm also lingers four frames after
the object leaves the gauge (the three "false" frames of the `doubleT_obstacle` evaluation,
EXPERIMENTS §1); that is the price of suppressing single-frame noise. Persistence is applied before
the alarm, not after, so the first alarm is already a confirmed object. On `doubleT_obstacle` the
person enters the strict gauge at frame 2 and was reported from frame 7 in v0.5 (v0.3: frame 9);
with the 2.1 m envelope of v0.6 it enters the envelope at frame 8 and is reported from frame 11
(EXPERIMENTS §0) — with 0.3 s and with 0.5 s alike, because the person was tracked while stepping in
from the side.

### 4b. Outputs for the train: decision, verified-clear distance, health — v0.6

The organizers asked for "can we go / is there an obstacle / how far" (Q&A fact 9). Besides the
flag and the distance, every frame carries:

* **`clear_distance`** (status JSON, `/resense/clear_distance`) — metres of track verified
  clear: the nearest confirmed obstacle, else the **monitored range** =
  `min(visibility, trusted corridor, gauge range)`, where *visibility* is the X of the 20th
  farthest return within 3 m of the track axis (the sightline in a curve, the end of a
  platform hall) — the organizers accept a detection at the visible limit ("no worse than a
  driver", fact 14), so the output says how far the path was actually checked. A consumer that
  brakes on `clear_distance` < stopping distance gets fail-safe behaviour for free: a blinded
  sensor, a lost track model or a stale input shrink it to 0. Since 25.09 (round 2,
  `health.clear_cap` on) it also stops at the nearest unconfirmed or advisory cluster touching the
  strict envelope (columns and a confirmed obstacle's own cluster excluded; its distance is in
  `health.candidate_distance`); it never changes a detection or the decision (§6, EXPERIMENTS §1i);
* **`health`** (`resense/health.py`, `/resense/health` as `diagnostic_msgs/DiagnosticArray`):
  `ok` / `warn` / `error` with messages — valid returns per frame (error below 20 000 = a
  blinded sensor or a truncated message, warning below half the running median), returns closer
  than 2.5 m (> 20 %: a dirty or blocked window), 10° azimuth sectors without returns in the
  central ±30° (view blocked), visibility < 60 m, rail lock in < 30 % of the last 20 frames
  (track model on its prior: stations, switches, pressure gates — where "the rails are flush
  with the gate floor", Q&A fact 16), latency p95 over the 100 ms budget, mount calibration
  fallback or drift; an error sets the monitored range to 0. Counters only (review 25.09, in the
  status JSON's `health`, never a message or a level): `floor_shadow_frames`,
  `floor_held_frames` and `floor_released_frames`, the frames since the start in which the
  floor-shadow rule of §3.1 found a shadow, held the previous bed, or was released by its
  20-frame cap;
* **`decision`** (node, `/resense/decision`): `STOP` when a confirmed obstacle is inside the
  envelope; `FAULT` on a health error, on an exception while processing (logged, the node
  keeps running and resets the detector after 5 in a row) and from the watchdog when no frame
  arrived for `stale_timeout` = 0.5 s; `CAUTION` for an advisory object or a health warning;
  else `GO`.

## 5. Parameters that matter most

All parameters live in one file, `configs/default.yaml` (`resense:` root key), loaded by both
the CLI and the ROS node; the one exception is `tracking.hold_misses`, a code default in
`resense/config.py`. The ones that change behaviour visibly:

| parameter | default | effect |
|---|---|---|
| `sensor.forward/left/up` | `-y/+x/+z` | sensor → vehicle axes; wrong values break everything |
| `gauge.profile`, `gauge.warning_margin` | v0.6: ±1.05 m, 0.12–3.0 m (the organizers' envelope); 0.35 m (v0.5: ±1.40 m, 0.12/0.55–3.5 m) | what counts as "in the way"; widen for safety, narrow to cut platform-edge false alarms |
| `gauge.range_max` | 250 m | how far the corridor is evaluated |
| `track.walls_*`, `track.axis_valid_margin` | band 1.6–2.8 m, +15 m | how far the curved corridor is trusted; beyond it only warnings |
| `track.rails_yaw_enabled`, `rails_yaw_slabs` | true, 3 | yaw of the axis from the rail pair (off = free quadratic through the walls, the v0.3 way: 0.8–1.0° yaw error on curve frames) |
| `track.rails_far_check_enabled` | false | experimental far-rail cross-check for station-wall curvature (§3.1); opt-in; never fires on the six recordings and set O (25.09, [`EXPERIMENTS.md`](EXPERIMENTS.md) §1f) |
| `track.axis_max_yaw_rate`, `axis_max_curvature_rate` | 0.003 rad, 1e-4 m⁻¹ per frame | how fast the corridor may swing between frames; 0 = unlimited |
| `track.axis_sides_max_disagreement`, `axis_disagree_range`, `axis_one_side_range` | 6.7e-4 m⁻¹, 60 m, 120 m | trusted range when the two boundaries disagree or only one is seen |
| `track.floor_valid_margin` | 20 m (60 in v0.3) | how far beyond the fitted bed the height reference is trusted without verification |
| `cluster.column_*`, `elevated_*`, `floating_*`, `edge_*`, `wall_face_*` | see §3.3 | infrastructure signatures (advisory only); 0 switches a rule off |
| `gauge.edge_margin`, `edge_margin_per_100m` | 0, 0.15 m (v0.6; 0, 0 in v0.5) | lateral margin inside the polygon edge required for the strict decision, growing with range (option, EXPERIMENTS §1b) |
| `tracking.confirm_time_s`, `min_hit_fraction`, `zone_window`, `zone_min_fraction`, `column_hold` | 0.5 s, 0.6, 10, 0.6, 2 | persistence in seconds and over the track's history (0.3 s before v0.6.2); column hits that keep a track advisory (25.09) |
| `accumulation.min_speed`, `tracks_min_speed` | 1 m/s, 1 m/s | no merging and no tracks-cue estimate for a stopped train |
| `cluster.eps`, `cluster.range_scale`, `cluster.voxel` | 0.35 m, 40 m, 5 cm | cluster granularity vs range |
| `cluster.min_points`, `cluster.min_points_far`, `cluster.far_range` | 5, 3, 100 m | sensitivity at range vs noise |
| `cluster.hardware_*`, `cluster.thin_*`, `cluster.wall_*`, `cluster.linear_*` | see table above | infrastructure suppression; the `hardware` rule also hides objects below 35 cm on the sleepers |
| `cluster.overhead_min_height` | 3.0 m (v0.6: the envelope top; 2.4 m in v0.5) | overhead fixtures are advisory only |
| `tracking.confirm_hits`, `tracking.conf_threshold` | 3, 0.6 | latency vs false alarms |
| `tracking.hold_misses` (v0.6.3) | 1 | frames a reported obstacle stays reported without a match; 0 = the v0.6.2 behaviour. Code default in `resense/config.py`, not in `configs/default.yaml` |
| `calibration.apply_min_deg` | 0.75° | smallest tilt applied (1.5× the p90 noise of the 20-observation median on a moving train; 0.5° until v0.6.3) |
| `tracking.ego_speed_max` | 25 m/s | association slack without odometry |
| `track.floor_verify_tolerance`, `track.floor_verify_band` | 0.5 m, \|dy\| 1.6–3.5 m | how far the bed extrapolation is trusted beyond the fit: looser = longer corridor, more phantom objects where the bed bends |
| `cluster.retro_intensity`, `retro_max_height`, `retro_max_width` | 0 (off), 1.2 m, 0.8 m | which bright clusters are signs (advisory) rather than obstacles; 0 disables the rule |
| `accumulation.enabled`, `n_frames`, `min_range` | true, 5, 40 m | how many frames are merged beyond which range; off = v0.3 single-frame behaviour |
| `accumulation.min_points_scale`, `smear_max_length` | 0.3, 2 m | noise bar of merged clusters; length beyond which a merged cluster is taken as smeared |
| `accumulation.speed_min_confidence` | 0.5 | how sure the ego-speed estimate must be before frames are merged without a given speed |
| `lowobj.min_point_top`, `min_top`, `min_excess`, `eps`, `range_max` (v0.6) | 0.03 m, 0.0 m, 0.05 m, 0.2, 60 m | every low candidate ≥ 3 cm above the rail head, the cluster's top at the rail-head plane (both −1 = any bump above the bed); excess over the bed template; clustering radius; how far the bed is used |
| `cluster.far_min_height`, `far_max_length`, `far_max_bottom` (v0.6) | 0.6 m, 3 m, 1.0 m | what may alarm between the trusted height reference and the trusted axis range (0 = v0.5 behaviour: nothing) |
| `cluster.signature_min_lateral`, `column_min_width` (v0.6) | 0.6 m, 0.25 m | where the column / floating signatures apply (hanging cables near the axis are obstacles) |
| `cluster.short_signature_max_length`, `short_signature_max_distance` (25.09) | 0 (off), 100 m | tried, not shipped: `elevated` / `floating` spare a cluster at most this long along the track and this far (§3.3); at 3.0 m set O 303 → 352 inside STOP frames, but ride STOP episodes 39 → 45 with the long rule (EXPERIMENTS §1f) |
| `cluster.floating_long_min_length` (25.09) | 3.0 m (on since 25.09) | `floating` also demotes a cluster near the axis longer than this along the track (§3.3): five bags 20 → 14 events, ride 47 → 46, set O and set F straight unchanged, gate PASS (EXPERIMENTS §1f) |
| `cluster.floating_long_min_bottom` (25.09, review) | 1.6 m | ... only when the cluster's lowest point is above this (overhead infrastructure; a tray or duct fallen onto the axis lower down is a STOP): 2.0 / 1.8 m bring back a ride event (ride 46 → 47), 1.6 m changes nothing on the recordings, the ride, set O and set F straight (§3.3, EXPERIMENTS §1f); 0 = no bottom condition |
| `cluster.floating_free_max_size`, `floating_free_max_dy`, `floating_free_max_top` (25.09, round 2) | 0.5 m (on), 0.95 m, 2.5 m | `floating` spares a compact cluster hanging free inside the envelope (§3.3): the organizers' floating cube a STOP from 52.5 m instead of 34.0 m, every recording and the ride identical, gate PASS (EXPERIMENTS §1i) |
| `calibration.enabled`, `frames` × `obs_spacing`, `provisional_min_deg`, `min_yaw_deg`, `drift_warn_deg` / `drift_window` (v0.6.1) | true, 20 × 10 frames, 2.5°, 3°, 1.5° / 10 checks | mount auto-calibration (final tilt over 20 s, provisional only for a clearly tilted rig); `sensor.roll_deg/pitch_deg/yaw_deg` freeze a known mount |
| `lowobj.straddle_enabled`, `straddle_min_top`, `straddle_min_width`, `straddle_max_length`, `straddle_band` (v0.6.2) | true, 0.10 m, 0.35 m, 0.8 m, 0.30 m | an object across a rail, straddling the envelope floor, clustered whole (§3.3b) |
| `lowobj.near_enabled`, `near_range`, `near_half_width`, `near_min_excess`, `near_min_width`, `near_max_width`, `near_min_length`, `near_min_height`, `near_min_bed_lateral_bins`, `near_min_points`, `near_max_length` | false, 30 m, 0.55 m, 0.05 m, 0.24 / 0.55 m, 0.0 m, 0.0 m, 20, 5, 0.75 m | opt-in central near-bed path (§3.3b), off: its first gates added 620 events on the ride; the width and bed-support gates halve its alarm frames, 107 events on the five recordings against 20 (§3.3b, §6) |
| `lowobj.max_length`, `max_width` | 1.5 m, 2.2 m | the largest low cluster along / across the track; 2.2 m (the envelope's width, 1.6 m until 23.09) keeps a person lying across the track; identical on all real frames (EXPERIMENTS §0) |
| `gauge.no_rail_range` (v0.6.2) | 40 m | without a rail pair in the near range clusters beyond it are advisory and the verified-clear distance is capped there (§3.2); 0 = off |
| `health.*` (v0.6) | see §4b | thresholds of the guards; they never change a detection |

## 6. Limitations (v0.6.3)

The v0.6–v0.6.3 limitations first, then what the organizers' own test objects exposed (set O,
24.09) and the organizers' answers that bound the task; the v0.5 list follows. Measurements:
[`EXPERIMENTS.md`](EXPERIMENTS.md); the criteria judgement of 24.09 and its risks on the hidden
data: [`SCORECARD.md`](SCORECARD.md).

* **Low objects below the rail head** (§3.3b): the shipped default does not report compact objects
  on the bed between the rails, and by the organizers' answer of 25.09 they are not obstacles
  (below, "What the organizers' answers settle"). The opt-in central near-bed path can report them
  within 30 m, provided the local bed is observed and the rails are locked, but a fixture with the
  same geometry can still cause a false alarm, and on real data it does. With its first gates (`a92625e`) it was
  measured on 24.09 on all 13 759 frames by the criteria review (EXPERIMENTS §1e [team record,
  unverified: raw not committed]): the five obstacle-free recordings give 145 events (20 with the
  defaults), the ride 667 events and 247 STOP episodes (47 and 39), while the 30 × 30 × 10 cm box
  on the bed stays at 0 of 6 approaches [synthetic: set F] and a dog-sized box is found in 5 of 6
  approaches from 19.5–50.2 m; on set O the background alarm frames rise from 3 to 466 (P4, 24.09).
  With the width (≤ 0.55 m) and bed-support gates added on 24.09 (`537e220`, box fix `7df1796`) the
  five recordings give 459 alarm frames / 107 events / 72 STOP episodes (1 035 / 145 / 42 before,
  107 / 20 / 27 with the defaults) and set O 319 background alarm frames; the ride has not been
  re-run, and the path stays off (for good since the organizers' answer).
  Beyond 30 m or beside a rail the rail-head rule applies. On a line with a clean bed,
  `lowobj.min_top: -1` with `min_point_top: -1` reports all bed bumps. An object lying *across* a
  rail (the organizers' object in `doubleT_obstacle`) is reported since v0.6.2 (§3.3b: 124 of the
  126 frames after the person leaves it), but only while the bed is seen (≤ ~50–60 m) and only when
  it is ≥ 0.35 m across the track: an object lying *along* a rail is indistinguishable from the
  trackside devices mounted there.
* **A person lying on the track** (synthetic, EXPERIMENTS §2d): across the rail heads the
  corridor stage finds it from ~60–64 m; between the rails only the part above the rail head
  counts: in these tunnels the bed lies 0.26–0.34 m below the rail head beside a 0.57–0.60 m
  drainage trough, so a 0.35 m body lying across the track rises 0.01–0.09 m above the rail head:
  found from ~42 m when 0.10 m of it is above the rail head, from ~17 m at 0.05 m, not below the
  3 cm point rule; on a shallower bed (0.15 m above) from ~50 m; in the trough not at all.
* **At stations without a rail lock** (v0.6.2, §3.2) an object beyond 40 m is advisory
  (`CAUTION`, verified-clear distance 40 m) until the train is within 40 m of it.
* **A long object hanging high near the axis** (§3.3, 25.09): a cluster near the axis longer than
  3 m along the track, under 1.2 m tall and 1.0 m wide, with its lowest point above 1.6 m (the
  shape of the overhead ducts, trays and beams along the track) is advisory (`CAUTION`), also when
  it is a tray or pipe fallen into the envelope; with its bottom at or below 1.6 m this shape no
  longer demotes it (a STOP inside the envelope; review of 25.09). A higher threshold (1.8 or
  2.0 m) brings back a ride false event: the overhead structures read 1.68–2.65 m
  (78–129 m ahead; beyond ~100 m the height reference drifts by 0.2–0.5 m, EXPERIMENTS §1f, §2d).
* **A 10 cm object is resolved to ~20–25 m**: its face is one ring high beyond that
  (0.125° = 5 cm at 25 m) — the physical limit of the sensor's vertical resolution.
* **Far field**: between the height reference and the axis range only tall, grounded, short
  clusters alarm (§3.3c); a small box (< 0.6 m) at 120–200 m is advisory until the height
  reference reaches it. There the corridor follows the extrapolated curvature, also where one
  boundary ends early: a hall wall seen to 72–92 m puts switch parts at 147.5 m into it
  (4 STOP episodes of `squareT_platform_squareT_switch`, EXPERIMENTS §1h, 25.09).
* **An obstacle far ahead can extend the bed fit.** Beyond ~90 m the real bed stops
  returning; the base of an object standing there fills a bed bin and lengthens the fit, and
  the far curvature follows. On the moving ride this made edge fixtures 30–65 m *beyond* an
  injected object alarm in 19 of 3 060 frames (v0.6.1, EXPERIMENTS §2d) — while the object
  itself was confirmed, so the decision was unchanged. A bed bin should span the bed's width to
  count; tried 25.09 and not shipped (`track.floor_far_min_width`, off; EXPERIMENTS §1h): the
  width alone drops the real far bed (most real bins beyond 90 m are narrower than 1.1 m), and
  dropping only an object's foot removes these detections but lets other fixtures beyond the
  object confirm instead.
* **A sensor mounted on its side** (spin axis horizontal) is not recognised: in a square
  tunnel its "down" is a flat wall that passes for the bed, the configured mapping looks valid
  and the detector alarms on the wall (EXPERIMENTS §6). Such a mount is set with
  `sensor.forward/left/up`; every upright or inverted mount is found from the data.
* **Mount calibration** needs a rail pair within `calibration.max_frames` = 400 frames (40 s; a
  start inside a pressure gate or a switch cavern delays it) and corrects roll / pitch / yaw only
  as a whole-run constant; the cant of a curve is part of the rail plane and is not separated
  from the mount roll. Since 25.09 (`calibration.time_cadence`) its spacing and limits count
  periods of the input rate, so 5 Hz calibrates in the same 20 / 40 s as 10 Hz.
* **A lower input rate or a re-mounted rig** (SCORECARD #13, 25.09, EXPERIMENTS §1i): at 5 Hz
  the five obstacle-free recordings give 10 false events (13 at 10 Hz); with the rig rolled 3°
  11, pitched 3° 16. The pitch excess is marginal clusters in the platform and switch recordings
  that change when the rig's own sub-degree tilt is corrected; a provisional tilt taken on a
  canted stretch can be ~2° off in roll for the first 4–6 s, until the spaced observations
  replace it (`refine_min_deg`).

### Found by the organizers' test objects (set O, 24.09)

The organizers' `cloud_with_fake_obj` recording carries ten objects added by their own tool,
the one used for the hidden check; the shipped detector stops for 5 of the 8 objects inside the
envelope [organizers' synthetic: set O, 24.09], 6 of 8 since the hanging stage of 25.09 (§3.3
item 8). Per-object grade and the config sweeps:
[`P4_AUDIT.md`](P4_AUDIT.md) "Organizer synthetic-obstacle recording", EXPERIMENTS §2e. The
causes, each a limitation of the current rules:

* **Two infrastructure signatures demote in-envelope test objects** (§3.3 item 5b). `floating`
  made the 0.3 m cube hanging 1.0–1.4 m above the rail head (#2) advisory at 44–59 m (its
  lateral offset of 0.61–0.82 m exceeds `signature_min_lateral` = 0.6 m); since 25.09 (round 2,
  `floating_free_max_size`) it spares a compact cluster hanging free inside the envelope and #2
  is a STOP from 52.5 m (EXPERIMENTS §1i). It still makes the 0.3 m cube at the envelope edge
  (#4) advisory in every frame: its outermost point is 1.18–1.32 m off the axis measured from
  the rails, like the outside cube #5's (Q1 below). `elevated` demotes the 2 × 2 m box at the
  envelope top (#8) in 36 frames: a 2 m wide cluster with its bottom above 1.2 m, although that
  bottom is 2.2–2.9 m above the rail head, inside the envelope. Relaxing either rule wins those
  frames back but alarms on a 3.9–5.7 m long overhead structure ~104 m ahead of the train
  standing at the platform of `squareT_platform_squareT_switch` (five empty bags 107 / 20 →
  139–186 alarm frames / 23–26 events); a "short signature" variant that keeps both rules only
  for clusters longer than 3 m or farther than 100 m gives 352 instead of 303 STOP frames on the
  inside objects for 113 / 22; since 25.09 it is the flag `cluster.short_signature_max_length`
  (off, §3.3), measured on the ride 25.09 and not shipped (EXPERIMENTS §1f).
* **A 5 cm object hanging from the roof is found only within ~30 m** (#10; since 25.09, §3.3
  item 8; before that it was missed in all 42 visible frames). Only its lowest 0.2–0.36 m dips
  into the 3.0 m envelope, with 1–3 returns a frame, below the cluster minimum of 5 voxels. The
  hanging stage links them to the object's part above the envelope top: STOP in 15 frames from
  30.1 m (EXPERIMENTS §1i). Beyond ~50 m none of its returns is inside the envelope measured
  from the rails, and beyond 60 m the stage does not look. At stations without a rail lock the
  tops of platform columns 13–40 m ahead passed the same test in single frames (28 on the ride),
  none confirmed; since the rail-lock guard of 25.09, round 2 (`cluster.hanging_needs_rails`),
  the stage does not run on such frames, so a thin object hanging where the rails are not found
  (a station, a switch cavern) is not looked for either.
* **0.3 m cubes are confirmed only from 43–53 m** (#3 on the rail from 42.7 m; #2 from 52.5 m
  since 25.09, round 2, 34.0 m before). At 60–115 m such a cube returns 2–4 points a frame,
  below the 5-voxel minimum within 100 m, so a single frame cannot confirm a 0.3 m object much
  beyond 50 m with this sensor; lowering `min_points`, `min_points_far` or `gauge_min_points`
  changed nothing for them.
* ~~**A large near object shadows the rails.**~~ Fixed 25.09 (§3.1, §3.3; EXPERIMENTS §1h):
  while the 2 × 2 m box (#1) was 26 → 9 m ahead, the roof behind it tilted the bed fit (rail head
  at 20 m 0.8–3.5 m off), the bed 3–10 m ahead read as the obstacle (3.0 m reported in frames
  213–226) and, with a correct bed, box + a line at the corridor edge formed one cluster > 8 m that
  was dropped. Now every STOP on #1 reports the box's distance (largest error 0.46 m). Left: a
  shadow that starts beyond 30 m is not handled (`track.floor_shadow_range`; on set O the drift
  starts at ~26 m), and an object touching a long line at the corridor edge beyond 30 m is still
  dropped with it (`cluster.oversize_split_max_distance`).
* **The edge tests are ambiguous.** The organizers placed the objects from the sensor's axis,
  which runs at −0.24° to the rails in this recording; the detector's envelope follows the rails
  (§3.1), so the edge tests (#4–#7) sit within ±0.1–0.4 m of the envelope edge, on different
  sides depending on the frame. Measured from the rails, the 2 × 2 m box "at the edge, inside"
  (#6, missed) is outside in 117 of its 125 frames and the 0.3 m cube "just outside" (#5, no
  STOP) inside in 101 of 112; the 2 × 2 m box outside (#7) gets 6 false STOP frames. Removing
  the growing edge margin only added false STOPs (#7 6 → 40 frames, background 3 → 8). Which
  reference the envelope follows is an open question to the organizers
  ([`QUESTIONS.md`](QUESTIONS.md) Q1).
* ~~**`clear_distance` counts only confirmed obstacles**~~ (§4b) — capped since 25.09, round 2:
  on set O the criteria judgement of 24.09 (judge B, [`SCORECARD.md`](SCORECARD.md)) found 184
  object-frames with the decision `GO` and a `clear_distance` beyond an in-envelope object, 89 of
  them with object points inside the measured envelope: the 5 cm hanging object at 6.7–30 m (3–27
  points, up to 13 inside the envelope) read `GO` with a clear distance of 150–170 m (a STOP from
  30.1 m since 25.09, §3.3 item 8), the 0.3 m cube on the rail at 46–67 m `GO` with 165–185 m.
  `health.clear_cap` (candidate R1) caps the distance at the nearest unconfirmed or advisory
  cluster touching the envelope, columns excluded, and changes no decision: the set O overclaim
  172 → 82 object-frames. It **failed** its pre-registered clutter limit (the five obstacle-free
  recordings' median −5.5 % against −5 %; the ride −3.1 %) and was shipped on by the captain's
  delegate anyway (EXPERIMENTS §1i). Left: objects that form no cluster touching the envelope (far
  0.3 m cubes) stay uncapped.

### What the organizers' answers settle

* **Switches.** The switch state is not given to the detector: it follows the track its own
  model locks on (§3.1), and in a switch cavern, where the rails and walls diverge, the corridor
  beyond 40 m becomes advisory without a rail lock (§3.2). The organizers answered on 24.09 that
  glitches at switches will not count as a minus
  ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md) §5), so false alarms
  at stations and platforms come first: on `squareT_platform_squareT_switch` the 25 STOP
  episodes in 88 s sit at the platform end (82–84 m), on an overhead structure at ~104 m and on
  switch parts at 147.5 m while the train stands at the platform [real, 24.09]. The ~104 m
  structure (10 of the 25 episodes) is an overhead element running along the track near the axis,
  5.5 m long with its bottom at 2.2 m; `cluster.floating_long_min_length: 3.0` (on since 25.09)
  removes it (25 → 15 episodes, set O unchanged). The 82.9 m platform end (10 episodes) is an
  axis error of ~0.8 m at 83 m: a platform-side boundary joined by its fit to the diverging hall
  end bends the axis (2.5–4e-4 /m), and the rails' tangent, fitted with that curvature held,
  follows it. The far-rail check cannot correct it (the station's far rails are not found in two
  slabs), and a rule letting the wall side whose far bins follow its fit set the shape was tried
  and not shipped: it removes up to 14 of the 15 episodes but moves marginal frames of set O and
  new events onto the ride (EXPERIMENTS §1h, 25.09). The switch parts at 147.5 m
  pass the far-field rule like a person [real, 25.09, EXPERIMENTS §1f]; they are an axis error of
  the same kind: a hall wall seen only to 72–92 m sets a curvature that moves the corridor by
  1.4–3.4 m at 147 m. A far height threshold (0.8–1.0 m) costs set F 8–47 m of first confirmation,
  and the opt-in `cluster.far_axis_both_sides` 2 (a far obstacle on a bent axis needs both
  boundaries to reach it) removes them and 4 ride events but costs a person 1.9 m on gentle
  curves: tried, not shipped [real and synthetic, 25.09, EXPERIMENTS §1h].
* **Mount.** The test recordings use the mounts of the provided ones, the LiDAR 1 075 mm above
  the rail head on the train's centreline, with no numeric orientation (24.09, same source; §2).
  The unknown-mount case is gone, but the provided data hold two rigs (1.12 m and 1.51 m by the
  calibration), so the auto-calibration stays on as a safeguard.
* **The bed.** A 30 × 30 × 10 cm object lying on the bed between the rails is not an obstacle: it
  is not inside the train's envelope (25.09, [`organizers/answers.md`](organizers/answers.md) §8).
  The shipped envelope-floor policy (§3.3b) is theirs; the near-bed path stays off.

### Limitations of v0.5 (still valid)

1. **The corridor edge is where the remaining false alarms live.** Cable ducts, benches and
   platform-edge fittings run 1.5–1.6 m from the axis; the v0.5 strict gauge was 1.40 m wide at
   that height (v0.6: the envelope ends at 1.05 m and the advisory zone at 1.40 m), so a
   0.1–0.2 m axis error at 40–80 m puts a sliver of them inside. In v0.6 the edge structures
   that still alarm sit at 0.9–1.2 m (brackets, platform-end fittings; 18 of the ride's 47
   events, EXPERIMENTS §0), and the edge margin grows 0.15 m per 100 m. With the rails
   pinning the yaw the near axis is good to a few centimetres, but at 60–80 m the curvature
   from the walls (R ≈ 1000 m in the organizer bags) still leaves ~0.1–0.3 m of uncertainty.
   The edge margin of §3.2 trades those alarms against the last borderline frames of an object
   leaving the gauge; the trade-off is measured in EXPERIMENTS §1b (v0.5 kept the polygon
   exact, margin 0; v0.6 ships 0.15 m per 100 m, §1d row v0.6d).
2. **Curvature is only known where a boundary parallel to the track is visible.** Stations, switch
   caverns and tunnel-type transitions (walls diverge) leave the curvature to the previous frames
   (it decays towards straight) and the corridor is trusted only to 60–120 m (`axis_disagree_range`,
   `axis_one_side_range`); detections beyond are advisory. The bed-trough axis as a second opinion
   is designed, not implemented (EXPERIMENTS §5). When the boundary fit is lost the trusted axis
   shrinks by 20 m per frame to a floor of 45 m (the rail range + 15 m): on
   `squareT_platform_squareT_switch` this is the case in 14 % of the frames, while the train stands
   at the platform, and everything beyond 45 m is advisory there (review of 22.09).
3. **Height reference beyond the bed fit.** The bed fit ends at 50–110 m on the bags (median
   ~70–90 m) and its linear extrapolation was 0.3–0.65 m off at 85–105 m in the platform
   bags, which is why roof strips and far rails alarmed in v0.3 (§3.1). v0.5 trusts the
   extrapolation 20 m beyond the fit and as far as the side structures verify it (105–145 m on
   the bags), and demotes wide elevated clusters; it still does not *correct* the bed, so a
   0.5 m box beyond the verified range is advisory, not an alarm, and the far bins of the
   synthetic-on-real sets are limited by the same reference (their objects are placed on the
   extrapolated bed and are often fully occluded by the real one, EXPERIMENTS §2c).
4. **Accumulation multiplies returns, not resolution.** A distant object is sampled by the same
   rings and columns frame after frame, so the merged cluster is denser but not larger: a
   0.5 m box beyond ~118 m is one ring high and fails the 8 cm flatness rule with or without
   accumulation. Nothing is merged below 1 m/s (a stopped train) and nothing without a
   trustworthy speed; the measured effect on the real bags and on the injected sets is in
   EXPERIMENTS §1 and §2c, and the default is set from those numbers.
5. **Ego speed without odometry depends on wall texture.** The estimator reports a speed on
   55–96 % of the moving frames (median error 0.06–0.08 m/s against an ICP reference, 24.09) and
   "unknown" on the rest, so accumulation is intermittent without a given speed; a given speed
   (parameter or odometry) is the reliable path, and a wrong given speed is caught by the smear
   guards at the cost of the accumulation gain. Neither the estimate nor a perfect speed improves
   the organizers' check, so the estimator is off (EXPERIMENTS §9).
6. **Objects lower than 35 cm on the sleepers are filtered by design** (the low-hardware rule);
   a plank lying on the sleepers is invisible whatever its reflectivity.
7. **Tall narrow things and small floating things are advisory by design** (§3.3): a ladder standing
   on the track (> 2.2 m, < 1 m wide) or a sign hanging inside the gauge would be a warning, not an
   alarm; both are infrastructure signatures on the six bags, and the extended dataset is the place
   to revisit them. Retro-reflective small objects are advisory too (a reflective 0.5 m cube reads
   as a marker); a person, a train, a trolley or a crate keep their zone. The signatures were
   checked against hand-built clusters in the review of 22.09 (persons of 0.4–0.6 × 1.6–1.9 m on the
   bed at any lateral offset, a trolley, boxes, a train ahead all stay `gauge`); the one real gap it
   found — a person standing on a 1.1 m platform edge with the body inside the gauge was `wall_face`
   or `floating` — is closed by `wall_face_min_height` 2.0 m and `floating_max_height` 1.2 m. A
   person seen only above the shoulders (lowest point above 0.75 m) is still `floating` and
   advisory.
8. **Filters are hand-tuned on six bags**; every signature threshold was chosen from the
   per-track tables of the v0.3 full-rate runs (EXPERIMENTS §1b) and checked on the same
   bags, so the numbers on the hidden bag will be worse than on these. The extended dataset
   is needed to calibrate them and to measure real recall beyond one person at 55 m.
9. **Python and numpy, optional C++ kernels, no GPU**: per-frame cost on the 4-core sandbox is in
   EXPERIMENTS §3; the optional C++ kernels cut the detector time by 38–57 % with identical output
   and the GPU was evaluated and not used ([`ARCHITECTURE.md`](ARCHITECTURE.md) "Native kernels",
   "GPU: evaluated, not used"); the jury's i7-9700E stand is not open to the team before
   submission ([`organizers/answers.md`](organizers/answers.md) §6), so the 8-core figures come
   from the team's own 8-core machine ([`CAPTAIN.md`](CAPTAIN.md) action 7).
10. **No semantics**: a legitimately parked train, a maintenance trolley or a worker on the
    track are all "obstacles", which is the intended behaviour for a safety function.
