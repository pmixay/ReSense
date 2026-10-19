# K1 / K2 review of v3 (`f07f5dd..83c8894`, off-identity vs `aec88d2`)

* **Reviewer:** fresh subagent (did not write the change, had not seen the v2 reviewer's reasoning beyond REVIEW.md),
  19.10.2026. Only this file written; no detector/config/test file touched, no commit, no pip install. Probe scripts
  and outputs are in the reviewer's scratchpad (`.../scratchpad/probes/p1.py p1b.py p2.py p2b.py p3.py p4.py p5.py
  e2e.py`), outside the repo.
* **Read:** CLAUDE.md; REVIEW.md; `git diff f07f5dd 83c8894 -- resense/ configs/ ros2_ws/ tests/` in full; the whole
  of `joint_axis_fit`, `_followed_reach`, `wall_drift_range`, `rotate_track_model`, `estimate_track` (track.py);
  `Detector._travel`, `reset`, `_process_once` call sites (detector.py); `EgoMotion.reset`; PROTOCOL §7;
  `git diff aec88d2 83c8894 -- resense/` (gauge.py, health.py, config.py, detector.py fully; track.py changed lines);
  all `center_coefs()` users; grep for axis rebuilds in web/, webapp/, ros2_ws/, scripts/.
* **Ran:**
  1. Requested pytest (`test_k1_k2_axis test_wall_drift test_rail_axis_extension test_native test_modules`, env as
     instructed): **127 passed** in 6.7 s.
  2. Synthetic probes on v3 and, as positive control, on a `git archive f07f5dd` tree (same native .so) — results below.
  3. End-to-end off-identity: `Detector(default.yaml).process()` on frames 0–249 of `squareT_platform_squareT_switch`
     and `roundT_pressureGate_roundT` (cache `.npy`, stamp = 0.1·k), base = `git archive aec88d2` + same .so, vs this
     checkout off, vs this checkout ON (`axis_joint_fit` true, `walls_smoothing_distance` 1.5); timing/latency/cpu
     keys stripped. **Off vs base: 0 differing frames on roundT (250/250 equal); 14 differing frames on squareT, all
     `health.messages` "latency p95 … ms" text and `health.level` ok→warn in frames 10–23 only** (wall-clock latency
     with three runs in parallel; no other field differs). Positive control: ON differs from base in 250/250 frames of
     both recordings (and in decisions: squareT warnings 38→53; roundT STOP frames 2→0, warnings 99→84 — not
     evaluated here, the protocol measures that). Native enabled in all runs. Scope: 2×250 frames, not the gate/X3/node.

## Findings 1–7 of REVIEW.md

| # | status | evidence |
|---|---|---|
| 1 initial fit unchecked | **resolved** | track.py:733-741: the start set is solved, then the segment with the largest residual is dropped until `consistent()` holds; returns None when none is left. Terminates (one segment removed per pass, empty → `return None` at :738-739). Probe p1 (9 converging-structure layouts × 3 seeds, incl. the v2 reviewer's 28–40 m @0.08–0.2 and 32–44 m @0.08–0.1): v3 \|err@100 m\| ≤ 0.01 m, real wall kept to 120 m in 27/27; **same cases on f07f5dd: 3.4–9.8 m error in 24/27** (positive control). Noise robustness (40 seeds, noise 0.03–0.12 m) equal to f07f5dd (None 0–1/40). Residual (p1b, also on f07, not a regression): a structure converging below `_DRIFT_NEAR_SLOPE` (0.01–0.019 m/m, 8–40 m) with the other wall also ending at 40 m bends k to 3–6e-4 (1.3–2.4 m @100 m, x_max 40). |
| 2 reach = own-fit reach | **partly** | :1290-1293 reach = `max(joint x_max, _followed_reach(final model))`. The `joint x_max` floor is measured against the *raw* joint solution, and the rate limits (:1356-1366) are applied *after* the reach is taken, so the comment "against the final axis … the one the corridor uses" does not hold. Probe p2/p2b (settled straight, then a curve-entry scene, rule 6 checked: hooked run == plain run): axis_valid 225 m while `_followed_reach` vs the final model gives 68/80 m and the corridor axis is 0.9 m off at 100 m and 5.9 m at 160 m; converges in ~12 frames with joint only; **with K1 at standstill (travel 0) still 0.9 m / 5.6 m off after 30 frames with axis_valid 225**. Base (off) is similarly over-trusted in this scene (213 m, 0.66 m @100 m), so not worse than base, but the fix does not do what it says. |
| 3 one-wall | **partly** | :1275 `one_wall = len(far_ok) < 2`, :1320 cap when `joint is not None and one_wall` (short-circuit: `one_wall` is only read when it was assigned — no NameError, but fragile). Probe p3 (straight, second wall ending at X): ON capped to 120 m for X ≤ 50 m (stricter than base 225 m); for X ≥ 58 m (≥ 6 far bins) ON = base = 225 m resting on one wall beyond X. Residual equals base behaviour. |
| 4 always bent | **partly** | :511 `_STEP_ZERO` 1e-7, zeroing at :1285, :1300, :1342. Covers only the "no far data" ridge (~1e-16); the new test truncates the scene at 58 m. Probe p4 (straight scene, walls to 160 m, 4 seeds × 15 frames): **bent in 14–15/15 frames**, step 1e-6–1.2e-5 (0.4–5 cm at 150 m). e2e ON: bent in **165/250** (squareT_platform) and **250/250** (roundT_pressureGate) frames → native kernels still bypassed on most real frames. The reviewer's suggested 1 cm-at-150 m threshold (≈2.5e-6) was not used. |
| 5 rotation range | **resolved** | :1151 samples to `max(x1, 60, knot+100)` when bent. Probe p5 (yaw 0.3°, floor end 55/62/90 m, three shapes): v3 rotated model vs exactly rotated axis ≤ 0.04 m to 250 m; f07f5dd 0.8–599 m at 100 m for floor end 55 m (positive control). |
| 6 non-finite / rank | **resolved (NaN); rank not guarded** | :643-645 rails finite, :658-659 boundary bins filtered, :771 `isfinite(sol)` → None; test `test_review_non_finite_bins_are_ignored`. No `rank < ncols` check (min-norm solution on a degenerate system remains possible; the step column is always regularised, so only c/t/k/offset degeneracy) — note. |
| 7 K1 standstill | **partly** | Done: K1 off while `prev.age < axis_warmup_frames` (:1191-1192); standstill rule at most `walls_smoothing_standstill_max` 60 s in a row (detector.py:429-434). Not done: rate limits still scale with `kr` (:1195, used at :1360/1363) — 5 % at standstill, see p2b K1 row; `ego.last_speed` still has no age limit; no record of which branch fired; a given odometry speed of 0 (or a confident LiDAR 0) holds `min_k` with no time bound. `_still_s` is **not** reset in `Detector.reset()` (detector.py:208-227), but it does not matter: `ego.reset()` sets `last_speed = None` (egomotion.py:154), the first post-reset frame returns before touching it (`self.track is None`, :423), and the next frame has `still` False → `_still_s = 0`. `dt` is the clipped frame dt (nominal on long gaps), so the 60 s is counted in nominal time across pauses — note. No test of the 60 s bound or the warm-up exemption. |

## Finding 8 (consumers ignoring `curv_step`) — **still open**

Not touched by v3 (`git diff f07f5dd 83c8894 -- web webapp scripts` empty). Still rebuilding from (center, yaw,
curvature) only: `webapp/frontend/src/lib/track.ts:68` (centre line), `:73` (heading); `web/index.html:172`, `:233`
(top view / corridor), `:519` (radius text); `ros2_ws/src/resense_ros/resense_ros/detector_node.py:1063` (status R);
`scripts/analyze_residual_events.py:288`. Display/analysis only; decision-path users are fine: every `center_coefs()`
native call in resense/ is guarded by `not bent` (track.py:94-96 via `center_y`, :286-287, :441, :802-803, :925-927;
gauge.py:44; health.py:104); `wall_drift_range` adds `_step_y` (:546-547); `scripts/gauge_stability.py:101` carries the step.

## New findings

| # | severity | where | finding |
|---|---|---|---|
| N1 | should-fix (ON) | track.py:1290-1293 vs :1356-1366 | Reach taken before the rate limits and floored by the raw joint `x_max` (finding 2 row). Fix: compute `reach` after the rate-limit block from `_followed_reach` alone (or min with it), as `wall_drift` already is (:1371-1373). |
| N2 | should-fix (ON, K1) | track.py:1195 | With K1 on, a not-yet-converged axis at a stop is held: p2b shows 0.9 m @100 m / 5.6 m @160 m unchanged over 30 frames with axis_valid 225 m. The combination of N1 and the unscaled-EMA/scaled-rate choice is the v2 finding-7 failure mode; v3's 60 s bound does not shorten it below 60 s. |
| N3 | note | track.py:735-741 | The start-set loop removes segments when the failure is the rails' 3-SD test (rail mids inconsistent with any shape): all segments go, joint None, the base path runs that frame. Safe, but frames can alternate between the joint and base paths; not traced on real data. |
| N4 | note | track.py:1285 + :1366 | The curv_step rate clip runs after the zeroing; with `prev.curv_step` in (r, r+1e-7) it re-creates a step < `_STEP_ZERO` for one frame. Harmless. |
| N5 | note | track.py:1290 | Reach now iterates all `bounds` sides, including a side `_fit_side` rejected (not in `fits`): such a side can set `x_valid` if it runs parallel to the axis. Plausible, but a change of semantics vs f07/base not covered by a test. |
| N6 | note | tests/test_k1_k2_axis.py | No tests for findings 2, 3, 7 (reach vs final axis, one-wall cap, warm-up exemption, 60 s bound); the finding-4 test covers only the no-far-data case. |

## Switch-off identity (aec88d2 → 83c8894, both switches default)

Traced every v3 change for the off path: `_followed_reach`, the start loop, `one_wall` are reached only with
`joint is not None` (never off); the one-side cap condition reduces to base `n_sides == 1` (:1320); rotation range
`max(x1, 60, 0)` = base (:1151; `curv_knot + 100.0 if bent else 0.0` parses as intended); `_STEP_ZERO` branches yield
0.0 where `curv_step` is already 0.0 (:1342); K1 gate needs `walls_smoothing_distance > 0` (:1191), `_travel` returns
None before any state change when it is 0 (detector.py:423-424). Earlier off-path parts (native guards, `to_dict` keys
only when bent, `center_y`) re-checked by reading. End-to-end (Ran 3): identical except wall-clock latency health text.

## Verdict

code (switches off): **OK**
code (switches on): **OK with fixes** — findings 1 and 5 fixed (verified with positive controls); 2, 3, 4, 7 partly
(N1/N2 should be fixed before ON: the trusted range still rests on the raw joint reach while the smoothed /
rate-limited axis lags, held for long at K1 standstill); 6 resolved for NaN; 8 open (display only).
