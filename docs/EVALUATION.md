# Evaluation Protocol

> **Purpose:** what "better" means for ReSense — data sets, metrics, procedure and targets —
> written once so that P3 optimises against it, P4 implements it (`resense/metrics.py`,
> `resense eval`) and the jury's criteria (spec §8) map onto numbers we actually report.
> **Audience:** team, jury · **Owner:** P1 (protocol), P4 (code) · **Language:** EN, summary RU
> **Last verified:** 2026-09-25 against `8932f3a` · **Status:** current

**Кратко.** Как мы измеряем качество. Наборы данных: S — наши синтетические объекты в реальных
пустых кадрах; E — пять реальных записей без препятствий (ложные срабатывания); R — реальные
человек и предмет на рельсе в `doubleT_obstacle`; O — синтетические объекты, добавленные
инструментом самих организаторов; F — наши объекты, приближающиеся к поезду в 20-минутной
поездке; H — скрытая контрольная запись. Метрики: полнота по дальности, дальность первого
обнаружения, ложные события и кадры, задержка и FPS; что не должно ухудшаться между версиями
(§3, шаг 6). Цели спринтов на 24.09 (§4): полнота по человеку до 100 м, ≤ 1 ложного кадра на 100
вне платформ и p95 ≤ 100 мс офлайн выполнены; ящик 0,5 м и ложные срабатывания с платформами — нет;
человек на 150 м — только на синтетике.

Results live in [`EXPERIMENTS.md`](EXPERIMENTS.md); this file defines how they are produced.

## 1. Data sets

| set | source | positives | negatives | use |
|---|---|---|---|---|
| **S** synthetic | `resense inject` on real empty frames of every organizer bag, every 10th frame | person 0.5 × 1.7 m, box 0.2 / 0.5 / 1.0 m, plank 2 × 0.25 × 0.3 m, trolley; one object per frame, uniform 10–250 m along the track | 20 % of objects placed outside the gauge (must **not** alarm) | recall by range, first-detection distance, tuning |
| **E** empty real | the five organizer bags without a known obstacle | none | every frame | false-alarm rates by scene type |
| **R** real obstacles | `doubleT_obstacle` (crossing person and object on a rail, both labelled in `labels/doubleT_obstacle.json`) | labelled visible frames | labelled empty frames and the five empty bags | real recall and a limited reflectivity check; the extended `new_data` recording has no obstacles |
| **O** organizers' synthetic | `cloud_with_fake_obj` (24.09): ten objects ray-cast by the organizers' own tool into a real recording, labelled exactly from the appended object points (`labels/cloud_with_fake_obj.json`, [`DATASET.md`](DATASET.md)) | eight objects inside the envelope (2 × 2 m, 0.3 m cubes, a plank across the rails, a 5 cm hanging object) | two objects just outside it | per-object first STOP / held-from distance and false STOP on the outside objects (`scripts/score_fake_objects.py`); the tool that is part of the hidden check, so the closest thing to it |
| **F** synthetic on the moving ride | `scripts/far_range_eval.py`: catalogue objects ray-cast into selected split files of the 20-minute ride `new_data`, approaching the moving train from 150–220 m; placement per §3 | person, trolley, 1 m crate, 0.5 m box, hanging cable, small objects on the bed and on a rail head | the ride's own frames (off-object detections) | first-confirmed and held distances on a moving background: straight track, curves, stations |
| **H** hidden | the organizers' control bag on the day | unknown | unknown | nothing is tuned on it; the dry-run script only checks the pipeline runs |

## 2. Metrics

Implemented in `resense/metrics.py` (`Evaluation.summary()` keys in brackets) and printed by
`resense eval` and `resense summarize results.jsonl [--speed-mps V] [--gt gt.json]`;
`resense summarize --compare before.jsonl after.jsonl` prints the before/after table of two
runs (frames, alarm frames, events, advisory frames, first alarm frame, alarm distance range,
latency, FP frames / events, recall, frames merged) with a delta column.
On an unlabelled recording that may contain obstacles, use `resense summarize ... --unlabelled`:
it leaves FP counts and rates unknown (`null`) rather than assuming every frame is clear.

| metric | definition | reported as |
|---|---|---|
| **recall by range** | matched gauge ground-truth objects / all gauge ground-truth objects, per bin 0–50, 50–100, 100–150, 150–200, 200–300 m; a detection matches if \|Δdistance\| ≤ max(2 m, 3 % of range) + half object length and \|Δlateral\| ≤ 1 m | table per bin [`recall_by_range`, `per_bin_counts`], per object class [`recall_by_class`, `per_class_counts`; class = the `name` of the `inject` catalogue, else `kind`] and overall [`recall`] |
| **recall by class and range** | the recall-by-range table split per object class [`per_class_bin_counts`: class → bin → [matched, total]]; the per-kind table of set S | counts per cell (the cells of a 26-frame set hold 1–4 objects: quote the counts, not only the ratio) |
| **first-detection distance** | for a moving-toward run (real, or `inject --sequence N --speed V`): the largest range at which the object is confirmed and matched | m, per ground-truth label [`first_detection_distance`] |
| **distance / lateral error** | over matched detections: mean and max of \|Δdistance\|, the signed mean (bias, + = reported farther than the label), mean \|Δlateral\| [`distance_error_mean_abs`, `distance_error_max_abs`, `distance_error_bias`, `lateral_error_mean_abs`] | m; on the real person of `doubleT_obstacle` 0.00–0.07 m mean in v0.4 ([`DATASET.md`](DATASET.md) "Real labels"), ≤ 0.23 m max on 24.09 ([`EXPERIMENTS.md`](EXPERIMENTS.md) "Current results") |
| **first alarm frame** | index of the first frame with `obstacle = true` [`first_alarm_frame`] | frame; on `doubleT_obstacle` it is 11 (the person enters the 2.1 m envelope at frame 8 and, tracked while it approached, is reported 0.3 s later) and must not get later |
| **ego-speed source / frames merged** | how the accumulation actually ran: frames per `ego_speed_source` value (`given` / `estimated` / `none`) and the mean `n_accumulated` [`ego_speed_sources`, `n_accumulated_mean`] | counts; `given` when the node receives a valid speed; without one, shipped defaults report `none` (`accumulation.estimate_speed: false`); `estimated` requires explicitly opting in |
| **false-alarm frames** | frames with `obstacle = true` among frames with no gauge ground truth [`fp_frames`, `fp_frame_rate`]; every frame with `obstacle = true` regardless of labels is an *alarm frame* [`alarm_frames`] | per bag and per scene type (tunnel / curve / gate / platform / switch) |
| **false-alarm events** | distinct confirmed gauge track ids (`detections[].id`) that were never matched to a ground-truth object [`fp_events`]; distinct ids of all alarms [`alarm_events`]. Injected sequences scope each ID by `seq`, because the tracker restarts at each sequence; one object that stays in the corridor for 50 frames is one event | **the headline false-alarm number**, per bag |
| **false alarms per hour / per km** | `fp_events` per hour of bag time (span of the `stamp` field [`bag_time_s`]) [`fp_events_per_hour`] and per km travelled [`fp_events_per_km`] when a speed is known: `--speed-mps V` (constant) or a per-frame `ego_speed_mps` key in the JSON, integrated over the stamp gaps [`distance_km`]. For independent injected `seq` runs, inter-sequence time and distance are excluded. | per bag; `null` when no speed is known |
| **advisory rate** | frames with `warning = true` [`advisory_frames`, `advisory_frame_rate` = share of all evaluated frames] | informational; the advisory zone is expected to be noisy near infrastructure |
| **alarm distance** | min / max of `nearest_distance` over alarm frames [`alarm_distance_min`, `alarm_distance_max`] | m; the max on `doubleT_obstacle` is the person (56.6 m), the min includes false alarms near the train, so quote the max or per-event distances |
| **latency** | per frame: decode + detect (status JSON `node.latency_ms`) and decode + detect + publish (`/resense/latency_ms`); offline `timing_ms.total` [`latency_ms_mean`, `latency_ms_p95`, `latency_ms_max`] | mean, p95, max in ms |
| **throughput** | frames processed per second in the ROS node (`/resense/fps`) against the sensor's 10 Hz; dropped frames from stamp gaps (`node.dropped_frames`) | fps, dropped / total (node stats line, `scripts/check_dry_run.py`) |
| **decision latency** | frames from the first frame an object is visible in the corridor to the first `obstacle = true` | frames: 5 (0.5 s, `tracking.confirm_time_s`) for an object that appears inside the envelope; fewer for one already tracked while it approaches (the real person: 3) |
| **subsampling caveat** | the stride between consecutive `frame` indices [`frame_stride`]; the detector hands the tracker the measured frame interval when it lies inside `accumulation.stamp_dt_range` (0.02–0.5 s), else the nominal 0.1 s, so with every N-th frame a track needs max(`confirm_hits`, ⌈`confirm_time_s` / interval⌉) consecutive hits, N × frame_dt s apart: 3 hits spanning 1.5 s at every 5th frame, 5 hits spanning 5 s at every 10th, instead of 5 frames (0.5 s) at 10 Hz: **subsampled alarm and false-alarm counts understate the full-rate values** [`stride_caveat`] | printed next to every number measured on subsampled frames; headline numbers are measured at every frame |
| **CPU / memory** | `top` per core and RSS of the node on the team's 8-core machine | the stand-in for the jury's i7-9700E, which the team cannot use before submission ([`organizers/answers.md`](organizers/answers.md) §6) |

Objects fully occluded by real geometry (`n_points == 0` in `gt.json`) are excluded from
recall and counted separately (`occluded_gt_skipped`). Match tolerance and bins are the ones
implemented in `resense/metrics.py`; change them there and here together. The 200–300 m bin
is kept for completeness: the Pandar128 is instrumented to 200 m at 10 % reflectivity, and
only on its horizon channels ([`SENSOR.md`](SENSOR.md) §3), so a non-reflective object in
that bin is not expected to be detectable by any algorithm.

## 3. Procedure

**Set F synthetic-positive placement.** `scripts/far_range_eval.py` defaults to
`--placement-mode legacy`, which uses the detector-derived per-frame far axis and vault
drift; those results are not an independent test of curve or gauge-edge generalisation.
`--placement-mode anchored` carries a fixed object position backwards from a near (≤ 30 m)
rail-supported track fit using consecutive near fits and recorded speed. It rejects missing
stamps, large movement gaps and sequences without a near reference. Its placement is
independent of the *far axis*, but its pose is estimated from the same ride, not surveyed
ground truth. For `--placement-mode independent`, provide a separately surveyed reference in
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
2. **Synthetic on real frames (S)** — rebuild from the same cached empty frames and seeds as the
   21.09 sets. The historical v0.4 summaries in
   [`experiments_v0.4_synthetic_on_real.json`](evidence/results/experiments_v0.4_synthetic_on_real.json)
   used older object placement, persistence and sequence handling; their scores must not be compared
   as a paired A/B against the commands below without re-running both versions:

   ```bash
   # static sets: every 10th frame of three empty bags, one catalogue object per frame, 20 % negatives
   for bag in roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT; do
     resense inject --npy /data/cache/$bag --every 10 --out data/S_$bag \
         --kinds person,box0.5,box1.0,plank,trolley --distances 10:250 --negative-fraction 0.2 --seed 1
     resense eval data/S_$bag --text                     # defaults to five repeats with the v0.6.3 config
   done
   # approach sequences on roundT_doubleT: 8 steps of 1.5 m (15 m/s) per background, one kind per set, seeds 1-3
   for kind in person box0.5 box1.0 plank trolley; do for seed in 1 2 3; do
     resense inject --npy /data/cache/roundT_doubleT --every 10 --out data/SEQ_${kind}_s$seed --kinds $kind \
         --distances 10:250 --negative-fraction 0.2 --sequence 8 --speed 15 --seed $seed
     resense eval data/SEQ_${kind}_s$seed --repeat 1 --text                 # the rows' speed_mps is given to the detector
     resense eval data/SEQ_${kind}_s$seed --repeat 1 --no-gt-speed --text   # single-frame default
   done; done
   ```

   `eval` gives the detector the `speed_mps` of `inject --sequence` rows (`ego_speed_source:
   given`, as the ROS node with `ego_speed_mps` / odometry); `--ego-speed V` forces a constant
   on any source, `--no-gt-speed` withholds it; static sets (`speed_mps: 0`) get nothing and
   the LiDAR speed estimator is off by default (enable `accumulation.estimate_speed` to
   evaluate it; its accuracy against an ICP reference: `scripts/speed_reference.py`,
   `scripts/speed_accuracy.py`, EXPERIMENTS §9). Report recall by range per kind
   (`per_class_bin_counts`), first-detection distances and the occluded count. Two caveats:
   the per-frame recall of an 8-step sequence is capped at 4/8 for a new track with the current
   five-frame confirmation (and an object that starts beyond 150 m approaches only
   10.5 m within its sequence), so sequences are read by their first-detection distances and
   the static sets give the per-range recall; and the false-alarm counts of a static set are
   **not** meaningful: every 10th frame of a moving bag is a new scene 1 s apart and the five
   repeats confirm any structure that sits in the corridor.
3. **Empty real (E):** `resense run --npy /data/cache/<bag> --out results/<bag>.jsonl --quiet`
   on every frame (`--bag` on the bag itself), then `resense summarize results/<bag>.jsonl`
   per bag (alarm frames, events, advisory frames, first alarm frame, distance range, latency)
   and `resense summarize --compare before.jsonl after.jsonl` for the before/after table of a
   change; the 21.09 record of v0.3 vs the merged head on all six bags is
   [`experiments_v0.4_real_fullrate.json`](evidence/results/experiments_v0.4_real_fullrate.json).
   Classify each false alarm event by cause (platform edge, gate frame, overhead fixture, axis
   error, switch, other) using the renders (`--render`), and report switch events separately:
   the organizers do not count glitches at switches as a minus, because the switch state is not
   given to the system (24.09,
   [`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md) §5); false alarms
   at platforms do count.
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
   sandbox the per-frame time of the same code varies by ±50 % with the load. State the path
   (native kernels, or numpy with `RESENSE_NATIVE=0`); `resense bench`'s `total` leaves out the
   health monitor (7–14 ms), which the node's latency includes. Offline runs whose result depends
   on the frame interval (a speed, the estimator) use `scripts/eval_real.py --nominal-stamps`:
   the cache's receive stamps jitter, the node's header clock does not (EXPERIMENTS §9).
   Both commands require their respective input data. `resense bench` and
   `scripts/bench_node_path.py` fail with an explicit empty-input diagnostic rather than printing
   a misleading timing result. ROS timing and throughput require a running ROS 2 graph and Docker
   acceptance requires a reachable daemon; when those are unavailable, report the check as
   unmeasured rather than reusing historical FPS/latency values.
6. **Regression: the gate** ([`CAPTAIN.md`](CAPTAIN.md) §6). One command, one JSON:

   ```bash
   python scripts/regression_gate.py --cache /data/cache \
       --baseline docs/evidence/results/regression_baseline_2026-09-25.json \
       [--config FILE] [--set section.key=value ...] [--allow PATTERN ...] \
       --out out/gate/<change>.json
   ```

   `--jobs 2` by default; the per-frame JSONL goes to `--work`; `--from-json F` compares an
   earlier result without running anything.

   **What it runs.** Every frame, with a fresh detector per recording:

   - required: the six organizer recordings (E, R) and `cloud_with_fake_obj` (O);
   - only when `<cache>/new_data` exists: the 20-minute ride (8 pieces, as
     `scripts/eval_real.py`) and set F straight track (`scripts/far_range_eval.py`, the round-3
     parameters). Otherwise it records "not available".

   **When it fails.** It prints better / same / worse per metric and exits 1 when a gated metric
   is worse:

   - any frame count changes;
   - alarm events or STOP episodes rise on any of the five obstacle-free recordings or the ride;
   - on `doubleT_obstacle`: the labelled hits drop (person 58 of 61; object 127 of 185, and 124
     of 126 from frame 75), the first alarm frame (11) gets later, or a false-alarm event appears;
   - on O: an inside object loses STOP frames or its first STOP comes closer (no STOP counts as
     the worst), or an outside object or the background gains false STOP frames or track IDs;
   - on F straight: a kind loses a detected sequence, its median first confirmation shrinks, or
     its false detections rise.

   **What never gates.** Alarm frames, advisory frames, totals, held-from distances, the distance
   error and latency are printed as information. For latency the jobs run in parallel on a
   shared machine; clean timing is step 5.

   **Trade-offs and like-for-like.** An intended trade-off passes only with `--allow <metric
   pattern>`, named in the PR. The comparison reports a set that only one run has, and runs whose
   stamps (`--nominal-stamps`) or ride pieces differ. A missing required recording, or a failed
   set F run on a cached ride, exits 2.

   **Baseline of 25.09.** Native path, six recordings and O
   ([`regression_baseline_2026-09-25.json`](evidence/results/regression_baseline_2026-09-25.json)).
   It is identical to the 24.09 re-measure on every recording and to EXPERIMENTS §2e on every O
   object. The same code passes with `RESENSE_NATIVE=0`; `--set cluster.min_points=8` fails
   ([`evidence/regression_gate_2026-09-25/`](evidence/regression_gate_2026-09-25/)). The merged
   `8932f3a` (DBSCAN on cKDTree, two opt-in flags off) passes with every gated metric the same
   ([its JSON](evidence/results/regression_gate_2026-09-25_8932f3a.json)).

   **Rules for PRs.** Every PR that touches `resense/` or `configs/` attaches the gate's JSON and
   table. A PR that is meant to move the numbers commits a new baseline with them. Set S is not in
   the gate: re-run step 2 when a change targets it. Nothing in the gate needs the organizers'
   stand; the ride and set F are run on the team's 8-core machine. Do not compare the 2.1 m-envelope
   counts to older 1.4 m-envelope runs as if the labels were identical.

## 4. Targets of the sprints (17–24.09) and their status on 24.09

The targets were set on day 1 for Sprint 1 (17–20.09) and Sprint 2 (21–24.09) of
[`PLAN.md`](PLAN.md); "v0" is the day-1 prototype, measured on subsampled frames (15.09). The
actual values come from [`EXPERIMENTS.md`](EXPERIMENTS.md) "Current results", §2d, §2e, §3 and
§3b and from [`P4_AUDIT.md`](P4_AUDIT.md), each tagged with its kind.

| target | sprint | v0 (15.09, measured) | actual (24.09) | status |
|---|---|---|---|---|
| person: recall ≥ 90 % within 100 m | 1 | 100 % ≤ 50 m, 50 % 50–100 m | 96 % (0–50 m) and 94 % (50–100 m) of the visible frames on straight track [synthetic: set F round 3, legacy placement]; the real person 58 of 61 envelope frames at 55–57 m [real: `doubleT_obstacle`] | met |
| box 0.5 m: recall ≥ 80 % within 80 m | 1 | found at 54–56 m | on the bed 1 of 6 approaches, first confirmed at 52 m [synthetic: set F round 3]; 0 of 13 in set S [synthetic, P4_AUDIT]; the organizers' answer that an object on the bed is not an obstacle ([`organizers/answers.md`](organizers/answers.md) §8, 25.09: the 30 × 30 × 10 cm one below the rail head) does not excuse it: on these tunnels' bed (0.26–0.34 m below the rail head) a 0.5 m box's top is 0.15–0.25 m above the rail head, above the envelope floor (0.12 m) (EXPERIMENTS §2d) | not met |
| false-alarm frames on E ≤ 1 per 100 outside platforms | 1 | 67 of 231 frames (49 in the platform-and-switch bag) | 2 of 1 065 frames = 0.19 per 100 (`roundT_doubleT` and the two pressure-gate bags) [real] | met |
| p95 latency ≤ 100 ms | 1, 2 | 47–125 ms | offline 53–78 ms on one core, numpy path, health monitor not included [timing: sandbox, 23.09]; ROS node in Docker 76 ms at 120°, 112–130 ms at 360° [timing: sandbox, 23.09]; the i7-9700E stand is not open to the team before submission, the 8-core bench stands in ([`CAPTAIN.md`](CAPTAIN.md) action 7) | met offline and at 120°; not at 360° on the sandbox |
| person confirmed at ≥ 150 m | 2 | 0 beyond 100 m | median 148 m over the 6 straight approaches with legacy placement (set F round 3); in the 5 paired approaches 154 m anchored on the near rails against 150 m legacy (round 4); 167 m with a given train speed [synthetic: set F]; no real obstacle beyond 57 m exists | met on synthetic only |
| box 0.5 m confirmed at ≥ 100 m | 2 | — | not beyond 52 m [synthetic: set F]; the organizers' 0.3 m cubes from 34–43 m, their 2 × 2 m box from 98 m [organizers' synthetic: set O] | not met |
| false-alarm frames on E ≤ 1 per 100 including platforms | 2 | — | 107 of 2 287 frames = 4.7 per 100 (101 of them in `squareT_platform_squareT_switch`, train standing at the platform); the ride 204 of 11 271 = 1.8 per 100 [real] | not met |
