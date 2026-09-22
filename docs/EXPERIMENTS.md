# Experiments log

Headline numbers are for **v0.5 (real data, 2026-09-21, Sprint 2)**: every frame of the six
organizer bags cached as `*.npy` (`scripts/cache_frames.py`, 2 488 frames), pure Python on the
4-core sandbox (the jury's i7-9700E has 8 faster cores; the load of every timing run is
stated). Raw per-frame results of the v0.3 baseline are the captain's
`/data/results/v0.3/<bag>.jsonl` (commit f2c57e5, 21.09); the v0.5 runs are
`python -m resense.cli run --npy /data/cache/<bag> --out <bag>.jsonl --quiet` with
`configs/default.yaml` of commit 9b56bdf (merged as 82815e9) (per-bag summaries in
[`experiments_v0.5_real_fullrate.json`](experiments_v0.5_real_fullrate.json)); the
same-machine A/B configs are listed in §1b. Every number below is either **real** (bag named)
or **synthetic** (said so). The day-1 numbers on subsampled frames that this file carried
before 21.09 are superseded (they understated the 10 Hz false-alarm rate by an order of
magnitude, CAPTAIN.md finding 2 of 21.09).

## 1. Real bags at full rate (every frame, 10 Hz)

The five bags other than `doubleT_obstacle` contain no obstacle inside the gauge: every alarm
there is false. `doubleT_obstacle` has one true obstacle, the person crossing the track at
55–57 m (in the strict gauge in frames 2–72, `labels/doubleT_obstacle.json`).

| bag | frames | v0.3 alarm frames / events / advisory | **v0.5 alarm frames / events / advisory** | v0.5 first alarm (frame) | v0.5 alarm distances | what alarms in v0.5 |
|---|---|---|---|---|---|---|
| `doubleT_obstacle` (stationary, person crossing) | 201 | 76 / 3 / 199 | **69 / 1 / 199** | 7 | 55.5–56.6 m | the person only (v0.3: also the column row at 17–19 m and 34 m, 2 false events) |
| `doubleT_platform` | 345 | 178 / 29 / 110 | **15 / 4 / 271** | 2 | 3.0–114.5 m | a 2.1 m tall, 0.5 m wide post at 85–87 m left of the axis (10 frames; 0.1 m under the column rule), one frame of a 5 m long 0.2 m high strip at the nose at frame 177 and one 4-voxel cluster at 104.5 m |
| `roundT_doubleT` | 252 | 126 / 20 / 140 | **0 / 0 / 226** | — | — | nothing (v0.3: columns and wall segments of the diverging double-track section, pulled in by the half curvature and the yaw jitter) |
| `roundT_pressureGate_roundT` | 268 | 106 / 19 / 135 | **16 / 5 / 262** | 48 | 42.0–77.9 m | five duct / cabinet fragments at \|dy\| = 1.5–1.6 m, 42–78 m, 1–8 frames each (inner edge 0.05–0.15 m inside the 1.40 m gauge) |
| `roundT_squareT_pressureGate_squareT` | 545 | 87 / 19 / 396 | **5 / 3 / 499** | 99 | 101.3–127.2 m | three far clusters at 101–127 m (6–16 voxels), one of them lasting 3 frames |
| `squareT_platform_squareT_switch` | 877 | 504 / 105 / 680 | **60 / 20 / 779** | 67 | 71.9–119.2 m | the platform-end structure at 82.9 m while the train stands at the platform (2.2 × 0.4 × 1.2 m, lowest point at the bed, 5–8 voxels, 15 events of 1–7 frames, ~50 frames): a low ramp / rail at dy +1.2…+1.8 m by the single-frame axis that the run's left-bending curvature (R ≈ 3 km from the hall walls) puts at +0.5…+1.0 m; plus four single-frame far clusters at 87–119 m |
| **five obstacle-free bags** | 2 287 | **1 001 / 192** / 1 461 | **96 / 32** / 2 037 | | | |

The per-bag "what alarms" column and the cause table below were written for the first cut of v0.5 (89 / 29); the final defaults carry the two safety tweaks of the review of 22.09 (`wall_face_min_height` 2.0 m and `floating_max_height` 1.2 m so that a person on a platform edge stays an obstacle; `walls_max_yaw` 0.09), which add 3 alarm frames / 1 event on `doubleT_platform` (a near strip at the nose in frame 2) and 4 / 2 on the switch bag, and change nothing on the person.

Renders (`img/`): `roundT_doubleT_0145_v03.png` vs `roundT_doubleT_0145_v05.png` (the v0.3 axis pulls the
column row of the diverging double-track tunnel into the corridor, v0.5 follows the rails),
`squareT_platform_switch_0400_v03.png` vs `_v05.png` (the train standing at the platform: roof strips and
the hall end wall are advisory in v0.5), `doubleT_obstacle_0030_v05.png` (the person on the track at
55.7 m; the whole bag as `video/doubleT_obstacle_offline.mp4`).

On the labels of `doubleT_obstacle` (`resense eval --npy /data/cache/doubleT_obstacle --gt
labels/doubleT_obstacle.json --text`, 71 in-gauge person frames): v0.3 recall 63/71, first
alarm frame 9, 13 false-alarm frames / 2 events (the column row); **v0.5 recall 66/71 (93 %),
first alarm frame 7, 3 / 0 (frames 73–75, the person 0.1–0.2 m outside the gauge) false-alarm frames / events**; the person is
confirmed inside 50–62 m in 69 (frames 7–75, one track) consecutive frames.

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

## 1b. False alarms by cause (why v0.3 alarmed on 44 % of the frames) and what removed them

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

**Ablation (all six bags, every frame, same code = commit 9b56bdf (merged as 82815e9), one lever group
switched off at a time by `--config`; five-bag alarm frames / events, and the person of
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
| + `confirm_time_s: 0.5` (5 frames at 10 Hz) | 69 / 21 | 66/71, 7, 3 / 0 | latency 0.5 s = 11 m at 80 km/h instead of 0.3 s = 6.7 m; not shipped: P4's tests pin the 3-frame confirmation (`tests/test_cli.py --repeat 3`, `tests/test_core.py` 4-frame loops) |
| + edge margin 0.05 m + 0.20 m per 100 m | not run | not run | |
| + edge margin 0.15 m per 100 m only | not run | not run | |
| + `confirm_time_s: 0.5` and edge margin 0.05 + 0.20 / 100 m | not run | not run | |

Reading (captain's runs of 22.09 on the six cached bags, every frame, commit 9b56bdf with one
lever group switched off per row by `--config`): the two levers that matter most are the
**infrastructure signatures** (without them 513 alarm frames — the platform-hall end wall, roof
strips and posts of the stopped train come back, 374 frames in the switch bag alone) and the
**height-reference range** (391 frames: the unverified extrapolation lifts far rails and pulls
the roof into the polygon exactly as §1b finding 2 describes). The **axis levers** cut 171 → 89 (first cut)
and, on the person, bring the first alarm from frame 11 to 7 (the rail-slab yaw keeps him inside
the gauge as soon as he is). The **history rules** trade 54 alarm frames for two frames of person
recall and a first alarm two frames earlier (68/71, frame 5 without them). A **0.5 s
confirmation** (`tracking.confirm_time_s: 0.5`) removes another 20 frames / 8 events at no cost
on the person (he is confirmed at frame 7 either way, 0.5 s after entering the gauge) and is the
first knob to turn if the control bag shows more short-lived false alarms; it stays at 0.3 s so
that the 3-frame confirmation the synthetic tests and the dry-run checker assume keeps holding.
The accumulation row is identical to the defaults because the offline runs have no train speed
and nothing is merged; the given-speed behaviour is measured in §2c. The edge-margin variants
were not run.

**Accumulation default.** The multi-frame accumulation stays in the code and stays *enabled for a given speed* (the node's `ego_speed_mps` / odometry, `eval` sequences; P4's CLI tests pin this path), but the LiDAR-only estimator that fed it in v0.4 is **off by default** (`accumulation.estimate_speed: false`): with the estimator on, the same code alarmed on 119 frames / 30 events of the five empty bags instead of 88 / 27 (pre-vectorisation copy of the code; the final code measures 89 / 29, `roundT_pressureGate_roundT` 8 → 31 frames, `roundT_squareT_pressureGate_squareT` 5 → 20), it did not change the person's recall or first alarm on `doubleT_obstacle` (66/71, frame 7, with the stopped-train guard), and it costs 7–8 ms per frame; the final-code number is in the ablation row above. The synthetic gain of §2b (person 189 vs 178 m on the tunnel at 22 m/s) is real but has no real-data counterpart yet (no moving bag with an obstacle); with a given speed the given-speed rows of §2c and the given-speed runs of the ablation table are the measured behaviour. Regression rule of EVALUATION.md §3.6: false-alarm frames on E 1 001 → 96 and p95 latency (§3: 51 vs 71 ms on `roundT_doubleT`, 60 vs 76 ms on `doubleT_obstacle`, back to back) are both better than v0.3; on R the first alarm frame is 7 (≤ 9) and the recall 66/71 (≥ 64/71).

## 1c. v0.5 on the organizers' extended recording (22.09, unlabelled, every frame)

The 20-minute bag `new_data` (221 split files, 11 271 frames, seven stops, top speed 77 km/h,
tunnels / curves / stations / a switch; `DATASET.md` "Extended dataset") streamed once through
the v0.5 defaults, a fresh detector per 51-frame file, no speed given. No labels exist, so
these are false-alarm numbers on a ride, not recall:

| recording | frames | alarm frames | alarm events | events / hour | events / km | latency mean / p95 / max |
|---|---|---|---|---|---|---|
| `new_data` (1 200 s, ≈ 13 km) | 11 271 | 358 (3.2 %) | 102 | 306 | 7.9 | 41 / 74 / 157 ms |
| five obstacle-free organizer bags (230 s, §1) | 2 287 | 96 (4.2 %) | 32 | ≈ 500 | — | see §3 |

Causes, by the median lateral offset of the 102 events (per-event rows in
`extended_dataset_intake.json`): 40 at the left gauge edge (contact-rail side, brackets 0.6 m
above the rail head flipping into the gauge at 40–100 m), 16 at the right edge (column row in
double-track sections), 28 central — 11 of them in the five files where the track model is not
locked (a switch, platform ends) and 17 with ≤ 15 points at 60–140 m — and 18 in between. The
biggest single family is therefore the left edge (the mirror image of the column-row family of
§1b), the second the unlocked track model at stations and switches; both are on P3's list in
`DATASET.md` "What follows". The tracker's measured-interval gate (§1b review fix) is exercised
for real here: the last third of the recording has holes of 1.2–7.1 s between frames.

## 2. Synthetic obstacles injected into real empty frames (`resense inject` / `resense eval`)

### 2a. Day-1 numbers (v0.3, 26 frames of `roundT_doubleT`, every 10th, synthetic objects)

One object per frame (person 0.5×1.7 m, box 0.5 m, plank 2×0.25×0.3 m), uniformly 10–220 m,
20 % placed outside the gauge as negatives; objects whose rays are all occluded by real
geometry (7 of 26) excluded. Recall v0.3: 0–50 m 3/3, 50–100 m 1/2, 100–150 m 0/5,
150–200 m 0/3, 200–300 m 0/3. First-detection distances: person 13.7 / 19.5 / 23.2 m (placed
there), box 53.7 m. Ray-cast point budget (single frame): person 24 pts @80 m, 10 pts @110 m,
3–5 pts @150–190 m, 0–1 @>200 m — consistent with the analytic estimate in DATASET.md.
Synthetic-tunnel unit tests (`tests/`): box 0.6 m detected at 30 and 80 m, person at 150 m, no
alarm on the clear tunnel, object 2.3 m off-axis not alarmed, occlusion of the background
verified.

### 2b. Multi-frame accumulation on the synthetic tunnel (v0.4, 21.09) — synthetic

**Every number in this section is synthetic** (`resense.synthetic.synthetic_tunnel_frame`, a
featureless round tunnel with benches at 1.95 m; `tests/test_algorithm.py`), 4-core sandbox.
The approach of a train at 22 m/s is emulated by injecting the object at 200, 197.8, … m
(2.2 m per 10 Hz frame) into the *same* background frame; the sequences use
`dropout_start=60, dropout_full=200`, which reproduces the real-frame budget (person 2–5
returns at 185–200 m; box 0.5 m: 4–6 at 100–130 m).

| object, sequence (given ego speed 22 m/s) | first confirmed alarm, v0.3 (base commit) | v0.4, accumulation off | v0.4, accumulation on (5 frames) |
|---|---|---|---|
| person 0.4×0.5×1.7 m from 200 m, 6 seeds | 162.6 m (corridor validity) | 167–189 m, median 178 m, frames 5–15 | **189–191 m in 6/6 seeds**, frames 4–5 |
| box 0.5 m from 140 m, 4 seeds | 114.6 m | 89–116 m (one seed collapses to 89 m) | **113.6–115.8 m in 4/4 seeds** |

What limited v0.3 at range on the synthetic tunnel was the corridor validity (bed fit to
107.5 m + 60 m), not the point count; the verified extrapolation (ALGORITHM.md §3.1) reaches
195 m there. The 0.5 m box does not gain range from accumulation (beyond ~118 m it is sampled
by a single ring). Ego-speed estimator on synthetic texture: 22.0 m/s ± 2 with posts on the
walls, "unknown" on a stopped train and on the featureless tunnel. Retro-reflector rule: sign
plate 0.05×0.6×0.8 m with reflectivity 220 → advisory, the same plate matte → obstacle, person
15 / 60 / 200 → obstacle, 1 m crate 220 → obstacle, 0.5 m box 220 → advisory (documented
choice). The independent review of v0.4 on real data (every frame, no speed given) found the
stopped-train merge smearing the crossing person laterally (width 1.06 vs 0.57 m), the
verified corridor promoting phantoms at 135–142 m, +17–23 ms per real frame, and the retro
rule never firing on the six bags (intensity ≥ 100 on < 1 % of the returns); all four are
addressed in v0.5 (§1b, §3) and the estimator's real-bag behaviour is in §2c.

### 2c. Recall by range on real backgrounds (set S, v0.5, 21.09) — synthetic objects, real frames

Sets built this round with the merged `resense inject` (commit 9b56bdf (merged as 82815e9); objects are placed
on the per-frame track model of *this* code, so the frames differ slightly from P4's sets of
f4e311f): the two static sets `S_roundT_doubleT` (26 frames) and
`S_roundT_pressureGate_roundT` (27), every 10th frame, one catalogue object per frame
(`person, box0.5, box1.0, plank, trolley`), 10–250 m, 20 % negatives, `--seed 1`, evaluated
with `resense eval --repeat 3`; and six approach sequences (`--sequence 8 --speed 15`, seeds
1–3 on both bags, 208–215 frames each, one random kind per background). Two protocol facts
decide how the far bins can be read:

* **Sightline.** Both bags are curves: from the v0.5 axes the inner wall (2.2 m from the
  axis) hides the track beyond √(2·R·2.2 m) ≈ 88 m (median frame of
  `roundT_pressureGate_roundT`, R = 1.8 km) and 124 m (`roundT_doubleT`, R = 3.5 km); only
  93 / 268 and 119 / 252 frames see further than 150 m. Nothing placed beyond the sightline
  can be detected by any sensor.
* **Placement.** The injector stands objects on the per-frame extrapolated bed, which beyond
  the fit (48–100 m in these frames) swings between +1.4 and −3.3 m at 100–250 m
  (`S_roundT_doubleT` rows at 133, 230, 102 m); combined with the sightline this leaves
  **11 of the 22 in-gauge objects of each static set fully occluded (all beyond 80 m)** and
  436 of the 1 269 sequence rows; they are excluded from recall and counted here. The far
  bins therefore hold 3–7 visible objects per set and measure the injector as much as the
  detector (§5: placement on the local bed).

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
| person 0.4×0.5×1.7 m | 28/37 | 38/68 | 1/30 | 0/21 | 0/9 | 104.9 / 56.7 (11) | 104.9 / 70.7 (10) |
| box 0.5 m | 15/21 | 4/11 | 0/20 | 0/35 | 0/15 | 57.6 / 49.1 (4) | 57.6 / 49.1 (3) |
| box 1.0 m | 23/29 | 23/59 | 0/38 | 0/1 | — | 81.8 / 55.0 (8) | 89.6 / 55.0 (8) |
| plank 2×0.25×0.3 m | 0/45 | 3/40 | 0/14 | 0/16 | 0/6 | 86.3 (1) | — (0) |
| trolley 0.6×0.6×1.0 m | 18/24 | 18/33 | 0/57 | 0/53 | 0/10 | 78.7 / 71.9 (5) | 149.5 / 88.6 (6) |

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
object-frames; the low-hardware rule, ALGORITHM.md §6.6), except three frames at 86 m where
the axis error lifted it.

The `person` first detection of 104.9 m and the `box1.0` 81.8 m are the honest single-frame
ranges on these two curved bags; the Sprint 2 targets (person ≥ 150 m, box ≥ 100 m) hold on
the synthetic tunnel only (§2b) and are not met on real backgrounds by any configuration
measured this round.

## 3. Timing (4-core sandbox, Python, every frame; the i7-9700E bench is still owed)

Where the v0.5 time went before the cost work (cProfile over frames 100–114 of
`roundT_doubleT`, load 4.6): the rail-slab profiles called `np.percentile` once per 5 cm bin
(6 208 calls per 14 frames, 49 ms per frame), the bed height was evaluated six times per frame
on the whole cloud (13 ms), and the polygon test ran on all 190 k in-range points (14 ms).
After vectorising the per-bin percentile (one sort per profile, exact linear interpolation),
computing the bed height and the corridor coordinates once per frame and prefiltering the
polygon test by its bounding box, the same frames took: track 81 → 31 ms, corridor 16 → 7,
egomotion 9 → 7 (now off by default), cluster 6, total 112 → 52 ms.

**Back-to-back bench on the idle machine** (`resense bench --npy /data/cache/<bag>`,
every frame, commit 9b56bdf (merged as 82815e9); the v0.3 switches are the config of §1b; load before each run
in the table; the i7-9700E has 8 faster cores):

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
cores) has not been measured (P1).

Per-stage means of the same runs are in the table; the platform bags remain the expensive
ones because their corridor holds 15–20 k candidates per frame (DBSCAN 45–70 ms in v0.3 and
v0.5 alike). The frame period is 100 ms; the ROS node adds decode (~5 ms) and publishing, and
drops frames rather than queueing, so the node's dropped-frame counter is the number to watch
on the bench.

## 4. What we learned / hard cases

1. **Sensor mounts differ between bags** (bed 1.5 m vs 2.0 m below the sensor, axis 0.05–0.25 m
   right of the sensor axis) → any fixed calibration fails; the rail-ridge self-calibration is
   stable to ±0.05 m frame to frame, provided the profile is built in the coordinates of the
   previous axis (in absolute Y the ridges smear in curves, §1b).
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
4. **Platform stop + switch bag** was 504 of the 1 001 v0.3 false-alarm frames: two roof
   strips (700 frames between them), the hall's end wall at 72–78 m, and switch parts at
   147.5 m, all seen by a stopped train for 40 s. v0.5 leaves 56 frames / 18 events there, 50 of them the platform-end structure at 82.9 m (see §1): the curvature beyond a platform comes from the hall walls, which follow the platform rather than the track curving into the tunnel, so the corridor at 80–90 m is 0.5–0.8 m off — a station-curvature limitation (ALGORITHM.md §6.2), not a shape signature.
5. **Corridor-edge structures** at 1.5–1.6 m from the axis are 0.1–0.2 m outside the 1.40 m
   gauge (ALGORITHM.md §6.1): the strict decision needs a centimetre-accurate axis there, or a
   margin that grows with range; the crossing person of `doubleT_obstacle` leaves the gauge
   through exactly that band (label margins of ±0.25 m in frames 70–76), so every margin costs
   borderline frames of a real object.
6. **Small objects**: anything below rail head + 12 cm inside the rails and low/narrow hardware
   (< 0.35 m top, < 0.4 m wide) is filtered — a 20 cm object on the sleepers is invisible by
   design; revisit with the extended dataset.
7. **Point budget** is the physical limit: 0.5 m object = 7 pts @100 m, 1.6 pts @200 m.
8. **Injected objects beyond ~80 m are often fully occluded** because the injector places
   them on the per-frame extrapolated bed, which lies under the real bed there (§2c): the
   far bins of set S measure the injector as much as the detector.

## 5. Next experiments (owner in PLAN.md)

- **Injector placement on the local bed** (P4, `resense/synthetic.py`): place the object's
  base on the 5th–20th percentile of Z of the real returns within ±1 m of the axis and ±5 m
  of the placement (fall back to the model where fewer than ~10 such points exist), and write
  the height offset used into the gt row; re-run §2c;
- **bed correction from the side-structure base** (P3): use `z_base(X) − offset_ref` as
  `z_floor(X)` beyond the fit where the side base is continuous, then re-measure the far bins
  and the 147.5 m switch structures;
- **persistence 0.5 s** as the default once the P4 tests use `tracking.confirm_hits` /
  `confirm_time_s` generically (§1b option table gives the numbers);
- **bed-trough centre vs wall axis** at stations (design in v0.4, not implemented): a second
  lateral axis where the walls are far;
- ego-speed estimator: the tracks cue is silent below 1 m/s by design; the profile cue is
  silent on 40–60 % of the moving frames — a bed profile with the ring stripes removed, or the
  organizers' speed / odometry (the reliable path);
- extended dataset with real obstacles → calibrate dropout / intensity in `inject`, real
  recall by range and class, false alarms per km, FP taxonomy per scene type with the label
  tool;
- GOST 23961-80 gauge polygon from the drawings (ALGORITHM.md §3.2); platform notch; overhead
  policy;
- timing on the i7-9700E bench; Numba for the DBSCAN stage on the platform bags (15–20 k
  candidates per frame) if needed.
