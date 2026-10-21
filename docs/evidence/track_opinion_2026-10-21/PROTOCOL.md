# Track opinion 1.3 (card G2): pre-registered protocol

Registered **before any measuring run** of a candidate (21.10). Branch `claude/track-opinion-1.3`, base
`6ee469c` (detector bytes equal v1.2.0, `detector_freeze.py verify` PASS, digest `6d091081…`). Author
evidence: an independent reviewer checks it afterwards. Amendments are appended at the end, dated, with the
reason, and never rewrite a registered criterion after its data were seen.

## 0. What is changed and what is not

* Only the existing learned component is retrained and improved: the gradient-boosted tree ensemble of
  `resense/opinion.py` read from `resense/models/*.json`, applied by `Tracker._doubt`. No new learned component.
  The doubt rule itself (extra hits, near range, sticky, body exemption, never a veto) is not changed.
* The new model ships as a **new file** `resense/models/track_opinion_1.3.json` (report
  `track_opinion_1.3_report.json`), selected by `tracking.doubt_model`; `track_opinion.json` stays.
* New features may be appended to `FEATURES` (the shipped model reads its columns by name, so its scores are
  unchanged; checked by a test and by the identity row ID below).
* Falcon handling behind a new switch `tracking.doubt_falcon` (class default and both YAML copies equal):
  `true` = v1.2.0 behaviour (the model is applied whatever the sensor); `false` = the Falcon profiles
  (`falcon_ros`, `falcon_native`, i.e. range model `falcon_prime`) turn the opinion off.
* Defaults stay v1.2.0 (`doubt_model: track_opinion.json`, `doubt_threshold: 0.015`, `doubt_falcon: true`)
  until the final commit; they are flipped there only under §5.

## 1. Data, groups, leakage

* Pandar caches (VM_GUIDE §2): six recordings, set O, the ride (11,271 frames, the gate's 8 pieces); node-decoded
  caches (`judgement_2026-10-13/scripts/cache_decoded.py`) for X3 and the range test; Falcon streamed from
  `https://disk.yandex.ru/d/SfBeRHbs8bNJAQ` (`scripts/stream_falcon.py` machinery, one node replica per config).
* **G3 (`docs/evidence/heldout_2026-10-15`) is never run, trained or tuned on.**
* Training groups: ride piece `new_data:K` (K = 0..7) together with every synthetic sequence ray-cast into it;
  each of the five obstacle-free recordings; Falcon (one group, only if Falcon rows are used for training).
  Cross-fitting and threshold calibration are by group (no frame of a held-out group, and no synthetic sequence
  injected into it, is seen by the model scoring it).
* Never trained on (test only): set O, `doubleT_obstacle`, the Falcon person, the X3 battery, the range test,
  the far-target set, set F straight. `doubleT_obstacle` objects and the Falcon person are used only for the
  synthetic-versus-real feature comparison (§2) and as tests.
* Training injection files of the ride are disjoint from the far-target set and from set F straight
  (files 46, 68, 98, 140, 168, 172): no training sequence starts within ±3 split files of a test file.

## 2. Development (choice of features, positives, hyper-parameters, threshold)

Done on training groups only, with grouped out-of-fold scores and the offline replay of the doubt rule
(`scripts/track_opinion.py train`, `simulate`). Steps:

1. **Reproduction R0.** The 27.09 recipe re-run as close as the record allows on the v1.2.0 detector, opinion
   pinned off (`tracking.doubt_model=""`, as the recipe collects): rows, held-out AUC, the replayed threshold.
   The 27.09 datasets are not archived in the repository (`/data/work/p2ride_c1` of that machine), so the shipped
   JSON cannot be rebuilt byte for byte; what is checked is the recipe's own numbers on today's detector and
   that `export_gbm` matches scikit-learn (`export_max_abs_diff` 0).
2. **Synthetic-versus-real check of every feature.** Real positive rows: the labelled in-gauge objects of
   `doubleT_obstacle` (`labels/doubleT_obstacle.json`, the gate's matcher) and the Falcon person (frames > 2900,
   rows whose track matches a person STOP of the v1.2.0 run). For each feature, the share of real rows inside
   the [2.5 %, 97.5 %] range of the synthetic positive rows of the same kind family (person / box-like) and range
   band (±10 m). **A feature is dropped when that share is below 80 % for either real set**, intensity is never
   a feature, and point-count features enter only in a sensor-normalised form and only if they pass this check.
3. **Positives.** Synthetic sequences ray-cast into ride frames (`resense.synthetic.inject_obstacles`,
   `far_range_eval.legacy_placement`), kinds person, hivis, box0.3, box0.5, box1.0, trolley, cable, cable_low,
   lowbox, railobj, dog, plank; moving train and standing train; starts up to 250 m; crossing and slowly moving
   objects. Positive rows are the in-envelope STOP-candidate rows beyond `doubt_near` as in the recipe.
4. **Negatives.** The rules' STOP rows on the ride pieces and the five empty recordings; the X2 ledger's
   classified false-STOP episodes if `claude/x2-ledger-1.3` has them when training starts (it has only the
   script on 21.10). Falcon false STOP episodes as negatives only under Falcon option F-b (§4).
5. **Threshold.** The highest threshold at which no held-out synthetic sequence is delayed by the replayed rule
   (`max_delayed` 0), then a margin factor ≥ 2 below it (as 1.2.0: 0.03 → 0.015). The candidate is the
   (features, model, threshold) with the most cross-fitted replayed ride + empty false-event removal among those
   with 0 delayed held-out synthetic sequences at the chosen threshold. Frozen before §3 runs (commit hash
   recorded).

## 3. Measurement of the frozen candidate (each against a fresh v1.2.0 control run)

Control = a worktree at `6ee469c` (v1.2.0 detector bytes) with its defaults. Candidate = the branch with
`tracking.doubt_model=track_opinion_1.3.json`, its threshold, and the Falcon option (§4); for X3 and the range
test, whose drivers take no overrides, a local unpushed worktree commit that only flips those defaults (its hash
and diff recorded). Identity row **ID**: the branch at its committed defaults equals the control on every
non-timing gate row and every Falcon row (the new code is inert at v1.2.0 settings).

### Hard rows (range first). Every one must hold; "not later" = first STOP at the same or a larger distance.

| id | set | criterion against the control |
|---|---|---|
| H1 | set O, every inside object (gate, per frame) | first STOP not later; no control STOP frame of the object lost |
| H2 | `doubleT_obstacle` labelled objects (gate, per frame) | labelled hits per label not fewer; first alarm frame not later; no control STOP frame on a label lost |
| H3 | Falcon person (frames > 2900, `score_falcon_pos.py` association), `falcon_ros` profile and the manual (default-config) path | first person STOP not later; 0 person STOP frames lost |
| H4 | X3 positives (`robustness_battery.py`, `doubleT_obstacle` and set O, 10 variants each) | per object and variant: no matching STOP row lost, first STOP not later (stricter than the battery's own ±2 tolerance; the battery's own comparison is reported too) |
| H5 | range test person 0.5×0.5×1.75 and cube 1.0 on A (`roundT_squareT_pressureGate_squareT`, start 150, d0 230, end 340) and C (`roundT_pressureGate_roundT`, start 0, d0 230) (`judgement_2026-10-13/scripts/range_test.py`, ICP odometry) | first STOP not later; no STOP frame on the object lost |
| H6 | far-target set 150–250 m: `scripts/far_range_eval.py --start 250 --frames 140 --kinds person,box1.0,box0.5,trolley --seed 21` on 8 straight ride files chosen by rule (lowest `curv_abs_med` with `speed_tracks` ≥ 5 m/s, not set F files, ≥ 4 files apart from each other and from every training injection file), plus set F straight in the gate | per sequence: first confirmed detection not later, no detected frame lost; set F straight gate rows not worse |

### Gain rows (false alarms; matter less than range, but must be no worse than v1.2.0)

| id | set | criterion |
|---|---|---|
| G1 | ride, gate (8 pieces, in-sample for the ride negatives) | alarm events and STOP episodes ≤ control |
| G1x | ride, cross-fitted (`scripts/opinion_crossfit.py`, 4 folds of 2 pieces, each fold model and threshold chosen by §2 without its pieces) | events and episodes ≤ control (v1.2.0's shipped model on the same pieces) |
| G2 | five obstacle-free recordings, gate | events and STOP episodes ≤ control, per recording |
| G2x | the same, run with a fold model trained without the five recordings | reported; ≤ control required |
| G3 | Falcon false STOP episodes (STOP episodes with no person frame; frames 159, 2312–2314, 4394–4401 are the v1.2.0 non-person STOP frames) | ≤ control, in the `falcon_ros` profile and in the manual path |

Plus: the full regression gate against the seal baseline **without `--allow`** (exit 0), X3 on the candidate
against the X3 of the control (battery comparison), every changed row of the gate's per-frame output and of the
Falcon run explained (paired per-row diff, track lineage), and the per-frame cost of the opinion (mean / p95 of
`Tracker._doubt` and of `Detector.process`, recorded, not a criterion).

### Threshold report

For the candidate model at thresholds {0, the chosen one, 0.5×, 2×, the `max_delayed` value} and for the shipped
model at 0.015: replayed ride / empty false events removed (cross-fitted) and held-out synthetic sequences / test
objects delayed (replayed per frame on the collected test rows). Information, not a criterion.

## 4. Falcon

* **F-a (gate off):** `tracking.doubt_falcon: false`; the Falcon profiles turn the opinion off.
* **F-b (apply):** the model is applied to the Falcon only if it is shown to generalise: Falcon rows collected
  (v1.2.0, opinion off), the Falcon person's onset rows scored above the threshold (0 delayed), and H3 / G3 pass
  in a real Falcon run with the model on.
* Choice: F-a, unless F-b passes every Falcon row and F-a fails G3. If the shipped model is found to delay the
  Falcon person's first STOP, F-a is the fix of that defect.

## 5. Decision

Switch the defaults (`doubt_model: track_opinion_1.3.json`, its threshold, the Falcon option) **only if every
hard row H1–H6 passes, every gain row G1–G3 (with G1x, G2x) is no worse than the control, the gate exits 0
without `--allow` and X3 shows no regression**. Otherwise the defaults stay v1.2.0 and the failing rows are
reported. The Falcon switch alone (F-a) may be flipped when its own rows (H3, G3, ID on Pandar) pass even if the
new model fails, only if it is an improvement on H3 and no worse on G3; this is stated separately.

## 6. Acceptance tests (committed with this protocol, before measuring)

`tests/test_track_opinion_13.py`: the switch defaults are equal in the class and both YAML copies; the Falcon
profiles turn the opinion off under `doubt_falcon: false` and keep it under `true` (v1.2.0), Pandar untouched;
appending features leaves the shipped model's scores unchanged; the new model file (once trained) loads, uses
only known features, no intensity / raw count feature, and its export matches scikit-learn on its report rows.

## Amendments

### A1 (21.10, after the §2.2 check of the first positives, before any §3 run)

The first synthetic-versus-real check (`feature_check.py`, `doubleT_obstacle` split by kind: the rail object
(`is_low` 1) against `railobj` / `lowbox`, the crossing person against `person`; the Falcon person against
`person` / `hivis`) found two **generator** defects, which are fixed instead of only dropping features:

1. The real rail object lies across a rail (|lateral| 0.85 m, bottom 0.13 m below the rail head) while the
   synthetic `railobj` was spread over ±0.8 m and stood on the rail head (top 0.31 m above it, where its own
   catalogue entry says ~0.13 m). Fixed: `collect --on-rail` (|lateral| 0.6–0.9 m either side; `railobj` top
   0.13 m above the rail head).
2. Every synthetic body has one size (the person is a 1.7 m mesh), so real heights / widths fall outside the
   synthetic band. Fixed: `collect --size-jitter 0.3` (each of L, W, H scaled by U(0.7, 1.3) per sequence).

New positive sets `p13j_moving`, `p13j_standing`, `p13_rail_moving`, `p13_rail_standing`
(`scripts/track_opinion_pipeline.py`). The §2.2 rule then applies unchanged to the check re-run with them.
Already determined artefacts, dropped whatever the re-run says: `raw_per_vox` (the recordings hold each echo
twice, the injector once: 0 % of real rows inside), `ring_fill` (injected points carry no real channel id),
and the count features `log_n_mean`, `log_gauge`, `vis_mean` (fail on the Falcon person; sensor-dependent).
The Falcon rows of the first check were collected in the v1.2.0 tree (23 features); the appended features are
checked on Falcon rows collected in the branch tree.
