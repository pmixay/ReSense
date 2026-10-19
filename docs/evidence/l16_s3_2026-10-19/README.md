# P3: ring-free directional orientation (L16) and bounded search (S3)

**Status: P3 AUTHOR CHECKS PASS; committed-source X3 / independent P4 review pending.**
Linux development VM, `/home/aiops/resense`, branch `det/l16-s3`, base main
`aec88d248fb1a48a275937607bd36c3587dc0dc9`. Measurements used an uncommitted author
snapshot; the published source matches that snapshot. [Publication handoff](PUBLICATION.md). Candidate
38-file fingerprint: `aacfd664bac988dfde9e911997b84589d409709af471af4bd758187e73b59c85`.
The changed frozen files are `resense/calibration.py` and `resense/detector.py`.
The existing seal pointer was not replaced by these author results.

## Implementation

* A unique axis with >98% same-sign returns constrains **signed forward** on a
  bounded 16k-point sample. This cue alone does not resolve roll. A separately
  resolved broad-horizontal/narrow-vertical angular field can constrain unsigned
  up under the existing upright-scanner assumption. Ambiguous/one-sided/pencil
  fields provide no invented up. The rail/bed check and two votes still apply.
* A first-frame, ring-free directional **up conflict** uses the existing owned
  <=4-frame / 32-MiB buffer to rebuild the newly supported startup in correct
  coordinates. Only the current stamp is returned. The normal eight-family
  startup retains its existing behaviour; `orientation_replay_frames` stays 0.
  The narrow automatic event explicitly records `trigger=directional_up_axis`.
* For this new history-recovery path, signed axis permutation precedes continuous
  tilt in canonical float32 XYZ order. Combining both into one multiplication
  changed rounding and later geometric thresholds on native-axis inputs.
* S3 samples **once to <=60,000 points before the candidate loop**, with scaled
  admission counts. The selected winner is separately validated on the original
  cloud so its voting/tilt observation is not a strided surrogate.

## Checked results

Recomputed from saved rows by [verify_rows.py](verify_rows.py), plus the existing
unmodified full-gate frame reviewer. [Machine-readable acceptance](author_acceptance.json),
[raw review](raw_review.json), [gate frame review](gate_frame_review.json).

| Check | Result |
|---|---|
| Actual Falcon, 24 rotations x 4,443 frames | All mappings correct by frame 1. The 16 newly recovered side/native-axis cases retain exactly the correct control's **1,387 STOP rows**, with none added or lost. Identity also has 1,387; the seven existing upright nonidentity cases retain their existing 1,372-row behaviour. |
| Normal Falcon input through the unchanged judge node replica | All **4,443 decisions, detections and warnings** match the same-runtime main control; no global/default replay event is activated. This is not a new real ROS/DDS execution. |
| Empty directional Pandar, with and without channels | **24 x 545 rows per variant: zero STOP in every case**, correct mapping. Old ring-free side controls had **355 / 498 STOP rows** and accepted the wrong mapping. |
| B4 positive Pandar with channels | All 24 cases retain the same-rotation main control's STOP and matched-object rows: identity/new-side cases **193 from frame 8**, existing upright nonidentity cases **191 from frame 10**. |
| Full author gate | **18,329 rows**, exit 0 without waivers/overrides; **208 non-latency metrics identical**. The serialized 15,269 ordinary rows and 3,060 Set F scoring/placement rows match outside the registered timing normalization. |
| Affected tests / lint | **226 passed**, no skips/errors/deselections; pinned Ruff passes. The older numeric implementation fails **20 of 24** coordinate-invariance controls. The rejected startup implementation fails the new history positive control. |
| Instrumentation | Two 100-frame plain/traced Falcon cases: **200 paired non-timing rows equal**. Search counts are 0 for correct input and 2 for the side recovery, with bounded candidate inputs. |

Matched-object checks use the existing judge distance/lateral tolerances and
visible in-gauge labels. Those tolerances can associate one detection with two
labels; retention is not a claim of separate object detections. Set F's legacy
rows do not contain full detection payloads, so independent hit/fp reassignment
is not claimed.

### S3 timing

Real node-decoded `doubleT_obstacle` frame 50, **340,610 points**, 90-degree yaw:
five calls after warmup, Haswell BLAS / one numerical thread on the shared
**8-vCPU VM**. Median search **98.45 -> 12.64 ms (~7.8x)**, maximum candidate
observation **340,610 -> 56,769 points**; both select candidate 9.
[Reference](search-reference-v4.json), [candidate](search-candidate-v4.json),
[driver](bench_search.py). This measures the candidate loop, not the complete
startup call or an idle-4-vCPU / stand / node-FPS acceptance.

## Input identity, failures and corrections

The organizer Falcon archive was unpacked separately; its 4,443 header/receive
time rows match SQLite. The first **100 CDR hashes** match the earlier retained
receipt. On **14 distributed frames**, direct NumPy views of the raw message
fields reproduce the cached XYZ exactly; ring absence and sign fractions are
recorded. [Input check](input_check.json), [raw examples](raw_falcon_examples.png).
The plots were inspected for forward-only coverage and plausible tunnel geometry.

The first FOV-only author candidate lost **19** Falcon STOP rows on side cases.
Full startup history repair fixed pure roll, but a cyclic/native-axis case still
lost **seven** rows because of composed float32 arithmetic. Both variants and
their partial runs are preserved under `/tmp/opencode/l16-s3/run2/` and `run3/`;
their source patches are `rejected_source.patch`. They are not passing evidence.
See [history amendment](AMENDMENT.md), [numeric amendment](NUMERIC_AMENDMENT.md).

The first snapshot driver kept mutable list aliases (frame 0 displayed later
observations). Its output `rejected_startup_snapshots.json` is invalid for
attribution. Deep-copy snapshots and explicit-source reproduction corrected this:
[verified 32-frame full states](rejected_startup_trace_verified.json). A separate
[dependency incident](environment_incident.json) invalidated an earlier interrupted
run; NumPy was restored/pinned to **1.26.4**, every replacement worker asserts it.
Both sources use native SHA-256 `67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394`.

Complete same-runtime main controls from `run2/` are reused explicitly by the
final `run4/` candidate, not relabelled as new candidate measurements. Execution
receipts: [suite](suite_execution_v4.json), [gate](gate_execution_v4.json).
All accepted raw directories and the exact source/tests/native binary are in
the `.tar.gz` files listed in `author_acceptance.json`; each accompanying manifest
records every member hash, and every archived member was reopened and verified.

## Limits and handoff

* This validates **coordinate remounts of the recorded directional Falcon FOV**.
  Field shape and channel cones are not gravity measurements. A physical scanner
  installed with a sideways scanning plane is not validated here.
* The deliberately ring-free **360-degree positive Pandar** control has only ~94%
  forward sign concentration. It supplies no directional cue and retains the
  inherited wrong/unresolved side mappings. These results remain in the report;
  **general L16 without usable independent evidence is not closed**.
* Existing upright nonidentity startup differences remain explicit. No new G3,
  J1, image, release or real-node timing result is claimed.
* Next owners: commit the actual selected P3 source/protocol/tests; run formal X3
  on that committed source and obtain independent P4 safety review; P1 integrates
  and reseals the accepted bundle. The current author snapshot does not replace
  those steps.
