# Detector quality cycle — 26 September 2026

The user authorized this cycle after asking to work on the system's weaknesses before a final
freeze. **Release publication remains on hold.** The sealed P3d version remains the reference.
This record separates measured improvements from goals that remain open.

## Results

| Work | Result | Disposition |
|---|---|---|
| Node freshness | Explicit live/replay clocks, source and residence age, queue validity, output expiry metadata, STOP retention and valid recovery. Stock Humble/Fast DDS functional trial passes all 15 checks. | Implemented; combined-image original-bag acceptance pending. |
| Dashboard freshness | Checks transport age under the synchronized-UTC contract, expires stale status locally, retains STOP across invalid input and labels old distances. | Implemented; 15 browser tests pass. |
| M1: every raw envelope return limits range | Removes all 46 GO diagnostic overclaims, but adds 14.8–49.6 percentage points uncertainty on empty bags and sharply reduces range. | Rejected; no production change. |
| M2: existing supported thin clusters limit range | Target overclaims 54→44; GO overclaims 46→36. Ride adds 0.612 percentage points uncertainty and retains 99.02% of median range. Detection output stays identical. | Eligible as a partial improvement; final validation pending. |
| A1: restrict extra tracking allowance to forward motion | Ride 45→44 events, 183→180 alarm frames; aggregate placement matches improve. One fixed case loses 2→1 matches and fails the registered per-case gate. | Rejected; source remains unmerged. |
| D1: full-cloud context for clipped thin/floating candidates | Small edge object gains five STOP frames; synthetic matches 544→591. Outside-object false STOPs rise 6→9 and ride STOP episodes 38→40. | Rejected; source remains unmerged. |

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
Original-bag raw comparison, stress checks and idle runtime results are being added before
an integration decision. The earlier phrase “183 gated metrics” counted unchanged informational
rows too; the [clarification](evidence/results/quality_cycle_2026-09-26_clarifications.json)
records the correction without changing the gate.

Freshness is validated at publication. The watchdog shares the detector executor and cannot
run while that executor is blocked. An actionable consumer must expire timestamped status on
its own timer; the plain decision topic cannot prove current validity. Source, node and live
dashboard UTC clocks must be synchronized. These mechanisms are not a braking safety guarantee.

## Goals still open

| Goal | Remaining gap |
|---|---|
| No actionable GO/range overclaims | M2 still leaves 36 GO overclaims in the existing fitted-envelope diagnostic. |
| Material sustained detection improvement | Neither detection-changing candidate passed acceptance. Edge and small-object ranges remain late. |
| At most 30 ride false events | Accepted detector behavior still has 45 events and 38 STOP episodes. |
| Independent generalization evidence | The user confirmed no additional untouched real-positive recording. Seen synthetic combinations do not replace one. |
| Envelope-reference decision | Organizer Q1, rails versus sensor axis, remains unanswered. Axis union stays off. |
| Final presentation identity | Approved team names, photos and Telegram contacts remain pending. |
| At least 75/100 | The previous independent combined score is 64.5; a new score requires review of the final evidence. |
| Final freeze and release | Quality goals remain open; release is explicitly prohibited by the user. |

## Evidence index

- [Central protocol](evidence/results/quality_cycle_2026-09-26_protocol.json)
- [Missed-object diagnosis](evidence/results/quality_cycle_2026-09-26_missed_diagnosis/README.md)
- [Actual false-target diagnosis](P4_FALSE_TARGET_DIAGNOSIS.md)
- [M1 rejection](evidence/results/quality_monitoring_M1_2026-09-26/README.md)
- [M2 observer](evidence/results/quality_monitoring_M2_2026-09-26/README.md)
- [M2 production validation](evidence/results/quality_monitoring_M2_production_2026-09-26/README.md)
- [A1 rejection](evidence/results/p4_A1_2026-09-26/README.md)
- [D1 rejection](evidence/results/quality_cycle_2026-09-26_D1/README.md)
