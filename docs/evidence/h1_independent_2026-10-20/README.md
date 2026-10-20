# H1 independent reference review — BLOCKED

**Verdict: BLOCKED. H1 remains OPEN.** No independently validated spatial
reference for the A/C rail corridor at 100–150 m was established. Neither a
reconstructed trajectory, ICP agreement, nor detector-axis-aligned injection
is surveyed truth. This is an independent P4 reference-method review, not
acceptance of the current detector bundle.

## Durable evidence and reproduction

* [`review_reference.py`](review_reference.py): read-only independent audit.
* [`report.json`](report.json): machine report from its real VM execution,
  including current Git source bytes, full input hashes and controls.
* Existing portable input archive:
  [`../h1_trajectory_2026-10-19/raw-evidence.tar.gz`](../h1_trajectory_2026-10-19/raw-evidence.tar.gz).
  The script reads its named members directly; it does not extract or modify it.

From the repository root, with the existing VM data layout and environment:

```bash
export RESENSE_REPO="$PWD"
export OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
/tmp/opencode/resense-b4-venv/bin/python -B \
  docs/evidence/h1_independent_2026-10-20/review_reference.py \
  --repo "$PWD" --vm-root /tmp/opencode \
  --out "$PWD/docs/evidence/h1_independent_2026-10-20/report-repeat.json"
```

Choose a fresh output filename: the script refuses to overwrite a report.
Exit 0 means the review completed, **not that the reference or H1 passed**.
Python dependencies are NumPy, PyYAML and rosbags, already in this VM venv.
There is no Open3D or production-detector import. The script writes only its
exclusive report in this new evidence directory. Git commands disable optional
locks; the index hash and production-source hashes are compared before/after.

The report hashes all 11 complete raw databases, metadata, NPZ checks, archive,
named archive members, review script and applicable instructions. It records
52 tracked production/configuration/ROS/build source files against HEAD and the
40-file freeze-manifest byte identity. This is source identification, **not a
new detector gate or reseal**. Runtime absolute paths appear only in receipts;
this public document uses repository-relative and generic temporary paths.

### Actual execution receipt and separate verification

The completed VM run wrote `report.json` at **2026-10-20 15:52:59 UTC**, exit 0,
in **137.51 s**, against Git HEAD
`f56ad5e62d9d051811c804734c7731b6951eae90`. It fully hashed **54 input files /
64,199,404,451 bytes**, including all 11 databases, and recorded nine archive
member reads. Source/index and input-stat signatures remained unchanged.

| Artifact | SHA-256 |
|---|---|
| `review_reference.py` | `b904555d5366ad30769d3d03fb3f578c77a7cac90075d6d62cb5bb0e729de55d` |
| `report.json` | `c6c4579654247feedc18d52d60adc68b94a8083e5c8116071c19d262970331e7` |

The completed script's output was then checked by a separate SSH calculation,
without importing `review_reference.py`:

* All 36 decisions were re-derived with the rotation **arccos(trace)** formula,
  independently of the script's **atan2(trace, antisymmetric part)** formula.
  The 4/24/7/1 counts agree; the known 80 m positive control passes.
* All 1185 validation observations were re-derived from the **raw support-point
  means using `math.fsum`**, homogeneous 4x4 transforms and `math.dist`, rather
  than the script's saved centroids and 3x3 rotation/vector path. Every track
  p95 agrees within 1e-12 m; counts remain A13/28 and C16/27.
* A0/A1 were independently decoded by a **manual CDR layout reader using
  `struct`**, without rosbags or production code. It found the same 9/11
  distinct raw reflector returns, identical serialized-message hashes and the
  same three-component centroid displacement. This is separate raw evidence,
  not acceptance of a number merely printed by the new audit script.
* The three durable files, all README links, public-document path/IP checks,
  final HEAD and unchanged index hash were checked after the run.

These secondary calculations are recorded here as witnessed checks; the JSON
is the unedited output of the real audit run, not a hand-populated summary.

## Checked scope and independently confirmed results

### Actual topic inventory

Eleven original SQLite databases are opened `mode=ro`, with `query_only=ON`.
For each, topic LEFT JOIN counts are compared with an independent `GROUP BY
topic_id`, total/orphan counts and the raw `metadata.yaml` counts.

| Input | Actual messages |
|---|---:|
| Six original recordings: doubleT_obstacle / doubleT_platform / roundT_doubleT / C / A / squareT_platform_squareT_switch | 201 / 345 / 252 / 268 / 545 / 877 PointCloud2 |
| A: roundT_squareT_pressureGate_squareT | 545 clouds; no other topic |
| C: roundT_pressureGate_roundT | 268 clouds; no other topic |
| Set O: cloud_with_fake_obj | 1510 clouds; no other topic |
| Falcon | 4443 clouds +215 rosout; initialpose/goal_pose each contain zero messages |
| Marked platform / switch / tunnels | 386 /736 /545 clouds and equal MarkerArray counts |

All 11 inventories have zero orphan messages and matching metadata. Nonzero
clouds in every bag, nonzero markers and rosout are positive controls in the
same inventory path. There is no populated external pose/rail-reference topic
in these databases. This is a bounded inventory, not a statement about all
possible files or unpublished organizer data.

The remaining ride-spool `new_data_215.db3` was malformed in the earlier session
(`database disk image is malformed`). It is excluded, not interpreted as an
empty inventory. It is a separate recording, not A/C.

### Existing 36 direct comparisons: independently re-evaluated, not rerun ICP

All rows of `direct-gicp-regularized-all.json` are recalculated from saved
matrices. Rotation uses the matrix trace/antisymmetric part, not the author's
SciPy rotation helper. Gates remain: seed projection <=0.10 m, reverse
translation <=0.10 m, reverse rotation <=0.05 degrees, fitness >=0.70.

**0/36 pass.** Ordered first-failed conditions: **4 seed disagreement,
24 reverse translation, 7 reverse rotation, 1 fitness**. These are recomputed
conditions, not a new instrumentation trace. All 36 individual metrics and
decisions are retained in `report.json`.

Positive control: the saved manufactured 80 m transform passes and agrees with
its known transform. Planted seed, reverse-translation, reverse-rotation and
fitness faults each fail their intended condition in the same validator.
This validates the checking path, not real-world absolute trajectory accuracy.

### Withheld landmark validation

All **55 withheld tracks /1185 observations** are transformed from saved raw
observation coordinates by the saved poses. Anchors, every residual and all
percentiles are recomputed rather than copied from summaries.

| Sequence | Training tracks | Validation tracks / observations | Tracks with p95 <=0.10 m | Maximum track p95 |
|---|---:|---:|---:|---:|
| A | 109 | 28 /685 | 13 | 0.341761958 m |
| C | 106 | 27 /500 | 16 | 0.327424294 m |

All **5903 retained observation centroids** also equal the mean of their stored
raw support. These residuals combine association, sampled centroid and pose
errors; they are **not a separately measured pure pose-error distribution**.
Optimizer convergence and low training cost do not validate the far reference.

### Raw independent reflector and direct return checks

The script independently deserializes PointCloud2 CDR using rosbags and the
declared byte offsets. It checks exact XYZ equality against NPZ for **A0, A1,
A135 and C55**, after the inclusive 2.5–250 m crop. No detector decoder,
calibration, fitted floor, candidates or axis participates.

The bright A0/A1 wall reflector has **9 /11 distinct returns**. Its raw
centroid displacement is **[1.3430430865, -0.0278243296, 0.0516521956] m**.
This supports the 1.34 m longitudinal mode over the old 0.335 m alias; it is
not full SE(3) truth. Identical selection on a 10 km shifted cloud is empty,
while the actual frames provide the positive selections. Raw support points,
serialized-message hashes and original timing ranges are retained.

The earlier finite-only alignment preflight was incorrect because it included
out-of-range/zero returns. The corrected inclusive crop is verified exactly
on all four frames before any raw result is used.

The 12 published bed slices are independently reproduced from original CDR:

| Frame; forward slabs +/-4 m | 15 m | 30 m | 60 m | 90 m | 120 m | 150 m |
|---|---:|---:|---:|---:|---:|---:|
| A135 | 5693 | 853 | 95 | 27 | 5 | 0 |
| C55 | 8205 | 1006 | 114 | 33 | 32 | 12 |

Counts are distinct returns, **not identified rail heads**. Near slices are
the same-path positive controls; actual far XYZ examples are retained.
Another 32 slices at 100/120/140/150 m cover A135/230/248/256 and C0/50/55/75.
Widening Z from -3..-0.4 to -8..1 m changes C55/150 m **12 ->20**, A248/150 m
**3 ->18**, A256/150 m **0 ->4**. Therefore the old narrow crop cannot prove
universal far-data absence. More returns do not establish a validated rail pair.

## New practical alternative and its checked feasibility

An explicit rigid solve from manually identified **fixed physical corners or
joints**, independently of ICP/detector state, could transfer later near-rail
observations into earlier frames. It needs at least three non-collinear
correspondences, additional excluded independent landmarks, conditioning and
measurement/timing error checks. A changing sampled reflector centroid should
not be silently treated as a fixed physical point.

The new preflight uses pose-invariant pairwise distances in the retained raw
feature observations. A185->A235 IDs 552/570 change separation by
**0.164171172 m**; C0->C1 IDs 11/12 change by **0.152740844 m**. These source
centroids are not compatible with a single exact rigid transform without an
error model. Partial visibility, association and intra-scan motion remain
possible causes; this does not isolate pose error. Known 80 m rigid motion
preserves pairwise distances to <3e-14 m; a planted nonrigid displacement is
detected by the same calculation.

In the **24 previously selected nominal 100/140 m frame pairs**, **23 have no
common retained track**, and A50->A114 has one. That is insufficient to solve
and independently check full SE(3). The same search finds >=4 common tracks
in **306 adjacent A pairs /239 adjacent C pairs**, its positive control.
This negative applies to these tracks/pairs, not all possible manual features.
The nominal far stations themselves come from rejected trajectories.

The preceding independent session additionally checked 791 support-point
memberships in NPZ on A185/A235/C0/C1; that raw-membership check is not claimed
as a rerun by this script. The script does rederive all 5903 centroids from the
portable archived support arrays.

## Historical misses and separate acceptance work

The archived A-axis probe has **114/177 matched visible rows**, **63 misses**
(58 CAUTION +5 GO). Nominal 100–150 m has **20/39** matches. Miss frame IDs:

```text
152–163, 171, 174, 176–180, 196,
224–239, 248–256, 306–323
```

These are **historical measurements of merged H1 source 0f02b28 / retained E
7d0f571, not fresh replay of the current Git HEAD**. The machine report marks
`fresh_current_replay: false`. No causal labels are accepted here. Fresh current
replay and actually wrong-selected-pair/no-rails work belong to the main lane.

## Additional source checks from the preceding read-only session

These were independently performed before this script, and are not represented
as live network/archive-intake work by the offline audit:

* Public organizer API listed exactly six files on 20 October: the four known
  archives, `new_synth_data_with_markers.zst`, and `obstacles.md`; no new spatial
  reference file. Both synthetic archive hashes matched the public API.
* Complete member lists of the original nested six-bag archive and both
  synthetic archives contained the databases/metadata, with no spatial-reference
  sidecar. The original archive README only describes extraction/playback.
* All 1667 saved marker-frame records describe `synthetic_obstacles` wire boxes
  in `hesai_lidar`. Obstacle markers do not provide independently validated ego
  poses or rail truth. Organizer answers explicitly describe approximate
  synthetic placement and possible object motion.
* Original `sequence-A-v2.json` has a first longitudinal step 0.335143845 m and
  accumulated roll -40.628 degrees at A100. This is a concrete rejected
  estimator mode, not asserted physical train motion.
* The original 948 captured A/C/E6 matching rows were checked independently;
  that was not a fresh detector replay. This script only recounts the archived
  A-axis probe and never claims full current-source instrumentation equality.

Sources: [`../organizer_markers_2026-10-19/README.md`](../organizer_markers_2026-10-19/README.md),
[`../../organizers/answers.md`](../../organizers/answers.md),
[`../../SENSOR.md`](../../SENSOR.md),
[`../h1_trajectory_2026-10-19/REFERENCE_AMENDMENT.md`](../h1_trajectory_2026-10-19/REFERENCE_AMENDMENT.md).

## Minimal missing input

The smallest direct reference input is **independently checked left/right
rail-head geometry in identified A/C sensor frames at 100–150 m**, including
support observations, correct path identity and quantified uncertainty,
especially on curves. A full global trajectory is not obligatory for this
option. An annotation is not called surveyed truth without survey provenance.

Alternatively supply **synchronized independently validated relative SE(3)
poses**, extrinsics and an error budget, plus independently checked later
near-rail observations. A new ICP chain or agreement between related chains
alone is insufficient.

For scale, allocating an entire 0.10 m budget to orientation at 150 m permits
only **0.0382 degrees**. The existing diagnostic 0.05-degree closure threshold
alone corresponds to **0.1309 m**, before translation and rail measurement
errors. Passing those diagnostics would not itself establish an absolute bound.

**Disposition: BLOCKED; keep H1 OPEN.** No detector run, production edit, Git
index/branch update, commit, push, reseal or G3/held-out work is part of this
package. Source identification in the report is contextual, not acceptance.

### Audit preflight correction

The first script invocation stopped before database hashing or report creation:
the 40-file seal also includes `scripts/build_native.sh`, outside the initially
listed production roots. The source snapshot was corrected to include the union
of those tracked roots and every sealed file (52 files in total). No production
file or existing evidence was changed by this correction.
