# Experiments

> **Purpose:** the measured results of ReSense for spec §5 «Эксперименты»: at what distance
> obstacles are detected, processing latency, frame rate, false alarms, hard situations, how the
> quality changed, and what was tried and not shipped (negative results included).
> **Audience:** team, jury · **Owner:** P3 / P4 (detector results), P1 (node timing) ·
> **Language:** EN, summary RU
> **Last verified:** 2026-09-29: current figures against the judgement's raw summaries of 28.09,
> the 27.09 gate and its VM re-run, the VM run of 28.09 and the node start-up A/B of 29.09; history
> against the archived log and changelog · **Status:** current

**Section numbers.** "EXPERIMENTS §x" (for example §1g, §3b, §3d) in code comments and older
records refers to the full experiment log, archived verbatim at
[`archive/EXPERIMENTS_log_2026-09.md`](archive/EXPERIMENTS_log_2026-09.md). In this file
"log §x" means a section of that log; the quality-cycle records are
[`archive/QUALITY_CYCLE_2026-09-26.md`](archive/QUALITY_CYCLE_2026-09-26.md) ("QC 26.09") and
[`archive/QUALITY_CYCLE_2026-09-27.md`](archive/QUALITY_CYCLE_2026-09-27.md) ("QC 27.09").

**Кратко.** Результаты детектора, запечатанного 27.09, и ROS-ноды от 29.09. Реальное препятствие
(`doubleT_obstacle`): `STOP` с 8-го кадра (человек входит в габарит) до конца записи на 55,5–56,6 м,
один кадр `GO` (111). Ложные срабатывания: 7 эпизодов `STOP` на пяти пустых записях, 30 на 13-км
поездке (2,3 на км). Объекты организаторов: `STOP` для 8 из 8, первый `STOP` на 29–111,5 м.
Реальный человек, перенесённый в другие тоннели: устойчивый `STOP` на 60 м в 11 из 15 окон, на
100 м — в 6. Скорость: 10 кадров/с, сквозная задержка p95 81–96 мс при 360° на 4-ядерной ВМ,
меньше одного ядра CPU. Все частоты ложных срабатываний получены «в выборке». Ниже — трудные
ситуации, как менялось качество с v0.1 и что пробовали, но не выпустили.

## Data and protocol

| data | frames | what it tests | kind |
|---|---|---|---|
| `doubleT_obstacle` | 201 (360°, train standing) | a real person crossing at 55–57 m; a real object (0.45 × 0.6 × 0.3 m) lying across the right rail at ~56 m, in view the whole recording | real, in-sample |
| five obstacle-free recordings (`doubleT_platform`, `roundT_doubleT`, `roundT_pressureGate_roundT`, `roundT_squareT_pressureGate_squareT`, `squareT_platform_squareT_switch`) | 2 287 (120°) | false alarms in round, square and double-track tunnels, a platform stop, a switch | real, in-sample |
| the ride `new_data` | 11 271 (20 min, 13.0 km, seven stops) | false alarms per km; the organizers confirmed it holds no obstacle | real, in-sample; held out only for the learned opinion (cross-fitted) |
| set O, `cloud_with_fake_obj` | 1 510 | ten objects ray-cast into a real ride by the organizers' own tool: 8 inside the envelope, 2 just outside | organizers' synthetic, in-sample |
| set F | 6 straight ride files × 5 kinds, 110 frames each, from 220 m | the team's objects (person, trolley, 1 m crate, 3 cm hanging cable, 0.5 m box on the bed) ray-cast into the moving ride, legacy placement | team synthetic on seen backgrounds |
| range test (28.09) | 5 recordings × 3 windows × 6 ranges | the real person of `doubleT_obstacle` pasted at 60–200 m into the other five tunnels, thinned to (55.5 / r)² of its points | real points on real frames; held-out composites on seen backgrounds |

**In-sample.** Every real recording and set O were inspected and tuned on, so every false-alarm
rate below is in-sample. Held out are only the ride pieces scored by an opinion model that never
saw them and the range test's composites; the hidden control data are not available. The labels
of `doubleT_obstacle` and the set O positions were measured with the team's own tools, so neither
is an independent ground truth. Sets, metrics and the gate: [`EVALUATION.md`](EVALUATION.md);
data, downloads and labels: [`DATASET.md`](DATASET.md).

**Two ways of counting.** The independent judgement of 28.09 (commit `464f5bc`,
[`evidence/judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md)) ran the detector on
every frame of the raw recordings and counts STOP frames and STOP episodes (runs of consecutive
STOP frames); the ride was processed split by split with a detector reset every 5 s. The team's
regression gate (`scripts/regression_gate.py`) replays the 1 cm frame cache and counts alarm
frames, events (distinct confirmed tracks) and STOP episodes, the ride in 8 pieces. Current
results lead with the judgement; the history table uses the gate.

## Current results (detector sealed 27.09, node of 29.09)

The detector is sealed ([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)); the node change of 29.09
leaves every decision after the start-up identical. Criterion-by-criterion assessment:
[`SCORECARD.md`](SCORECARD.md).

### Detection: the real obstacle

| what | result | kind | evidence |
|---|---|---|---|
| person crossing at 55–57 m | STOP from frame 8 (the first frame the person is inside the envelope) to the end, 55.5–56.6 m | real, in-sample | [`offline_summary.json`](evidence/judgement_2026-09-28/offline_summary.json) |
| object across the right rail at ~56 m | STOP on every frame after the person leaves it except **GO at frame 111** and CAUTION at 117 and 197 (reproducible; see [Hard situations](#hard-situations)) | real, in-sample | [`judge_outputs_2026-09-28/`](evidence/judge_outputs_2026-09-28/README.md) |
| the whole recording, offline | STOP on 190 of 201 frames | real, in-sample | [`offline_summary.json`](evidence/judgement_2026-09-28/offline_summary.json) |
| through the node (jury chain), first STOP after the first cloud | 1.0–1.4 s (node of 28.09); 0.79–1.16 s (node of 29.09) | real | [`chain_runs.json`](evidence/judgement_2026-09-28/chain_runs.json), [`node_startup_2026-09-29/`](evidence/node_startup_2026-09-29/README.md) |

On the team's frame cache the gate counts the person 61 of 61 frames from frame 8 and the rail
object 125 of 126 after the person leaves; on the raw recording, offline and through the node, it
is 123 of 126 (the three frames above).

### The organizers' objects (set O)

| object (organizers' intent) | first STOP | STOP / labelled frames inside the envelope | kind |
|---|---|---|---|
| 2 × 2 × 2 m box, centre | **98 m** (its first appearance) | 208 / 213 | organizers' synthetic, in-sample |
| 2 × 2 m box at the top of the envelope | **111.5 m** | 56 / 75 | same |
| long low object on the rails (0.5 × 2.0 × 0.2 m) | **87 m** | 52 / 77 | same |
| 0.3 m cube, centre (floating) | 56 m | 32 / 63 | same |
| 0.3 m cube on the rail | 48 m | 26 / 33 | same |
| 0.3 m cube at the envelope edge | 35 m | 16 / 16 | same |
| 2 m box at the envelope edge | 29 m | 8 / 8 | same |
| 5 cm hanging object | 30 m | 14 / 20 | same |
| 0.3 m cube just outside | 0 STOP (correct) | — | same |
| 2 m box outside | 9 false STOP frames at 126–142 m | — | same |

STOP for all 8 in-envelope objects; 22 stray STOP detections away from any object. Source:
[`setO.json`](evidence/judgement_2026-09-28/setO.json) (a STOP counts for an object within 3 m
along the track). The team's gate on the frame cache, with its own matching, gives 411 of 801
visible in-envelope object-frames, 0 background frames, and first STOPs of 42.7 m for the cube on
the rail and 18.3 m for the edge box (that scorer matches within 1 m of the 2 m box's centre; the
box's track STOPs from 28.7 m); this file quotes the judgement's figures.

### False alarms

| recording | frames | STOP frames | STOP episodes (distance) | CAUTION frames |
|---|---:|---:|---|---:|
| `roundT_doubleT` | 252 | 0 | 0 | 173 (69 %) |
| `doubleT_platform` | 345 | 3 | 1 (31–39 m) | 196 (57 %) |
| `roundT_pressureGate_roundT` | 268 | 2 | 1 (53–54 m) | 119 (44 %) |
| `roundT_squareT_pressureGate_squareT` | 545 | 0 | 0 | 190 (35 %) |
| `squareT_platform_squareT_switch` | 877 | 18 | 5 (83–148 m) | 443 (51 %) |
| **five obstacle-free recordings** | 2 287 | **23 (1.0 %)** | **7** | 1 121 (49 %) |
| **ride `new_data`**, 13.0 km, detector reset every 5 s | 11 271 | **164 (1.5 %)** | **30 = 2.3 per km** (~96 per hour), at 15–146 m | 4 142 (37 %) |

All real, in-sample, independent judgement of 28.09
([`offline_summary.json`](evidence/judgement_2026-09-28/offline_summary.json),
[`ride_summary.json`](evidence/judgement_2026-09-28/ride_summary.json)). CAUTION is advisory, not
an alarm. The team's gate on the frame cache
([`regression_gate_2026-09-27_quality.json`](evidence/results/regression_gate_2026-09-27_quality.json)):
five recordings 40 alarm frames / 11 events / 13 STOP episodes; the ride 130 / 32 / 31
in-sample, and **37 events = 2.8 per km on ride pieces the learned opinion never saw** (each pair
of the 8 pieces run with a model trained without them,
[cross-fit](evidence/results/quality_cycle_2026-09-27/opinion_crossfit_2x_margin.json); 43 events
with the opinion off). The rules themselves stay in-sample.

### Range

| evidence | result | kind |
|---|---|---|
| set O, first STOP | large objects 87–111.5 m (the 2 m box from its first appearance at 98 m), 0.3 m cubes 48–56 m, edge objects 29–35 m, 5 cm hanging object 30 m | organizers' synthetic, in-sample |
| range test, sustained STOP (STOP at the person on ≥ 15 of 30 frames) | 60 m **11 / 15**, 80 m 8 / 15, 100 m 6 / 15, 130 m 2 / 15, 160 m 1 / 15, 200 m 0 / 15 windows; any STOP 14, 11, 11, 6, 6, 3 / 15; controls without the person: 0 false STOP | real points, held-out composites ([`transplant.json`](evidence/judgement_2026-09-28/transplant.json)) |
| set F straight, median first detection (6 approaches each) | person **151.0 m** (6 of 6), trolley 151.4 m, 1 m crate 123.9 m, 3 cm hanging cable 98.9 m, 0.5 m box on the bed 1 of 6 (51.9 m); the person in 120 of 151 visible frames at 100–150 m, 13 of 125 at 150–200 m | team synthetic; gate of 27.09, re-run on the team VM 28.09 identical ([`gate_2026-09-28/`](evidence/gate_2026-09-28/gate_table.txt)) |
| set F, person anchored on the near rails (24.09, v0.6.3) | 154 m (legacy 150 m on the same 5 approaches); on R ≈ 350 m curves nothing matched at 100–150 m in either placement (legacy first confirmations 58–86 m, the sightline) | team synthetic, dated (log §2d) |
| set F with a given train speed (24.09, v0.6.3) | person 167 m, trolley 175 m, crate 182 m (held only from 79 m); the recordings carry no speed | team synthetic, dated (log §2d, §9) |
| sensor | no return beyond ~210 m in any of the 13 759 frames: 300 m is beyond this LiDAR | real |

Misses in the range test are CAUTION, not silence: `beyond_axis` where the trusted axis range is
short (platforms, double-track sections) or a merge with trackside structure into a `column`.

### Speed and resources

| measure | result | machine, date | evidence |
|---|---|---|---|
| end to end at 360° (player publishes the cloud → result), p95 of the current results | **81–82 ms** warm, 88–96 ms cold page cache | team VM, Xeon Icelake, 4 physical cores, 28.09 | [`vm_2026-09-28/summary.md`](evidence/vm_2026-09-28/summary.md) |
| same, independent judgement | 85–94 ms warm, 87–172 ms cold; 120°: 49–78 ms | 4-vCPU sandbox, 28.09 | [`chain_runs.json`](evidence/judgement_2026-09-28/chain_runs.json) |
| node decode + detect, p95 | 63–72 ms (VM); 79–98 ms (sandbox) | 28.09 | same |
| frame rate | **10.0 fps** at 360° with the C++ kernels; after the start-up every frame is processed | team VM, 28.09 | [`bench_2026-09-28/`](evidence/bench_2026-09-28/summary.txt) |
| start-up (node of 29.09) | results of the first 3 s 38–105 ms old (median; was 312–325 ms); first STOP 0.79–0.98 s after the first cloud | 4-vCPU sandbox, 29.09 | [`node_startup_2026-09-29/`](evidence/node_startup_2026-09-29/README.md) |
| CPU, memory | 0.5–1.0 core; RSS 130–740 MB; no GPU | 4-vCPU sandbox, 28.09 | [`chain_runs.json`](evidence/judgement_2026-09-28/chain_runs.json) |
| numpy fallback (no C++ kernels) | not real time at 360° on 4 cores (decode + detect p95 103 ms) | team VM, 28.09 | [`bench_2026-09-28/`](evidence/bench_2026-09-28/summary.txt) |

Details, per stage and before / after: [Speed](#speed).

### Tests and reproducibility

- `pytest`: 770 passed, 1 deselected (it needs the ride's frame cache), 6 subtests (29.09,
  `RESENSE_REQUIRE_SYNTHETIC=1`); ruff clean; CI (4 jobs, 2 stages) green on `main`.
- Seal: `python3 scripts/detector_freeze.py verify` PASS against
  [`detector_freeze_2026-09-27.json`](evidence/detector_freeze_2026-09-27.json).
- Gate: [`regression_gate_2026-09-27_quality.json`](evidence/results/regression_gate_2026-09-27_quality.json)
  passes against the 26.09 baseline with no waiver and is the current baseline
  ([`regression_baseline_2026-09-27_quality.json`](evidence/results/regression_baseline_2026-09-27_quality.json));
  the team VM re-ran it with the ride and set F on 28.09: every gated row identical.
  `python scripts/regression_gate.py --cache <cache> --jobs 4` re-measures the gate's rows (six
  recordings, set O, the ride, set F straight; caches: [`DATASET.md`](DATASET.md)).

## Speed

### Detector, per stage

`resense bench`, every frame, one core (`OMP_NUM_THREADS=1`), C++ kernels, the sealed detector on
an idle 4-vCPU sandbox, 27.09 ([`bench_native.txt`](evidence/results/quality_cycle_2026-09-27/bench_native.txt)),
means in ms:

| recording | track model | corridor | clustering | tracking | total mean / p95 / max |
|---|---:|---:|---:|---:|---|
| `doubleT_obstacle` (360°) | 12.4 | 5.5 | 4.2 | 0.8 | **22.9 / 32.6 / 41.3** |
| `roundT_doubleT` (120°) | 9.3 | 4.9 | 6.1 | 0.9 | 21.2 / 30.0 / 32.7 |
| set O (`cloud_with_fake_obj`) | 8.7 | 4.5 | 4.1 | 0.7 | 18.0 / 23.3 / 57.1 |
| `squareT_platform_squareT_switch` | 8.4 | 4.6 | 4.9 | 0.8 | 18.6 / 22.7 / 32.9 |

`total` stops after tracking; the health monitor runs after it and is included in the node's
decode + detect. On the team VM (28.09) the same totals are 24.6 / 34.5 ms (360°) and
22.5 / 31.4 ms (120°) mean / p95; the numpy path is 2.3× slower (55.9 / 67.4 ms at 360°).
**Worst stretch:** ride frames 5700–5900, a dense station scene: 57.3 ms mean, p95 111.3 ms, max
143.4 ms on one core, clustering up to 122 ms (27.09; the 26.09 detector was similar, QC 27.09
"Speed"). History: the v0.3 code 56–71 ms mean on two recordings, v0.6.3 42–64 ms mean and
p95 53–78 ms on the numpy path (23.09, log §3); the C++ kernels cut 38–57 % with identical output
(24.09).

### Node path

| step | before → after | when, machine |
|---|---|---|
| input: rclpy's conversion of the 24 MB message into Python | 12.5 ms median, 32 ms p95 → read from the serialized bytes, 0.1 ms | 28.09, 4-vCPU sandbox (log §3d) |
| RViz markers and corridor cloud | ~8 ms per frame always → built only while watched | 28.09 (log §3d) |
| decode to x / y / z arrays (`fastcloud.decode`, identical arrays on all 453 frames) | 360°: **20.3 → 16.6 ms** median (p95 29.2 → 23.7); 120°: 7.4 → 4.8 ms | 29.09, 4-vCPU sandbox |
| first frame after start (warm-up on three synthetic frames, ~0.7 s before "listening") | decode + detect 49 + 72 ms → ~31 + 42 ms | 29.09 |
| node path offline (decode, crop, rotation, detector; no ROS) | 40.2 / 49.9 ms mean / p95 at 360°, 31.1 / 39.9 ms at 120° | team VM, 28.09 (before the 29.09 decode) |

End to end through ROS (VM, 28.09): p95 of the current results 81–82 ms at 360° with the
recording in the page cache (88–96 ms cold) and 52–60 ms at 120° (log §3e). A 20 s 360° recording
is 4.5 GB, so playing it at 10 Hz needs ~225 MB/s of storage (see Hard situations).

### Start-up: A/B of the 29.09 node

The image of `464f5bc` against the image with the 29.09 node, alternated on one idle 4-vCPU
sandbox, through the jury chain with a listener that also subscribes to the clouds (absolute
latencies higher than without it). e2e = the listener receives a cloud → the status of that cloud.
[`node_startup_2026-09-29/`](evidence/node_startup_2026-09-29/README.md):

| condition | runs | e2e median, first 3 s | e2e p95, all results | first STOP after the first cloud |
|---|---:|---|---|---|
| 360° `doubleT_obstacle`, bag in the page cache | 3 + 3 | 312–325 → **38–105 ms** | 410–447 → **212–344 ms** | 0.90–0.99 → 0.79–0.98 s |
| 360°, page cache dropped | 2 + 2 | 829–1029 → **120–300 ms** | 864–1084 → **333–599 ms** | 1.16–1.35 → 0.81–1.16 s |
| 120° `roundT_doubleT` (clear) | 2 + 2 | 37–42 → 29–32 ms (p95 295–340 → 66–123 ms) | 52–60 → 48 ms | no STOP in either |
| 360°, default player (read-ahead 1 000) | 1 + 1 | 7.0 → 4.3 s, all stale | — | 7.5 → 2.3 s; 57 → 145 of 201 frames processed |

Decisions after the start-up are identical (STOP 55.5–56.6 m from frame 8, the GO at 111);
steady-state decode + detect and the current-result e2e are unchanged within noise.

## Hard situations

| situation | what happens | why | evidence |
|---|---|---|---|
| platforms and switches | 5 of the 7 STOP episodes of the five recordings are in `squareT_platform_squareT_switch` at 83–148 m while the train stands at the platform; `doubleT_platform` 1 at 31–39 m | beyond a platform the axis takes its curvature from hall walls that follow the platform, ~0.8 m off at 83 m, so the platform end reads inside the envelope; the switch parts at 147.5 m sit on an axis set by a hall wall seen only to 72–92 m | log §1f, §1h |
| ride false alarms | 30 STOP episodes at 15–146 m | the 45 events of the 26.09 detector, traced by their geometry: 21 low track-cross-section fragments, 6 vertically continuing structures, 4 side-profile fragments, 14 sparse targets unresolved; by the scene at the train: 20 platform / station, 16 tunnel, 9 uncertain | QC 26.09, log "Freeze validation" |
| trusted axis range (`beyond_axis`) | an object on the track beyond the trusted axis range is CAUTION, not STOP; in one platform window of the range test that range was 45 m for the whole window | the axis is trusted only as far as the tunnel boundaries are seen and agree; platforms and double-track sections shorten it | [`SCORECARD.md`](SCORECARD.md), [`transplant.json`](evidence/judgement_2026-09-28/transplant.json) |
| small and edge objects late | 0.3 m cubes first STOP 48–56 m; edge cube 35 m; edge 2 m box 29 m; set F 0.5 m box on the bed 1 of 6; a person 0.1 m inside the edge: 0 of 126 frames at 50–100 m from the rails | beyond 60 m a 0.3 m cube returns 1–4 points a frame; at 150–220 m the extrapolated rail level moves by ±1 m; the organizers place edge objects from the sensor axis, and the union with that envelope applies only within 60 m on straight track | log §1o, QC 27.09 "Limits" |
| curves and a standing train | set F: R ≈ 350 m curves first confirmed at 58–86 m; the person on six other ride segments at ±0.9 m: 115.5 m median (5 of 6); ahead of a standing train at 110 m 0 of 9 placed objects STOP (70 m: 6 of 9) | sightline past the inner wall; trusted range | log §2d, QC 27.09 "Limits" |
| sensor reach | nothing beyond ~210 m | the LiDAR's cut-off in every recording; beyond ~100 m the bed does not return | log §2d |
| monitored range | `clear_distance` extends past an in-envelope object in 300 of 605 set O frames (68 of them GO) | it is an estimate from what the sensor sees, not a guarantee | [`SCORECARD.md`](SCORECARD.md) |
| frequent CAUTION | 49 % of the frames of the five recordings (35–69 %), 37 % of the ride | columns, the advisory band, objects beyond the trusted axis; an object demoted to CAUTION is easy to overlook | [`offline_summary.json`](evidence/judgement_2026-09-28/offline_summary.json) |
| learned opinion's delay | a doubtful far STOP can wait up to 10 processed frames in a track's life (~1 s at 10 Hz, ~2 s at 5 Hz); never within 25 m or for a body ≥ 1 m tall within 40 m | its positives are synthetic; a real object unlike them can use the whole budget | QC 27.09 |
| processing history | which frames the node processes changes some false STOPs: history stress 55 events (78 on the 26.09 detector), mostly the platform structures at 82–147 m | the track model keeps state across frames | QC 27.09 |
| rate and mount | five recordings, false events: 13 as recorded, 10 at 5 Hz, 14 at +3° roll, 17 at +3° pitch; under +3° pitch a 2-frame low STOP at 1–3 m while the calibration is provisional | measured on the 26.09 detector | log §1g, §1p |
| dense station scene | detector p95 111 ms on one core (ride frames 5700–5900) | clustering of dense near structure | [Speed](#speed) |
| storage-bound playback | on the team VM (79 MB/s network disk) the 360° recording played in ~62.5 s, ~3 fps; the 120° one stalled once for 1.4 s and the node's catch-up skipped frames; the checker passed the ~3 fps runs | the 360° recording needs ~225 MB/s at rate 1.0; `check_dry_run.py` now prints the playback pace (`--min-playback-rate`) | [`vm_2026-09-28/summary.md`](evidence/vm_2026-09-28/summary.md) |
| the player's default burst | without `--read-ahead-queue-size 10` (Humble's read-ahead 1 000) the player sends the overdue recording in a burst: 57–135 of 201 frames processed, every result stale (queue lag median 11 s, RSS up to 4 GB); with the 29.09 node 145 of 201, first STOP +2.3 s (was +7.5 s), still stale | the player, not the node; keep `--read-ahead-queue-size 10` | [`node_startup_2026-09-29/`](evidence/node_startup_2026-09-29/README.md) |

**The single GO at frame 111.** On `doubleT_obstacle` the object lying across the rail forms no
cluster in frames 110–111, 116–117 and 196–197. Its confirmed `low` track is held over one miss
(`tracking.hold_misses` 1) and released on the second, so the node publishes GO at frame 111 and
CAUTION at 117 and 197 (other advisory objects in view); the next frame is STOP again, and
`clear_distance` stays capped at 56.2 m in those frames. It reproduces offline on the raw
recording and in every node capture that processed all 201 frames
([ARCHITECTURE «Known limitations»](ARCHITECTURE.md#limitations-of-the-sealed-2709-detector-verified-2809),
[`judge_outputs_2026-09-28/`](evidence/judge_outputs_2026-09-28/README.md)). The obvious fix,
`tracking.hold_misses` 2, restores the three frames (123 → 126 of 126) but fails the strict gate:
ride 130 → 150 alarm frames and 32 → 34 events, five recordings 40 → 46 alarm frames, and it
also keeps a stale off-axis track alive. It is recorded on the branch `gpt-score-push-20260928`
(`docs/evidence/results/p1_raw_continuity_2026-09-28/` there), not in `main`. The sealed detector
keeps the limitation; a consumer should not act on a single-frame GO.

## How quality changed

The team's counting (gate or its predecessors on the frame cache; five recordings = the 2 287
obstacle-free frames; events = distinct confirmed tracks). v0.1 was measured on subsampled
frames only, and on 22.09 the organizers' answers changed the target (a 2.1 × 3.0 m envelope), so
the rows before and after v0.6.1 are not strictly comparable.

| milestone | main change | five recordings: false events | ride: false events (per km) | real person: STOP frames of 61, first frame | set O: objects with STOP of 8 (STOP frames of 801) | set O first STOP: floating 0.3 m cube / edge cube | set F person, median first detection | source |
|---|---|---|---|---|---|---|---|---|
| v0.1 (15.09) | rail self-calibration, rail-relative gauge, voxelised DBSCAN | 92 alarm frames on 231 subsampled frames | — | — | — | — | — | log §1 |
| v0.3 (15.09; full rate 21.09) | nearer-boundary rule, 1.4 m gauge, hardware / wall filters | 192 (1 001 alarm frames, 44 %) | — | — | — | — | — | log §1, §1b |
| v0.5 (21–22.09) | axis yaw from the rails, full curvature from the walls, infrastructure signatures, persistence | 32 | 93 (7.2)¹ | 61, frame 8 | — | — | ~106 m (no far-field rule) | log §0a, §1 |
| v0.6.1 (22.09) | organizers' envelope, low-object stage at the rail heads, far-field rule, 20 s mount calibration | 30 | 82 (6.3) | 58, frame 11 | — | — | 150 m | log §0a, §1d |
| v0.6.2 (23.09) | objects straddling the envelope floor clustered whole (rail object 2 → 121 of 185 frames), 0.5 s confirmation, no far alarm without rails | 20 | 47 (3.6) | 58, frame 11 | — | — | 148 m | log §0 |
| v0.6.3 (23.09; set O 24.09) | a reported obstacle held over one missed frame | 20 | 47 (3.6) | 58, frame 11 | 5 (303) | 34.0 m / none | 148 m | log §0, §1f |
| 25.09 rules | long overhead rule, column hold, rail-shadow rules, hanging-object stage, free-hanging cube exemption, clear-distance cap, 5 Hz / re-mount flags | 13 | 46 (3.5) | 58, frame 11 | 6 (337) | 52.5 m / none | 151.0 m² | log §1f, §1h, §1i |
| 26.09 (P3d) | rail heads at a fresh start, near-field escalation, wall keep, STOP keep with a 10 s cap | 13 | 45 (3.5) | 58, frame 11 | 8 (384) | 52.5 m / 5.2 m | 151.0 m | log §1k–§1o |
| **27.09, sealed** | envelope from the rails ∪ the sensor axis within 60 m, learned track opinion (bounded delay), range caps, along-track association gate, far evidence | **11** (13 without the opinion) | **32 (2.5)** in-sample; **37 (2.8) held out** | **61, frame 8** | **8 (411)** | **55.8 m / 35.0 m** | 151.0 m | QC 27.09 |

¹ Same harness as the later rows; the v0.5 run of 22.09 with a fresh detector per 51-frame file
gave 102 events, 7.9 per km (log §1c). ² The set F script changed after 24.09 (the ray casting is
seeded per frame): 148 → 151 m is the measurement, not the detector (log §2d).

The 27.09 gains per mechanism (QC 27.09 ablations): the ride and five-recording gains are mostly
the learned opinion, whose negatives are those recordings (ride 43 → 32 in-sample, 43 → 37 held
out); the person's three extra frames and the edge cube's 5.2 → 35 m come from the envelope
reference; the set O range gains (box at the envelope top 101.3 → 111.4 m, plank 82.2 → 87.2 m)
from far evidence. The judgement of 28.09 on the raw recordings (its own counting) is the
[current result](#false-alarms): 7 STOP episodes on the five recordings, 30 on the ride.

## What was tried and not shipped

Every item stays off in the sealed configuration or was never merged; decisions with their
evidence: [`DECISIONS.md`](DECISIONS.md).

| approach (date, key) | result | why not shipped | source |
|---|---|---|---|
| bed-anomaly low-object stage: every bump > 7 cm above the learned bed (22.09) | ride 1 482 false events in 20 min (train-control inductors, drain covers, cable crossings) | a 30 × 30 × 10 cm box on the bed looks like the fixtures; the organizers do not count an object on the bed as an obstacle | log §1d, §7 |
| rail-level low-object stage: a low cluster reaching the rail head (22.09) | the real rail object 170 of 185 frames, but ride 734 events (guard rails, joints, fastenings) | would stop the train every 1.6 s; the straddle clustering of v0.6.2 took over (121 of 185, +1 event) | log §1d, §0 |
| central near-bed path, `lowobj.near_enabled` (24.09) | first gates: five recordings 20 → 145 events, ride 47 → 667, the 30 × 30 × 10 cm box 0 of 6 set F approaches; tighter gates: five recordings 107 events | false alarms; and a bed object below the rail head is not an obstacle (organizers, 25.09) | log §1e |
| short signatures, `cluster.short_signature_max_length` 3 m (25.09) | set O STOP frames 303 → 352 (floating cube 34 → 52.5 m); five recordings 20 → 22 events; ride STOP episodes +6 | pre-registered limit of +5 ride episodes exceeded; the cube's gain came later from a narrower exemption | log §1f |
| far-rail check, `track.rails_far_check_enabled` (24–25.09) | never fires on the six recordings, set O or the ride | nothing to gain on this data | log §1f, §1h |
| LiDAR-only train speed, `accumulation.estimate_speed` (v0.4; measured 24.09) | median error 0.06–0.08 m/s, +6.6–6.8 ms per frame; five recordings 103 / 18 → 114 / 17 alarm frames / events; even a perfect speed: no earlier first STOP on set O, outside box 6 → 17 false STOP frames | no gain on the organizers' check, only far-field frame recall | log §9 |
| far-support rule for the wall sides (82.9 m platform end), `track.walls_min_far_support` (25.09) | platform STOP episodes 15 → 1–10 | set O, `doubleT_platform` or the ride worse in every variant (ride 46 → 50 events): the axis filter amplifies any change | log §1h |
| switch parts at 147.5 m: `cluster.far_min_height` 0.8–1.0; `cluster.far_axis_both_sides` 1 / 2 (25.09) | height: set F person 151.0 → 138.8–143.5 m, trolley 151.4 → 104.5–106.9 m; mode 2 passes the gate (ride 46 → 42 events) | range loss; mode 2 costs a person's first confirmation on gentle curves (124.1 → 122.2 m) | log §1h |
| far bed bin dropped under an object's foot, `track.floor_far_min_width` (25.09) | removes one crate's 6 set F false detections, but other fixtures confirm instead (set F false detections 35 → 27–43) | a set O or set F row worse in every candidate | log §1h |
| `tracking.zone_min_fraction` 0.6 → 0.7 (25.09) | fewer 5 Hz / tilt alarms | real person 185 → 183 labelled hits, first alarm frame 11 → 13 | log §1g |
| start-up rules for low tracks (26.09): advisory while the calibration is pending; minimum model age; matched at ≥ 4 m | the third passed the gate (ride 46 → 45 events) | a real low object 3–3.9 m ahead of a standing train never STOPped; the other two lose or delay it | log §1j |
| envelope union `gauge.axis_union` 1, within 50 m (26.09); variants B / B2 | edge cube first STOP 5.2 → 18.2 m (full gate PASS with the review fixes); B: plank −1 STOP frame; B2: ride +3 events | a safety review found it could drop an obstacle touching a long edge structure (oversize split; fixed later); kept off while organizer question Q1 (rails or sensor axis) was open; superseded on 27.09 by `gauge.reference` 3, which never narrows the rails' envelope | log §1m, §1p |
| candidate B, `tracking.near_escalate_voxels` 10 → 8 (26.09) | gate PASS; edge cube first STOP 5.2 → 7.1 m, +1 STOP frame | one frame at 7 m against a lower bar for every demoted track; the detector was being frozen | log §1p |
| STOP keep without a voxel bar (26.09) | box at the envelope top STOP on every frame from 101.3 m | ride alarm frames 183 → 192; shipped instead with a 10-voxel bar and a 10 s cap | log §1o |
| M1: every raw envelope return limits the monitored range (26.09) | all 46 GO overclaims removed | +14.8–49.6 percentage points of uncertain frames on the empty recordings; range sharply reduced | QC 26.09 |
| M2: supported thin clusters limit the range (26.09) | GO overclaims 46 → 36, detections identical | the combined runtime acceptance failed (a clear-recording STOP at 53.0 m, also in the older baseline); the idea shipped on 27.09 as a range cap without its CAUTION | QC 26.09, QC 27.09 |
| A1: extra tracking allowance only for forward motion (26.09) | ride 45 → 44 events | one placement case 2 → 1 matches: its pre-registered per-case gate failed | QC 26.09 |
| D1: full-cloud context for clipped thin / floating candidates (26.09) | edge cube +5 STOP frames; placement matches 544 → 591 | outside-object false STOPs 6 → 9, ride STOP episodes 38 → 40 | QC 26.09 |
| T1: keep an observed boundary disagreement (26.09) | ride 45 → 43 events, 38 → 32 episodes | monitored-range median retention 50 % on a ride segment and 93.4 % on the platform / switch recording (95 % required) | QC 26.09 |
| `gauge.reference` 2, a one-sided shift (27.09, first version) | the same set O and person gains as the union | narrows the rails' envelope by up to 0.2 m on one side: a person 0.25 m inside on that side STOP in 24 of 91 frames at 30–60 m | QC 27.09 |
| envelope reference over the full range; clamp 0.3 m (27.09) | edge cube 21–25 frames from 42–48 m | ride +6 events | QC 27.09 |
| learned opinion at zero margin; `tracking.doubt_near` 35 m (27.09) | ride 25 events in-sample, 33 held out; 29 events | no margin (one fold's threshold would delay ten held-out test rows); `doubt_near` costs 7 events more than the standing-body exemption | QC 27.09 |
| `tracking.zone_min_votes` 5, `start_clean`, `confirm_hits` 5 (27.09) | history stress 78 → 55–70 events | each delays a set F person or trolley at ~150 m or a set O object by a frame | QC 27.09 |
| learned second opinion as a veto on candidates (22.09) | AUC 0.976 without intensity; 83 % of false candidates removed at 97 % object recall | synthetic positives only: a veto with no real positives behind it; a learned opinion on tracks shipped on 27.09 as a bounded delay, never a veto | log §8 |
| `tracking.hold_misses` 2 (28.09) | rail object 123 → 126 of 126 on the raw recording | strict gate fails: ride 130 → 150 alarm frames, 32 → 34 events; five recordings 40 → 46 alarm frames; branch `gpt-score-push-20260928` only | [above](#hard-situations) |
| GPU (24.09) | estimated ≤ 30–45 ms per 360° frame against numpy, 5–15 ms against fused CPU code | a GPU container does not start without `nvidia-container-toolkit`; image +0.3–6 GB; untestable in CI; latency is not the limit | [`ARCHITECTURE.md`](ARCHITECTURE.md) "GPU: evaluated, not used" |
| forward crop at X ≥ 2.9 m; reuse of the bed height (25.09) | identical output | no gain on the native path (crop +0.05…+2.4 ms, bed-height reuse 0.98 → 1.74 ms at 360°); faster only on the numpy fallback | log §7 |

Raw summaries of the history: [`evidence/results/`](evidence/results) (index:
[`evidence/README.md`](evidence/README.md)); the dated changelog with every measurement:
[`archive/CHANGELOG_2026-09.md`](archive/CHANGELOG_2026-09.md).

## Experimental branch evidence, 28.09

The accepted P3 changes and health histogram optimization on the experimental branch have a
separate [integration record](P3_SCORE_SYNC_2026-09-28.md) and
[health validation record](evidence/cycle_2026-09-28/health_histogram/README.md). Those records
identify the measured source and captures. The health runtime captures use the earlier node;
they do not establish runtime parity for the later node changes described above.
