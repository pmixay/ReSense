# Experiments

> **Purpose:** every measured result of ReSense with its data, date and raw summary: false alarms,
> range, latency, FPS, hard cases and how the quality changed (spec §5 "Эксперименты").
> **Audience:** jury, team · **Owner:** P3, P4 (content), P1 (structure, timing) · **Language:** EN,
> summary RU
> **Last verified:** 2026-09-25 against `79109f5` (detector v0.6.3 with the long overhead rule on
> since 25.09, node v0.6.4, package 1.0.0; re-measured by the regression gate with the ride) ·
> **Status:** current

**Кратко.** Здесь все измерения ReSense с датой и видом данных. На всех 13 759 реальных кадрах
организаторов пять бэгов без препятствий дают 14 ложных событий (20 до правила длинных навесных
конструкций, 25.09), 20-минутная поездка — 46 (3,5 на км); человек на пути найден в 58 из 61 кадра
с 11-го, предмет на рельсе — в 124 из 126 кадров после ухода человека, ошибка расстояния ≤ 0,23 м.
На синтетических объектах самих организаторов (набор O) STOP получают 5 из 8 объектов в габарите:
ящик 2 × 2 м с 98 м, кубы 0,3 м только с 34–43 м. Человек на 148–154 м — только на нашей синтетике
(151 м по текущему скрипту оценки, 25.09). Время кадра 42–64 мс (p95 53–78 мс) на одном ядре
машины разработки без монитора состояния; ядра на C++ (24.09) сокращают его на 38–57 %, DBSCAN на
cKDTree (25.09) — ещё на 1–3 мс, выход тот же; стенд i7-9700E до сдачи команде недоступен
(организаторы, 25.09), замер — на 8-ядерной машине команды. Все числа по реальным записям, набору O,
поездке и набору F на прямой перепроверяются одной командой (`scripts/regression_gate.py`, эталон
25.09 с поездкой). Собственная оценка скорости поезда по лидару точна (ошибка 0,06–0,08 м/с), но
даже точная скорость не улучшает проверку организаторов (§9), поэтому по умолчанию она выключена.

## Current results (detector v0.6.3 with the long overhead rule on since 25.09, node v0.6.4)

The shipped configuration, no train speed given unless said. Kinds: **real** = the organizers'
recordings as recorded; **synthetic** = our objects ray-cast into real frames (set F: into the
moving ride); **organizers' synthetic** = objects added by the organizers' own tool (set O). Sets
and terms: [`README.md`](README.md) §3 (glossary), [`EVALUATION.md`](EVALUATION.md) §1.

**Re-run in one command.** `scripts/regression_gate.py` (EVALUATION §3 step 6) re-measures the
real-data rows (five obstacle-free bags, the person, the object on the rail, the ride), the set O
row and set F straight track in one run, and gates every detector change against
[`regression_baseline_2026-09-25_ride.json`](evidence/results/regression_baseline_2026-09-25_ride.json)
(the shipped defaults of `935eecf`: six recordings, set O, the ride and set F straight; 25.09). It
is the single check of these results: a change that moves them commits a new baseline, one that
does not leaves this table as it is. The older
[`regression_baseline_2026-09-25.json`](evidence/results/regression_baseline_2026-09-25.json)
(six recordings and set O, no ride) is kept for history; the merged `8932f3a` passed against it with
every gated metric the same ([its JSON](evidence/results/regression_gate_2026-09-25_8932f3a.json)).

| metric | value | kind, date | where |
|---|---|---|---|
| false alarms, five obstacle-free bags (2 287 frames) | **14 events**, 60 alarm frames, 17 STOP episodes (long overhead rule on since 25.09; 20 / 107 / 27 without it); the start-offset spread 14–20 events was measured without the rule (24.09), not re-run | real, 25.09 [measured 25.09] | §1f |
| false alarms, 20-minute ride (11 271 frames, 13.0 km) | **46 events, 3.5 per km**, 197 alarm frames (1.7 %), 39 STOP episodes (without the long overhead rule 47 / 204 / 39, equal to the 24.09 record); 15 of the 46 first confirmed beyond 100 m (the removed event, an overhead structure 4–5 m along the track at 105–110 m, was one of the 16 of 24.09); causes: the 24.09 classification of the 47 (corridor-edge structures 18, bed-level fixtures 11, far small clusters 7, other 6, tall 2, hanging 2, person-like 1), not redone | real, 25.09 [measured 25.09] | §1f |
| crossing person, `doubleT_obstacle` | STOP in **58 of 61** frames inside the envelope, first alarm frame 11 (0.3 s after entering), 55.5–56.6 m, distance error ≤ 0.23 m | real, 24.09 | §0 |
| object lying across the rail (0.45 × 0.6 × 0.3 m, 56 m) | **124 of the 126** frames after the person leaves it (from frame 75)¹; 3 STOP episodes in the recording | real, 24.09 | §0 |
| health, `CAUTION` | non-latency health warnings on 196 of 13 759 frames (1.4 %: rails lost at stations and switches); `CAUTION` on 27–68 % of the frames of the empty bags, 41 % of the ride | real, 24.09 | "Re-measurement" |
| current code against v0.6.3 | identical per-frame output on all 13 759 frames | real, 24.09 | "Re-measurement" |
| regression gate with the ride and set F straight (native, 25.09) | new baseline [`regression_baseline_2026-09-25_ride.json`](evidence/results/regression_baseline_2026-09-25_ride.json) on `935eecf`: PASS against the shipped-defaults run of the same day (3 gated rows better: `squareT_platform_squareT_switch` events and STOP episodes, ride events); decision evidence [`rules_decision_2026-09-25.json`](evidence/results/rules_decision_2026-09-25.json); the review fix `cluster.floating_long_min_bottom` 1.6 m (`0bb1ba3`) passes against the same baseline with every number but latency identical and the same per-frame output, so the baseline stands ([`long_rule_bottom_2026-09-25.json`](evidence/results/long_rule_bottom_2026-09-25.json)) | real, organizers' synthetic and synthetic, 25.09 | §1f |
| organizers' objects (set O, `cloud_with_fake_obj`, 10 objects in 1 510 frames) | STOP for **5 of 8** in-envelope objects: 2 × 2 m box from 98 m (first sight), plank across the rails from 82 m, 0.3 m cubes from 34–43 m, 2 × 2 m box at the envelope top in 12 of 124 frames; the edge 2 × 2 m box and the 5 cm hanging object missed, the edge 0.3 m cube advisory only; STOP in 303 of 801 visible in-envelope object-frames, 1 of 236 beyond 100 m; 6 false STOP frames on the 2 × 2 m box outside, 3 background alarm frames | organizers' synthetic, 24.09 | §2e |
| long range, straight track | person first confirmed at **148 m** median (6 of 6), held in ≥ 90 % of the frames from 149 m and in every 10 m band from 115 m; trolley 144 m; 1 m crate 111 m; 3 cm hanging cable 95 m, held from 53 m (4 of 6); 0.5 m box on the bed 1 of 6; re-measured 25.09 by the gate on the current `far_range_eval.py` (changed by the P4 audit after 24.09; same files, seed, stamps, speeds): person 151.0 m median (6 of 6), held from 142.6 m; trolley 151.4 m; 1 m crate 123.9 m; cable 98.9 m, held from 34.2 m (6 of 6); 0.5 m box 1 of 6 (51.9 m); identical with and without either 25.09 rule [measured 25.09] | synthetic, set F round 3, legacy placement, 24.09; gate 25.09 | §2d |
| same, object anchored on the near rails | person **154 m** (legacy 150 m in the same 5 pairs), trolley 148 m (148 m), crate 110 m (116 m), cable 102 m (104 m) | synthetic, set F round 4, anchored placement, 24.09 | §2d |
| curves and the envelope edge, paired | no visible object matched at 100–150 m in either placement mode (6 paired R ≈ 350 m curve approaches per kind, lateral to the envelope edge); first confirmed person 74 → 68 m, 1 m box 75 → 80 m (legacy → anchored) | synthetic, set F paired, 24.09 | §2d |
| long range with a given train speed | person 167 m, trolley 175 m, crate 182 m (held only from 79 m) | synthetic, set F round 3, legacy, 24.09 | §2d |
| train speed (opt-in LiDAR-only estimate) | median error 0.06–0.08 m/s, p90 ≤ 0.20 m/s against an ICP reference on 55–96 % of the moving frames, +6.6–6.8 ms per frame; even the reference speed handed in as odometry buys nothing on the organizers' check: five bags 103 / 18 → 111 / 16 alarm frames / events, no organizers' object STOPs earlier, 6 → 17 false STOP frames on the 2 × 2 m box outside; only far-field frame recall rises | real, organizers' synthetic and synthetic, 24.09 | §9 |
| curves, stations, small and low objects | R ≈ 350 m curves 6 of 7 from 58–86 m (the sightline); station stops 6 of 6 from 113 m; 30 cm objects on a rail head 6 of 6 from 42–49 m; a person lying across the rails 6 of 6 from 64 m; objects on the bed between the rails stay below the envelope (policy, confirmed by the organizers on 25.09: not an obstacle, [`organizers/answers.md`](organizers/answers.md) §8) | synthetic, set F round 3, legacy, 24.09 | §2d |
| set S (108 real empty frames) | 22 of 67 visible in-gauge objects with bed placement, 29 of 68 with the old legacy height (small samples) | synthetic, 24.09 | [`P4_AUDIT.md`](P4_AUDIT.md) |
| sensor reach | no return beyond 210 m in any of the 13 759 frames: 300 m is beyond this sensor | real | §2d |
| other mounts | upside down, `+x` forward, backwards found; tilt recovered to 0.0–0.5° | real, re-mounted, 22–23.09 | §6 |
| offline timing per frame | 42–64 ms mean, p95 53–78 ms on every recording, one core, numpy path (v0.6.3), health monitor not included (7–14 ms more); on another idle VM on 24.09 36.5–52.2 ms mean, p95 50.3–67.1 ms; the optional C++ kernels (merged 24.09, after v0.6.3) cut the detector time by 38–57 % with identical output | timing: sandbox, 23.09 (kernels: 24.09, under load) | §3; [`ARCHITECTURE.md`](ARCHITECTURE.md) "Native kernels" |
| ROS 2 node in Docker | 120°: 10 fps, p95 76 ms; 360°: 7–10 fps, p95 112–130 ms in `dry_run.sh` (the sandbox is at the frame period); ~100 % of one core, 186 MB | timing: sandbox, 23.09 (v0.6.2 image) | §3b |
| node start-up (v0.6.4) | first STOP on `doubleT_obstacle` 1.59 s into the recording (v0.6.3: 4.02 s), no scene reset; peak RSS 403–434 MB at 360° | timing: sandbox, 24.09 [team record, unverified: raw captures not committed] | §3b |
| opt-in near-bed path (off) | first gates: five bags 20 → 145 events, ride 47 → 667, a 30 × 30 × 10 cm box on the bed in 0 of 6 set F approaches [team record, unverified]; current gates (`537e220` with the box fix `7df1796`): five bags 459 alarm frames / 107 events / 72 STOP episodes, the box found in the synthetic-tunnel test at 12–28 m; ride and set F not re-run, and no longer needed: a bed object is not an obstacle (organizers, 25.09, [`organizers/answers.md`](organizers/answers.md) §8) | real + synthetic, 24.09 | §1e |

¹ The same scene is counted three ways: 124 of 126 frames after the person leaves (the headline);
127 of the object's 185 visible frames by its own detection; 185 of the 246 labelled
obstacle-frames of the recording (person 58 of 61 + object 127 of 185).

**Caveats.**

* The opt-in paths `track.rails_far_check_enabled`, `lowobj.near_enabled` and
  `accumulation.estimate_speed` are `false` in both parameter files and the code defaults; the
  far-rail check was measured on 25.09 on the six recordings and set O and never fires (§1f), the
  near-bed path is §1e (off for good: the organizers do not count an object on the bed between the
  rails as an obstacle, 25.09, [`organizers/answers.md`](organizers/answers.md) §8), the speed
  estimator §9. No number in this table uses any of them.
* `cluster.floating_long_min_length` is 3.0 (on) in both parameter files and the code since 25.09
  (decided on the ride, §1f), with `cluster.floating_long_min_bottom` 1.6 m since the review of the
  same day (a tray or duct fallen onto the axis is a STOP again; every number of the gate identical
  frame by frame, §1f "Review of 25.09"); `cluster.short_signature_max_length` stays 0 (tried, not
  shipped, §1f). Every number of this table dated 25.09 uses the long rule; the 24.09 rows do not (the
  rule changes only `squareT_platform_squareT_switch` and one ride event: the person, the object
  on the rail, set O and set F straight are identical with and without it).
* Set F uses legacy placement unless said (protocol: EVALUATION §3; paired check: §2d round 4 and
  [`P4_AUDIT.md`](P4_AUDIT.md)); synthetic objects are not a real long-range test.
* ROS and Docker numbers are dated runs on the sandbox, not re-measured on every change.

## Re-measurement on the current code (24.09)

The v0.6.3 numbers were measured on commit `c1c2b6a` (merged as `1210580`); `a92625e` then changed
the detector and `configs/default.yaml` (two opt-in stages, both off) without data at hand, and set
F had not been re-run since v0.6.2. On 24.09 the organizers' data was downloaded again and cached at
full rate (all 13 759 frames), and the current code (`main` at `4cd32d6`) and v0.6.3 were run on it
(raw summaries:
[`experiments_2026-09-24_remeasure.json`](evidence/results/experiments_2026-09-24_remeasure.json)).
`537e220` (24.09) changed only the opt-in near-bed gates; the default path is unchanged.

| check | result |
|---|---|
| real frames: per-frame output of the current code against v0.6.3 (obstacle, warning, nearest and clear distance, every detection's id, distance, lateral, kind, zone) | **identical on all 13 759 frames.** Every real-data number of §0 holds for the current code: five obstacle-free bags 107 alarm frames / 20 events / 27 STOP episodes; ride 204 / 47 / 39 (3.6 events per km); the person 58 of 61 frames from frame 11, distance error ≤ 0.23 m; the object on the rail 124 of the 126 frames from frame 75 (127 of 185 by its own detection); 3 STOP episodes on `doubleT_obstacle`; health warnings other than latency on 196 frames (1.4 %) |
| false alarms by the first processed frame (`scripts/start_offsets.py`) | 30 of 30 rows identical to the v0.6.3 record (14–20 events on the five bags) |
| set F (synthetic objects in the moving ride) | first confirmations unchanged; the held ranges, frame recall and off-object detections moved because round 2 predates v0.6.3's hold over one missed frame — with the hold off the current code reproduces round 2's straight set value for value. Round 3 table: §2d |
| offline timing, the two versions back to back (`resense bench`, every frame, `OMP_NUM_THREADS=1`, an idle 4-core sandbox — not the machine of 23.09) | current code 36.5–52.2 ms mean, p95 50.3–67.1 ms; v0.6.3 35.1–57.4 ms, p95 46.3–75.4 ms; per recording −9…+6 % (run-to-run noise), no regression. §3's 42–64 / 53–78 ms of 23.09 stays the quoted figure |
| derived figures that had no recorded source | `CAUTION` (warning or a non-latency health warning, no obstacle) on 27–68 % of the frames of the five obstacle-free recordings and on 41 % of the ride; 16 of the 47 ride events are first confirmed beyond 100 m |

## Reading order and raw data

§0 is the shipped detector (v0.6.3, 23.09) on all real data, re-measured on the current code on
24.09 (above); §0a is v0.6.1, the version the organizers' Q&A answers produced; §1–§1f and §2–§2e
are the record of how the detector got there (real bags; synthetic obstacles in real frames; long
range on the moving ride; the organizers' synthetic-obstacle recording); §3 timing, §4 lessons,
§5 open experiments, §6 mount calibration, §7 the recognition methods side by side, §8 the learned
second opinion, §9 the train speed (the LiDAR-only estimate measured, and what a speed adds). Every
number is **real** (recording named), **synthetic** (said so) or **organizers' synthetic** (set O).

Raw summaries live in [`evidence/results/`](evidence/results/), one row each in
[`evidence/README.md`](evidence/README.md); the ones this file cites most:

* [`experiments_2026-09-24_remeasure.json`](evidence/results/experiments_2026-09-24_remeasure.json):
  every headline number re-measured on the current code, set F round 3, timing (24.09);
* [`experiments_v0.6.3_real_fullrate.json`](evidence/results/experiments_v0.6.3_real_fullrate.json):
  v0.6.3 over all 13 759 frames, STOP episodes, the leave-one-out check;
* [`experiments_v0.6.3_start_offsets.json`](evidence/results/experiments_v0.6.3_start_offsets.json):
  false alarms by the first processed frame;
* [`experiments_v0.6.2_real_fullrate.json`](evidence/results/experiments_v0.6.2_real_fullrate.json):
  v0.6.1 and every v0.6.2 step over all 13 759 frames, plus the leave-one-out check;
* [`experiments_v0.6.2_setF.json`](evidence/results/experiments_v0.6.2_setF.json): set F round 2
  (small objects, rail heads, the envelope edge, curves, station stops, sustained range);
* [`experiments_v0.6.2_margins_lying.json`](evidence/results/experiments_v0.6.2_margins_lying.json):
  the straddle thresholds' margins, the low-object width cap, the lying person;
* [`experiments_v0.6.1_real_fullrate.json`](evidence/results/experiments_v0.6.1_real_fullrate.json),
  [`experiments_v0.6.1_setF.json`](evidence/results/experiments_v0.6.1_setF.json): v0.6.1 and set F
  round 1;
* [`experiments_p4_setf_paired.json`](evidence/results/experiments_p4_setf_paired.json),
  [`experiments_p4_setf_straight_paired.json`](evidence/results/experiments_p4_setf_straight_paired.json):
  set F round 4, legacy against anchored placement;
* [`experiments_p4_fake_labelled.json`](evidence/results/experiments_p4_fake_labelled.json): set O,
  the per-object grade and the variants of §2e;
* [`experiments_2026-09-24_train_speed.json`](evidence/results/experiments_2026-09-24_train_speed.json):
  the train-speed study of §9 (estimator accuracy, false alarms, set O, set F, timing).

**P4's evaluation audit (23–24.09).** [`P4_AUDIT.md`](P4_AUDIT.md) corrected the synthetic
placement (set S on the local bed, set F anchored on the near rails) and the accounting (tracker
reset per sequence, event identity per sequence, one-to-one matching), then re-ran the six original
bags: the published real counts hold (107 / 20 on the five bags; 58 of 61 and 127 of 185 on
`doubleT_obstacle`). For the synthetic results it means: set S 22 of 67 with bed placement against
29 of 68 legacy; set F on straight track holds (person 154 m anchored), on curves and at the edge
nothing is matched beyond 100 m in either mode (§2d round 4); the organizers' own objects: §2e. The
historical set F figures below were measured with legacy placement.

## 0. v0.6.2 and v0.6.3 (23.09): after the two criteria reviews

**v0.6.3** (23.09, after the second review; raw:
[`experiments_v0.6.3_real_fullrate.json`](evidence/results/experiments_v0.6.3_real_fullrate.json);
per-frame fingerprints for refactors: `scripts/output_fingerprint.py`; measured on commit
`c1c2b6a`, merged as `1210580`). `a92625e` then added two opt-in stages to the detector and
`configs/default.yaml`, both off by default; re-run on 24.09, the current code gives **identical
output on every one of the 13 759 frames**, so every number of this section holds for it
("Re-measurement" at the top). Three changes, each measured on all 13 759 frames against v0.6.2
(the per-frame outputs of both runs compared):

1. **Low-object width cap 1.6 → 2.2 m** (the envelope's width): a person lying across the track
   on a shallow bed is kept (§2d); decision and distance **identical on every real frame**.
2. **Mount calibration**: between two spaced observations the frame is no longer measured
   (it cost 10–15 ms per frame for the first ~20 s of every recording, i.e. all of a short
   control bag), and a tilt is applied from 0.75° instead of 0.5° — 1.5× the p90 error of the
   20-observation median on a moving train (§6). With the old threshold the new sampling applied
   a noise-level +0.51° roll on one ride piece and gained 6 false events; with 0.75° the decision
   and distance are **identical on every real frame** and every rig correction stays (the
   `doubleT_obstacle` rig: roll +3.02°, pitch −0.88°). The re-mount check of §6 gives the same
   residuals for every supported mount.
3. **A reported obstacle is held over one missed frame** (`tracking.hold_misses` = 1, at its
   predicted distance): the decision flickered — a confirmed obstacle missed in one frame gave
   `GO` for that frame. Events cannot change (the hold neither creates nor confirms a track);
   alarm frames and STOP episodes do:

| | v0.6.2 | **v0.6.3** |
|---|---|---|
| five obstacle-free bags: alarm frames / events / STOP episodes | 81 / 20 / 36 | **107 / 20 / 27** |
| ride (13 km): alarm frames / events / STOP episodes | 164 / 47 / 52 | **204 / 47 / 39** |
| the crossing person: frames reported of 61, first alarm | 58, frame 11 | **58, frame 11** |
| the object on the rail, its own detection: of 185 / of the 126 after the person leaves | 121 / 118 | **127 / 124** |
| `doubleT_obstacle` STOP episodes | 6 | **3** |

On 25.09 the long overhead rule was switched on (§1f): five bags 107 / 20 / 27 → **60 / 14 / 17**,
ride 204 / 47 / 39 → **197 / 46 / 39** (3.5 events per km); the person, the object on the rail and
`doubleT_obstacle` are identical frame by frame [measured 25.09].

The hold costs 27 % more false-alarm frames (245 → 311 over all obstacle-free data) and saves
25 % of the STOP episodes (88 → 66) — a braking signal that switches off for one frame and back on
is worse than one that stays on 0.1 s longer; events, the number of times a train would stop for
nothing, are unchanged.

**Where processing starts** (review of 23.09: through ROS the first 2–4 s of a played bag were
lost, so the jury's runs started after frame 0 — until v0.6.4, §3b; `scripts/start_offsets.py`,
v0.6.3, raw:
[`experiments_v0.6.3_start_offsets.json`](evidence/results/experiments_v0.6.3_start_offsets.json)).
Alarm frames / events / STOP episodes by the first processed frame:

| recording | start 0 | 10 | 20 | 30 | 40 |
|---|---|---|---|---|---|
| `doubleT_platform` | 4 / 4 / 1 | 8 / 3 / 3 | 12 / 3 / 1 | 7 / 1 / 1 | 0 / 0 / 0 |
| `roundT_doubleT` | 2 / 1 / 1 | 4 / 2 / 2 | 3 / 2 / 2 | 1 / 1 / 1 | 2 / 1 / 1 |
| `roundT_pressureGate_roundT`, `roundT_squareT_pressureGate_squareT` | 0 | 0 | 0 | 0 | 0 |
| `squareT_platform_squareT_switch` | 101 / 15 / 25 | 73 / 15 / 20 | 83 / 15 / 17 | 86 / 16 / 18 | 74 / 13 / 17 |
| **five bags** | **107 / 20 / 27** | 85 / 20 / 25 | 98 / 20 / 20 | 94 / 18 / 20 | 76 / 14 / 18 |
| person in the envelope, frames reported | 58 / 61 | 50 / 59 | 40 / 49 | 31 / 39 | 20 / 29 |
| object on the rail, own detection | 127 / 185 | 129 / 176 | 129 / 174 | 129 / 171 | 128 / 161 |

Starting at frame 0 is the worst case for the false alarms in total (107 / 20), so the figures of
this file are not flattered by it; single recordings move by a few frames (a trackside device at
48–54 m in `roundT_doubleT` and a bed fixture at 26–49 m in `doubleT_platform` are confirmed from
some start frames and not from others). What a late start costs is the first second: a person
already inside the envelope when processing begins is reported ~9–10 frames later (the track
model and the 0.5 s confirmation start from nothing); the object on the rail is found from every
start.

**v0.6.2.** The first criteria review (23.09; its report is in the git history) found three things
on the detection side: the organizers' object on the rail was missed (2 of its 185 frames by its own
detection), there were too many false stops (82 events on the 20-minute ride), and nothing showed
that the tuning was not fitted to one stretch of track. v0.6.2 is v0.6.1 plus three changes, each
measured by a full run over the 13 759 real frames (`scripts/eval_real.py`, the ride in 8 pieces
with a fresh detector each):

| run | change | five bags: frames / events | ride: frames / events | person (61 frames in the envelope) | object on the rail, its own detection: of 185 frames / of the 126 after the person leaves |
|---|---|---|---|---|---|
| v0.6.1 | — | 104 / 30 | 289 / 82 | 58, first frame 11 | 2 / 2 |
| v0.6.2a | an object straddling the envelope floor is clustered whole ([`ALGORITHM.md`](ALGORITHM.md) §3.3b) | 126 / 39 | 396 / 131 | 58, 11 | 122 / 118 |
| v0.6.2b | + it must be ≥ 0.35 m across the track and ≤ 0.8 m along it | 105 / 31 | 292 / 83 | 58, 11 | 122 / 118 |
| v0.6.2c | + confirmation 0.5 s instead of 0.3 s (`tracking.confirm_time_s`) | 81 / 20 | 258 / 61 | 58, 11 | 121 / 118 |
| **v0.6.2** | + no rail pair in the near range → clusters beyond 40 m advisory (`gauge.no_rail_range`) | **81 / 20** | **164 / 47** | **58, 11** | **121 / 118** |

* **The object on the rail** (0.45 × 0.6 × 0.3 m lying across the right rail at 56 m, top 0.10–0.15
  m above the rail-head plane): **118 of the 126 frames after the person leaves it** (v0.6.1: 2),
  121 of 185 over the whole recording (v0.6.1: 2; counted by the object's own bed-level detection
  within 0.4 m — with a 1 m window, as §0a and §1d counted before, the person's track next to it
  adds frames: 27 for v0.6.1, 146 for v0.6.2). Most of its ~21 points are below the rail head, ~3
  above the 0.12 m envelope floor; v0.6.1 had the main stage see 0–3 points and the low-object stage
  a sliver, so neither confirmed it. v0.6.2 clusters all bed anomalies and the corridor points just
  above the floor together and reports a cluster whose top reaches 0.10 m above the rail head (rail
  fittings reach 1–8 cm, §1d). Without a shape rule (v0.6.2a) the trackside devices beside the rails
  — train stops, lubricators, signalling boxes, 0.2–0.35 m tall but mounted *along* the rail — added
  49 ride events; they are 0.2–0.3 m across and 0.5–1.4 m long, the object is 0.6 m across and 0.45
  m long.
* **Confirmation 0.5 s** removed 11 of 31 events on the five bags and 22 of 83 on the ride. It
  costs 0.2 s (4.4 m at 80 km/h) for an object that appears inside the envelope, nothing for one
  tracked while it approaches: the real person, stepping in from the side, is still reported
  from frame 11, 0.3 s after entering the envelope.
* **No rails, no far alarm**: the ride's station stops (pieces 1 and 4) lost 14 events and 94
  alarm frames; nothing else changed, including the five bags (the platform-end structure of
  `squareT_platform_squareT_switch` is seen with the rails locked). Cost: at a station where the
  rails are not found an object beyond 40 m is a `CAUTION` until the train is within 40 m, and
  the verified-clear distance says 40 m.
* **Ride: 47 events in 13.0 km = 3.6 per km** (v0.6.1: 6.3 per km); alarm frames 1.5 % of the ride
  (v0.6.3, with the hold: 1.8 %; 25.09 with the long overhead rule: 46 events, 3.5 per km, 197
  alarm frames, 39 STOP episodes, §1f). By cause (`scripts/mine_objects.py`,
  `labels/new_data_objects.json`): corridor-edge structures 18, bed-level fixtures 11, far small
  clusters 7 (91–180 m), other 6, tall structures 2, hanging equipment 2, person-like 1 (a wall
  cabinet in a curve, checked by eye in v0.6). The organizers confirmed in writing (23.09) that the
  ride contains no obstacle, so every one of these is a false alarm.
* Health warnings other than latency: 196 of 13 759 frames (1.4 %, rails lost at stations and
  switches), as in v0.6.1.
* **Long range and small objects** (set F, §2d, objects ray-cast into the moving ride; round 2
  on v0.6.2, round 3 on v0.6.3 = the current code): a person on straight track first confirmed
  at 148 m (median of 6), detected in ≥ 90 % of the frames from 135 m inward (round 3, with the
  v0.6.3 hold: 149 m) and in ≥ 90 % of every 10 m band from 115 m inward; 167 m first
  confirmation with a train speed given; curves R ≈ 350 m 6 of 7 approaches (58–86 m, the
  sightline); station stops 6 of 6 from 113 m; 30 cm objects on a rail head 6 of 6 from 42–44 m
  (round 3, new draws: 42–49 m); objects on the bed between the rails are below the envelope
  (policy, ALGORITHM §3.3b). With placement anchored on the near rails the straight-track person
  is first confirmed at 154 m; on curves and at the edge nothing beyond 100 m (§2d round 4).
* **Through ROS in Docker** (§3b): the organizers' procedure on the real frames, two recordings
  into one node; the first run found and fixed a transport bug (best-effort input lost 196 of
  201 ten-megabyte clouds).

**Is the gain spread over the data?** The parameters were chosen on the frames they are scored
on — there is no held-out data with obstacles. `scripts/consistency_check.py` splits the data
into 13 subsets (the five empty recordings and the ride's eight ~2.5-minute pieces) and asks,
leaving each subset out in turn, whether v0.6.2 would still have been chosen over v0.6.1 on the
rest (fewer events there, the real person and object still found):

| subset | v0.6.1 → v0.6.2 events | subset | v0.6.1 → v0.6.2 events |
|---|---|---|---|
| `doubleT_platform` | 6 → 4 | ride piece 0 | 4 → 3 |
| `roundT_doubleT` | 2 → 1 | ride piece 1 | 20 → 11 |
| `roundT_pressureGate_roundT` | 1 → 0 | ride piece 2 | 12 → 8 |
| `roundT_squareT_pressureGate_squareT` | 0 → 0 | ride piece 3 | 4 → 2 |
| `squareT_platform_squareT_switch` | 21 → 15 | ride piece 4 | 18 → 7 |
| | | ride piece 5 | 11 → 6 |
| | | ride piece 6 | 7 → 6 |
| | | ride piece 7 | 6 → 4 |

(events = distinct confirmed track ids, as `eval_real.py` counts them.) **Fewer events in 12 of
13 subsets, more in none; chosen in every leave-one-out.** The same check for the 0.5 s
confirmation alone: 12 fewer, 0 more; for the rail rule alone: fewer in the two pieces with
station stops, equal elsewhere. This is not a held-out test of the ~15 infrastructure rules
tuned since v0.5 — those were tuned on the same recordings — but none of the v0.6.2 gains rests
on one recording.

**Threshold margins of the straddle stage** (23.09, second review: "the thresholds sit close to
the one real object"). Each threshold moved by 20–25 % either way, one full run over the 13 759
frames each, compared subset by subset with the shipped run (`scripts/consistency_check.py`;
events summed over the 13 subsets, 67 for v0.6.2):

| variant | events (13 subsets) | object on the rail, of 185 frames | person |
|---|---|---|---|
| **v0.6.2** (top ≥ 0.10 m, ≥ 0.35 m across, ≤ 0.8 m along) | **67** | **121** | 58 / 61 |
| `straddle_min_top` 0.08 | 66 | 127 | 58 / 61 |
| `straddle_min_top` 0.12 | 67 | 91 | 58 / 61 |
| `straddle_min_width` 0.30 | 68 | 121 | 58 / 61 |
| `straddle_min_width` 0.40 | 68 | 110 | 58 / 61 |
| `straddle_max_length` 0.6 | 67 | 121 | 58 / 61 |
| `straddle_max_length` 1.0 | 69 | 121 | 58 / 61 |

The false alarms barely move (66–69 events) — the rail fittings (≤ 8 cm) and the trackside
devices (0.2–0.3 m across) are well inside the thresholds — while the object loses a quarter
of its frames at a 0.12 m top threshold and 9 % at 0.40 m width. The margin that is thin is the
one on the object's side; 0.10 m sits between the fittings' 8 cm and the object's 11–16 cm, and
lowering it to 0.08 m would add object frames at no measured cost here, but at the fittings' own
height — kept at 0.10 m.

**Low-object width cap 1.6 → 2.2 m** (23.09, second review). A person lying across the track on a
shallow bed is ~1.8 m wide; the low-object stage capped clusters at 1.6 m across, so it was rejected
(set F, §2d: 2 of 6 approaches). The cap is now the envelope's 2.1 m plus margin: **the decision and
the distance are identical on every one of the 13 759 real frames** (full run,
`lowobj.max_width=2.2` against v0.6.2), and the lying person is found in 6 of 6 approaches (§2d).
Raw summaries of both:
[`experiments_v0.6.2_margins_lying.json`](evidence/results/experiments_v0.6.2_margins_lying.json).

### 0a. v0.6.1 (22.09): after the organizers' Q&A session

The organizers' recorded Q&A session ([`organizers/QA_session.md`](organizers/QA_session.md))
changed the target: the envelope to monitor is **2.1 × 3.0 m** (not our assumed 2.8 × 3.5 m),
the size criterion is **30 × 30 × 10 cm**, **hanging cables must be detected**, the **LiDAR mount
varies**, the hidden check uses rides through other tunnels plus the organizers' **synthetic
obstacles**, and there is an **object on the rail** in `doubleT_obstacle`. v0.6 implements all of
it and is measured on **every frame of every recording** the organizers gave — 13 759 frames:
the six bags (2 488) and the 20-minute ride `new_data` (11 271) — cached once
(`scripts/cache_frames.py --int16 --stamps`) and run with `scripts/eval_real.py` (the ride in 8
parallel pieces with a fresh detector each; bag receive times; 4-core sandbox shared by the
four pieces, so the latencies in these runs are inflated ×2–3 — clean timing in §3).

| | v0.5 logic (same frames, same harness) | **v0.6.1** |
|---|---|---|
| five obstacle-free bags (2 287 frames): alarm frames / events | 116 / 32 | **104 / 30** |
| 20-minute ride (11 271 frames, 13.0 km): alarm frames / events | 448 / 93 | **289 / 82** (6.3 per km, 4.1 per minute) |
| frames with a health warning other than latency (all 13 759) | — | **196 (1.4 %)**: track model lost its rails at stations / switches (v0.6: 42 %, drift monitor) |
| crossing person, frames inside the 2.1 m envelope (61): reported / first alarm | 61 / frame 8 | 58 / frame 11 (0.3 s after entering) |
| object on the rail (185 visible frames) | 24 (only while the person stood next to it) | 27 (see §1d: 126/126 with the bed-level setting) |
| hanging cable, 10 cm box on a rail (synthetic tunnel) | not reported (column / floating / hardware rules) | reported (`tests/test_envelope.py`) |
| person approaching on the moving ride (set F, §2d): first confirmed detection | ~106 m (far rule off) | **150 m median, 169 m max** (6 of 6); **177 m** with a train speed given |
| other mounts (upside down, `+x` forward, backwards, rolled / pitched) | blind / skewed corridor | recovered from the data (§6) |

**v0.6 → v0.6.1** changed only the mount calibration (§6, ALGORITHM §2b): v0.6 froze the
median of the first 5 frames, which on a moving train is the local cant, not the mount — the
pieces of the ride froze −0.97…+1.63° of "roll" for one level sensor, `roundT_doubleT` −1.55°,
`squareT_platform_squareT_switch` −0.69° of pitch — and its drift monitor then warned on 42 %
of all frames. v0.6.1 finds those rigs level (the ride's survey: −0.09°) and keeps the 3.0° of
the `doubleT_obstacle` rig. Recordings whose calibration came out the same are bit-identical
between the two runs; on the others 139 alarm frames appeared and 87 disappeared (v0.6: 83 / 25
and 258 / 74): the edge structures that make most of the false alarms react to sub-degree tilts
in both directions, so these counts carry a ±20 % spread from the mount state alone. The v0.6.1
numbers are the ones with the physically right mount.

The v0.5 row is the v0.5 detection logic run by the v0.6 harness with the calibration off
(`calibration.enabled: false`); it differs slightly from §1 (96 / 32) because of
the bag receive times, the int16 cache and the v0.6 track warm-up (§6).

## 1. Real bags at full rate (every frame, 10 Hz)

The five bags other than `doubleT_obstacle` contain no obstacle inside the gauge: every alarm
there is false. `doubleT_obstacle` has one true obstacle, the person crossing the track at
55–57 m (in the strict gauge in frames 2–72, `labels/doubleT_obstacle.json`).

**Protocol of the v0.5 runs (real data, 21.09).** Every frame of the six organizer bags cached as
`*.npy` (`scripts/cache_frames.py`, 2 488 frames), Python / numpy on the 4-core sandbox (the jury's
i7-9700E has 8 faster cores; the load of every timing run is stated). Raw per-frame results of the
v0.3 baseline are the captain's `/data/results/v0.3/<bag>.jsonl` (commit `f2c57e5`, 21.09); the
v0.5 runs are `python -m resense.cli run --npy /data/cache/<bag> --out <bag>.jsonl --quiet` with
`configs/default.yaml` of commit `9b56bdf` (merged as `82815e9`); per-bag summaries in
[`experiments_v0.5_real_fullrate.json`](evidence/results/experiments_v0.5_real_fullrate.json), the
same-machine A/B configs in §1b. The day-1 numbers on subsampled frames that this file carried
before 21.09 are superseded: they understated the 10 Hz false-alarm rate by an order of magnitude
([`archive/CAPTAIN_log_2026-09.md`](archive/CAPTAIN_log_2026-09.md), finding 2 of 21.09); their raw
files are in [`archive/results/`](archive/results/).

| bag | frames | v0.3 alarm frames / events / advisory | **v0.5 alarm frames / events / advisory** | v0.5 first alarm (frame) | v0.5 alarm distances | what alarms in v0.5 |
|---|---|---|---|---|---|---|
| `doubleT_obstacle` (stationary, person crossing) | 201 | 76 / 3 / 199 | **69 / 1 / 199** | 7 | 55.5–56.6 m | the person only (v0.3: also the column row at 17–19 m and 34 m, 2 false events) |
| `doubleT_platform` | 345 | 178 / 29 / 110 | **15 / 4 / 271** | 2 | 3.0–114.5 m | a 2.1 m tall, 0.5 m wide post at 85–87 m left of the axis (10 frames; 0.1 m under the column rule), one frame of a 5 m long 0.2 m high strip at the nose at frame 177 and one 4-voxel cluster at 104.5 m |
| `roundT_doubleT` | 252 | 126 / 20 / 140 | **0 / 0 / 226** | — | — | nothing (v0.3: columns and wall segments of the diverging double-track section, pulled in by the half curvature and the yaw jitter) |
| `roundT_pressureGate_roundT` | 268 | 106 / 19 / 135 | **16 / 5 / 262** | 48 | 42.0–77.9 m | five duct / cabinet fragments at \|dy\| = 1.5–1.6 m, 42–78 m, 1–8 frames each (inner edge 0.05–0.15 m inside the 1.40 m gauge) |
| `roundT_squareT_pressureGate_squareT` | 545 | 87 / 19 / 396 | **5 / 3 / 499** | 99 | 101.3–127.2 m | three far clusters at 101–127 m (6–16 voxels), one of them lasting 3 frames |
| `squareT_platform_squareT_switch` | 877 | 504 / 105 / 680 | **60 / 20 / 779** | 67 | 71.9–119.2 m | the platform-end structure at 82.9 m while the train stands at the platform (2.2 × 0.4 × 1.2 m, lowest point at the bed, 5–8 voxels, 15 events of 1–7 frames, ~50 frames): a low ramp / rail at dy +1.2…+1.8 m by the single-frame axis that the run's left-bending curvature (R ≈ 3 km from the hall walls) puts at +0.5…+1.0 m; plus four single-frame far clusters at 87–119 m |
| **five obstacle-free bags** | 2 287 | **1 001 / 192** / 1 461 | **96 / 32** / 2 037 | | | |

The per-bag "what alarms" column and the cause table below were written for the first cut of v0.5
(89 / 29); the final defaults carry the two safety tweaks of the review of 22.09
(`wall_face_min_height` 2.0 m and `floating_max_height` 1.2 m so that a person on a platform edge
stays an obstacle; `walls_max_yaw` 0.09), which add 3 alarm frames / 1 event on `doubleT_platform`
(a near strip at the nose in frame 2) and 4 / 2 on the switch bag, and change nothing on the person.

Renders (`img/`): `roundT_doubleT_0145_v03.png` vs `roundT_doubleT_0145_v05.png` (the v0.3 axis
pulls the column row of the diverging double-track tunnel into the corridor, v0.5 follows the
rails), `squareT_platform_switch_0400_v03.png` vs `_v05.png` (the train standing at the platform:
roof strips and the hall end wall are advisory in v0.5), `doubleT_obstacle_0030_v05.png` (the person
on the track at 55.7 m; the whole bag as `video/doubleT_obstacle_offline.mp4`).

On the labels of `doubleT_obstacle` (`resense eval --npy /data/cache/doubleT_obstacle --gt
labels/doubleT_obstacle.json --text`, 71 in-gauge person frames): v0.3 recall 63/71, first alarm
frame 9, 13 false-alarm frames / 2 events (the column row); **v0.5 recall 66/71 (93 %), first alarm
frame 7, 3 / 0 (frames 73–75, the person 0.1–0.2 m outside the gauge) false-alarm frames / events**;
the person is confirmed inside 50–62 m in 69 (frames 7–75, one track) consecutive frames.

Evolution (the day-1 rows were measured on 272 subsampled frames and are kept for the
record; from v0.4 on the numbers are full rate):

| version | change | false-alarm frames / events on the empty bags | person recall (`doubleT_obstacle`) | ms/frame (4-core sandbox) |
|---|---|---|---|---|
| v0.0 (15.09) | fixed lateral centre, box corridor, raw DBSCAN | 149 / — (231 subsampled frames) | — | 42–1461 |
| v0.1 | rail-based self-calibration, rail-relative gauge, voxelised range-normalised DBSCAN, zones | 92 / — | — | 32–75 |
| v0.2 | wall-based yaw/curvature, robust two-stage floor fit | 76 / — | — | 38–75 |
| v0.3 (f2c57e5) | nearer-boundary rule, gauge 1.4 m, hardware/linear/wall filters, corridor validity range, overhead demotion | 67 / — subsampled; **1 001 / 192 at full rate** (2 287 frames) | 63/71, first alarm frame 9 | 48–83 mean, 84–132 p95 |
| v0.4 (f4e311f, 21.09) | ego-speed estimate + 5-frame accumulation beyond 40 m, verified bed extrapolation, retro rule, smear guard | 1 016 / 187 (+1.5 % frames, +9 % beyond 60 m) | 64/71 (one frame gained by lateral smear), first alarm 9 | 73–133 mean, 112–193 p95 |
| **v0.5 (real data, 21.09)** | axis: yaw from the rail slabs, curvature 1/R from the walls with the tangent fixed (v0.3 applied half the curvature), rate limits, side-agreement caps; height reference trusted 20 m beyond the bed fit (60) or as verified; five infrastructure signatures (column, elevated, floating, edge, wall face); zone / hit history over 10 frames, persistence in seconds; no merging below 1 m/s, lateral smear guard; vectorised binning | **89 / 29** | **66/71 (93 %)**, first alarm frame 7 | 43–84 mean, 51–171 p95 (quiet 4-core sandbox, §3); v0.3 code back to back: 56 / 71 and 71 / 76 on the two reference bags |

### 1b. False alarms by cause (why v0.3 alarmed on 44 % of the frames) and what removed them

Method: every confirmed gauge track id of the v0.3 full-rate runs on the five empty bags was
listed with its frames, distance range, lateral offset, size, lowest / highest point above
the rail head, voxel count, confidence and intensity, the worst cases were rendered
(`resense run --render --x-max 160`) and the raw points of the far structures dumped in
corridor coordinates. Each track is classified by the signature of its median cluster (first
matching rule); a frame can carry several causes, so the rows add up to more than the totals.
Counts are alarm frames / events:

| cause (v0.3 track signature) | `doubleT_platform` | `roundT_doubleT` | `roundT_pressureGate_roundT` | `roundT_squareT_pressureGate_squareT` | `squareT_platform_squareT_switch` | **total** | v0.5 |
|---|---|---|---|---|---|---|---|
| beyond the bed fit + 20 m: height reference (extrapolated bed 0.3–0.65 m off at 85–105 m lifts far rails / switch parts into the low zone and pulls the roof, h ≈ 4 m, into the polygon top) | 5 / 4 | 35 / 6 | 0 | 21 / 2 | 442 / 35 | **503 / 47** | — |
| column / post: > 2.2 m tall, < 1 m wide, pulled onto the axis by the yaw error in the diverging double-track section | 16 / 2 | 70 / 7 | 0 | 0 | 8 / 3 | 94 / 12 | — |
| elevated wide: lowest point > 1.2 m, > 2 m wide (roof strips / beams at 104–130 m of the stopped train) | 0 | 0 | 0 | 0 | 356 / 9 | 356 / 9 | — |
| floating small: lowest point > 0.7 m, < 1.5 m tall, < 1 m wide (signs, lamps on the wall at 46–73 m) | 109 / 8 | 3 / 1 | 1 / 1 | 5 / 1 | 10 / 4 | 128 / 15 | — |
| edge fragment: \|lateral\| > 1.2 m, long and low (duct / bench segments of the round tunnel at 3–35 m) | 0 | 0 | 90 / 11 | 12 / 4 | 17 / 4 | 119 / 19 | — |
| other corridor-edge structure at \|lateral\| > 1.2 m (platform-edge posts at 23–25 m, column row at 17–19 m, cabinets, signs) | 99 / 5 | 33 / 5 | 25 / 7 | 62 / 12 | 13 / 5 | 232 / 34 | — |
| wall / portal face (the platform-hall end wall at 72–78 m of the stopped train, full height, corridor centre empty) | 0 | 0 | 0 | 0 | 206 / 13 | 206 / 13 | — |
| other | 32 / 9 | 2 / 1 | 0 | 0 | 198 / 32 | 232 / 42 | — |
| **all** | 178 / 29 | 126 / 20 | 106 / 19 | 87 / 19 | 504 / 105 | **1 001 / 192** | **89 / 29** (per bag: 12 / 3, 0 / 0, 16 / 5, 5 / 3, 56 / 18) |

Three findings behind the causes, all measured this round:

1. **The axis bent half as much as the tunnel.** `estimate_axis_from_walls` fitted each
   boundary with a free quadratic, stored the quadratic coefficient (1/2R) as `curvature` and
   `center_y` applied it as 1/R: on a hand-made R = 800 m scene the estimated curvature was
   6.2e-4 against 1.25e-3 and the axis was 2.4 m off at 100 m (`tests/test_algorithm.py::
   test_axis_follows_a_curved_track`). On the curve bags the free fit also traded yaw against
   curvature: the rail-pair midpoints measured in three slabs (4–12, 12–20, 20–30 m) show the
   v0.3 axis 0.8–1.0° off the rail direction on `roundT_pressureGate_roundT` #100/#150/#200,
   `roundT_doubleT` #60/#145, `doubleT_platform` #100/#300 (up to 2.9° on `roundT_doubleT`
   #120), its yaw saturated at the ±2° clip in every moving bag, and it jumped by 0.5–1.2°
   between frames (p90–p99 of |Δyaw| on `roundT_doubleT` and `doubleT_platform`; a train at
   15 m/s on R = 700 m yaws 0.12° per frame). The rail-ridge profile itself was built in
   absolute Y, so in a curve the ridges smeared over 0.5 m and the centre was biased (0.9 m on
   the hand-made scene). v0.5: profile in the previous axis' coordinates, yaw and centre from
   the rail slabs, curvature 1/R from the walls with that tangent fixed, rate limits of 0.17°
   and 1e-4 m⁻¹ per frame, straight bonus only with two agreeing boundaries, range caps with
   one boundary (120 m) or disagreeing ones (60 m). Frame-to-frame |Δyaw| on the moving bags
   fell from p95 0.2–0.7° to 0.06–0.17° (v0.5 runs, `roundT_doubleT` / `doubleT_platform`).
2. **The height reference beyond the bed fit is not usable for the polygon's top and
   bottom.** On `squareT_platform_squareT_switch` frames 400/500/650 the run's EMA floor was
   −1.67 / −1.69 / −1.73 m at 72 / 85 / 105 m against a measured bed (5th percentile of Z
   within ±1 m of the axis) of −2.00 / −2.34 / −2.22 m: 0.3–0.65 m too high, so a roof beam at
   h = 4.1 m read 3.4–3.6 m (inside the 3.5 m top) and switch rails at h ≈ 0 read 0.3–0.5 m
   (inside the 0.12 m low zone); the 353- and 346-frame events at 127–130 m and 104–105 m
   (ids 325, 332) and the ~90 frames at 147.5 m are this. The bed fit ends at 50–110 m on the
   bags (p10–p90), the v0.4 verification reaches 105–145 m; v0.5 trusts the reference 20 m
   beyond the fit or as far as verified (was 60 m unverified).
3. **Corridor-edge structures at \|dy\| = 1.5–1.6 m are 0.1–0.2 m outside the 1.40 m gauge.**
   Ducts and benches of the round tunnels, the platform edge (1.6 m) and its fittings, the
   column row of the double-track tunnel (1.7 m) all sit at that distance; any axis error
   above 0.1 m at 20–80 m makes a sliver of them "inside" for a few frames, and three such
   frames were an alarm. The near axis is now good to a few centimetres (rails), the
   persistence needs 60 % of the last ten hits inside and 60 % matched, and the edge / column
   / floating / wall-face signatures cover the shapes; what remains is measured below.

**Ablation (all six bags, every frame, same code = commit 9b56bdf (merged as 82815e9), one lever
group switched off at a time by `--config`; five-bag alarm frames / events, and the person of
`doubleT_obstacle`: recall on the 71 labelled frames, first alarm frame):**

| variant | five empty bags: alarm frames / events | `doubleT_obstacle`: recall, first alarm, false frames / events | reading |
|---|---|---|---|
| v0.3 (f2c57e5 results) | 1 001 / 192 | 63/71, 9, 13 / 2 | baseline |
| v0.5 code with the v0.3 switches (`rails_yaw_enabled: false`, rate limits and caps 0, `walls_max_yaw: 0.035`, `floor_valid_margin: 60`, verification / retro / accumulation off, signatures 0, zone window 5, `confirm_time_s: 0`) | 785 / 155 (reviewer's run of 22.09: platform 212 / 20, `roundT_doubleT` 87 / 16, gate 94 / 15, `roundT_squareT` 0 / 0, switch 392 / 104) | 65/71, 8, 1 / 0 | only the curvature fix and the rail profile in curve coordinates remain: this is what the axis bug alone cost |
| **v0.5 first cut (the code the ablations were run on)** | **89 / 29** | **66/71, 7, 3 / 0** | |
| **v0.5 final defaults** (review tweaks: `wall_face_min_height` 2.0, `floating_max_height` 1.2, `walls_max_yaw` 0.09) | **96 / 32** | **66/71, 7, 3 / 0** | +7 frames / +3 events for keeping a person on a platform edge an obstacle |
| − axis levers (rail yaw, rate limits, side caps off, yaw clip 2°) | 171 / 56 (gate 57 / 8, switch 89 / 41) | 62/71, 11, 2 / 0 | |
| − infrastructure signatures (column, elevated, floating, edge, wall face = 0) | 513 / 62 (switch 374 / 37, `roundT_doubleT` 36 / 6) | 66/71, 7, 3 / 0 | |
| − height-reference margin (`floor_valid_margin: 60`) | 391 / 46 (switch 353 / 33) | 66/71, 7, 3 / 0 | |
| − history rules (`min_hit_fraction: 0`, zone window 5 / 0.5) | 143 / 44 | 68/71, 5, 1 / 0 | |
| − accumulation (`accumulation.enabled: false`, estimator off) | 89 / 29 (identical: without a given speed nothing is merged in the offline runs) | 66/71, 7, 3 / 0 | |
| + `confirm_time_s: 0.5` (5 frames at 10 Hz) | 69 / 21 | 66/71, 7, 3 / 0 | latency 0.5 s = 11 m at 80 km/h instead of 0.3 s = 6.7 m; not shipped in v0.5: P4's tests pinned the 3-frame confirmation (`tests/test_cli.py --repeat 3`, `tests/test_core.py` 4-frame loops); v0.6.2 ships 0.5 s (§0) |
| + edge margin 0.05 m + 0.20 m per 100 m | not run | not run | |
| + edge margin 0.15 m per 100 m only | not run | not run | |
| + `confirm_time_s: 0.5` and edge margin 0.05 + 0.20 / 100 m | not run | not run | |

Reading (captain's runs of 22.09 on the six cached bags, every frame, commit 9b56bdf with one lever
group switched off per row by `--config`): the two levers that matter most are the **infrastructure
signatures** (without them 513 alarm frames — the platform-hall end wall, roof strips and posts of
the stopped train come back, 374 frames in the switch bag alone) and the **height-reference range**
(391 frames: the unverified extrapolation lifts far rails and pulls the roof into the polygon
exactly as §1b finding 2 describes). The **axis levers** cut 171 → 89 (first cut) and, on the
person, bring the first alarm from frame 11 to 7 (the rail-slab yaw keeps the person inside the
gauge as soon as they are). The **history rules** trade 54 alarm frames for two frames of person
recall and a first alarm two frames earlier (68/71, frame 5 without them). A **0.5 s confirmation**
(`tracking.confirm_time_s: 0.5`) removes another 20 frames / 8 events at no cost on the person (he
is confirmed at frame 7 either way, 0.5 s after entering the gauge) and is the first knob to turn if
the control bag shows more short-lived false alarms; it stayed at 0.3 s in v0.5 so that the 3-frame
confirmation the synthetic tests and the dry-run checker assumed kept holding (v0.6.2 ships 0.5 s,
§0). The accumulation row is identical to the defaults because the offline runs have no train speed
and nothing is merged; the given-speed behaviour is measured in §2c. The edge-margin variants were
not run.

**Accumulation default.** The multi-frame accumulation stays in the code and stays *enabled for a
given speed* (the node's `ego_speed_mps` / odometry, `eval` sequences; P4's CLI tests pin this
path), but the LiDAR-only estimator that fed it in v0.4 is **off by default**
(`accumulation.estimate_speed: false`): with the estimator on, the same code alarmed on 119 frames /
30 events of the five empty bags instead of 88 / 27 (pre-vectorisation copy of the code; the final
code measures 89 / 29, `roundT_pressureGate_roundT` 8 → 31 frames,
`roundT_squareT_pressureGate_squareT` 5 → 20), it did not change the person's recall or first alarm
on `doubleT_obstacle` (66/71, frame 7, with the stopped-train guard), and it costs 7–8 ms per frame;
the final-code number is in the ablation row above. The synthetic gain of §2b (person 189 vs 178 m
on the tunnel at 22 m/s) had no real-data counterpart then (no moving recording with an obstacle;
since 24.09 there is one, and the estimator was measured on it: §9); with a given speed the
given-speed rows of §2c and the given-speed runs of the ablation table are the measured behaviour.
Regression rule of [`EVALUATION.md`](EVALUATION.md) §3.6: false-alarm frames on E 1 001 → 96 and p95
latency (§3: 51 vs 71 ms on `roundT_doubleT`, 60 vs 76 ms on `doubleT_obstacle`, back to back) are
both better than v0.3; on R the first alarm frame is 7 (≤ 9) and the recall 66/71 (≥ 64/71).

### 1c. v0.5 on the organizers' extended recording (22.09, unlabelled, every frame)

The 20-minute bag `new_data` (221 split files, 11 271 frames, seven stops, top speed 77 km/h,
tunnels / curves / stations / a switch; [`DATASET.md`](DATASET.md) "Extended dataset") streamed once
through the v0.5 defaults, a fresh detector per 51-frame file, no speed given. No labels exist, so
these are false-alarm numbers on a ride, not recall:

| recording | frames | alarm frames | alarm events | events / hour | events / km | latency mean / p95 / max |
|---|---|---|---|---|---|---|
| `new_data` (1 200 s, ≈ 13 km) | 11 271 | 358 (3.2 %) | 102 | 306 | 7.9 | 41 / 74 / 157 ms |
| five obstacle-free organizer bags (230 s, §1) | 2 287 | 96 (4.2 %) | 32 | ≈ 500 | — | see §3 |

Causes, by the median lateral offset of the 102 events (per-event rows in
`extended_dataset_intake.json`): 40 at the left gauge edge (contact-rail side, brackets 0.6 m above
the rail head flipping into the gauge at 40–100 m), 16 at the right edge (column row in double-track
sections), 28 central — 11 of them in the five files where the track model is not locked (a switch,
platform ends) and 17 with ≤ 15 points at 60–140 m — and 18 in between. The biggest single family is
therefore the left edge (the mirror image of the column-row family of §1b), the second the unlocked
track model at stations and switches; both were on P3's list of 22.09 (DATASET "What follows"; the
ride's current causes: §0). The tracker's measured-interval gate (§1b review fix) is exercised for
real here: the last third of the recording has holes of 1.2–7.1 s between frames.

### 1d. v0.6 on all real data: the variants that led to the defaults

Every row is a full run over the 13 759 frames (`scripts/eval_real.py`, ~14 min each); the
five-bag column sums `doubleT_platform`, `roundT_doubleT`, `roundT_pressureGate_roundT`,
`roundT_squareT_pressureGate_squareT`, `squareT_platform_squareT_switch`.

| run | what changed | five bags: frames / events | ride: frames / events | person (61) | object on the rail (185) |
|---|---|---|---|---|---|
| v0.5 logic | — | 116 / 32 | 448 / 93 | 61, first 8 | 24 |
| v0.6a | envelope 2.1 × 3.0 m, calibration, health, **low-object stage reporting every bump above the bed** | 1 310 / 256 | 6 391 / **1 482** | 54 | 26 |
| v0.6b | + a low object must reach 5 cm below the rail head | 528 / 99 | 1 502 / 345 | 61 | 102 |
| v0.6c | low stage off; far-field rule, near-axis tall objects allowed | 393 / 49 | 857 / 121 | 61 | 25 |
| v0.6d | + columns ≥ 0.25 m wide demoted anywhere, `edge` at 1.0 m, edge margin 0.15 m / 100 m, far clusters ≤ 3 m long and grounded; low stage with candidates ≥ 3 cm above the rail head | 81 / 21 | 239 / 60 | 58, first 11 | 29 |
| v0.6f | low stage: the cluster's top at the rail head, candidates from 5 cm excess, own clustering radius | 412 / 169 | 1 735 / 734 | 58 | **170** |
| v0.6g | low stage: every candidate ≥ 3 cm above the rail head again | 85 / 27 | 272 / 88 | 58 | 29 |
| v0.6 (h) | + a low object needs 5 hits (0.5 s) | 83 / 25 | 258 / 74 | 58, first 11 | 27 |
| **v0.6.1 (shipped)** | mount tilt over 20 s instead of 5 frames, median drift monitor (§6) — the detection logic of v0.6h | **104 / 30** | **289 / 82** | **58, first 11** | 27 |

**The bed is full of objects.** v0.6a reported every bump more than 7 cm above the learned bed
cross-section inside the envelope: 1 350 of the ride's 1 482 events were low-object events. The ones
looked at (`new_data_46` frames 26–39, a straight section at 20 m/s): 0.3 m wide, 5–12 cm tall bumps
in the middle of the track approaching at the train's speed (train-control inductors, drain covers),
0.6–1 m wide transverse ones (cable crossings), all with their top 15–30 cm *below the rail head*.
Geometrically a 30 × 30 × 10 cm box lying on the bed is the same thing. The train envelope starts at
the rail head, so such an object is below it; v0.6 reports low objects that reach the rail-head
plane.

**The rail area is full of objects too.** v0.6f let a cluster through when its top reached the rail
head (candidates from 5 cm above the bed): 734 events on the ride, at \|lateral\| 0.5–0.9 m — the
rails and just inside them (guard rails in curves, joints, fastenings), 3–43 m away, tops 1–8 cm
above the rail head (median 3 cm), excess over the bed 0.14 m median; no single-frame threshold on
height, width, excess or voxel count separates them (measured on 1 330 false clusters of 12 ride
files vs 125 clusters of the object). v0.6f finds the object in 170 of 185 frames and would stop the
train every 1.6 s. Shipped: every low candidate must be ≥ 3 cm above the rail head and the object
must be seen in 5 frames (the false clusters flicker for 2 frames median, 3 at the 90th percentile):
18 low events on the ride, a 10 cm box lying on a rail head found at 10–25 m (synthetic tunnel), the
real object in 2–4 of the 126 frames after the person leaves it. `lowobj.min_point_top: -1` with
`min_top: 0` restores the v0.6f behaviour for a line known to be clean.

**Why the real object is missed — corrected 23.09** (a jury-style review questioned the height,
and we re-measured it on the frames with the final v0.6.1 calibration): the object's top is
**0.10–0.15 m (median 0.13 m) above the detector's rail-head plane** in the 111 frames after the
person leaves — at the 0.12 m floor of the envelope, not "4–5 cm above its rail" as written here
before (that figure was taken against the rail ridge, ~6 points at 56 m, and is not confirmed).
What the pipeline produces at its position: **nothing in 99 of the 111 frames** — 0–3 points
above the envelope floor, below the main stage's cluster minimum — and a 3-point low-object
sliver 0.03–0.07 m high in 12 frames, too few hits to confirm. The object falls *between* the two
stages; clustering an object that straddles the envelope floor as one object is the fix to try
next (done in v0.6.2, §0).

**Mount roll changes what "on the rail" means.** The rail pair of `doubleT_obstacle` has its right
head 8 cm above the left over 4–30 m on a straight, stationary track: that rig is rolled by
3.0–3.2°. Without the correction (v0.5) the object reads 0.15–0.2 m above the *mean* rail level and
the corridor stage saw its top; with it, it is 0.10–0.15 m above the rail-head plane, at the
envelope floor, where it falls between the stages (above). The calibration is right (the gauge is
defined in the rail plane); the organizers said the hidden data use the mount of the empty-tunnel
rides, on which the calibration finds `roundT_doubleT` and `doubleT_platform` level within 0.5°
(v0.6.1, §6; the −1.0…−1.6° v0.6 measured on `roundT_doubleT` was the 5-frame window). On 24.09 the
organizers confirmed it: the test bags use the mounts of the provided ones, the LiDAR 1 075 mm above
the rail head on the train's centreline
([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md)).

**Where the ride's remaining events came from** (the v0.6h run, 74 events; the current 47: §0;
`scripts/mine_objects.py`, classes by median geometry, `labels/new_data_objects.json`):
corridor-edge structures 21 (at \|lateral\| 0.9–1.2 m, 30–70 m; a quarter of them at the station of
files 52–55), station / platform-end structures 13, low objects 12 (+6 low tracks classed
otherwise), far small clusters 11 (105–180 m, 8–12 points), hanging equipment 8 (1.5–2.7 m above the
rail head, 50–80 m), tall structures 7, person-like 2 (both infrastructure, below). 874 tracks were
confirmed on the ride in total, 800 of them advisory (mostly the edge structures). The 11
person-like tracks were checked by eye on close-ups (`img/new_data_person_like_check.png`): poles
from the bed to the vault, cabinets, signs, the wall of the R ≈ 350 m curve — no person anywhere
near the track, as the organizers said.

**Per bag (v0.6.1):** `doubleT_platform` 5 / 6 (low objects at the platform, 4 events),
`roundT_doubleT` 3 / 2, `roundT_pressureGate_roundT` 2 / 1, `roundT_squareT_pressureGate_squareT`
0 / 0, `squareT_platform_squareT_switch` 94 / 21 (v0.6: 75 / 17 with a spurious −0.69° pitch) —
the platform-end structure at 82–84 m while the train stands at the platform (§1), unchanged
since v0.5: the station-curvature limitation of [`ALGORITHM.md`](ALGORITHM.md) §6.

### 1e. Opt-in paths (24.09): the near-bed path measured, the far-rail check (measured in §1f)

Two stages added by `a92625e` (24.09) ship switched off (`false` in both parameter files and the
code defaults); neither changes a default number of this file. 25.09: the organizers answered that
a 30 × 30 × 10 cm object on the bed between the rails is not an obstacle
([`organizers/answers.md`](organizers/answers.md) §8), so the near-bed path below is not needed; it
stays off for good, its ride and set F re-run is dropped, and the measurements stay as the record.

**Central near-bed path** (`lowobj.near_enabled`, ALGORITHM §3.3b): it accepts a bed anomaly
lying entirely within ±0.55 m of the axis and 30 m of the train, below the rail head — meant for the
30 × 30 × 10 cm object on the bed that the default policy leaves below the envelope (§2d round 2,
reading 5). Measured with the gates of `a92625e` (excess over the bed 0.08 m, ≥ 5 voxels,
≥ 0.24 m across, ≤ 0.75 m along) by the criteria review of 24.09 (its report is in the git
history) and by P4 on set O:

| | defaults | near-bed path on | source |
|---|---|---|---|
| five obstacle-free bags: alarm frames / events / STOP episodes | 107 / 20 / 27 | 1 035 / **145** / 42 | review of 24.09 on `d58567e` (code of `4cd32d6`), all 13 759 frames [team record, unverified: raw not committed] |
| ride: alarm frames / events / STOP episodes | 204 / 47 / 39 | 3 730 (33 %) / **667** / 247 | same run |
| crossing person 58 of 61, object on the rail 124 of 126 | — | unchanged | same run |
| set F, objects on the bed from 150 m (straight files): 30 × 30 × 10 cm box / 0.3 m cube / dog-sized box 0.6 × 0.3 × 0.45 m | 0 / 1 / 1 of 6 (round 3) | **0** / 2 / 5 of 6 (cube at 9–15 m, dog from 19.5–50.2 m); 69–75 off-object detections per set against 0–6 | same review [team record, unverified] |
| set O (§2e): STOP frames on the inside objects / background alarm frames / IDs | 303 / 3 / 2 | 303 / 466 / 106 | P4, 24.09 [team record, re-checked against [`experiments_p4_fake_labelled.json`](evidence/results/experiments_p4_fake_labelled.json)] |

626 of the 667 ride events are low-object tracks, first confirmed at a median 19 m (10–90 %:
8–28 m), median |lateral| 0.02 m: the central bed fixtures of §1d (train-control inductors, drain
covers). The path finds no 30 × 30 × 10 cm box and gives 51 false events per km of the ride, so it
stays off.

**The gates of `537e220` and the box fix `7df1796` (24.09).** `537e220` retuned the gates to reject
those fixtures (excess 0.08 → 0.05 m, ≥ 10 voxels, ≤ 0.55 m across, ≥ 0.18 m along the track, bed
support in ≥ 20 of the lateral template bins of each 2 m bin) and then missed the synthetic
30 × 30 × 10 cm box on the bed (`tests/test_envelope.py`, 12 / 20 / 28 m; `main` red). At those
ranges the box is one scan line, 5–10 voxels and 0.03 m along the track, and the ≥ 10 voxel and
≥ 0.18 m gates each rejected it alone; `7df1796` sets `near_min_points` back to 5 and
`near_min_length` to 0 and keeps the other gates. Measured with `lowobj.near_enabled: true`,
`scripts/eval_real.py --jobs 2` on the six recordings (STOP episodes and the person / rail-object
counts as `scripts/start_offsets.py` counts them) and `scripts/score_fake_objects.py` on set O
[real and organizers' synthetic, 24.09; raw runs not committed]. The shipped default (path off)
reproduces the re-measurement above exactly, and the `4b5786b` row reproduces the review's
five-bag numbers of the first table.

| near-bed parameters | five recordings: alarm frames / events / STOP | `doubleT_obstacle` person, object | set O #2 / #3 / #4 STOP frames | set O background alarm frames / IDs |
|---|---|---|---|---|
| defaults (path off) | 107 / 20 / 27 | 58/61, 127/185 | 19 / 23 / 0 | 3 / 2 |
| `4b5786b` (excess 0.08, ≥ 5 voxels) | 1 035 / 145 / 42 | 58/61, 127/185 | 19 / 23 / 0 | 466 / 106 |
| `537e220` (+ width ≤ 0.55 m, bed support 20 bins, ≥ 10 voxels, ≥ 0.18 m long, excess 0.05) | 141 / 28 / 33 | 58/61, 127/185 | 19 / 23 / 0 | 95 / 17 |
| **current** (`537e220` with ≥ 5 voxels, no length minimum) | **459 / 107 / 72** | 58/61, 127/185 | 19 / 23 / 0 | 319 / 113 |

Each gate added alone to the `4b5786b` parameters (five recordings, alarm frames / events / STOP):
width ≤ 0.55 m 531 / 108 / 70; bed support 1 023 / 135 / 41; ≥ 10 voxels 763 / 81 / 32;
≥ 0.18 m 681 / 75 / 31; excess 0.05 1 061 / 169 / 50. The gates that did most of the reduction are
the ones the box cannot pass: the remaining false events are central bed fixtures (median
|lateral| 0.00 m, width 0.30 m, 7 voxels, first seen at 15 m) with the box's single-scan-line
signature. The ride and set F were not re-run. The path stays off.

**Far-rail check** (`track.rails_far_check_enabled`, `resense/track.py`: a wall-derived curvature
that contradicts rails visible in two slabs beyond the near fit is replaced, for station halls whose
walls look like a curve while the track is straight): unmeasured on 24.09; measured on 25.09 on the
six recordings and set O, where it never fires (§1f). It stays off.

### 1f. Late candidates of 25.09: short signatures, long overhead rule, far-rail check

Two detector rules were added on 25.09 behind flags that were 0 (off) in both parameter files
(`fa99929`, `8631e4c`; the merged `8932f3a` passed the regression gate with every gated metric the
same). The same day both were decided on the ride against pre-registered criteria ("Decision of
25.09 on the ride" below, [`CAPTAIN.md`](CAPTAIN.md) action 11): the long overhead rule is on
(3.0 m, `935eecf`), short signatures stay off. The first measurements below cover the six
recordings and set O: `scripts/regression_gate.py` against the first baseline of 25.09
([`regression_baseline_2026-09-25.json`](evidence/results/regression_baseline_2026-09-25.json)),
native path, `--jobs 2`, receive stamps [real and organizers' synthetic, 25.09; raw gate runs not
committed].

- **Short signatures** (`cluster.short_signature_max_length`, with
  `short_signature_max_distance`; ALGORITHM §3.3): the `elevated` and `floating` shapes no longer
  demote a cluster at most that long along the track and that far away. At 3.0 / 100 m the
  per-frame output is identical to `scripts/short_signature_experiment.py` on all 3 998 frames and
  reproduces the P4 record exactly (§2e: 303 → 352 inside STOP frames; five bags 107 / 20 / 27 →
  113 / 22 / 29; +3 false STOP frames on `small_outside_near`). The gate **fails** on 5 gated rows:
  `doubleT_platform` events and STOP episodes, `squareT_platform_squareT_switch` events and STOP
  episodes, `small_outside_near` false STOP. The two new events: `doubleT_platform` id 129,
  frames 150–154, a 0.26 × 0.49 × 1.12 m wall-mounted object at 36.1 m, lateral −1.19 m, bottom
  1.87 m (the envelope edge); `squareT…` id 86, frame 148, 85.0 m, lateral −1.09 m.
- **Long overhead rule** (`cluster.floating_long_min_length`; ALGORITHM §3.3): the `floating`
  shape (bottom > 0.7 m, < 1.2 m tall, < 1.0 m wide) also applies near the axis to a cluster
  longer than the threshold along the track: a duct, tray or beam along the track. A hanging
  cable (short along the track, or taller than 1.2 m) and every organizer object (0.3–2.2 m long)
  are left alone. At 3.0 m (4.0 m gives the same) it changes 69 frames (47 decisions), all in
  `squareT_platform_squareT_switch` and all at ~104 m; the other five recordings and
  `cloud_with_fake_obj` are identical per frame. The gate **passes** (2 gated rows better).
- **Far-rail check** (`track.rails_far_check_enabled`, the existing flag meant for station-wall
  curvature): **measured, no effect.** The output is identical on all 3 998 frames: it never
  changes the model. Of the 877 `squareT…` frames, 122 have no wall side, 248 a curvature below
  its threshold, and 507 no far rail pair in two slabs between 30 and 82 m (288 found one slab,
  219 none): the station's far rails are not visible enough for it to act.

Alarm frames / events / STOP episodes per recording (`doubleT_obstacle` labelled: 185 of 246, first
frame 11, person 58 of 61, rail object from frame 75 124 of 126, fp events 0 in every column):

| recording | default | short 3.0 / 100 | long 3.0 | short + long |
|---|---:|---:|---:|---:|
| `doubleT_obstacle` | 188 / 2 / 3 | 188 / 2 / 3 | 188 / 2 / 3 | 188 / 2 / 3 |
| `doubleT_platform` | 4 / 4 / 1 | **9 / 5 / 2** | 4 / 4 / 1 | 9 / 5 / 2 |
| `roundT_doubleT` | 2 / 1 / 1 | 2 / 1 / 1 | 2 / 1 / 1 | 2 / 1 / 1 |
| `roundT_pressureGate_roundT` | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| `roundT_squareT_pressureGate_squareT` | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| `squareT_platform_squareT_switch` | 101 / 15 / 25 | **102 / 16 / 26** | **54 / 9 / 15** | 55 / 10 / 16 |
| **five obstacle-free** | **107 / 20 / 27** | **113 / 22 / 29** | **60 / 14 / 17** | **66 / 16 / 19** |
| gate against the baseline | — | FAIL, 5 rows | PASS, 2 better | FAIL, 3 rows |

Set O (`cloud_with_fake_obj`), STOP frames (first STOP; advisory-only frames); the long rule leaves
every object identical per frame:

| object | default | short 3.0 / 100 |
|---|---:|---:|
| `big_center` 2 × 2 m centre | 207 (98.0 m; 0) | 207 (98.0 m; 0) |
| `small_center` 0.3 m floating | 19 (34.0 m; 11) | **30 (52.5 m; 0)** |
| `small_on_rail` | 23 (42.7 m; 0) | 23 (42.7 m; 0) |
| `small_edge_inside` | 0 (—; 25) | **7 (14.5 m; 18)** |
| `big_edge_inside` | 0 (—; 0) | 0 (—; 0) |
| `big_above` 2 × 2 m, envelope top | 12 (101.3 m; 37) | **43 (101.3 m; 6)** |
| `long_low_on_rails` | 42 (82.2 m; 0) | 42 (82.2 m; 0) |
| `thin_hanging` | 0 (—; 0) | 0 (—; 0) |
| `small_outside_near` (outside): false STOP | 0 (24 advisory) | **3** (21 advisory) |
| `big_outside` (outside): false STOP | 6 (44 advisory) | 6 (44 advisory) |
| inside STOP / outside false STOP / background frames, IDs / inside objects with a STOP | 303 / 6 / 3, 2 / 5 of 8 | **352 / 9 / 3, 2 / 6 of 8** |

**Where the station STOPs come from** (`squareT_platform_squareT_switch`, the train standing at
the platform; the tracked distances do not move, so no speed input changes them, §9): the 25 STOP
episodes (101 frames, 15 events) by structure, with the median shape of its gauge clusters:

| structure | episodes / STOP frames | gauge-cluster shape (median) | why it is an obstacle today |
|---|---|---|---|
| ~104 m overhead, along the track | **10 / 47** | 5.5 m along × 0.18 m wide × 0.65 m tall, bottom 2.2 m, lateral +0.54 m | `floating` applies only at \|lateral\| > 0.6 m (`signature_min_lateral`, kept for cables hanging near the axis); the long rule removes it |
| 82.9 m platform end | 10 / 26 | 2.2 × 0.41 × 1.25 m, bottom at the bed, lateral +0.96 m (the envelope edge is 1.05 m) | the corridor axis is ~0.5 m off at 83 m: curvature 1.6e-4 /m from the hall walls, 0.5·k·x² = 0.54 m (§1b, ALGORITHM §6.2) |
| 147.5 m switch parts | 4 / 23 | 0.07 × 0.41 × 0.96 m face, bottom 0.27 m, lateral −0.29 m | beyond the verified height reference it passes the far-field rule (≥ 0.6 m tall, ≤ 3 m long, bottom ≤ 1.0 m) like a person |
| 94 m | 1 / 2 | 4.8 × 0.21 × 1.35 m, bottom 1.4 m | too tall for `floating` (1.2 m) |

Also measured and not proposed: `cluster.far_min_height` 1.0 (for the switch parts) takes the
platform recording to 78 / 11 / 21 and set O background to 2 / 1 with the objects unchanged (with
the long rule: five bags 37 / 10 / 13), but the 1 m crate and the 0.5 m box of set F straight
beyond the height reference would become advisory and set F cannot be run here; the organizers do
not count switch glitches. The 82.9 m platform end needs a fix in the axis model, not a shape
rule: capping wall curvature in stations would also cut range in real R ≈ 350–1 000 m curves.

**Flipping a flag needs no code**: both are in `configs/default.yaml`, the ROS copy is synced by
`scripts/sync_params.sh`, the node reads `config_file`. The one measurement left, the ride with
`regression_gate.py --set …`, was measured 25.09 on the dev VM (the ride streamed with
`scripts/vm/stream_cache.py`).

**Decision of 25.09 on the ride** [measured 25.09]. Raw: the four gate summaries, the criteria, the
verdicts and the ride episodes each variant adds or removes in
[`rules_decision_2026-09-25.json`](evidence/results/rules_decision_2026-09-25.json). All runs:
`scripts/regression_gate.py --cache /data/cache --jobs 3`, native path, receive stamps, code
`7290873`, the 4-vCPU dev VM; the ride (`new_data`, 221 of 221 split files, 11 271 frames) in 8
pieces, set F straight with the round-3 parameters. The criteria were written before the ride
finished caching and before any variant run (09:16 UTC), and applied as written:

1. measure the shipped defaults: the ride (frames, alarm frames, events, STOP episodes, events per
   km over 13.0 km) and set F straight per kind (detected of 6, median first confirmation, median
   held-from distance);
2. run the long rule (3.0 m), short signatures (3.0 m, 100 m) and both, each with `--baseline` the
   defaults run;
3. the long rule is GO only if on the ride events, STOP episodes and alarm frames are each ≤ the
   defaults, on set F straight no kind loses an object and neither median drops by more than 2 m,
   and every set O and `doubleT_obstacle` gate metric is equal;
4. short signatures are GO only if, against X (the long rule if GO, else the defaults), ride
   events rise by at most max(5, 10 %) and STOP episodes by at most 5, set F straight is no worse
   (same 2 m tolerance), and set O gains at least +40 STOP frames on the inside objects;
5. latency is information only.

| the ride (11 271 frames, 13.0 km) | defaults | long 3.0 | short 3.0 / 100 | short + long |
|---|---:|---:|---:|---:|
| alarm frames / events / STOP episodes | 204 / 47 / 39 | **197 / 46 / 39** | 220 / 49 / 45 | 213 / 48 / 45 |
| events per km | 3.6 | **3.5** | 3.8 | 3.7 |
| five obstacle-free bags | 107 / 20 / 27 | **60 / 14 / 17** | 113 / 22 / 29 | 66 / 16 / 19 |
| set O inside STOP frames / outside false STOP / objects with a STOP | 303 / 6 / 5 of 8 | 303 / 6 / 5 of 8 | 352 / 9 / 6 of 8 | 352 / 9 / 6 of 8 |

The defaults run equals the 24.09 record on the ride exactly (204 / 47 / 39). Set F straight is
identical in all four runs (§2d, "Set F straight in the regression gate"); with the long rule set
O and `doubleT_obstacle` are identical frame by frame (it changes 53 frames of
`squareT_platform_squareT_switch` and 11 frames of the ride).

Long rule: **GO, shipped** (`935eecf`: `configs/default.yaml`, the ROS copy, `resense/config.py`).
It removes one ride event, track 524 in `new_data_192`: an overhead structure 4–5 m along the
track, 0.2–0.4 m wide, near the axis at 105–110 m, the same kind as the ~104 m structure of the
platform recording; no STOP episode is added or removed (that episode ends at frame 17 instead of
24). Short signatures on top: **NO-GO**: events +2 (limit +5), set F not worse, set O +49 inside
STOP frames (≥ +40 needed), but STOP episodes +6 (limit +5): a 1.8 m long fixture 0.07 m wide at
96.8 m, bottom 1.9 m, lateral +0.4…+0.9 m, flickers into STOP five times while the train stands
(`new_data_59`, frames 31–50), plus a 0.3 m wall object at 55.8 m (lateral −1.24 m) for one frame.
Tried, not shipped (`cluster.short_signature_max_length` stays 0). Latency is not read: the gate's
workers run in parallel on a shared machine (a ride mean of 20.9 ms on the new defaults against
26.0 ms for the long-rule run whose output is identical frame by frame). The gate on the new
defaults is the new baseline,
[`regression_baseline_2026-09-25_ride.json`](evidence/results/regression_baseline_2026-09-25_ride.json)
(PASS against the defaults run, 3 gated rows better; its output equals the long-rule run frame by
frame, only the load-dependent health-warning counts differ).

**Review of 25.09: the long rule near the axis needs an overhead bottom** [measured 25.09]. The
code review found that the along-track branch skipped the `signature_min_lateral` guard that keeps
objects hanging near the axis: a cluster on the axis longer than 3 m, under 1.2 m tall and 1.0 m
wide, with its bottom 0.7–1.9 m above the rail inside the envelope (a cable tray, duct or pipe
fallen onto the axis, e.g. 4.0 × 0.3 × 0.5 m with its bottom at 1.0 m at 60 m) was demoted to
advisory (`CAUTION`) instead of a STOP; the rule's evidence were overhead structures with their
bottom at ~2.2 m. Fix (approved by the captain): the branch applies only when the cluster's lowest
point is above `cluster.floating_long_min_bottom`; the off-centre `floating` path is unchanged.
Raw: [`long_rule_bottom_2026-09-25.json`](evidence/results/long_rule_bottom_2026-09-25.json)
(the pre-registration, the instrumented bottoms, the five gate summaries, the ride changes).

*Pre-registered* (11:08 UTC, before any run): candidates 2.0, 1.8, 1.6 m; choose the highest for
which, against [`regression_baseline_2026-09-25_ride.json`](evidence/results/regression_baseline_2026-09-25_ride.json),
the five obstacle-free recordings and the ride are not worse on alarm frames, events or STOP
episodes and set O, `doubleT_obstacle` and set F straight are identical; if none keeps every gain,
the one that loses least, the safety fix taking priority over the false-alarm gain. All runs:
`scripts/regression_gate.py --cache /data/cache --jobs 3 --set cluster.floating_long_min_bottom=<v>`,
native path, receive stamps, the ride in 8 pieces, code `3bf6324` (the parameter added with 0 =
the old rule), the 4-vCPU dev VM.

*What the branch demotes.* The shipped rule instrumented inside a gate run (output identical to
the baseline): every cluster classified `floating` near the axis (\|lateral\| ≤ 0.6 m), i.e. demoted
only because it is longer than 3 m. Lowest point above the rail head:

| recording | cluster-frames | where | bottom min / median / max |
|---|---:|---|---|
| `squareT_platform_squareT_switch` | 63 (62 frames) | 103.9–128.8 m; the ~104 m structure 56 + 5 (5.6 × 0.18 × 0.65 m median, lateral +0.36…+0.60 m), 2 at 127–129 m | 1.69 / 2.21 / 2.42 m (6 at ≤ 2.0 m, 1 at ≤ 1.8 m) |
| ride (`new_data`) | 8 | the removed event, track 524 in `new_data_192`: 5 frames at 105.9–111.0 m, 4.1–4.4 m long, top 2.82–2.96 m | 1.68 / 1.88 / 1.92 m |
| ride (`new_data`) | | single frames at 78.1 m (5.3 m long) and 115.7 m (5.7 m) | 2.49, 2.51 m |
| ride (`new_data`) | | one frame at 112.6 m, 4.7 × 0.41 × 0.25 m (never confirmed) | 0.89 m |
| `roundT_pressureGate_roundT` | 2 | 119–122 m, 4.7–4.8 m long | 2.64 / 2.65 m |
| the other four recordings, set O | 0 | | |

*The candidates* (alarm frames / events / STOP episodes; set O inside STOP frames / outside false
STOP / background frames, IDs; set F straight detected of 6 and median first confirmation per kind):

| | shipped (no bottom condition) | 2.0 m | 1.8 m | **1.6 m** |
|---|---:|---:|---:|---:|
| the ride | 197 / 46 / 39 | 204 / **47** / 39 | 202 / **47** / **40** | **197 / 46 / 39** |
| five obstacle-free recordings | 60 / 14 / 17 | 60 / 14 / 17 | 60 / 14 / 17 | 60 / 14 / 17 |
| `squareT_platform_squareT_switch` | 54 / 9 / 15 | 54 / 9 / 15 | 54 / 9 / 15 | 54 / 9 / 15 |
| `doubleT_obstacle` (person 58 of 61, rail object from frame 75 124 of 126, first frame 11) | identical | identical | identical | identical |
| set O | 303 / 6 / 3, 2 | identical | identical | identical |
| set F straight (person, trolley, 1 m crate, cable, 0.5 m box) | 6 / 151.0, 6 / 151.4, 6 / 123.9, 6 / 98.9, 1 / 51.9 m | identical | identical | identical |
| gate against the baseline | PASS | FAIL: ride events | FAIL: ride events, STOP episodes | PASS, identical frame by frame |

2.0 m brings back ride track 524 (`new_data_192`, frames 14–24, 105–110 m; 11 frames change);
1.8 m brings it back with one more STOP episode (8 frames change). Choice by the pre-registered rule:
**1.6 m**, shipped in `0bb1ba3` (`configs/default.yaml`, the ROS copy, `resense/config.py`). The gate
on the new defaults (no `--set`) passes against the old baseline with every number the same and
the per-frame output identical on the six recordings, set O and the ride, so
`regression_baseline_2026-09-25_ride.json` stays the baseline. What remains: a long cluster near
the axis with its bottom above 1.6 m (up to the 3.0 m envelope top) is still advisory, whether an
overhead duct or a tray hanging there; the finding's 0.7–1.6 m band is a STOP again. A higher
threshold is not free: the overhead structures the rule is for read as low as 1.68 m at 105–110 m,
where the extrapolated rail level drifts (§2d).

Tests (`tests/test_late_candidates.py`): the classification of the finding's box on the axis
(bottom 1.0 and 1.5 m: an obstacle; with the parameter 0: `floating`), the ~104 m structure
(bottom 2.2 m) still `floating`, the off-centre path unchanged; and end to end on the ray-cast
tunnel: the box's faces injected at 40–60 m (a single ray-cast frame returns only its 0.3 × 0.5 m
front face there, which the long rule never sees as long) give a STOP with the shipped defaults and
an advisory `floating` warning with the parameter 0.

## 2. Synthetic obstacles injected into real empty frames (`resense inject` / `resense eval`)

### 2a. Day-1 numbers (v0.3, 26 frames of `roundT_doubleT`, every 10th, synthetic objects)

One object per frame (person 0.5 × 1.7 m, box 0.5 m, plank 2 × 0.25 × 0.3 m), uniformly 10–220 m, 20
% placed outside the gauge as negatives; objects whose rays are all occluded by real geometry (7
of 26) excluded. Recall v0.3: 0–50 m 3/3, 50–100 m 1/2, 100–150 m 0/5, 150–200 m 0/3, 200–300 m 0/3.
First-detection distances: person 13.7 / 19.5 / 23.2 m (placed there), box 53.7 m. Ray-cast point
budget (single frame): person 24 pts @80 m, 10 pts @110 m, 3–5 pts @150–190 m, 0–1 @>200 m —
consistent with the analytic estimate in [`DATASET.md`](DATASET.md). Synthetic-tunnel unit tests
(`tests/`): box 0.6 m detected at 30 and 80 m, person at 150 m, no alarm on the clear tunnel, object
2.3 m off-axis not alarmed, occlusion of the background verified.

### 2b. Multi-frame accumulation on the synthetic tunnel (v0.4, 21.09) — synthetic

**Every number in this section is synthetic** (`resense.synthetic.synthetic_tunnel_frame`, a
featureless round tunnel with benches at 1.95 m; `tests/test_algorithm.py`), 4-core sandbox.
The approach of a train at 22 m/s is emulated by injecting the object at 200, 197.8, … m
(2.2 m per 10 Hz frame) into the *same* background frame; the sequences use
`dropout_start=60, dropout_full=200`, which reproduces the real-frame budget (person 2–5
returns at 185–200 m; box 0.5 m: 4–6 at 100–130 m).

| object, sequence (given ego speed 22 m/s) | first confirmed alarm, v0.3 (base commit) | v0.4, accumulation off | v0.4, accumulation on (5 frames) |
|---|---|---|---|
| person 0.4 × 0.5 × 1.7 m from 200 m, 6 seeds | 162.6 m (corridor validity) | 167–189 m, median 178 m, frames 5–15 | **189–191 m in 6/6 seeds**, frames 4–5 |
| box 0.5 m from 140 m, 4 seeds | 114.6 m | 89–116 m (one seed collapses to 89 m) | **113.6–115.8 m in 4/4 seeds** |

What limited v0.3 at range on the synthetic tunnel was the corridor validity (bed fit to 107.5 m +
60 m), not the point count; the verified extrapolation ([`ALGORITHM.md`](ALGORITHM.md) §3.1) reaches
195 m there. The 0.5 m box does not gain range from accumulation (beyond ~118 m it is sampled by a
single ring). Ego-speed estimator on synthetic texture: 22.0 m/s ± 2 with posts on the walls,
"unknown" on a stopped train and on the featureless tunnel. Retro-reflector rule: sign plate 0.05 ×
0.6 × 0.8 m with reflectivity 220 → advisory, the same plate matte → obstacle, person 15 / 60 / 200
→ obstacle, 1 m crate 220 → obstacle, 0.5 m box 220 → advisory (documented choice). The independent
review of v0.4 on real data (every frame, no speed given) found the stopped-train merge smearing the
crossing person laterally (width 1.06 vs 0.57 m), the verified corridor promoting phantoms at
135–142 m, +17–23 ms per real frame, and the retro rule never firing on the six bags (intensity ≥
100 on < 1 % of the returns); all four are addressed in v0.5 (§1b, §3) and the estimator's real-bag
behaviour is in §2c.

### 2c. Recall by range on real backgrounds (set S, v0.5, 21.09) — synthetic objects, real frames

Sets built this round with the merged `resense inject` (commit 9b56bdf (merged as 82815e9); objects
are placed on the per-frame track model of *this* code, so the frames differ slightly from P4's sets
of f4e311f): the two static sets `S_roundT_doubleT` (26 frames) and `S_roundT_pressureGate_roundT`
(27), every 10th frame, one catalogue object per frame (`person, box0.5, box1.0, plank, trolley`),
10–250 m, 20 % negatives, `--seed 1`, evaluated with `resense eval --repeat 3`; and six approach
sequences (`--sequence 8 --speed 15`, seeds 1–3 on both bags, 208–215 frames each, one random kind
per background). Two protocol facts decide how the far bins can be read:

* **Sightline.** Both bags are curves: from the v0.5 axes the inner wall (2.2 m from the
  axis) hides the track beyond √(2·R·2.2 m) ≈ 88 m (median frame of
  `roundT_pressureGate_roundT`, R = 1.8 km) and 124 m (`roundT_doubleT`, R = 3.5 km); only
  93 / 268 and 119 / 252 frames see further than 150 m. Nothing placed beyond the sightline
  can be detected by any sensor.
* **Placement (historical correction).** The v0.5 `resense inject` code actually stood ground
  objects 0.15 m below the *per-frame extrapolated rail head*, without calling the local-bed
  placement helper. The earlier text here calling that an extrapolated-bed placement was
  mistaken. With the sightline and ray-cast occlusion, **11 of the 22 in-gauge objects of each
  static set are fully occluded (all beyond 80 m)** and 436 of the 1 269 sequence rows are
  excluded from recall. The far bins therefore hold 3–7 visible objects per set and measure
  the injector as much as the detector. The corrected bed-height A/B is in
  [`P4_AUDIT.md`](P4_AUDIT.md); do not directly compare its counts to this v0.5 protocol.

**Static sets (53 frames, 26 in-gauge visible objects; recall = matched / visible in-gauge
objects, counts per bin):**

| config | 0–50 m | 50–100 m | 100–150 m | 150–200 m | 200–300 m | all | first detection (max) | fp events |
|---|---|---|---|---|---|---|---|---|
| v0.5 code with the v0.3 switches | 5/7 | 4/9 | 0/3 | 0/4 | 0/3 | 9/26 | person 42.6, box1.0 84.8, trolley 84.2, plank 14.6 m | 16 |
| **v0.5 defaults** | 5/7 | 3/9 | 0/3 | 0/4 | 0/3 | 8/26 | the same; trolley 50–100 m 1/3 instead of 2/3 | 11 |
| v0.5 defaults + retro rule on | 5/7 | 3/9 | 0/3 | 0/4 | 0/3 | 8/26 | identical to the defaults (no object of these sets is retro-reflective) | 11 |

Per kind (defaults): person 3/4 (the miss is at 158 m), box0.5 0/4 (46.8, 76, 102 m and one
beyond: the 0.5 m box at 46.8 m sits next to a column in the double-track section and merges
with it at that range), box1.0 3/7, plank 1/5, trolley 1/6. The static sets are too small to
separate the two configs (one object per cell); the sequences below carry the numbers.

**Approach sequences (six sets, 1 269 frames, 692 visible in-gauge object-frames; the
detector is reset at every background change — a train cannot jump between the 26
backgrounds of a set, and the smoothed, rate-limited axis of v0.5 needs 3–5 frames after such
a jump, which the plain `resense eval` does not give it; recall per bin = matched
object-frames / visible object-frames, "first detection" = the largest range at which a label
was matched, max and median over the labels of the kind):**

| config (all kinds) | 0–50 m | 50–100 m | 100–150 m | 150–200 m | 200–300 m | all | fp events / fp frames |
|---|---|---|---|---|---|---|---|
| v0.5 code with the v0.3 switches | 69/156 | 87/211 | 10/159 | 0/126 | 0/40 | 166/692 | 4 / 94 |
| **v0.5 defaults, no speed given** (single frame; with the estimator on it reports 473 "estimated" frames, all below 1 m/s because the background does not move, so nothing is merged either way — identical numbers) | 84/156 | 86/211 | 1/159 | 0/126 | 0/40 | **171/692** | 1 / 35 |
| v0.5 defaults, speed 15 m/s given (5-frame merge beyond 40 m; the background of these sets does *not* move, so the merged background is smeared by 1.5 m per frame — an artefact that works against accumulation) | 79/156 | 81/211 | 1/159 | 0/126 | 0/40 | 161/692 | 1 / 12 |
| v0.5 defaults + retro rule on, speed given | 73/156 | 81/211 | 1/159 | 0/126 | 0/40 | 155/692 | 1 / 12 |

Per kind, v0.5 defaults without a speed (matched / visible object-frames; first detection =
max / median over the labels of the kind, n labels ever matched):

| kind | 0–50 m | 50–100 m | 100–150 m | 150–200 m | 200–300 m | first detection (m) | v0.3-switch first detection (m) |
|---|---|---|---|---|---|---|---|
| person 0.4 × 0.5 × 1.7 m | 28/37 | 38/68 | 1/30 | 0/21 | 0/9 | 104.9 / 56.7 (11) | 104.9 / 70.7 (10) |
| box 0.5 m | 15/21 | 4/11 | 0/20 | 0/35 | 0/15 | 57.6 / 49.1 (4) | 57.6 / 49.1 (3) |
| box 1.0 m | 23/29 | 23/59 | 0/38 | 0/1 | — | 81.8 / 55.0 (8) | 89.6 / 55.0 (8) |
| plank 2 × 0.25 × 0.3 m | 0/45 | 3/40 | 0/14 | 0/16 | 0/6 | 86.3 (1) | — (0) |
| trolley 0.6 × 0.6 × 1.0 m | 18/24 | 18/33 | 0/57 | 0/53 | 0/10 | 78.7 / 71.9 (5) | 149.5 / 88.6 (6) |

Reading. (1) Up to 100 m the v0.5 defaults match or beat the v0.3 switches (0–50 m 84 vs
69 object-frames, 50–100 m 86 vs 87) with a quarter of the false-alarm events (1 vs 4) and a
third of the false-alarm frames (35 vs 94). (2) The 100–150 m bin loses 9 of its 10 v0.3
object-frames (a trolley matched at 149.5 m and persons at 100–105 m): the shorter trusted
height-reference range (fit + 20 m or verified) and the axis caps demote far clusters to
advisory — the price of the 503-frame cause of §1b; which lever costs what is measured in the
ablation rows of §1b (sequence runs with `floor_valid_margin: 60` and the axis levers off are
in `evalC/seq_reset2` of the run directory, quoted in §5). (3) Beyond 150 m nothing is
matched by any config: of the 126 + 40 object-frames there, 436 rows of the sets are fully
occluded (sightline, placement) and the visible ones return 1–5 points, below the 3-voxel
floor. (4) The given-speed merge costs 10 object-frames on these sets and removes 23
false-alarm frames; both effects are within what the static-background artefact can produce,
so the sequences do not decide the accumulation question — the real bags do (§1b). (5) The
retro rule costs 6 trolley frames (catalogue reflectivity 40–120 %) and gains nothing here or
on the bags: off by default. (6) The plank of the spec stays invisible by design (0/121
object-frames; the low-hardware rule, ALGORITHM §6.6), except three frames at 86 m where
the axis error lifted it.

The `person` first detection of 104.9 m and the `box1.0` 81.8 m are the honest single-frame ranges
on these two curved bags; the Sprint 2 targets of EVALUATION §4 (person ≥ 150 m, box ≥ 100 m) hold
on the synthetic tunnel only (§2b) and are not met on real backgrounds by any configuration measured
this round.

### 2d. The far field and long range on a moving background (set F, v0.6.1–v0.6.3, 22–24.09)

**What a straight tunnel returns far away** (`new_data_46`, 20 m/s, R > 100 km): of ~188 000 points
per frame, 422 lie 100–125 m ahead, 217 at 125–150 m, 73 at 150–175 m and 56 at 175–215 m; no return
of any frame of any recording lies beyond 210 m (every recording stops at 209.2–210.0 m: a cut-off
of the sensor, not a gradual fade). Beyond ~100 m the bed does not return (grazing incidence); only
the vault (4.4–4.7 m above the rail head) and the walls at ±2 m do. **The extrapolated height
reference drifts**: relative to the vault measured at 20–60 m, the vault seen through the model is
+0.07 m at 65 m, +0.15 at 85 m, +0.24 at 95 m, +0.49 at 115 m and +0.79 at 135 m (file 46); +0.10 at
85 m, +0.25 at 115 m, +0.40 at 155 m, +0.5 at 175–195 m (file 98) — the model's rail level runs low
by that much (a vertical curve ahead, or the extrapolated slope). The lateral residual of the walls
is ±0.3 m. That is why the corridor was trusted only to the bed fit + 20 m or the side-base
verification (100–130 m), and why v0.6 extends the alarm range for **tall, grounded, short**
clusters only (ALGORITHM §3.3c): a 0.5 m error does not move a 1.7 m person out of a 3 m envelope,
but it does lift flat far-bed returns into its bottom. A lining-anchored far reference (correct the
model by the vault drift) is measurable to ~200 m and is the next step (not in v0.6: the lateral
residuals are too noisy to anchor the axis).

**Set F** (`scripts/far_range_eval.py`): an object is placed at a fixed point of the tunnel
220 m ahead of 110 consecutive frames of the ride and ray-cast into every frame at the distance
it has then (the train speed of the ride from the static-track drift of each split file, the bag
frame intervals); it stands on the bed measured under it where the bed returns, else on the
model's rail level corrected by the vault drift above; laterally uniform in ±0.6 m; dropout
from 60 m to 200 m scaled by reflectivity (the real-frame budget, §2b). A fresh detector per
sequence, **no speed given** (single-frame pipeline + persistence). A frame is a hit when a
confirmed gauge detection lies within max(2 m, 3 %) and 1.2 m laterally of the object. Rounds 1–3
use the **legacy** placement: the object's lateral position follows the detector's own per-frame
far axis, which can flatter curves and the envelope edge; round 4 checks that against a placement
anchored on the near rails ([`EVALUATION.md`](EVALUATION.md) §3, P4_AUDIT).

**Set F straight in the regression gate (25.09).** `scripts/regression_gate.py` runs the round-3
straight set (files 46, 68, 98, 140, 168, 172, legacy placement, seed 0, from 220 m) with every
detector change. On 25.09 it ran four times on the dev VM (the shipped defaults, each 25.09 rule
and both, §1f) and gave the same figures every time: detected / first confirmed, median / held
from, median / confirmed detections away from the object:

| person | trolley | crate 1.0 m | cable 3 cm | box 0.5 m in the bed |
|---|---|---|---|---|
| 6 / 6, **151.0 m**, 142.6 m, 9 | 6 / 6, 151.4 m, 115.0 m, 15 | 6 / 6, 123.9 m, 114.1 m, 16 | 6 / 6, 98.9 m, 34.2 m, 12 | 1 / 6, 51.9 m, 55.6 m, 4 |

These do not match round 3 below (person 148 m) although the files, seed, stamps and speeds are
the same (their sha256 match): `far_range_eval.py` was changed by the P4 audit (`4b5786b`) after
that record, so compare them only run to run; they are the gate's baseline
([`regression_baseline_2026-09-25_ride.json`](evidence/results/regression_baseline_2026-09-25_ride.json))
[synthetic, measured 25.09].

**Round 4 (24.09, P4): legacy against anchored placement, in pairs.** Anchored placement fixes the
object where a near (≤ 30 m) rail-supported track fit puts it and carries it back through the
approach with the near fits of the following frames and the recorded speed: independent of the far
axis, but not surveyed ground truth. Both modes use the same files, seed, lateral and reflectivity
draws and frames; a sequence skipped in one mode (a recording gap) is dropped from both
(`scripts/compare_setf.py`; raw:
[`experiments_p4_setf_straight_paired.json`](evidence/results/experiments_p4_setf_straight_paired.json),
[`experiments_p4_setf_paired.json`](evidence/results/experiments_p4_setf_paired.json); commands in
P4_AUDIT):

| set | object | detected (both modes) | first confirmed, paired median: legacy → anchored | visible hits 100–150 m: legacy → anchored |
|---|---|---:|---:|---:|
| straight: files 46, 68, 98, 140, 172 (168 skipped: a 65.4 m motion step), \|lateral\| ≤ 0.6 m, from 220 m | person 0.4 × 0.5 × 1.7 m | 5 / 5 | 149.9 → **154.1 m** | 94 / 125 → 97 / 125 |
| | trolley | 5 / 5 | 148.1 → 148.1 m | 34 / 125 → 32 / 125 |
| | crate 1.0 m | 5 / 5 | 116.1 → 109.9 m | 26 / 125 → 28 / 125 |
| | cable 3 cm hanging to 1.0 m | 5 / 5 | 103.9 → 101.7 m | 12 / 80 → 5 / 87 |
| | box 0.5 m in the bed | 1 / 5 | 51.9 → 51.9 m | 0 / 119 → 0 / 119 |
| curves R ≈ 350 m: files 127, 129, 131, 160, 175, 177 (164 skipped: a 24.5 m step), \|lateral\| ≤ 1.0 m, from 160 m | person | 6 / 6 | 73.7 → 67.5 m | 0 / 116 → 0 / 102 |
| | box 1.0 m | 6 / 6 | 74.7 → 79.6 m | 0 / 116 → 0 / 103 |

Reading. (1) **On straight track the range does not depend on the detector's own far axis**: a
person placed from the near rails is first confirmed at a median 154 m (150–180 m), which supports
round 3's 148 m for the current code. The legacy median over all six attempted straight sequences
is 151.0 m, not round 3's 148 m, because set F now seeds the ray casting per frame (other dropout
draws), not because the detector changed. (2) **On the curves nothing is matched at 100–150 m in
either mode**, and the placement moves single first confirmations a lot (an earlier edge run on
file 133: person 85.1 m legacy, 51.9 m anchored); in the 50–100 m bin the person gives 82 / 199
(legacy) against 69 / 204 (anchored) hits, the box 98 / 202 against 106 / 208. These are
sensitivity results on synthetic objects, not surveyed recall. (3) A near-range smoke test (file 30,
one approach below 40 m) gave 31 of 35 visible hits for a person and a 1 m box in both modes. A
third mode, `--placement-mode independent`, takes a surveyed track reference (EVALUATION §3); no
survey exists, so it has not been run (§5).

**Round 3 (v0.6.3, the current code, 24.09)** — the same sets re-run on the shipped code (raw
summaries with the per-approach band ranges:
[`experiments_2026-09-24_remeasure.json`](evidence/results/experiments_2026-09-24_remeasure.json)).
Round 2 below was measured on v0.6.2 and never repeated after v0.6.3's hold over one missed frame
(`tracking.hold_misses` 1): with the hold switched off, the current code reproduces round 2's
straight set value for value, so every difference between the two tables is the hold. First
confirmations do not change (the hold neither creates nor confirms a track); the held ranges and the
frame recall rise where a single missed frame used to break a run, and so do the confirmed
detections away from the object (a held false detection counts once more). Placements are those of
round 2 (same files, start, lateral range, seed) except where marked: the envelope-edge set and the
rail-head and lying-on-the-rails sets of round 2 were drawn with parameters that the stored
summaries do not fully record, so these rows are new draws of the same scenario.

| set | object | detected | first confirmed, median (range) | sustained ≥ 90 %, median (range) | every 10 m band ≥ 90 %, median (per approach) | frame recall 0–50 / 50–100 / 100–150 / 150–200 m | confirmed detections away from the object |
|---|---|---|---|---|---|---|---|
| straight, \|lateral\| ≤ 0.6 m | person 0.4 × 0.5 × 1.7 m | 6 / 6 | 148 m (110–169) | 149 m (92–177) | 115 m (20–160) | 96 / 94 / 68 / 9 % | 9 |
|  | trolley 0.6 × 1.0 m | 6 / 6 | 144 m (85–154) | 115 m (22–129) | 70 m (20–110) | 96 / 90 / 29 / 3 % | 25 |
|  | crate 1.0 m | 6 / 6 | 111 m (79–156) | 119 m (22–129) | 105 m (20–110) | 96 / 92 / 28 / 1 % | 6 |
|  | cable 3 cm hanging to 1.0 m above the rail head | 6 / 6 | 95 m (13–108) | 53 m (19–98, 4 of 6) | 20 m (10–40) | 74 / 59 / 6 / 0 % | 4 |
|  | box 0.5 m in the bed | 1 / 6 | 52 m | 56 m, 1 of 6 | 50 m (50–50, 1 of 6) | 16 / 2 / 0 / 0 % | 2 |
| same, **train speed given** (5-frame accumulation) | person | 6 / 6 | 167 m (143–188) | 151 m (22–195) | 105 m (20–170) | 96 / 83 / 62 / 36 % | 6 |
|  | trolley | 6 / 6 | 175 m (110–194) | 122 m (22–186) | 110 m (20–160) | 96 / 84 / 44 / 44 % | 2 |
|  | crate 1.0 m | 6 / 6 | 182 m (142–201) | 79 m (22–174) | 70 m (10–120) | 95 / 73 / 58 / 41 % | 7 |
| to the envelope edge, \|lateral\| ≤ 1.0 m (new random placements) | person | 6 / 6 | 136 m (87–155) | 120 m (22–170) | 95 m (20–150) | 96 / 92 / 64 / 3 % | 6 |
|  | crate 1.0 m | 6 / 6 | 108 m (77–152) | 108 m (22–127) | 95 m (20–110) | 96 / 89 / 16 / 1 % | 9 |
|  | trolley | 6 / 6 | 122 m (96–151) | 109 m (22–120) | 95 m (20–110) | 96 / 90 / 21 / 1 % | 9 |
|  | cable hanging to 0.2 m above the rail head | 3 / 6 | 136 m (136–138) | 39 m (35–44, 2 of 6) | 30 m (10–40, 3 of 6) | 34 / 39 / 33 / 0 % | 4 |
| curves R ≈ 350 m (7 approaches) | person | 6 / 7 | 78 m (58–86) | 85 m (61–94, 6 of 7) | 75 m (50–80, 6 of 7) | 100 / 50 / 0 / 0 % | 0 |
|  | crate 1.0 m | 6 / 7 | 68 m (47–89) | 68 m (50–95, 4 of 7) | 60 m (40–70, 4 of 7) | 89 / 35 / 0 / 0 % | 8 |
|  | trolley | 6 / 7 | 68 m (51–89) | 72 m (24–97, 6 of 7) | 65 m (20–90, 6 of 7) | 92 / 39 / 0 / 0 % | 11 |
| station stops (6) | person | 6 / 6 | 113 m (89–144) | 122 m (78–127, 5 of 6) | 75 m (10–120) | 93 / 87 / 30 / 0 % | 111 |
|  | crate 1.0 m | 6 / 6 | 102 m (79–144) | 97 m (83–103, 3 of 6) | 60 m (10–90, 4 of 6) | 79 / 77 / 10 / 0 % | 91 |
|  | dog-sized box 0.6 × 0.3 × 0.45 m on the bed | 1 / 6 | 41 m | — | — | 3 / 0 / 0 / 0 % | 81 |
| small objects on a rail head (start 150 m) | 0.3 × 0.3 × 0.1 m | 6 / 6 | 42 m (28–46) | 45 m (30–50) | 40 m (20–40) | 79 / 0 / 0 % | 4 |
|  | 0.3 m cube | 6 / 6 | 49 m (44–64) | 53 m (46–70) | 45 m (40–60) | 95 / 10 / 0 % | 0 |
| across a rail (replica of the organizers' object, 0.4 × 0.6 × 0.31 m) |  | 5 / 6 | 46 m (24–50) | 40 m (26–50, 4 of 6) | 30 m (10–40, 5 of 6) | 52 / 1 / 0 % | 4 |
| on the bed between the rails | 0.3 × 0.3 × 0.1 m | 0 / 6 | — | — | — | 0 / 0 % | 6 |
|  | 0.3 m cube | 1 / 6 | 9 m | — | 10 m (10–10, 1 of 6) | 1 / 0 % | 0 |
|  | dog-sized 0.6 × 0.3 × 0.45 m | 1 / 6 | 50 m | 50 m, 1 of 6 | 40 m (40–40, 1 of 6) | 15 / 1 % | 2 |
| person lying, 0.5 × 1.8 × 0.35 m | across the rails, on the rail heads (start 150 m) | 6 / 6 | 64 m (54–112) | 68 m (58–83) | 60 m (40–70) | 99 / 30 / 1 % | 10 |
|  | on the measured (deep) bed, across | 0 / 6 | — | — | — | 0 % | 0 |
|  | same, along | 0 / 6 | — | — | — | 0 % | 0 |
|  | shallow bed, top 0.15 m above the rail head, across | 6 / 6 | 49 m (47–52) | 53 m (50–56) | 50 m (40–50) | 99 % | 0 |
|  | same, along | 6 / 6 | 50 m (48–52) | 54 m (52–56) | 50 m (50–50) | 100 % | 0 |
|  | top 0.10 m above the rail head, across | 6 / 6 | 42 m (30–47) | 46 m (32–50) | 40 m (30–40) | 82 % | 0 |
|  | same, along | 6 / 6 | 46 m (42–50) | 48 m (45–54) | 40 m (40–50, 4 of 6) | 91 % | 0 |
|  | top 0.05 m above the rail head, across | 6 / 6 | 17 m (10–24) | 17 m (16–25, 5 of 6) | 10 m (10–20) | 25 % | 0 |
|  | same, along | 6 / 6 | 29 m (11–43) | 39 m (22–47, 4 of 6) | 25 m (10–40) | 50 % | 0 |

Reading (what differs from round 2). A person on straight track: first confirmed at **148 m**
(unchanged), held in ≥ 90 % of the frames from **149 m** (round 2: 135 m; the approach through the
3.4 s recording hole of `new_data_169` no longer collapses to 22 m) and in every 10 m band from
**115 m** (unchanged; per approach 20–160 m). With a train speed the crate is held from 79 m
(round 2: 89 m, 5 of 6 approaches; now 6 of 6). At station stops the crate is held from 97 m
(round 2: 80 m), and the confirmed detections away from the objects rise from 75 / 58 / 51 to
111 / 91 / 81 (the stations' own false alarms, held). Small objects on a rail head: first at
42 m (the 10 cm box) and 49 m (the 30 cm cube), held from 45 m and 53 m.

**Round 2 (v0.6.2, 23.09)** — what the criteria review asked for: small objects, objects on a rail
head, lateral positions to the envelope edge, 7 approaches in curves and 6 at station stops, and the
**sustained range** next to the first hit: the largest distance D from which the object is detected
in ≥ 90 % of the frames in which it returns a point, all the way in (≥ 5 frames) — a lenient
measure: the misses may bunch at its far end. The strict one next to it: every 10 m band from the
train out to D detected in ≥ 90 % of its frames (straight, median of 6: person **115 m**, crate 95
m, trolley 70 m; with a train speed person 105 m, crate 70 m, trolley 110 m). The v0.6.2
configuration (0.5 s confirmation), no speed given unless said; 6 sequences per object unless said;
raw summaries in [`experiments_v0.6.2_setF.json`](evidence/results/experiments_v0.6.2_setF.json).

| set | object | detected | first confirmed, median (per sequence) | sustained ≥ 90 %, median (per sequence) | frame recall 0–50 / 50–100 / 100–150 / 150–200 m |
|---|---|---|---|---|---|
| straight, \|lateral\| ≤ 0.6 m | person 0.4 × 0.5 × 1.7 m | 6 / 6 | **148 m** (110, 146, 146, 149, 162, 169) | **135 m** (22, 92, 120, 150, 162, 176) | 96 / 94 / 67 / 7 % |
| | trolley 0.6 × 1.0 m | 6 / 6 | 144 m (85–154) | 115 m (22–118) | 96 / 88 / 27 / 3 % |
| | crate 1.0 m | 6 / 6 | 111 m (79–156) | 117 m (22–129) | 96 / 92 / 26 / 1 % |
| | cable 3 cm hanging to 1.0 m above the rail head | 6 / 6 | 95 m (13–108) | 53 m (19–98, 4 of 6) | 74 / 59 / 6 / 0 % |
| | box 0.5 m in the bed | 1 / 6 | 52 m | 56 m | 16 / 2 / 0 / 0 % |
| same, **train speed given** (5-frame accumulation) | person | 6 / 6 | **167 m** (143–188) | 151 m (22–190) | 96 / 83 / 58 / 34 % |
| | trolley | 6 / 6 | 175 m (110–194) | 122 m (22–186) | 96 / 84 / 41 / 42 % |
| | crate 1.0 m | 6 / 6 | 182 m (142–201) | 89 m (22–170, 5 of 6) | 94 / 71 / 55 / 38 % |
| to the envelope edge, \|lateral\| ≤ 1.0 m | person | 6 / 6 | 138 m (108–161) | 115 m (16–164) | 94 / 91 / 56 / 3 % |
| | crate 1.0 m | 6 / 6 | 116 m (83–151) | 118 m (22–129) | 95 / 91 / 22 / 1 % |
| | trolley | 6 / 6 | 116 m (101–157) | 95 m (22–120, 4 of 6) | 85 / 83 / 24 / 1 % |
| | cable hanging to 0.2 m above the rail head | 3 / 6 | 132 m (108–135) | 64 m (1 of 6) | 24 / 18 / 13 / 0 % |
| curves R ≈ 350 m (7 approaches) | person | **6 / 7** | 78 m (58–86) | 85 m (61–94) | 100 / 50 / 0 / 0 % |
| | crate 1.0 m | 6 / 7 | 68 m (47–89) | 68 m (48–95, 4 of 7) | 87 / 35 / 0 / 0 % |
| | trolley | 6 / 7 | 68 m (51–89) | 73 m (24–97) | 92 / 39 / 0 / 0 % |
| station stops (6) | person | 6 / 6 | 113 m (89–144) | 122 m (77–127, 5 of 6) | 93 / 85 / 29 / 0 % |
| | crate 1.0 m | 6 / 6 | 102 m (79–144) | 80 m (61–94, 3 of 6) | 76 / 73 / 10 / 0 % |
| | dog-sized box 0.6 × 0.3 × 0.45 m on the bed | 1 / 6 | 41 m | — | 2 / 0 / 0 / 0 % |
| small objects on a rail head | 0.3 × 0.3 × 0.1 m | **6 / 6** | 42 m (41–48) | 45 m (33–48) | 84 / 0 / 0 % |
| | 0.3 m cube | **6 / 6** | 44 m (42–50) | 47 m (44–50) | 87 / 1 / 0 % |
| across a rail (replica of the organizers' object, 0.4 × 0.6 × 0.31 m) | | 5 / 6 | 46 m (24–50) | 32 m (26–50, 4 of 6) | 48 / 1 / 0 % |
| on the bed between the rails | 0.3 × 0.3 × 0.1 m | 0 / 6 | — | — | 0 % |
| | 0.3 m cube | 1 / 6 | 9 m | — | 1 % |
| | dog-sized 0.6 × 0.3 × 0.45 m | 1 / 6 | 50 m | 42 m | 13 / 1 % |
| person lying, 0.5 × 1.8 × 0.35 m (added 23.09 after the second review) | across the rails, on the rail heads | 6 / 6 | 61 m (50–111) | 65 m (54–68, 4 of 6) | 90 / 20 / 2 % |
| | in the central drainage trough (0.57–0.60 m below the rail head in these tunnels: the body stays below it) | 0–1 / 6 | — | — | 0 % |
| | on a shallow bed, top 0.15 m above the rail head, **across** the track: v0.6.2 → with the 2.2 m width cap | 2 / 6 → **6 / 6** | 41 → **49 m** (47–52) | — → **53 m** (50–56) | 3 → 98 % (0–50 m) |
| | same, **along** the track | 6 / 6 | 50 m (48–52) | 54 m (52–56) | 100 % (0–50 m) |
| | across, top 0.10 m / 0.05 m above the rail head (2.2 m cap) | 6 / 6, 6 / 6 | 42 m / 17 m | 43 m / 17 m (4 of 6) | 79 % / 24 % (0–50 m) |

Reading. (1) **A person on straight track is first confirmed at ~148 m, held in ≥ 90 % of the frames
from ~135 m and in every 10 m band from ~115 m** (medians of 6; runs of up to 7 consecutive missed
frames occur inside the lenient range); v0.6.1 first hit 150 m — the 0.5 s confirmation costs ~3 m
there and ~10 m with a train speed (167 against 177 m). In one sequence out of six both sustained
measures collapse to ~20 m: the recording has a 3.4 s hole there (`new_data_169`, frames 14 → 15),
the object jumps ~65 m closer, the detector resets its scene and needs 0.5 s to confirm again (a
review found it; the sequence is kept as it is, a control recording can have such holes too) — the
first-hit median hides such dropouts, which is why all three are reported. (2) **Curves: 6 of 7
approaches** detected (round 1: 1 of 2), first at 58–86 m and sustained from 61–94 m — the sightline
past the inner wall of an R ≈ 350 m curve (≈ √(8·R·w) = 80–110 m). (3) **Station stops**: a person 6
/ 6 from 113 m; the stations carry the ride's own false alarms (75, 58 and 51 confirmed detections
away from the objects in these 18 sequences of ~110 frames — the platform-edge and platform-end
structures of §0a). (4) **Small objects on a rail head** — a 30 × 30 × 10 cm box and a 30 cm cube —
are found in 6 of 6 approaches from 42–44 m and held from 45–47 m; the replica of the organizers'
object lying across a rail in 5 of 6, from 46 m. (5) **The same objects on the bed between the rails
are below the envelope**: measured under these placements (files 46–172, 20–50 m), the bed lies
0.26–0.34 m below the rail head half a metre off the axis and the central drainage trough 0.57–0.60
m (the track model's `rail_offset`: 0.35–0.38 m), so a 10 cm box, a 30 cm cube and even a 45 cm
dog-sized box stay below the envelope floor (0.12 m above the rail head) or barely reach the
rail-head plane — not reported by the default policy (ALGORITHM §3.3b, §6; the organizers confirmed
on 25.09 that such an object is not an obstacle, [`organizers/answers.md`](organizers/answers.md)
§8), which a line with a clean bed can switch (`lowobj.min_top: -1`, `min_point_top: -1`). An
attempt to exempt low clusters centred between the rails from the track-hardware rule changed
nothing (no candidate reaches the corridor) and was not kept. (6) **A person lying on the track** (the review's case, 0.5 × 1.8 × 0.35
m, placed by `far_range_eval.py` with the bed depth fixed; shallow-bed runs with `local_bed_z`
replaced by "rail level − depth"): across the rail heads the corridor stage sees it (6 / 6, from ~60
m); on these tunnels' deep bed the whole body is below the rail head and not reported (policy);
where the bed is shallow it straddles the envelope floor and the straddle stage finds it, across the
track only since the width cap follows the envelope (§0) — from ~50 m with its top 0.15 m above the
rail head, from ~17 m when only 5 cm of it rise above the rail head. No false detection in these 60
sequences. A body lying across the track rests on the bed beside the trough, 0.26–0.34 m below the
rail head, so the 0.25 and 0.30 m rows are the realistic case in these tunnels: found in 6 of 6
approaches, but only from ~42 m (top 0.10 m) and ~17 m (top 0.05 m). (7) Off-axis objects to the
envelope edge lose ~10 m of first detection (the edge margin grows with range); a 3 cm cable near
the edge is found in 3 of 6.

**Round 1 (v0.6.1, 22.09).** Straight sections (files 46, 68, 98, 140, 168, 172; 17–21 m/s), v0.6.1:

| object | sequences detected | first confirmed detection: per sequence (m) | median | recall 0–50 / 50–100 / 100–150 / 150–200 / 200–250 m |
|---|---|---|---|---|
| person 0.4 × 0.5 × 1.7 m | 6 / 6 | 110, 146, 149, 152, 166, 169 | **150 m** | 97 % / 94 % / 68 % / 10 % / 0 % |
| trolley 0.6 × 1.0 m | 6 / 6 | 85, 142, 145, 146, 153, 171 | 146 m | 97 % / 88 % / 28 % / 3 % / 0 % |
| crate 1.0 m | 6 / 6 | 79, 108, 110, 112, 145, 156 | 111 m | 97 % / 92 % / 26 % / 1 % / 0 % |
| cable 3 cm hanging to 1.0 m above the rail head | 6 / 6 | 16, 59, 94, 96, 103, 112 | 95 m | 83 % / 63 % / 7 % / 0 % / 0 % |
| box 0.5 m standing in the bed | 2 / 6 | 52, 57 | 55 m | 15 % / 2 % / 0 % / 0 % / 0 % |

Curves (files 129 and 176, R ≈ 350 m): person first confirmed at 82 m and crate at 74 m in one
of the two sequences, nothing beyond ~100 m — the inner wall hides the track beyond
√(8·R·w) ≈ 80–110 m and the corridor is trusted only to 60–120 m there; the organizers accept
detection at the visible limit in a curve (Q&A fact 14).

Reading. (1) A person is confirmed at 146–169 m on straight track in 5 of 6 sequences with no speed
input; the 150–200 m bin holds 3–10 returns per frame and is where the single-frame pipeline ends
(10 % of those frames). (2) Beyond ~200 m nothing is detected, as the sensor physics predicts: no
return of the whole ride lies beyond 210 m. (3) A trolley is confirmed at 85–171 m (median 146 m), a
1 m crate at 79–156 m (the crate is 1 m tall, closer to `far_min_height` = 0.6 m after the far bed
error than a person). (4) **A 0.5 m box standing in the bed is borderline by construction**: beside
the central drainage trough the bed lies 0.26–0.34 m below the rail head (round 2, reading 5), so
the box top is 0.15–0.25 m above the rail head — at the envelope's bottom (0.12 m) — and it is
reported only in the frames where it reaches into the envelope (2 of 6 sequences, 50–60 m); on a
rail head the same box is found (the low-object stage, `tests/test_envelope.py`). (5) A 3 cm cable
hanging into the envelope is detected at 59–112 m (the beam-footprint model of the injector,
DATASET, makes it 5–11 cm wide at that range; a real cable's echo strength is the open question).
(6) **Confirmed gauge detections away from the object: 39 of the 3 060 injected frames (1.3 %), none
in the curves.** 10 are the object's own cluster merged with bed returns in front of it and reported
3–7 m short (outside the max(2 m, 3 %) match window: a localisation error, counted against us); 10
are the background's own false alarms (the same start of file 98 run with *no* object confirms 6
frames of 2 m tall fixtures at 134–158 m; files 68, 168 and 172 give none); 19 are a structure 30–65
m *beyond* the object that alarms only with the object present (file 98 at 105–165 m, file 168 at 94
m). Mechanism of those 19 (traced on file 98): where the real bed no longer returns (beyond ~90 m)
the base of the object fills a bed bin, the bed fit extends from ~80 to ~107 m, the wall band above
it shifts and the far curvature moves by ~2.5·10⁻⁵ m⁻¹ — 0.3 m at 150 m, enough to bring an edge
fixture inside the 0.15 m/100 m margin. The object itself is confirmed in the same frames, so the
train's decision (STOP at the object) does not change; a bed bin that is narrower than the bed (an
object, not the track) should not extend the fit — noted in ALGORITHM §6. (7) **Sensitivity to the
mount tilt.** The same set run with the v0.6 calibration (a 5-frame tilt frozen at the start of each
sequence: up to ±1.6° of spurious roll and ±0.4° of pitch on this level rig) gave a person median of
165 m, crate 127 m, trolley 121 m, box 0.5 m 4 / 6: far-field numbers move by ±15–30 m with a few
tenths of a degree of pitch (0.3° is 0.8 m of height at 150 m). The v0.6.1 numbers above are the
ones with the physically right (level) mount.

**What the far-field rule and a train speed add** (paired v0.6.1 runs of set F: the same 30
sequences, the same random draws; `far_range_eval.py --far-min-height 0` = the v0.5
behaviour, `--given-speed` = the ride's per-file train speed handed to the detector, which then
merges 5 frames beyond 40 m — what the node does when `speed_topic` / `odom_topic` /
`ego_speed_mps` is set):

| object (6 sequences each) | far rule off (v0.5) | **shipped, no speed** | shipped + speed given |
|---|---|---|---|
| person: first confirmed, median (range) | 106 m (83–110) | **150 m** (110–169) | **177 m** (150–192) |
| trolley | 105 m (85–110) | 146 m (85–171) | 190 m (144–205) |
| crate 1 m | 106 m (79–110) | 111 m (79–156) | 183 m (110–192) |
| 3 cm hanging cable | 92 m (16–112) | 95 m (16–112) | 107 m (65–110) |
| box 0.5 m in the bed | 55 m, 2 / 6 | 55 m, 2 / 6 | 110 m, 4 / 6 |
| person, frame recall 50–100 / 100–150 / 150–200 m | 94 / 13 / 0 % | 94 / 68 / 10 % | 86 / 62 / 44 % |
| trolley, frame recall 50–100 / 100–150 / 150–200 m | 88 / 11 / 0 % | 88 / 28 / 3 % | 67 / 55 / 51 % |
| confirmed detections away from the object (3 060 frames) | 12 | 39 | 21 |
| **the 20-minute ride without objects**: alarm frames / events | — | 289 / 82 | **274 / 75** |

Reading. The far-field rule is what takes a person from the height-reference limit (~106 m) to
~150 m without any speed. A train speed adds the rest of the sensor's reach — first
confirmation at 150–205 m for a person, a crate and a trolley, half of the 150–200 m frames —
and a 0.5 m box from ~110 m, **with fewer false alarms, not more**: on the whole ride (every
frame, `eval_real.py --given-speed`) 274 / 75 against 289 / 82, and 21 against 39 off-object
frames in set F — merged clouds are denser and steadier than single frames. It costs
mid-range frames (the merged cluster of an object is longer than the object when the speed is
off by a fraction of a m/s — the ride's speed is a per-file average here, not odometry — and
some frames leave the 3 % match window). Nothing is detected beyond ~205 m in any variant: the
sensor returns nothing there. The organizers said the trains may have no odometry (Q&A fact 6),
so the shipped numbers are the no-speed column; with an odometry or speed topic the node takes
the third column automatically.

### 2e. The organizers' synthetic-obstacle recording (set O, 24.09, P4)

`cloud_with_fake_obj` (organizers, 24.09): 1 510 frames of a real scan with ten objects ray-cast in
frames 0–803 by the tool the organizers will check solutions with ([Q&A](organizers/QA_session.md)
fact 4), so the closest thing to the hidden check. The object points are appended to each message,
so the recording is labelled exactly (`scripts/label_fake_objects.py` →
`labels/cloud_with_fake_obj.json`, 1 206 object-frames; DATASET "Synthetic-obstacle recording").
The objects stand still in the tunnel while the train drives up to them at 1.4–20 m/s (corrected
on 24.09: an earlier ICP had the train backing up), so a train speed can be tested on it (§9). Two
limits: the objects are placed from the sensor's axis, −0.24° to the rails, so the edge tests sit
within ±0.1–0.4 m of the envelope edge; beyond ~100 m their path leaves the tunnel, and those rows
are graded out.

**Grade of the shipped detector** (default config, every frame, no speed given;
`scripts/score_fake_objects.py`; raw:
[`experiments_p4_fake_labelled.json`](evidence/results/experiments_p4_fake_labelled.json)).
"Visible" counts plausible frames with at least one return, "in envelope" frames with a point
inside the envelope measured from the rails; STOP is an alarm frame, advisory is a warning only:

| # | object (organizers' intent) | visible frames (from) | in envelope | STOP frames | advisory only | first STOP | STOP held from | verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | 2 × 2 m, centre (inside) | 213 (98.7 m) | 213 | 207 | 0 | 98.0 m | 98.7 m | detected at first sight |
| 2 | 0.3 m, centre, floating 1.0–1.4 m up (inside) | 79 (128.9 m) | 63 | 19 | 11 | 34.0 m | 37.4 m | detected late |
| 3 | 0.3 m, on the left rail (inside) | 49 (237.3 m) | 33 | 23 | 0 | 42.7 m | 46.2 m | detected |
| 4 | 0.3 m, at the edge (inside) | 83 (154.7 m) | 16 | 0 | 25 | — | — | advisory only |
| 5 | 0.3 m, just outside (outside) | 112 (238.4 m) | 101 | 0 | 24 | — | — | correct: no STOP |
| 6 | 2 × 2 m, at the edge (inside) | 125 (248.6 m) | 8 | 0 | 0 | — | — | missed |
| 7 | 2 × 2 m, outside (outside) | 104 (249.4 m) | 52 | 6 | 44 | 142.3 m | — | 6 false STOP frames |
| 8 | 2 × 2 m, top of the envelope (inside) | 124 (248.2 m) | 75 | 12 | 37 | 101.3 m | — | mostly advisory |
| 9 | 2 × 0.2 m, across the rails (inside) | 86 (248.5 m) | 77 | 42 | 0 | 82.2 m | 58.6 m | detected |
| 10 | 0.05 m, hanging from the roof (inside) | 42 (199.7 m) | 20 | 0 | 0 | — | — | missed |

Standard metrics (`resense summarize --gt`): STOP in 303 of the 801 visible in-gauge object-frames
(0.378): 0–50 m 113 / 227, 50–100 m 189 / 338, beyond 100 m 1 / 236 — ten synthetic objects, not
an operating recall. Alarm tracks matched to no object: 2 IDs in 3 frames, at 129–141 m. The first,
unlabelled pass (342 alarm frames, 9 alarm track IDs, 459 advisory frames of 1 510) is in
[`experiments_p4_fake_unlabelled.json`](evidence/results/experiments_p4_fake_unlabelled.json).

What the grade says (the causes in detail: P4_AUDIT "Organizer synthetic-obstacle recording"):

* **Big objects in the corridor are found at first sight** (#1 at 98 m); the plank across the
  rails (#9) from 82 m, held from 59 m.
* **0.3 m objects only from 34–43 m.** At 60–115 m a 0.3 m cube returns 2–4 points a frame; the
  clustering needs 5 voxels within 100 m. Lowering the point minimums changed nothing for them.
* **Two infrastructure signatures demote test objects**: `floating` makes #2 advisory at 47–52 m
  and #4 always; `elevated` makes #8 advisory in 36 frames (its bottom is 2.2–2.9 m above the rail
  head, inside the envelope).
* **The 5 cm hanging object never becomes a candidate**: only its lowest 0.2–0.36 m is inside the
  envelope, 1–4 points a frame.
* **A 2 × 2 m box 10–20 m ahead shadows the rails**: the rail-height fit drifts by ~0.5 m and the
  bed 2.5–8 m ahead reads as an obstacle — the STOP is right, the reported 3.0 m is not.
* **The edge tests (#4–#7) depend on the reference**: measured from the rails, #6 is outside in 117
  of 125 frames and #5 inside in 101 of 112.

**Variants** (set O, every frame; the false-alarm cost on all six original bags, every frame):

| variant | STOP frames on inside objects | STOP frames on outside objects | background alarm frames / IDs | five empty bags: alarm frames / events |
|---|---:|---:|---:|---:|
| default | 303 | 6 | 3 / 2 | 107 / 20 |
| `gauge.edge_margin_per_100m: 0` | 303 | 40 | 8 / 4 | — |
| `cluster.min_points: 3`, `min_points_far: 2` | 306 (#10: 3 at 10 m) | 6 | 3 / 2 | — |
| `cluster.gauge_min_points: 2` | 303 | 9 | 3 / 2 | — |
| `lowobj.near_enabled: true` (gates of `a92625e`, §1e) | 303 | 6 | 466 / 106 | — |
| `cluster.signature_min_lateral: 0.9` | 314 (#2 from 52.5 m) | 6 | 3 / 2 | 168 / 26 |
| `elevated` signature off | 334 (#8: 43 frames) | 6 | 3 / 2 | 139 / 23 |
| both | 345 | 6 | 3 / 2 | 186 / 26 |
| **short signatures** (experiment, `scripts/short_signature_experiment.py`) | **352** | 9 | 3 / 2 | **113 / 22** |

`doubleT_obstacle` stays at 185 of 246 labelled frames, first alarm frame 11, in every variant run
on the six bags. The two blanket relaxations take all their extra false alarms from one structure
of `squareT_platform_squareT_switch` (~104 m ahead of the stopped train, 3.9–5.7 m long, bottom
2.0–2.5 m above the rail head); the organizers' objects are 0.3–2.2 m long. Short signatures keep
`elevated` and `floating` only for clusters longer than 3 m or farther than 100 m: #2 first STOP
34.0 → 52.5 m, #4 a STOP from 14.5 m, #8 43 STOP frames (held from 31 m), for +6 alarm frames and
+2 events on the five bags and 3 STOP frames on #5 (inside the envelope measured from the rails in
those frames). **Not shipped**: since 25.09 it is the flag `cluster.short_signature_max_length`
(0 = off), exact to this experiment on every frame; on the 20-minute ride, where most
infrastructure lives, it adds 6 STOP episodes on top of the long overhead rule (limit 5), so it
stays off (decision of 25.09, §1f). None of the ten
objects lies on the bed between the rails, so the shipped bed policy is not tested by this set.

## 3. Timing (4-core sandbox, numpy path, every frame; the team VM bench of 25.09 in §3a; the 8-core run owed)

**Which machine.** Every figure below comes from the team's 4-vCPU sandbox. The jury's stand
(i7-9700E, 8 cores) is not open to the team before submission (organizers, 25.09:
[`organizers/answers.md`](organizers/answers.md) §6), so the 8-core figures will come from the
team's own 8-core machine ([`CAPTAIN.md`](CAPTAIN.md) action 7). One command records them (25.09):
`scripts/bench_8core.sh <bags>/doubleT_obstacle <bags>/roundT_doubleT` builds the image, runs the
dry runs on both bags with the node on the native and the numpy path, the console tests with the
image's and a stock Fast DDS player, `docker stats` every 2 s, and the offline timing
(`bench_node_path.py`, `resense bench`, native and numpy, peak RSS) into
`docs/evidence/bench_<date>/summary.txt`. Its first run (25.09, a team VM with 8 vCPU = 4 physical
cores, so not yet the 8-core figure) is §3a; every other number below is from the 4-vCPU dev VM.

**What is timed.** `resense bench` prints the `timing_ms` of each frame. Its `total` runs from the
first stage through tracking and **leaves out the health monitor**, which `Detector.process` runs
after it (`resense/detector.py`): 7–14 ms more per frame on the sandbox [timing: sandbox, 24.09].
The node's `/resense/latency_ms` (decode + detect + publish) includes it. "360°" is
`doubleT_obstacle`, which covers about −124…+118° of azimuth in the vehicle frame. The tables below
are the numpy path; the optional C++ kernels merged on 24.09 cut the detector time by 38–57 % with
bit-identical output ([`ARCHITECTURE.md`](ARCHITECTURE.md) "Native kernels": `roundT_doubleT`
62.4 → 33.5 ms, `doubleT_obstacle` 81.3 → 34.6 ms with p95 107 → 51 ms, `total` under load);
`RESENSE_NATIVE=0` forces the numpy path.

**DBSCAN on cKDTree (25.09, `508b04a`, output identical).** Interleaved A/B, native path, mean
`process()` wall time per frame over frames 5+, each run a fresh subprocess pinned to one core
with single-threaded BLAS; median of the per-round paired differences [min…max over rounds]
[timing: sandbox, 25.09; raw not committed]:

| recording | image's libraries (sklearn 1.5.2, 4 rounds) | sandbox's libraries (sklearn 1.9.1, 5 rounds) | numpy path, sandbox's libraries (3 rounds) |
|---|---|---|---|
| 360° `doubleT_obstacle` (201 frames) | 31.6 → 29.4 ms, **−1.6 ms (−5 %)** [−4.0…+1.1] | 31.1 → 28.3 ms, **−3.1 ms (−10 %)** [−4.8…−1.1] | 72.1 → 66.4 ms, −3.9 ms |
| 120° `roundT_doubleT` (252 frames) | 26.8 → 24.1 ms, **−2.6 ms (−10 %)** [−3.8…−0.5] | 26.4 → 22.8 ms, **−4.2 ms (−16 %)** [−6.1…−1.9] | 52.7 → 48.1 ms, −5.5 ms |
| platform `squareT_…` (frames 0–299) | 22.1 → 20.8 ms, **−1.3 ms (−6 %)** [−3.0…+1.3] | 22.2 → 19.2 ms, **−3.0 ms (−14 %)** [−4.2…−3.0] | 42.5 → 41.5 ms, −1.6 ms |

One call costs 0.77 ms instead of 1.48 ms (scikit-learn 1.5.2) or 1.80 ms (1.9.1). The detector's
per-frame output is identical on all 3 998 cached frames on both paths (ARCHITECTURE "Native
kernels").

**v0.6.3 (23.09, the idle sandbox, `resense bench --npy <recording>`, every frame, recordings
back to back, `OMP_NUM_THREADS=1`)** — a review measured the v0.6.2 code 25–33 % slower than the
v0.6 figures below still quoted in the README — in part the mount calibration measuring every
frame of its first 20 s (bisected by the review), in part the stages added since v0.6 (not
broken down); v0.6.3 measures the calibration only every 10th frame:

| recording (every frame) | **v0.6.3** mean / p95 / max | track / corridor / cluster means |
|---|---|---|
| `roundT_doubleT` (189 k points, moving) | **50.2 / 63.4 / 76.1 ms** | 27.4 / 12.6 / 10.0 |
| `doubleT_obstacle` (347 k points, 360°) | **63.6 / 77.8 / 119.2 ms** | 39.9 / 16.7 / 6.7 |
| `doubleT_platform` | **53.7 / 75.2 / 115.1 ms** | 23.9 / 11.1 / 18.4 |
| `roundT_pressureGate_roundT` | **45.6 / 57.1 / 83.1 ms** | 26.6 / 11.7 / 7.3 |
| `roundT_squareT_pressureGate_squareT` | **43.9 / 55.8 / 73.8 ms** | 26.6 / 11.3 / 5.9 |
| `squareT_platform_squareT_switch` | **42.3 / 52.8 / 81.2 ms** | 23.5 / 10.5 / 8.1 |
| `new_data` frames 2550–3149 | **43.4 / 57.8 / 87.5 ms** | 22.3 / 10.2 / 10.8 |

Raw output:
[`evidence/timing_2026-09-23/bench_v063.txt`](evidence/timing_2026-09-23/bench_v063.txt). p95 stays
inside the 100 ms frame period on every recording; through ROS the node adds ~20–25 ms per 360°
frame (§3b), which is where the 360° recording reaches the frame period on the sandbox. Re-measured
on 24.09 on another idle 4-core sandbox, the current code and v0.6.3 back to back: 36.5–52.2 against
35.1–57.4 ms mean (p95 50.3–67.1 against 46.3–75.4 ms), −9…+6 % per recording — no regression
("Re-measurement" at the top; that sandbox is faster, so the table above stays the quoted figure).

**v0.6 (22.09, the idle sandbox, nothing else running; `resense bench --npy <recording>`,
every frame, recordings back to back; the load of 1–3 is the bench's own BLAS threads).**
`total` covers mount calibration, track model, corridor and the low-object stage, clustering and
tracking; the health monitor runs after it and is not included (see above):

| recording (every frame) | **v0.6** mean / p95 / max | track / corridor / cluster means | v0.5 mean / p95 (below) |
|---|---|---|---|
| `roundT_doubleT` (189 k points, moving) | **45.3 / 55.9 / 93.4 ms** | 26.8 / 11.6 / 6.7 | 43.0 / 50.9 |
| `doubleT_obstacle` (347 k points, 360°) | **57.9 / 69.1 / 109.6 ms** | 37.1 / 16.4 / 4.3 | 54.9 / 59.6 |
| `doubleT_platform` | **42.2 / 52.5 / 100.7 ms** | 22.9 / 10.2 / 8.9 | 83.3 / 170.8 |
| `roundT_pressureGate_roundT` | **43.0 / 52.8 / 86.7 ms** | 26.6 / 11.6 / 4.7 | 43.4 / 52.6 |
| `roundT_squareT_pressureGate_squareT` | **43.4 / 53.1 / 84.6 ms** | 27.2 / 12.2 / 3.8 | 42.3 / 54.2 |
| `squareT_platform_squareT_switch` | **43.4 / 52.2 / 81.2 ms** | 27.4 / 11.9 / 4.0 | 84.3 / 111.6 |
| `new_data` frames 2550–3149 (files 50–61: approach, station, departure) | **44.0 / 58.1 / 91.4 ms** | 26.0 / 12.1 / 5.7 | — |

p95 is inside the 100 ms frame period on **every** recording now, the platform bags included.
The v0.6 additions cost 2–5 ms mean on the tunnel bags (the corridor stage, 7 → 12 ms, now
holds the bed template and the low-object candidates; the calibration runs on the first
frames only). The platform bags got twice as fast (83 → 42 ms mean, p95 171 → 53 ms): the
2.1 m envelope keeps the platform edge out of the corridor, so DBSCAN no longer sees 15–20 k
candidates per frame. The maxima (81–110 ms) are single frames (the cold first fit, the
calibration frames).

**CPU and memory** (23.09, the same machine, frames loaded one at a time, `Detector.process` only):
`roundT_doubleT` 47 ms of CPU per frame, `doubleT_obstacle` 65 ms — **one core, 47–65 % of it at 10
Hz** — and 160–180 MB resident. With the library defaults the BLAS threads of numpy kept 3.9 cores
busy on the 347 k-point frames (250 ms of CPU per frame) for no speed-up (64 vs 65 ms wall time);
the image therefore sets `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`. The ROS node adds
~20–25 ms per 360° frame (message conversion, decode, publishing; §3b), part of which is the health
monitor that the node's latency includes and `total` does not; the jury's i7-9700E (8 faster cores)
is not open to the team before submission, the team's 8-core machine stands in (top of §3).

**v0.5 (history).**

Where the v0.5 time went before the cost work (cProfile over frames 100–114 of
`roundT_doubleT`, load 4.6): the rail-slab profiles called `np.percentile` once per 5 cm bin
(6 208 calls per 14 frames, 49 ms per frame), the bed height was evaluated six times per frame
on the whole cloud (13 ms), and the polygon test ran on all 190 k in-range points (14 ms).
After vectorising the per-bin percentile (one sort per profile, exact linear interpolation),
computing the bed height and the corridor coordinates once per frame and prefiltering the
polygon test by its bounding box, the same frames took: track 81 → 31 ms, corridor 16 → 7,
egomotion 9 → 7 (now off by default), cluster 6, total 112 → 52 ms.

**Back-to-back bench on the idle machine** (`resense bench --npy /data/cache/<bag>`, every frame,
commit 9b56bdf (merged as 82815e9); the v0.3 switches are the config of §1b; load before each run in
the table; the i7-9700E has 8 faster cores):

| bag (every frame, quiet 4-core sandbox, load < 1, runs back to back on 22.09) | v0.3 code (f2c57e5) mean / p95 / max | **v0.5 final** mean / p95 / max | v0.5 stage means |
|---|---|---|---|
| `roundT_doubleT` (189 k points, moving) | 56.4 / 70.6 / 83.2 ms | **43.0 / 50.9 / 87.7 ms** | track 28.8, corridor 6.7, cluster 7.2, tracking 0.3 |
| `doubleT_obstacle` (347 k points, 360°, stationary) | 70.7 / 75.9 / 92.7 ms | **54.9 / 59.6 / 79.7 ms** | track 38.1, corridor 11.5, cluster 5.0, tracking 0.4 |
| `doubleT_platform` | (v0.3 run of 21.09 under load: 79 / 132) | 83.3 / 170.8 / 196.3 ms | the platform approach: tens of thousands of candidates in the cluster stage, as in v0.3 |
| `roundT_pressureGate_roundT` | (56 / 89) | 43.4 / 52.6 / 71.6 ms | |
| `roundT_squareT_pressureGate_squareT` | (61 / 101) | 42.3 / 54.2 / 98.0 ms | |
| `squareT_platform_squareT_switch` | (83 / 131) | 84.3 / 111.6 / 151.3 ms | |

The vectorised bed / wall binning and the polygon bounding-box prefilter pay for the rail-slab
yaw and the bed verification (each ~3–4 ms mean, ~10 ms p95 in the track stage, reviewer's
attribution runs); the reviewer's pairs under load 4–7 gave the same picture (v0.3 code 83.7 /
120.8 vs v0.5 69.1 / 98.2 on `roundT_doubleT`). With a given speed the accumulation adds the
merged-cloud clustering (+12 ms mean on `roundT_doubleT` at load 8, reviewer's run). The frame
period is 100 ms: p95 is inside it on the tunnel bags and above it on the two platform bags on
this machine, where the node drops frames rather than queueing; the jury's i7-9700E (8 faster
cores) is not open to the team before submission (top of §3).

Per-stage means of the same runs are in the table; the platform bags remain the expensive ones
because their corridor holds 15–20 k candidates per frame (DBSCAN 45–70 ms in v0.3 and v0.5 alike).
The frame period is 100 ms; the ROS node adds message conversion, decode and publishing (~20–25 ms
at 360°, §3b; part of which is the health monitor, 7–14 ms, not in `total`), and drops frames
rather than queueing, so the node's dropped-frame counter is the number to watch on the bench.

### 3a. The bench kit on the team VM (25.09): 8 vCPU = 4 physical cores, not yet the 8-core analogue

**Machine.** A Yandex Cloud VM: Intel Xeon (Icelake) at 2.0 GHz, **8 vCPU = 4 physical cores × 2
threads**, 15.6 GiB RAM, Ubuntu 22.04, Docker 29.8.1, CPU steal 0.0 % before the runs; code
`7290873` (the long overhead rule shipped later, `935eecf`, changes no frame of the two bags played
here, §1f). The i7-9700E has 8 physical cores without SMT at 2.6–4.4 GHz, so this is **not** the
8-core analogue C8 asks for: the node's own work is one thread, but in `dry_run.sh` the node, the
player and the recorder share these 4 cores. The bags were played from a RAM tmpfs: the VM's network
disk reads 64 MB/s sequentially (`dd`, direct I/O), below the ~220 MB/s at which `ros2 bag play`
reads the 4.5 GB 360° bag. `scripts/vm/run_plan.sh bench` → `scripts/bench_8core.sh` (image from
the layer cache); raw: [`evidence/bench_2026-09-25/`](evidence/bench_2026-09-25/) (`summary.txt`).

| run (Docker chain, rate 1.0) | kernels | frames processed | fps | decode + detect mean / p95 / max | detector mean / p95 | dropped (after 5 s) | container CPU % mean / max | memory MB | check |
|---|---|---|---|---|---|---|---|---|---|
| `dry_run.sh doubleT_obstacle` (360°) | native | 146 / 201 | 10.0 | 58 / 70 / 171 ms | 27 / 38 ms | 53 (20) | 93 / 190 | 4 806 | FAIL: drops |
| same | numpy | 116 / 201 | 8.3 | 104 / 118 / 154 ms | 65 / 78 ms | 76 (45) | 123 / 238 | 4 463 | FAIL: p95, drops |
| `dry_run.sh roundT_doubleT --expect-clear --max-alarm-frames 2` (120°) | native | 233 / 252 | 10.0 | 38 / 48 / 57 ms | 24 / 34 ms | 14 (0) | 58 / 100 | 2 106 | FAIL: 4 alarm frames |
| same | numpy | 231 / 252 | 10.0 | 65 / 77 / 81 ms | 48 / 60 ms | 17 (0) | 86 / 122 | 2 159 | FAIL: 3 alarm frames |
| `console_test.sh` `roundT_doubleT` → `doubleT_obstacle`, player uid 1000, image's DDS profile | native | 378 / 453 | 10.0 | 46 / 68 / 84 ms | 25 / 36 ms | 70 (55) | 55 / 106 | 1 055 | PASS |
| same, stock Fast DDS player (`PLAYER_DDS=stock`) | native | 381 / 453 | 10.0 | 47 / 68 / 104 ms | 25 / 36 ms | 72 (55) | 54 / 123 | 1 113 | PASS |

In `dry_run.sh` the container holds the node, the player and the recorder, hence its CPU above
100 % and its memory: the player preloads the whole 4.5 GB recording (§3b). `console_test.sh`
measures the node container alone: about half a core at 10 Hz on the native path.

Offline on the host (python 3.10, numpy 2.2.6, one BLAS thread, every frame; peak RSS):

| recording | node path (`bench_node_path.py`: decode + crop + rotate + detect) native / numpy, mean / p95 | stages (`resense bench`, health monitor not included) native / numpy, mean / p95 | numpy ÷ native |
|---|---|---|---|
| `doubleT_obstacle` (360°) | 43.4 / 54.7 ms · 84.3 / 97.4 ms (238 MB) | 25.4 / 36.5 ms · 61.9 / 75.3 ms | 1.94× · 2.44× |
| `roundT_doubleT` (120°) | 33.6 / 44.0 ms · 59.3 / 70.9 ms (150 MB) | 23.4 / 34.4 ms · 47.0 / 59.4 ms | 1.76× · 2.01× |

**What fails, and why.** Every `dry_run.sh` failure repeats in the dry run and the offline rehearsal
of the same day ([`evidence/dry_run_2026-09-25/`](evidence/dry_run_2026-09-25/),
[`evidence/offline_2026-09-25/`](evidence/offline_2026-09-25/)):

* `doubleT_obstacle`, native: p95 70 ms and 10 fps pass; the drop criterion does not. The player's
  preload leaves the node 4.8 s of recording behind; the v0.6.4 catch-up (one frame per 0.3 s of
  recording) ends at 7.7–7.9 s, so ~16–18 of its skips fall after the checker's 5 s window. The
  rest is 4 frames at 13.1–13.4 s (1) and 16.0–16.3 s (3) of the recording, in the same place in both
  native runs of the day (`status.jsonl.gz`, counter `node.dropped_frames`).
* `doubleT_obstacle`, numpy: 8.3 fps, p95 118 ms: the numpy path does not keep up at 360° on this
  VM with the player on the same 4 cores.
* `roundT_doubleT`: every run through ROS on this VM (6 of 6, both paths, both player modes) has 3
  alarm frames at 111.0–114.9 m, 23.6–23.9 s into the recording; offline the same recording has
  its 2 known frames at 128.3–130.2 m (§0). The catch-up at the start changes which frames the
  tracker sees. One native run also had a frame at 53.0 m: the trackside start-frame case of §0.

**The `doubleT_obstacle` drops, diagnosed [measured 25.09].** From the node logs, captures and
`docker stats` of the dry run and the native bench run (numbers in that order). *Start-up*: the
first cloud reached the node 6.5 / 5.7 s after the player's clock started, while one core ran the
player's preload (container memory 0.2 → 4.1 / 4.7 GiB, the node idle); 4.8 / 1.8–4.9 s of
recording were then waiting, and the catch-up processed 30 frames in 2.3 / 2.8 s (decode + detect
62 / 63 ms mean) and was back on the newest frame at +7.9 / +7.7 s. Cold start is not the cause:
frame 0 took 98 / 171 ms against 69–72 ms for frames 1–3; CPU steal 0.0 %, container CPU ≤ 190 % of
8 vCPU. *Counting*: `dropped_frames` included the catch-up's own skips, 16 of the 20 "after 5 s".
Before +7.9 / +7.7 s 59 / 55 frames of the recording were not processed and the logs report 52 / 39
skipped, so ≤ 7 / 16 were lost inside the burst (the player's writer keeps 10 samples, §3b).
*The 4 later ones are holes of the recording*: 1 frame at +14.0 s and 3 at +16.9 s of the bag, the
same header stamps in all three runs and in the CycloneDDS run at 32 MiB; the bag's own receive
times jump by 0.201 and 0.413 s there (201 messages in 205 frame periods; `roundT_doubleT` has no
such gap and no drop after 5 s). Latency around them 54–57 ms, after the catch-up at most 70 / 83 ms.
*Changes (no processed frame and no decision changes)*: the status reports `node.catchup_skipped`
and `node.catchup`; `check_dry_run.py` counts drops after the later of 5 s and the end of the
start-up catch-up (at most 15 s), and with `--bag` (passed by `dry_run.sh`) the recording's messages
not processed. The two captures, with the catch-up end of their logs, keep 4 drops after it, and 0
against the bag's receive times (the frame cache's stamps with an estimated first header stamp;
the VM re-run with the original bag decides). Offline on the 4-vCPU sandbox (load 7–8 from other
jobs; native kernels; the first 12 frames of `doubleT_obstacle` in the 921 600-slot layout through
the node's path, a fresh process per run, 6 runs each): frame 0 took 91 ms cold, 80 ms after a
throwaway detector had processed one real frame; frames 1–4 82 / 79 ms, 5–11 68.5 / 68.5 ms, output
identical: a warm-up would save ~15 ms once, so none was added. Threads: the native kernels use no
OpenMP, `cKDTree.query_pairs` one thread, the image pins BLAS to one; numpy's default pool on this
busy box made the same path 256 ms per frame against 67 ms (5 runs each), so the ROS package now
defaults OMP / OpenBLAS / MKL to one thread outside the image too.

The 8-core figure (C8) still needs 16 vCPU (8 physical cores) or the team's own 8-core machine; the
kit runs unchanged there.

### 3b. The ROS 2 node in Docker on real recordings (23–24.09, v0.6.2–v0.6.4)

**Setup.** A Docker daemon runs on the sandbox (4 vCPU, 16 GB), so on 23.09 the organizers'
procedure was run for the first time on real frames: `docker build` of `docker/Dockerfile` (with
the sandbox's proxy CA added after `FROM`, nothing else changed), the node started as
`docker run --net=host --ipc=host resense` (the image's default command), the recordings played
by `ros2 bag play --delay 3` from **a second container** (standing in for the host console), and
`/resense/status` recorded by a third one. The original bags were no longer on disk; they were
rebuilt from the frame cache by `scripts/cache_to_bag.py` — same topic, `frame_id`, PointCloud2
layout (`point_step` 26, empty dual-return slots, scan order) and receive times; coordinates
carry the cache's 5 mm quantisation. Scored by `scripts/check_dry_run.py`.

**What the first run found.** The node received **5 of the 201 clouds** of `doubleT_obstacle`: a
360° cloud is ~10 MB, ~160 UDP fragments, and the node's best-effort subscription loses a whole
message with any fragment; it then reset its scene on every "hole" and confirmed nothing. `ros2 bag
play` publishes these recordings reliable (every original `metadata.yaml` records `reliability: 1`,
[`evidence/bag_metadata/`](evidence/bag_metadata/)); a reliable reader received 174+ of 201 in the
same setup. v0.6.2 adds `input_reliability` (default `auto`: subscribe reliable, and match the
publishers within a second — best-effort when a publisher is, e.g. a live sensor-data driver, to
which a reliable reader would get nothing). The CI smoke test had not caught it: its synthetic
clouds are a third of the size.

**What a review found next.** With the player run **as a normal user** — the organizers play the
bag from their host console — the node received nothing at all: with `ipc=host`, Fast DDS puts
the node's shared-memory segments in `/dev/shm` as root-owned 0644 files the player cannot
write. (`umask 0000` in the container does not help: Fast DDS sets the mode.) The image now runs
Fast DDS over UDP only (`docker/fastdds_udp.xml`, `FASTRTPS_DEFAULT_PROFILES_FILE`); on the
10 MB clouds this measured the same rate and latency as shared memory. `scripts/console_test.sh`
(node container, player as uid 1000 in another container, status recorded by a third) checks it
in CI on the two synthetic bags. The node also publishes `FAULT` / `NO_INPUT` while no frame
has arrived yet instead of staying silent.

| run (v0.6.2 image) | frames processed | fps (2 s windows) | latency decode + detect mean / p95 | detector stage mean | result |
|---|---|---|---|---|---|
| `dry_run.sh` `roundT_doubleT` (120° window, `/lidar_points` + `hesai_lidar`), node and player in one container, root | 237 of 252 | 10.0 | 65 / 76 ms | 53 ms | 2 alarm frames at 128.3–130.2 m — the same frames as the offline evaluation (§0) |
| `dry_run.sh` `doubleT_obstacle` (360°, `/sensing/lidar/hesai128/pointcloud` + `lidar_livox`), one container, root | 103–134 of 201 | 7–9 in steady state (6.8–8.3 in the stored log), lower at the start | 96–99 / 112–130 ms | 74–76 ms | obstacle 55.9–56.6 m, 88–118 alarm frames |
| **`console_test.sh`**, player **uid 1000** in its own container, UDP profile: `roundT_doubleT` then `doubleT_obstacle` into the same running node | 351 of 453 | 8.3–10 in steady state | 82 / 102 ms | 65 ms | input switched, detector restarted; 131 alarm frames: the person and the object at 56.1–56.5 m and the 2 known frames at 128–130 m of `roundT_doubleT` |
| `console_test.sh` on the two synthetic bags (the CI step) | 72 of 80 | 5 (bag at 0.5×) | 65 / 78 ms | 53 ms | PASS |
| CI smoke test (`scripts/smoke_test.sh`, one container) | 76 of 80 | 5 (bag at 0.5×) | 64 / 76 ms | 52 ms | PASS |

**The first seconds of a played bag (v0.6.3: lost; v0.6.4, 24.09: worked through).** Until
v0.6.3 the first cloud of a played recording arrived, then the next one 2–5 s later in recording
time, and every such hole reset the scene: the first STOP of the person came at 5.7–9.2 s of
recording time through ROS against 1.1 s offline. It was blamed on the DDS start-up; a packet
capture on 24.09 showed it is the player: `ros2 bag play` (Humble) starts its clock, then reads
min(1000 messages, the whole bag) before its first publish — 1.9 GB for `doubleT_obstacle` — and
then sends the overdue frames back to back (the first DATA_FRAG left the player 4.13 s after it
started publishing, clouds 1–46 followed in 0.39 s, then one every 100 ms; with
`--read-ahead-queue-size 5` the first cloud left at +0.11 s). `--delay 3` sleeps before the clock
starts and the preload, so it does not help. The node's keep-last-1 input kept only the newest
cloud of that burst. v0.6.4 holds 40 frames (`input_queue_depth`), takes every waiting frame, and
works through a backlog one frame every `catchup_step` = 0.3 s of recording from the recording's
first frame until it is back on the newest; a frame that waits alone is processed at once, as
before (`catchup_step: 0` restores the newest-only behaviour). In the Docker chain on bags rebuilt
from the frame cache (4 vCPU, 3 runs per cell, the player as uid 1000 in its own container unless
said; "gap" = recording time of the second processed frame, "largest gap" within the first 5 s):

| recording, setup | version | gap | largest gap | frames in the first 5 s | first STOP (recording time) | frames processed | scene resets per run | peak RSS |
|---|---|---|---|---|---|---|---|---|
| `doubleT_obstacle` (360°) | v0.6.3 | 2.32 s (2.09–2.59) | 2.07 s | 18 (13–26) | 4.02 s (3.19–4.48) | 161 | 1–2 | 182 MB |
| | **v0.6.4** | **0.38 s** (0.28–0.48) | **0.40 s** | 23 (21–27) | **1.59 s** (1.30–1.99) | 173 | **0** | 434 MB |
| same, player inside the node container | v0.6.3 / **v0.6.4** | 2.25 / **0.28 s** | 2.06 / **0.30 s** | 22 / 23 | 3.42 / **1.30 s** | 172 / 171 | 1 / **0** | — |
| same, stock `net.core.rmem_max` 212992 | v0.6.3 / **v0.6.4** | 2.95 / **0.48 s** | 2.69 / **0.34 s** | 16 / 25 | 4.35 / **1.59 s** | 162 / 175 | 1–2 / **0** | 180 / 403 MB |
| `roundT_doubleT` (120°) | v0.6.3 / **v0.6.4** | 2.02 / **0.28 s** | 2.02 / **0.29 s** | 26 / 40 | — | 223 / 241 of 252 | 1–2 / **0** | 143 / 188 MB |
| same, stock `rmem_max` | v0.6.3 / **v0.6.4** | 1.78 / **0.39 s** | 0.99 / **0.38 s** | 32 / 37 | — | 228 / 238 | 0–1 / **0** | — |

[team record, unverified: the node logs and status captures of these 24.09 runs are not committed;
the 23.09 captures are in [`evidence/docker_2026-09-23/`](evidence/docker_2026-09-23/).]

The node catches up in 1.5–2.2 s of wall time at 360° (at most 2.1–3.7 s of recording behind) and
0.3–0.7 s at 120°; after that fps (9.3–10) and latency (74–80 ms at 360°, 53–58 ms at 120°) are as
before. `scripts/console_test.sh` on the two real recordings and `scripts/dry_run.sh` on
`doubleT_obstacle` pass (largest gap 0.3 s, first STOP +1.3 s); the checker now prints the start
of the input (frames in the first 5 s, largest gap, first STOP). Not kept: a reader-side Fast DDS
profile (heartbeat response 0, initial acknack 0, faster announcements) — the first cloud still
came 2.7 s after the player started; larger socket buffers change nothing (the hole and the fix
are the same at 212992 and 4 MB). What remains: the player's preload itself (`FAULT` / `NO_INPUT`
for 2.6–4 s here, longer from a slow disk; nothing on the node's side can shorten it); the
frames between the catch-up steps are not processed (21–27 of ~50 in the first 5 s at 360°);
during the burst the node's UDP receive buffer can overflow and a late repair lose one of the
first 1–3 clouds (the player's writer keeps 10 samples); ~0.25 GB more resident memory at 360°.
With a live sensor a stall longer than 0.3 s is now worked through at ~3× real time instead of
jumping to the newest frame. The trackside false alarm at 48–54 m of `roundT_doubleT` (the
start-frame sensitivity of §0) appeared in 2 of 9 v0.6.3 runs and 3 of 22 v0.6.4 runs.

**Resources of the node container** (`docker stats` every ~0.5 s during the `doubleT_obstacle`
replay by a uid-1000 player): **~100 % of one core while frames arrive (median of the busy samples;
max 102 %), 186 MB** (v0.6.2 image, `ct_real_docker_stats.txt`) — at 360° the node is compute-bound
on the sandbox. The detector stage costs the same in the image (Python 3.10, numpy 1.26) as on the
host (74 vs 68 ms on the first 100 frames of `doubleT_obstacle`); the ROS path adds ~20–25 ms per
360° frame (message conversion, decode — `pointcloud2_to_arrays`, 40 → 9 ms in v0.6.2 — and
publishing the markers and the corridor cloud; part of which is the health monitor, 7–14 ms, not
in `total`). The node skips frames instead of lagging, as
designed (keep-last 1 until v0.6.3; since v0.6.4 a 40-frame queue worked through by the catch-up
above): over a whole 360° recording it processes 103–142 of 201 frames (v0.6.3, the start-up hole
included; v0.6.4: 171–175), 7–10 fps in steady state; the 120° recordings run at the full 10 Hz.
Captures, node logs and the checker output:
[`evidence/docker_2026-09-23/`](evidence/docker_2026-09-23/). The jury's i7-9700E (8 cores, higher
clock) is not open to the team before submission; the 8-core bench of the team stands in (§3).

**With RViz, on screen** ([`video/docker_chain_rviz.mp4`](video/docker_chain_rviz.mp4), 69 s, image
built from the current tree). The node container started with `rviz:=true` on a virtual display
(Xvfb, software OpenGL, no GPU), `ros2 topic echo /resense/decision` in a second container, the bag
played as uid 1000 from a third — every command on screen is the one that ran. The bag played at
0.5×: RViz renders the 360° cloud in software at 6–10 fps on the same 4 vCPU. Node log
([`evidence/docker_2026-09-23/rviz_chain_node.log`](evidence/docker_2026-09-23/rviz_chain_node.log)):
`FAULT` (no input) until the first cloud; a 1.1 s start-up hole (v0.6.3; the player's burst above);
OBSTACLE at 55.7–56.3 m from its frame 11 to 177; the last frames alternate STOP with CAUTION (the
object missed in that frame, advisory tracks at 11.6 m and beyond 139 m — the `console_test` capture
ends the same way, and offline the object is missed in 8 of its 126 frames); `FAULT` / `STALE` 0.5 s
after the bag ended. 5 fps (the input rate at 0.5×), latency mean 104–122 ms, p95 116–150 ms with
RViz on the same cores, 15 of 201 clouds skipped. The recording found one more transport defect:
**the shipped RViz config subscribed the raw clouds best-effort**, so during `ros2 bag play` it
would have shown almost none of them (the node's own first-run failure); it now subscribes reliable,
like the node (`rviz/resense.rviz`).

**Without a Docker daemon** (24.09, `a92625e`): `scripts/dry_run.sh`, `console_test.sh`,
`build.sh`, `run_demo.sh` and `run_headless.sh` check the daemon first (`scripts/require_docker.sh`)
and exit 3 with a diagnostic instead of reporting a result; `scripts/smoke_test.sh` exits 3 outside
the ROS 2 image. Offline latency needs no Docker: `resense bench --npy <cache>` or
`scripts/bench_node_path.py --npy <cache>` on a non-empty cache.

**Dry run with the original bags and the offline rehearsal, 25.09 (team VM, a rehearsal of the later
deployment).** `scripts/vm/run_plan.sh dryrun` and `offline`, code `7290873`, on the VM of §3a
(8 vCPU = 4 physical cores, Ubuntu 22.04 with stock ROS 2 Humble on the host), the **original** bags
played from a RAM tmpfs (the VM disk reads 64 MB/s); raw:
[`evidence/dry_run_2026-09-25/`](evidence/dry_run_2026-09-25/),
[`evidence/offline_2026-09-25/`](evidence/offline_2026-09-25/). Online, after a `--no-cache` build:
`doubleT_obstacle` person 55.7–56.5 m, first `STOP` +1.6 s, p95 69 ms, 10 fps, but 20 frames dropped
after 5 s → **FAIL** (the drop criterion only; §3a: the start-up catch-up runs past 5 s, plus 4
frames later); `roundT_doubleT` 3 alarm frames at 111.0–114.9 m against 2 allowed → **FAIL**;
`console_test.sh` with the image's and with a stock player **PASS**; the host console as a normal
user (`ros2 bag play` + `ros2 topic echo`, stock `rmw_fastrtps_cpp`, no profile) **PASS** (137
`STOP`, 55.7 m); the same with **`rmw_cyclonedds_cpp`: FAIL**, only 0–1 of the 201 360° clouds
reached the node (the 120° clouds did); with `net.core.rmem_default` / `rmem_max` raised to 32 MB for
one run they all arrived (`dry_run_2026-09-25/diag_cyclonedds_buffers/`; `wmem` was raised with
them, the node's side is the receive buffer). Since then the node logs a WARN with the host fix
when `rmem_max` is below 32 MiB, and the image asks for 32 MiB receive buffers instead of 8 MiB (a
whole cloud fits; the buffer is set explicitly, so only `rmem_max` caps it, silently, and Fast DDS
2.6 keeps the capped buffer: no change at 212992; README, ARCHITECTURE "Transport"). Offline (outbound blocked
by the kit's iptables chain, no host allowed, restored after 4 min; nothing but the kit's own probes
tried to go out): the archive of [`evidence/export_2026-09-25/`](evidence/export_2026-09-25/) loaded
in 29 s after every image was deleted, `load_image.sh` PASS; the README jury commands from the host
console **PASS** (134 `STOP`, 55.7–56.5 m, first `STOP` +2.3 s, p95 71 ms); `IMAGE_TAR=… OFFLINE=1
dry_run.sh` fails the same two criteria as online (22 dropped after 5 s; 3 alarm frames at
111–115 m).

## 4. What we learned / hard cases

1. **Sensor mounts differ between bags** (bed 1.5 m vs 2.0 m below the sensor, axis 0.05–0.25 m
   right of the sensor axis) → any fixed calibration fails; the rail-ridge self-calibration is
   stable to ±0.05 m frame to frame, provided the profile is built in the coordinates of the
   previous axis (in absolute Y the ridges smear in curves, §1b). The organizers answered on 24.09
   that the test bags use the mounts of the provided ones, the LiDAR 1 075 mm above the rail head on
   the train's centreline
   ([`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md)): the calibration stays
   as a safeguard.
2. **Curves**: the v0.3 axis applied half the measured curvature and took its yaw from a free
   quadratic through the walls (§1b finding 1): the corridor drifted into the outer wall /
   column row at 50–130 m in the three curve bags, which is where the columns and wall
   segments came from. The rails give the yaw, the walls the curvature; at tunnel-type
   transitions (walls diverge) the parallel side wins and the corridor is trusted to 60 m
   only.
3. **Height reference beyond the bed fit** (§1b finding 2): the extrapolated bed is 0.3–0.65 m
   off at 85–105 m in the platform bags; the roof and the far rails then enter the polygon.
   Trust it 20 m beyond the fit and as far as the side structures verify it; do not classify
   low or elevated clusters beyond. It still does not *correct* the bed, so the far bins of
   set S are limited by the same reference (§2c).
4. **Platform stop + switch bag** was 504 of the 1 001 v0.3 false-alarm frames: two roof strips (700
   frames between them), the hall's end wall at 72–78 m, and switch parts at 147.5 m, all seen by a
   stopped train for 40 s. v0.5 leaves 56 frames / 18 events there, 50 of them the platform-end
   structure at 82.9 m (see §1): the curvature beyond a platform comes from the hall walls, which
   follow the platform rather than the track curving into the tunnel, so the corridor at 80–90 m is
   0.5–0.8 m off — a station-curvature limitation ([`ALGORITHM.md`](ALGORITHM.md) §6.2), not a shape
   signature.
5. **Corridor-edge structures** at 1.5–1.6 m from the axis are 0.1–0.2 m outside the 1.40 m
   gauge (ALGORITHM §6.1): the strict decision needs a centimetre-accurate axis there, or a
   margin that grows with range; the crossing person of `doubleT_obstacle` leaves the gauge
   through exactly that band (label margins of ±0.25 m in frames 70–76), so every margin costs
   borderline frames of a real object.
6. **Small objects**: anything below rail head + 12 cm inside the rails and low/narrow hardware
   (< 0.35 m top, < 0.4 m wide) is filtered — a 20 cm object on the sleepers is invisible by
   design, and an object below the envelope between the rails is not an obstacle by the
   organizers' answer of 25.09 ([`organizers/answers.md`](organizers/answers.md) §8). (The ride
   has no obstacles; none of the organizers' ten test objects of set O lies on the bed, §2e; the
   opt-in near-bed path with its first gates raised the ride's false events from 47 to 667 [team
   record, unverified], and with the current gates the five bags' from 20 to 107, §1e.)
7. **Point budget** is the physical limit: 0.5 m object = 7 pts @100 m, 1.6 pts @200 m.
8. **Injected objects beyond ~80 m are often fully occluded** because the v0.5 injector placed
   them 0.15 m below the per-frame extrapolated rail head, which lies under the real bed there
   (§2c): the far bins of set S measure the injector as much as the detector. Since 24.09 set S
   stands objects on the local bed ([`P4_AUDIT.md`](P4_AUDIT.md)).
9. **The organizers' own objects are harder than ours** (set O, §2e): a 0.3 m cube returns 2–4
   points a frame at 60–115 m, so a single frame confirms it only from 34–43 m; the `floating`
   and `elevated` signatures, fitted to infrastructure on empty data, demote three of their
   objects; a 5 cm hanging object never becomes a candidate; and the edge tests depend on the
   reference (the organizers' sensor axis is −0.24° to the rails the detector follows).

## 5. Open experiments

Owners and dates: [`CAPTAIN.md`](CAPTAIN.md) §3; the expected gain per criterion:
[`SCORECARD.md`](SCORECARD.md) §6. Done or superseded since 22.09: the injector's local-bed
placement (P4, 24.09, [`P4_AUDIT.md`](P4_AUDIT.md)), the 0.5 s confirmation as the default
(v0.6.2, §0), the GOST 23961-80 gauge polygon (replaced by the organizers' 2.1 × 3.0 m envelope,
v0.6).

- ~~**short signatures and the long overhead rule** (25.09; §1f): the ride and set F straight
  with `scripts/regression_gate.py --set …`, then the go / no-go~~ decided 25.09 on the ride
  (§1f): the long overhead rule on (ride 47 → 46 events), short signatures off (ride STOP
  episodes +6 for +49 set O STOP frames);
- **thin hanging objects** (P3, P4; §2e): the organizers' 5 cm object dips only 0.2–0.36 m into the
  envelope with 1–4 points a frame and never becomes a candidate; a rule for thin clusters near
  the axis linked to points above the envelope, measured on set O, the empty bags and the ride;
- **the rail shadow of a large near object** (P3; §2e): a 2 × 2 m box 10–20 m ahead hides the
  rails, the rail-height fit drifts by ~0.5 m and a wrong 3.0 m distance is reported;
- ~~**the near-bed path with the current gates** (`537e220` + `7df1796`; P3; §1e): the ride and set F
  on the bed before any change of its default~~ dropped 25.09: a bed object below the rail head is
  not an obstacle (organizers' answer to Q3, [`organizers/answers.md`](organizers/answers.md) §8),
  the path stays off;
- **the far-rail check** (P3; §1e, §1f): never fires on the six recordings and set O (25.09);
  only the ride is left, and it is not expected to change anything;
- **the 82.9 m platform end** (P3; §1f): 10 of the 25 STOP episodes at the platform come from the
  axis being ~0.5 m off at 83 m (hall-wall curvature); a fix in the axis model, not a shape rule;
- **bed correction from the side-structure base** (P3): use `z_base(X) − offset_ref` as
  `z_floor(X)` beyond the fit where the side base is continuous, then re-measure the far bins
  and the 147.5 m switch structures;
- **bed-trough centre vs wall axis** at stations (design in v0.4, not implemented): a second
  lateral axis where the walls are far;
- ego-speed estimator (measured 24.09, §9): accurate (median error 0.06–0.08 m/s) on 55–96 % of
  the moving frames; the tracks cue reports 1.2–2.2 m/s at a standstill on 5 frames. A speed does
  not pay on the organizers' synthetic check, so the next step, if any, is the `floating`
  signature that demotes the merged 0.3 m cubes, not the estimator;
- more *labelled obstacle* materials, if provided in future → calibrate dropout / intensity
  in `inject` and measure real recall by range and class. The delivered `new_data` ride has
  no obstacles, but supports false alarms per km and FP taxonomy by scene with the label tool;
- timing on the team's 8-core machine (the i7-9700E stand is not open to the team before
  submission, §3), native and numpy paths: one command, `scripts/bench_8core.sh` (25.09). Of the
  CPU savings the GPU study measured as prototypes ([`ARCHITECTURE.md`](ARCHITECTURE.md) "GPU:
  evaluated, not used"), the exact cKDTree DBSCAN shipped on 25.09 (§3); the forward crop and the
  reuse of the bed height were measured and not shipped (§7); float32 corridor coordinates and a
  single-pass C++ decode in the node (−11…−20 ms at 360°) are not built.

**Independent set F placement** (P4): needs a separately surveyed vehicle-frame axis and rail
profile of the ride, not the detector's far fit (protocol: [`EVALUATION.md`](EVALUATION.md) §3).
With the full-rate `new_data` cache and its stamps, for example:

```bash
mkdir -p out
python scripts/far_range_eval.py --cache /data/cache/new_data --files 46,68,98,140,168,172 \
  --frames 110 --kinds person,box0.5,box1.0 --start 200 --seed 3 --jobs 4 \
  --placement-mode independent --axis-center <survey_m> --axis-yaw-deg <survey_deg> \
  --axis-curvature <survey_per_m> --rail-z0 <survey_m> --rail-grade <survey_m_per_m> \
  --lateral=-0.8:0.8 --lateral-offset 0.15 --yaw-perturb-deg 10 \
  --out out/far_independent.json
```

The `setF-placement-v1` JSON records the run parameters, the SHA-256 of the config and of the
speed input, the cache file names, per-frame truth and visibility, the summary and a hash of the
selected frame stamps. A single fixed vehicle-frame axis over a moving curve is an approximation:
validate the reference for each sequence before reading its results as evidence about curves, and
repeat with other offsets, yaws and surveyed curves under the same seed.

## 6. Mount calibration on real frames (v0.6.1)

`scripts/calib_check.py --npy <recording>`: a whole recording (201–260 frames, so that the
20-second final window completes), re-mounted by known rotations (the cloud rotated as a
sensor mounted that way would see it), a fresh detector over it. The residual is measured
against the correction found on the recording *as it is* — a rig may be tilted itself, which
is not an error — and split into tilt (roll + pitch) and yaw. Mount yaw below
`calibration.min_yaw_deg` (3°) is left to the per-frame track model by design, so the 2° of the
combined case stays in the yaw column.

| re-mount | `roundT_doubleT` (frames 0–251) tilt / yaw residual | `roundT_squareT_pressureGate_squareT` (100–359) | `doubleT_obstacle` (0–200, 360°) |
|---|---|---|---|
| as recorded: the rig's own correction | none (`identity`) | none (`identity`) | roll +3.02°, pitch −0.88° |
| roll +3° | 0.36° / 0 | 0.19° / 0 | 0.04° / 0 |
| pitch −4° | 0.26° / 0 | 0.34° / 0 | 0.07° / 0.21° |
| roll −2°, pitch 3°, yaw 2° | 0.32° / 2.09° (by design) | 0.49° / 2.09° | 0.04° / 2.26° |
| upside down | 0.00° — orientation found | 0.00° — found | 0.03° — found |
| forward = `+x` (the ROS convention) | 0.00° — found | 0.00° — found | 0.03° — found |
| mounted backwards | 0.00° — found | 0.00° — found | 0.03° — found |
| on its side (spin axis horizontal) | **not supported** (83°; 80° before v0.6.3) | **not supported** (89°; 90°) | **not supported** (84°) |

Reading. (1) Every upright or inverted mount is found from the data on all three recordings and the
tilt is recovered to 0.0–0.5° (median 0.2°: < 1 cm at the edge of the 1.05 m envelope). (2) The
`doubleT_obstacle` rig is rolled by 3.0° (its right rail head is 8 cm above the left over 4–30 m of
straight, stationary track) — corrected after half a second by the provisional stage and confirmed
by the final one; the two moving rigs are level within 0.5°. (3) The first version searched all 24
axis-aligned orientations: on `roundT_squareT_pressureGate_squareT` the upside-down, `+x`-forward
and backwards mounts adopted "left = ±z" (83° off, status `ok`) — the flat side wall of the square
tunnel with two cable trays on it passed for the bed with a rail pair and scored higher than the
real track. A spinning LiDAR is mounted with its spin axis vertical, so the default search is now
the 8 orientations that keep it vertical (`calibration.keep_up_axis`, `tests/test_calibration.py`).
(4) The same wall is why a sensor that really is mounted on its side cannot be recognised from the
geometry (the configured mapping "passes" on the wall and the detector then alarms): such a mount
must be set with `sensor.forward/left/up` (launch arguments `sensor_forward` / `sensor_left` /
`sensor_up`); [`ALGORITHM.md`](ALGORITHM.md) §6. (We tried the ring structure as a physical cue for
the spin axis and dropped it: a real sensor always spins about its own z, so its rings say nothing
about how it is mounted.)

**Why the tilt needs 20 s on a moving train** (`scripts/mount_survey.py --npy new_data`: the
calibrator's roll measurement on every 5th frame of the 20-minute ride with the correction
off). The per-frame roll has a median of **−0.09°** and a 10–90 % range of −1.0…+0.7° — on
straight track (|k| < 2·10⁻⁴: −0.9…+0.6°) as in curves (−1.1…+0.8°): cant transitions, the
body's lean and the rail geometry itself. Neighbouring frames see the same stretch of rail, so
the error of a median depends on the time it spans more than on the count:

| window a fresh calibration freezes | median error | p90 | max |
|---|---|---|---|
| 5 consecutive frames (v0.6) | 0.37° | 1.01° | 2.20° |
| 20 observations every 10 frames (20 s, **v0.6.1 default**) | 0.24° | 0.53° | 1.02° |
| 20 observations every 20 frames (40 s) | 0.19° | 0.42° | 0.84° |

With v0.6 the eight parallel pieces of the ride evaluation froze eight different "mount
rolls" (−0.97…+1.63°) for one sensor, and the drift monitor (an EMA of single checks against
1°) then flagged 5 482 of the 11 271 frames — `CAUTION` on half of the ride for nothing. v0.6.1:
a provisional correction after 5 frames only above 2.5° (a clearly tilted rig such as
`doubleT_obstacle`), the final one from the 20-s window above 0.5° (0.75° since v0.6.3, §0), and
the drift monitor on the
median of the last 10 checks (50 s) against 1.5° (ALGORITHM §2b). The v0.6 table (25 frames,
5-frame median) had tilt residuals of 0.0–0.8°.

## 7. Recognition methods tried, side by side

The task statement allows any approach; these are the ones we built and measured (numbers from
the sections named; "real" = the organizers' frames, "set F" = objects ray-cast into the moving
ride, 30 sequences × 110 frames, straight track, no speed unless said).

| # | method | what it is | measured | verdict |
|---|---|---|---|---|
| 1 | rectangle corridor + DBSCAN (v0.0) | fixed box ahead of the sensor, raw clustering | 149 alarm frames of 231 sampled empty frames; DBSCAN up to 1.4 s on dense near points (§1) | replaced by 2 |
| 2 | **normal-tunnel geometry** (v0.3 → v0.5) | per-frame bed and rail fit, axis from the rails, curvature from the walls, gauge polygon, range-scaled voxel DBSCAN, infrastructure signatures, persistence in time | empty bags 1 001 → 96 alarm frames at 10 Hz; the real person 66/71 (§1, §1b) | **the core** |
| 3 | multi-frame accumulation with a LiDAR-only speed estimate (v0.4) | merge 5 frames beyond 40 m, motion-compensated by a speed estimated from the tunnel texture | synthetic tunnel: person 189 vs 178 m; real empty bags 119 / 30 vs 88 / 27 (more false alarms), no change on the real person (§1b, §2b); 24.09: estimate accurate (median error 0.06–0.08 m/s), but even a perfect speed buys nothing on set O (§9) | estimator off; accumulation kept for a given speed |
| 4 | **accumulation with the ride's train speed given**, on a moving real background (v0.6) | 5 frames merged beyond 40 m, motion-compensated with the given speed | set F: person 150 → **177 m** median, trolley 146 → 190 m (max 205 m), crate 111 → 183 m, 0.5 m box 2 → 4 of 6; the whole ride 289 / 82 → **274 / 75** false alarm frames / events (§2d) | on whenever the node gets a speed (odometry / speed topic / parameter); the organizers' trains may have none |
| 5 | bed-anomaly low-object stage (v0.6a) | every bump > 7 cm above a learned bed cross-section inside the envelope | ride 1 482 events / 20 min (inductors, drain covers, cable crossings) (§1d) | rejected |
| 6 | rail-level low-object stage (v0.6f) | a low cluster whose top reaches the rail head | object on the rail 170 / 185 frames; ride 734 events (guard rails, joints, fastenings) (§1d) | option for a line known to be clean |
| 7 | **per-point rail-head rule + 0.5 s** (v0.6, shipped) | every low candidate ≥ 3 cm above the rail head, 5 hits | ride 18 low events; 10 cm box on a rail head 10–25 m (synthetic tunnel); real object 2 / 185 by its own detection (§1d) | shipped in v0.6–v0.6.1 |
| 7b | **straddle clustering** (v0.6.2, shipped) | bed anomalies and the corridor points just above the envelope floor clustered together; top ≥ 0.10 m above the rail head, ≥ 0.35 m across, ≤ 0.8 m along the track | real object 2 → **121 / 185**, 118 of the 126 frames after the person leaves; +1 event on the five bags and on the ride; 30 cm objects on a rail head 6 / 6 from 42–44 m (set F round 2); without the shape rule +49 ride events (§0, §2d) | shipped; the thresholds sit close to the one real object (top 0.11–0.16 m, 0.38–0.50 m across) |
| 7c | **confirmation 0.5 s; no far alarm without rails** (v0.6.2, shipped) | 5 frames instead of 3; clusters beyond 40 m advisory in frames without the rail pair | false events: five bags 31 → 20, ride 83 → 47; the real person unchanged; a person 3 m later on straight track, 10 m later with a speed (§0, §2d) | shipped |
| 7d | central near-bed path (24.09, opt-in, off) | bed anomalies within ±0.55 m of the axis and 30 m, below the rail head, above the local bed | first gates: five bags 20 → 145 events, ride 47 → 667, the 30 × 30 × 10 cm box on the bed 0 of 6, set O background 3 → 466 alarm frames [team record, partly unverified]; current gates (`537e220` + `7df1796`): five bags 20 → 107 events, set O background 319 alarm frames, the box found in the synthetic-tunnel test (§1e) | off; the ride not re-run |
| 7e | short signatures (24.09 experiment; 25.09 flag `cluster.short_signature_max_length`, off) | `elevated` / `floating` do not demote a cluster at most 3 m long along the track within 100 m | set O: STOP frames on the inside objects 303 → 352, the 0.3 m floating cube from 52.5 m instead of 34 m; five bags 107 / 20 / 27 → 113 / 22 / 29; gate FAIL on 5 rows; on the ride, on top of the long rule, STOP episodes 39 → 45 (§1f, §2e) | tried, not shipped (25.09: ride STOP episodes +6 against a limit of +5) |
| 7f | far-rail check (24.09, opt-in, off) | a wall-derived far curvature contradicted by rails visible beyond the near fit is replaced | 25.09: never fires on the six recordings and set O, output identical on all 3 998 frames (§1f) | off: nothing to gain on this data |
| 7g | **long overhead rule** (25.09 flag `cluster.floating_long_min_length`, 3.0 m) | the `floating` shape also demotes a cluster near the axis longer than 3 m along the track (a duct, tray or beam), since the review of 25.09 only with its bottom above 1.6 m (`cluster.floating_long_min_bottom`; a tray fallen onto the axis lower down is a STOP) | the platform recording 101 / 15 / 25 → 54 / 9 / 15, five bags → 60 / 14 / 17, ride 204 / 47 / 39 → 197 / 46 / 39; every other recording, set O and set F straight identical; gate PASS (§1f); the 1.6 m bottom condition changes none of it (2.0 / 1.8 m would bring back a ride event) | shipped 25.09 (`935eecf`; bottom condition `0bb1ba3`) |
| 8 | **far-field rule** (v0.6, shipped) | beyond the height reference, tall (≥ 0.6 m), short (≤ 3 m), grounded clusters alarm to the trusted axis range | set F, rule off → on: person first confirmed 106 → **150 m** median, trolley 105 → 146 m, crate 106 → 111 m; off-object detections 12 → 39 of 3 060 frames (§2d) | shipped |
| 9 | learned second opinion (v0.6 experiment) | gradient-boosted trees on the descriptors of the geometric candidates (positives: set-F objects; negatives: every candidate on empty data) | held-out ride part + unseen sequences: AUC 0.976–0.990; 83–95 % of false candidates removed at 97 % object recall; intensity is an injector artefact (§8) | not shipped: no real positives; ready as a re-weighting |
| 10 | considered, not built | a trained 3D detector (PointPillars / CenterPoint: no real positives, ~0–3 % AP beyond 100 m in the rail literature), change detection against a map (needs localisation and repeated rides; "a map of the given tunnels will not fully work" — Q&A), a range-image anomaly model (fires on cables, signs, wet patches; needs the same gauge and persistence) | [`RESEARCH.md`](RESEARCH.md) §0 | — |

**Tried, not shipped: CPU savings with identical output (25.09).** Measured against the shipped
native path with the same interleaved A/B as §3 [timing: sandbox, 25.09; raw not committed]:

- **forward crop at X ≥ 2.9 m inside the detector** (the minimum of the stages' lower X bounds;
  the calibrator and the health monitor keep the whole cloud): identical on all 3 998 frames on
  both paths, but 41 % of the points are cropped at 360° and only 11 % at 120°, and on the native
  path the gather costs what the cheaper passes save (+0.05…+0.65 ms with `np.take`, +1.0…+2.4 ms
  with fancy indexing); −8 ms at 360° on the numpy path only. Kept on the side branch
  `wf2/late-changes-crop-dropped` (`3f0de67`), worth reviving only if numpy became the shipped
  path;
- **reusing the track stage's bed height in `corridor_coordinates`**: bit-identical, but slower on
  the native path (0.98 → 1.74 ms at 360°, 0.56 → 1.21 ms at 120°), because the kernel
  `rs_corridor_coordinates` already does it in one pass; faster only on numpy (4.21 → 3.18 ms).
  Not implemented.

## 8. A learned second opinion on the geometric candidates (experiment, not shipped)

Question: can a small classifier on cluster descriptors remove the geometric pipeline's false
candidates without losing objects? `scripts/ml_dataset.py` records every single-frame
candidate the pipeline places in the envelope (or demotes by a signature): **negatives** = all
of them on the five empty bags and on every second split file of the ride (5 042 rows — every
one is infrastructure or noise), **positives** = the candidates that match an object ray-cast
into consecutive ride frames (set-F injection, 12 files × 5 kinds, 2 049 rows). 14 descriptors
(distance, lateral, box size, voxel / raw point counts, visibility ratio, height span,
intensity, low-object flag, demoted flag, share of points inside the envelope).
`scripts/ml_second_opinion.py` trains gradient-boosted trees (scikit-learn
`HistGradientBoostingClassifier`, 300 iterations, class-balanced) on the five bags + the first
60 % of the ride and the first half of the object sequences, and tests on **the last 40 % of
the ride and the other half of the sequences** (never seen).

| descriptors | AUC (test) | false candidates removed at 99 / 97 / 95 % object recall | objects kept beyond 150 m (at 97 %) |
|---|---|---|---|
| all 14 | 0.990 | 74 / **95** / 98 % | 82 % |
| without intensity | 0.988 | 81 / **91** / 95 % | 84 % |
| without intensity and the point counts (n_vox, n_raw, visibility) | 0.976 | 67 / **83** / 89 % | 81 % |

**Leakage check.** Permutation importance puts *intensity* first by a factor of eight (AUC drop
0.136) — but the intensity of an injected object is drawn from the injector's reflectivity
catalogue, and its point budget from the injector's dropout model: the classifier can learn
"injected vs real" from them. Without them the trees still separate the two on shape and
place alone (width, length, the demoted flag, the envelope share, the lateral offset: AUC
0.976, 83 % of the false candidates removed at 97 % recall), which is the honest number.

**Why it is not shipped.** Every positive is synthetic (our five object models); a real object
of another shape (a bag, a fallen panel, a tool box) is outside what the trees have seen, and
the negatives come from the same seven recordings the geometry was tuned on. As a veto it
would trade an explainable rule set for a learned boundary with no real positives behind it
— the opposite of what a safety function needs. The use we see: a confidence re-weighting of
tracks (never a veto inside 60 m) once the organizers' real obstacles exist to train and test
on; the dataset and training scripts are ready for that.

## 9. Train speed: the LiDAR-only estimate measured, and what a speed adds (24.09)

**Organizers' fact, team decision.** The recordings carry no odometry, and some trains will have
none ([Q&A](organizers/QA_session.md) fact 6, 22.09). The team therefore ships the no-speed path
and keeps a given speed optional ([`CAPTAIN.md`](CAPTAIN.md) decision log, 22.09). ReSense has
estimated a speed itself since v0.4 (`resense/egomotion.py`: the wall texture sliding past, and
persistent tracks), switched off since v0.5 (`accumulation.estimate_speed: false`, §1b
"Accumulation default"). A speed does two things in the detector: it enables the 5-frame
accumulation beyond 40 m, and the tracker predicts a new track's first step with it. Everything
below was measured on 24.09 on every frame of the seven cached recordings, detector `537e220`
unchanged, on the shared 4-core sandbox (raw summaries:
[`experiments_2026-09-24_train_speed.json`](evidence/results/experiments_2026-09-24_train_speed.json)).

**The reference** (`scripts/speed_reference.py`). No recording has odometry, so the train's
displacement per frame is measured by registering consecutive frames: a 1-D scan of the
along-track shift over the points whose normals face along the track (sleepers, brackets,
cabinets, niche edges, gates, platform ends; the lining constrains nothing along a straight
tunnel), refined by 6-DOF point-to-plane ICP. It is valid on 89–100 % of the frames, its
frame-to-frame noise is 0.01–0.03 m/s, scan and ICP agree within 1–4 mm, and on the standing
`doubleT_obstacle` it reads 0.00 m/s (−0.1 m in 20 s). In `cloud_with_fake_obj` each of the
organizers' ten objects approaches by the reference displacement within 0.00–0.04 m per frame:
their tool places obstacles fixed in the tunnel, and the train drives forward ~2.0 km at
1.4–20 m/s ([`DATASET.md`](DATASET.md) "Synthetic-obstacle recording", corrected on 24.09).

**Stamps.** The cache's bag receive stamps jitter (sd 6–11 ms), while the displacement per frame
varies by 0.2–0.3 % and is uncorrelated with them: the sensor frames are evenly spaced at 10 Hz,
as the node's header clock is. The runs below give the detector the stamps snapped to the rotation
(`scripts/eval_real.py --nominal-stamps`). With the raw receive stamps the estimator's error is
3–5 times larger (median 0.15–0.38 m/s, p90 0.4–1.3 m/s: the jitter enters through its
smoothing), so offline runs that depend on the frame interval should use `--nominal-stamps`.

**The estimator against the reference** (`scripts/speed_accuracy.py`, nominal stamps)
[real: seven recordings, 24.09]:

| recording | train speed min / median / max (m/s) | distance (m) | estimate on moving frames | error median / p90 (m/s) | off by > 1 m/s | standing frames with an estimate ≥ 1 m/s |
|---|---|---|---|---|---|---|
| `doubleT_obstacle` (standing) | 0 / 0 / 0 | 0 | — (none on 200 standing frames) | — | — | 0 of 200 |
| `doubleT_platform` | 0 / 5.3 / 14.9 | 213 | 96 % | 0.08 / 0.20 | 0 % | 0 of 81 |
| `roundT_doubleT` | 15.1 / 16.8 / 19.3 | 426 | 58 % | 0.07 / 0.19 | 0 % | — |
| `roundT_pressureGate_roundT` | 14.6 / 15.0 / 15.3 | 400 | 61 % | 0.06 / 0.18 | 0.6 % | — |
| `roundT_squareT_pressureGate_squareT` | 8.3 / 13.4 / 15.0 | 689 | 58 % | 0.07 / 0.18 | 0 % | — |
| `squareT_platform_squareT_switch` | 0 / 1.9 / 14.3 | 400 | 72 % | 0.06 / 0.18 | 1.7 % | 5 of 360 |
| `cloud_with_fake_obj` | 0 / 15.1 / 20.3 | 2 024 | 55 % | 0.07 / 0.17 | 0 % | — |

No confident estimate was off by more than 3 m/s. The texture cue is accurate: 1 982 estimates, 2
off by more than 1 m/s. The tracks cue is the weak part: 52 estimates, 7 off by more than 1 m/s; on
5 frames it reported 1.2–2.2 m/s while the train stood at a platform (jittering tracks of platform
structures). The estimator costs **+6.6–6.8 ms per frame** (median of per-frame differences, three
detectors interleaved on the same 145 frames × 3, one pinned core, load 6.5–8;
`scripts/speed_timing.py`); a given speed costs +1.1–1.3 ms (the accumulation).

**What a speed changes: false alarms** (`scripts/eval_real.py --nominal-stamps`; "reference" is the
ICP speed handed to the detector as odometry would be, `--speed-ref`: the ceiling for any
estimator). Alarm frames / events [real: six recordings, 24.09]:

| recording | no speed (shipped) | estimator | reference | reference, merge ≥ 100 m | estimator, merge ≥ 100 m, tracks cue ≥ 5 m/s |
|---|---|---|---|---|---|
| `doubleT_platform` | 4 / 4 | 9 / 2 | 9 / 2 | 9 / 3 | 9 / 3 |
| `roundT_doubleT` | 2 / 1 | 8 / 2 | 5 / 1 | 0 / 0 | 2 / 1 |
| `roundT_pressureGate_roundT` | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| `roundT_squareT_pressureGate_squareT` | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| `squareT_platform_squareT_switch` | 97 / 13 | 97 / 13 | 97 / 13 | 97 / 13 | 97 / 13 |
| **five obstacle-free recordings** | **103 / 18** | 114 / 17 | 111 / 16 | 106 / 16 | 108 / 17 |
| `doubleT_obstacle` (person, standing train) | recall 0.752, first alarm frame 11 | identical | identical | identical | identical |

The no-speed column differs from the headline 107 / 20 only by the stamps: with the receive stamps
of the usual offline runs it is 107 / 20 without and 122 / 21 with the estimator. The added alarms
are accumulation effects that a perfect speed has too: a column in a curve at 44–50 m
(`roundT_doubleT`) whose merged cluster is 2.4 m long and so no longer passes the `column`
signature, and a 2 m flat structure at the gauge edge at 99–107 m (`doubleT_platform`). All 13
squareT events happen while the train stands or creeps below 1 m/s at the platform-end structures
(82.9, 104.3 and 147.5 m); no speed can fix those.

**What a speed changes: the organizers' obstacles** in the moving ride (`cloud_with_fake_obj`,
`scripts/score_fake_objects.py`; first STOP / STOP held from; "seen" = first advisory or STOP)
[organizers' synthetic: set O, 24.09]:

| object (intent) | no speed | estimator | reference | reference, merge ≥ 100 m |
|---|---|---|---|---|
| 2 × 2 m centre (in) | 98.0 / 98.7 m | same | same | same |
| 0.3 m floating, centre (in) | 34.0 / 37.4 m, seen 50.8 m | same | **30.6 / 32.3 m**, seen 57.5 m | same as no speed |
| 0.3 m on the rail (in) | 42.7 / 46.2 m, seen 42.7 m | same | 42.7 / 46.2 m, seen 58.6 m | same as no speed |
| 0.3 m at the edge (in) | advisory only, seen 47.9 m | seen 51.6 m | seen 57.1 m | seen 47.9 m |
| 2 × 2 m top of the envelope (in) | 99.3 m, 11 STOP frames | same | same | same |
| 2 × 0.2 m across the rails (in) | 82.2 / 58.6 m | same | 82.2 / 55.3 m | same as no speed |
| 2 × 2 m outside (out) | 6 false STOP frames | 6 | **17** | 9 |
| 0.3 m just outside (out) | 0 false STOP frames | 0 | 0 | 0 |
| background alarm frames | 0 | 1 | 0 | 0 |

Merged frames make the 0.3 m cubes visible 7–16 m earlier, but as advisories (the `floating`
signature, [`P4_AUDIT.md`](P4_AUDIT.md)), and the longer advisory history then delays the STOP; the
outside box's inner face, 0.1 m from the edge, crosses into the envelope in more merged frames. No
object gets its first STOP earlier; a perfect speed costs one 0.3 m cube 3.4 m and adds 11 false
STOP frames. With the receive stamps the estimator run had the same first STOP and held-from
distance as the defaults on every object.

**Long range with a speed** (set F on the original moving recordings, `scripts/speed_setf.py`: a
synthetic person / 1 m crate fixed in the tunnel 200 m ahead, moved with the reference, 14
approaches on straight and curved track at 10–18 m/s, legacy placement; frame recall per range)
[synthetic: set F, 14 approaches on four moving recordings, 24.09]:

| object | variant | first confirmed, median | 0–50 / 50–100 / 100–150 / 150–200 m | detections away from the object |
|---|---|---|---|---|
| person | no speed | 86 m | 95 / 66 / 33 / 4 % | 26 |
| person | estimator | 86 m | 94 / 62 / 34 / 10 % | 23 |
| person | reference | 90 m | 94 / 61 / 36 / 11 % | 19 |
| crate 1 m | no speed | 74 m | 92 / 50 / 9 / 1 % | 26 |
| crate 1 m | estimator | 75 m | 92 / 51 / 24 / 3 % | 32 |
| crate 1 m | reference | 69 m | 91 / 47 / 25 / 3 % | 29 |

The far-field frame recall rises (person at 150–200 m 4 → 10–11 %, crate at 100–150 m
9 → 24–25 %), the 50–100 m recall falls by up to 5 points, and the first confirmation hardly moves:
on these curved, short recordings the sightline, not the point count, limits it (on the straight
ride of set F, §2d, a given speed moved a person's first confirmation 148 → 167 m). The estimator
delivers nearly all of what the reference speed does.

**Other uses of a speed, checked.**

1. *Static-world rule* (an obstacle must approach at the train's speed;
   `scripts/speed_static_check.py`, offline): of the 18 false-alarm events of the five recordings,
   14 approach exactly like the tunnel (12 of them while the train stands or creeps below 1 m/s),
   so at most 4 events (9 frames) could go, and a person running along the track would be rejected
   too. On the organizers' ride the only non-static alarm is the 2 × 2 m box's own near-range
   artefact at 3 m, a correct STOP. Not implemented.
2. *Holding the last estimate* for 5 frames when the estimator is unsure: coverage 55 → 76 % on the
   organizers' ride, but the held standstill errors of the tracks cue merge frames at a platform
   (squareT 97 / 13 → 105 / 16, five recordings 121 / 20); reverted.
3. *Merging only beyond 100 m*, with the tracks cue silenced below 5 m/s: 108 / 17 and the
   organizers' objects unchanged, the closest to neutral, and no gain either.
4. *Time to reach / braking*: the organizers put braking decisions outside the task (Q&A 22.09,
   30:32); at a standstill the estimator reports "unknown", not 0. Not pursued.

**Decision (unchanged, now measured).** The shipped path stays the no-speed one and
`accumulation.estimate_speed` stays `false`. The estimator is accurate, but neither it nor a
perfect speed pays on the organizers' own check (+3 to +11 false-alarm frames on the empty
recordings, no earlier first STOP, +11 false STOP frames on the outside box); its only clear gain
is far-field frame recall, which that check does not reward. It stays an opt-in with a known cost
of +6.6–6.8 ms per frame. A speed from the node's `ego_speed_mps` / `speed_topic` / `odom_topic`
is still honoured: if the stand provides one, the effect is the far-field gain for a few false-alarm
frames. The next step, if anyone continues, is the `floating` signature that demotes the merged
0.3 m cubes, not the estimator.
