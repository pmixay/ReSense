# Reserved v2: fixed continuity candidate

**PASS: no candidate regression, and no synthetic gain.** Baseline and candidate public
signals are identical on all 1,152 paired detector frames: STOP/matching flags, IDs, detection
geometry, clear distance, warning and offline decision. Absolute detection remains limited.

The protocol was registered before generation, the baseline/candidate were frozen in
`f22fd50`, and the root reviewer authorized this run in `6f910cf` after inspecting the complete
candidate real regression gate. The reserved cache was then generated **once**, followed by
baseline and candidate replays of identical float32 clouds and compact16 derivatives. No source,
config, tool, label or acceptance threshold was tuned after observing reserved outcomes.

## Results

These values are identical for the baseline and candidate:

| Metric | Float32 | Compact16 |
|---|---:|---:|
| Sustained positive sequences | 14/32 | 13/32 |
| Matched STOP / visible target frames | 168/512 | 158/512 |
| Positive cases never detected | 18/32 | 18/32 |
| Unmatched STOP frames in positive cases | 0 | 0 |
| STOP frames across four negative controls | 0/64 | 0/64 |
| Visible-target clear-distance flags with GO | 232/512 | 233/512 |
| All visible-target clear-distance flags | 232/512 | 243/512 |

A clear-distance flag means the public clear distance exceeds the registered target distance
by more than 1 m. The ten additional compact16 flags have **CAUTION**, not STOP or GO.
All 32 positive bodies physically intersect the canonical envelope, and every positive frame
has target returns; visibility of the intersecting body portion is a separate reported count.

All rail_box, compact_box30 and box50 cases at **60, 110 and 170 m** are never detected, on
both lateral placements and both encodings. Their 28 m cases detect. Persons detect at every
registered distance, but the quantized 170 m edge person does not sustain its STOP.

### Quantization failure

`person_170m_1` confirms at frame 4 in both encodings. Float32 keeps STOP through frame 15
(12 frames); compact16 keeps STOP only at frames 4–5 (two frames) and misses frames 6–15.
Its steady visible recall is therefore **1.0 versus 0.0**. This discrepancy occurs identically
in baseline and candidate; the continuity change does not fix it.

There are **10/576 matched-STOP disagreements** between encodings, despite **0/576 differences
in physical-envelope target-return counts**. Equal counts do not mean identical coordinates,
fitted geometry or downstream decisions. This is an observed reserved failure, not evidence
for a particular unmeasured cause. No diagnostic detector rerun or parameter search followed it.

## Provenance and scope

The measured candidate is `ef1d8f50299d9ccbbf65fc4ad5519764615853f6` with source digest
`2389db97234b8c59ca4e5ebacf0eccffaba8ea44e97cdcbfe1df272864a5dab2` and effective config digest
`6a6e5d859a0c1a86adce91edf1e8a46cd35b4bee21c5876406f1071cf2eaa46f`. The baseline retains the
original detector/config bytes; its current documentation-only commit is `f22fd50`.
The freeze contains both complete source/config identities.

Every replay checks every cloud digest. Source, effective config, native library, protocol,
evaluator and physical-auditor hashes match the committed freeze. The physical counter uses
the canonical polygon saved at generation, and the actual imported helper was independently
checked against its frozen hash. All 36 cases completed in both encodings for both detectors.
The input manifest and compressed reports are committed; cloud binaries remain outside Git.

This was the final reserved synthetic check for this fixed candidate. The full real regression
result, history stress, image tests and original ROS replay are separate evidence. Passing this
paired comparison does not demonstrate improved range or generalization: these scenes expose
substantial existing misses. Stationary related synthetic geometries are not independent trials
or a new real-route holdout. No latency claim is made while other jobs share the machine.

The reserved split is now **spent**. If these results guide another change, later evaluation
must say so and use fresh prospective cases for a new reserved acceptance claim.

## Artifacts

- [Acceptance and authorization provenance](reserved-acceptance.json).
- [Full comparison summary](comparison-reserved-v2.json), with complete-case gate result,
  per-encoding counts, signal differences and exact report-file hashes.
- [Baseline per-frame report](baseline-reserved-v2.json.gz) and
  [candidate per-frame report](candidate-reserved-v2.json.gz).
- [Reserved input manifest](reserved-manifest-v2.json.gz), containing all 576 cloud digests,
  seeds, physical labels and generator identity.
- [Committed freeze](reserved-v2-freeze.json) and [registered protocol](protocol_v2.json).

Summary hashes refer to linked gzip bytes. Manifest hashes inside replay reports refer to the
uncompressed manifest JSON. The summary's `split: evaluation` identifies this reserved run;
its general caveats about synthetic development do not describe real-route holdout evidence.

## Reproduce the measured comparison

From the same checked-out tooling and frozen production implementations, with the saved
reserved cache (do not regenerate different clouds):

```sh
RESENSE_DETECTOR_ROOT=/workspace/ReSense-evaluation \
  python3 scripts/synthetic_sensitivity.py evaluate \
  --protocol docs/evidence/cycle_2026-09-28/evaluation/protocol_v2.json \
  --candidate-freeze docs/evidence/cycle_2026-09-28/evaluation/reserved-v2-freeze.json \
  --cache /cycle/synthetic/evaluation-v2 --output /cycle/synthetic/baseline-reserved-v2.json
RESENSE_DETECTOR_ROOT=/workspace/ReSense-continuity \
  python3 scripts/synthetic_sensitivity.py evaluate \
  --protocol docs/evidence/cycle_2026-09-28/evaluation/protocol_v2.json \
  --candidate-freeze docs/evidence/cycle_2026-09-28/evaluation/reserved-v2-freeze.json \
  --cache /cycle/synthetic/evaluation-v2 \
  --baseline /cycle/synthetic/baseline-reserved-v2.json \
  --output /cycle/synthetic/candidate-reserved-v2.json
```
