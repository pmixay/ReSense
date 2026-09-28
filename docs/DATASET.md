# Dataset Notes

*На русском: [DATASET.ru.md](DATASET.ru.md).*

> **Purpose:** the organizers' data: the recordings, their topics, formats and point budget, the
> labels, the frame cache, the synthetic-obstacle injector and the intake recipe for a new bag.
> **Audience:** team, jury · **Owner:** P4 · **Language:** EN, summary RU
> **Last verified:** 2026-09-29: links, sizes and checksums, the label files' `_meta`, the named
> scripts, functions and options · **Status:** current

**Кратко.** От организаторов у нас шесть записей по 20–88 с из разных участков метро (2 488
кадров, 250 с), 20-минутная поездка `new_data` (11 271 кадр, ~13 км, семь остановок, препятствий
нет) и запись `cloud_with_fake_obj` (1 510 кадров) с десятью объектами, добавленными
инструментом самих организаторов. Реальные препятствия есть только в `doubleT_obstacle`: человек
пересекает путь на 55–57 м, а предмет лежит на правом рельсе на 56 м; разметка обоих — в
`labels/`. Лидар — Hesai Pandar128, ~190 тыс. точек в кадре при 10 Гц, дальше 210 м точек нет.
Для других дальностей и объектов мы вставляем синтетические объекты в реальные пустые кадры
(`resense inject`, трассировка лучей по сетке самого датчика).

## Downloads and unpacking

The bags are never committed (`.gitignore`). The organizers' links:

| archive | size, checksum | holds |
|---|---|---|
| [`Датасет.zip`](https://drive.google.com/file/d/1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu/view) (Google Drive) | 3.7 GB, sha256 in `scripts/cold_bags.sha256` | the six original bags: zip → `датасет.zip` → `archive/for_hackathon.zst` (zstd tar) → `for_hackathon/<bag>/` (`metadata.yaml` + `*_0.db3`, sqlite3), ~22 GB |
| [`new_data.zst`](https://disk.yandex.ru/d/N8IUpAyd7jyvow) (Yandex Disk folder) | 17 078 961 996 bytes, sha256 `8124b627a8a70516a4023db522849f1cadae711e7b152b0f701535a69dab99ec` | the 20-minute ride: one rosbag2 bag `new_data/`, 221 split files `new_data_<N>.db3` (51 frames, 408 MB each) and `metadata.yaml`, 90.1 GB |
| [`cloud_with_fake_obj.zst`](https://disk.yandex.ru/d/KpkG_yKoGk-vHQ) (Yandex Disk) | 1 746 145 824 bytes, sha256 `d41c2fb28475194a98efeca5d2ee3fd175c0aef350ffb92fff4c26d497e696e9` | set O: `cloud_with_fake_obj/metadata.yaml` and one 7.42 GB `.db3` |

`scripts/unpack_dataset.py` streams zip → zip → zstd → tar from a file or a Yandex Disk link and
writes only the bags asked for (no 30 GB scratch copy); `$RESENSE_DATA` (default
`/data/for_hackathon`) is where the node's scripts look (README "Where the data lives"):

```bash
python scripts/unpack_dataset.py Датасет.zip --out /data          # /data/for_hackathon/<six bags>
python scripts/unpack_dataset.py Датасет.zip --out /data --only doubleT_obstacle,roundT_doubleT
python scripts/unpack_dataset.py https://disk.yandex.ru/d/N8IUpAyd7jyvow --member new_data.zst --out /data   # /data/new_data/
python scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out /data                         # /data/cloud_with_fake_obj/
```

The `new_data` folder also holds `cloud_with_fake_obj.zst`, hence `--member`. An unpacked bag is
an ordinary rosbag2 bag (`resense run --bag`, `ros2 bag play`); a single split file of the ride
opens on its own. `scripts/fetch_cold_bags.sh <dir>` fetches and verifies the two bags CI plays.

## The recordings

| recording | duration | frames | size | topic, `frame_id`, window | scene |
|---|---|---|---|---|---|
| `doubleT_obstacle` | 20.4 s | 201 | 4.5 GB | `/sensing/lidar/hesai128/pointcloud`, `lidar_livox`, full turn | double-track tunnel, **train stationary**; the real obstacles (below); a second person walks away along the left side in frames 146–200 |
| `doubleT_platform` | 34.4 s | 345 | 2.6 GB | `/lidar_points`, `hesai_lidar`, 120° | double-track tunnel → station platform |
| `roundT_doubleT` | 25.1 s | 252 | 1.9 GB | same | round single-track tunnel → double-track tunnel |
| `roundT_pressureGate_roundT` | 26.7 s | 268 | 2.0 GB | same | round tunnel through a pressure gate (гермозатвор), right-hand curve |
| `roundT_squareT_pressureGate_squareT` | 55.4 s | 545 | 4.1 GB | same | round → rectangular tunnel, pressure gate |
| `squareT_platform_squareT_switch` | 88.2 s | 877 | 6.6 GB | same | rectangular tunnel → platform (train stops) → switch |
| `new_data` | 1 199.9 s | 11 271 | 90.1 GB | same | 20-minute ride, ~13 km, seven stops, no obstacles |
| `cloud_with_fake_obj` | 150.9 s | 1 510 | 7.42 GB | same, no `ring` field | a real ride with ten objects added by the organizers' tool |

**Real obstacles exist only in `doubleT_obstacle`:** a person crossing the track at 55–57 m
(inside the 2.1 m envelope in frames 8–68) and an object lying on the right rail at ~56 m for the
whole recording (pointed out by the organizers in the Q&A session); both are labelled
([Real labels](#real-labels-set-r-labelsdoublet_obstaclejson)). Every alarm on the other five
recordings and on `new_data` is a false alarm: the organizers confirmed that the ride holds no
obstacles ([`organizers/answers.md`](organizers/answers.md) §2). Positives at other ranges come
from set O (the organizers' tool) and `resense inject` (ours; [`EVALUATION.md`](EVALUATION.md) §1).

## Synthetic-obstacle recording (`cloud_with_fake_obj`, labelled)

1 510 PointCloud2 messages on `/lidar_points`, frame `hesai_lidar` (120° window), over 150.851 s.
Its fields are `x,y,z,intensity` **without a ring field**; the reader fills a zero ring. Labels:
[`labels/cloud_with_fake_obj.json`](../labels/cloud_with_fake_obj.json).

```bash
python scripts/label_fake_objects.py /data/cloud_with_fake_obj --out labels/cloud_with_fake_obj.json   # ~2 min
resense run --bag /data/cloud_with_fake_obj --out out/fake.jsonl --quiet
python scripts/score_fake_objects.py out/fake.jsonl --gt labels/cloud_with_fake_obj.json   # per-object table
```

The organizers' description (24.09): ten objects about 100 m apart, in this order.

| # | organizers' text | label | envelope (intent) |
|---|---|---|---|
| 1 | посередине габарита крупный, 2х2 метра | `big_center` | inside |
| 2 | посередине габарита мелкий 0.3х0.3 м | `small_center` | inside (floats 1.0–1.4 m above the rail head) |
| 3 | мелкий 0.3х0.3 м стоит на рельсах | `small_on_rail` | inside (on the left rail) |
| 4 | 0.3х0.3 м скраю габарита | `small_edge_inside` | inside (straddles the edge) |
| 5 | 0.3х0.3 м за пределами габарита, но близко | `small_outside_near` | outside |
| 6 | 2х2 метра скраю в пределах габарита | `big_edge_inside` | inside |
| 7 | 2х2 за пределами габарита | `big_outside` | outside |
| 8 | 2х2 сверху габарита | `big_above` | inside (see below) |
| 9 | длинный низкий предмет лежит на рельсах (2х0.2) | `long_low_on_rails` | inside (across both rails) |
| 10 | узкий длинный свисает с потолка (ширина 0.05 м) | `thin_hanging` | inside (hangs to 2.7 m above the rail head) |

**How the labels are made.** Each message is the organizers' real scan (no-return points kept
as zeros, hidden returns removed) **followed by the object points, all with intensity 1**.
`scripts/label_fake_objects.py` takes every point after the last zero as object points, splits
them at X gaps over 8 m and links them into exactly ten tracks, in the organizers' order. Frames
0–803 carry objects (1 206 object-frame rows), 804–1509 are the real recording alone. `distance`
and `lateral` are measured from the detector's mount calibration and per-frame track axis (the
independence caveat: [`EVALUATION.md`](EVALUATION.md) §1); `in_gauge` is the organizers' intent.
Extra keys: `gauge_margin`, `h_above_rail`, `lateral_sensor` (offset from the sensor's axis),
`n_in_envelope` (points inside the rail-measured envelope), `plausible` (inside the tunnel).

Three properties decide how the recording can be scored:

* **The objects stand still; the train drives up to them**: 1.4 m/s at frame 0, 14–20 m/s from
  frame ~300 to ~1300, 2 m/s at the end, 2.0 km in 151 s (ICP, `scripts/speed_reference.py`);
  each object approaches by exactly the train's displacement.
* **The objects were placed from the sensor's axis, not from the rails** (the LiDAR is 1 075 mm
  above the rail head on the train's centreline,
  [`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md); the detector measures
  1.08 m here). The rails run at −0.24° to that axis (0.1 m apart at 25 m, 0.4 m at 100 m), so the
  edge tests #4–#7 sit within ±0.1–0.4 m of the envelope edge, on either side depending on the
  frame (#5 "outside" has points inside the rail-measured envelope in 101 of its 112 frames). The
  sealed detector takes the union of both references within 60 m on straight track
  ([`ALGORITHM.md`](ALGORITHM.md) §3.6); which one the hidden check uses is question 1 in
  [`QUESTIONS.md`](QUESTIONS.md). Far out the objects follow their own path, not the tunnel (#3 is
  4 m above the rail head at 81 m): `plausible` drops those rows.
* **"сверху габарита" is read as the top of the envelope.** The bottom of #8 is 2.4–2.9 m above
  the rail head, inside the 3.0 m envelope, so it is labelled `in_gauge: true`; the opposite
  reading ("must not alarm") is question 2 in [`QUESTIONS.md`](QUESTIONS.md).

Results per object: [`SCORECARD.md`](SCORECARD.md), [`EXPERIMENTS.md`](EXPERIMENTS.md).

## Extended dataset: `new_data` (the 20-minute ride)

Recorded 17.09, **no labels and no obstacles** (organizers, Q&A 22.09 and written answer 23.09:
"В new_data препятствий нет", [`organizers/answers.md`](organizers/answers.md)). Every file was
read once at intake; per-file rows are in [`extended_dataset_intake.json`](extended_dataset_intake.json).

| what | read from the bag |
|---|---|
| topic, type, frame | `/lidar_points`, `sensor_msgs/msg/PointCloud2` (cdr), the only topic; `hesai_lidar` in every file; 11 271 messages (51 per file, `metadata.yaml` agrees) |
| layout, points | `width 307 200`, `point_step 26`, as the five 120° bags; returns within −49.5° … +49.6°; 152 754 – 191 094 valid points per frame (median ≈ 183 k, the low values at stations) |
| clock | bag receive time from 2026-09-17 11:02:06 UTC; `header.stamp` is the year-2000 sensor clock — use the bag time |
| frame period | 0.100 s, continuous across split files, **except holes in the last third**: from file 156 (t ≈ 800 s) 26 files span 6–12 s instead of 5.1 s, with 1.2–7.1 s gaps (≈ 70 s without frames); the tracker's gate uses the measured frame interval |
| the ride | from the drift of static tracks: departs from standstill, seven stops (168–209, 291–306, 439–459, 592–648, 760–775, 984–1007, 1106–1117 s), top speed 21.3 m/s at t ≈ 230 s, mean 11.5 m/s, ≈ 13 km |
| scenes | tunnels of both kinds, curves down to R ≈ 350 m (files 129–134, 176–180), stations and a switch; files 22, 55, 113–114 and 155 have the track model unlocked (platforms, switch) |

Every alarm on the ride is a false alarm (counts: [`SCORECARD.md`](SCORECARD.md),
[`EXPERIMENTS.md`](EXPERIMENTS.md)). `labels/new_data_objects.json` lists every confirmed track of
the v0.6.2 run (23.09, historical) with its geometry and a cause class (`scripts/mine_objects.py`).

## Topic and sensor

* **Both (topic, frame) pairs may occur in the control data** — `/lidar_points` + `hesai_lidar`
  and `/sensing/lidar/hesai128/pointcloud` + `lidar_livox` — and **all data were recorded with the
  same LiDAR** (organizers, 23.09, [`organizers/answers.md`](organizers/answers.md)): the 120°
  window and the full turn are two configurations / mounts of one Pandar128. The node
  auto-discovers PointCloud2 topics and restarts the detector per recording (README "How a bag is
  processed"); RViz uses the fixed frame `resense_lidar`, linked to whatever frame the input has.
* **Full turn** (`doubleT_obstacle`): 3600 azimuth columns × 128 rings × 2 returns = 921 600
  slots, valid returns over ~210° (−104° … +106°), ~347 k valid points. **120° window** (the other
  recordings): 1200 columns × 128 × 2 = 307 200 slots, valid returns within ±50°, 160–190 k
  points (fewer at platforms). Azimuth = `atan2(x, −y)` in the sensor frame.
* `sensor_msgs/msg/PointCloud2`, ~10 Hz (80–120 ms in the bag clock), `point_step` 26. Fields:
  `x y z` float32, `intensity` float32 (reflectivity %, median 6–7, retro-reflectors 255), `ring`
  uint16 (0–127), `timestamp` float64 (sensor clock, **not synchronised**: year-2000 epoch).
* **Dual-return slots.** Missing returns are stored as `(0,0,0)`, ~38 % of the slots; 96–98 % of
  the valid points come in identical pairs (one echo stored in both return blocks, measured in all
  seven recordings), so a 120° frame holds ~190 k valid but 85–95 k distinct points. The detector
  counts occupied voxels, so the copies change no decision ([`SENSOR.md`](SENSOR.md) §2, §4).
* Angular grid: azimuth step **0.1°**; 128 rings from **+14.4° to −25.1°**, **0.125° step in the
  band +2° … −6.2°**, 0.5° outside; one 120° sweep takes 33 ms. The unit is a **Hesai Pandar128
  (E3X)** ([`SENSOR.md`](SENSOR.md) §1).
* Range: nothing beyond 209.2–210.0 m; walls return to ~150–200 m, the bed to ~100 m.
* Sensor frame: **−y forward, +x left, +z up**; the package maps it to the vehicle frame X forward
  / Y left / Z up (`sensor.forward/left/up` in `configs/default.yaml`).

## Geometry seen in the data

* Round tunnel: inner radius ≈ 2.5–2.7 m, crown ≈ 3.4 m above the sensor, bed ≈ 1.5 m below it
  (≈ 2.0 m on the `doubleT_obstacle` rig). The mount is calibrated from the data: 1.12 m and
  1.51 m above the rail head on the two rigs, against the organizers' 1 075 mm ([`SENSOR.md`](SENSOR.md) §4).
* Track axis 0.05–0.25 m right of the sensor axis; 1.59 m between rail-head centres; rail head
  ≈ 0.30–0.42 m above the 20th-percentile bed (a central drainage trough).
* Contact rail with its cover ~1.6–2.0 m left of the axis, top ≈ 0.35–0.5 m above the rail head;
  column rows ≈ 1.7 m and platform edges ≈ 1.6 m from the axis (the envelope's half-width is
  1.05 m); a pressure gate's frame narrows the tunnel to about the structure gauge.
* Curves R ≈ 350–3000 m: a straight corridor cuts into the wall beyond 50–100 m, hence the
  wall-based yaw / curvature estimate ([`ALGORITHM.md`](ALGORITHM.md) §3.1).

## Point budget at range (why 300 m is hard)

Angular resolution 0.1° × 0.125° ⇒ a target of w × h metres at range r returns roughly
`n ≈ w·h / (r² · 3.8e-6)` points per frame (single return, normal incidence):

| target | 50 m | 100 m | 150 m | 200 m | 300 m |
|---|---|---|---|---|---|
| 0.5 × 0.5 m box | 26 | 6.6 | 2.9 | 1.6 | 0.7 |
| person 0.5 × 1.7 m | 90 | 22 | 10 | 5.6 | 2.5 |
| 1 × 1 m crate | 105 | 26 | 12 | 6.6 | 2.9 |

Beyond ~150 m a single frame gives a handful of points, and no recording has a return beyond
210 m: 300 m is out of reach for this sensor ([`SENSOR.md`](SENSOR.md) §3).

## Cached frames for fast iteration

`resense.io.iter_bag_compact` reads bags without ROS (`rosbags`); frames are cached as `*.npy`:

```bash
python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/roundT_doubleT --every 1 --int16 --stamps   # ~1.5 MB / frame
```

`--int16` writes `resense.pointcloud.COMPACT16_DTYPE` (centimetres as int16, intensity and ring as
uint8: 8 bytes per point; 5 mm quantisation, a quarter of the range noise).
`compact16_dedup` can store each identical dual-return pair once (~0.75 MB per frame; the reader
restores them). `--stamps` writes `<name>_stamps.json` (bag receive time and `frame_id` per
frame), which `resense.io.iter_npy_frames` uses for the frame interval. The six bags take 3.6 GB,
the ride 8.0 GB (deduplicated). The file name carries the **bag frame index**
(`roundT_doubleT_0120.npy` = message 120, 0-based), which `resense eval --npy <dir> --gt gt.json`
uses to find the labels. `scripts/eval_real.py --cache <dir>` runs one configuration over every
cached recording (the ride in eight parallel pieces); `scripts/far_range_eval.py` builds set F.

## Synthetic obstacles (`resense inject`)

`resense inject` ray-casts catalogue objects into empty real frames with the sensor's own angular
grid (occlusion-correct; range-dependent dropout beyond 120 m scaled by reflectivity). Objects
are chosen with `--kinds` from `resense.synthetic.OBJECT_CATALOGUE`:

| name | mesh | size L × W × H (m) | reflectivity (%) | stands for |
|---|---|---|---|---|
| `person` / `hivis` | cylinder body + head sphere | 0.4 × 0.5 × 1.7 | 10–60 / 150–250 | person in ordinary clothing / a hi-vis vest |
| `box0.2`, `box0.3`, `box0.5` (`box`), `box1.0` | box | cube of that edge | 20–40 (`box0.3`: 20–60) | cardboard box / crate |
| `lowbox` | box | 0.3 × 0.3 × 0.1 | 20–60 | the organizers' minimum object |
| `plank` | box | 2.0 × 0.25 × 0.30 | 30–60 | wooden plank / sleeper |
| `railobj` | box | 0.4 × 0.6 × 0.31 | 15–40 | replica of the object across a rail in `doubleT_obstacle` |
| `trolley` / `cylinder` / `sphere` | cylinder / cylinder / sphere | 0.6 × 0.6 × 1.0 / 0.4 × 0.4 × 0.9 / 0.4 × 0.4 × 0.4 | 40–120 / 30–90 / 20–60 | maintenance trolley / drum / ball-like debris |
| `cable` / `cable_low` | thin cylinder | 0.03 × 0.03 × 3.5 / 4.3 | 10–40 | broken cable hanging to 1.0 / 0.2 m above the rail head |
| `dog` | box | 0.6 × 0.3 × 0.45 | 10–40 | animal-sized object on the bed |

Reflectivity is drawn uniformly per object ([`SENSOR.md`](SENSOR.md) §2). The ranges are
assumptions: the real labels give three observed ones (mean intensity p05 / median / p95):
`person_crossing` 35.7 / 59.8 / 68.2, `person_walkway` 39.1 / 74.4 / 96.1, `object_on_rail`
13.6 / 15.4 / 22.5. The intervals are kept for reproducibility; `--reflectivity V` (also in
`scripts/far_range_eval.py`) fixes the value for a paired sensitivity run.

**Placement.** `--per-frame` objects per background, distance uniform in `--distances lo:hi`,
lateral uniform ±0.9 m, or for the `--negative-fraction` share 2.2–3.0 m to either side (must
**not** alarm, `in_gauge = false`), random yaw. Ground objects stand on the measured local bed, or
0.25 m below the model's rail level where the bed has no returns; `gt.json` stores the resulting
`base_z`. `--augment` perturbs the background (5 % dropout, 1 cm range noise, ±0.3° yaw / pitch,
±0.2° roll, 10 % intensity jitter). `--sequence N --speed V` keeps the background and moves the
objects by `V × 0.1 s` per step (rows carry `seq`, `seq_step`, `speed_mps`): a test of persistence
and association, not of ego-motion; `resense eval` passes the rows' speed to the detector. Set
F's placement modes are in [`EVALUATION.md`](EVALUATION.md) §3.

## Label format (`gt.json`)

One JSON object per bag (or injected dataset), **keyed by the bag frame index** as a zero-padded
5-digit string. `resense inject` writes it, `resense eval` and `resense summarize --gt` read it,
and the browser label tool (`web/`) exports it.

```json
{"_meta": {"bag": "doubleT_obstacle", "source": "label-tool", "coords": "vehicle"},
 "00042": [{"kind": "person", "size": [0.4, 0.5, 1.7], "distance": 55.6, "lateral": -0.2,
            "yaw_deg": 0.0, "reflectivity": 40.0, "label": "person_crossing", "in_gauge": true}],
 "00043": []}
```

| key | meaning |
|---|---|
| frame key | bag frame index in message order, 0-based, 5 digits: the `frame` field of `resense run --out`, the index `resense info` / `iter_bag_compact` count and the number in cache file names; an injected dataset uses its own running index |
| value | objects in that frame; **`[]` = looked at and empty** (a negative label); a frame without a key is unlabelled and counts as empty unless `--labelled-only`; keys starting with `_` (`_meta`) are ignored |
| `kind` | geometry class (`person`, `box`, `plank`, `cylinder`, `sphere`; real labels any short class) |
| `size` | `[L, W, H]` m: along the track, across it, height |
| `distance` | m, **X (forward, vehicle frame) of the object's nearest point**; what `nearest_distance` reports and the match tolerance applies to |
| `lateral` | m, offset of the object centre from the **track axis**, + left (a tool that only knows the vehicle frame may use Y: the axis is typically within 0.25 m of it, inside the 1 m match tolerance) |
| `yaw_deg`, `reflectivity` | rotation about Z; mean intensity of the returns (0 when unknown) |
| `label` | **one string per physical object, kept across frames**; first-detection distance is per label |
| `in_gauge` | `true` if the object's rotated footprint intersects the strict envelope (must alarm); `false` for objects next to the track that must **not** alarm |
| `name` | optional catalogue name or real class; the per-class recall table is keyed by it (falls back to `kind`) |
| `n_points` | optional: ray hits; **`0` = fully occluded**, excluded from recall and counted in `occluded_gt_skipped` |
| `bbox` | optional `[[xmin, ymin, zmin], [xmax, ymax, zmax]]` in the vehicle frame; missing `distance` / `size` / `lateral` are derived from it (raw sensor frame → vehicle: `X = −y_s`, `Y = x_s`, `Z = z_s`) |
| `seq`, `seq_step`, `speed_mps` | written by `inject --sequence N --speed V` |

Matching (`resense/metrics.py`, [`EVALUATION.md`](EVALUATION.md) §2): |Δdistance| ≤ max(2 m, 3 %
of range) + L/2 and |Δlateral| ≤ 1 m, in the vehicle frame. Use `resense eval … --repeat 1` on
real sequences (true frame order); static injected frames default to
`tracking.frames_to_confirm()` repeats (5 at 10 Hz), with a tracker reset per background.

## Real labels (set R): `labels/doubleT_obstacle.json`

Made by P4 from the cached frames of `doubleT_obstacle` with the recipe below — **not** from the
detector's output, but with its per-frame track model ([`EVALUATION.md`](EVALUATION.md) §1). All
201 frames carry a label list.

| label | frames | where | `in_gauge` |
|---|---|---|---|
| `person_crossing` | 0–200 | 55.4–56.7 m ahead; lateral +1.8 m (frame 0) → −0.26 m (35–45, on the axis) → +1.5 m (70) → +2.5 m (90–115) → +2.33 m (140–200, standing at 54.65 m) | **true in frames 8–68** (61 frames) |
| `object_on_rail` | 0–200 | ~0.45 × 0.6 × 0.3 m at X 56.1–56.6 m, lateral −0.6 … −1.2 m (on the right rail), top 0.07–0.22 m above the rail head; 19–23 points; hidden by the person in 16 frames (`n_points` 0) | true |
| `person_walkway` | 146–200 | walks away along the left side: X 0.9 → 15.4 m, lateral +2.2 … +2.5 m, ~2.8 m/s | false (0.4–0.8 m outside) |

Recipe (package functions only, so the file can be rebuilt):

1. Each cached frame → `resense.frame.frame_from_compact` (vehicle frame) and the per-frame
   `resense.track.estimate_track` for the rail-head height; the lateral axis is the **median of
   the 201 per-frame axes** (centre −0.225 m, yaw −1.25°; the train does not move).
2. Far window X 50–62 m, |dy| ≤ 4 m, 0.1–2.3 m above the rail head → DBSCAN (0.4 m, 4); a person
   is ≥ 15 points, ≤ 1.2 × 1.3 m, 0.6–2.0 m tall: exactly one per frame. Near window X 0.5–25 m,
   dy 0.8–3.5 m, static background removed → DBSCAN (0.35 m, 5): the walking person, frames
   146–200. The rail object: the points in X 55.9–56.8 m, dy −1.3 … −0.55 m, h −0.15 … +0.45 m.
3. `distance` = X of the nearest point, `lateral` = mean dy from the median axis; `in_gauge` = the
   nearest edge inside the 1.05 m half-width, `gauge_margin` = 1.05 − edge (the old 1.40 m polygon
   survives only as `in_gauge_v05` / `gauge_margin_v05`). Checked by eye on renders
   (`resense run --npy … --start F --limit 1 --render out/render`, F = 0, 40, 72, 100, 165, 200).

## How to check a new bag (intake recipe)

Before anything is labelled or run, `resense info <bag>` (metadata and first frame); record in
the recordings table: **duration, frames, size, topic, `frame_id`**, the **`width`** of
the first message (307 200 = 120° window, 921 600 = full turn), its **point count** and
**azimuth span** (~100° of valid returns for a 120° window, ~210° for the full turn) and the
**frame period** (≈ 0.1 s). Then:

1. `resense run --bag <bag> --limit 30` — the track model must lock (`yc` stable within a few cm,
   median `track.rail_score` 0.15–0.19; single frames can drop to 0) and an empty tunnel start
   must not alarm; a jumping `track.center` or `n_corridor` 0 means the axis mapping
   (`sensor.forward/left/up`) or the topic is wrong for that bag.
2. `scripts/cache_frames.py <bag> cache/<bag> --every 10` — cached frames.
3. If the bag holds an obstacle: label it with the tool (format above), keep it as
   `labels/<bag>.json` and run `resense eval --bag <bag> --gt labels/<bag>.json --repeat 1 --text`.
4. Add the table row with the scene; only what was read from the bag goes in (a value copied
   from another bag is marked as such).
