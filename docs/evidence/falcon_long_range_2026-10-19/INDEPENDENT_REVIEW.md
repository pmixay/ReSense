# Independent review: Falcon long range (`det/falcon-long-range`, base `aec88d2`)

Reviewer: fresh subagent with no stake in the change, 19.10. I reviewed the code and the criteria and
method, not the author's conclusions. I modified no file under `resense/`, `native/`, `configs/`,
`ros2_ws/`, `tests/` or `scripts/`, and ran nothing on G3. All my analyses were read-only, on at most a
few hundred frames. My helper scripts are in the session scratchpad
(`/tmp/claude-0/-home-user-ReSense/59dc66a4-87f5-5856-bf41-e3e06cfb4659/scratchpad/*.py`).
HEAD at review time: `ad753b6` (docs only on top of `ab26c04`; `git diff ab26c04 HEAD -- resense ros2_ws tests configs native` is empty).

## Verdict summary

| # | Question | Verdict |
|---|---|---|
| 1a | Behaviour changes reachable only with `farrange.enabled` / `falcon_prime` | **PASS** (non-blocking notes) |
| 1b | Correctness of far-axis math, gauge shrink, axis_valid, accumulation | **CONCERN** |
| 1c | Safety: curve or diverging wall, near obstacles, relaxed size rules | **FAIL** (curves and diverging walls beyond 50 m). Near field below 50 m: PASS |
| 1d | C5 small-target range of 48.2 m | **PASS** (labelling notes) |
| 2 | Evidence method (controls, injector, A1, association, false-alarm accounting) | **CONCERN**: C6 not pre-registered and evaluated in-sample; rule 5.1(b) fails |
| 3 | Independent re-derivation | Done: baseline error +2.08 m at 150 m; candidate −0.02 m; real walker 4.4 returns/frame at 250–260 m |

## Blocking issues

**B1. The far axis is accepted on curves that start beyond the join, and on a single diverging wall. It then moves the corridor by metres, while its stated uncertainty stays at 0.15–0.19 m.**

The test: synthetic tunnel boundaries built like the helper `tests/test_farrange.py::_walls`, with
both walls following the curve, run through `FarAxisTracker` for 8 frames
(`scratchpad/curve.py`, `scratchpad/diverge.py`). The near model is straight.

- **Positive control:** straight track. Accepted, error 0.00 m to 400 m.
- **Curve starting at Xc = 120, 160, 200 or 240 m, with R = 300, 600, 1000 or 3000 m:** accepted in **16 of 16** cases.
  - Maximum lateral error of the far axis inside its trusted range (`valid`) was 1.0–9.6 m. Examples: Xc 120 m / R 600 m gave 9.57 m at 230 m; Xc 200 m / R 300 m gave 4.08 m at 250 m.
  - `sigma` at those points was 0.16–0.19 m. The strict gauge half-width is 1.05 m.
  - With the inner wall occluded beyond Xc + 20 m, the curve was still accepted: Xc 150 m / R 500 m, error 3.34 m at 210 m.
- **One wall diverging at slope 0.003–0.009, the other wall absent or shorter than `axis_min_span`:** accepted with `sides = 1`, valid to 328–388 m.
  - Axis error at 300 m: 0.75–2.24 m. `sigma`: 0.15 m.

Causes in the code:
- `resense/farline.py` `_side_line` drops far bins as outliers (more than 2 × `axis_max_rms` off the line). The bow test only sees the kept bins, so the start of a curve is removed instead of failing the frame.
- `FarAxis.valid = support + axis_margin` (40 m). Beyond the support, `sigma` uses `axis_unseen_curvature = 1e-5` (R = 100 km): 0.008 m at 40 m. A metro curve of R = 300 m departs 2.7 m in the same 40 m.
- Only `axis_max_side_disagreement` checks one side against the other. A one-sided fit is accepted, and only the kink check (0.01 rad at the join) limits it.
- `FarAxisTracker.update` smooths `support` with `max(new, EMA)`. The trusted range grows immediately but shrinks only slowly, which is the optimistic direction when a curve is approaching.

Consequences on a curve or a diverging wall beyond about 100 m:
- `axis_valid` is raised to `far.valid` (`detector.py` hook in `_corridor`). STOP authority and the monitored range then extend along a wrong line. On the real recording the detector's monitored range already reaches 231.5 m (baseline maximum 175 m).
- The result is false "clear" claims, plus phantom STOPs from the outer wall where it enters the shifted gauge.
- An obstacle on the real curved track beyond about 150 m is not in the corridor. The baseline also misses it there, but it does not claim to monitor that range.
- The unit test rejects only a curve that starts exactly at the join (`0.5*curv*(X-50)**2`), which is the easy case.

The Falcon recording is straight beyond 40 m, so none of the real-data evidence (recording, matrix, walk control) can show this failure. The only negative control of the matrix (`outside`) is on straight track.

Required before acceptance:
- Do not trust the axis beyond the last *contiguous* kept bin, or use a realistic unseen curvature (at least 1/300 m^-1).
- Reject a frame whose far bins were dropped as outliers at the end of the span.
- Cap or refuse one-sided fits.
- Use a symmetric (or pessimistic) support filter.
- Add negative unit tests: a curve starting at 120–240 m, and a diverging single wall.

**B2. C6 is an unplanned change, chosen after results were seen and evaluated on the same data.**

C6 is `cluster.far_min_height` 0.6 → 0.3 and `far_max_length` 3.0 → 4.0 under the profile (`resense/config.py` FarRangeConfig; `sensor_profiles.py`).
- C6 is not in PROTOCOL §6 (C1–C5) or in A1. It was committed (`ab26c04`, 12:23) after A1 (11:37) and after the c13 and c134 matrices and the real-recording replays.
- On the real far walker (E4), C6 is what raises the 250–260 m STOP fraction from 0.354 (c134) to 0.783 (c136/final), and the 260–270 m fraction from 0.085 to 0.368 (`far_walker_eval_c13_c134.json`, `far_walker_eval.json`).
- 214 STOP detections in `final` need the relaxed rule: height < 0.6 m, mostly 3–4 points at 245–262 m, heights 0.27–0.62 m. E4 for the candidate is therefore in-sample for C6.
- The protocol's own rule ("no parameter tuned on seeds 0–2 without re-running seeds 10–12") is not yet met: `final_s10` was still running during this review.

Required: a dated amendment that names C6 and how its values were chosen; seeds 10–12; and an E4-style statement that the walker result is in-sample.

**B3. Pre-registered acceptance rule 5.1(b) fails, and the evaluation tool says so.**
- `falcon_recording_eval.json` → `candidates.final.checks.all_stop_episodes_le = false` and `empty_stop_episodes_le = false`, `pass = false`. There are 25 STOP episodes against the baseline's 8, and 22 against 2 in frames 0–1700.
- Rule 5.1(b) reads "whole recording: STOP episodes ≤ baseline (8)", with no qualifier. A1 states "Acceptance rule 1 otherwise unchanged".
- The extra episodes are real: STOP flicker on the real far walker at 245–275 m. But they are STOP onsets, which is an operational cost (emergency-brake onsets).
- The report must state this as a failed criterion. Changing the rule now would be moving the goalposts after the result was seen.

**B4. The accumulation reconstruction mixes coordinate systems when the far axis switches on or off. This path is untested on Falcon.**
- `_accumulate` stores each frame's `cand.dy`, measured from whichever axis was active then (the near parabola, or the far line), together with its `in_gauge` flag.
- It rebuilds y as `center_y + dy + far.offset(X)` using the *current* far axis (`detector.py` hook in `_accumulate`).
- In the frames after the far axis confirms, buffered points from frames with no far axis are re-placed onto the far line, carrying their old in-gauge flags. At 250 m the near model is 9.4 m off, so these are wall or structure points.
- When the far axis drops, the opposite happens.
- This is reachable only with a given ego speed of at least 1 m/s (`accumulation.min_speed`; `estimate_speed` is off). Every Falcon replay and matrix run used `ego_speed=None` on a standing train, so moving operation was never exercised.
- I did not run this. It is a finding from reading the code, and the `smear_max_length` fallback may partly mask it.
- Fix: clear the buffer (or tag entries with their axis) when `_far_axis` changes between None and not None. Then run a moving-ego Falcon test.

## Non-blocking issues

1. **Effective-config hash changes for Pandar.** `DetectorConfig.to_dict()` (asdict) now has a `farrange` section, so `scripts/regression_gate.py::config_info` sha256 differs from the baseline for the unchanged default config. Without the `farrange` key the hash is identical (`0c9d663f067e55ff` on both base and branch). This is informational, but any sealed comparison of effective-config hashes will flag it.
2. **C5 does not depend on the `farrange` flag.** `small_target_limit("falcon_prime")` now returns 48.2 m instead of None, even with `farrange.with_falcon_profile=false`. The test comment "explicit opt-out keeps the old Falcon behaviour" (`tests/test_farrange.py`) is therefore only true for the detector, not for the node decision (GO with 48.2 m instead of the small-target range being unavailable).
3. **The strict-gauge shrink does not cover the real bias.** On the recording the far-axis lateral error (detection corridor lateral minus raw-reference lateral) is −0.16 m at 240–260 m and −0.19 m at 260–280 m (p10/p90 −0.27/−0.13). `sigma` there is about 0.16 m, and part of the bias is inherited from `y_join`: the near model is −0.13 m off at 50 m. Marginal for the gauge edge.
4. **Hold behaviour.** `FarAxisTracker` keeps the last line for 10 failed frames with no ego shift of `support` or `valid`. At 20 m/s that is 20 m of stale trust.
5. **Boundary selection near obstacles.** `measure()` takes the inner-boundary 10th percentile in a 1.2–4.0 m band from the near tangent line, at 1.0–2.8 m height. A person or object at the gauge edge, when the provisional line is offset, can be picked as boundary. The robust refit makes a single bin harmless; long objects (a parked train beside the track) are untested.
6. **Frame-level crediting in false-alarm accounting** (`falcon_eval.py`): a STOP frame counts as "person" if any detection in it is associated, which masks a co-occurring false detection. In practice small here:
   - frames 0–1724: 0 unassociated STOP detections;
   - frames ≥1725: 20 frames with an unassociated detection in the candidate, 30 in the baseline.

   It should still be per detection.
7. **The walk control overlaps the far walker.** It still runs on frames 300–1210, which contain the real far walker at 250–307 m. That has little effect at 97–210 m, but the "empty frames" premise is false and A1 did not move this window.
8. **Injector validation stops at about 210 m for detector behaviour.**
   - Beyond 250 m, only returns per frame were calibrated (POD k = 3 fit).
   - At 250 m, the injected `person_back` gives 3.5–3.7 returns per frame and a STOP fraction of 0.19–0.38. The real far walker at 250–260 m gives 4.4 returns per frame (my count) and a STOP fraction of 0.78.
   - The injector is thus pessimistic for that model at 250 m. At 300 m the injected `person_front` has 3.9 returns per frame against 1.5–2.0 for the real walker (at the gauge edge).
   - `person_front` keeps ρ 0.05/0.30, fitted with k = 2.35, but the matrix uses k = 3. It was not re-validated at k = 3.
   - The joint fit in `calibrate_far.py` uses a coarse grid and leaves bands at 230–250 m under-predicted (model 4.0 against 6.8–7.0 real).
9. **Wrong timestamp in A1.** The header says "~12:30 UTC", but A1 was committed at 11:37 (`a48260b`). The commit time is consistent with "before any candidate injection matrix", since c13 finished at 11:58. The header should be corrected.
10. **C5 labelling.**
    - 48.2 m is an *expected-count* range (mean of 3 returns on a 0.3 × 0.3 m flat target, POD = 1) on the median outside-ROI grid. It is not a measured detection range, and no 0.3 m target was injected.
    - My raster measurement on frame 300 (|az| < 20°, 152 lines):
      - outside ROI: azimuth step median 0.171° (p90 0.192°), elevation spacing median 0.237° (p10/p90 0.205/0.305°);
      - ROI: azimuth 0.088°, elevation 0.062°.
    - With the p90 elevation spacing the expected count at 48.2 m is 2.3. On the track at about 48 m the ray elevation (about −2°) lies inside the ROI, so the real density there is higher and the value is conservative in practice. The docstring wording "measured" should say "expected returns on the measured median grid".
11. **The `matrix/c136` run has no `--check-prefix`.** Only `baseline_a1` has one (0 of 310 mismatches). `final_s10` has it requested.

## Answers per question with evidence

### 1a. Isolation of the behaviour change: PASS

- **Code reading** (`git diff aec88d2 -- resense ros2_ws tests`):
  - `Detector.__init__` builds `FarAxisTracker` and `FarConfirm` only if `fr.enabled and fr.axis_enabled`, or `confirm_enabled`.
  - Every hook in `_corridor`, `_accumulate` and `_confirm` is guarded by `self._far_axis is not None` or `self.far_confirm is not None`.
  - `reset()` only touches None-guarded objects.
  - `apply_sensor_profile` sets `farrange.enabled`, the 400 m crops and the relaxed `far_min_height`/`far_max_length` only for `range_model == "falcon_prime"` with `with_falcon_profile`.
  - A runtime profile switch rebuilds from `manual_cfg` (`detector_node.py` `on_profile_parameters`), so it cannot leak the Falcon values into a Pandar profile.
  - In `decision_policy.small_target_limit` the model set is still validated to {pandar128, unknown, falcon_prime}, and the pandar128 branch is unchanged.
- **Run (positive comparison):** `scratchpad/pandar_ident.py` ran the base worktree (`/home/user/wt_base`, `aec88d2`) and the branch on 100 frames of Pandar `doubleT_obstacle` (profile `pandar128`, 95 STOP detections, 2 warnings) and 100 frames of `squareT_platform_squareT_switch` (profile `manual`, 35 warnings).
  - Every `FrameResult.to_dict()` field matched, except the wall-clock latency health message (`latency p95 10x ms over the 100 ms budget`, base 25 frames, branch 0).
  - That difference is the diff tool's positive control: it detected a real, timing-only difference.
  - After removing `health.level`/`messages`, all 200 rows were identical. The manual bag hash was identical even with them.
- **Tests:** `tests/test_farrange.py` and `tests/test_range_reporting.py` gave 34 passed. `tests/test_lidar_proxy_hook.py::test_child_process_inherits_hook_and_bad_source_fails_closed` fails on **both** base and branch (pre-existing, environment-related). I did not run the full suite or `test_node.py` myself; the author's `/home/user/data/pytest2.log` shows 1974 passed and that one failure.
- **Not checked:** native C++ path equivalence (no native change in the diff), the full regression gate, X3.

### 1b. Math: CONCERN

- `FarAxis.offset` = `y_join + slope (X − join) − center_y(X)` for X > join, and 0 otherwise. It is continuous at the join (y_join = center_y(join)), so there is no lateral step for clusters straddling 50 m. Correct.
- `measure()` uses the tangent `tan(yaw) + curvature·j`, which is the derivative of `center_y`. Correct.
- The slope SE is `rms/sqrt(Sxx)`, a statistical error only, with no bias term (see B1 and note 3).
- The strict-gauge shrink `|dy| ≤ max|profile y| − sigma(X)` is an AND with the polygon test, so it can only remove points from the gauge. Correct direction.
- The `axis_valid` extension is `max(near, far.valid)`, which can only extend STOP authority. That is the hazard in B1.
- Accumulation: see B4.
- **Real-data check of the straight case:** corridor lateral minus raw-reference lateral of the candidate's STOP detections is −0.02 m (140–160 m), −0.08 m (190–210 m), −0.16 m (240–260 m) and −0.19 m (260–280 m). n is 159, 155, 500 and 93.

### 1c. Safety: FAIL (beyond the join), PASS (below 50 m)

- **Below 50 m:** `offset` = 0 and `sigma` = 0 for X ≤ `axis_join`, and nothing feeds back into `_fit_track` (the far update runs after it). No near-field path is changed, apart from `valid`, which only rises. PASS.
- **Curves and diverging walls:** see B1. FAIL.
- **Relaxed `far_min_height` 0.3 / `far_max_length` 4.0:** CONCERN.
  - On the recording, all 322 STOP detections in frames 0–1724 lie on the labelled walker (see 2), and the only non-person STOP frame of the whole recording is 2387. That frame has a 6.5 m long cluster at 197 m, 1.3 m from the person and just outside the N2 margins. The baseline has 18 such frames.
  - 38 STOP detections are longer than 3 m. Examples: frames 57 and 66 at 251 m, 6.7–7.4 m long, reason `beyond_height_ref` but zone `gauge`, kept by the tracker. They merge the walker with a static low structure at 251.2 m (lateral −1.24 m, height 0.3 m), which I found in the raw frames 151, 449 and 1502.
  - The negative evidence for the relaxed rule is one straight tunnel with a standing train. There is no curve, station, parked train or moving-ego data. Infrastructure admission is therefore *not shown*, rather than shown absent.

### 1d. C5: PASS

`falcon_expected_points(r, 0.3, 0.3) ≥ 3` gives r ≤ 48.25 m. This reproduces 48.2 analytically (0.09 / (r² · 0.0031416 · 0.0041015) = 3). The grid values match my measurement (note 10). The method is the same as the Pandar prior; for the labelling caveats see note 10.

### 2. Evidence method: CONCERN

**Far-walker labels** (`far_walker_labels.py`): raw points only, no detector output.
- I checked 10 raw frames: 5, 151, 302, 449, 598, 802, 1003, 1201, 1502 and 1703.
  - 8 of them have person-like returns at the labelled range and lateral: heights 0.9–1.8 m, lateral span ≤ 0.6 m, 2–7 points.
  - 598 and 449 are interpolated and have no walker returns, which is consistent with their interpolation.
- The path is smooth: 253 → 307 → 245 m at about 0.9 m/s.
- Over 59 sampled frames at 250–260 m: top height median 1.53 m, p90 1.71 m; 4.39 returns per frame including frames with no returns (7 % have none).
- `far_251` is not static infrastructure. Returns at 249–253 m, lateral −1.6…−0.5 m, appear only in frames 1350–1650 of the 30 frames I sampled across 0–4443, and the path walks onto the track at 1722–1724 into the main approach.
- Weakness: by construction the labeller turns any continuous in-gauge return track beyond 240 m into a label. It is a person here only because the raw geometry shows one. I confirmed that; the method alone would not.

**Association margins:**
- In `final`, all 322 STOP detections beyond 240 m in frames 0–1724 associate with the labels.
- Residuals: along p50/p95/max 0.02/0.10/1.4 m; lateral 0.05/0.21/0.62 m (margins 2.5/1.0 m). The margins did not credit a wrong object here.
- 6 random STOP frames (62, 90, 98, 1066, 1204, 1244): each detection is a 3–4 point cluster on the walker returns at heights 0.9–1.57 m. Frame 1204 also has unrelated points at lateral +2.0 m, outside the gauge and not part of the detection.

**Negative control `outside`:** I read the c136 case summaries and the `outside_static200_s0.jsonl` rows.
- No STOP and no warning in any of 18 c136 cases, with injected returns 3–17 per frame (frame 1290: 17 returns, `expected` 17.6, `occluded` 0).
- Baseline: CAUTION only, with the approach first output at 157 m.
- The control passes, but it is weak: 1.45 m beyond the gauge edge, on straight track.

**A1:**
- Moving the matrix window and excluding the far-walker outputs from "not associated with the person" is justified by the raw labels, which I verified independently. The window move does not favour the candidate.
- The k = 3 POD refit is a real-data fit that makes injection beyond 250 m harsher than k = 2.35. It is not a goalpost move in the candidate's favour.
- A1 does not cover C6 (B2) or the episode rule (B3).

**Positive control for instrumentation:** `baseline_a1` prefix check, 0 mismatches over 310 rows.

### 3. Independent re-derivations

- **Baseline near-model centre minus the raw-reference centre** (from `track_reference.json`, fitted to the raw rails 30–90 m), computed from each row's `track_detail` and `mount_rotation`, every 20th frame of `base_ros2` (223 frames):

  | range | median | p10 / p90 |
  |---|---|---|
  | 50 m | −0.13 m | — |
  | 100 m | +0.34 m | — |
  | **150 m** | **+2.08 m** | 1.81 / 2.47 |
  | 200 m | +5.11 m | — |
  | 250 m | +9.41 m | — |

  This confirms the claim that the parabola is about 2 m off at 150 m. The candidate's corridor lateral error from its detections is −0.02 m at 150 m and −0.16 m at 250 m (1b).
- **Real far-walker returns per frame at 250–260 m from raw points:** 4.39 (59 frames, including frames with no returns). The label file's 4.8/4.6 per *labelled* frame is consistent once the selection of non-empty frames is accounted for.

## What I did not check

- Native C++ equivalence, the full regression gate, X3, `test_node.py` on my own run, ROS launch.
- The seeds 10–12 matrices (`baseline_s10`, `final_s10` were running).
- `cache_falcon_full.py` decode equivalence and `track_reference.py` beyond reading the reference values.
- `calibrate_person.py`, `count_control.py` and `validate_raster.py`: I read their outputs, not their code.
- `make_tables.py` and the author's report text.
- B4 by execution (no moving-ego Falcon replay).
- The FarConfirm (C4) logic beyond the unit test; it is off by default.

---

## Re-review of e416b4e (19.10, same reviewer, same rules)

This re-review covers commit `e416b4e` (HEAD of `det/falcon-long-range`), on top of `ab26c04`:
- detector changes in `resense/farline.py`, `resense/detector.py`, `resense/config.py` and `tests/test_farrange.py`;
- PROTOCOL amendment A2.

I made no edits under `resense/`, `native/`, `configs/`, `ros2_ws/`, `tests/` or `scripts/`, and ran nothing on G3. The runs were small: about 200 real frames per run, 1–2 processes. My scripts are in the session scratchpad:
- `curve.py`, `diverge.py`: the first review's cases;
- `adv2.py`: new adversarial cases;
- `b4.py`, `b4w.py`: accumulation with ego speed given;
- `fr2731.py`: the final4 false episode;
- `handover.py`: the handover rule;
- `pandar_ident.py`: Pandar identity.

The `ab26c04` comparison code was extracted with `git archive` to `scratchpad/old/`, with the same native `.so` (native/ is unchanged).

### Status of B1–B4

| | Status | Evidence |
|---|---|---|
| B1 far axis on curves / diverging walls | **Partly resolved. A new failure mode remains: still blocking** | See (1) |
| B2 C6 post hoc, in-sample | **Resolved procedurally** (A2 §1). The seeds 10–12 numbers (`final4_s10`) were still running, so not checked | A2 text |
| B3 rule 5.1(b) | **Resolved as reporting** (A2 §5). The rule still **fails** on the new code: `eval_final4.json` gives `all_stop_episodes_le: false`, 12 STOP episodes against the baseline's 8 (`map300`: 11) | `/home/user/data/work/eval_final4.json` |
| B4 accumulation across axis switches | **Resolved** (verified by execution) | See (2) |

### (1) Adversarial tests of the new far axis

Unit tests: `tests/test_farrange.py` gives 10 passed.

**Cases from the first review now handled.** On `curve.py` and `diverge.py`:
- Every curve case is either rejected, or accepted with an error inside the stated uncertainty. The worst accepted error is 0.27 m against sigma 0.35 m. No point has error > sigma + 0.3 m.
- The occluded-inner-wall cases: one rejected, the others within sigma (0.08 m).
- Diverging walls at slopes 0.006 and 0.009 are rejected. At 0.003 the wall is accepted with error 0.45 m against sigma 0.47 m at 200 m, valid to 208 m.
- Positive control: straight track accepted to 398 m with error 0.00 m.

**New cases handled correctly** (`adv2.py`; within sigma or rejected):
- S-curve jogs of 0.25, 0.6 and 1.5 m over 130–190 m: 0.25 m accepted with error 0.12 m against sigma 0.15 m; 0.6 m rejected; 1.5 m accepted only to 128 m, before the jog.
- A niche (no points at 150–160 m) followed by a curve of R = 300 m from 160 m: support ends at 178 m, error 0.24 m against sigma 0.35 m.
- The same with a recessed wall (boundary 1 m further out at 150–160 m): same result.

**New failure mode: a straight boundary while the track curves away from it.** The geometry is physically possible:
- a straight station or cavern wall, or a parked train on a straight siding, beside a track that curves away into an opening;
- in my first `adv2.py` sign convention the track ran through the wall; those cases are discarded and the results below have the track curving *away* from the straight boundary.

| Scene | Accepted | Trusted to | Error > gauge half-width (1.05 m) from | Worst error inside the trusted range | sigma there |
|---|---|---|---|---|---|
| Straight wall on one side only, track curves R 300 m from 100 m | 1 side | 208 m | 130 m | 18.4 m at 205 m | 0.49 m |
| Same, curve R 500–600 m from 120–150 m | 1 side | 208 m | 160–185 m | 3.0–6.0 m | 0.49 m |
| Parked straight train 60–260 m at lateral 2.2 m, own walls end at 100 m, track curves R 300–400 m from 110–130 m | 1 side | 208 m | 140–160 m | 9.4–11.3 m | 0.49 m |
| **Straight wall plus a second side that ends early** (wall or column row ending at 135–190 m), track curves away just after it (R 300–600 m) | **2 sides** | **398 m** | 170–230 m | 46–108 m at 395 m | **0.35 m** |

Causes in the code:
- In `measure()` the frame's support is `max(f[3] for f in primary)`, so the end of a second side's support never caps the trust.
- With two sides, the one-side divergence allowance is dropped.
- The curve lead and the unseen-curvature term start from the *primary* support end (398 m). Up to there a straight boundary looks like evidence that the track is straight.
- One straight boundary, or two whose overlap ends early, cannot tell "the track is straight" from "the track leaves this boundary".

Result: the strict corridor is moved by metres to tens of metres in 130–400 m. STOP authority and the monitored range follow the wrong line, as in B1.

Compared with the baseline:
- On such a scene the near parabola (curvature from 4–90 m boundaries) is probably also blind to a curve starting beyond 100 m. Its trust, though, ends at its own `axis_valid` (107–175 m on this recording).
- With two sides the candidate extends trust to 398 m. With one side it extends to 208 m, and it replaces the near model from 50 m on.
- I did not build a full-scene comparison (with rails) of the baseline on this geometry. That relative statement is **unverified**.

Suggested fixes:
- Take the trusted support as the **minimum** over the accepted sides.
- Beyond the shorter side's end, treat the axis as one-sided, applying the curve lead and the unseen-curvature term from that end.
- With one side, cap trust at the near model's own `axis_valid` unless a declared map section or far rail evidence supports the axis.
- Add these scenes as negative tests.

**Real recording (straight track), as observed:**
- The new far axis is trusted only to about 128–187 m (`fr2731.py`, frames 2721–2736: `valid` jumps 128–180 m from frame to frame, 1 side); about 182–184 m on frames 1295–1305.
- `final4`: the far walker gets 0 STOP frames (the first candidate had 322), and the main person's first STOP is at 168.7 m (baseline 127 m, first candidate 249 m). `final4_map300`: 0 and 205 m.
- **New false STOP episode at frames 2731–2734**, at 153 m with raw lateral +2.1 to +3.3 m (a wall or structure), reason `beyond_axis`, zone `gauge`. I reproduced it on a fresh run from frame 2600.
  - Mechanism: the main person is tracked at 154 m with the far axis. When `far.valid` drops below the person's range (frame 2729: valid 144 m, decision GO while the person is in the gauge at 153.6 m), points beyond `valid` get near-model laterals, 2 m off at 150 m.
  - The person leaves the corridor and the wall at +2.1 m enters it. The existing STOP track (age 26–29) is re-associated to the wall and held at STOP by the tracker.
  - Cause: the "far offset only for join < X ≤ valid" change together with a `valid` that fluctuates by tens of metres from frame to frame.
  - It does not lose a baseline STOP, since the baseline does not STOP at 154 m. It is a false STOP on infrastructure plus STOP flicker on a real person, neither of which the first candidate had.
  - This is not counted by any rule except 5.1(b) and "false episodes" (1 against the baseline's 3).

**Far axis toggling while moving with ego speed given:** see (2).

### (2) B4 by execution, ego speed given

`b4.py`: real frames 1290–1333 with ego speed 2.0 m/s given, so accumulation is active. Frames 1306–1319 are cropped at 110 m to force the far axis to fail, be held, and drop. I compared `e416b4e` with `ab26c04`.

- **Far axis appears (frame 1295):**
  - New code: `n_accumulated` is 1, then 2, 3, 4, 5 in the following frames, so the buffer was cleared.
  - Old code (positive control): `n_accumulated` = 5, merging four frames stored before the axis existed.
  - At 1295–1297 the old code has two extra warnings at 104.8 and 114.2 m (lateral 1.3 m). They persist to 1298, so I do **not** attribute them to the mixed buffer.
- **Line moves more than 0.2 m at the range end (during the hold):** buffer clears at 1307–1312.
- **Axis disappears (1315):** cleared, `n_accumulated` = 1, then 2–5.
- When the axis returns after the hole, the new code did not re-confirm within 14 frames, while the old code did at 1324. I did not investigate this.
- `n_accumulated` alone is confounded during the cropped frames: the old code also shows 1 there, with no clear.
- The appearance transition is a clean test. B4 is resolved.

### (3) Can the handover rule drop a baseline STOP near the sensor?

- **Below 50 m: no, by construction.** `offset` and `sigma` are 0 for X ≤ `axis_join`. The handover sets `axis_valid = end`, with `end ≥ far.valid ≥ axis_join` (50 m; `FarAxisTracker` floors `valid` at `j`). A demotion needs distance > `axis_valid`, which is at least 50 m.
- **Between 50 m and the near model's `axis_valid`: yes, per frame.**
  - When the far line and the near model disagree by more than 0.5 m at `end`, `axis_valid = end`, which can be below the near model's `axis_valid`.
  - Clusters in (end, near `axis_valid`] then get `beyond_axis`, where the baseline (same near-model laterals there) would not.
  - Test (`handover.py`): real person at 120 m, frames 2900–3029, both runs cropped at 130 m from frame 3010 so the held far axis decays (valid 149 → 64 m).
  - Frames 3014–3015: the candidate's detection at 119.7 m is `beyond_axis`, while the baseline's at 119.7 m is a clean `gauge` detection.
  - The **decision** stayed STOP in every frame, identical to the baseline from 3010 to 3029, because the tracker held the track.
  - A new or young track at 50–125 m during a far-axis hold or a short `valid` could therefore lose a STOP that the baseline gives. On the real recording no baseline person STOP frame was lost (`eval_final4.json`: `lost_person_stop_frames` 0).
- Suggested fix: never lower `axis_valid` below the near model's own `axis_valid` (use `max(near, end)` always). Separately, decide the lateral beyond `far.valid` by the same agreement rule, so the near model's laterals are not used where it disagrees.

### (4) Pandar re-check

`pandar_ident.py` on `e416b4e`, `doubleT_obstacle`, profile `pandar128`, 100 frames: identical to `aec88d2` on every field except the wall-clock latency health message (same as the first review). Code reading confirms the new detector hooks (buffer clear, handover) are inside the `self.far is not None` / `far is not None` guards.

### Remaining blocking issues after the re-review

- **R1 (from B1).** A straight boundary while the track curves away is accepted. With a second side that ends early, the far axis is trusted to 398 m with sigma 0.35 m and errors of tens of metres. The support must be the minimum over sides, and one-sided trust must be capped.
- **R2 (new).** Frame-to-frame swings of `far.valid` on straight real track (128–187 m), combined with near-model laterals beyond `valid`, produced a false STOP episode on a wall at 153 m (frames 2731–2734). They also produced a GO frame while the real person stood in the gauge at 153.6 m (frame 2729).
- **R3 (new, minor in effect on the recording).** The handover rule can lower `axis_valid` below the baseline's in 50–175 m. A per-frame `beyond_axis` demotion was observed at 119.7 m, and the decision was saved only by tracker hysteresis.
- **B3 still fails as a criterion** (12 > 8) and must be reported as failed (A2 §5 commits to this).

### Not checked in this re-review

- Seeds 10–12 matrices (`final4_s10` was running), the walk control on `final4` (`walk_final4_*`), the full test suite, X3, the regression gate, `map300` beyond its eval summary.
- Why the far walker gets 0 STOPs in `final4_map300` despite a declared section to 300 m.
- Why the far axis did not re-confirm after the forced hole in `b4.py`.

---

## Re-review of 89e0f3b (19.10, same reviewer, same rules)

Commit `89e0f3b`. The detector diff since `e416b4e` touches `resense/farline.py`, `resense/detector.py`, `resense/config.py` and `tests/test_farrange.py`.
- `measure()`: with two sides the support is the shorter side's.
- One side: trust is capped at the near model's `axis_valid` unless `declared_straight_to > 0`.
- `axis_valid = max(near, far.valid)`, and the handover rule is removed.
- Beyond `far.valid` the near model's laterals are used, as in `e416b4e`. `lateral_to` defaults to 0 and is never set, so the 0e49f7c variant is inactive.

No edits under the protected paths and no G3. Small runs only: one or two processes, at most 140 real frames each, plus reads of the replay outputs.

### Checks run

- **Tests:** `tests/test_farrange.py` and `tests/test_range_reporting.py`: 40 passed.
- **Pandar identity** (`pandar_ident.py`, `doubleT_obstacle`, profile `pandar128`, 100 frames): identical to `aec88d2` except the wall-clock latency message.
- **`adv3.py`:** `adv2.py` with a realistic near-model `axis_valid` of 123 m and 175 m (the range seen on the recording).
- **R2 probe:** `fr2731.py`, fresh run of frames 2600–2740.
- **R3 probe:** `handover.py`, frames 2900–3029, cropped at 130 m from 3010, against the baseline (`with_falcon_profile=false`).
- **B4 probe:** `b4.py`, ego speed 2 m/s.
- **Full-recording scans** of `final6.jsonl` against `base_ros2.jsonl`, `final4.jsonl` and `c136.jsonl`:
  - every STOP detection with raw lateral more than 1.3 m from the raw track reference;
  - every non-STOP frame whose clear distance reaches a labelled person standing in the gauge. Labels: far-walker labels plus the walk-control path of the main approach, 1055 frames with |lateral| ≤ 0.8 m.

### Adversarial results (`adv3.py`)

**Two sides, the second ending early, track curving away from a straight wall** (8 cases):
- Trust now ends at the shorter side: `valid` 133–188 m for second sides ending at 135–190 m.
- Error 0.00 m everywhere inside `valid` (sigma 0.35 m). **Resolved.**

**One straight side (wall or parked train), track curving away:** trust is capped at the near model's `axis_valid`.

| Near `axis_valid` | Result |
|---|---|
| 123 m | Worst error 0.67 m at 120 m (sigma 0.26 m); never more than the gauge half-width |
| 175 m | Errors exceed 1.05 m from 130–160 m, up to 9.4 m at 175 m (R 300 m from 100 m), 5.0–5.3 m for the parked-train and R 300 m from 120 m cases (sigma 0.40 m) |

- This error lies **inside the range the near model already trusts**. A near parabola that is equally blind to a curve beginning beyond its 4–90 m fit has the same error there, so the far axis no longer extends trust on a wrong line.
- What remains: in 50 m–`axis_valid` the far line replaces the near model's laterals. If the near model had partly captured the curve, the kink limit (0.006 with one side) is the only guard. I did not test this in a full scene with rails. **Residual, unverified, not blocking.**

**Unchanged since the previous round:** S-curve jogs, niche or recess followed by a curve, curves, diverging walls. All are within sigma or rejected; the farline changes do not touch these paths.

### R2 on the real recording

**Frames 2725–2740** (person standing in the gauge at 152–154 m, raw lateral −0.15 m):
- `final6`: GO in 2722–2735 and 2737–2740; CAUTION at 2736–2737 on a wall warning (`beyond_axis`, lateral +2.2 m). **No STOP on the wall.**
- My fresh run gives the same picture. One side only, `valid` 107–127 m (capped at the near trust), support 131–173 m.
- The person is beyond `far.valid`, so the near laterals (2 m off) put it outside the corridor. That is the baseline's behaviour: the baseline is CAUTION there on wall warnings, its first person advisory is at 144 m, and it never STOPs the person beyond 127 m.

**Whole recording, STOP detections more than 1.3 m off the track reference:**
- `final6`: 7 frames (4241–4247), all on the 115 m structure at lateral 1.8 m. Every one co-occurs with a person STOP at about 22 m; frames 4241–4244 are also baseline frames.
- Baseline: 29 frames (25–28, 125, 2312–2314, 3925–3932, 4060–4064, 4241–4244, 4253–4256).
- `final4`: 9 frames at 152–162 m. These were the R2 hijacks; they are gone.

**False-clear scan** (non-STOP frame whose clear distance reaches a labelled in-gauge person, of 1055):

| Run | Frames | Detail |
|---|---|---|
| `final6` | 2 | 2700 GO, clear 157.6 m vs person 157.4 m; 3050 CAUTION 115.4 m vs 115.4 m |
| baseline | 2 | 2800 CAUTION 155.2 m vs 144.8 m; 3050 115.1 m vs 115.4 m |
| `final4`, `c136` | 0 each | |

The `final6` frames are 0.0–0.2 m beyond the person, within the lateral and range error. Comparable to the baseline.

**R2 resolved** as a regression. The mechanism (near-model laterals beyond `far.valid`, 2 m off at 150 m on this recording) remains, but it is now exactly the baseline's behaviour there.

### R3 (`handover.py`)

Per-frame reasons now match the baseline during the decaying hold:
- frames 3013 and 3015 `beyond_axis` in both runs; 3014 clean `gauge` in both;
- the decision is identical to the baseline in every frame 3010–3029.

Code: `axis_valid = max(near, min(far.valid, range_max))` can never be below the near trust. **Resolved.**

One difference seen: at frames 3017–3018 the candidate also has a `gauge` detection at 115.0 m. This is the 115 m structure, the baseline's false-STOP object; the baseline has it as a warning in those frames. It co-occurs with the person STOP at 119 m, so the decision is the same. **Residual, not blocking.**

### B4 again (`b4.py`)

Still cleared on appearance: `n_accumulated` 5 → 1 at frame 1295, then 2, 3. Also cleared on disappearance: 1 at frame 1315, then 2–5. **Resolved.**

### Status per item

| Item | Status at 89e0f3b |
|---|---|
| B1 curves / diverging walls | **Resolved** (in-sigma or rejected in every probe) |
| R1 straight boundary beside a curving track | **Resolved** for two sides. **Residual** for one side: errors up to 9.4 m inside the near model's own trust when that trust is 175 m. It is no longer an extension of trust; the full-scene comparison with the baseline is unverified |
| R2 hijack / false wall STOP beyond `far.valid` | **Resolved** as a regression: no false wall STOP at 152–162 m; wall-STOP frames 7 (all co-occurring with a person STOP) vs baseline 29 |
| R3 handover lowering the trust | **Resolved** |
| B2 C6 post hoc / in-sample | **Resolved procedurally** (A2). The seeds 10–12 numbers were not available to me |
| B3 rule 5.1(b) | **Fails as a criterion**: 9 STOP episodes vs baseline 8 (`eval_final6.json`, `all_stop_episodes_le: false`). It must be reported as failed (A2 §5); it is not a code defect |
| B4 accumulation across axis switches | **Resolved** (by execution) |

### Is 89e0f3b acceptable as a Falcon-profile-only candidate?

**Yes, conditionally.** On the measured evidence I found no remaining blocking code defect.

**Supporting evidence:**
- **Pandar** is byte-identical apart from timing (300 frames over the three rounds; code paths guarded).
- **Real recording, `eval_final6.json`, against the baseline:**
  - 0 baseline person-STOP frames lost;
  - main-person STOP frames 1388 vs 1369;
  - first person STOP at 146.3 m vs 127.1 m;
  - STOP episodes without a person 0 vs 3; STOP frames not associated with the person 0 vs 18;
  - CAUTION share lower.
- **Adversarial geometry:** no probe extends trust onto a wrong line beyond what the near model already trusts.

**Conditions:**
1. Report rule 5.1(b) as **failed** (9 > 8).
2. Report the seeds 10–12 matrix numbers (C6 is post hoc) with the X3 and regression-gate results; I did not see them.
3. State the measured gain honestly. It is **about 20 m on the first person STOP (127 → 146 m)**, not 250–300 m.
   - The far walker at 245–307 m gets **0 STOP frames** with `final6` (`far_target_stop_frames` 0).
   - Longer range needs the declared route-map section (`map300`). That section switches off the unseen-curvature guard up to the declared distance, so it is only as safe as the map.
   - C5 (48.2 m small-target range) is an expected-count model value, not a measured detection.
4. Keep the residuals listed as open:
   - one-sided far axis inside the near trust on a track curving away from a straight boundary;
   - the 115 m structure is a gauge detection in some candidate frames where the baseline has it as a warning (always co-occurring with a person STOP in my samples);
   - moving-train operation tested only with synthetic shifting of a static scene (`b4.py`), not with a moving recording.

### Not checked in this round

- Seeds 10–12 matrices, the walk control on `final6`, X3, the regression gate, the full test suite.
- `map300` on 89e0f3b.
- The one-sided residual in a full scene with rails.
