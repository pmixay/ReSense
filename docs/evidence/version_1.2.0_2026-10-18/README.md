# Unreleased 1.2.0 candidate — version and acceptance record

Measured source candidate: **`e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569`** on
`work/n5-labels-c2-acceptance`. The four core/ROS package declarations now say **1.2.0**.
This commit changes no detector, node, default configuration or display behavior: only the
four version lines, changelog and registered [plan](PLAN.md).

The captain selected **sealed `main` 1.1.0 for P4's next J1**, reviewing 1.2.0 separately.
[The pinned J1 target](main_j1_target.json) verifies all 36 frozen Git blobs and the original
1.1.0 gate at `3b7d7aa7cbbf238c21f84330497697da131b7cb9`. It is not a new judgement.
[CI](ci_status.json) remains blocked before job start by account billing/spending limits.
There is no release, tag, new published image or agreed release date.

## Validation state

The fresh complete default [gate](gate.json) **passed**, exit 0, on a detached checkout of
`e9d8fc6`, from **12:44:32 to 12:56:49 UTC**. It uses verified original/Set O/ride caches,
native binary `511f7766…`, Haswell BLAS and one thread, with no overrides or waivers.
All **18,329 rows** are complete: **15,269 ordinary + 3,060 Set F**. Every shared non-timing
ordinary field and every Set F scoring/placement row matches `cecab1b` exactly. All **805
ordinary STOP frames and 51 intervals** are preserved; none are added, lost, delayed or shortened.
[Reconstructed summaries and exact boundaries](gate_acceptance.json),
[field comparison](gate_frame_review.json), [execution identity](gate_execution.json).
An [independent agent review](../p4_followup_2026-10-18/INDEPENDENT_VERSION_GATE_REVIEW.md)
also verifies all rows, STOP boundaries, source/native hashes and 25 archived members.

The [finalizer](finalize_gate.py) retains the exact wrapper, execution status, raw rows and
input receipts in [the raw archive](raw/gate.tar.gz), then reopens and hashes every member
against [its manifest](raw/gate_manifest.json). Set F's legacy rows omit complete detections;
their stored hit/fp summaries and input identities are revalidated, not independently relabeled.

Version/release-tool validation passes **53 tests** ([JUnit](junit-release.xml)).
The [source-continuity review](../p4_followup_2026-10-18/source_continuity.json) ties the new
version to P4's checked source and to the already measured default-off source.

## Supporting runs retain their original identities

| Run | Measured source | Result |
|---|---|---|
| Previous selected default gate | `cecab1b` | 18,329 rows; all shared non-timing outputs exact against the native baseline |
| X3 | `cecab1b` | 40 cases, 29,765 rows, 260 checks; all 6,284 STOP frames and 204 intervals preserved |
| Full Falcon | `cecab1b` | 4,443 rows; all 1,372 STOP frames and eight intervals preserved |
| Actual Docker/DDS | `cecab1b` image | 140/140 Pandar/Falcon inputs; explicit profiles, pause/rate/reset tested |
| Host suite | `cecab1b` | 1,906 tests + 12 subtests; seven unavailable historical-fixture tests deselected |

[Raw evidence and precise limits](../lidar_adaptation_2026-10-18/default_off/README.md).
The version-only proof supports continuity; these are not relabeled 1.2.0 executions.
No throughput gain is inferred from shared-host timings. The missing historical Windows
Set O frame 332 remains a provenance limitation of the Linux X3 reference.

## Review and remaining defects

P4's original development check covered `b423562`; it was not a release-seal approval or J1.
Our source/data reviews are identified as agent reviews. **P4's final 1.2.0 approval remains
pending**, as does P3's acknowledgement of the proposed integration ownership. A candidate
integrity manifest will bind reviewable source/evidence bytes without declaring that approval.

Replay remains opt-in. N3 robustness fails, N6 remains below 60 m and off, and automatic
side-mounted orientation and curve-axis bias remain unresolved. The [P4/P3 handoff](../p4_followup_2026-10-18/README.md)
keeps those defects and the separately measured explicit-mount/display diagnostics visible.
