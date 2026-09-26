# Criteria Scorecard

> **Purpose:** the judgement of ReSense against the eight criteria of spec §8: the current one of
> 26.09 (§0) and the first of 24.09 (§1–§8, kept as the record): score per criterion, the evidence
> behind it, the risks on the hidden data and the fastest points to gain.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN, summary RU
> **Last verified:** 2026-09-26 against `867bb8a` (judged on `052e7c5` / `867bb8a`; the detector is
> the same in both) · **Status:** current (§0); §1–§8 dated record of 24.09

**Кратко.** Итог по восьми критериям ТЗ §8 на 24.09 — **60 / 100** (два независимых судьи: 63 и
58,5). Сильная сторона — инженерия (8.5–8.7): 235 тестов, CI с ROS в Docker, результаты
воспроизводятся кадр в кадр, гипотезы и отказы записаны с цифрами. Слабая — 8.1 и 8.2 на
синтетических препятствиях организаторов: STOP получают 5 из 8 объектов в габарите, дальше ~101 м
STOP нет, кубы 0,3 м — только с 34–43 м, висящий объект 5 см пропущен. Быстрее всего баллы дают
зелёный `main`, ответы организаторов, README, слайды и правило коротких сигнатур (§6). Что
изменилось после оценки и на какие критерии это должно повлиять (без переоценки) — §8.

## 0. Re-judgement of 26.09 (current): 65 / 100

**Кратко.** Повторная независимая оценка 26.09 — **65 / 100** (судьи: 66 и 65; было 60). Выросли
8.1 (6 из 8 объектов организаторов со STOP вместо 5, висящий объект 5 см — STOP с 30,1 м), 8.3
(C++-ядра, 10 кадр/с через ROS на 4 ядрах), 8.4 (5 Гц), 8.5–8.7 (зелёный CI, 486 тестов, шлюз
регрессий, отказы с цифрами). Не выросли 8.2 (дальше ~101 м STOP нет) и 8.8 (колода и ролик ждут
заморозки, слайды команды не заполнены).

Two independent judges re-scored the branch head on 26.09 (A: the jury's view of the hidden data
and the stand; B: a sceptic checking claims against the raw evidence), without trusting this
file, CAPTAIN or the README. Both re-ran set O (`resense run --npy` + `score_fake_objects.py`)
and `doubleT_obstacle` at head and matched the gate baseline `_ride_p3b` exactly; both ran the
486 tests. Final = the mean, rounded down where only one judge measured a hold-down.

| § | criterion | 24.09 | judge A | judge B | **26.09** | one-line reason |
|---|---|---:|---:|---:|---:|---|
| 8.1 | Works | 13 | 14.5 | 14.5 | **14.5 / 25** | 6 of 8 organizers' objects get a STOP (5 held; the box at the envelope top only 12 of 124 frames); the 5 cm hanging object a STOP from 30.1 m; the edge box reads GO; ride false STOPs 3.5 per km (in-sample) |
| 8.2 | Range | 7 | 7.5 | 7.5 | **7.5 / 15** | 1 STOP frame beyond 100 m on the organizers' objects; 0.3 m cubes at 43–53 m; the injected person at 148–154 m is the team's own |
| 8.3 | Speed | 6 | 7.5 | 7 | **7 / 10** | C++ kernels halve the detector; 360° through ROS at 9.8–10 fps, p95 70–73 ms on 4 physical cores; over-budget latency turns the decision into CAUTION on a loaded machine; never on the i7-9700E |
| 8.4 | Generalisation | 8.5 | 9.5 | 8.5 | **9 / 15** | geometry, no map; 5 Hz fixed (13 → 10 events); 264 tuned keys (54 added on 25–26.09 around set O objects), "pre-registration" honest but in-sample; tilt ±3° still 14–17 events |
| 8.5 | Technical quality | 7 | 7.5 | 7.5 | **7.5 / 10** | clean staged code, 486 tests, 6-job CI, a real regression gate; `main` 169 commits behind, review waived, ~7 800–8 800 lines of docs with stale counts |
| 8.6 | Ease of launch | 7.5 | 8 | 8.5 | **8 / 10** | jury commands first, `docker load` offline proven in CI and on 3 clean VMs; the final archive does not exist yet; one VM's offline jury console failed (CycloneDDS without step 0) |
| 8.7 | Team approach | 8 | 8.5 | 8.5 | **8.5 / 10** | tried-and-rejected record with raw JSON, ship rules, safety reviews; dense; some addenda written after the runs they react to |
| 8.8 | Pitch | 3 | 3 | 3 | **3 / 5** | deck and video stale (5 of 8, 289 tests, "hanging missed", `docker build`, «релиз v1.0.0»), team slides `<…>`, no rehearsal |
| | **Total** | **60** | **66** | **65** | **65 / 100** | |

**Claims the judges found wrong or overstated** (to fix in the consistency pass after the freeze,
CAPTAIN action 19):
- "6 of 8 with a STOP" is a count; 5 are held (the box at the envelope top: 12 of 124 frames).
- README: hanging objects are obstacles "whatever their shape" — the hanging stage covers groups
  ≤ 0.5 m, within 0.8 m of the axis, ≤ 60 m, with a rail lock only; "~200 m" for tall objects —
  set O has no STOP beyond 101 m.
- "The node lost no frames" — none lost in transport, but 39–53 are skipped by the start-up
  catch-up by design (the drop check was redefined after the run that failed on drops).
- EXPERIMENTS §1g "0 of 706 alarm frames" in the held-out suffix of `cloud_with_fake_obj`: on the
  cached frames frame 1131 is a STOP at 140.7 m (one of set O's 3 background alarm frames, the same
  in every baseline since 25.09; the §1g figure came from bag playback).
- "3.5 per km" is in-sample (the ride decided the rules); CAUTION is on 41–48 % of empty-ride
  frames.
- Stale: README header (`79109f5`, v0.6.3), CAPTAIN C16 (`main` green at `5de0844`; `main` is at
  the revert `6962519`), C17 (396 tests; 486 now).

**Top risks on the hidden data:** objects at the envelope edge or top (advisory or GO: the
organizers place from the sensor axis, ReSense measures from the rails); nothing beyond ~100 m on
their objects; false STOPs at stations and at the start of a fresh bag (a 2.9–3.1 m STOP in the
first 1.5 s of one ride chunk while calibration was pending); CAUTION on a loaded stand; delivery
(no archive from the final commit yet, `main` behind).

**Actions after the judgement** (owner; being done on 26.09 unless noted):
- before the freeze (26.09 20:00): start-up STOPs of a fresh bag measured on all 221 ride starts
  and fixed if common (P3 / P4); latency kept out of the decision, CAUTION explained in the README
  (P1);
- after the freeze: the consistency pass with the corrections above (P4 or agent, by 27.09 20:00);
  the deck and the video rebuilt from `_ride_p3b`, team slides, two rehearsals (P2 + captain);
  the archive from the frozen commit, an offline dry run, PR #12 merged or the commit hash named
  in the upload (captain);
- not before the freeze (risky, or waiting on the organizers' Q1 / Q2): the envelope from the
  sensor axis for edge objects; a far-field rule for the high wide box.

## 1. How it was judged

Two independent judges scored the same checkout, `4b5786b` (`main` on the evening of 24.09), with
different lenses and without reading any earlier scorecard:

* **Judge A, execution lens** (total 63): scores only what it ran itself; every team claim is
  re-run or marked unverified.
* **Judge B, demo-day lens** (total 58.5): an adversarial jury member and metro engineer; adds a
  stress test on real frames, an audit of `/resense/clear_distance` and the deck as shipped.

**Rubric.** The spec's eight criteria with maxima fixed before scoring. The organizers publish no
weights, so the maxima encode the spec's own emphasis: 8.1 is «основной критерий» (25); 8.2 gets
«особое внимание» (15); 8.4 is where the final check on unseen data lands (15); 8.3, 8.5, 8.6 and
8.7 get 10 each (compute is only a tie-breaker, [Q&A](organizers/QA_session.md) fact 19); 8.8 has
«меньший вес, чем реальные технические результаты» (5). The final score is the mean of the two
judges, rounded down to the nearest 0.5 (§2).

Evidence tags: **[measured 24.09]** = a judge ran it; **[team record, re-checked]** = a team
figure a judge reproduced or matched against committed evidence or the GitHub API; **[team
record, unverified]** = a team figure no judge could check. Runs were on the team's 4-vCPU dev VM,
shared with other jobs, so timings are noisy.

| check | result | tag |
|---|---|---|
| `python -m pytest -q -p no:cacheprovider` (A with `RESENSE_REQUIRE_SYNTHETIC=1`, open3d present); `ruff check .`; `scripts/sync_params.sh --check` | 235 passed, 0 skipped (104 s / 115 s); ruff clean; parameter files in sync | measured 24.09 |
| `scripts/eval_real.py --cache /data/cache --bags <six> --jobs 2` | five empty bags (2 287 frames, 229 s): 107 alarm frames / 20 events / 27 STOP episodes; `doubleT_obstacle`: 185/246 labelled frames, first alarm frame 11, distance error ≤ 0.23 m; every field equals the team's re-measure of 24.09 (`evidence/results/experiments_2026-09-24_remeasure.json`) | team record, re-checked |
| `resense run --npy …/cloud_with_fake_obj` + `scripts/score_fake_objects.py` | the per-object grade of §4, value for value as in [`P4_AUDIT.md`](P4_AUDIT.md) | team record, re-checked |
| `OMP_NUM_THREADS=1 resense bench --npy …` (load average ~3) | 120° `roundT_doubleT`: 63.9 ms mean, p95 81.6 ms; 360° `doubleT_obstacle`: 81.2 ms mean, p95 101.1 ms (track stage 49.3 ms) | measured 24.09 |
| largest return range, every 5th frame | 207.4–209.5 m on the six real bags; 296.8 m on `cloud_with_fake_obj` (its ray-cast objects only) | measured 24.09 |
| judge B only: stress test on real frames; `clear_distance` audit; deck text from the pptx and video lengths | 5 Hz input, 50 % point dropout, +3° pitch (8.4); 184 object-frames `GO` past an in-envelope object (8.1); placeholders, stale test count, one stationary scene (8.8) | measured 24.09 |
| GitHub Actions API | run 36039303135 on `4b5786b`: all 5 jobs green; run 36044487647 on `537e220`: `pytest` and `docker` red (§7) | team record, re-checked |
| **not run:** Docker / ROS chain (no daemon on the judges' VM) | stood in: the CI `docker` job of run 36039303135 (build, tests in the image, two smoke bags through the node, a uid-1000 player in a second container) and the team's captures of 23.09 ([`evidence/README.md`](evidence/README.md)) | team record, re-checked |
| **not run:** the i7-9700E stand (never available) | stood in: the team's idle bench `bench_v063.txt` of 23.09 | team record, re-checked |
| **not run:** the 20-minute ride (`new_data`, 11 271 frames, not on the VM) | stood in: [`EXPERIMENTS.md`](EXPERIMENTS.md), 47 false events, 3.6 per km | team record, unverified |

## 2. Scores

| § | criterion | score / max | % | one-line reason |
|---|---|---:|---:|---|
| 8.1 | Works | 13 / 25 | 52 | the real person and rail object are found and reproduce exactly; on the organizers' bag only 5 of 8 in-envelope objects get a STOP, the 5 cm hanging object reads `GO`, and a platform bag flaps 25 STOP episodes in 88 s |
| 8.2 | Range | 7 / 15 | 47 | organizers' bag: 2 × 2 m box at 98 m, plank at 82 m, no STOP beyond ~101 m, 0.3 m cubes at 34–43 m; the 148–154 m person comes only from the team's own injector |
| 8.3 | Speed | 6 / 10 | 60 | 64 / 81 ms mean (120° / 360°) on one core under load; 360° through ROS failed the team's own p95 and drop check; never measured on the i7-9700E |
| 8.4 | Generalisation | 8.5 / 15 | 57 | geometry, not appearance, and a clean background on the unseen bag; but signatures fitted to the empty tunnel demote organizer objects, and a 5 Hz input triples the false events |
| 8.5 | Technical quality | 7 / 10 | 70 | readable staged code, 235 tests, 5-job CI with ROS in Docker, reproducible runs; `main` red at `537e220`, version labels disagree, ~5 500 lines of Markdown |
| 8.6 | Ease of launch | 7.5 / 10 | 75 | the organizers' chain exactly, proven in CI with a uid-1000 player; never run on a stand or by a judge, commands buried in the README, 2.6–4 s of `FAULT` at start |
| 8.7 | Team approach | 8 / 10 | 80 | hypotheses, rejected methods and a self-critical audit, all with numbers; headlines still lead with superseded set F figures; organizer questions not confirmed sent |
| 8.8 | Pitch | 3 / 5 | 60 | organizers' template, a strong 55.8 m frame, 4 videos; placeholders, stale test count, range slide on legacy synthetic numbers, no organizers' benchmark, no moving train |
| | **Total** | **60 / 100** | **60** | engineering strong (8.5–8.7); detection and range weak on the organizers' own test objects |

| § | judge A | judge B | final | how the gap was closed |
|---|---:|---:|---:|---|
| 8.1 | 13.5 | 13 | 13 | rounded down: only B measured the `clear_distance` overclaim and the `GO` at 6.7 m on the hanging object |
| 8.2 | 7.5 | 7 | 7 | rounded down: only B checked the injector against the organizers' tool (team's 3 cm cable found at 95 m, organizers' 5 cm object never) |
| 8.3 | 6 | 6 | 6 | agreed |
| 8.4 | 9 | 8 | 8.5 | mean: A's clean background on the unseen bag against B's stress test (5 Hz triples the false events) |
| 8.5 | 7.5 | 6.5 | 7 | mean: same facts (red `main`, versions, doc sprawl); B also weighed the private rclpy calls |
| 8.6 | 8 | 7 | 7.5 | mean: neither could run Docker; A credited the CI proof more, B the buried commands and the missing stand run |
| 8.7 | 8.5 | 8 | 8 | rounded down: only B checked that the headlines quote superseded set F figures and that the questions were not sent |
| 8.8 | 3 | 3 | 3 | agreed |
| | **63** | **58.5** | **60** | |

## 3. Notes by criterion

Evidence from both judges, merged. The actions that would raise each score are ranked once, in §6.

### 8.1 Works: 13 / 25

* **Rests on:** `doubleT_obstacle`, the one real obstacle scene: the crossing person is a STOP in
  58 of 61 in-envelope frames from frame 11 (55.5–56.6 m), the object on the rail in 124 of 126
  frames after the person leaves, distance error ≤ 0.23 m, 0 false STOP [team record, re-checked];
  3 unmatched alarm frames in the organizers' bag, 0 false STOP on both pressure-gate bags
  [measured 24.09].
* **Held down by:**
  * the organizers' bag, the closest thing to the hidden check (Q&A fact 4): a STOP for only 5 of
    8 in-envelope objects, 6 false STOP frames on #7 outside (§4) [measured 24.09];
  * hanging cables are "very important" (Q&A fact 3), yet the 5 cm hanging object reads `GO` at
    6.7–30 m with `clear_distance` 150–170 m; 184 object-frames read `GO` with `clear_distance`
    past an in-envelope object, 89 with points inside the measured envelope [measured 24.09];
  * 25 STOP episodes in 88 s on `squareT_platform_squareT_switch`, train standing, at 82.9 m
    (platform end), ~104 m and 147.5 m (switch) [measured 24.09]: switch glitches do not count
    ([answer of 24.09](organizers/mount_and_switch_qa.md)), platforms do; the ride has 47 false
    events, 3.6 per km [team record, unverified];
  * the 30 × 30 × 10 cm object below the rail head is not detected by default (the opt-in near-bed
    path gave 47 → 667 ride events before `537e220` retuned it [team record, unverified]).
* **To raise before 29.09:** short signatures +0.5 to +1.5, thin-hanging rule +1.5, conservative
  `clear_distance` +1, far platform STOPs +1, organizers' answers +0.5 (§6 rows 2, 6, 10–12).

### 8.2 Range: 7 / 15

* **Rests on:** the organizers' bag: 2 × 2 m box a STOP at 98.0 m (first visible frame), plank
  first at 82.2 m and held from 58.6 m, #8 first at 101.3 m [measured 24.09]; set F, straight
  track: a person first confirmed at a median of 148 m (legacy placement), 154 m anchored from the
  near rails [team record, unverified; matches P4_AUDIT]; an honest physical limit, no real return
  beyond 209.5 m, so 300 m is out of reach [measured 24.09].
* **Held down by:** no STOP beyond ~101 m on the organizers' bag (1 of 236 in-envelope frames), and
  under 100 m is rated "poorly" (Q&A fact 14); 0.3 m objects confirmed only at 34–43 m (2–4
  returns a frame at 60–115 m against a 5-voxel minimum); the only real positive is at 55–57 m
  from a stationary train; curves: sightline 58–86 m, no match beyond 100 m in the paired rerun
  [team record]; the team's injector is optimistic (its 3 cm cable is found at 95 m).
* **To raise before 29.09:** organizers' numbers first on the range slide and README, plus a
  moving-train clip, +0.5 to +1 (judge A: protects more than it raises); far-field rule for tall
  objects with a high bottom +0.5 (§6 rows 5, 14). 0.3 m beyond 45 m stays open: it needs
  accumulation, hence a train speed (judge A: too risky without a full re-run).

### 8.3 Speed: 6 / 10

* **Rests on:** detector 63.9 ms mean / p95 81.6 ms at 120°, 81.2 / 101.1 ms at 360°, one core at
  load average ~3 [measured 24.09], consistent with the team's idle 43.9–63.6 ms mean, p95
  55.8–77.8 ms (`bench_v063.txt`) [team record, re-checked]; the node's catch-up absorbs the
  player's start-up burst [team record]; compute is a tie-breaker (Q&A fact 19).
* **Held down by:** 360° through ROS on the 4-vCPU VM ran at 7–10 fps and failed the team's own
  check (`doubleT_obstacle`: p95 130 ms > 100, 86 dropped frames; 120° passed at 10 fps, p95
  76 ms; `docker_2026-09-23/checks.txt`) [team record, re-checked]; never measured on the
  i7-9700E; the GPU is unused, pure Python on one thread; over-budget latency turns the decision
  into `CAUTION` (97 % of frames at load average 8–11) [measured 24.09]; confirmation takes 0.5 s.
* **To raise before 29.09:** forward-sector crop at 360° (track stage 49 of 81 ms) +1; an 8-core
  analogue bench through ROS (the stand is not available before submission, organizers 25.09),
  latency kept out of the decision, +0.5 to +1.5 (§6 rows 8, 9); parallel, GPU or C++ stages only
  if equivalent frame for frame.

### 8.4 Generalisation: 8.5 / 15

* **Rests on:** tunnel geometry, not object appearance: rails, bed profile and wall curvature every
  frame (`resense/track.py`), then the 2.1 × 3.0 m envelope (`resense/gauge.py`), nothing learned;
  mount auto-calibration, both topic / frame-id pairs, reset per recording, a leave-one-out check
  [team record]; a clean background on the unseen organizers' bag; at 50 % point dropout the
  person is still found from frame 13 [measured 24.09].
* **Held down by:** signatures tuned on negative-only data demote the organizers' positives
  (`floating` #2 and #4, `elevated` #8; `cluster.*` in `configs/default.yaml`); over 200 tuned keys
  fitted on the same 7 recordings, so no false-alarm figure is held out; at 5 Hz `roundT_doubleT`
  goes from 2 frames / 1 event to 6 / 3 and the mount calibration never finalises, +3° pitch gives
  7 / 2 [measured 24.09]; edge objects depend on the reference (sensor axis 0.24° off the rails).
* **To raise before 29.09:** the signature fix of 8.1 +1; 5 Hz and tilt checks plus a held-out
  false-alarm figure +0.5 to +1 (§6 rows 10, 13).

### 8.5 Technical quality: 7 / 10

* **Rests on:** readable staged code (`Detector.process` in `resense/detector.py`: 47 lines, seven
  named stages timed one by one; no ROS in the core); 235 tests with 0 skipped, ruff clean, one
  parameter source checked in CI [measured 24.09]; 5 CI jobs including ROS in Docker, green on
  `4b5786b` [team record, re-checked]; frame-identical reruns; `FAULT` snapshot and watchdog.
* **Held down by:** `main` red at `537e220`, pushed without a PR (§7), against "PR + review, `main`
  always green" ([`PLAN.md`](PLAN.md)); package 0.6.3 against README v0.6.4 at `4b5786b`; ~5 500
  lines of Markdown (EXPERIMENTS 1 331, README 489) with sprint-log noise and stale counts;
  `detector_node.py` is 840 lines and calls private rclpy APIs (`handle.take_message`).
* **To raise before 29.09:** green `main`, enforced PR + CI and one version +0.5 to +1; the README
  as a 1–2 page jury guide, sprint logs out, +0.5 (§6 rows 1, 3).

### 8.6 Ease of launch: 7.5 / 10

* **Rests on:** the organizers' chain exactly: `docker build` → `docker run --net=host resense`
  (the default command starts the node) → `ros2 bag play <bag> --delay 3` →
  `ros2 topic echo /resense/decision`; topic auto-discovery; DDS over UDP for a normal-user player;
  `scripts/dry_run.sh` asserts the result; CI runs node and player in separate containers, player
  as uid 1000, two bags into one node [team record, re-checked on run 36039303135].
* **Held down by:** no judge could build or run it; never rehearsed on a stand or with a host
  `ros2 bag play` of a 360° bag (planned for 28.09); at `4b5786b` the commands sat under ~20 lines
  of status text and `--net=host` was not stated loudly; `FAULT` for 2.6–4 s while the player
  preloads [team record]; seeing the cloud needs X11 / xhost or a Foxglove import.
* **To raise before 29.09:** jury commands and expected output first in the README, with a host
  RViz one-liner (`rviz2 -d ros2_ws/src/resense_ros/rviz/resense.rviz`), +0.5 to +1; the 28.09
  clean-machine dry run, transcript in SUBMISSION.md (removed 25.09; the submission is handled by
  the captain), +0.5 (§6 rows 3, 7).

### 8.7 Team approach: 8 / 10

* **Rests on:** [`EXPERIMENTS.md`](EXPERIMENTS.md) records hypotheses, ablations and rejected
  paths with numbers: the LiDAR-only speed estimator off (false-alarm frames 88 → 119, §1b), the
  near-bed path off (ride 47 → 667 events), no learned second opinion after a leakage analysis
  (§8), 10 methods side by side (§7); P4's audit refutes the team's own flattering set F placement.
* **Held down by:** the volume hides the story (EXPERIMENTS 1 331 lines); headlines (README, deck,
  SUBMISSION cover letter "~148 м") quote set F figures the audit weakened; the organizers'-bag
  gaps of 24.09 are not acted on yet; the questions are drafted, not confirmed sent.
* **To raise before 29.09:** a one-page decision log (hypothesis → experiment → result →
  decision), including the organizers' bag, +0.5 (§6 row 4).

### 8.8 Pitch: 3 / 5

* **Rests on:** 15 slides in the organizers' template with the problem → approach → algorithm →
  demo → results arc; the main frame shows the person at 55.8 m from the cab; 4 videos in
  `docs/video/` (the Docker chain with RViz, 69 s, among them) and the dashboard.
* **Held down by:** team slides still show `<…>` placeholders; "199 тестов" (235); the range slide
  is titled «300 м — предел лидара» against 210 m in the data and leads with legacy set F (149 m
  held, 167 m with speed); nothing from the organizers' benchmark; all 4 videos (21.8 / 68.8 /
  20.1 / 20.1 s) show the same stationary-train scene, silent; no rehearsal record.
* **To raise before 29.09:** team data, test count, a corrected range slide, a §4 slide, a
  moving-train STOP beyond 80 m and a rehearsed `docker run` → STOP at 56 m demo: +1 (§6 row 5).

## 4. The organizers' synthetic-obstacle bag

`cloud_with_fake_obj`: 1 510 frames of real scans with ten ray-cast objects in frames 0–803; the
organizers check solutions with this tool (Q&A fact 4), so it is the closest thing to the hidden
check. Shipped config, every frame, no speed input [measured 24.09; identical to
[`P4_AUDIT.md`](P4_AUDIT.md)]. Frames: visible / with a point inside the envelope measured from
the rails / STOP.

| # | object | intent | visible from | frames | first STOP | STOP held from | verdict |
|---|---|---|---:|---|---:|---:|---|
| 1 | 2 × 2 m, centre | inside | 98.7 m | 213 / 213 / 207 | 98.0 m | 98.7 m | detected at first sight |
| 2 | 0.3 m, floating 1.0–1.4 m up | inside | 128.9 m | 79 / 63 / 19 (11 advisory) | 34.0 m | 37.4 m | late |
| 3 | 0.3 m, on the left rail | inside | 237.3 m | 49 / 33 / 23 | 42.7 m | 46.2 m | late |
| 4 | 0.3 m, at the edge | inside | 154.7 m | 83 / 16 / 0 (25 advisory) | — | — | advisory only |
| 5 | 0.3 m, just outside | outside | 238.4 m | 112 / 101 / 0 (24 advisory) | — | — | correct |
| 6 | 2 × 2 m, at the edge | inside | 248.6 m | 125 / 8 / 0 | — | — | missed |
| 7 | 2 × 2 m, outside | outside | 249.4 m | 104 / 52 / 6 (44 advisory) | 142.3 m | — | 6 false STOP frames |
| 8 | 2 × 2 m, top of the envelope | inside | 248.2 m | 124 / 75 / 12 (37 advisory) | 101.3 m | — | mostly advisory (`elevated`) |
| 9 | 2 × 0.2 m plank across the rails | inside | 248.5 m | 86 / 77 / 42 | 82.2 m | 58.6 m | detected |
| 10 | 0.05 m, hanging from the roof | inside | 199.7 m | 42 / 20 / 0 | — | — | missed |

Totals: in-envelope objects get a STOP in 303 of 801 visible frames (37.8 %): 0–50 m 113/227,
50–100 m 189/338, beyond 100 m 1/236. Alarms matched to no object: 3 frames, 2 IDs. The edge
objects (#4–#7) were placed from the sensor's axis, 0.24° off the rails the detector follows.

## 5. Top risks on the hidden control data

1. **Organizers' tool objects that hang, sit at the edge or at the top of the envelope:** missed
   or advisory, reported `GO` with a large `clear_distance` (#4, #6, #8, #10); the envelope
   reference (sensor axis vs rails, 0.24°) is unresolved and the questions are not confirmed sent.
2. **Small objects and range:** 0.3 m objects confirmed only inside ~35–45 m; no STOP beyond
   ~101 m; 58–86 m in R ≈ 350 m curves. Under 100 m is rated "poorly".
3. **Stations:** 25 STOP episodes in 88 s at a platform and switch (82–147 m) and ~3.6 false
   events per km on rides; the LiDAR stays on at stations (Q&A fact 18).
4. **Real time at 360°:** detection plus decoding ~75–100 ms, at the frame period; never measured
   on the i7-9700E; a slow run turns the decision into `CAUTION` on almost every frame, and a node
   that falls behind raises the false events (1 → 3 at 5 Hz).
5. **Process:** shipping from a red or untested `main`; `4b5786b` is the last green commit (§7).

## 6. Fastest points to gain

Gains are the judges' estimates in points out of 100; they overlap and do not add up. Effort is
a rough size (≤ 1 h, hours, half a day, 1 day); ranked by gain per effort.

| # | action | criterion | expected gain | effort | owner |
|---:|---|---|---:|---|---|
| 1 | fix or revert `537e220`; branch protection with required CI; one version everywhere | 8.5 | +0.5 to +1 | ≤ 1 h | P3, P1 |
| 2 | send QUESTIONS Q1–Q3 (edge reference, #8, bed object) and record the answers | 8.1, 8.4 | +0.5 | ≤ 1 h | P1 |
| 3 | README: jury commands and expected output first, `--net=host`, host RViz one-liner | 8.6, 8.5 | +0.5 to +1 | hours | P1 |
| 4 | one-page decision log, including the organizers' bag | 8.7 | +0.5 | hours | P1, P4 |
| 5 | deck: team data, 235 tests, range slide led by the organizers' numbers, §4 slide, moving-train STOP beyond 80 m, rehearsal | 8.8, 8.2 | +1 to +2 | 1 day | P2, P1 |
| 6 | conservative `clear_distance`: cap it at the nearest unconfirmed or advisory candidate touching the envelope; STOP unchanged | 8.1, 8.4 | +1 | half a day | P3, P4 |
| 7 | clean-machine dry run on 28.09 with a real 360° bag and a host player | 8.6 | +0.5 | half a day | P1 |
| 8 | an 8-core analogue bench through ROS (`resense bench`, `scripts/console_test.sh`, 360° bag; the stand is not available before submission, organizers 25.09); latency kept in `/resense/health`, no longer turning the decision into `CAUTION` | 8.3 | +0.5 to +1.5 | half a day | P1 |
| 9 | forward-sector crop at 360° before the track fit; identical output checked with `scripts/output_fingerprint.py` | 8.3 | +1 | half a day | P3, P1 |
| 10 | length-limited `elevated` / `floating` rule (`scripts/short_signature_experiment.py`), shipped after a ride re-run | 8.1, 8.4 | +0.5 to +2.5 | 1 day | P3, P4 |
| 11 | thin-hanging rule: \|dy\| < 0.8 m, h > 1.8 m, linked to points above 3.0 m, ≥ 2 voxels, 5 frames; measured on the organizers' bag, the empty bags and the ride | 8.1 | +1.5 | 1 day | P3, P4 |
| 12 | platform and switch STOPs beyond 80 m advisory unless confirmed nearer; re-checked on all 13 759 frames | 8.1 | +1 | 1 day | P3, P4 |
| 13 | **Measured, fix open (25.09):** 5 Hz and +3° roll/pitch checks on all six original bags; extra events localized but not fixed without harming real detections. Parameters frozen; frames 804–1 509 of `cloud_with_fake_obj` report 0/706 false-alarm frames (EXPERIMENTS §1g and [raw summary](evidence/results/scorecard13_2026-09-25.json)). This suffix was previously inspected, so it is held out from this parameter decision, not an unseen route. | 8.4 | +0.5 to +1 still open | 1 day | P4 measures; P3 fixes detector behavior |
| 14 | far-field rule for tall objects with a high bottom (#8) | 8.2 | +0.5 | 1 day | P3 |

## 7. State of `main` when judged

The judges scored `4b5786b`, green in CI. On 24.09 at 18:53 UTC `main` moved to `537e220`, pushed
without a PR, which retunes the opt-in near-bed gates (`lowobj.near_*`). `lowobj.near_enabled`
stays `false`, so shipped behaviour does not change, but CI run 36044487647 is red: 3 of 235 tests
fail (`tests/test_envelope.py::test_minimum_object_below_the_rail_head_is_a_policy`, the three
parametrised cases that switch the path on and expect the 30 × 30 × 10 cm box below the rail
head), and the `docker` job stopped at the in-image tests, skipping the smoke steps. Fixed on
branch `claude/nifty-pascal-lzgl78` by `7df1796` (`near_min_points` 10 → 5, `near_min_length`
0.18 → 0, the other gates kept): all 235 tests pass again, and all 266 with the tests added since
(§8), on the native and the numpy path. Until that branch is merged and CI is green on `main`,
`4b5786b` stays the last green commit of `main`. 25.09: PR #11 (merged 06:51 UTC, `5de0844`)
brought `7df1796` to `main`, and CI run 36104815305 on `main` is green; the PR had no review.

## 8. After the judgement (24.09, night)

What changed on branch `claude/nifty-pascal-lzgl78` after `4b5786b`, and the effect expected on
each criterion. **Nothing here is re-scored**: the scores of §2 stay as judged until a new
judgement.

| change | what it is | criterion | expected effect |
|---|---|---|---|
| `537e220`, then `7df1796` | the near-bed gates that turned `main` red, and their fix: all tests green again; five bags with the opt-in path on 459 / 107 / 72 instead of 1 035 / 145 / 42 (EXPERIMENTS §1e) | 8.5 | the "`main` red at `537e220`" item of §3 8.5 is fixed on the branch; the first part of §6 row 1 (fix or revert `537e220`) is done once it is merged with CI green; its other parts (branch protection, one version) are still open |
| C++ kernels (merge `d1a2d0c`) | optional kernels for the full-cloud passes and percentiles; detector time −38…−57 %, p95 at 360° 107 → 51 ms on the sandbox under load; 0 differing frames of 3 998; `RESENSE_NATIVE=0` falls back to numpy ([`ARCHITECTURE.md`](ARCHITECTURE.md) "Native kernels") | 8.3 | addresses "360° through ROS at the frame period" and "pure Python on one thread" of §3 8.3, the image builds them (CI run 36058665640, 24.09); an 8-core analogue run must still confirm the latency (the stand is not available before submission, organizers 25.09) |
| train-speed study | the LiDAR-only estimator measured against an ICP reference: median error 0.06–0.08 m/s on 55–96 % of the moving frames; even a perfect speed buys nothing on the organizers' check (EXPERIMENTS §9; raw: [`experiments_2026-09-24_train_speed.json`](evidence/results/experiments_2026-09-24_train_speed.json)) | 8.7 | a hypothesis → experiment → decision record with raw data |
| | judge A's suggestion for 8.2 (a speed estimate, e.g. scan-to-scan ICP, to re-enable accumulation for range; §3 8.2: 0.3 m beyond 45 m needs a train speed) was tested with the ICP speed itself | 8.2 | it does not hold on the organizers' check: with the reference speed the 0.3 m cubes are seen 7–16 m earlier but only as advisories, no object gets its first STOP earlier, and the box outside gets 17 false STOP frames instead of 6; no 8.2 gain from a speed |
| GPU study | no GPU before 29.09: the i7-9700E has PCIe 3.0, ~1 160 array operations per frame make a CuPy port dispatch-bound (≤ 30–45 ms per 360° frame saved against numpy, 5–15 ms against fused CPU code), and a container that requests a GPU does not start without `nvidia-container-toolkit` ([`ARCHITECTURE.md`](ARCHITECTURE.md) "GPU: evaluated, not used") | 8.7, 8.3 | "the GPU is unused" (§3 8.3) becomes an evaluated decision; the CPU savings it found (a forward crop −17 ms at 360°, an exact cKDTree DBSCAN −4…−6 ms) are candidates for §6 row 9 |
| documentation | one format, one home per fact; `cloud_with_fake_obj` corrected (the objects stand still, the train drives ~2.0 km forward), so QUESTIONS Q1 lost a sentence built on the error; EXPERIMENTS §3 corrected: `timing_ms["total"]` leaves out the 7–14 ms health monitor | 8.7, 8.5 | fewer stale or wrong statements; the old Q1 must not be sent |
| tests | 235 → 266 in `tests/` (+28 native kernels, +3 speed evaluation helpers), 11 in `web/demo`; 25.09: 289 (+17 regression gate, +3 DBSCAN exactness, +3 late candidates) | 8.5 | the deck's test count (§6 row 5) is 289 since the rebuild of 25.09 |
| 25.09, merged on the branch | stock Fast DDS player and listener in CI (green, run 36112092652); the 8-core bench kit `scripts/bench_8core.sh` (not yet run); the regression gate `scripts/regression_gate.py` with a baseline (the merged code passes, every gated metric the same); DBSCAN on cKDTree (identical output, −1.3…−2.6 ms per frame); two opt-in rules, off (EXPERIMENTS §1f); the deck rebuilt (16 slides, the organizers' objects, 289 tests) and a video script; the image archive for the offline stand (0.49 GiB, CI) | 8.6, 8.5, 8.3, 8.8 | §3 8.6 "never rehearsed … with a host player" is now covered in CI by a stock-DDS player as uid 1000 (a real host console stays for the 28.09 dry run); §6 rows 5 and 8 are partly done (deck, kit); nothing here is re-scored |
| organizers' answer (25.09) | the team gets no access to the test stand before submission ([`organizers/answers.md`](organizers/answers.md) §6); every stand run is dropped, the team's 8-core machine and CI stand in | 8.3 | §3 8.3 "To raise" and §6 row 8 now name an 8-core analogue bench (they read "i7-class" when judged); "never measured on the i7-9700E" (§2, §3 8.3, §5) stays true at submission |
| organizers' answer (25.09) | Q3: a 30 × 30 × 10 cm object lying on the bed between the rails (below the rail head) is not an obstacle, it is not inside the train's envelope ([`organizers/answers.md`](organizers/answers.md) §8) | 8.1 | the §3 8.1 hold-down "the 30 × 30 × 10 cm object below the rail head is not detected by default" is answered by the organizers: the shipped envelope-floor policy is theirs and the near-bed path stays off; §6 row 2 is done for Q3 (Q1–Q2 open); nothing is re-scored |
