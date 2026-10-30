# Learned far track axis (22.10) — a real out-of-sample accuracy gain, no range gain under the trust rule; switch stays off

> ML agent of the captain's session. Branch `claude/ml-far-axis-1.3` (from `claude/integration-1.3`, merged with its
> head `2a64cfe` before any measuring run). Protocol: [PROTOCOL.md](PROTOCOL.md), registered at `0926c82` before any
> held-out or detector measurement; amendment A1 (`eb46172`) before the model was applied to any
> held-out frame. Environment: Python 3.13 venv, numpy / scikit-learn / open3d 0.20 from `pip install -e ".[dev]"`,
> rosbags 0.11.5, `scripts/build_native.sh`, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `RESENSE_REPO` = the
> evaluated tree, 4 vCPU. G3 (held-out 15.10) not touched. No tag, release or PR; no edit to BACKLOG / CAPTAIN /
> DECISIONS / CHANGELOG / README / version files / `detector_freeze.py` / manifests. `detector_freeze.py verify`
> fails on this branch as on `claude/integration-1.3` (detector files changed since the 1.2.0 seal; reseal is the
> captain's); `scripts/sync_params.sh --check`: parameter files in sync.
> Full test suite on this branch: 2,562 passed, 1 failed (`test_rail_start.py::test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop`,
> which fails with the same assertion and values on the control tree `2a64cfe`: pre-existing, as the integration README records).

## Answer

1. **The learned axis is more accurate than the current axis on lines it never saw.** Pooled over the five moving
   Pandar recordings (truth: later frames' near-field rails stitched back by odometry, validated against the
   independent B6 poses), axis lateral error p50 / p90:

   | band | learned (middle) | current: K2 published | current: base model | 90 % band covers truth |
   |---|---|---|---|---|
   | 60-100 m | **0.07 / 0.25** | 0.09 / 0.29 | 0.20 / 0.74 | 0.98 |
   | 100-150 m | **0.19 / 0.77** | 0.28 / 1.57 | 0.38 / 5.45 | 0.99 |
   | 150-200 m | **0.60 / 2.74** | 1.07 / 7.16 | 2.54 / 15.3 | 1.00 |
   | 200-250 m | **2.62 / 15.0** | 7.76 / 23.1 | 9.96 / 28.3 | 1.00 |

   On the curves: B (`roundT_doubleT`) 100-150 m p90 **1.11 vs 3.31 m**; C (`roundT_pressureGate_roundT`)
   150-200 m p90 **2.99 vs 8.04 m**, 200-250 m 10.1 vs 21.6 m. Not everywhere: on `doubleT_platform` 150-250 m and
   `squareT_platform` 100-200 m the learned axis is slightly worse than K2 (table below).
2. **It gives no range gain under the pre-registered trust rule, so the switch stays off (protocol §4: A3 fails).**
   The detector may use the learned centreline only where its calibrated 90 % band is ≤ 0.5 m. Calibrated on the
   ride, the band is that narrow only up to 50-60 m (0 held-out rows beyond 100 m); the trusted range is extended in
   **0 frames of B and C** (6 of 345 `doubleT_platform`, 75 of 877 `squareT_platform`, each only to 50-60 m, on
   frames whose current trusted range was shorter than that). The band is honest — it covers the truth in 98-100 % of held-out rows — but wide: beyond
   ~150 m the Pandar returns almost nothing from the tunnel sides (0 returns per 5 m bin beyond 160-190 m in the
   sampled ride frames, `png/` and the follower statistics: both sides followed at the query distance in 12 % of the
   100-150 m ride rows and 1 % beyond 150 m),
   so a single frame carries no geometry there and no model can be *sure* where the track goes, only less wrong on
   average.
3. **The detector integration works and is safe at its defaults.** `track.learned_far_axis` (off in the class and
   both YAMLs): at the defaults the branch equals the integration head on all 15,269 gate rows (B0). With the switch
   on, the full gate passes without `--allow` (exit 0) and only 2 STOP rows change over all recordings: set O
   `small_edge_inside` gets its STOP one frame earlier (first STOP 35.0 → 36.8 m), and one single-frame false STOP of
   the ride (`new_data:5716`, 21.8 m, an X2 "side (surface)" episode) is not confirmed — an indirect tracker effect,
   not a robust fix. Cost: **~21 ms per frame** (numpy, CPU; detector mean 38 → 64 ms on a ride sample).
4. **Falcon (different sensor): the model is worse than K2 in every band** (60-100 m p50 0.45 vs 0.06 m, band
   coverage 0.35 there). The switch is off whenever the Falcon profiles are on (`learned_far_axis_falcon: false`);
   this result says it must stay so.

What would turn the accuracy gain into range: either a band calibrated per situation instead of per distance (tried
on the ride, out of fold: more trusted rows, but the truth inside the trusted band drops to 66-81 % — unsafe), or
an integration that uses the learned centreline as a *second opinion* rather than as trust (e.g. instead of K2's
shape in the K2 union, which only adds obstacles; on C frame 110 K2 bends the wrong way and the learned centreline
does not, `png/C_roundT_pressureGate_roundT.png`). Both need a new protocol; neither was measured here.

## Result table (pre-registered criteria, PROTOCOL.md)

| id | criterion | result | pass |
|---|---|---|---|
| A1a | pooled, every band: model p90 ≤ K2 p90, p50 ≤ K2 p50 + 0.05 | table above | **PASS** |
| A1b | one band with model p90 ≤ 0.8 × K2 p90 | 100-150: 0.77 vs 1.57 (0.49×), 150-200: 0.38× | **PASS** |
| A1c | B and C each, every band: model p90 ≤ K2 p90 + 0.1 | B 0.44/1.11/5.83/22.7 vs 1.05/3.31/9.48/28.3; C 0.25/0.95/2.99/10.1 vs 0.25/1.93/8.04/21.6 | **PASS** |
| A2a | pooled coverage ≥ 0.85 per band | 0.977 / 0.992 / 0.997 / 0.999 | **PASS** |
| A2b | trusted rows (band ≤ 0.5): ≥ 99 % within 0.35 m, none beyond 1.05 m | 99.75 % (2,023 rows, all at 40-100 m), max 0.61 m | **PASS** |
| A3 | B and C: trusted range +10 m (median) | +0 m on both (0 of 199 / 243 frames extended) | **FAIL** |
| B0 | branch at defaults = integration head `2a64cfe`, all gate rows | 0 of 15,269 rows differ; injected change found (1 row) | **PASS** |
| B1-B5 | STOP safety, false-alarm bound, gate, X3 with the switch on | not required once A fails (§4); gate + paired diff run for information: gate exit 0, 2 STOP rows changed (attributed above); X3, range jobs, marked-bag STOP scoring and Falcon starts **not run** | — |
| decision | flip only if every criterion passes | A3 fails | **switch stays off** |

Expectation registered before measuring (protocol §1): A1b and A3 expected to fail. A3 failed as expected; **A1b
passed against expectation**: the held-out gain on curves is larger than the ride's out-of-fold gain (ride 100-150 m
p90 2.13 vs K2 2.49, 0.86×).

## Per recording (held out), p50 / p90 in m

| recording | band | n rows | learned | K2 | base | coverage |
|---|---|---|---|---|---|---|
| A `roundT_squareT_pressureGate_squareT` | 60-100 / 100-150 / 150-200 / 200-250 | 1140 / 820 / 325 / 13 | 0.05/0.14, 0.08/0.27, 0.13/0.36, 0.36/0.86 | 0.06/0.23, 0.10/0.31, 0.12/0.31, 0.18/0.38 | 0.06/0.22, 0.09/0.28, 0.12/0.31, 0.18/0.38 | 1.0 all |
| B `roundT_doubleT` | same | 746 / 795 / 641 / 559 | 0.13/0.44, 0.28/1.11, 1.19/5.83, 7.77/22.7 | 0.18/1.05, 0.71/3.31, 3.48/9.48, 12.4/28.3 | 0.87/4.16, 5.05/11.8, 12.3/22.0, 22.9/34.6 | 0.97-1.0 |
| C `roundT_pressureGate_roundT` | same | 932 / 1018 / 852 / 795 | 0.07/0.25, 0.21/0.95, 0.77/2.99, 2.39/10.1 | 0.11/0.25, 0.51/1.93, 3.37/8.04, 10.1/21.6 | 0.19/0.51, 1.06/3.52, 4.88/9.56, 9.53/16.7 | 1.0 |
| `doubleT_platform` | same | 491 / 396 / 210 / 81 | 0.15/0.57, 0.20/0.56, 0.48/1.33, 1.59/3.23 | 0.17/0.90, 0.24/0.85, 0.33/0.78, 0.66/1.86 | 0.20/0.94, 0.47/1.78, 0.67/4.59, 5.85/8.45 | 0.91-1.0 |
| `squareT_platform_squareT_switch` | same | 2761 / 797 / 459 / 260 | 0.07/0.20, 0.25/0.67, 0.55/1.21, 0.72/1.93 | 0.08/0.19, 0.23/0.52, 0.51/0.87, 0.88/2.78 | 0.28/0.68, 0.25/0.97, 0.60/2.95, 0.96/5.74 | 0.98-1.0 |

`doubleT_obstacle`: the train stands, no future labels. Raw: [`out/stage_a/stage_a.json`](out/stage_a/stage_a.json).

## The model

* **What it predicts:** per frame, the lateral offset of the true centreline from the detector's base track model at
  X = 40, 50, …, 250 m, as the 5 %, 50 % and 95 % quantiles, widened by split-conformal margins per distance
  (0.07 m at 40 m … 1.8 m at 150 m … 14.6 m at 250 m) computed from the grouped out-of-fold residuals of the ride.
* **Inputs** (`resense/far_axis.py`, 44 features; identical code at training and at run time): the base model's
  state (curvature, tangent, centre, curvature step, trusted range, rail slabs, fitted sides, wall quality), the K2
  curve model's offset and range, the far line's offset (Falcon only), and the frame's observations as lateral
  histograms (0.1 m) per 5 m bin of the returns 0.4-3.2 m above the rail head (±25 m), above 3.2 m (vault) and on the
  bed: inner boundaries per side relative to their near-field distance, their robust midline fit, and a corridor
  **follower** that tracks the tunnel outward bin by bin from the near field. Not used: previous frames' predictions
  moved by ego motion (history cannot see farther ahead than the current frame; not implemented).
* **Learner:** `HistGradientBoostingRegressor(loss="quantile")`, 400 trees, 31 leaves, min 80 rows per leaf, lr 0.05.
  Exported to JSON (`resense/models/far_axis_1.3.json`, 3.1 MB, SHA-256 `fa28db81…`); numpy evaluation equals
  scikit-learn to 1.4e-13 (`resense/models/far_axis_1.3_report.json`, the training report).
* **Training data:** the ride only, 9,893 frames with a valid label, 122,217 (frame, distance) rows.

## Labels without humans

Truth ahead of frame t = the rail-pair midpoints (3 m slabs, 4-34 m, own outward ridge tracking seeded only by the
near model, `fa_extract.py near_rails`) of the later frames t+1 … t+k, brought into frame t by composed
frame-to-frame ICP (open3d point-to-plane, B6 / judge settings, plus a coarse 0.5 m pass and a re-seed from the
detector's own speed estimate on a cold start), and a robust local line through them at each query distance
(`fa_labels.py`). Motions with low fitness or off the running median are repaired from their neighbours (435 of
11,271 on the ride); a standing train's motion is set to identity; a label needs ≥ 3 samples, spread ≤ 0.12 m and
≤ 2 repaired motions in its chain. The far axis plays no part.

### What was checked, and how

| check | method | result |
|---|---|---|
| known answer (CLAUDE.md 1, 2) | 9 ray-cast scenes with an exact centreline (straight, R 300 / 500 / 1000, left R 700, curve entry, S-curves R 400 / 700, curve exit), 420 frames each, exact poses (`raycast_scenes.py`, `validate_synth.py`) | labels within p90 ≤ 0.016 m, max ≤ 0.066 m in every band of every scene; near-rail extractor p90 0.02-0.03 m. Positive control: the same tool shows the detector's base axis off by 25.7 m (p50, r300, 200-250 m) |
| odometry error → label error | the exact motions with yaw noise / bias added per frame | 1e-4 rad/frame noise: p50 0.16-0.25 m at 200-250 m; 2e-5 rad/frame bias: 0.45-0.70 m. The labels are as good as the real ICP's heading |
| ICP on the synthetic scenes | | **fails**: the swept, perfectly smooth tunnel locks ICP to zero shift (the sensor-fixed sampling matches better than the true motion); kept as a finding, not used. Real data has the texture (below) |
| ICP scale, real | ICP travel per ride split vs the organizers' per-split speed (`speed_tracks`, from tracked structures, not ICP) × the split's duration (`out/ride_speed_check.json`) | 179 moving splits: median ratio 0.997, p10 0.72; 17 of the 27 splits below 0.85 contain a recording gap (below); without them (158 splits) median 1.002, p10 0.895, total 10,879 vs 10,781 m. Of the other 10 low splits, 4 are slow (1-2 m/s, reference from 3-5 structures) and 4 (3, 132-134) have 13-25 repaired motions: ICP likely under-reports travel there (not resolved) |
| ICP heading at range, real, odometry-free | both tunnel boundaries seen in frame t itself at X, referenced to their own near-field distance, parallel walls only (`fa_checks.py walls`, full ride, `out/ride_walls_check.json`) | label−walls p50 / p90: 0.09 / 0.26, 0.13 / 0.41, 0.28 / 1.27, 0.52 / 1.50 m at 40-60 / 60-100 / 100-150 / 150-200 m; the positive control base−walls 0.08 / 0.25, 0.13 / 0.38, 0.20 / 0.65, 0.30 / 0.73. Agreement only within the walls' own noise at ≤ 100 m; at 100-200 m the labels disagree with the walls more than the base model does (p90 1.3-1.5 vs 0.65-0.73 m, 2,166 / 464 rows): not resolved which is wrong (the base model is fitted to these same walls). It found the station-stop drift below |
| a found and fixed defect | labels with chains of 260-550 frames (train standing at a station) were 2-4 m off the walls | standing motions set to identity; 100-150 m p90 label−walls 2.43 → 0.84 m (ride pieces 0-2, before the full-ride run above) |
| independent truth on the held-out lines | the B6 driven path (independent ICP run of 18.10) + a constant mount offset | after amendment A1, label vs B6 p90 ≤ 0.25 m in every band of every recording (C before and after: ≤ 0.25 m) |
| B6 itself (CLAUDE.md 5) | B6 vs our motions where they differ by > 0.1 m, arbitrated by the detector's texture speed estimate | ours agrees in 151 of 157, B6 in 6; B6 reports −0.68 m/frame (backwards) at the start of B: B6 cold-start failures (A1) |
| pictures (CLAUDE.md 4) | `png/B_roundT_doubleT.png`, `png/C_roundT_pressureGate_roundT.png`: raw points, every stitched midpoint, labels, base, K2, learned band | the stitched midpoints continue the near track smoothly; raw returns end at 120-170 m |
| leakage | 8-fold CV by gate ride piece, purging training rows whose label chain reaches into the held-out piece and the held-out labels' stretch after it | done (`fa_train.py cv`) |
| export | numpy evaluator vs scikit-learn on all ride rows | max |Δ| 1.4e-13 |

### Ride, grouped cross-validation (development data), p50 / p90 in m

| band | learned | K2 | base | calibrated coverage | band ≤ 0.5 m |
|---|---|---|---|---|---|
| 60-100 | 0.15 / 0.66 | 0.16 / 0.72 | 0.17 / 1.30 | 0.895 | 11 % of rows |
| 100-150 | 0.44 / 2.13 | 0.43 / 2.49 | 0.62 / 5.12 | 0.898 | 0 % |
| 150-200 | 1.32 / 8.00 | 1.10 / 7.92 | 1.75 / 13.4 | 0.892 | 0 % |
| 200-250 | 4.13 / 20.0 | 2.91 / 19.7 | 5.15 / 24.8 | 0.888 | 0 % |

Versions tried on the ride before the freeze (all in `out/cv/`): v1 features in a fixed window around the base axis
(lost the walls on curves; p90 100-150 2.51 m); the residual referred to K2 instead of the base model (no better,
`cv_v2_k2.json`); width-normalised conformal margins (unsafe, above; computed inline from `oof_v2_base`, the numbers in this README are the record). The frozen model is v2 / base / constant margins.

## Detector integration (`resense/detector.py`, `resense/config.py`, both YAMLs)

`track.learned_far_axis` (false), `learned_far_axis_model` (`far_axis_1.3.json`), `learned_far_axis_from` (40 m),
`learned_far_axis_max_band` (0.5 m), `learned_far_axis_falcon` (false). On: per frame the profile, features and
calibrated quantiles; from 40 m (blended over 20 m) the laterals are measured from the learned centreline up to the
farthest query distance whose band is ≤ 0.5 m, contiguously; the trusted range becomes max(current, that distance)
— never shorter; the accumulation buffer reconstructs with the learned offset and is cleared when it moves > 0.2 m
(the far line's rule); the K2 curve pass never sees it; with farrange on (Falcon) it is off. Acceptance tests
`tests/test_far_axis.py` (10, committed before any measuring run; one test corrected after the model file existed:
it fed NaN as the query distance).

Gate runs (`out/gate/`): control = integration head `2a64cfe`, candidate = this branch at defaults, on = candidate
with `--set track.learned_far_axis=true`; all three exit 0 without `--allow` against
`regression_baseline_2026-09-29_shell_off.json`. On vs candidate (`cmp_on_vs_cand.json`): ride events 25 → 24, STOP
episodes 29 → 28, alarm frames 119 → 118; set O inside STOP frames 414 → 415; `doubleT_obstacle` object-on-rail hits
129 → 131 (distance error max 0.23 → 0.28 m, information row); set F identical; no gated row worse; latency +23-35 ms
mean in the 4-job gate. Per-row diff (`rows_diff_on_vs_off.txt`): 9,551 of 15,269 rows differ in some non-timing field (mostly
the corridor point count from the shifted 40-60 m laterals); the STOP flag in 2 (`stop_diff_on_vs_off.txt`).
Per-frame rows of both runs: `out/gate/per_frame_off_on.tar.xz`.

## Weaker checks (protocol §3)

* **Falcon** (`out/falcon/`, 889 frames of 4,443, both paths, `falcon_axis.py`): truth = the far-range review's
  straight reference line through the detector's mount rotation. falcon_ros, p50 / p90: 60-100 learned 0.45 / 0.61,
  K2 0.06 / 0.10, base 0.11 / 0.19; 100-150 0.36 / 0.96 vs K2 0.14 / 0.50; 150-200 0.64 / 1.59 vs 0.57 / 1.52;
  200-250 1.50 / 3.70 vs 1.33 / 3.35 (manual path the same within 0.05 m). Out of domain, worse than K2.
* **Marked synthetic bags:** see below.
* **Per-frame time:** learned axis 21.9 ms mean / 28.0 ms p95 (ride frames), 20.9 / 28.3 (B); 15 / 22 ms on Falcon.

### Marked synthetic bags (organizer scenes, `new_synth_data_with_markers.zst`, SHA-256 `04d176b4…`; `out/marked/`)

Labels as on the held-out lines; against the B6 poses of the same scenes (A1 rule) p90 ≤ 0.27 m in every band
(tunnels ≤ 0.20, platform ≤ 0.14, switch ≤ 0.27). Pooled p50 / p90 (m), registered model:

| band | learned | K2 | base | coverage |
|---|---|---|---|---|
| 60-100 | 0.08 / 0.38 | 0.12 / 0.36 | 0.15 / 0.92 | 0.957 |
| 100-150 | 0.23 / 1.57 | 0.38 / 2.79 | 0.75 / 7.00 | 0.938 |
| 150-200 | 1.02 / 6.27 | 3.00 / 11.2 | 5.40 / 18.5 | 0.933 |
| 200-250 | 4.13 / 21.0 | 12.9 / 28.2 | 17.3 / 35.9 | 0.936 |

Trust extended: tunnels 0 of 545 frames, switch 0 of 736, platform 74 of 386 (to ≤ 60 m). The same picture as the
Pandar lines: more accurate than K2, no range under the 0.5 m band rule.

### A defect found after the registered measurement: recording gaps (post-hoc, not a decision input)

The ride has 43 stamp gaps of 0.25-7.1 s (splits 156-220, pieces 6-7: recording dropouts). ICP sees one step across a
gap, so the train's travel during it (up to ~130 m) is missing from every label chain that crosses it. The registered
pipeline did not break segments there; 14,838 of the 122,217 training rows crossed a gap. Held out: B and C have no
gap; A has one (1.1 s), `squareT_platform` one (0.7 s); the marked bags none. `fa_labels.py --gap-break 0.25` (off
by default, the registered behaviour) ends the segment at a gap. **Post-hoc** (labels fixed, model retrained, margins
recomputed, Stage A rerun on the same held-out lines — so optimistic, and not able to flip anything under this
protocol; `out/posthoc_gap_fix/`): ride CV and held-out numbers move little (pooled held-out p90 0.27 / 0.78 / 3.05 /
15.5 m vs K2 0.30 / 1.69 / 7.54 / 24.5), the band is still never ≤ 0.5 m beyond 100 m, A1-A2 pass, **A3 still fails**
(0 frames extended on B and C). The gaps are not why the switch gains no range.

## What failed, what is not verified

* Not verified: X3, the 37 K2 range jobs, the marked bags' STOP scoring and the Falcon 6-start replays **with the
  switch on** were not run (protocol §4: Stage A failed, the switch cannot flip; they would only describe a
  configuration that is not proposed). The gate with the switch on is informational, not an acceptance.
* The label truth is as good as the real ICP's heading and travel; the odometry-free wall check confirms it only to the
  walls' own noise at ≤ 100 m and disagrees more than the base model at 100-200 m (unresolved, above); B6 confirms it
  to ≤ 0.25 m p90 on the held-out lines but is the same algorithm family; four ride splits likely under-report travel.
* Recording gaps corrupted 12 % of the training rows (post-hoc section): the registered model was trained with them.
* The ray-cast scenes validate the rail extraction and stitching, not ICP (ICP fails on them, see above).
* The 0.85 / 0.9 coverage of the ride's conformal band became 0.98-1.0 on the held-out lines: the band is
  conservative there, which is part of why it never gets narrow; a less conservative calibration was not tried on
  held-out data (it would need a new protocol).

## Files

`PROTOCOL.md`; `scripts/` (`raycast_scenes.py`, `fa_extract.py`, `fa_labels.py`, `fa_train.py`, `fa_checks.py`,
`validate_synth.py`, `stage_a.py`, `fa_plot.py`, `falcon_axis.py`); `out/cv/`, `out/stage_a/`, `out/labels_heldout/`
(B6 and own driven-path checks), `out/gate/`, `out/falcon/`, `out/synth_label_validation.json`; `png/`.
Model and training report: `resense/models/far_axis_1.3.json`, `resense/models/far_axis_1.3_report.json`.
`out/` is matched by the repository's `.gitignore`; it was added with `git add -f`. The CV files the protocol cites
(`out/cv/`) were computed before the protocol commit and committed after it (`82fe0e8`), unchanged.

Reproduce: environment as above; data per `docs/VM_GUIDE.md` §2 (six recordings from the team storage, ride with
`scripts/cache_extended_ride.py`); then `fa_extract.py` per ride piece (`--start/--end` of the gate's 8 pieces, 1-frame
overlap), `fa_labels.py` over the pieces, `fa_train.py dataset / cv --ref base / fit --cv`, `fa_extract.py` +
`fa_labels.py` per held-out recording, `stage_a.py /data/fa/held out.json`.
