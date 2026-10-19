# H1: completed available repair, blocked far-axis reference

P3 candidate **E**, source **`7d0f571`**, branch `det/h1-positive-core`, relative
to D / `19ffbe4`. **Overall H1 remains OPEN / blocked by an independently
validated far-axis reference.** This report records both the retained repair
and the unsuccessful attempt to construct that missing reference from LiDAR.

[Protocol](PROTOCOL.md), [reference correction](REFERENCE_AMENDMENT.md),
[retained E](CANDIDATE_E.md), [unretained F screen](CANDIDATE_F.md).

## Retained repair

The actual D tracker/cluster trace covers all177 visible A-axis rows, including
all68 unmatched rows, with a hooks-off equality check and complete snapshots.
Forty-eight unmatched rows are column demotion/hold cases. The detailed core
trace additionally equals the earlier plain raw FrameResult fingerprints on all
340 input frames. At30..45 m the wall-profile hull grows to metre-scale offsets
while observed near-rail residuals are centimetre-scale: local wall structures
are not a replacement for locally observed paired rails.

E therefore uses the current near-rail residual hull directly inside the
three paired slab stations' supported interval. Outside that interval the four
wall-profile hypotheses still apply; there is no rail-only extrapolation. The
additional body-interior erosion is0.02 m rather than0.05 m. The ordinary growing
gauge margin, full axis hull, point/height bars and confirmation remain.
The final geometric interval is still a consistency check, **not a calibrated
true-axis error bound**.

### Physical results, E versus D

| Fixed physical check | D | E |
|---|---:|---:|
| Three left137 m opaque cases |1/14 each|**10/14 each**, every scan after ordinary confirmation|
| All32 standing cases |293 matched rows|**320**, no previous matches lost|
| Outside bodies,8/17/25/37/67/109/137 m, errors0/+-0.3/+-0.6 m, with/without rails |expanded check|**0/280** false cores/STOP|
| Moving opaque body, y=-0.68,22 m/s |continuous from126.4 m|**130.8 m**|
| Moving opaque body, y=+0.68,22 m/s |continuous from130.8 m|**135.2 m**|

All32 standing cases now match every scan4..13 in the fixed14-scan cold-start
window. All12 moving phase/asymmetric-wall/off-centre-rail scenes have continuous
STOP from128.6..146.2 m through34 m, with no missed scan at or below100 m.
These are idealized physical scenes, **not real-world range or braking claims**.
[All physical rows](physical-e.json).

The additional72 physical extra-rail scenes produce no false STOP, but their
accepted anchors still follow the correct pair. They **do not validate recovery
from an actually selected wrong pair**. [Results](ambiguous-pairs-first.json).

F was tested in a separate P3 worktree, leaving E unchanged during its gate.
Its spatial rather than per-bin height support gives no output improvement on
the complete A-axis and fixed physical screen. F is not retained; its exact
different source and outputs are archived.

## Real recordings and preservation

* Full gate passes with no waivers/overrides/missing metrics: all208 non-timing
  metrics and15,269 ordinary +3,060 Set F rows equal D outside timing.
* Falcon preserves all4443 non-timing rows /1372 STOP rows, including every
  detection and warning payload.
* A-axis109->**114/177** matched visible rows, no lost matches or new unmatched
  STOP relative to D. Pooled held90 is19.75 m; the remaining63 unmatched rows
  are explicit. This injection follows the baseline detector axis, so it cannot
  certify independently correct far-axis placement.
* C-person55 matches /82.77 m first and E6 cable34 /86.25 m first /61.28 m held
  are retained. Every critical hit label is independently recomputed from full-
  precision captured detections on948 rows;340 A-axis raw fingerprints also
  agree between plain and assignment-traced runs.
* **X3 PASS:**40 cases /29,765 raw rows; every non-timing node row equals D.
  All source identities, worker completions, raw hashes and re-derived summaries
  are checked. The206 affected tests passed before the full runs.
* Final full pytest: **2188 passed +17 subtests, one inherited proxy-hook error-
  message assertion failure**, independently witnessed on the previous reference;
  eight external-data deselections and zero skips. All timing tests pass in this
  run. The full suite is not all-green and its failure is retained.

The raw comparator is exercised on a deleted captured positive STOP/payload and
a changed axis field. The same physical-control paths contain positive inside
bodies, observed rail pairs and confirmed STOPs. No absence result is inferred
from an unexercised detector.

## Why the far-axis reference was not accepted

1. Reconstructed full SE(3) trajectories and independently extracted near-rail
   profiles on340 A frames and268 C frames, without using the evaluated model's
   axis/floor/candidates to select reference rail points. Archived every support
   profile and input-frame hash. Known physical rail offsets and identity/
   nonzero rigid-transform controls pass.
2. Compared different registration methods/resolutions/ranges and direct skipped-
   frame closures. The first point-to-point alternate drifts by metres and is
   rejected. Whole-cloud point-to-plane comparisons improve consistency on some
   intervals, but do not establish a validated absolute far-reference budget.
3. Ran36 pre-registered long-baseline real comparisons using two initializations
   and reverse closure. **0/36 pass all validation gates:**17 fail initialization
   agreement,16 reverse translation and3 reverse rotation (the actual first
   failing branch is recorded on every row). A manufactured80 m /1-degree
   transform with partial overlap passes the same validator from different seeds.
4. Checked original per-point timestamps (about33 ms per scan), byte-matched
   their XYZ alignment to **all608 cached frames**, and compensated constant
   SE(3) motion before reconstructing both trajectories again. The independent
   matrix-exponential control agrees within1.6e-14 m on a known0.50 m scan motion.
   **The36 compensated real comparisons also fail validation:**25 initialization
   disagreements,8 reverse-translation and3 reverse-rotation failures. Motion
   compensation is retained as a rejected offline reference attempt, not installed
   in the production detector. [Compensated checks](reference-validation-deskew.json).

Thus the printed initial/subset axis-error percentiles and the plotted future-
view curves are **unverified reference estimates, not accepted truth**. They
must not be used to tune or certify a global model correction. The implausible
divergent registrations are retained as rejected estimates, not physical motion.
[Direct checks](direct-reference.json), [executed gates and positive control](reference-validation.json),
[diagnostic raw near points and unverified curves](reference-raw-v2.png).

The read-only SQLite inventory independently checks the original bags: A has545
and C268 PointCloud2 messages and no other recorded topic. Falcon has4443 point
clouds and215 log messages; its pose topics contain zero messages. This inventory
finds known nonzero point-cloud counts in the same queries, so the absence of an
independent trajectory is checked against raw bags, not just cache metadata.
[Raw topic inventory, checked against total/orphan message counts](raw-topic-inventory-checked.json).
Original per-return timing fields are present; the missing input is an
**independently validated spatial reference**, not the acquisition timestamps.

## Closure blocker and handoff

The next required input is **an independently surveyed/annotated far track axis,
or synchronized independently validated poses/trajectory**, sufficient to check
the100..150 m corridor on straight and curved scenes. LiDAR-only chain agreement
or detector-axis-aligned injected objects cannot substitute for that input.
No such validated reference was established in this work. P4 independent review
and P1 selection/reseal also remain pending. Missing fresh rails and actually
wrong selected rail pairs remain explicit limits of the collision proof.

This completes the available repair and its checks; it **does not close overall
H1 or establish real-world100 m stopping sufficiency**. All source/runtime
receipts, failed reference attempts and test failures are retained in the
portable source/raw archives with per-member hashes. Measured source bytes are
checked against the Git source commit before packaging. Original commands and
thread/native settings are in the execution receipts.
