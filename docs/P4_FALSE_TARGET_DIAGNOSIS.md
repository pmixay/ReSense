# P4: actual false-target diagnosis, 26 September 2026

Status: development evidence against the sealed P3d baseline. No candidate result is claimed
here. The ride has no labeled real obstacles; it cannot measure independent obstacle recall.

## What was traced

`scripts/trace_false_targets.py` replayed all eight frozen ride pieces, resetting the detector
at the same piece boundaries. All 11,271 frames reproduced the archived detections exactly.
It followed all 45 false-event tracker identities through their complete lifetimes, including
pre-confirmation and advisory states. A passive wrapper observed association inputs after any
mount reseed; it did not change matching. Unit tests check observation against an unwrapped
tracker through matches, misses and a reseed.

Target points are the current cluster's exact `points_idx`, not points selected by a bounding
box around a reported alarm. A held STOP with a missed current match has no new target points;
old indices are never applied to a later cloud. Snapshots include the first, middle and last
matched alarm where available, and nearby frames while the track exists. Temporal records
cover every tracked frame. The diagnostic fits are the detector's own estimates, not surveyed
rail coordinates or independent envelope ground truth.

## Geometry review of every event

The contact sheets show the actual target in red with surrounding points at the target's range.
They replace the earlier near-sensor scene labels for this diagnosis. One reviewer inspected all
45 target crops and their physical Y/Z trajectories. These broad geometry families account for
every event; they do not claim an independently surveyed physical object class.

| Observed target family | Events | Evidence and remaining uncertainty |
| --- | ---: | --- |
| Rail-bed or lower-side fragments | 21 | Small low returns or fragments at the base of the repeated track cross-section. Fifteen identities emit low-stage STOPs with maximum fitted height 0.030–0.120 m. Several identities join fragments on opposite sides. Exact rail versus sleeper/side equipment identity remains uncertain. |
| Vertically continuing structures clipped by the corridor | 6 | Same-X/Y context extends above the target's 3 m corridor cap; tracks also carry column demotions in other frames. Removing the upper context changes the apparent shape. Physical column semantics and true surveyed envelope membership are unverified. |
| Continuous side-profile fragments | 4 | Target lies on a visible, extended side profile and near the fitted corridor edge. This supports a context-loss mechanism; it does not by itself prove a particular rail-axis error. |
| Sparse distant targets, cause unresolved | 14 | Too little context to identify the structure reliably. Several alternate between trusted/demoted geometry, but reason codes alone do not establish their cause. |

The mutually exclusive review labels are in the evidence inventory. Additional temporal facts
(association residuals, low/corridor transitions and column history) can overlap these families.
The 14 unresolved events remain in every evaluation denominator.

## Association mechanism

Across 945 matched updates of these false-event identities, the median physical transverse
prediction residual was 0.145 m; the 95th percentile was 0.886 m. The existing tracker documents
an extra along-X approach allowance, but adds that allowance to the entire 3D matching sphere
whenever the candidate is closer than predicted. Two matched STOPs exceeded even the original
range-dependent transverse radius:

| Identity / frame | Residual X, Y, Z (m) | Base radius (m) | Allowed 3D radius (m) | Previous hits |
| --- | --- | ---: | ---: | ---: |
| `new_data_5:144 / 321` | −1.27, +2.57, +0.70 | 2.19 | 4.77 | 7 |
| `new_data_2:581 / 1340` | −1.51, −2.19, −0.51 | 2.15 | 4.59 | 5 |

The first joins a low central fragment to a right-side fragment. The second joins a right-side
fragment to a left rail-bed sliver. Physical coordinates and pre-update predictions are recorded
after calibration reseeding, so these residuals are not artifacts of comparing fitted lateral
coordinates across changing rail models. Existing confirmation history transfers to the new
support. Other opposite-side jumps fit the base radius itself: limiting the extra allowance to
X cannot be expected to remove all of them.

This supports a narrow directional-association bugfix experiment. It does **not** support claiming
that this fix alone will reduce 45 events to 30. A separate preregistration specifies the candidate
and acceptance gates; this diagnosis does not contain candidate results.

Evidence: [review inventory](evidence/results/p4_false_targets_2026-09-26/inventory.json),
[complete compressed temporal trace](evidence/results/p4_false_targets_2026-09-26/trace.json.gz),
[contact sheets and provenance](evidence/results/p4_false_targets_2026-09-26/README.md).

## Reproduce

Use the exact ride caches from the freeze intake and detector source hashes recorded in the
provenance file. If the main branch has later detector changes, use a baseline worktree and copy
only the two diagnostic scripts into it. Then run from that worktree's root:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/trace_false_targets.py \
  --archives docs/evidence/freeze_2026-09-26/gate_frames \
  --cache /path/to/cache/new_data --out /path/to/fp
python scripts/render_false_targets.py \
  --trace /path/to/fp/trace.json \
  --inventory docs/evidence/results/p4_ride_scenes_2026-09-26/inventory.json \
  --out /path/to/fp/sheets
```

The local run used `/home/resense/.venv/bin/python` and caches under
`/home/resense/data/cache/new_data`. Raw point snapshots remain reproducible local artifacts;
the compact trace and reviewed contact sheets are retained with the evidence.

## Limits

- Exact reproduction establishes which points and histories caused the baseline outputs. It
  does not establish real-obstacle recall or prove surveyed physical envelope membership.
- Mount-corrected physical coordinates must be compared after the same reseed. A change in
  fitted lateral coordinate alone is insufficient evidence of an association error.
- Full-cloud continuation is evidence about connected structure, not a safe automatic rejection
  rule: a true obstacle may touch infrastructure, and a small visible part can belong to a larger
  real object. Any use of context needs explicit positive and coverage gates.
- A candidate must be registered before its evaluation. Diagnosis does not authorize choosing
  thresholds from a sweep or discarding false events that are difficult to explain.
