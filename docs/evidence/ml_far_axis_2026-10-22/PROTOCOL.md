# Learned far track axis — pre-registered protocol (22.10)

> Registered **before** any held-out axis measurement and before any detector measuring run (gate, X3, range jobs,
> Falcon, marked bags) with the switch on. What existed when this was written: the ride extraction and labels, the
> grouped cross-validation on the ride (development data), the frozen model, the six Pandar recordings extracted with
> the control detector (inputs and labels only; the model was not applied to them). Branch `claude/ml-far-axis-1.3`.
> Any change to a criterion after the first measurement is an amendment appended below with its reason; the original
> text stays.

## 0. What is measured

* **Model:** `resense/models/far_axis_1.3.json`, SHA-256 `fa28db819b3dacc38403663f65dafba11213b99da5f2e21feb8bb3219b8928c8`
  (three HistGradientBoostingRegressor quantile models 0.05 / 0.5 / 0.95, 400 trees each, 44 features of
  `resense/far_axis.py`, split-conformal margins per query distance from the grouped out-of-fold residuals of the
  ride). Trained on the ride only (`new_data`, 9,893 frames with a valid label, 122,217 rows). Nothing is retrained,
  re-thresholded or re-calibrated after this file is committed.
* **Switch:** `track.learned_far_axis` (default `false` in the class and both YAMLs), with
  `learned_far_axis_from 40`, `learned_far_axis_max_band 0.5` (m), `learned_far_axis_falcon false`. The candidate
  configuration is the defaults with only `track.learned_far_axis: true`.
* **Current axis** (the comparison): the detector's own track model of the frame (**base**), and the axis the
  detector publishes on a curve frame with the K2 union (**K2**, `curve_offset`). The Falcon far line only exists in
  the Falcon profiles (§3).
* **Truth for the axis** (self-supervised, as on the ride): the near-field rail-pair midpoints (5-34 m) of the later
  frames of the same recording brought into the frame by frame-to-frame ICP (`scripts/fa_labels.py`, unchanged).
  Validity check of that truth per recording: the label against the driven path of the **B6 poses**
  (`docs/evidence/gauge_stability_2026-10-18/b6_raw.tar.xz`, an independent ICP run of 18.10) plus a constant mount
  offset. A band of a recording whose label-vs-B6 p90 exceeds 0.30 m is reported as **unreliable truth** and left out
  of the pooled A1 / A2 numbers (reported separately).

Bands: 60-100, 100-150, 150-200, 200-250 m (query distances every 10 m; 250 belongs to the last band).

## 1. Stage A — held-out axis (the five moving Pandar recordings)

Held-out lines: A = `roundT_squareT_pressureGate_squareT`, B = `roundT_doubleT`, C = `roundT_pressureGate_roundT`,
`doubleT_platform`, `squareT_platform_squareT_switch` (`doubleT_obstacle`: the train stands, no future labels).
Pooled = all rows of the five with valid truth.

| id | criterion (all must hold) |
|---|---|
| A1a | pooled, every band with ≥ 100 rows: model p90 ≤ K2 p90 and model p50 ≤ K2 p50 + 0.05 m |
| A1b | real gain: in at least one band with ≥ 100 rows, model p90 ≤ 0.8 × K2 p90 (pooled) |
| A1c | B and C each, every band with ≥ 50 rows: model p90 ≤ K2 p90 + 0.10 m |
| A2a | calibration: pooled share of truth inside the conformal band ≥ 0.85 in every band with ≥ 100 rows |
| A2b | trusted rows (band ≤ 0.5 m, i.e. where the detector would use the learned centreline): ≥ 99 % within 0.35 m (`gauge.warning_margin`) of the truth and none beyond 1.05 m (half the envelope) |
| A3 | range: on B and C, the trusted range `max(axis_valid, to_x)` exceeds the current trusted range by ≥ 10 m (median over the frames with a label at 60 m or beyond) — the "gain on curves" the switch exists for |

**Expectation stated before measuring** (from the ride cross-validation, `out/cv/`): A1a likely holds at 60-150 m and
is uncertain beyond; A1b and A3 are **expected to fail**: out of fold on the ride the model's p90 at 100-150 m is
2.13 m against K2's 2.49 m (0.86×) and the calibrated band is ≤ 0.5 m in 11 % of the 60-100 m rows and in **no**
row beyond 100 m; the Pandar sees almost no tunnel-side returns beyond 160-180 m on the ride, so beyond that a
single frame carries no geometry to learn from.

## 2. Stage B — the detector (switch on vs the control)

Control: this branch at its defaults (switch off). The branch at its defaults must first equal a fresh tree of the
integration head it was merged with (B0). All runs: `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `RESENSE_REPO` =
the evaluated tree.

| id | criterion |
|---|---|
| B0 | identity: the branch at its defaults vs `claude/integration-1.3` @ `2a64cfe` — full gate per-frame rows equal in every field but timing (paired per-row diff), 0 differing rows |
| B1 | no true STOP lost or delayed (switch on vs off): set O inside objects (gated rows: per object STOP frames, first STOP, held from, no lost STOP frame); `doubleT_obstacle` labelled hits and first alarm frame; the 37 K2 range jobs at the control's placement (`k1_k2_gauge_2026-10-19/tools/prebuild_range.py`): first STOP and held-from not later, 0 STOP frames lost; X3 positives (`doubleT_obstacle`, set O, 10 variants): every inside STOP row kept; the three marked synthetic bags (`per_object.py`): per-object STOP frames not fewer, first STOP not later; Falcon person, 6 starts of the far-range review (`scene_run.py --plain`, `falcon_ros`): first / held STOP not later — the switch is off in the Falcon profiles (`learned_far_axis_falcon false`), so this is an identity check |
| B2 | false-alarm bound: STOP episodes over Falcon (both paths) + ride + the five empty recordings together at most **+11** against the control, each new one attributed (frame, distance, lateral, cause) |
| B3 | full regression gate without `--allow` against `regression_baseline_2026-09-29_shell_off.json`: exit 0 |
| B4 | X3 (`scripts/robustness_battery.py -j 2`) against a fresh control run on the same machine: PASS |
| B5 | paired per-row diff of the gate (switch on vs off): every changed row listed and attributed |

Expected gains, stated before measuring (what a pass would have to show and where): earlier first / held STOP on the
curved range jobs B and C and beyond 150 m on A; fewer far side-structure false STOPs of the X2 classes on the ride
and `squareT_platform_squareT_switch`. **Expected outcome: none of these gains**, because the trusted band is
expected to be narrow only where the base / K2 axis is already right (Stage A expectation).

## 3. Weaker checks, reported, not gating

* **Falcon** (a standing long-range sensor, no future labels): the model's middle prediction and band in the
  `falcon_ros` and manual paths against `falcon_long_range_2026-10-19/track_reference.json` (rail-pair centres
  measured to 90 m and its straight far fit), at the frames of the recording; a different sensor from the training
  data, so a far-off result there is expected and does not decide anything.
* **Marked synthetic bags** (`new_synth_data_with_markers.zst`): axis error where a label can be built honestly (the
  scene moves; ICP + rail stitching as above).
* Per-frame time of the learned axis (profile + features + trees), reported.

## 4. Decision rule

The default flips to `true` only if **every** criterion of Stage A and Stage B holds. If any Stage A criterion fails,
the switch stays off; Stage B is then run only as far as needed to document what the switch would do (B0 always; the
gate with the switch on and its paired diff for information), and that is stated as such. No criterion, threshold,
model or margin is changed after a measurement to make it pass.

## Amendments

**A1 (22.10, before the model was applied to any held-out frame; only labels and the B6 comparison had been
computed).** The B6 validity check of §0 found label-vs-B6 p90 above 0.30 m in most bands of A, B,
`doubleT_platform` and `squareT_platform_squareT_switch` (C: all bands within). Diagnosis: B6's frame-to-frame ICP
has no outlier repair and a cold start from the identity; in 157 motions (A 51, B 6 with a speed estimate / 56 in all,
`doubleT_platform` 23, `squareT_platform` 77) its forward step differs from ours by > 0.1 m, and the detector's own
texture-based speed estimate (independent of both ICP runs) agrees within 0.3 m with ours in 151 of them and with
B6 in 6 (B6 even reports -0.68 m per frame, backwards, at the start of B). The B6 truth is wrong there, not the
labels. **Change:** the B6 validity check leaves out every frame whose B6 driven path passes through a B6 motion
whose forward step differs from ours by more than 0.1 m (`fa_checks.py driven --b6-trust`); the 0.30 m rule is
otherwise unchanged, and the bands it then marks unreliable stay out of the pooled numbers. Nothing else changes.
