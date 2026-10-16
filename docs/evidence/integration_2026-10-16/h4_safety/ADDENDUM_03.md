# Adapter audit and beam-dropout follow-up — before follow-up measurement

The component adapter initially treated `Tracker.update()`'s return list as the
reported list. Source inspection at tracking.py:478 confirms it returns **all**
tracks. All raw component frames already preserve the actual `reported` boolean,
zone and physical identity of every track, so correct postprocessing is possible
without changing or repeating detector measurements. Initial `stop_labels` /
`stop_ids` and `*-summary.json` component fields are invalid STOP counts.
Keep them as audit artifacts. A separate `derive.py` will recompute STOP sets
strictly as `reported and zone == 'gauge'` from the immutable raw track snapshots;
all final comparisons and witnesses will use those derived sets. The end-to-end
real replay uses FrameResult.obstacle/detections and is unaffected.

The initial beam sequence's dropout mask also removed its above-envelope beam
along with the target. Register a separate `beam` follow-up for both sources:
keep beam returns, remove target-object returns only on frames 9/10; preserve all
original geometries, ring modes and seeds. No other physical scene is affected.
The corrected adapter is used for this follow-up and the previously registered
`span` follow-up. No production changes or assertion changes are involved.
