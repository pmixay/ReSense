# Falcon long range: pre-registered protocol (19.10, committed before the injected measurements)

Branch `det/falcon-long-range`, base `aec88d2`. Owner: P3 lane (with P4-style measurement), ordered by P1.
This file is written after the instrument was built and validated (cache, replay runner, injector,
person calibration, count control, raster leave-out) and **before** any injected baseline or candidate run.
Changes to this protocol after that point are appended in a dated "amendments" section, never edited in place.

## 1. Instruments (validated before this protocol)

* **Cache + runner** (`scripts/cache_falcon_full.py`, `scripts/run_cache.py`): node decode to 600 m;
  89/89 sampled frames identical to the node decode at 250 m; full replay rows identical (decision,
  detections, warnings, nearest, clear, monitored) to the archived N2 replays on all 4,443 frames
  for both the default launch and `sensor_profile:=falcon_ros`.
* **Track reference** (`scripts/track_reference.py`, `track_reference.json`): raw-frame rail-centre line
  fitted 30–90 m, extended straight; height = rail-head line with the slope of the walking person's top
  (20–250 m). The real person's path lies within 0.17 m (band means) of it from 0 to 250 m and its top
  at 1.44–1.55 m above it in every band. Beyond 250 m the straight extension is an **assumption**.
* **Injector** (`scripts/inject.py`): the frame's own raster (returned rays + linear reconstruction
  inside each scan line; leave-out p99 error 0.024° az / 0.038° el in the far-track core),
  Gaussian beam (datasheet 0.1° divergence), POD model anchored to the datasheet (10 %, 250 m → 0.9).
* **Person calibration** (`scripts/calibrate_person.py`, `person_model.json`): fill 0.9, effective
  reflectivity 0.05 below 0.8 m and 0.3 above; fit on even anchors, held out on odd anchors and the
  separate early episode. **Count control** (`count_control.json`): injected vs real points per frame
  agree within ~15 % in every band 30–250 m (240–250 m: 6.2 vs 6.9).

## 2. Remaining validation (run before the matrix, reported with it)

* **Walk control** (`scripts/walk_control.py`, `walk_compare.py`): the real person's walk from frame
  2290 (≈200 m) to 3200 (≈97 m) re-enacted on empty frames 300–1210 (3 seeds) with the baseline
  detector (`falcon_ros`). Pass: injected first STOP within ±15 m of the real first STOP, and per-band
  STOP fractions within ±0.25 of the real ones in the 150–100 m bands. A fail is reported and the
  injected results are then labelled "uncalibrated detector behaviour".

## 3. Injection matrix (identical for baseline and every candidate)

Profile `falcon_ros` (the explicit Falcon launch). A fresh detector from frame 0 of the recording;
targets on the empty part of the recording (the train stands, the scene is static, no person before
frame 1200). Lateral 0 = track reference centre; bottom −0.2 m (bed level). Seeds 0, 1, 2.

| target | size L×W×H m | reflectivity |
|---|---|---|
| `person` | 0.5 × 0.5 × 1.75 | calibrated (`person_model.json`) |
| `person_dark` | 0.5 × 0.5 × 1.75 | fill 0.9, 0.05 lower / 0.10 upper |
| `cube` | 1 × 1 × 1 | 0.10, 0.20, 0.50 |
| `box2` | 2 × 2 × 2 | 0.10, 0.20, 0.50 |
| `outside` (negative control) | 1 × 1 × 1 at lateral +2.5 m | 0.50 |

* **Static**: at 150, 200, 250, 300, 350 m, frames 300–449 (15 s). Metrics: seconds to the first
  associated STOP, STOP fraction of the 150 frames, fraction after the first STOP (held), first
  associated output (STOP or advisory).
* **Approach**: from 400 m towards the sensor at 10 m/s from frame 300 to 100 m (frame 600).
  Metrics: first associated output distance, first STOP distance, held fraction after the first
  STOP, STOP fraction per 50 m band.
* Association (`scripts/assoc.py`): output centre mapped to the raw frame within 2.5 m along and 1.0 m
  laterally of the target. Report the median and range over the seeds.

## 4. Primary endpoints and targets (stated before measuring)

* **E1** person approach: first STOP distance and held fraction (candidate vs baseline).
* **E2** static person and cube 20 % at 250 m and 300 m: STOP within 3 s and held ≥ 0.9.
* **E3** largest range at which each target × reflectivity is STOPped within 3 s and held ≥ 0.9.
* Target set by P1: stable detection "as close to 300 m as is honest". Pre-registered aim: E2 at
  250 m for the person and the 20 % cube; 300 m is reported as achieved or not, with the blocking
  cause (sensor physics: returns per frame below the clustering minimum; our code; missing data:
  no track reference beyond 250 m).
* **Negative control** `outside`: no STOP at any range (baseline and candidate).

## 5. Acceptance rules for a Falcon candidate

1. **False alarms do not rise** (real recording, `falcon_ros`): (a) frames 0–1700: STOP episodes and
   STOP frames not associated with the person (main or early episode) ≤ baseline; CAUTION share ≤
   baseline; (b) whole recording: STOP episodes ≤ baseline (8), CAUTION share ≤ baseline
   (3,043/4,443), STOP frames not associated with the person ≤ baseline.
2. **Person STOP rows kept**: every baseline frame with a person-associated STOP is STOP with a
   person-associated detection in the candidate.
3. **Pandar unchanged**: Falcon behaviour only through the Falcon profile / an explicit config
   block that is off by default; full regression gate exit 0 without `--allow` with identical rows;
   X3 PASS; unit tests pass.
4. Independent review by a fresh subagent (code + criteria).
5. Changes are measured one at a time (cumulative order C1 → C5), each against the previous step.

## 6. Planned changes (Falcon profile only)

* **C1** range crop ≥ 350 m (`sensor.max_range`, `gauge.range_max`, `track.floor_verify_max_range`).
* **C2** Falcon visibility prior (ROI / non-ROI grid) in place of the Pandar one.
* **C3** long-range axis on straight track: extrapolate the axis supported at 50–150 m with a
  lateral uncertainty growing with range; not trusted on curves.
* **C4** far confirmation accumulating evidence over frames for compact targets on the line of sight.
* **C5** honest Falcon clear-range reporting (node policy).

Not used: the held-out G3 set. No parameter is tuned on the injected matrix's seeds 0–2 without
re-running on seeds 10–12 for the reported numbers (stated in the report if done).
