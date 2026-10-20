# P4 handoff (20.10): the measurements that need the data

> **For:** an agent with access to Google Drive and Yandex Disk. **From:** the P4 cloud session of 20.10, which had
> no data access (proxy 403), so everything below it built or found is checked on committed files and synthetic
> scenes only. **Owner of the work:** P4 (Pavel). **Deadline:** code stop 20.10 23:59 MSK (DECISIONS row 42); T1
> feeds P3's fixes before it.

## 0. Read first

1. [`CLAUDE.md`](../../../CLAUDE.md): verify every result (positive control for every negative, look at frames,
   physical plausibility), evidence runs with `RESENSE_REPO=<checkout> OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`,
   evaluation runs never edit `resense/`, `native/`, `configs/` or the ROS package (use overrides), **nobody runs
   or tunes on G3**.
2. [`k2_v5c_2026-10-20/README.md`](../k2_v5c_2026-10-20/README.md): the K2 v5c switch, the Falcon re-score, §1b the
   second loss, §4 the registered rows (revision 2), §5 the commands.
3. [`p4_review_shipping_2026-10-20/README.md`](../p4_review_shipping_2026-10-20/README.md): three problems in what
   ships on (L16/S3, F1a, R3), each with a proposed P3 fix.
4. [`n5_markers_2026-10-20/README.md`](../n5_markers_2026-10-20/README.md): per-object scoring on the marked bags and
   the tunnels cube K2 loses.
5. [`docs/VM_GUIDE.md`](../../VM_GUIDE.md) §2 (data and frame caches) and §4.4 (the gate).

**State.** `main` (`0acb18c`) carries the final detector `4cf8e27`: K2 held off; F1a, H′, R3, L16/S3 on. Branch
`claude/k2-refinement-ty1aya` ([PR #43](https://github.com/pmixay/ReSense/pull/43), draft) = `main` + the K2 v5c
switch `track.axis_joint_reach_dual` (default 0 = off) + P4 evidence. With every switch off it equals `main` on 180
synthetic frames; **not yet checked on the recordings** (row ID below). Work on this branch, or on a branch made from
it with a PR into it.

## 1. Data

| what | where | size | used by |
|---|---|---|---|
| six Pandar recordings (`Датасет.zip`) | [Google Drive](https://drive.google.com/file/d/1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu/view) | 3.7 GB | gate, T1 |
| ride `new_data.zst` | Yandex `N8IUpAyd7jyvow` | 17.1 GB | gate (ride, set F), T4 |
| set O `cloud_with_fake_obj.zst` | Yandex `KpkG_yKoGk-vHQ` | 1.75 GB | gate, T4 |
| Falcon `falcon_test.zst` | Yandex `SfBeRHbs8bNJAQ` (folder `bags`) or `DK6H3Lxiyi-M-Q` | 6.76 GB | F-1, T1 |
| marked synthetic bags `new_synth_data_with_markers.zst` | Yandex `SfBeRHbs8bNJAQ` | 2.53 GB | M-1, T3 |

Download with `scripts/unpack_dataset.py` (it resolves Yandex public links; `--member`, `--only`, `--list`), caches
with `scripts/cache_frames.py ... --every 1 --int16 --stamps` (VM_GUIDE §2; checksums in `docs/DATASET.md`). Use
numpy 1.26.4 as the committed runs did, and build the native kernels (`scripts/build_native.sh`) in each worktree.

## 2. Tasks, in order

### T1. L16/S3 open-air FAULT: is any real start exposed? (first; about an hour; P3 needs it today)

The bug: `directional_axes` (`resense/calibration.py:282`) takes any unique axis with > 98 % same-sign returns as
signed forward; a full-revolution Pandar starting in open air (< ~2 % of returns above the sensor) gets −Z, and the
run is FAULT to the end (review A1). For the **first 10 frames** of each of the six recordings, set O, the first
ride split, `falcon_test` and the three marked synthetic bags: decode as the jury runner does
(`judge_runner.NodeReplica`: fastcloud decode, then `R_vs`), and report the share of returns with z > 0, the share
with x < 0, and `directional_axes(xyz)`. Positive control: `p4_review_shipping_2026-10-20/scripts/cue_synthetic.py`
gives (0, 0, −1) at 0.2 % above. A real frame with a one-sided axis other than +X means the bug fires there; the
smallest share above the sensor among real starts says how close the data is to it. Then, when P3 commits a fix:
gate + Falcon on that commit vs `4cf8e27` (expected identical) and `scripts/fault_open_air.py` (expected GO).

### T2. K2 v5c: the registered measurement (P4's P0)

Exactly the rows of the v5c README §4 (revision 2), nothing else tried: candidate **v5c-15**; **v5c-30** only if
F-1 fails at 15. Overrides `V` and the gate / Falcon / probe commands are in §5. Run the K2-off reference with the
same commands on the same head (it is row **ID** against `4cf8e27`/`main`, and the per-frame reference for the
others). Rows: **F-1** (`score_falcon_pos.py`), **G-1** (gate, no `--allow`), **G-2** (X3), **K1-2** (standing-person
probe), **ID**, and **M-1**, the three marked bags:

```
S=docs/evidence/p4_handoff_2026-10-20/scripts; N=docs/evidence/n5_markers_2026-10-20/scripts
RESENSE_REPO=$PWD python $S/judge_runner_set.py --bag <raw>/synthetic_<bag>_cloud_with_markers --out <out>/off_<bag>
RESENSE_REPO=$PWD python $S/judge_runner_set.py --bag <raw>/synthetic_<bag>_cloud_with_markers --out <out>/v5c_<bag> \
  --set track.axis_joint_fit=true --set track.axis_joint_range=false --set track.axis_joint_min_curvature=0.0001 \
  --set track.axis_joint_reach_cap=true --set track.axis_joint_reach_dual=15.0
xz -dc docs/evidence/synth_markers_2026-10-19/out/markers_<bag>.jsonl.xz > markers_<bag>.jsonl
python -I $N/per_object.py markers_<bag>.jsonl <out>/off_<bag>.jsonl <out>/v5c_<bag>.jsonl
```

(`judge_runner_set.py` is the jury runner with `--set` overrides; smoke-tested here without a bag, not yet run on
one.) The registered prediction is that M-1 **fails** on the tunnels cube (marker id 19). Report every row as
pass / fail with its numbers; commit the summaries and the per-frame outputs (xz) under
`docs/evidence/k2_v5c_2026-10-20/runs/` and update §6 "Not done".

### T3. Why K2 loses the tunnels cube (marker id 19), and a fix if the data shows one

Under variant B the cube (inside the gauge, inner face ~0.7 m from the axis) is not confirmed at 30–55 m (frames
259–273) while B's trusted range is 67–87 m: B's joint axis is inferred to sit ~0.3 m farther from the cube than
the true axis. Replay `synthetic_tunnels_cloud_with_markers` frames 240–290 with variant B's overrides (`V` without
`axis_joint_reach_dual`) and record per frame: the output axis, `track.base`, `track.joint_shape`,
`track.joint_reach`, `axis_valid`, the wall boundary samples the joint fit used (`bounds` in
`resense/track.py:estimate_track` → `joint_axis_fit`), each axis's lateral at the cube's distance, and the
marker-implied axis (marker centre − (−0.96 m); method in the n5_markers README). Look at the frames (plots of
rails, walls, both axes and the marker box). Questions: what pulls the joint shape (a wall segment's offset, the
curvature step at the 60 m knot, a niche or object at the wall)? Is it the same mechanism as set O `small_center`
(55 m) and the ride removals at 30–60 m that an OR-of-gauges rule would bring back (`new_data_4` 1223–1228,
`new_data_7` 623–624, 643–644)? If one rule separates them: implement it behind a **new off-by-default switch** with
tests, register its rows in the v5c README as revision 3 **before** measuring, then measure as in T2. Any default
change needs review by P3 or a fresh agent and the captain's decision.

### T4. F1a exposure (sizes P3's fix)

Review B1: a plain low cluster's top is capped below the envelope floor, so where the frame's rail line reads
≥ 0.11 m above the model's plane (ride frame 5709 does), F1a makes every plain low cluster weak. On the ride and
set O, with a traced run that equals the plain run (CLAUDE.md rule 6), list the low clusters F1a makes weak with that
reference ≥ 0.11 m, and look at each (pictures): real objects or rail fragments? When P3 commits the proposed fix
(top over the cluster's own footprint including returns above the floor), measure it with the gate and Falcon.

## 3. Report

To Pavel, in the project thread: per task what ran (commit, data, frames), the numbers against the criteria, what
was checked and how, and what stays unverified. Keep `main` and G3 untouched.
