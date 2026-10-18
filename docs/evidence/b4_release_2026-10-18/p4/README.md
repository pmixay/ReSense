# Independent P4 safety review — B4, 2026-10-18

**Disposition: BLOCK / NOT ACCEPTED for release.** One reproducible matched-STOP
delay exists in the new recovery path under supported non-default calibration
settings (B1). Committed-candidate acceptance and paired X3 evidence were also
not available at review close (B2). The historical default-config B4 evidence
passes the independent frame audit; that does not resolve B1 or B2.

Reviewer: a separate **AI reviewer**, not the patch author and not independent
human approval. Review branch: `det/b4-orientation`. Observed HEAD:
`3b7d7aa7cbbf238c21f84330497697da131b7cb9`; candidate detector files were still
uncommitted. This reviewer wrote only this directory's review/scripts. Detector,
tests, seal and Git history were not changed by this reviewer; no push occurred.

## Source and chronology

Reviewed candidate SHA-256:

| file | SHA-256 |
|---|---|
| `resense/calibration.py` | `b340acda96830a6641b85a4da2172b7138ef0c27bce897341b3b45d9ab514429` |
| `resense/detector.py` | `4fa84cf71daac501e811383eed4db18b1f8057af8cd3448fc86265dbff100c84` |
| `resense/health.py` | `6b392b75f49c8065d73e120a962954ae1c0dad52b8ecb427c25999e532b45144` |

All five members of the author's `candidate_source.tar.xz` equal the live files
(including the test and historical protocol). These three production files are
the only changes among the 36 sealed paths. Reference checkout
`/tmp/opencode/resense-b4-reference` is clean at
`1b880168ce2dbeec2071838892ac05eed5a9166a`; **all 36** files equal the 1.1.0
seal. Every Python/config hash recorded in both B4 runs matches its respective
checkout. Both native binaries independently hash to
`67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394`.

The historical `PROTOCOL.md` existed as a file before author experiments, as
stated in the supplied chronology and the author report. It was **not committed
before exploratory measurements**. Its archived bytes match the current file;
archive timestamps are not a substitute for committed preregistration. The
author gate identifies the base commit and three dirty detector files. A later
prospective release protocol and fresh committed-candidate measurements can
govern release acceptance, but cannot make that historical sequence satisfy
`docs/DETECTOR_FREEZE.md:159-168` retroactively. The deviation must remain explicit.
At review close, the prospective protocol/committed candidate and new results
had not appeared in the shared release directory.

## Blocking findings

### B1 — lost voting observation delays a real matched STOP (supported config)

**Location:** `resense/calibration.py:394-420`, especially `414-417`.

The two orientation-voting observations are retained in `_recent`, but only
`samples[0]` is put into `_obs`. For `obs_spacing=1`, both voting frames are
eligible spaced observations. The second one is lost. The identity control
completes five observations on frame 4; the newly recovered sideways case
completes on frame 5. The real positive recording then first STOPs one frame
later, and frame 8's previously matched person STOP is absent.

Minimal real-data reproduction (zero-based frame indices):

* Original node-decoded float32 `doubleT_obstacle`, first 15 frames, unchanged
  `NodeReplica`/`run_frame`, real `observe_mount`, native kernels.
* Compare identity rotation 0 with P4 rotation 4, using the same rotation formula
  and correct-frame label matching as the author. The baseline is the correctly
  oriented control, not a false detection from the old wrong mapping.
* Supported configuration overrides, parsed fields already exposed by
  `DetectorConfig`/YAML:

  ```yaml
  resense:
    calibration:
      frames: 5
      obs_spacing: 1
      provisional_min_deg: 10.0
  ```

| observation | identity control | recovered rotation 4 |
|---|---|---|
| orientation confirmed | frame 0 | frame 1 |
| fifth spaced observation/final tilt | frame 4 | frame 5 |
| first real STOP | **frame 8** | **frame 9** |
| decision on frame 8 | **STOP** | **GO**, no detections |
| matched `person_crossing` frames in 15-frame probe | 8–14 | 9–14 |

The original frame-8 label is visible (`n_points=93`), in gauge, at **55.51 m**
(`labels/doubleT_obstacle.json:579-613`). The independent matching reports
`lost_matched_stop_frames = {"person_crossing": [8]}`. The sealed-reference
identity control with the same overrides also first STOPs at frame 8.
No observation/detection stub is used in this reproduction. The higher
provisional threshold exposes the final-calibration cadence; it is a valid
configuration, not a threshold change inside the detector.

Reproduce with the environment below:

```bash
"$PY" docs/evidence/b4_release_2026-10-18/p4/directed_checks.py \
  --only-short-window --assert-no-loss \
  --out /tmp/opencode/p4-b4-minimal-repro.json
```

**Observed exit 1**, as intended for the no-loss assertion. This does not
invalidate the author's default-config 35,808-frame result. It does invalidate
unqualified observation-preservation/no-added-STOP-delay claims for supported
configurations. State-isolated cadence probes reproduce the one-processed-frame
delay at periods 1, 2 and 5 with spacing 1; spacing 10 retains the control's
cadence in these probes.

**Resolution required:** author preserves every voting observation eligible
under the configured observation cadence, verifies actual per-object STOP
retention, and returns a new exact source identity for review. Alternatively,
the release owner must explicitly decide and enforce a narrower supported
configuration scope. This reviewer has not accepted such a scope reduction.
Fresh gates alone on this exact candidate do not close B1.

### B2 — release acceptance evidence incomplete

`DETECTOR_FREEZE.md` requires a complete gate on the committed candidate,
independent per-frame safety review, then reseal; X3 is an additional requirement.
The inspected gate is an author-worktree gate. No fresh committed-candidate and
sealed-baseline gate pair or X3 pair was available here. Approval remains blocked
until their completeness, identity and per-frame results are independently
checked. See exact requested inputs below. A future gate passing totals cannot
overrule the B1 matched-frame counterexample.

## Other findings and limits

### N1 — late channel evidence cannot undo an early false confirmation

Reproduced on **real empty rotation 4**, first nine frames. Omit channel metadata
only at frame 0 (`has_ring=false`); restore the original rings on every later
frame. Decisions are `CAUTION` on frames 0–3 and **STOP on frames 4–8**. With
normal channels, there are zero STOPs in the same nine frames and orientation
is recovered on frame 1. `_config_passed` latches the wall observation before
any scan-axis check, so subsequent rings are ignored at `369-371`.

This is a serious residual B4 failure, but it is explicitly excluded by the
author's README (mapping confirmed before usable channels arrive) and is not
a demonstrated regression from the sealed implementation. Treat it as a
nonblocking **scope limit**, not a fixed late-ring case. Absence of rings after
an already observed conflict does not erase that conflict; this control passed.

### N2 — three channel IDs do not enforce three distinct cones

`scan_axis` requires at least three successful channel fits, but its final
`ptp(means @ axis) >= .01` tests only total span. Three IDs with elevations
`[-.2, -.2, +.2]` radians produce an accepted Z axis despite having only **two**
distinct cone planes. Three IDs on one cone are rejected. Reproduced with
well-resolved, noiseless rays in `geometry_probes()`.

The README's “>=3 distinct cones” wording is therefore stronger than the code.
No wrong-axis adoption or lost STOP was established from this case, so this is
nonblocking evidence-bar/documentation feedback. Ordinary random/mixed IDs,
constant, negative, short, floating and two-dimensional channel arrays were
rejected in directed probes; that does not prove rejection of every constructed
or geometry-derived fake channel assignment.

### N3 — physical scan axis is not gravity; evidence has provenance assumptions

The fit normal is an **unsigned physical scan axis**, contingent on genuine
per-channel cone geometry in sensor-origin coordinates. It supplies neither
gravity, the forward sign, nor a guarantee for a physically horizontal spinning
scanner. Translation/deskew can invalidate the cone relation or, in special
geometries, leave an apparently good fit; these cases were not validated by B4.
Do not promote derived direction bins to independent hardware evidence.

The candidate caches the first usable axis; the two orientation votes reuse it
and are not two independent scan-axis measurements. Valid cones are independent
of misleading rail-like scene ridges only under these sampling assumptions.

With `keep_up_axis=true`, even `search_orientations=false` permits a measured-axis
conflict to prevent confirmation. Correctly configuring a physical horizontal
scanner's axes does not make its physical spin axis vertical. Such a mount needs
an explicit domain/configuration decision; the old general advice to change
`sensor.forward/left/up` is insufficient as a new scan-axis guarantee. The
documented `keep_up_axis=false` path bypasses the new constraint and retains the
old geometry-only limitations. Disabling calibration retains `disabled` behavior.
No result here validates a ring-free second LiDAR or resolves Falcon N2.

### N4 — label matches are algorithmic associations, not separate-object proof

The author's jury matching permits a single detection to match both labels.
For identity rotation, frames **27–51** share a detection under those tolerances:
61 person matches and 153 object-on-rail matches. An additional one-to-one gate
matcher audit on the rounded B4 records gives 61 and 128. Neither loses frames
relative to its own appropriate comparator. The full gate uses its own
unrounded outputs and records 61/129. These numbers are not interchangeable.
This does not change the preservation conclusion; it limits claims that every
reported object match independently proves a separate detected physical object.

## Independent evidence audit results

Read the freeze acceptance/X3 criteria, historical README/protocol, production
diff, added tests, runner/scorer, health/decision flow and config paths.
`audit_evidence.py` reads every archived B4 frame and original label row; it
does not trust the author's precomputed case totals or matched frame sets.

* **10/10 SHA256SUMS entries verified.** All four raw B4 file hashes match the
  summary receipts. Original positive labels SHA-256:
  `070bf3596ae42b682362aa97d8812b53155e288b03a79aff204441fa1c700402`.
* **35,808 B4 frames**, four complete files, 24 unique rotations each, contiguous
  frame indices 0–544 or 0–200. Paired input receipts, runtime/environment and
  per-checkout source hashes agree; runner script hashes also agree.
* Candidate empty recording: **zero STOP** for all 24 rotations. No incorrectly
  accepted orientation and no GO before `_config_passed`. Every nonidentity
  mapping is recovered on frame 1; identity is confirmed on frame 0.
* Positive default identity: 193 STOP, first frame 8. Seven other previously
  supported upright mappings: 191 STOP, first frame 10, retaining their old
  two-frame startup delay. Sixteen new sideways recoveries: 193 STOP each,
  first frame 8. All per-label matched-frame sets retain their comparator under
  **both** jury and one-to-one matching. Frame-set inclusion rules out a lost,
  delayed or shortened previously matched interval in these recorded cases.
* Upright comparator is the same-rotation baseline. Newly recovered sideways
  comparator is the correctly oriented baseline identity. Old wrong-mapping
  STOPs are recorded as raw differences, never credited as real saved obstacles.
* Author gate raw archive: **15,269 recording/Set O/ride rows + 3,060 Set F rows**
  in **30 sequences = 18,329**. Six-recording, five-empty, Set O, ride and Set F
  gate sections reconstruct exactly from the raw outputs/summary. All 146 gated
  rows pass; 208 compared non-latency metric rows equal the named historical
  baseline; 16 changed informational rows are latency. No waivers/missing rows.
  This is a recomputation of archived evidence, not a fresh detector gate.
* Author JUnit: **421 test cases**, zero failures/errors/skips; 38 belong to the
  new test file. The loaded-host failed run and earlier rejected attempt are
  separately disclosed in the author README; their existence is not a later PASS.
* Independently reran the small new test file: **38 passed in 0.63 s**, no timing
  suite. Health conflict is an error with zero monitored/clear range; the node's
  existing STOP-before-FAULT policy preserves actual obstacle precedence.
* Scan-axis equivariance/small-tilt controls pass in the supplied tests. The
  `cos(max_tilt)^2` bound accommodates combined per-axis tilts; it is not by
  itself a sufficient per-axis tilt acceptance test. Existing final tilt checks
  still supply that limit. Search needs rail/bed/forward evidence and two winning
  votes; channel normals alone do not select a mapping. Votes are cumulative,
  not necessarily consecutive, as in the previous implementation.

## Commands, outputs and reproducibility

Use from `/home/aiops/resense`:

```bash
export PY=/tmp/opencode/resense-b4-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export LD_LIBRARY_PATH=/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu
export PYTHONPATH=/home/aiops/resense

"$PY" docs/evidence/b4_release_2026-10-18/p4/audit_evidence.py \
  --out /tmp/opencode/p4-b4-audit.json
"$PY" docs/evidence/b4_release_2026-10-18/p4/directed_checks.py \
  --assert-no-loss --out /tmp/opencode/p4-b4-directed.json
"$PY" -m pytest -q -p no:cacheprovider tests/test_mount_ring_axis.py \
  --basetemp /tmp/opencode/p4-b4-pytest --junitxml /tmp/opencode/p4-b4-pytest.xml
"$PY" -m ruff check docs/evidence/b4_release_2026-10-18/p4/audit_evidence.py \
  docs/evidence/b4_release_2026-10-18/p4/directed_checks.py
```

Audit exited 0; directed no-loss check exited **1** (B1); pytest and reviewer
script lint exited 0. `git diff --check` passed. Native hashes and clean
reference identity were checked separately. The full directed diagnostic uses
48 real replay frames plus small synthetic/state probes. The minimal B1 mode
uses 30 real frames. A further 30-frame sealed-source control used:

```bash
PYTHONPATH=/tmp/opencode/resense-b4-reference "$PY" \
  docs/evidence/b4_release_2026-10-18/p4/directed_checks.py \
  --repo /tmp/opencode/resense-b4-reference --only-short-window \
  --out /tmp/opencode/p4-b4-baseline-short-window.json
```

The first baseline-control invocation exposed a reviewer-script access to a new
state field absent from baseline and aborted. The compatibility access was
corrected in this directory only; the control then completed. No detector
result from the aborted invocation is used. The full 421-test suite, fresh
gates and X3 were not independently rerun during this review.

Detailed generated audit/diagnostic receipts remain at the `/tmp/opencode/`
paths above; [verification.json](verification.json) records their hashes and
the principal results. The repository-retained review files are this report,
that receipt, `audit_evidence.py`, and `directed_checks.py`.

## Exact evidence needed before reconsidering acceptance

1. **B1 resolution:** author response, corrected committed source identity (or
   explicit, enforced scope decision), and paired per-frame real-label evidence
   showing no loss at frame 8 in the reproducer. Include relevant cadence
   controls at differing `periods`/`time_cadence` settings. Any changed source
   needs review and renewed B4/affected-test acceptance.
2. Prospective release protocol **commit ID**, candidate **commit ID**, exact
   source/runner/config/native hashes, source-clean receipts before and after
   measurement, and an explicit record that historical author preregistration
   was a file, not a pre-experiment commit. Preserve the original evidence.
3. Fresh complete **candidate and sealed-reference gate JSONs**, commands,
   exit codes, logs, raw `*.jsonl` for all six originals, Set O and all eight
   ride pieces, full `setF_straight.json` sequence rows, and hashes of these
   artifacts. State cache/intake identity, stamps, config and native path on both
   sides. Need same-runtime per-frame comparison for matched STOP preservation
   on real positive, Set O and Set F, not only the 208 metric-row comparison.
4. Complete **X3 baseline and candidate** reports and raw outputs with exact
   four decoded input identities, variant definitions/seeds and measured commits.
   Independently compare every variant to the explicitly identified full
   baseline: at most +1 false STOP episode and at most 2 lost matched STOP
   frames per positive object/recording, with empty/external/unmatched false
   alarms separately accounted. Missing/corrupt reports or unequal inputs fail.
5. After evidence review resolves the blockers and an explicit accepted P4
   disposition exists, P1 can perform the separately ordered reseal/review/verify.
   This blocked report is not authorization to reseal, merge, push or release.
