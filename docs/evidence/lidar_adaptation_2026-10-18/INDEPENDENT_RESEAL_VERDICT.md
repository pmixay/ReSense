# Independent corrected-core acceptance verdict — 18 October 2026

**The complete default gate and corrected-core X3 PASS, but unconditional acceptance/resealing of global replay4 is BLOCKED by the registered actual-Falcon no-loss criterion.** Measured core is `7b7b02c9b535d2b03d053df1b309301b619269ad`. The passing original-data checks supersede the X3-pending condition in the earlier [full-gate review](INDEPENDENT_GATE_REVIEW.md); they do not waive the separately observed actual-Falcon losses or approve release/deployment.

## Actual-Falcon criterion adjudication

The registered [bounded orientation-adoption replay protocol](PROTOCOL.md#n2-bounded-orientation-adoption-replay-candidate) requires: **“preserve every existing STOP.”** It does not restrict that clause to Pandar or the original gate. N2 also requires measuring the actual Falcon recording and quantifying degradations. Quantification alone is not acceptance of a failed preservation requirement. Applying the stricter clause only to original recordings after observing Falcon losses would silently narrow the registered scope.

The independent audit rehashed and compared all4,443 original-auto/replay4 rows. **28 added and13 lost overall STOP rows** are real decision differences. The lost list is recorded in [the receipt](independent_x3_boundaries.json) under `actual_falcon_no_loss_review`; four lost rows2972–2975 are associated with the main person. At2972, the original output is STOP with a19-return box at centre`[124.99, 0.11, -1.18]`, lateral−0.61m. Replay4 retains that same centre/19 returns as a warning at lateral−0.84m and publishes CAUTION. Changed estimated gauge geometry therefore changes the actual decision; this is not merely a reporting or association-counter discrepancy.

Person association does not prove surveyed in-gauge truth, and the old decision may itself be inaccurate. However, there is no evidence establishing that all13 lost STOPs were false positives and no approved exception for them. Earlier first person association (124.67→127.07m) and a net increase in STOP coverage do not satisfy a requirement to preserve every previous STOP. Matching explicit axes is useful correctness evidence but is not an authorized replacement for the registered old-auto preservation baseline.

The full replay4 recording is from the earlier `candidate_71d3067` source. Corrected7b has independently verified ordinary-metadata/prefix/orientation compatibility, but no evidence shows its storage-accounting correction eliminates these full-recording losses. This provenance limit cannot turn the known failure into a pass.

**User resolution:** the user chose **“keep replay opt-in.”** This rejects the global replay4 default for this acceptance scope. Restore default0 and validate that new measured source; retain replay4 as an explicit experiment with its measured tradeoff. Until the new default's required checks complete, no unconditional default4 reseal recommendation is made. Existing gate/X3 evidence remains valid for the exact measured7b candidate and must not be relabeled as default0 evidence.

## Final X3 result

The producer completed with exit0 at **10:36:38 UTC**, after all **40 cases / 29,765 rows**. The [standard raw review](x3_metadata_fixed_independent_review.json) revalidates raw hashes, worker completion identities, exact input membership/stamps, label/protocol identity and recomputed metrics. It reconstructs all **260/260 passing directional checks** independently of the producer's claimed result.

The separate [strict boundary audit](independent_x3_boundaries.json), reproduced by [review_x3_boundaries.py](review_x3_boundaries.py), additionally checks every actual raw decision and all non-timing serialized fields, then derives each STOP interval in processed order. It does **not** use the standing allowance for two lost positive rows or one additional false episode: **all 6,284 STOP frames and 204 episodes are identical**, with zero added, lost, delayed or shortened alarms. Each case starts a fresh detector; no intervals are joined across cases. The `hz5` interval endpoints retain their original source-frame indices.

| Recording, all ten variants | Processed rows | STOP frames, both | STOP episodes, both |
|---|---:|---:|---:|
| Set O | 14,345 | 4,185 | 90 |
| Real obstacle | 1,910 | 1,742 | 32 |
| Square track / pressure gate | 5,178 | 0 | 0 |
| Square track / platform / switch | 8,332 | 357 | 82 |
| **Total** | **29,765** | **6,284** | **204** |

Nominal real-obstacle output retains **193 STOP frames, first at frame8**. Nominal Set O retains452 STOP frames, first at4; nominal platform/switch retains11, first at313. These are the judge X3 input/serialization contract; its counts differ from the separate compact-cache default gate and must not be mixed between protocols.

## Source and acceptance scope

All **38 frozen files** match live source, the immutable measured checkout, Git blobs at `7b7b02c` and the full-gate identity receipt. Digest: `4d57add1f5e255d5aa4a645a2a390eb47204e64893a2b45d1ec6a2a6e1073993`. Every X3 worker completion names that exact source and configuration. Native SHA256 is `511f7766639f0ddab471a77263f7a343de19d0a8217dd7cd3a11635c8a7db2c8`, identical to the measured full gate; the historical X3 reference used its separately recorded Python3.10 native binary. No claim of identical historical runtime is made.

The measured configuration matches the complete default gate: bounded orientation startup replay4, experimental rail-axis extension off. The gate has no waivers, overrides or missing datasets, and preserves all805 ordinary STOP frames/51 episodes plus all3,060 Set F scoring rows. Startup/adoption behavior and memory bounds have separately reviewed orientation and metadata-budget evidence; the normal-axis default gate and X3 are compatibility checks for those changes.

This review excludes decode/detect/total timing and latency-only health text/promotion; it preserves decision health, ranges, geometry and every other serialized field. These are serialized comparisons, not a full-precision internal observer. Timing under shared load is not a performance claim. Set F hit assignments cannot be independently reconstructed from full detections because that legacy format omits them.

## Changes this verdict does not accept

- **N3:** no dust suppression is accepted. The initial suppression hypotheses failed their controls; corrected rail-relative stress measurements remain separately reported. Adding reproducible stress tooling does not establish dust robustness.
- **N6:** the rail-axis extension remains **off**. Source-removal sensitivity and failed controls are retained; no first-person-range improvement is accepted for runtime.
- **Actual Falcon:** the no-loss violation above blocks unconditional global replay4 acceptance. The4,443-frame new automatic replay matches explicit ROS detections/warnings and post-initial decisions; the initial frame remains FAULT with zero range. Increased static-support associations and lost person-associated STOPs remain explicit. See the [full Falcon attribution](../n2_falcon_2026-10-18/README.md#full-recording-static-supports-and-the-person).
- **C2 and deployment:** the accepted conservative projection keeps its explicit sensor applicability; unknown/Falcon small-target coverage remains unavailable with zero claimed conservative clear range. Node/DDS/display evidence has its own image/source scope. No Falcon density prior, release, CI repair or deployment is authorized by this verdict.

After the actual-Falcon criterion is resolved, any new seal should retain historical lineage, identify the current18October task and exact newly accepted measured core, link its full gate/X3 and independent reviews, retain the failed experiments, and pass verification before it is described as complete. The old `f5ff15f` X3 was explicitly rejected by this audit's source-identity guard and was not used for the corrected-core verdict.

## Reproduce the strict audit

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/resense/.venv/bin/python \
  docs/evidence/lidar_adaptation_2026-10-18/review_x3_boundaries.py \
  --reference /home/resense/data/x3_reference/reference.json \
  --candidate docs/evidence/lidar_adaptation_2026-10-18/x3_metadata_fixed.json \
  --review docs/evidence/lidar_adaptation_2026-10-18/x3_metadata_fixed_independent_review.json \
  --source /home/resense/data/final_lidar_7b7b02c \
  --out /tmp/independent_x3_boundaries.json
```

The script reads existing captures only, including the actual-Falcon comparison. Recorded paths must be restored for this strict source-bound invocation; the standard validator separately supports portable raw-archive relocation. Pinned Ruff passes. The opt-in decision is recorded above; implementation and validation of the newly measured default0 source are separate work.
