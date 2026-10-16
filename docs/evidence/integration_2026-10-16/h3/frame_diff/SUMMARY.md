# Same-runtime full-frame comparison

Control: `707ea9cda051369326fb9407c42488c1033dad76`
Candidate: `f8c088dc4f3243fbd15a3aae9be0459e8a0aa941`

Compared **18329 frames**, including **3060 Set F rows**; **18329 frames** changed outside explicit timing telemetry.

| Field group | Changed frames | Leaf changes |
|---|---:|---:|
| candidates | 12781 | 51414 |
| health | 2422 | 12774 |
| nearest_clear | 1834 | 3668 |
| track | 18329 | 20751 |

Exact field counts and examples: `summary.json`. Every changed field/value: `changes.jsonl`. Set F placement/scoring: `setF_report_changes.json`. Excluded timing audit: `excluded_timing_changes.jsonl`.

## Interpretation
- Monitored/clear range and track.axis_valid changes are retained. The integration plan intends an axis-supported range cap; review counted examples before attributing any individual change to it.
- Legacy Set F placement depends on detector track fits. GT, injected point counts and scoring row changes are reported separately; changed input placement is not automatically a candidate gain.
- serialized is exact FrameResult.to_dict(); raw retains unrounded scalar/array/dataclass result fields and full candidate descriptors. Health/mount may already be rounded by the detector. xyz is not a result field serialized by the application; corridor membership is retained as dtype/shape/SHA-256.
- Raw-only changes can also be additive unreported fields, not just rounding. Inspect field names/examples and source before assigning a cause.
- Shared Docker CPU performance is informational only; all excluded differences remain in excluded_timing_changes.jsonl.
