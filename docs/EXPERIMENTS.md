# Experiments

> **Purpose:** every measured result of ReSense with its data, date and raw summary: false alarms,
> range, latency, FPS, hard cases and how the quality changed (spec §5 "Эксперименты").
> **Audience:** jury, team · **Owner:** P3, P4 (content), P1 (structure, timing) · **Language:** EN,
> summary RU
> **Last verified:** 2026-09-25 against `154db25` (detector v0.6.3 with the long overhead rule,
> `tracking.column_hold` and the rail-shadow rules on since 25.09, node v0.6.4, package 1.0.0;
> re-measured by the regression gate with the ride) ·
> **Status:** current

**Кратко.** Здесь все измерения ReSense с датой и видом данных. На всех 13 759 реальных кадрах
организаторов пять бэгов без препятствий дают 13 ложных событий (20 до правила длинных навесных
конструкций и удержания колонн, 25.09), 20-минутная поездка — 46 (3,5 на км); человек на пути найден в 58 из 61 кадра
с 11-го, предмет на рельсе — в 124 из 126 кадров после ухода человека, ошибка расстояния ≤ 0,23 м.
На синтетических объектах самих организаторов (набор O) STOP получают 5 из 8 объектов в габарите:
ящик 2 × 2 м с 98 м (с 25.09 и вблизи — на своём расстоянии, а не 3,0 м), кубы 0,3 м только с
34–43 м. Человек на 148–154 м — только на нашей синтетике
(151 м по текущему скрипту оценки, 25.09). Время кадра 42–64 мс (p95 53–78 мс) на одном ядре
машины разработки без монитора состояния; ядра на C++ (24.09) сокращают его на 38–57 %, DBSCAN на
cKDTree (25.09) — ещё на 1–3 мс, выход тот же; стенд i7-9700E до сдачи команде недоступен
(организаторы, 25.09), замер — на 8-ядерной машине команды. Все числа по реальным записям, набору O,
поездке и набору F на прямой перепроверяются одной командой (`scripts/regression_gate.py`, эталон
25.09 с поездкой). Собственная оценка скорости поезда по лидару точна (ошибка 0,06–0,08 м/с), но
даже точная скорость не улучшает проверку организаторов (§9), поэтому по умолчанию она выключена.

## Current results (detector v0.6.3 with the long overhead rule, `tracking.column_hold`, the rail-shadow rules and the P3 round-2 items on since 25.09, the P3 items of 26.09 since 26.09, node v0.6.4)

The shipped configuration, no train speed given unless said. Kinds: **real** = the organizers'
recordings as recorded; **synthetic** = our objects ray-cast into real frames (set F: into the
moving ride); **organizers' synthetic** = objects added by the organizers' own tool (set O). Sets
and terms: [`README.md`](README.md) §3 (glossary), [`EVALUATION.md`](EVALUATION.md) §1.

**Re-run in one command.** `scripts/regression_gate.py` (EVALUATION §3 step 6) re-measures the
real-data rows (five obstacle-free bags, the person, the object on the rail, the ride), the set O
row and set F straight track in one run, and gates every detector change against
[`regression_baseline_2026-09-26_ride_p3c.json`](evidence/results/regression_baseline_2026-09-26_ride_p3c.json)
(the shipped defaults of `ed03bc2`: the P3 items of 26.09 merged with the fixes of their safety
review, `lowobj.rail_start_within`, `tracking.near_escalate_*` and `cluster.wall_keep_*` on,
`gauge.axis_union` off: six recordings, set O, the ride and set F straight; 26.09, §1n). It is the
single check of these results: a change that moves them commits a new baseline, one that does
not leaves this table as it is. The five before it,
[`regression_baseline_2026-09-25_ride_p3b.json`](evidence/results/regression_baseline_2026-09-25_ride_p3b.json)
(`30d0cac`, the P3 round-2 items, re-cut on `0c8f8e1` after their safety review, §1i),
[`regression_baseline_2026-09-25_ride_p3.json`](evidence/results/regression_baseline_2026-09-25_ride_p3.json)
(`c598cf6` re-cut on `154db25`, the rail-shadow rules, §1h),
[`regression_baseline_2026-09-25_ride_column.json`](evidence/results/regression_baseline_2026-09-25_ride_column.json)
(`d117c8c`, `tracking.column_hold` 2),
[`regression_baseline_2026-09-25_ride.json`](evidence/results/regression_baseline_2026-09-25_ride.json)
(`935eecf`, before `column_hold`) and
[`regression_baseline_2026-09-25.json`](evidence/results/regression_baseline_2026-09-25.json)
(six recordings and set O, no ride), are kept for history; the merged `8932f3a` passed against the latter with
every gated metric the same ([its JSON](evidence/results/regression_gate_2026-09-25_8932f3a.json)).

| metric | value | kind, date | where |
|---|---|---|---|
| false alarms, five obstacle-free bags (2 287 frames) | **13 events**, 58 alarm frames, 16 STOP episodes with `tracking.column_hold` 2 (on since 25.09, §3a: the `roundT_doubleT` column); without it 14 events, 60 alarm frames, 17 STOP episodes (long overhead rule on since 25.09; 20 / 107 / 27 without it); the start-offset spread 14–20 events was measured without the rule (24.09), not re-run | real, 25.09 [measured 25.09] | §1f |
| P4 rate / mount stress and empty suffix | five bags false events / STOP episodes: 5 Hz **10 / 10**, +3° roll **14 / 16**, +3° pitch **17 / 18** since the safety review of 26.09 turned the refinement off (with it, round 2 of 25.09: 10 / 10, 11 / 13, 16 / 17; P4's run of 25.09 before the rate / re-mount flags: 13 / 17 with 3 new events in `roundT_doubleT`, 16 / 17, 17 / 18); `roundT_doubleT` 0 / 2 / 1 events (0 / 1 / 0 with the refinement); `doubleT_obstacle` labelled hits 92 of 123 @ frame 12, 183 of 246 @ 12, 186 of 246 @ 11 (26.09; 181 of 246 at +3° roll before). Frames 804–1 509 of `cloud_with_fake_obj`: **0 false frames / 0 events in 706 frames**, both from a fresh start and after continuous playback (P4, before round 2) | real backgrounds, 25.09, 26.09 [measured] | §1g, §1i; [`scorecard13_2026-09-25.json`](evidence/results/scorecard13_2026-09-25.json), [`p3_round2_combined_2026-09-25.json`](evidence/results/p3_round2_combined_2026-09-25.json), [`p3_round2_review_fixes_2026-09-26.json`](evidence/results/p3_round2_review_fixes_2026-09-26.json) |
| false alarms, 20-minute ride (11 271 frames, 13.0 km) | **45 events, 3.5 per km**, 183 alarm frames (1.6 %), 38 STOP episodes with `lowobj.rail_start_within` 4 m (on since 26.09, §1k: the fresh start's STOP on the rail heads at 2.9–3.1 m removed; the gate's nearest ride alarm 2.9 → 20.7 m); 46 / 187 / 39 before it, with `tracking.column_hold` 2 (on since 25.09, §3a); without that 46 / 197 / 39 (without the long overhead rule 47 / 204 / 39, equal to the 24.09 record); 15 of the 45 first confirmed beyond 100 m (the event removed on 25.09, an overhead structure 4–5 m along the track at 105–110 m, was one of the 16 of 24.09); causes: the 24.09 classification of the 47 (corridor-edge structures 18, bed-level fixtures 11, far small clusters 7, other 6, tall 2, hanging 2, person-like 1), not redone | real, 25.09, 26.09 [measured 26.09] | §1f, §1k, §1n |
| crossing person, `doubleT_obstacle` | STOP in **58 of 61** frames inside the envelope, first alarm frame 11 (0.3 s after entering), 55.5–56.6 m, distance error ≤ 0.23 m | real, 24.09 | §0 |
| object lying across the rail (0.45 × 0.6 × 0.3 m, 56 m) | **125 of the 126** frames after the person leaves it (from frame 75)¹, 2 STOP episodes in the recording, since `calibration.keep_within_deg` (25.09, round 2: the final mount calibration no longer re-seeds the track model at frame 190, frame 191 kept); 124 of 126 and 3 STOP episodes before | real, 24.09; gate 25.09 | §0, §1i |
| verified-clear distance (`clear_distance`, `health.clear_cap` on since 25.09, round 2) | capped at the nearest unconfirmed or advisory cluster in the envelope: set O object-frames with a `clear_distance` past an in-envelope object **147 → 67** of 505 on the round-2 code (172 → 82 on the item's branch), **60** since the review fixes of 26.09 (also capped at a lost reported track); median clear distance five bags 127.0 → 120.0 m (**−5.5 %**, the pre-registered limit was −5 %: failed, shipped by the captain's delegate; unchanged by the review fixes), ride 127.0 → 123.0 m (−3.1 %, 1.50 % of the frames pushed under 60 m), 122.6 m since 26.09 (53 more frames under 60 m); no decision changes | real and organizers' synthetic, 25.09, 26.09 | §1i |
| health, `CAUTION` | non-latency health warnings on 196 of 13 759 frames (1.4 %: rails lost at stations and switches); `CAUTION` on 27–68 % of the frames of the empty bags, 41 % of the ride | real, 24.09 | "Re-measurement" |
| current code against v0.6.3 | identical per-frame output on all 13 759 frames | real, 24.09 | "Re-measurement" |
| regression gate with the ride and set F straight (native, 25.09) | current baseline [`regression_baseline_2026-09-26_ride_p3c.json`](evidence/results/regression_baseline_2026-09-26_ride_p3c.json) on `ed03bc2` (the P3 items of 26.09 merged with the fixes of their safety review; `gauge.axis_union` off, [`regression_gate_2026-09-26_p3_integrated.json`](evidence/results/regression_gate_2026-09-26_p3_integrated.json), §1n): PASS against the one before with 7 gated rows better (ride events 46 → 45 and STOP episodes 39 → 38; set O box at the envelope top 12 → 22 STOP frames, edge box 0 → 6 and none → 10.3 m, edge cube 0 → 2 and none → 5.2 m), none worse; five bags, `doubleT_obstacle` and set F straight identical. Before it: [`regression_baseline_2026-09-25_ride_p3b.json`](evidence/results/regression_baseline_2026-09-25_ride_p3b.json), re-cut on 26.09 on the review fixes (the refinement off; every gated value and every decision, detection and track model of the 15 269 frames the same, `clear_distance` shorter in 398 frames, [`p3_round2_review_fixes_2026-09-26.json`](evidence/results/p3_round2_review_fixes_2026-09-26.json), §1i); first cut on `30d0cac` (the four P3 items of round 2 merged, `health.clear_cap` and `cluster.hanging_needs_rails` on, [`p3_round2_combined_2026-09-25.json`](evidence/results/p3_round2_combined_2026-09-25.json)): PASS against the one before with 6 gated rows better (set O hanging 0.3 m cube 19 → 30 STOP frames and first STOP 34.0 → 52.5 m, 5 cm hanging object 0 → 15 and none → 30.1 m; `doubleT_obstacle` object on the rail 127 → 128 and 124 → 125 hits), none worse; five bags, the ride and set F straight identical, decisions on them identical frame by frame, §1i. Before it: [`regression_baseline_2026-09-25_ride_p3.json`](evidence/results/regression_baseline_2026-09-25_ride_p3.json) on `c598cf6` (the four P3 items of 25.09 merged, the rail-shadow rules on, [`p3_combined_2026-09-25.json`](evidence/results/p3_combined_2026-09-25.json)): PASS against the one before with 5 gated rows better (set O 2 × 2 m box 207 → 208 and plank 42 → 49 STOP frames; set F straight false detections person 7 → 6, 1 m box 13 → 10, trolley 12 → 5), none worse, every gated row equal to the rail-shadow item's own gate, §1h; re-cut after the review fixes of the rail-shadow rules ([`p3_review_fixes_2026-09-25.json`](evidence/results/p3_review_fixes_2026-09-25.json)): the same 5 rows better, the 1 m box 13 → 12 (10 in the first cut: a STOP reported 4 m short), every decision and the track model identical frame by frame, gauge distances only shorter, §1h. Before it: [`regression_baseline_2026-09-25_ride_column.json`](evidence/results/regression_baseline_2026-09-25_ride_column.json) on `d117c8c` (`tracking.column_hold` 2, pre-registered 3 / 2 / 1, [`column_hold_2026-09-25.json`](evidence/results/column_hold_2026-09-25.json)): PASS against the one before with 7 gated rows better (`roundT_doubleT` events and STOP episodes, set F false detections of every kind), none worse, §3a. Before it: [`regression_baseline_2026-09-25_ride.json`](evidence/results/regression_baseline_2026-09-25_ride.json) on `935eecf`: PASS against the shipped-defaults run of the same day (3 gated rows better: `squareT_platform_squareT_switch` events and STOP episodes, ride events); decision evidence [`rules_decision_2026-09-25.json`](evidence/results/rules_decision_2026-09-25.json); the review fix `cluster.floating_long_min_bottom` 1.6 m (`0bb1ba3`) passes against the same baseline with every number but latency identical and the same per-frame output, so the baseline stands ([`long_rule_bottom_2026-09-25.json`](evidence/results/long_rule_bottom_2026-09-25.json)) | real, organizers' synthetic and synthetic, 25.09 | §1f |
| organizers' objects (set O, `cloud_with_fake_obj`, 10 objects in 1 510 frames) | STOP for **8 of 8** in-envelope objects since the near escalation of 26.09 (§1l; 6 of 8 before): 2 × 2 m box from 98 m (first sight), plank across the rails from 82 m, 0.3 m cubes from 43–53 m (the hanging one from 52.5 m since round 2 of 25.09, 34.0 m before), 2 × 2 m box at the envelope top in 22 of 124 frames, held from 23.9 m (12, none within 50 m, before), the 5 cm hanging object from 30.1 m in 15 frames (missed before round 2), the edge 2 × 2 m box from 10.3 m in 6 frames (missed before), the edge 0.3 m cube at 5.2 m in 2 frames (advisory only before); STOP in **355 of 801** visible in-envelope object-frames (337 before 26.09, 311 with the rail-shadow rules, 303 on 24.09), 1 of 236 beyond 100 m; 6 false STOP frames on the 2 × 2 m box outside, 3 background alarm frames. Since the rail-shadow rules (25.09) every STOP on the 2 × 2 m box is at its own distance (12 STOP frames at the bed's 3.0 m before, largest error 14.1 → 0.46 m) and the plank is held from 90.8 m instead of 58.6 m | organizers' synthetic, 24.09; gate 25.09, 26.09 | §2e, §1h, §1i, §1l |
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

¹ The same scene is counted three ways: 125 of 126 frames after the person leaves (the headline;
124 before `calibration.keep_within_deg`, 25.09 round 2); 128 of the object's 185 visible frames
by its own detection (127 before); 186 of the 246 labelled obstacle-frames of the recording
(person 58 of 61 + object 128 of 185; 185 before).

**Caveats.**

* The opt-in paths `track.rails_far_check_enabled`, `lowobj.near_enabled` and
  `accumulation.estimate_speed` are `false` in both parameter files and the code defaults, and
  `track.walls_min_far_support`, `cluster.far_axis_both_sides` and `track.floor_far_min_width`
  are 0 (off; tried and not shipped, §1h); the far-rail check was measured on
  25.09 on the six recordings, set O (§1f) and the ride (§1h) and never fires, the
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
* The rail-shadow rules are on since 25.09 (`track.floor_shadow_height` 1.0 within 30 m,
  `cluster.oversize_split_max_length` 3.0 within 30 m, `cluster.gauge_distance` true; §1h): they
  change only set O (two objects' STOP frames, #1's distances) and set F straight's false
  detections (35 → 24; 26 since the review fixes, which measure a gauge distance on the envelope
  widened by the axis margin, so distances only get shorter, §1h); the six recordings, the ride
  and set F detections are identical with and without them (the gate of 25.09).
* The P3 round-2 items are on since 25.09 (§1i): `cluster.floating_free_max_size` 0.5 (the
  hanging 0.3 m cube), `cluster.hanging_enabled` with `hanging_needs_rails` (the 5 cm hanging
  object; the stage runs only on frames with the rail pair found), `health.clear_cap` (R1,
  shipped although it missed its pre-registered clutter limit) and the rate / re-mount flags
  `calibration.time_cadence`, `keep_within_deg` 0.25, `track.rates_per_period`,
  `walls_smoothing_per_period` (`refine_min_deg` 0.5 too until the safety review of 26.09 turned
  it off; since then `calibration.reseed_keep_max_deg`, `tracking.reseed_hold`,
  `health.clear_cap_lost` and `cluster.hanging_yield_gauge_only` are on, §1i). They change set O
  (two objects), `doubleT_obstacle` (one frame of the object on the rail) and `clear_distance`; the
  five bags, the ride and set F straight are identical with and without them, decisions frame by
  frame (the gates of 25.09 and 26.09). The 24.09 rows above that they do not touch are not
  re-dated.
* The P3 items of 26.09 are on since 26.09 (§1k, §1l, §1n): `lowobj.rail_start_within` 4 m (with
  `rail_start_min_ref` 0.06 m), `tracking.near_escalate_*` 10 / 35 m / 5 and
  `cluster.wall_keep_*` 10 / 20 m; `gauge.axis_union` stays 0 (tried, not shipped, §1m). They
  change the ride (one event, the fresh start at a standing train) and set O (three objects); the
  five bags, `doubleT_obstacle` and set F straight are identical (the gate of 26.09).
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
beyond the height reference would become advisory and set F cannot be run here (measured with set
F on 25.09: person 151.0 → 138.8 m, trolley 151.4 → 104.5 m, crate 123.9 → 104.0 m, §1h); the organizers do
not count switch glitches. The 82.9 m platform end needs a fix in the axis model, not a shape
rule: capping wall curvature in stations would also cut range in real R ≈ 350–1 000 m curves.

**Flipping a flag needs no code**: both are in `configs/default.yaml`, the ROS copy is synced by
`scripts/sync_params.sh`, the node reads `config_file`. The one measurement left, the ride with
`regression_gate.py --set …`, was measured 25.09 on the dev VM (the ride streamed split by split
as in [`VM_GUIDE.md`](VM_GUIDE.md) §2.3).

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

### 1g. P4 SCORECARD #13: 5 Hz, 3° re-mount, and an empty suffix (25.09)

P4 replayed all **six original bags** from full-rate caches on `7466979` with the shipped
`configs/default.yaml` (SHA-256 `b7c393594d5ae45aabca57e932e21c06c700b28458c797e06f719ef21d623f97`).
Each bag starts a fresh detector. The 5 Hz run takes every second frame while keeping the
original timestamps. The mount runs rotate the input points by +3° roll or +3° pitch *before*
automatic calibration, as in `scripts/calib_check.py`; they do not feed a known correction to
the detector. Source and per-track first/last frames are in
[`scorecard13_2026-09-25.json`](evidence/results/scorecard13_2026-09-25.json); the replay tool is
[`scripts/robustness_check.py`](../scripts/robustness_check.py).

| bag | as recorded: frames / false events / STOP episodes | 5 Hz | +3° roll | +3° pitch |
|---|---:|---:|---:|---:|
| `doubleT_platform` | 345 / 4 / 1 | 173 / 2 / 1 | 345 / 4 / 3 | 345 / 6 / 4 |
| `roundT_doubleT` | 252 / 0 / 0 | 126 / **3** / 4 | 252 / **2** / 2 | 252 / **1** / 1 |
| `roundT_pressureGate_roundT` | 268 / 0 / 0 | 134 / 0 / 0 | 268 / 0 / 0 | 268 / 0 / 0 |
| `roundT_squareT_pressureGate_squareT` | 545 / 0 / 0 | 273 / 0 / 0 | 545 / 0 / 0 | 545 / 0 / 0 |
| `squareT_platform_squareT_switch` | 877 / 9 / 15 | 439 / 8 / 12 | 877 / **10** / 12 | 877 / **10** / 13 |
| **five empty bags** | **2 287 / 13 / 16** | **1 145 / 13 / 17** | **2 287 / 16 / 17** | **2 287 / 17 / 18** |

The real-positive `doubleT_obstacle` was also replayed: labelled hits / labelled frames and
first alarm frame were 185/246, 11 as recorded; 92/123, 12 at 5 Hz; 181/246, 12 at +3° roll;
186/246, 11 at +3° pitch. The 5 Hz denominators are halved; do not compare their raw hit
counts to the 10 Hz counts. In `roundT_doubleT`, the 5 Hz extra STOPs are at original frames
106–108 (a low cluster), 186 and 190–196 (far clusters); at 10 Hz these are advisory or absent.
The final 20-observation calibration never completes on that 25 s bag at 5 Hz because its
spacing is 10 processed frames, so the stress result includes a calibration cadence problem.

**Parameter decision.** A trial raising `tracking.zone_min_fraction` from 0.6 to 0.7 reduced
some stress alarms but left one 5 Hz event in `roundT_doubleT`. More seriously, on the unrotated
real-positive bag it reduced labelled hits from 185 to 183 of 246 and delayed the first alarm
from frame 11 to 13. This breaches the regression gate's real-positive criteria, so the trial
was rejected. The shipped parameters remain frozen at the hash above. The extra 5 Hz and tilt
events are **open**, with their exact frames recorded for P3; this check does not claim #13 is
fully fixed or increase the 8.4 score.

**Empty suffix after the freeze.** The organizers' labels contain no object points in frames
804–1 509 of `cloud_with_fake_obj`. At 10 Hz with the frozen configuration, those 706 frames
(70.48 s) have **0 alarm frames, 0 false events**. A detector started at frame 804 and a detector
run continuously from frame 0 both give zero; the latter has 220 advisory frames, the former
218. This is a held-out *segment for this parameter decision*, not an independent unseen route:
the team's earlier audit inspected this recording and mentioned frame 1131. No parameters were
selected from this suffix. An observation of zero in 70 s is not a reliable per-hour false-alarm
rate or evidence that the 5 Hz / tilt cases are fixed.

Reproduce the six-bag checks with `python scripts/robustness_check.py --cache <cache> --out
<out>`; add `--every 2`, `--mount roll_3`, or `--mount pitch_3` for the other columns. Reproduce
the held-out measurement with `resense run --bag <cloud_with_fake_obj> --out <full.jsonl>
--quiet`, filter its JSONL rows to `804 <= frame <= 1509`, and run `resense summarize` on the
filtered file. The raw bags and caches stay outside Git.

### 1h. P3 items of 25.09

**The rail shadow of a large near object (set O #1; shipped 25.09).** While the organizers'
2 × 2 m box is 26 → 9 m ahead, the bed band (\|dy\| < 1 m) behind it holds only roof returns 3–4 m
above the bed. From frame 203 (box at 25.8 m) they outnumber the bed bins in front and tilt the
floor line: the rail head at 20 m is 0.8–3.5 m off (frames 208–226), the bed 3–10 m ahead enters the
envelope (a track at 3.0 m, frames 213–226) and the box falls below the wrong rail head (unmatched
in 217–224; the STOP held by the bed alone). With a correct bed a second fault shows: the box's
face touches a line at the corridor edge (dy 1.35–1.40 m, 0.16–0.38 m above the rail head, 3–26 m)
and from 20 m box + line are one cluster > 8 m (`max_extent`), dropped whole. Three rules, on since
25.09 (ALGORITHM §3.1, §3.3): `track.floor_shadow_height` 1.0 (two bed bins > 1 m above the
previous bed, starting within `floor_shadow_range` 30 m: only bed bins within 0.35 m of the previous
bed are fitted, never the object's face; the rail pair is searched in front of the face; with < 5
bed bins / 10 m of track in front the previous bed and rail model are held);
`cluster.oversize_split_max_length` 3.0 (a cluster > 8 m keeps its part inside the gauge when that
part is ≤ 3 m long and starts within `oversize_split_max_distance` 30 m); `cluster.gauge_distance`
(a gauge cluster's distance is its nearest point inside the envelope). Set O #1 over its 229
labelled frames: STOP frames whose distance is off by more than the matching tolerance 12 → 0,
largest error 14.1 → 0.46 m, STOP frames 224 → 224, matched by an alarm 216 → 224. Pre-registered
(16:07 UTC, amended 16:16 before any result). Round 1 (shadow start within 40 m, split at any range;
4 candidates) failed the six-recording subset on the same rows: `doubleT_platform` +1 event and STOP
episode (the rule fired at 37–38.5 m; the millimetre model change moved a marginal low-object
alarm), `roundT_doubleT` +1 (a 0.08 m gauge fragment of a 10–40 m far cluster, 125 m), set O #7
+1 false STOP frame (split at 154 m). Round 2 (16:32 UTC): 35 m fails (set O #8 loses frame 643:
the axis then differs by ~0.03° for the rest of the recording and #8's cluster reads 2.02 m wide,
`elevated`), **30 m passes the full gate**: 5 gated rows better (#1 207 → 208, #9 42 → 49 STOP
frames, held from 58.6 → 90.8 m; set F straight false detections person 7 → 6, 1 m box 13 → 10,
trolley 12 → 5), none worse; ride 187 / 46 / 39, five bags 58 / 13 / 16, `doubleT_obstacle` and set F
detections identical. The shadow rule fires only on set O (29 frames); per frame on
`doubleT_platform` and `roundT_doubleT` only advisory distances move (`gauge_distance`, 10 frames;
the rest compared on the gate's rows). Tests: +4 in
`tests/test_late_candidates.py` (ray-cast approach; a person in front of the box and a person next
to an edge line stay STOPs). Left: a shadow starting beyond 30 m; the axis fit is chaotic at the
~0.03° level, so any change flips marginal decisions hundreds of frames later (a noise floor of the
gate). Raw: [`p3_rail_shadow_2026-09-25.json`](evidence/results/p3_rail_shadow_2026-09-25.json),
[`regression_gate_2026-09-25_rail_shadow.json`](evidence/results/regression_gate_2026-09-25_rail_shadow.json).

**The 82.9 m platform end: a far-support rule for the wall sides, tried, not shipped** [measured
25.09]. Raw: [`p3_platform_end_2026-09-25.json`](evidence/results/p3_platform_end_2026-09-25.json)
(two pre-registrations, 16:18 and 16:32 UTC, before their runs; every gate summary). *Diagnosis*
(the defaults, per frame): at the alarm frames of `squareT_platform_squareT_switch` (train
standing, frames 310–700) the curvature is 2.5–4.0e-4 /m (not 1.6e-4, §1f) and the axis is ~0.8 m
off at 83 m: +0.47 m against a running-tunnel centre of about −0.45 m (walls at +1.6 and −2.5 m at
90–120 m, frames 400–600 accumulated); the "platform-end structure" is that tunnel's left wall /
hall end face, ~1.8 m from the true axis. The bend is the left boundary's: a platform-side
structure at +1.6 m (6–33 m) joined by the robust quadratic to one bin at 44 m and one bin of the
diverging hall end at 76 m, while its bins at 80–108 m lie off its own fit (2–4 of its 7–10 bins
beyond 30 m within 0.4 m of it; the right wall 15–23 of 17–24). The sides disagree by 2.4–3.6e-4
(< 6.7e-4), so they are averaged and the left wins on rms; the rails' tangent, computed with the
prior curvature held fixed, feeds the bend back (yaw −0.0038 before the stop, −0.0065…−0.0085
during it). The far-rail check never fires here (§1f), and a bed-trough axis has too little to
work with at 83 m: beyond 55 m only 7–26 returns per 5 m slab and frame lie at bed height within
±3 m (frames 400–600; 92 at the end face, 75–80 m). *The rule* (`track.walls_min_far_support` f, with
`walls_far_support_max_curvature` 2e-4 and, round 2, `walls_far_support_frames` N): with both sides
fitted and a rail tangent, a side keeping less than f of its bins beyond 30 m on its own fit does
not set the axis shape when the other side keeps f and is nearly straight (a real curve is never
overruled); side count and disagreement stay as fitted, as for the nearer-side rule. *Round 1*
(f 0.5 / 0.4 / 0.6, six recordings and set O): platform STOP episodes 15 → 9 / 8 / 1, but the gate
fails every time: set O `big_above` 12 → 11 STOP frames (one firing at set O frame 146 changes the
track model of the next 1 364 frames by millimetres; at frame 643 the 2 × 2 m box at the envelope
top reads `elevated`), and with 0.5 / 0.6 `doubleT_platform` 4 / 4 / 1 → 6 / 5 / 2 and 8 / 6 / 2 (a
7-frame firing at its start sends its axis elsewhere; an event at 6 m at frames 182–183). *Round 2*
(the count against such short firings): 0.6 × 10 frames passes the six recordings and set O
(platform 54 / 9 / 15 → 24 / 7 / 10 alarm frames / events / STOP episodes: the 82.9 m end 10 → 4
episodes, the 147.5 m switch parts 4 → 6; every other recording and set O identical frame by
frame), but five of its platform events fall on frames the defaults did not alarm (the same two
structures) and the full gate fails on the ride, 187 / 46 / 39 → 187 / 50 / 40: four new events,
one at 72 m on an R ≈ 770 m curve (`new_data_73`), where the station stop of `new_data_59` had
changed the axis of the whole piece; 0.6 × 20 fails on the platform itself (events 9 → 12); 0.5 ×
10 passes the six recordings and set O (platform 42 / 8 / 10) but two of its switch-part events
fall 1–8 frames off the defaults' (the pre-registered per-frame no-new-event condition).
`doubleT_obstacle`, set O and set F straight are identical in every round-2 run, and for 0.6 × 10
set F curves and station stops (anchored placement) are identical per sequence (curves: person 6
of 6 first at 67.5 m, 1 m box 79.6 m; stops: 4 of 4 at 112.2 / 102.8 m, 2 of 6 approaches skipped
for recording gaps). Not shipped: `walls_min_far_support` stays 0 (off), the default output
unchanged. The lesson: the axis filter is chaotic under any change of its state (bin, side and
residual decisions amplify millimetres), so a rule that fires anywhere moves marginal frames
elsewhere; the fix left is to break the rails–walls feedback (tangent and curvature fitted jointly
from the rail slabs and both boundaries), after the freeze.

**The far-rail check on the ride** (`track.rails_far_check_enabled: true`, the full gate, 25.09,
same raw file): **measured, no effect.** The gate passes with every gated row the same (ride 187 /
46 / 39, set F straight identical), and the per-frame output (all but timing and health) is
identical on all 11 271 ride frames, the six recordings and set O: on the ride too the check never
changes the model. Why (its exits counted once over the ride): 7 132 frames find no far rail pair
in two slabs between 30 and 82 m, 3 480 have a curvature below its threshold (\|k\|·82²/2 ≤ 0.3 m),
394 no near rail pair, 247 no wall side, 11 too few rail-head returns at 77–82 m, 7 an axis range
already short: none reaches the disagreement test. The flag stays off.

**The 147.5 m switch parts (`far_switch`): tried, not shipped** [measured 25.09]. Raw:
[`p3_far_switch_2026-09-25.json`](evidence/results/p3_far_switch_2026-09-25.json) (the
pre-registration of 17:19 UTC, two addenda written before their candidates, every stage) and the
gate of the last candidate,
[`regression_gate_2026-09-25_far_axis_both_sides_2.json`](evidence/results/regression_gate_2026-09-25_far_axis_both_sides_2.json).
With the shipped defaults the parts give 4 of the 15 STOP episodes of
`squareT_platform_squareT_switch` (frames 500–501, 580, 640–642, 692–708; 19 STOP frames with a
detection at 140–155 m). **The cause is the axis, not the height reference.** The parts stand still
in the vehicle frame (y +1.42 m) while their corridor lateral jumps −0.86…+0.98 m between frames:
both tunnel boundaries are fitted, but the left one (a hall wall, \|dy\| 1.7–2.0 m) is seen only to
72–92 m with a curvature of 3.4–5.4·10⁻⁴ /m and the right one to 128–152 m with 0.2–0.9·10⁻⁴ /m;
the two "agree" (under 6.7·10⁻⁴), the rms weighting lets the short side set the axis
(1.3–3.2·10⁻⁴ /m, 1.4–3.4 m at 147 m), and `axis_valid` (147–167 m) is the longer side's. The
parts are 0.33–0.41 m wide and 0.38, 0.67–0.69 or 0.96–0.98 m tall: 2–4 rings at 0.32 m spacing.
(a) A bed from the side-structure base is no candidate: at the switch the side band holds the wall
foot to 122–127 m and only vault returns (+3.8…+4.3 m) beyond, and on straight track (file 46)
the lowest side point rises +0.5 m at 100 m, +1.0–1.2 m at 127–132 m and +1.6–1.9 m at 150 m
against the vault's +0.49 m at 115 m and +0.79 m at 135 m (§2d). (b) Five candidates, staged
(the platform recording, set F straight, the full gate; `--jobs 1`, native, the dev VM):

| candidate | switch-part episodes; platform alarm frames / events / STOP episodes | set F straight: person / trolley / 1 m crate, median first confirmation | verdict |
|---|---|---|---|
| shipped defaults | 4; 54 / 9 / 15 | 151.0 / 151.4 / 123.9 m | |
| `cluster.far_min_height` 0.8 | 1; 42 / 6 / 12 | **143.5 / 106.9 / 107.8 m** | fails set F |
| 0.9 | 1; 42 / 6 / 12 | **143.5 / 104.5 / 104.0 m** | fails set F |
| 1.0 | 0; 31 / 5 / 11 | **138.8 / 104.5 / 104.0 m** | fails set F |
| `cluster.far_axis_both_sides` 1: beyond the height reference the corridor ends at the shorter boundary's last bin + 15 m (+ the straight bonus), every frame | 0; 31 / 5 / 11 | **147.8 / 136.6** / 123.9 m (person file 46 169.2 → 146.0 m) | fails set F; also `roundT_doubleT` 0 / 0 / 0 → 1 / 1 / 1 (a 2.2 m column at 130–141 m turned `beyond_axis` and left the `column_hold` count) |
| `cluster.far_axis_both_sides` 2: the same limit only on bent frames (no straight bonus), would-be obstacles demoted `beyond_axis`, other reasons kept | 0; 31 / 5 / 11 | 151.0 / 151.4 / 123.9 m (every hit identical; cable false detections 3 → 2) | gate PASS, 5 gated rows better; **fails the gentle-curve check** |

A far height threshold cannot separate the parts from set F's objects: a 1.7 m person at
150–170 m is measured under 0.8 m in some frames (3 rings, dropout), the 1.0 m trolley and crate
at 0.64–0.96 m. Mode 2 is the near miss. The gate against
[`regression_baseline_2026-09-25_ride_column.json`](evidence/results/regression_baseline_2026-09-25_ride_column.json):
five bags 58 / 13 / 16 → 35 / 9 / 12, the ride 187 / 46 / 39 → 147 / 42 / 33 (3.5 → 3.2 events per
km), set O and `doubleT_obstacle` identical, set F straight identical; the median verified-clear
range drops (ride 127.6 → 120.0 m, `doubleT_obstacle` 151 → 139 m) because the limit also ends the
monitored range. The extra safety condition of its addendum, set F on six gentle-curve approaches
of the ride (files 5, 16, 45, 97, 100, 137, R 2.1–3.0 km, person / trolley / crate, chosen before
the run): trolley and crate identical, but the person's median first confirmation 124.1 → 122.2 m
(file 45 134.9 → 130.5 m, file 97 139.6 → 137.7 m; 3 of 1 950 frames change) — a range loss on
real curves, so not shipped. Both modes stay in the code, off (`cluster.far_axis_both_sides` 0,
default output byte-identical); mode 2 is a trade-off for the captain (−4 ride events and −6 STOP
episodes against ~2 m of a person's first confirmation on gentle curves). The fix without that
cost is in the axis model (weigh each boundary by the range it is seen to), the same place as the
82.9 m platform end (§1f). Tests (`tests/test_late_candidates.py`, the ray-cast tunnel with a bent
hall wall seen to 76 m): a 1.7 m face at 125 m on the extrapolated corridor is a STOP with the flag
off and advisory `beyond_axis` in either mode; mode 2 keeps a column a `column`; a person at 50 m in
the same scene STOPs on the same frame and a person at 140 m in the straight tunnel still STOPs.

**An obstacle far ahead extends the bed fit (`bed_bin`; ALGORITHM §6): tried, not shipped**
[synthetic (set F) and real, measured 25.09]. Pre-registered at 17:50 UTC before any candidate run;
candidates, rule, runs:
[`p3_bed_bin_2026-09-25.json`](evidence/results/p3_bed_bin_2026-09-25.json). *Diagnosis* on the
shipped code: of set F straight's 35 false detections only 6 are this mechanism (file 98, the
1 m crate at 100–110 m: its bin extends the fit from 82.5–92.5 to 102.5–107.5 m, the curvature
doubles, −8.3e-5 against −3.5e-5 /m, and edge fixtures at 150–160 m confirm); 18 are the object
reported 3–8 m short, 3 are fixtures at 132–136 m that the same frames confirm with no object, 8
are detections at 90–96 m (lateral −1.3 m) after the 3.4 s recording hole of file 168. *Rule*
(`track.floor_far_min_width`, 0 = off, output identical; `track._narrow_far_bins`): a bed bin at
or beyond `floor_far_from` (90 m) is dropped when its low points (≤ 0.2 m above its level) span
less than 1.1 m laterally and ≥ `floor_far_min_standing` points stand on them (0.3–1.5 m above,
over the same lateral span: an object's face). The width rule alone, as ALGORITHM §6 proposed it,
drops the real far bed: on the set F backgrounds (3 060 frames) 501 of the 712 accepted bins at
90–125 m are narrower than 1.1 m, 452 of them with nothing on them (4–10 low points near the axis
or on one rail); of the 139 bins the objects fill beyond 90 m, 127 are narrower (median 0.74 m)
and 114 carry ≥ 2 standing points. Set F straight with the gate's parameters, and
`regression_gate.py` on the six recordings and set O against
`regression_baseline_2026-09-25_ride_column.json` (`--jobs 1`, native path):

| 1.1 m from 90 m | set F false: person / crate / box 0.5 / trolley / cable | set F rows worse | five empty bags: alarm frames / events / STOP episodes | gate, six recordings + set O |
|---|---|---|---:|---|
| shipped (flag 0) | 7 / 13 / 0 / 12 / 3 = **35** | — | 58 / 13 / 16 | PASS, identical |
| A: ≥ 2 standing | 7 / 12 / 0 / **21** / 3 = **43** | cable first 98.9 → 96.9 m | **32 / 9 / 10** | FAIL: `big_outside` false STOP 6 → 9 |
| B: ≥ 3 standing | 7 / **8** / 0 / **18** / 3 = **36** | trolley false 12 → 18 | 42 / 10 / 11 | FAIL: `big_above` STOP 12 → 11 |
| C: width only | 6 / 7 / 0 / **14** / 0 = **27** | trolley false 12 → 14; first trolley 151.4 → 149.5, cable 98.9 → 94.9 m | 43 / 13 / 11 | FAIL, 4 rows: set O background 3 → 12 frames, `big_above` 12 → 11, `doubleT_platform` STOP 1 → 2, `squareT…` events 9 → 10 |

Reading. The rule removes what it is for: with B the crate's six file-98 false detections go and
the crate is confirmed from 108.0 m instead of 101.9 m (A: 110.0 m; the 0.5 m box in 2 of 6
approaches instead of 1 in A and B). But a dropped bin changes the smoothed fit and curvature of
the next frames, and other marginal fixtures 40–55 m beyond the object confirm instead (trolley in
file 98: 0 → 7 in A, 4 in B); C moves 19 of the 30 first confirmations (trolley in file 172: 148.1
→ 103.3 m). On the real recordings the rule drops station structure feet from the fit:
`squareT_platform_squareT_switch` STOP episodes fall 15 → 9 (A: detections of the 82.9 m platform
end 27 → 13, of the 147.5 m switch parts 23 → 9), so these two STOP sources (§1f) sit in the far
bed fit, not in a shape rule; but set O loses a STOP frame (B, C) or gains false STOP frames (A),
advisory frames rise on 3–5 recordings and the per-frame height-reference range
`max(fit + 20 m, floor_verified)` shortens (C: median 127.5 → 115.0 m on
`squareT_platform_squareT_switch`). `doubleT_obstacle` is identical in A and B. The full gate
with the ride, run for A as information, fails on 4 gated rows: the ride 187 / 46 / 39 → 171 / 45
/ **40** (one STOP episode more; the fit range changes in 1 349 of its 11 271 frames, the median
height-reference range stays 120 m), set O `big_outside` false STOP 6 → 9, set F trolley false
12 → 21, cable first 98.9 → 96.9 m. With the flag off the full gate equals the baseline in every
row but latency. **Not shipped** by the pre-registered rule: no candidate lowers set F's false detections without a
kind or a gated row getting worse; `floor_far_min_width` stays 0. Tests: the rule on a synthetic
far bed (the crate's foot dropped, a rail head kept, both paths) and end to end on the ray-cast
tunnel (a person-size box standing at 60 m and, with the bed trimmed beyond 90 m, at 105 m is a
STOP on the same frame with the rule on; `tests/test_late_candidates.py`).

**The four items combined; new gate baseline** [measured 25.09]. The four branches merged
(`489fef3`; `estimate_axis_from_walls` returns both the shorter side's range of `far_switch` and
the persistence count of `platform_end`, `_fit_floor` both the shadow check and the far-bin
drop). Shipped: the rail-shadow rules; `walls_min_far_support`, `far_axis_both_sides` and
`floor_far_min_width` stay 0. Pre-registered at 19:03 UTC before any run on the merged code
([`p3_combined_2026-09-25.json`](evidence/results/p3_combined_2026-09-25.json)). The full gate of
the merged defaults (`c598cf6`, `--jobs 3`, 332 s, the dev VM alone) against
`regression_baseline_2026-09-25_ride_column.json`: **PASS**, 5 gated rows better, none worse, 95
the same, and every gated row equal to the rail-shadow item's own gate (383 values compared, only
latency differs): five bags 58 / 13 / 16, ride 187 / 46 / 39, `doubleT_obstacle` 185 of 246 from
frame 11, set O 303 → 311 inside STOP frames, set F straight false detections 35 → 24 with every
detection and first confirmation unchanged. Set O #1 over its 229 labelled frames: wrong-distance
STOP frames 12 → 0, largest error 0.46 m, 224 STOP frames, matched 216 → 224 (the rows of the item's
own run, byte for byte). Per frame on set O against the merged code with the three rail-shadow keys
off: no inside object loses a matched-alarm or STOP frame (#1 gains 217–224, the plank 704 and 707–712),
frames with an alarm matching no object 29 → 9; with those keys off the #1 rows equal the item's
pre-change baseline, so the three other flags do not act. No pair interacts: nothing was turned
back off. New baseline
[`regression_baseline_2026-09-25_ride_p3.json`](evidence/results/regression_baseline_2026-09-25_ride_p3.json).

**Review fixes of the rail-shadow rules** [measured 25.09]. A safety review of the shipped rules
found three faults. (1) `cluster.gauge_distance` took the nearest point of the strict-gauge mask,
which is the envelope *shrunk* by the axis-uncertainty margin (0.15 m per 100 m, §3.2 of
ALGORITHM), so an object entering the envelope obliquely was reported beyond its entry: a 1.2 m
bar crossing the 1.05 m edge at 0.15 m per m of X, +0.38 / +0.80 / +1.20 m at 40 / 80 / 120 m; on
set O the false STOP on the outside 2 × 2 m box (#7) at 136–144 m was reported 1.2–1.5 m beyond it.
(2) A held bed is the next frame's reference and nothing ended a hold: a 3.4° pitch step after the
warm-up held the flat bed for good (a lasting false STOP at 4.5 m, the rising bed). (3) The two
high bins that start a shadow need not be adjacent (28 and 62.5 m made one), and the object's face
was the first off-bed bin, not the one nearest the shadow (an off-bed bin at 8 m cut the rail
search to 4–7 m). Fixes (`95ff725`, ALGORITHM §3.1, §3.3, §4b): the distance is measured on the
envelope *widened* by that margin (never beyond where the object enters the envelope while the axis
error stays within the margin; the set O edge line at 1.35–1.40 m stays out);
`track.floor_shadow_max_hold` 20 frames, then the rule is released until no shadow is found (set O
#1 holds the bed 14 frames in a row, 11 of them fits, at ~0.95 m of approach per frame); adjacent bins and the face nearest the
shadow; health counters `floor_shadow_frames` / `floor_held_frames` / `floor_released_frames`.
Pre-registered at 19:47 UTC before any run of the fixed code on the organizer data, with the
unshrunk envelope and `gauge_distance` off as fallbacks. The full gate (`b718a37`, `--jobs 3`,
331 s) against `regression_baseline_2026-09-25_ride_column.json`: **PASS**, the same 5 gated rows
better, none worse. Against the first `_ride_p3` cut 4 values differ, all distances: the platform
end alarm 82.9 → 82.0 m and the ride's farthest alarm 160.5 → 158.3 m (both back to the
`_ride_column` values), and set F straight's 1 m box 10 → 12 false detections (file 168: the box at
112.6–114.4 m is one 6.6 m cluster with structure in front of it, part of which lies within the
widened reach, and the STOP is reported 4 m short). Per frame against `8556773` (its gate re-run
reproduces the first cut): decisions and the track model identical in all 15 269 frames; a gauge
detection's distance changes in 124 detection-frames, always shorter (the person of
`doubleT_obstacle` by ≤ 0.12 m, #7's false STOP to its labelled distance). Set O #1: every row
identical (224 STOP frames, 0 beyond 1 m, largest error 0.46 m); no inside object loses a
matched-alarm or STOP frame. The floor-shadow rule still fires only on set O (29 frames, held 14,
released 0). Tests 431 → 436, each new one failing on `8556773`. The baseline
`regression_baseline_2026-09-25_ride_p3.json` is re-cut on `154db25` (same name; that run equals
the `b718a37` one on every value but latency and in every frame). Raw:
[`p3_review_fixes_2026-09-25.json`](evidence/results/p3_review_fixes_2026-09-25.json).

### 1i. P3 items of 25.09, round 2

**The free-hanging exemption of `floating` (set O cube #2, 25.09)** [organizers' synthetic and
real, measured 25.09]. `floating` demoted the organizers' 0.3 m cube hanging 1.0–1.4 m above the
rail head (#2) at 44–59 m: measured from the rails it is 0.61–0.82 m off the axis, beyond
`signature_min_lateral` 0.6 m. The shipped rule, instrumented in one run on the six recordings,
set O and the ride (decisions identical to the baseline), shows what the cube is not: the ride's
43 `floating` cluster-frames (56.7–152.4 m) are 0.35–5.7 m in their largest extent (median 1.7 m),
24 of them reach up to the vault (top above 2.5 m) and 12 the wall side of the corridor (outermost
point beyond 0.95 m); the platform recording's 154 are mostly the ~104 m overhead structure. The cube is compact
(extents 0.04–0.33 m, 5–7 voxels), hangs free mid-envelope (top 1.37–1.40 m, outermost point
0.73–0.98 m, the wall 2.0–2.2 m off the axis, every other return ≥ 1.07 m away) and is a cluster
in 9 of the 10 frames from 59 m. Of the ride's two compact `floating` clusters, one hangs from the
vault (56.7 m, top 3.0 m, 0.13 m from the next return, a confirmed track), the other reaches
1.26 m off the axis. Rule (`cluster.floating_free_max_size`, with `floating_free_max_dy`,
`floating_free_max_top`): `floating` does not demote a cluster whose every extent is ≤ 0.5 m, whose
outermost point is ≤ 0.95 m off the axis and whose top is ≤ 2.5 m. Pre-registered at 20:52 UTC,
after the instrumented run and before any candidate run
([`p3_signatures_2026-09-25.json`](evidence/results/p3_signatures_2026-09-25.json)): A 0.5 /
0.95 / 2.5 m, B 0.4 / 0.95 / 2.5, C 0.5 / 0.90 / 2.2 in that order; ship the first with gate exit
0, #2 improved and the safety conditions (`doubleT_obstacle`, set O inside objects and set F
straight identical or better, no new false event on the five bags or the ride). A, on `edec4da`
with `--jobs 1`: **gate PASS**, 2 gated rows better, none worse. #2: 19 → **30 STOP frames**, first
STOP **34.0 → 52.5 m**, held from 37.4 → 57.5 m (inside STOP frames 303 → 314, still 5 of 8
objects). The six recordings and all 11 271 ride frames are identical frame by frame (decisions,
detections, warnings); set O differs in 11 frames, all #2; `doubleT_obstacle` 58 / 127 / 124 hits,
first frame 11; set F straight identical; #5 0 and #7 6 false STOP frames, background 3 / 2. B and
C were not run. **Shipped** (0.5 / 0.95 / 2.5 m; the new defaults resolve to the configuration of
that gate run). Not won: #4 stays advisory, its outermost point 1.18–1.32 m off the axis like the
outside cube #5's (Q1); #8 waits on Q2. Tests: `tests/test_floating_free.py` (ray-cast: the cube at
30–55 m is a STOP, a person beside it a STOP, a plate fixed to the wall stays `floating`).

**Thin hanging objects (SCORECARD #11, `cluster.hanging_enabled`; shipped, on)** [measured
25.09]. The organizers' 5 cm object hanging from the roof of set O read `GO` in all 42 visible
frames. Beyond ~50 m none of its returns is inside the envelope measured from the rails. At
30–61 m 1 of 1–7 returns a frame is inside, at 17–28 m 1–3 voxels: the rings above +2° are 0.5°
apart. The corridor cluster (5–8 voxels) forms only at 8–15 m, too late to confirm. The new stage
(`clustering.find_hanging`, ALGORITHM §3.3 item 8) links those returns to the part above the
envelope top (\|dy\| < 0.8 m, 1.8 m to 0.6 m above the top, ≤ 0.5 m along and across, ≤ 60 m).
It drops a group that another stage already has, and confirms over 5 frames. *Pre-registered*
at 20:53 UTC ([`p3_thin_hanging_2026-09-25.json`](evidence/results/p3_thin_hanging_2026-09-25.json),
with the points per frame by range): A (≥ 1 voxel inside), B (≥ 2), C (B nearer the axis,
thinner, ≤ 40 m); ship the first with gate exit 0 and a STOP on the target. **A passed first**
(`--jobs 1`, the ride and set F straight included,
[gate JSON](evidence/results/regression_gate_2026-09-25_thin_hanging.json)): `thin_hanging` 0 →
**15 STOP frames, first STOP 30.1 m**; set O 303 → 318 inside STOP frames (6 of 8 objects).
Every other gated row is the same: five bags 58 / 13 / 16, ride 187 / 46 / 39, `doubleT_obstacle`,
the other set O objects, set F straight. B and C were not run. **Imitators** (every group kept,
logged): in set O only the target, none in the six recordings, 29 single-frame groups on the ride.
28 of those are tops of station columns 13–40 m ahead at \|dy\| 0.4–0.8 m, in frames without a
rail pair. All joined tracks already advisory, so nothing was added. A fresh track there could
confirm; a rail-lock condition (not measured on the branch) would remove 28 of the 29. Cost 0.5 ms
a frame. The new defaults (`c0b4f2f`) reproduce A frame by frame on the seven recordings. Tests
(`tests/test_thin_hanging.py`): shapes, and ray-cast at 16.5 m/s, where the object STOPs from
30.1 m and a person 3 m beyond it STOPs on the same frame as without the rule.
*Rail-lock guard (decision B of the captain's delegate, 25.09): adopted.* Pre-registered at
22:13:58 UTC, before its code existed
([`p3_thin_hanging_2026-09-25.json`](evidence/results/p3_thin_hanging_2026-09-25.json),
`addendum_rail_lock`): `cluster.hanging_needs_rails` true runs the stage only on frames whose
track model found the rail pair in the near range (`track.rail_slabs` > 0); adopt only if set O's
hanging object keeps 15 STOP frames and a first STOP at ≥ 30.1 m and the combined gate with it
has no row worse than without it. Both held on the combined round-2 code (`e29d932`, `--set`):
`thin_hanging` 15 STOP frames from 30.1 m, held from 31.8 m, as without it; the gate with the
guard against the gate without it exits 0 with all 107 compared rows the same. Decisions are
identical in all 15 068 frames; on the ride the guard removes 28 of the 29 groups, the station
ones (the one it keeps is in a frame with a rail pair; set O's 14 are all in such frames; advisory
frames 4 747 → 4 743, 4 742 before round 2; `clear_distance` no longer capped by them in 22
frames; track ids renumbered). On since `30d0cac`; the full gate on that commit equals the
`--set` run frame by frame.

**Conservative `clear_distance` (SCORECARD §6 row 6; 25.09; failed its pre-registered clutter limit, shipped on by the captain's delegate).** The verified-clear
distance counts confirmed obstacles only (ALGORITHM §6). On set O, current code, 172 of the 505
object-frames of in-envelope objects with points inside the measured envelope report a
`clear_distance` more than 0.5 m beyond the object (`scripts/score_clear_distance.py`; the
judgement's count, decision `GO` without tolerance: 192, 89 of them inside the measured envelope;
184 / 89 on 24.09). The opt-in `health.clear_cap` caps it at the nearest cluster of the frame that
touches the strict envelope and is not a confirmed obstacle's own (the obstacle keeps its own
distance, so the rule is independent of how that distance is defined). The node's decision does not
read `clear_distance`: 0 frames change between GO, CAUTION and STOP on set O, the five
obstacle-free recordings and the ride, for every candidate. Pre-registered at 20:42 UTC (C0–C5) and,
after round 1, at 21:07 UTC (R1–R4, the same without column-demoted clusters); shipping needed the
set O count to drop, the gate to pass, and on the five recordings and on the ride a median
`clear_distance` shrinking by ≤ 5 % with ≤ 2 % of the frames pushed under 60 m
([`p3_clear_distance_2026-09-25.json`](evidence/results/p3_clear_distance_2026-09-25.json)):

| candidate | set O overclaim | five recordings: median 127.0 m, change / frames pushed < 60 m | ride: median 127.0 m, change / < 60 m |
|---|---:|---:|---:|
| C0 3rd strict-envelope return + clusters | 46 | −23.9 % / 4.59 % | −12.7 % / 4.87 % |
| C1 clusters ≥ 1 voxel or a point within envelope + 0.1 m | 76 | −16.6 % / 4.24 % | −5.5 % / 4.53 % |
| C2 / C3 clusters ≥ 1 strict voxel, seen ≥ 1 / ≥ 2 frames | 82 / 92 | −5.5 % / 3.02, 2.62 % | −5.5, −5.4 % / 3.42, 3.02 % |
| C4 / C5 ≥ 3 voxels, ≥ 2 / ≥ 3 frames | 92 / 101 | −5.5 % / 2.45, 2.14 % | −3.5, −3.1 % / 2.80, 2.53 % |
| R1 = C2 without columns | 82 | −5.5 % / 1.22 % | −3.1 % / 1.49 % |
| R2 / R3 / R4 | 92 / 92 / 101 | −5.5 % / 0.79, 0.66, 0.35 % | −1.8, −0.9, −0.2 % / 1.04, 0.86, 0.59 % |

No candidate passed. In round 1 the column row of the double-track tunnels, which the far axis puts
0–1.1 m off the axis at 40–60 m with up to 79 strict voxels, made 228 of the 293 ride frames pushed
under 60 m (C5). In round 2 only the five recordings' median fails: 17 % of their frames sit on the
120.0 m plateau of the monitored range, and `squareT_platform_squareT_switch`, standing at the
platform, is capped at the platform-end and overhead structures at ~80–150 m that also cause its
false STOPs. R1 would have cut the overclaim from 172 to 82 (judgement count 192 → 172, 76 inside)
and the ride's median clear distance from 127.0 to 123.0 m; of the 90 frames it fixes, the cap
comes from `elevated` clusters in 38, `floating` in 21, not-yet-confirmed clusters in 26 and an
advisory track in 5. Of the 82 left, the far 0.3 m floating cube (30) and the 5 cm hanging object (15) mostly form no cluster
that touches the envelope; the point-level C0 brings them only to 17 and 11 and shortens the
empty-track range by 13–24 %. The flag stays off, byte-identical to `1c96233`
(`scripts/output_fingerprint.py`, 2 930 frames); `health.clear_cap: true` alone runs R1. The gate
with R1 on (`--jobs 1`, 1 093 s) passes with no gated row changed (five recordings 58 / 13 / 16,
ride 187 / 46 / 39, set O 303 STOP frames, set F straight identical), and its per-frame
`clear_distance` equals the sweep's on all 15 068 frames.
*Decision (25.09, 22:15 UTC, the captain's delegate): `health.clear_cap` on, candidate R1.* It did
**not** pass: R1 missed the pre-registered clutter limit (the five obstacle-free recordings'
median clear distance −5.5 % against −5 %, by 0.5 pp; the ride −3.1 %, 1.49 % of its frames under
60 m), and R1–R4 were designed after round 1. It ships anyway because it makes the verified-clear
distance conservative (set O object-frames with a `clear_distance` past an in-envelope object
172 → 82) and changes no detection and no decision. The status JSON now carries
`health.candidate_distance` (additive). Recorded in
[`p3_clear_distance_2026-09-25.json`](evidence/results/p3_clear_distance_2026-09-25.json)
(`decision`); the numbers on the combined round-2 code are in the combined paragraph below.

**5 Hz and a ±3° re-mount (SCORECARD #13, criterion 8.4; P3, 25.09 evening): shipped.** The §1g
events, traced frame by frame on `1c96233`, had four causes, none in the tracker windows
(`confirm_time_s` is already in seconds): the calibration spacing counted frames (the 5 Hz final
never completed on the 25 s bags); the axis rate limits and yaw / curvature EMA were per frame,
so at 5 Hz the axis lagged the curve of `roundT_doubleT` (yaw 0.009 rad behind at frame 112) and
a low cluster at 47 m and structures at 83–137 m swept into the gauge; the provisional tilt (5
consecutive frames) saw one canted stretch there (roll −1.0…−2.2°), so a re-mounted rig ran ~20 s
with a 1.6–2° roll error; a final confirming the provisional (`doubleT_obstacle`, 0.16°) re-seeded
the track model and lost frame 191. On since 25.09: `calibration.time_cadence` and
`track.rates_per_period` / `walls_smoothing_per_period` (periods of the input rate, the median of
the last 9 stamp intervals), `calibration.refine_min_deg` 0.5 (the spaced observations replace the
provisional tilt) and `calibration.keep_within_deg` 0.25. Pre-registered 20:50 UTC with three
dated addenda written before their runs
([`p3_robustness_2026-09-25.json`](evidence/results/p3_robustness_2026-09-25.json); all runs:
[`scorecard13_p3_2026-09-25.json`](evidence/results/scorecard13_p3_2026-09-25.json)). Five empty
bags false events / STOP episodes, `roundT_doubleT` events, `doubleT_obstacle` hits @ first alarm:

| mode | base `1c96233` (= P4) | shipped |
|---|---|---|
| 10 Hz as recorded | 13 / 16, 0, 185/246 @ 11 | 13 / 16, 0, **186/246** @ 11 |
| 5 Hz | 13 / 17, **3**, 92/123 @ 12 | **10 / 10**, 0, 92/123 @ 12 |
| +3° roll | 16 / 17, **2**, 181/246 @ 12 | **11 / 13**, 1, 181/246 @ 12 |
| +3° pitch | 17 / 18, **1**, 186/246 @ 11 | 16 / 17, 0, 186/246 @ 11 |

The axis flags make the 5 Hz gain, the refinement the tilt gain (it adds one roll event in
`roundT_pressureGate_roundT`); time cadence and keep-within change no stress count. Tried, not
shipped: the EMA of the bed and rails per period (5 Hz `doubleT_obstacle` 92 → 87/123), a
per-axis provisional gate (roll / pitch 19 events), periods from each single interval (the ride's
receive stamps come in bursts: gate FAIL, ride 46 / 39 → 48 / 42). 10 Hz gate (`--jobs 1`): PASS,
`doubleT_obstacle` object on the rail +1 hit, ride, five bags, set O and set F straight identical.
Open: pitch stays at 16 (`doubleT_platform` 6 vs 4, `squareT_platform_squareT_switch` 10 vs 9:
marginal clusters, not traced to a rate or tilt rule); roll alarms once on the far column of
`roundT_doubleT` (frame 234).

**The four round-2 items combined; new gate baseline (P3 integrator, 25.09, delegated by the
captain)** [real, organizers' synthetic and synthetic, measured 25.09]. The four branches
(`wf9/signatures`, `wf9/thin-hanging`, `wf9/clear-distance`, `wf9/robustness`, all from
`1c96233`) merged with `--no-ff` on top of the §1h items (`f46a669`) on `wf10/p3-round2`; code
conflicts only in `clustering.py` imports, the stage order in `Detector.process` (the opt-in
`far_axis_both_sides` mode-2 step, then the hanging stage) and the track model's age (it counts
nominal periods, next to the floor-shadow fields; `floor_hold_run` stays per frame). The
captain's delegate's decision A turned `health.clear_cap` on (above); decision B was the
rail-lock guard (thin-hanging paragraph above). Pre-registered at 22:13:25 UTC, before any run on
the merged code ([`p3_round2_combined_2026-09-25.json`](evidence/results/p3_round2_combined_2026-09-25.json)):
gate exit 0 against `_ride_p3`, no gated row worse, and the safety conditions (`doubleT_obstacle`
labelled hits and first alarm frame, set O inside STOP frames and first STOPs, set F straight
detections identical or better; no new false event on the five bags or the ride). Full gate
(`--jobs 3`, the ride in 8 pieces, set F straight) on the final clean commit `30d0cac` (333 s):
**PASS, 6 gated rows better, none worse**:

| | `_ride_p3` | round 2 combined |
|---|---|---|
| five bags alarm frames / events / STOP episodes | 58 / 13 / 16 | 58 / 13 / 16 |
| ride | 187 / 46 / 39 | 187 / 46 / 39 |
| set O inside STOP frames (of 801) / objects with a STOP (of 8) | 311 / 5 | **337 / 6** |
| set O hanging 0.3 m cube (#2) STOP frames, first STOP | 19, 34.0 m | **30, 52.5 m** |
| set O 5 cm hanging object (#10) | 0, none | **15, 30.1 m** |
| set O outside false STOP frames / background frames, ids | 6 / 3, 2 | 6 / 3, 2 |
| `doubleT_obstacle` labelled hits (person + object) @ first alarm frame | 185 / 246 @ 11 | **186 / 246** @ 11 |
| set F straight person first confirmation / false detections (all kinds) | 151.0 m / 26 | 151.0 m / 26 |

Every gated row moved as its item's own gate said, so no pair interacts and nothing was turned
back off. With the four items off (`--set`) the merged code reproduces `_ride_p3` on every gated
row; against that run, per frame, the STOP decision and every detection (track id, distance,
kind) are identical in all 2 287 five-bag and 11 271 ride frames; the ride's advisory warnings
differ in 3 frames, the warning flag in 1 (advisory frames 4 742 → 4 743: a hanging group in a
frame with a rail pair joins an advisory track); set O gains
26 STOP frames and loses none; `doubleT_obstacle` gains frame 191. `clear_distance` with the cap
(decision A), from the same run: five bags median 127.0 → 120.0 m (−5.5 %, the failed limit
unchanged), ride 127.0 → 123.0 m (−3.1 %, 169 frames = 1.50 % pushed under 60 m), set O
object-frames with a clear distance past an in-envelope object 147 → 67 of 505 (147 without the
cap here, not 172: the two newly stopped objects no longer overclaim); no decision changes. The
stress check on the combined defaults (`scripts/robustness_check.py --jobs 3`; five bags false
events / STOP episodes, `roundT_doubleT` events, `doubleT_obstacle` labelled hits @ first alarm)
equals the robustness branch in every mode: as recorded 13 / 16, 0, 186/246 @ 11; 5 Hz
**10 / 10**, 0, 92/123 @ 12; +3° roll **11 / 13**, 1, 181/246 @ 12; +3° pitch **16 / 17**, 0,
186/246 @ 11. The new gate baseline is
[`regression_baseline_2026-09-25_ride_p3b.json`](evidence/results/regression_baseline_2026-09-25_ride_p3b.json)
(the final run without its gate block). Tests 436 → 456.

**Safety review of the round-2 items and its fixes (26.09): the refinement off; calibration
changes keep a confirmed STOP** [real, organizers' synthetic and synthetic, measured 26.09]. An
adversarial review of `17a850d` returned BLOCKING: every refinement of the provisional tilt
re-seeded the track model from nothing (`prev=None`), and for its warm-up the fresh model had no
floor-shadow reference and no smoothing. On `doubleT_obstacle` (5 Hz, rig +2° roll / +2° pitch) the
bed fit then ran to 87.5 m and swallowed the object at 56 m: no STOP on frames 102 and 104, with
`clear_distance` 151 / 163 m while the object's track was alive; also frame 76, frame 182 (5 Hz,
(0, −1.5°)) and frame 197 (10 Hz, (0, +2°)); and the refinement flapped (4 re-seeds on
`roundT_doubleT` +3° pitch). Reproduced on a clean copy of `17a850d` with the reviewer's sweep per
frame (26 mounts × 10 / 5 Hz): 5 STOP frames lost in 3 runs against the refinement off, 15 gained.
MAJOR: the hanging stage dropped its own cluster for an overlapping *advisory* one (a cable hanging
to 1.85–2.2 m, 0.65–0.75 m off the axis, demoted as `floating`: no STOP in 5 of 6 ray-cast cases).
MINOR: the input-rate estimate dropped stamp intervals under 0.02 s, so bursty 10 Hz stamps read as
2–3 periods. *Pre-registered* at 00:25 UTC with two dated addenda written before their runs
([`p3_round2_review_fixes_2026-09-26.json`](evidence/results/p3_round2_review_fixes_2026-09-26.json)).
Shipped, on: a change of the correction up to 1° rotates the track model into the corrected frame
instead of re-seeding it (`calibration.reseed_keep_max_deg`); the tracks follow every change and a
STOP stays reported up to 5 frames after its last match, only STOPs are kept through a change above
1° (`tracking.reseed_hold`); `clear_distance` is also capped at a lost reported track
(`health.clear_cap_lost`); a hanging cluster yields only to an overlapping obstacle
(`cluster.hanging_yield_gauge_only`); the input rate is the mean of the last 14 stamp intervals
within 0–0.5 s (the periods are identical to the old ones on every 10 Hz frame of the gate and every
stress frame; alternating 0.19 / 0.01 s stamps give 1). **The refinement could not be made safe
and is off** (`calibration.refine_min_deg` 0): C1 (a per-axis trigger on the raw medians, two
observations in a row, every reported track kept) lost no STOP frame against the refinement off,
but failed the stress rule (5 Hz `doubleT_obstacle` first STOP 12 → 18: an object reported as
advisory under the 3° tilt kept its advisory vote after the correction; +3° roll 11 / 13 → 14 / 16:
the per-axis trigger kept noise-level provisional tilts); C1b (the round-2 trigger on two
observations in a row, at most one refinement, only STOPs kept above 1°) lost frame 182 at 5 Hz
(0, −1.5°) and gave +3° roll 13 / 16, +3° pitch 17 / 18; C1c (one observation) loses frame 182 too:
the refined, final-like pitch applied before frame 182 loses it in every variant. The fallback C3
(`6c19890`): **gate PASS** against `_ride_p3` (the same 6 rows better, none worse), against `_p3b`
every row but latency the same; per frame against `17a850d`'s gate run, decisions, detections and
the track model are identical in all 15 269 frames, warnings differ in 2 ride frames (a column
track's association after a hanging cluster kept by the overlap fix; it keeps one in 2 frames of
`roundT_doubleT` and 25 of the ride, none confirmed), and `clear_distance` is shorter in 398 frames,
never longer: five bags median 120.0 m unchanged, the ride 123.0 → 122.6 m (53 more frames under
60 m), set O overclaim 67 → 60 of 505 object-frames. Reviewer's sweep against `17a850d` with the
refinement off: in the 18 gating runs 2 frames lost, both frame 197 at 10 Hz ((−2°, 0) and (0, +2°):
the frame the as-recorded run misses too, which the fresh re-seed at the final correction happened
to catch and the rotated model does not), 23 gained (frames 190–200 after the final correction of
the +2° / +3° roll rigs: the STOP held through it); the reviewer's 5 Hz cases keep every STOP frame
((+2°, +2°) 95 STOP frames as with the refinement off, 76, 102 and 104 among them; (0, −1.5°) 95,
182 among them); the reviewer's other 17 mounts: 2 lost (frame 197 again), 52 gained. Against
`17a850d` as shipped, with the refinement on, the refinement's own gains are given up too (10 Hz
(+2°, +2°) and (0, −3°) frame 117, (+3°, +2°) frame 197, 5 Hz (0, −3°) frames 76, 122 and 182). Stress: 5 Hz five bags
**10 / 10**, `doubleT_obstacle` 92/123 @ 12 (the same); +3° roll **14 / 16**, 183/246 @ 12; +3°
pitch **17 / 18**, 186/246 @ 11: the refinement's tilt gain of round 2 (11 / 13, 16 / 17) given up,
no worse than `17a850d` with the refinement off (16 / 17, 17 / 18). Tests 456 → 469
(`tests/test_reseed_safety.py`: a final or refined correction of 0.7 / 1.5° while a ray-cast STOP
is confirmed keeps it and never reports `clear_distance` beyond it — on `17a850d` the 1.5° change
reset the tracker, 4 frames without the STOP; the rotated model, the hold, the lost-track cap, no
flapping, the bursty input rate; `tests/test_thin_hanging.py`: the overlap rule, and the reviewer's
cable STOPs from 31–34 m, never without the rule). The gate baseline
[`regression_baseline_2026-09-25_ride_p3b.json`](evidence/results/regression_baseline_2026-09-25_ride_p3b.json)
is re-cut on the final commit `0c8f8e1` (its gate: PASS, per frame identical to C3's run; every
gated and recorded value the same as the first cut, the configuration hash, the commit and the
latency changed).

*26.09, re-review of `10e2707` (addendum 3 of the same file, pre-registered 03:47 UTC):* a match
on the change frame ended a STOP's `tracking.reseed_hold`, so the hold is now a fixed window of 5
frames from the change, matched or not (6 at 10 Hz when the model is re-seeded: its warm-up without
a floor-shadow reference), a ray-cast test guards the rotation sign (fails with `dR` transposed or
not applied) and `scripts/robustness_check.py` imports its own checkout; on `5f64ad4` the gate
(PASS), the stress check and the reviewer's sweep are identical to `10e2707` frame by frame, so the
`_p3b` baseline stands; tests 469 → 486.

### 1j. Start-up of a fresh bag (26.09): census; three rules tried, none shipped

[real, organizers' synthetic and ray-cast, measured 26.09; P3 / P4.] An independent judge
replayed ride piece 2 of 8 from a fresh start. It got a STOP at 2.9–3.1 m in the first 1.5 s,
with the mount calibration still pending. The jury plays every hidden bag from a fresh start.
*Census* (`scripts/startup_census.py`, on `867bb8a`): a fresh detector over the first 40 frames
(4 s) of each of the 221 ride split files (the bags as recorded), the 8 piece starts of the gate,
the six recordings and set O. Counts are STOP frames / events / episodes.

| starts | with a STOP | STOPs | events `low` / corridor | in the first 1.5 s |
|---|---|---|---|---|
| 221 ride splits | 18 | 120 / 35 / 28 | 9 / 26 | 8 events, all corridor, 32–145 m |
| 8 gate pieces | 2 | 22 / 2 / 2 | 1 / 1 | the finding (`low`, 2.9 m); piece 0 at 138 m |
| five obstacle-free recordings | 1 | 4 / 4 / 1 | 3 / 1 | none (`doubleT_platform` frames 34–37) |

Every ride and five-bag event happens under calibration status `pending`. On an untilted rig that
status lasts until the final tilt (~20 s), so it separates nothing. The provisional decision
comes on frame 4 in 215 of 221 starts, before every event. Real objects in the windows:
`doubleT_obstacle`'s person from frame 11 (corridor, 55.5 m, provisional rig) and set O's 2 × 2 m
box from frame 5 (98 m). No real low object is in any window.

**Conclusion: a fresh start does not add false STOPs.** On the same 8 588 frames inside the
continuous gate run, the warm detector STOPs more: 128 frames / 41 events, against 97 / 31 fresh.
The start-window STOPs are the ride's ordinary false alarms, at the same places.

**The finding** reproduces only from the gate's cut at `new_data_55_0013`. It does not appear from
`new_data_55_0000` or warm. The train stands there. The young model (age 12–15, rail score
0.06–0.09) puts both rail heads 3.0–3.6 m ahead 3–12 cm above its rail-head plane. That is in
front of the 4–30 m range the bed cross-section is learned from. The low track is matched at
3.0–3.6 m and never at 4 m. In the gate and in every census start, it is the only confirmed low
track that stays under 6 m.

*Pre-registered* at 05:47 UTC, before any candidate code
([`p3_startup_2026-09-26.json`](evidence/results/p3_startup_2026-09-26.json)). The candidates, in
order:

* (a) `low` tracks advisory while the calibration is `pending`;
* (b) no new `low` STOP while the track model is younger than 16 frames;
* (c) a `low` track reported only once it has been matched at ≥ 4 m.

A candidate must pass three checks, in order:

* S1: ray-cast fresh starts. The empty tunnel never STOPs. Objects 20–40 m ahead keep their STOP
  frames.
* S2: the census.
* S3: the full gate.

**(a) fails S1:** a real low object 20 / 40 m ahead of an untilted fresh start never STOPs. For
information, its census would give 41 → 30 false events.

**(b) fails S1:** the first STOP of the same object moves from frame 4 to frame 16. Its census:
41 → 39.

**(c) passes S1–S3:** census 41 → 40 false events (the finding's 4 frames), gate PASS, ride
187 / 46 / 39 → 183 / 45 / 38, every other row the same. It was first shipped on `904fd7c`.

**The coordinator's blind-zone check then reverted it** (addendum of 26.09, same file). The case
(ray-cast, fresh or warm detector, rule on / off): the organizers' 30 × 30 × 10 cm object on a rail
head, an object lying across a rail, and a 0.5 m box, each 2.5–3.9 m ahead of a standing train,
or appearing there (falling onto the track).

* With the rule off, every object at 3.0–3.9 m STOPs from its 5th frame.
* With it on, the two low objects never STOP, at any of those distances, fresh or appearing. The
  same holds for objects appearing at 3.9 m ahead of a train at 0.5 and 1 m/s.
* A 0.5 m box across a rail at 3.9 m from a fresh start is taken as `low` and lost too.
* At 2.5 m nothing is visible either way (`gauge.range_min` 3 m).

A safety fix wins over a false-alarm gain (1 ride event, 4 frames in 229 starts): **none of the
three is shipped**. The flags `lowobj.pending_advisory`, `lowobj.min_model_age` and
`tracking.low_min_seen_distance` stay in the code, off. The default output is identical to
`11c50a7` frame by frame on the six recordings and set O. The
[`_p3b`](evidence/results/regression_baseline_2026-09-25_ride_p3b.json) baseline stands.

The finding stays open: a fresh start at a standing train can STOP on the rail heads 3 m ahead.
The corridor STOPs of the windows are not addressed: delaying them would delay
`doubleT_obstacle`'s frame 11. Tests 492 → 500 (`tests/test_startup.py`). Among them: the
organizers' object 3 m ahead of a standing fresh start STOPs from frame 4.

### 1k. P3 items of 26.09

**Rail heads ahead of a standing train at a fresh start: `lowobj.rail_start_within` 4 m, shipped.**
[real and ray-cast, measured 26.09; P3.] This closes the open finding of §1j. From the gate's
piece-2 cut (`new_data_55_0013`), a fresh detector STOPs on frames 12–15 at 2.9–3.1 m. The STOP
is a `low` track on the rail heads 3.0–3.6 m ahead. Reproduced on `bd67fb0` (`resense run --npy`
and the census of the 8 piece starts): the same frames, track and distances.

*Why a narrow rule exists.* The young model's rail-head plane lies 13.5–15 cm under the real rail
heads at 2.5–6 m. The low clusters are the rails' flank returns, just under the rail head's own
line. For each low cluster under 4 m, two heights were measured with no rule applied:

* its top: the highest return in its lateral band within its extent;
* the band's height where it continues along the track: the median, over 0.25 m bins at 2.5–6 m,
  of each bin's highest return.

In the finding, all 13 low clusters under 4 m have their top 1.0–3.7 cm above that line. The
ray-cast objects rise more: the organizers' 0.10 m object on a rail head 10.0–10.8 cm, the object
across a rail 13–14 cm (and it is 0.54–0.60 m wide), the 0.5 m box 32 cm.

*The rule* (pre-registered at 07:12:49 UTC, before any candidate run:
[`p3_rail_start_2026-09-26.json`](evidence/results/p3_rail_start_2026-09-26.json)). A low cluster
under 4 m is rail geometry when all of these hold:

* it reaches an expected rail line (the axis ± 0.795 m) within 0.10 m;
* it is at most 0.45 m wide;
* its band continues along the track (≥ 4 bins outside its extent ± 0.3 m);
* it rises at most 0.05 m above that band's line.

The tracker does not newly report a low track on such a cluster if the track was never matched
at ≥ 4 m. A track already reported, or seen farther away (set O's low objects from ≥ 10 m), is
not affected. The association is unchanged, so the rule can only withhold a report.

| check (pre-registered order) | result with the rule (C1) |
|---|---|
| S1 the finding | STOP frames 4 → 0; all 13 low clusters under 4 m marked; census of the 8 piece starts: piece 2 no STOP, piece 0 unchanged |
| S2 blind zone: `tests/test_startup.py` and the 40 ray-cast cases of §1j, rebuilt | all pass; the 40 cases identical to the defaults (32 STOP, same first frame and STOP count), the 17 that rule c lost included; 0 of 465 low clusters under 4 m marked |
| S3 full gate against `_p3b` (on `16c4cac`, the rule on by default) | **PASS**: ride 187 / 46 / 39 → 183 / 45 / 38 (the finding's 4 frames), every other gated and recorded row the same. `doubleT_obstacle` 58 / 61, 128 / 185, 125 / 126 from frame 75, first alarm frame 11; set O first STOPs and STOP frames the same (its low objects still STOP down to 1.4 m); set F straight the same ([JSON](evidence/results/regression_gate_2026-09-26_rail_start.json)) |
| census of §1j, information (all 236 starts) | false STOP events 41 → 40: only the finding's; no start loses or gains any other STOP event; `doubleT_obstacle` first STOP frame 11 and set O's 2 × 2 m box from frame 5, as before |

C2 (tighter margin and width) was not needed. With the flag at 0 the output is identical to
`bd67fb0` (`scripts/output_fingerprint.py`: 2 930 frames, 0 differ). The baseline is not re-cut.
An object lying *along* a rail stays the documented limitation (ALGORITHM §6). Beyond 4 m
nothing changes. Under 4 m, a low track is withheld only if it was never matched farther and
rises less than 5 cm above the rail head's own returns. Tests 500 → 527
(`tests/test_rail_start.py`).

**Safety review of 26.09.** Three corrections and one hardening, taken before the combined gate.
* The "never matched at ≥ 4 m" clause is not a safeguard. A track is deleted after more than 3
  missed frames; a detector reset or a re-mount starts it again. What protects a real object is
  the 5 cm margin above the rail head's own line. The spec minimum is 30 × 30 × 10 cm.
* Hardening, `lowobj.rail_start_min_ref` 0.06 m: a cluster is marked only where the band's line
  is at least 0.06 m above the model's rail-head plane. That is the young-model fault the rule
  compensates: 0.135–0.148 m in the finding, ~0 under a correct model, where nothing is marked
  now (`tests/test_rail_start.py`). The finding stays fixed: `resense run --npy
  /data/cache/new_data --start 2818 --limit 40` has no STOP frame (rule off: frames 12–15,
  2.88–3.15 m, `low`) [real, 26.09].
* A known weakness, not caused by the rule: on real frames the 0.3 × 0.3 × 0.1 m box 3.0–3.9 m
  ahead of a standing fresh start first STOPs at frame 5–36, with the rule on or off (the reviewer's
  replays [team record, unverified: raw not committed]). `tests/test_startup.py`'s frame 4 is the
  synthetic tunnel only. A bar along the rail head never STOPs (`lowobj.min_width`).

### 1l. P3 items of 26.09: near-field escalation

**Near-field escalation (judge B, action 6): shipped.** [organizers' synthetic, real and
ray-cast, measured 26.09; P3.] On set O, objects with points inside the envelope get no alert or
only CAUTION. The box at the envelope top (#8) STOPs in 12 of 124 frames, none within 50 m. The
edge box (#6) reads GO in its 8 in-envelope frames. Replay on `bd67fb0`, inside objects, frames
with object points inside the envelope:

| object | frames | STOP / CAUTION / GO | why not STOP |
|---|---|---|---|
| #8 box at the top | 75 | 12 / 37 / 26 | within 50 m `elevated`: a 1.4–2.4 m wide sliver 2.76–3.0 m up, 18–235 strict voxels; thin slivers dropped (`min_height`) |
| #4 cube at the edge | 16 | 0 / 16 / 0 | `floating` (3–30 strict voxels) or < 3 strict voxels |
| #6 box at the edge | 8 | 0 / 0 / 8 | inside only at 16–2 m; the wall rule drops it (1.95 m tall, 1.21–1.24 m off the axis) in 5 frames, a young track in 3 |
| #1, #2, #3, #9, #10 | 406 | 324 / 0 / 82 | sparse returns at 50–250 m, first frames of a track |

That makes 116 GO and 67 CAUTION-only frames; 78 of the GO frames have ≥ 3 points inside (the
judge's ~80). Measured from the rails, #6's inner face is 1.06–1.33 m off the axis beyond 16 m, so
it is outside there. From the sensor axis it is 1.1 m at every range.

What else would meet the rule (every track matched within 60 m on the six recordings, set O and
the ride in the gate's pieces):

* on the ride, confirmed advisory tracks within 40 m carry ≤ 8 strict voxels, except a station
  column row (`new_data_54`–`55`, 20–32 m, 0.7–1.2 m off the axis) with 50–150;
* on `doubleT_platform`, a platform structure with 5–15 at 37–40 m;
* #5 has ≤ 4 in any frame, #7 none within 40 m.

*Pre-registered* at 07:19 UTC, before any candidate run
([`p3_near_escalation_2026-09-26.json`](evidence/results/p3_near_escalation_2026-09-26.json)).
`tracking.near_escalate_voxels` N, `_distance` D, `_hits` K: a track whose last K hits each had
≥ N strict voxels within D m is a STOP (reason `near_envelope`). A column never counts, and the
column hold wins. The candidates were A (10, 35 m, 5), B (20, 35 m, 5) and C (10, 30 m, 5). D, for
#6: `cluster.wall_keep_gauge_voxels` 10 within 20 m spares the wall rule.

**A passes and ships** (full gate, `--jobs 1`, against `_p3b`: PASS, 3 gated rows better).

* Set O inside STOP frames 337 → 349: #8 12 → 22, held from 23.9 m; #4 0 → 2 (5.2 m).
* #5 0, #7 6, background 3 / 2: unchanged.
* The ride 187 / 46 / 39, the five bags 58 / 13 / 16 and `doubleT_obstacle` (hits, frame 11):
  identical.
* Set F straight: identical.
* Every first STOP is unchanged.

B and C were not run.

**D on top of A passes and ships too** (full gate: PASS, 5 gated rows better).

* #6 0 → 6 STOP frames, from 10.3 m (5 of its 8 in-envelope frames).
* Set O inside STOP frames 349 → 355; 8 of 8 inside objects now STOP.
* Everything else the same as A.

On the ride, the only wall-dropped blobs with ≥ 10 strict voxels within 20 m are the column row
(the column signature takes it) and a 7 m wall segment (the wall-segment rule drops it).

The escalation alone cannot reach #6: it is never an advisory track. Without the column exclusion
it would add 40 STOP frames and 6 events on the ride's column row (offline replay).
`tests/test_near_escalation.py`, +12 tests: a box inside the envelope top 20–30 m ahead goes from
CAUTION to STOP on its 5th frame; a cube in the advisory zone just outside stays CAUTION. With
both flags off, the output is identical to `bd67fb0` (`scripts/output_fingerprint.py`, 2 930
frames). Numbers moved: the gate baseline is not re-cut here, the integrator will.

**Safety review of 26.09.** Three changes, taken before the combined gate. Each is a no-op wherever
it does not apply.
* A: a `beyond_axis` or `beyond_height_ref` demotion never counts as a near hit, like a column.
  The corridor's axis or height reference is not trusted there, so its strict voxels are not either.
* D counts the strict voxels inside the envelope measured from the rails only
  (`Candidates.in_rail`), so it does not change with `gauge.axis_union` (§1m).
* A blob kept only by D (`Cluster.wall_kept`) that another rule demotes, such as the ride's column
  row, is no longer a duplicate source for a low cluster and does not take a hanging cluster over.
  Before, a low STOP beside it could be lost.

`tests/test_near_escalation.py` +4 for them, +1 for the interaction with the rail-start rule
(§1n).

### 1m. P3 items of 26.09: the envelope also from the sensor axis (judge A, action 7)

[organizers' synthetic, real and ray-cast, measured 26.09; P3.] The organizers place their
edge-test objects from the sensor's X axis. The detector measures the envelope from the rails
(ALGORITHM §3.1, §6). In set O the rails run at −0.24° to the sensor axis (median of the frames
with a rail pair). The rail axis is 0.05 m right of the sensor axis at 5 m, 0.14 m at 25 m and
0.23 m at 45 m. Four of the six recordings show the same rig yaw, −0.23 … −0.36°.

*Measured* on `bd67fb0`, per edge object and frame. "Inside" means that at least one of the
object's own points lies in the 2.1 × 3.0 m envelope.

| object (organizers' intent) | frames | inside, from the rails | inside, from the sensor axis | decision |
|---|---|---|---|---|
| #4 0.3 m cube at the edge (inside) | 83 | 16 | 74 | CAUTION 25 (`floating`), GO 58 |
| #5 0.3 m cube just outside | 112 | 98 | **0** | CAUTION 24, GO 88 |
| #6 2 × 2 m box at the edge (inside) | 125 | 8 | 93 | GO in all 125 |
| #7 2 × 2 m box outside | 104 | 58 | **0** | STOP 6 (142 m), CAUTION 43 |

**From the sensor axis, the four tests match the organizers' intent at every range. From the rails
they do not.** Within 50 m:
* #4's centre is 1.01 m from the sensor axis (1.15 m from the rails), so it straddles the edge.
* #5's inner face is 1.13–1.27 m from the sensor axis.
* #6's face starts 0.96 m from the sensor axis at 30 m (1.11 m from the rails).

Two other rules decide #4 and #6:
* #4 is demoted as `floating` whatever the reference. Its outermost point is 1.04–1.23 m from the
  sensor axis, beyond `floating_free_max_dy` 0.95 m.
* #6's part inside the advisory corridor is a strip ~2 m tall, 1.2–1.3 m from the rails. The wall
  rule drops it (`wall_min_height` 1.9, `wall_min_lateral` 1.2).

*Pre-registered* at 07:10 UTC, before any candidate code; addendum at 07:25 UTC
([`p3_edge_axis_2026-09-26.json`](evidence/results/p3_edge_axis_2026-09-26.json)). Every candidate
acts only under four conditions (`gauge.axis_union_*`):
* the rail pair is locked;
* the track is straight (|curvature| ≤ 2e-4 /m);
* the point is within 50 m;
* the two axes are at most 0.30 m apart there.

The candidates:
* A (`gauge.axis_union` 1): inside if inside either envelope; nothing else changes.
* B (2): the corridor coordinate re-measured on the side where the sensor axis widens the envelope.
* B2 (3, addendum): A, and the shape rules of a corridor cluster read its lateral from the axis
  that places it nearer the centre.

The axis-only envelope was not a candidate: on the other side it gives up to 0.3 m of the space
the train sweeps.

| stage | A | B | B2 |
|---|---|---|---|
| six recordings and set O (gate rows) | PASS | **FAIL**: plank #9 49 → 48 STOP frames | PASS |
| #6 STOP frames (scorer) | 0 → 1 | 0 → 3 | **0 → 7**, first STOP 18.3 m |
| #4, #5, #7, background | unchanged | unchanged | unchanged |
| set F, gentle curves (6 approaches × 3 kinds) | identical | not run | identical |
| full gate | **PASS**: 2 gated rows better, none worse | not run | **FAIL**: ride 187 / 46 / 39 → 189 / 49 / 39 |

* **A's single frame is weak evidence.** Three gauge hits of the box (frames 572–574, measured
  from the sensor axis) confirm a track in frame 576. The track is reported there on an edge-line
  fragment 2.4 m in front of the box: 11.87 m against 14.3 m, on the safe side. The box itself is
  still dropped as a wall in frames 575–579.
* **B's map compresses the whole widened side**, so it changes centre objects: the plank loses a
  STOP frame and the box above the track loses `elevated`.
* **B2 turns #6 into a real detection**: a STOP track on the box from frame 568 (30.65 m) to the
  end, 16 frames. The scorer credits 7 of them: it needs the detection within 1 m of the label's
  centre, which is 2.2–2.4 m off the rails, while the detection is the box's strip at 1.2–1.3 m.
  B2 costs 3 ride events, 30–40 m ahead on straight track: a 3.6 m long, 0.4 m tall object 0.93 m
  from the rails, a rail-level track, and a thin fixture 1.34 m from the rails (0.47 × 0.10 ×
  0.17 m). Edge-line fragments 1.39 m from the rails also alarm in more frames. From the rails the
  shape rules keep these advisory or drop them; from the sensor axis they pass.

The union applies in 4 745 of the ride's 11 271 frames, to the full 50 m in 3 782.

**A passed the pre-registered rule and was shipped on the branch; the safety review of 26.09
blocked it: tried, not shipped (`gauge.axis_union` 0).** A is the only candidate that passes every
stage. It gains set O #6 one STOP frame (the weak one above) and changes nothing else on the six
recordings, set O, the ride and set F (338 of 801 inside STOP frames, 7 of 8 objects; the 7th is
that single frame). The branch's claim that the union only ever adds strict membership, so it
cannot remove a STOP, is **false**. The oversize split (`cluster.oversize_split_max_length`, §1h)
takes the strict points of a cluster longer than 8 m as the object and drops the cluster when that
part is longer than 3 m. The union adds the strict points of a long structure 1.05 to 1.05 + c m
from the rails (a hose, cable or pipe along the edge). The part then grows past 3 m, and an
obstacle touching the structure inside the envelope is dropped with it. The reviewer reproduced it
on the ray-cast tunnel [synthetic, 26.09]:
* c 0.25 m, a 0.5 m box 0.85 m from the rails touching a 30 m line 1.20 m from them, 32 → 8 m:
  19 → 6 STOP frames;
* c 0.15 m, a person touching a 40 m line 1.12 m from the rails: 16 → 11.

Fixed in the code anyway, for a later decision: the corridor keeps the rails-only strict mask
beside the union (`Candidates.in_rail`, also through the accumulation buffer). An oversize cluster
whose union part fails the split falls back to its rails-only part: the first case 19 → 19 STOP
frames with the union on (`tests/test_edge_axis.py`). The wall keep of §1l counts the rails-only
strict voxels, so it does not change with the union either. The union was never measured with
these fixes in a full gate; it stays off, with B and B2.

Tests 500 → 508 (`tests/test_edge_axis.py`), +2 with the review (the edge-line scene above, the
rails-only mask through the accumulation buffer). They include a ray-cast straight track with the
sensor yawed 0.5° against the rails: a box at 30 m, 0.2 m inside the envelope measured from the
sensor axis, STOPs with A and is advisory from the rails alone. A 2 × 2 × 2.3 m box at the same
edge (#6's shape) is still dropped as a wall with A and STOPs only with B2.

**For the organizers' Q1** ([`QUESTIONS.md`](QUESTIONS.md)):
* Measured from the sensor axis, the edge tests are what the organizers intended. #4 and #6 are
  inside in 74 of 83 and 93 of 125 frames; #5 and #7 in none.
* Measured from the rails, #4 is inside in 16 frames, #6 in 8, #5 in 98 and #7 in 58.
* The train sweeps the rail envelope. The rails run at ~0.25° to the sensor axis on most
  recordings: 0.1 m apart at 25 m, 0.2 m at 50 m, 0.4 m at 100 m.
* The union of both envelopes within 50 m on straight track (A) was tried on 26.09 and is off
  after the safety review: the detector keeps the rails.
* Whatever the answer, a sustained STOP on #6 needs B2's shape rule (3 ride events) and one on #4
  a different `floating` exemption (not tried).

### 1n. The P3 items of 26.09 combined; gate baseline `_ride_p3c`

[real, organizers' synthetic and synthetic, measured 26.09; P3 integrator.] Branch
`wf14/integrate-p3` from the working-branch head `00143b0`: `wf14/rail-start` (§1k),
`wf14/near-escalation` (§1l) and `wf14/edge-axis` (§1m) merged with `--no-ff`, then the fixes of
their safety review (`ed03bc2`). Record:
[`p3_integration_2026-09-26.json`](evidence/results/p3_integration_2026-09-26.json).

*Interaction of the rules.*
* Rail start and near escalation: the first marks only `low` clusters and withholds only a track
  whose last hit is such a cluster; the second counts only corridor clusters. In a frame where the
  first applies, the second's last 5 hits are broken anyway, and the first keeps no state. A track
  escalated to a STOP whose next hit is a rail-line cluster under 4 m behaves the same with the
  rail-start rule on and off (`tests/test_near_escalation.py`).
* Rail start and the wall keep: the wall keep spares only corridor clusters taller than 1.9 m and
  more than 1.2 m off the axis; the rail-start rule reads low clusters and the frame's points.
  No shared input.
* The union and the wall keep did interact: the wall keep counted `in_gauge`, so with the union
  it kept a tall cluster with ≥ 10 voxels inside the envelope measured from the sensor axis (the
  ray-cast #6 shape STOPped with both on, and with neither alone). Since the review the wall keep
  counts the rails' envelope only, and the union is off.

*The gate* (`scripts/regression_gate.py --cache /data/cache --jobs 1 --baseline
results/regression_baseline_2026-09-25_ride_p3b.json`, 857 s): **PASS**, 7 gated rows better,
none worse ([JSON](evidence/results/regression_gate_2026-09-26_p3_integrated.json)).

| row | `_p3b` | combined | from |
|---|---|---|---|
| ride: alarm frames / events / STOP episodes | 187 / 46 / 39 | **183 / 45 / 38** | rail start (§1k) |
| set O #8, box at the envelope top: STOP frames, held from | 12, — | **22, 23.9 m** | near escalation A (§1l) |
| set O #6, edge box: STOP frames, first STOP | 0, none | **6, 10.3 m** | wall keep D (§1l) |
| set O #4, edge cube: STOP frames, first STOP | 0, none | **2, 5.2 m** | near escalation A (§1l) |
| set O: inside STOP frames, objects with a STOP | 337, 6 of 8 | **355, 8 of 8** | |

Everything else is identical: the five bags 58 / 13 / 16; `doubleT_obstacle` 58 of 61, 128 of
185, 125 of 126 from frame 75, first alarm frame 11; set F straight; set O #5, #7 and the
background. The combination is exactly the sum of the two shipped items' own gates: rail start
moves only the ride rows, the near escalation only the set O rows. The union's single frame on #6
(§1m) is gone with the union off; D gives #6 its 6 frames either way. The review's fixes changed
no gated or recorded value: the same gate on `a88e6e9` (rail start and near escalation merged,
before the review) gave every value the same; only the latency-driven health warning counts of the
ride and `doubleT_platform` differ (never gated).

*The union in the combination* (set O replays, not a full gate): with `gauge.axis_union` 1 on top,
#4 gets 2 → 9 STOP frames, first STOP 5.2 → 18.2 m (its strict voxels from the sensor axis reach
the escalation's 10), and inside STOP frames 355 → 362. #6, #8 and the other objects are
unchanged. The same on `e2a5327` (all four on, before the review) and on `ed03bc2` with `--set
gauge.axis_union=1`. It stays off (§1m).

*Checks.* Tests 500 → 555 (rail start +27, near escalation +12, edge axis +8, the combination +1,
the review +7), the same on the native kernels and with `RESENSE_NATIVE=0`; `web/demo` 13. With
every new flag off (`lowobj.rail_start_within`, `tracking.near_escalate_voxels`,
`cluster.wall_keep_gauge_voxels` and `gauge.axis_union` 0) the output is identical to `bd67fb0`
(`scripts/output_fingerprint.py --cache /data/cache --jobs 1`: 2 930 frames, 0 differ).

*New gate baseline:*
[`regression_baseline_2026-09-26_ride_p3c.json`](evidence/results/regression_baseline_2026-09-26_ride_p3c.json),
this run without its gate block. `ls docs/evidence/results/regression_baseline_*_ride*.json |
LC_ALL=C sort | tail -n 1` picks it (VM_GUIDE §4.4). The same run against it
(`--from-json`): PASS, every row the same.

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
  bed 2.5–8 m ahead reads as an obstacle — the STOP is right, the reported 3.0 m is not. Fixed
  25.09 (§1h): the bed is fitted in front of the shadow or held; every STOP on #1 reports the box.
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
reads the 4.5 GB 360° bag. `scripts/bench_8core.sh` through the VM kit of 25.09 (removed the same
day; now [`VM_GUIDE.md`](VM_GUIDE.md) §4.3), image from the layer cache; raw: [`evidence/bench_2026-09-25/`](evidence/bench_2026-09-25/) (`summary.txt`).

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
  its 2 known frames at 128.3–130.2 m (§0). Not the catch-up at the start: the same column, see
  the replay below. One native run also had a frame at 53.0 m: the trackside start-frame case of §0.

**`roundT_doubleT` replayed offline [measured 25.09].** `scripts/replay_node_frames.py` feeds the
frames a ROS run processed (the header stamps of its `status.jsonl`; here `946692931.6334 + 0.1·i`
s is cache frame `i`) to the detector as the node does. The 10 captures of this recording on the VM
(first frame 2–41, 192–235 of 252 processed) all alarm on frames 241–243 (114.93 / 112.99 /
111.04 m); 3 add frame 159 (53.0 m), one frame 234 (128.27 m). The same sequences from the cache,
with `7290873`'s parameters, the current ones or `3bf6324`'s `floating_long_min_bottom` 1.6–2.0
(the same decisions frame by frame: the long rule needs a cluster over 3 m long), give 1–2 frames
at 128.3–130.2 m (233–234; one sequence also 4 at 49–54 m), as every frame from frame 0 does
(`resense run --npy`: 2 frames, 1 event). Replay and node part on the first processed frame (142
vs 145 corridor points), before any state: the cache's 1 cm coordinates, not the frame spacing;
±5 mm of noise on them (`--dither-mm 5`, 10 seeds, every frame) gives 0–10 alarm frames, the
node's three to the centimetre in 4. The object: a column 0.3–1.1 m off the far axis, an advisory
track from 149 to 101 m (frames 223–248), mostly 0.1–0.4 m along the track, its top at the envelope
top (2.7–3.0 m), its bottom at 0.1–1.7 m. A frame showing more than 2.2 m of it (`column_min_height`)
demotes it as a `column`; one showing 1.6–2.2 m matches no signature and puts it in the gauge; 6
such hits of the last 10 (`zone_min_fraction` 0.6) make it an obstacle. **`tracking.column_hold:
2`**: a track demoted as a column in 2 of its last 10 hits stays advisory. Chosen by a rule
registered before the runs
([`column_hold_2026-09-25.json`](evidence/results/column_hold_2026-09-25.json), 12:18 UTC): of 3, 2,
1 the highest with (a) at most 2 alarm frames left in each of the 10 captures, counted from the
column hits in their windows, and (b) the gate against the `_ride` baseline passing. 3: (a) at
most 2 left (frames 159 and 234 of `ct_stock`), (b) FAIL, ride STOP episodes 39 → 40. **2**: (a)
at most 1 left (frame 159, 3 of 10; 241–243 have 4 column hits in the window, 234 has 2), (b)
PASS, 7 gated rows better: `roundT_doubleT` 2 / 1 / 1 → 0 / 0 / 0, five bags 60 / 14 / 17 →
58 / 13 / 16 alarm frames / events / STOP episodes, ride 197 / 46 / 39 → 187 / 46 / 39, set F
false detections 56 → 35; `doubleT_obstacle`, set O and set F detections identical. 1 was not
run under the rule (measured before it: five bags 57 / 13 / 15, ride 176 / 45 / 37,
[JSON](evidence/results/regression_gate_2026-09-25_column_hold.json)). With 2, from the cache no
alarm on the column on any of the 11 sequences or 20 noise runs. The cost (ray-cast tunnel, 60 m,
`tests/test_late_candidates.py`): a person who stood in front of a column for 2 or more frames (one
narrow `column` cluster) and steps onto the axis gets the STOP 8 frames after the step instead of 4
(1 would hold it back after a single such frame, to frame 9); a person beside a column is one
cluster, never a column, and a STOP on its usual frame at 40–80 m. New gate baseline
[`regression_baseline_2026-09-25_ride_column.json`](evidence/results/regression_baseline_2026-09-25_ride_column.json)
(`d117c8c`). Left: the trackside device at 38–54 m (§0), 3 and 6 frames on 2 of the 10 noise runs.

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

C8 is closed on this run (the captain, 25.09): a machine with half the i7-9700E's cores meets the
latency criterion, and its drops were no losses of the node (above); no 8-core run is needed.

**Confirmation re-run (25.09 afternoon, a second team VM, code `76bf24e`)** after the fixes above
([`VM_GUIDE.md`](VM_GUIDE.md) §4.0 / §4.3; same VM type: Xeon Icelake 2.0 GHz, 8 vCPU = 4 physical
cores, 15.6 GiB, CPU steal 0.0 %; bags from a RAM tmpfs as before; raw:
[`evidence/bench_2026-09-25_2/`](evidence/bench_2026-09-25_2/)):

| run (Docker chain, rate 1.0) | kernels | frames processed | fps | decode + detect mean / p95 / max | dropped input frames | check |
|---|---|---|---|---|---|---|
| `dry_run.sh doubleT_obstacle` | native | 147 / 201 | 9.8 | 60 / 73 / 84 ms | 51, 43 of them the catch-up's; after +7.7 s only the 4 frames missing from the recording, 0 of its messages not processed | **PASS** |
| same | numpy | 120 / 201 | 8.3 | 104 / 119 / 162 ms | 79, 69 of them the catch-up's; 12 of the recording's messages not processed after +10.6 s | FAIL: p95, drops |
| `dry_run.sh roundT_doubleT --expect-clear --max-alarm-frames 2` | native | 234 / 252 | 10.0 | 38 / 48 / 53 ms | 13 (0) | **PASS** (0 alarm frames) |
| same | numpy | 232 / 252 | 10.0 | 67 / 79 / 83 ms | 16 (0) | PASS |
| `console_test.sh`, image's DDS / stock Fast DDS player | native | 382 / 384 of 453 | 10.0 | 47 / 68–69 / 87–115 ms | — | PASS / PASS |

Offline node path at 360° 45.1 ms native, 90.9 ms numpy (×2.02); `resense bench` stages 26.5 / 64.2
ms. The native path meets every criterion on 4 physical cores; numpy stays short at 360°, as on the
first run.

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
deployment).** The VM kit's `dryrun` and `offline` steps (kit removed 25.09; now
[`VM_GUIDE.md`](VM_GUIDE.md) §4.1 / §5), code `7290873`, on the VM of §3a
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

**Confirmation re-run with the original bags, 25.09 afternoon (a second team VM, code `76bf24e`).**
[`VM_GUIDE.md`](VM_GUIDE.md) §4.0 as written: §2 data on the VM (the ride's cache 221 of 221 split
files), §4.1 with the `--no-cache` build as the VM's first build, §4.2, §4.3 (§3a), §4.4, §4.5, §5;
the VM of §3a's re-run, the bags from a RAM tmpfs; raw:
[`evidence/dry_run_2026-09-25_2/`](evidence/dry_run_2026-09-25_2/),
[`evidence/offline_2026-09-25_2/`](evidence/offline_2026-09-25_2/),
[`evidence/gate_2026-09-25_2/`](evidence/gate_2026-09-25_2/),
[`evidence/export_2026-09-25_2/`](evidence/export_2026-09-25_2/). **Both fixes hold:**
`doubleT_obstacle` **PASS** (person 55.5–56.5 m, first `STOP` +0.4 s, p95 70 ms, 10.07 fps; the node
log `dropped 46 (39 skipped by the catch-up)`; back on the newest frame at +6.9 s, then the 4 frames
missing from the recording itself and 0 of its messages not processed); `roundT_doubleT` **PASS** with
0 alarm frames, and `replay_node_frames.py` on the node's 234 processed frames gives the same (0 and
0). Offline from the new archive (`resense-image-1.0.0.tar.gz`, 475 515 293 bytes, loaded after every
`resense` image was deleted; outbound blocked on IPv4 and IPv6, no host allowed, a new SSH login
worked during the block, restored after 4 min): both dry runs **PASS** again (55.6–56.5 m, p95 73 ms,
catch-up end +7.7 s, 4 missing frames; 0 alarm frames). The regression gate with the ride against
`regression_baseline_2026-09-25_ride_column.json` **PASS**: all 105 gated rows the same on this second
machine (ride 187 / 46 / 39), only latency information rows differ. The console: `console_test.sh`
with a stock Fast DDS player in Docker **PASS**; the host console with `rmw_cyclonedds_cpp` at
`rmem_max` 32 MiB (`rmem_default` left at 212992) **PASS** (144 `STOP`, no rmem WARN). The host
console labelled "stock Fast DDS" failed at Ubuntu's `rmem_max` 212992 in 5 of 5 runs (0–1 of the
201 360° clouds) and passed at 32 MiB, and so did the offline README jury console (6 of 201), but
**corrected 25.09 evening: those players were CycloneDDS.** The host's ROS 2 was installed as
VM_GUIDE §1 then said (`ros-humble-ros-base` with `ros-humble-rmw-cyclonedds-cpp` in one apt call;
`ros-humble-rmw-implementation` takes either RMW), so no Fast DDS RMW was on the host and a player
with `RMW_IMPLEMENTATION` unset loaded `rmw_cyclonedds_cpp`
([`diag_host_fastdds/README.txt`](evidence/dry_run_2026-09-25_2/diag_host_fastdds/README.txt)): the
runs repeat the CycloneDDS result above, not a Fast DDS one.

**Transport fixes on a third team VM (25.09 evening, code `d4b396e`: README jury step 0 and the
opt-in `RESENSE_DDS=shm` of `be39362`).** Same VM type, the image built by `dry_run.sh --no-cache` as
its first build, the original bags from a RAM tmpfs; the player's RMW checked in `/proc/<pid>/maps`
(raw: [`evidence/dry_run_2026-09-25_3/`](evidence/dry_run_2026-09-25_3/), its `README.txt`). The
host first had the same install and again ran CycloneDDS; with `ros-humble-rmw-fastrtps-cpp` added,
a **genuine stock Fast DDS player** (`librmw_fastrtps_cpp.so`, `libfastrtps.so.2.6.12`, the image's
version):

| node | host player | `rmem_max` | result |
|---|---|---|---|
| UDP (default) | stock Fast DDS | 212992 | **PASS, 2 of 2** (152 / 150 `STOP`, 55.5–56.6 m) |
| UDP | stock Fast DDS, README steps 0–5 | 32 MiB | PASS (153 `STOP`) |
| `RESENSE_DDS=shm` | stock Fast DDS | 212992 | **PASS, 2 of 2** (148 / 146 `STOP`); the player maps the node's `root 666 /dev/shm/fastrtps_port7411`: the clouds go over shared memory |
| shm | CycloneDDS | 212992 | FAIL: the 360° recording never arrives (CycloneDDS cannot use Fast DDS shared memory) |
| shm | CycloneDDS | 32 MiB | PASS (153 `STOP`); no Fast DDS port mapped |
| UDP | CycloneDDS, README steps 0–5 | 32 MiB | PASS (152 `STOP`) |
| shm | stock Fast DDS in Docker (`NODE_DDS=shm console_test.sh`) | 212992 | PASS over shared memory |

`dry_run.sh` on both bags (UDP, in the container): PASS and PASS (55.6–56.5 m, p95 65 ms, 4 drops
after the catch-up = the recording's own missing frames; 0 alarm frames). **Reading:** a stock Fast
DDS player reaches the node at Ubuntu's default buffer over UDP (the first and this third VM) and in
shm mode; a CycloneDDS player needs `rmem_max` 32 MiB in either mode. README step 0 covers
CycloneDDS and costs Fast DDS nothing; the shm mode passes [`VM_GUIDE.md`](VM_GUIDE.md) §4.6, but no
Fast DDS failure over UDP is left for it to fix, so it stays opt-in until the captain decides.

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
- **5 Hz and a ±3° re-mount** (SCORECARD #13; P3; §1g, §1i): the causes fixed on 25.09 (five
  bags false events 5 Hz 13 → 10, roll 16 → 11, pitch 17 → 16; `roundT_doubleT` 3 / 2 / 1 →
  0 / 1 / 0; the same on the combined round-2 defaults); open: pitch above the as-recorded 13 (marginal clusters in `doubleT_platform` and
  `squareT_platform_squareT_switch`) and one roll alarm on the far column of `roundT_doubleT`;
- ~~**the `floating` signature on the organizers' hanging cube** (P3; §2e)~~ done 25.09, round 2
  (§1i): `cluster.floating_free_max_size` 0.5 m, #2 a STOP from 52.5 m (34.0 m), every recording
  and the ride identical; #4 (edge, Q1) and #8 (`elevated`, Q2) wait on the organizers;
- ~~**thin hanging objects** (P3, P4; §2e): a rule for thin clusters near the axis linked to
  points above the envelope, measured on set O, the empty bags and the ride~~ shipped 25.09
  (§1i, `cluster.hanging_enabled`): the organizers' 5 cm object STOPs from 30.1 m, no gate row
  worse; the rail-lock guard (`hanging_needs_rails`, round 2) removes the station column tops it
  took on the ride without a rail pair. Left open: a thin object hanging where the rails are not
  found (stations, switch caverns) is not looked for;
- **conservative `clear_distance`** (P3; §1i, 25.09): `health.clear_cap` (R1) cuts the set O
  overclaim from 172 to 82 object-frames with no decision changed; it failed the pre-registered
  median limit on the five obstacle-free recordings (−5.5 % against −5 %: at the platform the train
  stands capped at the platform-end structures) and was shipped on by the captain's delegate
  anyway (25.09). Open: a cap for objects that form no cluster (far 0.3 m cubes);
- ~~**the rail shadow of a large near object** (P3; §2e): a 2 × 2 m box 10–20 m ahead hides the
  rails, the rail-height fit drifts by ~0.5 m and a wrong 3.0 m distance is reported~~ shipped
  25.09 (§1h): set O #1 wrong-distance STOP frames 12 → 0, gate PASS with the ride; a shadow that
  starts beyond 30 m is not handled;
- ~~**the near-bed path with the current gates** (`537e220` + `7df1796`; P3; §1e): the ride and set F
  on the bed before any change of its default~~ dropped 25.09: a bed object below the rail head is
  not an obstacle (organizers' answer to Q3, [`organizers/answers.md`](organizers/answers.md) §8),
  the path stays off;
- ~~**the far-rail check** (P3; §1e, §1f): never fires on the six recordings and set O (25.09);
  only the ride is left~~ measured on the ride 25.09 (§1h): identical frame by frame there too, the flag stays off;
- ~~**an obstacle far ahead extends the bed fit** (P3; §2d, ALGORITHM §6)~~ tried 25.09, not
  shipped (§1h): dropping a far bin that is an object's foot (narrow, with its face standing on
  it; `track.floor_far_min_width`, off) removes the mechanism's 6 set F false detections, but other
  fixtures 40–55 m beyond the object confirm instead (set F 35 → 36–43) and a set O row gets worse;
- **the 82.9 m platform end** (P3; §1f, §1h): 10 of the 15 STOP episodes at the platform come from
  the axis being ~0.8 m off at 83 m (a platform-side boundary joined to the hall end, 2.5–4e-4 /m);
  a far-support rule for the wall sides was tried in two pre-registered rounds on 25.09 and not
  shipped (platform episodes 15 → 1–10, but set O, `doubleT_platform` or the ride move every
  time); next: break the rails–walls feedback with a joint fit of tangent and curvature, after the
  freeze. Lead (25.09, §1h): dropping station structure feet beyond 90 m from the bed fit
  (`track.floor_far_min_width` 1.1) takes the platform recording's STOP episodes 15 → 9;
- ~~**bed correction from the side-structure base** (P3): use `z_base(X) − offset_ref` as
  `z_floor(X)` beyond the fit where the side base is continuous, then re-measure the far bins
  and the 147.5 m switch structures~~ measured 25.09 (§1h): the side base does not reach 147.5 m
  at the switch and rises 1.5–2× faster than the vault drift on straight track (+1.6–1.9 m at
  150 m), so it is no bed height; the switch parts are an axis error (a hall wall seen to 72–92 m
  sets the curvature). `far_min_height` 0.8–1.0 and the both-boundaries rule
  (`cluster.far_axis_both_sides` 1, 2) tried, not shipped; mode 2 passes the gate (ride 46 → 42
  events, 39 → 33 STOP episodes) but costs 1.9 m of a person's median first confirmation on
  gentle curves; next: weigh each boundary by its observed range in the axis model (with the
  82.9 m platform end above);
- **bed-trough centre vs wall axis** at stations (design in v0.4, not implemented): a second
  lateral axis where the walls are far; at the `squareT_platform_squareT_switch` stop only 7–26
  bed-height returns per 5 m slab and frame are left beyond 55 m, too few for the 82.9 m platform
  end (§1h);
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
