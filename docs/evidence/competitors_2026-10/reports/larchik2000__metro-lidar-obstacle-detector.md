# larchik2000/metro-lidar-obstacle-detector

## Verdict
Classical and naive: fixed sensor-frame box, voxel, DBSCAN, size gate, and an alarm when every one of the last 3 frames has any candidate. Single-commit baseline that its README calls unvalidated; no FP/FN numbers, only point counts.

## Pipeline
1. `ros2_ws/.../detector_node.py:ObstacleDetector.__init__`: subscribes to `/sensing/lidar/hesai128/pointcloud`, reads x, y, z only.
2. `detector_node.py:filter_roi`: fixed box in sensor frame, x (forward) 3-200 m, |y| <= 1.7 m, z in [-0.3, 3.5] and z > -0.35 (`config/detector_params.yaml`).
3. `detector_node.py:voxel_downsample`: voxel 0.15 m, keeps the first point per voxel, not the centroid.
4. `detector_node.py:find_clusters`: DBSCAN(eps=0.45, min_samples=6).
5. `detector_node.py:cluster_to_candidate`: >= 15 points, each extent >= 0.10 m; distance = |bbox centre xy|.
6. `detector_node.py:confirm_candidates`: alarm iff every one of the last 3 frames has >= 1 candidate, regardless of position or identity.
7. Publishes Bool, nearest distance (inf when none), `/filtered_points`, RViz markers.
8. Not present: background map (`background_map.py` is empty, `use_background_map: false`), ground or rail model, axis, ego-motion.

## Candidate ideas
| # | idea | where in code | mechanism | have in ReSense? | expected effect: recall / range / FPR | cost & risk | evidence in repo |
|---|---|---|---|---|---|---|---|
| 1 | Fixed rectangular ROI in sensor frame | `detector_node.py:filter_roi`, `detector_params.yaml` | Crops to a box before clustering | no, and ReSense is stronger: gauge follows fitted axis (`resense/gauge.py`, `track.py`) | none | none | none |
| 2 | "Candidate in every frame of last N" confirmation | `detector_node.py:confirm_candidates` | Temporal gate without association | no as a rule; ReSense requires matched track hits (`resense/tracking.py`) | none; any static cluster in the box passes | none | none |
| 3 | First-point-per-voxel downsampling | `detector_node.py:voxel_downsample` | Keeps one raw point per voxel | trivial; ReSense voxelises to the per-voxel mean (`resense/clustering.py:voxelize`) | none | none | none |

No idea here is worth porting.

## Things done worse than ReSense / red flags
- Infrastructure inside the box becomes candidates, and the "every frame" rule then confirms a STOP on any static structure. The README admits this ("Без фоновой карты элементы инфраструктуры ... могут образовывать кластеры-кандидаты"). This is the failure mode ReSense's infrastructure rules were built against.
- Box limits are start values ("Текущий ROI задан стартовыми параметрами"), not tied to the envelope or the rails.
- README file list includes `background_map.py`, `pointcloud_utils.py`, `scripts/inspect_bag.sh`; all are 0-byte files. `background_map_path` points to a file that is not in the repo.
- Only one bag mentioned in results (`doubleT_obstacle`), with no ground truth and no empty-tunnel run.

## Eval/data tooling worth borrowing
None. The RViz topic list (`/filtered_points`, `/obstacle_markers`) is the only tooling; ordinary.
