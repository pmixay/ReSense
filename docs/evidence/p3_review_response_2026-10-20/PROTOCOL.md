# P3 response to shipping review — verification protocol

Scope: answer the remaining author-side comments on F1a B1, R3 B2/B3,
L16/S3 A1 and H-prime B4 on pinned `fb92213`. This is a P3 disposition and
bounded verification, not final independent P4 acceptance. Detector source,
defaults and the current seal are not changed by this protocol. G3 is excluded.

## Registered checks

1. Verify the current 40-file F1a seal and source equality to its measured
   `a77d884` detector. Use the existing identical native binary only after
   comparing its build inputs. Pin scripts, configuration and input hashes.
2. B4: directly exercise `_mount_cross_check` on explicitly supplied gauge
   candidates with analytically known true rail height. Sweep distances
   3/5/10/20/30/30.001/37 m, signed mount-height errors -3.2..3.2 m and hanging,
   standing-person and low-body supports. Check every result against a separate
   scalar predicate on raw Z. Save actual executed line paths and prove
   plain/traced candidate equality. Include exact/just-over threshold controls,
   pending/fallback/invalid-height guards and the known erroneous-model ceiling
   control. These are component/state-fault-injection cases, not a claim that
   normal calibration produces those errors on real data.
3. B4 persistence: for representative retained/demoted candidates, run cold
   tracker confirmation and a previously confirmed track. Count actual gauge
   reports, zone votes and misses rather than assuming an earned STOP persists
   indefinitely. Separately test whether consistent synthetic observations with
   incorrect height can be finalized by the calibrator. Do not equate this with
   a raw-cloud demonstration of false calibration.
4. F1a: use P4's original ray caster and raised-rail scene. Full-detector
   stationary scenes at 40 m: rail rises 0/.18/.20 m and tops
   absent/-.02/0/.02/.05/.08/.10/.12/.17/.20/.25/.30 m relative to true heads,
   F1a on/off, 12 scans. Recompute target matching from saved detections and
   raw source geometry. Empty and rail-height controls must be exercised.
5. R3: P4's carried-along tall/hanging 37 m target, R3 on/off, 18 scans;
   approached tall cable from 80 m at 10 m/s, speed known/unknown, R3 on/off,
   62 scans. Capture actual qualification returns and current/accumulated
   evidence. Compare full non-timing raw-result fingerprints and tracker state
   in plain and traced runs. A physical in-gauge co-moving target is labelled
   an obstacle per the organizers' answer; this is a P3 semantic response,
   not a captain's sign-off or completion of M1.
6. L16 A1: run P4's 450-scan open-air and tunnel starts and a 450-scan open-air
   person control. Check full decisions, mapping states and matched detections.
   Existing independent T1 and ring-free ambiguity evidence retain their
   original source/scope; no claim of universal mount recovery is made.
7. Recount existing F1a full-gate raw rows and verify provenance of the retained
   reports. Preserve the distinction between labelled-object retention and
   visually attributed rail-fragment STOP removal. Reuse full gate/X3/Falcon
   measurements only when their detector bytes match the current seal.
8. Run affected F1a/R3/calibration tests and the repository's pinned lint and
   integrity checks. Use a second read-only verifier and planted changed-label,
   missing-detection, changed-payload and boundary controls. Inspect raw examples.

Runtime: NumPy 1.26.4, `RESENSE_REPO` and `PYTHONPATH` point to the isolated
checkout, `OPENBLAS_CORETYPE=Haswell`, `OPENBLAS_NUM_THREADS=1`,
`OMP_NUM_THREADS=1`. Previous latency is set to 42 ms, with the initial `None`
preserved, only for deterministic output comparisons. This is not a latency run.
Output paths are exclusive. Any failed run remains separate from the accepted
capture. Report observed limits explicitly; do not turn them into measured
mount-error bounds or independent acceptance.
