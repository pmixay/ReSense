# Falcon far range 1.3: pre-registered protocol (21.10)

Branch `claude/falcon-far-range-1.3`, base `6ee469c` (detector bytes = v1.2.0 `3b73bbe`, freeze digest
`6d091081…`). Card N7. Predecessor: [`falcon_long_range_2026-10-19`](../falcon_long_range_2026-10-19/REPORT.md)
(candidate `89e0f3b`, merged off). Written after the reproduction and the diagnosis below and **before any
measuring run of the change** (the change is not implemented at the time of this commit). Later changes to
this file are appended as dated amendments, never edited in place.

## 0. What was done before this protocol (inputs to the design, all on the real recording)

1. **Reproduction** (step 1 of the task). Full Falcon cache rebuilt (4,443 frames, 89/89 decode checks
   identical to the node decode). Replays on v1.2.0 (`/home/user/wt_v120`, detached `3b73bbe`) with
   `falcon_ros`: baseline (farrange off) and candidate (`--pre farrange.with_falcon_profile=true`).
   `falcon_eval.py` reproduces the published rows exactly: decisions 13/3,043/1,387 and 1,420/1,635/1,388;
   STOP episodes 8 and 9; episodes without a person 3 and 0; first STOP on the main person 127.07 m and
   146.30 m. Row comparison against the archived 19.10 replays (`aec88d2` era, numpy 1.26): decision, nearest,
   clear and monitored identical on all 4,443 rows; last-bit float differences in `curv`; frames 4366–4367
   have one detection at 28 m reported as a warning instead (decision STOP in both).
   The traced runs (`scripts/run_far.py --trace`, `--detail`) are row-identical to the plain run (0 of 4,443
   rows differ on every field except wall-clock timing).
2. **Diagnosis, traced** (`run_far.py --trace --detail`, per-frame far-axis state and the per-side bins of
   `farline.measure`, hook checked to leave the rows unchanged):
   * The far axis is one-sided (left wall) in every traced frame of the person approach; its trust is then
     capped at the near model's `axis_valid`, which jumps between 107 and 171 m from frame to frame. The
     person at 137–157 m is STOPped only in the frames where that cap happens to reach it: candidate episodes
     2787–88, 2800–02, 2856, 2858 (4 short onsets) replace the baseline's 3 false episodes, hence 9 vs 8.
     The walk-control "real 146.5 m" is the single frame 2787: band 150–125 m STOP fraction 0.071 real,
     0.0–0.01 injected; the gap is the flicker, not the person model.
   * The right side (a column row) is seen in most frames, but as a second fitted line it fails the
     0.002 slope-agreement test and then **rejects the whole frame** (888 of 929 frames where it was accepted
     as a second side); otherwise its rms (0.17–0.25 m) fails 0.15 m.
   * Raw geometry (track reference, frames 1300–1700 and 3900–4440, `scene.py`, raw points only):
     left boundary in the 1.0–2.8 m band to 192 m, **no returns 195–245 m** (≤ 0.07 points per frame at any
     height 1.2–4.5 m from the axis), then 247–262 m; right column row every 30 m at two lateral families
     (−1.35…−1.68 m at 52, 82, 142, 202 m; −1.97…−2.16 m at 112, 172, 232 m); the right bins at 172 / 202 /
     232 m enter the far-axis band in 77 / 6 / 16 % of frames. Relative to the validated track reference the
     left wall drifts outward by ~0.2 m over 50–260 m.
   * Consequence for the range target: with the review's rule "the trust ends at the shorter side" (R1), the
     two-sided support on this recording cannot exceed the left wall's 192 m without bridging an unobserved
     56 m gap, and the right row usually ends at 172 m. **Expected honest unconditional trust: about
     165–190 m; ≥ 200 m is the goal but is not expected without a route map.**

The design parameters below were chosen from these real-recording bins (in-sample, stated as such). The
out-of-sample checks are the synthetic negative controls (§3) and the injection matrix with fresh seeds (§4).

## 1. The change (behind one new switch, `farrange.axis_stable`, class default `False`)

All of it is inside `resense/farline.py` / the far-axis hooks, reachable only with `farrange.enabled`
(set only by the Falcon profiles when `farrange.with_falcon_profile`). Pandar is untouched by construction.

* **C7 second side as a parallel tube.** A side with fewer than `axis_min_bins` kept bins (the column row)
  is fitted robustly with keep tolerance `axis_second_tube` (T = 0.5 m) and rms ≤ `axis_second_max_rms`
  (0.25 m), ≥ 4 bins over ≥ 80 m, contiguous (gap ≤ 40 m). Its support ends at the first observed bin outside
  the tube (a **contradiction** at that X). The two sides need not agree to 0.002: their slope difference Δs
  gives a **divergence cap** `join + T / |Δs|` (where they have diverged by T); a frame is not rejected for it.
  The two-sided support is min(primary, second); the curve lead uses T (√(2T/k) = 17.3 m at k = 1/300).
* **C8 support history.** The per-frame two-sided support is kept for `axis_history_frames` (10) frames and
  aged by `axis_history_speed` (25 m/s, metro maximum) × elapsed time: an unseen-curve bound from an older
  frame stays a bound after the train has moved at most that far. The used support is the second-highest
  aged value (two frames must agree), capped by the aged contradictions of the same window. A frame that
  fails the curve tests keeps the existing hold (10 m decay per failed frame, `axis_hold_frames`).
* **C9 two sides only.** Without a two-sided support in the window the far axis is not used (the near model,
  as v1.2.0); with `declared_straight_to` the one-sided behaviour of 89e0f3b applies (route-map variant).
  This removes the R1 residual (one-sided far line inside the near trust) instead of capping it.

Unchanged: the primary side's checks, the unseen curvature R 300 m, sigma ≤ 0.5 m, the strict-gauge shrink
by sigma, the accumulation-buffer clear, C5/C6 under the profile, the clear-distance model and
`decision_policy.py` (not this lane).

## 2. Configurations measured

| label | config |
|---|---|
| `base` | v1.2.0 detached checkout `3b73bbe`, `falcon_ros`, farrange off (fresh control, run once, reused) |
| `c89` | this branch, `--pre farrange.with_falcon_profile=true` (= 89e0f3b behaviour, `axis_stable` off) |
| `cand` | this branch, `--pre farrange.with_falcon_profile=true --pre farrange.axis_stable=true` |
| `map300` | `cand` + `--pre farrange.declared_straight_to=300` (conditional route-map variant, reported separately) |

## 3. Synthetic negative controls (must keep failing safe)

`scripts/neg_controls.py` and `tests/test_farrange.py`, with `axis_stable` on. **Fail-safe** means: in every
case and every frame where a far axis is returned, for X in (join, valid]: |far lateral − true centre| ≤
sigma(X) + 0.3 m (the review's tolerance) and never above the strict-gauge half-width 1.05 m; rejecting is
always acceptable. Cases: the review's 16 curves (Xc 120/160/200/240 m × R 300/600/1000/3000 m) with and
without an occluded inner wall; single diverging wall 0.003–0.009 with the other side absent or ending at
120 m; one straight wall (station / parked train) beside a track curving away; two sides with the second
ending early (135–190 m); S-curve jogs 0.25 / 0.6 / 1.5 m; a niche or recess followed by a curve; **new:** a
sparse column row (30 m, two lateral families ±0.25 m) that follows the track while it curves away from a
straight wall (R 300–3000 m, Xc 120–240 m) or towards it; the same with the row seen only in alternate
frames; a curve start approaching at 20 m/s (moving scene, 100 frames) with intermittent visibility.
Reported, not required (a known limit of boundary-based axes, also of the near model): a turnout leaving a
straight two-wall tunnel through a ≤ 40 m gap.

## 4. Pre-registered acceptance criteria for `cand` (switch on only if all pass)

Real recording, `falcon_ros`, whole recording, `falcon_eval.py` (person association as 19.10 A1):

1. Rule 5.1(b): STOP episodes ≤ 8.
2. STOP episodes without a person frame: 0.
3. No v1.2.0 (`base`) person-STOP frame lost.
4. CAUTION share ≤ `base` (0.6849).
5. STOP frames not associated with a person ≤ `base` (18).

Walk control (`walk_control.py`, seeds 7000–7002 as 19.10, frames 300–1210, candidate config):

6. Injected first STOP within ±15 m of the real first STOP of `cand`, every seed.

Injection matrix (`matrix2.py`, window frames 1290+, POD k = 3, targets of 19.10 A1; **fresh seeds 20, 21, 22**):

7. Approach 400 → 100 m at 10 m/s: per target and seed, `cand` first associated STOP ≥ `base` − 2 m (or
   `base` has none).
8. Static 150/200/250/300/350 m: per target, range and seed, `cand` STOP fraction ≥ `base` − 0.05.
9. Moving (person_front and cube20; M1 approaching walk 230 → 185 m at 1.5 m/s; M2 receding walk 120 →
   165 m; M3 receding trolley 100 → 250 m at 5 m/s; M4 lateral random walk at 160 m within ±0.8 m; M5
   stop-and-go from 200 m; M6 crossing at 150 m, −3 → +3 m at 1 m/s; M7 chaotic: along random walk around
   170 m ± 20 m plus lateral ±0.8 m): per case and seed, `cand` associated STOP frames while the target is in
   the gauge (|lateral| ≤ 0.8 m) ≥ `base` − 2, and associated STOP frames while it is outside (|lateral| ≥
   1.6 m) ≤ `base` + 2.
10. Negative control `outside` (1 m cube at lateral +2.5 m): 0 STOP frames in every case.

Negative controls (§3):

11. Every required case fails safe.

Pandar and robustness (on the final commit):

12. Full regression gate `scripts/regression_gate.py` (default config, cache, ride) exit 0 without
    `--allow`, and every per-frame row identical to a v1.2.0 run of the same gate (`farrange` is
    Falcon-profile-only; any differing row is explained or the criterion fails).
13. X3 (`scripts/robustness_battery.py -j 2`, protocol `p4_start_2026-10-15`) on the final commit, paired with
    a fresh v1.2.0 reference: within its limits (≤ 1 extra false STOP episode, ≤ 2 lost matching STOP frames
    per positive object).
14. ROS node path: the `falcon_ros` / `falcon_native` profiles enable farrange and `axis_stable` when switched
    on; the node's decisions and detections on Falcon frames equal the offline replay.

Reported, not pass/fail: first STOP on the main person (**goal ≥ 200 m**; 100 m good, 200 m very good,
300 m excellent per QA row 14); the fraction of frames where the far trusted range changes by ≥ 20 m
between frames (19.10: 34 %); far-walker E4 rows; the 115 m left-wall structure (gauge detection or
warning); frames 0–1700 rows of rule 5.1(a); `map300` rows (conditional on a route map, never the
unconditional result); unit tests.

If any of 1–14 fails, `farrange.axis_stable` and `farrange.with_falcon_profile` stay off and the failing
rows are reported. Not used: the held-out G3 set. Parameters are not tuned on seeds 20–22.
