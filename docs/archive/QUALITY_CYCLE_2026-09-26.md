# Detector quality cycle — 26 September 2026

The user authorized this cycle after asking to work on the system's weaknesses before a final
freeze. **Release publication remains on hold.** The sealed P3d version remains the reference.
This record separates measured improvements from goals that remain open.

## Results

| Work | Result | Disposition |
|---|---|---|
| Node freshness | Explicit live/replay clocks, source and residence age, queue validity, output expiry metadata, STOP retention and valid recovery. Stock Humble/Fast DDS functional trial passes all 15 checks. All six original-bag captures pass freshness and post-settle delivery checks. | Implemented; the combined image fails its separate clear-bag detector alarm criterion. |
| Dashboard freshness | Checks transport age under the synchronized-UTC contract, expires stale status locally, retains STOP across invalid input and labels old distances. | Implemented; 15 browser tests pass. |
| M1: every raw envelope return limits range | Removes all 46 GO diagnostic overclaims, but adds 14.8–49.6 percentage points uncertainty on empty bags and sharply reduces range. | Rejected; no production change. |
| M2: existing supported thin clusters limit range | Target overclaims 54→44; GO overclaims 46→36. Ride adds 0.612 percentage points uncertainty and retains 99.02% of median range. Offline detection output stays identical. | Offline gates pass; combined runtime acceptance fails. Source remains outside the main branch. |
| A1: restrict extra tracking allowance to forward motion | Ride 45→44 events, 183→180 alarm frames; aggregate placement matches improve. One fixed case loses 2→1 matches and fails the registered per-case gate. | Rejected; source remains unmerged. |
| D1: full-cloud context for clipped thin/floating candidates | Small edge object gains five STOP frames; synthetic matches 544→591. Outside-object false STOPs rise 6→9 and ride STOP episodes 38→40. | Rejected; source remains unmerged. |
| T1: retain observed boundary disagreement | Removes both exact-sequence clear failures; ride events 45→43 and episodes 38→32. All 72 placement results remain unchanged. Median published range retention fails on a ride segment (50%) and a platform/switch recording (93.4%), below the required 95%. | Rejected; source remains unmerged. |

All candidates were specified before their evaluations. Failures remain in the repository;
no acceptance threshold was relaxed to turn a failed candidate into a pass.

## What the diagnosis established

- Exact source-return tracing reproduces all 1,510 organizer-object frames and all 72 placement
  cases. Sparse returns can disappear at the confidence margin or clustering stage. Clipping
  can leave a flat row from a taller object, which cannot start a track.
- The synthetic study combines detector misses with disagreement between the placed objects
  and the detector's fitted envelope. Its 22.1% match rate is not real-obstacle recall. Every
  original case remains in the reported denominator; fitted geometry is not surveyed truth.
- All 45 actual ride alarm identities were traced through 11,271 frames with unchanged output:
  21 low track-cross-section fragments, six vertically continuing structures, four extended
  side-profile fragments and 14 unresolved sparse targets. The categories describe observed
  geometry, not independently verified physical object classes.
- Selected real rail-object heights overlap the low false fragments. Raising a height threshold
  is not justified by this diagnosis. Local context needs broader validation before it can
  support another rejection rule.

## Acceptance evidence

M2 production output exactly matches its observer on **15,269 frames**. The full comparison
retains **199 rows, including all 146 enforced metrics**, with no regression, omission or waiver.
All 72 placement case dictionaries, including their per-frame results, are exactly unchanged.
The combined detector/node code passes **668 tests plus six subtests**, with zero skips.
Raw Set O detection/warning output is identical to its reference across all 1,510 frames.
All 18 rate/positive-roll/positive-pitch summaries and all 30 startup-offset summaries preserve
their detection metrics. Raw and quantized-cache scores retain their earlier differences.
The earlier phrase “183 gated metrics” counted unchanged informational
rows too; the [clarification](../evidence/results/quality_cycle_2026-09-26_clarifications.json)
records the correction without changing the gate.

### Combined runtime failure

The preregistered image built at `0145cbb` passes cold, warm, bounded-load and stock Fast DDS
switch trials. Across all six per-bag captures, decode+detect p95 is below 39 ms, source freshness
checks pass and no original-header messages are lost after settling. These are controlled
measurements on this machine, not organizer-hardware results.

**Standalone clear replay fails:** one genuine detector STOP at 53.0 m where the registered
limit is zero. It occurs at header stamp `946692947.533395`; freshness is valid and the STOP is
not held from an earlier result. The same source frame caused an identical geometric alarm in
the older baseline's stock-console capture. An older successful clear trial processed that frame
as advisory. Exact replay now reproduces all three processed sequences in both the baseline and
M2 with zero detector mismatches: 233/243/234 frames and 1/1/0 STOPs. The failure remains a failure;
it is not waived because an older detector also exhibits it.

The trace identifies a trust increase after boundary loss and a merged fragment that changes the
column's apparent width. [Point-level diagnosis and figure](../evidence/results/quality_cycle_2026-09-26_clear_failure/README.md).
T1 tests the trust mechanism with unchanged numerical limits; it does not tune the column rule.
Its target screen passes, but its coverage gate fails: in ride segment 4 the `clear_distance`
median falls from 120 to 60 m. The separate `health.monitored_range` median falls from 120 to
107 m. A separate empty platform/switch recording falls from 88.9 to 83.0 m (93.4% retention).
The contradiction cap persists for about 40 s through one-boundary fits. All 72 original
placement cases and rows remain identical. The failed coverage criterion rejects T1; no further
stress, raw or runtime trials are used to seek a favorable outcome.

The local image archive is an offline review artifact with `runtime_acceptance_passed: false`.
Its source/native checks and load test pass; packaging does not confer detector acceptance.
The prior baseline image remains separately preserved. No tag or release is published.
[Captures, exact image identity and archive receipt](../evidence/results/quality_freshness_2026-09-26/README.md).
The combined image contains M2; it is not an acceptance record for the main branch's P3d core.

The separate P3d-plus-freshness CI archive at `d480b13` passes local checksum, offline load,
revision, installed/imported source and enabled-native checks. All six CI jobs pass for that
source. The previous local image is restored. [Delivery receipts](../evidence/results/quality_delivery_2026-09-26/README.md)
record its exact identity; successful delivery does not close the detector acceptance failures.

Freshness is validated at publication. The watchdog shares the detector executor and cannot
run while that executor is blocked. An actionable consumer must expire timestamped status on
its own timer; the plain decision topic cannot prove current validity. Source, node and live
dashboard UTC clocks must be synchronized. These mechanisms are not a braking safety guarantee.

## Goals still open

| Goal | Remaining gap |
|---|---|
| No actionable GO/range overclaims | The main detector retains 46 GO overclaims in the existing fitted-envelope diagnostic; unmerged M2 reduces that to 36. Freshness validity establishes the age of evidence, not completeness of obstacle detection. |
| Material sustained detection improvement | No detection-changing candidate passed acceptance. Edge and small-object ranges remain late. |
| At most 30 ride false events | Accepted detector behavior still has 45 events and 38 STOP episodes. |
| Independent generalization evidence | The user confirmed no additional untouched real-positive recording. Seen synthetic combinations do not replace one. |
| Envelope-reference decision | Organizer Q1, rails versus sensor axis, remains unanswered. Axis union stays off. |
| Final presentation identity | The supplied names/nicks/school and four individual portraits are in a local private preview. City, team-formation details, group photo and contact details remain pending. |
| At least 75/100 | Not met at the time; the reviews of that day are superseded by [`SCORECARD.md`](../SCORECARD.md) (28.09 evening). Rejected candidates receive no improvement credit. |
| Final freeze and release | Quality goals remain open; release is explicitly prohibited by the user. |

## Evidence index

- [Central protocol](../evidence/results/quality_cycle_2026-09-26_protocol.json)
- [Missed-object diagnosis](../evidence/results/quality_cycle_2026-09-26_missed_diagnosis/README.md)
- [Actual false-target diagnosis](P4_FALSE_TARGET_DIAGNOSIS.md)
- [M1 rejection](../evidence/results/quality_monitoring_M1_2026-09-26/README.md)
- [M2 observer](../evidence/results/quality_monitoring_M2_2026-09-26/README.md)
- [M2 production validation](../evidence/results/quality_monitoring_M2_production_2026-09-26/README.md)
- [M2 raw, stress and startup checks](../evidence/results/quality_cycle_2026-09-26_M2_validation/README.md)
- [Combined runtime protocol](../evidence/results/quality_combined_runtime_2026-09-26_protocol.json)
- [Freshness and runtime results](../evidence/results/quality_freshness_2026-09-26/README.md)
- [A1 rejection](../evidence/results/p4_A1_2026-09-26/README.md)
- [D1 rejection](../evidence/results/quality_cycle_2026-09-26_D1/README.md)
- [Clear-failure attribution](../evidence/results/quality_cycle_2026-09-26_clear_failure/README.md)
- [T1 protocol](../evidence/results/quality_cycle_2026-09-26_T1_protocol.json)
- [T1 rejection and full results](../evidence/results/quality_cycle_2026-09-26_T1/README.md)
- [Main branch test evidence](../evidence/results/quality_root_checks_2026-09-26/README.md)
- [Comment-only baseline refresh](../evidence/results/quality_comment_baseline_2026-09-26/README.md)
- [Current-source offline delivery verification](../evidence/results/quality_delivery_2026-09-26/README.md)
