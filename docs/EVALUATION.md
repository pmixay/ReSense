# Evaluation protocol

What "better" means for ReSense, written down once so that P3 optimises against it, P4
implements it (`resense/metrics.py`, `resense eval`) and the jury's criteria (spec §8) map
onto numbers we actually report. Results go to [`EXPERIMENTS.md`](EXPERIMENTS.md).

## 1. Data sets

| set | source | positives | negatives | use |
|---|---|---|---|---|
| **S** synthetic | `resense inject` on real empty frames of every organizer bag, every 10th frame | person 0.5×1.7 m, box 0.2 / 0.5 / 1.0 m, plank 2×0.25×0.3 m, trolley; one object per frame, uniform 10–250 m along the track | 20 % of objects placed outside the gauge (must **not** alarm) | recall by range, first-detection distance, tuning |
| **E** empty real | the five organizer bags without a known obstacle | none | every frame | false-alarm rates by scene type |
| **R** real obstacles | `doubleT_obstacle` (person at 55–57 m) + the organizers' extended dataset once labelled (`gt.json` via the label tool) | labelled frames | unlabelled frames of the same bags | honest recall, calibration of `inject` |
| **H** hidden | the organizers' control bag on the day | unknown | unknown | nothing is tuned on it; the dry-run script only checks the pipeline runs |

Objects whose rays are fully occluded by real geometry (`n_points == 0` in `gt.json`) are
excluded from recall, and their count is reported.

## 2. Metrics

| metric | definition | reported as |
|---|---|---|
| **recall by range** | matched gauge ground-truth objects / all gauge ground-truth objects, per bin 0–50, 50–100, 100–150, 150–200, 200–300 m; a detection matches if \|Δdistance\| ≤ max(2 m, 3 % of range) + half object length and \|Δlateral\| ≤ 1 m | table per object class and overall |
| **first-detection distance** | for a moving-toward run (real or simulated by decreasing injected range): the largest range at which the object is confirmed | m, per class |
| **false-alarm frame rate** | frames with `obstacle = true` among frames with no gauge ground truth | per bag and per scene type (tunnel / curve / gate / platform / switch) |
| **false alarms per km / per hour** | false-alarm *events* (a new confirmed track id) per travelled distance (from speed, when known) and per hour of bag time | per bag; the headline false-alarm number |
| **advisory rate** | frames with `warning = true` on empty frames | informational; the advisory zone is expected to be noisy near infrastructure |
| **latency** | per frame: decode + detect (status JSON `node.latency_ms`) and decode + detect + publish (`/resense/latency_ms`); offline `timing_ms.total` | mean, p95, max in ms |
| **throughput** | frames processed per second in the ROS node (`/resense/fps`) against the sensor's 10 Hz; dropped frames from stamp gaps (`node.dropped_frames`) | fps, dropped / total |
| **decision latency** | frames from the first frame an object is visible in the corridor to the first `obstacle = true` | frames (3 by construction with `confirm_hits = 3`) |
| **CPU / memory** | `top` per core and RSS of the node on the reference machine | for the i7-9700E comparison |

Match tolerance and bins are the ones implemented in `resense/metrics.py`; change them there
and here together. The 200–300 m bin is kept for completeness: the Pandar128 is instrumented to
200 m at 10 % reflectivity, and only on its horizon channels ([`SENSOR.md`](SENSOR.md) §3), so a
non-reflective object in that bin is not expected to be detectable by any algorithm.

## 3. Procedure

1. **Freeze the config.** One `configs/default.yaml` per evaluation; record its git hash.
2. **Synthetic (S):** `resense inject --bag <bag> --every 10 --out data/synth/<bag>
   --distances 10:250 --kinds person,box,plank` for every empty bag, then `resense eval
   data/synth/<bag> --repeat 3` (the repeat emulates persistence on static frames). Report the
   recall table, first-detection distances and occluded count.
3. **Empty real (E):** `resense run --bag <bag> --out results/<bag>.jsonl` on every frame,
   then count alarm frames, alarm events and advisory frames per bag; classify each false
   alarm event by cause (platform edge, gate frame, overhead fixture, axis error, other) using
   the renders (`--render`).
4. **Real obstacles (R):** same as E on labelled bags with `gt.json`, reporting recall and
   distance error against the labels.
5. **Timing:** `resense bench --bag <bag> --every 5` offline; in ROS, play a bag at rate 1.0
   for its full length and read the node's stats line (fps, latency mean / p95 / max, dropped
   frames). Run on the closest available machine to the bench (8 cores, no GPU) and state which.
6. **Regression:** the three numbers that must not get worse between versions are recall
   50–100 m on S, false-alarm frames on E (all bags), and p95 latency. Each PR that touches
   `resense/` re-runs S and E on the cached frames (`scripts/cache_frames.py`) and adds a row
   to the version table in EXPERIMENTS.md.

## 4. Targets (from PLAN.md sprints)

| milestone | recall person | recall box 0.5 m | false-alarm frames on E | p95 latency |
|---|---|---|---|---|
| v0 (day 1, measured) | 100 % ≤ 50 m, 50 % 50–100 m, 0 beyond | box 0.5 m at 54–56 m | 67 / 231 frames (49 in the platform-and-switch bag) | 47–125 ms |
| Sprint 1 | ≥ 90 % ≤ 100 m | ≥ 80 % ≤ 80 m | ≤ 1 per 100 frames outside platforms | ≤ 100 ms |
| Sprint 2 (accumulation) | confirmed at ≥ 150 m | confirmed at ≥ 100 m | ≤ 1 per 100 frames including platforms | ≤ 100 ms |
