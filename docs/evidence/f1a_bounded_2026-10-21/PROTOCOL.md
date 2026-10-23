# F1a bounded head top — pre-registered protocol (21 October 2026)

Committed **before any measuring run** (synthetic scenes, recordings, X3, gate). Everything measured after this
commit is reported, including failures. Lane: P3 detector change toward 1.3.0, branch `claude/f1a-bounded-1.3`.
Held-out G3 (`docs/evidence/heldout_2026-10-15`) is not used for anything.

## 1. Defect

The B1 repair (`f07f4b8`, `docs/evidence/f1a_b1_2026-10-20/`) compares a low cluster's **uncapped** footprint top
(returns above the low-stage floor included) with F1a's rail line (median of 0.5 m bin maxima). On the ride the rail
returns are bimodal and the median sits below the head's top surface, so a rail fragment's uncapped top is the
**rail head's own top** and the fragment is reported as an object: chunked ride gate alarm events 18 → 23, STOP
episodes 24 → 26; continuous replay STOP rows 109 → 120, low-kind episodes 1 → 3 (accepted for 1.2.0 as a cost).
The completion that removed the cost (`a77d884`) read the head surface as a ±5 m maximum, which an object's own top,
a 1 cm/m slope or a local rise can supply; it lost 69 of 831 STOP frames in the review's ray-cast scenes and was
reverted (DECISIONS rows 46–47).

## 2. Design (fixed by this commit)

Design set: B1's 250 archived real ride states (`f1a_b1_2026-10-20/raw-evidence.tar.gz`,
`f1a-b1-compact-snapshots`; 111 clusters the pre-repair rule rejected, 45 of them kept by B1). Scripts and outputs:
`design/`. Findings that shaped the rule (`design/variants.txt`, `design/geometry.txt`):

* For the 39 rail-eligible flips the uncapped top lies within −0.02 … +0.03 m of the head's top surface measured as
  the **lowest** of the per-region maxima around the cluster; a ±5 m maximum is not needed.
* The top-surface returns of these fragments are 0–0.085 m wide across the track (one or two azimuth samples on a
  0.07 m head); a 0.3 m object's top face spans its width.
* Medians of bin maxima are 3–6 cm below the head's top (bins without a head crossing), so they cannot serve as
  the head-top estimate.

**Rule** (`resense/lowobj.py`, `rail_head_top` and the branch in `rail_reference_check`; switch
`lowobj.rail_head_bounded`, class default and both YAML copies `false` until §6 is met). A clean low gauge cluster
that the B1 rule keeps is weak low evidence again (as F1a's other rejections: it may continue a reported low STOP,
never start one) only if **all** hold:

1. the low-free mask is in use (`local_rail_exclude_low`, the B1 default; the unsafe ablation keeps the branch off);
2. the **pre-repair** rule rejected it: capped top `height_max` < original line + `local_rail_margin` (so the new
   rejections are a subset of the pre-repair rule's);
3. it is at most `rail_start_max_width` (0.45 m) wide and its lateral extent reaches **exactly one** rail line
   within `rail_start_lateral` (0.10 m);
4. head top `H` = the lowest of four maxima of low-free returns with −0.3 < h < `foot_max_top`, each inside a rail
   band (|dy ∓ spacing/2| ≤ `local_rail_band` 0.10): its **own** rail in [x0 − 5, x0 − 0.3] and [x1 + 0.3, x1 + 5]
   (its own extent and a 0.3 m guard excluded), the **other** rail in [x0 − 5, xc] and [xc, x1 + 5]
   (xc = centre); every region must hold a return, and `H` ≤ `rail_head_max_above_plane` (0.25 m);
5. its uncapped top ≤ `H` + `rail_head_margin` (0.03 m);
6. its top surface (footprint returns within `rail_head_top_band` 0.02 m of the uncapped top) is at most
   `rail_head_max_spread` (0.10 m) wide across the track;
7. no footprint return lies from `foot_max_top` (0.35) up to `rail_head_clear_height` (1.5 m) above the plane.

What the object cannot supply: an object along its own rail raises only the own-rail regions it covers (the other
rail's two regions stay at the real head); a local rise or a stray return raises one region; a slope raises the far
region of each pair only (bias ≤ 0.3 m × slope on the own rail); a one-sided head (only before or only after) leaves
a region at web/foot height (fail-open). An object wider than the head shows a wide top surface (6); a taller one
shows returns above the foot cap (7). Missing evidence always keeps the cluster (fail-open).

Parameters at this commit: margin 0.03, max above plane 0.25, top band 0.02, spread 0.10, clear height 1.5; window,
band, guard, eligibility reuse the existing values. **No parameter changes after the first measuring run** except
by a numbered amendment in this file (reason, the runs before it reported, and a full re-measurement of every
criterion on the amended commit).

## 3. Sources and environment

* **Control:** v1.2.0 = tag `3b73bbe` (detector bytes equal the branch base `6ee469c`; `detector_freeze.py verify`
  PASS there). Fresh control runs in a detached worktree of `3b73bbe`, never stored numbers.
* **Candidate:** the branch commit with the switch **on** (class default and both YAMLs), measured from a clean
  detached worktree of that commit (X3 requires committed source). Its hash is recorded in every output. If any
  criterion fails, a later commit sets the switch back off.
* Python 3.12, numpy 1.26.4, scipy 1.11.4, scikit-learn 1.4.2, native kernel built by `scripts/build_native.sh`;
  `RESENSE_REPO` = the worktree measured, `PYTHONPATH` = it and its `ros2_ws/src/resense_ros`,
  `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`; `resense.__file__` checked to lie in the worktree. No commit on
  the branch while an X3 run is in progress.

## 4. Pre-registered acceptance criteria (all must pass to switch on)

"Lost" = a frame/row that is a STOP (synthetic: `matched`) on the control and not on the candidate. "Later" =
the first STOP frame of a scene/object is a later frame (nearer) on the candidate.

| # | check | instrument | pass condition |
|---|---|---|---|
| A1 | the review's ray-cast families `approach_bed` (48 scenes), `approach` (48), `rail` (64), `rail_ranges` (40), `beside` (16), `centre` (8), `empty` (3), `approach_empty` (3) | the review's own `synth_controls.py` (unchanged copy), control vs candidate, per frame | **0 frames lost and 0 scenes later** in every family; added frames reported; empty families 0 matched on both |
| A2 | the review's 13 controls | `review_findings_checks.py` (unchanged; on the candidate worktree the default is on) | 13 / 13 pass |
| A3 | extended scenes (`ext_scenes.py`, committed with this protocol): head slope ±0.5/±1/±2 cm/m; a 1 m local rise of +0.05/+0.10 m next to the object (before / after); objects 0.05/0.10/0.15/0.20 m above the real head; widths 0.05 and 0.07 (narrower than / as the head), 0.3 and 0.6 m (wider); on either rail and between the rails; rail model right (raise 0) and low (raise 0.10/0.18); approach 58 → 22 m, 45 frames | same per-frame comparison | **0 frames lost and 0 scenes later** |
| A4 | unit acceptance tests `tests/test_f1a_bounded.py` | pytest | all pass; the defect test fails with the switch off (asserted inside) |
| B1 | set O (every object: `long_low_on_rails`, `small_on_rail`, `thin_hanging`, …) | full gate per-object rows + per-frame JSONL, control vs candidate | every object: STOP frames ⊇ control's, first STOP not later |
| B2 | `doubleT_obstacle` labelled hits | gate `labelled` rows + per-frame | no labelled STOP lost or later |
| B3 | P4's 32 raised-rail physical scenes and their empty controls | `f1a_b1_2026-10-20/physical.py` (unchanged) on both sources | per scene matched STOP rows ≥ control's (same frames); empty controls 0 |
| B4 | the five empty recordings, set F | gate rows | no STOP frame added; set F sequences equal or better |
| C1 | the ride (chunked gate, 8 pieces) | gate rows + per-frame diff | **target: alarm events 18 and STOP episodes 24** (the pre-repair values). Pass condition for switching on: events < 23 or episodes < 26, **no ride STOP row added**, and every changed row explained by the new branch (trace) |
| C2 | the ride, continuous one-detector replay | `f1_false_alarms_2026-10-19/scripts/replay.py --full` | reported (target STOP rows 109, low-kind episodes 1); no STOP row added |
| D1 | Falcon whole recording (4,443 rows) | `falcon_long_range_2026-10-19/scripts/run_cache.py --profile falcon_ros` on the full-range cache, both sources | no STOP row lost; every changed row explained |
| D2 | X3 | `scripts/robustness_battery.py` (protocol `p4_start_2026-10-15`), fresh control run, candidate `--reference` = that control | **0 failing comparisons** |
| D3 | full regression gate | `scripts/regression_gate.py --jobs 2` against `regression_baseline_2026-09-29_shell_off.json` | exit 0 **without `--allow`** |
| D4 | tests | affected suites (F1a/B1/F1/low-object/rail-start/core/algorithm/native) and the full suite | affected pass; full-suite failures, if any, identical on the control |

Paired per-row diff: every gate per-frame row (all eight recordings, ride pieces, set O) and every Falcon row of
candidate vs control is compared field by field outside timing; each changed row is attributed by a read-only trace
of `rail_reference_check` (which branch rejected which cluster). A traced run must equal its plain run (every field
but timing) before its attribution is used. Positive control for the diff tool: a deliberately altered row must be
reported.

## 5. Checks of my own instruments

* The comparison scripts get a positive control (an injected difference must be found) and a negative one
  (control vs control re-run must be equal).
* Determinism: one synthetic family is re-run on the control and its per-frame `matched` rows must be equal.
* Raw frames: pictures of a sample of rows the new branch rejects on the ride (`frame_*.png`) and of any
  synthetic row that changes.

## 6. Decision rule

Switch on (class default and both YAMLs, one commit) **only if every row A1–D4 passes**. Otherwise the switch stays
off, and the README lists the failing rows with the frames/scenes. Partial ride improvement with all safety rows
passing still counts as a pass of C1 if events < 23 or episodes < 26 and no STOP row was added; the README then
states the achieved values against the 18/24 target. The detector freeze manifest is not edited here (the captain
reseals); `detector_freeze.py verify` fails on this branch by design after the detector edit.

## Amendment 1 (21.10, after the first measuring runs on `086353d`)

**Runs before it (all reported, raw outputs in `raw/pre_amendment_086353d/`):** A1 `approach_bed`: **FAIL**, 13 of
831 matched frames lost, 0 gained, 3 scenes later (raise 0.18, left rail (+1), width 0.3, δ +0.05, lengths 0.3/1/4:
first STOP 34.8 → 30.8/31.6 m); `approach_empty`, `empty`, `centre`, `beside`: equal (0 lost, 0 gained). D1 Falcon:
4,443 rows, 0 changed fields. A2 13/13, A4 49/49.

**Cause (trace, `diag/trace_scene.py`, traced == plain checked):** the bounded head top was right (0.162–0.166 from
all four regions, no self-support), but the 5 cm box's top-face returns lie beyond its low footprint and the
highest ring on its front face was only 0.005–0.009 m above the head (0.168 / 0.172 at 38.0 / 35.6 m; ring spacing
≈ 8 cm at that range), so `top ≤ H + 0.03` held; two rejected frames broke the track's build-up and delayed the
STOP by four frames.

**Change:** condition 8 — the cluster is not rejected when its footprint shows a **face toward the sensor**: a
top-surface return with another footprint return straight below it (|Δx| ≤ `rail_head_face_dx` 0.05 m,
|Δdy| ≤ `rail_head_face_dy` 0.02 m, 0.03 ≤ Δh ≤ 0.30 m). Rings stacked at one (x, dy) mean a surface facing the
sensor — an obstacle's front; a continuous rail head never shows one (its rings land metres apart along the
track; side-by-side azimuth samples are ≥ 0.035 m apart across it). Design-set cost (`design/facing.py`): the
signature appears in 5 of 40 eligible real flips. Unit tests added (`test_a_face_toward_the_sensor_is_an_obstacle`,
`test_head_returns_side_by_side_are_not_a_face`). Checked on the 3 failing scenes before committing (16 = control
in each); that is in-sample for those 3 scenes, so **every criterion A1–D4 is re-measured on the amended commit**.

## Revision 2 (21.10 evening, after the independent review REJECTED `61b6e1a`)

Review: branch `claude/f1a-bounded-review-1.3`, `docs/evidence/f1a_bounded_review_2026-10-21/README.md` (F1 real
per-ring azimuth phases, F2 ramps / pipes across the rail, F3 cant, F6 root cause: the compared top is the maximum
inside the cluster's own box). Registered **before any revision-2 measuring run**; design only on the ride design
set (`design_r2/`: the 37 r1 ride / platform rejections with their raw points, B1's 250 snapshots).

**Rule changes** (`resense/lowobj.py`; switch default **off** in the code commit, on only in the measurement commit):

* **Object's full extent (root cause F6):** no return of the cluster's lateral extent ± `rail_head_extent_pad`
  (0.05 m), from x0 − 0.3 to x1 + `rail_head_extent` (1.0 m) along the track, below `rail_head_clear_height` (1.5 m),
  may lie more than `rail_head_margin` (0.03) above H. Replaces the in-box uncapped-top and "nothing above" checks.
  Design set: 34 of 37 ride rejections stay rejectable at 1.0 m (26 at 2 m, 9 at 5 m: `design_r2/ride_extent.txt`).
* **Rails must agree (F3):** each rail's level is the lower of its two regions; if the two rails' levels differ by
  more than `rail_head_rails_tol` (0.03 m), no rejection (cant or an object along one rail). H = the lower level.
  Ride: |own − other| p50 0.008, p90 0.023, max 0.027 m.
* **Face toward the sensor (F1):** any two footprint returns within 0.05 m along and **0.07 m** across
  (`rail_head_face_dy`, was 0.02; admits the measured per-ring phases ±0.044° plus one 0.1° column), 0.03–0.30 m
  apart in height. Physical basis: one ring is a cone of near-constant elevation, so returns at one range and
  different heights come from different rings, i.e. a surface facing the sensor; a rail's next ring crossing lands
  metres further. Design cost: 5 of 37 ride rejections show it (`design_r2/ride_face.txt`).
* Unchanged: pre-repair eligibility, rail-line eligibility, the four regions, H ≤ 0.25, top surface ≤ 0.10 wide.

**Hard rows added (all in addition to A1–D4, which are re-measured on the revision-2 commit):**

| # | check | instrument | pass condition |
|---|---|---|---|
| R1 | every review family as the review defined it: `apb`, `apb_meas`, `ext_meas`, `azoff`, `fine_delta`, `shapes`, `two`, `cant`, `curve`, `moving`, `falcon`, `empty`, `seeds` (6 configurations × 5 noise seeds) | the review's `attack.py` + `rc2.py` (unchanged, read from its branch), control vs candidate, per frame | **0 STOP frames lost, 0 scenes with a later first STOP**; empty: 0 detections both |
| R2 | the same families with the **measured per-ring phases forced on every scene** (families that used the ideal grid get `az_off = measured`), noise seeds 0, 101, 202 | `attack_r2.py` (wrapper only: sets `az_off` and `seed_off`, nothing else) | same, on every seed |
| R3 | the earlier synthetic rows A1 / A3 (ideal grid) | as before | same |

Every synthetic row's comparator gets a self-test and a positive control (the rejected `a77d884` or `61b6e1a` on a
family where the review measured losses must show them). Decision rule unchanged: switch on only if every row passes;
if making the rule safe removes the ride gain, that is reported and the switch stays off.

### Amendment 2 (21.10, after the first revision-2 runs on `f1f6f44`)

**Runs before it (reported; raw in `raw/pre_amendment2_f1f6f44/`):** R1 on the candidate against the review's archived
control rows: `apb` 831 → 831, `apb_meas` 709 → 709, `ext_meas` 287 → 287, `azoff` 827 → 827, `fine_delta` 444 → 444,
`two` 273 → 273, `cant` 336 → 336 (all 0 lost), but **`shapes` FAIL: 1,075 → 1,074, 1 scene later** (0.3 m ramp rising
away from the sensor, right rail, δ +0.05, raise 0.18: frame 31 lost, first STOP 33.2 → 32.4 m). Positive control:
revision 1 (`61b6e1a`) on `apb_meas` reproduces the review's loss exactly (709 → 700, 3 scenes, 34.8 → 32.4 m).

**Cause (`diag/trace_attack.py`, traced == plain):** at 38 m one ring crossed the ramp's sloped surface at head
height (5 returns, h 0.162–0.163 against H 0.1616), spread 0.27 m across the track; 4 of them lie 1–2 mm outside the
cluster's strict box, so the top-surface width test (box only) saw a single return (0 m wide).

**Change:** the top surface is taken over the object-extent region (lateral extent ± 0.05, x0 − 0.3 … x1 + 1.0),
returns within `rail_head_top_band` (0.02) of that region's highest return; width ≤ 0.10 as before. Design cost
(`design_r2/ride_spread_ext.txt`): 0 of 37 ride rejections exceed 0.10 (max 0.097). Unit test
`test_a_ramp_crossed_at_head_height_is_wide_not_a_head`. All rows re-measured on the amended commit.
