# Sensor: Hesai Pandar128 (E3X)

Source: Hesai downloads page, https://www.hesaitech.com/downloads/#pandar128 — user manual
`Pandar128E3X_v4p5` (rev. 2025-11), angle correction file `Pandar128_Angle_Correction_File`,
firetime correction file, STEP model. Numbers below are from the manual; the "measured" column
is what [`DATASET.md`](DATASET.md) found in the organizer bags.

## 1. Identification

The bags come from a **Pandar128**, not an AT-series unit as first assumed. Evidence:

| property | manual (Pandar128) | measured in the bags |
|---|---|---|
| channels | 128 | 128 rings |
| vertical FOV | 40° (−25° … +15°) | +14.40° … −25.12° |
| fine vertical band | 0.125° on channels 26–90 (+2.01° … −6.10°) | 0.125° step on rings 26–90 (+2.0° … −6.2°) |
| coarse bands | 0.5° on channels 2–26 and 90–127, 1° at the ends | 0.5° outside the fine band |
| per-channel elevations (angle correction file) | channel 1 = +14.436°, channel 128 = −25.016° | ring 0 = +14.402°, ring 127 = −25.120°; all 128 agree within 0.12° |
| horizontal resolution | 0.1° at 10 Hz (0.2° in Standard mode) | 0.1° |
| horizontal FOV | 360°, configurable azimuth window(s) | 1200 columns = 120° window, returns within ±50° |
| frame rate | 10 Hz / 20 Hz | ~10 Hz |
| return modes | single (last / strongest / first), dual (last+strongest, last+first, first+strongest) | dual return, 2 × 153 600 slots |
| range | 0.3 … 200 m @ 10 % reflectivity | last returns at ~206 m |

`resense/sensor.py` keeps the measured ring elevations; the design values from the angle
correction file differ by ≤ 0.12° (each real unit carries its own calibration), so the measured
table stays.

## 2. Specifications that matter for the project

| item | value | consequence |
|---|---|---|
| instrumented range per channel | **200 m only on channels 26–89** (elevation +2.0° … −6.0°); 100 m on channels 1–25 and 90–128 | the corridor beyond ~15 m is seen exclusively by the 200 m channels: the track bed at 100 m is at −0.9° for a 1.5 m sensor height, at 200 m at −0.4° |
| max range at 10 % reflectivity | **200 m on the 32 "far-field enhanced" channels 34–65** (≈ +0.95° … −3.0°); 140 m on the rest of 26–89 (200 m needs 37 % reflectivity); 100 m and less elsewhere | a dark object (10 %: dark clothing, wet cardboard) is detectable to 200 m only within a ~4° band around the horizon — which is exactly where a 1–2 m obstacle on the track at 100–200 m sits. **300 m is outside the sensor's instrumented range** for ordinary targets; only retro-reflective ones return from further away |
| ranging accuracy | ±2 cm (1–200 m, average); ±5 cm below 1 m | the reported obstacle distance is limited by our clustering (nearest point), not by the sensor |
| minimum range | 0.3 m on 32 near-field channels, 2.7 m on the others; near-field returns (0.3–2.85 m) have 0.4° horizontal resolution | `sensor.min_range = 2.5 m` discards the near-field zone, which only contains the train's own nose |
| point rate | 3 456 000 pts/s single, 6 912 000 dual (max, 360°) | the 120° window gives ~1.15 M valid points/s single; with dual return and empty slots the bags carry ~190 k valid points per frame |
| dual return blocks | two adjacent blocks per firing; **when a ray has a single return both blocks carry the same point** | duplicates in the cloud: ~190 k points but ~150 k distinct rays; the range-normalised voxel grid merges them before clustering |
| reflectivity | 0–255, default linear mapping (value = reflectivity in %); > 100 for retro-reflectors | `intensity` in the bags is reflectivity %; rails and signs saturate at 255. Usable to flag retro-reflective infrastructure (signs, markers) as non-obstacles |
| clock | GNSS or PTP (1588v2 / 802.1AS), ≤ 1 µs; unsynchronised sensor time starts in year 2000 | the bags have no clock source (`timestamp` field is year-2000 epoch): use the bag receive time. On the train PTP will be available: per-point timestamps allow motion deskew |
| sweep and motion | one 120° window is swept in 33 ms; at 80 km/h (22 m/s) that is 0.7 m of travel within a frame and 2.2 m between frames | relevant for multi-frame accumulation (Sprint 2): the ego-motion estimate must be applied per frame, and per-point deskew is worth it above ~40 km/h |
| azimuth FOV setting | up to 5 azimuth windows can be configured in the sensor | the 120° window in the bags was set on the sensor; the control bag will presumably use the same window, but the code does not assume it |
| coordinate system | Z = rotation axis, Y = 0° azimuth, clockwise rotation (top view) | in the bags forward = −Y, left = +X, up = +Z: the sensor's 0° mark points backwards. `sensor.forward/left/up` in `configs/default.yaml` captures this and nothing else in the code depends on the sensor model |
| mechanical | 1.63 kg, Ø116 × 124 mm, IP6K7 / IP6K9K, −40 … 85 °C, 23–27 W | reference for the pitch (automotive-grade unit, ISO 26262 ASIL B) |

## 3. Implications for the algorithm and the evaluation

1. **Range targets.** Spec §8.2 rates 300 m as excellent; for a 10 %-reflectivity target the
   sensor is instrumented to 200 m and only on the 32 horizon channels. Our evaluation bins
   (`EVALUATION.md`) keep 200–300 m for completeness, but the physical ceiling for a person in
   dark clothing is ~200 m, for a light-coloured box ~200 m on channels 26–89, and 100 m
   elsewhere. The pitch should say so: "we detect to the sensor's instrumented limit".
2. **The corridor is in the best channels.** Beyond ~15 m the track bed and everything on it is
   observed by the 0.125° × 0.1° channels, and beyond ~30 m by the far-field enhanced ones. The
   expected-point prior in `resense/sensor.py` (used to score clusters) already uses the fine
   angular step in that band; the 100 m limit of the coarse channels only affects the tunnel
   roof and the near bed, which the detector does not need at range.
3. **Reflectivity is calibrated.** Because intensity is reflectivity %, a threshold above 100
   isolates retro-reflective material (signs, rail-head polish is also very bright). This is a
   cheap false-alarm filter for platform-edge signs (P3 backlog item 5).
4. **Ego-motion.** With PTP on the train each point has a µs timestamp; the accumulation stage
   should deskew within a frame using the ego speed, not only align whole frames.
5. **Generalisation to another unit or mount.** The detector never uses the ring index; only
   `resense inject` (synthetic obstacles) and the expected-point prior use the elevation table.
   A control bag from a different Pandar128 or mount needs no code change; a different model
   would only degrade the synthetic injector and the visibility score.
6. **Data-rate headroom.** The node processes ~190 k points per frame in 40–75 ms. If the
   control bag uses the full 360° or single-return mode the point count per frame changes by up
   to 3×; `sensor.max_range` and the azimuth crop happen after decoding, so a wider window costs
   decode time only.

## 4. Open questions for the organizers

* Return mode of the recordings (last + strongest is the manual's default) and whether the
  control bag uses the same 120° azimuth window and High Resolution mode.
* Mounting height and pitch on the train (the bags show two different mounts; the detector
  self-calibrates, but the number helps the synthetic injector).
* Whether PTP time will be available on the train, and the odometry / speed source.
