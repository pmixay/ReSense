# Sensor: Hesai Pandar128 (E3X)

> **Purpose:** what the LiDAR that recorded the organizers' data is and can do, from its manual and
> from the recordings, and what that implies for the detector and the evaluation.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN, summary RU
> **Last verified:** 2026-09-24 against `537e220` · **Status:** current

**Кратко.** Данные организаторов записаны лидаром Hesai Pandar128 (E3X): 128 каналов, 10 Гц; в
записях — окно 120° с шагом 0,1° по азимуту и 0,125° по вертикали около горизонта. По паспорту
200 м при отражательной способности 10 % дают только 32 канала у горизонта; ни в одной записи нет
точек дальше 210 м, поэтому 300 м для этого датчика недостижимы. Интенсивность — отражательная
способность в процентах (больше 100 — световозвращающие материалы). Лидар стоит на 1 075 мм выше
головки рельса по оси состава (ответ организаторов 24.09); автокалибровка измеряет 1,12 м.

Source: the user manual handed out by the organizers on 22.09, kept in the repository as
[`sensor/Pandar128E3X_v4p5_User_Manual_128-en-240710-1.pdf`](sensor/Pandar128E3X_v4p5_User_Manual_128-en-240710-1.pdf)
(Hesai document version 128-en-240710, July 2024, 145 pages, classification "Public", 5.4 MB,
sha256 `69c09eb2af5eb358e6d76559108238f15a1ee57b742560b8be8d7fce582e915a`). The angle
correction file `Pandar128_Angle_Correction_File`, the firetime correction file and the STEP
model are on Hesai's downloads page, https://www.hesaitech.com/downloads/#pandar128. The
manual's legal notice forbids reproducing it without Hesai's authorization, while its safety
notice requires integrators to give the users access to it: the copy here is the organizers'
hand-out for the team's own use — do not redistribute it outside the hackathon. An earlier
revision of this file cited "rev. 2025-11" from the downloads page; the hand-out is the
2024-07 version and every number below was re-checked against it on 22.09 (the sections and
appendices named below are the manual's own). The "measured" column is what
[`DATASET.md`](DATASET.md) found in the organizer bags.

## 1. Identification

The bags come from a **Pandar128**, not an AT-series unit as first assumed. Evidence:

| property | manual (Pandar128) | measured in the bags |
|---|---|---|
| channels | 128 | 128 rings |
| vertical FOV | 40° (−25° … +15°) | +14.40° … −25.12° |
| fine vertical band | 0.125° on channels 26–90 (+2.01° … −6.10°) | 0.125° step on rings 26–90 (+2.0° … −6.2°) |
| coarse bands | 0.5° on channels 2–26 and 90–127, 1° at the ends | 0.5° outside the fine band |
| per-channel elevations (angle correction file) | channel 1 = +14.436°, channel 128 = −25.016° | ring 0 = +14.402°, ring 127 = −25.120°; all 128 agree within 0.12° |
| horizontal resolution | High Resolution mode at 10 Hz: **0.1° on the 64 channels 26–89, 0.2° on the other channels**; Standard mode (factory default): 0.2° for all channels; near-field measurement (< 2.85 m) always 0.4° (§4.4) | 0.1° column grid (1200 columns for the 120° window); whether the coarse channels fill every column was not checked |
| horizontal FOV | 360°, configurable azimuth window(s) | 1200 columns = 120° window, returns within ±50° |
| frame rate | 10 Hz / 20 Hz | ~10 Hz |
| return modes | single (last / strongest / first), dual (last+strongest, last+first, first+strongest) | dual return, 2 × 153 600 slots |
| range | 0.3 … 200 m @ 10 % reflectivity | last returns at 209–210 m (every recording stops at 209.2–210.0 m) |

`resense/sensor.py` keeps the measured ring elevations; the design values from the angle
correction file differ by ≤ 0.12° (each real unit carries its own calibration), so the measured
table stays.

## 2. Specifications that matter for the project

| item | value | consequence |
|---|---|---|
| instrumented range per channel | **200 m only on channels 26–89** (elevation +2.0° … −6.0°); 100 m on channels 1–25 and 90–128 | the corridor beyond ~15 m is seen exclusively by the 200 m channels: for the organizers' sensor height of 1.075 m above the rail head the rail head is at −0.6° at 100 m and −0.3° at 200 m, the bed 0.26–0.34 m lower at −0.8° and −0.4°. The mount calibration measures 1.12 m (lateral −0.02 m) on `roundT_doubleT` and 1.51 m on the older `doubleT_obstacle` rig, where the rail head at 100 m is at −0.9° [real, 24.09] |
| max range at 10 % reflectivity | **200 m on the 32 "far-field enhanced" channels 34–65** (≈ +0.95° … −3.0°); 140 m on the rest of 26–89 (200 m needs 37 % reflectivity); 100 m and less elsewhere | a dark object (10 %: dark clothing, wet cardboard) is detectable to 200 m only within a ~4° band around the horizon — which is exactly where a 1–2 m obstacle on the track at 100–200 m sits. **300 m is outside the sensor's instrumented range** for ordinary targets; only retro-reflective ones return from further away |
| ranging accuracy | ±2 cm (1–200 m, average); ±5 cm below 1 m | the reported obstacle distance is limited by our clustering (nearest point), not by the sensor |
| minimum range | 0.3 m on 32 near-field channels, 2.7 m on the others; near-field returns (0.3–2.85 m) have 0.4° horizontal resolution | `sensor.min_range = 2.5 m` discards the near-field zone, which only contains the train's own nose |
| point rate | 3 456 000 pts/s single, 6 912 000 dual (max, 360°) | the 120° window gives ~1.15 M valid points/s single; with dual return and empty slots the bags carry ~190 k valid points per frame |
| dual return blocks | two adjacent blocks per firing with the same azimuth (§3.1.2.3). In **Last and First** mode a ray with a single return is stored in both blocks; in **Last and Strongest** (default) and First and Strongest, block 2 stores the *second strongest* return when block 1's return is also the strongest — the manual does not say what block 2 holds when there is only one return | measured on 24.09, 12 frames per recording: in all seven recordings 96–98 % of the points come in identical pairs, i.e. one echo stored in both blocks (~190 k points, 85–95 k distinct per 120° frame; 346 k and 175 k at 360°). The organizers (24.09, §4): the unit is on Last and Strongest now, the recordings are old and may have used another mode, and the control data use the same settings. The detector's point bars count occupied voxels, so the copies change no decision |
| reflectivity | 0–255, default linear mapping (value = reflectivity in %); > 100 for retro-reflectors. Two optional non-linear mappings (Appendix C) compress the scale, and the value is then no longer a percentage | the bags' values (median 6–7, retro-reflectors 255) match the linear mapping: `intensity` is reflectivity %; rails and signs saturate at 255. Usable to flag retro-reflective infrastructure (signs, markers) as non-obstacles; if the train's unit were switched to a non-linear mapping the `cluster.retro_intensity` threshold would have to be re-derived |
| clock | GNSS (GPS PPS + NMEA) or PTP (1588v2 / 802.1AS), ≤ 1 µs; without a source the sensor clock starts at a virtual UTC 2000-01-01 | the bags have no clock source (`timestamp` field is year-2000 epoch): use the bag receive time. The organizers (24.09): PTP / GNSS will exist on the train, but not within this hackathon, so there is no per-point deskew |
| built-in IMU | every point-cloud packet tail carries IMU data (§3.1.2.5): 3-axis acceleration (unit 0.244 mg), 3-axis angular velocity (unit 17.5 mdps), IMU temperature and an IMU timestamp (25 µs ticks from power-on) | the sensor itself reports angular rate and acceleration — enough for vibration / pitch compensation and, integrated with a speed reference, for the ego-motion step. The `PointCloud2` messages in the bags do not carry it; whether the train's driver publishes an IMU topic is not known, and the team works without speed or IMU input (§4) |
| factory defaults (web control, §4) | 600 rpm (10 Hz), return mode Last and Strongest, Standard horizontal resolution (0.2°), clock source GPS, linear reflectivity mapping, angle-based trigger, azimuth FOV "for all channels" 0–360° | the bags show 0.1° columns and a 120° window, so the recording unit was reconfigured (High Resolution, custom FOV). The organizers confirmed on 24.09 that the control data use the same settings, so the point budget in [`DATASET.md`](DATASET.md) "Point budget at range" holds |
| sweep and motion | one 120° window is swept in 33 ms; at 80 km/h (22 m/s) that is 0.7 m of travel within a frame and 2.2 m between frames | relevant for multi-frame accumulation (Sprint 2): the ego-motion estimate must be applied per frame, and per-point deskew is worth it above ~40 km/h |
| azimuth FOV setting | up to 5 azimuth windows can be configured in the sensor | the 120° window in the bags was set on the sensor; the control bag will presumably use the same window, but the code does not assume it |
| coordinate system | Z = rotation axis, Y = 0° azimuth, clockwise rotation (top view) | in the bags forward = −Y, left = +X, up = +Z: the sensor's 0° mark points backwards. `sensor.forward/left/up` in `configs/default.yaml` captures this and nothing else in the code depends on the sensor model |
| mechanical | 1.63 kg, Ø116 × 124 mm, IP6K7 / IP6K9K, −40 … 85 °C, 23–27 W | reference for the pitch (automotive-grade unit, ISO 26262 ASIL B) |

## 3. Implications for the algorithm and the evaluation

1. **Range targets.** Spec §8.2 rates 300 m as excellent; for a 10 %-reflectivity target the
   sensor is instrumented to 200 m and only on the 32 horizon channels. Our evaluation bins
   ([`EVALUATION.md`](EVALUATION.md) §2) keep 200–300 m for completeness, but the physical
   ceiling for a person in dark clothing is ~200 m, for a light-coloured box ~200 m on channels
   26–89, and 100 m elsewhere. The pitch should say so: "we detect to the sensor's instrumented
   limit".
2. **The corridor is in the best channels.** Beyond ~15 m the track bed and everything on it is
   observed by the 0.125° × 0.1° channels, and beyond ~30 m by the far-field enhanced ones. The
   expected-point prior in `resense/sensor.py` (used to score clusters) already uses the fine
   angular step in that band; the 100 m limit of the coarse channels only affects the tunnel
   roof and the near bed, which the detector does not need at range.
3. **Reflectivity is calibrated.** Because intensity is reflectivity %, a threshold above 100
   isolates retro-reflective material (signs, rail-head polish is also very bright). This is a
   cheap false-alarm filter for platform-edge signs, implemented as the retro-reflector rule
   ([`ALGORITHM.md`](ALGORITHM.md) §3.3 item 6) and off by default
   (`cluster.retro_intensity: 0`: it never fired on the six bags).
4. **Ego-motion.** With PTP on the train each point would have a µs timestamp, and the
   accumulation stage could deskew within a frame using the ego speed, not only align whole
   frames. The organizers said on 24.09 that this will not come within this hackathon.
5. **Generalisation to another unit or mount.** The detector never uses the ring index; only
   `resense inject` (synthetic obstacles) and the expected-point prior use the elevation table.
   A control bag from a different Pandar128 or mount needs no code change; a different model
   would only degrade the synthetic injector and the visibility score.
6. **Data-rate headroom.** The node processes ~190 k points per frame in 40–75 ms. If the
   control bag uses the full 360° or single-return mode the point count per frame changes by up
   to 3×; `sensor.max_range` and the azimuth crop happen after decoding, so a wider window costs
   decode time only.

## 4. Questions to the organizers (answered)

Answered on 24.09 ([`organizers/answers.md`](organizers/answers.md) §3):

* **Return mode, resolution and window.** The unit is on Last and Strongest now. The provided
  recordings, especially the one with people (`doubleT_obstacle`), are old and may have used
  another mode. **The control data use the same settings.** In every recording one echo is
  stored in both return blocks (§2 "dual return blocks"), and the detector counts occupied
  voxels, not points. The High Resolution 0.1° columns, the 120° window with `/lidar_points` +
  `hesai_lidar` and the full turn with `/sensing/lidar/hesai128/pointcloud` + `lidar_livox` stay
  as they are (both pairs may occur, one LiDAR: answers of 23.09).
* **PTP / GNSS time.** It will exist on the train, but not within this hackathon. The bag
  receive time and the differences of the unsynchronised year-2000 `header.stamp` remain the
  clocks.

**Mount.** On 22.09 (Q&A session) the mounting height and pitch were **not fixed** between
trains — "count on a variable position, set it in the launch parameters": the auto-calibration
and the mount launch arguments cover it ([`organizers/answers.md`](organizers/answers.md)). On
24.09 the organizers added that the test bags use the mounts of the provided recordings and that
the LiDAR is **1 075 mm above the rail head, on the train's centreline**; no numeric orientation
was given ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md)). The
calibration measures 1.12 m and −0.02 m lateral on `roundT_doubleT` (4.5 cm above the answer)
and 1.51 m with a +3.0° roll on the older `doubleT_obstacle` rig [real, 24.09]: the provided
recordings hold two rigs, so the calibration stays on as the safeguard
([`ALGORITHM.md`](ALGORITHM.md) §2b).

Closed on 22.09 (team decision, [`organizers/answers.md`](organizers/answers.md) §4): **no train
speed, odometry or IMU data will be available for this case** — the solution operates without
them. The packet-tail IMU noted in §2 is therefore documentation only; the node's speed inputs
stay optional and the multi-frame accumulation stays off unless a speed is given.
