# Experiments log

Numbers are for the **v0 prototype (2026-09-15, day 1)**, pure Python, 4-core sandbox, every
5th/10th frame of the organizer bags cached as `*.npy` (`scripts/cache_frames.py`). Raw results:
[`experiments_v0_real_bags.json`](experiments_v0_real_bags.json),
[`experiments_v0_synthetic.json`](experiments_v0_synthetic.json). Renders: [`img/`](img/).

## 1. Real bags (no ground truth; one known obstacle)

![person crossing the track at 55.7 m, doubleT_obstacle frame 20](img/doubleT_obstacle_0020.png)
*`doubleT_obstacle` #20: the person crossing the track is reported at 55.7 m (red); the track axis
(green) follows the right-hand drift of the column row / wall; side structures are advisory (blue).*

![same bag, frame 165: person standing next to the column row → advisory only](img/doubleT_obstacle_0165.png)
*Frame 165: the same person now stands at the column row, ~1.8 m left of the axis → warning, not an alarm.*

| bag | frames | frames with **gauge alarm** | frames with advisory warning | mean / p95 ms | comment |
|---|---|---|---|---|---|
| `doubleT_obstacle` | 41 (every 5th) | 12 | 39 | 51 / 60 | **true positive**: person crossing / standing on the track at 55–57 m, reported at 55.6 m in frames 15–70 (while moving inside the gauge); walking person at 2–11 m next to the train is outside the gauge → advisory zone only |
| `roundT_doubleT` | 26 | 1 | 1 | 41 / 52 | 1 FP at 30.7 m (side structure at the tunnel-type transition) |
| `doubleT_platform` | 35 | 14 | 3 | 73 / 108 | FPs during the platform approach/stop: signs and objects at the platform edge overhanging the 1.4 m corridor by 0.1–0.3 m, overhead fixtures |
| `roundT_pressureGate_roundT` | 27 | 3 | 3 | 42 / 53 | FPs at 15–25 m when passing the gate frame (curve + gate, corridor edge) |
| `roundT_squareT_pressureGate_squareT` | 55 | 0 | 17 | 38 / 47 | clean |
| `squareT_platform_squareT_switch` | 88 | 49 | 49 | 76 / 125 | **main open problem**: train standing at a platform + switch ahead; periodic transverse structures at 40–130 m across the track (unidentified: beams / signs / people on the platform beyond the train?) and platform-edge objects trigger persistent alarms |

Evolution during the day (same 272 cached frames):

| version | change | gauge-alarm frames on empty bags (231 frames) | ms/frame |
|---|---|---|---|
| v0.0 | fixed lateral centre, box corridor, raw DBSCAN | 149 | 42–1461 (DBSCAN blow-up on dense near points) |
| v0.1 | rail-based self-calibration, rail-relative gauge, voxelised range-normalised DBSCAN, zones | 92 | 32–75 |
| v0.2 | wall-based yaw/curvature, robust two-stage floor fit | 76 | 38–75 |
| v0.3 | nearer-boundary rule, gauge 1.4 m, hardware/linear/wall filters, corridor validity range, overhead demotion | **67** (49 of them in the platform/switch bag) | 38–76 |

## 2. Synthetic obstacles injected into real empty frames (`resense inject` / `resense eval`)

26 frames of `roundT_doubleT` (every 10th), one object per frame (person 0.5×1.7 m, box 0.5 m,
plank 2×0.25×0.3 m), uniformly 10–220 m, 20 % placed outside the gauge as negatives. Objects
whose rays are all occluded by real geometry (7 of 26 — mostly because the per-frame height
reference is unreliable beyond ~80 m, see §4) are excluded.

| range bin | recall (v0.3) | n |
|---|---|---|
| 0–50 m | 3/3 | 3 |
| 50–100 m | 1/2 | 2 |
| 100–150 m | 0/5 | 5 |
| 150–200 m | 0/3 | 3 |
| 200–300 m | 0/3 | 3 |

First-detection distances: person 13.7 / 19.5 / 23.2 m (placed there), box 53.7 m; earlier run of
the same harness with objects on the rail head: person 68 / 80 / 110 m, box 56 m. Ray-cast point
budget (single frame): person 24 pts @80 m, 10 pts @110 m, 3–5 pts @150–190 m, 0–1 @>200 m —
consistent with the analytic estimate in DATASET.md. **Conclusion: single-frame geometry reaches
~100 m for a person; 150–300 m needs multi-frame accumulation (Sprint 2).**

Synthetic-tunnel unit tests (`tests/`): box 0.6 m detected at 30 and 80 m, person at 150 m, no
alarm on the clear tunnel, object 2.3 m off-axis not alarmed, occlusion of the background verified.

## 3. Timing (4-core sandbox, Python)

| stage | mean ms | notes |
|---|---|---|
| track model (bed + rails + walls) | 19–32 | numpy percentile binning; 32 ms on the 340k-point stationary bag |
| corridor mask | 9–14 | polygon test on ~190k points |
| voxel + DBSCAN + filters | 6–46 | 40+ ms only in platform scenes (tens of thousands of candidates) |
| tracking | <1 | |
| **total** | **38–76 mean, 47–125 p95** | frame period 100 ms; ROS 2 node adds decode (~5 ms) and publishing |

## 4. What we learned / hard cases

1. **Sensor mounts differ between bags** (bed 1.5 m vs 2.0 m below the sensor, axis 0.05–0.25 m
   right of the sensor axis) → any fixed calibration fails; the rail-ridge self-calibration is
   stable to ±0.05 m frame to frame.
2. **Curves**: a straight corridor hits the wall / column row at 50–130 m in three of six bags.
   The wall-boundary quadratic works on the pressure-gate curve (R ≈ 1.5–2.6 km, confirmed by the
   track-bed trough drift) but is ambiguous at tunnel-type transitions (walls diverge) and at
   stations. Next: fuse the bed-trough centre (usable to ~60–100 m), require agreement, and
   demote beyond disagreement.
3. **Height reference beyond ~80 m**: the bed is sparse/hidden (platforms, switches), the linear
   extrapolation drifts by up to 1–2 m at 120 m → phantom "overhead" obstacles and occluded
   synthetic objects. Next: fit the rail/bed line with far wall-base points, or the tunnel
   cross-section, as a second height anchor.
4. **Platform stop + switch bag** is where 49 of 67 residual FPs live. The advisory zone is
   inherently noisy near infrastructure (0.35 m outside the gauge).
5. **Small objects**: anything below rail head + 12 cm inside the rails and low/narrow hardware
   (< 0.35 m top, < 0.4 m wide) is filtered — a 20 cm object on the sleepers is currently
   invisible by design; revisit with the extended dataset.
6. **Point budget** is the physical limit: 0.5 m object = 7 pts @100 m, 1.6 pts @200 m.

## 5. Next experiments (owner in PLAN.md)

- ego-motion from the bag (bed/wall texture ICP or the organizers' speed if provided) → 5–10-frame
  accumulation → re-run §2 (target: person ≥ 150 m, box ≥ 100 m);
- extended dataset with real obstacles → calibrate dropout/intensity in `inject`, real recall/FP;
- FP taxonomy per scene type with the label tool (web/), report FP/km;
- GOST 23961-80 gauge polygon; platform notch; overhead policy;
- timing on the i7-9700E bench; Numba for the binning stages if needed.
