# R3 completion: current-frame cable support and moving-target disposition

**Author implementation/acceptance complete; integrated on user request.**
Patch `0a472d6`, base `5fa865b`; merge of updated main `5d83c5b` is `47b220c`.
The merged detector/native/config/ROS-package tree is byte-identical to the
measured patch (Git diff and all 47 receipt members checked). Independent
final-bundle P4 acceptance remains separate.

## B2: correct label before changing the algorithm

P4's original [B2 review](../p4_review_shipping_2026-10-20/README.md) calls a
co-moving thin physical target's STOP false. The [organizer answer §12](../../organizers/answers.md)
says objects may move and everything inside the gauge is an obstacle. These
boxes occupy the gauge; their correct label is **STOP**. Waiting for the
static-world ego-veto would introduce a miss.

The original review is retained unchanged. At 30/37 m, both cable kinds keep
their existing early STOP, including when moving at train speed. The patch
also removes dependence on which rule becomes ready first: a fully qualified
clean cable run cannot be demoted just because ego-veto has enough history.
Other confidence, zone, timing, infrastructure-history, column and fresh-onset
guards still apply. The general ego-veto and its off switch are retained.

## B3: accumulation can help, historical returns cannot confirm

Accumulated corridor clusters now carry immutable `CurrentSupport`:
footprint, height span, distinct voxel count and strict-gauge voxel count
from **current-frame** points only. R3 reads these rather than rejecting
every accumulated cluster. Missing current descriptors fail closed. Old or
duplicate points, flat/sparse/wide/off-gauge returns and demoted clusters
cannot supply the fast run. No threshold or default configuration changed.

* P4-style speed-known approach from 80 m: first matched STOP **76 →78 m**,
  frame **4 →2**, with every old hit retained.
* At that new onset, the actual accumulated cluster has current footprint
  **0.0733 m**, height span **2.7448 m**, **17 current strict voxels** and three
  consecutive qualifying hits. Trace records the executed `_cable_kind=1`
  and `_cable_confirmed=True` returns.
* A co-moving resolved target at 80 m with known speed improves **0 →16/18**
  matched frames. A 20 Hz tracker control also confirms when veto is ready
  before the 0.3 s cable run.

## Checked results

| Check | Result |
|---|---|
| Registered red witnesses before production edits | 2 failures /10 passes on unchanged base |
| Focused cable/veto/history suite | **67 passed** |
| Affected tests in merged full run | **448 passed**, no skips |
| Physical analytic scenes | **32 cases /576 rows per side**, every old detection payload retained; three negative controls have no STOP |
| Plain versus actual return-traced control | **36/36 rows equal**, full non-timing payload and saved track state |
| Standing 5 cm cable, unchanged judge E6 | **86.25 m first /61.28 m held**, 34/59 visible matched rows; all340 rows equal base |
| Hanging Set O, node-faithful float32 replay | **48.19 m first**, 19 matched rows; retained on fresh X3 nominal |
| Full original gate, no waivers | **PASS**, all208 non-timing metric tuples equal base |
| Ordinary gate raw rows | **15,269 equal**, including791 STOP rows; no added/lost alarm payload |
| Set F | **30 sequences /3,060 rows equal** |
| X3 fresh paired runs | **40 cases /29,765 rows /260 comparisons**, all matched payloads/decisions retained exactly |
| Whole Falcon | **4,443 equal rows**:1364 STOP,3070 CAUTION,8 GO,1 inherited startup FAULT |
| Ride | **unchanged**23 events /26 STOP episodes /111 STOP frames |
| Integrity/release checks after reseal | **65 passed +6 subtests**; `detector_freeze.py verify` PASS |

The compact 1 cm gate's hanging first STOP remains **35.1 m**; it is not the
48.19 m float32 result. The previous [Set F population diagnosis](../r3_sustained_2026-10-20/README.md)
also stands: conditional median34.2 →17.8 m because coverage2/6 →4/6; no lost
old success. Neither number is a surveyed physical range guarantee.

## Verification, failures and limits

* [Gate audit](audit-gate.json), [fresh-pair X3/Falcon audit](audit-replay-final.json),
  [analytic audit](audit-analytic-strict.json), [independent E6 recount](audit-range.json).
  Audits reopen raw rows, validate source/label identity and recompute comparisons.
  A planted known-hit loss and an X3 metric loss are detected by the same checks.
* Physical labels were re-derived from the input boxes on **all576 analytic
  rows**. Four raw examples are printed in the analytic audit; the three raw
  positive/outside plots were visually inspected:
  [raw-cable-controls.png](raw-cable-controls.png). In-gauge returns visibly
  occupy the envelope; the outside target is lateral2 m from the rail axis.
* **Full merged pytest:2386 passed +17 subtests,1 failure,8 external-data
  deselections,0 skips.** The inherited child-process proxy-hook assertion
  expects “outside the pinned source”; the child instead raises
  `ModuleNotFoundError`, still exiting86. Paired targeted reruns reproduce
  that same failure on base and candidate, with timing and node tests passing
  on both. No all-green-suite claim is made.
* The initial loaded full run had2384 passes and three failures: timing
  p95=156.7 ms against150 ms, proxy-hook, and a node clear-distance mismatch.
  Those raw failures are preserved. The latter two additional failures do
  not recur in the merged full run or paired targeted reruns; their transient
  cause is **unverified**. No assertion was relaxed.
* This does not complete general M1. The receding80 m scene still has only
  three matched STOP frames; no broader moving-target recall is claimed.
  Unresolved H1, K2, F1a ride-cost decisions and release remain separate.
* The new [integrity seal](../detector_freeze_2026-10-20_1.2.0_r3.json) uses
  the strict measured gate and40 frozen files. The [integration amendment](INTEGRATION.md)
  explains the seal update after main advanced. A checksum seal is not
  independent acceptance, a release or a G3 run.

## Reproduce and inspect

The [protocol](PROTOCOL.md) and first failing tests were committed before
production edits. [Source audit](audit-sources-final.json) checks all source
archive members and the merged-tree Git identity; [test audit](audit-tests-final.json)
recounts JUnit. NumPy1.26.4, native built from unchanged source, Haswell BLAS,
one OMP/BLAS thread. Set `RESENSE_REPO` and `PYTHONPATH` to the checkout.

`run_checks.py` runs gate/X3/Falcon/analytic/E6/tests with immutable logs and
source snapshots under `/tmp/opencode/r3-completion-work`; use a fresh root
for reproduction. `audit.py` rechecks raw output; `package.py` reopens and
hashes every published member. Candidate X3's standard comparator uses the
authenticated prior-main result; the audit separately compares every case
against the **fresh** base replay.

The two `raw-*.tar.gz` archives contain full per-frame runs, input identities,
source snapshots, logs, initial failures and JUnit. [package.json](package.json)
and [raw-manifest.json](raw-manifest.json) list archive/member sizes and hashes.
No recording data or held-out G3 inputs are packaged or used.
