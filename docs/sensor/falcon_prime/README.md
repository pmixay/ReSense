# Seyond (Innovusion) Falcon Prime: what the second lidar changes for ReSense

> **Source:** the organizers' Falcon Prime documents of 16.10 ([`../../organizers/extended_dataset_2026-10-16.md`](../../organizers/extended_dataset_2026-10-16.md)),
> read against the code on branch `ccr-027997e8-kqywat`. Its `resense/`, `ros2_ws/` and `configs/` are identical to `origin/main` at `44b462e`.
> **Owner:** P1 (node, launch, docs), P3 (detector), P4 (evaluation), as in FINALS_BRIEF card **N2**.
> **Status:** 17.10. Based on the documents and the code only. The recording (`falcon_test_second_dark/`, one 20.3 GB
> rosbag2 `.db3`, from the archive member listing) has not been decoded yet, so every statement about its actual fields,
> axes and ROI is **open** until that decode is done (§3.3).

Each statement has one of three tags:
* **[doc]**: from the Falcon documents.
* **[code]**: read from our source, with `file:line`.
* **[inferred]**: our own arithmetic or reasoning, not stated in either.

Document references:
* **DS p.N**: the datasheet `Innovusion_Falcon-Prime-1_Datasheet_EN_Public_20230215.pdf`, 4 pages with no printed numbers.
* **UM p.N**: the user manual `Seyond_Falcon_Prime_LiDAR_System_V1_0_2_English_public_20221214.pdf`. N is the **PDF** page;
  the page number printed on the page is N − 3.

## 1. Key specifications (Falcon Prime)

| property | value | ref |
|---|---|---|
| principle | ToF, 1550 nm fibre laser, Class 1 eye-safe. **Semi-solid-state, dual-axis mirror scanning**: an image-like raster, not a spinning multi-beam head | DS p.1–2; UM p.7, p.8 |
| FOV | 120° × 25° (DS: HFOV 100–120°, VFOV 25° outside the ROI). Vertical **−13° … +12°** and horizontal **−60° … +60°** relative to the housing. **Forward only** | DS p.1; UM p.8, p.9, p.11 (figure) |
| ROI (dense window) | 40° × 4.8° (DS: "≥"), "configurable". The centre can be moved in real time, horizontally within ±20° and vertically within ±6°. The ROI has about 6× the point density of the rest of the field | UM p.8, p.9, p.36 |
| angular resolution (H × V) | outside the ROI 0.18° × 0.24°; inside the ROI 0.09° × 0.08°. Optional 0.06° × 0.06° ROI mode, which changes other values: 200 m at 10 % reflectivity, 1600 lines/s, VFOV 22.5°, non-ROI 0.12° × 0.24°. UM p.7 also says "as high as 0.05° × 0.05°", which conflicts with the tables | DS p.1–2; UM p.7–9 |
| angular accuracy, beam divergence | ±0.1°; 0.1° | DS p.2 |
| scan lines ("channels") | 1500–2000 vertical scan lines per second (UM: 1500 lines/s, configurable). **[inferred]** That gives about 150 lines per frame at 10 FPS, roughly 60 inside the ROI (4.8° / 0.08°) and 84 outside it (20.2° / 0.24°). The example figure shows **curved** scan lines: a line's elevation is not constant across the azimuth | DS p.1; UM p.8 (figure), p.9 |
| frame rate | 10 FPS; configurable from 5 to 20 FPS | DS p.2; UM p.9 |
| points | 900,000 points/s. **[inferred]** About **90,000 points per frame** at 10 FPS, single return. Data rate 7.385 MB/s single return, 10.965 MB/s dual (×1.48) | DS p.2 |
| range | maximum 500 m. **250 m at 10 % Lambertian** reflectivity (10 Hz, 100 klx, POD > 90 %). Minimum 1.5 m (DS); "blind area ≤ 2 m" (UM) | DS p.1; UM p.9 |
| range accuracy / precision / resolution | ±5 cm on Lambertian targets, ±10 cm on retroreflectors. Precision 2 cm (1σ at 50 m). Resolution 0.5 cm | DS p.1; UM p.9 |
| false positives | < 1 / 10,000 at 100 klx sunlight | DS p.2 |
| returns | single (the **default**), "2 strongest", or "strongest & furthest" | DS p.2; UM p.37 |
| intensity | "Reflectance" can be set to *intensity* or *reflectivity*. **The numeric scale is not documented** | UM p.36–37; DS p.2 |
| per-point data on the wire | radius, azimuth, elevation, reflectivity, timestamp, frame ID, return mode, working mode, fault state, CRC. The user manual says "Pointcloud (X, Y, Z) intensity or reflectivity". Timestamps have 10 µs resolution per point | DS p.2; UM p.10 |
| timing | NTP (< 1 ms), IEEE 1588 PTP (< 1 µs), 802.1AS gPTP. The PTP set-up is described (`ptp_en 1`). GPS / PPS appear only in the abbreviation list | DS p.2; UM p.44–48, p.54 |
| interfaces | Gigabit Ethernet, UDP (broadcast, multicast 239.0.0.1 or unicast) and TCP. Default IP 172.168.1.10, TCP port 8010, web UI (ILA) on port 8675. Ready about 11–18 s after power-on | DS p.2; UM p.19–21, p.34, p.40–43 |
| ROS driver | DS lists ROS / ROS2 / Apollo drivers. The UM shows only ROS 1 (melodic): package `innovusion_pointcloud`, launch file `innovusion_points.launch`, topic **`/iv_points`**, fixed frame **`innovusion`**. **The PointCloud2 field names, types and axis convention are not documented** | DS p.3; UM p.20–24, p.27–28 |
| file formats | `inno_pc` (spherical), `inno_pc_xyz` (Cartesian), `inno_raw`, pcd, bag, csv | UM p.35–36 |
| coordinate system (sensor) | **x perpendicular to the ground, pointing up; y parallel to the ground, pointing right; z parallel to the ground, pointing forward.** Right-handed (x × y = z) | UM p.8 (text and figure) |
| mounting | flat surface, preferably aluminium; 4 × M4 × 18 screws; 2.3 kg. Dimensions differ between the documents: 83.8 × 268 × 172 mm (DS) and 228 × 84 × 148 mm (UM) | DS p.2, p.4; UM p.11–14 |
| environment | DS: −40 to 70 °C, IP67. UM: −40 to +75 °C, IP67K body, IP69K window. **No rain, fog or dust figures.** Troubleshooting lists a contaminated window and strongly reflective objects as causes of noise points (blooming), and window contamination and "visibility of the weather" as causes of short range | DS p.2; UM p.9, p.17–18, p.49–50 |

## 2. Pandar128 (our recordings) against Falcon Prime

Pandar values come from [`../../SENSOR.md`](../../SENSOR.md) (manual and measured) and the Pandar128 manual.

| property | Hesai Pandar128 E3X, as recorded | Falcon Prime | consequence **[inferred]** |
|---|---|---|---|
| wavelength / mechanism | 905 nm, spinning head with 128 fixed channels | 1550 nm, mirror raster | no "ring" in the Hesai sense; scan lines are curved |
| horizontal FOV | 360° sensor; the recordings are a 120° window with returns only within ±50°, or a full turn | **120° (±60°), forward only** | ±60° is wider than our ±50° assumptions; nothing behind the sensor |
| vertical FOV | +14.4° … −25.1° | **+12° … −13°** | rail head first visible at about 4.7 m instead of 2.3 m (1.075 m mount); the bed from about 5.5 m |
| vertical resolution near the horizon | 0.125° (rings 26–90, +2° … −6.2°); 0.5° elsewhere | ROI 0.08°; **0.24° outside the ROI** | bed scan-line spacing at 50 m: Pandar 5.1 m, Falcon ROI 3.2 m, non-ROI **9.7 m** |
| horizontal resolution | 0.1° columns (High Resolution mode) | ROI 0.09°; **0.18° outside** | — |
| lines / channels | 128 rings, constant elevation | about 150 curved lines per frame (from 1500 lines/s) | ring tables and ring order do not apply |
| frame rate | 10 Hz (a 120° window is swept in 33 ms) | 10 FPS (5–20). A frame is likely scanned over the whole 100 ms | about 3× more motion inside a frame (2.2 m at 80 km/h) |
| points per frame | ~190 k valid per 120° frame, of which 96–98 % are identical pairs (85–95 k distinct) | **~90 k**, single return by default | about the same number of *distinct* rays, but half the raw returns |
| returns | dual (Last and Strongest); a single echo fills both slots | single by default; dual optional | every "each echo twice" threshold becomes twice as strict |
| range at 10 % reflectivity | 200 m on 32 channels; no return beyond about 210 m in any recording | **250 m; maximum 500 m** | our 250 m crop discards real Falcon returns |
| minimum range | 0.3 m / 2.7 m | 1.5 m (DS) / ≤ 2 m (UM) | `min_range` 2.5 m is fine |
| precision | ±2 cm | 2 cm (1σ at 50 m), accuracy ±5 cm | same class |
| intensity | 0–255, reflectivity in %, > 100 for retroreflectors | intensity or reflectivity, scale not stated | `retro_intensity` is off (0), so no effect today |
| timing | PTP / GNSS (not used in the bags) | NTP / PTP / gPTP, 10 µs per point | per-point `timestamp` is ignored by us either way |
| sensor axes | Z = spin axis; recorded frame: forward = −y, left = +x, up = +z | **x up, y right, z forward** (sensor). Driver output not documented | up is **x**, not z |
| ROS identity | topics `/lidar_points`, `/sensing/lidar/hesai128/pointcloud`; frame `hesai_lidar` / `lidar_livox` | `/iv_points`; frame `innovusion` (ROS 1 manual) | auto-discovery finds the topic; nothing else uses the name |

## 3. Coordinate systems and the launch values

### 3.1 What the documents give **[doc]**

Sensor frame (UM p.8): **x = up, y = right, z = forward.** Mapped onto our vehicle frame (X forward, Y left, Z up), this is:

```
sensor_forward:=+z  sensor_left:=-y  sensor_up:=+x
```

`axis_matrix` (`resense/frame.py:14-31`) builds `[[0,0,1],[0,-1,0],[1,0,0]]` from these values. Its determinant is +1, so the
handedness check at `frame.py:25` passes.

### 3.2 What the ROS driver may publish **[inferred]**

The manual does not say whether `innovusion_pointcloud` (or the ROS 2 driver) republishes points in the native frame or
converts them to the ROS convention (x forward, y left, z up). The organizers' warning about "different axis directions"
fits the native frame, but that is not proof. The two cases need different values:

| recording publishes | jury launch values | with the default `auto_calibrate` (`keep_up_axis: true`) |
|---|---|---|
| native (x up, y right, z forward) | `sensor_forward:=+z sensor_left:=-y sensor_up:=+x` | **cannot be found**: the configured up axis is sensor `+z`, and the 8 candidates keep it vertical (`calibration.py:68-81`, `configs/default.yaml:336`). This mount is "on its side" for the search. After `max_frames` 400 (40 s) the status is `fallback` and the configured mapping is kept (`calibration.py:453-458`), so the detector is blind |
| ROS convention (x fwd, y left, z up) | `sensor_forward:=+x sensor_left:=+y sensor_up:=+z` (the example already in `launch/detector.launch.py:12`) | found: `forward=+x left=+y up=+z` is one of the 8. It is adopted after `orientation_votes` = 2 frames on which the configured mapping fails and this candidate passes (`calibration.py:304-319`) |

### 3.3 How to tell which case the recording is in (P4, minutes, no code change)

A forward-only ±60° sensor gives every return a forward component of at least r · cos 60° > 0. The **forward axis is the
one whose sign is the same for (almost) every point**. The **up axis** is the one along which the bed sits about 1.1–1.3 m
below the sensor between 10 and 30 m ahead. `resense info <bag>` together with a NumPy check of one frame settles it. Record
the result here and in the jury README. If the axes are tilted (a pitched mount), the auto-calibration corrects up to
`max_tilt_deg` = 15° (`configs/default.yaml:341`).

## 4. Code-impact audit

**Effect:**
* **breaks**: wrong output or no detection.
* **degrades**: silently worse.
* **config**: needs a parameter.
* **fine**: no impact.

**Severity:** H / M / L.

| # | assumption (Pandar128) | where | Falcon provides | effect | proposed test / change | sev |
|---|---|---|---|---|---|---|
| A1 | the default axis mapping is `-y / +x / +z` | `configs/default.yaml:3-5`, `resense/config.py:18-20` | native x up, y right, z forward (§3) | **breaks** without launch parameters (blind; see A2) | jury command with explicit axes (§3); orientation battery including the native permutation | **H** |
| A2 | the mount search keeps the configured up axis vertical (8 candidates); sideways candidates are off because a side wall can pass for a bed | `calibration.py:15-28, 68-81, 213`; `configs/default.yaml:336-337` | up = sensor **x** | **breaks** auto-detection of the native frame. `keep_up_axis` is not a node parameter (`launch/detector.launch.py:28-81`), so the jury can only change it through a config file | node parameter `calib_keep_up_axis` (P1, S). Better: a forward-only test (the axis with one sign on > 98 % of returns is forward) that narrows the 24 candidates to 4 before the rail test, with no side-wall risk (P3, S–M) | **H** |
| A3 | before adoption the detector runs on the configured mapping | `detector.py:356-378`; `health.py:206-209` | — | with a wrong mapping, the first frames (or, in case A2, every frame) have no corridor. The decision should come from health (`visibility` < 60 m, `rail_lock`, then calibration `fallback`): `CAUTION`, not `GO`. **This has not been measured** | battery N2 task 1: record the decision on every frame before adoption and after `fallback`; it must never be a silent `GO` | **H** |
| A4 | one axis mapping per node; the node resets on a topic or `frame_id` change but keeps its parameters | `detector_node.py:276-292` | `frame_id` `innovusion` versus `hesai_lidar` | **config**: a jury that switches between Pandar and Falcon bags in one running node (N4) keeps the wrong axes for one of them | per-`frame_id` axis profiles (for example `hesai_lidar: -y,+x,+z`, `innovusion: <measured>`), or document a restart (P1, S–M) | M |
| F1 | field `ring` (uint16) | `pointcloud.py:82, 95`; `fastcloud.py:126-130, 169` | the driver's per-point fields are undocumented. Seyond drivers usually carry `scan_id` / `scan_idx` rather than `ring` **[inferred]** | node: **fine**. With no `ring` the node passes `ring=None` (`detector_node.py:917`), and the ring rules are off (`weak_min_rings: 0`, `far_min_ring_count: 0`, `rails_far_rings: false`; `default.yaml:74, 134, 248`) | none for the node. **Do not** map `scan_id` to `ring`: it is not a constant-elevation channel (F3) | L |
| F2 | offline path: a missing `ring` becomes 0 for every point | `io.py:34` → `pointcloud.py:95`; `frame.py:66` | no `ring` | **degrades parity**: offline `ring` is all zeros (a known single channel) while the node has `None`. `Cluster.ring_count` is 1 instead of 0. Harmless with the defaults; it would diverge if the experimental ring flags were turned on | make `structured_to_compact` / `frame_from_compact` carry "unknown" (P3, S); a field-variant test that compares offline and node output on a ring-less bag | L |
| F3 | ring = a constant-elevation channel, numbered from the top down, ≥ 0.086° apart | `clustering.py:458-492` (`_ids_in_elevation_order`, `_ring_between`), `:550, 575-579` (`top_is_free`: the top's ring is within 0.06°, the next ring is more than 0.04° above it); `farrails.py:29-32, 71-96`; `track.py:599-600` (half a 0.125° ring) | curved raster lines. ROI lines 0.08° apart (0.06° in the hi-res mode), non-ROI 0.24° | **degrades** the column free-top test (`top_is_free`): with `ring=None` it falls back to geometry, which assumes Pandar line spacing. A tall narrow object (a person) can then be demoted as a `column` more or less often than on the Pandar. `farrails` is off. The `floor_verify` offset uses 0.125° where the Falcon has 0.08 or 0.24° (a cm-level bias) | replay test: column / spare counts and person `STOP` frames on a Pandar frame thinned to the Falcon grid (W3). Make the ring spacing a sensor parameter (P3, S) | M |
| F4 | each echo appears twice (dual-return duplicates, 96–98 % of points) | `config.py:265` (`column_free_min_returns: 2` = "one ray"); `clustering.py:477` (6 returns = 3 rays); `default.yaml:390` (`persist_min_points: 2`); the track model and health count raw points (`SENSOR.md` §2) | single return by default | **degrades**: return-count thresholds are 2× stricter in rays. The judge's de-duplication run of 13.10 is the proxy: `doubleT_obstacle` 193 → 189 `STOP` frames, `squareT_platform` `CAUTION` 51 % → 11 % (`evidence/judgement_2026-10-13` §6) | full regression gate on de-duplicated Pandar data. If it moves decisions, scale these thresholds by a `returns_per_ray` sensor parameter (P3, M) | M |
| F5 | float32 x / y / z at offsets 0 / 4 / 8 (fast path); datatypes 1–8 | `fastcloud.py:133-170`; `pointcloud.py:12` | unknown layout. PCL-style points (x, y, z, padding, …) also match the fast path **[inferred]** | **fine**: any other layout goes through the reference decode; float64 x / y / z work | field-variant test (N2 task 2) with a 32-byte PCL layout, float64 x / y / z and an organized cloud with `row_step` padding | L |
| F6 | intensity is reflectivity in % (0–255) | `config.py:328-329`; `default.yaml:208`; `pointcloud.py:144` (cache clip 0–255) | intensity or reflectivity, unknown scale | **fine**: no default rule reads intensity (`retro_intensity: 0`). The offline 8-bit cache rounds a 0–1 scale to 0/1 (only for display and statistics) | note in the jury README; never enable `retro_intensity` for the Falcon without calibrating it | L |
| F7 | offline caches: int16 cm (±327 m), 8-bit ring with `DUP_FLAG` = 0x80 | `pointcloud.py:22-29, 125-146` | 500 m range; ids above 127 if `scan_id` were stored as `ring` | **degrades the offline tooling only**: points beyond 327 m are dropped, and ids ≥ 128 collide with the duplicate flag (points get duplicated) | do not cache Falcon data with `COMPACT16` and a `ring`; use the float cache (P4) | L |
| R1 | range crop 2.5–250 m | `default.yaml:6-7`; `fastcloud.py:162-164`; `frame.py:63` | 250 m at 10 %, up to 500 m | **degrades**: returns beyond 250 m (reflective objects, or the organizers' "300 m ideal") are discarded. Raising `max_range` alone is not enough: `floor_verify_max_range` 250 (`default.yaml:95`), `marker_x_max` 250 and the axis model's trusted ranges stop there too | measure first: the Falcon recording's range histogram (P4). Only if useful, a sealed change of `sensor.max_range` plus the far-axis ranges (P3, M) | M |
| V1 | visibility prior on the Pandar grid: 0.1° azimuth × 0.125° / 0.5° elevation | `sensor.py:162-203`; `clustering.py:312-316, 336, 758, 1033`; confidence gain `tracking.py:322, 372, 386` | ROI 0.09 × 0.08; non-ROI 0.18 × 0.24 | **degrades**: for a 1 × 1 m target at 100 m the model expects 26 returns; the Falcon gives about 46 in the ROI and about 8 outside it. Outside the ROI the visibility score drops about 3.5× (clipped at 1 after `/0.15`), so confidence builds more slowly and the first `STOP` comes later; inside the ROI it is inflated | a sensor-grid parameter set (azimuth step, an elevation-step function or ROI box) for `expected_points` (P3, S); A/B on the thinned Pandar data | M |
| V2 | azimuth buckets cover ±50° | `clustering.py:379` (`FrameRays.SCALE / MID`); `sensor.py:163` | ±60° | **fine**: 50–60° falls in the end buckets, and the exact test follows (`clustering.py:401-404`); only slower there | none | L |
| V3 | a split part must span at least 0.1° of azimuth | `clustering.py:893` | 0.18° columns outside the ROI | **fine**: a single scan column is still rejected; two columns pass | none | L |
| G1 | bed and rails sampled densely enough from 3 m out (`floor_fit_range` 3–120 m, `floor_min_points` 15 per 2 m bin) | `default.yaml:17-22`; `calibration.py:132-137` (near window 2–45 m, ≥ 500 points) | first bed return at about 5–6 m; bed lines 2.4 m apart at 25 m and 9.7 m at 50 m outside the ROI | **degrades**: fewer populated bins beyond 25–30 m outside the ROI, so the floor and rail fit is shorter and less stable (lower `rail_lock`, a shorter trusted range). Inside the ROI it is better than the Pandar. Depends on where the ROI is (unknown) | when the bag arrives: per-line elevation histogram → ROI position; `rail_lock`, `axis_valid` and `floor_range` over the recording (P4) | M |
| G2 | the calibration's "far returns ahead ≥ 1.5 × behind" sanity check | `calibration.py:127-137` | nothing behind | **fine**: with nothing behind, `ratio = fwd / 1` | none | L |
| G3 | ego-speed texture, walls and health sectors use the forward half only | `egomotion.py:73, 82`; `health.py:171-181` (±30° sectors) | forward only | **fine**. The frame is scanned over about 100 ms, so motion inside a frame is about 3× the Pandar's 33 ms window: up to 2.2 m at 80 km/h between the first and last line. Per-point timestamps exist but are ignored | measure the frame span from the point `timestamp` field if present (P4) | L |
| H1 | health: `min_points` 20,000, `min_visibility` 60 m, `min_lock_rate` 0.3 | `default.yaml:354-363`; `health.py:163-185` | about 90 k points per frame at 10 FPS, about 45 k at 20 FPS; visibility up to 250 m | `min_points` **fine**. Visibility **fine** in a straight tunnel. `rail_lock` depends on G1. If the recording is not a metro tunnel with a 1.52 m gauge (unknown), lock stays low and the node reports `CAUTION` throughout | read the recording's health columns before judging it (P4) | M |
| H2 | the near-return fraction (window dirt) counts returns under 2.5 m | `default.yaml:356-358` | blind area ≤ 2 m, so few returns under 2.5 m | **fine** (a dirty window may show less) | none | L |
| T1 | frame period 10 Hz, latency budget 100 ms | `default.yaml:345, 363` | 5–20 FPS | **fine**: `time_cadence` handles 5 Hz. At 20 Hz the catch-up skips frames by design | none | L |
| J1 | the judge's ray-caster: needs `ring`, builds per-ring median elevations, 0.1° azimuth columns, writes each hit twice | `docs/evidence/judgement_2026-10-13/scripts/range_test.py:13-16, 34, 68-73, 159-192` | no ring, curved lines, single return | **breaks**: synthetic range tests cannot be run on a Falcon frame as written (`ring.max()` on `None`; elevation tables are meaningless) | a sensor-agnostic variant (W5) | M |
| J2 | the synthetic injector uses the Pandar ray grid | `synthetic.py:24`; `sensor.py:206-216` | — | **degrades evaluation**: objects injected into Falcon frames would have Pandar sampling | same as W5 | M |
| D1 | docs say "another sensor model would only degrade the injector and the visibility prior" | `docs/SENSOR.md` §3.5; `gitbook/reference/node-parameters.md:41`; `README.md:311` | — | **incomplete**: A2 (sideways up axis), F3, F4, V1 and R1 are not mentioned. The jury README has no command for a lidar whose axes differ, does not mention `/iv_points`, and does not mention `keep_up_axis` | W2 | M |

Ingest note **[inferred]**: the archive holds a rosbag2 `.db3` (`falcon_test_second_dark/`), which both the node (`ros2 bag play`) and
`resense run` (rosbags `rosbag2.Reader`, `io.py:20-24`) read. A ROS 1 bag or `inno_pc` would not have been readable.

## 5. Risks for the jury evaluation (ordered)

1. **The jury runs the default command, and the detector is blind for the whole Falcon recording.** If the recording is in
   the native frame, auto-calibration cannot find up = +x (A2) and falls back after 40 s. The output is probably a
   constant `CAUTION` (A3, unmeasured), with no `STOP` on real obstacles. If it is in the ROS frame, about 2 frames are
   lost before adoption.
2. **Wrong axes are passed by hand, or the bags are switched in one node** (A4). The Pandar and Falcon recordings need
   different mappings.
3. **Single return changes decisions** (F4). The de-duplicated Pandar runs moved `STOP` and `CAUTION` counts. Thresholds
   counted in "returns" assume two per ray.
4. **Sparse bed and rails outside the ROI, and a different visibility prior** (G1, V1). Expect a shorter trusted range,
   a later first `STOP` and possibly more `column` demotions (F3). Better than the Pandar only if the ROI sits on the far
   track.
5. **Our evaluation tools do not transfer** (J1, J2). Range claims for the Falcon cannot be backed by the judge's
   ray-cast method without a sensor-agnostic version, and the 250 m crop (R1) caps what we can show against the experts'
   300 m ideal.

## 6. Recommended work (FINALS_BRIEF card N2), in priority order

| # | item | owner | size | needs |
|---|---|---|---|---|
| W1 | Decode the first Falcon frames: field list, dtypes, `point_step`, `height`, topic, `frame_id`, the forward and up axes (§3.3), points per frame, range histogram, line-elevation histogram (ROI position), `timestamp` span. Fill §3.2 with the actual values | P4 (+ the decoding agent) | S | the bag |
| W2 | Jury README and gitbook: the Falcon command with explicit `sensor_forward / left / up` (W1), `input_topic:=/iv_points`, `auto_calibrate` and `keep_up_axis` limits ("a lidar whose up axis is not z must be given its axes"), and "restart the node when switching between lidars" | P1 | S | W1 |
| W3 | Orientation battery (N2 task 1), **including the native Falcon permutation (up = x)**, which the 8-candidate search cannot find. Record the decision on every frame before adoption and after `fallback` (it must not be a silent `GO`) | P4 | M | — |
| W4 | Falcon proxy from our data: crop to ±60°, de-duplicate (single return), thin rows and columns to the Falcon grid (0.18 × 0.24° outside a 40 × 4.8° ROI, 0.09 × 0.08° inside), drop returns under 1.5 m, then run the full gate and the person / organizer objects. Quantifies F3, F4, V1 and G1 before any detector change | P4 | M | — |
| W5 | Sensor-agnostic range test: replace the ring and column grid with "every real return is a ray; a box hit nearer than the return replaces it" (single write); the same for the injector | P4 | M | — |
| W6 | Node parameters `calib_keep_up_axis` and per-`frame_id` axis profiles (A2, A4) | P1 | S–M | — |
| W7 | Forward-only orientation prior in the calibrator (A2): the sign-consistent axis is forward, then only 4 candidates are tested. This is a detector change, so it needs the seal and the gate | P3 | S–M | W3 |
| W8 | Sensor-model parameters: azimuth / elevation steps or an ROI box for `expected_points`, ring spacing for `top_is_free`, `returns_per_ray` for the return-count thresholds. Pandar defaults stay byte-identical. Tune for the Falcon only if W4 shows a loss | P3 | M | W4 |
| W9 | Range beyond 250 m (R1): only if W1 shows useful returns there and W4 / W5 show a gain; sealed | P3 | M | W1, W5 |
| W10 | Offline parity: unknown `ring` as `None` offline (F2); no `COMPACT16` caching of Falcon data (F7) | P3 / P4 | S | — |

W1 → W2 make the jury run correct. W3 → W5 measure without changing the detector (as N2 asks). W6 → W10 follow only from
what those measurements show.
