# P4 review of two switches that are on: H′ mount cross-check and the Falcon clear-distance model (20.10)

> **For:** Pavel, P3 and the captain · **From:** P4 (evaluation), the independent review of the seal's step 3
> ([`DETECTOR_FREEZE.md`](../../DETECTOR_FREEZE.md)) for two of the switches that the seal does not review ·
> **Detector code:** not touched (`resense/`, `native/`, `configs/` and the ROS package are byte-identical to the sealed
> `cc6226e`; see the table) · **Source reviewed:** `cc6226e` (seal manifest
> [`detector_freeze_2026-10-20_1.2.0_f1a_l16.json`](../detector_freeze_2026-10-20_1.2.0_f1a_l16.json)), detector tree
> identical to `5fa865b`, the source of the reused shipped-source runs · environment: Python 3.12.3, numpy 1.26.4, scipy 1.13.1,
> `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`, native kernels built in the worktree with `scripts/build_native.sh` ·
> **Not touched:** G3, any detector change. This record reports disagreements and does not fix them.
> **Main has moved since** (`f56ad5e`: R3 completion, detector files `resense/clustering.py` and `resense/tracking.py` differ from
> `cc6226e`; new seal `0a472d6`). The Falcon pair and the H′-off gate were rerun on `f56ad5e`; every number below carries over (section
> "Current main"). X3 was not rerun there.

## Answer

### (a) H′ mount cross-check, `cluster.mount_cross_tol` 0.5

**Claim: "removes the 8 false STOP frames on the Falcon tunnel ceiling and changes 0 gate rows."**

| part of the claim | result |
|---|---|
| removes 8 STOP frames on the Falcon | **confirmed.** With H′ off exactly frames 4394–4401 are STOP where the shipped run is CAUTION; no other frame of 4,443 differs in decision, detections or warnings; STOP frames 1,364 shipped, 1,372 off; no STOP only with H′ on |
| they are false | **confirmed on the raw returns.** The 8 STOPs stand on clusters at 9.4–11.2 m whose returns are 4.14–4.31 m above the calibrated mount's rail-head plane, on the tunnel ceiling (pictures below). The same frames' only object on the track is the person at 2.5–6 m, and neither run reports a STOP on it there (finding 1) |
| changes 0 gate rows | **confirmed, with a caveat.** The full gate with H′ off (`--set cluster.mount_cross_tol=0`, seal baseline, no `--allow`): **exit 0**, 8 gated rows better, none worse, the same as the shipped gate. Against the shipped per-frame rows: **15,269 rows, 0 differ** in any non-timing field (735 differ only in the latency-driven health level; the first run, whose set F step failed on a missing libEGL, gave the same 15,269 / 0). Set F straight: only the config hash, the wall time and the ground truth's `gt_vehicle_y_m` (ICP odometry, at most 7e-9 m) differ in 65,121 values; no detector field. The caveat is finding 2: the check is never armed on this data |
| X3 | not worse: **0 of 260** comparisons fail, and in **40 of 40** cases every row's decision, detections and warnings equal the shipped run's (29,765 rows; 401 rows differ only in the latency health level / message) |
| no STOP on a real object is lost | **confirmed on the person, the recording's known object:** all 1,360 person STOP frames are STOP in both runs (positive control: below). Not shown for anything else: the gate and X3 contain almost no case the check can act on (finding 2) |

**Attribution of the 8 frames** (read-only trace, `falcon_pair.py`; both replicas in one pass of the stream):

| frames | what H′ does | off run |
|---|---|---|
| 4394, 4396, 4397, 4398 | H′ makes the ceiling cluster at 9.4–9.7 m (and at 11.1–11.2 m, track 1106) advisory `height_conflict`: model rail head 2.19–2.27 m, mount plane −1.772 m, disagreement 3.96–4.04 m against a threshold of 0.97–1.06 m; every point is 4.14–4.31 m above the plane, above the envelope top (3.0 m) | the same clusters are STOP detections of tracks 1105 / 1106 (hits 5–7, `zone_hist` all 1) |
| 4395, 4399 | the reporting track 1105 (shipped: a `height_conflict` warning) coasts on a missed hit (misses 1) | STOP at the track's predicted place (9.16 / 9.68 m) |
| 4400, 4401 | no H′ action in these frames: the cluster is a plain `elevated` warning at 9.39 m (2.09–2.21 m above the model rail head) | the track earned its STOP in 4394–4399 and `stop_hold` carries it |

So 6 of the 8 frames are H′ demotions (two of them through the track's coast) and 2 are the stop-hold of a STOP that only exists
with H′ off, which matches the author's own account (`f1_false_alarms_2026-10-19/PROTOCOL.md`: "the track never earned a STOP, so
nothing is held at 4400–4401"). Mechanism: after the person shadowed the bed, the track model's floor fit climbed to the ceiling
(`floor_coef` [0, 0.044, 1.438] in 4387–4398; the whole recording before: ≈ −1.98); the mount plane (frozen calibration) did not.

**Positive control for "H′ does not demote a real object".** The hook looked at 265 gauge clusters within 30 m on the whole
Falcon recording. 31 had a model / mount disagreement over the threshold. **20 were demoted: all on the ceiling** (4.14–4.31 m
above the plane). **11 were kept: the person**, in frames 4371, 4376–4381 and 4410, at 1.20–1.59 m above the plane, where H′ is armed
(the model had lost the bed) and still leaves the person's cluster an obstacle because the mount puts it inside the envelope's
height band. The demotion needs all of a cluster's points above 3.0 m
(`mount_cross_above_only`): the margin to a person is about 1.4 m of plane error.

**Pictures** ([`out/png/`](out/png/)): `falcon_f4383/4394/4396/4398/4400.png` draw shipped and H′-off side by side, the model rail
head, the mount plane and its envelope top, the clusters H′ looked at (red demoted, blue kept) and the clusters of the reported
detections. The ceiling is the sheet of returns at Z ≈ +2.5 m in every frame, and the demoted cluster is part of it.

### (b) The Falcon clear-distance model, `small_target_limit('falcon_prime')`

**Claim: "reports up to 48.2 m from the measured Falcon raster (density model, as for Pandar) instead of 0."**

| part of the claim | result |
|---|---|
| 48.2 m | **confirmed.** `small_target_limit('falcon_prime')` = 48.2518 m, equal to the closed form `√(0.3·0.3 / (3 · 0.18° · 0.235°))` = 48.2518 m, reported rounded down to the decimetre: 48.2 m; the largest clear distance over the 4,443 frames is 48.2 m (4,053 frames at it). The Pandar limit is unchanged (88.76 m) |
| instead of 0 | **confirmed, with the model off defined from the source.** Before 19.10 `small_target_limit` returned `None` for every model but `pandar128` (`0acb18c^`), so the conservative policy set the Falcon's clear distance to 0 in all 4,443 frames; with the model on it is above 0 in 4,442 (frame 0 is a FAULT, 0 either way) |
| it is "on" | **only in a non-default path.** It acts only in the ROS node's non-legacy range policy (`clear_range_policy:=conservative` or `small_candidate`; the launch default is `legacy`, which never calls it) with a Falcon sensor profile (`falcon_ros` / `falcon_native`) or `range_sensor_model:=falcon_prime`. The detector (`resense/`) never calls it: 0 calls in the whole-Falcon run of both replicas, so the gate and X3 cannot see this switch, and no "switch-off gate / X3" exists for it. The documented demo commands use `conservative` ([`README.md`](../../../README.md), [`gitbook/.../run-on-a-bag.md`](../../../gitbook/getting-started/run-on-a-bag.md)) |
| no decision changes | **confirmed:** in the node's own path on every Falcon frame (`candidate_ranges` after `evaluate_decision`, policies conservative and small_candidate, model on and off), 0 of 4,443 decisions differ from the detector's |
| no STOP lost | the model only caps `clear_distance`; STOP, detections and warnings are not its inputs or outputs (above) |

**Disagreements for P3 (not fixed here):**

1. **The model lets the detector's own clear distance through where it used to report 0, and on the Falcon that distance is wrong
   when the track model has lost the bed.** In **38 frames (4373–4414)** the node would report a clear distance beyond the
   nearest return on the track while the frame is not STOP: the person is at 2.5–7 m (205–1,159 returns per frame, 0.2–1.6 m above the
   rail plane, |Y| < 0.9 m) and the reported clear distance is 3.0–40.0 m (for example 9.7 m at frame 4396, 21.0 m at 4385, 37.6 m at 4405,
   40.0 m at 4414 where 205 returns stand at 2.5–2.7 m).
   In all 38 the model-on value equals the detector's own clear distance (the model only takes `min(·, 48.2)`), so the fault is the
   detector's; with the model off the same frames report 0. [`out/person_clear.txt`](out/person_clear.txt),
   [`out/png/person_f4371/4375/4385/4396/4405/4413.png`](out/png/).
2. **On 145 STOP frames the clear distance exceeds the STOP distance by up to 0.05 m** (for example 48.0 m against a STOP at 47.97 m).
   The detector's clear distance is rounded to 0.1 m and the detections to 0.01 m; the model-on value equals the detector's in all 145.
3. **The density model at the person.** Observed returns of the person's clusters against the model's expectation for a flat
   target of the cluster's own size: ratio 1.34 at 25–50 m (p10 0.93), 2.9 at 50–80 m, 4.0 at 80–120 m, but 0.65 at 10–25 m and
   0.23 under 10 m ([`out/density_check.txt`](out/density_check.txt)). At the limit (48 m) the model is close to what is observed, optimistic
   in the person's near range, where the boxes are clipped and the target is not flat. This is an order-of-magnitude check of the
   raster, not of the 0.3 × 0.3 m / 3-return criterion.
4. **`BACKLOG.md` says "on" without the condition** (the node's non-default range policy). The wording should say so.

## Current main (`f56ad5e`)

After the review on `cc6226e`, main received the R3 completion (`git diff cc6226e f56ad5e -- resense native configs ros2_ws` is
`clustering.py` +22 and `tracking.py` ±55; `detector.py` and `decision_policy.py` are unchanged). Rerun on `f56ad5e` (worktree built
with `build_native.sh`, same commands), outputs in [`out/main/`](out/main/):

| check | result |
|---|---|
| the whole Falcon stream, shipped replica | **4,443 rows equal the `cc6226e` shipped record in every non-timing field, and the 4,443 track records are byte-equal** (`ref_differ_on` 0): the R3 patch changes no Falcon row here; stream sha256 `90dea27d…` equal to the published |
| H′ off vs shipped on main | the same 8 frames (4394–4401, CAUTION → STOP), STOP 1,364 vs 1,372, nothing else; the hook looked at the same 265 clusters, 31 over the threshold, 20 demoted, 11 kept; the clear-distance results (4,442 frames model on vs off, max 48.2 m, 0 decision differences) are the same. The analysis texts of the two sources are identical line by line ([`out/main/falcon_analysis_main.txt`](out/main/falcon_analysis_main.txt) against [`out/falcon_analysis.txt`](out/falcon_analysis.txt)) |
| gate with H′ off on main | exit 0, no `--allow`, 8 gated rows better, none worse; **15,269 rows, 0 differ** against the `cc6226e` shipped rows ([`out/main/identity_gate_main_hoff_vs_cc6226e.txt`](out/main/identity_gate_main_hoff_vs_cc6226e.txt)); set F: only the config hash, the wall time and `gt_vehicle_y_m` (≤ 7e-9 m) ([`out/main/setF_straight_compare_main.txt`](out/main/setF_straight_compare_main.txt)) |
| X3 on main | **not rerun** (unverified here); R3's own record reports its paired X3 equal |

The comparison is of main with H′ off against `cc6226e` with H′ on, so a 0 means the R3 patch and H′ together change no gate row. It does
not show the two apart: H′ on, on main, was not rerun through the gate (the shipped gate on main is R3's record, not reproduced here).

## Independent findings that are not caused by either switch

1. **Frames 4373–4414: a person-like object 2.5–7 m ahead gets no STOP in the shipped run, with or without H′.** Only 4380–4382 are
   STOP (the person's upper body at ~6 m); the other 39 frames of the 42 are CAUTION in the shipped run, and in the H′-off run too
   except 4394–4401, which are STOP on the ceiling cluster, not on the person. The track model has no rail pair
   (`rail pair found in 0 % of the last 20 frames`) and its floor fit wanders. The shipped run is the reference of the whole seal;
   these 39 frames are unchanged by H′, so this is not H′'s doing, but they are the frames where the claim "no STOP lost" has
   nothing to say. There is no Falcon ground truth, so whether the object must be STOP, and whether it is the person, is unverified
   (the picture and the returns say a column 0.7–0.9 m wide, 1.6 m above the plane, that continues the person's track:
   [`out/png/person_f4371.png`](out/png/person_f4371.png), [`out/png/person_f4396.png`](out/png/person_f4396.png)).
2. **The gate and X3 hardly exercise H′.** H′ acts only with a final mount calibration and on gauge clusters within 30 m. In the gate
   replay it ran in 12,277 of 15,269 frames but looked at **157 clusters** (117 on set O, 40 on the ride, 0 on the six recordings), none over
   the threshold; the closest is 0.50 m under it. So "0 gate rows change" is true because the check is never armed there, not because
   it was tested and passed. The only place H′ acts is the 8-frame Falcon event.

## How it was checked

| # | what | method | result |
|---|---|---|---|
| 1 | the source is the sealed one | `git diff 5fa865b cc6226e -- resense native configs ros2_ws` and the same against this branch's head | empty; the X3 summary's recorded source tree equals the tree of `cc6226e` |
| 2 | reused shipped runs are of that source | my pass 1 of the stream with the shipped configuration, hooked read-only, against the committed shipped Falcon record; a second, plain `falcon_trace.py` run against it again | **4,443 rows, 0 differ in any non-timing field, the 4,443 `.x.jsonl` track records byte-equal, both runs** |
| 3 | the whole Falcon stream is the published file | the stream's sha256 for both passes | `90dea27d…5611`, equal to the published; 20,281,548,800 bytes, 4,443 frames found and kept, 0 lost, 0 duplicates, 0 order violations |
| 4 | traced run equals plain run | Falcon: hooked shipped replica against the committed plain record (above); gate: `gate_h_trace.py` (the gate's own replay, `_mount_cross_check` wrapped read-only) against the shipped gate rows with `cmp_frames.py` and `list_diff.py` | Falcon as in 2. Gate: **15,269 rows, 0 differ** (936 differ only in the latency health level) ([`out/identity_gate_trace_vs_shipped.txt`](out/identity_gate_trace_vs_shipped.txt)) |
| 5 | the override takes effect | each X3 worker logs the effective value; the same wrapper with an override known to change results; the Falcon off replica | 40 of 40 workers `mount_cross_tol` 0; `gauge.range_max=40` changes 193 of 201 rows, `mount_cross_tol=0` changes 0 ([`out/x3_set_override_control.txt`](out/x3_set_override_control.txt)); the off replica finds exactly the 8 frames of the claim |
| 6 | the frame lister is correct | `list_diff.py` against `cmp_frames.py` on a known pair, the F1a repair (`8c2bf51` against the shipped gate rows) | 2,052 + 35 = 2,087 differing rows, as `cmp_frames.py` and the F1a acceptance ([`out/control_list_diff_8c2bf51_vs_shipped.txt`](out/control_list_diff_8c2bf51_vs_shipped.txt)) |
| 7 | the sets I ran on are the ones the shipped runs used | sha256 of every X3 node-decoded `.npz` and `meta.json` against `x3_l16.json`'s inventory; the six recordings' `metadata.yaml`; frame counts; archive sha256 | 877 / 201 / 545 / 1,510 `.npz` equal, meta equal; archives equal the published (six recordings `e2316680…`, ride `8124b627…`, set O `d41c2fb2…`); counts 201 / 345 / 252 / 268 / 545 / 877 / 1,510 / 11,271 |
| 7b | the ride cache is the published ride | the archive was streamed again through `scripts/cache_extended_ride.py` (size, sha256, 221 splits × 51 frames, the cache's compact16 / zstd level 3 encoding as the shipped gate's) before the gate ran | `8124b627…` equal to the published; `intake_manifest.json` complete; the first 96 splits (4,896 frames), cached as plain `.npy` before I switched to `--zstd` to save disk, were converted to `.npy.zst` losslessly, each read back and compared |
| 7c | the H′-off gate | `regression_gate.py --set cluster.mount_cross_tol=0`, 4 jobs, seal baseline, no `--allow`; per frame against `gatework_l16.tar.xz` with `cmp_frames.py` and `list_diff.py`, the gate JSONs with `gate_diff.py`, set F straight leaf by leaf | as in the answer ([`out/identity_gate_hoff_vs_shipped.txt`](out/identity_gate_hoff_vs_shipped.txt), [`out/setF_straight_compare.txt`](out/setF_straight_compare.txt)); the work files' `config.yaml` carry `mount_cross_tol: 0` against the shipped 0.5 |
| 8 | the 8 frames' cause | the raw returns of the frames (dumps), the clusters H′ looked at with their heights above the mount plane, the track records of both runs | table above; pictures |
| 9 | the 8 frames are false | by looking at the returns (pictures), the ceiling sheet at Z ≈ +2.5 m in every frame, 4.1–4.3 m above the rail plane; a tunnel ceiling is a physically plausible height, a person is not 4 m tall | ceiling |
| 10 | H′ does not demote a real object | the 11 person clusters over the threshold that H′ kept (positive control: same tool, a case where it must not demote) | kept; heights 1.2–1.6 m above the plane |
| 11 | clear-distance model value | closed form against the code, the pre-19.10 source from git history, 48 unit tests of `decision_policy` | 48.2518 m both ways; pre-19.10 `None`; 48 passed |
| 12 | the model does not touch the detector | counters on `small_target_limit`, `candidate_ranges`, `falcon_expected_points` during every frame of both replicas, with a positive control (the node path called with the counters up) | 0 / 0 / 0 during the frames; the control counts 1 / 1 / 49 |
| 13 | physical plausibility | the model against the person's returns by distance band; the clear distances against the nearest return on the track | [`out/density_check.txt`](out/density_check.txt); finding 1 of (b) |

## Not verified

* A Falcon ground truth beyond the person's walk: whether the object of frames 4373–4414 must be STOP, and what exactly it is.
* X3 on current main (`f56ad5e`), and the gate with H′ on there (only the H′-off gate was rerun).
* The node path itself: the clear-distance results are a read-only replay of `candidate_ranges` after `evaluate_decision` with
  the node's arguments (`min_points_far`, `max_range`, policy v1, a valid freshness record), not a ROS run. The live node's
  freshness, latch and health overrides are not modelled. `small_candidate` is run and equals `conservative` here.
* Why `gt_vehicle_y_m` of set F differs by up to 7e-9 m between two runs of one detector (the ground truth is built from ICP odometry with open3d;
  probably thread order; the two gate runs used 3 and 4 jobs). No detector field differs.
* How the detector counts `n` for the density check (accumulation, returns held twice in the cloud).
* Any other switch (F1a, R3, L16/S3, H1 and the rest of the seal) and the test suite: only `tests/test_decision_policy.py` (48 tests)
  was run here; the full suite was not.
* G3 and anything on the held-out set.
* H′ against a real object whose cluster lies entirely more than 3.0 m above the mount plane while the model and the mount disagree
  (the only way the check could demote a real object): no such case exists in the data; the gate and X3 do not arm the check
  (finding 2) and the Falcon's person is 1.2–1.6 m above the plane.

## Files and reproduce

* [`scripts/falcon_pair.py`](scripts/falcon_pair.py): the stream through two replicas (shipped and `--set` off), the H′ hook and the node's
  range path; [`scripts/falcon_analyse.py`](scripts/falcon_analyse.py) (analysis, `out/falcon_analysis.txt`);
  [`scripts/person_clear.py`](scripts/person_clear.py), [`scripts/person_plot.py`](scripts/person_plot.py), [`scripts/near_person.py`](scripts/near_person.py),
  [`scripts/density_check.py`](scripts/density_check.py), [`scripts/plot_pair.py`](scripts/plot_pair.py), [`scripts/crop_dump.py`](scripts/crop_dump.py);
  [`scripts/gate_h_trace.py`](scripts/gate_h_trace.py), [`scripts/gate_h_summary.py`](scripts/gate_h_summary.py); [`scripts/x3_set.py`](scripts/x3_set.py) (the
  unchanged battery with overrides); [`scripts/list_diff.py`](scripts/list_diff.py) (every differing row).
* `out/`: `falcon/` (both replicas' per-frame and track records, the H′ hook and node-path records, the cropped dumps, stream
  sha256 and meta), `x3_hoff.json` and `x3_raw_hoff.tar.xz` (unpack to `/home/user/out/x3/`, the summary's `raw_path`),
  `x3_compare_hoff.txt`, `gate_hoff/` (the H′-off gate JSON, its per-frame rows, both logs), `gate_trace/` (H′ trace of the gate data), `png/`, the analysis texts.

```
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
T=<tree at cc6226e>; S=docs/evidence/p4_review_h_mount_falcon_2026-10-20/scripts   # build native: scripts/build_native.sh in $T
export RESENSE_REPO=$T PYTHONPATH=$T:$T/ros2_ws/src/resense_ros
curl -L <falcon_test.zst href> | python $S/falcon_pair.py /dev/stdin --out OUT/pair --ref docs/evidence/l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz
python -I $S/falcon_analyse.py OUT/pair <l16.jsonl.xz> <l16.x.jsonl.xz>
X3_SET='{"cluster.mount_cross_tol": 0}' python $S/x3_set.py --repo $T --cache <decoded> --out OUT/x3_hoff.json -j 2 --reference docs/evidence/l16_acceptance_2026-10-20/out/x3_l16.json
RESENSE_REPO=$T python -I docs/evidence/f1a_acceptance_2026-10-20/scripts/x3_compare.py docs/evidence/l16_acceptance_2026-10-20/out/x3_l16.json OUT/x3_hoff.json
python scripts/regression_gate.py --cache <cache> --jobs 4 --work OUT/gate_hoff --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json --out OUT/gate_hoff.json --set cluster.mount_cross_tol=0
python -I docs/evidence/integration_2026-10-19/scripts/cmp_frames.py <gatework_l16 unpacked> OUT/gate_hoff
```
