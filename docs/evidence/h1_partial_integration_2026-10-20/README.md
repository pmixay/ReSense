# H1 partial improvement accepted for main — 20 October 2026

**Decision: publish the implemented improvement and its evidence in main.
Overall H1 / inherited High 8.1 remains OPEN.** The user explicitly requested
this publication after reviewing the measured gains and remaining limitations.
This supersedes the earlier instruction to push only after complete H1 closure.

The measured merged detector is **`0f02b283a9a8ebeb8bccae76a7b12f23862206df`**:
retained H1 candidate E (`7d0f571`) plus fetched remote main
**`0acb18c57bfb84c61d9344aacaad8b65be648b07`**. Its production source bytes are
unchanged through the final X3, physical checks and publication documentation.
This is a source integration, **not** a new seal, image, release or claim of
independent P4 acceptance.

## What is implemented

* Positive **current-frame collision evidence** can exempt a tall narrow body
  from the `column` shape signature. It requires occupied-voxel/height/footprint
  support, an additionally eroded rail-relative envelope, fresh raw paired rail
  anchors, and boundary consistency where locally observed rails do not cover
  the target range.
* Inside the supported interval of at least three paired rail slab stations,
  the fresh observed rail residuals supply the direct local reference; it is
  not extrapolated beyond those stations.
* Only uninterrupted ordinary confirmation of the positive core suspends a
  track's `column_hold`. Measured history is preserved; a miss/non-core resets
  the fresh run. Axis/height limits, zone votes, other signatures, doubt and
  ego-motion guards remain in force.
* Defaults: `column_core_margin=0.02`, `column_core_min_voxels=8`,
  `column_core_min_height=2.2`, `column_core_max_footprint=0.8`. The class and
  both YAML copies agree. The withdrawn free-top experiment stays off:
  **`column_free_max_top=0`**. Zero `column_core_margin` disables the new path.

## Measured gains — distinguish the data types

| Check | Earlier result | Retained result | What it establishes |
|---|---:|---:|---|
| A-axis: injected 0.3 ×0.3 ×2.8 m object in real scans | **82/177**, pre-core base | **114/177**, no previous matched rows lost in the retained stages | More matched visible development-probe frames; **63 misses remain** |
| Three left137 m opaque stationary cases, D ->E | **1/14** each | **10/14** each | Every scan after ordinary confirmation, not 100% from cold start |
| All 32 stationary physical cases | D: 293 matched rows | **320**, frames 4–13 of each 14-scan run | Repeated physical ray-cast cases at 37/67/109/137 m, both sides, opaque/absorbing continuations |
| Fully outside physical controls | — | **0/280** false cores/STOP | Fixed 8/17/25/37/67/109/137 m controls, lateral offsets/errors, rails present/absent |
| Nominal moving opaque body, 22 m/s | D continuous: 126.4 /130.8 m | **130.8 /135.2 m** | Physical simulation only; 12 complete moving variants are checked |

**These are not verified real-world obstacle detection ranges, braking
sufficiency or calibrated absolute rail-axis error bounds.** The A-axis object
is placed relative to the baseline detector axis, not a surveyed track. The
physical scenes have analytically specified geometry. A first STOP or pooled
held90 metric is not a guarantee against individual missed frames.

The historical base ->C ->D ->E stages are preserved in
[core](../h1_core_2026-10-19/README.md),
[absolute-axis follow-up](../h1_axis_range_2026-10-19/README.md) and
[retained E](../h1_reference_2026-10-19/README.md).
One additional unmatched A-axis STOP at frame335 is the ordinary one-miss hold
of the newly retained target after it leaves the injection range; this is
explicitly traced in the core record, not removed from unmatched accounting.

## Checks on the combined source

| Check | Result / provenance |
|---|---|
| Complete original regression gate | **PASS**, no overrides/waivers. 15,269 ordinary frames +3,060 Set F rows. All **208 non-timing metrics equal** the published main integration gate |
| Fresh final merged-tree X3 | **PASS: 40 cases, 29,765 raw rows, 260 comparisons** against retained E. Raw STOP row sets and every detection payload are identical to E: **0 lost, 0 added** |
| Fresh final physical replay | **32 stationary +280 outside +12 moving cases**, all retained E hit rows and continuous onsets reproduced |
| A-axis / C-person / E6 | Every captured range-probe row equals E: **114/177**, **55/153**, **34/59** matched visible rows respectively |
| Complete Falcon | 4,443 rows checked: **1364 STOP**, vs E 1372. Exactly frames4394–4401 removed by main's H-prime ceiling filter; no added STOP or other detection-payload change |
| Affected integration unit tests | **252 passed** |
| Complete pytest on the combined detector | **2276 passed +17 subtests; one inherited failure**, eight external-data deselections, no skips |

The full suite is **not all-green**: the proxy-hook negative-source test expects
`outside the pinned source`, while this environment reports missing `resense`;
the child still exits the required fail-closed code86. The exact failure was
also observed on the prior reference and is retained, not deselected here.
The worse original-seal informational Set F cable sustained-median metric
(34.2 ->17.8 m) already exists in main's R3 integration; merged H1 does not
change it. No new independent review/reseal or release validation is claimed.

Gate/probe/full-test receipts and the independently recomputed audit are in
[trajectory / integration evidence](../h1_trajectory_2026-10-19/README.md).
This folder adds the previously missing **fresh X3 of the combined tree** and
fresh physical replay, verified from raw outputs in [acceptance.json](acceptance.json).

## What remains open

1. **63 A-axis visible unmatched frames** and the remaining axis/height/column
   limitations; C-person's first STOP is still82.77 m.
2. **An independently validated far rail axis / trajectory** for straight and
   curved 100–150 m scenes. Repairing the initial ICP alias did not validate the
   later trajectory: new direct checks still fail36/36, and separate landmark
   tracks retain excessive inconsistency. Failed methods and source hashes are
   archived in the [trajectory report](../h1_trajectory_2026-10-19/README.md).
3. Missing fresh rails and an **actually selected wrong rail pair** do not have
   a universal collision proof. The 2 cm erosion is an extra geometric margin,
   not a measured bound on true-axis error.
4. Independent final review and the combined detector reseal remain pending.

The organizer's new markers improve **obstacle geometry/visibility** evidence,
but do not provide rail-axis truth. Their [independent intake](../organizer_markers_2026-10-19/README.md)
also corrects the earlier blanket dust-absence claim: 31 near-field added
returns in platform0–314 are organizer-marked sparse particles.

## Audit and reproduction

`run_checks.py physical` / `run_checks.py x3` make fresh source snapshots,
read-only source hashes and execution receipts using the existing Linux
runtime. `audit_results.py`:

* reopens both reference/current X3 workers, checks every raw hash, source and
  completion identity, and independently reconstructs all40 metric summaries;
* recomputes all260 comparisons, all STOP row sets and detection-payload losses;
* verifies every stationary hit from captured detection coordinates and every
  moving continuation onset from complete row sequences;
* exercises the negative outside-selector path with a known positive inside
  body, and the comparison path with a planted lost positive;
* confirms that all measured source hashes equal the existing merged gate,
  probe and full-test source, then archives raw outputs and reopens every member
  to verify its SHA-256.

`raw-evidence.tar.gz` contains the new raw workers, physical rows, source
snapshots and logs. [package.json](package.json) and
[raw-manifest.json](raw-manifest.json) pin archive and member hashes.
`x3.json` is the full battery report; it retains the execution paths in
`/tmp/opencode/h1-publication/`. The portable raw archive contains those files
by paths relative to that working directory. Use a fresh output directory when
reproducing because outputs are created exclusively. No G3 input or judging run
is used.
