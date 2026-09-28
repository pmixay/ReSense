# Algorithm

> **Purpose:** how ReSense decides that the path ahead is blocked, stage by stage, structured
> after spec §5 "Описание алгоритма": problem → input data → point-cloud processing → decision
> rule → parameters → limitations. Code comments cite the section numbers: keep them.
> **Audience:** jury, P3 · **Owner:** P1 (structure), P3 (content) · **Language:** EN, summary RU
> **Last verified:** 2026-09-29: every parameter value against `configs/default.yaml` and
> `resense/config.py` of the sealed 27.09 detector, the results against the judgement of 28.09
> · **Status:** current

**Кратко.** ReSense описывает не объекты, а окружение: в каждом кадре лидара заново строится
модель пути (полотно, рельсы, ось с кривизной по стенам), вдоль оси откладывается габарит поезда
организаторов 2,1 × 3,0 м, и препятствием считается всё, что внутри габарита и не похоже на путь
или известную инфраструктуру. Кандидаты кластеризуются DBSCAN с радиусом, растущим с дальностью;
отдельные стадии ищут предметы на рельсах и тонкие висящие предметы; объект подтверждается за
0,5 с (5 кадров при 10 Гц). Небольшая обученная модель может задержать сомнительный дальний STOP
не более чем на 10 кадров, но никогда его не отменяет. Выход — решение GO / CAUTION / STOP /
FAULT, расстояние до препятствия, оценка проверенной свободной дистанции и состояние датчика.
Обучающие данные с препятствиями не нужны. Параметры — §5, ограничения — §6. Детектор опечатан
27.09 ([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)).

The code path is `resense.Detector.process()` (`resense/detector.py`), one method per stage;
each stage below names its module and its section of `configs/default.yaml`. The node, topics and
data flow: [`ARCHITECTURE.md`](ARCHITECTURE.md). Results: [`EXPERIMENTS.md`](EXPERIMENTS.md),
[`SCORECARD.md`](SCORECARD.md); "log §x" is a section of the full dated experiment log
[`archive/EXPERIMENTS_log_2026-09.md`](archive/EXPERIMENTS_log_2026-09.md), where each threshold
was measured.

## 1. Problem

A driverless metro train has a forward-looking 3D LiDAR (Hesai Pandar128, ~190 000 valid returns
per frame, none beyond ~210 m in the data; [`DATASET.md`](DATASET.md), [`SENSOR.md`](SENSOR.md)).
Ten times a second the system must answer: **is there a foreign object inside the space the train
is about to sweep, and how far ahead is it?** The objects are unknown (a person, a box, a plank, a
trolley, a hanging cable); the environment is known: a tunnel with two rails, a track bed, walls,
columns, ducts, platforms, pressure gates and switches. We therefore model the *environment*, not
the objects (spec §8.4): anything inside the train's envelope that is not track, bed or known
infrastructure is reported, whatever it looks like; no labelled obstacles are needed.

## 2. Input and coordinate frames

* `sensor_msgs/PointCloud2` on `/lidar_points` (`hesai_lidar`) or
  `/sensing/lidar/hesai128/pointcloud` (`lidar_livox`, full-turn recording): the organizers
  confirmed that the control data may use either pair, all from the same LiDAR. Fields
  `x y z intensity ring timestamp`, dual-return layout with empty `(0,0,0)` slots. The node takes
  one input at a time and restarts the detector for every new recording
  ([`ARCHITECTURE.md`](ARCHITECTURE.md) "The node").
* Decoding (`resense/pointcloud.py`; in the node `resense_ros/fastcloud.py`, the same arrays)
  drops the empty slots and returns closer than `sensor.min_range` (2.5 m, the train's own nose)
  or beyond `sensor.max_range` (250 m).
* Three axis strings (`sensor.forward/left/up`, default `-y/+x/+z`) and the mount rotation of §2b
  map the sensor onto the **vehicle frame** X forward, Y left, Z up, used by every later stage.

Height, lateral offset and yaw of the track are re-estimated every frame (§3.1); the mount itself
is found once from the data (§2b). The organizers stated that the LiDAR position is not fixed
between trains ([`organizers/QA_session.md`](organizers/QA_session.md) fact 7) and that the test
recordings use the mounts of the provided ones, 1 075 mm above the rail head on the centreline,
with no numeric orientation ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md)).
The provided data hold two rigs: the calibration measures 1.12 m above the rail head on
`roundT_doubleT` (4.5 cm from the stated height) and 1.51 m with a +3.0° roll on `doubleT_obstacle`.

### 2b. Mount auto-calibration (`resense/calibration.py`, section `calibration`)

The calibrator hands the detector a rotation `R` (`p_processed = R · p_configured`) found from:

1. **orientation** — only if the configured mapping shows no rail pair ahead: the 8 axis-aligned
   rotations that keep the spin axis vertical are scored by the rail pair they reveal (two ridges
   1.59 m apart, 0.08–0.5 m above a bed below the sensor, along +X); a winner of
   `orientation_votes` = 2 frames is adopted. Upside-down, backwards, `+x`-forward and rolled mounts
   are recovered to < 0.5° (`tests/test_calibration.py`, log §6); sideways mounts are not searched;
2. **roll** from the height difference of the two rail heads (the envelope lives in the rail plane);
3. **pitch** from the slope of the bed fit at X = 0 (the train rides on the track);
4. **yaw** from the rail tangent, only above `min_yaw_deg` = 3° (the track model follows the rest).

On a moving train the per-frame roll swings by ±1° with cant and body lean, so the tilt is taken
in two stages: a **provisional** tilt from the first `provisional_frames` = 5 observations only for
a clearly tilted rig (≥ `provisional_min_deg` = 2.5°: the `doubleT_obstacle` rig after 0.5 s), and
the **final** tilt, the median of `frames` = 20 observations every `obs_spacing` = 10 frames (20 s;
p90 error 0.5° on the ride), applied above `apply_min_deg` = 0.75° and then frozen. Tilts above
`max_tilt_deg` = 15° are rejected; without a rail pair in `max_frames` = 400 frames the calibrator
gives up (`fallback`, configured mapping kept). A change up to `reseed_keep_max_deg` = 1° rotates
the track model into the corrected frame; a larger one re-seeds it. A track reported as a STOP stays
reported for `tracking.reseed_hold` = 5 frames from any change, matched or not. Afterwards the same
measurement runs every `monitor_period` = 50 frames, and a median of the last `drift_window` = 10
checks above `drift_warn_deg` = 1.5° (a mount knocked loose) is reported in `health`, never applied.
Spacings and limits count periods of the measured input rate (`time_cadence`), so 5 Hz input
calibrates in the same 20 s. The status JSON carries `mount` (status pending / provisional / ok /
identity / fallback, orientation, roll, pitch, yaw, height, lateral, drift); a known mount can be
frozen with `sensor.roll_deg/pitch_deg/yaw_deg` or the node's `mount_*_deg` / `sensor_*` arguments.

## 3. Processing pipeline

**The model in formulas.** With X along the track (vehicle frame), the track model of §3.1 gives
per frame

```
axis        y_c(X)    = c + tan(ψ)·X + ½·κ·X²          (c centre, ψ yaw, κ = 1/R curvature)
rail head   z_rail(X) = z_floor(X) + r                  (z_floor fitted bed, r rail offset)
corridor    dy = y − y_c(X),   h = z − z_rail(X)       (per point)
envelope    E = { |dy| ≤ 1.05 m, 0.12 m ≤ h ≤ 3.0 m },  advisory band |dy| ≤ 1.40 m
DBSCAN      eps(r) = 0.35 m · (1 + r / 40 m)           (r = range of the point)
```

A cluster of points in `E` that is not explained by infrastructure (§3.3) and persists (§3.5) is
an obstacle; its distance is the smallest X of its points inside `E` (§4).

### 3.1 Track model (`resense/track.py`, section `track`)

* **Bed height `z_floor(X)`.** Per bin (2 m, 5 m beyond 40 m) the 20th percentile of Z in a ±1 m
  band around the previous axis; a robust line through the near bins, far bins kept within 0.35 m
  of it; a quadratic only with ≥ 4 consistent far bins bending less than a 1 500 m vertical curve;
  linear extrapolation beyond; EMA across frames. **Shadow of a large near object**: two adjacent
  bins > `floor_shadow_height` = 1 m above the previous bed, the first within
  `floor_shadow_range` = 30 m, mean the bed behind an object is hidden; then only bins near the
  previous bed are fitted, the rail pair is searched in front of the object, and with fewer than 5
  bed bins there the previous bed and rails are held (at most `floor_shadow_max_hold` = 20 frames
  in a row). Without it the organizers' 2 m box 26 → 9 m ahead was reported at the bed (log §1h).
* **Verified extrapolation `floor_verified`.** The bed stops returning at ~100 m, but the foot of
  walls, benches and ducts is seen to the end of the range at a constant height above the rail
  head. Per 5 m bin the lowest point in the side band |dy| 1.6–3.5 m is compared with the
  extrapolated bed; the extrapolation stays verified while the median deviation over the last 30 m
  is within `floor_verify_tolerance` = 0.5 m (a vertical curve or a platform ends it). The height
  reference is trusted to `max(fit end + floor_valid_margin (20 m), floor_verified)`.
* **Rail head, centre and yaw.** A lateral height profile at 4–30 m in 5 cm bins (85th percentile),
  built in the previous axis' coordinate so the rails stay straight lines in a curve; the rails
  are the pair of ridges `rails_spacing` = 1.59 m apart with a head 0.08–0.5 m above the bed. The
  pair is located again in `rails_yaw_slabs` = 3 along-track slabs; a line through their midpoints
  (previous curvature held) gives `c` and `tan(ψ)`: ±2 cm per ridge over 26 m ≈ 0.1°.
* **Curvature from the walls.** Per 4 m bin between 6 and 160 m, in a band 1.6–2.8 m above the
  rail head (above platforms, below the roof), each side's boundary is the 90th percentile of
  |dy|; a robust quadratic per side **with the tangent fixed by the rails** gives κ. A boundary
  that does not fit with that tangent (a diverging hall wall) is rejected; if the sides disagree by
  more than `axis_sides_max_disagreement` (6.7e-4 m⁻¹, R 1 500 m) the **nearer** one wins. Clipped
  to |tan ψ| ≤ 0.09 and R ≥ 150 m, smoothed, and rate-limited to `axis_max_yaw_rate` = 0.003 rad
  (0.17°) and `axis_max_curvature_rate` = 1e-4 m⁻¹ per input period (a train at 15 m/s on
  R = 700 m yaws 0.12° per frame) after `axis_warmup_frames` = 5 frames.
* **Trusted axis range `axis_valid`.** The last observed boundary bin + 15 m (+50 m on straight,
  well fitted track with agreeing sides); at most `axis_one_side_range` = 120 m with one boundary
  and `axis_disagree_range` = 60 m when the sides disagree; −20 m per frame without a fit, down to
  the height reference. Beyond it clusters are advisory (`beyond_axis`). A far rail-pair
  cross-check of the wall curvature (`rails_far_check_enabled`) exists and is off (no evaluation
  on real recordings).

### 3.2 Clearance-gauge corridor (`resense/gauge.py`, section `gauge`)

The gauge is a closed polygon in `(dy, h)` swept along the axis: **the train envelope the
organizers gave, 2.1 m wide × 3.0 m high, protruding elements included**
([`organizers/QA_session.md`](organizers/QA_session.md) fact 1): |dy| ≤ 1.05 m, from 0.12 m above
the rail head (rail heads, fastenings and joint bars stay out; lower objects are §3.3b's) to 3.0 m.
The **advisory** polygon is the same profile widened by `warning_margin` = 0.35 m (|dy| ≤ 1.40 m):
a confirmed object there is a `warning` (`CAUTION`), not an alarm — a person on a platform or beside
the track is not an obstacle unless inside the envelope (the organizers' answer).

Points between `range_min` (3 m) and `range_max` (250 m) are tested against both polygons (a
bounding-box prefilter, then a vectorised even-odd test); points in the advisory polygon are the
*candidates*, their strict membership is kept per point. The **edge margin**
(`edge_margin_per_100m` = 0.15 m per 100 m, 0.3 m at 200 m) counts a point as strictly inside only
that far inside the lateral edge: the axis is uncertain by ~0.1°.

**Without rails the far corridor is advisory** (`no_rail_range` = 40 m). In a frame without a rail
pair in the near range (a station with the rails in shadow, a switch cavern) the axis rests on
walls, which at stations are platform edges and end structures: clusters beyond 40 m are advisory
(`beyond_axis`) and the clear distance is capped at 40 m; nearer, the strict decision stays (a 0.1°
error is 7 cm at 40 m). **Near the train the envelope is also measured from the sensor axis**
(`gauge.reference` 3, §3.6; the earlier variant `gauge.axis_union` is off).

### 3.3 Candidate clustering and infrastructure filters (`resense/clustering.py`, section `cluster`)

Everything is **range-adaptive**, because a 0.5 m object gives ~500 returns at 20 m and ~7 at
100 m (`resense/sensor.py`):

1. coordinates are scaled by `1 / (1 + r / range_scale)` with `range_scale` = 40 m, so a fixed
   voxel (`voxel` = 5 cm) and a fixed DBSCAN radius (`eps` = 0.35 m) grow linearly with range;
2. candidates are voxel-downsampled in that space (merges dual returns; the voxel count is a proxy
   for distinct rays) and clustered with DBSCAN (`min_samples` = 3) on scipy's `cKDTree` with
   scikit-learn's exact labels (`resense.clustering.dbscan_labels`);
3. each cluster gets a bounding box, the distance of its nearest point inside the envelope
   (`gauge_distance`), its centroid's lateral offset, lowest and highest point and mean intensity;
4. clusters that describe infrastructure rather than obstacles are removed, in this order:

| filter | rule (defaults) | what it removes |
|---|---|---|
| size | extent > 8 m or height < 0.08 m; a cluster > 8 m whose part inside the strict envelope is ≤ 3 m long and starts within 30 m is kept as that part (`oversize_split_*`: an object touching a long line at the corridor edge) | walls, floor noise |
| point count | < 5 voxels (< 3 beyond 100 m) | noise |
| thin linear | length > 3 m, width < 0.35 m, height < 0.25 m | rails, pipes, cables, duct edges |
| low hardware | top < 0.35 m, width < 0.4 m, height < 0.3 m | clamps, joint bars, cables on the sleepers |
| wall-like | height > 1.9 m and \|lateral\| > 1.2 m, or height > 1.9 m, length > 4 m, width < 1.5 m; kept when it has ≥ 10 voxels in the strict envelope within 20 m (`wall_keep_*`) | columns, gate frames, platform walls |
| linear side structure | aspect > 5, height < 0.8 m, \|lateral\| > 0.8 m | platform edges, ducts, cabinet rows |

5. the surviving cluster gets a **zone**: `gauge` if ≥ `gauge_min_points` (3) voxels lie inside
   the strict polygon, otherwise `warning`; it is demoted to `warning` beyond the trusted axis
   (`beyond_axis`) or entirely above `overhead_min_height` (3.0 m, the envelope top);

5b. **infrastructure signatures** demote a gauge cluster to `warning` with their name as `reason`
   (0 switches a rule off); derived on the six organizer recordings (log §1b), checked against
   hand-built persons, trolleys, boxes and a train ahead, which stay `gauge`:

   | signature | rule (defaults) | what it is | why a listed obstacle does not match |
   |---|---|---|---|
   | `column` | height > 2.2 m and width < 1.0 m, and either \|lateral\| > `signature_min_lateral` (0.6 m) or width ≥ `column_min_width` (0.25 m); the width is read between the 5 % and 95 % lateral quantiles when the trimmed tails span ≥ 0.25 m (`column_width_trim`) | columns of the double-track tunnel, posts, gate legs | a person is 1.7 m; a trolley or train is wider; **a thin cable hanging near the axis stays an obstacle** |
   | `elevated` | lowest point > 1.2 m above the rail head and width > 2.0 m | roof strips and beams read too low by the extrapolated bed | listed objects stand on the bed; a train ahead reaches the polygon bottom |
   | `floating` | lowest point > 0.7 m, height < 1.2 m, width < 1.0 m and \|lateral\| > 0.6 m; near the axis only when longer than `floating_long_min_length` (3.0 m) with the lowest point above `floating_long_min_bottom` (1.6 m); never a compact free-hanging cluster (every extent ≤ `floating_free_max_size` 0.5 m, outermost point ≤ `floating_free_max_dy` **1.2 m** off the axis, top ≤ `floating_free_max_top` 2.5 m) | signs, lamps, brackets on the wall; ducts, trays and beams along the track overhead | an object on the track touches the ground; an object hanging into the envelope near the axis, or a tray fallen lower than 1.6 m, stays an obstacle |
   | `edge` | \|lateral\| > `edge_min_lateral` (1.0 m), length > 2.5 × width, height < 1.0 m | duct, bench and platform-edge fragments along the corridor edge | boxes and persons are not elongated |
   | `wall_face` | height > 2.0 m, top above 2.8 m, and the part below has \|dy\| ≥ 0.3 m everywhere and > 1.3 m somewhere | platform-hall end walls, portal jambs | a train ahead fills the corridor centre; a person is lower than 2.0 m (also on a 1.1 m platform edge) |

   A demoted cluster is never dropped: a persistent object that stops matching (a person stepping
   away from a column) returns to `gauge` through the zone history, and near an obstacle the shape
   signatures give way (§3.5). `short_signature_max_length` is off (it added ride false alarms);
6. **retro-reflector rule** (`retro_intensity`, off): when on (100), a cluster lower than 1.2 m and
   narrower than 0.8 m with ≥ 50 % of its returns above 100 % reflectivity is a sign (`retro`)
   ([`SENSOR.md`](SENSOR.md) §3.3);
7. a **visibility score** (voxels against the returns a target of that size should give at that
   range, saturating at `visibility_ratio` = 15 %) feeds the tracker's confidence;
8. **thin objects hanging from above** (`hanging_*`): a cable dipping 0.2–0.4 m below the envelope
   top gives 1–3 returns there, below the 5-voxel minimum. Points near the axis (|dy| < 0.8 m) from
   1.8 m up to 0.6 m above the envelope top are linked at the corridor radius; a group with a voxel
   inside the strict envelope and one above it, ≤ 0.5 m along and across the track and ≤ 60 m away,
   is a gauge cluster of kind `hanging`. It yields to an overlapping gauge obstacle and runs only
   with a rail pair in the near range (`hanging_needs_rails`: else station column tops pass).

### 3.3b Low objects on the track (`resense/lowobj.py`, section `lowobj`)

The organizers' size criterion is **300 × 300 × 100 mm** (Q&A fact 2). Such an object is lower than
the polygon bottom (0.12 m above the rail head), so the corridor cannot see it; it is, however, an
anomaly of the *track bed*, whose cross-section (rails, fastenings, bed, drainage trough) repeats
every metre:

1. the **bed template** `h_bed(dy)` (bed height above the rail head at lateral offset `dy`): the
   30th percentile per 2.5 cm lateral bin at 4–30 m, dilated by ±5 cm, EMA 0.8, learned only while
   the rail pair is locked;
2. per 2 m along-track bin the **local offset** from the template is the median residual of the
   bed-like points; a bin without bed returns ends the stage's range (`range_max` = 60 m);
3. a point inside the envelope width, below the polygon bottom, with a residual above `min_excess`
   = 5 cm **and itself at least `min_point_top` = 3 cm above the rail head** is a low candidate;
4. low candidates are clustered on their own with a tighter radius (`lowobj.eps` = 0.2,
   range-normalised: 0.48 m at 56 m); a low cluster is ≤ 1.5 m long, 0.15–2.2 m across (a person
   lying across the track fits), has ≥ 3 voxels and reaches the rail-head plane (`min_top` = 0); it
   is a gauge obstacle of kind `low`, confirmed after `tracking.low_confirm_hits` = 5 hits;
5. it is dropped when corridor candidates taller than `foot_max_top` = 0.35 m stand in its footprint
   (the foot of a sign or a person) or a corridor cluster overlaps it (one detection per object).

**Why the rail-head rule.** The metro bed carries fixtures 5–40 cm tall every few tens of metres
(train-control inductors, drain covers, cable crossings), geometrically a 30 × 30 × 10 cm box and
below the rail head by design. Every bump above the bed gave ~1 350 false events on the 20-minute
ride, a cluster top at the rail head ~800 (joints, guard and check rails); every candidate point
≥ 3 cm above the rail head leaves 2 on the 13 worst files of the ride and still finds a 10 cm box on
a rail head at 10–25 m (log §1d, `tests/test_envelope.py`). The organizers confirmed the policy: an
object on the bed between the rails is not inside the envelope, so it is not an obstacle
([`organizers/answers.md`](organizers/answers.md) §8). `min_top` / `min_point_top` −1 restore the
bed-level policy for a line with a clean bed; the central near-bed path (`lowobj.near_enabled`) is
off, because a compact inductor returns the same scan line as a box (log §1e).

**Objects straddling the envelope floor** (`straddle_*`). The organizers' object across the right
rail of `doubleT_obstacle` (0.45 × 0.6 × 0.3 m, 56 m) returns ~21 points, most below the rail head
and ~3 above the envelope floor, so it fell between the two stages. A third clustering joins the
bed anomalies without the 3 cm rule and the corridor points less than `straddle_band` = 0.30 m above
the floor; a cluster is `low` when its top reaches `straddle_min_top` = 0.10 m above the rail head
(rail fittings reach 1–8 cm), it is ≥ `straddle_min_width` = 0.35 m across and ≤
`straddle_max_length` = 0.8 m along the track (trackside devices are mounted along the rail,
0.2–0.3 m across). The object is a STOP in 123 of the 126 frames after the person leaves it (§6);
the margins are thin on its side (top 0.11–0.16 m, width 0.38–0.50 m; log §0). Puddles return
nothing or mirror images below the bed (negative residuals) and are ignored by construction.

### 3.3c The far field of a straight tunnel

On a straight tunnel the height reference, not the axis, limits the corridor: the bed fit ends at
70–90 m, its verification at 100–145 m, while the walls confirm the axis to ~200 m. The
extrapolated rail level runs 0.1 m low at 85 m and 0.4–0.5 m at 150–200 m (log §2d): enough to lift
far-bed returns into the polygon bottom, not to change whether a person is inside a 3 m envelope. So **between the height reference and the
axis range a cluster is an obstacle only if it is at least `far_min_height` = 0.6 m tall, at most
`far_max_length` = 3 m long and reaches below `far_max_bottom` = 1.0 m** — a face standing on the
track, not a surface at grazing incidence nor a sign above the corridor (`beyond_height_ref`
otherwise).

### 3.4 Ego speed and multi-frame accumulation (`resense/egomotion.py`, `resense/accumulate.py`, section `accumulation`)

Beyond ~150 m a person returns 3–5 points per frame, near the clusterer's floor. The candidates
beyond `min_range` = 40 m of the last `n_frames` = 5 frames can therefore be merged before
clustering: stored in track coordinates (X, dy, h), shifted by `v · dt` per frame and re-embedded
with the current track model, so they follow the curve; the voxel grid makes a static object
denser, not doubled. **This runs only with a speed the caller gives** (`Detector.process(frame,
ego_speed)`, the node's `ego_speed_mps` / `speed_topic` / `odom_topic`) of at least `min_speed` =
1 m/s; the organizers' recordings carry no odometry (Q&A fact 6), so the delivered path is
single-frame. Merged clusters get a higher voxel bar (`1 + n_merged · min_points_scale`, ×1.5 for 5
frames), and a **smear guard** re-describes a merged cluster longer than 2 m or wider than 1 m from
its current-frame points (a wrong speed or a moving object), so a wrong speed degrades to the
single-frame result. The LiDAR-only estimator (`estimate_speed`, off) cross-correlates the wall
texture along the track between frames (ICP is degenerate along a straight tunnel,
[`RESEARCH.md`](RESEARCH.md) §2); it is accurate (median error 0.06–0.08 m/s), but neither it nor a
perfect speed improved the organizers' check, and it added false alarms (log §1b, §9).

### 3.5 Temporal persistence (`resense/tracking.py`, section `tracking`)

**Association.** Greedy nearest neighbour on predicted centroids (constant velocity per track),
gate `gate_base + gate_per_m · distance` (1.5 m + 2 cm/m), widened along X only by
`ego_speed_max · frame_dt` (25 m/s × 0.1 s = 2.5 m) towards the vehicle, because without odometry a
static obstacle approaches at the train's speed. Confidence rises by `conf_gain · score` per hit and
falls by `conf_decay` per miss; a track is dropped after `max_misses` = 3.

**Confirmation and zone.** A track must have `confirm_hits` = 3 hits over `confirm_time_s` = 0.5 s
of sensor time (5 frames at 10 Hz, 3 at 5 Hz), be matched in `min_hit_fraction` = 60 % of its last
`hit_window` = 10 frames (a structure flickering into the corridor never qualifies) and be matched
now (or held, §4). Its **zone** is voted over its last `zone_window` = 10 hits: `gauge` when
`zone_min_fraction` = 60 % were inside the strict envelope, so an object first seen beyond the
trusted corridor, or an edge structure flickering with the axis, stays advisory until the history is
clear; also while `column_hold` = 2 of those hits were a `column`.

**Near an obstacle the shape signatures give way** (a signature may keep a track from being
confirmed, not take a confirmed obstacle down):

* **near escalation** (`near_escalate_*`): a track whose last 5 hits each had ≥ 10 voxels inside the
  strict envelope within 35 m is a STOP whatever shape signature or zone vote demoted it (never a
  `column`, `beyond_axis` or `beyond_height_ref` demotion);
* **STOP keep** (`stop_keep_*`): a track that was a STOP in the previous frame counts a cluster with
  ≥ 10 strict voxels demoted only by a shape signature as a hit inside the envelope, and a
  one-scan-line cluster inside the envelope may continue it; never starts a track, and only while
  its last clean hit is at most `stop_keep_max_s` = 10 s of sensor time ago;
* **rail start** (`lowobj.rail_start_within` = 4 m): a narrow (≤ 0.45 m) low cluster nearer than
  4 m on a rail line, at most 5 cm above the rail head's own returns, is rail geometry (a bag
  starting at a standing train showed the rail heads at 2.9–3.1 m).

**Far evidence for approaching tracks** (`thin_far_min_distance` = 60 m, `cluster.weak_min_points`
= 4). Beyond 60 m a scan line inside the envelope, or a cluster one voxel under the point-count bar,
may start or continue a track when unambiguous; while its gauge vote needs such hits, the track is a
STOP only while its distances approach on a line in sensor time (`approach_hits` 5, 2–25 m/s,
RMS ≤ 0.5 m), and advisory otherwise, never hidden.

### 3.6 Envelope reference near the train and the learned track opinion

**Envelope reference** (`gauge.reference` 3; `resense/gauge.py` `reference_offset`, `union_shift`).
The organizers place their test objects from the sensor's X axis, which on straight track runs
0.22–0.29° off the rails in most recordings (0.2 m apart at 50 m); §3.2 measures from the rails.
Within `reference_range` = 60 m, on straight track (|κ| ≤ 2e-4 m⁻¹) with the rail pair locked, the
strict membership and the shape rules read the **union** of the two envelopes: with `c(X)` the rail
axis in the sensor frame, clamped to ±`reference_max_offset` = 0.2 m, a return takes the lateral
`dy + c` only where that is nearer the centre than `dy`, so neither side of the rails' envelope is
ever narrowed. The candidates, the reported lateral and distance, the bed, low-object, rail-start
and clear-distance stages and the rules for structure along the track (`reference_along_rails`:
linear side structure, `edge`) keep the rails. Beyond 60 m, on curves and without a rail lock the
envelope is the rails' alone.

**Learned track opinion** (`tracking.doubt_*`, `resense/opinion.py`,
`resense/models/track_opinion.json`). When the rules are about to make a track a STOP beyond
`doubt_near` = 25 m, a gradient-boosted tree ensemble (60 trees, 19 features of the last 10 matched
clusters: range, lateral stability, approach consistency, size and height, strict-envelope share,
demotion history) scores it. Below `doubt_threshold` = 0.015 the track stays advisory (`doubt`) for
at most `doubt_extra_hits` = 10 frames over its whole life (misses spend the budget); it is released
at once within 25 m, and a cluster ≥ `doubt_body_height` = 1.0 m tall within `doubt_body_range` =
40 m is never delayed. The opinion **never vetoes and never takes a STOP down**. Negatives: the
rules' STOPs on the ride and the empty recordings; positives: synthetic sequences; trained grouped by
ride piece / recording (`scripts/track_opinion.py`), threshold a 2× margin below the highest one
that delays no held-out synthetic sequence. Run with models that never saw the ride piece
(`scripts/opinion_crossfit.py`), it cuts the ride's false events from 43 to 37
([`DECISIONS.md`](DECISIONS.md) row 19).

## 4. Decision rule

A frame reports `obstacle = true` when at least one track is **confirmed**:

* ≥ `confirm_hits` = 3 hits (low objects `low_confirm_hits` = 5) spanning ≥ `confirm_time_s` =
  0.5 s of sensor time, matched in ≥ 60 % of its last 10 frames, confidence ≥ `conf_threshold` =
  0.6;
* matched in the current frame, or reported in the previous frame and missed for at most
  `hold_misses` = 1 frame (then at its predicted distance; a code default in `resense/config.py`);
* zone `gauge`: ≥ 60 % of its last 10 hits had ≥ `gauge_min_points` voxels inside the strict
  envelope and none of the demotions of §3.3 (signature, beyond the trusted axis or height
  reference, overhead, retro) — unless the near escalation or the STOP keep (§3.5) overrides a
  shape signature — and it is not withheld by the learned opinion (§3.6); `tracking.reseed_hold`
  holds a STOP through a mount-calibration change (§2b).

`timing_ms.stages` sums the six historical detector stages through tracking. `health` measures
mount serialization and health monitoring; `result` measures `FrameResult` construction; `total`
measures from detector entry through result construction. Detector health consumes the prior
completed `total` and identifies its one-frame age, so the health call measures its own cost on
the following frame. This is a telemetry correction; decisions do not use latency by default.

`nearest_distance` is the along-track distance of the nearest confirmed gauge track, to the
object's nearest point inside the envelope. Confirmed advisory tracks set `warning`, not
`obstacle`. Every confirmed track (distance, lateral, size, confidence, age, kind, reason), the
track model, `mount`, `health`, `clear_distance`, the ego speed and per-stage timing go into the
status JSON ([`ARCHITECTURE.md`](ARCHITECTURE.md) "Data flow and formats").

**Cost of the rule.** An object appearing inside the envelope is reported after 0.5 s (11 m at
80 km/h). One tracked while it approached — a person stepping in from the side, a far object the
train nears — costs nothing extra: the persistence clock runs while the track is advisory. On
`doubleT_obstacle` the crossing person is a STOP from frame 8, its first frame inside the envelope.

### 4b. Outputs for the train: decision, verified-clear distance, health

The organizers asked "can we go / is there an obstacle / how far" (Q&A fact 9). Besides the flag
and the distance every frame carries:

* **`clear_distance`** (`/resense/clear_distance`) — metres of track estimated clear: the nearest
  confirmed obstacle, else the **monitored range** `min(visibility, trusted corridor, gauge
  range)`, *visibility* being the X of the 20th farthest return within 3 m of the axis (the
  sightline in a curve, the end of a platform hall). Without changing any decision it is also
  capped at the nearest unconfirmed or advisory cluster touching the strict envelope (columns
  excluded; `health.clear_cap`), at the predicted distance of a reported track missed this frame
  (`clear_cap_lost`), at the nearest supported scan-line cluster inside the envelope
  (`clear_cap_thin`) and at sparse envelope evidence chained over `clear_cap_persist` = 4 frames
  (`resense/evidence.py`). A blinded sensor, a lost track model or invalid input make it 0. **It is
  an estimate, not a guarantee of an empty track** (§6).
* **`health`** (`resense/health.py`, `/resense/health`): `ok` / `warn` / `error` — returns per frame
  (error below 20 000, warning below half the running median), returns closer than 2.5 m (> 20 %: a
  dirty window), empty 10° sectors in the central ±30° (view blocked), visibility < 60 m, rail lock
  in < 30 % of the last 20 frames, latency p95 over 100 ms, calibration fallback or drift. An error
  sets the monitored range to 0. `decision_level` is `level` without the latency warning (a slow
  machine is not an unsafe path; `health.latency_affects_decision` false).
* **`decision`** (node, `/resense/decision`): `STOP` for a confirmed obstacle inside the envelope;
  `FAULT` on a health error, on a processing exception (the detector is reset after 5 in a row),
  when no frame arrived for `stale_timeout` = 0.5 s, or on invalid input clocks; `CAUTION` for an
  advisory object, a warning in `decision_level` or a result made while the node catches up; else
  `GO`. A STOP is held until a fresh valid non-STOP result ([`ARCHITECTURE.md`](ARCHITECTURE.md)
  "Freshness contract"). `CAUTION` is advisory; the alarm is `STOP` (`/resense/obstacle_detected`).

## 5. Parameters that matter most

All detector parameters live in `configs/default.yaml` (`resense:` root key), loaded by the CLI and
the ROS node (the ROS package carries a copy, kept identical by `scripts/sync_params.sh --check`
in CI); the one exception is `tracking.hold_misses`, a code default in `resense/config.py`. The
node's own parameters are in [`ARCHITECTURE.md`](ARCHITECTURE.md) "The node". Values as sealed on
27.09:

| parameter | default | effect |
|---|---|---|
| `sensor.forward/left/up`; `min_range`, `max_range` | `-y/+x/+z`; 2.5 m, 250 m | sensor → vehicle axes (the calibration corrects upright / inverted mounts); returns kept |
| `gauge.profile`, `warning_margin`, `range_min` / `range_max` | \|dy\| ≤ 1.05 m, h 0.12–3.0 m; 0.35 m; 3 / 250 m | what counts as "in the way" (the organizers' envelope), the advisory band, how far the corridor is evaluated |
| `gauge.edge_margin`, `edge_margin_per_100m` | 0, 0.15 m | lateral margin inside the edge required for the strict decision, growing with range |
| `gauge.no_rail_range` | 40 m | without a near rail pair, clusters beyond are advisory and the clear distance is capped there |
| `gauge.reference`, `reference_range`, `reference_max_offset`, `reference_max_curvature` | 3, 60 m, 0.2 m, 2e-4 m⁻¹ | union of the rails' and the sensor-axis envelope near the train (§3.6); 0 = rails only |
| `track.rails_range`, `rails_spacing`, `rails_yaw_slabs` | 4–30 m, 1.59 m, 3 | rail pair search and the yaw from it |
| `track.walls_range`, `walls_band`, `walls_bin` | 6–160 m, 1.6–2.8 m, 4 m | curvature from the tunnel boundaries |
| `track.axis_valid_margin`, `axis_valid_straight_bonus` | 15 m, 50 m | trusted axis beyond the last boundary bin |
| `track.axis_one_side_range`, `axis_disagree_range`, `axis_sides_max_disagreement` | 120 m, 60 m, 6.7e-4 m⁻¹ | trusted range with one boundary or disagreeing ones |
| `track.axis_max_yaw_rate`, `axis_max_curvature_rate` | 0.003 rad, 1e-4 m⁻¹ per period | how fast the corridor may swing; 0 = unlimited |
| `track.floor_valid_margin`, `floor_verify_tolerance`, `floor_verify_band` | 20 m, 0.5 m, \|dy\| 1.6–3.5 m | how far the height reference is trusted beyond the bed fit |
| `track.floor_shadow_height`, `floor_shadow_range`, `floor_shadow_max_hold` | 1.0 m, 30 m, 20 frames | bed and rails in front of a large near object |
| `cluster.eps`, `range_scale`, `voxel`, `min_samples` | 0.35 m, 40 m, 5 cm, 3 | cluster granularity against range |
| `cluster.min_points`, `min_points_far`, `far_range`, `gauge_min_points` | 5, 3, 100 m, 3 | sensitivity at range against noise |
| `cluster.max_extent`, `oversize_split_max_length`, `oversize_split_max_distance` | 8 m, 3 m, 30 m | oversize clusters; an object touching a long edge line |
| `cluster.wall_keep_gauge_voxels`, `wall_keep_distance` | 10, 20 m | a tall side cluster with real envelope mass near the train is kept |
| `cluster.hardware_*`, `thin_*`, `wall_*`, `linear_*`; `column_*`, `elevated_*`, `floating_*`, `edge_*`, `wall_face_*`, `signature_min_lateral`, `retro_intensity` | tables in §3.3; retro 0 (off) | infrastructure removal (`hardware` also hides objects under 35 cm on the sleepers) and signatures (advisory only; 0 switches a rule off) |
| `cluster.floating_long_min_length` / `_min_bottom`; `floating_free_max_size` / `_max_dy` / `_max_top` | 3.0 m / 1.6 m; 0.5 m / 1.2 m / 2.5 m | long overhead structure near the axis is `floating` only above 1.6 m; a compact cluster hanging free inside the envelope never is |
| `cluster.far_min_height`, `far_max_length`, `far_max_bottom`; `overhead_min_height` | 0.6 m, 3 m, 1.0 m; 3.0 m | what may alarm between the height reference and the axis range; clusters entirely above 3 m are advisory |
| `cluster.hanging_enabled`, `hanging_max_distance`, `hanging_max_size`, `hanging_needs_rails` | true, 60 m, 0.5 m, true | thin objects hanging into the envelope (§3.3 item 8) |
| `cluster.weak_min_points` | 4 | far weak clusters for approaching tracks |
| `lowobj.min_point_top`, `min_top`, `min_excess`, `eps`, `range_max` | 0.03 m, 0 m, 0.05 m, 0.2, 60 m | low objects: every candidate ≥ 3 cm above the rail head (−1 = any bump above the bed) |
| `lowobj.max_length`, `min_width`, `max_width` | 1.5 m, 0.15 m, 2.2 m | size of a low cluster |
| `lowobj.straddle_min_top`, `straddle_min_width`, `straddle_max_length`, `straddle_band` | 0.10 m, 0.35 m, 0.8 m, 0.30 m | an object across a rail, clustered whole |
| `lowobj.near_enabled`, `rail_start_within` | false, 4 m | the central near-bed path (off); rail geometry near a standing train is not a low obstacle |
| `tracking.confirm_hits`, `confirm_time_s`, `low_confirm_hits`, `conf_threshold` | 3, 0.5 s, 5, 0.6 | latency against false alarms |
| `tracking.hit_window`, `min_hit_fraction`, `zone_window`, `zone_min_fraction`, `column_hold` | 10, 0.6, 10, 0.6, 2 | persistence and the zone vote over the track's history |
| `tracking.hold_misses`, `max_misses` | 1, 3 | frames a reported obstacle stays reported without a match; frames a track survives |
| `tracking.gate_base`, `gate_per_m`, `ego_speed_max`, `gate_along_only` | 1.5 m, 0.02, 25 m/s, true | association gate and its slack without odometry |
| `tracking.near_escalate_voxels`, `near_escalate_distance`, `near_escalate_hits` | 10, 35 m, 5 | near escalation (§3.5) |
| `tracking.stop_keep_signature`, `stop_keep_thin`, `stop_keep_max_s`, `stop_keep_min_voxels` | true, 1, 10 s, 10 | STOP keep (§3.5) |
| `tracking.thin_far_min_distance`, `approach_hits`, `approach_min_speed`, `approach_max_residual` | 60 m, 5, 2 m/s, 0.5 m | far evidence for approaching tracks |
| `tracking.doubt_model`, `doubt_threshold`, `doubt_extra_hits`, `doubt_near`, `doubt_body_height` / `doubt_body_range` | `track_opinion.json`, 0.015, 10, 25 m, 1.0 m / 40 m | the learned opinion (§3.6); `""` = off |
| `accumulation.enabled`, `n_frames`, `min_range`, `min_speed`, `estimate_speed` | true, 5, 40 m, 1 m/s, false | merging only with a given speed; the estimator off |
| `accumulation.min_points_scale`, `smear_max_length`, `smear_max_width` | 0.3, 2 m, 1 m | noise bar of merged clusters; smear guard |
| `calibration.enabled`, `frames` × `obs_spacing`, `provisional_min_deg`, `apply_min_deg` | true, 20 × 10 frames, 2.5°, 0.75° | mount auto-calibration; `sensor.roll_deg/pitch_deg/yaw_deg` freeze a known mount |
| `calibration.min_yaw_deg`, `max_tilt_deg`, `max_frames`, `reseed_keep_max_deg`, `drift_warn_deg` / `drift_window`; `tracking.reseed_hold` | 3°, 15°, 400, 1°, 1.5° / 10 checks; 5 | limits, re-seed, drift monitor; frames a STOP is held through a change |
| `health.clear_cap`, `clear_cap_lost`, `clear_cap_thin`, `clear_cap_persist` | true, true, true, 4 | caps of the clear distance (§4b) |
| `health.min_points`, `min_visibility`, `min_lock_rate`, `latency_budget_ms`, `latency_affects_decision` | 20 000, 60 m, 0.3, 100 ms, false | health thresholds; they never change a detection |

## 6. Limitations of the sealed 27.09 detector

Every rule and the opinion's negatives were tuned on the six organizer recordings, the 20-minute
ride and the organizers' test objects (set O) and checked on the same data; `doubleT_obstacle` and
set O were labelled with the team's own tools ([`EVALUATION.md`](EVALUATION.md) §1). Figures are
from the judgement of 28.09 ([`SCORECARD.md`](SCORECARD.md)); the node's view:
[`ARCHITECTURE.md`](ARCHITECTURE.md#limitations-of-the-sealed-2709-detector-verified-2809).

**Detection and range**

* **A confirmed STOP drops for one frame when its object is missed twice in a row**
  (`hold_misses` = 1). On `doubleT_obstacle` the object across the rail forms no low cluster in
  frames 110–111, 116–117 and 196–197: GO at frame 111, CAUTION at 117 and 197 (STOP on 190 of 201
  frames offline; `clear_distance` stays capped at the lost track's 56.2 m). `hold_misses` 2
  restores those frames but failed the gate (more false alarms on the ride and the empty
  recordings) and was rejected. A consumer should not act on a single-frame GO.
* **Range.** A real person pasted into the five other tunnels gives a sustained STOP at 60 m in 11
  of 15 windows, 80 m 8, 100 m 6, 130 m 2, 160 m 1, 200 m 0. The misses are `CAUTION`, not silence:
  `beyond_axis` where the trusted axis range is short (platforms, double-track sections; 45 m for a
  whole platform window), or a merge with trackside structure into a `column`. Without a rail lock
  anything beyond 40 m is advisory (§3.2).
* **Small objects are confirmed late.** Set O's 0.3 m cubes STOP from 48–56 m (at 60–115 m they
  return 2–4 points a frame, below the 5-voxel minimum); a 10 cm face is one ring high beyond
  ~20–25 m. The 5 cm hanging object STOPs from 30 m: beyond ~50 m none of its returns is inside the
  envelope, the hanging stage looks to 60 m only and not without a rail lock. Beyond the height
  reference only clusters ≥ 0.6 m tall alarm (§3.3c).
* **Edge objects and the envelope reference.** Set O's edge cube and edge 2 m box STOP from 35 m and
  29 m. Beyond 60 m, on curves and without a rail lock the envelope is measured from the rails only,
  while the organizers place objects from the sensor axis; which reference the hidden check uses is
  open ([`QUESTIONS.md`](QUESTIONS.md) Q1).
* **The learned opinion delays a doubtful far STOP** by up to 10 processed frames over a track's
  life (beyond 25 m, not a body ≥ 1 m tall within 40 m): ~1 s at 10 Hz, ~2 s at 5 Hz. Its positives
  are synthetic; a real object unlike them can use the whole budget.

**By design**

* A compact object on the bed between the rails is not reported (the organizers' policy, §3.3b);
  one across a rail is, while the bed is seen (≤ ~50–60 m) and when ≥ 0.35 m across; one lying
  *along* a rail looks like the trackside devices there. A person lying between the rails rises only
  0.01–0.09 m above the rail head in these tunnels: found from ~42 m at 0.10 m, from ~17 m at 0.05 m,
  not below 3 cm (synthetic, log §2d). Objects under 35 cm and 0.4 m wide on the sleepers are
  removed as hardware.
* Tall narrow things (> 2.2 m, < 1 m wide: a ladder on the track) are `column` and never escalate;
  a long object near the axis with its bottom above 1.6 m (the shape of overhead ducts) is
  `floating`. A person, a train, a trolley or a crate keep their zone.
* A sensor mounted on its side is not recognised; the calibration needs a rail pair within 400
  frames and treats the tilt as a whole-run constant (the cant of a curve is not separated from the
  mount roll); a 5 Hz input or a re-mounted rig raise the false events slightly (log §1g, §1i).
* No semantics: a parked train, a trolley or a worker on the track are all obstacles, as a safety
  function should report them.

**False alarms and advisories**

* **STOP on empty track**: 23 STOP frames (1.0 %) in 7 episodes on the five obstacle-free
  recordings, 30 episodes on the 13 km ride (2.3 per km). Most are axis errors: at the platform end
  of `squareT_platform_squareT_switch` (83 m) a platform boundary joined to the diverging hall end
  bends the axis by ~0.8 m, at its switch (~147 m) a hall wall seen only to 72–92 m moves the far
  corridor by 1.4–3.4 m; in general the wall curvature leaves 0.1–0.3 m of lateral uncertainty at
  60–80 m, enough to put edge fixtures inside. Rules that removed some of them cost real objects
  range or moved false alarms onto the ride and were not shipped (log §1h).
* **`CAUTION` is frequent**: 49 % of the frames of the empty recordings (35–69 % per recording),
  37 % of the ride (columns, the advisory band, beyond the trusted axis); an object demoted to it is
  easy to overlook.
* **`clear_distance` is an estimate**: it extends past an object inside the envelope in 300 of 605
  set-O frames (68 of them GO); an object forming no cluster at the envelope does not cap it.
* **Far and near geometry**: an obstacle far ahead can lengthen the bed fit beyond ~90 m and bend
  the far corridor (edge fixtures beyond an injected object alarmed in a few ride frames while the
  object was confirmed, log §2d); a large near object's shadow is handled only within 30 m, and an
  object touching a long edge line beyond 30 m is dropped with it.
* **Single-frame without a given speed** (§3.4); **CPU only**: with the native kernels a 360° frame
  fits the 100 ms period on 4 cores, the numpy fallback does not
  ([`ARCHITECTURE.md`](ARCHITECTURE.md) "Real-time budget").

**What the organizers' answers settle.** *Switches*: the switch state is not an input; the detector
follows the track its model locks on, and glitches at switches do not count as a minus
([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md) §5). *Mount*: the test
recordings use the provided mounts (§2). *Bed*: a 30 × 30 × 10 cm object between the rails is not
an obstacle ([`organizers/answers.md`](organizers/answers.md) §8).
