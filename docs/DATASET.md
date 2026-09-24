# Dataset notes (organizers' bags, 2026-09)

**Download:** [`Датасет.zip`, 3.7 GB, Google Drive](https://drive.google.com/file/d/1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu/view)
(organizers' link, shared with the team — the bags themselves are never committed, see
`.gitignore`).

**Extended dataset (recorded 2026-09-17, link received 22.09):**
[`new_data.zst`, 17.1 GB, Yandex Disk](https://disk.yandex.ru/d/N8IUpAyd7jyvow) — a
zstd-compressed tar of **one 20-minute rosbag2 bag `new_data/`** split into 221 sqlite3 files
`new_data_<N>.db3` (408 MB / 51 frames each) plus its `metadata.yaml` (90 GB unpacked); what
was read from it is in the section "Extended dataset" below. `scripts/unpack_dataset.py`
streams it straight from the link (no 17 GB copy; since 24.09 the folder also holds
`cloud_with_fake_obj.zst`, so pass `--member new_data.zst`) or from a downloaded `new_data.zst`; the
unpacked directory is an ordinary bag (`resense info /data/new_data`, `ros2 bag play
/data/new_data`), and a single split file opens on its own with `resense run --bag
<file>.db3` (the `rosbags` reader does not need the metadata file).

**Synthetic-obstacle recording (24.09):**
[`cloud_with_fake_obj.zst`, 1.75 GB, Yandex Disk](https://disk.yandex.ru/d/KpkG_yKoGk-vHQ) —
a 151-second, 1,510-frame bag with ten obstacles the organizers ray-cast into a real
recording, in a known order. Labelled by P4 in
[`labels/cloud_with_fake_obj.json`](../labels/cloud_with_fake_obj.json); see
["Synthetic-obstacle recording"](#synthetic-obstacle-recording-cloud_with_fake_obj-labelled).
It must not be confused with the empty 20-minute `new_data` ride.

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
| `doubleT_obstacle` | 20.4 s | 201 | 4.5 GB | double-track tunnel, **train stationary**; a person crosses the track at 54.5–57 m (inside the current 2.1 m envelope in frames 8–68, then standing 2.1–2.5 m left of the axis until the end); a second person walks away from the train along the left side (X 1 → 16 m, 2.2–2.5 m left of the axis) in frames **146–200** — both labelled in `labels/doubleT_obstacle.json` (section "Real labels" below) |
| `doubleT_platform` | 34.4 s | 345 | 2.6 GB | double-track tunnel → station platform |
| `roundT_doubleT` | 25.1 s | 252 | 1.9 GB | round single-track tunnel → double-track tunnel (walls diverge) |
| `roundT_pressureGate_roundT` | 26.7 s | 268 | 2.0 GB | round tunnel through a pressure gate (гермозатвор), right-hand curve |
| `roundT_squareT_pressureGate_squareT` | 55.4 s | 545 | 4.1 GB | round → rectangular tunnel, pressure gate |
| `squareT_platform_squareT_switch` | 88.2 s | 877 | 6.6 GB | rectangular tunnel → platform (train stops) → switch |

Total 2 488 frames / 250 s (plus the 11 271-frame extended recording, section "Extended
dataset" below). **The obstacles inside the envelope in the six bags are in `doubleT_obstacle`:
the person crossing the track at 55–57 m** (inside the 2.1 m envelope in frames 8–68) **and the
object lying on the right rail next to it** (the organizers pointed it out in the Q&A session;
both labelled in `labels/doubleT_obstacle.json`); every alarm on the other five bags is a false
alarm.
The organizers confirmed that the extended `new_data` recording has no obstacles. Positive
examples at other ranges and for other objects therefore come from `resense inject` (synthetic
obstacles ray-cast into real frames, see ARCHITECTURE.md and "Set S" below).

## Synthetic-obstacle recording (`cloud_with_fake_obj`, labelled)

**Download:** [Yandex Disk](https://disk.yandex.ru/d/KpkG_yKoGk-vHQ) (the organizers' link of
24.09): `cloud_with_fake_obj.zst`, 1,746,145,824 bytes, SHA-256
`d41c2fb28475194a98efeca5d2ee3fd175c0aef350ffb92fff4c26d497e696e9` (MD5
`5c0cefe7ef10fae249b5ae653cbd165d`). The archive holds `cloud_with_fake_obj/metadata.yaml` and
one 7.42 GB `cloud_with_fake_obj_0.db3`. The bag has 1,510 PointCloud2 messages on
`/lidar_points`, frame `hesai_lidar` (the 120° pair), spanning 150.851 s. Unlike the original
bags, its cloud fields are `x,y,z,intensity` **without a ring field**; the reader fills a zero ring.

```bash
python scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out /data   # or the downloaded .zst
python scripts/cache_frames.py /data/cloud_with_fake_obj /data/cache/cloud_with_fake_obj --every 1 --int16 --stamps
python scripts/label_fake_objects.py /data/cloud_with_fake_obj --out labels/cloud_with_fake_obj.json   # ~2 min
resense run --npy /data/cache/cloud_with_fake_obj --out out/fake.jsonl --quiet
python scripts/score_fake_objects.py out/fake.jsonl --gt labels/cloud_with_fake_obj.json   # per-object table
resense eval --npy /data/cache/cloud_with_fake_obj --gt labels/cloud_with_fake_obj.json --repeat 1   # standard metrics
```

**What is in it (the organizers' description, 24.09).** The obstacles follow one another about
100 m apart, in this order:

| # | organizers' text | label | envelope (intent) |
|---|---|---|---|
| 1 | посередине габарита крупный, 2х2 метра | `big_center` | inside |
| 2 | посередине габарита мелкий 0.3х0.3 м | `small_center` | inside (floats at mid-height, 1.0–1.4 m above the rail head) |
| 3 | мелкий 0.3х0.3 м стоит на рельсах | `small_on_rail` | inside (on the left rail) |
| 4 | 0.3х0.3 м скраю габарита | `small_edge_inside` | inside (straddles the edge) |
| 5 | 0.3х0.3 м за пределами габарита, но близко | `small_outside_near` | outside |
| 6 | 2х2 метра скраю в пределах габарита | `big_edge_inside` | inside |
| 7 | 2х2 за пределами габарита | `big_outside` | outside |
| 8 | 2х2 сверху габарита | `big_above` | inside (see below) |
| 9 | длинный низкий предмет лежит на рельсах (2х0.2) | `long_low_on_rails` | inside (across both rails) |
| 10 | узкий длинный свисает с потолка (ширина 0.05 м) | `thin_hanging` | inside (hangs to 2.7 m above the rail head) |

**How the labels are made.** Each message is the organized real scan (128 × 2 400 points,
no-return points kept as zeros, the returns an object hides removed) **followed by the object
points, all with intensity 1**. `scripts/label_fake_objects.py` takes every point after the last
zero point of a message as object points, splits them into objects at X gaps over 8 m and links
them into tracks. Exactly ten tracks come out, and they pass the sensor in the organizers'
order. Frames 0–803 carry object points; frames 804–1509 are the real recording alone. Each
visible object-frame gets a row in the "Label format" below, 1,206 rows in all. `distance` and
`lateral` are measured in the detector's mount-calibrated frame from its per-frame track axis,
as for `doubleT_obstacle`. `in_gauge` is the organizers' intent. Extra keys:

* `gauge_margin` and `h_above_rail`: the measured position;
* `lateral_sensor`: the lateral offset from the sensor's own axis;
* `n_in_envelope`: object points inside the envelope measured from the rails;
* `plausible`: the object lies in the tunnel cross-section.

Three properties of the recording decide how it can be scored:

* **The objects move, the train does not follow them.** They approach at 14–20 m/s (object 1
  at 2–7 m/s). Frame-to-frame ICP on the real points shows the train itself slowing, backing up
  ~70 m over frames 300–650, creeping at under 1 m/s from frame ~850 to ~1200 and then moving on. The injected
  motion is therefore not ego-motion: a given train speed or the LiDAR speed estimator would
  accumulate the background wrongly. The shipped single-frame path is what can be scored.
* **The objects were placed from the sensor's axis, not from the rails.** Near the train the
  objects are centred on the sensor's Y = 0. The rails of this recording, fitted directly
  (0.76–0.81 m either side), run at **−0.24°** to that axis in frames 0–100, 400–500 and
  1300–1400, and the detector's axis agrees. The two frames differ by 0.1 m at 25 m and 0.4 m at
  100 m. So the edge tests (#4–#7) sit within ±0.1–0.4 m of the envelope edge, on different
  sides depending on the frame. For example, #5 "outside but close" has points inside the
  rail-measured envelope in 101 of its 112 frames. Further out, the objects follow the curve of
  their own path. It is not the tunnel: #3 "on the rail" is 4 m above the rail head at 81 m,
  and single points of #2 and #4 lie 17–37 m above or below the track beyond 200 m.
  `plausible` drops those rows from grading.
* **"сверху габарита" is read as the top of the envelope.** The bottom of #8 is 2.4–2.9 m above
  the rail head in both frames, inside the 3.0 m envelope, so it is labelled `in_gauge: true`.
  The opposite reading, "above the envelope, must not alarm", is question 4 in
  [`QUESTIONS.md`](QUESTIONS.md).

The first P4 pass (24.09, before the description arrived) scored the bag unlabelled: 342 alarm
frames / 9 track IDs / 459 advisory frames with the shipped detector
([`experiments_p4_fake_unlabelled.json`](experiments_p4_fake_unlabelled.json)). The per-object
grade is now in [`P4_AUDIT.md`](P4_AUDIT.md) "Organizer synthetic-obstacle recording" and
[`experiments_p4_fake_labelled.json`](experiments_p4_fake_labelled.json).

## Extended dataset: `new_data` (recorded 17.09, streamed and run on 22.09)

**What it is.** [`new_data.zst`](https://disk.yandex.ru/d/N8IUpAyd7jyvow) (17 078 961 996
bytes, sha256 `8124b627a8a70516a4023db522849f1cadae711e7b152b0f701535a69dab99ec`, uploaded
2026-09-17 12:51 UTC) is a zstd tar holding **one rosbag2 bag `new_data/`**: 221 sqlite3
split files `new_data_0.db3` … `new_data_220.db3` (407 789 568 bytes = 51 frames each, the
recorder's ~400 MB split size) and `metadata.yaml` as the last tar member (rosbag2 metadata
version 5, one topic, 11 271 messages, 1 199.9 s, `relative_file_paths` listing all 221
files). Unpacked it is 90.1 GB, 5.3× the archive. The extracted directory is an ordinary bag
(`resense info /data/new_data`, `resense run --bag /data/new_data`, `ros2 bag play
/data/new_data`, the launch file's `bag:=/data/new_data`); a single split file also opens on
its own (`resense run --bag /data/new_data/new_data_30.db3`, `scripts/cache_frames.py
/data/new_data/new_data_30.db3 cache/new_data --every 10`), which is what the intake used.

**Intake** (the recipe of "How to check a new bag" below, every file read on 22.09; the
sandbox had 9 GB of disk, so the archive was streamed once — `curl … | zstd -d | tar`, 16 MB/s,
20 min — and every split file was processed as it arrived and deleted: `sqlite3` counts, the
first message's header and layout, every frame decoded, the v0.5 detector at full rate with a
fresh detector per file, every 10th frame cached as `new_data_<N>_<i>.npy` (1 326 files,
4.1 GB). Per-file rows, the first message and the alarm events are in
[`extended_dataset_intake.json`](extended_dataset_intake.json)):

| what | read from the bag |
|---|---|
| topic / type | `/lidar_points`, `sensor_msgs/msg/PointCloud2`, cdr — the only topic; 11 271 messages (`metadata.yaml` and the 221 files agree, 51 per file) |
| `frame_id` | `hesai_lidar` in every file |
| layout | `height 1`, `width 307 200`, `point_step 26`, fields `x y z intensity` float32, `ring` uint16, `timestamp` float64 — identical to the five 120°-window bags above |
| azimuth window | valid returns within −49.5° … +49.6° (0.5–99.5 percentiles of the first frame of every file): the 120° window, 1200 columns |
| points per frame | 152 754 – 191 094 valid (median ≈ 183 k); the low values are stations, where the near walls are missing |
| rings / range / intensity | 128 rings; last returns to 210 m (every recording stops at 209.2–210.0 m); p99 of ranges ≈ 65 m; intensity median 8, retro-reflectors 255 (linear reflectivity mapping, `SENSOR.md` §2) |
| clock | bag receive time starts 2026-09-17 11:02:06 UTC; `header.stamp` is still the year-2000 sensor clock — use the bag time, as before |
| frame period | 0.100 s inside a file and 0.100 s from the last frame of file N to the first of N+1 (max 0.12 s): **one continuous recording** — except **recording holes in the last third**: from file 156 (t ≈ 800 s) on, 26 files span 6–12 s instead of 5.1 s, with gaps of 1.2–7.1 s between consecutive frames (`period_max` per file in the JSON). 51 frames still sit in every file, so ≈ 70 s of the 1 200 s carry no frames; `ros2 bag play` pauses there and the tracker's gate (measured frame interval, `tracking.py`) is what keeps a track alive across such a gap |
| the ride | from the drift of static tracks (m/s per file, `speed_tracks` in the JSON — the estimator in the detector is off, `EXPERIMENTS.md` §1b): departs from standstill at t = 0, stops at 168–209 s, 291–306, 439–459, 592–648, 760–775, 984–1007 and 1106–1117 s (seven stops: stations or signals), top speed 21.3 m/s (77 km/h) at t ≈ 230 s, mean 11.5 m/s, ≈ 13 km covered |
| scenes | tunnels of both kinds, curves down to R ≈ 350 m (median \|curvature\| up to 3·10⁻³ m⁻¹ in files 129–134, 176–180), stations and a switch — files 22, 55, 113–114 and 155 have the track model unlocked (median `rail_score` < 0.1, platforms / switch, as in `squareT_platform_squareT_switch`). **No labels and no obstacles**: confirmed by the organizers (Q&A session 22.09; written answer 23.09 "В new_data препятствий нет", [`organizers/answers.md`](organizers/answers.md)) |

**v0.5 defaults at full rate** (every frame, fresh detector per 51-frame file, no speed given;
raw per-frame JSONL kept out of git, 442 files / 17 MB):

| frames | alarm frames | alarm events | events / hour | events / km | advisory frames | latency mean / p95 / max |
|---|---|---|---|---|---|---|
| 11 271 (1 200 s) | 358 (3.2 %) | 102 | 306 | 7.9 | 8 564 (76 %) | 41 / 74 / 157 ms |

For scale: the five obstacle-free organizer bags give v0.5 96 alarm frames / 32 events in
230 s, ≈ 500 events per hour (`EXPERIMENTS.md` §1). Where the 102 events sit (median lateral
offset of each event, `events` in the JSON; 27 last one frame, 31 last ≥ 5 frames, the longest
21 frames):

* **40 at the left gauge edge** (lateral −1.35 … −1.65 m, bottom ≈ 0.6 m above the rail head,
  median 0.9 m long × 0.7 m tall, median first distance 61 m): the contact-rail side — brackets
  and insulators above the cover, which flip from the advisory zone into the gauge at 40–100 m
  where the axis is uncertain by ±0.5 m. The same family as the edge false alarms of §1b, now
  the largest single cause (the column row of `doubleT_obstacle` was the right-hand version).
* **16 at the right edge** (+1.5 m): the same on the other side, in the double-track sections
  the column row (file 81 at 95–106 m: 0.2–0.5 × 0.5–0.7 × 1.5 m clusters 1.0–1.6 m above the
  rail head, the columns' feet).
* **28 central** (|lateral| < 0.8 m): 11 in the unlocked-track files (a switch in file 22 — a
  "7 m × 0.4 m × 0.2 m object" at 6–8 m is the diverging rail; platform-end structures 2–3 m
  tall at 25–55 m in files 22, 23, 113, 114); 17 of the 28 have ≤ 15 points at 60–140 m (thin
  clusters on the bed or hanging 0.7–1.9 m above the rail head — cables, signs). Only five
  central events outside the unlocked files have more than 15 points, all 1.5–3.1 m tall
  structures at 48–115 m (files 23, 53, 64, 81, 138) that last 1–7 frames.
* 18 in between (0.8–1.35 m), mostly the edge family seen with a worse axis.
* 4 events while the train stands (files 188, 190, 207): 4–12-point clusters at 82–139 m.

**Organizers' answer (Q&A session, 22.09):** nothing is staged in `new_data` — "all we can give
is more empty tunnel"; no labels exist; the hidden check adds synthetic obstacles made with the
organizers' own tool. Every alarm on this ride is therefore a false alarm. The v0.6 object list
of the ride (every confirmed track, alarm or advisory, with geometry and cause class) is
`labels/new_data_objects.json`; the classes and counts are in EXPERIMENTS.md §1d.

Renders looked at (from the cache, `resense run --npy … --render`): file 22 frame 10 (switch:
diverging track, axis wanders), 55 frames 10 and 20 (platform: the axis bends into the
platform, a straight fit two frames later), 81 frame 10 (double-track, columns on the right),
134 frame 20 (R ≈ 350 m curve, the corridor follows the wall; candidates are wall / ceiling
brackets, rejected as elevated). Nothing person- or box-like sits in the gauge for more than a
few frames below 60 m outside station ends — as far as one can say without labels.

**What follows.** (1) `new_data` has no staged obstacles, so it supports false-alarm and
generalisation checks but cannot add real positive recall; the known positive labels are in
`labels/doubleT_obstacle.json`. (2) P3: the left-edge family is now the largest cause
(40 of 102 events) — the contact-rail side needs the same treatment as the column row (`edge`
signature with the rail-side offset), and the switch / platform-end cases need the track model
to declare itself unlocked rather than fit a platform. (3) Run the bag in one go
(`resense run --bag /data/new_data --out …`) on a machine with 90 GB free: the per-file numbers
above reset the tracker every 5.1 s (6 events start in frames 0–2 and 12 end in frames 49–50
of a file, so a continuous run can only merge a few of them). (4) `ros2 bag play
/data/new_data` through the container is the closest thing to the control run we have: 20 min,
seven stops, curves, stations, recording holes — the dry run should use it once the stand has
the disk.

## Topic and sensor

* **Organizers, 23.09 (written answer, [`organizers/answers.md`](organizers/answers.md)):** the control data may contain
  **both (topic, frame) pairs** — `/lidar_points` + `hesai_lidar` and
  `/sensing/lidar/hesai128/pointcloud` + `lidar_livox`; **all data were recorded with the same
  LiDAR**; the storage format matters little, the bag will most likely be played from the
  console. The two layouts below (120° window vs full turn, 307 200 vs 921 600 slots) are
  therefore two driver configurations / mounts of one Pandar128, not two sensors; the node
  handles both and restarts per recording (README "How a bag is processed"). Also 23.09:
  **`new_data` has no obstacles** (item 1).
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
* Range: last returns at 209–210 m (every recording stops at 209.2–210.0 m); the tunnel walls return points to ~150–200 m, the track bed to
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
  v0.5 gauge polygon was 1.4 m wide there; the v0.6 envelope is 1.05 m).
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
cache frames as compact `*.npy` (x, y, z, intensity, ring):

```bash
python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/ --every 10                  # float32, ~3.5 MB / frame
python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/roundT_doubleT --every 1 --int16 --stamps   # 1.5 MB / frame
```

**v0.6 cache formats.** `--int16` writes `resense.pointcloud.COMPACT16_DTYPE`: coordinates in
centimetres as int16 (±327 m), intensity and ring as uint8 — 8 bytes per point instead of 18;
the 5 mm quantisation is a quarter of the sensor's range noise, and `roundT_doubleT` gives the
same alarms from it as from the float cache (0 alarm frames, 222 vs 226 advisory frames).
`resense.pointcloud.compact16_dedup` additionally stores each pair of identical points once
with a flag in the ring's high bit: **49 % of the points of a frame are exact duplicates** (a
ray with a single echo repeats it in both return slots of the dual-return layout); the reader
(`expand_compact16`, called by `frame_from_compact`) restores them, so the detector sees the
same multiset of points (0.75 MB per frame). `--stamps` writes `<name>_stamps.json` with the
bag receive time of every frame; `resense.io.iter_npy_frames` then gives frames their bag
time (the measured frame interval matters for the tracker and the recording holes of
`new_data`) and plays split-file caches in natural order (`new_data_2_…` before
`new_data_10_…`). All 2 488 frames of the six bags (3.6 GB) and all 11 271 frames of the
extended ride (8.0 GB, deduplicated) were cached this way on 22.09 in ~10 minutes.

The file name carries the **bag frame index** (`roundT_doubleT_0120.npy` = message 120 of the
bag, 0-based, in message order). `resense eval --npy <dir> --gt gt.json` reads that number
back to find the frame's labels. `scripts/eval_real.py --cache <dir>` runs one configuration
over every cached recording (the ride split into parallel pieces) and prints the real-data
report card; `scripts/far_range_eval.py` builds set F (objects approaching on the moving ride,
EXPERIMENTS.md §2d); `scripts/mine_objects.py` lists every confirmed object of a run.

## Synthetic obstacles (`resense inject`)

Set F (`scripts/far_range_eval.py`) positives are **ray-cast synthetic objects** on real
empty backgrounds, not real long-range obstacle labels. `--placement-mode anchored` uses a
rail-supported near reference and near-frame motion instead of the far detector axis, but
remains dependent on track fits and estimated speed. `--placement-mode independent`
accepts an externally measured fixed axis and rail profile in the vehicle frame; do not
derive those parameters from the detector's far-field fit on the evaluated frames. The
report's per-frame `gt` rows carry `reference` (for anchored and independent runs) and
`base_z`, even when an object has zero returns; independent runs also carry `perturbation`.

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
| `lowbox` | box | 0.3 × 0.3 × 0.1 | 20–60 | organizers' minimum object on the track |
| `box0.3` | box | 0.3 × 0.3 × 0.3 | 20–60 | 30 cm cube |
| `cable` | thin cylinder | 0.03 × 0.03 × 3.5 | 10–40 | broken cable hanging to 1.0 m above the rail head |
| `cable_low` | thin cylinder | 0.03 × 0.03 × 4.3 | 10–40 | hanging to 0.2 m above the rail head |
| `dog` | box approximation | 0.6 × 0.3 × 0.45 | 10–40 | animal-sized object on the bed |
| `railobj` | box | 0.4 × 0.6 × 0.31 | 15–40 | replica of the organizers' object across a rail |

Reflectivity is drawn uniformly from the range per object (intensity in the bags is
reflectivity %, > 100 retro-reflective, [`SENSOR.md`](SENSOR.md) §2). Most ranges are
assumptions: `new_data` contains no real obstacles. The one labelled person and one object on a
rail provide the limited observed ranges below; they cannot calibrate every material or the
long-range dropout. Reflectivity affects the injected intensity and dropout beyond 120 m.

Observed **per-frame mean return intensity** in the committed real labels, using rows with
`n_points >= 15` (5th / 50th / 95th percentiles; repeated views of the same physical objects,
not independent material samples):

| real label | frames | p05 / median / p95 | catalogue assumption |
|---|---:|---:|---|
| `person_crossing` | 201 | 35.7 / 59.8 / 68.2 | `person`: 10–60 |
| `person_walkway` | 55 | 39.1 / 74.4 / 96.1 | `person`: 10–60 |
| `object_on_rail` | 152 | 13.6 / 15.4 / 22.5 | `railobj`: 15–40 |

The person and rail-object ranges do not fully cover these observations. We keep the old
catalogue intervals so the published synthetic experiments remain reproducible; a paired
material sensitivity run can set `resense inject --reflectivity 59.8` or
`scripts/far_range_eval.py --reflectivity 15.4` with the same seed. This changes only the
sampled reflectivity, not the seeded position, and no longer-range conclusion is drawn from
the near (~55 m) real labels.

Placement: one object set per background frame (`--per-frame`), distance uniform in
`--distances lo:hi`, lateral uniform ±0.9 m inside the gauge or, for the `--negative-fraction`
share, 2.2–3.0 m to either side (must **not** alarm, `in_gauge = false`), random yaw. The current
injector puts ground objects on the measured local bed, or uses the model's rail level minus
0.25 m corrected by the observed tunnel-vault drift where the bed has no returns. `gt.json`
stores the resulting `base_z`. Earlier set S runs used rail head − 0.15 m and need re-evaluation
before comparison with new results.

**Current set S rebuild recipe using the 21.09 frame selection** (EVALUATION.md §3;
historical scores in
[`experiments_v0.4_synthetic_on_real.json`](experiments_v0.4_synthetic_on_real.json) were
made with older placement and evaluation logic and must be re-run for a comparison; the
seeds still fix the same frame selection):

```bash
# static sets (recall by range per kind): every 10th frame of three empty bags, one catalogue
# object per frame, 20 % negatives outside the gauge; 26 / 27 / 55 frames, ~1.1 MB each
for bag in roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT; do
  resense inject --npy /data/cache/$bag --every 10 --out data/S_$bag \
      --kinds person,box0.5,box1.0,plank,trolley --distances 10:250 --negative-fraction 0.2 --seed 1
  resense eval data/S_$bag --text                   # five repeats emulate current persistence
done

# approach sequences (first-detection distance) on roundT_doubleT: 8 steps of 1.5 m (15 m/s)
# per background, one kind per set, seeds 1-3; 208 frames per set, deleted after the evaluation
for kind in person box0.5 box1.0 plank trolley; do for seed in 1 2 3; do
  resense inject --npy /data/cache/roundT_doubleT --every 10 --out data/SEQ_${kind}_s$seed --kinds $kind \
      --distances 10:250 --negative-fraction 0.2 --sequence 8 --speed 15 --seed $seed
  resense eval data/SEQ_${kind}_s$seed --repeat 1 --text                 # rows' speed_mps given to the detector
  resense eval data/SEQ_${kind}_s$seed --repeat 1 --no-gt-speed --text   # single-frame by default; estimator only if explicitly enabled
done; done

# robustness: augmented backgrounds (5 % dropout, 1 cm range noise, ±0.3° yaw/pitch, ±0.2° roll, 10 % intensity jitter)
resense inject --npy /data/cache/<bag> --every 10 --out data/synth_aug/<bag> --augment
```

`resense eval` gives the detector the `speed_mps` of `inject --sequence` rows on every frame
(`ego_speed_source: given`, the way the ROS node passes `ego_speed_mps` / odometry);
`--ego-speed V` forces a constant speed on any source, `--no-gt-speed` withholds the rows'
speed. Static sets carry `speed_mps: 0` and get nothing: the shipped default is single-frame
(`accumulation.estimate_speed: false`), as in `resense run` without a given speed. The LiDAR-only
estimator runs only when explicitly enabled. `resense run` and `resense bench` take the same
`--ego-speed V`.

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
| `in_gauge` | bool | `true` if the object's rotated horizontal footprint intersects the current strict envelope width (it must alarm, including low objects handled by the low stage); `false` for objects next to the track that must **not** alarm. The sampled inside/outside positions are separated enough that the current catalogue objects keep their intended labels. |
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

`--repeat 1` for real sequences (the tracker sees the true frame order); the default for static
injected frames is the current `tracking.frames_to_confirm()` (five with v0.6.3). The evaluator
resets the tracker between independently injected backgrounds or approach sequences and scopes
track IDs to each sequence when counting false-alarm events.

## Real labels (set R): `labels/doubleT_obstacle.json`

**v0.6 update (22.09).** (1) **`object_on_rail`**: the organizers pointed out in the Q&A session
(`organizers/QA_session.md` fact 8) that besides the person "an object lies on the rails where
the person stands". It is there for the whole bag: ~0.45 × 0.6 × 0.3 m at X 56.1–56.6 m,
lateral −0.6…−1.2 m (on the right rail), top 0.15–0.2 m above the mean rail-head level
(5–10 cm above its own rail once the 3° roll of this mount is corrected), 19–23 points per
frame; visible (≥ 5 points) in 183 of 201 frames, hidden by the person in 16 (`n_points` 0,
excluded from recall). Rows were added to every frame from the points in X 55.9–56.8 m,
dy −1.3…−0.55 m, h −0.15…+0.45 m of the per-frame track model. (2) **`in_gauge` now means the
organizers' 2.1 × 3.0 m envelope** (half-width 1.05 m): the crossing person is inside it in
frames 8–68 (61 frames; 71 frames 2–72 with the 1.40 m polygon of v0.5, kept as `in_gauge_v05`
/ `gauge_margin_v05`).

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
   per-frame rail head; `n_points` = cluster size for the people and 0 when the rail object is
   occluded by the person.
5. `in_gauge` = the nearest edge of the person, |lateral| − W/2, is inside the strict gauge
   half width of 1.05 m (`gauge.profile` in `configs/default.yaml`);
   `gauge_margin` = 1.05 − edge (m, negative = outside). The earlier 1.4 m polygon is retained
   only in `in_gauge_v05` / `gauge_margin_v05` for historical comparisons.
6. Checked by eye on renders: `resense run --npy /data/cache/doubleT_obstacle --start F
   --limit 1 --render out/render --x-max 70` for F = 0, 40, 72, 100, 165, 200 (the person
   cluster sits at the labelled X / Y in every render; `img/doubleT_obstacle_0020.png` and
   `_0165.png` are the v0 renders of the same scene), and against the v0.3 full-rate results
   (`/data/results/v0.3/doubleT_obstacle.jsonl`: track 6 follows the same lateral path,
   55.4–56.6 m, frames 2–72).

| label | frames | where | `in_gauge` |
|---|---|---|---|
| `person_crossing` | 0–200 (every frame) | 55.4–56.7 m ahead; lateral +1.8 m (frame 0) → +1.1 m (10) → +0.4 m (20) → −0.26 m (35–45, on the axis) → +0.6 m (60) → +1.5 m (70) → +1.8 m (73) → +2.5 m (90–115) → +2.33 m (140–200, standing still at 54.65 m) | **true in frames 8–68** (61 frames) under the current envelope; 2–72 (71 frames) was the old v0.5 polygon |
| `person_walkway` | 146–200 | walks away from the train along the left side: X 0.9 → 15.4 m, lateral +2.2…+2.5 m, ~2.8 m/s | false (edge 0.4–0.8 m outside the gauge) |

Two corrections to earlier notes: the walking person is in the **last** 55 frames, not the
first ones, and the standing person of `EXPERIMENTS.md` §1 (frame 165, "~1.8 m left") is
2.33 m left of the axis, 0.6 m outside the advisory corridor.

**Historical v0.4 results with the old 1.4 m polygon** (21.09, every frame of the cached bag,
commit f4e311f; the current `in_gauge` field uses 1.05 m, so these numbers are not a current
`resense eval --gt` result without restoring `in_gauge_v05` first):
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
