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
| `doubleT_obstacle` | 20.4 s | 201 | 4.5 GB | double-track tunnel, **train stationary**, a person walks away from the train on the left walkway (2.5 → 11 m, ~1.9 m left of the sensor axis, ~2.1–2.5 m left of the track axis) |
| `doubleT_platform` | 34.4 s | 345 | 2.6 GB | double-track tunnel → station platform |
| `roundT_doubleT` | 25.1 s | 252 | 1.9 GB | round single-track tunnel → double-track tunnel (walls diverge) |
| `roundT_pressureGate_roundT` | 26.7 s | 268 | 2.0 GB | round tunnel through a pressure gate (гермозатвор), right-hand curve |
| `roundT_squareT_pressureGate_squareT` | 55.4 s | 545 | 4.1 GB | round → rectangular tunnel, pressure gate |
| `squareT_platform_squareT_switch` | 88.2 s | 877 | 6.6 GB | rectangular tunnel → platform (train stops) → switch |

Total 2 488 frames / 250 s. **No obstacle inside the clearance gauge in any bag** (the only
foreign object is the walking person next to the track in `doubleT_obstacle`). Organizers
promised an extended dataset with obstacles — until then all positive examples come from
`resense inject` (synthetic obstacles ray-cast into the real frames, see ARCHITECTURE.md).

## Topic and sensor

* **The bags do not agree on the topic name, the frame id or the azimuth window** (verified
  2026-09-20 by reading the bags, not the notes):

  | bag | topic | `frame_id` | `width` | azimuth span |
  |---|---|---|---|---|
  | `roundT_doubleT` | `/lidar_points` | `hesai_lidar` | 307 200 | 100° (−140°…−40°) |
  | `doubleT_obstacle` | `/sensing/lidar/hesai128/pointcloud` | `lidar_livox` | 921 600 | 360° |

  `doubleT_obstacle` is a **full-turn recording** (3600 azimuth columns × 128 rings × 2 returns
  = 921 600 slots, ~347 k valid points) with a `lidar_livox` frame id left over from an earlier
  rig; the others use the 120° window (1200 columns, ~190 k valid points). **Only these two
  of the six bags have had their topic and frame id verified by reading the bag**; the other
  four (`doubleT_platform`, `roundT_pressureGate_roundT`, `roundT_squareT_pressureGate_squareT`,
  `squareT_platform_squareT_switch`) are unverified — **do not assume, read the metadata**
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
| `lateral` | m | lateral offset of the object centre from the **track axis**, + left. A tool that only knows the vehicle frame may use the object's Y: the axis is within 0.25 m of the sensor axis in all six bags, well inside the 1 m match tolerance |
| `yaw_deg` | deg | rotation about Z; 0 when unknown |
| `reflectivity` | 0–255 | mean intensity of the object's returns (reflectivity %, > 100 retro-reflective); 0 when unknown |
| `label` | string | **one string per physical object, kept across frames** (`person_crossing` in every frame it appears in). Recall is per object-frame; first-detection distance is per label, so a label that changes every frame breaks that metric |
| `in_gauge` | bool | `true` if any part of the object is inside the strict clearance gauge (it must alarm); `false` for objects next to the track that must **not** alarm (negatives). `inject` sets it from `abs(lateral) < 1.3` |
| `name` | string | optional: the `inject` catalogue name (`box0.5`, `hivis`, …) or a real class; the per-class recall table is keyed by it (falls back to `kind`) |
| `n_points` | int | optional: `inject` writes the number of ray hits; **`0` means fully occluded** by real geometry, and such rows are excluded from recall and counted in `occluded_gt_skipped`. Real labels leave it out |
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

The first real label file to produce is `doubleT_obstacle` (the person crossing the track at
55–57 m, reported at 55.6 m in the v0 run — [`EXPERIMENTS.md`](EXPERIMENTS.md) §1). Its frame
numbers and lateral offsets have to come from the label tool on the bag, not from memory.

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
window spans about 100° of valid returns, a full turn 360°), and the **frame period**
(stamp gaps ≈ 0.1 s). Then:

1. `resense run --bag <bag> --limit 30` — the track model must lock (`yc` stable within a
   few cm, `rail_score` > 0.05 in the JSONL) and no alarm should appear on an empty tunnel
   start; if `yc` jumps or `corr` is 0, the axis mapping (`sensor.forward/left/up`) or the
   topic is wrong for that bag.
2. `scripts/cache_frames.py <bag> cache/<bag> --every 10` — cached frames for P3/P4.
3. If the bag contains an obstacle: label it with the tool (format above), keep the file as
   `labels/<bag>.json` (not in git if it is large; a few KB is fine), and run
   `resense eval --bag <bag> --gt labels/<bag>.json --repeat 1 --text`.
4. Add a row to the bag table with the scene description from the organizers' notes and
   what was verified (topic / frame id / window / obstacle), and the date.

Only what was read from the bag goes into the table; a value copied from another bag is
marked as such.
