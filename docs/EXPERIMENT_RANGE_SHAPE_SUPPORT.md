# Range/shape support investigation — 28 September 2026

**Historical report:** source/default references and replay commands describe the pre-merge
research state preserved in `9aa1775`; see [integration provenance](RESIDUAL_REVIEW_2026-09-28.md#integration-provenance).

**Result: concrete positive-loss diagnosis; no justified production candidate selected.**
Exact point-identity tracing found both under-resolved small objects and resolved person/cable
support rejected after connection to background. These require different remedies. A generic
point/height relaxation or whole-component infrastructure veto is not supported by this evidence.

Deliverables: this report and `tests/test_range_shape_support.py` (eight mechanism tests plus a
read-only replay/inspection runner). **Detector flags: none. Experimental YAML: none.** There is
no range/geometry production-source change or measured candidate improvement.

## Replayed inputs and scope

Read with [EXPERIMENT_FRESH_STOP_EVIDENCE.md](EXPERIMENT_FRESH_STOP_EVIDENCE.md) and
[EXPERIMENT_FAR_STRUCTURE.md](EXPERIMENT_FAR_STRUCTURE.md).

The local stress cache contains 102 frames, splits 46 and 47. Although the saved jobs request
80 frames each, the actual approach starting at split 46 stops after **68 frames, 150.0–9.1 m**
because the object passes the evaluation cutoff. The approach starting at split 47 has only
**51 frames, 150.0–46.8 m**, because the cache ends. A split-47 miss is therefore not evidence
that the object is never detected at close range.

Replayed all six centre and six edge draws from:

* `C:/Users/alikh/AppData/Local/Temp/opencode/fresh-stop-positive-stress/setF_base.json`
* `C:/Users/alikh/AppData/Local/Temp/opencode/fresh-stop-positive-stress/setF_edge_base.json`

Every saved per-frame evaluation row matched exactly: **714/714 rows**, including rendered
point counts, ground-truth specification, hit/candidate flags, false detections and monitored
range. The same rows also equal the saved `setF_fresh.json` / `setF_edge_fresh.json` rows. This
is an instrumented baseline replay plus comparison to saved fresh-onset results, not a new
range/shape A/B. No full-ride replay was run here.

### Shared-tree tracking isolation

The live tree had tracking work referencing `TrackingConfig.evidence_coherence` before that
field existed. The initial live-tree diagnostic stopped with `AttributeError`. To complete a
reproducible geometry investigation without changing the tracking owner's files, both successful
replays explicitly used **the tracker from revision `6385ff9`**, loaded into an isolated Python
module with `--tracking-ref 6385ff9`. All geometry stages used the working-tree source; clustering
and its defaults were unchanged from that revision. The output records tracker source SHA-256,
source/input hashes, effective config, and cache path. This is not a claim that the concurrently
edited tracker passes default parity.

## Positive ranges actually observed

Each entry is **first confirmed / sustained** range in metres. Sustained is the existing set F
metric: at least 90% of visible frames from that distance inward, with at least five visible
frames. It can precede the first detection because the aggregate permits some misses. `—` means
the metric was not achieved in the available interval.

| Placement / kind | Split 46, ends at 9.1 m | Split 47, ends at 46.8 m |
|---|---:|---:|
| Centre person | 141.5 / 150.0 | 139.6 / 75.7 |
| Centre cable | 80.2 / 44.3 | 92.1 / 71.5 |
| Centre plank | — / — | — / — |
| Edge person | 80.2 / 86.6 | 104.6 / 98.4 |
| Edge 0.3 m cube | 13.3 / — | — / — |
| Edge rail object | 15.3 / — | — / — |

These are synthetic positives on real moving backgrounds, placed using the frame-derived legacy
track/bed model. They are not surveyed objects or independent real-positive acceptance evidence.

## Causal findings

### 1. Resolved person/cable support is lost through connected background

The centre person beginning at split 47 has **11 missed frames** where the actual corridor
descriptor returns `None` at its oversized-component split, yet the known target-only subset
passes the unchanged descriptor as an ordinary gauge cluster. The frames/ranges are:

`0017/114.8`, `0019/110.8`, `0022/104.6`, `0023/102.5`, `0025/98.4`, `0026/96.3`,
`0028/92.1`, `0029/90.1`, `0032/83.8`, `0034/79.8`, `0035/77.7`.

At `new_data_47_0017`:

| Support | Raw points | Occupied voxels | XYZ extent (m) |
|---|---:|---:|---|
| Known injected person in this component | 8 | 8 | 0.127 × 0.201 × 1.030 |
| Whole connected component | 16 | 13 | 8.180 × 1.360 × 1.030 |
| Effective strict part of the component | 12 | 10 | 4.120 × 0.770 × 1.030 |
| Background in the strict part | 4 | 2 | 4.120 × 0.390 × 0.450 |

All eight target points are strict; their rail-relative heights are 0.472–1.502 m. The whole
component exceeds `max_extent=8`. Its strict part is itself polluted, exceeds the 3 m split
length, and is beyond the 30 m split distance. **Only extending the split distance cannot fix
this example.** It is not a sparse-height failure and not solely off-gauge pollution.

For the centre cable, `new_data_47_0025` at 98.4 m similarly has a 10.13 m whole component,
but six target voxels spanning only 0.120 × 0.00063 × 1.330 m; the target-only descriptor
returns gauge. At 125.1 m, removing the connection instead yields `beyond_height_ref`, so
removing an infrastructure rejection alone would not establish STOP eligibility there.

The counterfactual is deliberately **oracle-only**: it uses exact injection labels to remove
background, preserves the original voxel memberships, and calls the unchanged descriptor.
It does not recluster, change live detector output or claim that a real detector can identify
that subset. Its gauge output is not a measured temporal detection gain.

### 2. Small edge objects face several independent gates

At `box0.3`, split 46, `new_data_46_0034` (78.1 m), five object returns are present. Three
enter the corridor, only two are strict, and the three occupied voxels form a DBSCAN component.
The actual return is the point-count branch: at 78 m the ordinary bar is **five** voxels and
the weak bar is four. The three-voxel ordinary bar begins at 100 m. The observed component
height is just **1.41 mm**, and two strict voxels also fall below `gauge_min_points=3`.
Relaxing only one count threshold would therefore not turn this support into an ordinary STOP.

At `railobj`, split 46, `new_data_46_0019` (109.8 m), the three-voxel component passes the
far point count but is rejected as low narrow hardware: 0.195 × 0.383 × 0.00272 m and only
one strict voxel. For other frames, two occupied voxels never form a component at all under
`min_samples=3`; duplicate returns do not repair that deficit.

Connections do inflate small-object shape too. At split 47 frame `0022`, the cube's own two
returns span only 0.029 × 0.183 m horizontally, while its joined component is 3.48 m long
and rejected as infrastructure. Target-only support still fails the descriptor. This is
different from the resolved person case above.

### 3. Low-object and straddle width limits must not be conflated

The earlier incomplete report attributed width rejections to the ordinary low-object 0.15 m
guard. The effective descriptor arguments show that many instead use the **straddle stage's
0.35 m guard** and 0.8 m maximum length.

For example, split 46 frame `0043` at 59.1 m rejects a cube component **0.207 m wide** at
`size[1] < low_cfg.min_width`; the effective minimum is 0.35 m. The corresponding rail-object
component is also 0.207 m wide and encounters the same gate. A nominal 0.30 m cube cannot
satisfy that guard in isolation; it needs the separate bed-level path where available.

There is also real background pollution near the train: the cube sequence at split 47 frame
`0010` (21.5 m) has a straddle component **2.42 m long**, versus **0.273 m** for its target
subset, and exceeds the 0.8 m length guard. That subset is still only 0.264 m wide, so removing
the background alone is not a sufficient straddle rescue.

### 4. Some plank observations are below the envelope; not all are

The catalogue plank is 2.0 × 0.25 × 0.30 m. A bed placement 0.25 m below the rails would put
its nominal top at 0.05 m, below the 0.12 m corridor floor. However, the actual legacy bed and
vault corrections vary frame by frame. The earlier blanket statement that these planks are
outside the corridor's physical envelope was too strong.

| Plank sequence | Visible frames | Placement-model top < 0.12 m | Highest observed point < 0.12 m |
|---|---:|---:|---:|
| Split 46 | 63 | 32 | 47 |
| Split 47 | 41 | 12 | 13 |

Placement-model top and detector-relative observed height use different fitted references;
neither is surveyed physical ground truth. A below-floor observation is not an ordinary
corridor recall miss. Conversely, above-floor points are not proof of sufficient support:
at split 46 frame `0037` (71.7 m), the plank component has three strict voxels, a 1.303 m
length and only 0.024 m height, and fails the point-count path. Low/straddle observations
also encounter their effective width/length guards. These cases need separate reporting.

## Why no candidate was selected

The replay establishes a useful future target: isolate a resolved local body despite background
connections. It does not establish an accuracy-preserving selection rule. The saved negative
snapshots were re-inspected using the existing `test_far_structure.py` diagnostic:

* `new_data_6.jsonl:331`: a 1.24 × 0.63 × 1.95 m strict body, nine trace rings, that becomes
  9.61 m long when joined to two distinct background positions by the production metric.
* `new_data_1.jsonl:298`: 6.80 m full length but a strict face only 0.09 × 0.94 × 0.18 m.
* `new_data_1.jsonl:74`: 5.29 m full length but a strict body only 0.19 × 0.59 × 1.36 m.

Thus a long connected shape cannot safely veto a person, and compact strict support alone
does not distinguish a real body from these known false targets. The snapshot diagnostic
examines cropped context; its connectivity is not a replay of the original corridor candidate
set. It is used as a counterexample, not as a prediction of extra or removed alarms.

The narrow follow-up is a measured local-body decomposition with the actual reference/union
mask and current-frame point provenance. It would need accuracy evidence on rejected
background components as well as these detected false bodies. No such justified rule emerged
here; the existing thresholds were not swept to manufacture one.

## Reproduce

From the repository root in PowerShell (output parent already exists):

```powershell
$py = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe'
$tmp = 'C:/Users/alikh/AppData/Local/Temp/opencode'
$stress = "$tmp/fresh-stop-positive-stress"
& $py tests/test_range_shape_support.py replay "$stress/setF_edge_base.json" "$tmp/range-shape-edge-v2.json" --paired-report "$stress/setF_edge_fresh.json" --tracking-ref 6385ff9
& $py tests/test_range_shape_support.py replay "$stress/setF_base.json" "$tmp/range-shape-centre-v2.json" --paired-report "$stress/setF_fresh.json" --tracking-ref 6385ff9
& $py tests/test_range_shape_support.py summary "$tmp/range-shape-centre-v2.json"
& $py tests/test_range_shape_support.py frame "$tmp/range-shape-centre-v2.json" person new_data_47_0000.npy new_data_47_0017
& $py tests/test_far_structure.py --measurement 'D:/Datasets/ReSense/cross_ring_2026-09-28_measurement'
& $py -m pytest -q tests/test_range_shape_support.py tests/test_far_structure.py
ruff check tests/test_range_shape_support.py
```

The runner records actual production return sites and effective low/straddle limits, target,
strict and background geometry, exact component points, and the target-only descriptor
counterfactual. It aborts on any saved baseline row mismatch. Low descriptor points are stage
support, not a recomputed strict-polygon mask. It does not infer physical sensor rings.

The eight new tests pin the measured person/background failure, the recorded sparse edge cube,
the real false body's compact strict support, exact mask/point provenance, duplicate-return
DBSCAN failure, and distinct low/straddle width behavior with an accepted wider counterexample.

**Verification:** focused range/shape + far-structure tests: **17 passed**. Ruff: passed.
An additional run including `tests/test_stage_trace.py` produced **21 passed, 1 failed**:
`test_tracing_preserves_stateful_detector_output` hit the live shared-tree missing
`TrackingConfig.evidence_coherence` field described above. That integration failure is outside
the geometry-owned files; the successful historical-tracker diagnostics do not hide it.

## Limits and coordinator handoff

* Outputs are `range-shape-edge-v2.json` and `range-shape-centre-v2.json` under the temporary
  directory above. They are diagnostic artifacts; instrumented timing is not latency evidence.
* Exact injected point identity establishes rejection causality, while set F's reported hit
  uses its existing distance/lateral matching tolerance. The oracle subset is unavailable at runtime.
* Set O has 1,510 frames and lacks real rings. Its earlier traces and the 11,271-frame empty
  ride provide context, but this task adds no Set O or full-ride measurement.
* Fresh-onset saved-row parity, partial approaches, and synthetic fixtures do not constitute
  adequate small-object recall or holdout acceptance. No default, seal or acceptance change
is proposed. Full replay of any later grounded candidate remains the coordinator's task.

## Coordinator verification after temporal closeout

The unfinished interval-coherence candidate was rejected and removed. On the final working tree,
the coordinator reran both instrumented stress replays **without `--tracking-ref`**, using the live
tracker. All **12 sequences / 714 rows** again matched the saved baseline and saved fresh-onset
evaluation rows exactly; the eleven person-loss frames and cable loss at 98.4 m reproduced.
This resolves the shared-tree integration limitation above for these diagnostics. It remains a
baseline replay compared with saved fresh results, not a newly executed fresh-onset A/B or latency
measurement. Outputs are `range-shape-{edge,centre}-coordinator.json` under the same temporary root.
Commands and the combined checks are in [the coordinator closeout](RESIDUAL_REVIEW_2026-09-28.md).
