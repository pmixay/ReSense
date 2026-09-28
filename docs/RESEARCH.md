# Research Notes: LiDAR Obstacle Detection in a Metro Tunnel

> **Purpose:** the literature and implementation survey behind the approach (spec §8.7): the
> approaches considered, why the chosen one, and what became of the alternatives.
> **Audience:** team, jury · **Owner:** P3 · **Language:** EN
> **Last verified:** 2026-09-29: §0 against the sealed detector and [`DECISIONS.md`](DECISIONS.md);
> the survey (§1–§6) is of 15.09 · **Status:** current (§0), reference (§1–§6)

§0 is our reading of the task and the choice we made, kept current; §1–§6 are the day-1 survey
(15.09), condensed. Claims marked *(uncertain)* were not checked against the primary source. The
current method is [`ALGORITHM.md`](ALGORITHM.md); results are in [`EXPERIMENTS.md`](EXPERIMENTS.md)
and [`SCORECARD.md`](SCORECARD.md).

## 0. Our reading of the problem and the chosen approach

**Task** (ТЗ §2, §8): from a 10 Hz stream of 3D-LiDAR frames say "path clear" / "obstacle at X m"
for anything inside the train's envelope, as far as possible (100 m good, 200 m very good, 300 m
excellent), with few false alarms, in real time, on unseen recordings, as ROS 2 Humble in Docker.

**Data facts that shape the design** ([`DATASET.md`](DATASET.md), [`SENSOR.md`](SENSOR.md)): a
Hesai Pandar128, 0.1° × 0.125° around the horizon, 10 Hz, ~190 k valid points per 120° frame;
walls return to 150–200 m, the bed to ~100 m, rails to ~30–40 m, nothing beyond 210 m. Real
positives: one crossing person and one object on a rail at 55–57 m; the rest (six short
recordings, a 20-minute ride) is empty tunnel with curves, platforms, a switch, pressure gates and
two mounts. A 0.5 × 0.5 m target returns ~7 points at 100 m, ~1.6 at 200 m, < 1 at 300 m.

**Chosen approach: describe the normal tunnel geometrically and flag what does not fit inside
the envelope.**

1. self-calibrate the mount and the track frame on every frame (bed, rail heads, axis from the
   rails) — no map, no prior of the given tunnels;
2. extend the axis with yaw / curvature from *parallel references* (walls, column rows) that are
   visible far beyond the rails, and trust the corridor only as far as they are seen;
3. keep the points inside the envelope, cluster them with range-scaled parameters, drop known
   infrastructure shapes, confirm over 0.5 s;
4. report distance along the track, lateral offset, size, zone (STOP / CAUTION) and an
   estimated clear distance (an estimate, not a guarantee).

**Why this one.** It works with almost no real positives, runs on a CPU in real time, is
explainable rule by rule, and the closest published method (Shen et al. 2024, §1) reaches 150 m,
200 m in tunnels, with the same wall-based axis. Its costs, stated in
[`SCORECARD.md`](SCORECARD.md): rules were added per infrastructure type and per organizer
object, and several thresholds are tuned on the data they are measured on.

**Alternatives and what became of them** (evidence: [`DECISIONS.md`](DECISIONS.md), the methods
table in the [experiment log](archive/EXPERIMENTS_log_2026-09.md) §7):

| approach | against it | outcome |
|---|---|---|
| trained 3D detector (PointPillars / CenterPoint, §4) | no real positives to train on; stock detectors reach ~0–3 % AP beyond 100 m (Rail-BEV) | not built |
| learned *second opinion* on the rules' tracks (§4) | trained on synthetic positives; a veto would hide real objects | shipped as a bounded delay, never a veto (DECISIONS row 19) |
| map / pass-to-pass change detection (§2) | needs a prior map and cm localisation; the check includes rides beyond the given data | rejected (row 2) |
| expected-range image / range-image anomaly model (§2, §4) | fires on cables, signs, wet patches; needs the same envelope and persistence | not built |
| multi-frame accumulation with ego-motion (§3, §5) | LiDAR odometry degenerates in straight tunnels; the trains may give no speed | built; on only when a speed is given; the LiDAR-only speed estimate is accurate but buys nothing on the organizers' objects (row 3) |
| GPU acceleration (§3) | a container that requests a GPU does not start without the toolkit; untestable in CI | CPU only, optional C++ kernels (rows 4, 5) |
| GOST 23961-80 gauge polygon | the organizers gave the train envelope instead | 2.1 × 3.0 m envelope (row 1) |

## 1. Railway / tunnel LiDAR obstacle-detection literature

**Datasets.** **OSDaR23** (Tagiew et al., arXiv:2305.03001; http://data.fid-move.de/dataset/osdar23):
45 sequences, 6 LiDARs, 204k annotations in 20 classes, CC BY 4.0 *(verify)* — the only public
multi-LiDAR rail set with obstacle cuboids. RailSem19 (Zendel et al., CVPR-W 2019) images only.
WHU-Railway3D (IEEE TITS 2024), RailCloud-HdF (VISAPP 2024), SemanticRail3D (Sci. Data 2025,
doi 10.1038/s41597-025-06392-9), Rail3D (Infrastructures 2024): static segmentation sets, no
obstacles. RailGoerl24 (arXiv:2504.00204) camera-only; SynRailObs (arXiv:2505.10784) synthetic
*(image-centric, uncertain if LiDAR)*; TrainSim (arXiv:2302.14486) simulator with LiDAR.

**Methods.**
- **Shen et al., Sensors 2024** (PMC11314673), Livox Tele-15: rails vanish beyond ~100 m, so fit
  *parallel references* (tunnel walls, barriers) with RANSAC and derive the track area: **150 m
  generally, 200 m in tunnels**, 95.2 % accuracy, ~50 ms/frame embedded. **Closest to our
  problem; our wall-based axis follows it.**
- **Nan et al., Sensors 2024** (PMC11124792): scanline rail extraction, adaptive Euclidean
  clustering, PCA + ICP filtering; a 15 cm cube 96 % within ±25 m — small-object range collapses
  quickly with classical clustering.
- **Dias et al., EPJ Web Conf. 305, 2024** (doi 10.1051/epjconf/202430500027): DBSCAN inside a
  track ROI from a pre-recorded path; non-ML by choice for lack of data.
- Curvature-following corridors from the trajectory (ResearchGate 2025 *(venue uncertain)*);
  trajectory maps + cm positioning (Springer LNEE, doi 10.1007/978-981-92-2262-9_50).
- **Rail-PillarNet** (CMC 2024, doi 10.32604/cmc.2024.054525): PointPillars on OSDaR23, mAP 58.5 %.
  **Rail-BEV** (Sensors 2026, PMC13306471): at 100+ m pedestrian AP 36.8 % vs CenterPoint 2.9 %
  and BEVFusion 0.3 % — **stock detectors fail beyond 100 m**.
- Industry: Shift2Rail SMART/SMART2; Siemens Mobility (map-based change detection); DSD with Aeva
  FMCW LiDAR. Requirements: Tagiew, arXiv:2307.02586 — human detection distances (40 cm cube
  ≈ 250 m, person ≈ 240 m by day).

**Take:** corridor from walls + known envelope, detection only inside it; classical clustering to
~100 m, accumulation or evidence over time beyond.

## 2. Tunnel-specific point-cloud processing

- Cross-section fitting: robust ellipse / RANSAC fits of the lining per slice (Appl. Sci. 2025,
  doi 10.3390/app15042249; Sensors 2026, doi 10.3390/s26103111); fixtures make naive fits jump.
- Clearance inspection offline: Zhou et al., Sensors 2017 (PMC5621173) — track-based frame,
  slices tested against a gauge polygon: our online formulation.
- Background / anomaly: lining-fit residuals; an **expected-range image** per (azimuth, elevation)
  flagging returns closer than expected; change detection against a prior pass (Dynablox, ERASOR,
  DUFOMap, DynamicMap_Benchmark, LiSTA) — mostly for moving objects or map cleaning.
- Degenerate geometry: a straight tunnel is unobservable along its axis for ICP (X-ICP
  arXiv:2211.16335, GenZ-ICP, LP-ICP arXiv:2501.02580, D²-LIO arXiv:2508.14355); fix with wheel
  odometry / IMU for the along-track DOF.

**Take:** build the tunnel prior from each frame, work in a track-aligned frame; for ego-motion
prefer odometry / IMU over plain ICP.

## 3. Generic building blocks (ROS 2 / open source)

| block | tools | note |
|---|---|---|
| ground / bed | Patchwork++ (BSD-2), Autoware ground segmentation | a per-slice percentile fit suffices on a flat bed (ours) |
| clustering | PCL Euclidean, Autoware, depth_clustering (range image), Open3D DBSCAN, cupoch (GPU) | range-adaptive ε and minimum points |
| GPU | cuPCL, NVIDIA Lidar_AI_Solution | a CPU is enough for ~200 k points per frame |
| odometry | KISS-ICP (degenerate in tunnels), GenZ-ICP, FAST-LIO2 (GPL-2.0, needs IMU) | GPL matters for shipped binaries |
| accumulation | Autoware distortion corrector; VADet (arXiv:2411.13186); 3–5 frames best (arXiv:2308.15357) | |

**Take:** compensate + accumulate, per-slice bed, envelope crop in the track frame, range-adaptive
clustering, k-of-N persistence — all on a CPU in < 50 ms.

## 4. Learning-based options and the data problem

- Detectors: PointPillars / CenterPoint via OpenPCDet or mmdetection3d, Autoware
  `lidar_centerpoint`; per Rail-BEV viable only for 0–100 m, with heavy augmentation.
- Copy-paste GT sampling (OpenPCDet) ignores occlusion and range-dependent density.
  Realism-aware augmentation: Real-Aug (arXiv:2305.12853), LiDAR-Aug (CVPR 2021), PolarMix
  (arXiv:2208.00223), False-Positive Sampling (arXiv:2403.02639), **Paved2Paradise**
  (arXiv:2312.01117: background scans + objects inserted with occlusion — "empty tunnel + few
  objects").
- Ray-cast insertion against the sensor's exact ray table (Open3D `RaycastingScene`; CARLA, Isaac
  Sim, Gazebo as alternatives): occlusion- and range-correct density. **This is what
  `resense.synthetic.inject_obstacles` implements.**
- Anomaly / OOD: survey arXiv:2204.07974; STU (arXiv:2505.02148); range-image autoencoders fire on
  cables, signs and wet patches without the envelope mask and persistence.

**Take:** do not train a detector on a handful of real obstacles; insert objects into the empty
recordings with correct density and occlusion, and use learning at most as a second opinion.

## 5. Long-range specifics

At 10 % reflectivity the Pandar128 reaches 200 m only on its 32 horizon channels
([`SENSOR.md`](SENSOR.md) §2); Livox Tele-15 (320 m), Velodyne VLS-128 (300 m) and RoboSense Ruby
Plus (240 m) are the units that reach further. Points on a 0.5 × 0.5 m target per frame: ≈ 6.6 at
100 m, 1.6 at 200 m, 0.7 at 300 m. Strategies: accumulate 0.5–1 s with ego-motion compensation
(22 m/s at 80 km/h); treat 1–3 points at 200–300 m as a *candidate* confirmed by persistence as
the range shrinks; intensity anomalies; second returns against dust; an expected-range background.

## 6. Evaluation metrics

- Safety framing: Tagiew (arXiv:2307.02586) — mAP is the wrong metric; report detection versus
  distance per object size and minimise false stops. Gleirscher et al. (arXiv:2306.14814) turn
  detection probabilities into hazard rates. IEC 62267 sets GoA3/4 requirements without numbers.
- Papers report range-stratified AP, detection rate per size and distance, frame time, false-alarm
  rate, maximum range per scenario (straight 240 m, R = 312 m curve → 70 m).
- Kinematics: 80 km/h = 22.2 m/s; emergency braking 1.0–1.3 m/s² → 190–250 m + 25–45 m reaction,
  so 200–300 m detection ≈ one stopping distance; time to collision 4.5 s at 100 m, 9 s at 200 m.
- Our report card: [`EVALUATION.md`](EVALUATION.md) §2.

**Reading list (priority):** Shen et al. (PMC11314673); Tagiew (arXiv:2307.02586); Rail-BEV
(PMC13306471) and Rail-PillarNet; OSDaR23 (arXiv:2305.03001); Paved2Paradise, Real-Aug,
FP-sampling; Patchwork++ / depth_clustering / GenZ-ICP / Dynablox; X-ICP; the tunnel-lining and
gauge-inspection papers of §2.
