# K1 / K2 gauge stability and curve synchronisation: acceptance protocol (pre-registered)

> Written and committed **before any candidate acceptance measurement** (19.10, P3 lane). Exploratory
> development runs on the development recordings were made while designing the change (B6 track
> metrics only, listed in §5); none of the numbers below was measured on the frozen candidate before
> this commit. G3 (held-out) is not touched.

## 1. What is measured

| tree | what | how built |
|---|---|---|
| **base** | `aec88d2` (merged 1.2.0 candidate, `detector_freeze verify` PASS, digest `68dee667…`) | `git worktree add /opt/base aec88d2`, `scripts/build_native.sh` |
| **off** | this branch, switches at their committed defaults (off) | the branch commit that carries this file |
| **cand** | the same commit with the two switches on (nothing else changed) | `/opt/cand` worktree of that commit, `configs/default.yaml` **and** `ros2_ws/src/resense_ros/config/detector.yaml` with `track.axis_joint_fit: true`, `track.walls_smoothing_distance: 1.5` |

Code under test: commit `4068f0d` (v1; superseded, see §6 and §7: the candidate is v3 = `83c8894`) (`resense/track.py` `joint_axis_fit` and its use in `estimate_track`;
`resense/detector.py` `_travel`; `TrackModel.curv_step / curv_knot / bent`; native kernels skipped only when
`bent`; `gauge.py` / `health.py` one-line native guards; `scripts/gauge_stability.py` records the step).
All other parameters at the committed defaults (`axis_joint_knot` 60, `axis_joint_step_sigma` 1e-3,
`axis_joint_tolerance` 0.3, rails / walls sigma 0.03 / 0.10, grow 40 + 16 m, `walls_smoothing_min_k` 0.05,
`walls_smoothing_standstill_speed` 1.0). If the code changes after this commit, everything below is re-run.

Environment: `RESENSE_REPO=<tree> PYTHONPATH=<tree>:<tree>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell
OMP_NUM_THREADS=1`, Python 3.12 venv, numpy 1.26.4, scipy 1.11.4, scikit-learn 1.4.2, rosbags 0.11.5, native built.

## 2. Switch-off identity (required regardless of the outcome)

* **off** vs **base**: full regression gate JSON identical in every per-recording / per-object row except
  commit, config hash, date and latency; B6 `track` rows identical (centre, yaw, curvature, axis range,
  decision, mount) on all ten recordings; X3 nominal rows identical.
* Instrumentation: the capture / wrapper runs (`/opt/work/capture.py`, Falcon wrapper) must give the same
  decisions and track rows as the plain runs.

## 3. Acceptance (exact numbers; PASS needs every primary row)

Range probes: `tools/prebuild_range.py` (the 16.10 J1 harness; its `range_test.py` differs from the judge's
only in carrying the curvature step into the object placement, rows unchanged for a quadratic axis; the
object follows each tree's **own** object-free axis as in the judge's method). ICP: `icp_odometry.py` on the
decoded caches (`/data/x1/icp`). "first / held" = `first_stop_X` / `held_from_X`.

| # | card | metric | base (to be measured) | PASS if |
|---|---|---|---|---|
| K2-1 | K2 | wall-referenced axis error on C (`roundT_pressureGate_roundT`), frames 57–117, X = 80, 90, 100, 110, 120 m: per X the median over frames of \|axis(X) − wall-referenced track(X)\| | (1.0–2.4 m at 100 m in round 3) | every per-X median ≤ 0.5 m |
| K2-2 | K2 | C person (`--obj 0.5,0.5,1.75 --start 0 --d0 230`) first / held | 82.8 / 91.6 (1.1.0) | first ≥ 110 m and held ≥ 100 m |
| K2-3 | K2 | B person (`roundT_doubleT --start 50`) first; STOP share of visible frames at 60–100 m | 51.8 m; 0/23 | first ≥ 90 m and 60–100 m ≥ 80 % |
| K2-4 | K2 | A person (`roundT_squareT… --start 150 --d0 230 --end 340`) first / held | 218.4 / 221.8 | first ≥ 218.0 and held ≥ 221.0 |
| K2-5 | K2 | ride STOP episodes with onset within ±5 frames of 6867, 7859, 7868, 3753 (gate ride run, global frame index; base must show them — positive control) | 4 | ≤ 1; and no STOP in ride frames 4720–4729 |
| B6-1 | K2 | B6 honesty per recording (`gauge_stability.py honesty`, reported = probe `monitored`): share of the reported range > 1.05 m off the driven path | 40 % roundT_doubleT, 40 % synthetic_platform | ≤ 5 % on all ten |
| B6-2 | K2 | roundT_doubleT off-track p50 in the 80–100 m bin within the trusted range | 1.78 | ≤ 0.5 m |
| B6-3 | K1/K2 | trusted-range blinks per recording | base per recording | ≤ base on every recording |
| K1-1 | K1 | standing person at 100 m (`S_person_100`) STOP frames | 82/260 | ≥ 200/260 |
| K1-2 | K1 | standing person at 150 m (`S_person_150`) STOP frames | 90/259 | ≥ 150/259 |
| K1-3 | K1 | `probe.py` on squareT_platform_squareT_switch: false-STOP episodes (STOP episodes; no object in this recording) | 3 | ≤ 1 |
| K1-4 | K1 | doubleT_obstacle `probe.py` STOP frames | 193 | = 193 (not fewer) |
| F-1 | Falcon | person STOP frames of the full Falcon stream (frames of the 1,360 true person STOPs of `falcon_full_v110.jsonl`, i.e. STOP frames from bag time 297 s on minus the 8 frames at 9.4 m) | 1,360 | every one still STOP |
| G-1 | clean | `scripts/regression_gate.py --cache /data/cache --jobs 3 --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json` | exit 0 (b4 record) | exit 0 without `--allow` |
| G-2 | clean | X3 battery `scripts/robustness_battery.py` against the base battery as `--reference` | — | exit 0 (PASS) |

B6-1 / B6-2 / B6-3 are evaluated with **two truths** and both are reported. **Primary: the validity-filtered
driven path** (`posesV_*`: every ICP step with forward motion < −0.05 m becomes a segment break). Reason,
found and checked before this protocol (CLAUDE.md rule 5): on `roundT_doubleT` the composed ICP moves the
train **backwards** 0.6–0.8 m per frame in frames 1–57 and forwards 1.6 m per frame afterwards; the
detector's independent texture speed estimate says 15 m/s forward at frames 36 and 54 — ICP aliases on the
tunnel rings there. 57 steps on roundT_doubleT, 17 on doubleT_platform, 11 on squareT_platform, 4 on
synthetic_platform, 2 on synthetic_tunnels become breaks; none elsewhere. **Secondary: the original B6
poses** (as the backlog numbers were measured).

Reported, not gated: B6 trusted-range p50, flicker (motion-compensated p90 at 40/80/120 m), off-track per bin;
Falcon trusted-range frame-to-frame change (share of frames with |Δ axis range| ≥ 20 m, p90) and the 115 m
static false-STOP frames before/after; the 0.5 m cube probes (S_cube05_100 ≥ 150/260, S_cube05_60 ≥ 255 are
the backlog's secondary K1 targets); every other range-probe job (no first-STOP loss > 2 m is expected);
GaugeDisplay (`docs/evidence/n1_n4_2026-10-18/replay_gauge.py`) drawn range on roundT_doubleT and jitter at
40/80/120 m against N1's limits 0.05/0.08/0.15 m; per-frame latency.

## 4. Decision rule

* Every primary row PASS, identity (§2) holds, independent review finds no blocking defect → recommend
  **ship on** (P1 flips the two switches and reseals).
* Identity holds and the change is safe (no lost true STOP, gate exit 0) but some rows FAIL → **ship off**
  (switches committed off) with the failures listed, or **do not ship** if the code itself is a risk.
* Partial switches (K1 only, K2 only) are measured only as attribution of the combined candidate, on the
  cheap rows (B6, S/A/B/C probes); they are not separately accepted.

## 5. Exploration done before this commit (development data only)

B6 `track` + `measure` (both truths) on the nine moving recordings for successive drafts (`/data/res/exp/*`),
single-frame offline fits on captured wall observations (`/opt/work/joint.py`, `pw.py`, `seg.py`). Draft
changes driven by those runs: the joint fit itself, the segment rule, the parallel test in the rail range,
the straight test as a bend at 150 m, its hysteresis, the reach floor (own-side fit reach), the inner-wall far
support for the disagreement. No range probe, gate, X3, ride or Falcon run was made on any draft.

## 6. Revision 1 (19.10, ~12:10 UTC) — candidate v1 failed, v2 is the candidate; criteria unchanged

Measured on v1 (`97d55f1` + switches) before this revision, as the protocol required: B6 (all ten), the
wall-referenced error K2-1, `probe.py` on squareT_platform and doubleT_obstacle, the Falcon stream, part of
the range probes. **v1 fails K1-3 badly**: squareT_platform 319 STOP frames in 14 episodes on a static
structure at 147.45 m during the standstill (base: 11 frames, 3 episodes). Raw top view (frame 450): the right
wall runs straight to 170 m, both axes bend left, v1's less; the structure (y ≈ +1.5 m) is outside the gauge of a
straight track. Cause: far boundary segments joined the joint fit without a consistency test and the curvature
was extrapolated beyond the walls' reach. These v1 results are kept and reported as v1.

v2 = commit `f07f5dd`: during the outward growth a segment's remaining bins (or a new segment) join only as
a group whose refit keeps every used bin within `axis_joint_tolerance` and the rail midpoints within 3 SD.
Development checks of v2 before this revision (development data, the same recordings): squareT_platform
`probe.py` 15 STOP frames, 1 episode; B6 `track`/`measure` on the nine moving recordings. Everything in §2–§3
is re-run on v2 (`/opt/off2`, `/opt/cand2` = `f07f5dd`, the latter with the same two switches on). The
acceptance numbers, truths and decision rule are unchanged. A failure that remains is reported as a failure.

Measurement incident (instrumentation): installing matplotlib at 11:54:52 UTC upgraded numpy to 2.5.4 for
14 s (11:54:52–11:55:06). Every process that started in that window (v1 range-cand baseline, base X3, off B6
tracks) was killed and its output deleted; numpy 1.26.4 restored and asserted at the start of every later lane.
Runs before the window (base gate, base range probes, base/cand B6, Falcon) are unaffected. Plotting uses a
separate virtualenv (`/opt/plotvenv`).

## 7. Revision 2 (19.10, ~13:00 UTC) — independent review of v2, v3 is the candidate

A fresh subagent reviewed v2 code and these criteria (`REVIEW.md`): code "OK with fixes" (switches off), two
findings blocking a default-on, criteria "issues". v2 measurements were stopped before completion; none is used.

**v3 = commit `83c8894`** fixes findings 1–7 (initial fit held to the consistency test; reach against the final
axis; one-wall cap; |step| < 1e-7 is none; rotation range; non-finite inputs; K1 off during warm-up and the
standstill rule at most 60 s in a row). Development checks of v3 before this revision: `probe.py`
squareT_platform 0 STOP episodes; B6 `track`/`measure` on the nine moving recordings. Trees: `/opt/off3`,
`/opt/cand3` = `83c8894` (cand3 with the two switches on). Everything in §2–§3 is re-run on v3.

Changes to the measurement (review C1, C3, C4, C6, C7); thresholds unchanged:
* **C1**: `scripts/gate_identity.py` excludes only the metadata prefixes `created`, `code.`, `config.`,
  `native.`, `run.`, `latency_ms.`, `gate.baseline_`; health-level counts are listed separately (they follow the
  wall-clock latency budget); per-frame files are compared without `timing_ms`, health latency fields / messages,
  and the health level only where either record carries a latency message. Off-identity = 0 differing rows and
  0 differing frames.
* **C3**: added row **K1-5** (backlog K1): an object appearing on the standing background —
  `range_test.py` on squareT_platform `--obj 0.5,0.5,1.75 --start 450 --d0 100 --end 620 --appear 100` (the
  person appears at frame 450 at 100 m after 90 standing frames): PASS if the first STOP comes within 5 frames
  (0.5 s) of its appearance. Also reported (backlog K1, not gated here): `S_cube05_100` ≥ 150/260,
  `S_cube05_60`/`S_person_60` ≥ 255; X3 per variant: squareT ≤ 3 STOP episodes, roundT_squareT 0.
* **C4**: K2-1 reference = `true_axis_all.py` (round 3, `investigate_curve/`) on the base run, side +1 (the
  outer, left wall; the right wall reaches 61 m only), frames 57–117, every frame with a reference (61 of 61 on
  base); the script asserts the mount rotation equals the base run's in every frame of the window. The reference
  is wall-based (not independent of the candidate's input); the independent check is B6 against the driven path.
* **C6**: B6-1 is over the nine recordings with a driven path (doubleT_obstacle: the train stands). "Blink" is
  `gauge_stability.py measure`'s definition: the trusted range (capped at `gauge.range_max`) falls to at most half
  in one frame and comes back to ≥ 90 % of the previous value within 10 frames.
* **C2** acknowledged: K1-3 (squareT_platform) was used to diagnose v1 and to check v2/v3; it is reported as a
  development-informed result, not as an independent pre-registered test.
