# Independent review of the F1a completion (`a77d884`, merged as `769d075`) — 20 October 2026

> **Reviewer:** independent agent, not the author. **Detector code:** not touched (`resense/`, `native/`, `configs/`, ROS package,
> `scripts/detector_freeze.py`, existing evidence all unchanged; the monkeypatch used for one control lives in my script only).
> **Held-out G3:** not touched. **Nothing tuned.** Environment: `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `RESENSE_REPO` = the
> checkout evaluated, Python 3.12.3, numpy 1.26.4; native kernel rebuilt from `native/resense_native.cpp` (sha256
> `67fa0887…c7394`, **identical** to the digest in the author's execution records).
> **Sources compared** (three detached `git worktree`s):
> reference `f56ad5e` (what the author's gate used as "reference"; the tree of the B1 repair's acceptance) ·
> parent `450a99f` (the actual git parent of `a77d884`: an intermediate "variant B" that the author measured and discarded; **not** what the
> author calls the reference) · candidate `a77d884` (= `resense/lowobj.py` of `769d075`; `git diff a77d884 769d075 -- resense native configs ros2_ws` is empty).

## 1. VERDICT

**REJECT as sealed (`769d075`/seal `…_1.2.0_f1a.json`): the headline safety claim "the change loses no real detection" is falsified by a
positive control the brief itself prescribes — in the repo's own ray-cast scenes, objects standing 5–20 cm *above* the rail head are
rejected as "rail head" in 59 frames of 23 of 48 approach scenes (69 of 831 STOP frames lost, 0 gained; first STOP up to 8.8 m later), because the
"head surface" the rule reads can be the object's own top face; the ride benefit (9 false STOP frames removed, 85 of 98 flips explained) is real and
reproduced, but the evidence offered for "no loss" never exercises the rejecting path.** It becomes acceptable only after the surface estimate can no
longer be supplied by the candidate's own neighbourhood and the controls in §4 pass on the fixed source (this review's tests
`review_findings_checks.py` fail 13/13 on `a77d884` and pass 13/13 on `f56ad5e` and `450a99f`).

## 2. What was checked

"Independent" = my own script/derivation, not the author's `compare_*.py`, `audit.py`, `apply_continuation.py`, `inspect_*.py`.
Scripts and raw outputs are in this directory (`out/` = every raw output cited).

| # | What | Method | Size | Result | Indep. |
|---|---|---|---|---|---|
| 1 | Sources of the author's runs | `git show <commit>:resense/lowobj.py \| sha256sum` vs `source_sha256` in the `*-execution.json`; the other frozen files; `tracked_diff`; `native .so` | gate, X3, Falcon, tests, physical records (ref+cand) | candidate `a77d884` = `05fee7e7…` (clean tree), reference **`f56ad5e`** = `6474e3db…`; all other 37 common frozen files identical; only `docs/…/compare_gate.py` is dirty in four candidate records (docs, not detector); my rebuilt native `.so` has the identical sha256 | yes |
| 2 | Same data/config on both sides | execution commands, `config.sha256`, `file_sha256`, frame counts; full-leaf diff of the two gate JSONs | 2,243 leaves | identical command lines (same cache path), same config digests; data content hash itself is **not** recorded in the gate JSON → data identity rests on path + frame counts + equal `sha256` leaves (**partly UNVERIFIED**) | yes |
| 3 | Headline gate numbers | `gate_rederive.py`: generic leaf-by-leaf diff of `gate-c-reference.json` vs `gate-c-candidate.json` | 65 differing leaves, 40 outside timing | ride events 23→18, STOP episodes 26→24, alarm frames 111→102, `ride.alarm_dist[0]` 20.7→27.6 m; set O: 10 objects, **every field identical**, `inside_stop_frames` 414=414; five-empty 37/7/11 equal, advisory 1006→1004; `doubleT_platform` advisory 182→180; set F identical; `doubleT_obstacle` labelled hits identical; gate PASS, no `--allow`. Positive controls: swapping the files flips all 37 numeric deltas; changing one equal leaf is detected (+1); lowering a set O count is detected | yes |
| 4 | The 9 removed STOP frames, reference side | P4's archived per-frame gate of the B1 tree (`gatework_f1a.tar.xz`, other session) read by `p4_gate_rows.py` | 8 ride pieces, 11,271 rows | 111 STOP rows (= reference alarm frames); **9 of 9** removed rows are STOP rows at exactly the author's reference distances (42.1, 38.9, 36.9, 35.8, 24.3, 23.6, 21.8, 47.6, 45.9 m); rows 1262–1264 are also STOP in the reference but not in the removed list (they stay in the candidate: other tracks) | yes |
| 5 | The 9 removed frames, cause | `removed_frames.py`, `track_lineage.py` on P4's read-only trace; `plot_snap.py` pictures | 9 rows, 8 lineage clusters | every removed STOP chain starts from a low cluster on a rail line (lateral 0.73–0.86 m, width 0.18–0.46 m, uncapped top from 6 cm below to 3.5 cm above S) that the pre-repair rule rejected and the B1 repair let through; row 1265 (35.8 m) stands on a **centre** cluster (lat 0.02, width 0.39) which the candidate does *not* itself reject — its STOP disappears only because the track's earlier hits (rail fragments) are now weak; row 80 of piece 4 has no matched track at 21.8 m (inferred: a kept/predicted ghost of a track last matched at 37–41 m); pictures `out/fig_removed_frames_lineage.png`, §5 F7 | yes |
| 6 | 98 archived flipped clusters replayed through the production `rail_reference_check` | `snap_replay.py` (cluster rebuilt from record; bbox padded 0.5 mm, see §7), three sources, plain and traced (traced == plain) | 98 snapshots × 3 sources | reference rejects **0** (= the trace's own D flags, positive control for the harness), parent **77**, candidate **85** of 98 (matches author's 85) | yes |
| 7 | Why the other 13 are kept | `classify_kept.py`: my own reading of the rule from raw points, compared with the production decision | 98 | 85 rejected / 5 not on a rail line / 4 single return / 3 one side empty / 1 wide; **0 mismatches** with the production function | yes |
| 8 | Head-surface numbers from raw points | `noise_est.py` (97 snapshots with ≥ 2 distinct returns), `head_web.py` (98 snapshots, 9,920 distinct rail-band returns) | 98 | my S equals the production surface in 85/85; S p10/p50/p90 = 0.156/0.191/0.234 m above the model plane (max 0.297); local scatter of head returns sd p50 1.4 cm; see §6 | yes |
| 9 | Threshold and adversarial controls at the production call site | `unit_controls.py` (repo fixtures `_rails`, `_low`; `Detector._rail_reference`), ref/parent/cand | 115 variants (36 of them Monte-Carlo cells × 500 trials) | exact threshold `top ≤ S + 0.05`; failures F1–F3 (§5); noise table §4.3 | yes |
| 10 | Ray-cast scenes, full detector (author's `raycast.py`) | `synth_controls.py`: stationary (195 scenes × 12 frames), approach (48 × 45), approach_bed (48 × 45), empty (3 × 45) | about 6,800 frames per source | raise 0 / centre / beside / empty: identical; `approach_bed`: **candidate loses 69 STOP frames in 23 scenes**, gains 0 (§4.2). Controls: traced == plain (2,160 frames, 0 differ); candidate with the new branch **neutralized** == reference (2,160 frames, 0 differ) | yes |
| 11 | Ground truth for the cause | `self_support_check.py` | 14 rejecting frames in 3 scenes (L 4 m, δ 0.10 and 0.20; 0.3 m box, δ 0.10) | at **13 of 14** rejecting frames S equals the box's own top height in the detector's height frame (|S − top| ≤ 1 mm) and is defined by a return lying on the box 0.5–3.1 m beyond the rejected cluster's bbox; the exception is the organizers'-size box at f23 (S from a return 3.8 m before the box, top-face returns outside the cluster's bbox so its uncapped top was only 0.20) | yes |
| 12 | Edge cases | `edge_cases.py` | 22 lines (21 cases + a timing) | empty/NaN/inf/duplicate/missing own rail line/one side empty/zero width/free=None/margin 0: all fail open (cluster kept); with a control that the same scene *is* rejected when the support is present; `rails_spacing=None` raises `TypeError` (pre-existing pattern, config is always a float); 100k returns in the window: 0.3 s | yes |
| 13 | Tests | affected suite (author's list) on candidate with native kernel built; new tests on ref/parent; parent's test file on candidate; full suite | 363 / 18 / 20 / 2,422 | affected **363 passed, 1 deselected** (28 more skipped without the native `.so`); new `test_f1a_continuation.py`: **6 of 18 fail on `f56ad5e`** (the positive tests) and 12 pass on both (guards), all 18 pass on parent `450a99f`; the **parent's version** of the file fails 2 of 20 on the candidate (`test_one_sided_or_absent_head_support…[before/after]`, deleted in `a77d884`); full suite 2,404 passed + 17 subtests, 1 failed = `test_lidar_proxy_hook::…fails_closed`, **fails identically on `f56ad5e`** (pre-existing, environment) | yes |
| 14 | Freeze | `python3 scripts/detector_freeze.py verify` on `769d075`; own `freeze_check.py` | 40 files | PASS, source `9cc33a68…`; my own sha256 of the 40 files: 0 mismatches; manifest `validation.sha256` = sha256 of `gate-c-candidate.json`; execution-record digests = manifest for the 37 common files | yes |
| 15 | Author's physical scenes | re-created with the same generator (`centre` family, 8 scenes) | 8 × 12 | reference = candidate; the new function is called but returns `None` (the boxes are at the track centre: never rail-eligible) → these scenes **cannot** test the new rule | yes |

## 3. Answers to A–F

### A. Code (`resense/lowobj.py:321-361`, call site `:403-416`)

Read line by line. Eligibility is the pre-repair rule (`c.height_max < original + local_rail_margin`, :410) **and** `free` present **and** a
narrow (≤ 0.45 m) cluster whose own lateral interval reaches an expected rail line ±0.10 m (:340-343). `_rail_surface_reference` then reads
`S = max h` over the low-free returns in the cluster's own lateral band `[d0,d1]`, `-0.3 < h < foot_max_top`, within
`x0-5 … x1+5` (:345-346, :353) and returns it if ≥ 2 **distinct** returns lie within 0.05 m of it (:356-359); the call site rejects the
cluster if its uncapped footprint top ≤ S + 0.05 (:412).

* **Fallbacks are fail-open (the safe direction).** No `free` mask (the ablation), `local_rail_margin = 0`, original reference `None` (own rail line
  absent), cluster wide or off the rail line, one side without any band return, fewer than 2 distinct returns, empty/NaN/inf input → `None` →
  not rejected → the alarm path stays open (`edge_cases.py`, all cases; duplicates held twice count once). NaN heights are excluded by the
  comparisons.
* **Does the rule reject only what the pre-repair rule rejected?** Yes at the call site (:410 is exactly the pre-repair condition); confirmed on
  the 98 snapshots (all 85 rejections are pre-repair rejections). But that subset argument carries the **pre-repair defect with it**: eligibility is
  decided by the *all-returns* median, which a long object along a rail raises itself (the B1 problem). The whole safety of the new branch
  therefore rests on S being independent of the candidate — and it is not (F1).
* **Edge cases of the geometry.** `rails_spacing` is a config constant (1.59), so "a missing second rail" cannot be seen by this function; a
  missing own-side rail line makes `original` `None` (fail-open, tested). Curved/banked track: the band is the cluster's *own* lateral interval,
  so cant is handled per rail; an axis error of more than ~0.1 m on a curve makes the cluster ineligible or the band miss the head (fail-open).
  A rail head whose height varies along the track is **not** handled: S is the window maximum (F2).
* **Constants.** "All parameter-free" (README, docstring) is not accurate. Reused knobs: `rail_start_margin` 0.05 (borrowed from
  `mark_rail_line`, where it protects a different situation), `local_rail_window` 5 m, `rail_start_lateral` 0.10, `rail_start_max_width` 0.45,
  `foot_max_top` 0.35. Literals: guard 0.3 m, lower bound −0.3 m, **the count 2**, the 1 mm de-duplication. The count 2 and the 0.05 were chosen
  while looking at the same 98 flips (PROTOCOL: variant B recovered 77, this 85) — in-sample; on those snapshots a bar of 1 return
  would reject all 4 "one return" flips (89 of 98; `out/one_return_check.txt`), i.e. the bar of 2 is a fail-open choice that costs 4 recoveries.
* **The invisible band, in metres.** With S the highest rail-band return: an eligible narrow rail-line cluster is **not reported when its uncapped
  top is ≤ S + 0.05 m**. Measured S on the ride's rail fragments: p10/p50/p90 = **0.156 / 0.191 / 0.234 m above the model plane** (max
  0.297), i.e. tops up to ≈ 0.21 / 0.24 / 0.28 m above the plane are hidden. Relative to the true head top the nominal band is +0.05 m, but the
  real band is larger because S is a *maximum over ±5 m*: + noise bias (0–3 cm), + the along-track rise of the head returns in the window
  (data: |slope| p50 0.7, p90 1.8 cm/m → up to +9 cm; the 10 cm object is hidden at ≥ 1 cm/m, F2), and it has **no bound** when the object's own
  returns supply S (F1). Above S ≥ 0.30 the 0.35 cap `foot_max_top` makes *every* narrow rail-line cluster hideable (unit control
  `high_head_cap`; not observed in the data, max S 0.297).
* **Physical acceptability.** The smallest object that must be seen is the organizers' 30 × 30 × 10 cm. Resting on a rail head its top is at head +
  0.10 m, i.e. 5 cm above the nominal limit; with realistic ring sampling and 1–2 cm scatter it is hidden in ≤ 1 % of frames (§4.3), which would
  be acceptable. It is **not** acceptable that the margin collapses to 0 with a 1 cm/m slope, a local 5 cm rise, one-sided data or the object's own
  unclustered returns.

### B. Positive control for "loses no real detection" — §4

### C. Evidence from raw data — checks 2–8 above. The numbers 23→18 / 26→24 / 111→102, 9 removed STOP frames and "set O identical, 414 unchanged,
five-empty 7/11" reproduce from the stored JSON; 9/9 removed rows are confirmed on the reference side from an independent archive; the
candidate side per frame is **UNVERIFIED** (no per-frame candidate output is archived; "0 added" follows only from the net −9 alarm frames and
the author's list). My replay of the production function on the raw snapshots reproduces 85 of 98.

### D. Re-run — **not possible, UNVERIFIED.** `/tmp/opencode/` (cache `resense-b4-data`, Falcon decode, X3 inputs) does not exist in this container;
the ride is a 90 GB bag on Yandex Disk (`docs/DATASET.md`); 20 GB free. I did not attempt to fetch it. What I could rerun without the recordings:
the 98 archived raw snapshots (§2 #6–8) and synthetic full-detector scenes (§2 #10).

### E. Tests — §2 #13–14. The new tests do fail on the reference (6/18) and pass on the candidate (18/18); they do **not** distinguish the candidate from
`450a99f` (all 18 pass there too), they delete the one-sided tests, and none of them contains a case where S comes from the object's own returns, a local
rise or a slope. My `review_findings_checks.py` (13 tests) closes that: 13 pass on `f56ad5e` and `450a99f`, 13 fail on `a77d884`.

### F. Plausibility — §6.

## 4. Positive controls ("B")

### 4.1 Threshold (unit level, repo fixtures; `out/unit_compare.txt`)
Fragment on a rail, rail web 0.11, head surface 0.20 seen by returns on both sides, fragment top = head + δ. Candidate **HIDE** for δ ≤ +0.05, **KEEP**
at +0.0501 and above (both rails); reference KEEP for every δ in [−0.06, +0.10] (HIDE at +0.15/+0.20 for both: the top return ≥ 0.35 is outside
`foot_max_top`, pre-existing). The adversarial case "top at the head" (δ = 0): HIDE by design.

### 4.2 Real object clearly above the margin, full detector (`out/synth_approach_bed_compare_ref_cand.txt`, `out/apb_analyze.txt`)
Ray-cast approach 58 → 22 m, 0.8 m/frame, fresh noise seed per frame; box standing on the bed against a rail (z from bed to **real head + δ**, δ = 0.05/0.10/0.20),
length L = 0.3/1.0/4.0 m, width 0.3 (and 0.1), both rails, the rail raised 0.10 or 0.18 m beyond 32 m (the track model, learned in 4–30 m, then sits 0.10–0.18 m below the real head — the situation F1a completion targets).
Matched STOP frames (reference → candidate) and first-STOP distance:

| scene | ref → cand frames | first STOP ref → cand |
|---|---|---|
| raise 0.10, right rail (side −1), L 4.0, δ +0.10 | 26 → **15** | 42.8 → **34.0 m** |
| raise 0.10, right rail, L 4.0, δ +0.20 (20 cm above the head) | 29 → **20** | 45.2 → **39.6 m** |
| raise 0.18, left rail (side +1), L 4.0, δ +0.10 | 19 → **12** | 37.2 → **31.6 m** |
| raise 0.18, left rail, 0.3 × 0.3 (organizers' size), δ +0.05 | 16 → 11 | 34.8 → 30.8 m |
| raise 0.18, left rail, 0.3 × 0.3, δ +0.10 | 14 → 13 | 33.2 → 32.4 m |
| 48 scenes in total | 831 → **762** | 23 scenes lose frames, 15 detect later, **0 gain any frame** |

*Controls.* (a) Traced candidate run == plain candidate run, 2,160 of 2,160 frames. (b) The candidate with `_rail_surface_reference` monkeypatched to
return `None` (an evaluation-side patch in `synth_controls.py --neutralize`) == the reference on 2,160 of 2,160 frames: **every lost frame is caused by
the new branch.** (c) The trace shows 59 frames (in exactly those 23 scenes) in which the branch returned a surface and a low cluster was rejected.
(d) `self_support_check.py`: at those frames the box's true top in the detector's height frame is, e.g., +0.196, and S = +0.196 — S **is the object's top face** (defined by a return lying on the
box 0.5–3.1 m beyond the rejected cluster's bbox, outside every low footprint; 13 of 14 rejecting frames in three scenes). (e) With the model right (`raise` 0) reference == candidate on
all 24 `approach` scenes at raise 0 and on 21 of 24 at raise 0.18; the 3 that differ are boxes flush with the head (δ = 0, right rail: 14 → 13 frames, first STOP one frame later);
the empty-world controls give 0 STOP frames on both sources (so my synthetic world shows no false-alarm benefit either).
**What this does not show:** it is synthetic first-return geometry, an object enclosing the rail from the bed up; objects *resting on* a raised head are not
detected by **either** source in this world (0/45, pre-existing, not caused by the change); stationary scenes were not informative (clusters appear in
only 3 of 12 frames in both sources). I could not test real-world occurrence.
The parent `450a99f` (the discarded variant B) on the same 48 scenes also loses frames, fewer: 831 → 803 (28 lost, 0 gained, 9 scenes, 9 with a later first STOP);
the candidate loses 41 more frames than the parent in 17 scenes (`out/apb_analyze_parent_vs_ref.txt`, `out/apb_analyze_cand_vs_parent.txt`). So variant B is not obviously a safe fallback either (the mechanism of its losses was not analyzed: UNVERIFIED); on the unit controls of F1–F3 it behaves like the reference (KEEP in every row, `out/unit_compare.txt`; the 13 tests of `review_findings_checks.py` pass on it).

### 4.3 Noise (unit level; `unit_controls.py`, 500 trials per cell, σ on every height)
10 cm object resting on the head (δ = 0.10), hidden per frame by the candidate: σ = 1 cm 0–0.2 %, 1.5 cm 0–5.8 %, 2 cm 0.4–19.8 %, 3 cm 3.8–45.6 % depending on the
return count (sparse: 1 head return per ring crossing, object seen by 4 returns: 0 / 0 / 0.4 / 4.6 %; dense: 0 / 0 / 1.0 / 3.8 %; pessimistic: 1 object return
0.2 / 5.8 / 19.8 / 45.6 %). δ = 0.06: 17–82 %. Reference 0 in every cell. Data: local scatter of head returns sd 1.4 cm (p50), 1.9 cm (p90).

## 5. Findings, ranked

**F1 — HIGH. The "head surface" can be the object's own top face (self-support); a real object above the margin is rejected and detected later.**
`resense/lowobj.py:345-353` (window over `x0-5 … x1+5`, any free return counts, maximum) with the free mask built from the **bboxes of low
clusters only** (`low_free_mask`, :303-318); the call site `:411-412`. The object's returns above the low-stage floor that lie outside every low cluster's
bbox (a long plank/pipe whose later part forms no low cluster, or the top face beyond the low fragment's bbox) are "free" and become S, so
`top ≤ S + 0.05` holds for the object itself. *Scenario:* a plank/duct/cable bundle ≥ 1 m long standing against a rail 5–20 cm above the head
while the model plane is 0.1–0.2 m low (the ride's regime): its front fragment is rejected in 6–7 of 45 frames of the approach (two traced scenes), the track is
confirmed up to 8.8 m later (0.8–8.8 m over the 15 scenes with a later first STOP; §4.2; ground truth S = object top, ±1 mm). Unit level: two unclustered returns of the object within the window hide it
(`object_own_unclustered_returns`, x = 40.5…44.5; reference and parent KEEP). The author's test `…neighbouring_object_upper_return…` only
covers neighbours that are low clusters. Does **not** reproduce: when the model is right (rail at the plane), because the cluster is then not
eligible (identical on 48 scenes).

**F2 — HIGH/MEDIUM. S is a maximum over ±5 m, so the band grows with any rise of the rail line in the window.** `:353`. A local rise of two returns 5–10 cm above
the head within 5 m hides a 10 cm object (`local_rise_on_rail_line`); a head slope ≥ 1 cm/m (either sign) hides it (`head_slope`; data: 35 % of the
78 ride windows with ≥ 3 head-hit bins have |slope| ≥ 1 cm/m, p90 1.8 cm/m). Reference and parent KEEP all of these (the parent uses the lower side).

**F3 — MEDIUM. "Two-sided support" is not what the code does, and the tests that said so were deleted.** `:347-349`: the side clause only asks for *any*
band return (bed at −0.2 counts) on each side; S and the two supporting returns may all lie on one side, or in the guard zone. A head seen on one side only now rejects
(`head_before_only`, `head_after_only`); the parent's tests `test_one_sided_or_absent_head_support_does_not_suppress[before|after]` fail on the candidate
(`out/tests_parent_version_on_candidate.txt`). README/PROTOCOL still describe two-sided support. Picture: `out/fig_cand_only_rejections.png` (e.g.
`new_data_52_0016:5`: S from two returns on the before side only).

**F4 — MEDIUM. The evidence offered for "no loss" does not exercise the rule.** The author's 32 physical scenes put the box at the track centre (never
rail-eligible; the function returns `None`, §2 #15); set O, Falcon, X3 are *outcome* equalities with no record of whether the branch was reached on them
(I could not instrument them); the ride is both the design set (the 98 flips shaped the rule) and the acceptance set; X3 for the candidate was compared against the stored
`r3-completion-work/x3-a-candidate.json` (see its command), not only against the fresh reference run, and the X3/Falcon outputs are not archived (only execution records);
the README's link to `out/` points to a directory that does not exist in the evidence folder. The claim "no real detection lost" is therefore unsupported and, by §4.2, false in synthetic scenes.

**F5 — MEDIUM/LOW. Max-statistic fragility: isolated high points define S.** e.g. `new_data_52_0018:5`: S = 0.281 comes from one return 3.5 cm above the pack
(gap to the second highest 3.7 cm, only 2 supporting returns; the gap is 4.2 cm at p90 over the snapshots), hiding a cluster whose top (0.246) lies below S + 0.05 (the parent rejects it too); noise MC §4.3: a 10 cm object at σ = 3 cm is hidden in 4–5 % of frames.

**F6 — LOW. Explanation of the mechanism not supported by the numbers.** The ride's rail-band returns (98 snapshots, 9,920 distinct returns) are bimodal, but the upper
mode (the head top if the author is right) is at **+0.19 m** above the model plane (p50 of per-snapshot maxima; p10–p90 0.17–0.23), the lower mode peaks at **−0.02…0.00 m** (not "0.05–0.11"; the histogram has a valley at 0.06–0.10), so the plane sits
~0.19 m, not "~0.1 m", below the real head top (`out/head_web.txt`). Whether the lower mode is web, ballast or the head with the plane correct and the upper mode something else on the
rail line cannot be decided from this data; it matters because the invisible band is relative to whatever S is. No implausible physical value found otherwise (STOP distance steps of 2.0–3.2 m/frame at 10 Hz on the ride are 72–115 km/h;
`new_data_4` row 80's STOP 21.8 m comes from a kept/predicted ghost of a track whose last matched centroid was at 37–41 m three frames earlier — the tracker's predicted position, not a measured 20 m/frame).

**F7 — LOW. One removed STOP frame is removed by track lineage, not by the rule.** Row 1265 of piece 1 (35.8 m) stands on a centre cluster (lat 0.02, width 0.39, top 0.18) that the candidate keeps; the
STOP disappears because the track's earlier hits were rail fragments. The ride has no objects (organizers, `docs/DATASET.md`), so it is a false alarm either way; it shows removals are not all
"rail head rejected by S". **Does not reproduce as a loss.**

**F8 — INFO. Reference mismatch.** The brief/git define the parent as `450a99f`; the author's gate/X3/Falcon/physical runs use `f56ad5e`. Both evaluated here; on the 98 snapshots the candidate rejects 10 clusters the parent keeps and keeps 2 the parent rejects.

Does not reproduce: any defect in fail-open handling, any exception on empty/NaN input, any change to the five empty recordings or set O in the stored gate, any new STOP frame in the stored aggregate.

## 6. Plausibility (F)
`out/head_web.txt`, `out/noise_est.txt`: rail-band heights above the model plane, 9,920 distinct returns: p5/p25/p50/p75/p95 = −0.087/−0.022/+0.034/+0.137/+0.182; per-snapshot max (the surface) p10/p50/p90 =
+0.166/+0.194/+0.234; per-0.5 m-bin max (the F1a median line input) p10/p50/p90 = +0.034/+0.126/+0.192; S − second-highest return p50 0.7 cm. Values in range for rails and sleepers; the
"~0.1 m" claim is not what these show (F6). The number of distinct returns within 5 cm of the top is p10 2, p50 6 (min 1): in ≥ 10 % of windows the "≥ 2 distinct returns" bar is met by exactly two.

## 7. Corrected during my own work (my errors)
1. First snapshot replay rejected 1 of 98 on the reference (expected 0): the archive stores the bbox rounded to 1 mm, so a return exactly on the bbox edge fell out of the footprint (top 0.042 instead of 0.163). Fixed by padding the bbox by 0.5 mm (`--pad`); reference now 0/98 (= the trace's flags); unpadded and padded outputs both kept (`snap_*.json`, `snap_pad_*.json`).
2. `gate_rederive.py` positive controls were wrong twice (a sign test that could never be true; a mutation of a leaf that already differed). Rewritten; the version in this directory is the corrected one.
3. `unit_compare.py` asserted equality of results as if they were parameters (noise rows); fixed.
4. `edge_cases.py`: first coordinates sat on the open boundary of the ±5 m window (spurious `None`), one "missing rail" case passed `free=None` and so did not test the path. Rewritten with a control.
5. `synth_compare.py` compared only the first 12 frames of 45-frame scenes (it printed "frames differing 0" next to different counts). Fixed to all frames.
6. The first Monte Carlo used one object return and dense head returns (pessimistic); I added sparse/dense realistic counts and report all three.
7. The first slope estimate included bins without a head hit; restricted to head-hit bins.
8. My first synthetic families (stationary, `beside`, `rail`) were uninformative (the reference itself detects nothing in the raised world and the branch is rarely reached); I built `approach_bed` after seeing that, and report the uninformative ones as such.
9. I first read "reference" as the git parent `450a99f`; the author's runs use `f56ad5e`; both are evaluated.

## 8. UNVERIFIED
* Any re-run on recordings: ride, set O, five empty, set F, Falcon (4,443 rows identical), X3 (0/260), per-frame candidate output ("0 STOP frames added" is only
  consistent with the net −9, not independently derived), 9 removed frames on the **candidate** side.
* Whether the new branch is reached (and does not fire wrongly) on set O / Falcon / X3 frames.
* Occurrence of F1/F2 on real data (found only in the repo's ray-cast scenes and fixtures); sensor height noise (1–2 cm assumed from the data's local scatter).
* The physical reading "web / head top / bed" of the rail-band modes and the "~0.1 m" statement.
* Data identity beyond path + frame counts + equal config digests (no data hash in the gate JSON).
* Full-suite parity on the reference (I ran only the one failing test there); X3 `--reference` provenance.
* G3: untouched by design.

## 9. Files
`snap_replay.py`, `snap_compare.py`, `classify_kept.py`, `removed_frames.py`, `track_lineage.py`, `p4_gate_rows.py`, `plot_snap.py`, `make_lists.py`, `head_web.py`, `noise_est.py` (98 raw snapshots / P4 archive);
`gate_rederive.py`, `freeze_check.py`, `junit_summary.py` (stored evidence); `unit_controls.py`, `unit_compare.py`, `edge_cases.py`, `review_findings_checks.py` (fixtures);
`synth_controls.py`, `synth_compare.py`, `apb_analyze.py`, `apr_trace.py`, `synth_trace_pick.py`, `self_support_check.py`, `trace_check.py`, `trace_calls.py`, `trace_count.py`, `rows_equal.py` (ray-cast).
`out/`: all raw outputs, pictures (`fig_removed_frames_lineage.png`, `fig_cand_only_rejections.png`, `fig_flips_kept_by_candidate.png`). The extracted P4 archives and the three worktrees live in the session scratchpad and are not committed.
