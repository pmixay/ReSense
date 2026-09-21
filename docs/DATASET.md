# Dataset notes (organizers' bags, 2026-09)

**Download:** [`Датасет.zip`, 3.7 GB, Google Drive](https://drive.google.com/file/d/1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu/view)
(organizers' link, shared with the team — the bags themselves are never committed, see
`.gitignore`).

Source: `Датасет.zip` (3.7 GB) → `датасет.zip` → `archive/for_hackathon.zst` (tar, zstd).
Unpack: `tar --zstd -xvf for_hackathon.zst` (or `python -c "import zstandard,tarfile..."` if
`zstd` is missing). Six ROS 2 bags (sqlite3 storage, `metadata.yaml` + `*_0.db3`), one topic.
Put the unpacked `for_hackathon/` where `$RESENSE_DATA` points (default `/data/for_hackathon`,
see README "Where the data lives"):

```bash
mkdir -p /data && tar --zstd -xf for_hackathon.zst -C /data
ls /data/for_hackathon          # six bag directories
resense info /data/for_hackathon/roundT_doubleT
```

| Bag | Duration | Frames | Size | Scene (from the name) |
|---|---|---|---|---|
| `doubleT_obstacle` | 20.4 s | 201 | 4.5 GB | double-track tunnel, **train stationary**; a person crosses the track at 54.5–57 m (inside the gauge in frames 2–72, then standing 2.1–2.5 m left of the axis until the end); a second person walks away from the train along the left side (X 1 → 16 m, 2.2–2.5 m left of the axis) in frames **146–200** — both labelled in `labels/doubleT_obstacle.json` (section "Real labels" below) |
| `doubleT_platform` | 34.4 s | 345 | 2.6 GB | double-track tunnel → station platform |
| `roundT_doubleT` | 25.1 s | 252 | 1.9 GB | round single-track tunnel → double-track tunnel (walls diverge) |
| `roundT_pressureGate_roundT` | 26.7 s | 268 | 2.0 GB | round tunnel through a pressure gate (гермозатвор), right-hand curve |
| `roundT_squareT_pressureGate_squareT` | 55.4 s | 545 | 4.1 GB | round → rectangular tunnel, pressure gate |
| `squareT_platform_squareT_switch` | 88.2 s | 877 | 6.6 GB | rectangular tunnel → platform (train stops) → switch |

Total 2 488 frames / 250 s. **The only obstacle inside the clearance gauge in the six bags is
the person crossing the track at 55–57 m in `doubleT_obstacle`** (frames 2–72; the labels are
in `labels/doubleT_obstacle.json`); every alarm on the other five bags is a false alarm.
Organizers promised an extended dataset with obstacles — until then the positive examples at
other ranges and for other objects come from `resense inject` (synthetic obstacles ray-cast
into the real frames, see ARCHITECTURE.md and "Set S" below).

## Topic and sensor

* **The bags do not agree on the topic name, the frame id or the azimuth window.** Topics
  from every bag's `metadata.yaml` (read by the captain on 2026-09-21, CAPTAIN.md finding 3 of
  21.09); `frame_id` and `width` read from the messages of two bags only (2026-09-20); the
  window and the point counts measured on the cached frames of all six bags (P4, 21.09: five
  frames per bag, azimuth `atan2(x, −y)` in the sensor frame, 0.5–99.5 percentiles):

  | bag | topic (`metadata.yaml`) | `frame_id` | `width` | azimuth window | valid points / frame |
  |---|---|---|---|---|---|
  | `doubleT_obstacle` | `/sensing/lidar/hesai128/pointcloud` | `lidar_livox` (read) | 921 600 | full turn; valid returns over ~210° (−104°…+106°) | ~347 k |
  | `doubleT_platform` | `/lidar_points` | not verified | not read | ±50° | 160–186 k |
  | `roundT_doubleT` | `/lidar_points` | `hesai_lidar` (read) | 307 200 | ±50° | 180–190 k |
  | `roundT_pressureGate_roundT` | `/lidar_points` | not verified | not read | ±50° | 182–190 k |
  | `roundT_squareT_pressureGate_squareT` | `/lidar_points` | not verified | not read | ±50° | 181–190 k |
  | `squareT_platform_squareT_switch` | `/lidar_points` | not verified | not read | ±50° | 160–182 k |

  `doubleT_obstacle` is a **full-turn recording** (3600 azimuth columns × 128 rings × 2 returns
  = 921 600 slots, ~347 k valid points) with a `lidar_livox` frame id left over from an earlier
  rig; the others use the 120° window (1200 columns, valid returns within ±50°, 160–190 k
  points — fewer at the platforms, where the near walls are missing). **Only two of the six bags
  have had their frame id verified by reading the bag**; for the other four the topic comes
  from `metadata.yaml` and the frame id is unknown — **do not assume, read the messages**
  (recipe below). Consequences: the node takes a candidate topic list and auto-discovers
  PointCloud2 topics, and the RViz layout must not hard-code the topic or the fixed frame.
* `sensor_msgs/msg/PointCloud2`, ~10 Hz (frame period 80–120 ms in the bag clock).
* Fields: `x y z` float32, `intensity` float32 (0–255, median 6–7, rails/retro-reflectors up to 255),
  `ring` uint16 (0–127), `timestamp` float64 (sensor clock, **not synchronised**: year 2000 epoch —
  use the bag receive time, not `header.stamp`).
* Layout: `height=1, width=307200`, `point_step=26`. 1200 azimuth columns × 128 rings × **2 returns**
  (dual-return mode). Missing returns are stored as `(0,0,0)` — ~38 % of the slots. A frame therefore
  holds ~190 000 valid points, ~150 000 distinct rays.
* Angular grid (measured): azimuth step **0.1°**, valid returns only within **±50°**; 128 rings with
  elevation **+14.4° … −25.1°**, **0.125° step in the ROI (+2° … −6.2°)**, 0.5° outside. The sweep
  of one frame takes 33 ms. The unit is a **Hesai Pandar128 (E3X)** — identified from the manual and the
  angle correction file, see [`SENSOR.md`](SENSOR.md).
* Range: last returns at ~206 m; the tunnel walls return points to ~150–200 m, the track bed to
  ~100 m; p99 of ranges is only ~48 m (most points are the near walls).
* Sensor frame: **−y is forward, +x is left, +z is up** (right-handed). The package converts
  this to the vehicle frame X-forward / Y-left / Z-up (`SensorConfig.forward = "-y"`).

## Geometry seen in the data

* Round tunnel: inner radius ≈ 2.5–2.7 m, crown ≈ 3.4 m above the sensor, track bed ≈ 1.5 m below
  the sensor (moving bags) and ≈ 2.0 m below in `doubleT_obstacle` (different mount!). The
  detector therefore self-calibrates the bed and rail level per frame.
* Track axis is **0.05–0.25 m to the right of the sensor axis** (rail ridge template, gauge 1.52 m
  → 1.59 m between rail-head centres); rail head ≈ 0.30–0.42 m above the 20th-percentile bed level
  (the bed has a central drainage trough).
* Contact (third) rail with its cover: ~1.6–2.0 m left of the track axis, top ≈ 0.35–0.5 m above rail head.
* Column row in the double-track tunnel: inner faces ≈ 1.7 m from the track axis, floor to ceiling.
* Platform edge: ≈ 1.6 m from the track axis, 1.1 m above rail head (long, straight, thin → the
  gauge polygon is 1.4 m wide there).
* Pressure gate: frame narrows the tunnel to roughly the structure gauge.
* Curves: at least three bags contain curves with R ≈ 700–3000 m; a straight corridor cuts into
  the wall / column row beyond 50–100 m, hence the wall-based yaw/curvature estimator.

## Point budget at range (why 300 m is hard)

Angular resolution 0.1° × 0.125° ⇒ a target of w×h metres at range r returns roughly
`n ≈ w·h / (r² · 3.8e-6)` points per frame (single return, normal incidence):

| target | 50 m | 100 m | 150 m | 200 m | 300 m |
|---|---|---|---|---|---|
| 0.5 × 0.5 m box | 26 | 6.6 | 2.9 | 1.6 | 0.7 |
| person 0.5 × 1.7 m | 90 | 22 | 10 | 5.6 | 2.5 |
| 1 × 1 m crate | 105 | 26 | 12 | 6.6 | 2.9 |

Beyond ~150 m a single frame gives a handful of points → temporal accumulation with ego-motion
compensation (and the extended dataset for calibration of dropout at range) is the path to 200 m+.

## Cached frames for fast iteration

`resense.io.iter_bag_compact` reads bags without ROS (pure-python `rosbags`). For prototyping we
cache every N-th frame as compact `*.npy` (x,y,z,intensity,ring; ~3.5 MB each):

```bash
python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/ --every 10
```

The file name carries the **bag frame index** (`roundT_doubleT_0120.npy` = message 120 of the
bag, 0-based, in message order). `resense eval --npy <dir> --gt gt.json` reads that number
back to find the frame's labels, and `resense run --npy` numbers frames by their position in
the directory (every file = one frame, `stamp = position × 0.1 s`; cached files carry no bag
time, so per-hour rates need the bag itself).

## Synthetic obstacles (`resense inject`)

`resense inject` ray-casts catalogue objects into empty frames with the sensor's own angular
grid (occlusion-correct, range-dependent dropout beyond 120 m scaled by reflectivity). Objects
are selected by name with `--kinds`; the catalogue is `resense.synthetic.OBJECT_CATALOGUE`:

| name | mesh | size L × W × H (m) | reflectivity (%) | stands for |
|---|---|---|---|---|
| `person` | cylinder body + head sphere | 0.4 × 0.5 × 1.7 | 10–60 | person in dark / ordinary clothing |
| `hivis` | same | 0.4 × 0.5 × 1.7 | 150–250 | person in a hi-vis vest (retro-reflective) |
| `box0.2` | box | 0.2 × 0.2 × 0.2 | 20–40 | cardboard box (top below the `hardware` filter's 0.35 m: invisible by design in v0, EXPERIMENTS.md §4 item 5) |
| `box0.5` (alias `box`) | box | 0.5 × 0.5 × 0.5 | 20–40 | cardboard box |
| `box1.0` | box | 1.0 × 1.0 × 1.0 | 20–40 | cardboard crate |
| `plank` | box | 2.0 × 0.25 × 0.30 | 30–60 | wooden plank / sleeper |
| `trolley` | cylinder | 0.6 × 0.6 × 1.0 | 40–120 | maintenance trolley (painted metal), cylinder approximation |
| `cylinder` | cylinder | 0.4 × 0.4 × 0.9 | 30–90 | drum / bin (legacy name) |
| `sphere` | sphere | 0.4 × 0.4 × 0.4 | 20–60 | ball-like debris |

Reflectivity is drawn uniformly from the range per object (intensity in the bags is
reflectivity %, > 100 retro-reflective, [`SENSOR.md`](SENSOR.md) §2). **The ranges are
assumptions** until they are calibrated on real obstacles of the extended dataset (PLAN.md,
P4 item 1); they only affect the injected intensity and the dropout beyond 120 m.

Placement: one object set per background frame (`--per-frame`), distance uniform in
`--distances lo:hi`, lateral uniform ±0.9 m inside the gauge or, for the `--negative-fraction`
share, 2.2–3.0 m to either side (must **not** alarm, `in_gauge = false`), random yaw. Objects
stand on the sleepers (rail head − 0.15 m) of the per-frame track model.

**Set S as built on 21.09** (EVALUATION.md §3, raw summaries in
[`experiments_v0.4_synthetic_on_real.json`](experiments_v0.4_synthetic_on_real.json); the
seeds are fixed, so the same frames come out of the cache on any machine):

```bash
# static sets (recall by range per kind): every 10th frame of three empty bags, one catalogue
# object per frame, 20 % negatives outside the gauge; 26 / 27 / 55 frames, ~1.1 MB each
for bag in roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT; do
  resense inject --npy /data/cache/$bag --every 10 --out data/S_$bag \
      --kinds person,box0.5,box1.0,plank,trolley --distances 10:250 --negative-fraction 0.2 --seed 1
  resense eval data/S_$bag --repeat 3 --text        # 3 repeats emulate persistence; no speed given
done

# approach sequences (first-detection distance) on roundT_doubleT: 8 steps of 1.5 m (15 m/s)
# per background, one kind per set, seeds 1-3; 208 frames per set, deleted after the evaluation
for kind in person box0.5 box1.0 plank trolley; do for seed in 1 2 3; do
  resense inject --npy /data/cache/roundT_doubleT --every 10 --out data/SEQ_${kind}_s$seed --kinds $kind \
      --distances 10:250 --negative-fraction 0.2 --sequence 8 --speed 15 --seed $seed
  resense eval data/SEQ_${kind}_s$seed --repeat 1 --text                 # rows' speed_mps given to the detector
  resense eval data/SEQ_${kind}_s$seed --repeat 1 --no-gt-speed --text   # estimator / single-frame path
done; done

# robustness: augmented backgrounds (5 % dropout, 1 cm range noise, ±0.3° yaw/pitch, ±0.2° roll, 10 % intensity jitter)
resense inject --npy /data/cache/<bag> --every 10 --out data/synth_aug/<bag> --augment
```

`resense eval` gives the detector the `speed_mps` of `inject --sequence` rows on every frame
(`ego_speed_source: given`, the way the ROS node passes `ego_speed_mps` / odometry);
`--ego-speed V` forces a constant speed on any source, `--no-gt-speed` withholds the rows'
speed. Static sets carry `speed_mps: 0` and get nothing (the estimator runs, as in
`resense run`). `resense run` and `resense bench` take the same `--ego-speed V`.

`--sequence N --speed V` keeps the same background frame and moves the objects by
`V × tracking.frame_dt` per step (`d − k·V·0.1` for k = 0..N−1), stopping early if an object
would pass `gauge.range_min`; files are numbered in order and every row carries `seq`
(background index), `seq_step` (k) and `speed_mps`, so `eval` in file order sees a
moving-toward run. The background itself does not move, so this exercises persistence and
the association gate, not ego-motion compensation.

## Label format (`gt.json`)

One JSON object per bag (or per injected dataset), **keyed by the bag frame index** as a
zero-padded 5-digit string. `resense inject` writes this format, `resense eval` and
`resense summarize --gt` read it, and the browser label tool (P2, `web/`) exports it.

```json
{
  "_meta": {"bag": "doubleT_obstacle", "topic": "/sensing/lidar/hesai128/pointcloud",
            "source": "label-tool", "coords": "vehicle", "every": 1},
  "00042": [
    {"kind": "person", "name": "person", "size": [0.4, 0.5, 1.7],
     "distance": 55.6, "lateral": -0.2, "yaw_deg": 0.0, "reflectivity": 40.0,
     "label": "person_crossing", "in_gauge": true}
  ],
  "00043": []
}
```

| key | meaning |
|---|---|
| frame key | bag frame index in message order, 0-based, zero-padded to 5 digits (`"00042"`): the `frame` field that `resense run --out` writes, the index `resense info` / `iter_bag_compact` count, and the number in `scripts/cache_frames.py` file names. An injected dataset uses its own running index (`"00000"`, `"00001"`, …) — same shape. |
| value | list of objects in that frame. **`[]` = the frame was looked at and is empty** (a negative label). A frame with no key is *unlabelled*: `eval` treats it as empty unless `--labelled-only`. |
| `_meta` | optional; any key starting with `_` is metadata and ignored by the loaders (`bag`, `topic`, `source`, `coords`, `every`, `speed_mps`, …). |

Object keys (the first seven are what `resense inject` has always written; keep them):

| key | type | meaning |
|---|---|---|
| `kind` | string | geometry class: `person`, `box`, `plank`, `cylinder`, `sphere` for injected objects; for real labels any short class string (`person`, `box`, `bag`, `trolley`, `sign`, `unknown`) |
| `size` | `[L, W, H]` m | extent along the track, across it, and height |
| `distance` | m | **X in the vehicle frame (forward) of the object's nearest point**, measured from the sensor. This is what `nearest_distance` reports and what the match tolerance is applied to |
| `lateral` | m | lateral offset of the object centre from the **track axis**, + left. A tool that only knows the vehicle frame may use the object's Y: the axis is typically within 0.25 m of the sensor axis (single frames up to 0.7 m on the platform and curve bags), inside the 1 m match tolerance; label relative to the track axis when the tool knows it |
| `yaw_deg` | deg | rotation about Z; 0 when unknown |
| `reflectivity` | 0–255 | mean intensity of the object's returns (reflectivity %, > 100 retro-reflective); 0 when unknown |
| `label` | string | **one string per physical object, kept across frames** (`person_crossing` in every frame it appears in). Recall is per object-frame; first-detection distance is per label, so a label that changes every frame breaks that metric |
| `in_gauge` | bool | `true` if any part of the object is inside the strict clearance gauge (it must alarm); `false` for objects next to the track that must **not** alarm (negatives). `inject` sets it from `abs(lateral) < 1.3` |
| `name` | string | optional: the `inject` catalogue name (`box0.5`, `hivis`, …) or a real class; the per-class recall table is keyed by it (falls back to `kind`) |
| `n_points` | int | optional: `inject` writes the number of ray hits; **`0` means fully occluded** by real geometry, and such rows are excluded from recall and counted in `occluded_gt_skipped`. Real labels may write the measured cluster size (never 0; see "Real labels", which also adds `gauge_margin` and `h_above_rail`) |
| `bbox` | `[[xmin, ymin, zmin], [xmax, ymax, zmax]]` m | optional, for the label tool: an axis-aligned box in the **vehicle frame** (X forward, Y left, Z up). When `distance` / `size` are missing they are derived: `distance = xmin`, `lateral = (ymin + ymax) / 2`, `size = max − min`. A tool that works in the raw sensor frame converts first: `X = −y_s`, `Y = x_s`, `Z = z_s` for the hackathon mount (`configs/default.yaml` → `sensor.forward/left/up`) |
| `seq`, `seq_step`, `speed_mps` | int, int, m/s | written by `inject --sequence N --speed V`: the approach-sequence id, the step within it (0 = farthest) and the simulated train speed |

Matching rule (`resense/metrics.py`, [`EVALUATION.md`](EVALUATION.md) §2): a detection matches
an object if |Δdistance| ≤ max(2 m, 3 % of range) + L/2 and |Δlateral| ≤ 1 m. Coordinates are
in the vehicle frame after `SensorConfig` axis mapping, **not** the raw sensor frame.

Usage:

```bash
resense eval --bag /data/for_hackathon/doubleT_obstacle --gt labels/doubleT_obstacle.json --repeat 1 --text
resense eval --npy cache/doubleT_obstacle --gt labels/doubleT_obstacle.json --repeat 1 --labelled-only
resense run  --bag <bag> --out results.jsonl && resense summarize results.jsonl --gt labels/<bag>.json --speed-mps 15
```

`--repeat 1` for real sequences (the tracker sees the true frame order); the default
`--repeat 3` is for static injected frames, where it emulates persistence.

## Real labels (set R): `labels/doubleT_obstacle.json`

Made on 2026-09-21 (P4) from the cached frames of `doubleT_obstacle`, **not** from the
detector's output: every one of the 201 frames was searched for person-sized clusters with the
recipe below and every frame carries a label list (74 KB, one line per frame). The recipe uses
the package only, so the file can be rebuilt and checked:

1. frame `NNNN` = `/data/cache/doubleT_obstacle/doubleT_obstacle_NNNN.npy` →
   `resense.frame.frame_from_compact(arr, SensorConfig())` (vehicle frame, X forward / Y left /
   Z up) and a per-frame track model `resense.track.estimate_track(xyz, cfg.track, prev=None)`
   for the rail-head height. The lateral axis of the labels is the **median of the 201
   per-frame axes** (centre −0.225 m, yaw −1.25°, curvature −7.6e−5 m⁻¹; the per-frame yaw
   scatters between −2.0° and −0.84°, i.e. ±0.5 m at 55 m, while the train does not move, so
   one axis is the physical truth and the per-frame value is detector noise).
2. **Far window** X 50–62 m, |dy| ≤ 4 m, 0.1–2.3 m above the rail head → DBSCAN (0.4 m, 4
   points); a person is a cluster of ≥ 15 points, ≤ 1.2 m long, ≤ 1.3 m wide, 0.6–2.0 m tall
   (the columns at 45.6 m and 46.8 m are 2.2–2.6 m tall and outside the window). Exactly one
   such cluster exists in every frame: 80–123 points, 0.2–0.75 m long, 0.5–1.2 m wide,
   1.0–1.6 m tall measured from the bed (the head is not always returned; in frames 28–48 the
   person bends down while crossing the rails: 1.0–1.2 m tall, 1.2 m wide, 30–45 points fewer).
3. **Near window** X 0.5–25 m, dy 0.8–3.5 m, 0.05–2.3 m above the rail head, minus the static
   background (0.25 m voxels occupied in ≥ 50 % of frames 0–100) → DBSCAN (0.35 m, 5); a person
   is ≥ 30 points, ≤ 1.5 m long, ≤ 1.2 m wide, 0.8–2.0 m tall. Found in frames 146–200 only
   (400–4 200 points, 1.5–1.6 m tall; partial in 146–150 while entering the 2.5 m minimum range).
4. Row keys: `distance` = X of the nearest point; `lateral` = mean dy of the cluster from the
   median axis (+ left); `size` = bbox extent, height measured on all points inside the
   footprint down to 0.25 m below the rail head (the person stands on the bed); `bbox` in the
   vehicle frame; `reflectivity` = mean intensity; `h_above_rail` = [min, max] above the
   per-frame rail head; `n_points` = cluster size (not an occlusion flag for real labels).
5. `in_gauge` = the nearest edge of the person, |lateral| − W/2, is inside the strict gauge
   half width of 1.4 m (`gauge.profile` above 0.55 m in `configs/default.yaml`);
   `gauge_margin` = 1.4 − edge (m, negative = outside) is written so that borderline frames can
   be re-thresholded: **frames 0–4 and 70–76 are within ±0.25 m of the boundary** (the axis
   uncertainty at 55 m), everything else is clear-cut.
6. Checked by eye on renders: `resense run --npy /data/cache/doubleT_obstacle --start F
   --limit 1 --render out/render --x-max 70` for F = 0, 40, 72, 100, 165, 200 (the person
   cluster sits at the labelled X / Y in every render; `img/doubleT_obstacle_0020.png` and
   `_0165.png` are the v0 renders of the same scene), and against the v0.3 full-rate results
   (`/data/results/v0.3/doubleT_obstacle.jsonl`: track 6 follows the same lateral path,
   55.4–56.6 m, frames 2–72).

| label | frames | where | `in_gauge` |
|---|---|---|---|
| `person_crossing` | 0–200 (every frame) | 55.4–56.7 m ahead; lateral +1.8 m (frame 0) → +1.1 m (10) → +0.4 m (20) → −0.26 m (35–45, on the axis) → +0.6 m (60) → +1.5 m (70) → +1.8 m (73) → +2.5 m (90–115) → +2.33 m (140–200, standing still at 54.65 m) | **true in frames 2–72** (71 frames), false in 0–1 and 73–200 (beside the track / column row) |
| `person_walkway` | 146–200 | walks away from the train along the left side: X 0.9 → 15.4 m, lateral +2.2…+2.5 m, ~2.8 m/s | false (edge 0.4–0.8 m outside the gauge) |

Two corrections to earlier notes: the walking person is in the **last** 55 frames, not the
first ones, and the standing person of `EXPERIMENTS.md` §1 (frame 165, "~1.8 m left") is
2.33 m left of the axis, 0.6 m outside the advisory corridor.

**Results on the labels** (21.09, every frame of the cached bag, commit f4e311f;
`resense eval --npy /data/cache/doubleT_obstacle --gt labels/doubleT_obstacle.json --text`,
`--labelled-only` gives the same numbers because every frame is labelled):

| detector | recall (person in gauge, 71 frames) | first detection | distance error mean / max (bias) | lateral error | FP frames / events | alarm frames / events |
|---|---|---|---|---|---|---|
| f4e311f defaults (v0.4: accumulation + estimator on, no speed given) | 64/71 = **90.1 %** | 56.5 m | 0.07 / 0.19 m (−0.07 m) | 0.18 m | 16 / 2 | 80 / 3 |
| f4e311f with the v0.3-equivalent config (`accumulation.enabled: false`, `estimate_speed: false`, `track.floor_verify_enabled: false`, `cluster.retro_intensity: 0`) | 63/71 = 88.7 % | 56.5 m | 0.00 / 0.05 m (+0.00 m) | 0.17 m | 13 / 2 | 76 / 3 |
| `/data/results/v0.3/doubleT_obstacle.jsonl` (commit f2c57e5) through `resense summarize --gt` | 63/71 = 88.7 % | 56.5 m | 0.00 / 0.05 m | 0.17 m | 13 / 2 | 76 / 3 |

Reading: the misses are frames 2–8 in both versions (the person enters the strict gauge at
frame 2 with a 0.04 m margin; `confirm_hits = 3` confirms at frame 9) plus frame 72 for v0.3
(the last in-gauge frame, margin 0.0 m). The two false-alarm events are the column-row
structures on the right, 17.4–19.5 m (−1.6 m, track id 1, 40 frames between 10 and 159) and
33.6–33.9 m (id 3, frames 13–14), which flip from the advisory zone into the gauge. The three
extra FP frames of v0.4 (73–75) are the person himself, 0.12–0.22 m outside the gauge by the
label and still reported inside by the laterally accumulated track (EXPERIMENTS.md §2b:
"stays in gauge four frames longer"); they are borderline, not phantoms. The distance bias of
v0.4 (−0.07 m) comes from the same accumulation.

## How to check a new bag (intake recipe)

For every bag of the extended dataset, before anything is labelled or run
(captain's item 16, [`CAPTAIN.md`](CAPTAIN.md)):

```bash
resense info /data/for_hackathon/<bag>          # metadata.yaml + first frame
```

Record in the table at the top of this file: **duration, frame count, size**, the
**topic name(s)** and message count, the **`frame_id`**, the **`width`** of the first
message (307 200 = 120° window, 921 600 = full turn), the **point count** of the first frame
and the **azimuth span** of its valid returns (`atan2(x, -y)` in the sensor frame — a 120°
window spans about 100° of valid returns, well over 120° for the full-turn recording: about 210° of valid returns in `doubleT_obstacle`), and the **frame period**
(stamp gaps ≈ 0.1 s). Then:

1. `resense run --bag <bag> --limit 30` — the track model must lock (`yc` stable within a
   few cm, median `track.rail_score` of 0.15–0.19 over the run in the JSONL; single frames can drop to 0) and no alarm should appear on an empty tunnel
   start; if `track.center` jumps or `n_corridor` is 0 in the JSONL (`yc` / `corr` in the `resense run` output), the axis mapping (`sensor.forward/left/up`) or the
   topic is wrong for that bag.
2. `scripts/cache_frames.py <bag> cache/<bag> --every 10` — cached frames for P3/P4.
3. If the bag contains an obstacle: label it with the tool (format above), keep the file as
   `labels/<bag>.json` (not in git if it is large; a few KB is fine), and run
   `resense eval --bag <bag> --gt labels/<bag>.json --repeat 1 --text`.
4. Add a row to the bag table with the scene description from the organizers' notes and
   what was verified (topic / frame id / window / obstacle), and the date.

Only what was read from the bag goes into the table; a value copied from another bag is
marked as such.
