# Far ordinary-cluster structure investigation — 28 September 2026

**Result: no justified rejection candidate selected.** Baseline: `3ba4521`.
The examined geometry does not establish a conservative separation between the remaining
ordinary multi-ring false targets and positive obstacles. In particular, applying an
infrastructure signature to an entire connected component can erase a localized body.
This is a diagnostic result, not a measured false-alarm improvement or acceptance result.

Deliverables are this report and `tests/test_far_structure.py`: nine focused research tests
and a read-only snapshot diagnostic. **Flags: none. Detector integration: none requested.
Expected changed event IDs: none.** No experimental YAML is supplied because there is no
selected decision rule to enable. No production source, defaults, seal or acceptance record
is changed by this work.

## Evidence and method

Read together with [EXPERIMENT_CROSS_RING.md](EXPERIMENT_CROSS_RING.md),
[QUALITY_CYCLE_2026-09-27.md](archive/QUALITY_CYCLE_2026-09-27.md),
[P4_FALSE_TARGET_DIAGNOSIS.md](archive/P4_FALSE_TARGET_DIAGNOSIS.md), and the rejected
[D1 context protocol](evidence/results/quality_cycle_2026-09-26_D1_protocol.json).
The earlier D1 experiment increased outside-object false STOPs from 6 to 9 and ride STOP
episodes from 38 to 40; it was rejected. It promoted clipped candidates and did not validate
a new ordinary-cluster demotion. The prior far-height experiments also lost person/trolley/
crate range; the 27.09 confirmation/vote experiments delayed positive detections.

Inputs are under `D:/Datasets/ReSense/cross_ring_2026-09-28_measurement`:

| Input | SHA-256 |
|---|---|
| `false_target_trace/trace.json` | `ba9922128a61d3117407acaa0c682d8ae68ab899302ea635d327894f206ce1e8` |
| `false_alarm_scenes_source/inventory.json` | `c2054c8aca4763675fc5d4680e3d1d7c0d8ca925afdd79e3dfd84f225dbee0be` |
| `false_alarm_analysis.json` | `b0cbbe9260bacdd8d51de81f00ccc215b2ba3ddda9dcb288d22aaec8be84caf4` |

The existing chronological trace reproduces 11,271 frames with zero detection mismatches:
32 false track identities, 130 distinct STOP frames, 31 STOP episodes. Fifteen events reach
at least 80 m; 13 start STOP with multi-ring strict support, and nine have multi-ring support
on every fresh strict-gauge corridor STOP hit. Rings are elevation channels, not independent
sensors. The local work here reads that trace; it does not replay the detector.

The diagnostic examines the first STOP snapshot of **every one of the 15 far identities**,
plus the requested nearer `new_data_5.jsonl:330`. All these onsets have fresh target points.
It validates the target count against `n_points_idx`, uses the saved exact target mask,
and never applies stale `track.last` indices to a later frame. Selected later STOP snapshots
of `:331`, `:383` and `:266` were also inspected for continuation.

Measurements:

- Compare the full current target with its strict-gauge subset. The latter is recomputed
  with `gauge_core_mask` on the saved **rail-relative** coordinates, not a surveyed envelope.
  The separate trace voxel/ring counts retain their original definitions. Distinct XYZ
  points and occupied range-normalized voxels are different quantities.
- Deduplicate XYZ before target PCA, so duplicate returns do not dominate direction.
- Measure the nearest **non-target** return in physical XYZ. Non-target does not necessarily
  mean outside the strict gauge, nor does proximity establish physical attachment.
- Inspect a fixed 0.45 m horizontal-radius vertical tube around the median target XY. Its
  height is descriptive only; this window is not a proposed rejection threshold.
- Recluster each saved context using the existing `voxelize` and `cluster_labels`, with
  unchanged `ClusterConfig`. Inspect the component(s) containing target points, their
  outside support, extent and direction. This is a cropped-context measurement: large
  components can run into the crop boundary, so their extent is not a complete object size.

## Measured onset geometry

Lengths and gaps below are metres. `Lx` is physical along-X extent. `Joined Lx` uses the
production range-normalized clustering on the saved context, not a fixed-radius XYZ graph.
All keys have the prefix `new_data_` and retain the baseline trace's chunk-local identities.

| Event key suffix | Frame | Strict rings | Target Lx | Strict Lx | Nearest non-target | Joined Lx |
|---|---|---:|---:|---:|---:|---:|
| `0.jsonl:3` | `0023` | 4 | 0.10 | 0.10 | 3.99 | 5.22 |
| `0.jsonl:383` | `1378` | 4 | 0.17 | 0.17 | 0.35 | 25.49 |
| `1.jsonl:74` | `1847` | 5 | 5.29 | 0.19 | 0.45 | 16.86 |
| `1.jsonl:298` | `2671` | 2 | 6.80 | 0.09 | 0.44 | 6.90 |
| `1.jsonl:377` | `2729` | 4 | 3.99 | 3.99 | 0.51 | 16.74 |
| `2.jsonl:81` | `3060` | 4 | 1.84 | 1.84 | 0.87 | 29.56 |
| `3.jsonl:266` | `5065` | 5 | 0.41 | 0.41 | 0.38 | 21.80 |
| `4.jsonl:36` | `5699` | 7 | 0.24 | 0.23 | 1.99 | 0.24 |
| `5.jsonl:113` | `7338` | 3 | 1.68 | 1.68 | 2.81 | 1.68 |
| `5.jsonl:358` | `7943` | 6 | 2.79 | 1.52 | 2.05 | 2.79 |
| `6.jsonl:250` | `9125` | 0 | 1.22 | none | 0.18 | 29.62 |
| `6.jsonl:331` | `9263` | 9 | 1.24 | 1.24 | 3.16 | 9.61 |
| `6.jsonl:336` | `9284` | 3 | 0.08 | 0.08 | 0.93 | 0.51 |
| `6.jsonl:518` | `9786` | 2 | 0.10 | 0.10 | 1.82 | 0.10 |
| `7.jsonl:264` | `10644` | 1 | 5.71 | 5.71 | 0.18 | 28.68 |
| `5.jsonl:330` (nearer comparison) | `7859` | 3 | 5.48 | 5.39 | 0.09 | 29.82 |

### 1. A compact body can become a long component through only two outside returns

At `new_data_6.jsonl:331 / new_data_9263`, all 20 distinct target positions are in the
strict gauge. They span **1.24 × 0.63 × 1.95 m**, height 0.278–2.227 m above the fitted
rail head, supported by nine strict rings in the trace. Its normalized absolute principal
direction is approximately **(0.244, 0.080, 0.967)**: predominantly vertical.

No non-target point lies within 3.16 m in the saved context. Nevertheless production
range-normalized clustering joins two distinct farther low positions (four raw returns):

| XYZ | Rail-relative dy | Height |
|---|---:|---:|
| `(114.40, 13.21, -0.85)` | -0.760 | 0.004 |
| `(119.20, 13.68, -1.19)` | -1.331 | -0.339 |

The joined component is **9.61 × 0.87 × 2.56 m**, with principal direction approximately
**(0.975, 0.071, 0.209)**. Thus connectivity plus full-component length/direction can label
a localized vertical body as an along-track structure. The range transform stretches the
effective along-range linking distance more than the transverse distance; a 3 m physical
gap does not imply disconnection under the production metric.

The tests retain this real support and its two context positions. A separate controlled
person with two farther ground returns also becomes a component longer than `max_extent`,
while its original strict support remains an ordinary gauge obstacle. This is an explicit
positive counterexample to rejecting a seed because the connected component is too long.

The next saved STOP (`9264`) still has nine rings and a 1.28 × 0.55 × 1.93 m body. By
`9274` the fresh cluster has zero strict support and zone `warning` while the track still
STOPs. That later continuation is a tracking issue; it does not retroactively prove that
the onset's compact support could safely be rejected as structure.

### 2. A long ordinary cluster need not have a long in-gauge body

At `new_data_1.jsonl:298 / new_data_2671`, the current cluster is 6.80 m long and its
principal direction has an X component 0.980. Its strict subset is only
**0.09 × 0.94 × 0.18 m**: a transverse face. At `new_data_1.jsonl:74`, full length 5.29 m
similarly collapses to 0.19 m inside the strict gauge. A global length/aspect/direction
criterion would confuse off-gauge connections with the shape actually intruding into the
envelope. The committed `:298` fixture pins this distinction.

At the nearer `new_data_5.jsonl:330 / new_data_7859`, the situation differs: the strict
subset itself spans **5.39 × 0.40 × 0.23 m**, with fitted heights 0.168–0.398 m. The full
target's 1.45 m height comes mostly from its off-gauge part. This is a useful ordinary-edge
diagnostic, but not evidence to extend a far rule into 40–48 m or to suppress a low plank
that touches a longer line. Local protrusion above a support surface, rather than whole
component extent, would need separate validation.

### 3. Vertical continuation is a watchlist, not yet a conservative classifier

`new_data_0.jsonl:383` and `new_data_3.jsonl:266` have clear same-XY upper context:
their diagnostic tubes span 4.05 m and 3.59 m, versus target heights 1.89 m and 2.02 m.
But their onsets have only **five and six distinct target positions**. Fitting a narrow
column to upper context does not establish that there is no localized intrusion below it.
There is no measured protrusion/noise margin with which to retain an attached edge person,
upper object or irregular debris at this sampling density. `new_data_2.jsonl:81` also has
a 4.34 m tube, yet its target direction is along X, showing why tube height alone is weak.

The positive counterexample test places a person beside a tall narrow structure: nearest
context is under 6 cm, whole-context PCA is almost vertical, but the person protrudes
0.60 m from its outer face. The localized target remains a gauge obstacle. Sparse sampling
can make that protrusion less observable; absence of sampled protrusion is not evidence
of its physical absence. No threshold sweep was used to force a separation.

## Verification and coordinator handoff

Use the specified isolated environment, from the repository root:

```powershell
& 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe' -m pytest -q tests/test_far_structure.py
& 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe' tests/test_far_structure.py --measurement 'D:/Datasets/ReSense/cross_ring_2026-09-28_measurement'
```

**Focused tests: 9 passed (0.47 s). Ruff: passed** using the installed system `ruff.exe`
(the isolated environment's `python -m ruff` launcher could not find its executable).
The tests cover the actual `:331` body, its misleading connected
context, the actual `:298` strict/full direction difference, a person joined to farther
ground returns, person/edge-cube/plank/above-box strict support, and a person protruding from
a vertical structure. The two recorded fixtures contain distinct XYZ positions and saved
model coordinates, not invented ring assignments. They pin geometry mechanisms, not the
complete original frame or temporal STOP outcome.

The diagnostic emits all 16 onset rows, input hashes and each snapshot's hash. It has no
detector hook and does not write to the dataset. It is intentionally housed in the assigned
test file so the research is reproducible without modifying another agent's scripts.

For a later, separately justified candidate, the strongest geometry follow-up identities
are `new_data_0.jsonl:383` and `new_data_3.jsonl:266` (vertical continuation), with
`new_data_2.jsonl:81` as a direction/connection ambiguity. Mandatory fallback examples are
`:331`, `new_data_1.jsonl:298` and `new_data_1.jsonl:74`. These are investigation targets,
**not predicted removed events**. `new_data_6.jsonl:250` begins with no fresh strict support;
`:331` later leaves the strict gauge. Those facts are useful to the tracking owner.

Any future full-cloud integration needs exact current-frame indices and the effective
strict mask, including reference/union handling; accumulation must not supply outside
connection evidence. It also needs bounded queries with a boundary/ambiguity fallback and
a localized protrusion check before changing an ordinary cluster. A connected component
alone is insufficient. No such integration is requested for this no-candidate result.

Limits: model-relative coordinates are not independent ground truth; point snapshots are
bounded crops; first-onset geometry cannot predict event/episode reductions; positive tests
are controlled point supports rather than real-object recall evidence. Set O has fabricated
`ring=0`, and all six short organizer bags are missing locally. Full replay and acceptance
remain the coordinator's responsibility if a later decision rule is proposed. This work
makes no recall, default-parity replay, latency or acceptance claim.
