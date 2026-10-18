# N6: platform person range, with negative controls

The recorded defect is a first person STOP at **44.01 m**, despite earlier visible
returns. During wall loss the baseline trusts the near rail tangent only through
45 m. The [existing attribution](../synthetic_labels_2026-10-17/README.md) identifies
129 person rows demoted beyond that range. The new work tests current raw rail
support; it does not remove the range check or infer labels from detections.

The candidate remains **off by default** (`track.rails_axis_extension: false`).
The investigation is complete: the measured person improvement is real, but
default activation is **not accepted** because raw object removal reveals
conflicting farther rail evidence on two frames. The narrower-band remedy was
also rejected before runtime implementation. Work remains on
`work/n5-labels-c2-acceptance`; no release is part of this task.

## Evidence rule

On a frame with no fitted wall and a valid near rail pair, supplied scan-line IDs
can provide additional paired rail observations. Missing ring IDs provide no
extension; a Pandar elevation table is not assumed for another sensor.

- Each pair has the configured rail-head spacing (normally 1.59 m), within 0.10 m,
  height within 0.30 m of the rail plane and at most 0.10 m height difference.
- The two heads may differ by at most 5 m forward. The station is placed at the
  **nearer head**, never their average. This constraint is specific to the new
  path; the previous experimental far-curvature path keeps its old defaults.
- The connected rail chain may not cross a gap greater than 10 m. At least three
  distinct metre stations beyond the near 30 m fit must span at least 5 m.
- Every consensus-selected station must agree with the existing axis within
  0.10 m. The consensus can reject competing raw pairs; this is not proof that
  every return in the scene agrees.
- The search ends at 80 m. The supported range is the last observed station plus
  the **existing 15 m observation margin**, with no straight-axis bonus. No yaw,
  curvature, center or floor coefficient is changed.
- The pre-extension range is restored before the next frame, including a failed
  floor fit. There is no extension carried through missing evidence. A mount
  reseed currently lacks the new supplied-ring argument and conservatively uses
  the baseline range on that reseed frame.

Revision 3 also preserves the pre-extension range for the low-bed stage: paired
rails validate lateral placement, not a farther bed-anomaly model. Low, straddle
and central-near admissions remain at their baseline boundary. The existing
tracker can retain an already confirmed STOP after fresh axis support disappears;
that behavior is reported separately from the range itself.

## Candidate history

The parent [protocol](../lidar_adaptation_2026-10-18/PROTOCOL.md) was committed
before candidate runs. Defaults stay off throughout these measurements.

| Candidate | Result |
|---|---|
| Initial incomplete attempt | Aborted after 133 frames when independent review found the unbounded forward separation of paired heads. Not an acceptance run. [Receipt](interrupted_v1.json). |
| Revision 2, `5b305a3` | Person first STOP **44.01 → 51.12 m**, matched rows **147 → 158**, no lost person rows; rejected because the empty `doubleT_platform` gained six low-object STOP frames, one episode. [Rejection](v2_rejection.json). |
| Revision 3, `745096f` | Preserves the low-bed boundary; registered in [V3_PROTOCOL.md](V3_PROTOCOL.md). Person improvement is retained; all ten full recordings have been measured. Default activation rejected after source attribution exposed object-dependent visibility of conflicting rail evidence. |

Revision 2's full [platform comparison](platform_v2_comparison.json) found no axis
shape change, no unmatched STOP and no newly outside-object STOP. It added nine
STOP rows for the marginal box at frames 133–141. Their gauge relation remains
uncertain: false-STOP bounds widened from **0–38 to 0–47**. The [raw review](marginal_box_review.png)
shows the object straddling the detector-estimated boundary; that boundary is
not an independent survey, so it cannot remove the frozen-label uncertainty.

The [range invariant report](platform_range_invariants.json) verifies all 84
revision-2 extension frames are wall-loss frames and stay within the observed
station plus margin, allowing for serialized rounding. At person frame 229 the
axis correctly returns to 45 m while the existing tracker retains the preceding
confirmed STOP at 50.22 m with `beyond_axis`. This is STOP history, not a retained
range extension. The 60 m target has not been met by revision 2.

## Revision 3 measurements

The full [platform comparison](synthetic_platform_v3_comparison.json) retains
the **44.01 → 51.12 m** first-person STOP improvement: frame 239 becomes frame
228, all 147 baseline matched STOP rows remain, and 11 are added. The nine added
unknown-gauge box rows also remain: the false-STOP bound is **0–38 → 0–47**.
Passing known negative controls does not resolve that label uncertainty. The
60 m first-STOP target remains unmet. The scorer's 62.24 m sustained-range value
permits initial misses and is not a first detection at 62 m.

| Empty recording | Frames | Baseline → candidate STOP frames | Changed detection/warning payloads |
|---|---:|---:|---:|
| doubleT_platform | 345 | 0 → 0 | 0 / 0 |
| roundT_doubleT | 252 | 0 → 0 | 0 / 0 |
| roundT_pressureGate_roundT | 268 | 2 → 2 | 0 / 0 |
| roundT_squareT_pressureGate_squareT | 545 | 0 → 0 | 0 / 0 |
| squareT_platform_squareT_switch | 877 | 11 → 11 | 0 / 0 |

All five positive controls also completed. The [full control matrix](v3_full_control_matrix.json)
covers **5,665 frames**, each replayed with the candidate off and on.

| Positive recording | Frames | Baseline → candidate STOP frames | Result |
|---|---:|---:|---|
| synthetic_platform | 386 | 185 → 205 | 11 added person rows; 9 added unknown-gauge box rows; none lost |
| synthetic_switch | 736 | 142 → 142 | Every detection, warning and range unchanged |
| synthetic_tunnels | 545 | 126 → 126 | Every detection, warning and range unchanged |
| cloud_with_fake_obj (Set O) | 1,510 | 452 → 452 | Every detection, warning and range unchanged; all ten object results unchanged |
| doubleT_obstacle | 201 | 193 → 193 | Every detection, warning and range unchanged; crossing person first STOP stays 56.55 m |

The [real-person object comparison](doubleT_obstacle_v3_legacy.json) preserves
all 67 crossing-person and 128 rail-object matches; the outside walkway person
has no STOP before or after. The [Set O comparison](cloud_with_fake_obj_v3_legacy.json)
preserves every object match, including existing outside-object detections.
The exact platform-source interval 1308–1433 has no STOP before or after.
These are parity results, not claims that baseline false alarms were zero.

Trusted range changes on 6 empty-platform frames and 91 empty-switch frames;
the other three empty controls have identical ranges. The current
[range-invariant report](v3_range_invariants.json) finds no unsupported extension
beyond the observed nearer rail head plus the existing 15 m margin. There are no
non-latency health-message changes. Concurrent CPU load produces latency-health
warnings; these do not affect the operational decision level under the current
C2 policy and are not an isolated timing comparison.

The [platform baseline receipt](platform_baseline_receipt.json) verifies every
shared non-timing field against the committed v1.1.0 archive across all 386
frames. The earlier diagnostic capture lacked a per-module source receipt; that
limitation is recorded rather than filled in retrospectively.

## Exact source attribution and activation decision

[check_source_rail_support.py](check_source_rail_support.py) replays frames 0–314
from the immutable candidate and probes the full-precision model and near fit
before the extension mutates them. Every decision, detection, warning, range and
stored model field matches the previous candidate capture; timing and the
latency-dependent health level/messages are excluded from this probe comparison.
On all **84 extension frames**, it compares the original
cloud with every exactly-new XYZ return removed, independently frozen object
boxes removed with 2 cm padding, and a near fit recomputed from matching source
geometry. This uses no intensity-only truth. Source frame `i + 1195` has the
same stamp; the sensor-to-vehicle mount is checked as identity.

Set O has **no ring field**. Its zero-valued cache placeholder must not be used
as actual scan-line evidence; the full source therefore cannot activate N6.
For shared-return comparisons, only actual synthetic supplied rings attached to
XYZ present exactly in the source are retained. No ring is inferred.

The [station provenance check](rail_station_provenance.json) reproduces the
production pairing calculation exactly and identifies the actual selected head
returns. **All 655 accepted stations, 1,310 heads, come from exact source XYZ**;
none uses an inserted head. Removing object returns preserves every originally
selected station. This includes frame 228, where support at 36.803 m plus the
existing 15 m margin allows the first person STOP at 51.12 m.

However, the [full removal result](exact_source_rail_support.json) shows that
frames **145 and 146** gain additional farther stations after removal. Stations
at 51.467 and 51.495 m disagree with the existing axis by −0.152 and −0.144 m,
respectively, exceeding the 0.10 m limit and vetoing the whole chain. With the
box present, the ring/lateral-cell peak reduction hides those farther stations;
the retained 39.6 m prefix extends the range to about 54.6 m. This is
object-dependent visibility of conflicting evidence, not fabricated rail heads.
Recomputing the near seed from exact source geometry also withdraws frame 167.
The support rule therefore lacks the evidence independence required for default
activation, even though no added STOP occurs on a known empty control.

The [exploratory height-band assessment](exploratory_height_band.json), reproduced
by [inspect_height_band.py](inspect_height_band.py), tested
geometry only, with no modified detector replay. All accepted original heads
lie within −0.141 to +0.064 m of the fitted rail plane, but narrowing its window
from ±0.30 to ±0.15 m hides the farther conflicting evidence at frames 145/146.
It also withdraws 32 of the original 84 extension frames. Retaining both broad
and narrow tests would still preserve the original object-dependent difference,
so that proposed conjunction is rejected too. No V4 runtime change was made.

A second proposed restriction would require the last directly observed station
itself to exceed the previous trusted range, so the 15 m margin alone could not
create an extension. Saved full-precision scalars already disprove it as a remedy
that preserves this gain: frame 228 has observed support **36.803 m**, below its
previous **45 m** trust, so it would lose the 51.12 m first STOP. Meanwhile,
source-near-sensitive frame 167 has observed support **47.076 m**, above its
previous **45 m**, so that dependence would remain. The rule would exclude
frames 145/146, but fails both the preserved-gain and complete-dependence-removal
conditions. No additional detector replay or runtime change was made for it.

The final [raw range-support assessment](range_support_limit.json), reproduced
by [inspect_range_support.py](inspect_range_support.py), examines all 15
previously valid extension frames with the person 60–80 m away. Their largest
directly supported endpoint is **48.635 m**; neither direct observations nor the
existing 15 m margin reach the person on any of those frames. Even the
unclassified raw pair proposals contain no station at or beyond 60 m in this
sample. The maximum accepted endpoint across all 84 extension frames is
**52.760 m**. This bounds the current validated paired-rail evidence, not the
physical LiDAR range or every possible future method. No measured geometry in
this investigation justifies activating a 60 m fix.

**Recommendation: keep N6 off in the integrated defaults and seal.** The opt-in
experiment improves first person STOP by 7.11 m, preserves all measured baseline
STOP rows, and has complete positive/negative control evidence. It does not meet
the 60 m target, does not resolve the nine uncertain box rows, and does not yet
justify default range extension under the observed rail-evidence occlusion.

## Reproduction and scope

[replay.py](replay.py) processes every decoded frame through the node-faithful
judge replica, with original stamps, continuity and actual ring-presence metadata.
It writes complete detections, warnings, track geometry, timings, configuration,
source hashes and reset records. [compare.py](compare.py) checks every frame and
uses the unchanged N5 scorer for annotated recordings; it lists all new/lost STOP
rows and explicit outside-object additions rather than comparing only totals.
[compare_legacy.py](compare_legacy.py) applies the unchanged repository matcher
to Set O and the real-person recording, retaining every lost/new object match.
These captures omit persistent track IDs, so this additional comparison does
not claim event counts; the full regression gate remains responsible for them.

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_CORETYPE=Haswell \
  python docs/evidence/n6_platform_2026-10-18/replay.py \
  /path/to/decoded/synthetic_platform /path/to/baseline.jsonl
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_CORETYPE=Haswell \
  python docs/evidence/n6_platform_2026-10-18/replay.py \
  /path/to/decoded/synthetic_platform /path/to/candidate.jsonl --candidate
python docs/evidence/n6_platform_2026-10-18/compare.py \
  /path/to/baseline.jsonl /path/to/candidate.jsonl /path/to/comparison.json \
  --labels docs/evidence/n5_labels_2026-10-17/labels_synthetic_platform.json
```

For an immutable export, set `RESENSE_REPO` to that export and
`RESENSE_MEASURED_COMMIT` to its actual commit. The revision-3
[source manifest](v3_source_export.json) records every exported source and the
native library. The [input manifest](../n5_c2_execution_2026-10-17/data_intake.json)
identifies the decoded recordings. N5 labels remain frozen; full frame coverage
does not imply exhaustive scene negatives.

These are development measurements on one exposed CPU and 4 GB RAM. Other
decode, replay and validation jobs share the host, so concurrent timings are
informational rather than an isolated performance acceptance result.
