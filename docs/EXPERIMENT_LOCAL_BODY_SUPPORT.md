# Local-body support decomposition — 28 September 2026

**Historical report:** source/default references describe the pre-merge research state preserved
in `9aa1775`; see [integration provenance](RESIDUAL_REVIEW_2026-09-28.md#integration-provenance).

**Result: diagnostic rejection; no detector selector or production change is justified.**

This experiment tested whether one fixed, runtime-identifiable local decomposition could recover
resolved person/cable support after a connected background connection while rejecting compact false
bodies. It did not find an accuracy-preserving selector. The diagnostic output is:

`C:/Users/alikh/AppData/Local/Temp/opencode/local-body-support.json`

The only new repository files are this report, `scripts/analyze_local_body_support.py`, and
`tests/test_local_body_support.py`. No production/configuration file or existing file was edited.

## Inputs and provenance

Positive inputs were the coordinator's live-default diagnostic artifacts, compared with saved
fresh-onset evaluation rows (not direct fresh-config traces):

* `C:/Users/alikh/AppData/Local/Temp/opencode/range-shape-centre-coordinator.json`
* `C:/Users/alikh/AppData/Local/Temp/opencode/range-shape-edge-coordinator.json`

These contain exact saved component points, current-frame point identities, effective strict masks,
reference coordinates, effective validity ranges, and injection identities. The injection identity
was read only after decomposition for scoring. The script validates the reconstructed float32
production voxel memberships against every saved positive support record before reporting results.
It also requires the saved baseline and paired replay parity flags.

Negative inputs were the first alarm/current-support snapshots for:

* `new_data_1.jsonl:74` — `new_data_1_id74_0438.npz`
* `new_data_1.jsonl:298` — `new_data_1_id298_1262.npz`
* `new_data_6.jsonl:331` — `new_data_6_id331_0810.npz`
* `new_data_5.jsonl:330` — `new_data_5_id330_0819.npz`

The frozen trace reports 11,271 frames with no detection-mismatch frames. Only snapshots with
current matched support were used; missed-track rows were not treated as current support.

## Fixed diagnostic

The decomposition operates only on runtime points, supplied masks, reference fields, current-frame
indices, and production voxel membership:

1. Retain current candidate points (`frame_idx >= 0`), optionally intersecting the supplied strict
   mask.
2. Represent each occupied production voxel by its point centroid.
3. Link voxel centroids in physical XY with a fixed **0.45 m** radius and unchanged
   `ClusterConfig.min_samples == 3`. Vertical voxels remain separate support; Z is not used as a
   link distance.
4. Describe each subset with existing ordinary clustering geometry, without changing thresholds.
   The positive report records both an ordinary geometry proxy and a reference-aware proxy.

The radius is the existing fixed diagnostic window used by `tests/test_far_structure.py`; it was not
swept or fitted per event. There is no connected-size veto, threshold lowering, ring assignment,
invented channel identity, temporal rule, or detector output change.

### Mask distinction

Positive support uses the actual effective corridor strict mask saved by the production-stage trace,
including the active reference/union result where applicable. It is not reconstructed from the rail
polygon. Low-stage records are excluded from the corridor-mask measurement and counted separately.

Negative NPZ snapshots have current XYZ, `dy`, `h`, and saved track membership, but do not contain
the production candidate/strict/union masks or effective validity flags. Their masks are therefore a
clearly labelled **rail-only crop approximation**, computed from the supplied runtime `dy/h` and the
current `GaugeConfig`; they are not production strict/union masks. Negative reference-aware results
are consequently unknown, not inferred. The crop's saved track membership is used only for scoring.

## Measurements

The complete per-frame/per-subset values, hashes, and counterexamples are in the JSON artifact.
The decisive aggregate values are:

| Dataset | Fixed corridor subsets | Fixed strict subsets | Interpretation |
|---|---:|---:|---|
| Centre person, split 47 | 11/11 complete oracle-target recoveries in the 11 missed rejected frames | 11/11 | The local decomposition can isolate the known target subset in these exact positive blobs. |
| Centre cable, split 47 | 1/1 complete oracle-target recovery in the missed rejected frame | 1/1 | Same mechanism occurs once in the supplied cable trace. |
| Negative `1:74` | 1 ordinary local body; complete strict false-body overlap | 1 ordinary local body; complete strict false-body overlap | Compact support is not identity evidence. |
| Negative `1:298` | 1 ordinary local body; complete strict false-body overlap | 1 ordinary local body; complete strict false-body overlap | Same compact-body ambiguity. |
| Negative `6:331` | 1 ordinary local body; no complete strict false-body overlap | 1 ordinary local body; no complete strict false-body overlap | The crop approximation changes strict completeness, but does not remove the false local body. |
| Negative `5:330` | 1 ordinary local body; no complete strict false-body overlap | 1 ordinary local body; no complete strict false-body overlap | The crop approximation changes strict completeness, but does not remove the false local body. |

For context, all 11 centre-person positive failures and the one centre-cable failure are the
already identified oracle-only cases. The report also measures all six centre and six edge sequence
draws: positive local ordinary overlap exists in many frames, while sparse edge cube/rail-object
sequences have no complete ordinary local rescue. Removing background cannot create missing count,
height, or distinct-voxel support.

## Rejection and counterexamples

The positive result is an oracle decomposition result: injection identities show that one local part
contains the target support. It does not show that runtime can know which part is the target. The
negative snapshots show why a compact strict body, ordinary local descriptor, vertical extent, and
local separation from cropped context are insufficient: each of `1:74`, `1:298`, `6:331`, and `5:330`
also yields an ordinary local body under the same fixed measurement.

No selector was selected because the same runtime-observable body predicates required to retain the
resolved positives are present in known false bodies. The negative masks are approximate, so they
cannot support a claim of production false-alarm prediction; they are nevertheless sufficient as
counterexamples to claiming that compact local decomposition alone establishes identity. The
coordinator's fresh trace with common-reference transforms and tracker provenance remains required
for any future temporal experiment.

## Verification

Commands, run from the repository root with the requested interpreter:

```powershell
$py = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe'

& $py scripts/analyze_local_body_support.py `
  --centre 'C:/Users/alikh/AppData/Local/Temp/opencode/range-shape-centre-coordinator.json' `
  --edge 'C:/Users/alikh/AppData/Local/Temp/opencode/range-shape-edge-coordinator.json' `
  --measurement 'D:/Datasets/ReSense/cross_ring_2026-09-28_measurement' `
  --out 'C:/Users/alikh/AppData/Local/Temp/opencode/local-body-support.json'
# passed; status diagnostic_only_no_justified_selector

& $py -m pytest -q tests/test_local_body_support.py
# 5 passed

ruff check --no-cache scripts/analyze_local_body_support.py tests/test_local_body_support.py
# All checks passed!
```

The analyzer's output JSON is temporary by design. Its measured decomposition is not a latency
measurement, not a replay of negative production candidates, and not evidence for changing a
detector default.

## Follow-up with direct fresh inputs

[The direct fresh-support experiment](EXPERIMENT_FRESH_LOCAL_SUPPORT.md) subsequently replaced the
cropped negative masks and geometry proxies with actual descriptor inputs and effective validity
ranges. It also reran both positive sets with fresh STOP enabled. This distinction changes two
negative results: local subsets of `1:74` and `1:298` are **advisory, `beyond_height_ref`**, not ordinary
STOP-eligible bodies. Their nearest support is farther than the nearest point of the full component.
`6:331` still produces an ordinary body in both modes; `5:330` does so only in corridor mode.
The 11 person and one cable local-subset recoveries persist with the exact descriptor. Thus the
geometry-proxy table above is historical exploratory evidence, not the direct-fresh result.
