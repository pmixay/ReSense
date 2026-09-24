# Research notes — LiDAR obstacle detection in a metro tunnel

Compiled 2026-09-15 (day 1). Sections 1–6 are a literature/implementation survey; section 0 is
our own reading of the task and data and the hypothesis we chose. Claims marked *(uncertain)*
were not verified against the primary source.

## 0. Our reading of the problem and the chosen hypothesis

**Task** (ТЗ §2, §8): from a 10 Hz stream of 3D-LiDAR frames say "path clear" / "obstacle at X m"
for anything inside the train's clearance gauge, as far as possible (100 m good, 200 m very good,
300 m excellent), with few false alarms, in real time, on unseen bags, packaged as ROS 2 Humble in
Docker. Evaluation is dominated by working detection on hidden data, range, FP count, latency.

**Data facts that shape the design** (see DATASET.md): Hesai 128-line lidar, 0.1° × 0.125°
in the ROI, ±50° FOV, 10 Hz, ~190k valid points per frame; walls return to 150–200 m, track bed
to ~100 m, rails visible to ~30–40 m. Six bags, ~250 s, essentially **no obstacles inside the
gauge** (one person crossing the track at 55 m and one walking next to the train in
`doubleT_obstacle`), several curves (R ≈ 700–3000 m), a platform stop, a switch, pressure gates,
two different sensor mounts. Point budget per frame for a 0.5 × 0.5 m target: ~7 points at 100 m,
~1.6 at 200 m, <1 at 300 m ⇒ beyond ~150 m only multi-frame evidence can work.

**Hypothesis (v0, implemented)**: describe the *normal tunnel* geometrically and flag what does
not fit, restricted to the clearance gauge:
1. self-calibrate the track frame every frame (bed profile, rail head, axis from the two rails);
2. extrapolate the axis with yaw/curvature taken from *parallel references* (walls, column rows)
   that are visible far beyond the rails — and only trust the corridor as far as they are seen;
3. keep points inside the gauge polygon, cluster them with range-adaptive parameters, drop known
   infrastructure shapes, confirm over ≥3 frames;
4. output distance along the track, lateral offset, size, confidence, zone (gauge / advisory).

Learned detectors are deliberately not in v0: with zero real positives they would be trained on
synthetic data only; the plan is to use them (if at all) as a *second opinion* on the 0–100 m band
trained on `resense inject` data plus mined false positives (see §4).

**Open research items, by expected value**
- ego-motion estimate (bag speed, ICP on the near range, or wheel odometry if provided) →
  multi-frame accumulation in the world frame → 150–300 m for person-sized objects;
- an "expected range image" background model of the tunnel (per ray) as an independent anomaly cue;
- curvature estimation robustness at stations/switches (boundary jumps), fusion with the rails;
- gauge polygon from GOST 23961-80 drawings; small-object policy on the rail head;
- calibration of dropout/intensity at range if genuinely new labelled obstacle materials become
  available; the extended `new_data` ride has no obstacles.

---

## 1. Railway / tunnel LiDAR obstacle-detection literature

**Datasets**
- **OSDaR23** (Tagiew et al., arXiv:2305.03001; data: http://data.fid-move.de/dataset/osdar23). 45 sequences, Hamburg; 6 LiDARs (3× Livox Tele-15 long range, Hesai Pandar64, 2× Waymo Honeycomb); ego-motion-compensated merged clouds at 10 Hz; 204k annotations, 20 classes (person, car, animal, catenary pole, signal, track, …). CC BY 4.0 *(verify on portal)*. The only public multi-LiDAR rail dataset with obstacle cuboids.
- **RailSem19** (Zendel et al., CVPR-W 2019) — images only; useful only as a rail-segmentation prior.
- **WHU-Railway3D** (IEEE TITS 2024; https://github.com/WHU-USI3DV/WHU-Railway3D), **RailCloud-HdF** (VISAPP 2024), **SemanticRail3D** (Sci. Data 2025, doi 10.1038/s41597-025-06392-9), **Rail3D** (Infrastructures 2024, doi 10.3390/infrastructures9040071) — static MLS segmentation sets (rails, track bed, masts), no obstacles.
- **RailGoerl24** (arXiv:2504.00204) camera-only; **SynRailObs** (arXiv:2505.10784) synthetic obstacle dataset *(image-centric, uncertain if LiDAR)*; **TrainSim** (arXiv:2302.14486) railway simulator producing labelled LiDAR + camera + IMU.

**Methods (with achieved range)**
- **Shen et al., "LiDAR-Based Urban 3D Rail Area Extraction for Improved Train Collision Warnings", Sensors 2024** (PMC11314673). Livox Tele-15. Key idea: do not detect rails directly (rail points vanish beyond ~100 m); RANSAC-fit *parallel references* (tunnel walls, protective walls, sound barriers) per segment, derive the track centreline from known geometry, build a 3D track area. Track area to **150 m generally, 200 m in tunnels**, 95.2 % accuracy (97.4 % in tunnels), ~50 ms/frame on embedded HW. **Closest published match to our problem; our wall-based axis follows it.**
- **Nan et al., "A Novel High-Precision Railway Obstacle Detection Algorithm Based on 3D LiDAR", Sensors 2024** (PMC11124792). Scanline rail extraction, octree downsampling, adaptive Euclidean clustering, PCA + local-ICP FP filtering. 15 cm cube: 96 % within ±25 m; 10 cm cube: 84 % within ±20 m — shows how fast small-object range collapses with classical clustering.
- **Dias et al. (INEGI), "A LiDAR based obstacle detection framework for railway", EPJ Web Conf. 305, 2024** (doi 10.1051/epjconf/202430500027). Tele-15 + GNSS + pre-recorded track path; DBSCAN inside a track ROI at a fixed look-ahead (100 m at 80 km/h); static person tests at 50/100/150/200 m. Non-ML by choice because of data scarcity.
- "Railway Intrusion Detection Based on Dynamic Corridors and Multidimensional Constraints" (ResearchGate, 2025 *(venue uncertain)*): curvature-following corridors from the vehicle trajectory + track constraints.
- "LiDAR-Based Obstacle Detection Using Trajectory Maps" (Springer LNEE, doi 10.1007/978-981-92-2262-9_50): offline trajectory map + cm positioning, online clearance-envelope check.
- **Rail-PillarNet** (CMC 2024, doi 10.32604/cmc.2024.054525): PointPillars variant on OSDaR23, mAP 58.5 %.
- **Rail-BEV** (Sensors 2026, PMC13306471): LiDAR BEV + rail-geometry branch; range-stratified evaluation — at 100+ m pedestrian AP 36.8 % vs CenterPoint 2.9 % and BEVFusion 0.3 % — **stock detectors fail beyond 100 m**.
- Industry: SMART/SMART2 (Shift2Rail) multi-sensor on-board OD; Siemens Mobility Berlin S-Bahn test (2024) compares LiDAR against a cm-accurate 3D map (map-based change detection); DSD AutomatedTrain uses Aeva FMCW LiDAR; Hesai and Livox market railway OD.
- Metric/requirements: Tagiew, "Mainline Automatic Train Horn and Brake Performance Metric" (arXiv:2307.02586) — human detection distances: 40 cm cube ≈ 250 m, 20 cm ≈ 175 m, 10 cm ≈ 50 m, person ≈ 240 m by day — a good target ladder.

**Take:** corridor from walls + known gauge, detection only inside it; expect classical clustering to work to ~100 m and need accumulation/anomaly logic beyond; use OSDaR23 for sanity checks of augmentation.

## 2. Tunnel-specific point-cloud processing

- Cross-section fitting: shield-tunnel ellipse fitting with Huber loss (Appl. Sci. 2025, doi 10.3390/app15042249); continuity-constrained RANSAC ellipse across adjacent sections (Sensors 2026, doi 10.3390/s26103111); tunnel deformation from MLS (PMC11598767). Lesson: fit the lining per slice, robustly; fixtures make naive cylinder fits jump.
- Clearance-gauge inspection offline: Zhou et al., "Railway Tunnel Clearance Inspection Method Based on 3D Point Cloud from MLS", Sensors 2017 (PMC5621173) — track-based coordinate frame, slice, test points against a gauge polygon. This is exactly our online formulation.
- Background / anomaly: (a) per-slice lining fit residuals; (b) **expected-range image** — predict free range per (azimuth, elevation) from the tunnel model, flag returns closer than expected inside the gauge (cheap, degrades gracefully with sparsity); (c) map-based change detection against a prior pass. Tools: **Dynablox** (https://github.com/ethz-asl/dynablox), **ERASOR** (https://github.com/LimHyungTae/ERASOR), DUFOMap, **DynamicMap_Benchmark** (https://github.com/KTH-RPL/DynamicMap_Benchmark), LiSTA (arXiv:2403.02175), Octomap differencing — mostly for *moving* objects / map cleaning; static obstacles need pass-to-pass differencing with good localisation.
- Degenerate geometry: a straight tunnel is unobservable along its axis for ICP odometry. **X-ICP** (arXiv:2211.16335), **GenZ-ICP** (https://github.com/cocel-postech/genz-icp), LP-ICP (arXiv:2501.02580), D²-LIO (arXiv:2508.14355), rail-specific degeneracy-aware LIO (Sensors 2025, PMC12349154). Fix: fuse wheel odometry/IMU for the along-track DOF.

**Take:** build the tunnel prior from the bag, work in a track-aligned frame, flag gauge-interior residuals; for ego-motion prefer odometry/IMU (or the bag's own speed) over plain KISS-ICP.

## 3. Generic building blocks (ROS 2 / open source)

| Block | Tool | Notes / license |
|---|---|---|
| Ground/track-bed segmentation | **Patchwork++** (https://github.com/url-kaist/patchwork-plusplus, BSD-2, ROS 2 pkg); Autoware `autoware_ground_segmentation` (ray/scan ground filter, RANSAC; Apache-2.0) | plain per-slice RANSAC/percentile is fine on a flat bed (what we do) |
| Clustering | PCL `EuclideanClusterExtraction` (+GPU); Autoware `autoware_euclidean_cluster`; **depth_clustering** (https://github.com/PRBonn/depth_clustering, MIT, range-image, fast, handles sparse far points); Curved-Voxel Clustering (https://github.com/xmba15/curved_voxel_clustering); Open3D `cluster_dbscan`; GPU DBSCAN in **cupoch** | use range-adaptive ε and min points (we scale by 1 + r/40 m) |
| GPU PCL | **cuPCL** (https://github.com/NVIDIA-AI-IOT/cuPCL) filter/RANSAC/octree/cluster/ICP/NDT; NVIDIA Lidar_AI_Solution (PointPillars/CenterPoint TensorRT) | CPU is enough for ~200k pts/frame; GPU only for accumulation buffers / learned scoring |
| Odometry | **KISS-ICP** (https://github.com/PRBonn/kiss-icp, MIT, ROS 2) — degenerate in tunnels; **GenZ-ICP** (ROS 2); **FAST-LIO2** (GPL-2.0, needs IMU; ROS 2 ports exist) | GPL matters if shipping binaries |
| Accumulation | Autoware `pointcloud_preprocessor` (distortion corrector + concatenate); literature: VADet (arXiv:2411.13186), accumulation study (arXiv:2308.15357: 3–5 frames best) | |
| Libraries | PCL (BSD-3), Open3D (MIT; RaycastingScene, DBSCAN, ICP), Autoware Universe (Apache-2.0) | |

**Take:** range-image/voxel pipeline: (1) compensate + accumulate 5–10 frames; (2) per-slice bed; (3) gauge crop in the track frame; (4) range-adaptive clustering; (5) ≥k-of-N persistence. All CPU, <50 ms.

## 4. Learning-based options and the data problem

- Detectors: PointPillars/CenterPoint via **OpenPCDet** or **mmdetection3d**; Autoware `autoware_lidar_centerpoint` (TensorRT, ROS 2 node). Evidence (Rail-BEV) says stock detectors get ~0–3 % AP beyond 100 m on Tele-15 data → viable only for 0–100 m, and only with heavy augmentation / accumulated clouds.
- GT-sampling (copy-paste) in OpenPCDet `database_sampler.py`: pastes cropped object points, checks BEV collisions, does **not** handle occlusion or range-dependent density.
- Realism-aware augmentation: **Real-Aug** (arXiv:2305.12853, https://github.com/JinglinZhan/Real-Aug), **LiDAR-Aug** (CVPR 2021, ray-cast CAD models with occlusion), Real3D-Aug (arXiv:2206.07634), DR.CPO (arXiv:2303.12743), **PolarMix** (arXiv:2208.00223), pattern-aware DA (arXiv:2112.00050), **False-Positive Sampling** (arXiv:2403.02639, paste FP-prone clutter as negatives), **Paved2Paradise** (arXiv:2312.01117: background scans + separately captured objects, inserted with occlusion — the closest recipe to "empty tunnel + few objects"). Survey: arXiv:2308.12113.
- Synthetic insertion via ray casting: Open3D `RaycastingScene` against the sensor's exact (az, el) ray table → occlusion-correct, range-correct density; add dropout vs range/incidence and intensity ∝ ρ·cosθ/R². CARLA `sensor.lidar.ray_cast`, Isaac Sim RTX LiDAR, Gazebo `gpu_lidar` / rmagine as alternatives. **This is what `resense.synthetic.inject_obstacles` implements.**
- Anomaly / OOD: survey arXiv:2204.07974; STU LiDAR anomaly dataset (arXiv:2505.02148); range-image autoencoders fit our data distribution but fire on cables/signs/wet patches — need the gauge mask and persistence.

**Take:** don't train a detector on a handful of real obstacles; generate thousands of frames by inserting objects into the empty-tunnel bags with correct density/occlusion, mix with real negatives, and (optionally) train a small detector for 0–120 m as a second opinion.

## 5. Long-range specifics

Datasheet ranges (10 % reflectivity): Ouster OS2 200 m; Velodyne VLS-128 300 m; **Hesai OT128/AT128 200 m** (0.1° × 0.125° dense band); RoboSense Ruby Plus 240 m; Livox **Tele-15 320 m** (non-repetitive, 240k pts/s in 14.5° × 16.2°); Avia 190 m; Mid-360 40 m. Only Tele-15, VLS-128, Ruby Plus reach 300 m on dark targets; 200 m is the practical limit for our AT128-class sensor.

Points on a 0.5 × 0.5 m target per frame (angular pitch × range): OT128/AT128 ≈ 6.6 @100 m, 1.6 @200 m, 0.7 @300 m (beyond range). Strategies: (1) accumulate 0.5–1 s with ego-motion compensation (22 m/s at 80 km/h → must compensate); (2) range-adaptive thresholds, 1–3 points at 200–300 m are a *candidate* confirmed by persistence as range decreases; (3) intensity anomalies; (4) second returns to reject dust/water; (5) per-pixel expected-range background with range-growing tolerance.

## 6. Evaluation metrics

- Safety framing: Tagiew (arXiv:2307.02586) argues mAP is the wrong metric; report detection vs distance per object size, minimise false stops. Gleirscher et al. (arXiv:2306.14814) convert detection probabilities into hazard rates. IEC 62267 sets the functional requirement for GoA3/4 without numeric thresholds.
- Papers report: range-stratified AP (0–50/50–100/100+), detection rate per size vs distance, track-area accuracy vs range, frame time, false alarm rate, max range per scenario (straight 240 m, R=312 m curve → 70 m, 3 % ramp → 100 m).
- Kinematics to quote: 80 km/h = 22.2 m/s; emergency braking 1.0–1.3 m/s² → 190–250 m stopping distance + 25–45 m reaction ⇒ 200–300 m detection ≈ one stopping distance; TTC 100 m → 4.5 s, 200 m → 9 s, 300 m → 13.5 s.
- **Our report card** (`resense eval`): first-detection distance per object size and track section; recall by range bin (0–50, 50–100, 100–150, 150–200, 200–300); FP per frame / per km on empty bags by cause; latency mean/p95; frames-to-alarm.

### Reading list (priority order)
1. Shen et al., Sensors 2024 (PMC11314673) — tunnel-wall-based track area to 200 m
2. Tagiew, arXiv:2307.02586 — metric & human detection distances
3. Rail-BEV (PMC13306471), Rail-PillarNet (doi 10.32604/cmc.2024.054525) — learned baselines on OSDaR23
4. OSDaR23, arXiv:2305.03001 — data & sensor setup
5. Paved2Paradise arXiv:2312.01117, Real-Aug arXiv:2305.12853, FP-sampling arXiv:2403.02639 — augmentation recipes
6. Patchwork++ / depth_clustering / GenZ-ICP / Dynablox repos — building blocks
7. X-ICP arXiv:2211.16335 — why odometry breaks in tunnels
8. Sensors 2026 doi 10.3390/s26103111 & Sensors 2017 PMC5621173 — tunnel lining fitting and gauge inspection
