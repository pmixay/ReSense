# P1 raw-bag rail-object continuity screen — 28 September

**Outcome: `tracking.hold_misses = 2` is rejected; the shipped detector is unchanged.** The
candidate restores the three reported rail-object STOP dropouts in an offline replay of the
original bag. It also increases false detections and fails the strict cached regression gate, so
this result earns no score credit.

## Input and provenance

The organizer's `doubleT_obstacle` bag was streamed from the Google Drive archive documented in
[`docs/DATASET.md`](../../../DATASET.md) and unpacked outside Git at
`/data/for_hackathon/doubleT_obstacle`. Its DB3 SHA-256 is
`05f1d7f7d1bbbc5e9453877416cc9f7367c19e31d35a5291271d863fc89c5ad9`, matching
[`scripts/cold_bags.sha256`](../../../../scripts/cold_bags.sha256). The repository also pins the
archive at `e23166801794cdeb2dcd77a3cc8b40a906b1d9cefab6f26739e368234e9168be`, but that archive
hash was not recomputed during this streamed extraction. The metadata SHA-256 is
`90f3314528232a912a0a2a1de8e90e1d155a814ab59a130aec3fcf65d76a6c09` and it byte-matches the
repository-captured metadata. The archive itself was not saved or hashed. The data files remain
outside Git.

The bag-level metadata and SQLite both report 201 stored messages over 20.392 s. The nested
per-file count in `metadata.yaml` says 205, so that one field disagrees. The replay used the 201
actual SQLite messages and preserved the recording's timestamp gaps: 0.2011 s at +13.992 s and
0.4126 s at +16.902 s. No frames or timestamps were added.

The experiment used branch `gpt-score-push-20260928`, code commit `d73af5a`, Python 3.12.3 and the
built native kernels. `resense/detector.py` and `resense/tracking.py` were unchanged. The default
effective config hash was `de5c7fd6dfa74c1e656af6e233efd625e3e552736534e32efa625e5e8ff57f47`; the
candidate's only effective change was `tracking.hold_misses: 1 → 2` (effective hash
`0648a9b68aacdabba65a811d1c83667878a1f22b286d141d29beecb5e8efe02c`). The exact candidate YAML,
full per-frame outputs, gate JSON and comparison JSON are kept beside this README. Their hashes
and the compact counts are in [`summary.json`](summary.json). Latencies in these offline files are
not comparable: the runs had different page-cache state and overlapped other CPU work.

## Result

| Measure | Default, raw bag | `hold_misses = 2`, raw bag |
|---|---:|---:|
| Rail object, frames 75–200 | 123/126 | **126/126** |
| Rail object, all visible frames | 125/185 | 128/185 |
| Crossing person, visible frames | 61/61 | 61/61 |
| Alarm frames | 190 | 193 |
| Rail-object misses after frame 75 | 111, 117, 197 | none |

The default raw replay reproduces the committed ROS-node decisions at the three target frames:
GO at 111 and CAUTION at 117 and 197. In the candidate replay, each becomes a STOP while the
person remains 61/61. The hold also extends a stale, unmatched gauge track at frame 75 (track 4,
56.70 m, lateral 1.29 m), adding one unmatched detection on the same recording. That is evidence
that a global extra hold can preserve false tracks as well as a real obstacle.

The candidate then failed the strict full-data gate with no waivers. Against the current default
reference, the cached empty-ride evaluation changed from 130 alarm frames / 32 events / 31 STOP
episodes to 150 / 34 / 29. The five empty recordings went from 40 alarm frames to 46. Set F false
detections increased for person 6→8, 1.0 m box 12→13 and trolley 5→6. The gate reports those four
rows as regressions; it also reports better set-R rail-object hits and fewer ride STOP episodes.
The regressions reject the setting despite its gain on this known object.

The candidate was not replayed through the ROS node after failing the registered strict gate
stage. The raw offline run used the production `Detector` on the original PointCloud2 bag; default
ROS-node evidence is in the [28 September per-frame review](../../judge_outputs_2026-09-28/README.md).
This screen shows that extra track hold bridges the output gaps, but it does not yet isolate which
point-filter or association stage drops the rail-object evidence on those frames. The next detector
investigation must trace that stage and find a continuity rule that distinguishes a confirmed
obstacle track from stale off-axis tracks before it can be reconsidered.

The latest independent score remains **69/100 on `a2f9122`**. No score was recalculated because no
detector change passed acceptance. This is previously inspected organizer data, not new holdout
evidence.

## Reproduction

With the verified bag at `/data/for_hackathon/doubleT_obstacle`:

```bash
/tmp/resense-p4-venv/bin/resense run \
  --bag /data/for_hackathon/doubleT_obstacle \
  --topic /sensing/lidar/hesai128/pointcloud --every 1 \
  --config configs/default.yaml \
  --out /tmp/default.jsonl --quiet

/tmp/resense-p4-venv/bin/resense run \
  --bag /data/for_hackathon/doubleT_obstacle \
  --topic /sensing/lidar/hesai128/pointcloud --every 1 \
  --config docs/evidence/results/p1_raw_continuity_2026-09-28/hold_misses_2.yaml \
  --out /tmp/hold_misses_2.jsonl --quiet

python scripts/regression_gate.py \
  --cache /data/cache --jobs 1 --chunks 8 \
  --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json \
  --set tracking.hold_misses=2 \
  --work out/p1_hold_misses_2_20260928/gate \
  --out out/p1_hold_misses_2_20260928/gate.json
```

The last command exits nonzero by design because the candidate fails the gate. The measured
comparison against the current default reference is also preserved in
[`current_reference_comparison.json`](current_reference_comparison.json).
