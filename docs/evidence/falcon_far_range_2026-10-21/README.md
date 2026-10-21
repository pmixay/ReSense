# Falcon far range 1.3 (card N7), 21.10

Branch `claude/falcon-far-range-1.3`, base `6ee469c` (detector = v1.2.0 `3b73bbe`). Author evidence; an
independent review is still to come. Protocol: [PROTOCOL.md](PROTOCOL.md). It was registered at `a01acdc`
before any measuring run, and amendments A1–A5 were added before the runs they govern. A4 is the user's
priority change, sent by the captain: distance first, with a bounded false-alarm regression allowed.

**Commits measured.** `544b2f2` is the design (the switch passed with `--pre`). `0eb4dda` switches it on by
default. A replay of `0eb4dda` with no overrides is row-identical to the `544b2f2` candidate on all 4,443
rows. Detector paths are unchanged from `0eb4dda` to the final evidence commit. **Switch state:**
`farrange.with_falcon_profile: true` and `farrange.axis_stable: true` are set in the class defaults and in
both YAML copies. They take effect only under the `falcon_ros` / `falcon_native` profiles; the Pandar
profiles never read them. `detector_freeze.py verify` fails on this branch, as expected after a detector
edit (P1 reseals).

## 1. Result

| row (whole Falcon recording, `falcon_ros`) | v1.2.0 (fresh control) | 19.10 candidate `89e0f3b` (= `c89`) | **21.10 candidate** | `map300` (route map, conditional) |
|---|---|---|---|---|
| **first STOP on the main person** | 127.1 m | 146.3 m (1 frame; held from 127.1 m) | **149.5 m** (≥ 90 % STOP from there) | 249.3 m |
| GO / CAUTION / STOP frames | 13 / 3,043 / 1,387 | 1,420 / 1,635 / 1,388 | 2,148 / 811 / 1,484 | 1,312 / 137 / 2,994 |
| STOP episodes (rule 5.1(b), ≤ 8) | 8 | 9 | **5** | 25 |
| STOP episodes with no person frame | 3 | 0 | **0** | 0 |
| STOP frames not on a person | 18 | 0 | **0** | 2 |
| CAUTION share | 0.685 | 0.368 | **0.183** | 0.031 |
| v1.2.0 person-STOP frames lost | — | 0 | **0** | 0 |
| main-person STOP frames | 1,369 | 1,388 | 1,484 | — |
| frames 0–1700: STOP episodes / not-person STOP frames | 2 / 5 | 0 / 0 | 0 / 0 | 23 / 0 |
| far walker 245–307 m (E4), STOP frames | 0 | 0 | 0 | 338 (240–260 m: 0.83–0.91) |
| 115 m left-wall structure, STOP frames | 29 | — | 1 | — |
| frames whose far trusted range changes by ≥ 20 m | — | 23 % (far line) / 36.5 % (corridor) | **2.3 → 4.1 %** (far line, A3 → A5) / 34 % (corridor, see §4) | — |

**The range goal of ≥ 200 m is not reached without a route map.** The honest unconditional first STOP is
149.5 m, a gain of 22.4 m over v1.2.0. The limit is the observed support, not the sensor (§3).

### Pre-registered criteria (§4 of the protocol, with A4)

| # | criterion | result |
|---|---|---|
| 1 | STOP episodes ≤ 8 (A4: Falcon + ride + empty Pandar ≤ +11) | **PASS**: 5 (−3 vs v1.2.0); Pandar rows unchanged (§5) |
| 2 | 0 STOP episodes without a person | **PASS**: 0 |
| 3 | no v1.2.0 person-STOP frame lost | **PASS**: 0 lost |
| 4 | CAUTION share ≤ v1.2.0 | **PASS**: 0.183 vs 0.685 |
| 5 | not-person STOP frames ≤ 18 | **PASS**: 0 |
| 6 | walk control within ±15 m | **PASS (narrow)**: real 149.7 m; injected 136.7 / 135.1 / 136.7 m (13.0–14.6 m); 150–125 m band STOP fraction 0.34 real vs 0.35–0.41 |
| 7 | injected approach first STOP ≥ v1.2.0 − 2 m, every target and seed | **PASS**: 27 / 27, all later than v1.2.0 by 20–28 m (131–141 m vs 109–117 m) |
| 8 | static STOP fraction ≥ v1.2.0 − 0.05 | **PASS**: 135 / 135 cases (no static target ≥ 150 m is STOPped by either) |
| 9 | moving in-gauge STOP frames ≥ v1.2.0 − 2, outside ≤ +2 | **PASS**: 42 / 42 |
| 10 | `outside` control: 0 STOP | **PASS** |
| 11 | curve / diverging / one-wall negative controls fail safe | **PASS**: 92 / 92 required (the 19.10 axis fails 16 of them) |
| 12 | full Pandar gate, exit 0 without `--allow`, rows identical to v1.2.0 | **PASS**: exit 0 (8 gated better, the same as v1.2.0's run); 15,269 rows identical except the wall-clock latency message (§5) |
| 13 | X3 paired with a fresh v1.2.0 reference | **PASS**: all 40 entries' metrics identical to v1.2.0 |
| 14 | ROS node path | **PASS**: profiles enable it; 250 / 250 frames identical |

Matrix gains (seeds 20–22), in [matrix_tables.md](matrix_tables.md) and [matrix_compare.json](matrix_compare.json):
* Approach from 400 m: first STOP 131–141 m vs 109–117 m.
* Receding walk (120 → 165 m): 97–108 in-gauge STOP frames vs 7–20.
* Receding trolley: 61–72 vs 38–40.
* Crossing at 150 m: 0–11 vs 0.
* Not STOPped by either: targets kept beyond ~140 m (static 150–350 m, the walk 230 → 185 m, the lateral walk
  at 160 m, stop-and-go from 200 m, chaotic motion at 150–190 m).

## 2. What was wrong (traced, CLAUDE.md item 3) and what changed

**Reproduction first.** The cache was rebuilt (89 / 89 decode checks identical). v1.2.0 and the 19.10
candidate reproduce the published rows exactly. Against the archived 19.10 replays, decision, nearest,
clear and monitored are identical on all rows. Frames 4366–4367 report one 28 m detection as a warning
instead (the decision is STOP in both), and `curv` differs in the last float bits.

**Diagnosis**, from `scripts/run_far.py --trace --detail` (a hook on `farline.measure`; the hooked runs are
row-identical to the plain run):
* The 19.10 far axis was one-sided (the left wall) in every frame of the approach. Its trust was therefore
  capped at the near model's `axis_valid`, which jumps between 107 and 171 m frame to frame.
* The person at 137–157 m was STOPped only in frames where that cap reached them. Those were the 4 short
  onsets 2787–2858, which gave the 9th episode.
* The walk control's "146.5 m" was that single frame (frame 2787).
* The right column row was found in most frames, but as a second fitted line it failed the 0.002
  slope-agreement test. That failure rejected the whole frame (888 of the 929 frames where it was accepted).

**The change: `farrange.axis_stable`** (`resense/farline.py`, ~200 lines; hook `dt=` in `detector.py`):
* **C7.** A sparse second side confirms the primary wall. Its bins, from the near end outwards, must stay
  within T = 0.5 m of a line parallel to the primary. The first bin that breaks this line is a
  contradiction, which caps at the last consistent bin.
* **C8.** The support is a vote over the last 10 frames, each value aged at 25 m/s. It is the farthest level
  that at least two frames reach and that more frames reach than contradict. This frame's contradiction
  caps at once.
* **C9.** Without a two-sided support there is no far axis: the near model is used, as in v1.2.0. This
  removes the R1 residual (a one-sided far line inside the near trust).

**In-sample iteration on the real recording, all recorded as amendments** (rows in `results/`):

| version | why it changed | episodes | false episodes | first STOP |
|---|---|---|---|---|
| `3de4534` | first design: own-slope divergence cap, aged | 6 | 2 (115 m structure) | 127.1 m |
| `bff848b` (A2) | second side tested against the primary line | 5 | 1 | 127.1 m |
| `52d2447` (A3) | older contradictions need two frames | 3 | 0 | 127.1 m |
| `544b2f2` (A5) | support as a vote of aged confirmations / contradictions | 5 | 0 | **149.5 m** |

The out-of-sample checks were run after A5 only: the negative controls, the walk control, the matrix with
fresh seeds 20–22, X3, the gate and the node check.

## 3. Why not 200 m: what the physics and the observed support allow

* **Raw geometry**, in the track reference, frames 1300–1700 and 3900–4440 ([`scripts/scene.py`](scripts/scene.py),
  [figs/scene_late.png](figs/scene_late.png)):
  * The left boundary is contiguous to 192 m, has **no returns at 195–245 m** (≤ 0.07 points per frame at
    any height), then returns at 247–262 m.
  * The right column row stands every 30 m in two lateral families: −1.35 … −1.68 m and −1.97 … −2.16 m.
    Relative to a line along the left wall, the 172 m column sits ~0.5 m out of line.
* **Consequence for the second side.** With the review's rule "trust ends at the shorter side" (R1), the
  right row confirms parallelism to 142 m in most frames. It confirms 172 m in 26 % of frames and is
  contradicted after 142 m in 49 %.
* **Consequence for the trust and the first STOP.** The trusted far range is 124–154 m (p5–p95, median
  134 m), and the first STOP on the person comes at 149.5 m. Bridging the 56 m left gap or the 60 m gap of
  the row would trust geometry nobody observed. A track that leaves through such a gap is exactly the R1
  failure.
* **Sensor physics, unchanged from 19.10.** The person gives 4.4 returns per frame at 250–260 m and fewer
  than 1 beyond ~280 m.
* **With a route map** (`declared_straight_to = 300`, conditional, never the unconditional result): first
  STOP 249.3 m. It flickers on the real far walker at 240–270 m (25 episodes, none without a person), so it
  fails 5.1(b) and the A4 bound.
* **Figure:** [figs/trust.png](figs/trust.png) shows the far trusted range per frame (19.10 vs 21.10) against
  the person's raw distance, plus the STOP frames of the three runs.

## 4. What was checked, how, and what is open

* **Negative controls.** [`scripts/neg_controls.py`](scripts/neg_controls.py) produces
  [neg_controls.json](neg_controls.json): 92 required cases for each axis. They cover the review's 16 curves
  ×2 (occluded inner wall), diverging walls, one wall, a parked train, a second side ending early, S-jogs,
  a niche or recess, and new cases: a sparse row following a curve away from or towards a straight wall,
  the same row in alternate frames, and a curve start approaching at 20 m/s.
  * `axis_stable`: 92 / 92 fail safe. The 19.10 axis fails 16, all one-sided inside the near trust (R1 residual).
  * **Reported, not required:** a turnout leaving a straight two-wall tunnel through a 35 m gap fools both
    axes (error tens of metres). Physically, for R ≥ 300 m and a boundary ≥ 1.7 m from the axis, a train needs
    an opening of ≥ 44 m, and the support already ends at gaps > 40 m. A metro turnout with R ≈ 200 m needs
    only ~36 m, so this is an **unverified residual** shared with the 19.10 axis and the near model.
* **Unit tests.**
  * `tests/test_farrange.py` has 7 new acceptance tests, registered before the change. The 19.10-axis tests
    now pin `axis_stable=false`.
  * Full suite (without `tests/test_algorithm.py`, which cannot import open3d here: `libEGL.so.1` missing):
    23 failed + 9 errors. These are the **same test IDs as on v1.2.0** in this container.
* **Doubt model** (`tracking.doubt_model`, captain's request A4.5).
  * Rows with `doubt_model=""` are identical to the default on all 4,443 rows, for v1.2.0 and for the
    candidate.
  * No `doubt` warning appears in any of the 408 matrix cases.
  * Positive control: with `doubt_threshold=1.0`, the label appears (10 withheld frames) and the first STOP
    moves from frame 2904 to 2968.
  * Conclusion: it delays nothing on the Falcon, so no Falcon change is needed.
* **Node path.** [`scripts/node_check.py`](scripts/node_check.py) feeds the real `DetectorNode` (rclpy stand-ins
  from `tests/test_node.py`, `sensor_profile:=falcon_ros`, YAML with the switches) with the raw CDR bytes of
  frames 2650–2900. The detector results equal the offline replay on 250 / 250 frames. The published
  decisions are equal except frame 0 (`epoch_unconfirmed`, the node's normal first frame). Both
  `falcon_ros` and `falcon_native` enable the far axis; `manual` and `pandar128` never do.
* **Instrumentation.** The traced and detail-hooked runs equal the plain runs. The `c89` run after the
  bin-builder refactor equals the v1.2.0 candidate row for row. The matrix prefix check shows 0 mismatches
  (base and cand).
* **Timing** (not a criterion, A4.6). Same machine, frames 2600–3200, cache input, detector stage:
  v1.2.0 p50 16.6 / p95 25.2 ms; candidate p50 19.3 / p95 30.5 ms.
* **Open:**
  * **Corridor trust still flickers.** The corridor's effective trusted range, max(near `axis_valid`, far
    valid), still changes by ≥ 20 m in 34 % of frames. The near model's own `axis_valid` (107–167 m)
    dominates when it is larger, and beyond the far trust the near laterals are used, as in v1.2.0.
    Stabilising the near model is not done here.
  * **Shared turnout residual:** the turnout case above.
  * **No moving-train recording:** the history is aged at 25 m/s, and the moving case is synthetic only (J).
  * **Thin walk-control margin:** 13.0–14.6 m against the ±15 m limit.
  * **R2 / bias** (19.10 review note 3, −0.16 m at 250 m): not re-measured.

## 5. Pandar regression gate (criterion 12) and the A4 false-alarm bound

**Runs.** `scripts/regression_gate.py --cache /data/cache --jobs 2 --baseline
docs/evidence/results/regression_baseline_2026-09-29_shell_off.json`, without `--allow`. It was run once in
the v1.2.0 checkout `3b73bbe` and once on this branch (detector = `0eb4dda`), on the same caches:
* the six recordings (bag SHA-256 = `scripts/cold_bags.sha256` where listed; frame counts 201 / 345 / 252 /
  268 / 545 / 877);
* set O (1,510 frames; bag 7,421,644,800 bytes);
* the ride via `scripts/cache_extended_ride.py` (221 splits, 11,271 frames; archive size and SHA-256
  `8124b627…` verified, [results/ride_intake.log](results/ride_intake.log));
* set F straight.

**Both runs: GATE PASS, exit 0** ("no gated metric worse; 8 gated better, 0 worse but allowed, 25 information
rows changed": the same line for v1.2.0 and the candidate). Files:
[results/gate_v120.json](results/gate_v120.json), [results/gate_cand.json](results/gate_cand.json) and the logs.

**A first attempt failed for an environment reason.** It exited 2 in both checkouts because set F could not
import open3d (`libEGL.so.1` missing): [results/gate_cand_without_open3d.log](results/gate_cand_without_open3d.log).
The fix was `apt-get install libegl1` in the container, then a rerun. The gate itself was not changed and no
`--allow` was used.

**Per-row comparison**, [`scripts/gate_rowdiff.py`](scripts/gate_rowdiff.py) →
[results/gate_rowdiff.json](results/gate_rowdiff.json), every field except wall-clock timing:
* 15,269 per-frame rows over 15 files: identical except 97 rows of ride chunk 4.
* Those 97 rows differ only in `health.messages`: the wall-clock `latency p95 … ms over the 100 ms budget`
  message, present in one run and not the other. All 97 message differences contain it, checked
  programmatically; rows 189 and 287 were printed and read.
* One of them also differs in `health.level` (ok vs warn, from that message). Its `decision_level`,
  obstacle and warning are identical.
* Set F straight: identical except the effective-config SHA-256 (the YAML now carries a `farrange`
  section; 19.10 review note 1) and the wall time.

So Pandar is row-identical to v1.2.0 in everything the detector decides, as designed: `farrange` is read
only under the Falcon profiles.

**A4 bound.** Added STOP episodes: Falcon −3 (8 → 5), ride 0, five empty Pandar recordings 0. The total is −3
against a bound of +11. No false-alarm row regressed, so no `--allow` run was needed. X3 on `0eb4dda`
against a fresh v1.2.0 reference: PASS, all 40 recording × variant metrics identical
([results/x3_cand_0eb4dda.json](results/x3_cand_0eb4dda.json),
[results/x3_v120_reference.json](results/x3_v120_reference.json)).

## 6. Reproduce

```bash
# environment: Python 3.12 venv, pip install -e ".[dev]", pip install rosbags==0.11.5, scripts/build_native.sh
. docs/evidence/falcon_far_range_2026-10-21/scripts/env.sh <checkout>
E=docs/evidence/falcon_long_range_2026-10-19/scripts; F=docs/evidence/falcon_far_range_2026-10-21/scripts
python $E/cache_falcon_full.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out /data/falcon          # 4.9 GB, ~13 min
python $F/run_far.py --cache /data/falcon --profile falcon_ros --out base          # in a v1.2.0 checkout
python $F/run_far.py --cache /data/falcon --profile falcon_ros --trace --out cand # this branch (defaults on)
python $F/run_far.py ... --pre farrange.axis_stable=false --out c89               # the 19.10 axis
python $F/run_far.py ... --pre farrange.declared_straight_to=300 --out map300
python $E/falcon_eval.py --base base.jsonl --cand cand.jsonl --out eval.json
python $E/walk_control.py specs && for s in 0 1 2; do python $F/run_far.py ... --frames 0:1211 --inject specs/walk_seed$s.json --out walk_s$s; done
python $E/walk_compare.py --real cand.jsonl --inj walk_s0.jsonl walk_s1.jsonl walk_s2.jsonl --spec specs/walk_seed0.json --out walk.json
python $F/matrix2.py --name base --out m --seeds 20,21,22 --check-prefix          # v1.2.0 checkout
python $F/matrix2.py --name cand --out m --seeds 20,21,22 --check-prefix
python $F/matrix_compare.py m/base_summary.json m/cand_summary.json --out matrix_compare.json
python $F/neg_controls.py --out neg_controls.json
python $F/node_check.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --frames 2650:2900 --farrange with_falcon_profile=true,axis_stable=true --out node
python scripts/robustness_battery.py --repo <checkout> --cache /data/decoded --out x3.json -j 2 [--reference v120.json]
```

Raw outputs in [raw/](raw/) (xz, `SHA256SUMS`):
* `replays.tar.xz`: every full replay named here, plus the iterations, the walks, the doubt runs and the
  default-config replay.
* `matrix_cases.tar.xz`: 408 cases.
* `node_check.tar.xz`, `detail.tar.xz`: the per-side bins of the v1.2.0 candidate.
* `map300_final.tar.xz`.

Evaluations are in [results/](results/). The Falcon cache, the Pandar caches and the gate work directories
are not committed; the commands above regenerate them.
