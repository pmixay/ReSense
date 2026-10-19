# K1 / K2: gauge stability and curve synchronisation — P3 report (19.10)

> **Handoff (19.10): see [`HANDOFF.md`](HANDOFF.md) for the stopped v4 (partial results, commands, data).**
> Branch `det/k1-k2-gauge`. Final candidate code **v3 = `83c8894`** (two switches, **both off by default**).
> Evidence: this folder (`results/`; raw per-frame data `results/raw_v3.tar.xz`, checksums `SHA256SUMS`). Protocol pre-registered in [`PROTOCOL.md`](PROTOCOL.md) before any candidate
> measurement, with two dated revisions (§6 v1 failed; §7 independent review → v3). Reviews:
> [`REVIEW.md`](REVIEW.md) (v2, fresh subagent), [`REVIEW_v3.md`](REVIEW_v3.md) (v3 fixes, a second fresh subagent).
> Development data only; G3 not touched. No version, seal, README, CHANGELOG, BACKLOG or other shared doc changed.

## Recommendation for the captain

**Ship OFF** (merge the code with both switches at their committed defaults: off ⇒ every output identical to
`aec88d2`, proven below). **Do not turn the switches on for 23.10**: the candidate fails the full regression gate
(far first-detection range on straight track, set F; one more ride event; set O `small_center` −2 STOP frames)
and 10 of the 17 primary acceptance rows (incl. X3). The change is a large step on what the experts named — the gauge now
follows curves (curve axis error at 80–120 m down 2–7×), the standing-train STOP at 100 m goes from 82 to 255 of
260 frames, false STOPs on the empty recordings fall from 12 episodes to 1, and the Falcon 115 m static false
STOP disappears — but it buys that with ~50 m of trusted range on straight track. One identified follow-up
(below) addresses exactly that loss; it is untested.

## What was changed (files and switches)

| switch (`track.*`, default) | card | what it does | code |
|---|---|---|---|
| `axis_joint_fit` (false) + `axis_joint_*` (knot 60 m, step σ 1e-3, rail / wall σ 0.03 / 0.10 m, tolerance 0.3 m, growth 40 + 16 m, min segment 3, min far bins 4) | K2 | One least-squares fit of the near rail-pair slab midpoints and every tunnel-boundary segment (each its own offset) for tangent, curvature and a curvature step beyond 60 m (C1 piecewise axis). Grown outward; a bin joins within 0.3 m, a segment or remaining group only when the refit keeps every bin within 0.3 m and the rail midpoints within 3 σ; the start is held to the same test. Trusted reach measured against the final axis; straight test = same bend at 150 m as \|k\| < 1e-4 (with hysteresis); a side without far bins neither disagrees nor counts as a second wall | `resense/track.py` `joint_axis_fit`, `_followed_reach`, `estimate_track`; `TrackModel.curv_step / curv_knot / bent` |
| `walls_smoothing_distance` (0 = off; candidate 1.5 m) + `walls_smoothing_min_k` 0.05, `walls_smoothing_standstill_speed` 1.0 m/s, `walls_smoothing_standstill_max` 60 s | K1 | Axis yaw / curvature EMA exponent and rate limits per distance travelled (previous frame's speed × dt / 1.5 m, between 0.05 and the frame periods); a texture profile without any change after a crawl counts as standing (≤ 60 s in a row); not during warm-up | `resense/track.py` `estimate_track(travel=…)`, `resense/detector.py` `_travel` |

Supporting changes: native kernels are skipped only when the axis has a step (`track.py`, one-line guards in
`gauge.py`, `health.py`); `rotate_track_model` keeps the step; `scripts/gauge_stability.py` records the step when
present (rows unchanged otherwise). Tests: `tests/test_k1_k2_axis.py` (14; the review-driven ones fail on v2).

### Root cause found (K2)

The rail tangent was a line through the 8–26 m slab midpoints **with the prior curvature held fixed**; with a prior
that is too straight it is the tangent at ~17 m (roundT_doubleT frames 124–164: rails −0.057, driven path −0.028).
The walls were then fitted with that tangent fixed, which pulls the curvature back towards the prior (2–4× too
small, self-sustaining) and makes the two walls "disagree" (the 60 m `axis_disagree_range` cap on double track).
A quadratic additionally cannot follow a transition (C: flat to ~60 m, then bending). The joint fit removes the
coupling; the step handles the transition.

## Before / after: every acceptance row (v3, PROTOCOL §3 + revision 2)

Base = `aec88d2`, cand = v3 with both switches on. Primary B6 truth = validity-filtered driven path (§3).

| # | metric | base | cand v3 | criterion | |
|---|---|---|---|---|---|
| K2-1 | C wall-referenced axis error, median at 80/90/100/110/120 m (frames 57–117, 61/61 frames) | 0.72 / 1.03 / 1.39 / 1.90 / 3.43 | 0.40 / 0.47 / 0.51 / 0.52 / 0.56 | each ≤ 0.5 | **FAIL** (100–120 m) |
| K2-2 | C person first / held | 82.8 / 91.6 | 112.4 / 69.5 | ≥ 110 / ≥ 100 | **FAIL** (held) |
| K2-3 | B person first; 60–100 m STOP | 51.8; 0/23 | 72.9; 8/13 (62 %) | ≥ 90; ≥ 80 % | **FAIL** |
| K2-4 | A person first / held | 218.4 / 221.8 | 165.2 / 179.6 | ≥ 218 / ≥ 221 | **FAIL** |
| K2-5 | ride curve-edge episodes (onset ±5 of 3753/6867/7859/7868); STOP in 4720–4729 | 2 (7859, 7868); none | 1 (7859); none | ≤ 1; none | PASS (positive control partial, see checks) |
| B6-1 | share of reported range > 1.05 m off, worst recordings (9 with a path) | roundT_doubleT 30.8 %, synthetic_platform 20.5 %, synthetic_tunnels 13.4 %, roundT_squareT 9.3 % | 11.2 %, 12.9 %, 6.2 %, 8.9 % | ≤ 5 % on all | **FAIL** (4 recordings) |
| B6-2 | roundT_doubleT off-track p50, 80–100 m | 1.70 m | 0.498 m | ≤ 0.5 | PASS (by 2 mm; original truth 1.78 → 0.69: fail) |
| B6-3 | trusted-range blinks per recording | see B6 table | ≤ base on 9, squareT_platform 4 → 7 | ≤ base everywhere | **FAIL** (1 recording) |
| K1-1 | standing person 100 m STOP | 82/260 | **255/260** | ≥ 200 | PASS |
| K1-2 | standing person 150 m STOP | 90/259 | 78/260 | ≥ 150 | **FAIL** |
| K1-3 | squareT_platform false-STOP episodes (`probe.py`) | 3 | 0 | ≤ 1 | PASS (development-informed, review C2) |
| K1-4 | doubleT_obstacle STOP frames (`probe.py`) | 193 | 188 | = 193 | **FAIL** (first STOP 5 frames later, see below) |
| K1-5 | person appearing at 100 m on the standing background: frames to first STOP | 28 | **5** | ≤ 5 | PASS |
| F-1 | Falcon: every one of the 1,360 reference person STOP frames still STOP | 1,360 | 1,353 (7 lost: 2972–2975, 3037–3038, 4380) | all | **FAIL** |
| G-1 | full regression gate vs `regression_baseline_2026-09-29_shell_off.json`, no `--allow` | exit 0 | exit 1, 12 gated rows worse | exit 0 | **FAIL** |
| G-2 | X3 battery vs base battery (`results/x3_*.json`) | MEASURED | FAIL: 13 of 260 comparisons | PASS | **FAIL** |
| ID | switch-off identity (gate, B6, all ten) | — | 0 differing rows / frames | identical | PASS |

Secondary (backlog, reported): S_cube05_100 94 → 36/260 (backlog ≥ 150: fail); S_cube05_60 and S_person_60
255 → 255; S_person_150 above. Other probes: A_cube1 151.1 → 161.7 first; C_cube1 85.7 → 110.9 first;
C_cube05 75.4 → 84.3; B_cube1 50.0 → 72.9; D_person held — → 118.6 m (STOP 165 → 194/320);
E6 low cable first 59.8 → 162.9 (held 43.4 → 56.8); E5 centre pole 218.4 → 165.2; A_cube03 44.9 → 43.4.
Full table: `results/range/summary_*.json`.

### Gate (G-1) in detail (`results/gate/`)

| | base | cand v3 |
|---|---|---|
| five empty recordings: alarm events / STOP episodes / alarm frames | 8 / 12 / 39 | **1 / 1 / 6** |
| squareT_platform_squareT_switch events / episodes | 7 / 11 | 0 / 0 |
| ride alarm events / STOP episodes / alarm frames / CAUTION frames | 27 / 30 / 126 / 4,766 | **28** / 25 / 111 / 3,137 |
| doubleT_obstacle labelled hits (person / object on rail / from frame 75), first alarm frame | 61 / 129 / 126, frame 8 | 61 / 143 / 126, frame 8 |
| set O: `small_center` STOP frames, first STOP | 32, 55.8 m | **30, 52.5 m** |
| set O: `small_edge_inside` first STOP; `big_outside` false STOP frames | 35.0 m; 6 | 46.1 m; 0 |
| set F straight first-detection median: person / box 1.0 / trolley / cable | 151.0 / 123.9 / 151.4 / 98.9 | **147.4 / 111.2 / 117.2 / 92.0** |
| set F trolley false detections | 5 | **6** |

The far losses come from the trusted range on straight track: ride frames with a trusted range ≥ 180 m fall
from 23 % to 14 % (median 139 → 135 m). On straight `roundT_squareT…` the curvature-step estimate carries
±2e-4 noise from the sparse far wall bins, which bends the far axis by up to 0.8 m at 150 m; the reach measured
against that axis then ends near 100 m where the base (quadratic, +50 m straight bonus) trusted 156 m.

## Moving objects (post-hoc, added 19.10 13:25 after the coordinator's note that objects may move; not pre-registered)

Already in the measured range run and the gate (same trees, nothing re-run):

| probe | base first STOP / STOP frames | cand v3 |
|---|---|---|
| E1 person crossing at 150 m (`--vy 1.0`) | 129.6 m / 20 of 96 | 129.6 m / 22 of 92 |
| E2 person crossing at 80 m (`--vy 1.0`) | 53.3 m / 26 of 60 | **50.8 m / 23 of 60** (worse) |
| E3 object receding 5 / 8 m/s | 97.1 / 96.2 m; 101 / 101 frames | same; 104 / 101 frames |
| E4 object appearing at 60 / 100 m | 53.8 / 92.0 m | same |
| doubleT_obstacle real person crossing (gate labelled hits; `probe.py` STOP frames) | 61; 193 | 61; **188** (first STOP 5 frames later) |
| K1-5 person appearing on the standing background | 28 frames to STOP | 5 frames |

The K1 logic smooths only the *axis* by the train's own travel; no object or track logic assumes a static
object. Still, the two crossing persons lose STOP frames (E2 −3, doubleT −5) at the gauge edge: one more reason
not to switch on.

## X3 robustness battery (G-2; 4 recordings × 10 variants, against the base battery)

**FAIL**, 13 of 260 comparisons, all of the "fewer STOP frames on a positive" or "more outside false STOPs" kind:
doubleT_obstacle person crossing −5 (nominal), −4 (roll +2°), −3 (dropout s2) STOP rows (tolerance 2; the
gauge-edge crossing above); set O positive STOP frames −5 / −6 / −8 under 30 % dropout, `big_center` −4
(pitch −2°), `small_center` −4 (5 Hz), `long_low_on_rails` −6 (dropout s3); `big_outside` 0 → 2 outside
false-STOP episodes (dropout judge7); roundT_squareT pitch +2° 0 → 1 false-STOP episode (backlog: 0).
On the other side, squareT_platform false-STOP episodes fall to **0 in every variant** (base: nominal 3,
pitch +2° 4, pitch −2° 7, roll 7, 5 Hz 9, dropout 10–14, dedup 3) — the backlog's K1 X3 target (≤ 3 each) is
met there.

## B6 before / after (v3; `results/b6/b6_table_v3.json`, both truths)

Off-track = axis lateral against the driven path, median within the trusted range; honesty = share of the
reported range > 1.05 m off. Primary truth (validity-filtered) first, original in brackets where different.

| recording | trusted range p50 | blinks | flicker p90 40/80/120 m | off-track 90 m | off-track 135 m | honesty > 1.05 m |
|---|---|---|---|---|---|---|
| doubleT_obstacle (stands) | 151 → 127 | 0 → 0 | .015/.043/.092 → .012/.046/.097 | – | – | – |
| doubleT_platform | 120 → 120 | 22 → 17 | .085/.204/.455 → .084/.247/.441 | 0.07 → 0.08 (0.17 → 0.09) | 0.11 → 0.28 | 0.0 → 0.0 % (8.6 → 0.3 %) |
| roundT_doubleT | 157 → 135 | 1 → 1 | .097/.269/.483 → .066/.225/.629 | **1.70 → 0.50** (1.78 → 0.69) | **6.81 → 1.97** (7.42 → 6.43) | **30.8 → 11.2 %** (40.1 → 26.1 %) |
| roundT_pressureGate_roundT | 143 → 139 | 5 → 1 | .038/.146/.376 → .032/.119/.299 | **0.31 → 0.09** | **1.58 → 0.79** | 2.2 → 2.4 % |
| roundT_squareT_pressureGate_squareT | 175 → 151 | 1 → 1 | .038/.167/.388 → .028/.134/.359 | 0.15 → 0.12 | 0.28 → 0.24 | 9.3 → 8.9 % |
| squareT_platform_squareT_switch | 151 → 120 | **4 → 7** | .029/.075/.148 → .020/.066/.208 | **0.65 → 0.14** | 2.76 → 1.97 | 7.5 → 2.5 % (11.7 → 7.0 %) |
| cloud_with_fake_obj (Set O) | 155 → 151 | 4 → 3 | .036/.130/.301 → .026/.116/.295 | 0.11 → 0.11 | 0.15 → 0.27 | 1.6 → 1.2 % |
| synthetic_platform | 120 → 115 | 5 → 3 | .038/.078/.208 → .041/.080/.244 | 1.04 → 0.98 (1.46 → 1.44) | 2.76 → 2.13 | 20.5 → 12.9 % (40.4 → 36.3 %) |
| synthetic_switch | 147 → 135 | 11 → 8 | .034/.099/.227 → .023/.067/.190 | 0.18 → 0.15 | 0.54 → 0.18 | 3.5 → 1.2 % |
| synthetic_tunnels | 139 → 139 | 8 → 7 | .087/.259/.506 → .039/.148/.475 | 0.37 → 0.21 | **2.87 → 0.59** | 13.4 → 6.2 % |

Reading: the axis now follows curves and transitions (roundT_doubleT 90 m 1.70 → 0.50 m, 135 m 6.8 → 2.0 m;
C 1.58 → 0.79 m at 135 m; synthetic_tunnels 2.87 → 0.59 m), flicker falls at 40/80 m nearly everywhere, the
trusted range blinks less on 6 recordings and more on squareT_platform (switch area, frames 750–800: the
disagreement cap toggling 60 ↔ 120 m between one and two fitted walls). Platforms remain the weak case
(synthetic_platform 1 m off at 90 m before and after; doubleT_platform 135 m worse).

## Falcon (full stream, 4,443 / 4,443 messages, 0 lost; `results/falcon/compare_v3.json`)

| | base | cand v3 | (v1, superseded) |
|---|---|---|---|
| decisions GO / CAUTION / STOP | 8 / 3,062 / 1,372 | 561 / 2,479 / 1,402 | 545 / 2,246 / 1,651 |
| 115 m static false STOP frames | 4 (159, 2312–2314) | **0** | 0 |
| person STOP frames matching the raw-reviewed trajectory (`atlas_proposals.json`, ±3 m) | 1,337 | 1,358 | 1,639 |
| first person STOP | 124.8 m (frame 2972) | 122.5 m (2992) | **164.9 m (2639)** |
| reference person STOP frames lost (F-1) | 0 | 7 | 1 |
| non-person STOP frames | 35 (115 m ×4, 101 m ×1, floor 7–12 m ×30) | 44 (floor 3–23 m, frames 4278–4411, after the person passed) | 12 |
| trusted range p10 / p50 / p90 | 107 / 123 / 167 | 111 / 123 / 131 | 119 / 167 / 175 |
| frames whose trusted range changes ≥ 20 m from the previous frame; p90 of the change | 34.3 %; 48 m | **16.2 %; 32 m** | 37.3 %; 56 m |

The CAUTION share of the standing first four minutes falls (the static 105.6 / 115 m warnings now sit outside the
corrected gauge: GO frames 8 → 561). The end of the recording (the person in the near blind zone, rails lost)
produces floor-level false STOPs on both trees at different distances (base 9.4 m, v3 ≈ 22 m).

## Display (shipped GaugeDisplay, unchanged; `results/display_summary.json`)

| recording | drawn range p50 / p90, base → v3 | displayed 3D edge step p90 at 40 / 80 / 120 m, v3 (pairs) | N1 limits 0.05 / 0.08 / 0.15 |
|---|---|---|---|
| roundT_doubleT (curve) | 52 / 102 → 51 / 94 m | 0.031 / 0.043 / – (152 / 46 / 0) | within at 40 / 80; 120 m never drawn |
| roundT_pressureGate_roundT (curve entry) | 45 / 98 → 43 / 89 m | 0.037 / 0.030 / – (152 / 34 / 0) | within; 120 m never drawn |
| cloud_with_fake_obj | 86 / 134 → 85 / 131 m | 0.017 / 0.031 / 0.040 | within |
| doubleT_platform | 45 / 120 → 53 / 85 m | 0.017 / 0.019 / – | within; 120 m never drawn |
| Falcon (streamed; lateral step only) | 102 / 119 → 111 / 123 m | 0.002 / 0.003 / 0.024 (4311 / 4107 / 472) | within |

The display draws the candidate's bent axis (it uses `center_y`); its drawn range on the curve barely changes
because N1 limits drawing by its own lag rules. Base reproduces N1's committed 52 m median on roundT_doubleT.

## What was checked, and how (CLAUDE.md)

* **Truth validity (rule 5):** the B6 ICP poses move the train **backwards** 0.6–0.8 m/frame in roundT_doubleT
  frames 1–57 (then +1.6 m/frame); the detector's independent texture speed says +15 m/s at frames 36 and 54.
  ICP aliases on the tunnel rings. 57 (roundT_doubleT), 17 (doubleT_platform), 11 (squareT_platform), 4 and 2
  steps become segment breaks in the primary truth; both truths are reported. This inflated the B6 baseline
  (roundT_doubleT 90 m 1.78 → 1.70 m, honesty 40 → 31 % on the base itself).
* **Root cause re-derived three ways:** rails' tangent vs driven-path tangent (−0.057 vs −0.028), single-frame
  offline fits on captured wall observations (`/opt/work/joint.py`, `seg.py`), and closed-loop B6.
* **Positive controls:** K2-1's reference reproduces round 3's base error at 100 m (1.39 → 1.394 m); the gate
  identity checker finds 105 differing rows and every frame differing for base vs candidate; the capture
  instrumentation reproduces the plain run (0 of 201/252/268/345/545/877/1510 rows differ); the Falcon wrapper
  reproduces the committed reference decisions (0 of 4,443 differ); each review-driven test fails on v2;
  base range probes reproduce the 1.1.0 prebuild numbers (A_person 218.38 / 221.78, C_person 82.77 / 91.63).
  The ride episode list (K2-5) found 2 of 4 named onsets on base with ±5 frames (the 6867 episode starts at 6859
  on this tree; 3753 is only a warning) — reported, the criterion was not changed.
* **Switch-off identity:** full gate `off3` vs base: 0 of 425 compared rows differ, 0 frames differ in all
  per-frame files (wall-clock `timing_ms`, health latency fields and latency messages excluded; the health-level
  counts of the ride, which follow the latency budget, listed separately); B6 `track` rows of all ten recordings
  identical (also for v1's off tree). The first identity checker skipped any key containing "platform" or "wall"
  (review C1) and was replaced before the v3 identity run.
* **Looked at the data (rule 4):** top views of squareT_platform frame 450 (`results/sq450_topview.png`: the right
  wall straight to 170 m; the base axis bends 2.4 m left by 147 m (v1 did 1.0 m and STOPped on the 147 m
  structure); the v3 axis runs parallel to the right wall and the structure lies outside its gauge), rail-head
  midpoints of doubleT_obstacle frame 8 (the candidate axis 0.05–0.11 m from the rail midpoints at 27–47 m, the
  base 0.07–0.16 m: both lag, the candidate less — the crossing person stands at the gauge edge in frames 8–12,
  which is why its first STOP moves by 5 frames; crude estimator, supporting only), the Falcon early STOPs against
  the raw-reviewed person trajectory (157.26 vs 157.35 m at frame 2700).
* **Independent review:** two fresh subagents (code + criteria, not these conclusions). v2 (`REVIEW.md`): "code
  OK with fixes (off), two findings block a default-on; criteria: issues". v3 (`REVIEW_v3.md`): **switches off:
  OK** (read + end-to-end on two recordings, positive control); **switches on: OK with fixes** — findings 1, 5, 6
  resolved; 2 (reach can still rest on the raw joint-fit floor, taken before the rate limits), 3 (one-wall cap only
  when the second wall ends ≤ ~54 m), 4 (the step is non-zero on most real frames: native kernels bypassed),
  7 (rate limits 5 % at standstill, speed age) only partly; 8 (web / webapp / node text / one script rebuild
  the axis without the step) open; new N1 (take the reach after the rate limits), N2 (a stop before convergence
  keeps a wrong, far-trusted axis up to 60 s). All of these matter only with the switches on.
* **Measurement incident:** a matplotlib install upgraded numpy to 2.5.4 for 14 s (11:54:52–11:55:06 UTC); every
  process started in the window was killed and its output deleted; later lanes assert numpy 1.26.4 at start.
* **Not checked / unverified:** the ROS node and Docker path with the switches on; the web cab view and webapp
  (they rebuild the axis from centre/yaw/curvature and would draw a different corridor beyond 60 m when on —
  review finding 8, open); latency on an idle machine (gate latency rows are from a shared 4-vCPU run: 360°
  p95 within 59–105 ms on both, doubleT_obstacle mean 43 → 79 ms worth an idle re-measure); the ride with the
  switches on beyond the gate's own rows; G3.

## History (failed attempts kept)

* **v1** (`97d55f1`): failed K1-3 badly — squareT_platform 319 STOP frames in 14 episodes on a static 147.45 m
  structure during the standstill (new boundary segments joined the fit untested; the curvature was extrapolated
  past the walls' reach). v1 also showed the largest gains (Falcon person from 164.9 m; C person held 116.9 m;
  B person 72.9 m). Kept in `results/v1/`.
* **v2** (`f07f5dd`): group admission; reviewed (REVIEW.md); measurement stopped after the review.
* **v3** (`83c8894`): review fixes; the measured candidate.

## Tests

Full suite on the branch (switches off): **1,983 passed**, 7 deselected, 1 failed —
`tests/test_lidar_proxy_hook.py::test_child_process_inherits_hook_and_bad_source_fails_closed`, environmental
(a child process without `PYTHONPATH`); it fails identically on the untouched `aec88d2` worktree.

## What remains / next step (not done)

1. **Keep the base trust-range policy, use the joint fit for the axis shape only** (`axis_valid`, sides, bonus,
   caps from the old per-side fits): expected to recover A / set F range while keeping the corridor accuracy;
   B's 60 m double-track cap would then need the joint-tangent disagreement only. Untested.
2. A stronger prior or minimum far support for the curvature step on straight track (the ±2e-4 noise above).
3. Platforms (synthetic_platform, doubleT_platform at 135 m) are not solved by either version.
4. Web / webapp axis rendering with `curv_step` before any default-on; the open review items N1, N2, 2, 3, 4, 7.
5. Real-obstacle losses at the gauge edge (doubleT_obstacle crossing, set O under dropout) must be understood
   before any default-on, even where the axis itself is the more accurate one.
