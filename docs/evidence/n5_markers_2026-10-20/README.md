# N5 labels and the organizers' markers: supplement and per-object scoring (20.10)

> **Purpose:** P4's part of [`synth_markers_2026-10-19`](../synth_markers_2026-10-19/README.md) "What it changes": add
> the object N5 missed, flag the N5 rows that match no marker, and score the committed runs per marked object,
> including K2 variant B. **Owner:** P4 · **Status:** done from committed files; the bags themselves were not
> reachable from this container · **Detector code:** not touched (committed run records re-read).

## Result in short

1. **Supplement, not an edit.** [`labels_n5_marker_supplement.json`](labels_n5_marker_supplement.json) adds the
   `synthetic_tunnels` small cube left (marker id 18, `obstacles.md` tunnels item 1) as `box_left_0`, 34 rows
   (frames 4–59, near face 83.0 → 3.8 m), and lists the **12 N5 rows that match no marker object** (switch 328, 330,
   510, 521, 523–529; tunnels 346). The N5 files of 17.10 are unchanged.
2. **Per marked object, K2 variant B loses STOPs on one object only: the tunnels small cube right (marker id 19).**
   STOP frames 29 → 13 (2.5–250 m), first STOP **55.0 → 27.6 m**. Every other object keeps or gains STOP frames.
3. **That cube is inside the gauge**, contrary to the integration note "probably just outside the 2.1 m gauge". The
   cube is static, so its offset from the true track axis is constant. Measured from 1.1.0's axis it is 0.96 m (centre,
   median) right of the axis both inside the rails' range (≤ 30 m, 15 frames, where the axis comes from the rails) and
   at 30–55 m (15 frames). K2's own axis agrees inside the rails' range (0.98 m, 14 frames). Its inner face is
   therefore about 0.71 m from the axis, about 0.3 m inside the 1.05 m half-width.
4. **K2 loses it inside its trusted range, not beyond it.** At 30–55 m (frames 259–273) variant B's monitored range
   is 67–87 m, and the cube touches B's strict envelope in 9 of the 15 frames (the clear distance is capped at the
   cube), never long enough to be confirmed. So B's joint axis sits about 0.3 m farther from the cube than the true
   axis there (inferred from the cap: the trace has no axis at the cube for B). K2 v5c acts only beyond the reach cap
   and does not change this.

## Per marked object (A = 1.1.0 committed runs, B = K2 variant B `c9e8daa`)

[`scripts/per_object.py`](scripts/per_object.py), full output in [`out/per_object_v110_vs_k2B.txt`](out/per_object_v110_vs_k2B.txt).
A detection matches a marker box in the same frame by the rule of
[`stops_vs_markers.py`](../synth_markers_2026-10-19/scripts/stops_vs_markers.py) (near face within max(3 m, 3 %),
vehicle lateral `c[1]` within 1.5 m; the vehicle frame does not depend on the track axis, so K2 cannot shift it).
Only frames with the box's near face at 2.5–250 m count; dust boxes are left out.

| bag | object (`obstacles.md`) | marker id | frames | STOP frames A → B | first STOP A → B (m) |
|---|---|---|---:|---|---|
| platform | person (8 parts) | 15–22 | 198–329 | 147 → 147 (each part) | 44.0 → 44.0 |
| platform | small cube right | 23 | 175 | 38 → 40 | 86.8 → 89.5 |
| platform | small cube left | 24 | 188 | 0 → 0 (28 / 27 warnings) | — |
| switch | small cube on the left rail | 0 | 102 | 35 → 37 | 51.4 → 54.0 |
| switch | hanging inclined cable | 1 | 139 | 42 → 42 | 69.1 → 69.1 |
| switch | small cube right (first) | 12 | 255 | 11 → 21 | 110.6 → 110.6 |
| switch | small cube left | 13 | 51 | 4 → 9 | 23.5 → 26.5 |
| switch | small cube right (last) | 14 | 140 | 41 → 41 | 104.0 → 104.0 |
| tunnels | big cube 2 × 2 × 2 m | 0 | 102 | 52 → 55 | 96.8 → 100.4 |
| tunnels | beam across the rails | 1 | 50 | 37 → 37 | 70.4 → 70.4 |
| tunnels | small cube left (first; missing in N5) | 18 | 34 | 0 → 0 (no warning either) | — |
| tunnels | **small cube right** | **19** | 101 | **29 → 13** (lost: 259–273, 279) | **55.0 → 27.6** |
| tunnels | small cube left (last) | 20 | 49 | 0 → 0 (6 / 6 warnings) | — |

The integration README counts this cube "30 → 14": the same frames plus frame 288 (near face 2.2 m, outside the
2.5 m crop used here). The three left cubes that are never STOPped (platform 24, tunnels 18 and 20) end with their inner face
1.20–1.33 m left of the sensor axis, so they are probably outside the gauge; not checked against the rails.

**Is 1.2.0 the same as A here?** The integration states that `4cf8e27` gives every decision and detection of 1.1.0
on these bags. Its per-frame records are not committed; its STOP summaries
(`integration_2026-10-19/runs/marked_bags_4cf8e27/final_<bag>_stops.txt`) are byte-identical to 1.1.0's
(`synth_markers_2026-10-19/out/<bag>_stops_v110.txt`), 3 of 3 bags. So column A stands for 1.2.0 to that extent.

## The lost cube, frame by frame

[`scripts/trace_object.py`](scripts/trace_object.py) → [`out/trace_tunnels_cube19.txt`](out/trace_tunnels_cube19.txt)
(marker box; per run the decision, clear distance, monitored range, and the detections and warnings at the box):

| frames | near face | A (1.1.0) | B (K2 variant B) |
|---|---|---|---|
| 257–258 | 59.4–57.3 m | candidate (clear capped at the cube) | candidate in 257 |
| 259–273 | 55.0–30.2 m | STOP on the cube every frame; monitored 136–148 m (70 m in 272) | no detection or warning at the cube; clear capped at it in 262, 263, 265, 267–270, 272, 273; monitored **67–87 m** |
| 274–288 | 27.6–2.2 m | STOP | STOP from 274 (27.6 m) except 279 (a warning at 19.2 m) |

Why the cube is inside the gauge: the marker box gives the cube's centre and inner face in the sensor frame, and a
matched detection gives the axis position at the cube (`c[1] − lat`). The cube's centre is then 0.79–1.08 m right of
1.1.0's axis at 30–55 m and 0.86–1.13 m inside the rails' range (medians both −0.96 m); its inner face is 0.55–0.88 m
from the axis. B's axis inside the rails' range gives the same (median −0.98 m). A static object cannot change its
offset from the track, so 1.1.0's axis at 30–55 m is right to within about 0.1 m, and the cube's inner 0.3 m is inside
the 1.05 m half-width (the core half-width at 50 m, 0.97 m, still leaves 0.26 m). N5's own note on this object
("near raw shape lies by a rail") agrees: the right rail is 0.80 m from the axis.

## How it was checked

| check | method | result |
|---|---|---|
| supplement rows are the marker | each of the 34 rows against `marker_objects.py`'s own track of id 18 (`tunnels_objects.json`, separate code) | 34 of 34 equal within 0.01 m in distance and lateral |
| counts agree with the intake | rows in 2.5–250 m and unmatched N5 rows against the intake README | 34 (README: 34) and 12 (README: 12, the same frames) |
| the matching (positive control) | the same matching rule, all frames, on 1.1.0: STOP detections matched to a non-dust box, against the intake's `stops_vs_markers.py` totals | 185 / 185, 133 / 142, 120 / 128: equal to the intake in all three bags; the tunnels cube agrees with the integration's count once frame 288 is included |
| the lost frames are real | trace printed for every frame 257–289 in both runs | as tabulated; B's clear distance equals the cube's distance in 9 of the 15 frames |
| plausibility | marker sizes and speeds | cube 0.44 × 0.49 × 0.42 m; over frames 259–273 the near face steps unevenly (0.9–2.7 m per frame, as the intake noted), 1.8 m on average: about 18 m/s at 10 Hz, inside the intake's 14–19 m/s for this bag |

**Not checked / limits.** The track axis in B at 30–55 m is not in the records, so "about 0.3 m farther from the
cube" is inferred from the clear-distance cap (one strict voxel or none). Why the joint fit bends there needs the
cloud (the tunnel walls at 30–80 m in frames 255–275); this container cannot reach the bags. Left cubes' gauge
relation is not checked against the rails.

## Reproduce

```
E=docs/evidence; S=$E/n5_markers_2026-10-20/scripts
tar -xJf $E/synthetic_labels_2026-10-17/runs/detector_runs.tar.xz v110_synthetic_<bag>.jsonl
xz -dc $E/integration_2026-10-19/runs/marked_bags_k2B/final_<bag>.jsonl.xz > k2B_<bag>.jsonl
xz -dc $E/synth_markers_2026-10-19/out/markers_<bag>.jsonl.xz > markers_<bag>.jsonl
python -I $S/per_object.py markers_<bag>.jsonl v110_synthetic_<bag>.jsonl k2B_<bag>.jsonl
python -I $S/trace_object.py markers_tunnels.jsonl v110_synthetic_tunnels.jsonl k2B_tunnels.jsonl 19 60
python -I $S/n5_supplement.py markers_tunnels.jsonl $E/synth_markers_2026-10-19/out $E/n5_markers_2026-10-20/labels_n5_marker_supplement.json
```
