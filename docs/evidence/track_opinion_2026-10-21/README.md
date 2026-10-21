# Track opinion 1.3 (card G2): retrain and improve the learned doubt model

> Author evidence for an independent reviewer. Branch `claude/track-opinion-1.3`, base `6ee469c` (detector bytes
> equal v1.2.0). Protocol: [PROTOCOL.md](PROTOCOL.md) (registered at `244a452` before any measuring run; amendments
> A1, A2 appended before any §3 run). Measured candidate code: `30aece0` (model file + code; later commits are
> scripts and evidence only). Environment: Python 3.12 venv, numpy 1.26.4, scipy 1.11.4, scikit-learn 1.4.2,
> `scripts/build_native.sh`, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `RESENSE_REPO` = the evaluated tree,
> 4 vCPU container. `detector_freeze.py verify` **fails on this branch** (expected: `resense/config.py`,
> `resense/opinion.py`, both YAML copies, `sensor_profiles.py` and a new model file changed); the captain reseals.

## Answer

1. **The shipped 27.09 model still earns its place on v1.2.0, but mostly in-sample, and with a thin margin.**
   Gate on v1.2.0, opinion off → on: ride false events **30 → 23**, STOP episodes **30 → 26**, five recordings
   9 / 14 → 7 / 11 (`squareT_platform`), set O background 3 → 0 frames; no labelled-object, set F, range-test,
   far-target or Falcon row changes. On 1,017 new synthetic positive onsets beyond 25 m (none of which it has seen)
   it delays **none**, but its lowest score is **0.0177 against its threshold 0.015** (1.18×, not the 2× it was
   tuned for); at 0.03 it would delay 5 sequences.
2. **A retrained model that is honest about real objects earns nothing out of fold on v1.2.0.** With the 27.09
   recipe reproduced on v1.2.0 (R0: held-out AUC 0.978 vs the report's 0.9745) the out-of-fold gain is ride
   35 → 34 events at the 2× margin. With realistic positives (475 sequences: far starts to 250 m, moving, crossing,
   standing train, sizes jittered, rail objects across the rail) and only the 18 features whose synthetic
   distribution matches the real objects, **no threshold that delays zero held-out synthetic sequences removes a
   single held-out false event** (ride 35 → 35, empty 10 → 10), also with 3.7× more negatives from X3-style
   augmentation; removing 6 ride events costs ≥ 21 delayed held-out synthetic sequences.
3. **The 27.09 model's dominant feature fails the synthetic-versus-real check.** `lat_std` (importance 0.46–0.50)
   of the real crossing person in `doubleT_obstacle` lies outside the synthetic band in 21 % of its rows (real
   median 0.155 m vs synthetic 0.030 m); the Falcon person is twice as wide as the synthetic one (0.88 vs 0.40 m).
   A model leaning on lateral stability and the body shape of five meshes is what keeps the margin thin.
4. **Falcon:** the shipped model never withholds on the Falcon recording (all 17 onsets beyond 25 m score
   ≥ 0.022 > 0.015): opinion on and off are identical on every non-timing field of all 4,443 frames, in the
   `falcon_ros` profile and in the manual path. The candidate scores the real person (0.036–0.20) *below* the
   false 115 m support structure (0.21–0.80): no evidence that it generalises. `tracking.doubt_falcon: false`
   (option F-a) turns the opinion off in the Falcon profiles; it is implemented, tested and measured (identical to
   v1.2.0 on the recording), but **left at `true`** because protocol §5 flips it alone only on an H3 improvement.
5. **Decision (§5): defaults unchanged** (`doubt_model: track_opinion.json`, `doubt_threshold: 0.015`,
   `doubt_falcon: true`). The new file `resense/models/track_opinion_1.3.json` ships **off**: it passes every hard
   row because it is inert (equal to opinion-off on every gate row), and therefore fails G1 / G1x / G2 / G2x and
   the gate (exit 1, ride 23 → 30 events). The pipeline that produced it is one command and byte-reproducible, for
   the rerun on the integrated 1.3.0 detector.

## Result table (candidate `track_opinion_1.3.json` @ 0.0101 vs a fresh v1.2.0 control)

| row | set | control (v1.2.0, shipped model) | candidate | criterion | pass |
|---|---|---|---|---|---|
| ID | branch at defaults vs v1.2.0 tree | — | gate: see "Not checked"; Falcon 0 of 4,443 rows differ (manual and `falcon_ros`) | identical | PASS (Falcon) |
| H1 | set O, inside objects (gate per frame) | 450 alarm frames, background 0 | every inside- and outside-object row identical; background 0 → 3 frames (2 track ids), total 450 → 451 | no first STOP later, no STOP frame lost | PASS |
| H2 | `doubleT_obstacle` labels | hits / first alarm frame | identical | not fewer / not later | PASS |
| H3 | Falcon person, `falcon_ros` | first STOP 127.1 m, 1,369 person STOP frames | identical (F-a and F-b) | not later, 0 lost | PASS |
| H3 | Falcon person, manual path | 124.7 m, 1,350 frames | identical | same | PASS |
| H4 | X3 positives | see [X3](#x3) | see [X3](#x3) | 0 lost matching STOP rows | see X3 |
| H5 | range test A / C, person and 1 m cube | A person 218.4 m, A cube 151.1 m, C person 82.8 m, C cube 85.7 m first STOP; 158 / 104 / 55 / 57 STOP frames | every row identical | not later, 0 lost | PASS |
| H6 | far-target set 150–250 m (32 sequences) | first detections person median 106.3 m, box1.0 95.7 m, box0.5 60.8 m, trolley 107.3 m | first detection and every detected frame identical in 32 / 32; false detections +2 to +3 in 8 sequences | not later, 0 lost | PASS |
| H6 | set F straight (gate) | | identical | not worse | PASS |
| G1 | ride, gate | 23 events / 26 episodes | 30 / 30 | ≤ control | **FAIL** |
| G1x | ride, cross-fitted (4 folds) | 23 / 26 (shipped model, same pieces) | 30 / 30 | ≤ control | **FAIL** |
| G2 | five recordings, gate | 7 events / 11 episodes (all on `squareT_platform`) | 9 / 14 | ≤ control | **FAIL** |
| G2x | five recordings, fold E model | 7 / 11 (gate) | fold E model at 0.0100, replayed on the five recordings' rows: 10 → 10 events (withholds nothing, so its run equals opinion-off: 9 / 14); not run in the detector | ≤ control | **FAIL** (by replay; see Not checked) |
| G3 | Falcon false STOP episodes | 3 (`falcon_ros`), 2 (manual) | 3, 2 | ≤ control | PASS |
| gate | full gate vs the seal baseline, no `--allow` | PASS (exit 0) | **FAIL** (exit 1: ride events, squareT events / episodes, set O background frames / ids) | exit 0 | **FAIL** |

Switch state at the head of the branch: **all defaults v1.2.0** (`track_opinion.json`, 0.015, `doubt_falcon: true`).

## What the shipped model earns, and how far thresholds move it

Gate on v1.2.0 ([`out/gate/`](out/gate/)): control 23 events / 26 STOP episodes / 111 alarm frames on the ride;
opinion off 30 / 30 / 154. All 66 per-frame differences between the two runs are attributed
([`out/gate/explain_ctl_cand.json`](out/gate/explain_ctl_cand.json), candidate = off): 64 rows where a STOP of the
off run is an advisory with reason `doubt` in the control, 2 rows where only that reason label differs on an
advisory that is advisory in both runs (ride piece 1 rows 1267–1268, track 301).

Replay of the doubt rule on the v1.2.0 rows (`scripts/replay_model.py`, opinion pinned off as collected; the ride
and empty rows are not out of fold for the shipped model's 27.09 training on the same ride):

| threshold | ride events kept (of 35) | empty (of 10) | synthetic positive sequences delayed (of 607 events) | test objects delayed (set O, dto, crossing, Falcon) |
|---|---|---|---|---|
| shipped 0.0075 | 33 | 10 | 0 | 0 |
| **shipped 0.015 (default)** | **27** | **9** | **0** | **0** |
| shipped 0.0177 (its highest delay-free) | 24 | 7 | 0 | 0 |
| shipped 0.03 | 19 | 7 | 5 | 0 |
| shipped 0.06 | 11 | 3 | 11 | 0 |
| candidate 0.0066 / 0.0101 (chosen) / 0.0202 (zero margin), out of fold | 35 / 35 / 34 | 10 / 10 / 10 | 0 / 0 / 0 | 0 / 0 / 0 |
| candidate at its positive quantiles 0.5 % / 1 % / 2 % (0.059 / 0.099 / 0.198), out of fold | 29 / 24 / 20 | 9 / 9 / 8 | 23 / 32 / 53 | 12 / 16 / 46 rows |

## What was done

1. **Data** (VM_GUIDE §2): the six Pandar caches (counts 201 / 345 / 252 / 268 / 545 / 877), set O (1,510), the ride
   via `scripts/cache_extended_ride.py` (archive SHA-256 `8124b627…` verified, 221 splits, 11,271 frames; 5 sampled
   frames bit-identical to a first `.npy` cache made by the VM_GUIDE stream), node-decoded caches for X3 / range
   test, Falcon streamed per run from the organizers' link (4,443 frames found, kept, 0 lost, every pass).
2. **Falcon control and rows** ([`scripts/falcon_multi.py`](scripts/falcon_multi.py): one stream, one node replica
   per config; [`scripts/falcon_eval13.py`](scripts/falcon_eval13.py): N2 anchors + far-walker labels as
   `falcon_long_range_2026-10-19/scripts/falcon_eval.py`). The v1.2.0 control reproduces the published figures
   (`falcon_ros`: 1,387 STOP / 8 episodes / 3 false / first person STOP 127.1 m, as `falcon_long_range` REPORT §4;
   manual: 1,364 STOP rows, as `f1a_acceptance_2026-10-20`).
3. **Collection** (`scripts/track_opinion_pipeline.py`, opinion pinned off, branch tree): ride 15,290 rows, five
   recordings 3,733, set O 2,309, `doubleT_obstacle` 369, Falcon 13,108; synthetic positives 11 sets, 475 sequences,
   30,342 rows; augmented negatives 8 sets ([`out/rows/`](out/rows/), [`out/train/collect.log`](out/train/collect.log)).
4. **R0** (the 27.09 recipe on v1.2.0, 19 features, its two positive families): 180 negative / 3,219 positive rows,
   82 sequences, held-out AUC **0.9782** (report 0.9745), `lat_std` importance 0.501 (0.459), zero-margin threshold
   0.0158 (0.03), out of fold ride 35 → 29 (zero margin) / 34 (2×) ([`out/train/r0_report.json`](out/train/r0_report.json)).
   The 27.09 datasets are not archived, so the shipped JSON itself is not rebuilt.
5. **Synthetic versus real** ([`scripts/feature_check.py`](scripts/feature_check.py),
   [`out/train/feature_check.json`](out/train/feature_check.json) first, [`feature_check_a1.json`](out/train/feature_check_a1.json)
   after A1). Found and fixed two generator defects (A1): the synthetic rail object stood on the bed spread over
   ±0.8 m where the real one lies across the rail (|lat| 0.85 m, bottom below the rail head) — `--on-rail`; every
   synthetic body had one size — `--size-jitter 0.3`. Dropped as artefacts: `raw_per_vox` (the recordings hold each
   echo twice: real 1.85–2.27 vs synthetic 1.12–1.32 returns per voxel, 0 % of real rows inside), `ring_fill` (no
   channel ids on injected points), the count features (fail on the Falcon person). Still failing after A1 and
   dropped by the registered 80 % rule: `abs_lateral`, `lat_std`, `cz_std`, `hmax_mean`, `hmin_mean`,
   `height_mean`, `width_mean`, `dist_rough`, `hmax_last`, `top_rel`.
6. **Candidate** (frozen at `30aece0`): 18 features (`distance, is_low, frac_low, hits, lat_jump, len_mean,
   gauge_frac, frac_demoted, frac_column, frac_beyond, dist_step, hit_fraction, frac_core, frac_cut, frac_weak,
   frac_thin, frac_spared, dist_span`), 60 depth-3 trees as before, every positive sequence the same total weight,
   negatives plus augmentation (665 rows), grouped cross-fitting by ride piece / recording (sequences go with the
   piece they are injected into), threshold = ½ × the highest that delays no held-out synthetic sequence (0.0202
   → 0.0101). Held-out AUC 0.968, export identical to scikit-learn (max |Δp| 0). Variants tried (all in
   [`out/train/variants/`](out/train/variants/)): with / without sequence weights, the 19 R0 features on the new
   positives, the 18 features on the R0 positives, each with plain and augmented negatives: none removes a
   held-out false event at zero delayed held-out sequences.
7. **Measurement** (§3): gate on the control, opinion-off and the candidate; `scripts/opinion_crossfit.py` with the
   four fold models (+ the shipped model and off on the same pieces); Falcon in both paths with F-a and F-b; range
   test and far-target set in the control and a local candidate-defaults worktree (`9661cc7`, **not pushed**, diff
   = the three defaults in `resense/config.py` and both YAML copies); X3 on both trees.

## What was checked and how

| check | method | result |
|---|---|---|
| control reproduces published v1.2.0 figures | gate vs `f1a_acceptance_2026-10-20` (ride 23 / 26 / 111); Falcon vs the long-range REPORT and f1a | equal |
| the candidate is inert | per-frame `cmp_frames.py` candidate vs opinion-off gate work dirs | 0 of 15,269 rows differ (639 latency-level only); positive control: control vs candidate 66 rows |
| every changed gate row explained | [`scripts/explain_rows.py`](scripts/explain_rows.py) on all 66 rows | 64 withheld STOPs (`doubt`), 2 reason-label rows, inspected by hand |
| cross-fit harness | the shipped model run through `opinion_crossfit.py` on the same pieces | 23 / 26 / 111, equal to the gate |
| Falcon identity and gating | every non-timing field of 4,443 rows; F-a replica's effective config | branch defaults = v1.2.0 tree (both paths); F-a `doubt_model ''`; positive control: manual vs `falcon_ros` differ on all 4,443 rows |
| person labels of Falcon rows | rows labelled from N2 anchors / far-walker paths; STOP rows on the person 1,369 = the control's person STOP frames | consistent |
| pipeline reproducible | `--stages model` run twice | model JSON and report byte-identical |
| export = scikit-learn | `export_max_abs_diff` on 300 rows, every model | 0.0 |
| cost wrapper does not change results | decisions of the timed and an untimed run, 600 ride frames, each config | equal |
| physical plausibility | ICP travel of C 400.6 m over 267 frames (≈ 15 m/s); range-test and far-target first STOP distances in the range of earlier judge runs | plausible |

## Cost

`Tracker._doubt` on 600 ride frames ([`out/opinion_cost.json`](out/opinion_cost.json)): shipped 0.008 ms mean,
0.011 ms p95, 0.53 ms max per frame (one evaluation at an onset); candidate 0.008 / 0.011 / 0.46 ms;
`Detector.process` ≈ 30 ms mean, 45 ms p95 in all three (noise on a shared 4 vCPU machine).

## X3

(filled in below when the candidate battery finished)

## Not checked / unverified

* The gate of the branch **at its own defaults** (row ID on Pandar) was not run separately; ID rests on the code
  (the new code is the appended features, read only by a model that names them, and the profile switch at
  `true`), on the unit test that the shipped model's scores are unchanged, and on the Falcon identity run.
* G2x was evaluated by the offline replay of the fold E model, not by a detector run of the five recordings.
* The ride has no ground truth: "false" events are by construction (an obstacle-free ride).
* The synthetic-versus-real comparison rests on two real Pandar objects (one person crossing at 56 m with the train
  standing, one rail object) and one Falcon person; the 80 % rule is a judgement on that small sample.
* The X2 false-STOP ledger (`claude/x2-ledger-1.3`) had only its script when training started (no classified
  episodes); not used.
* Not done from the task's list: frame-context features that need the frame's points (returns behind the object);
  only cluster-level flags were added.

## Reproduce

```bash
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros
E=docs/evidence/track_opinion_2026-10-21
python scripts/cache_extended_ride.py --cache /data/cache/new_data --spool /data/.spool --reserve-gib 3   # + VM_GUIDE §2 caches
python $E/scripts/falcon_multi.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out OUT --spec SPEC.json      # Falcon rows / runs
python $E/scripts/falcon_eval13.py label OUT/off_ros.rows.npz OUT/off_ros.jsonl --case explicit_ros --out test_falcon_ros.npz
python scripts/track_opinion_pipeline.py --cache /data/cache --work WORK --falcon-rows test_falcon_ros.npz \
    --export resense/models/track_opinion_1.3.json          # collect + R0 + model + 5 fold models, one command
python $E/scripts/feature_check.py --syn WORK/p*.npz WORK/r0_moving.npz WORK/r0_standing.npz \
    --real dto_low=WORK/test_dto.npz:railobj,lowbox:is_low=1 --real dto_body=WORK/test_dto.npz:person:is_low=0 \
    --real falcon=test_falcon_ros.npz:person,hivis --out check.json
python scripts/regression_gate.py --cache /data/cache --jobs 2 --set tracking.doubt_model=track_opinion_1.3.json \
    --set tracking.doubt_threshold=0.0101 --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json
python scripts/opinion_crossfit.py --fold 0,1:WORK/foldA.json:0.0037 --fold 2,3:WORK/foldB.json:0.0032 \
    --fold 4,5:WORK/foldC.json:0.0111 --fold 6,7:WORK/foldD.json:0.0059 \
    --baseline-model resense/models/track_opinion.json:0.015 --baseline-model off --out crossfit.json
$E/scripts/run_range.sh <tree> <out>;  far: scripts/far_range_eval.py --files 184,198,210,7,19,154,11,158 \
    --kinds person,box1.0,box0.5,trolley --start 250 --frames 140 --seed 21
python scripts/robustness_battery.py --repo <tree> --cache /data/decoded --out x3.json -j 2 [--reference x3_ctl.json]
```

Raw outputs: [`out/`](out/) (gate JSONs, tables and per-frame work dirs `out/gate/gatework_ctl_off_cand.tar.xz`;
Falcon records `out/falcon/falcon_records.tar.xz`; range-test rows; far-target JSONs; every collected row set;
reports of R0, the candidate, the folds and every variant). The ride / Falcon caches themselves are regenerated
by the commands above.
