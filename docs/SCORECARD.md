# Criteria judgement (spec §8) — v0.6.1, 23.09

**How this was judged.** Two independent reviewers with no stake in the work read the whole
repository against the organizers' criteria (technical specification §8, the Q&A session, the
written answers of 23.09, [`organizers/answers.md`](organizers/answers.md)). One judged the
results (8.1–8.4), the other the engineering, launch, method and pitch (8.5–8.8 and the §7.2
deliverables). Both were told to distrust the team's own claims and to check them against the
code, the labels and the experiment records. The team then re-checked every finding. Confirmed
errors were fixed on 23.09 (marked **fixed**); findings that need more than an hour are in
"What is left". The earlier self-assessment ("good" / "very good" everywhere) was too generous
on 8.1, 8.2 and 8.6 and is replaced by this file.

## Scores

| § | criterion (weight) | score /10 | verdict | strongest evidence | what holds the score down |
|---|---|---|---|---|---|
| 8.1 | **Works: detects, stable across sections, few misses, few false alarms, unseen data** (main criterion) | **5** | reliable on tall objects; misses what the organizers named as small; too many false stops | the real crossing person in 58 of 61 envelope frames, first alarm 0.3 s after entering (`labels/doubleT_obstacle.json`); false alarms counted on all 13 759 real frames (EXPERIMENTS §0, §1d); tall objects 6 of 6 on the moving ride (§2d) | **the organizers' object on the rail: 27 of 185 frames** — it straddles the envelope floor and falls between the two detection stages (re-measured 23.09, below); a 30×30×10 cm box on the bed is not reported by design; a 0.5 m box in the bed 2 of 6; the ride: **82 events in 20 min (4.1 per minute, 6.3 per km)**, station ends unchanged since v0.5 |
| 8.2 | **Range** (300 excellent / 200 very good / 100 good; balance with reliability and false alarms) | **6** | tall objects first confirmed at ~150 m on straight track; sustained detection only to ~100 m | honest physics (farthest return in all data 208.5 m, 300 m impossible); paired runs with and without the far-field rule (person 106 → 150 m); 177 m with a train speed (§2d) | "first confirmed" is the first hit, not sustained detection: person frame recall 68 % at 100–150 m, 10 % at 150–200 m; 6 approaches per object on hand-picked straight sections, objects within ±0.6 m of the axis; objects < 0.6 m cannot alarm beyond ~100 m; curves: 2 approaches, 1 detected |
| 8.3 | **Speed: latency, FPS, CPU/GPU, real-time stability** | **7** | the detector is comfortably real-time; the ROS chain was never timed on real data | 42–58 ms mean, p95 52–69 ms on every recording, CPU only (§3); **fixed 23.09:** CPU and memory measured — one core, 47–65 % of it at 10 Hz, 160–180 MB (§3); single-threaded BLAS in the image (it kept 3.9 cores busy for nothing); input queue of one frame so the node skips rather than lags | the i7-9700E stand and the real ROS node (decode + publish in rclpy) are not measured |
| 8.4 | **Generalisation to unseen data** | **6** | the right idea — a model of the normal tunnel, no map, no object classes — but not tested on held-out data | per-frame bed / rails / axis / curvature; mount auto-calibration verified on re-mounted real frames (§6); either topic / frame pair, per-recording restart | every variant was chosen on the same frames it is scored on; ~15 infrastructure rules tuned on these tunnels; counts move ±20 % with sub-degree mount changes, far range ±15–30 m with 0.3° of pitch; small tilts corrected only after 20 s |
| 8.5 | **Technical quality: architecture, code, robustness, reproducibility, tests, resources, docs** | **7.5** | well engineered; the ROS path is unproven on real data | pure-Python core, thin ROS node; 140 tests incl. the node against ROS stand-ins; CI builds the image, tests inside it, plays a synthetic bag; launch arguments and node parameters match one to one | the node never processed a real bag; ~196 parameters tuned and evaluated on 7 recordings; long functions (`find_clusters`, `Detector.process` ~180 lines); docs had drifted (**fixed 23.09**, list below) |
| 8.6 | **Ease of launch: `docker build → docker run → ros2 bag play → result`** | **6.5** | the right design, but the organizers' procedure has never been run | default image command starts the detector; either topic pair, discovery, per-recording restart; README "How a bag is processed" and "What to look at" | **the default branch `main` does not contain v0.6** (13 commits behind); `docker build → run → host-console bag play` never executed; **fixed 23.09:** `--delay 3` and `ROS_DOMAIN_ID` in the README steps, `ipc: host` for every compose service, `.dockerignore`, the in-image `pytest` note |
| 8.7 | **Team approach: hypotheses, experiments, failures, final choice, trade-offs** | **9** | exemplary | EXPERIMENTS §7 (ten methods side by side), §1d (rejected low-object stages: 1 482 and 734 events), §8 (learned second opinion with a leakage check, not shipped), every number marked real / synthetic | the section order (§0, §1d, §2d before §1) is confusing; tuning and evaluation share data (stated) |
| 8.8 | **Pitch** (lower weight) | **5** | good texts, no deliverable yet | PRESENTATION.md: slides 7–11 texts, slide 16 speaker text, results table with every number marked | no pptx in the organizers' template; personal data are `<…>`; the videos are v0.5 (offline renders and a dashboard replay), no RViz / Docker-chain footage and no "train → LiDAR → obstacle at X m" shot |

Indicative total (8.1 counted twice, 8.8 half): **6.4 / 10**. The weights are not published;
the ranking of what to fix does not depend on them.

## What the reviewers found, and what was done on 23.09

| finding | checked | action |
|---|---|---|
| The organizers' object on the rail "protrudes ~5 cm" (docs) — the labels say more | **confirmed**: with the final calibration its top is **0.10–0.15 m (median 0.13 m) above the detector's rail-head plane** in the 111 frames after the person leaves; at its position the pipeline produces **nothing in 99 of 111 frames** (0–3 points above the 0.12 m envelope floor, below the main stage's cluster minimum) and a 3-point low-object sliver in 12 — it falls **between** the two stages | docs corrected (ALGORITHM §3.3b / §6, EXPERIMENTS §1d, PRESENTATION); the fix is item 6 below |
| Scorecard said "no confirmed detection away from an object on backgrounds without one" | wrong since v0.6.1: the empty start of file 98 confirms 6 frames | fixed (this file) |
| Stale numbers: 35 vs 19 off-object frames, `overhead_min_height` 2.4 vs 3.0, `edge_margin_per_100m` 0 vs 0.15, "frame 7", "only obstacle is the person", "the detector uses its own speed estimate", v0.5 timing in ARCHITECTURE, "3.3°", 1 350 vs 1 482, slide 19 "21 of 74", the intermediate cover message promising accumulation to 150 m | confirmed | fixed |
| Raw results of v0.6 / v0.6.1 not in the repository | confirmed | committed: `experiments_v0.6.1_real_fullrate.json`, `experiments_v0.6.1_setF.json` |
| Curves reported as "at the sightline 74–82 m" hides the undetected approach | confirmed | wording fixed: 2 approaches, 1 detected |
| No CPU / memory figures | confirmed | measured (§3); BLAS threads limited in the image |
| Input queue of 5 frames contradicts "drops rather than queues" | confirmed | `input_queue_depth` = 1 (parameter, launch argument, test) |
| `publish()` outside the node's exception guard | confirmed | guarded (test) |
| RViz / Foxglove do not show `/resense/decision` | confirmed | the RViz status text now shows GO / CAUTION / STOP / FAULT and the clear distance (test); the Foxglove layout is item 11 |
| compose `echo` / `foxglove` without `ipc: host`; no `.dockerignore`; README bag play without `--delay` | confirmed | fixed |
| Default branch `main` 13 commits behind; no tag | confirmed | open — item 1 (needs the team's decision to merge) |
| The ROS node never ran on a real bag; the organizers' procedure never executed | confirmed | open — item 2 (needs a machine with Docker) |

Re-verified on the current code: the real person 58 / 61 from frame 11, the object 27 / 185,
`roundT_doubleT` 3 alarm frames / 2 events, `roundT_squareT_pressureGate_squareT` 0 — identical to
the v0.6.1 run; 140 tests and 6 dashboard tests pass; parameter files in sync.

## What is left (by expected gain per hour)

**Needs a person (cannot be done in the sandbox)**

1. **Merge `claude/stoic-goldberg-vxjp6g` into `main`, tag `v1.0-final`, make sure the repository
   is public.** A jury cloning the default branch today gets the v0.5-era code. 15 min.
2. **Real dry run on a machine with Docker** — `scripts/dry_run.sh` on `doubleT_obstacle` and with
   `--expect-clear` on `roundT_doubleT`; then the organizers' way: the node container plus
   `ros2 bag play --delay 3` from a host console, both topic / frame pairs, two bags one after the
   other into one node; record `docker stats` (CPU, memory) and the latency on an i7-class CPU.
   3–4 h. Moves 8.3, 8.5 and 8.6.
3. **A 1–2 minute v0.6.1 video**: build → run → bag play → RViz showing "STOP: OBSTACLE 55.x m"
   and `ros2 topic echo /resense/decision`. 2–3 h. Moves 8.8 and the §7.2 video item.
4. **The pptx in the organizers' template**: slides 7–11 unchanged with the personal data, then
   12–20 from PRESENTATION.md with the main shot. 4–6 h.
5. **Send [`QUESTIONS.md`](QUESTIONS.md)** (three questions still open). 5 min.

**Algorithm (the largest score gains)**

6. **Cluster an object that straddles the envelope floor as one object** (the low-object stage
   and the main stage currently split it at 0.12 m). Target: the organizers' object in ≥ 80 % of
   its 126 frames after the person leaves, ≤ 10 extra ride events, re-run all 13 759 frames. Also
   re-check the "low hardware" rule, which drops a dog-sized object between the rails. 1–2 days.
   Up to +1–2 on 8.1.
7. **A second round of set F**: `lowbox`, `box0.3`, a 0.5 m box on the bed and on a rail,
   `cable_low`, a dog-sized object; lateral positions up to ±1.0 m; 10+ approaches in curves and
   at stations; report the **sustained** range (from where ≥ 90 % of frames detect it) next to the
   first hit. ~1 day, mostly compute. Makes 8.1 and 8.2 credible.
8. **Fewer false stops**: persistence 0.5 s as the default (measured in §1b: fewer alarms, no cost
   on the real person), and a station-end policy when the rails are lost (CAUTION beyond ~40 m).
   Expected −20–30 % false alarms; 1 day with the full re-evaluation.
9. **A held-out check**: freeze the parameters and re-score on the halves of the ride and one
   recording left out at a time; commit the summaries. Half a day. Moves 8.4.
10. **A far height reference anchored on the tunnel vault** (measurable to ~200 m, §2d) so that
    0.3–0.6 m objects can alarm beyond 100 m; relax `far_max_bottom` for thin vertical clusters
    near the axis (cables). 2 days, some risk. Moves 8.2.

**Hardening and docs**

11. Pin the base image (or `--pull` in `build.sh`), a CI smoke test for the
    `/sensing/lidar/hesai128/pointcloud` + `lidar_livox` pair and for two bags in a row, the
    Foxglove layout with `/resense/decision`. ~2 h.
12. Faster tilt calibration for short bags (straight-track or stationary frames count as spread
    out in time). Half a day.
13. Reorder EXPERIMENTS.md (v0.6.1 first, history after), a v0.6 hero image for the README,
    regenerate `labels/new_data_objects.json` from the v0.6.1 run. 2 h.
