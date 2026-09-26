# Criteria Scorecard

> **Purpose:** the independent judgements of ReSense against the eight criteria of spec §8: score
> per criterion, the evidence behind it, the risks on the hidden data and the fastest points to gain.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN, summary RU
> **Last independent judgement:** 2026-09-26 evening against `be5f5fc` (the integrated head: the
> detector of `fa18832`, gate baseline `_ride_p3d`), §0; earlier ones are dated records (§0a, §1–§8)
> · **Status:** current (§0), dated records (§0a–§8)

**Кратко.** Переоценка 26.09 (вечер) на интегрированной версии — **62,5 / 100** (судьи: A
65,5, B 61,5; утром 26.09 на версии до интеграции — 65, 24.09 — 60). Судья A заново скачал данные
организаторов и всё перемерил сам, судья B проверил каждое утверждение по коду и сырым JSON. Числа
команды воспроизводятся точно: полный регрессионный шлюз с поездкой и набором F на другой машине — PASS, каждая строка эталона `_ride_p3d` та же. Интеграция P3c/P3d дала реальный прирост (ящик у верха
габарита — STOP в каждом кадре с 101 м), но заголовок «8 из 8» его преувеличивает: краевые объекты
получают STOP лишь на 5–10 м, `clear_distance` проходит за объект в габарите, всё решалось на тех же
данных. Новая находка — с холодного диска 360° запись проваливает сухой прогон (обработано 34 кадра
из 201). Что поднимет оценку — §0.6. Третий круг (§0.8): работу P3/P4 того же вечера (кода она не
меняла) оба судьи проверили — судья A перемерил устойчивость, сдвиги старта и кандидатов B и
объединения габаритов, судья B сверил JSON; все числа совпали, оценки не изменились. Третий судья
(агент самой работы P3/P4) ставит 67, но он не независим; со всеми тремя среднее было бы 64.

## 0. Re-judgement of 26.09 evening (integrated head `be5f5fc`): 62.5 / 100

### 0.1 How it was judged

The same rubric as before (§1: maxima 25 / 15 / 10 / 15 / 10 / 10 / 10 / 5, fixed before scoring;
the organizers publish no weights), two judges who did not trust README, SCORECARD, CAPTAIN, PLAN,
CHANGELOG, EXPERIMENTS prose or the deck:

* **Judge A, execution lens:** scores only what it ran itself on a fresh 4-core machine (Xeon
  @ 2.8 GHz, 15 GiB; not the i7-9700E stand). The organizers' data downloaded again from their
  links (the six recordings, `cloud_with_fake_obj`, the 20-minute ride streamed split by split),
  the image built from `docker/Dockerfile`, then: the test suite, the jury chain offline on the
  original bags, the organizers' console with a stock Fast DDS player, set O from the float bag
  and through `ros2 bag play` into the node, the full regression gate with the ride and set F
  straight, the offline timing ([`evidence/rejudge_2026-09-26/`](evidence/rejudge_2026-09-26/)).
* **Judge B, metro safety engineer, sceptic lens:** ran nothing heavy; checked every headline
  claim against the code, the config and the raw JSON of `docs/evidence/`, and hunted for
  overstated, stale or contradictory claims (§0.4); wrote its scores before reading this file.

Both judged `be5f5fc` (CI green, run 36248096431); judge B then re-checked this pass's first
commit `4974242` claim by claim and re-scored; judge A's 8.5 and 8.8 saw the documents and the deck
after every fix of §0.4. Final = the mean per criterion, rounded down to 0.5.

### 0.2 Scores

Judge B scored `be5f5fc` first (61), then re-checked the pass's commit `4974242` claim by claim
(10 of its 17 claims fixed, 4 partly, 3 not; five new inconsistencies) and re-scored (61.5); the
remaining items were then fixed as well (§0.4). Judge A scored after the fixes.

| § | criterion | 26.09 morning | judge A | judge B (`be5f5fc` → re-check) | **26.09 evening** | one-line reason |
|---|---|---:|---:|---:|---:|---|
| 8.1 | Works | 14.5 | 14.5 | 13 → 13 | **13.5 / 25** | the real person 58 / 61 and the rail object 125 / 126 reproduce (in-sample, a standing train); set O "8 of 8" counts one STOP frame: the edge objects get 2 and 6 frames at 5–10 m, too late for a train; 384 of 801 in-envelope object-frames; ride 45 events / 38 STOP episodes in 13 km, in-sample; `clear_distance` past an in-envelope object: 51 of 505 frames with the object in the rail envelope, `GO` past it in 149–154 frames by the organizers' placement (cache, float bag and through ROS alike) |
| 8.2 | Range | 7.5 | 8 | 7 → 7 | **7.5 / 15** | first STOPs unchanged (101.3 / 98 / 82 m; cubes 43–53 m), 1 of 236 set O STOP frames beyond 100 m; new: the box at the envelope top is held from 101.3 m (was 23.9 m); the 148–154 m person is the team's own synthetic |
| 8.3 | Speed | 7 | 7.5 | 7.5 → 7.5 | **7.5 / 10** | measured through ROS in Docker on 4 cores: 360° p95 81 ms at 9.97 fps, 120° p95 58 ms at 10 fps, set O p95 52 ms; detector 23–31 ms on one core; latency no longer flips the decision; never on the i7; a 9.5 s start-up catch-up at 360° and the cold-disk collapse (§0.3) |
| 8.4 | Generalisation | 9 | 8.5 | 8 → 8 | **8 / 15** | geometry, no map, auto mount; but 287 config keys, 72 added on 25–26.09, several sized to single set O objects and gated only on the data they are reported on; no hold-out; the envelope-edge reference unresolved |
| 8.5 | Technical quality | 7.5 | 7.5 | 7 → 7.5 | **7.5 / 10** | 587 tests, 6-job CI, ruff, one parameter file; the full gate reproduced value for value on a fresh machine; the stale claims fixed (§0.4); minus: ~11 500 lines of Markdown, rule accretion, a node defect found and not yet fixed (the catch-up's own skips reset the scene, CAPTAIN action 21) |
| 8.6 | Ease of launch | 8 | 7.5 | 7.5 → 7 | **7 / 10** | the offline jury chain and the stock console PASS on the original bags, but only with the bag in the page cache: the first cold play of a 360° bag fails and the fix so far is one more manual step (README step 3); the only archive of the head is a login-gated CI artifact; root `sysctl` step for CycloneDDS |
| 8.7 | Team approach | 8.5 | 8.5 | 8 → 8 | **8 / 10** | pre-registration, a regression gate, safety reviews, tried-and-rejected with raw JSON; but an in-sample loop that fixes whichever set O object failed last |
| 8.8 | Pitch | 3 | 3.5 | 3 → 3.5 | **3.5 / 5** | the organizers' template, a strong real frame; the deck, PDF and video now consistent with the gate baseline and with each other, in-sample and synthetic figures labelled; team slides `<…>`, a silent video, no rehearsal |
| | **Total** | **65** | **65.5** | **61 → 61.5** | **62.5 / 100** | |

**Why lower than the morning's 65 on a better detector.** The product did not regress: every gated
number is the same or better (§0.3). The evening judges measured three things the morning ones did
not: how late the "8 of 8" edge objects are, how often `clear_distance` runs past an object on the
integrated code, and the jury chain from a cold disk; and they counted the config growth of 25–26.09
against generalisation. The morning score was for `867bb8a`; nobody had scored the integrated head.

### 0.3 What judge A measured

All on the fresh 4-core machine; logs and captures in
[`evidence/rejudge_2026-09-26/`](evidence/rejudge_2026-09-26/) (its `README.txt` has the machine and
the one sandbox-only deviation of the image build: the base image from a mirror with the proxy's CA).

| check | result | criteria |
|---|---|---|
| `pytest` (host, native path, `RESENSE_REQUIRE_SYNTHETIC=1`) | 585 passed + 1 deselected (needs the ride cache; run once the ride was cached: `tests/test_rail_start.py` 28 passed), 0 skipped, 218 s; `ruff` clean; parameter files in sync; `web/demo` 13 passed and `check_dashboard.py` PASS in headless Chromium | 8.5 |
| the organizers' data | downloaded from their links: the six recordings (2 488 frames; `doubleT_obstacle` and `roundT_doubleT` metadata equal to `bag_metadata/`), `cloud_with_fake_obj` (1 510), the ride (11 271, 221 split files, streamed) | |
| full regression gate against `_ride_p3d` (`--jobs 4`, every cache) | **PASS**, every gated row the same as the baseline, 302 s: five bags 58 alarm frames / 13 events / 16 STOP episodes (`squareT_platform_squareT_switch` 54 / 9 / 15, `doubleT_platform` 4 / 4 / 1, the other three 0); the ride 183 / 45 / 38 (alarms at 20.7–158.3 m), `CAUTION` by the node's decision rule on 41.3 % of its frames (27–69 % on the five bags; `warning` frames 42.1 %); `doubleT_obstacle` person 58 of 61, the object on the rail 125 of 126 from frame 75, 0 false-alarm frames, distance error ≤ 0.23 m, first alarm frame 11; set O 384 of 801 in-envelope object-frames, 8 of 8 objects with a STOP, 6 false STOP frames outside, 3 background; set F straight: person 151.0 m (6 of 6), trolley 151.4 m, 1 m crate 123.9 m, cable 98.9 m, 0.5 m box on the bed 1 of 6. Only the latency rows differ (information: 4 jobs on 4 cores) | 8.1, 8.2, 8.5 |
| set O from the float bag (`resense run --bag`, not the cache) | 387 of 801 in-envelope object-frames `STOP` (cache 384: 5 mm quantisation); per object as the baseline but #3 26 frames from 48.0 m (cache 23 from 42.7 m); 7 false `STOP` frames on the outside box #7 from 142.3 m; 1 background frame | 8.1, 8.2 |
| `clear_distance` on set O (float bag, `score_clear_distance.py`) | past an object inside the rail-referenced envelope in **51 of 505** frames (44 of them `GO`); by the organizers' placement 217 of 801; 154 `GO` frames past an in-envelope object | 8.1 |
| set O through `ros2 bag play` into the node (Docker, offline, warm cache) | **PASS** as a node run (10 fps, p95 52 ms, back on the newest frame at +5.9 s); 1 452 of 1 510 frames processed: all 58 skipped ones fall in the start-up catch-up (frames 0–22, then every second one to frame 80), every frame after that processed. Graded per object after mapping the node's header stamps onto the bag's frames: every object as offline except #1, the 2 × 2 m box in view when the recording starts: 153 of its 155 processed frames, first STOP 94.6 m instead of 98.0 m (its first frames fell into the catch-up); 10 false STOP frames on the outside box #7 (offline 6–7), 0 background frames; `clear_distance` past an object in the rail envelope in 52 of 447 frames, `GO` past an in-envelope object in 149 frames by the organizers' placement (judge B re-mapped the capture: the same). The checker's line "132 of its messages not processed" is wrong on this bag: it matches the node's header stamps (year 2000, the organizers' tool) against the bag's receive times, which drift apart; the frame mapping shows none unprocessed after frame 80 | 8.1, 8.6 |
| `OFFLINE=1 dry_run.sh doubleT_obstacle` (360°, the jury image path, `--network none`), bag in the page cache | **PASS**: 139 status messages, 126 alarm frames at 55.7–56.5 m, decode + detect p95 81 ms (detector 42 ms), 9.97 fps, back on the newest frame at +9.5 s, 0 of the recording's frames unprocessed after it | 8.3, 8.6 |
| the same with the page cache dropped (337 MB/s cold reads) | **FAIL**: 34 status messages, first `STOP` +15.5 s: the player sent the whole overdue recording at once; the catch-up dropped frames > 5 s behind, the processed frames were 1.0–1.4 s apart, each gap reset the scene. Twice more before the cache was warm: FAIL (53 and 32 messages) | 8.3, 8.6 |
| `OFFLINE=1 dry_run.sh roundT_doubleT --expect-clear` (120°) | **PASS**: 0 alarm frames, p95 58 ms, 10.0 fps | 8.1, 8.3 |
| `PLAYER_DDS=stock console_test.sh roundT_doubleT doubleT_obstacle` (the organizers' console: a uid-1000 stock Fast DDS player and listener, shared memory on) | **PASS**: both recordings into one running node, `STOP` at 55.7–56.5 m, the listener heard 128 `STOP` | 8.6 |
| offline timing, `resense bench` (native, one process, idle) | detector per frame, native path, one thread: 360° `doubleT_obstacle` 30.7 ms mean, p95 42.1 ms, max 57.9 ms; 120° `roundT_doubleT` 25.8 / 37.1 / 58.1 ms; set O 22.7 / 32.8 / 79.8 ms; the numpy fallback at 360° 78.3 / 95.5 / 135.5 ms | 8.3 |
| deck, video, docs against the evidence | 17 claims wrong, stale or contradictory (§0.4) | 8.5, 8.8 |

### 0.4 Claims found wrong, stale or contradictory, and what this pass did

Judge B listed 17 on `be5f5fc` and 5 more on the pass's first commit `4974242`; judge A confirmed
them against its own runs. The deck and video are P2's lane, the documents P1's; no detector or
config change.

| # | where | claim | evidence | status |
|---|---|---|---|---|
| 1 | deck slide 13, notes | the box at the envelope top "STOP лишь в 22 из 124 кадров" | 51 of 124, every frame from 101.3 m | fixed; the deck test reads it from the baseline |
| 2 | deck slides 11, 15, notes | "ящик у края пропущен", "два объекта без STOP" next to "8 из 8" | edge objects 2 of 83 at 5.2 m, 6 of 125 from 10.3 m | fixed: one wording everywhere; the test forbids «пропущен» |
| 3 | deck slides 14, 16 | 555 tests | 587 | fixed; tested |
| 4 | deck slides 2–3 | template placeholders | | **open: people's data** (CAPTAIN §4) |
| 5 | CHANGELOG | top entry about an older deck; no entry for `e5f0f02` | | fixed |
| 6 | ALGORITHM §6 | set O #8 "12 of its 124 frames" | 51 of 124 | fixed, "8 of 8" qualified |
| 7 | ALGORITHM §3.5 / §4 | the decision rule without the shipped rules of 26.09; §4 "matched none of the signatures" | `configs/default.yaml` | fixed: §3.5 "Rules of 26.09", §4 names its exceptions (near escalation, STOP keep, `reseed_hold`); stamp updated |
| 8 | PRESENTATION | "6 из 8, пять устойчиво", 46, 492 tests | | fixed |
| 9 | ARCHITECTURE | 289 tests (then an off-by-one 586) | 587 | fixed |
| 10 | README, EXPERIMENTS, deck slide 12 | the person "held in ≥ 90 % from 149 m" beyond "first confirmed 148 m" | the 90 % rule counts the misses before the first confirmation | fixed: the band figure (≥ 90 % of every 10 m band from 115 m) instead; the artefact explained where the old figure stays; the deck test forbids «~149» |
| 11 | deck slide 13 title | "STOP — 8 из 8" without the edge objects' lateness | | fixed: «STOP у 8 из 8, у края — лишь вблизи» |
| 12 | video subtitles | 148 m without "our synthetic" | | fixed |
| 13 | README, EXPERIMENTS, deck slides 5 / 11 and notes, video card and subtitle | "42–64 ms per frame on one core" (the numpy path of 23.09) | the shipped path: 22.7–30.7 ms, p95 ≤ 42.1 ms (`bench_native.txt`) | fixed everywhere; the old figure kept only as dated history; the deck test forbids «42–64» |
| 14 | deck slides 5, 11, 16; video card | "3,5 на км" without "in-sample" | the ride decided the rules | fixed: «правила решались на ней же» on each |
| 15 | README | CAUTION "27–68 %, 41 %" of 24.09 | node decision rule: 27–69 %, ride 41.3 % | fixed |
| 16 | DECISIONS | no row for the rules that gave 8 of 8 and 51 of 124; row 15 "none shipped" | `lowobj.rail_start_within` is on | fixed: rows 15 and 17 |
| 17 | EXPERIMENTS §3a | the second VM's bench PASS without saying the drop criterion changed after the first FAIL | `5be4143` | fixed: disclosed next to the PASS |
| 18 | README status | "back in real time within ~2–7 s" then 9.5 s | | fixed: ~2–10 s |
| 19 | README | first STOP "1.3–1.6 s into the recording" | the team's VMs; the re-judgement's warm run: 2.9 s after the node's first frame | fixed: both, per machine |
| 20 | README | "587 tests green" credited to the re-measurement | 585 passed + 1 deselected (then passed with the ride cached); the 587th added by this pass | fixed |
| 21 | evidence | `setO_header_stamps.jsonl` listed but not committed (`.gitignore` `*.jsonl`) | | fixed: committed with `git add -f` |
| 22 | SCORECARD §0 | "17 found by B, fixed in this pass" | 10 / 4 / 3 at `4974242` | fixed: this table |

Left as they are, stated here: "8 of 8" is the scorer's one-hit verdict and is always said with the
edge objects' 2 and 6 frames; set O #8's "held from 111.4 m" field of the scorer is quoted nowhere
as a range (README and EXPERIMENTS say "a STOP on every frame from 101.3 m").

### 0.5 Top risks on the hidden control data

1. **Objects at the envelope edge.** The organizers place objects from the sensor axis (−0.24° to
   the rails in `cloud_with_fake_obj`), ReSense builds the envelope from the rails: the edge objects
   STOP only at 5–10 m and the outside box gets 6 false STOP frames from 142 m (Q1, unanswered).
2. **Nothing beyond ~100 m on the organizers' objects**; 0.3 m objects from 43–53 m.
3. **Stations and platforms:** `squareT_platform_squareT_switch` 15 STOP episodes in 88 s; switch
   glitches are forgiven by the organizers, platform ones are not.
4. **A cold first play** of a 360° bag (§0.3): 34 of 201 frames, first STOP +15.5 s.
5. **`clear_distance` past a present obstacle** in 51 of 505 frames (object in the rail-referenced
   envelope; 44 of them `GO`); 217 of 801 by the organizers' placement. `STOP` and
   `nearest_distance` are the outputs to read (README "What to look at").
6. **The start of a fresh bag:** a STOP in the first 4 s of 18 of 221 ride bags, none within 10 m since the rail-start rule (EXPERIMENTS §1j, §1p; reproduced on the evening's second machine).

### 0.6 What raises the score before the upload (29.09 23:59)

| # | action | owner | who can do it | criteria |
|---|---|---|---|---|
| 1 | publish the image archive of the frozen commit where a logged-out visitor gets it (release tag or a public copy of the CI artifact), `docker load` it on a second machine | P1 | the captain decides (releases were deferred); an agent runs it | 8.6 +0.5 |
| 2 | the node's catch-up under a whole-recording burst (CAPTAIN action 21): no scene reset on the node's own skips, chain steps ≤ `catchup_step`; proven by the cold dry run | P1 | the captain decides; an agent implements | 8.3, 8.6 +0.5 |
| 3 | the envelope-edge reference: chase Q1; without an answer, a pre-registered near-field variant for compact objects within 30–50 m, gated and safety-reviewed, or the limit stated in README "What to look at" | P3 + P1 | the captain asks; an agent measures | 8.1 +1 |
| 4 | `clear_distance` capped at any in-envelope track, or kept off the headline | P3 | an agent measures, the captain decides | 8.1 +0.5 |
| 5 | one honest out-of-sample number: the organizers' own object point sets re-injected at new offsets into the five empty recordings and the ride, reported next to the in-sample figures | P4 | an agent | 8.4 +0.5–1 |
| 6 | the ride's 45 events split by scene (switch / platform / open tunnel) on the current code | P4 | an agent (the ride cache) | 8.1 +0.5 |
| 7 | team slides filled, two rehearsals, the optional voice-over | P2 + captain | people | 8.8 +0.5–1 |
| 8 | freeze and merge: PR #12 merged or the commit named in the upload | P1 | the captain | 8.5, 8.6 |

### 0.7 Cross-check by a third measurement (the P3 / P4 completion pass, the same evening)

A third judge (the agent of the P3 / P4 completion pass) scored the same head before reading §0,
on another fresh container (4 vCPU, 15 GB, no Docker daemon), with the rubric of §1. Everything
that runs without Docker was run: the caches rebuilt from the organizers' links, the strict gate
with the ride and set F straight, set O alone, the robustness and start-offset tools, the
221-start census, the whole test suite, ruff, the parameter sync; the deck's text read from the
pptx (before this pass rebuilt it), the videos probed, CI and the PR read from the GitHub API.
Not run: Docker, the ROS 2 node, any bag through ROS. Every result agrees with judge A's:

| check | result | tag |
|---|---|---|
| set O cache rebuilt from `cloud_with_fake_obj.zst`; `resense run --npy` + `score_fake_objects.py` | every object equal to `_ride_p3d`: 384 / 801, 8 of 8, 6 false STOP frames outside, 3 background frames / 2 ids | measured |
| the six recordings rebuilt from `Датасет.zip` (`metadata.yaml` = the committed originals); the ride from `new_data.zst` (11 271 frames, 221 splits); **the strict gate with no `--allow`** | **PASS, every gated row the same** (five bags 58 / 13 / 16, ride 183 / 45 / 38, set F straight all 15 rows); 319 s at `--jobs 3` ([`regression_gate_2026-09-26_head_fresh_machine.json`](evidence/results/regression_gate_2026-09-26_head_fresh_machine.json)) | measured |
| `robustness_check.py` as recorded / 5 Hz / +3° roll / +3° pitch; `start_offsets.py` | 13 / 16, 10 / 10, 14 / 16, 17 / 18; offsets 13 / 16, 13 / 14, 13 / 12, 10 / 11, 7 / 11: P4's figures value for value; the pitch's extras are 1–4 frame events, one of them a `low` STOP at 1.0–3.0 m on `doubleT_platform`; under the roll the 360° recording's calibration never leaves `pending` (EXPERIMENTS §1p) | measured |
| `startup_census.py` on the head (221 ride splits + 8 pieces + 7 recordings) | 18 of 221 ride starts with a STOP, 120 frames / 35 events / 28 episodes, none within 10 m; `doubleT_obstacle` first STOP frame 11 | measured |
| `pytest` with and without the ride cache; `ruff`; `sync_params.sh --check` | 586 passed with the ride (585 + 1 deselected without it; 587 since this pass's video test); clean; in sync | measured |
| `OMP_NUM_THREADS=1 resense bench --npy`, one thread ([`bench_offline.txt`](evidence/results/p4_robustness_2026-09-26_evening/bench_offline.txt)) | 360°: 24.2 ms mean / p95 33.5 ms native, 57.5 / 71.3 ms numpy (−58 %); 120°: 21.8 / 30.7 ms (detector stages only) | measured |
| P4's candidate B and the envelope union, each a full gate with the ride | B: PASS, only set O #4 moves (2 → 3 STOP frames), every acceptance check identical to the head; the union: PASS, #4 2 → 9, nothing else moves; neither shipped (EXPERIMENTS §1p) | measured |
| GitHub: CI run 36248096431 on `be5f5fc`; PR #12; `main`; authorship | six jobs green; PR open, mergeable, 233 commits ahead; `main` green at `6962519`; 205 of 250 commits by agent sessions | re-checked |

Its scores, and where they differ from the reconciled §0.2 (which stays the judgement of record:
two judges against one, and this one did not run Docker or ROS):

| § | third judge | §0.2 | why the third judge differs |
|---|---:|---:|---|
| 8.1 | 15.5 | 13.5 | credits the held STOP from 101.3 m on the box at the envelope top and 8 of 8 with a STOP as detection quality on the organizers' own tool, not "one STOP frame"; agrees on every hold-down (edge objects 2 and 6 frames, 6 false STOP frames on #7, the platform's 15 STOP episodes, in-sample 3.5 per km) |
| 8.2 | 7.5 | 7.5 | agrees |
| 8.3 | 7.5 | 7.5 | takes §0's ROS measurement; offline 24 ms mean native at 360° confirms the C++ figures |
| 8.4 | 9 | 8 | 5 Hz gives fewer events than as recorded, roll and pitch add only 1–4 frame flickers, 18 of 221 fresh starts STOP and none within 10 m, all reproduced; agrees that no held-out figure exists |
| 8.5 | 8 | 7.5 | the gate reproduced row for row on a third machine from the raw links |
| 8.6 | 7 | 7 | takes §0's cold-disk finding, which it could not test |
| 8.7 | 9 | 8 | the process reproduced end to end, from a pre-registration commit to the raw JSON (note: this judge is the agent that wrote that pre-registration and ran those candidates, so the credit is partly self-assessment); agrees the loop is in-sample |
| 8.8 | 3.5 | 3.5 | agrees (the deck rebuilt by this pass) |
| **total** | **67** | **62.5** | the difference is 8.1, 8.4, 8.5 and 8.7: a reading of the same evidence, not new evidence |

### 0.8 Third round: the P3 / P4 pass checked, the scores re-checked (26.09 evening, `1f8b8ff`)

The P3 / P4 completion pass (§0.7, EXPERIMENTS §1p) changed no detector, config, node or Docker
code (`git diff be5f5fc 1f8b8ff -- resense configs ros2_ws native docker` is empty): it measured.
Both judges checked it instead of taking it:

* **Judge A re-ran on its own machine** (the caches of §0.3;
  [`evidence/rejudge_2026-09-26/p34/`](evidence/rejudge_2026-09-26/p34/)): `robustness_check.py`
  as recorded / 5 Hz / +3° roll / +3° pitch → five bags 13 / 16, 10 / 10, 14 / 16, 17 / 18 events /
  STOP episodes; `start_offsets.py` → 13 / 16, 13 / 14, 13 / 12, 10 / 11, 7 / 11; the gate of
  candidate B (`tracking.near_escalate_voxels` 8) and of the union (`gauge.axis_union` 1) on the
  six recordings and set O → PASS, only set O #4 moves (2 → 3 and 2 → 9 STOP frames; first STOP
  7.1 and 18.2 m); `tests/test_edge_axis.py` (the union's safety scenes) 10 passed. Every number
  as the pass reported it.
* **Judge B diffed the committed JSONs** (the head on the fresh machine: 0 differences from
  `_ride_p3d`; B and the union: only #4; the census 18 of 221, none within 10 m; the robustness
  runs and their hashes) and found seven text issues, now fixed or stated: `doubleT_platform` +3
  under pitch was net +2 (4 → 6); 3, not 4, of the 7 new pitch events under `provisional`; the
  1.0–3.0 m `low` STOP under pitch and the roll's calibration that never finishes on the 360°
  recording were left out of the summaries (§0.7, EXPERIMENTS §1p); EXPERIMENTS and P4_AUDIT
  still called 67 the current score; §0.7 called the third judge "a stranger" to the process it
  ran; the union's safety scenes were promised by the pre-registration but not reported. It also
  notes that the pre-registration (`53b75d4`, 15:32:50 UTC, before every run's timestamp) was
  pushed only with the results, so its order rests on that machine's clock, and carried little
  risk: both effects were known and both candidates were "not shipped whatever the result".

**Re-scores.** The pass adds reproducibility and robustness evidence for things already scored,
and ships nothing, so neither judge moves:

| § | judge A | judge B | third judge (§0.7) | why A and B stay |
|---|---:|---:|---:|---|
| 8.1 | 14.5 | 13 | 15.5 | the held STOP from 101.3 m was already credited; "8 of 8" still counts one STOP frame; B and the union are not shipped (and the union does nothing for #6) |
| 8.2 | 8 | 7 | 7.5 | no first STOP moves |
| 8.3 | 7.5 | 7.5 | 7.5 | |
| 8.4 | 8.5 | 8 | 9 | the rate / mount / start-offset runs perturb the same five tuning recordings (pitch still 13 → 17 events and a 1–3 m STOP; roll leaves the 360° calibration pending); the census (none within 10 m) is a real gain but in-sample; no held-out figure |
| 8.5 | 7.5 | 7.5 | 8 | reproducibility was already credited; the node's catch-up defect is still open (CAPTAIN action 21) |
| 8.6 | 7.5 | 7 | 7 | |
| 8.7 | 8.5 | 8 | 9 | good discipline (pre-registered, measured, not shipped over the freeze and Q1), but self-dated, low-risk and still no out-of-sample number |
| 8.8 | 3.5 | 3.5 | 3.5 | |
| **total** | **65.5** | **61.5** | **67** | |

**The judgement of record stays 62.5 / 100** (§0.2: the mean of A and B, rounded down per
criterion). The third judge is not independent of the pass it scores, so it is a cross-check,
not a vote; with it as a third vote the mean would be 64 (14 / 7.5 / 7.5 / 8.5 / 7.5 / 7 / 8.5 /
3.5). The spread 61.5–67 is the honest uncertainty of this score. What would move it is in §0.6;
of the pass's candidates, B is +1 STOP frame at 7 m (no score change) and the union +7 frames on
#4 from 18.2 m (worth ~+0.5 on 8.1 if the organizers' Q1 confirms the sensor axis).

## 0a. Re-judgement of 26.09 morning (pre-integration head `867bb8a`): 65 / 100 (dated record)

The score below is the judges' dated result for the pre-integration head. A later P3c consistency
pass refreshed the public deck, PDF and overview video from current results: five empty bags 13
events, ride 45 events / 3.5 per km, set O 8/8 inside objects with at least one STOP (two edge
objects get only 2 and 6 frames), and 555 tests. The empty-suffix replay confirms one background
STOP on both raw and cached inputs (EXPERIMENTS §1g). These updates have not been independently
re-scored.

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

## 0a.1. Integrated P3c evidence (26.09; scored in §0)

The integrated baseline [`regression_baseline_2026-09-26_ride_p3c.json`](evidence/results/regression_baseline_2026-09-26_ride_p3c.json)
records 125/126 rail-object hits after frame 75, 13 false events on five empty bags, 45 events on
the 13 km ride, and 355 STOP frames of 801 visible in-envelope object-frames in set O. All 8
inside objects get a STOP; #4 gets 2 frames, #6 gets 6, and #8 gets 22/124. Only one set O STOP
frame is beyond 100 m. The longest consecutive visible misses are 77 frames for #4, 110 for #6,
and 73 for #8. The empty suffix has one background STOP at frame 1131 (140.72 m), reproduced
from the raw bag and quantized cache.

P4 has strengthened `scripts/regression_gate.py`: set O comparisons now fail if a previously
measured held-from STOP distance shrinks, a distance-bin denominator changes, or per-bin STOP
frames fall. P4 restored and verified all six original recording caches and reproduced the
available baseline rows. The `new_data` ride cache and set F rows remain absent, so the strict
gate reports three ride and fifteen set F metrics as missing. The 65/100 remains the last
independent judge score, not a score for the integrated head.

## 0a.2. Historical P3c provisional assessment of the available P4 head: 66.5 / 100

This is a **provisional internal assessment**, not an independent organizer or judge score. It
uses the repository's eight assessment maxima (25, 15, 10, 15, 10, 10, 10, 5); the organizers
have not published criterion weights. It assesses the current P3c detector plus the available P4
evidence, but does not credit P4 with inherited P3 detector changes. The separate 65/100 judgment
above remains unchanged on its original pre-P3c commit.

| § | criterion | provisional / max | change vs. independent 65 | evidence and reason |
|---|---|---:|---:|---|
| 8.1 | Works | **15 / 25** | +0.5, inherited P3c | All 8 in-gauge set O objects receive a STOP, but #4 is 2/83 frames, #6 6/125, and #8 22/124; outside object #7 has six false STOP frames. No P4 detector gain is claimed. |
| 8.2 | Range | **7.5 / 15** | 0 | Only one set O STOP frame is beyond 100 m; ride and set F could not be rerun. The 148–154 m synthetic person is not real long-range validation. |
| 8.3 | Speed | **7 / 10** | 0 | Existing native and ROS measurements remain dated; P4 did not add a controlled stand or timing run. |
| 8.4 | Generalisation | **9 / 15** | 0 | Six-recording 5 Hz, mount and start-offset checks are reproducible, but the ride is absent and set O is already inspected. Synthetic placements do not prove material robustness. |
| 8.5 | Technical quality | **8 / 10** | +0.5, P4 evidence | Verified cache hashes, run provenance, strict gate results, false-alarm inventory, and candidate outcomes are recorded. The full gate and ride-dependent tests remain incomplete. |
| 8.6 | Ease of launch | **8 / 10** | 0 | The existing offline image and CI evidence stand; no new operator rehearsal or independent stand run was done. |
| 8.7 | Team approach | **9 / 10** | +0.5, P4 process | Candidates were preregistered, safety rules held fixed, and unsafe or incomplete outcomes recorded. A and B are not accepted without ride, set F and candidate-specific checks. |
| 8.8 | Pitch | **3 / 5** | 0 | No new independent deck review, presentation, or rehearsal was part of this pass. |
| | **Total** | **66.5 / 100** | **+1.5 provisional** | 8.1's half point is inherited P3c detector work; the 8.5 and 8.7 half points reflect P4 evidence and process only. |

The score is limited by the raw/cache sensitivity: the float bag scores 357 inside, 7 outside,
and 1 background STOP frame, while its 5 mm int16 cache scores 355, 6, and 3. The available
regression reference is cache-based. The 20-minute ride contains no real obstacles, and anchored
set F placement is not surveyed ground truth. Review packet:
[`p4_review_packet_2026-09-26.json`](evidence/results/p4_review_packet_2026-09-26.json); full
criterion notes and limitations:
[`p4_provisional_score_2026-09-26.json`](evidence/results/p4_provisional_score_2026-09-26.json).

## 0a.3. P4's provisional internal assessment against inherited P3d: 67 / 100 (superseded by §0)

This is a **provisional internal assessment**, not an independent organizer or judge score. It
uses the repository's eight assessment maxima (25, 15, 10, 15, 10, 10, 10, 5); the organizers
have not published criterion weights. The +0.5 Works point over the historical P3c assessment
comes from inherited upstream P3d STOP-keep behavior; P4 receives no detector-improvement credit.
P4 receives evidence/process credit only. The independent 65/100 remains unchanged on commit
`867bb8a`.

| § | criterion | provisional / max | change vs. independent 65 | evidence and reason |
|---|---|---:|---:|---|
| 8.1 | Works | **15.5 / 25** | +1.0, inherited P3c and P3d | All 8 in-gauge set O objects receive a STOP. Inherited P3d raises #8 from 22/124 to 51/124 and held-from 23.9→111.4 m, while it still first stops at 101.3 m; total is 384/801. #4 remains 2/83, #6 6/125, and outside #7 has six false STOP frames. No P4 detector gain is claimed. |
| 8.2 | Range | **7.5 / 15** | 0 | Only one set O STOP frame is beyond 100 m; no real positive obstacle or set F rerun supports long-range recall. The 148–154 m synthetic person is not real validation. |
| 8.3 | Speed | **7 / 10** | 0 | Existing native and ROS measurements remain dated; P4 did not add a controlled stand or timing run. |
| 8.4 | Generalisation | **9 / 15** | 0 | Six-recording 5 Hz, mount, and start-offset checks are reproducible, but routes were already available; ride is absent and set O is already inspected. |
| 8.5 | Technical quality | **8 / 10** | +0.5, P4 evidence | Six recording caches and set O are verified; run provenance, strict-gate results, false-alarm inventory, paired-placement identities, and candidate outcomes are recorded. Ride-dependent gate/test coverage remains incomplete. |
| 8.6 | Ease of launch | **8 / 10** | 0 | Existing offline image and CI evidence stand; no new operator rehearsal or independent stand run was done. |
| 8.7 | Team approach | **9 / 10** | +0.5, P4 process | A/B/C were preregistered and screened against P3d. A/C were rejected for no target gain; B improves #4 but remains unaccepted because the strict gate lacks ride/set F rows. |
| 8.8 | Pitch | **3 / 5** | 0 | No new independent deck review, presentation, or rehearsal was part of this pass. |
| | **Total** | **67 / 100** | **+2 provisional** | 8.1's point is inherited P3c/P3d detector work; 8.5 and 8.7 reflect P4 evidence and process only. |

The cached P3d set O replay and original raw bag remain score-different: cache 384 inside / 6
outside / 3 background STOP frames versus raw 387 / 7 / 1. The ride has no real obstacles; set O is
not unseen validation; anchored placement is not surveyed ground truth. The strict gate still lacks
3 ride and 15 set F rows. Review material:
[`p4_review_packet_p3d_2026-09-26.json`](evidence/results/p4_review_packet_p3d_2026-09-26.json),
[`p4_provisional_score_p3d_2026-09-26.json`](evidence/results/p4_provisional_score_p3d_2026-09-26.json),
and [`P4_AUDIT.md`](P4_AUDIT.md).

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
| 13 | **Measured, fix open (25.09):** 5 Hz and +3° roll/pitch checks on all six original bags; extra events localized but not fixed without harming real detections. The 25.09 playback report claimed 0/706 false-alarm frames in the empty suffix of `cloud_with_fake_obj` ([raw summary](evidence/results/scorecard13_2026-09-25.json)); the current cached-frame gate has a background STOP at frame 1131 in that suffix (EXPERIMENTS §1g). It was previously inspected, so neither result is an unseen-route check. | 8.4 | +0.5 to +1 still open | 1 day | P4 measures; P3 fixes detector behavior |
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
