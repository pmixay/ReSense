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

## Amendments

### A1 (21.10, after implementing, before any measuring run of the change)

1. **C7 as implemented.** The second side is taken from its near end outwards while its bins stay within
   T = 0.5 m of one straight line with rms ≤ 0.25 m; the first observed bin that breaks that line is the
   contradiction X; observed bins off that line *before* its first kept bin are contradictions too (found by
   the acceptance test `test_stable_contradiction_caps_the_history_at_once`: a robust fit over all bins could
   pick the far, bent half of a row and ignore the near half). Parameters unchanged.
2. **Test fix.** The committed acceptance tests built the synthetic column row with lateral families ±0.25 m:
   an alternating ±0.25 m pattern has an rms of exactly 0.25 m, the registered limit, so the row was accepted
   or not by noise. The helper now uses ±0.2 m (rms 0.2 m). The registered parameters are not changed.
3. **Design check on recorded bins (not a measuring run of the detector):** the implemented `_second_tube`
   applied to the right-side bins recorded by `run_far.py --detail` on the v1.2.0 candidate run (4,312 frames
   with right bins): support 172 m in 70 %, 142 m in 22 %, 202–262 m in 5 %, none in 3 %; a contradiction in
   1.5 % of frames.

### A2 (21.10, after the first `cand` replay of the real recording at `3de4534`; in-sample)

The first `cand` replay (`3de4534`) gave 6 STOP episodes, **2 without a person** (frames 121, 147–148: the
115 m left-wall structure), first STOP on the main person 127.1 m (no gain). Trace: the far trust was
104–128 m because the divergence cap `join + T/|Δs|` used the second side's own fitted slope, which the
column row's two lateral families bias (Δs median 0.0046, its standard error 0.0022 on the recorded bins),
and the cap was aged over the history (another ~20 m). With the far trust below 115 m the structure got the
near model's laterals (≈ 0.8 m off there) and the baseline's false STOP came back. Changes, all in C7:

1. The second side is tested **against the primary line**: its bins, from the near end outwards, must stay
   within T of a line parallel to the primary (offset = mean residual, rms ≤ 0.25 m). This bounds the
   divergence at every observed bin; no slope estimate of the sparse row is used. A divergence cap
   `join + T/|Δs|` remains only for two fitted walls (dense, small slope errors), and it caps the current
   frame only (a property of the fit, not an observed location); observed contradictions are still aged.
2. A contradiction caps at the **last consistent bin before** the breaking bin (a curve may start right after
   it), for the second side and for a primary side's rejected run (was: at the breaking bin).
3. A statistically reduced cap (Δs − 2 SE) was tried and dropped: it let the negative control "row follows a
   R 3000 m curve from 160 m" fail (0.70 m error, allowed 0.70 m).

Design check on the recorded bins after these changes: the right row stays within the tube to 142 m in 70 %
of frames and to 172 m in 26 %; a contradiction after 142 m in 49 %. **Revised expectation: two-sided trust
≈ 120–170 m on this recording.** Negative controls after the change: 92/92 required cases fail-safe; unit
tests 19/19. All `cand` / `map300` numbers reported are from the commit after this amendment; the
`3de4534` replay is kept as history (`raw/`).

### A3 (21.10, after the second `cand` replay at `bff848b`; in-sample)

`bff848b`: 5 STOP episodes, **1 without a person** (frames 912–913, the 115 m structure again), first STOP
on the main person 127.07 m (= baseline), CAUTION 0.218, far trust 116–127 m (p10–p95). Trace: every
observed contradiction was aged and kept for 1 s with the minimum taken, so isolated contradictions (the
right row breaking after 82 or 112 m in 0.5–1.7 % of frames) pulled the trust down to 64–79 m for up to
ten frames (frames 905–915), and the frequent one after 142 m (49 %) minus up to 22 m of ageing held it
near 120 m. Change: **this frame's contradiction caps at once (unchanged); older contradictions cap once two
frames agree** (the second-lowest aged one), the same rule as for supports. A variant without the
current-frame cap was rejected because it failed the registered acceptance test
`test_stable_contradiction_caps_the_history_at_once`. Unit tests 19/19, negative controls 92/92 required
fail-safe after the change.

### A4 (21.10, priority change from the user via the captain; before the measurements it governs)

Registered after the `52d2447` replay (A3 rows: 3 STOP episodes, 0 false, CAUTION 0.200, first STOP on the main
person 127.07 m = v1.2.0) and before: the doubt-model runs, any further design change, the candidate matrix,
the walk-control comparison of the final design, the node check, X3 and the gate.

1. **Distance first.** False-alarm rows may regress within a bound: the STOP episodes added over the whole
   Falcon recording + the ride + the five empty Pandar recordings together ≤ +25 % of v1.2.0 (8 + 26 + 11 = 45,
   so ≤ +11). CAUTION share may rise. Every added false episode is listed with frames, traced cause and a
   picture. Criteria 1, 2, 4, 5 and the outside rows of 9 and 10 become this bound.
2. **Still hard:** no positive object (Falcon main / far person, injected targets, set O, labelled
   recordings, X3 positives) loses its STOP; a first STOP may come later than v1.2.0 by at most max(5 m, 5 %)
   and only on objects listed; the net change over the registered objects must be a gain. Criteria 3, 7, 8,
   the in-gauge rows of 9, and 11 (no trust across an unseen curve) are unchanged. `declared_straight_to`
   stays a separately reported conditional variant.
3. **Gate:** first without `--allow` (failures reported), then with `--allow` covering exactly the
   false-alarm rows inside the bound (listed).
4. **Switch on** in the final commit if the range gain and the hard rows pass and the false alarms stay
   inside the bound.
5. **Learned track opinion** (`tracking.doubt_model`, Pandar-trained, not profile-gated): measured on the
   Falcon for `base` and `cand` with `tracking.doubt_model=""` against the default: delay of the main person's
   first STOP (frames, m) and of the injected targets' first STOP, with the withheld tracks traced. If it costs
   range on the Falcon, a Falcon-profile-only change (doubt off under `with_falcon_profile`) is in scope; Pandar
   unchanged.
6. **Timing** is not a criterion; per-frame time p50 / p95 (same machine, baseline vs candidate) is reported.

### A5 (21.10, under A4, before its measurement; in-sample design change)

The A3 history ages every observed contradiction over 1 s and takes the second-lowest, so a contradiction
seen once or twice (the right row's 172 m column sits at the tube edge: contradiction after 142 m in 49 % of
frames) holds the trust 5–20 m below the 142 m that most frames confirm. Change (C8 only): **the support is
the farthest aged level that at least two frames reach and that more frames reach than contradict below
it**; this frame's contradiction still caps at once; divergence of two fitted walls caps this frame.
Expected on the recorded bins: support ≈ 142 m in most frames (trust ≈ 139 m), not more: the 172 m level is
contradicted more often than confirmed. Unit tests 19/19 and negative controls 92/92 required fail-safe
after the change. The registered criteria are A4's.

### A6 (21.10 evening, after the independent review `claude/falcon-far-range-review-1.3` @ `f0f3b8d`, ACCEPT WITH CONDITIONS; before any measuring run of this revision)

Inputs: the review's findings F1–F7 and the captain's work order. F1 was reproduced on my own `cand` replay
before writing this: `person_frames.py` (the reviewer's) gives 30 GO frames with the main person inside the
reported clear and monitored range, person at 138.6–162.3 m, `far.valid` 134–139 m, near `axis_valid` 159–167 m.

**Changes (all under `farrange`, Falcon profiles only):**

1. **F1, root cause: the corridor between `far.valid` and the near model's trusted range.** Today the near
   model's laterals are used there; on this recording they are ~2 m off at 150 m, so a person on the track is
   outside the corridor while the clear distance runs past them. Change (`farrange.axis_union_beyond`, on with
   `axis_stable`): for far.valid < X ≤ max(near `axis_valid`, far.valid), a point's corridor lateral is the
   nearer to the centre of (a) the near model's lateral (exactly v1.2.0's corridor) and (b) the lateral
   from the far line continued straight. So the corridor is the union of both hypotheses. The trusted range is
   unchanged (never beyond v1.2.0's near trust). It can only add points to the corridor, never remove one, so
   no v1.2.0 detection is lost by it. A reported clear range then means both hypotheses are empty. If
   GO-with-person-inside-clear is still > 0 after it, the reviewer's cap is added on top: the clear and
   monitored range is cut at far.valid where the two laterals disagree by more than the strict-gauge
   half-width. That is reported as A7 if needed.
2. **C3, turnout / crossover guard (two physical conditions on a confirming boundary):**
   * **(a) Tight boundaries.** A side confirms the far line only if its boundary lies within
     `axis_max_boundary_lateral` = 2.5 m of the line (median over its support bins). A single-track tunnel's
     boundaries hug the track (1.35–2.2 m on this recording). Between wide boundaries (a two-track box, a
     cavern), a track can curve away with no boundary evidence.
   * **(b) Exit gaps.** Within a confirming side's support, a gap g between kept bins ends the support at the
     gap's start when g ≥ √(2·R_t·(d + 1.6)), where d is the side's lateral, 1.6 m the train half-envelope and
     R_t = `axis_turnout_radius` = 200 m (metro 1/9 turnout). A diverging track can leave through such an
     opening. At d = 1.7 m the limit is 36.3 m (the real left wall's longest kept gap is 35.0 m: expected
     cost 0, to be measured).
   * Expected: the reviewer's probe W and my case K become fail-safe.
3. **F6:** the stale config comments are corrected; the acceptance test
   `test_stable_switch_is_off_by_default_and_enabled_with_the_profile_switch_only` is renamed and asserts the
   current defaults (on under the Falcon profiles, off under manual / pandar128). **F7:** the README states
   that C6 (`far_min_height` 0.3, `far_max_length` 4.0) and the 400 m crop ship with the switch.

**Hard rows (all on the final commit):**

* **H1.** GO frames with the person / target inside the reported clear and monitored range
  (`person_frames.py`, the review's `summarize_scenes.py` column and `matrix_go.py`) = **0** on the real
  recording (6 start frames 0 / 600 / 1200 / 1800 / 2100 / 2400), on the review's 82 scenes and on the
  matrix with fresh seeds **60, 61** (never used).
* **H2.** No v1.2.0 STOP lost or delayed: whole recording (`falcon_eval.py` lost frames = 0; first and held STOP
  ≥ v1.2.0 at every start), scenes (target first / held STOP not later than v1.2.0 by more than max(5 m, 5 %),
  no target that v1.2.0 STOPs left without a STOP), matrix criteria 7–10.
* **H3.** Negative controls: the 92 required cases fail safe, and **K and the review's W probes become fail-safe**
  (C3). Unit tests pass.
* **H4.** False alarms within the A4 bound (Falcon + ride + empty Pandar added STOP episodes ≤ +11); every added
  false episode listed and traced. Scenes are reported, not bounded (non-physical edits included).
* **H5.** Walk control within ±15 m; Pandar gate exit 0 without `--allow`, rows identical to v1.2.0
  (timing messages excepted); X3 PASS paired with v1.2.0; node check equal to the replay.

**Reported (C2):** first STOP and **held STOP** (≥ 90 % of the next 3 s, the review's `evalrows.py`) for every
start frame. A first STOP that is a short blip is called one. Goal: improve the held STOP (v1.2.0
114.4–123.0 m, the 0eb4dda candidate 127.4–130.2 m).

If H1–H5 pass, the switches stay on (`axis_union_beyond` on with them); otherwise the failing rows are reported
and the switch state is decided by the A4 rule.

### A7 (21.10, after the first A6 replay at `884b572`; the cap A6 §1 anticipated)

`884b572`, whole recording (`a6_cand`):
* GO with the person inside clear and monitored: 30 → **6** frames (person at 150.9–162.3 m).
* STOP episodes 13, all with the person (0 without one); first person STOP 150.5 m; held STOP 129.4 m.

Traced at frame 2660 from frame 0 (`scripts/trace_person.py`): the union works. The person's 17 points get
the far-line lateral (≈ 0) and are all strict-gauge candidates. But the near-model hypothesis of the same
stretch places the left wall (152–162 m) inside the corridor, because the near model is 2.3–3.0 m off there.
The person merges with it into one 10 m blob (x 152.7–162.7, y −0.54…2.41), which the shape rules drop. v1.2.0
has the same wall-in-corridor; it never sees the person there.

Change (the reviewer's cap, A6 §1), `farrange.axis_report_tolerance` = 1.05 m (the strict-gauge half-width):
beyond `far.valid`, the reported monitored and clear range ends at the first X where the near model's corridor
centre is farther than that from the continued far line. Through the existing `wall_drift` cap of
`health.update`: "the corridor beyond is not where the track is". Detection, trust and clustering are
unchanged, so no STOP can be lost by it. The union stays (it adds person detections where they do not merge).
Hard rows and reporting as A6.

### A8 (21.10, after the A7 replays at `50bfc0c`; in-sample)

`50bfc0c`:
* GO with the person inside clear and monitored is **0** at all 6 start frames (v1.2.0: 0 / 0 / 0 / 0 / 0 / 1).
* First person STOP 150.4–150.5 m at every start. Held STOP 129.4–135.5 m (v1.2.0 114.4–123.0; `0eb4dda` 127.4–130.2).
* Whole recording: 13 STOP episodes, 0 without a person, no v1.2.0 person-STOP frame lost.
* The start at 1800 has 1 false episode (frames 2704–2705): a STOP detection at 152–156 m, 0.95–1.5 m left of
  the track reference (the left wall, which the near hypothesis places at the corridor centre; or the person
  merged with it).

The A7 trace showed the mechanism: beyond `far.valid`, the near-hypothesis points (here the left wall) and the
far-hypothesis points (the person) are clustered together. The person is then lost in a 10 m wall blob, or the
wall is reported.

Change (`farrange.axis_union_separate`, on with `axis_union_beyond`): the corridor candidates beyond `far.valid`
that kept the near model's lateral are clustered on their own. Everything else is clustered together as before:
everything up to far.valid, and the points the union gave the far line. So an object seen in one hypothesis is
not merged with structures seen only in the other. Hard rows and reporting as A6. If this costs a v1.2.0 STOP
(H2) or adds false episodes beyond the bound, it is switched off and A7 is the final state.

**A8 result (`fdea950`, measured, switched off):**
* Whole recording: 13 episodes, 0 false (= A7).
* Held STOP at the 6 starts: 129.4 / 135.4 / 135.0 / 129.4 / 135.5 / 132.2 m (= A7).
* First STOP: 150.5–157.5 m (A7: 150.4–150.5).
* **False episodes 0 / 1 / 1 / 1 / 0 / 1** (A7: 0 / 0 / 0 / 1 / 0 / 0).

No held-STOP gain, more false episodes: `axis_union_separate` is **off** (class default False) and the final
detector behaves as A7. The final full replay is compared row by row with the A7 replay to confirm it.

### A9 (21.10, after the review scenes on `73421f6`; in-sample)

`73421f6` (= A7 behaviour; its full replay is row-identical to the A7 replay) on the review's 82 scenes:
* 0 lost or delayed STOPs; false episodes 141 → 81 (added only in `curve_all_xc150_R300_d+1` +1 and the
  non-physical `row_offset_+0.8` +2, as the review's F4).
* GO with the target inside clear: v1.2.0 92, candidate 63 frames. In no scene is the candidate's count above
  v1.2.0's.
* Per frame (`scripts/scene_go_frames.py`), **1** frame is the candidate's alone: `row_step_0.45_from150` frame
  2730. There the far trust grew 142 → 146 → 154 m in three frames, and the reported clear (154.0 m) ran 0.26 m
  past the person at 153.7 m before the detector had a frame to see them.
* The other 62 are v1.2.0's own frames (near-model false clear where the far axis does not form: curves,
  turnouts, the scrolled moving scenes). The Falcon clear-distance model is another lane's; I report them.

Change (`farrange.axis_report_lag_frames` = 3): the reported monitored / clear range covers the far line's
stretch only as far as it has been trusted in each of the last 3 frames (a frame without a far line counts as
no far trust; the near model's own range is not lagged, as v1.2.0). Detection and trust are unchanged.
Re-measured on the final commit: everything in A6's list.

**H1 as written** ("0 on the review's scenes") cannot pass by this lane's change alone: the 62 inherited v1.2.0
frames remain. It is reported per frame. The criterion this lane can meet, and reports as H1':
no GO-with-target-inside-clear frame that v1.2.0 does not also have.
