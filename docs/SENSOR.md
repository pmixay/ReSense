# Sensor: Hesai Pandar128 (E3X)

*На русском: [SENSOR.ru.md](SENSOR.ru.md).*

> **Purpose:** what the LiDAR that recorded the organizers' data is and can do, from its manual and
> from the recordings, and what that implies for the detector and the evaluation.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN, summary RU
> **Last verified:** 2026-09-29: the manual's figures, the organizers' answers and the node's
> current timings · **Status:** current

**Кратко.** Данные организаторов записаны лидаром Hesai Pandar128 (E3X): 128 каналов, 10 Гц; в
записях — окно 120° с шагом 0,1° по азимуту и 0,125° по вертикали около горизонта. По паспорту
200 м при отражательной способности 10 % дают только 32 канала у горизонта; ни в одной записи нет
точек дальше 210 м, поэтому 300 м для этого датчика недостижимы. Интенсивность — отражательная
способность в процентах (больше 100 — световозвращающие материалы). Лидар стоит на 1 075 мм выше
головки рельса по оси состава (ответ организаторов 24.09); автокалибровка измеряет 1,12 м.

Source: the user manual handed out by the organizers,
[`sensor/Pandar128E3X_v4p5_User_Manual_128-en-240710-1.pdf`](sensor/Pandar128E3X_v4p5_User_Manual_128-en-240710-1.pdf)
(Hesai 128-en-240710, July 2024, sha256 `69c09eb2af5eb358e6d76559108238f15a1ee57b742560b8be8d7fce582e915a`;
section and appendix numbers below are the manual's). It is the organizers' hand-out for the
team's own use: do not redistribute it outside the hackathon. The angle correction file and the
STEP model are on Hesai's downloads page, https://www.hesaitech.com/downloads/#pandar128. The
"measured" values are what [`DATASET.md`](DATASET.md) found in the recordings.

## 1. Identification

The recordings come from a **Pandar128**, not an AT-series unit as first assumed:

| property | manual (Pandar128) | measured in the bags |
|---|---|---|
| channels | 128 | 128 rings |
| vertical FOV | 40° (−25° … +15°) | +14.40° … −25.12° |
| fine vertical band | 0.125° on channels 26–90 (+2.01° … −6.10°) | 0.125° step on rings 26–90 (+2.0° … −6.2°) |
| coarse bands | 0.5° on channels 2–26 and 90–127, 1° at the ends | 0.5° outside the fine band |
| per-channel elevations | channel 1 = +14.436°, channel 128 = −25.016° (angle correction file) | ring 0 = +14.402°, ring 127 = −25.120°; all 128 within 0.12° |
| horizontal resolution | High Resolution mode at 10 Hz: 0.1° on channels 26–89, 0.2° elsewhere; Standard (default) 0.2°; near field (< 2.85 m) 0.4° (§4.4) | 0.1° column grid (1200 columns for the 120° window) |
| horizontal FOV | 360°, configurable azimuth windows (up to 5) | 120° window (returns within ±50°) or the full turn |
| frame rate | 10 Hz / 20 Hz | ~10 Hz |
| return modes | single (last / strongest / first) or dual | dual, 2 blocks per firing |
| range | 0.3 … 200 m @ 10 % reflectivity | last returns at 209.2–210.0 m in every recording |

`resense/sensor.py` keeps the measured ring elevations (each unit carries its own calibration).

## 2. Specifications that matter for the project

| item | value | consequence |
|---|---|---|
| instrumented range per channel | **200 m only on channels 26–89** (+2.0° … −6.0°); 100 m on the others | beyond ~15 m the corridor is seen only by the 200 m channels: at the organizers' 1.075 m sensor height the rail head is at −0.6° at 100 m and −0.3° at 200 m |
| max range at 10 % reflectivity | **200 m on the 32 "far-field enhanced" channels 34–65** (≈ +0.95° … −3.0°); 140 m on the rest of 26–89 (200 m needs 37 %) | a dark object is detectable to 200 m only within a ~4° band around the horizon — where a 1–2 m obstacle at 100–200 m sits. **300 m is out of range** for ordinary targets |
| ranging accuracy | ±2 cm (1–200 m); ±5 cm below 1 m | the reported distance is limited by clustering (nearest point), not by the sensor |
| minimum range | 0.3 m on 32 near-field channels, 2.7 m on the others | `sensor.min_range` 2.5 m discards the near field, which holds only the train's own nose |
| point rate | 3 456 000 pts/s single, 6 912 000 dual (360°) | ~190 k valid points per 120° frame, ~347 k at 360° |
| dual return blocks | two blocks per firing with the same azimuth (§3.1.2.3); in Last and First mode a single return fills both; in Last and Strongest (default) block 2 holds the second strongest | in all seven recordings 96–98 % of the points come in identical pairs (one echo in both blocks): 85–95 k distinct points per 120° frame. The detector counts occupied voxels, so the copies change no decision |
| reflectivity | 0–255, linear mapping by default (value = reflectivity %); > 100 for retro-reflectors; two optional non-linear mappings (Appendix C) | the bags match the linear mapping (median 6–7, rails and signs 255): `intensity` is reflectivity %. A non-linear mapping would need `cluster.retro_intensity` re-derived |
| clock | GNSS or PTP, ≤ 1 µs; without a source the clock starts at a virtual 2000-01-01 | the bags have no clock source: use the bag receive time; no per-point deskew |
| built-in IMU | every packet tail carries 3-axis acceleration and angular rate (§3.1.2.5) | enough for vibration / pitch compensation, but the `PointCloud2` messages do not carry it; the solution works without IMU or speed input (§4) |
| factory defaults (§4) | 10 Hz, Last and Strongest, Standard resolution (0.2°), linear reflectivity, azimuth FOV 0–360° | the recording unit was reconfigured (0.1° columns, 120° window); the control data use the same settings (§4), so the point budget in [`DATASET.md`](DATASET.md) "Point budget at range" holds |
| sweep and motion | one 120° window is swept in 33 ms; at 80 km/h that is 0.7 m of travel within a frame, 2.2 m between frames | multi-frame accumulation needs the ego motion per frame; per-point deskew would matter above ~40 km/h |
| coordinate system | Z = rotation axis, Y = 0° azimuth, clockwise (top view) | in the bags forward = −Y, left = +X, up = +Z; `sensor.forward/left/up` in `configs/default.yaml` captures this and nothing else depends on the model |
| mechanical | 1.63 kg, Ø116 × 124 mm, IP6K7 / IP6K9K, −40 … 85 °C, 23–27 W, ISO 26262 ASIL B | automotive-grade unit |

## 3. Implications for the algorithm and the evaluation

1. **Range.** Spec §8.2 rates 300 m as excellent; a 10 %-reflectivity target is instrumented to
   200 m, and only on the 32 horizon channels, and no recording has a return beyond ~210 m. The
   evaluation bins ([`EVALUATION.md`](EVALUATION.md) §2) keep 200–300 m for completeness only.
2. **The corridor is in the best channels.** Beyond ~15 m the bed and everything on it is seen by
   the 0.125° × 0.1° channels, beyond ~30 m by the far-field enhanced ones; the expected-point
   prior in `resense/sensor.py` uses that fine step. The coarse channels' 100 m limit affects only
   the roof and the near bed.
3. **Reflectivity is calibrated.** A threshold above 100 isolates retro-reflective material (signs,
   polished rail heads): the retro-reflector rule ([`ALGORITHM.md`](ALGORITHM.md) §3.3 item 6),
   off by default (`cluster.retro_intensity: 0`: it never fired on the six bags).
4. **Ego-motion.** With PTP each point would carry a µs timestamp and the accumulation could
   deskew within a frame; the organizers said this will not come within this hackathon.
5. **Another unit or mount.** The detector never uses the ring index; only `resense inject` and
   the expected-point prior use the elevation table. A different Pandar128 or mount needs no code
   change (the mount is calibrated from the data); a different model would degrade only the
   injector and the visibility score.
6. **Data-rate headroom.** A full turn has 3× the slots of the 120° window. The node's decode takes
   16.6 ms median at 360° and 4.8 ms at 120° (since 29.09); with the native kernels decode +
   detect stays below the 100 ms period on 4 cores (timings: [`SCORECARD.md`](SCORECARD.md),
   [`EXPERIMENTS.md`](EXPERIMENTS.md)); the numpy fallback does not keep up at 360°. The range and
   azimuth crop happen after decoding, so a wider window costs decode time only.

## 4. Questions to the organizers (answered)

* **Return mode, resolution and window** (24.09, [`organizers/answers.md`](organizers/answers.md)
  §3). The unit is on Last and Strongest now; the provided recordings, especially
  `doubleT_obstacle`, are old and may have used another mode; **the control data use the same
  settings**. Both (topic, frame) pairs may occur, from one LiDAR (answers of 23.09).
* **PTP / GNSS time.** It will exist on the train, but not within this hackathon: the bag receive
  time and the differences of the year-2000 `header.stamp` remain the clocks.
* **Mount.** Not fixed between trains ("count on a variable position, set it in the launch
  parameters", 22.09); the test bags use the mounts of the provided recordings, with the LiDAR
  **1 075 mm above the rail head, on the train's centreline**, no numeric orientation
  ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md)). The calibration
  measures 1.12 m (lateral −0.02 m) on `roundT_doubleT` and 1.51 m with a +3.0° roll on the older
  `doubleT_obstacle` rig, so it stays on as the safeguard, with the mount launch arguments
  ([`ALGORITHM.md`](ALGORITHM.md) §2b).
* **Train speed.** The recordings carry no odometry and some trains have none (Q&A 22.09): the
  solution works without speed, odometry or IMU; the node's speed inputs stay optional and the
  multi-frame accumulation stays off unless a speed is given. The LiDAR-only speed estimate is
  accurate (median error 0.06–0.08 m/s) but does not improve the organizers' check, so it stays
  opt-in ([experiment log](archive/EXPERIMENTS_log_2026-09.md) §9).
