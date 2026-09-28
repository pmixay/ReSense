# Evaluation Protocol

> **Purpose:** what "better" means for ReSense — data sets, metrics, procedure and targets —
> written once so that the detector is optimised against it, `resense/metrics.py` and
> `resense eval` implement it, and the jury's criteria (spec §8) map onto numbers we report.
> **Audience:** team, jury · **Owner:** P1 (protocol), P4 (code) · **Language:** EN, summary RU
> **Last verified:** 2026-09-29: sets, metrics and gate rules against `resense/metrics.py`,
> `scripts/regression_gate.py`, the 27.09 baseline and `docs/SCORECARD.md` · **Status:** current

**Кратко.** Как мы измеряем качество. Наборы данных: S — наши синтетические объекты в реальных
пустых кадрах; E — пять реальных записей без препятствий (ложные срабатывания); R — реальные
человек и предмет на рельсе в `doubleT_obstacle`; O — синтетические объекты, добавленные
инструментом самих организаторов; F — наши объекты, приближающиеся к поезду в 20-минутной
поездке; H — скрытая контрольная запись. Все реальные записи и набор O использовались при
разработке, поэтому все частоты ложных срабатываний — «в выборке»; отложенные данные — части
поездки для обученной модели, тест дальности с перенесённым человеком и запись H (§1). Метрики:
полнота по дальности, дальность первого обнаружения, ложные события и кадры, задержка (§2);
регрессионный шлюз (§3, шаг 6); цели первого дня и их состояние (§4).

Results: [`EXPERIMENTS.md`](EXPERIMENTS.md) and [`SCORECARD.md`](SCORECARD.md); the full dated
log is [`archive/EXPERIMENTS_log_2026-09.md`](archive/EXPERIMENTS_log_2026-09.md). This file
defines how results are produced.

## 1. Data sets

| set | source | positives | negatives | use |
|---|---|---|---|---|
| **S** synthetic | `resense inject` on real empty frames of the organizer bags, every 10th frame | person, boxes 0.2 / 0.5 / 1.0 m, plank, trolley; one per frame, 10–250 m | 20 % of objects outside the envelope (must **not** alarm) | recall by range and class, tuning |
| **E** empty real | the five organizer bags without an obstacle, and the 20-minute ride `new_data` | none | every frame | false alarms by scene type |
| **R** real obstacles | `doubleT_obstacle`: the crossing person and the object on the rail ([`labels/doubleT_obstacle.json`](../labels/doubleT_obstacle.json)) | labelled frames | labelled empty frames | real recall, distance error |
| **O** organizers' synthetic | `cloud_with_fake_obj`: ten objects ray-cast by the organizers' own tool into a real ride ([`DATASET.md`](DATASET.md) "Synthetic-obstacle recording") | eight objects inside the envelope | two just outside | per-object first STOP, STOP frames, false STOP (`scripts/score_fake_objects.py`); the tool of the hidden check, so the closest thing to it |
| **F** synthetic on the moving ride | `scripts/far_range_eval.py`: catalogue objects approaching the moving train from 150–220 m in selected split files of `new_data` (placement: §3) | person, trolley, crates, a hanging cable, small objects on the bed and a rail head | the ride's own frames | first-confirmed and held distances on straight track, curves, stations |
| **H** hidden | the organizers' control data | unknown | unknown | nothing is tuned on it |

**How independent the ground truth is.** Neither labelled set is independent of the team's own
processing, so their recall figures are consistency checks, not an external truth:

* **R** — made by the team with DBSCAN on its frame cache, thresholds it chose, lateral positions
  from the **median of the detector's own per-frame track axis** and heights from its rail-head
  model; checked by eye on renders ([`DATASET.md`](DATASET.md) "Real labels"). Not the detector's
  output, but its track model: an error both share would not show as a miss.
* **O** — the object *points* are exact (appended by the organizers' tool) and `in_gauge` is their
  intent, but `distance` and `lateral` are measured in the frame the **shipped detector's mount
  calibration and track axis** give (`scripts/label_fake_objects.py`), and the team tuned on set O.
* Nothing was labelled by a third party; the sets without labels (E) count alarms, which need no
  ground truth.

**What is in-sample and what is held out.** Every real recording (the six bags, the ride) and set
O were inspected and tuned on: rules were added per organizer object, several thresholds are
bracketed by set O objects, and the learned track opinion was trained on the rules' tracks of the
ride and the five empty bags. **Every false-alarm rate is therefore in-sample**
([`SCORECARD.md`](SCORECARD.md)). Held out are only: the ride pieces each scored by an opinion
model that never saw them (cross-fitting, [`DECISIONS.md`](DECISIONS.md) row 19); the range test
of the independent judgement (the real person cut from `doubleT_obstacle` and pasted at 60–200 m
into the other five tunnels: unseen composites on seen backgrounds,
[`evidence/judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md)); and H. Sets S and F
are synthetic objects on seen backgrounds: sensitivity tests, not held-out recall.

## 2. Metrics

Implemented in `resense/metrics.py` (`Evaluation.summary()` keys in brackets), printed by
`resense eval` and `resense summarize results.jsonl [--speed-mps V] [--gt gt.json]`;
`resense summarize --compare before.jsonl after.jsonl` prints a before / after table.
`--unlabelled` leaves FP counts unknown (`null`) on a recording that may contain obstacles.

| metric | definition | reported as |
|---|---|---|
| **recall by range** | matched in-envelope ground-truth objects / all, per bin 0–50, 50–100, 100–150, 150–200, 200–300 m; a match needs \|Δdistance\| ≤ max(2 m, 3 % of range) + half the object length and \|Δlateral\| ≤ 1 m | per bin [`recall_by_range`, `per_bin_counts`], per class [`recall_by_class`; class = the catalogue `name`, else `kind`], overall [`recall`] |
| **recall by class and range** | the same split per class [`per_class_bin_counts`] | counts per cell (small cells: quote counts, not ratios) |
| **first-detection distance** | on an approaching run: the largest range at which the object is confirmed and matched | m per label [`first_detection_distance`] |
| **distance / lateral error** | over matched detections: mean and max \|Δdistance\|, signed bias (+ = reported farther), mean \|Δlateral\| [`distance_error_*`, `lateral_error_mean_abs`] | m |
| **first alarm frame** | first frame with `obstacle = true` [`first_alarm_frame`] | on `doubleT_obstacle` the person enters the envelope at frame 8; the alarm must not come later |
| **false-alarm frames** | alarm frames among frames without in-envelope ground truth [`fp_frames`, `fp_frame_rate`]; all alarm frames [`alarm_frames`] | per recording and scene type |
| **false-alarm events** | distinct confirmed alarm track ids never matched to ground truth [`fp_events`]; all alarm ids [`alarm_events`]; one object in the corridor for 50 frames is one event | **the headline false-alarm number** |
| **STOP episodes** | GO → STOP transitions of the decision (the gate's count) | per recording, per km of the ride |
| **per hour / per km** | `fp_events` per hour of bag time [`fp_events_per_hour`] and per km [`fp_events_per_km`] when a speed is known (`--speed-mps V` or a per-frame `ego_speed_mps`) | `null` without a speed |
| **advisory rate** | frames with `warning = true` [`advisory_frames`, `advisory_frame_rate`] | informational (CAUTION is expected near infrastructure) |
| **ego-speed source** | frames per `ego_speed_source` (`given` / `estimated` / `none`) and mean `n_accumulated` | `none` with the shipped defaults unless a speed is given |
| **latency** | per frame decode + detect (status JSON `node.latency_ms`), + publish (`/resense/latency_ms`); offline `timing_ms.total` [`latency_ms_*`] | mean, p95, max in ms |
| **end-to-end latency of current results** | a listener receives an input cloud → it receives `/resense/status` with the same stamp and `freshness.reason` `current` (the jury chain) | p95 in ms, warm and cold page cache |
| **throughput** | frames processed per second (`/resense/fps`) against the sensor's 10 Hz; frames left unprocessed | fps, node stats line, `scripts/check_dry_run.py` |
| **decision latency** | frames from the first in-envelope frame to the first alarm | 5 frames (0.5 s, `tracking.confirm_time_s`) for an object that appears inside; fewer for one tracked while it approaches |
| **subsampling caveat** | on every N-th frame a track needs max(`confirm_hits`, ⌈`confirm_time_s` / interval⌉) hits N × 0.1 s apart [`frame_stride`, `stride_caveat`] | subsampled alarm counts understate full-rate ones; headline numbers are at every frame |
| **CPU / memory** | `top` per core and RSS of the node | on a 4-vCPU sandbox and the team VM (8 vCPU = 4 physical cores), standing in for the jury's i7-9700E, which the team cannot use ([`organizers/answers.md`](organizers/answers.md) §6) |

Fully occluded objects (`n_points == 0`) are excluded from recall and counted in
`occluded_gt_skipped`. Tolerances and bins live in `resense/metrics.py`; change them there and
here together. The 200–300 m bin is kept for completeness: the Pandar128 reaches 200 m at 10 %
reflectivity only on its horizon channels ([`SENSOR.md`](SENSOR.md) §3).

## 3. Procedure

**Set F placement.** `scripts/far_range_eval.py --placement-mode legacy` (the default) places
objects on the detector's own per-frame far axis, so it is not an independent test of curves or
envelope edges. `anchored` carries a fixed position back from a near (≤ 30 m) rail-supported
track fit using the recorded speed: independent of the far axis, but estimated from the same ride,
not surveyed. `independent` takes an externally surveyed reference in vehicle coordinates
(`--axis-center`, `--axis-yaw-deg`, `--axis-curvature`, `--rail-z0`, `--rail-grade`; never derived
from the evaluated frames) and fixed perturbations (`--lateral-offset`, `--yaw-perturb-deg`); on a
curve it is an extrapolation, so check its validity per sequence. Record the reference, cache and
config hashes and seeds with every report. `recall_by_bin` counts visible object-frames only;
`false_detections` counts unmatched detections per frame, not events.

1. **Fix the configuration.** The detector and `configs/default.yaml` are sealed
   ([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md); `python3 scripts/detector_freeze.py verify`).
   Record the commit and `sha256sum configs/default.yaml` with every result.
2. **Synthetic on real frames (S):**

   ```bash
   for bag in roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT; do
     resense inject --npy /data/cache/$bag --every 10 --out data/S_$bag \
         --kinds person,box0.5,box1.0,plank,trolley --distances 10:250 --negative-fraction 0.2 --seed 1
     resense eval data/S_$bag --text                     # static set: five repeats per frame
   done
   resense inject --npy /data/cache/roundT_doubleT --every 10 --out data/SEQ_person_s1 --kinds person \
       --distances 10:250 --negative-fraction 0.2 --sequence 8 --speed 15 --seed 1
   resense eval data/SEQ_person_s1 --repeat 1 --text   # the rows' speed is given; --no-gt-speed withholds it
   ```

   `eval` gives the detector the rows' `speed_mps` (`ego_speed_source: given`, as the node with
   `ego_speed_mps` / odometry); `--ego-speed V` forces a constant. Read sequences by their
   first-detection distances (an 8-step sequence caps per-frame recall at 4/8 with five-frame
   confirmation) and static sets for per-range recall; a static set's false-alarm counts mean
   nothing (every 10th frame of a moving bag is a new scene). The historical set S scores
   ([`experiments_v0.4_synthetic_on_real.json`](evidence/results/experiments_v0.4_synthetic_on_real.json))
   used older placement and must be re-run before any comparison.
3. **Empty real (E):** `resense run --npy /data/cache/<bag> --out results/<bag>.jsonl --quiet` on
   every frame, then `resense summarize`; `scripts/eval_real.py --cache /data/cache` runs every
   recording and the ride (eight pieces). Classify each false alarm by cause with `--render`.
   Report switch events separately: the organizers do not count glitches at switches, because
   the switch state is not given to the system
   ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md) §5); platforms count.
4. **Real obstacles (R):** `resense eval --npy /data/cache/doubleT_obstacle --gt
   labels/doubleT_obstacle.json --repeat 1 --text` (`--out r.jsonl` keeps per-frame results).
   Report recall over the in-envelope frames, first alarm, distance / lateral error, FP events.
5. **Timing:** offline `resense bench --npy /data/cache/<bag>` (native kernels; `RESENSE_NATIVE=0`
   for the numpy fallback; `bench` leaves out the health monitor, which the node includes).
   Through ROS: play a bag at rate 1.0 with the jury's player (`--read-ahead-queue-size 10`) and
   read the node's stats line, or measure end to end with a listener as in
   [`evidence/judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md). State the machine,
   its load (`uptime`) and warm or cold cache, and run compared variants back to back: on a
   shared 4-core machine the same code varies by ±50 %. `scripts/check_dry_run.py` does not see a
   player that falls behind real time (slow storage), so check the player too. Speed-dependent
   offline runs use `scripts/eval_real.py --nominal-stamps`. Without a ROS graph or a Docker
   daemon, report the check as unmeasured rather than reuse old figures.
6. **Regression: the gate** ([`CAPTAIN.md`](CAPTAIN.md) §6). One command, one JSON:

   ```bash
   python scripts/regression_gate.py --cache /data/cache \
       --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json \
       [--set section.key=value ...] [--allow PATTERN ...] --out out/gate/<change>.json
   ```

   **What it runs**, every frame with a fresh detector per recording: the six organizer
   recordings and set O (required); the ride in eight pieces and set F straight when
   `<cache>/new_data` exists. **It fails** (exit 1) when a gated metric is worse: a frame count
   changes; alarm events or STOP episodes rise on an empty recording or the ride; on
   `doubleT_obstacle` a label's hits drop, the first alarm comes later or a false-alarm event
   appears; on set O an inside object loses STOP frames, sustained range or its first-STOP
   distance, or an outside object or the background gains false STOPs; on set F straight a kind
   loses a sequence, first-confirmation distance, or gains false detections; or a gated row of
   the baseline is missing (the ride rows without `<cache>/new_data`, unless accepted on purpose
   with `--allow 'ride.*' --allow 'set_F_straight.*'`). Alarm and advisory frames, held-from
   distances, distance error and latency are information only.

   **The baseline** is the gate of the sealed 27.09 detector
   ([`regression_baseline_2026-09-27_quality.json`](evidence/results/regression_baseline_2026-09-27_quality.json));
   earlier baselines are listed in [`evidence/README.md`](evidence/README.md). A change to the
   sealed detector needs this gate with the ride and set F, a review and a new seal
   ([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)); an intended trade-off passes only with a named
   `--allow`. Set S is not in the gate. Do not compare counts under the 2.1 m envelope with
   older runs under the 1.4 m polygon.

## 4. Targets and where they stand

Targets set on day 1 (15.09); status of the sealed detector from the independent judgement of
28.09 ([`SCORECARD.md`](SCORECARD.md), raw data in
[`evidence/judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md)) unless another source
is named. False-alarm figures are in-sample (§1).

| target | status | met? |
|---|---|---|
| person: recall ≥ 90 % within 100 m | the real person at 55–57 m: STOP on every in-envelope frame, from frame 8; the same person pasted into the other tunnels: sustained STOP in 11 / 8 / 6 of 15 windows at 60 / 80 / 100 m (the misses are CAUTION) | at 55 m only |
| box 0.5 m: recall ≥ 80 % within 80 m | set F straight: 1 of 6 approaches, at ~52 m ([27.09 baseline](evidence/results/regression_baseline_2026-09-27_quality.json), synthetic); the organizers' 0.3 m cubes: first STOP at 35–56 m | no |
| false-alarm frames ≤ 1 per 100 on E | five empty recordings: 23 of 2 287 STOP frames (1.0 %), 7 episodes; the ride: 164 of 11 271 (1.5 %), 30 episodes = 2.3 per km | borderline; no on the ride |
| p95 latency ≤ 100 ms | jury chain on 4 vCPU before the 29.09 node change: end to end, current results, 360° 85–94 ms warm and 87–172 ms cold, 120° 49–78 ms; decode + detect p95 79–98 ms | warm yes; cold 360° not always |
| person confirmed at ≥ 150 m | pasted real person: sustained STOP at 130 / 160 / 200 m in 2 / 1 / 0 of 15 windows; synthetic person on the ride (set F straight): median first detection 151 m (27.09 baseline) | synthetic only |
| box 0.5 m confirmed at ≥ 100 m | set F 0.5 m box ≤ 52 m; the organizers' 2 × 2 m box from 98 m (its first appearance) | no |
