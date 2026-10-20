# L16/S3: open-air startup repair — 20 October 2026

**Delivered:** P4 shipping A1 fixed by P3, real-start T1 measured; paired recorded
replay, full gate and X3 pass. Final F1a-main merged source `afbf9fc` also passes fresh
gate/X3/Falcon/affected checks. This is author acceptance, not independent P4 approval.
Base main `8c2bf51`, registered tests
`679bca8`, committed detector repair `4bf62f3`. Isolated checkout:
`/tmp/opencode/l16-open-air-checkout`, branch `fix/l16-open-air`.
[Publication/merge and source identity](PUBLICATION.md).

## Why an already delivered task was still open

The [19.10 delivery](../l16_s3_2026-10-19/README.md) recovered directional ring-free
remounts and bounded the orientation search. That source remained in main.
P4 subsequently found a new regression in its signed-forward cue, [shipping A1](../p4_review_shipping_2026-10-20/README.md#a1-a-correct-full-revolution-pandar-that-starts-in-open-air-is-fault-for-the-whole-run-confirmed).
The earlier author report explicitly left general ring-free/physical-mount limits
and independent acceptance open. S3's <=60,000-point search budget itself was not
the cause of A1.

## Repair

The only changed production file is `resense/calibration.py`. A unique >98%
one-sided coordinate now also needs a forward-cone check on the existing bounded
<=16,384-point sample: its second-percentile ray cosine must exceed cos(80 deg).
This is equivalent to P4's proposed 98th-percentile angle below 80 deg. A half-space
of ground below the scanner supplies neither forward nor up evidence.

Existing channel-axis evidence, rail/bed observations, votes, conflict handling,
bounded history, float32 coordinate application and S3 sampling stay active.
There is no blanket clearing of a real conflict at the 400-frame timeout.
An unsupported directional cue no longer vetoes the valid configured mapping.

## Fresh analytic controls

Original P4 analytic ray caster, NumPy 1.26.4 and native kernels on the same VM.
The stationary scene is replayed at 10 Hz; distances are scene geometry, not a new
real-world range acceptance. Every input hash is equal across the pair.

| 450-frame case | Before | Repaired | Independently checked |
|---|---|---|---|
| Correct upright Pandar, open air | 450 FAULT | **450 GO** | no false cue, confirmed mapping, actual cone-rejection branch |
| Correct upright Pandar, tunnel | 450 GO | **450 GO** | every non-timing result field equal |
| Open air, 0.45 m-wide /1.7 m-tall body at 40 m | 4 FAULT +446 STOP | **4 GO +446 STOP** | all **446 matched body rows retained**, no STOP lost/added |

The empty open scene has 162,848 points, only 0.1793% above the sensor. Before the
repair it supplies false forward -Z, despite channel geometry identifying up +Z;
the configured mount is never observed and fallback freezes at frame399.
The repaired source rejects that cue and observes the correct mount immediately.
All450 accepted traced/plain rows agree outside the registered clock-dependent
health/timing normalization; the executed rejecting return was recorded directly.
[Raw-derived audit](audit-analytic.json).

## T1: all 12 original starts, first 10 raw frames

**120 raw CDR frames**: six Pandar recordings, Set O, first ride split, Falcon,
and three marked bags. Every frame was decoded independently by direct NumPy
views of the declared CDR point fields, range-filtered and compared exactly with
the jury decoder. The configured sensor-to-vehicle matrix is retained per row.
Computed cues, actual executed cue lines, complete mount state, health, fractions,
CDR/XYZ hashes and raw examples are saved.

* **No A1 exposure in these 120 original frames.** The minimum above-sensor share
  is **28.2693%**, not near the <2% failure scene. This does not assert that an
  unseen recording cannot start in open air.
* All12 runs confirm a supported mapping by frame9. Falcon's legitimate default
  +Y configured-frame forward is preserved; it is an automatic remap, not A1.
* The same checker detects the known open-air false -Z cue on the pre-fix source
  and verifies its removal by the repaired source (positive control).
* The original first ride split was reacquired (407,789,568 bytes). Its first10
  raw frames reproduce the previously verified compact cache **exactly**, including
  receive timestamps. The source's published checksum/size match the earlier full
  intake. This acquisition stops after split0: it does **not** claim a new checksum
  of the entire17.1 GB archive. Its compressed-prefix/member hashes are retained.

[T1 audit](audit-t1.json); producer [real_starts.py](real_starts.py),
acquisition [acquire_ride.py](acquire_ride.py).

## Tests and acceptance scope

The new test first fails on pre-fix main with false forward `[0,0,-1]`.
**242 affected tests pass**: 48 ground-half-space rotation controls, four complete
450-frame starts (ring/ring-free, stationary/open-to-tunnel), existing directional
positive controls, history/numeric recovery, health and S3 search budgets.

The full suite completed with **2,340 passed, three failed, eight external-data
deselections and 17 passed subtests**. The failures are preserved in the raw log:

* Accumulation timing p95 was 245.0 ms against the existing 150 ms assertion.
  A paired targeted rerun also fails on the unmodified reference (343.3 ms) and
  repair (349.2 ms), under concurrent VM load. The assertion is unchanged.
* The inherited proxy-hook assertion fails on both sources: the child correctly
  exits86, but reports `ModuleNotFoundError` rather than the expected pinned-source
  message. This remains a final-acceptance follow-up.
* One node status-marker test got `FAULT: input not trusted` instead of GO in the
  full run. The exact test passes in both source-bound targeted reruns. Its full-run
  transient cause is not established; this is not an all-green-suite claim.
  An initial complete node-only pair gives146 passed on the reference and145 passed
  plus a different ring-field/FAULT failure on the repair. The subsequent complete
  source-bound pair gives **146/146 passed on both**. Every failed run is retained;
  the post-failure diagnostic reporter never hooks a detector/node call.

[JUnit-derived test audit](audit-tests.json).

Paired recorded startup prefixes are complete: **120 cases /3,840 rows per side**,
all non-timing results, full mapping matrices and confirmation states equal.
Wrong-mapping labels were independently rederived from every output matrix; the
known ring-free full-revolution positive control retains its inherited ambiguity.
The same row comparator rejects a planted deletion of an actual detection.
[Prefix audit](audit-prefix.json).

## Complete paired recordings and gate

* All **120 prefix cases /3,840 rows** plus **20 full cases /23,740 rows** per side
  are audited: **27,580 paired rows**, exact non-timing results, full mapping matrices
  and confirmation states. Full cases0/4/5/12 cover Falcon4,443 frames and Pandar
  empty545 /positive201 frames with and without channel metadata.
* Each full Falcon case retains1,387 core-replay STOP rows; channel-supported Pandar
  positives retain193. These are the core replay's arithmetic/axis path; the later
  ordinary node-replica Falcon check is reported separately.
* Every wrong-mapping label was rederived from the complete output rotation matrix.
  The inherited unsupported ring-free full-revolution positive cases4/5 still have
  201 wrong-accepted rows each; case12 remains unconfirmed. A1 repair does not solve
  that general ambiguity. The planted actual-detection deletion is rejected.
  [Recorded audit](audit-recordings.json).
* Both complete default gates **PASS without waivers** on their committed sources.
  All **208 non-timing metric tuples**, **15,269 ordinary rows** (782 STOP rows) and
  **30 Set F sequences /3,060 rows** are equal. Every ordinary result field is checked
  outside the registered timing-only normalization; every Set F field is equal
  except summary wall time. [Gate audit](audit-gate.json).

* The original committed-source X3 pair **PASS**: **40 cases /29,765 rows /260
  comparisons**, no changed decision/detection/warning payload, no lost STOP or
  detection. Raw metrics are rederived; a planted three-STOP loss fails the comparator.
  [X3 audit](audit-x3.json).

## Final merged source, including current F1a main

While these runs were executing, F1a was published on main `99dab01`. A separate
committed merge **`afbf9fc949f31e920a4d698df8fdfd058afeb308`** incorporates it and
PR #43 without textual conflicts. Fresh runs on that exact source:

| Check | Result |
|---|---|
| Default full gate against the seal baseline | **PASS**, exit0, no waivers, clean committed detector source |
| Raw gate versus F1a's published author run | all **208 non-timing metric tuples**, **15,269 ordinary rows**, **30 Set F sequences /3,060 rows** equal |
| Standard committed-source X3 | **PASS**, 40 cases /29,765 rows /260 comparisons; no decision/detection/warning changes versus pre-F1a reference |
| Whole ordinary Falcon node replica | **4,443 rows**, exact decisions/detections/warnings/mount versus F1a's published run; **1,364 STOP**, 3,070 CAUTION, 8 GO, 1 inherited startup FAULT |
| Affected L16/F1a/K2/native tests | **489 passed**, 1 external-path deselection, no skips |
| Analytic controls | unchanged: open450 GO, tunnel450 GO, positive4 GO +446 STOP |

Audits: [gate](audit-merged-gate.json), [X3](audit-merged-x3.json),
[Falcon](audit-merged-falcon.json), [tests](audit-merged-tests.json),
[analytic](audit-merged-analytic.json). F1a reference files are authenticated against
its committed raw manifest, not an arbitrary current working tree.

F1a's documented ride false-alarm cost remains: the chunked gate has23 events /
26 STOP episodes instead of18 /24 before F1a (111 STOP frames). The final source
equals F1a's retained raw run; **this is not an L16 regression or closure of F1a's
stronger current-main no-regression goal**. Its separate review/cost disposition is
preserved. The original full-pytest failures above remain disclosed.

Full-suite or shared VM timings do not establish live-node FPS or stand timing.

## Reproduce

Use a fresh output namespace: `run_checks.py` reserves outputs exclusively and
creates source/native snapshots, logs and source-unchanged receipts. Runtime:
`RESENSE_REPO` and `PYTHONPATH` point at the tested checkout,
`OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`, NumPy1.26.4.
The reference checkout is pinned at `8c2bf51`.

```sh
python docs/evidence/l16_open_air_2026-10-20/run_checks.py analytic --side reference
python docs/evidence/l16_open_air_2026-10-20/run_checks.py analytic
python docs/evidence/l16_open_air_2026-10-20/run_checks.py t1
python docs/evidence/l16_open_air_2026-10-20/run_checks.py gate
python docs/evidence/l16_open_air_2026-10-20/audit_results.py analytic
```

`run_checks.py --repo <checkout> --revision <fresh-name>` also supports the final
merged check commands recorded in their `*-execution.json` receipts. Every receipt
has source/native snapshots, exact environment/command, log digest and before/after
source continuity. [Source audit](audit-sources.json) reopens all snapshots and logs;
the actual pre-fix/repaired source difference is exactly `resense/calibration.py`.

Portable raw outputs are in three `raw-evidence-*.tar.gz` bundles with
[`raw-manifest.json`](raw-manifest.json) and [`package.json`](package.json). Every
member is reopened and hashed. Restore them under `/tmp/opencode/l16-open-air-work`;
the final F1a comparison additionally uses its already-published
[`raw-evidence.tar.gz`](../f1a_b1_2026-10-20/raw-evidence.tar.gz), restored under
`/tmp/opencode`. Organizer raw databases are excluded; acquisition identities remain.

This addresses the current L16/S3 A1/T1 follow-up. Field shape is not gravity;
general ring-free full-revolution or unknown physical-sideways installations
without usable independent orientation evidence remain an explicit support limit.
H1/F1a/R3 findings, final-bundle independent P4 review/reseal and release work are
tracked separately. No G3 data or judging run is used.
