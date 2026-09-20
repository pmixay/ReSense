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
  rig; the others use the 120° window (1200 columns, ~190 k valid points). The remaining four
  bags have not been re-checked — **do not assume, read the metadata**. Consequences: the node
  takes a candidate topic list and auto-discovers PointCloud2 topics, and the RViz layout must
  not hard-code the topic or the fixed frame.
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
