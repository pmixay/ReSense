# Range geometry diagnostic — 28 September

Status: diagnostic only, production unchanged. Base `786a5fb`. No detector improvement,
range gain, false-alarm result or score change is claimed.

**Measured conclusion:** the physical-edge filter isolates the cube from background in
four measured far frames, but all four still have only two strict source voxels against
the required three. Radial voxel subdivision adds no far-cube source support. This
diagnostic supplies **no demonstrated STOP gain** and does not justify lowering that bar.
The [138-frame evidence packet](evidence/results/range_metric_2026-09-28/README.md)
records the findings and limitations.

## Hypothesis and existing evidence

`resense/clustering.py:57` transforms each point as `p / (1 + r/R)`, with `R=40 m`.
The comment at `cluster_labels` says its metric radius grows linearly with range.
That holds locally transverse to the viewing direction. Along the viewing direction,
the derivative is `1/(1+r/R)^2`, so the physical neighborhood grows quadratically.
Both `voxelize` and `cluster_labels` use this transform. `find_hanging` also uses it.
There is no separate implementation of this transform in the native C++ source.

| Range | Outward radial neighbor at eps 0.35 | Local transverse radius | Local radial voxel size at voxel 0.05 |
|---:|---:|---:|---:|
| 50 m | 1.81 m | 0.79 m | 0.25 m |
| 100 m | 4.42 m | 1.23 m | 0.61 m |
| 150 m | 8.24 m | 1.66 m | 1.13 m |
| 200 m | 13.30 m | 2.10 m | 1.80 m |

The radial neighborhood figures are exact for two points on the same outward ray;
voxel figures are local derivatives, not a bound for every Cartesian cell orientation.

The retained **26 September P3d trace**, not a current-head replay, contains 23 rejected
oversized blobs touching `small_center`, frames 299–327, target distances 116.03–72.30 m.
Their median X extent is 22.99 m. Eleven frames retain strict source returns. Eight of
those have four source returns (311, 314, 316, 318, 321, 323, 325, 327), but only two
strict source returns each. Thus removing background links may still leave too few
strict voxels for detection. Historical trace totals cannot establish a current gain.

The trace stores total blob voxels, not source-only voxel occupancy or neighbor edges.
Those must be measured separately. In the same historical trace, edge objects mostly
have no points in the fitted nominal polygon (67/83 small-edge; 116/125 large-edge).
This metric hypothesis cannot fix that upstream geometry loss.

## Lightweight observer

`scripts/diagnose_range_metric.py` reads the committed organizer source fixture and
selected full set O cache frames, restores serialized historical geometry, and calls
only the current corridor-selection function. It never calls `Detector.process` or
changes detector state through tracking. The restored geometry is rounded and the
current corridor differs from the historical one, so outputs are explicitly labelled
**historical-geometry conditional corridor**, not baseline replay parity.

It matches fixture returns by exact quantized XYZ/intensity with multiplicity. The
fixture omits ring; indistinguishable extra copies are recorded. Missing source points
fail. It checks the fixture's extraction hash and records cache/code/trace hashes.
The fixture covers 15–80 m; it cannot quantify voxel loss above 80 m.

For the full selected corridor it reports:

- Source occupied voxels, strict source occupied voxels, mixed source/background cells,
  and the largest radial span of source-occupied cells.
- Production neighbor edges, their physical lengths, and edges exceeding
  `eps * (1 + min(r_i,r_j)/R)`, including source/background bridges.
- Background returns connected to source voxels before and after that edge filter.
  Connectivity is measured before DBSCAN core tests; it is not a detection prediction.
- The same quantities after subdividing existing voxels by
  `floor(R * log(1+r/R) / voxel)`. This adds radial resolution without merging any
  previously separate voxel. It is a diagnostic alternative, not a proposed default.

```bash
python scripts/diagnose_range_metric.py \
  --cache /cycle/cache/cloud_with_fake_obj --object small_center --limit 40 \
  --out out/range_metric/small_center.json
```

## Registered next diagnostic, before a production candidate

1. Freeze current source/config and select target and negative frames before comparing
   alternatives. Capture exact inputs to `voxelize` with explicit source identities from
   a sequential baseline run; include low-object, main corridor and hanging consumers.
   Preserve geometry, masks, intensity, raw indices, timestamps and accumulation tags.
   First prove the observer leaves every detector output unchanged.
2. Compare four variants on the same captured input: existing voxels/graph; existing
   voxels with bounded physical edges; radially subdivided voxels with existing graph;
   both changes. Keep min_samples, strict membership, cluster shape tests, confirmation
   and all other thresholds fixed. Record source footprint occupancy separately from
   raw point count. Record edge distances and component contamination by range bin.
3. Promote only if removing bridges recovers actual admissible source clusters on more
   than isolated frames. Stop if strict membership or independent source support still
   blocks them. Increased voxel count alone is not new independent sensor evidence.
4. Then test complete chronological approaches: first and sustained STOP range, misses,
   nearest-distance correctness, and every existing regression gate. Require material
   sustained gain on target cases, no lost existing positive frames, no additional
   outside-object/background STOP frames, and no increase in ride/empty-bag events,
   episodes or alarm frames. No monitored-range regression or new overclaims.
   Measure speed only without the observer. Check native enabled/disabled agreement.

## Controls and limits

Reserve new synthetic seeds and placements before changing code. Cover both sides of
the physical envelope, inside/outside offsets, straight and curved tracks, positive and
negative yaw, short cubes and long planks, top-only scan lines, sparse people, multiple
objects at distinct depths, and real tunnel/platform/rail structures with no injection.
Use pairings with their untouched backgrounds. Add physical cases with radial gaps just
below/above the intended neighborhood at 30, 60, 100, 150 and 200 m. Include long connected
infrastructure: splitting it can create compact false targets that evade existing shape
filters. Require no new STOPs on these controls before any default changes.

The inspected fixture and trace are development evidence. New synthetic controls still
do not establish real unseen obstacle performance. Earlier edge detection needs an
independently validated rail/vehicle pose and envelope reference; widening a polygon or
reducing its uncertainty margin cannot resolve the missing reference truth. Reliable
small-target detection above the available return density likely needs motion-compensated
multi-frame point evidence with measured pose, or additional real labeled examples for
a learned point/instance model. Existing threshold changes cannot supply missing returns.

## Next bounded experiment: motion-supplied upper bound

The shipped accumulation path already exists: `Detector._accumulate`,
`resense/accumulate.py::CandidateBuffer`. It retains five frames beyond 40 m but needs
a supplied speed; speed estimation is off by default. It stores X/dy/height and historical
strict flags, then shifts X by speed times dt and re-embeds points in the current track.
At five frames the count multiplier is 1.5, raising the strict voxel bar from 3 to 5.
Smear guards return clusters longer than 2 m or wider than 1 m to current-frame points.
These mechanisms must be observed before assuming temporal density will help.

Weak far tracking does not bypass the strict envelope: `_far_thin` requires a gauge-zone
cluster; flat candidates additionally need four strict voxels. Two strict points remain
warning evidence even if the weak total-point bar is met. Existing approach confirmation
therefore cannot alone rescue the isolated far cube in this diagnostic.

The next experiment should compare default and bounded physical neighbor graphs with
the **same supplied source-relative motion**, then compare each with no supplied speed.
Fit a local approach trajectory only to the organizer fixture's original vehicle-frame
X coordinates and extraction timestamps, independent of detector axis/height/decisions.
Do not place or move an injected object using a fitted detector track. Record source Y/Z
changes as well, to distinguish lateral motion or height changes from pose-fit jitter.
For the 39-frame cube fixture the median adjacent X approach speed is 16.96 m/s; one
repeated source range gives zero and the following step reaches 33.17 m/s. A constant
speed or naïve per-step derivative would misalign those frames. Register a local-fit
method and preserve all frames and gaps; do not tune it against detection results.

This supplied speed is an **oracle source-motion upper bound**, not measured vehicle
odometry: synthetic source motion need not equal the destination/background motion.
The same speed must be applied to paired backgrounds with source points removed, so
false compact clusters produced by background smearing remain visible. First capture
source identities through accumulation and report unique contributing frames, strict
occupied voxels, duplicates, smear fallback and final cluster rejection. Only then run
tracking and assess sustained STOP gain. If ideal supplied motion still fails the count,
geometry or shape tests, stop this candidate. If it helps, obtaining accurate physical
ego-motion/pose remains a separate requirement before any production deployment.
