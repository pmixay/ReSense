# zuykovmikhail1305-boop/3D-lidar_ml

## Verdict
Learned (range-image U-Net "inpainting" + volumetric clustering of points the net *added*), early prototype: 2nd-epoch weights, no gauge/path/rail logic, no tracking, no GPU-free path (CPU "hundreds of ms/frame"). The only metrics (README `inference/README.md`, "Качество сейчас": 87 % of clusters on inserted objects, 46 % of frames with an object detected, 16 % of empty frames with a false cluster) are measured on `cloud_with_fake_obj` with a label trick that only exists for organizer-inserted points; no real-obstacle, held-out, or FPR-per-km number exists. Not a usable competitor for case 05; the top-level repo is mostly a PySide6 UI skeleton (`3D-lidar-windowUI`, empty `ros_worker.py`, `mp/main.py` is "Hello"), the `inference/`, `lidar_api/`, `src/model/model/*` trees are near-copies of each other.

## Pipeline
1. `inference/lidar_detector/range_image.py:points_to_range`: cloud -> 128 x 1024 range/intensity image (ring x azimuth 0.1 deg), sector -140..-40 deg cut by a further 17 deg each side (net sees only ~+-33 deg ahead); nearest return per pixel.
2. `model.py:restore`: U-Net (4 levels, base 32, 31 MB) on [log-range, intensity, occupancy, left-filled range]; outputs range correction, "point should exist" logit, "input point is junk" logit. Training script is NOT in the repo (`train_unet.py` referenced, absent), so training data/labels are unknown (presumably self-supervised on masked empty frames + synthetic junk).
3. `clusters.py:added_mask`: "added" = pixel empty in input but present in net output; drop pixels that are structurally empty (`structural_empty.npy`) or where the net "habitually" adds points (`added_rate.npy` > habit 0.2, calibrated on 300 frames of the very eval bag).
4. `clusters.py:find_clusters`: 5 cm voxelization, range-growing radius (1 cm/m), union-find components, per-range-zone (0-300 m, 50 m zones) min points scaling 1/r^2 (floor 6), size/thickness limits (`cluster_zones_3d.json`).
5. Output: any cluster anywhere in the sector = `detected=1` (no gauge test, no distance-to-track, no temporal confirmation). README top-level promises 300/200/100 m zone probabilities but this is UI-only mock (`3D-lidar-windowUI/mainwindow.py` "демо-стрим").

## Candidate ideas (table)
| # | idea | where in code | mechanism | have in ReSense? | expected effect | cost & risk | evidence in repo |
|---|---|---|---|---|---|---|---|
| 1 | Recover `ring` from elevation angle by nearest fixed beam angle (clouds without ring field) | `range_image.py:ring_from_elevation`, `estimate_elevations` | Beam elevations are fixed; real points sit on them within float32 rounding, so nearest-beam lookup gives ring | no: for ring-less clouds ReSense fills ring with zeros (`resense/pointcloud.py:82,95`), `.npz` caches use `ring=None` (`resense/cli.py:171`); ring-based code (`farrails.py`, cross-ring) is opt-in and would be blind there. No elevation->ring recovery found (grep `ring_from`, `elevation` in resense/) | enables ring-wise checks (cross-ring, far-rail) on ring-less organizer clouds; no direct recall effect | trivial (1 function) ; Gabarit repo has a histogram-peak variant, see Gabarit report | claimed "100 % match on 3 clouds with ring" (README), unverified here |
| 2 | Exact labels for organizer synthetic objects: inserted points do not lie on any beam elevation angle | README "Качество сейчас"; `ring_from_elevation` docstring | Points off the 128 fixed elevations (or after the last zero return, see Gabarit) are inserted => per-point ground truth | partial: ReSense matches fixtures by exact quantized XYZ/intensity (`docs/ORACLE_ACCUMULATION_PROTOCOL_2026-09-28.md`, `docs/RANGE_METRIC_DIAGNOSTIC_2026-09-28.md`); elevation-grid test not found | eval tooling only; a second independent labeller to cross-check ours | low | only on the 10 organizer objects |
| 3 | "Habit mask": per-pixel rate at which an anomaly detector fires on normal frames, then suppress those pixels | `clusters.py:added_mask` (`rate > habit`), `calibrate.py` | persistent per-pixel false-positive rate learned on empty frames | no (we rejected prebuilt tunnel map / revisit comparison, same family: `docs/DECISIONS.md`) | FPR on repeated places only, memorises the tunnel; rejected for us already | n/a | calibrated on the same bag it is evaluated on |
| 4 | Range-adaptive min-points law 1/r^2 with floor 6, per 50 m zone | `clusters.py:required_points` | threshold falls with expected point count ~ 1/r^2 | yes: range-growing eps + `_visibility` expected-points score (`resense/clustering.py:_visibility`) | none | - | no ablation |

Nothing else is transferable: the U-Net/inpainting route is the "range-image anomaly / learned" family we already rejected (`docs/RESEARCH.md` row "expected-range / range-image anomaly", `docs/EXPERIMENTS.md`), and here it has no positive training examples, no gauge, and the sector is narrower than our needs.

## Things done worse than ReSense / red flags
- No train-gauge/corridor at all: cluster outside the rails (wall equipment, platform) is "detected"; the 16 % FP-frame rate and 0.19 FP clusters/frame is >100x worse than any of ours per frame.
- Metrics are from one organizer bag with synthetic points, weights from epoch 2, `added_rate.npy` calibrated on that same bag; labelling uses an artifact of how organizers inserted points, so numbers say nothing about real obstacles.
- Sector limited to +-33 deg and 128x1024 grid; sensor-specific (Hesai 128 only); zero use of ego-motion, temporal filtering, calibration; CPU is slow (README).
- Repo hygiene: 4 copies of the same code (`inference/`, `lidar_api/`, `src/model/model/inference`, `.../lidar_api`), 31 MB weights x4, colcon `install/`+`log/` committed, UI stub only.
- README top-level claims 300/200/100 m obstacle probabilities from an ML model; nothing in repo computes them (UI uses mock stream).

## Eval/data tooling worth borrowing
- Elevation-grid test as an independent label source for organizer-inserted points (see idea 2); trivial to add to our oracle tooling as a cross-check.
- `inference/viewer/server.py` before/after viewer is irrelevant for us (we have viz.py); nothing else.
