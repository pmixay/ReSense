# Independent judgement, 13.10.2026 — ReSense detection system: 66 / 100

> Strict independent evaluation of the detection system (not the web interface) against the case 05 ТЗ §8.
> Judge: an independent agent that did not read prior scores or self-assessments until its own scores were final,
> and credited only what it reproduced. Weights are an assumption (the ТЗ publishes none):
> 8.1 = 25, 8.2 = 15, 8.3 = 10, 8.4 = 15, 8.5 = 10, 8.6 = 10, 8.7 = 10, 8.8 = 5.
> Headline numbers were recomputed from the per-frame CSVs by the lead and match.

## 0. What was judged

- **Commit:** `2cb0463` (branch `claude/eloquent-volta-qcxq9d`). `git diff` of `resense/`, `native/`, `configs/`,
  `ros2_ws/`, `docker/` against `main`'s CI commit `317eabf` and release tag `v1.0.0` (`5d6e9b5`) is empty: the same
  detector.
- **Detector fingerprint:** `scripts/detector_freeze.py verify` → PASS, 36 files,
  source `075a20df9fcdba6605a92e6505ae4dfdb3bf410ec09d17a8b3c79ce714db9292`.
- **Config:** `configs/default.yaml` exactly as shipped (identical to the ROS package copy).
- **Environment:** sandbox, 4 vCPU, 15 GB RAM; Python 3.13 venv with the native C++ kernels loaded; Docker 29.8.
- Every README / docs number was treated as a claim; credit only for what was measured, plus GitHub CI and release facts.

## Scores

| criterion | max | score | confidence | one line |
|---|---:|---:|---|---|
| 8.1 Работоспособность | 25 | **15** | medium-high | Real obstacle and all 8 in-gauge organizer objects get STOP. But ~91 false STOP episodes per hour of empty tunnel, CAUTION on 43 % of empty frames, and silent misses (tall narrow objects, objects next to long edge structure on curves). |
| 8.2 Дальность | 15 | **9** | medium | On straight track: person-size box ~220 m, 1 m box ~150 m (ideal ray-cast). On curves / double track only 41–75 m. 0.3 m objects ~45–56 m. |
| 8.3 Скорость | 10 | **7** | medium (4 vCPU, not the stand) | 120° is real-time with margin (node p95 84 ms, 0.44 core). 360° p95 is 106–119 ms and the node lags up to 1.2 s. The organizers' default `ros2 bag play` gives stale results. |
| 8.4 Обобщаемость | 15 | **8** | medium | Map-free model of the normal tunnel and tilt robustness are good. Against it: 333 parameters, rules tuned to named recordings/objects, a learned model trained on the ride itself, false alarms sensitive to small input changes, range collapse on curves. |
| 8.5 Техническая проработка | 10 | **7** | medium-high | 1,284 tests pass, ruff clean, CI green (including Docker), freeze verify passes. Very high complexity, dead code paths, a few claims not reproduced. |
| 8.6 Простота запуска | 10 | **8** | high (archive path) | Release archive verified; offline `docker load` + `docker run` work in ~3 s; topics auto-discovered. A non-default player flag is required, and `docker build` needs internet. |
| 8.7 Подход команды | 10 | **8** | low-medium | Hypotheses, gates, rejected approaches and a safety review are recorded; every rule tuned on development data, no held-out real data. |
| 8.8 Питч | 5 | **4** | low (files only) | 16-slide deck in the organizers' template, 3-minute video, Docker+RViz clip; slides text-dense, headline numbers favourable. |
| **Total** | **100** | **66** | | |

## Top 10 problems

1. **8.1/8.4, critical — tall narrow obstacles are never STOP.** A 0.3 × 0.3 × 2.8 m pole inside the envelope is demoted
   as `column`. On the axis: CAUTION from ~70 m down to 5 m; 0.7 m off-axis: never STOP (0/176 frames). The rule catches
   anything ≥ 2.2 m tall and 0.25–1 m wide, even at lateral 0, and near escalation never overrides it.
2. **8.1/8.2, high — silent GO on curves.** A person-size box with 24–40 returns at 82–120 m merges with a 46–55 m long
   corridor-edge blob and is dropped as oversize; the decision is GO (confirmed by instrumenting `_corridor_cluster`).
3. **8.1, high — false STOPs on empty tunnel.** 36 episodes / 173 frames in 1,430 s (13,558 frames), ~91 per hour;
   on the ride ~2.5 per km; 7 of the 32 ride episodes start below 40 m; a start-up false STOP at 138–145 m.
4. **8.2/8.4, high — range collapses on curves and double track.** All sizes confirmed only at 41–75 m although visible
   earlier and placed on the detector's own axis (`beyond_axis` → CAUTION, and the oversize merge of item 2).
5. **8.3/8.6, medium-high — the organizers' literal `ros2 bag play <bag>` gives stale output.** 360°: only 146/201
   frames processed, every result stale (age 7–10 s), node RSS 3.4 GB. 120°: first ~5 s FAULT.
6. **8.3, medium — 360° processing ≈ the frame period on 4 vCPU.** Offline p95 106–119 ms; with the README flags only
   35/201 node results "current", median result age 0.83 s.
7. **8.1, medium — small objects confirmed late.** 0.3 m cubes STOP only from 41–56 m. The organizers' small centred
   cube is inside the envelope at 60–95 m with decision GO. A 0.5 m cube is sustained only from 83 m.
8. **8.4, medium — overfitting risk.** 333 parameters, dozens of rules justified by named recordings/objects; the
   learned "doubt" model was trained on the ride's own tracks (ride false-alarm rates are in-sample); platform/switch
   false STOP episodes go 3 → 4–14 under ±2° tilt, 5 Hz input or 30 % dropout; removing duplicated dual-return echoes
   changes 4 decisions on doubleT_obstacle and drops CAUTION 51 % → 11 % on squareT_platform.
9. **8.1, medium — advisory and clear-distance outputs unreliable.** CAUTION on 43 % of empty frames; `clear_distance`
   reports the path clear beyond a visible in-gauge object in 148 of 694 set O frames (90 of them GO).
10. **8.5, low-medium — complexity.** 22 disabled experimental rules wired in the code, ~60 dated docs, 8 tests depend
    on hard-coded personal paths (`D:/Datasets`, `C:/Users/alikh`), several documentation claims did not reproduce.

## 1. Data processed

Every frame of every organizer recording, **15,279 frames**; checksums matched for the zip, both cold bags and
`new_data.zst`.

| recording | frames | notes |
|---|---:|---|
| doubleT_obstacle | 201 | also replayed through the node in Docker (3 runs) |
| doubleT_platform | 345 | |
| roundT_doubleT | 252 | also replayed through the node in Docker (2 runs) |
| roundT_pressureGate_roundT | 268 | |
| roundT_squareT_pressureGate_squareT | 545 | |
| squareT_platform_squareT_switch | 877 | |
| cloud_with_fake_obj | 1,510 | |
| new_data | 11,271 / 11,271 (all 221 splits) | one detector instance, strictly in temporal order |

The ride archive's tar members arrive out of order, so it was streamed twice: a producer stored the needed splits
zstd-recompressed (~78 MB each), a consumer fed them to one detector in order. Peak disk ~14 GB.

**Method** (`scripts/judge_runner.py`): the node's input path — `fastcloud` decode of the raw CDR bytes, header stamp,
`ring=None` without a ring field, the node's continuity rules (stamp hole > 1 s resets the scene, > 30 s a new
detector), auto-calibration on, `ego_speed=None`, and the node's decision rule (STOP if obstacle; FAULT on health error;
CAUTION on a warning object or health warn; else GO). The Docker node reproduced 193/201 STOP on doubleT_obstacle.

**Labels.** cloud_with_fake_obj: the organizers' appended points were extracted independently (after the last empty
slot; all intensity 1); all 1,206 labelled object-frames match within 1 m (median 0.00 m). The organizers' tool emits
points up to ~298 m, beyond the real sensor's ~210 m. Inside/outside by the organizers' stated intent: inside #1–4, 6,
8–10; outside #5, #7. doubleT_obstacle: an own rail fit (no detector code) confirms the person crossing at 55.5–56.5 m
and the object across the right rail at ~56 m; in-gauge window frames 8–68, ±2 frames at each end.

## 3. 8.1 measurements

**Real obstacle (doubleT_obstacle):** STOP 193, GO 8 (frames 0–7), CAUTION 0, FAULT 0. First STOP at frame 8 (0.8 s),
55.53 m — the first frame the person is in the gauge. Person in gauge: 61/61 frames STOP; after the person leaves,
STOP on the object on the rail at 56.1–56.2 m. Frames 0–7 GO although the object on the rail is present (start-up
confirmation). In Docker: STOP 193 / FAULT 8; first STOP 1.0 s after the first result.

**Organizers' objects (cloud_with_fake_obj):**

| object (intent) | first STOP (m) | held ≥ 90 % from (m) | notes |
|---|---:|---:|---|
| big_center (inside) | 98.2 | 98.7 | STOP from its first appearance (98.7 m) |
| small_center (inside) | 55.8 | 60.8 | **GO at 65–95 m while inside the envelope** |
| small_on_rail (inside) | 48.0 | 51.5 | |
| small_edge_inside (inside) | 35.0 | 38.7 | |
| big_edge_inside (inside) | 28.2 | 30.2 | |
| big_above (inside) | 111.4 | 123.6 | |
| long_low_on_rails (inside) | 89.0 | 97.7 | |
| thin_hanging (inside) | 30.1 | 31.8 | |
| small_outside_near (outside) | none | — | 0 STOP — correct |
| big_outside (outside) | 142.3 | — | 9 STOP frames at 130–142 m |

big_outside STOPs are ambiguous (measured from the rails, the box intrudes 0.2–0.5 m into the envelope there; the
organizers allow for imprecise synthetic placement). The two edge objects lie outside the rails-measured envelope until
~27 m: defensible by that definition, misses by the organizers' intent. No false STOP in the 706 object-free frames; the
only unmatched STOPs are 6 single frames right after an object passes under 2.5 m. `clear_distance` overclaims in
148/694 object frames (90 of them GO).

**Obstacle-free data:**

| recording | STOP frames | STOP episodes | CAUTION |
|---|---:|---:|---:|
| roundT_doubleT | 0 | 0 | 67 % |
| doubleT_platform | 0 | 0 | 58 % |
| roundT_pressureGate_roundT | 2 | 1 (bed-level object at 54 m) | 43 % |
| roundT_squareT_pressureGate_squareT | 0 | 0 | 35 % |
| squareT_platform_squareT_switch | 11 | 3 (148 / 83 / 140–146 m) | 51 % |
| five bags total | 13 (0.57 %) | 4 | 49 % |
| ride, 1,200 s | 160 (1.42 %) | 32 (20 events after merging within 1 s) | 42 % |
| all, 1,430 s | 173 | 36 → ~91 / hour | 43 % |

Ride per km: ~2.5 episodes/km with the team's 13 km; 3.7/km with the detector's own 8.6 km. The 32 ride episodes start
at: 16 beyond 100 m, 9 at 40–100 m, 7 below 40 m. Start-up false STOP 1.0–3.8 s into the ride. The last third of the
ride has 23 stamp holes of 1.2–7.1 s; each resets the scene (replicated).

**Dynamic and shape probes (own ray-cast, straight tunnel):**

| probe | result |
|---|---|
| person-size box crossing the track at ~130 m | STOP 0.4 s after entering the gauge, released after it leaves |
| same crossing at ~60 m | STOP after 0.5 s |
| box receding at 5 or 8 m/s | STOP from 96–97 m |
| object appearing at 100 m / 60 m | STOP after 0.6–0.7 s |
| **pole 2.8 m, on the axis** | CAUTION from ~70 m to 5 m |
| **pole 2.8 m, 0.7 m off the axis** | never STOP |
| 5 cm cable | STOP from 60 m, sustained from 43 m |

## 4. 8.2 measurements

**Method.** Backgrounds: real 120° frames of four recordings — A straight (R > 7 km); B curve (R 700–1100 m) into a
double-track section; C curves with a pressure gate (R 400–1100 m); D train braking into a platform; S standing at the
platform. Train motion from ICP odometry, validated against the organizers' world-static objects (2 cm/frame median
error, +3 % cumulative bias). A world-static box starts 230 m ahead and approaches by the train's travel, placed on the
detector's own baseline axis and rail-head height (favourable to the detector). Ray-cast on the sensor's own grid with
occlusion; returns are ideal unless a range-dependent dropout is applied (full to 120 m, half at 200 m — an assumption).

| background | object | first STOP (m) | held ≥ 90 % from (m) |
|---|---|---:|---:|
| A straight | person-size box | 218 | 222 |
| A straight | person-size box, with dropout | 209 | 204 |
| A straight | person-size box, ±0.5 m off axis | 218 | 222 |
| A straight | 1 m cube | 151 | 163 |
| A straight | 0.5 m cube | 135 | 83 |
| A straight | 0.3 m cube, or 0.3 × 0.3 × 0.15 on the rail head | 45 | 49 |
| B curve → double track | person / 1 m / 0.5 m / 0.3 m | 52 / 50 / 50 / 41 | — |
| C curves + pressure gate | person / 1 m / 0.5 m / 0.3 m | 74 / 74 / 75 / 42 | — |
| D braking into platform | person / 1 m cube | 106 / 106 | — |

In B the objects are visible at 60–95 m but get CAUTION (`beyond_axis`). In C the person-size box is visible at
82–120 m but gets GO (oversize merge, problem 2). Standing at the platform (S), a person-size box gets STOP in only
83/260 frames at 100 m and 92/259 at 150 m; sustained only at 60 m.

## 5. 8.3 measurements

Offline, quiet machine, single process:

| cloud | decode+detect p50 / p95 / max | frames > 100 ms | CPU | RAM |
|---|---|---:|---|---|
| 360° | 78–86 / 106–119 / 129–212 ms | 18–34 of 200 | ~1 core at 10 Hz | 209–263 MB |
| 120° | 49–60 / 72–76 / ≤ 98 ms | 0 | ~0.6 core | 127 MB |

Docker, release image; node, player (uid 1000) and listener each in its own container:

| run | frames processed | results current | result age p50 / max | node latency p50 / p95 / max | CPU / RAM |
|---|---:|---:|---|---|---|
| 360°, README flags | 201/201 | 35/201 | 0.83 / 1.2 s | 88 / 111 / 197 ms | 0.66 core / 517 MB |
| 360°, literal default `ros2 bag play` | 146/201 | 0 | 7.3 / 10.5 s | 77 / 112 / 134 ms | 0.69 core / 3.4 GB |
| 120°, README flags | 252/252 | 242 | 0.06 / 0.31 s | 54 / 84 / 99 ms | 0.44 core / 165 MB |
| 120°, literal default | 252/252 | 196 (first ~5 s FAULT) | 0.06 / 1.46 s | 49 / 72 / 90 ms | 0.41 core / 418 MB |
| 360°, renamed topic | 201/201 | 94/201 | 0.30 / 1.2 s | 82 / 107 / 132 ms | 0.61 core / 540 MB |

Renamed topic: auto-discovered; first STOP 1.1 s after the first result. Node start to "listening": 3.1–4.2 s including
a 1.2 s warm-up.

## 6. 8.4 measurements

`configs/default.yaml` has 333 leaf parameters; 22 are disabled experimental rules still in the code. Comments justify
enabled rules by specific recordings or objects ("set O #2/#6", "doubleT_platform 37–38.5 m", "roundT_doubleT column
101–149 m", "doubleT_obstacle frame 111"); 40 such references in `resense/*.py` alone. The doubt model (gradient-boosted
trees, 19 features) was trained on negative tracks from the ride and two bags plus synthetic positives.

| perturbation | doubleT_obstacle STOP frames (of 193 after frame 8) | squareT_platform false STOP episodes | squareT_platform CAUTION |
|---|---:|---:|---:|
| none | 193 | 3 | 51 % |
| tilt ±2° / roll +2° | 192–193 (person 60–61/61) | 4–7 | 48–50 % |
| yaw +3° or 2 cm noise | 193 | — | — |
| 5 Hz input | 95 of 97 frames | 9 | 46 % |
| 30 % point dropout | 154 | 14 | 42 % |
| 50 % point dropout | 126 | — | — |
| one echo per dual return | 189 | 3 | 11 % |

roundT_squareT stays at 0 false STOPs under every perturbation. On set O, dropout or 5 Hz moves the small-object first
STOPs by 5–19 m.

## 7. 8.5 measurements

pytest: 1,284 passed, 8 deselected (they need local data caches at hard-coded paths). ruff 0.15.8: clean with CI's
exclusion. CI run 36618421427 on main `317eabf` (same detector): all 5 jobs green (checks, pytest, webapp,
offline-build, docker — Dockerfile build, tests inside the image, bags through the node). Architecture: clean split
between the library (~7.6k lines) and the node (1,339 lines); optional C++ kernels with a numpy fallback. Documentation
extensive and candid; reproduced: doubleT_obstacle STOP 193/201 from frame 8; set O first-STOP distances; 1,284 tests;
the release archive; first STOP ~1 s after the first cloud; CAUTION 35–69 % on empty data; ~2.3–2.5 STOP episodes per km.

## 8. 8.6 measurements

Following the README's jury section literally: the `sysctl` socket-buffer step is needed only for some DDS players;
release v1.0.0 has the 477 MB archive and its sha256 verifies; `docker load` 67 s; `docker run --net=host --ipc=host
resense` starts the node in replay mode, offline, in ~3 s (also with `--network none`); the player needs
`--read-ahead-queue-size 10`; a containerised non-root player needs HOME set (the team's script does); `ros2 topic echo`
of the decision and distance works. 5–6 manual steps with two pitfalls; `scripts/play_bag.sh` wraps them (not run here;
its CI step is green).

## 9. 8.7 and 8.8

8.7: hypotheses, pre-registered gates, rejected variants with numbers, adopted rules from other teams and a safety review
that removed one of them are recorded. All tuning used the development data; no held-out real set.
8.8: 16 template slides; 3:00 overview video with Russian subtitles; 69 s Docker + RViz clip.

## 10. Claims not reproduced

| claim | finding |
|---|---|
| 360° end-to-end p95 81–82 ms | 106–119 ms offline, 111 ms in the node — different hardware: not reproduced rather than refuted |
| duplicated dual returns "change no decision" | refuted (§6) |
| docker build ≈ 1.5 / ≈ 9 min | not runnable here (sandbox proxy rejects plain-HTTP apt); CI shows 1 min 43 s |
| five empty bags: 12 STOP episodes / 39 frames (team's frame cache) | 4 / 13 on the raw bags — better than claimed (different pipeline) |
| team synthetic range: person 151 m, 1 m box 124 m | different test; see §4 |
| real person transplanted into five tunnels | not re-run (refers to the older detector) |

## 11. Not measured

Literal `docker build` (sandbox proxy; credited from the green CI job; the published archive was tested instead); the
i7-9700E stand (all timings on a 4-vCPU VM); `ros2_ws` tests on the host (no ROS on the host; they run in CI inside the
image); real obstacles at other distances / tunnels (none exist; range from synthetic ray-casts); far-field track
geometry (objects placed on the detector's own track model, favouring the detector); ride distance (team's 13 km used);
pitch delivery and 8.7 process quality (files only).

## 12. After scoring: disagreements with prior judgements

Read only after `scores.json` was final; nothing changed.

| criterion | SCORECARD 28.09 (61) | review 28.09 (69) | review 29.09 (65) | this (66) |
|---|---:|---:|---:|---:|
| 8.1 | 14.5 | 16 | 16 | 15 |
| 8.2 | 7 | 7.5 | 6 | 9 |
| 8.3 | 7.5 | 8 | 8 | 7 |
| 8.4 | 7 | 8 | 6 | 8 |
| 8.5 | 7 | 8 | 9 | 7 |
| 8.6 | 7 | 8.5 | 8 | 8 |
| 8.7 | 8 | 9 | 9 | 8 |
| 8.8 | 3 | 4 | 3 | 4 |

8.1: fewer false STOPs on the five bags than earlier (on the older detector), and two silent-miss mechanisms none of
them mention (`column`, the oversize merge on curves). 8.2: higher because this range test moves the object toward the
train; the earlier constant-distance transplant is blocked by the current ego-motion veto by design. 8.5: complexity,
dead code and personal-path tests weigh more than in the internal 9. 8.6: above SCORECARD's 7 because the image archive
is now published and verified; "build from scratch in 79 s" not reproduced.

## 13. Files

`scores.json`; `out/<recording>.csv|.jsonl|.meta.json` for all 8 recordings (`new_data.csv` 11,271 rows);
`out/empty_summary.json`, `out/cloud_with_fake_obj.score.json`, `out/fake_gt_judge.json`; range, probe, timing and Docker
outputs (in the repository archive: `raw.tar.xz`); `scripts/` (node-faithful runner `judge_runner.py`, the ride stream
processor, scorers, ICP odometry, range and probe tools, clustering debug, Docker chain scripts).
