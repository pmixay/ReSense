# B4 author fix: channel-constrained orientation recovery

**Historical author results:** B4 paired acceptance PASS; 421 affected tests
PASS; author-worktree gate PASS. Independent P4 subsequently found a supported-
config cadence blocker. Corrected committed-candidate acceptance is tracked in
[the release evidence](../b4_release_2026-10-18/PROTOCOL.md); the receipts here
describe the earlier exact source hashes, not the subsequent revision.
Base `3b7d7aa`, detector 1.1.0. P4's observation-only reference is `1b88016`
(`origin/ccr-027997e8-kqywat` at intake); its sealed detector/config are identical
to the base. Acceptance was saved in [PROTOCOL.md](PROTOCOL.md) before author
replays/implementation. No commit was authorised during that exploratory author
phase. The release protocol records the chronology and prospective acceptance.

## Confirmed cause

On P4 rotation 4 of `roundT_squareT_pressureGate_squareT`, frame 0's rotated
wall passes `observe_mount`: rail score **0.057226229** (bar 0.05), inferred
height **2.25355 m**, roll **−0.8908°**, pitch **+0.2136°**, forward ratio
**20,973**. `MountCalibrator.update` sets `_config_passed` immediately. The
configured orientation therefore never enters the alternative search. The
first false STOP is frame 4, while mount status is still pending; frame 202
reports `ok`. The existing forward-return check does not distinguish roll.

For the very same cloud, unit directions in individual channels resolve planes
whose shared normal is **Y**, not Z (e.g. ring 0: second covariance eigenvalue
0.01067, smallest 7.6e−17). Channel scan geometry supplies evidence independent
of the scene's misleading wall/rail-like ridges.

## Patch

* `resense/calibration.py`: at startup, fit at most eight channel-direction
  planes from a bounded 16k-point sample. Require >=3 distinct cones, resolved
  two-dimensional angular coverage, tight plane residuals and mutually aligned
  normals. Ring IDs need not follow an elevation order. Missing, constant,
  malformed, mixed or unresolved IDs supply **no** orientation evidence.
* Under the existing default upright-scanner assumption (`keep_up_axis`), a
  reliable measured scan axis constrains the proposed up axis. A contradicted
  configured mapping cannot confirm itself on a wall. Search all 24 rotations
  **only with that independent constraint**, and still require the existing
  forward/bed/rail checks and two orientation votes. Without channel evidence,
  the original eight-candidate search remains in force.
* Preserve the real observations from the voting frames for **newly recoverable
  sideways cases**, so restoring the mapping does not add two frames to the
  provisional tilt / true STOP onset. Previously supported mappings keep their
  existing calibration cadence.
* `resense/detector.py`: pass the actual frame channels to calibration.
* `resense/health.py`: the additive `mount.orientation_conflict` flag reports
  contradicted/awaiting-confirmation mapping as a health error, with zero
  monitored/clear distance. The decision rule still gives an actual obstacle
  STOP precedence; this is not a blanket STOP suppression while pending.

The scan-axis bar respects the existing per-roll/per-pitch tilt limit using
`cos(max_tilt_deg)^2`; a combined legal tilt is not incorrectly rejected by a
single-axis angular bar.

## Scope and limits

This fixes the **P4 transformed-Pandar B4 cases**, whose scanner is upright in
the reference frame. Channel-cone geometry identifies a physical **scan axis**,
not gravity. A scanner physically installed with a horizontal spin axis is not
validated by this experiment. Neither are arbitrary translated/deskewed clouds
or ring-free scanners. In particular the actual ring-free Falcon recording
does not gain a new orientation guarantee; its N2 warning attribution remains
a separate task. The unconstrained explicit `keep_up_axis: false` mode retains
its prior geometry-only limitations. A mapping already confirmed before any
usable channel evidence arrives retains the prior behaviour.

## Verification and reproduction

### Complete B4 result

[Summary](summary.json), [comparison log](b4-comparison.log), full paired
per-frame records [b4_raw.tar.xz](b4_raw.tar.xz): **PASS**, all registered B4
checks passed, **35,808 processed frames** (24 rotations × 746 frames × 2 sources).

| check | baseline | candidate |
|---|---|---|
| Empty recording, bad sideways cases 4/5/6/7/16/17/18/19: STOP frames | 395 / 509 / 505 / 505 / 509 / 509 / 509 / 509 | **0 in every case** |
| Empty recording, all 24 rotations | eight wrong accepted mappings | **0 STOP, 0 wrong accepted mappings** |
| Correct axis mapping, non-identity rotations, both recordings | only 7 of 23 found | **all 23 found on frame 1** |
| GO before mapping confirmed, both recordings | one upright case has a frame-0 GO | **0** |
| Positive recording, original upright cases | identity 193 STOP, other seven 191 | **same**, no lost per-object matched STOP frames |
| Positive recording, all 16 newly recovered sideways cases | wrong-frame STOP counts not meaningful | **193 STOP each, first frame 8**, no lost per-object matches vs correctly oriented control |

The object check matches **visible in-gauge** `person_crossing` and
`object_on_rail` rows using the original labels, not just a distance interval or
the total alarm count. Every previously matched object frame of the supported
upright mappings is retained. Every matched object frame of the correct
unrotated control is retained by the 16 new sideways recoveries.

The pre-existing two-frame startup delay of the seven non-identity upright
cases (191 vs identity 193) remains visible in the evidence. This patch does
not claim to remove it. The first author attempt and failing combined-tilt
check are preserved in [rejected_attempt1.tar.xz](rejected_attempt1.tar.xz).

### Complete regression gate

[Gate JSON](gate.json), [log](gate.log), [frame-count audit](gate_frame_audit.json),
[per-frame outputs and Set F details](gate_raw.tar.xz): **PASS, exit 0** against
`regression_baseline_2026-09-29_shell_off.json`, **208/208 non-latency metrics
identical**, no missing rows, overrides or allowed regressions. Coverage:
**18,329 processed frames** = 15,269 original/Set O/ride frames + 3,060 Set F
frames in 30 sequences. Runtime 478.8 s on this shared host, four workers.
The 16 changed information rows are timing; this is not a speed benchmark.

```bash
# On this stripped host, also expose the task-local EGL/OpenGL libraries:
export LD_LIBRARY_PATH=/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu
export OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python -c 'import open3d'
python scripts/regression_gate.py --cache <cache> --jobs 4 \
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json \
  --out <gate.json> --work <new-work-directory>
```

This is an **author-worktree** gate: `code.uncommitted_detector_changes`
explicitly records the three changed files. The source hashes are the same as
the final B4 battery and affected tests, and the exact candidate sources/test/
protocol are retained in [candidate_source.tar.xz](candidate_source.tar.xz).
[SHA256SUMS](SHA256SUMS) covers the raw archives and numerical receipts.

`run_b4.py` uses P4's exact rotation ordering and the unmodified judge node
replica / `run_frame`, recording detections as well as decisions and mount
status. It asserts the imported detector's origin and saves source hashes,
input hashes, Python version and BLAS/thread environment. Both sides use the
same newly decoded float32 inputs and native kernels on this host. Runtime:
Python 3.12.3, NumPy 1.26.4; this is a paired author replay, not a claim of
bit-identical Windows/P4 timing.

```bash
export OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python docs/evidence/b4_orientation_fix_2026-10-18/run_b4.py \
  --repo <baseline-or-candidate-checkout> --cache <decoded/bag> \
  --out <runs>/b4-<baseline-or-candidate>-<empty-or-positive>.json --jobs 2
python docs/evidence/b4_orientation_fix_2026-10-18/summarize_b4.py \
  --runs <runs> --labels labels/doubleT_obstacle.json --out <summary.json>
```

`empty` is the full 545-frame `roundT_squareT_pressureGate_squareT`; `positive`
is the full 201-frame `doubleT_obstacle`. Run all four combinations. The summary
checks completeness, mapping correctness, no GO before mapping confirmation,
zero empty STOPs and per-object matched STOP frame retention. New sideways
recoveries are compared with the **correctly oriented** positive control;
false STOPs from the former wrong mapping are not counted as detections saved.
Matching uses the judge's X/Y tolerances and visible, in-gauge original labels.

### Rejected first author attempt

The first candidate restored orientation but discarded the two voting
observations. It gave 191 rather than 193 positive STOP frames after recovery.
It also rejected a legal combined 12° roll + 12° pitch (a new directed test
failed). Both defects were corrected before the final battery. Preserve the
first-attempt evidence and the final source hashes separately.

The first broad test invocation exceeded its 120 s tool limit. A completed
follow-up on the first attempt was **418 passed / 1 failed** (combined tilt).
The refined candidate's loaded-host run was **420 passed / 1 timing failure**
(`test_timing_with_accumulation`: p95 240.85 ms during parallel replays/intake).
That loaded run is not counted as PASS; its [JUnit](loaded_host_pytest.xml) is
retained. After the competing replays/intake finished, the same full affected
suite passed: **421 passed in 45.65 s**, zero failures/skips/deselections,
including that timing test ([log](pytest.log), [JUnit](pytest.xml)). The pinned
CI lint wrapper passed ([log](lint.log)); the ROS parameter copy is unchanged
and in sync ([log](params.log)).

Source/package/native identities and the verified original archive checksum
are recorded in [provenance.json](provenance.json). Native binary hashes are
identical for baseline and candidate. [intake_tools.tar.xz](intake_tools.tar.xz)
retains the task-local cache preparation tools; they call the unchanged
repository decoder/cache writer. Ride source bytes and all 221 cached splits
were checked ([parallel receipt](ride_intake.json)); the official serial
intake then verified the entire published archive again, reused all 221 splits
and produced its standard [verified manifest](official_ride_intake.json).
The first gate invocation exited 2 because that manifest was absent, before
any detector measurement ([retained prerequisite failure](gate_prerequisite_failure.log)).

The next gate measured all **15,269** real/Set O/ride frames with no gated
detection regressions, but exited 2 when the Set F worker could not import
Open3D: the author runner had omitted its local `LD_LIBRARY_PATH`. That failed
run is preserved as [JSON](gate_without_egl.json) and [log](gate_without_egl.log).
The corrected complete run above passed with four workers and the same
native/BLAS/source and input identities; no missing-data override was used.

The old seal correctly reports the three changed detector files
([freeze.log](freeze.log)). It was not rewritten to bless an author worktree.
The X3 driver requires a committed detector and refuses this uncommitted
candidate; X3 remains a post-commit acceptance step together with independent
safety review and P1 reseal.
