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

Implemented in `resense/metrics.py` (`Evaluation.summary()` keys in brackets) and printed by
`resense eval` and `resense summarize results.jsonl [--speed-mps V] [--gt gt.json]`;
`resense summarize --compare before.jsonl after.jsonl` prints the before/after table of two
runs (frames, alarm frames, events, advisory frames, first alarm frame, alarm distance range,
latency, FP frames / events, recall, frames merged) with a delta column.

| metric | definition | reported as |
|---|---|---|
| **recall by range** | matched gauge ground-truth objects / all gauge ground-truth objects, per bin 0–50, 50–100, 100–150, 150–200, 200–300 m; a detection matches if \|Δdistance\| ≤ max(2 m, 3 % of range) + half object length and \|Δlateral\| ≤ 1 m | table per bin [`recall_by_range`, `per_bin_counts`], per object class [`recall_by_class`, `per_class_counts`; class = the `name` of the `inject` catalogue, else `kind`] and overall [`recall`] |
| **recall by class and range** | the recall-by-range table split per object class [`per_class_bin_counts`: class → bin → [matched, total]]; the per-kind table of set S | counts per cell (the cells of a 26-frame set hold 1–4 objects: quote the counts, not only the ratio) |
| **first-detection distance** | for a moving-toward run (real, or `inject --sequence N --speed V`): the largest range at which the object is confirmed and matched | m, per ground-truth label [`first_detection_distance`] |
| **distance / lateral error** | over matched detections: mean and max of \|Δdistance\|, the signed mean (bias, + = reported farther than the label), mean \|Δlateral\| [`distance_error_mean_abs`, `distance_error_max_abs`, `distance_error_bias`, `lateral_error_mean_abs`] | m; on the real person of `doubleT_obstacle` 0.00–0.07 m mean (DATASET.md "Real labels") |
| **first alarm frame** | index of the first frame with `obstacle = true` [`first_alarm_frame`] | frame; on `doubleT_obstacle` it must stay 9 (the person enters the gauge at frame 2, `confirm_hits = 3`) |
| **ego-speed source / frames merged** | how the accumulation actually ran: frames per `ego_speed_source` value (`given` / `estimated` / `none`) and the mean `n_accumulated` [`ego_speed_sources`, `n_accumulated_mean`] | counts; `given` when the node receives a valid speed; without one, shipped defaults report `none` (`accumulation.estimate_speed: false`); `estimated` requires explicitly opting in |
| **false-alarm frames** | frames with `obstacle = true` among frames with no gauge ground truth [`fp_frames`, `fp_frame_rate`]; every frame with `obstacle = true` regardless of labels is an *alarm frame* [`alarm_frames`] | per bag and per scene type (tunnel / curve / gate / platform / switch) |
| **false-alarm events** | distinct confirmed gauge track ids (`detections[].id`) that were never matched to a ground-truth object [`fp_events`]; distinct ids of all alarms [`alarm_events`]. One object that stays in the corridor for 50 frames is one event | **the headline false-alarm number**, per bag |
| **false alarms per hour / per km** | `fp_events` per hour of bag time (span of the `stamp` field [`bag_time_s`]) [`fp_events_per_hour`] and per km travelled [`fp_events_per_km`] when a speed is known: `--speed-mps V` (constant) or a per-frame `ego_speed_mps` key in the JSON, integrated over the stamp gaps [`distance_km`] | per bag; `null` when no speed is known |
| **advisory rate** | frames with `warning = true` [`advisory_frames`, `advisory_frame_rate` = share of all evaluated frames] | informational; the advisory zone is expected to be noisy near infrastructure |
| **alarm distance** | min / max of `nearest_distance` over alarm frames [`alarm_distance_min`, `alarm_distance_max`] | m; the max on `doubleT_obstacle` is the person (56.6 m), the min includes false alarms near the train, so quote the max or per-event distances |
| **latency** | per frame: decode + detect (status JSON `node.latency_ms`) and decode + detect + publish (`/resense/latency_ms`); offline `timing_ms.total` [`latency_ms_mean`, `latency_ms_p95`, `latency_ms_max`] | mean, p95, max in ms |
| **throughput** | frames processed per second in the ROS node (`/resense/fps`) against the sensor's 10 Hz; dropped frames from stamp gaps (`node.dropped_frames`) | fps, dropped / total (node stats line, `scripts/check_dry_run.py`) |
| **decision latency** | frames from the first frame an object is visible in the corridor to the first `obstacle = true` | frames (3 by construction with `confirm_hits = 3`) |
| **subsampling caveat** | the stride between consecutive `frame` indices [`frame_stride`]; with every N-th frame the `confirm_hits` consecutive hits are `N × frame_dt` s apart, so a candidate must persist `confirm_hits × N × frame_dt` s (1.5 s at every 5th, 3 s at every 10th) instead of 0.3 s at 10 Hz: **subsampled alarm and false-alarm counts understate the full-rate values** [`stride_caveat`] | printed next to every number measured on subsampled frames; headline numbers are measured at every frame |
| **CPU / memory** | `top` per core and RSS of the node on the reference machine | for the i7-9700E comparison |

Objects fully occluded by real geometry (`n_points == 0` in `gt.json`) are excluded from
recall and counted separately (`occluded_gt_skipped`). Match tolerance and bins are the ones
implemented in `resense/metrics.py`; change them there and here together. The 200–300 m bin
is kept for completeness: the Pandar128 is instrumented to 200 m at 10 % reflectivity, and
only on its horizon channels ([`SENSOR.md`](SENSOR.md) §3), so a non-reflective object in
that bin is not expected to be detectable by any algorithm.

## 3. Procedure

**Set F independent placement (synthetic positives).** `scripts/far_range_eval.py` defaults
to `--placement-mode legacy`, which uses the detector-derived per-frame far axis and vault
drift; those results are not an independent test of curve or gauge-edge generalisation.
For `--placement-mode independent`, provide a separately surveyed physical reference in
vehicle coordinates: `--axis-center`, `--axis-yaw-deg`, `--axis-curvature`, `--rail-z0`,
`--rail-grade`. The tool never reads background points to set this reference or the object's
height: bed placement is 0.25 m below the supplied rail profile (an assumption), rail
placement at rail height. `--lateral-offset` and `--yaw-perturb-deg` apply fixed, explicit
perturbations to each sequence; `--lateral` supplies the nominal sampled lateral interval.
Matched detections are compared in vehicle-frame Y instead of assuming the detector's axis
is ground truth. Record reference survey provenance, cache and config hashes, visible-return
denominators and seeds alongside every report. A fixed extrapolation may miss the real curve
or grade, especially beyond the sensor's sightline; this protocol is a sensitivity test, not
a measured real-positive generalisation score. The script's `recall_by_bin` counts visible
synthetic object-frames only (`n > 0`), and its `false_detections` counts unmatched detections
per frame, not distinct false-alarm events from `resense.metrics.Evaluation`.
The fixed reference is held in vehicle coordinates for the entire approach: on a moving
curve it is an extrapolation, not a surveyed world-fixed trajectory. Check its physical
validity over each sequence before interpreting range or edge results.

1. **Freeze the config.** One `configs/default.yaml` per evaluation; record the commit and
   `sha256sum configs/default.yaml`. For a same-machine A/B against v0.3 use a copy of the
   file with `accumulation.enabled: false`, `accumulation.estimate_speed: false`,
   `track.floor_verify_enabled: false`, `cluster.retro_intensity: 0` (`--config`): v0.4 then
   reproduces v0.3 bit for bit (verified on the six bags on 21.09).
2. **Synthetic on real frames (S)** — the sets of 21.09 (commit f4e311f; the seeds are fixed,
   so the same frames come out of `/data/cache` on any machine; raw summaries and these
   commands in [`experiments_v0.4_synthetic_on_real.json`](experiments_v0.4_synthetic_on_real.json)):

   ```bash
   # static sets: every 10th frame of three empty bags, one catalogue object per frame, 20 % negatives
   for bag in roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT; do
     resense inject --npy /data/cache/$bag --every 10 --out data/S_$bag \
         --kinds person,box0.5,box1.0,plank,trolley --distances 10:250 --negative-fraction 0.2 --seed 1
     resense eval data/S_$bag --repeat 3 --text          # 3 repeats emulate persistence; no speed given
   done
   # approach sequences on roundT_doubleT: 8 steps of 1.5 m (15 m/s) per background, one kind per set, seeds 1-3
   for kind in person box0.5 box1.0 plank trolley; do for seed in 1 2 3; do
     resense inject --npy /data/cache/roundT_doubleT --every 10 --out data/SEQ_${kind}_s$seed --kinds $kind \
         --distances 10:250 --negative-fraction 0.2 --sequence 8 --speed 15 --seed $seed
     resense eval data/SEQ_${kind}_s$seed --repeat 1 --text                 # the rows' speed_mps is given to the detector
     resense eval data/SEQ_${kind}_s$seed --repeat 1 --no-gt-speed --text   # estimator / single-frame path
   done; done
   ```

   `eval` gives the detector the `speed_mps` of `inject --sequence` rows (`ego_speed_source:
   given`, as the ROS node with `ego_speed_mps` / odometry); `--ego-speed V` forces a constant
   on any source, `--no-gt-speed` withholds it; static sets (`speed_mps: 0`) get nothing and
    the estimator is off by default, as in `resense run` (enable
    `accumulation.estimate_speed` explicitly to evaluate it). Report recall by range per kind
   (`per_class_bin_counts`), first-detection distances and the occluded count. Two caveats:
   the per-frame recall of an 8-step sequence is capped at 6/8 (the first two steps cannot be
   confirmed with `confirm_hits = 3`, and an object that starts beyond 150 m approaches only
   10.5 m within its sequence), so sequences are read by their first-detection distances and
   the static sets give the per-range recall; and the false-alarm counts of a static set are
   **not** meaningful: every 10th frame of a moving bag is a new scene 1 s apart and the 3
   repeats confirm any structure that sits in the corridor.
3. **Empty real (E):** `resense run --npy /data/cache/<bag> --out results/<bag>.jsonl --quiet`
   on every frame (`--bag` on the bag itself), then `resense summarize results/<bag>.jsonl`
   per bag (alarm frames, events, advisory frames, first alarm frame, distance range, latency)
   and `resense summarize --compare before.jsonl after.jsonl` for the before/after table of a
   change; the 21.09 record of v0.3 vs the merged head on all six bags is
   [`experiments_v0.4_real_fullrate.json`](experiments_v0.4_real_fullrate.json). Classify each
   false alarm event by cause (platform edge, gate frame, overhead fixture, axis error, other)
   using the renders (`--render`).
4. **Real obstacles (R):** `resense eval --npy /data/cache/doubleT_obstacle --gt
   labels/doubleT_obstacle.json --text` (every frame is processed; `--labelled-only` counts only
   the labelled frames of a partially labelled bag; `--out r.jsonl` keeps the per-frame results
   for `summarize --compare`; for a moving labelled bag pass the known speed with
   `--ego-speed V`). Report recall over the in-gauge person frames, first detection, distance /
   lateral error, FP frames / events. The 21.09 numbers and the label recipe are in
   [`DATASET.md`](DATASET.md) "Real labels".
5. **Timing:** `resense bench --npy /data/cache/<bag>` (`--ego-speed V` for the node's
   given-speed path, which skips the estimator) offline; in ROS, play a bag at rate 1.0 for its
   full length and read the node's stats line (fps, latency mean / p95 / max, dropped frames).
   Run on the closest available machine to the bench (8 cores, no GPU), state which, state the
   load (`uptime`) and run compared variants back to back on the same bag: on the shared 4-core
   sandbox the per-frame time of the same code varies by ±50 % with the load.
   Both commands require their respective input data. `resense bench` and
   `scripts/bench_node_path.py` fail with an explicit empty-input diagnostic rather than printing
   a misleading timing result. ROS timing and throughput require a running ROS 2 graph and Docker
   acceptance requires a reachable daemon; when those are unavailable, report the check as
   unmeasured rather than reusing historical FPS/latency values.
6. **Regression:** the three numbers that must not get worse between versions are recall
   50–100 m on S, false-alarm frames on E (all bags), and p95 latency; on R the first alarm
   frame (9) and the recall (64/71) must not drop. Each PR that touches `resense/` re-runs S,
   E and R on the cached frames (`scripts/cache_frames.py`) and adds a row to the version
   table in EXPERIMENTS.md.

## 4. Targets (from PLAN.md sprints)

| milestone | recall person | recall box 0.5 m | false-alarm frames on E | p95 latency |
|---|---|---|---|---|
| v0 (day 1, measured) | 100 % ≤ 50 m, 50 % 50–100 m, 0 beyond | box 0.5 m at 54–56 m | 67 / 231 frames (49 in the platform-and-switch bag) | 47–125 ms |
| Sprint 1 | ≥ 90 % ≤ 100 m | ≥ 80 % ≤ 80 m | ≤ 1 per 100 frames outside platforms | ≤ 100 ms |
| Sprint 2 (accumulation) | confirmed at ≥ 150 m | confirmed at ≥ 100 m | ≤ 1 per 100 frames including platforms | ≤ 100 ms |
