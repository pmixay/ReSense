# Development v1 stage diagnosis

This is an observation of the unchanged baseline, not a detector improvement or an official
organizer score. The historical v1 protocol and all original labels/results remain intact.

## Geometry correction

The synthetic rails are **0.18 m above the bed**. The canonical envelope is 2.10 m wide,
from **0.12 to 3.00 m above the physical rail head**. Body intrusion and returned-point
intrusion are separate facts. The audit uses the actual mesh dimensions/yaw and known
floor/axis; no fitted track supplies the labels. Person geometry follows the actual
20-sided cylinder plus head mesh, whose top is `0.85 * declared_height + 0.22` above its base.

[`geometry-audit-v1.json`](geometry-audit-v1.json) audits every registered case in both splits.
Auditing the reserved mesh parameters does not generate clouds or observe detector outcomes.
The v1 development cube30 only **touches the envelope floor**: its top is exactly 0.12 m above
the rail head. Its eight cases cannot automatically be treated as positive-volume envelope
intrusions. Rail boxes have 0.01 m vertical penetration; box50 has 0.20 m. The ungenerated v1
reserved split would scale cube30/rail_box below that floor altogether (tops 0.090/0.099 m).
Those 16 reserved positive labels would therefore not be valid envelope-incursion labels.

The original 13 missed v1 cases / 208 GO frames include **five boundary-contact cube cases /
80 frames**, plus **eight cases with physical envelope intrusion / 128 frames**. These are
annotations, not post-hoc relabeling or a recalculated headline success rate. Below-envelope
objects can still engage the detector's separate low/rail-straddle policy; a boundary-contact
case is not evidence that the entire physical body is below the rail head. V2 fixes positive
geometry in advance and separately tests an object entirely below the rail head.

## Replay and parity

[`stage-diagnosis-v1.json.gz`](stage-diagnosis-v1.json.gz) contains all 13 missed v1 cases plus
`person_150m_0` as a sustained control, 16 frames each, float32 and compact16. All **448 outputs**
match the previously saved uninstrumented baseline, including public detection geometry,
clear distance, offline decision, and non-timing health. Instrumented latency and latency-only
health warnings are excluded from parity; this diagnostic supplies no timing measurements.

The observer records target membership through corridor, bed, low/straddle selection,
voxelization, DBSCAN, cluster description and tracking. Hooks invoke production functions once,
observe their actual locals/results and restore them afterward. Each cloud/mask hash is checked;
compact16 target masks follow the decoder's actual finite/range filtering. The baseline/core,
config, observer and runner hashes are saved in the report.

## Causal findings

The following return counts are stable across all 16 float frames. Compact16 has the same
public outputs. Maximum absolute fitted-axis error is 0.020 m; maximum rail-height error is
0.0038 m across the traced float frames. Geometry fitting does not explain these failures.

| Cases | Physical envelope returns | Processing bottleneck |
|---|---:|---|
| rail_box at 100/150 m, both sides | 0 | Body penetrates by 0.01 m, but LiDAR rays do not sample that strip. No corridor points. Low stage ends at 60 m and observed bed at 55 m. |
| cube30 at 100/150 m, both sides | 0 | Body only touches envelope floor; returns lie below it. Same low-stage range restriction. These are boundary-policy diagnostics. |
| cube30 at 50 m, edge | 0 | Seven target returns → four inside low-stage lateral band → three bed-anomaly candidates → two distinct voxels. DBSCAN requires three voxels, so all are noise before low-cluster description. |
| box50 at 100 m, both sides | 0 | Body penetrates by 0.20 m, but center-case returns fall below envelope floor. Edge case adds one advisory return outside nominal width; no strict return. |
| box50 at 150 m, both sides | 2 | Two corridor voxels become DBSCAN noise (`min_samples=3`). Edge uncertainty margin leaves one strict decision point, but clustering fails first. |
| person at 150 m, center | 5 | Five corridor voxels form a valid cluster; STOP confirms at frame 4 and persists through frame 15. |

A target's visible returns do not prove that its envelope-intersecting volume was sampled.
Consequently, the v1 `clear_overclaim` flag means the reported clear distance exceeds that
case's registered target distance; it is not by itself an organizer-policy verdict.

## Bounded next experiments, not accepted fixes

1. Preserve distinct angular-return support in a **near-field compact bed anomaly** when
   voxel merging turns three returns into two voxels. Keep existing physical height, lateral,
   temporal confirmation and real-negative constraints. This addresses the observed edge50
   density loss; it must be remeasured on v2 intrusion cases before proposing production use.
2. For sparse **already strict-envelope** returns at far range, investigate temporal evidence
   that caps clear distance before a confirmed STOP. This requires a narrowly defined stationary
   exception to current approach-based evidence and full real negative regression testing.
   It is not justification for globally lowering DBSCAN density or treating isolated noise as STOP.
3. Far boxes with zero sampled envelope returns need physical observability or validated
   low-object inference. Merely raising the low-stage range flag is insufficient: the measured
   bed ends at 55 m. Their unsampled mesh strip cannot be recovered by changing the fitted axis.

No production code, detector threshold or v1 metric has changed.

## Reproduce

```sh
python3 scripts/diagnose_synthetic_sensitivity.py \
  --cache /cycle/synthetic/development \
  --baseline /cycle/synthetic/baseline-development.json \
  --output /cycle/synthetic/stage-diagnosis.json.gz
python3 scripts/synthetic_geometry.py \
  --protocol docs/evidence/cycle_2026-09-28/evaluation/protocol.json \
  --output /cycle/synthetic/geometry-audit-v1.json
python3 -m pytest -q tests/test_synthetic_diagnosis.py tests/test_stage_trace.py
```
