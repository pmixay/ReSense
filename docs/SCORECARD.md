# Criteria Scorecard

> **Purpose:** the independent judgement of ReSense against the eight criteria of spec §8: score per
> criterion, what was measured, the deductions and what would raise each score.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN, summary RU
> **Judged:** 2026-09-28 evening, commit `464f5bc` (`main`, CI run 36424461052 green): the sealed
> 27.09 detector and the node of 28.09. Raw material, scripts and per-frame outputs:
> [`evidence/judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md).
> **Scope:** independent main-branch assessment of `464f5bc`. Experimental development reviews below have different source and evidence scopes. Earlier main-branch reports remain in Git history; cycle evidence is retained on this branch.

## Experimental development reviews

The main review below is **61/100 for `464f5bc`**, not a paired score of the current
experimental detector. The historical lead assessment was **69/100**. These reviews
use separate judgments and evidence; their difference is not a measured software regression.
Main `059948a` is being synchronized into experimental, and its new node needs combined
runtime acceptance. No new score is assigned to that combination yet.

## Checkpoint 3: health optimization, 28 September

| Functionality /25 | Range /15 | Speed /10 | Generalization /15 | Technical quality /10 | Launch /10 | Approach /10 | Pitch /5 | Total /100 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 17 | 6 | 8 | 6 | 9 | 8.5 | 9 | 4 | **67.5** |

The [fresh-context paired review](evidence/cycle_2026-09-28/checkpoint3_health_astra.md)
awards only **+0.5 for speed**, compared with the same reviewer's 67-point baseline.
The [machine-readable judgment](evidence/cycle_2026-09-28/checkpoint3_health_astra.json)
and [runtime captures](evidence/cycle_2026-09-28/health_histogram/runtime/README.md)
retain the baseline failure, exact source/image identities and remaining freshness gaps.
Processing p95 improves 105.15 → 76.32 ms on the positive recording and 77.33 → 60.51 ms
on the clear recording. Raw detections match all 453 frames. Positive current end-to-end
p95 is still 167.85 ms; fresh person recall is 49/61, and fresh rail recall after frame 75
is 115/126. One fixed-order local warm pair does not establish target-hardware performance.

The [checkpoint 2 priority review](evidence/cycle_2026-09-28/checkpoint2_priority_astra.md)
separately rated the combined baseline 67/100 before health acceptance. Its mention of
33 production files is a counting typo: the committed manifest and root audit cover 34.
Both original reports are retained verbatim. The earlier paired 66 → 66 review below
and historical lead rating of 69 are separate assessments, not a measured score decline.
The next priorities are accurate full-call timing, startup/current-result recovery,
and acceptance of the near-preserving fresh-onset candidate, which has no credit yet.

## Checkpoint 1: 28 September evening

| Functionality /25 | Range /15 | Speed /10 | Generalization /15 | Technical quality /10 | Launch /10 | Approach /10 | Pitch /5 | Total /100 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 17 | 6 | 7 | 6 | 9 | 8 | 9 | 4 | **66** |

The bounded continuity fix restores raw rail-object STOP coverage from 123 to
126/126 after frame 75. Full quality and history gates pass; false alarms and
reserved synthetic recall do not improve. Local full-rate positive ROS replay
fails freshness and the 100 ms threshold for both baseline and candidate.

The difference from the earlier 69-point lead review reflects an independent
reviewer and newly measured limitations. It is not a paired measurement of a
three-point software regression. Read the [complete independent review](CHECKPOINT1_REVIEW_2026-09-28.md)
and [machine-readable result](evidence/cycle_2026-09-28/checkpoint1_astra.json).
The [paired reassessment](evidence/cycle_2026-09-28/checkpoint1_astra_paired.md)
holds evidence and reviewer constant: baseline 66, candidate 66, no whole-point
change. It confirms no numerical regression within that review.

## Independent main review — measured at `464f5bc`

**Кратко.** Независимая оценка 28.09 (вечер), коммит `464f5bc`: **61 / 100**. Всё перемерено
заново на данных организаторов; прежним оценкам и цифрам документов не доверяли. Сильное: цепочка
жюри `docker build → docker run → ros2 bag play` работает с нуля; реальный человек на 55,5–56,6 м —
STOP во всех 8 прогонах на этом бэге, с 8-го кадра (первого в габарите) в 4 из 5 прогонов по README;
на пяти пустых записях 23 кадра STOP из 2 287 (1 %); 753 теста проходят; задержка p95 85–94 мс на
360° облаках. Слабое: на 20-минутной поездке 30 ложных эпизодов STOP на 13 км (2,3 на км, примерно
раз в 38 с); дальность — реальный человек, перенесённый в другие тоннели, получает устойчивый STOP
на 60 м в 11 из 15 окон, на 100 м — в 6 из 15, на 160 м — в 1; кубы 0,3 м организаторов — только с
35–56 м; одиночный GO при препятствии в кадре 111; CAUTION на половине кадров пустого тоннеля; с
командой организаторов `ros2 bag play <бэг>` без флага очереди все результаты устаревшие; архив
образа для шага 1 README не опубликован.

## Result

The organizers publish no weights; the maxima below are the team's reading of the spec (8.1 is
"the main criterion", 8.8 "has less weight"). Lanes follow [`PLAN.md`](PLAN.md) and
[`CAPTAIN.md`](CAPTAIN.md) §8.

| # | criterion | max | score | in one line | lane |
|---|---|---:|---:|---|---|
| 8.1 | Functionality | 25 | **14.5** | the real obstacle is found in every run, early, at the right distance; 1 % STOP frames on the short empty recordings; but 2.3 false STOP episodes per km on the ride, a GO frame with the obstacle present, CAUTION on ~half of empty frames, and no sustained STOP for a real person at 60 m in 4 of 15 transplanted windows | P3 (detector), P4 (evaluation) |
| 8.2 | Range | 15 | **7** | 2 m boxes from ~100 m; a real person sustained to 60 m in 73 % of windows, 100 m in 40 %, 160 m in 7 %; 0.3 m cubes from 35–56 m | P3 |
| 8.3 | Speed | 10 | **7.5** | 10 fps, e2e p95 85–94 ms at 360° and 49–78 ms at 120° on 4 vCPU, < 1.1 core; but slow start-up catch-up and stale output under the default player | P1 (node), P3 (detector cost) |
| 8.4 | Generalization | 15 | **7** | map-free per-frame tunnel model and auto-calibration are the right idea; transfer to other tunnels is uneven (trusted-axis limits, special-case rules tuned on 7 recordings) | P3, P4 |
| 8.5 | Technical quality | 10 | **7** | clean library/node split, 753 passing tests, strong CI, native kernels with fallback; 323 parameters, dead flags, 16 k lines of Markdown with stale claims | P1 (CI, Docker, docs), P3 (code) |
| 8.6 | Ease of launch | 10 | **7** | builds from scratch in 79 s and runs with the default command; but no published image archive, `--read-ahead-queue-size 10` and `--net=host` are required | P1 |
| 8.7 | Team approach | 10 | **8** | hypotheses, rejected variants, pre-registered criteria and limitations are recorded; over-tuning to the organizers' objects and a scattered record cost points | all; P1 edits |
| 8.8 | Pitch | 5 | **3** | the deck follows problem → idea → algorithm → demo → results; silent video, placeholder team slides, dense text, no rehearsal yet | P2 (pitch, deck, video; since 28.09) |
| | **Total** | **100** | **61** | | |

The captain's own criteria (8.3 node side, 8.5 CI / Docker / docs, 8.6) come to **21.5 of 30**;
the pitch and the video (8.8) moved to P2 on 28.09. The work that would raise them is in
[`CAPTAIN.md`](CAPTAIN.md) §3.

## How it was judged

* **Independence.** Nothing was taken from the documents: the earlier scorecard, the judge
  reports and the captain board's scores were not read before scoring. A second reviewer (a
  separate agent, same rule) audited code and documents for 8.5–8.8; its findings were checked
  and merged into the scores below.
* **Machine.** A 4-vCPU cloud sandbox (15 GB RAM), Docker 29.3. The runtime image was built from
  `docker/Dockerfile` at `464f5bc`; the sandbox's proxy needed a CA file, apt over https and the
  base image from `mirror.gcr.io` (Docker Hub answered 429): a sandbox-only shim, the image content
  is the Dockerfile's ([diff](evidence/judgement_2026-09-28/scripts/Dockerfile.sandbox.diff)).
* **Data.** The organizers' `Датасет.zip` from their link (sha256 matches
  `scripts/cold_bags.sha256`), all six recordings; `cloud_with_fake_obj` (their ten ray-cast
  objects, "set O") and the 20-minute ride `new_data` from their Yandex Disk links.
* **Runs.** `pytest`, `ruff`, `detector_freeze.py verify`; the Docker build; 11 runs of the jury
  chain with the judge's own listener; the detector offline on every frame of the six recordings,
  set O and the ride; a range test that pastes the real person of `doubleT_obstacle` into the
  other tunnels (15 windows × 6 ranges); GitHub state (tags, releases, CI).

## What was measured

### Jury chain (`docker run` default command → `ros2 bag play` as uid 1000 → `/resense/*`)

| bag | player | runs | frames with a result | decisions after the first STOP | first STOP | e2e p95, current results | node p95 | CPU | RSS |
|---|---|---:|---|---|---|---|---|---|---|
| `doubleT_obstacle` (360°, 24 MB clouds) | README step 3 (`--read-ahead-queue-size 10`) | 5 | 200–201 of 201 (170 in the first run after the build) | STOP except **GO at frame 111** (4 of 5 runs; frame 197 in the fifth), CAUTION at 117 and 197 | frame 8, 1.0–1.4 s after the first cloud (frame 11, 2.5 s in the first run); 55.5–56.6 m | 85–94 ms warm, 87–172 ms cold | 79–98 ms | 0.8–1.0 core | 430–740 MB |
| `roundT_doubleT` (120°, clear) | README step 3 | 3 | 252 of 252 | no STOP; CAUTION 170–176, GO 58–81, FAULT 1–18 at start-up | — | 49–78 ms | 56–75 ms | 0.5–0.8 core | 130–250 MB |
| `doubleT_obstacle` | the organizers' literal `ros2 bag play <bag>` (Humble defaults) | 3 | **57–135 of 201** | STOP, **every result flagged stale** (queue lag median 11 s) | frame 21–24 | — (stale) | 79–88 ms | 1.0–1.3 core | 1.0–**4.0 GB** |

e2e = the judge's listener receives the input cloud → receives the status with the same stamp.
Over all frames, start-up included, e2e p95 is 0.5–1.1 s on the obstacle bag: the node catches up
on the player's initial burst for the first seconds. The 8-core i7 stand was not available.

### Detection and false alarms, offline on every frame (`resense run --bag`, default config)

| recording | frames | STOP frames | STOP episodes (distance) | CAUTION frames |
|---|---:|---:|---|---:|
| `doubleT_obstacle` (person crossing at 55–57 m, object on the rail) | 201 | 190 | one, frames 8–200 (55.5–56.6 m), **GO at frame 111** | 2 |
| `roundT_doubleT` | 252 | 0 | — | 173 (69 %) |
| `doubleT_platform` | 345 | 3 | 1 (31–39 m) | 196 (57 %) |
| `roundT_pressureGate_roundT` | 268 | 2 | 1 (53–54 m) | 119 (44 %) |
| `roundT_squareT_pressureGate_squareT` | 545 | 0 | — | 190 (35 %) |
| `squareT_platform_squareT_switch` | 877 | 18 | 5 (83–148 m) | 443 (51 %) |
| **five empty recordings** | **2 287** | **23 (1.0 %)** | **7** | **1 121 (49 %)** |
| the ride `new_data` (20 min, 13.0 km, no obstacles; detector reset every 5 s split) | 11 271 | 164 (1.5 %) | **30** (from 15–140 m): **2.3 per km**, ~96 per hour | 4 142 (37 %) |

### The organizers' objects (`cloud_with_fake_obj`, 1 510 frames, offline)

Matched when a STOP detection lies within 3 m of the object's box along the track; "inside" =
frames with object points inside the envelope (labels by P4 from the organizers' appended points).

| object | size, m | inside frames | STOP frames inside | first STOP |
|---|---|---:|---:|---:|
| box, centre | 2 × 2 × 2 | 213 | 208 (98 %) | 98.0 m (its first appearance) |
| box on top of the envelope | 2 × 2 × 2 | 75 | 56 (75 %) | 111.5 m |
| long low object on the rails | 0.5 × 2 × 0.2 | 77 | 52 (68 %) | 87.3 m |
| cube, centre | 0.3 | 63 | 32 (51 %) | 55.8 m |
| cube on the rail | 0.3 | 33 | 26 (79 %) | 48.0 m |
| cube, envelope edge | 0.3 | 16 | 16 | 35.0 m |
| box, envelope edge | 2 × 2 × 2 | 8 | 8 | 28.7 m |
| hanging, 5 cm | 0.05 × 1.5 | 20 | 14 (70 %) | 30.1 m |
| cube outside, near (not an obstacle) | 0.3 | — | 0 | — |
| box outside (not an obstacle) | 2 × 2 × 2 | — | 9 false STOP frames | 142 m |

Plus 22 STOP detections near no object. `clear_distance` extends past an object inside the
envelope in 300 of the 605 frames that hold one (68 of them `GO`): it is not a guarantee of an
empty track, as README says.

### A real person pasted into the other tunnels (range and transfer)

The person of `doubleT_obstacle` (bag frames 20–49) cut out with its label box and pasted onto the
detector's own track axis in the five obstacle-free recordings, three 3-second windows each, at a
fixed distance, thinned to (55.5 / r)² of its points. Sustained = STOP at the person on ≥ 15 of the
30 frames. No window had a STOP without the person (controls 0 / 15).

| range | 60 m | 80 m | 100 m | 130 m | 160 m | 200 m |
|---|---|---|---|---|---|---|
| sustained STOP | **11 / 15** | 8 / 15 | 6 / 15 | 2 / 15 | 1 / 15 | 0 / 15 |
| any STOP | 14 / 15 | 11 / 15 | 11 / 15 | 6 / 15 | 6 / 15 | 3 / 15 |

The misses are CAUTION, not silence: the cluster is demoted as `beyond_axis` when the trusted axis
range drops below its distance (in one platform window it is 45 m for the whole window, person or
not), or merges with trackside structure into a `column`. Caveats: no occlusion shadow is cut
behind the pasted person; placement uses the detector's own axis; one person, one posture set.

### Software

* `pytest`: **753 passed**, 1 deselected (needs the ride cache), 6 subtests, 168 s; `ruff` clean;
  parameter copy in sync; `detector_freeze.py verify` PASS (31 files).
* Docker: the runtime image builds from a clean checkout in 79 s (base image cached), 2.08 GB on
  disk, native kernels compiled and enabled; default command
  `ros2 launch resense_ros detector.launch.py freshness_mode:=replay`.
* GitHub: CI green on `main`; **0 tags, 0 releases** at judging (`v1.0.0` is scheduled for 28.09
  21:00 Moscow time).

## Per criterion

### 8.1 Functionality — 14.5 / 25

For: the real obstacle is found in every run, from the first frame the person is inside the
envelope (frame 8) offline and in 4 of 5 README-procedure runs, at the right distance (55.5–56.6 m
against labels 55.4–56.6 m), and held to the end of the bag; 1 % STOP frames on the five empty
recordings and 1.5 % on the ride; every in-envelope object of the organizers gets a STOP; the
outside cube never does.
Against: on the ride 30 false STOP episodes in 13 km (2.3 per km, one every ~38 s of riding), 15 of
them starting inside 60 m; a single **GO with the obstacle in view** (frame 111, reproducible) — a
consumer that acts on one frame would release the brake; CAUTION on 35–69 % of empty-tunnel frames,
so CAUTION carries little information; 9 false STOP frames on the outside box and 22 stray STOPs on
set O; in the transplant test a real person at 60 m got no sustained STOP in 4 of 15 windows.
Raise it: hold a confirmed track over two misses (the GO at 111); cut the ride's false STOPs
(traced per episode first); explain or cut CAUTION on empty track; the `beyond_axis`
demotion of on-axis objects (P3; the detector is frozen, so the captain decides).

### 8.2 Range — 7 / 15

For: big objects from ~100 m (the 2 m box from its first appearance at 98 m, the box on top of the
envelope from 111 m, the plank on the rails from 87 m); a real person sustained to 100 m in
6 of 15 windows and to 130–160 m in the best ones.
Against: the spec's "100 m — good" is reached for a person in 40 % of windows; small objects
(0.3 m) only inside 35–56 m, the 5 cm hanging object from 30 m, edge objects from 29–35 m — inside
braking distance at line speed. The LiDAR returns nothing past ~210 m, so 300 m is out of reach
for anyone; 200 m needs multi-frame evidence, which is off without a speed input.

### 8.3 Speed — 7.5 / 10

For: 10 fps sustained with no node-side losses in steady state; e2e p95 85–94 ms (360°, 24 MB
clouds) and 49–78 ms (120°) on 4 vCPU; decode ~30 ms + detect ~35–50 ms; under one core; RSS
130–740 MB; C++ kernels, CPU only.
Against: at 360° the p95 is close to the 100 ms period (one cold run 172 ms); start-up e2e p95
0.5–1.1 s while the node catches up; with the default player the node never gets current
(57–135 of 201 frames, 11 s queue lag, 4 GB RSS). Not measured on the 8-core stand.

### 8.4 Generalization — 7 / 15

For: no classes, no map, no training on objects: the tunnel is modelled every frame from rails,
bed and walls, the mount is calibrated from the rails; the same config runs on round, square,
double-track, platform and gate sections.
Against: transfer is uneven — the same real person is a STOP from 60 to 100 m in one stretch and a
CAUTION at 60 m in another, decided by the trusted axis range; ~30 special-case rules and 323
parameters were tuned on seven recordings and the organizers' objects (some thresholds sit between
two set O objects); the learned opinion is trained on the same recordings; all false-alarm rates
are in-sample.

### 8.5 Technical quality — 7 / 10

For: the detector library has no ROS and one method per stage; the node handles input switching,
freshness, a watchdog and error reset; 753 tests, many behavioural; CI lints, tests, builds the
image, plays bags through the archive offline, checks the detector seal; native kernels are
bit-identical with a numpy fallback; one parameter source, synced and checked.
Against: 323 parameters with a dozen dead experimental modes still branched in the hot path;
functions of 110–190 lines (`Tracker.update`, node `__init__`); the node uses private rclpy calls;
76 files in `scripts/` (~13.6 k lines) against ~9 k lines of product; ~16 k lines of Markdown
with dated team process in jury documents and in config comments; stale or contradictory statements (below).

### 8.6 Ease of launch — 7 / 10

For: `docker build` from a clean checkout works; `docker run --net=host resense` needs no
arguments for a recorded bag; `ros2 bag play` from a normal user reaches it; `scripts/play_bag.sh`
does steps 0–5 in one command; the README jury block is short.
Against: README step 1 is `docker load` of an archive that is not published (0 releases; a CI
artifact needs a GitHub login); the organizers' literal `ros2 bag play <bag>` gives stale results,
so `--read-ahead-queue-size 10` is mandatory; `--net=host` is mandatory; step 0 `sysctl` for
CycloneDDS consoles.

### 8.7 Team approach — 8 / 10

For: DECISIONS (question → measurement → decision → evidence), EXPERIMENTS with the rejected
variants and their numbers, pre-registered acceptance criteria that were also failed and said so,
limitations stated next to results, held-out numbers separated from in-sample ones.
Against: rules were added one per organizer object and several thresholds are bracketed by them;
the record is spread over a 3.7 k-line log and partly describes an older detector.

### 8.8 Pitch — 3 / 5 (materials only)

For: 16 slides in the spec's order with the hero frame (the real person crossing at 55–57 m); a 2:50
overview video with Russian subtitles and a 69 s Docker + RViz chain clip.
Against: the video is silent; team slides carry roles but no names; several slides hold
~1 000–1 100 characters; the headline false-alarm figure is the in-sample 2.5 per km (labelled as such, 2.8 held out next
to it); rehearsals and the
live remote demo are not done yet (only people can close these).

## Since the judgement (29.09, not re-scored)

The scores above stay those of 28.09 evening; nothing below was judged independently.

* **Node start-up (8.3):** a faster decode giving the same arrays byte for byte, a warm-up before
  listening, and a recording's start-up burst caught up at 5 Hz. Results of the first 3 s at 360°
  are 38–105 ms old instead of 312–325 ms (median). With the page cache dropped: 120–300 ms instead
  of 829–1029 ms. Decisions are identical
  ([evidence](evidence/node_startup_2026-09-29/README.md)). The node exits cleanly on Ctrl+C;
  `check_dry_run.py` reports the playback pace. 770 tests pass.
* **Documents (8.5):** README cut to the jury path and the results. The full experiment log,
  the dated changelog and the dated records moved to [`archive/`](archive/README.md); a compact
  EXPERIMENTS replaces the log. The stale statements in the table below are corrected, except the
  release (still unpublished) and the deck's figures (P2 rebuilds the deck). The GitBook
  ([resense.gitbook.io/resense-docs](https://resense.gitbook.io/resense-docs/)) is synced and
  gained a results page and a team-approach page.
* **Pitch and video (8.8):** owned by P2 since 28.09.
* `tracking.hold_misses` 2, the fix for the GO at frame 111 suggested under 8.1, was measured on
  the branch `gpt-score-push-20260928`: it fails the strict gate (more false alarms on the ride and
  the empty recordings) and is rejected.

## Stale or contradictory statements found (to fix)

| where | says | is |
|---|---|---|
| README step 1, «Где взять архив» | `docker load -i resense-image-<версия>.tar.gz` | no tag and no release on GitHub at judging (~19:50 Moscow time; `v1.0.0` is scheduled for 21:00): the jury has no archive to load until it is published |
| README «Где взять архив», ARCHITECTURE | the working branch `claude/amazing-fermi-t67v8g` | merged as PR #20; `main` is the branch |
| ALGORITHM §3 and §6 | `cluster.floating_free_max_dy` 0.95 m | `configs/default.yaml`: 1.2 |
| EXPERIMENTS "Current results" | 13 events on the five empty bags, 45 on the ride (26.09 detector) | the sealed 27.09 detector (see above) |
| EXPERIMENTS §7, §8 | the learned second opinion "not shipped" | shipped: `tracking.doubt_model: track_opinion.json` |
| deck slide 5 vs README | p95 "87–118 ms" vs "102 ms cached, 118 ms cold" | this judgement: 85–94 ms warm, 87–172 ms cold |
| README parameters, `bag:=` row | launch with `bag:=` | without `freshness_mode:=replay` the node's default `live` gives FAULT on a recorded bag |

## Top risks on the hidden control data

1. A person or object beyond the trusted axis range, or next to trackside structure, is CAUTION,
   not STOP — in this judgement 4 of 15 windows at 60 m (platform and double-track sections).
2. Small or edge objects are found only inside ~30–56 m.
3. The jury plays the bag the literal way (`ros2 bag play <bag>`): every result stale, few frames.
4. A single GO frame between STOPs is read as "clear".
5. False STOPs at platforms and switches (5 episodes on one 88 s recording).
