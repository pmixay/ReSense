# N5: team annotations of all three new synthetic recordings — 17 October 2026

The missing annotations have been produced from the recordings themselves. The package covers
**all 1,667 frames and 12 object tracks**: three platform objects, five switch objects, and
**four tunnel objects**. It contains **1,684 supported object/frame rows**. These are team
annotations with explicit uncertainty, not a claim that the organizers supplied ground truth.
No detector decision was used to create a label.

| Recording | Frame records | Object tracks | Supported object/frame rows | Labels |
|---|---:|---:|---:|---|
| platform | 386 | 3 | 696 | [labels_synthetic_platform.json](labels_synthetic_platform.json) |
| switch | 736 | 5 | 692 | [labels_synthetic_switch.json](labels_synthetic_switch.json) |
| tunnels | 545 | 4 | 296 | [labels_synthetic_tunnels.json](labels_synthetic_tunnels.json) |

The additional tunnel object matters: a small **left-side box about 10 m behind the flat
cross-rail object** was absent from the previous three-object inventory. Independent broad-scene
review found it, and backward raw-point tracking recovered frames **446–495**, including its
partial near-range exit. The switch recording also now has a separate annotated left-side box
at frames 469–553, previously discussed only as a mixed detector/background event. The two
previous switch observations at frames 60–80 and 141–251 are one continuous right-side box track.

This is development evidence. It does not replace G3, authorize a detector change, or constitute
a release result. Frozen-label scores and their uncertainty bounds are documented in
[SCORING.md](SCORING.md).

## What was done

1. Rebuilt the raw caches from verified organizer archives. The [input manifest](../n5_c2_execution_2026-10-17/data_intake.json)
   identifies the archives and every decoded file. The cache filter is **radial distance 2.5–250 m**;
   valid near-exit labels can have forward distance below 2.5 m.
2. Kept the previous exact-reference platform 0–314 object geometry and independently repeated
   its source comparison. Reviewed every one of the remaining 71 platform frames and labeled
   the continuing person. [Platform review and control](PLATFORM_REVIEW.md).
3. Scanned **every switch and tunnel frame**, across forward 2.5–250 m, left ±120 m and sensor
   height −4 to +4 m, for compact raw geometry. Intensity 1 was a proposal cue, never sufficient
   evidence by itself. The wide lateral scan was necessary: some distant inserted objects lie
   tens of metres to the side of the near-track axis.
4. Proposed tracks from manually inspected raw seed volumes, then followed shape and motion
   in both time directions. Object paths were reviewed in forward/left/height plots; near, middle,
   far and sparse-boundary examples were inspected in top, side and front projections. A second
   agent independently checked the seed shapes and contact sheets. Supplemental whole-scene
   review found the fourth tunnel box.
5. Re-read every gap in each supported lifespan. Checked up to 50 frames before the initial
   proposal using a broad trajectory search, retaining sparse support explicitly and recording
   exclusions. Checked the first frame after each near exit rather than confusing the radial
   filter with a forward cutoff.
6. Corrected a proposal failure found by visual review: the switch left-side box tracker attached
   to sparse rail returns in frames 548–553. Those proposals were replaced with the actual dense
   box surfaces. The removed and corrected bounds are preserved in
   [switch_nearpass_corrections.json](switch_nearpass_corrections.json).
7. Recovered each final annotation's points directly from its reviewed raw volume. Every emitted
   row has actual raw support. Detector output is read only by the separate scorer, after label
   hashes have been frozen.

The raw-point/geometry materializer is [annotate_synthetic_tracks.py](../../../scripts/annotate_synthetic_tracks.py).
Accepted annotation volumes are [switch](reviewed_boxes_switch.json) and
[tunnels](reviewed_boxes_tunnels.json). The [scripts](scripts/) directory preserves the discovery,
proposal, gap, boundary and rendering tools used during review; proposal output is expressly
not ground truth. Session paths in those exploratory evidence tools are explicit. The materializer
accepts arbitrary cache and annotation paths.

## Quality and uncertainty

The platform continuation method was checked on exact-reference frames 255–314 before extending
past the available source: **60/60 person rows recovered, 58,638 true selected points, 93 extra
background points, zero missed object points** — 99.842% point precision and 100% recall on that
control. The original source comparison was also reproduced: 119,377 differing raw points,
119,346 labeled object points, and 31 excluded non-marker near-field differences. See the
[control](platform_extension_control.json) and [source check](platform_reference_check_rebuilt.json).
This control does **not** establish the same point accuracy for every other shape or bag.

The switch/tunnel boxes are assisted segmentation volumes. They can include a few nearby real
returns and their sparse far extents underestimate the complete physical mesh. Echo duplicates
are retained in `n_points`; `n_unique_points` makes sparse support visible. The materializer
records the one proposal-count change caused by its floating-point boundary tolerance: four
additional returns on switch frame 548. Coordinates are observed point bounds, not invented
full-size boxes when only one return is visible.

- Every frame has a record, including frames with no supported annotation. An empty list means
  **no supported annotation**, not a proven obstacle-free scene. `exhaustive_obstacles` is false;
  unmatched detector STOPs are unresolved observations, not automatically false positives.
- Unsupported intervals inside an object's visible lifespan are explicit in the per-object
  summaries and `coverage_unknown_frames`: **109 switch frames and 36 tunnel frames**. No
  interpolated box is asserted as a visible object in those gaps.
- `annotation_confidence` distinguishes supported shape, sparse returns and uncertainty. The
  hanging object's isolated frame-248 return at 246.7 m is retained as **uncertain**, not silently
  converted into a confirmed early visibility claim. Earlier-boundary inclusions and exclusions
  are retained in [switch](boundary_review_switch.json) and [tunnels](boundary_review_tunnels.json).
- The rail-adjacent small boxes have **boundary uncertainty**. Sensor-left zero is not assumed
  to be a surveyed rail axis, and organizer intent is not invented. The independently reviewed
  central hanging obstruction, panel and cross-rail object are marked inside only in the near
  supported scene, at most 60 m; farther relationships are unknown. The platform labels retain
  their separate exact-reference provenance and the marginal original box remains uncertain.
- `in_gauge` is `null` for unknown/boundary cases. Scores preserve that uncertainty as bounds;
  `null` is never treated as outside. The old single Boolean intent is not sufficient for these
  annotations.

Coordinates are `forward=-sensor_y`, `left=sensor_x`, `up=sensor_z`. In these archived runs the
mount state is pending for the first 190 frames, then identity, with no provisional rotation.
The mapped sensor points therefore share the detector's vehicle geometry for matching. This
uses calibration provenance, not a detector-fitted track axis as label truth.

## Review artifacts

- [Switch all-frame candidate sweep](pictures/switch_all_candidates.png),
  [accepted trajectories](pictures/switch_trajectory_review.png),
  [all candidate records](candidates_switch.json.gz).
- [Tunnel all-frame candidate sweep](pictures/tunnels_all_candidates.png),
  [accepted trajectories](pictures/tunnels_trajectory_review.png),
  [all candidate records](candidates_tunnels.json.gz).
- Corrected [switch left box](pictures/switch_box_left_4_review.png), newly found
  [tunnel left box](pictures/tunnels_box_left_4_review.png),
  [hanging obstruction](pictures/switch_hanging_3_review.png),
  [panel](pictures/tunnels_panel_2_review.png), and
  [cross-rail object](pictures/tunnels_flat_crossrail_3_review.png).
- Other object contact sheets and the complete platform-tail contact sheets are in
  [pictures](pictures/) and [platform_review](platform_review/).
- Missing-support checks: [switch](gap_review_switch.json), [tunnels](gap_review_tunnels.json).
- Independent broad-scene and fourth-tunnel-object review:
  [root review notes and contact sheets](root_residual_review/README.md).
- Frozen source hashes and annotation-tool checks: [validation receipt](VALIDATION.md).

Magenta in the final contact sheets is the selected raw annotation support; grey is surrounding
raw context. A sparse far row can be one unique point stored twice. It is not a complete object
shape, and the full-scene candidate plots still contain unlabelled background proposals.

## Reproduce accepted labels

```bash
python scripts/annotate_synthetic_tracks.py <cache>/synthetic_switch \
  docs/evidence/n5_labels_2026-10-17/reviewed_boxes_switch.json \
  --out <output>/labels_synthetic_switch.json
python scripts/annotate_synthetic_tracks.py <cache>/synthetic_tunnels \
  docs/evidence/n5_labels_2026-10-17/reviewed_boxes_tunnels.json \
  --out <output>/labels_synthetic_tunnels.json
python -m pytest -q tests/test_team_annotation_builder.py tests/test_score_team_labels.py
```

The platform builder and exact-source reproduction are described in
[PLATFORM_REVIEW.md](PLATFORM_REVIEW.md); scoring has its own fixed protocol and reproduction
instructions in [SCORING.md](SCORING.md). The canonical JSON files are frozen before scoring.
