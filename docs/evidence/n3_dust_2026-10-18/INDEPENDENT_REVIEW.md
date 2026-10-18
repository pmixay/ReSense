# Independent N3 review

Reviewer: `c2_implementation`, independent of the dust generator, regular harness,
Set F harness and verifier authors. This review makes no production acceptance
claim. Corrected complete recording and Set F batteries are still pending.

## Findings and disposition

1. **Corrected: the original regular harness mixed coordinate frames.** It placed
   dust into configured, pre-mount-correction XYZ using `rail_z(20)` from the clean
   detector's corrected model. The frame100 dark-person diagnostic gives about
   **0.254 m** vertical disagreement. This estimate uses archived mount angles
   rounded to 0.01 degrees (roughly 2 mm uncertainty here); the source-level
   mismatch itself is exact. The reproducible calculation, raw hashes and exact
   archived v1 harness hash are in [independent_coordinate_review.json](independent_coordinate_review.json).
   Set F used its separate pre-process legacy placement model. This particular
   mismatch was not demonstrated for Set F; its incomplete bank instead lacked
   the shared auditable reference contract. No Set F dust levels had been evaluated.
2. **Corrected: the original Set F verifier trusted summary counters.** A summary
   edit could change reported recall without changing raw rows. The strengthened
   verifier reconstructs all aggregate fields from raw rows using the hash-verified
   recorded summarizer, independently bounds matching using serialized geometry,
   reconstructs the complete 110-source cadence and 8 m cutoff, and checks the
   common reference at every density. Deliberate summary hit/count edits, raw
   hit/decision edits with updated gzip hashes, missing sequences, shortened banks
   with updated manifest hashes, changed references and missing required source
   frames are all rejected. See [independent_set_f_verifier_probes.json](independent_set_f_verifier_probes.json).
   Those probes use artificial records and establish verifier behavior only.

The corrected regular verifier also passed seven independent tamper probes for
counts, first-inside range, raw associations, source hashes, cross-level references,
density and missing rows. A valid artificial case with first-any ratio **1.0**
and first-inside ratio **0.8** confirms that an early outside association cannot
mask an inside-range regression. See [independent_regular_verifier_probes.json](independent_regular_verifier_probes.json).

The original experiments remain separately labeled historical evidence. Their
raw data were not altered and their failed criteria were not promoted to passes.

## Corrected coordinate contract

`scripts/dust_reference.py` observes the actual clean `MountCalibrator.apply`
operation, rather than reconstructing its transform from rounded outputs or a
later state. Observing the class method also covers the fresh calibrator created
by bounded orientation replay. An identity shortcut records identity even when
state contains a tiny unapplied rotation; the method is restored after failures.

For row-vector points the helper applies `XYZ @ R.T`, performs attenuation and
volume generation in that frozen clean frame, and inverse-maps only newly
created points. Every retained source XYZ, intensity and ring is restored through
its original index. The entire source frame, stamp, frame ID and metadata are
hashed into the reference. The reference and source hashes are checked before
augmentation. Reference data and source indices remain outside detector inputs.

The registered cloud is a flat, axis-aligned volume anchored at clean
`rail_z(20 m)`. It is not a surveyed or graded rail surface. Its uniform volumetric
returns and approximate ring assignment are deliberate synthetic stresses, not
measured scanner or dust physics. No default density, extinction, intensity,
seed, physical-positive label or acceptance threshold was relaxed by this fix.

Independent observer tests passed **3/3** in **3.80 s**, covering actual orientation
adoption and replacement-calibrator replay, exact applied-cloud parity against an
ordinary detector, identity-shortcut behavior and exception restoration. The
root author's separate geometry tests cover noncommuting rotations, retained
bytes, bounds, deterministic replay, ringless input and source tampering. Source
hashes and commands are recorded in [independent_review_sources.json](independent_review_sources.json).

## Clean truth, fixed placement and metrics

The generator leaves source arrays and labels untouched, returns source indices
separately and adds no truth flag to input metadata. Set F removes the injector's
`obstacles` metadata before clean placement processing and evaluated processing.
A separate baseline instance advances legacy placement; every object specification,
placement model, render seed, original source identity and injected-cloud hash is
frozen before any dusty evaluation. Re-rendering must match that hash at every
level. Evaluated dusty state cannot move the object or its scoring denominator.

Physical-positive labels persist when attenuation removes all returns. Observed
return-supported hits are reported separately. Set F retains the historical
approximate distance/lateral matcher; zero-clean-return held matches are neither
supported hits nor false detections. Its raw serialized detection positions have
1 cm precision, so the verifier checks explicit ±0.005 m association bounds and
keeps ambiguous boundary rows visible rather than inventing exact geometry.

The regular-recording audit retains each label's per-frame inside, outside or
unknown gauge relation. An outside crossing association is not silently counted
as an inside positive. STOP episodes are counted independently within each bag
and level. First range and per-frame retention are both needed: an early match
can survive while most subsequent positive frames are lost.

## Independently checked historical complete captures

The independent raw-record check reproduced all hashes, indices, timestamps,
decision counts, STOP episodes and legacy associations in **804 dark-person
records**, and compared **1,035 health-only platform records** against their
corresponding baseline records. No detector replay was used for this check.
See [independent_completed_artifact_review.json](independent_completed_artifact_review.json).

For the historical dark experiment, low density retained all **61 inside** crossing
matches and lost one outside match; medium retained 4 inside crossing matches and
high retained none. Low also lost 25 of 128 clean inside rail-object matches;
medium lost all 128 clean rail-object match frames despite two new matches.
These are substantive retention regressions, not hidden by a preserved first range.

The historical health-only experiment retained every detection, warning, track,
input augmentation and STOP row exactly. Medium/high explicitly degraded all
345 frames and returned zero clear distance, but still had **25/3 false STOP
episodes** respectively. Recognizing poor visibility does not meet the false-STOP
criterion. Neither this result nor the rejected pre-tracker suppression is enabled
in production.

All these counts are labeled **pre-coordinate-correction**. They support the
historical diagnosis only; the final registered geometry requires new complete
captures. Concurrent or paused wall times are not throughput measurements.

## Corrected clean control

The first corrected complete platform clean recording contains all **345 frames**.
Every decision, range, detection, warning, track and other non-health detector
field is exactly equal to the earlier clean recording. All 345 configured input
frame hashes were independently rebuilt from the original NPZ files and metadata;
they match the captured references, and the full cache hash matches both runs.
Captured helper/config/native identities are unchanged from start to end, and
the corrected replay used the native implementation.

Strict non-timing JSON equality is **false**: 335 rows have changed health severity
or message text because this concurrent replay exceeded the 100 ms latency budget.
These are preserved individually. `decision_level`, decisions, ranges and all
remaining health fields are unchanged; the warning is not silently removed to
claim a full pass. For example, frame30 is GO in both recordings while measured
latency p95 changes from 74.6 to 252.9 ms. See
[independent_corrected_clean_comparison.json](independent_corrected_clean_comparison.json).
