# kurorodev/lct2026_metro

## Verdict
Classical geometry (pure NumPy, class-agnostic "Metro Guard" baseline, no learned model). Maturity: a working offline pipeline plus ROS 2 node and web review tool, with 18 unit tests. Its own docs say the numbers are not accuracy: `docs/EXPERIMENTS.md` states there is no ground truth, `quality_metrics` are null, and alarm counts are "not quality". The only labelled evidence is 10 checkpoint frames of the new scenario. Their selection used the organizer insertions' intensity=1 signature, and the same frames were used to choose the `mounted_lidar` profile. Treat it as a useful reference for corridor/rail code and for the review and evaluation tooling, not as a detector with known performance.

## Pipeline
1. `metro_guard/cloud.py:canonical`, `bag.py`: read PointCloud2 from bag; forward axis -y; keep 2-220 m, |y|<60, |z|<25.
2. `metro_guard/geometry.py:estimate_corridor` (rail_guided, `config/mounted_lidar.json`): per 5 m bin, roadbed height, rail pair (`surface.py:rail_pair`), and rail-to-wall offset learned from rail-visible bins, used to place the centre when rails are absent.
3. `baseline_geometry.py:estimate_corridor` (default): same idea with fixed wall offset 2.5 m, kept as a frozen baseline.
4. Corridor nodes per bin: [x, centre, floor, support, ceiling]; floor and centre are slope-limited extrapolations.
5. `detector.py:Detector.process`: points inside a height-dependent half-width envelope (0.85 m underbody to 1.45 m at 0.8 m height), 0.28-3.2 m above floor (0.10 m in the mounted profile), below ceiling-0.2 m.
6. `detector.py:clusters`: 26-neighbour connected components on a fixed 0.35 m voxel grid; drop clusters with <5 points or extent <0.12 m.
7. Per cluster: interior-point count (penetration > boundary margin); `boundary_uncertain` when interior points < 5; geometry-support confidence from corridor nodes.
8. Tracking: greedy nearest match (dx < 1 + 35 m/s * dt, |dy|,|dz| < 0.8 m); confirmed after 3 frames and not boundary-uncertain.
9. Status: obstacle / candidate / unknown / no_obstacle_observed; reasons include timestamp gap, insufficient or ambiguous corridor.
10. `ros_node.py` publishes the result; `web/` review UI with manual labels; `evaluate.py` frame-level metrics.

## Candidate ideas
| # | idea | where in code | mechanism (1-2 lines) | have in ReSense? (yes/partial/no, evidence) | expected effect: recall / range / FPR | cost & risk | evidence in repo (measured? held-out?) |
|---|---|---|---|---|---|---|---|
| 1 | Rail pair per 5 m range bin from a 2 cm lateral histogram: peak must exceed max(4, 1.8 x median); gauge window 1.52 +/- 0.12 m; heights of both heads within 0.25 m; "never infer a rail from a single peak" | `surface.py:rail_pair`; used in `geometry.py:estimate_corridor` | Per-bin rail evidence with explicit gauge and height-consistency checks | partial. ReSense `config.py:72` `rails_spacing=1.59` (prior) and `track.py:estimate_rails` (ridge histogram). ReSense has no per-bin pair-peak rule with a height-consistency gate (verify before claiming) | FPR on platform/switch frames: possibly down (single peaks rejected). Recall: may drop if rails are missing | low | none measured separately |
| 2 | Wall offset learned from rail-visible bins (median of last 6 offsets), then used to place the centre where rails are absent | `geometry.py:estimate_corridor` (`offsets`, proposals, `nominal_wall_offset`) | Keeps the track centre in platform/double-track bins where only walls are visible | partial. ReSense `track.py:estimate_axis_from_walls` fits walls directly and `config.py` `axis_one_side_range`, `no_rail_range` cap trust. Learning a per-run wall offset is not in ReSense (grep `wall_offset` no hit) | range on platforms: possibly up. FPR on switches/curves: risk if offset is stale | medium | none separate |
| 3 | Roadbed height as the mode of a 0.08 m histogram inside the lowest 8th-percentile band, to avoid drainage troughs | `surface.py:roadbed_height` | Floor estimate follows the dominant low surface, not the trough | partial. ReSense `track.py:bin_percentile`, `_fit_floor` use percentiles per bin. Mode-based floor is a small change | floor accuracy: small; FPR near drainage: possibly down | very low | none |
| 4 | Per-node continuity gates: reject a rail pair whose height differs by >0.15 m from prediction; clamp floor to bed-0.1..bed+0.6 when extrapolating; skip a node if floor jumps >0.65 m | `geometry.py:estimate_corridor` | Stops a raised structure or a switch from producing a vertical jump in the corridor | yes/partial. ReSense rate limits and warm-up (`config.py:105` `axis_warmup_frames`, rate limits in `track.py`) | FPR on switches/raised platforms: down. Recall: small loss | low | none |
| 5 | Interior-point count with boundary-uncertain flag: a cluster counts as confirmed only if >=5 points lie inside the envelope by a margin | `detector.py` (`penetration`, `interior_points`, `boundary_uncertain`) | Edge-of-gauge hits are reported as uncertain, not as obstacles | yes. ReSense `config.py:145-146` `edge_margin` (0.15 m per 100 m) and strict/advisory split (`gauge.py` `warning_margin`) | edge-of-gauge FPR: down. Recall for edge objects (0.3 m, edge): down | low | none |
| 6 | Fixed 0.35 m voxel components regardless of range (contrast with range-dependent cells) | `detector.py:clusters(q, 0.35)` | Keeps component boundaries continuous over range, avoids over-splitting far objects | partial. ReSense uses range-growing DBSCAN radius (per brief). Our own range-banded voxels in MoscowMetropilot are a third option. Needs an ablation, not a claim | range: unclear, probably neutral. FPR: unknown | low | none |

## Things done worse than ReSense / red flags
- Default profile (`config/default.json`, baseline geometry) missed a low object on rails in the new scenario, so `config/mounted_lidar.json` was made (`min_height` 0.28 -> 0.10 m, `lidar_height` 1.075 m, boundary_margin 0.12). The README says this was checked on 10 selected frames. That is in-sample tuning, and it lowers the height floor, which raises the false-alarm risk.
- Alarm rates are very high on platform/switch bags: `docs/EXPERIMENTS.md` table shows 765/877 frames `obstacle` on squareT_platform_squareT_switch and 343/345 on doubleT_platform. The docs call this out and say the detector is not ready. The counts are frames with any confirmed candidate, not STOP episodes, so they are not comparable to ReSense's per-km numbers.
- Ceiling exclusion (`detector.py`: points above `ceiling - 0.2` dropped; ceiling = 98th percentile of points near the track) removes everything under the tunnel roof, including hanging cables and poles. ReSense rejected a similar rule (`shell`) for this reason. Do not borrow without a hanging-object test.
- Hard point deletion in envelope and ceiling masks, while ReSense never deletes structure.
- Runtime measured on macOS arm64 Python 3.8 (`analysis/benchmark-final.json`), not on target hardware.

## Eval/data tooling worth borrowing
- `metro_guard/evaluate.py`: frame-level metrics from reviewed JSONL labels. It rejects a label whose bag name or timestamp does not match the prediction, counts `unknown` as a miss, and reports distance MAE only for true positives. Copy the binding check, it prevents mixing bags.
- `web/review.js`, `web/index.html`: manual frame labels, with the prediction hidden on request, exported as JSONL for independent review (`docs/EXPERIMENTS.md`).
- `analysis/benchmark-*.json` with environment record and per-bag alarm counts; `scripts/audit_data.py` and `analysis/dataset_audit.json` for bag inventory.
- `scripts/review_fake_scenario.py` for checkpoint review. It uses the insertion intensity signature for review only (not the detector), so it is not a general labelling method.
