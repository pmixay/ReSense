# Full-return oracle translation: clean-improvement screen fails

**No production change, real-odometry claim or measured STOP gain.** All 44 registered
frames were retained. Translating full clouds with oracle source-relative X motion does
not preserve the earlier source-only >100 m result as independently supported object
candidates. Recomputed membership creates many background-only gauge candidates.

Protocol registered at `6dd095b` before execution:
[`ORACLE_FULL_RETURN_PROTOCOL_2026-09-28.md`](../../../ORACLE_FULL_RETURN_PROTOCOL_2026-09-28.md).
The first study is [separate](../oracle_accumulation_2026-09-28/README.md): its physical
union contained known source points only. This follow-up translates **all cached returns**,
then uses the same current advisory corridor for held/recomputed strict-mask alternatives.
Paired backgrounds remove every organizer-appended object group before clustering.

## Results

All variants use the bounded physical neighbor graph and existing count, shape and smear
rules. There are 34 source frames above 70 m and 15 above 100 m. These are correlated
frames of one inspected synthetic approach, not independent trials.

| Window / strict flags | Source-candidate frames >70 m | Source-candidate frames >100 m | Pure-source candidates >100 m | Paired-background gauge candidates / frames | Ordinary background candidates |
|---|---:|---:|---:|---:|---:|
| 2 / historical | 11 | 0 | 0 | 3 / 3 | 1 |
| 3 / historical | 7 | 0 | 0 | 5 / 4 | 3 |
| 2 / recomputed | 16 | 1 | 0 | 4 / 4 | 2 |
| 3 / recomputed | 10 | 1 | 0 | 121 / 35 | 98 |

“Ordinary” excludes candidates flagged thin or weak. Even ordinary gauge candidates
still need tracker confirmation; none of these figures is a false-STOP count. Some thin
candidates would fail the far-tracking strict-voxel bar, so counting all 121 as alarms
would overstate the result. The 98 ordinary candidates alone fail the clean-improvement
screen against the prior one-frame background result of zero.

The two source-touching candidates above 100 m both depend on background points:

- Frame 303, two recomputed frames: object at 110.12 m; 4 source points among 12 total,
  only **2 source strict voxels**; candidate begins at 108.61 m. The paired background
  also produces a gauge candidate at 108.61 m. This is not an injection-only gain.
- Frame 308, three recomputed frames: object at 102.55 m; 6 source points among 9 total,
  from frames 306/307/308, but only **2 source strict voxels**. Its third strict voxel
  is supplied by background. Candidate begins at 102.41 m.

The requirement for three contributing source frames is met in the second case, but
independent source support still fails the unchanged strict minimum of three. Source
membership and background contribution must be assessed together.

## Causal interpretation

Physical alignment can supply enough source-only voxels: before clustering, the
three-frame recomputed full union has three strict source voxels at frames 301, 303,
305 and 309. After it joins background, smear fallback strips away history. At frame
301 the cluster passed to the shape/count stage retains only the current source point,
then fails the count bar. Frames 303 and 309 retain current source points in elongated
background fragments and fail infrastructure filtering. The point-count threshold
alone is not the limiting stage.

Holding historical strict flags remains conservative. Recomputing them on the same
translated union substantially increases background membership, as the 5→121 three-frame
background-candidate count shows. This isolates a membership effect under this particular
oracle alignment. Comparison with the earlier production buffer also changes coordinate
re-embedding and the retention of raw points outside past corridors; it does **not**
establish track-fit jitter as the sole or principal cause.

Source-relative scalar motion is not a rigid physical ego pose, particularly on a curved
track. The result therefore rejects this simple candidate; it does not prove accurate
six-degree pose compensation cannot work. It also shows why source-only injection masks
would give an optimistic picture of the actual background tradeoff.

## Recommended next gate

Keep the production defaults. Further range work needs a measured vehicle-pose signal or
independently validated cloud registration, with uncertainty sufficient for the narrow
envelope margin, before reconsidering a physical point buffer. The next implementation
should be an optional candidate, assessed with an exact sequential observer, source-free
full-ride controls, and new obstacle placements/real labeled approaches. It must preserve
source support without promoting compact fragments of track/tunnel surfaces.

If pose compensation still leaves those fragments indistinguishable from small objects,
the missing component is a local surface/instance model trained and validated on such
negatives plus real small targets. Changing count thresholds or increasing the number of
frames cannot supply that distinction. No additional threshold or buffer experiment is
authorized by this completed protocol.

## Reproduce

```bash
python scripts/diagnose_oracle_full_returns.py \
  --db /data/fake-positive/cloud_with_fake_obj/cloud_with_fake_obj_0.db3 \
  --cache /cycle/cache/cloud_with_fake_obj \
  --out out/oracle_full_returns/results.json.gz
python scripts/summarize_oracle_accumulation.py out/oracle_full_returns/results.json.gz \
  --out out/oracle_full_returns/summary.json
```

Results retain per-message/cache hashes, historical geometry, original timestamps, source
identities through accumulation, cluster contamination, source-frame support, actual filter
return conditions and current thresholds. The source/model/observer hashes are embedded.
The translation/provenance test and eight preceding diagnostic tests pass; Ruff passes.
No tracker or full detector replay was run for this study.
