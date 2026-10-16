# H3 full-frame explanation

Measured candidate: `f8c088dc4f3243fbd15a3aae9be0459e8a0aa941`
Same-runtime sealed control: `707ea9cda051369326fb9407c42488c1033dad76`

Compared 18,329 frames, including every one of the 3,060 Set F frames. No numeric tolerance was used.

| Result field group | Changed frames | Changed leaf/schema entries |
|---|---:|---:|
| obstacle_warning | 0 | 0 |
| nearest_clear | 1834 | 3668 |
| detections_warnings | 0 | 0 |
| candidates | 12781 | 51414 |
| track | 18329 | 20751 |
| health | 2422 | 12774 |
| ego_motion | 0 | 0 |
| mount | 0 | 0 |
| other_result_fields | 0 | 0 |

## Preexisting output checks

- `obstacle`: **0 changed frames**.
- `warning`: **0 changed frames**.
- `nearest_distance`: **0 changed frames**.
- `detections`: **0 changed frames**.
- `warnings`: **0 changed frames**.
- `n_candidates`: **0 changed frames**.
- `n_points`: **0 changed frames**.
- `n_corridor`: **0 changed frames**.
- `preexisting_track_fields`: **0 changed frames**.
- `non_range_non_latency_health`: **0 changed frames**.
- `ego_motion`: **0 changed frames**.
- `mount`: **0 changed frames**.
- `preexisting_raw_candidates`: **1 changed frames**.
- `raw_corridor_membership`: **0 changed frames**.

## Interpretation

- `explained_frames.json` retains every changed field's counts/examples, per-dataset range counts and cap traces. Additive raw `wall_drift`, `cut` and `spared` metadata is counted separately from preexisting output changes.
- Independent min-cap equation checks: 18329 frames per range field. Mismatches/unclassified changes: **2**.
- Set F scoring/placement field changes: `{"sequences[].rows[].mon": 90}`.
- Exact comparison covers the captured preexisting raw numeric result fields, including candidate descriptors and point indices. Health/mount may already be rounded inside the detector. This is not a claim that every internal intermediate, cloud array, or arithmetic operation is bit-identical.
- The wall-drift min-cap equation is checked independently on every frame for monitored range and both health/result clear distance. All other changed fields remain listed; new cut/spared flags are measured metadata and are not assumed false.

Complete raw and serialized changes remain in the external generic `changes.jsonl`, including raw corridor membership hashes. Only the explicitly registered timing telemetry is excluded; its complete audit is retained separately.
