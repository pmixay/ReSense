# Labels and scores for the organizers' new synthetic recordings (B1 / BACKLOG N5) — 17.10

> **Development data (observation only).** These are not G3, not a J1 result and not a release
> score. No detector code was changed. Owner: P4.

The organizers' `new_synth_data.zst` (16.10) holds three bags: `synthetic_platform` (386 frames),
`synthetic_switch` (736) and `synthetic_tunnels` (545). Objects are inserted into real Pandar128
scans, and the inserted points carry intensity exactly 1. There is no ground truth and no stated
intent ([extended data README](../extended_data_2026-10-17/README.md)).

## Summary

| | result |
|---|---|
| exact labels | `synthetic_platform` frames **0–314** only (their real scans are Set O frames 1195–1509) |
| no exact labels yet | platform 315–385, all of `switch` and `tunnels`: their real scans are not in any organizer recording we hold (see [Source search](#source-search)) |
| intensity-1 marker | **not usable as truth**: finds 57 % of the inserted points and makes about 12 false objects per frame |
| inserted objects | **not static in the world**: they approach the train about 12 m/s faster than the train moves, in uneven 0.8–3 m steps per frame |
| 1.1.0 vs 707ea9c | identical decisions on all 1,667 frames of the three bags, so identical scores |
| platform 0–314 | person (obj03): first STOP **44.0 m**, visible from 249.5 m; box at the gauge edge (obj01): first STOP 86.8 m; box outside the gauge (obj02): never STOP (correct); no unmatched STOP |

## How the labels are made

`scripts/label_marked_objects.py` (exact mode only):

1. **Inserted points** = the points of a synthetic frame whose float32 xyz is absent from the real
   scan it was made from (`--reference`, here Set O, `--ref-offset 1195`). Frame stamps must match.
2. Each frame is run through the judge's node replica (`judge_runner.NodeReplica`, 1.1.0 checkout).
   This puts the points in the detector's mount-calibrated vehicle frame, and lateral and height
   are measured from the detector's own track axis, as in `labels/cloud_with_fake_obj.json`.
3. Points are grouped (DBSCAN 1 m) and linked into tracks over frames.
4. **Intent** (`in_gauge`) is **measured**, because the organizers gave none: an object counts as
   inside when most of its plausible rows nearer than 60 m have points in the strict envelope
   (half width 1.05 m). The flag is constant per object, as in Set O.
5. Frames without a reference get no label row (`_meta.unlabelled_frames`). Scoring uses only the
   labelled frames.

Files: [labels_synthetic_platform_0-314.json](labels_synthetic_platform_0-314.json) (same layout as
the Set O label file).

## Checks of the labels (not taken on trust)

`scripts/check_synth_labels.py` re-reads the raw sensor-frame points rather than trusting the
labeller's transforms ([check_platform_0-314.json](check_platform_0-314.json)):

| check | result |
|---|---|
| exactly-new points that do **not** have intensity 1 | 31 of 119,377. These are real near-field points (4–5 m, frames 21–36) that differ from Set O; none is in a label row |
| exactly-new points that end up in a label row | 119,346 of 119,377 (the same 31 dropped) |
| label distance vs raw sensor-forward distance (median / max) | obj01 0.14 / 0.45 m, obj02 0.16 / 0.56 m, obj03 0.04 / 0.24 m (mount calibration and object depth) |
| size near (< 60 m), p10–p90, L × W × H | obj01 0.23–0.39 × 0.48–0.52 × 0.32–0.44 m (box); obj02 0.16–0.46 × 0.37–0.54 × 0.32–0.46 m (box); obj03 0.05–0.22 × 0.55–0.60 × 1.59–1.70 m (person) |
| inner edge from the track axis near (median / min) vs half width 1.05 m | obj01 **0.96** / 0.68 m: inside, but only by 9 cm. obj02 1.41 / 1.27 m: outside. obj03 0.45 / 0.14 m: inside |
| frame-to-frame jumps | all three objects jump by the same 2–3 m on the same frames, while the timestamps are regular (0.1 s, no gaps): see the next section |
| pictures | [pictures/](pictures/), frames 100, 220, 300: grey = all points, red = exactly-new points, label numbers in the title. They show a box beside the track, a 1.6 m column on the track and a box at the right rail |

**obj01 is marginal.** Its inner edge is 0.96 m from the axis estimated by the detector, which is
within the axis and calibration uncertainty of the 1.05 m edge. If the organizers meant it as a
box beside the rail, its 38 STOP rows would be false alarms, not hits. Its results are reported,
but its intent should be confirmed with the organizers.

## The inserted objects move

ICP odometry on the real scans under platform frames 57–100 (judge's `icp_odometry.py`, fitness
0.90–0.97, [icp_setO_1252-1295.json](icp_setO_1252-1295.json)) shows the train moving 0.0–0.6 m per
frame (mean 0.22 m). Over the same frames the inserted objects come closer by:

| object | approach per frame, mean (min–max) | train per frame, mean | object's own speed toward the train |
|---|---|---|---|
| obj01 | 1.47 (0.83–3.05) m | 0.22 m | ≈ 12.5 m/s |
| obj02 | 1.51 (0.83–3.02) m | 0.27 m | ≈ 12.4 m/s |
| obj03 | 1.47 (0.84–3.04) m | 0.22 m | ≈ 12.5 m/s |

The steps are the same for all three objects, frame by frame, to within 5 cm. A static obstacle
would close in exactly as fast as the train moves. These objects instead slide over the ground
toward the train, in jerky steps of up to 3 m per 0.1 s. A detector that checks an object's motion
against the scene, or requires stable tracks, sees a fast, jerky moving object, not a static one.
This is relevant to the late person STOP (A5) and is a question for the organizers.

## Scores (platform frames 0–314, the jury's `score_objects.py`)

Both versions give byte-identical score files ([v110](score_platform_0-314_v110.json),
[v100](score_platform_0-314_v100.json)).

| object | intent (measured) | visible rows | first visible | first STOP | STOP rows | held from | STOP rows per range bin (0–30 / 30–60 / 60–100 / 100–150 / 150–200 / 200–300 m) |
|---|---|---:|---:|---:|---:|---:|---|
| obj01 box at the gauge edge | STOP (marginal) | 170 | 242.0 m | **86.8 m** | 38 | – | 17/27, 8/24, 13/29, 0/34, 0/34, 0/22 |
| obj02 box outside | no STOP | 189 | 243.0 m | never | 0 | – | 0 in every bin (CAUTION on 30 rows) |
| obj03 person | STOP | 258 | 249.5 m | **44.0 m** | 76 | 48.5 m | 50/50, 26/50, 0/45, 0/43, 0/36, 0/34 |

There are 0 unmatched STOP frames. Decisions on the 315 frames: GO 66, CAUTION 135, STOP 114.

## Detector decisions without labels (all frames)

| bag | frames | GO / CAUTION / STOP | STOP episodes (frames: nearest detection at the first frame) |
|---|---:|---|---|
| synthetic_platform | 386 | 66 / 135 / 185 | 106–118: 86.8 m; 142–166: 38.8 m; 239–385: 44.0 m |
| synthetic_switch | 736 | 300 / 294 / 142 | 7–14: 147.1 m; 145–155: 110.6 m; 318–352: 51.4 m; 374–416: 69.1 m; 540–545: 23.5 m; 616–659: 104.0 m |
| synthetic_tunnels | 545 | 196 / 223 / 126 | 147–149: 70.1 m; 259–288: 55.0 m; 367: 131.5 m; 391–444: 96.8 m; 452–489: 70.4 m |

These are the same for 1.1.0 and 707ea9c. Whether these STOPs are hits or false alarms is unknown
until switch and tunnels have exact labels. All runs: [runs/detector_runs.tar.xz](runs/detector_runs.tar.xz)
(`probe.py` nominal, Linux runtime of the P4 protocol, `OPENBLAS_CORETYPE=Haswell`; SHA-256 in
`runs/SHA256SUMS`).

## The intensity-1 marker is not truth

On 105 platform frames (every 3rd of 0–314) the marker clusters (DBSCAN 0.5 m / 4 points on
intensity-1 points, grown box purity ≥ p) were compared with the exactly-new points
([marker_check.json](marker_check.json), `scripts/eval_marker.py`):

| purity ≥ | inserted points found (of 36,865) | real points taken as inserted | false clusters | true clusters |
|---|---:|---:|---:|---:|
| 0.70 | 23,313 | 13,898 | 2,017 | 166 |
| 0.85 | 21,198 | 6,607 | 1,223 | 156 |
| 0.95 | 14,477 | 5,630 | 1,126 | 143 |

Real returns with intensity exactly 1 are common (about 36,000 per frame mid-recording), and many
dark patches are 100 % intensity 1. Labels built from the marker would contain about 12 false
objects per frame and miss the sparse far objects, so the labeller never uses it.

## Source search

* **Local** (`scripts/find_source_local.py`, [find_source_local.txt](find_source_local.txt)): five
  frames per synthetic bag, 300 real points each, searched in all decoded recordings (Set O and the
  six bags). Sampled platform frames 0, 96, 193 and 289 match Set O 1195, 1291, 1388 and 1484 at 300/300. Platform frame 385, every
  switch frame and every tunnels frame match at most 17/300, which is chance.
* **The 20-minute ride `new_data`** (`scripts/match_source_frames.py`, streamed, never stored):
  all 1,667 synthetic frames, 60 real points each. Part 1 searched 165 of 221 split files
  (8,415 messages) and found **0 matches**; the stream then broke. The remaining splits:
  being searched on 17.10 (resumed with `--skip-members`); this README gets the result.

## Reproduce

```
# decode (707ea9c node decoder), see ../extended_data_2026-10-17/
scripts/run_probe.sh v110 <1.1.0 checkout> synthetic_platform       # and v100 <707ea9c>, other bags
RESENSE_REPO=<1.1.0> PYTHONPATH=<1.1.0>:<1.1.0>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
  python scripts/label_marked_objects.py <cache>/synthetic_platform --out labels.json \
  --reference <cache>/cloud_with_fake_obj --ref-offset 1195 --ref-frames 0:315
python scripts/check_synth_labels.py <cache>/synthetic_platform labels.json \
  --reference <cache>/cloud_with_fake_obj --ref-offset 1195 --out check.json --png-dir pictures --png-frames 100,220,300
python docs/evidence/rejudge_2026-10-16/scripts/score_objects.py <run restricted to frames 0-314>.jsonl labels.json score.json
```
