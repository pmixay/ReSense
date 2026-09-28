# Temporal evidence-coherence investigation — 28 September 2026

**Decision: reject the interval-coherence candidate.** The unfinished candidate was removed from
`resense/tracking.py` and `TrackingConfig`; its experimental YAML was removed as well. The measured
diagnostic remains in `tests/test_evidence_coherence.py` so the rejection and its counterexamples can
be reproduced without changing tracker defaults.

## Question tested

The proposed rule compared adjacent ordinary/low clusters using:

* `Cluster.lateral +/- Cluster.size[1] / 2`, expressed against the fitted track axis; and
* `[Cluster.height_min, Cluster.height_max]`, expressed against the fitted rail-height reference.

It cleared fresh-onset evidence when either interval gap exceeded `0.25 m`. Association, confirmation,
earned STOP continuation, thin continuation and far-sparse evidence were otherwise left unchanged.
The motivation was the low-to-ordinary transition in `new_data_1.jsonl:293`, where a source trace
summary reported a roughly `.56 m` raw lateral gap and the candidate's centre/width calculation
reported roughly `.66 m`.

This did not establish identity. The intervals are whole-cluster descriptors in moving fitted
coordinates, not strict local footprints or surveyed object labels. The trace also does not contain a
physical identity for a return surface, so a matched cluster cannot be declared a different object
from those fields alone.

## Measurement of the remaining histories

Inputs:

* `D:/Datasets/ReSense/cross_ring_2026-09-28_measurement/false_target_trace/trace.json`
* the eight `fresh_stop_v1/new_data_*.jsonl` outputs and `summary.json`
* saved point snapshots under `false_target_trace/points/`

The fresh-onset output has **27 retained event identities, 117 node STOP frames and 133 STOP
track-frames**. The five removed source identities are `1:295`, `2:586`, `4:210`, `5:146` and
`6:250`. The diagnostic joins retained event keys to the source timeline, then applies the unfinished
interval calculation to every eligible adjacent matched hit.

| Measurement | Result |
|---|---:|
| retained event identities | 27 |
| retained node STOP frames | 117 |
| retained STOP track-frames | 133 |
| adjacent matched source transitions | 467 |
| retained histories with an eligible `>.25 m` break | 6 |
| eligible interval breaks | 9 |
| gauge-to-gauge evidence-reset proxies | 6 |
| retained histories with a break at the proposed onset only | not isolated by the fields |

The nine breaks are distributed as follows:

* `new_data_0.jsonl:3`: three ordinary-to-ordinary breaks;
* `new_data_1.jsonl:286`: one low-to-ordinary break;
* `new_data_1.jsonl:293`: one low-to-low and one low-to-ordinary break;
* `new_data_4.jsonl:36`: one ordinary-to-ordinary break;
* `new_data_4.jsonl:58`: one low-to-low break; and
* `new_data_6.jsonl:518`: one ordinary-to-ordinary break.

The fresh alarm rows themselves contain low/ordinary switches in retained `:286` and `:570`
histories. This is enough to show that the proposed geometry is not a specific separator for the
suspected mixed-support mechanism. The preliminary `1:293` prediction of one affected identity was
an onset-only interpretation, not a replay result and not a measurement of all remaining histories.

## The `1:293` discrepancy and reference movement

At source frame `new_data_2671`, the low cluster has:

* fitted lateral `-0.02295 m`, width `0.290 m`, proposed interval `[-0.168, 0.122] m`;
* raw saved bbox lateral range `[-0.370, -0.080] m`; and
* saved snapshot support `[-0.171, 0.119] m`.

At `new_data_2673`, the ordinary cluster has:

* fitted lateral `1.09840 m`, width `0.640 m`, proposed interval `[0.778, 1.418] m`;
* raw saved bbox lateral range `[0.480, 1.120] m`; and
* saved snapshot support `[0.754, 1.391] m`.

Therefore the three gaps are different measurements:

* raw bbox gap: `0.560 m`;
* proposed fitted centre/width gap: `0.656 m`; and
* saved snapshot-support gap: approximately `0.635 m`.

The intervening source frame `new_data_2672` also changes the fitted model: centre `-0.029` to
`-0.130 m`, rail offset `0.294` to `0.314 m`, trusted axis range `115` to `143 m`, and fitted
boundary sides `1` to `2`. The candidate's gap is thus affected by a changing reference and by
whole-cluster support. The ordinary hit remains associated: its cross-track residual is `1.695 m`
against a `2.357 m` base cross-track gate (`0.719` of the gate). That is an association within the
saved gate, not evidence of a wrong association.

Across retained source histories, every saved association residual is within its saved base gate.
Only two retained history rows have cross-track residual at least half the gate: `0:383` at
`new_data_1333` and `1:293` at `new_data_2673`. There is no identity label with which to classify
either as a wrong-object join.

## Positive and preservation counterexamples

The owned tests cover the cases a coherence veto would risk:

* an already earned STOP survives one missed frame and a later lateral-shifted reacquisition;
* a late-arriving body can earn a new STOP from its own three coherent hits without stale evidence;
* the saved sparse-edge positive replay is unchanged: all **357/357** edge evaluation rows match
  between `setF_edge_base.json` and `setF_edge_fresh.json`, including the two detected edge-person
  sequences with sustained ranges `86.6 m` and `98.4 m`;
* the measured reference movement and the `1:293` low-to-ordinary history are asserted directly.

The range/shape investigation supplies the relevant positive-loss limitation. Target-only oracle
subsets of resolved synthetic person support survive the unchanged descriptor at **114.8–77.7 m**,
and a cable subset at **98.4 m**, after connected background is removed using injection labels. Those
are not runtime selectors or a temporal-coherence replay. Conversely, compact negatives `:331`,
`:298` and `:74` mimic real compact bodies. Temporal boxes cannot rescue the connected-background
loss or distinguish those negatives from a valid body.

Occlusion, late arrival, sparse edge support and reference movement therefore argue for preserving
association and continuation while measuring local point provenance in a future investigation. They do
not justify this interval veto or an evidence reset.

## Verification

From the repository root, using the requested interpreter:

```powershell
$py = 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-cross-ring-venv/Scripts/python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $py -m pytest -q -p no:cacheprovider tests/test_evidence_coherence.py
& $py tests/test_evidence_coherence.py --measurement 'D:/Datasets/ReSense/cross_ring_2026-09-28_measurement'
ruff check resense/tracking.py resense/config.py tests/test_evidence_coherence.py
```

The measurement tests skip capture-dependent checks when the external measurement or positive-stress
cache is absent. With the supplied data they verify the 133 track-frame inventory, nine-break
rejection, exact `.56/.656/.635 m` discrepancy, reference movement, in-gate association residual,
occlusion, late arrival and sparse-edge parity. No detector replay was run for the rejected candidate.
Controlled same-body tests also demonstrate delayed onset under the rejected test-only intervention:
different visible patches, low-to-ordinary support, or a changed fitted reference with fixed
sensor-space centroid and bbox. A separate two-body fixture shows that a wrong association with
overlapping lateral/height projections escapes the rule. These are mechanism counterexamples, not
measured real-positive misses. The coordinator reproduced the 467-transition diagnostic and ran the
combined checks recorded in [the closeout](RESIDUAL_REVIEW_2026-09-28.md).

## Limits and handoff

The full trace is a saved default/source trace, not a fresh candidate replay. The residual inventory
maps saved outputs with its documented limitations: candidate evidence history, hidden tracker source
flags, exact candidate point membership, stale low-bed state and learned-opinion probabilities are not
available for reconstruction. The positive set F files are saved comparisons on partial approaches,
not full-ride acceptance evidence. No default, acceptance, seal or unrelated source change follows
from this investigation.
