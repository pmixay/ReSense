# H1 closure investigation — independent review BLOCKED

**H1 remains OPEN. The audit and independent review are complete; the required
repair, validated far-axis reference and H1 acceptance are not complete.**

The investigation was performed on the VM. Original measured source:
`f56ad5e62d9d051811c804734c7731b6951eae90`. A concurrent F1a completion was
handled in an isolated checkout pinned to
`520e7dcd2843a0e7c9055fca6c186c0d1687945f`, with a fresh H1 replay rather than
assuming the earlier conclusions carried over.

## Requirements and independently checked outcomes

| Requirement | Outcome |
|---|---|
| Independently confirmed far rail axis / trajectory | **BLOCKED.** Neither raw A/C topics nor the supplied organizer archives provide a validated reference. The attempted trajectories fail their checks. |
| Resolve the 63 misses | **Not achieved.** Every miss is now attributed to actual executed rules and snapshots; all 63 remain on the F1a-completion source. |
| Wrong rail pair and missing rails | **Checked in directed scenes; failures confirmed.** The raw anchor can agree with the same incorrectly selected pair. |
| Independent review | **Completed, BLOCKED verdict.** Raw results, labels, rail fits, physical geometry and positive controls independently checked. |
| H1 final acceptance / reseal | **Not accepted.** The existing 1.2.0 F1a integrity seal passes, but does not establish H1 safety acceptance. |

## 1. All 63 misses

The fresh A probe processes 340 frames; 177 have visible injected returns.
Full-precision detection matching gives **114 hits /63 misses**, with exactly
the historical miss IDs. Plain/traced runs are equal on all 19 non-timing
`FrameResult` fields, including raw arrays. All 63 primary labels and their
contributing gates were independently checked from the executed traces.

| Executed primary mechanism | Miss rows |
|---|---:|
| Column hold | 43 |
| Axis limit | 9 |
| Zone-vote delay | 7 |
| Merged wall-segment filter | 2 |
| Height-reference limit | 1 |
| Tracker confirmation | 1 |
| **Total** | **63** |

These are observed executed mechanisms, not a claim that each is the sole
counterfactual root cause. The injection follows the cached detector baseline;
its physical in-gauge placement has no external validation. The numbers must
not be interpreted as surveyed-axis recall or braking sufficiency.

[Full miss audit](../h1_miss_audit_2026-10-20/README.md),
[independent final review](../h1_final_review_2026-10-20/README.md).

## 2. Actually selected wrong rails and no rails

The new physical matrix contains **31 sequences /518 scans**, with explicit
host and distractor geometry. All 837 actual track/core-anchor rail-estimator
calls were independently reconstructed from their raw points.

* In four outside-target sequences, the detector actually selects the
  distractor and produces **56 false-core rows /40 false target-STOP rows**.
  For targets at lateral ±1.50 m, the entire body lies outside the true host
  envelope with a **0.22 m** gap.
* Four inside-target sequences miss all 14 scans each. The matrix also includes
  successful correct-pair and inside-target positive controls.
* Three actual rail-free cold starts give no new core or target STOP in
  **42 scans**. This is a detection limit, not evidence that the path is clear.
* After rail loss with the target still visible, an existing STOP persists
  for four scans through the zone vote. After loss of the target itself, it
  persists for one missed scan. Current evidence and tracker retention are
  counted separately.
* In the actual floor-held scene, `rail_slabs=3` is inherited from the prior
  despite zero current rail returns. A separate physical blocker produces its
  own STOP; this is not confused with the target's retained STOP.

These are conditional physical simulations using rail-like rectangular ridges,
not a frequency estimate on real routes. Other mounts, phases, curves, motion,
standard-height host mis-selection and ±1.59 m wrong selection are not certified.

[Rail limits, raw geometry and reproduction](../h1_rail_limits_2026-10-20/README.md).

## 3. Independent reference and the supplied links

The reference audit checks 11 original SQLite bag databases, independently
counts their topics/messages and validates nonzero point-cloud controls. A has
545 point clouds and C 268, without recorded pose topics. Falcon has 4443 clouds
and 215 log messages; its pose-topic entries contain zero messages.

All **36** saved direct-reference comparisons fail the diagnostic gates. The
separate landmark validation covers **55 withheld tracks /1185 observations**;
it does not establish an independently measured pose-error budget.

The links supplied during this investigation were checked against live metadata:

* <https://disk.yandex.ru/d/DK6H3Lxiyi-M-Q> is `falcon_test.zst`,
  **6,758,209,772 bytes**, SHA-256
  `90dea27d8636bcb2e5cdddf9bc15add3eae0e05196c2b3de959482da7e505611`.
* <https://disk.yandex.ru/d/SfBeRHbs8bNJAQ> is the six-file organizer folder:
  set O, Falcon, the ride, original and marked synthetic data, and the obstacle
  description. The marker topics establish synthetic obstacle geometry, not
  independently validated host rail geometry.

These match the already investigated inputs. Fresh, sanitized VM API metadata
is retained in `user-sources.json`; signed download URLs are excluded.

[Independent reference audit](../h1_independent_2026-10-20/README.md).

## 4. Verification after F1a completion

On pinned `520e7dc`, fresh A340 and directed518 replays reproduce **all 858
outputs exactly outside timing**, including all 63 miss IDs and the wrong-pair
failures. Directed tracker state is also exact. All **104 H1 tests pass**.
The 40-file F1a integrity seal passes; its digest is
`9cc33a6838dcc30b3162bbf892d33a962008712060e12d68c363dc315d033507`.

The original causal traces retain their original source identity; the new run
is a plain replay demonstrating preservation on the updated source.
[Exact-source delta report](../h1_current_source_2026-10-20/README.md).

## 5. Required next input and implementation work

The missing spatial input is independently checked **left and right rail-head
geometry plus host-path identity at 100–150 m in identified A/C frames**, with
measurement support and quantified uncertainty. Alternatively, provide validated
synchronized relative SE(3), extrinsics and an error budget, with independently
checked later near-rail observations. Another self-consistent ICP chain or
detector-axis injection alone does not supply this validation.

The implementation must then address the measured column/axis/height/merging
and confirmation failures, and must distinguish the host path under ambiguous
rail geometry. Fixes require the acceptance-first detector workflow, strict
gate, X3/Falcon checks, independent safety review and a new seal. The present
publication records the reproducible blockers; it supplies no new accepted
H1 detector version.

## Publication contents

Only the explicit portable allowlists are copied into this publication. The
exact measured one-off Python tools are stored, without edits, in each package's
`tool-snapshots.tar.xz`. `tool-snapshots.json` binds every original filename to
its measured byte count and SHA-256. Before executing that package's original
reproduction or checksum commands, restore its tools into the package directory:

```bash
tar -xJf tool-snapshots.tar.xz
```

The snapshots retain their original imports and run-time source hashes. They
are archived experiment inputs; the publication adds no lint exclusions and
does not silently rewrite measured tools. `validate_bundle.py` checks both
ordinary files and archived tools against the original checksum lists, verifies
the copied allowlists and compiles every archived tool before publication.

The
miss package retains compact raw target supports, all miss events/snapshots
needed for its standalone verifier, and hashes of omitted full clouds. Full
plain/traced and current-source captures remain on the VM. The rail package
contains an 18.6 MB lossless archive whose 128 members were reopened, restored
and independently hash-checked; follow its `PUBLICATION.md` before running
tools that expect the original extracted filenames.

`copy-receipt.json` records each copied file's size/hash and the exact-source
identity. `publication-paths.txt` lists only this H1 publication's intended Git
paths. Measured reports retain their run-time provenance; publication does not
relabel their initial `PREPARED_NOT_UPLOADED` status as a measured result.
