# Organizer dust and the three marked bags on the final source (20.10)

> **Purpose:** the P0 row "Organizer dust and all three marked bags on H1 main / final reseal source", done so far only on
> `4cf8e27` and only as STOP summaries. Replay of the marked bags on the shipped source, per-frame comparison with the
> earlier records, dust at the 13 dust frames, per-object M-1 scoring (also for K2 variant B and v5c-15), the 12 background
> false STOPs, and the T1 rerun on the L16-repaired code. **Owner:** P4 · **Status:** measured, development data (not
> G3) · **Detector code:** not touched (evaluation only; overrides through `--set`, the dust guard stays off)

## Result in short

1. **The final source gives the 1.1.0 results on the three marked bags, in every field but one, in 1,663 of 1,667 frames.**
   Source: `main` `f56ad5e` (detector bytes of the R3 reseal `0a472d6`, `detector_freeze.py verify` PASS, 40 files). Against the
   committed 1.1.0 records (same clouds): decision, detections, warnings, `nearest`, `monitored`, mount, health: identical in
   all 1,667 frames. **Four frames differ in `clear`** (platform 316; tunnels 45, 52, 291), none in a decision. Cause, by
   ablation and by trace: **F1a's switch-on of 19.10** (`lowobj.local_rail_margin` 0.01). With it set to 0 the final source
   reproduces 1.1.0 in all 1,667 frames; with it on, F1a marks a rail-level cluster weak in exactly those 4 frames, at exactly
   the distance 1.1.0's `clear` stopped at. **The F1a repair (`f07f4b8`), the L16 repair (`4bf62f3`), R3 (`0a472d6`), H1 and
   H′ change nothing on these bags** (commit bisect, 7 commits, and one-switch ablations). The final source equals the
   committed `8c2bf51` K2-off records in all 1,667 frames, and its STOP summaries are byte-identical to the committed
   `4cf8e27` ones (3 of 3 bags).
2. **Dust: no STOP, no detection, no warning at any of the 30 dust boxes in the 13 dust frames.** 0 STOP; 6 CAUTION
   frames, each from a warning 1.8–152 m away on an object that approaches at about train speed through the frames before
   and after (not dust). The dust is 1–14 returns per 4–6 cm box. Deleting the dust returns from the cloud changes no
   decision in any of the 13 frames. With `dust.enabled=true` every frame is identical to the shipped (guard off) run: the
   guard does not see this dust either. Even 300 extra returns in each box for the one or two dust frames raise nothing; an
   object of 10 returns per box that *stays* is a STOP 4–5 frames after it appears (if the box is in the gauge): the
   delivered dust is below what the detector treats as an object because it does not persist, not because the check is blind.
3. **M-1 on the final source = the `8c2bf51` K2-off rows, all 13 objects, STOP frames and first STOP distance** (person
   147 / 44.0 m, platform cube 38 / 86.8 m, switch 35 / 51.4, 42 / 69.1, 11 / 110.6, 4 / 23.5, 41 / 104.0, tunnels 52 / 96.8,
   37 / 70.4, 29 / 55.0 m, the three left cubes never STOP). M-1 PASS.
4. **K2 variant B and v5c-15 on the final source equal the committed `8c2bf51` (and for B the `c9e8daa`) records in all
   1,667 frames.** M-1 FAIL on one object, as registered: tunnels cube right (id 19) 29 → 13 STOP frames, first STOP
   55.0 → 27.6 m. Every other object equal or better (platform cube 23: 38 → 40, 86.8 → 89.5 m; switch 12: 11 → 21; 13: 4 → 9;
   0: 35 → 37; tunnels big cube 52 → 55). B and v5c-15 give the same decisions and detections on these bags (they differ in
   `clear`, `monitored` and the warnings of 18 frames).
5. **The 12 background false STOPs of 1.1.0 are all still there**, detection by detection (distance, centre, size equal),
   also with the dust guard on. K2 variant B and v5c-15 remove all 12 (switch 7–12 GO, 13–14 CAUTION; tunnels 147–149, 367
   CAUTION). They are still no dust: structures with no marker.
6. **T1 on the L16-repaired code:** first 10 frames of each marked bag, share of returns above the sensor 29.1–31.5 %,
   share behind the sensor 0 %, `directional_axes` = +X in every frame, the calibrator's locked forward axis +X,
   `orientation_confirmed` true from frame 0 on all three bags, no orientation conflict. Equal to the numbers of the earlier
   T1 on the unrepaired code (`l16_exposure_2026-10-20`) and to P3's independent T1 on the repaired code
   ([`audit-t1.json`](../l16_open_air_2026-10-20/audit-t1.json): minimum above-sensor share 0.29113 / 0.30821 / 0.29794, +X,
   confirmed by frame 9): the repair only changes a branch these clouds never take.
7. **New, not asked: a replay is one sample.** Deleting 31 / 33 / 74 returns (of about 190,000 per frame, in 4–5 frames) changes
   the *later* decisions of the tunnels bag in 8–31 frames (K2 variant B: 19–43), the axis by up to 0.49 m, and the three false
   STOPs at tunnels 147–149 vanish in 3 of 5 perturbed runs (K2 off). The organizers' dust removed is one such perturbation
   and is **not** special: random returns deleted instead do the same (§7). Per-object STOP frames are stable under it
   (±0–1 frames; for M-1 the tunnels cube 19 stays lost in every perturbed run, B 14–18 frames against K2 off's 29).

## What ran

| item | value |
|---|---|
| source | `main` `f56ad5e` (`git worktree`, clean; `scripts/build_native.sh`; `detector_freeze.py verify` PASS, digest `6d091081…2452`, the R3 manifest) |
| data | `new_synth_data_with_markers.zst` from Yandex `SfBeRHbs8bNJAQ`, 2,533,631,921 B, sha256 `04d176b4…8682760` = the intake's value (checked after download), unpacked with `scripts/unpack_dataset.py`; 386 + 736 + 545 = 1,667 frames |
| runner | the jury runner (`judgement_2026-10-13/scripts/judge_runner.py`) through `p4_handoff_2026-10-20/scripts/judge_runner_set.py` (the same runner with `--set`); `RESENSE_REPO=<worktree>` `PYTHONPATH` the worktree `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1` |
| environment | Python 3.12.3, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, rosbags 0.11.5, native kernels; 4-core Xeon, 20–37 s per bag; open3d not needed by the runner (not installed) |
| markers | `synth_markers_2026-10-19/out/markers_<bag>.jsonl.xz` (committed, unchanged) |
| references | committed 1.1.0 records `synthetic_labels_2026-10-17/runs/detector_runs.tar.xz` (`v110_synthetic_<bag>.jsonl`), K2 runs `k2_v5c_2026-10-20/runs/data_8c2bf51/markers/`, `integration_2026-10-19/runs/marked_bags_k2B/` |
| not in the repository | `4cf8e27` itself (a branch that was never merged; `git cat-file` cannot find it), so only its STOP summaries (`integration_2026-10-19/runs/marked_bags_4cf8e27/`) could be compared |

The seal of this commit is the R3 one (`0a472d6`), not the earlier `cc6226e` of the brief: `main` moved on after PR #45. The
replays at `cc6226e` and at `0a472d6` are equal in all 1,667 frames, so the answer is the same for both.

## 1. Per-frame comparison with 1.1.0 / `4cf8e27` / `8c2bf51`

| comparison | platform 386 | switch 736 | tunnels 545 |
|---|---|---|---|
| final vs committed 1.1.0 records | `clear`: frame 316 | identical | `clear`: frames 45, 52, 291 |
| final vs committed `8c2bf51` K2-off records | identical | identical | identical |
| final vs the replay at `0a472d6` (R3 head) | identical | identical | identical |
| STOP summary vs the committed `4cf8e27` one | byte-identical | byte-identical | byte-identical |
| decisions (GO / CAUTION / STOP) | 66 / 135 / 185 | 300 / 294 / 142 | 196 / 223 / 126 |

[`out/diff_final_vs_v110.txt`](out/diff_final_vs_v110.txt) (every differing field, with values), `out/diff_final_vs_8c2bf51_off.txt`.
Compared: every field of the records except `decode_ms`, `detect_ms`, `total_ms`; health `msgs` after dropping the wall-clock
"latency" messages, and `level` only when those messages explain it (the rule of `compare_runs.py`).

**The four frames** ([`out/f1a_weak_*.json`](out/), [`pictures/f1a_*.png`](pictures/)):

| frame | 1.1.0 `clear` | final `clear` | decision (both) | F1a weak low cluster (trace) |
|---|---:|---:|---|---|
| platform 316 | 7.6 | 11.5 | STOP, the person at 11.5 m | at 7.61 m, 26 returns, 0.79 × 0.38 × 0.27 m, top 0.104 m |
| tunnels 45 | 58.5 | 121.9 | GO | at 58.55 m, 5 returns, 0.04 × 0.2 × 0.0 m, top 0.051 m |
| tunnels 52 | 50.5 | 127.0 | CAUTION (warning at 80.7 m) | at 50.46 m, 5 returns, 0.15 × 0.18 × 0.0 m, top 0.044 m |
| tunnels 291 | 36.2 | 40.9 | CAUTION (a `column` warning at 50.5 m) | at 36.15 m, 6 returns, 1.28 × 0.15 × 0.03 m, top 0.107 m |

In 1.1.0 a low cluster of a handful of returns at rail height capped `clear_distance` for that one frame (its neighbours
have no such cap: platform 315 and 317 clear 11.6 / 11.4, tunnels 44 and 46 clear 118.8 / 57.1). F1a (on since the captain's decision of 19.10) classes it as
rail-line fragments (top below the local rail-head reference + 1 cm), removes it from the clusters, and the cap is gone.
Each weak cluster lies at exactly the distance of the old `clear` (7.61 / 58.55 / 50.46 / 36.15 vs 7.6 / 58.5 / 50.5 / 36.2).
The pictures show returns at bed level, no object; no marker box is within 3.1 m forward of any of the four (the person
at 11.5 m is the nearest, platform 316). **F1a changed `clear` and nothing else on these bags, and removed no STOP or
warning of a marked object.**

**Which change does it, and which do not** ([`out/bisect_commits.txt`](out/bisect_commits.txt), [`out/ablation.txt`](out/ablation.txt)):

| run (same runner, same clouds) | vs committed 1.1.0 records |
|---|---|
| `3b7d7aa` (1.1.0) replayed here | **identical in all 1,667 frames** (control: this environment reproduces the committed records) |
| `0f02b28` (H1 + the 19.10 switch-ons), `cefd4c4`, `8c2bf51` (K2 code, off), `060bde7` (F1a repair), `cc6226e` (L16), `0a472d6` (R3), `f56ad5e` | the same 4 `clear` frames in every one, nothing else |
| final with `lowobj.local_rail_margin=0` (F1a off) | **identical in all 1,667 frames** |
| final with `cluster.column_core_margin=0` (H1 core off) | the same 4 frames as the final source |
| final with `cluster.mount_cross_tol=0` (H′ off) | the same 4 frames as the final source |

The F1a *repair* (`local_rail_exclude_low`, the independent reference; `060bde7`), the L16 repair (`directional_axes`
rejects ground half-spaces; `cc6226e` contains it), R3's cable confirmation (`0a472d6`), the H1 collision core and H′ therefore
have **no effect on any of the 1,667 frames**; the first difference to 1.1.0 appears with the merge that switched F1a on
(`0f02b28`). The trace (`scripts/trace_f1a.py`, a read-only wrap of `rail_reference_check`) fires F1a in 4 frames in all
(platform 1, switch 0, tunnels 3), exactly these, and its records equal the plain run's in all 1,667 frames.

## 2. Dust (13 frames, 30 boxes)

A dust box is a marker box with extent < 0.1 m in all axes (`per_object.py`'s rule). Each row: the frame's dust boxes
(marker id, forward / lateral / up in the sensor frame), the returns inside each box grown by 5 cm
([`out/dust_box_points_*.txt`](out/)), the final run's decision, and every detection or warning of the frame
([`out/dust_check_final_*.txt`](out/) has the full lines, including decisions of the frames i−3 … i+3).

| bag | frame | boxes | dust boxes (m) | returns in box | decision | detections / warnings of the frame | at a dust box |
|---|---:|---:|---|---|---|---|---:|
| platform | 21 | 2 | 0 (3.5, +1.5, +0.3); 1 (4.4, +1.8, +0.5) | 5/2 | GO | none | 0 |
| platform | 27 | 2 | 6 (4.4, +1.4, +0.5); 7 (6.1, +1.8, +0.3) | 7/1 | GO | none | 0 |
| platform | 35 | 2 | 12 (4.3, −0.4, +0.2); 13 (5.0, +0.2, +0.3) | 6/4 | CAUTION | warning 1.8 m | 0 |
| platform | 36 | 1 | 13 (3.9, +0.2, +0.3) | 6 | GO | none | 0 |
| switch | 481 | 2 | 2 (4.1, −0.6, +0.2); 3 (5.5, +0.3, +0.4) | 1/3 | CAUTION | warning 55.9 m | 0 |
| switch | 483 | 1 | 5 (4.8, +1.5, +0.3) | 2 | CAUTION | warning 52.9 m | 0 |
| switch | 611 | 3 | 7 (3.4, +1.4, +0.3); 8 (4.5, −0.3, +0.6); 9 (5.7, −1.5, +0.2) | 3/4/10 | CAUTION | warning 151.9 m (`beyond_height_ref`) | 0 |
| switch | 613 | 2 | 10 (4.9, −1.7, +0.5); 11 (6.9, +0.6, +0.2) | 5/5 | GO | none | 0 |
| tunnels | 70 | 3 | 3 (4.3, +0.6, +0.3); 4 (5.5, +1.5, +0.5); 5 (4.8, −1.6, +0.3) | 8/4/2 | GO | none | 0 |
| tunnels | 166 | 3 | 6 (4.5, +1.5, +0.4); 8 (6.1, −0.2, +0.2); 9 (7.2, +0.6, +0.1) | 1/2/10 | CAUTION | warnings 38.8, 50.2 m | 0 |
| tunnels | 167 | 3 | 7 (4.0, −1.4, +0.6); 8 (4.7, −0.2, +0.2); 9 (5.8, +0.6, +0.1) | 2/2/14 | CAUTION | warnings 37.1, 48.5 m | 0 |
| tunnels | 195 | 4 | 10 (3.8, −1.6, +0.4); 11 (4.4, −0.5, +0.2); 12 (5.7, +0.3, +0.5); 13 (6.3, +1.6, +0.2) | 6/3/6/8 | GO | none | 0 |
| tunnels | 446 | 2 | 15 (4.2, −1.4, +0.3); 16 (4.7, +1.5, +0.6) | 2/4 | GO | none | 0 |

**Totals:** 0 STOP, 6 CAUTION, 7 GO of 13 frames; 0 detections; 0 of 8 warnings within 1.0 m of a dust box's footprint
(`tight`) or by `per_object.py`'s rule (`coarse`). The 6 CAUTIONs agree with the 19.10 intake (13 frames, 6 CAUTIONs, none
at a dust box). The nearest warning to any dust box is 1.8 m ahead (platform 35: 0.12 m wide, 0.87 m *below* the sensor, 2.5 m
nearer than the boxes), the others are 31–150 m away. **None of the six is dust:** each warning is on an object that is
there in the neighbouring frames and approaches at about the train's speed: platform 34 → 35 at 3.2 → 1.75 m (1.45 m per frame),
switch 478–486 at 59.9 → 48.3 m, tunnels 163–168 at 43.8 → 35.5 m and 163–170 at 55.3 → 43.5 m, switch 608, 610–612 at 155.7 → 150.3 m
(consistent with static infrastructure the train passes; what they are was not identified). Pictures: [`pictures/dust_<bag>_<frame>.png`](pictures/), top view, side view (boxes red,
the cloud 0–14 m) and a 0–160 m overview with every detection (blue) and warning (orange), e.g.
[platform 35](pictures/dust_platform_0035.png), [switch 611](pictures/dust_switch_0611.png),
[tunnels 167](pictures/dust_tunnels_0167.png).

**With `--set dust.enabled=true`** ([`runs/final_dustguard_on_*.jsonl.xz`](runs/), information only): identical to the shipped
run in every non-timing field, 1,667 of 1,667 frames. The same dust-frame table results.

**Positive controls** (CLAUDE.md: a negative counts only if the same tool finds the known positive):

| control | result |
|---|---|
| the matching rules find a detection put on a dust box | 30 / 30 boxes (`tight` and `coarse`); a detection 20 m beyond the box: 0 / 30 (`dust_check.py` exits 3 if either fails) |
| the same rules find the real objects: STOP frames with a known object in range that `coarse` matches | 185 / 185 platform, 133 / 141 switch, 118 / 121 tunnels (the rest are the unmatched background / beam detections of §5) |
| the dust is in the cloud and the boxes sit on it | every one of the 30 boxes holds 1–14 returns (box + 5 cm), the person's parts and cubes in the same pictures sit on their points, as in the intake |
| `--set dust.enabled=true` reaches the detector | [`out/dust_control_*.txt`](out/): uniform volumetric returns (1/m³, 5–60 m, ±1 m, 2 m high) in the first 40 frames: guard off STOP in 31 / 24 / 18 of 40 frames (platform / switch / tunnels; without the added dust 0 / 8 / 0), guard on CAUTION in 40 / 16 / 40 with the "visibility degraded" message (switch: 24 STOP remain); guard on without dust equals guard off in 40 / 40 frames |
| a real object at a dust box is detected if it stays | [`out/dust_amp_*_persist.txt`](out/dust_amp_platform_persist.txt): 10 returns per box, injected at the first dust frame's boxes in 13 consecutive frames (6 before to 6 after): first STOP at the boxes at frame 34 (platform), 68 (tunnels), 479 (switch), 4–5 frames after the injection starts (the platform bursts 21 and 27 lie 1.4–1.8 m left of the sensor axis, outside the gauge, and give no STOP; the burst at 35 does); the returns are really added (K × boxes: 70, 80, 150 in the single mode) |
| the dust returns deleted | [`remove_boxes.py --dust`](scripts/remove_boxes.py), [`out/dust_removed_*.removed.json`](out/): the returns inside the 30 boxes (+5 cm) deleted (31 / 33 / 74 returns in 4 / 4 / 5 frames): the decision, `clear` and the number of warnings are unchanged in all 13 dust frames; `n_points` differs, and `curv` by 7·10⁻¹¹ … 6·10⁻⁹ in platform 35 and 36, switch 611 and 613 and tunnels 70 (float level; 0 in the other four platform and switch frames). In tunnels 166, 167, 195, 446 the differences (`curv` 8·10⁻⁶ … 1.4·10⁻⁴, `track_center` ≤ 4 mm, warning values) have grown since frame 70: later decisions change in the tunnels bag, §7. Control of the tool: 1,266 returns of the platform cube 23 deleted in frames 100–140 remove all its STOP frames there (106–118 → none; [`out/remove_control_cube23.txt`](out/remove_control_cube23.txt)); a null deletion (margin −1, tunnels) equals the delivered run in all 545 frames |
| the same returns for the 1–2 dust frames only | [`out/dust_amp_*_single.txt`](out/dust_amp_platform_single.txt): K = 10, 30, 100, 300 extra returns in each dust box in the dust frames: no detection or warning at any box (guard off and on), decisions unchanged |

**Limits.** The delivered dust is a few returns for one or two frames. The detector does not react to it because a track needs
several frames, not because it has a dust rule (the guard is off and sees nothing either). This is **not evidence for dense
or sustained dust**: the control above (uniform 1/m³) gives false STOPs with the guard off in all three bags, and the guard
leaves 24 STOP frames on the switch (`out/dust_control_switch.txt`; the N3 battery is the real test and is not repeated
here). Caveat of the persist control on tunnels: frames 440–444 are the real 2 m cube (a STOP at a "box" even at K = 0).

## 3. Per marked object, M-1 on the final source (K2 off)

[`scripts/score_m1.py`](scripts/score_m1.py) (the matching of `per_object.py`; its output text equals `per_object.py`'s run on
the committed `8c2bf51` records byte for byte, 3 of 3 bags). A = the committed `8c2bf51` K2-off rows of
[`k2_v5c_2026-10-20/README.md`](../k2_v5c_2026-10-20/README.md) §6 / `n5_markers_2026-10-20` (records `off_<bag>.jsonl.xz`),
B = the final source. [`out/score_m1.txt`](out/score_m1.txt), `out/per_object_8c2bf51off_vs_final_*.txt`.

| bag | object | marker id | frames | STOP frames 8c2bf51 → final | first STOP (m) | warnings |
|---|---|---|---:|---|---|---|
| platform | person (8 parts) | 15–22 | 198–329 | 147 → 147 (each part) | 44.0 → 44.0 | 51–127 → same |
| platform | small cube right | 23 | 175 | 38 → 38 | 86.8 → 86.8 | 40 → 40 |
| platform | small cube left | 24 | 188 | 0 → 0 | — | 28 → 28 |
| switch | small cube on the left rail | 0 | 102 | 35 → 35 | 51.4 → 51.4 | 9 → 9 |
| switch | hanging inclined cable | 1 | 139 | 42 → 42 | 69.1 → 69.1 | 6 → 6 |
| switch | small cube right (first) | 12 | 255 | 11 → 11 | 110.6 → 110.6 | 100 → 100 |
| switch | small cube left | 13 | 51 | 4 → 4 | 23.5 → 23.5 | 0 → 0 |
| switch | small cube right (last) | 14 | 140 | 41 → 41 | 104.0 → 104.0 | 30 → 30 |
| tunnels | big cube 2 × 2 × 2 m | 0 | 102 | 52 → 52 | 96.8 → 96.8 | 13 → 13 |
| tunnels | beam across the rails | 1 | 50 | 37 → 37 | 70.4 → 70.4 | 0 → 0 |
| tunnels | small cube left (first, missing in N5) | 18 | 34 | 0 → 0 | — | 0 → 0 |
| tunnels | small cube right | 19 | 101 | 29 → 29 | 55.0 → 55.0 | 0 → 0 |
| tunnels | small cube left (last) | 20 | 49 | 0 → 0 | — | 6 → 6 |

Every row equals the K2 README's K2-off row (and the per-frame records are identical, §1), so the final source does not
change a marked object's STOP frames by one. The three left cubes that never STOP (24, 18, 20) still do not: platform 24 and
tunnels 20 are warnings in 28 and 6 frames, tunnels 18 nothing; their inner faces sit 1.2–1.3 m left of the sensor axis (probably outside the gauge, not checked against the rails; see the n5 README).

## 4. K2 variant B and v5c-15 on the final source (for the K2 session)

Overrides, as in the handoff: variant B `--set track.axis_joint_fit=true --set track.axis_joint_range=false --set
track.axis_joint_min_curvature=0.0001 --set track.axis_joint_reach_cap=true`; v5c-15 adds `--set
track.axis_joint_reach_dual=15.0`. Per-frame records: [`runs/final_k2B_<bag>.jsonl.xz`](runs/),
[`runs/final_k2v5c15_<bag>.jsonl.xz`](runs/), and the final K2-off run [`runs/final_f56ad5e_<bag>.jsonl.xz`](runs/).

| bag | object (id) | STOP frames final → B | STOP frames final → v5c-15 | first STOP final → B / v5c-15 (m) | M-1 |
|---|---|---|---|---|---|
| platform | person (15–22) | 147 → 147 | 147 → 147 | 44.0 → 44.0 | equal |
| platform | cube right (23) | 38 → 40 (+104, 105) | 38 → 40 | 86.8 → 89.5 | better |
| platform | cube left (24) | 0 → 0 (28 → 27 warnings) | same | — | equal |
| switch | cube on left rail (0) | 35 → 37 (+316, 317) | 35 → 37 | 51.4 → 54.0 | better |
| switch | cable (1) | 42 → 42 | 42 → 42 | 69.1 → 69.1 | equal |
| switch | cube right first (12) | 11 → 21 | 11 → 21 | 110.6 → 110.6 | better |
| switch | cube left (13) | 4 → 9 | 4 → 9 | 23.5 → 26.5 | better |
| switch | cube right last (14) | 41 → 41 | 41 → 41 | 104.0 → 104.0 | equal |
| tunnels | big cube (0) | 52 → 55 (+388–390) | 52 → 55 | 96.8 → 100.4 | better |
| tunnels | beam (1) | 37 → 37 | 37 → 37 | 70.4 → 70.4 | equal |
| tunnels | cube left first (18) | 0 → 0 | 0 → 0 | — | equal |
| tunnels | **cube right (19)** | **29 → 13** (lost 259–273, 279) | **29 → 13** | **55.0 → 27.6** | **WORSE** |
| tunnels | cube left last (20) | 0 → 0 (6 → 6 warnings) | same | — | equal |

**M-1: FAIL for both, on tunnels id 19 only** (the registered prediction; the same frames as in the K2 README §6 and the
n5 README: 259–273 and 279). **Both K2 runs on the final source equal the committed K2 runs in all 1,667 frames** (variant B vs
`8c2bf51` and vs `c9e8daa`, v5c-15 vs `8c2bf51`: identical in every non-timing field), so every K2 number measured on `8c2bf51`
holds unchanged for the final source on these bags. Decisions (GO / CAUTION / STOP): B and v5c-15 platform 68 / 131 / 187, switch
336 / 249 / 151, tunnels 284 / 152 / 109 (K2 off: 66 / 135 / 185, 300 / 294 / 142, 196 / 223 / 126). Differences B vs v5c-15: `clear`
and `monitored` (v5c-15 extends the trusted range), the warnings in 6 + 12 frames; no detection and no decision differs. Control: the
committed v5c-30 records scored with the same script flag platform id 23 (38 → 31, 86.8 → 76.4 m) and id 19, as the K2 README says.
To reuse: `python -I scripts/score_m1.py --markers <dir with markers_<bag>.jsonl> --ref <ref prefix> --cand NAME=<prefix>`
(prefix + `_<bag>.jsonl`); one call scores all three bags and prints the M-1 verdict.

## 5. The 12 background false STOPs of 1.1.0

| frames | 1.1.0 | final | final, guard on | B / v5c-15 |
|---|---|---|---|---|
| switch 7–14 (147 m, 8 frames) | STOP | **STOP**, detections identical (d 147.11 … 142.40, lateral +1.34 … +1.52 m) | STOP | 7–12 GO, 13–14 CAUTION |
| tunnels 147–149 (70–67 m, wall in a curve) | STOP | **STOP**, identical | STOP | CAUTION |
| tunnels 367 (131.5 m, below rail level) | STOP | **STOP**, identical | STOP | CAUTION |

Still unmatched to any marker by the intake's rule ([`out/stops_vs_markers_final_*.txt`](out/): 142 STOP detections on the
switch, 133 matched, 9 unmatched = these 8 + frame 416; tunnels 128, 120 matched, 8 unmatched = these 4 + 439–441 + 460;
platform 185 of 185). Pictures ([`pictures/bg_switch_*.png`](pictures/), [`bg_tunnels_*.png`](pictures/)): a thin vertical stripe of returns, 1 m tall, 147 m ahead and 1.3 m left of the
axis (switch 7; no marker near), a cluster in the tunnel wall in the curve (tunnels 148). F1a, L16 and R3 did not touch them.
With K2 B / v5c-15 the other unmatched detections stay (switch 416, tunnels 439–441, 460), the 12 go.

## 6. T1: the open-air cue on the L16-repaired code (first 10 frames)

[`out/t1_table_final.txt`](out/t1_table_final.txt), probe [`scripts/t1_probe_p4.py`](scripts/t1_probe_p4.py) (the wrap of
`MountCalibrator.update` / `directional_axes` of `l16_exposure_2026-10-20/scripts/t1_probe.py`, read-only, plus the calibrator's confirmation state).

| marked bag | returns above the sensor (z > 0) | behind (x < 0) | `directional_axes` | locked forward | `orientation_confirmed` | conflict frames | probed run = plain run |
|---|---|---|---|---|---|---:|---|
| platform | 29.1–29.8 % | 0 % | +X (all 10 frames) | +X | true from frame 0 | 0 | identical, 10 rows |
| switch | 30.8–31.5 % | 0 % | +X | +X | true from frame 0 | 0 | identical |
| tunnels | 29.8–30.0 % | 0 % | +X | +X | true from frame 0 | 0 | identical |

The mapping in force stays `configured` (forward −y, left +x, up +z → +X), the calibrator's tilt status is `pending` in all of
these frames (`mount` in the runner records: tilt calibration is unfinished in the first frames; the orientation is confirmed
separately). The bags are cropped forward (no returns with x < 0), so +X *is* the one-sided axis and the cue is correct, not
a case of the A1 bug (a full revolution starting in open air, below ~1.5–2 % returns above the sensor). The numbers equal the
earlier T1 table of the unrepaired code to the fourth decimal (platform 0.2911–0.2984, switch 0.3082–0.3148, tunnels 0.2979–0.3000) and
P3's independent minima (0.29113, 0.30821, 0.29794, `audit-t1.json`, a separate decoder).
**Control** ([`out/t1_control_wrong_mapping.txt`](out/t1_control_wrong_mapping.txt)): the same platform frames with a deliberately
wrong configured mapping (`+x / +y / +z`): `orientation_confirmed` false and a conflict in frame 0 ("alternative orientation
awaiting confirmation"), the correct `forward=-y left=+x up=+z` found and confirmed from frame 1: the flag is not constant.
The repair itself (a full-revolution open-air start) is P3's `fault_open_air` and not rerun here; no recording or marked bag
in the data starts in open air.

## 7. A replay is one sample: what deleting a few returns does (not asked; found while checking the dust)

Deleting the dust returns (§2) is a counterfactual, and it changes *later* decisions of the tunnels bag. To see whether that
is the dust or the replay, the same number of returns was deleted at random instead ([`scripts/remove_boxes.py`](scripts/remove_boxes.py),
`--random-seed`): the same frames, 3–8 m ahead, |lateral| < 2.5 m, outside the dust boxes. Table: frames whose **decision**
differs from the delivered-bag run of the same configuration, per perturbed run ([`out/sensitivity_decisions.txt`](out/sensitivity_decisions.txt)).

| configuration | bag (returns deleted) | dust deleted | random, seeds 1–4 | max axis difference (`track_center`) |
|---|---|---|---|---|
| K2 off | platform (31) | 0 | 2, 0, 0, 0 | ≤ 0.06 m |
| K2 off | switch (33) | 0 | 0, 13, 0, 0 | ≤ 0.03 m |
| K2 off | tunnels (74) | 18 | 31, 24, 9, 8 | 0.47–0.49 m |
| K2 off | tunnels, 8 returns in each of the frames 30, 50, 100, 130, 250 (no dust) | – | 10, 25, 15 (seeds 1–3) | 0.34–0.49 m |
| K2 variant B | platform | 0 | 2, 0, 1, 0 | ≤ 0.08 m |
| K2 variant B | switch | 0 | 0, 16, 0, 0 | ≤ 0.06 m |
| K2 variant B | tunnels | 19 | 37, 43, 27, 26 | 0.47–0.49 m |

* **Not special to the dust.** The dust deleted never changes more decisions than the random deletions do (tunnels, K2 off: 18 vs
  8–31; variant B: 19 vs 26–43; platform and switch: 0). Not special to dust frames either (the 40 returns at non-dust frames: 10–25).
* **The mechanism looks like amplification, not a dust effect on the axis.** At the dust frames themselves the difference is at float
  level (`curv` 7·10⁻¹¹ … 6·10⁻⁹, `track_center` 0.000). It grows with the frames after the first change: tunnels, dust deleted,
  max |Δcurv| 3·10⁻⁸ (frames 70–100), 5·10⁻⁷ (100–130), 7·10⁻⁵ (130–160), 8·10⁻⁴ (200–300), and the axis moves by up to 0.49 m
  ([`out/sensitivity_nondust_and_growth.txt`](out/sensitivity_nondust_and_growth.txt)). Why the axis estimate amplifies a 10⁻⁸ difference was **not investigated**.
  The switch is almost insensitive (one random seed in four makes a difference), the platform nearly so.
* **Controls.** A null deletion (margin −1) equals the delivered tunnels run in all 545 frames, so the transform itself changes
  nothing; repeated replays of one configuration (the final run, the plain runner, the F1a trace, the replay at `0a472d6`) are identical in all frames. Deleting a *real* object's returns (§2) removes its STOPs.
* **The 12 background false STOPs are fragile.** With K2 off, the 4 tunnels frames (147–149, 367) stay STOP in 1, 0, 1, 3, 3 of 4 frames
  across the five perturbed runs (dust deleted, seeds 1–4) and in 3 of 4 in the three non-dust runs; the 8 switch frames stay in all
  of them. With K2 variant B none of the 12 is STOP in any of the ten perturbed runs.
* **Per-object STOP counts (M-1) are stable.** [`out/noise_floor_k2off.txt`](out/noise_floor_k2off.txt), [`out/noise_floor_k2B.txt`](out/noise_floor_k2B.txt)
  (five perturbed runs each: dust deleted, seeds 1–4): K2 off differs from the delivered run by 0 frames for 12 of 13 objects
  and by 1 frame (51–52) for the tunnels big cube (first STOP 94.4–96.8 m). Variant B: platform cube 23 39–40 (first STOP
  87.7–89.5 m), switch cube 13 6–9, tunnels big cube 54–55 (99.1–100.4 m), all others 0 spread. **Tunnels cube 19: B has 14–18 STOP
  frames (first STOP 27.6–48.8 m) in the five perturbed runs and 13 (27.6 m) in the delivered run, against K2 off's 29 (55.0 m) in
  all six, so the M-1 loss is real, not noise,** while it can vary by a few frames. B's gains are outside the spread too, the ranges
  do not overlap: platform 23 38 vs 39–40, tunnels big cube 51–52 vs 54–55, switch 0 35 vs 37, switch 12 11 vs 21, switch 13 4 vs 6–9.

What this means: quote the delivered replay as what it is (a deterministic result, reproduced here bit for bit across
commits), and do not read frame-level differences in the tunnels bag, or STOP-frame differences of one or two frames, as
effects of a change without a perturbation ensemble like this one. It does not change the dust answer (§2), the F1a
attribution (§1: that comparison is between deterministic replays of the *same* clouds) or the M-1 verdicts (§3, §4).

## How it was checked

| check | method | result |
|---|---|---|
| the environment reproduces committed runs | the 1.1.0 source `3b7d7aa` replayed on the marked bags, all fields vs the committed `v110_synthetic_<bag>.jsonl` (`compare_runs.py`'s rule, `field_diff.py`) | identical, 1,667 frames |
| the comparison finds differences | the same tool, final vs 1.1.0; and F1a-off / H1-off / H′-off ablations vs 1.1.0 | 4 frames found; F1a off removes all 4, the other two none; positive control for "no difference" (F1a repair, L16, R3) |
| the final replay is not an artefact of the wrapper | `judge_runner.py` (plain) vs `judge_runner_set.py` with no overrides, tunnels | identical, 545 frames |
| attribution is by trace, not reconstruction | `trace_f1a.py` wraps `rail_reference_check`, records every weak cluster | 4 frames, at the distance of the old `clear`; traced records equal plain, 1,667 frames (rule 6) |
| per-object scoring | `score_m1.py` vs `per_object.py` text, v5c-30 control | byte-equal, 3 / 3 bags; control flags platform 23 and tunnels 19 |
| STOPs vs markers | `stops_vs_markers.py` on final, B, v5c-15, 1.1.0 | final = committed `4cf8e27` and 19.10 1.1.0 text, byte-identical; 185/185, 133/142, 120/128 |
| dust | `dust_check.py` with built-in controls, pictures of all 13 frames, returns per box, injection controls | §2 |
| T1 | `t1_probe_p4.py` | §6 |
| the removal / perturbation tool | null deletion equals the delivered run (545 / 545); deleting the returns of a real object (platform cube 23, frames 100–140) removes its STOP frames; random deletions of the same count as the dust | §2, §7 |
| physical plausibility | distances of warnings move 1.4–1.8 m per frame (train 14–18 m/s), dust boxes 3.4–7.2 m ahead and 0.1–0.6 m above the sensor, 3–6 cm | consistent with the intake; F1a clusters 4–10 cm tall, 5–26 returns |

## Not checked / limits

* `4cf8e27` has no per-frame record in the repository; the "4cf8e27 comparison" is the committed STOP summaries (byte-equal)
  plus 1.1.0 and `8c2bf51` per frame. **Not compared:** `4cf8e27`'s `clear` values.
* The four `clear` frames were attributed by one-switch ablation and by trace on the final source; the bisect is over seven
  commits, so a change *between* them that cancels another is not excluded for other data. Only these bags.
* The dust result is for the delivered tiny, short bursts; it is not a dense-dust result (the control shows false STOPs with the
  guard off at 1/m³ and the guard does not remove them on the switch).
* "At a dust box" uses the detection footprint ±1 m (tight) and `per_object.py`'s rule (coarse); the vehicle frame is the
  mount-calibrated sensor frame, close to the markers' frame at 3–7 m (centimetres). The records have no cluster list below
  detections / warnings, so a cluster that is neither cannot be seen; `clear` is 94–165 m in 12 of the 13 dust frames, and **0.0 m
  at tunnels 446** (GO; the same 0.0 with the dust deleted, and the same in 1.1.0; frames 444–446 follow the train's arrival at the 2 m cube; the cause of `clear` 0.0 was not investigated).
* GO frames with `clear` < 5 m exist unchanged from 1.1.0 (switch 354, tunnels 445–446, just after the train reached an object); not
  investigated.
* Not run: the gate, X3 and Falcon (P3 / P1 own them); G3 not touched; detector code not touched.

## Reproduce

```
R=<worktree of f56ad5e, scripts/build_native.sh run>; B=<unpacked bags>; E=docs/evidence; P=$E/p4_dust_markers_final_2026-10-20
export RESENSE_REPO=$R PYTHONPATH=$R:$R/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python $R/scripts/unpack_dataset.py new_synth_data_with_markers.zst --out $B           # sha256 04d176b4…8682760
for b in platform switch tunnels; do
  python $E/p4_handoff_2026-10-20/scripts/judge_runner_set.py --bag $B/synthetic_${b}_cloud_with_markers --out final_$b
  ... --out dust_$b --set dust.enabled=true
  ... --out B_$b --set track.axis_joint_fit=true --set track.axis_joint_range=false --set track.axis_joint_min_curvature=0.0001 --set track.axis_joint_reach_cap=true
  ... --out v5c15_$b <the same four> --set track.axis_joint_reach_dual=15.0
  ... --out f1aoff_$b --set lowobj.local_rail_margin=0
  python $P/scripts/trace_f1a.py $B/synthetic_${b}_cloud_with_markers trace_$b
  python $P/scripts/dust_check.py markers_$b.jsonl final_$b.jsonl --json dust_$b.json
  python $P/scripts/dust_frames.py $B/synthetic_${b}_cloud_with_markers markers_$b.jsonl final_$b.jsonl pictures/dust_$b
  python $P/scripts/dust_amp.py  $B/synthetic_${b}_cloud_with_markers markers_$b.jsonl --ref final_$b.jsonl [--persist 6]
  python $P/scripts/t1_probe_p4.py t1_$b $E/p4_handoff_2026-10-20/scripts/judge_runner_set.py --bag ... --out t1_${b}_probe --limit 10
done
python $P/scripts/dust_control.py $B/synthetic_platform_cloud_with_markers --frames 40 --density 1.0
python $P/scripts/remove_boxes.py $B/synthetic_${b}_cloud_with_markers markers_$b.jsonl nodust_$b --dust [--random-seed N] [--set k=v ...]
python -I $P/scripts/noise_floor.py --markers <dir> --base final --ens nodust rnd1 rnd2 rnd3 rnd4     # prefix + _<bag>.jsonl
python -I $P/scripts/field_diff.py final $E/..v110_synthetic --verbose          # prefix + _<bag>.jsonl
python -I $P/scripts/score_m1.py --markers <dir> --ref <8c2bf51 off prefix> --cand final=final --cand k2B=B --cand v5c15=v5c15
# bisect: git worktree add --detach <dir> <commit>; scripts/build_native.sh; the same runner with RESENSE_REPO=<dir>
```

## Files

* [`runs/`](runs/): per-frame jury-runner records (xz, one JSON line per frame): `final_f56ad5e_<bag>` (shipped, K2 off, guard off),
  `final_dustguard_on_<bag>`, `final_dust_removed_<bag>` (the dust returns deleted), `final_k2B_<bag>`, `final_k2v5c15_<bag>`, `final_f1a_off_<bag>`, and the 1.1.0 source `3b7d7aa`
  replayed on the marked bags, `v110_3b7d7aa_marked_<bag>` (the 19.10 replay was not committed).
* [`out/`](out/): the comparisons, dust, M-1, T1, trace and control outputs named above.
* [`pictures/`](pictures/): `dust_*` (13 dust frames), `f1a_*` (the 4 frames), `bg_*` (background STOPs).
* [`scripts/`](scripts/): `dust_check.py`, `dust_frames.py`, `dust_control.py`, `dust_amp.py`, `field_diff.py`, `score_m1.py`,
  `trace_f1a.py`, `f1a_frames.py`, `remove_boxes.py`, `noise_floor.py`, `t1_probe_p4.py`, `t1_table_p4.py` (`per_object.py`, `stops_vs_markers.py`, `compare_runs.py`
  and `marker_frames.py` are reused from the earlier evidence folders, unchanged).
* [`SHA256SUMS`](SHA256SUMS).
