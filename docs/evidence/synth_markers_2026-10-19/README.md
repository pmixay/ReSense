# The organizers' marked synthetic bags and `obstacles.md` (19.10)

> **Purpose:** intake of `new_synth_data_with_markers.zst` (the three synthetic bags of 16.10 with
> marker boxes around the objects) and of `obstacles.md` (the order in which the objects appear), and
> what they change for our labels (N5), the dust work (N3) and the reading of 1.1.0's results.
> **Owner:** P1 (intake, 19.10); P4 takes the markers over for scoring · **Status:** development data,
> not G3 · **Detector code:** not touched (evaluation only, 1.1.0 `3b7d7aa` replayed read-only)

## Result in short

1. **Same clouds as the bags of 16.10.** The 1.1.0 replica gives, on the marked bags, exactly what the
   committed 1.1.0 runs of 16.10 gave, in every field except wall-clock timing, on **all 386 + 736 + 545
   frames** (decisions, every detection and warning, distances, mount, header stamps, bag times, point
   counts). Our earlier results on these bags therefore stand as they are.
2. **The markers are a separate topic**, `/synthetic_obstacle_markers` (`visualization_msgs/MarkerArray`),
   one message per cloud with the cloud's header stamp. A marked object is a wire box (`LINE_LIST`, 24
   points, its own pose) in the `hesai_lidar` frame. Unused slots are `DELETE` arrows. There is no class
   and no text, all boxes have the same colour, and **no marker id is reused** within a bag. The person is
   8 part boxes; every other object is one box.
3. **The markers agree with `obstacles.md`, 24 of 24 entries.** Ordered by the frame where the train
   passes them (the object's last marked frame), the marked objects reproduce the organizers' list item
   by item in all three bags. The list counts **3 + 4 + 4 = 11 dust clouds and 3 + 5 + 5 = 13 objects**.
4. **Dust in these bags is a few points for one or two frames.** Each "dust cloud" is a burst of 1–4
   boxes, each 3–6 cm in size, 3.4–7.2 m ahead, 0.1–0.6 m above the sensor. There are 1–14 points within 0.1 m of a box in
   its frame and none in the 6 frames before or after (28 of 30 boxes; the other 2 sit next to platform
   structure). On 1.1.0 these frames give **no STOP and no CAUTION caused
   by the dust**: 13 dust frames; their 6 CAUTIONs come from warnings elsewhere (1.75–152 m), none at a
   dust box. Our 17.10 statement "no dust in this delivery" was wrong: the dust is there, just too small
   to be seen by a search for a dust volume.
5. **Our N5 team labels match the markers**, with a median offset of 0.00–0.04 m. All 696 platform rows
   match. In switch, 681 of 692 rows match: the other 11 are sparse 1–4 point rows 2.4–5 m in front of
   the marked box. In tunnels, 295 of 296 rows match. **N5 missed one object:** the first small cube of
   `synthetic_tunnels` (marker id 18, frames 4–60, left of the track, 83 m → 1.2 m; 34 frames in the
   2.5–250 m crop).
6. **1.1.0's STOPs against the markers.** Platform: 185 of 185 STOP detections are on marked objects.
   Switch: 133 of 142. Tunnels: 120 of 128. The 17 detections without a marker:
   * background structures with no marker: switch frames 7–14 (147 m, from below the rail head up to
     it), tunnels 147–149 (68 m, at the tunnel wall in a curve) and 367 (131 m, below rail level). These
     are exactly N5's "false STOPs on background" (switch 8 frames, tunnels 3 + 1). **They are not dust.**
   * real objects in a frame without their marker: tunnels 460, the beam (a 1.83 m wide flat cluster at
     0.8 m below the sensor, between its marked positions in frames 459 and 461). Switch 416 is probably
     the hanging cable one frame after its last marker (1.6 m, 0.4–0.7 m above the sensor); this is **not
     verified**, the picture does not settle it.
   * a second detection on the track bed at 3 m (5.3 m long, at rail level) in tunnels 439–441, frames
     that are STOP anyway because of the 2 m cube ahead.
7. **A marker means the object has returns.** Each of the 3,893 published boxes holds at least one point
   (inside the box grown by 5 cm). In 1,214 of 1,246 frames where a marker is missing between two
   appearances, the box interpolated there is empty. The missing markers are therefore mostly frames
   with no returns. They are **not a complete per-frame label**, though: tunnels 460 has a missing marker
   on a detected object, and the linear interpolation is rough because the marker positions step
   unevenly (up to ~3 m in one frame).
8. **Synthetic objects get returns far beyond the real sensor.** The 2 m cube of `synthetic_tunnels` is
   marked, with points in its box, from **737 m** (54 m to the side, the track curves). The cubes and the
   person of the platform bag are marked from 244–335 m. Our 250 m crop ignores everything beyond it, and
   a real Pandar would not see it. Do not count these frames as misses.

## What was delivered

| file | size | SHA-256 | modified (UTC) |
|---|---:|---|---|
| `new_synth_data_with_markers.zst` | 2,533,631,921 B | `04d176b49526e5da55a0481cf92d8442604dc0fb9f69c31680482b21d8682760` | 2026-10-19 10:21 |
| `obstacles.md` | 1,024 B | `db62201d049da4f16063abceab8a918f7091335e41a093fcb9211863df687558` | 2026-10-19 10:57 |

The SHA-256 of the archive was checked on download. `obstacles.md` is recorded verbatim in
[`../../organizers/obstacles_2026-10-19.md`](../../organizers/obstacles_2026-10-19.md). The archive holds three rosbag2
(sqlite) bags with two topics each, `/lidar_points` and `/synthetic_obstacle_markers`, one message each per frame
([`meta/`](meta/)):

| bag | clouds = marker messages | marker slots per message | active boxes (all frames) | marker ids |
|---|---:|---:|---:|---:|
| `synthetic_platform_cloud_with_markers` | 386 | 25 | 2,758 | 16 |
| `synthetic_switch_cloud_with_markers` | 736 | 15 | 715 | 13 |
| `synthetic_tunnels_cloud_with_markers` | 545 | 21 | 420 | 18 |

## The objects (marker boxes, sensor frame: forward = −y, left = +x, up = +z)

"Passed" is the object's last marked frame. The table is in that order, with the `obstacles.md` item
it reproduces. Distances are of the box's near face.

| bag | `obstacles.md` | marker ids | frames (marked) | first marked → last | lateral, first → last (m) | box f × l × h (m) | N5 |
|---|---|---|---|---|---|---|---|
| platform | 1 dust left | 0, 1 | 21 | 3.5, 4.4 m | +1.48, +1.75 | 0.04 | — |
| platform | 2 dust right | 6, 7 | 27 | 4.4, 6.1 m | +1.40, +1.77 (**left**, see below) | 0.04 | — |
| platform | 3 dust (first cloud) | 12, 13 | 35–36 | 4.2, 4.9 → 3.9 m | −0.38, +0.17 | 0.04 | — |
| platform | 4 small cube right | 23 | 0–178 (179) | 243.8 → 0.5 m | −1.17 → −1.41 | 0.45 × 0.52 × 0.44 | obj01 |
| platform | 5 small cube left | 24 | 8–257 (209) | 289.2 → 0.4 m | +2.15 → +1.47 | 0.56 × 0.54 × 0.46 | obj02 |
| platform | 6 person | 15–22 (8 parts) | 0–385 (386) | 334.9 → 7.8 m (train stops) | +0.18 → −1.06 | 0.24 × 0.60 × 1.73 | obj03 |
| switch | 1 small cube right | 12 | 0–255 (256) | 161.8 → 1.4 m | +0.09 → −1.39 | 0.48 × 0.47 × 0.36 | box_right_1 |
| switch | 2 small cube on the left rail | 0 | 13–353 (111) | 298.5 → 1.2 m | +11.3 → +0.79 | 0.35 × 0.35 × 0.30 | box_left_2 |
| switch | 3 hanging inclined cable | 1 | 181–415 (140) | 318.9 → 3.4 m | +18.3 → +0.26 | 0.62 × 0.49 × 2.36, 0.55–2.91 m above the sensor | hanging_3 |
| switch | 4, 5 dust | 2, 3 / 5 | 481 / 483 | 4.0–5.5 m | −0.62, +0.30 / +1.51 | 0.03–0.05 | — |
| switch | 6 small cube left | 13 | 365–554 (57) | 296.8 → 0.8 m | +16.8 → +1.38 | 0.44 × 0.48 × 0.48 | box_left_4 |
| switch | 7, 8 dust | 7, 8, 9 / 10, 11 | 611 / 613 | 3.4–6.9 m | −1.68 … +1.42 | 0.04–0.06 | — |
| switch | 9 small cube right | 14 | 505–684 (143) | 274.1 → 1.8 m | +33.1 → −1.45 | 0.49 × 0.45 × 0.40 | box_right_5 |
| tunnels | 1 small cube left | 18 | 4–60 (35) | 83.0 → 1.2 m | −0.32 → +1.55 | 0.45 × 0.44 × 0.34 | **missing** |
| tunnels | 2 dust | 3, 4, 5 | 70 | 4.3–5.5 m | −1.57 … +1.46 | 0.04–0.05 | — |
| tunnels | 3 dust | 6, 7, 8, 9 | 166–167 | 4.0–7.2 m | −1.35 … +1.50 | 0.04–0.05 | — |
| tunnels | 4 dust | 10, 11, 12, 13 | 195 | 3.8–6.3 m | −1.59 … +1.64 | 0.04–0.05 | — |
| tunnels | 5 small cube right | 19 | 166–289 (103) | 219.3 → 0.7 m | +29.2 → −1.37 | 0.44 × 0.49 × 0.42 | box_right_1 |
| tunnels | 6 big cube 2 × 2 × 2 m | 0 | 2–444 (167) | **736.7** → 0.7 m | −54.1 → −0.54 | 2.0 × 2.0 × 2.0 (axis-aligned 2.0–2.6) | panel_2 |
| tunnels | 7 dust | 15, 16 | 446 | 4.2, 4.7 m | −1.41, +1.53 | 0.05 | — |
| tunnels | 8 beam across the rails | 1 | 351–489 (50) | 246.8 → 2.9 m | −30.9 → +0.04 | 0.19 × 2.25 × 0.14, 0.78–0.92 m below the sensor | flat_crossrail_3 |
| tunnels | 9 small cube left | 20 | 446–495 (50) | 90.1 → 1.6 m | +0.46 → +1.51 | 0.51 × 0.51 × 0.40 | box_left_4 |

Notes:

* Large lateral values at first sight (switch, tunnels) are the track curving. The objects end at
  ±0.3–1.5 m from the sensor axis when the train reaches them.
* **Platform dust item 2 ("dust right") is marked on the left** (+1.40, +1.77). Every other left/right
  in the list agrees with `+x = left` (all six cubes). The table records it as found; it is not a
  question worth the organizers' time.
* The person drifts sideways relative to the sensor (+0.18 → −1.06 m over 335 m). The cubes drift
  −0.24 and −0.68 m over similar spans, so how much of this is the person moving and how much is the
  track is **not separated**. In the last 3.2 s (frames 353–385) the train stands still (near face within
  5 cm) and the person moves 3 cm sideways. These bags therefore do not show the "chaotic" motion the
  organizers announced; that still needs our own probe set (M1, [`../../BACKLOG.md`](../../BACKLOG.md) §9f).
* The train speed from the marker distances is about 15.6 m/s, braking to 0 (platform). Switch is about
  0.6 m/s rising to 13 m/s, and tunnels 14–19 m/s. These speeds are plausible for the scenes. The marker
  positions step unevenly: 1 m, 1 m, 3 m, ..., averaging the speed.

## How it was checked

| check | method | rows / frames | result |
|---|---|---|---|
| archive integrity | SHA-256 on download | 1 | matches the listing |
| clouds identical to 16.10 | `judge_runner.py` of the sealed 1.1.0 checkout `3b7d7aa` (worktree, native kernels built with `scripts/build_native.sh`) on each marked bag, compared field by field with the committed `v110_synthetic_*.jsonl` (`../synthetic_labels_2026-10-17/runs/`) by [`compare_runs.py`](scripts/compare_runs.py) | 386 + 736 + 545 | identical except timing. Health `level` differs in 10 / 39 / 52 frames, only through "latency p95" messages (wall clock) |
| positive control for the comparison | the same replay vs the committed **1.0.0** runs | 3 bags | differences found: `clear`/`monitored` in 8 / 139–179 / 88–99 frames (1.0.0's range rules differ) |
| marker encoding | every marker of every message, [`read_markers.py`](scripts/read_markers.py) (pose applied to the 24 points) | 9,650 + 11,040 + 11,445 markers | as in "Result" 2. Marker stamp = cloud stamp in 386/736/545 messages |
| pose decoding is right | points inside each box, [`marker_frames.py`](scripts/marker_frames.py), pictures | 3,893 boxes; [`pictures/`](pictures/) | every box holds points. The person's parts sit on its points at 15.5 m ([`platform_0300.png`](pictures/platform_0300.png)). Without the pose all boxes sat at the origin (first attempt, fixed) |
| id reuse | segments split on a height change > 0.15 m or a jump > 10 m per elapsed frame, [`marker_objects.py`](scripts/marker_objects.py) | 47 ids | 47 segments: no reuse |
| markers ↔ returns | [`marker_visibility.py`](scripts/marker_visibility.py): points in published boxes, and in boxes interpolated over missing frames | 3,893 / 1,246 | 0 published boxes empty; 1,214 interpolated boxes empty |
| dust is transient | the same script: points within 0.1 m of each dust box in the 6 frames before and after | 30 boxes | 28 boxes: nothing nearby before or after. 2 platform boxes (ids 1, 7) are next to platform structure |
| order vs `obstacles.md` | objects ordered by last marked frame, by hand against the list | 24 items | 24 / 24 (one left/right mismatch, item 2 of platform) |
| N5 vs markers | [`compare_n5.py`](scripts/compare_n5.py): same frame, near face within max(2 m, 2 %), lateral within 1 m | 1,684 N5 rows | 1,672 match; 12 unmatched sparse rows listed; 1 object missing in N5 |
| 1.1.0 STOPs vs markers | [`stops_vs_markers.py`](scripts/stops_vs_markers.py): near face within max(3 m, 3 %), lateral within 1.5 m | 455 STOP detections | 438 on marked objects; the 17 others looked at in [`pictures/`](pictures/) (blue = detections) |
| physical plausibility | sizes and speeds | all objects | cubes 0.35–0.56 m, person 1.73 m, big cube 2.0 m, beam 2.25 m, cable 2.36 m; speeds ≤ 19.1 m/s |

**Not checked / limits.** The clouds were compared through the detector's output (rounded to 2 decimals) and
point counts, not byte for byte: the unmarked bags of 16.10 were deleted for disk space. Switch frame 416 is
attributed to the cable only by position. The left/right of the dust bursts is as marked; what "dust left" means
to the organizers is unknown. The markers say nothing about the gauge: whether a marked object is inside the train's
gauge (now the organizers' definition of an obstacle) is still measured by us. No 1.2.0 or candidate runs are here.
P4 re-scores 1.2.0 and the agents' branches against the markers.

## What it changes

| for | change | owner |
|---|---|---|
| N5 labels | the markers become the reference for these bags; add the missing tunnels cube (id 18, frames 4–60); drop or mark the 12 unmatched sparse rows; no other change needed | P4 |
| scoring | score against marker objects inside the 2.5–250 m crop; frames beyond 250 m (up to 737 m) are not misses; a missing marker is not a negative (tunnels 460) | P4 |
| dust (N3, dust agent) | the organizers' dust is 1–14 points per 4–6 cm box, for one to two frames, 3–7 m ahead. 1.1.0 already ignores it: no STOP or CAUTION from it in 13 frames. It is a **non-regression set** for the dust guard, not the failure case. N3's generator dust (volumetric) is still the robustness test | dust agent, P4 |
| false STOPs on these bags | the 12 frames (switch 7–14, tunnels 147–149, 367) are background structures, not dust: F1's subject | F1 agent |
| far range (N7) | the synthetic objects have returns to 737 m, so they are no evidence for what a real sensor sees beyond 250 m. Use the Falcon recording for N7 | Falcon agent |

## Reproduce

```
S=<scratch>; R=<1.1.0 worktree at 3b7d7aa, scripts/build_native.sh run>; E=docs/evidence/synth_markers_2026-10-19/scripts
python scripts/unpack_dataset.py new_synth_data_with_markers.zst --out <raw> --only synthetic_<bag>_cloud_with_markers
python -I $E/read_markers.py <raw>/synthetic_<bag>_cloud_with_markers $S/<bag>       # markers + cloud hashes
python -I $E/marker_objects.py $S/<bag>                                              # objects, speed
RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
  python $R/docs/evidence/judgement_2026-10-13/scripts/judge_runner.py --bag <raw>/synthetic_<bag>_cloud_with_markers --out $S/v110_marked_<bag>
python -I $E/compare_runs.py $S/v110_marked_<bag>.jsonl <v110_synthetic_<bag>.jsonl from ../synthetic_labels_2026-10-17/runs>
python -I $E/marker_visibility.py <raw>/... $S/<bag>.jsonl $S/<bag>_visibility.json
python -I $E/compare_n5.py $S/<bag>_objects.json ../n5_labels_2026-10-17/labels_synthetic_<bag>.json $S/<bag>_vs_n5.json
python -I $E/stops_vs_markers.py $S/v110_marked_<bag>.jsonl $S/<bag>.jsonl $S/<bag>_stops_v110.json
python -I $E/marker_frames.py <raw>/... $S/<bag>.jsonl $S/png/<bag> --frames 460 --window 45,70 --lat 4 --dets $S/v110_marked_<bag>.jsonl
```

Python 3.12, numpy 1.26.4, `rosbags` (Humble typestore), matplotlib 3.11. One bag at a time; each raw bag (3.1 /
5.9 / 4.4 GB) was deleted after use.

## Files

* [`out/markers_<bag>.jsonl.xz`](out/): every marker message, decoded (boxes in the sensor frame). `out/clouds_<bag>.jsonl.xz`:
  stamp, size and SHA-256 of every cloud message (CDR) of the marked bags.
* `out/<bag>_objects.{json,txt}`: segments, objects with per-frame tracks, speed. `out/<bag>_visibility.json`.
  `out/<bag>_vs_n5.{json,txt}`. `out/<bag>_stops_v110.{json,txt}`. `out/identity_<bag>.txt` (comparison, control,
  replay meta and SHA-256 of the replay output). `out/frames_*_boxes.json`: points per box in the pictured frames.
* [`pictures/`](pictures/): red = marker boxes, blue = detections of the 1.1.0 replay (where drawn).
* [`meta/`](meta/): the bags' `metadata.yaml`.
* [`SHA256SUMS`](SHA256SUMS).
