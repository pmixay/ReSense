# P4 final-bundle acceptance on `fb92213` (20.10)

> **From:** P4 (evaluation) · **Source:** `fb92213` (main's tip when run; detector tree = `f56ad5e` + `resense/lowobj.py` of the
> F1a completion `450a99f`, `a77d884`) · **Environment:** Python 3.12.3, numpy 1.26.4, native kernels built in a clean
> worktree, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, `RESENSE_REPO` = the worktree · **Detector code:** not touched ·
> **G3:** not touched · started 18:58 UTC, results 19:28–19:37 UTC. This is P4's recommendation to the captain, not an approval.

## Verdict

**No blocking finding on the measured source.** The strict gate, X3 and the whole Falcon recording pass against the
`cc6226e` records and the F1a completion is bounded and fails open. **H1 ships as partial**: this is the repository's own
status (A-axis 82 → 114/177, 63 misses, independent acceptance **blocked** by measured failures, `65af1f2` and `fb92213`),
and nothing here contradicts it. None of my runs measures H1's improvement or its open failures (wrong-pair false core/STOP,
inside misses); they show only that the bundle does not regress the gate, X3 or the Falcon.

| item | result |
|---|---|
| strict gate, default config, no `--allow`, seal baseline | **PASS**, exit 0: 8 gated rows better, **0 worse, 0 missing**, 190 equal ([`out/gate_fb92213.txt`](out/gate_fb92213.txt)) |
| X3 (40 cases, 29,765 rows) against the `cc6226e` run | **PASS**: 0 of 260 comparisons fail; 40 of 40 cases equal in every row's decision, detections and warnings ([`out/x3_compare_fb92213.txt`](out/x3_compare_fb92213.txt)) |
| whole Falcon, 4,443 frames | decision, detections and warnings equal to the `cc6226e` record in **all 4,443 rows**; 41 rows differ only in the latency health level / message; stream sha256 `90dea27d…` = the published ([`out/falcon_vs_cc6226e.txt`](out/falcon_vs_cc6226e.txt)) |
| affected tests | **338 passed**, 6 subtests, 17 files (list below), and the 1 test the cache check deselected, `test_rail_start.py::…standing_fresh_start_do_not_stop`, passes with the ride cache present (`test_rail_start.py`: 28 passed). The full suite was not run |
| `detector_freeze.py verify` on `fb92213` | PASS, 40 files, digest `9cc33a68…` |
| set O and `doubleT_obstacle` (the real, labelled objects) | **0 rows differ** from `cc6226e`: no positive STOP moved |

Affected tests: `test_f1a_b1`, `test_f1a_continuation`, `test_f1_false_alarms`, `test_low_height_keep`, `test_low_local_support`,
`test_lowobj_near`, `test_rail_start`, `test_cable_confirmation`, `test_cable_current_support`, `test_column_local_rails`,
`test_detector_freeze`, `test_core`, `test_algorithm`, `test_ego_veto`, `test_k1_k2_axis`, `test_clear_cap`, `test_far_thin`
(chosen by what imports `lowobj`, `tracking`, `clustering`, rails and cables; [`out/tests_affected.log`](out/tests_affected.log)).

## What changed in the detector since the source I reviewed (`cc6226e`)

`git diff cc6226e fb92213 -- resense native configs ros2_ws`: `clustering.py` +22 and `tracking.py` ±55 (R3 completion, `0a472d6`),
`lowobj.py` +58 −2 (F1a completion). Since `f56ad5e` only `lowobj.py` changed, and `f56ad5e` gives the same gate rows as `cc6226e`
(my H′-off gate on it: 15,269 rows, 0 differ, PR #46; H′ is never armed on the gate data), so **every changed gate row below comes from the
F1a completion**.

## The F1a change, line by line (`resense/lowobj.py`, `450a99f` + `a77d884`)

New `_rail_surface_reference(c, X, dy, h, d0, d1, cfg, rails_spacing)` and a new branch in `rail_reference_check`.

1. **When it can act.** The branch sits inside `if cfg.local_rail_margin > 0`, runs only `if free is not None and original is not None
   and c.height_max < original + local_rail_margin`, after the first rule has not rejected. `c.height_max < original + margin` is
   exactly the pre-B1 rule's rejection (top = `height_max`, reference over every return), so the new branch can only re-reject clusters
   the pre-B1 F1a rejected; it never rejects anything that rule accepted. It is a partial undo of the B1 repair, bounded by it.
2. **Narrow and on a rail.** `c.size[1] <= rail_start_max_width` (0.45 m) and the lateral interval reaches a rail line ± `rail_start_lateral`
   (0.10 m), the geometry of `mark_rail_line`. Otherwise `None`: fail open.
3. **The surface.** The highest return of the *low-free* points in the fragment's own lateral band `[d0, d1]`, heights −0.3 m … `foot_max_top`
   (0.35 m), within `local_rail_window` (5 m) of the fragment along the track. The caller passes `X[free], dy[free], h[free]`;
   `detector._rail_reference` builds `free` with `low_free_mask(n, clusters + self._low_height, xyz[:, 0], dy_rail)`, which with X and dy
   excludes the **full footprint** (X range × lateral range, every height) of every low cluster, weak ones included: **checked in
   the code, so neither the fragment nor a neighbouring low fragment can supply its own surface.**
4. **Two-sided and distinct support.** Both along-track sides (`x0−w … x0−0.3`, `x1+0.3 … x1+w`) must carry at least one such return, and at
   least two *distinct* returns (rounded to 1 mm, since the cloud holds every return twice) must lie within `rail_start_margin` (0.05 m)
   of the maximum; otherwise `None`.
5. **The rule.** `top <= surface + rail_start_margin`, with `top` = the larger of `height_max` and the footprint top (the B1 repair's top), so
   the cluster's upper body still counts. An object rising more than 0.05 m above the head's top surface is not rejected: the organizers'
   0.10 m object on a rail head rises 0.10 m (`config.py` comment).
6. **Unchanged behaviour.** The first rule is the same: `original` is now computed whenever `free` is not `None`, then
   `ref = min(ref, original)` exactly as before. Bug check on `d`: defined inside the same `if` block before the new use. Cost: a Python loop
   over the window's returns per qualifying cluster. Gate latency (information only, shared machine, 3 jobs each): p95 ride 75.7 → 71.8 ms,
   `doubleT_platform` 74.1 → 78.4 ms, set O 85.7 → 46.7 ms; the ride's **max** went 238 → 575 ms, one frame, **not investigated**.

**Residual risks I could not close (reported, not fixed).**
* The surface is a **maximum**. Anything in the band within ±5 m that is not a low cluster and rises above the head (rail fastenings, a weld,
  clutter, a taller object's lower returns) with two returns near its top raises the surface; a real low object whose top is within 0.05 m
  above that is rejected. The safety margin for the organizers' 0.10 m object is therefore the clutter height, 0.05 m or less. The trace
  below shows the rejected ride clusters' tops 0.14 m below to 0.035 m above their surface; **no real object on a rail exists in the ride data
  to test this against**, and `doubleT_obstacle`'s 0.10 m object on the right rail at 56 m is unchanged (0 rows differ).
* The branch is fed by `original` (all returns) and the surface (low-free returns); it assumes the cloud holds every return twice
  (a comment says "in this recording"), which is true of the Pandar bags; on a sensor without duplicates the distinct-return rule still holds.

## Which rows changed, and why (read-only trace)

`scripts/surface_trace.py` replays the gate's own pieces (`eval_real.run_piece`) with `_rail_surface_reference` and
`rail_reference_check` wrapped read-only; `scripts/change_summary.py` ties changed rows to the branch
([`out/change_summary.txt`](out/change_summary.txt), [`out/change_followup.txt`](out/change_followup.txt), records in `out/fb/surface_trace.tar.xz`).

| check | result |
|---|---|
| traced run equals the plain gate run | **0 of 1,409 / 1,409 / 1,409 / 1,408 / 345 rows differ** (ride pieces 1, 2, 4, 7 and `doubleT_platform`) |
| the recomputed rule equals the detector's verdict | on every traced cluster (0 mismatches); 83 clusters rejected by the new branch in these pieces |
| the margin | `top − surface` of the 83: −0.143 … **+0.035** m; none above 0.05 m |
| where rows change | only the ride (pieces 1, 2, 4, 7) and `doubleT_platform`: no real object in either; the rest of the gate, set O and `doubleT_obstacle` 0 rows |
| the effect on the gate metrics | ride alarm events 23 → **18**, STOP episodes 26 → **24**, alarm frames 111 → **102** (the pre-B1 values); `doubleT_platform` advisory frames 182 → 180; set O `inside_stop_frames` 414 = 414; empty recordings 7 / 11 / 37 = 7 / 11 / 37 |
| decision-word changes in the traced pieces | STOP → CAUTION 7, STOP → GO 2 (ride 7, rows 623–624), STOP → STOP 17 (same STOP distance kept, only the track `id` differs; one row, ride 4 row 266, also drops a second STOP detection while the main one stays), CAUTION → GO 9, GO → CAUTION 1, CAUTION → CAUTION 1,649 |

The 6 STOP frames lost on ride piece 1 (rows 1259–1261, 1265–1267; STOP at 42.1 → 36.9 m, lateral 0.74–1.06 m, then 35.8 → 23.6 m,
lateral −0.84 … −0.79 m) are the rail fragments the B1 repair had made STOP (F1a acceptance, tracks 288 and 305); the new branch rejects
clusters in those frames at lateral ±0.72–0.88 m, 0.1–1.4 m long, tops 0.06–0.25 m. The 2 STOP → GO frames (ride 7, 47.6 m, lateral 0.86 m, 0.65 × 0.25 × 0.02 m) are one cluster the branch rejects at
`top − surface` +0.008 m. **Ride 4 row 80 (21.8 m, lateral 1.23 m) is not directly attributed:** the branch rejects three clusters in the
frame at row 74 (31–42 m) and none in rows 77–80; the loss is an association effect through the tracker, **not traced through the old run's
lineage** (unverified). All these frames are on the ride, where the organizers confirm there is no obstacle.

## Findings

1. **The F1a completion gives back about half of the B1 repair on the ride**, in exchange for removing its measured cost: the ride's alarm
   events, STOP episodes and alarm frames return to the pre-B1 numbers. The risk it trades back is the one B1 named: a **long low object
   lying along a rail**, now rejected when its top is within 0.05 m of the highest non-low return in its band. The data cannot test that
   case (no such object on the ride; `doubleT_obstacle`'s object is a short 0.10 m one and is unchanged).
2. **X3 does not cover the changed rows.** Its four bags contain none of the ride or `doubleT_platform` rows that changed; X3's 0 of 260 says
   the F1a completion changes nothing on set O, `doubleT_obstacle` or the squareT / roundT bags, under pitch, roll, 5 Hz, dropout and dedup.
3. The Falcon record equal to `cc6226e` in all 4,443 rows confirms again that neither R3 nor the F1a completion touches it.

## Not verified / not done

* Anything after `fb92213`: P3 had not said code was final when I ran; a later change needs a new run.
* The F1a completion's one-row indirect effect (ride 4 row 80) through the old run's lineage.
* Real objects lying along a rail (none in the data); the 'surface' maximum's sensitivity to clutter on a recording with rail hardware.
* The full test suite, the ROS node tests (`test_node.py`) and Docker/CI.
* **Not started by this session:** the dust and marked-bag replay (the original assignment gave it to another P4 session; I was not
  asked to take it over and did not run it); **G3** (CLAUDE.md: only the fresh agent of the final check runs it, after P3 says code is done;
  I am not that agent and have no P3 confirmation); the J1 retarget and the N5 re-score (they follow the reseal).

## Files and reproduce

`scripts/surface_trace.py`, `scripts/change_summary.py`; `out/`: gate summary and per-frame rows, X3 summary and raw records, Falcon
record and stream hash, trace records, the comparison texts. Commands as in
[`../p4_review_h_mount_falcon_2026-10-20/README.md`](../p4_review_h_mount_falcon_2026-10-20/README.md), with `RESENSE_REPO` = a worktree at
`fb92213`:

```
python scripts/regression_gate.py --cache <cache> --jobs 3 --work OUT/gate --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json --out OUT/gate.json
python scripts/robustness_battery.py --repo $T --cache <decoded> --out OUT/x3.json -j 2 --reference docs/evidence/l16_acceptance_2026-10-20/out/x3_l16.json
curl -L <falcon_test.zst href> | python docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py /dev/stdin --out OUT/falcon
python docs/evidence/p4_acceptance_fb92213_2026-10-20/scripts/surface_trace.py <cache> OUT/trace --names doubleT_platform,new_data --pieces 1,2,4,7
python -I docs/evidence/p4_acceptance_fb92213_2026-10-20/scripts/change_summary.py <gate work cc6226e> OUT/gate OUT/trace
```
