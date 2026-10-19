# B4 orientation acceptance — registered before candidate measurements

Base: `3b7d7aa` (`main`), sealed detector 1.1.0. P4 reference:
`1b88016`, `docs/evidence/orientation_2026-10-18/` and
`scripts/orientation_battery.py`. No commits or release are authorised in this
session; this protocol is saved before reproduction/patching, but is not yet
the committed preregistration required for shipping by DETECTOR_FREEZE.

## Defect and scope

Eight sideways mounts accept a tunnel wall as a bed and report STOP on
395–509/545 frames of the empty `roundT_squareT_pressureGate_squareT` recording.
Find the observation that incorrectly confirms the orientation. Fix orientation
validation/recovery, not obstacle suppression. A pending/failed orientation
must not silently become GO. Do not change corridor, cluster or tracker rules.

## Acceptance fixed before the patch

1. Reproduce the baseline on the original node-decoded float32 clouds with the
   P4 24-rotation ordering. Keep runtime and inputs identical for before/after.
2. All eight problematic sideways rotations: no incorrectly accepted mapping
   (`ok`, `identity`, `provisional` with a wrong axis mapping). Target zero STOP
   frames on the empty recording and no silent GO while orientation is unknown.
3. All eight previously supported upright/upside-down rotations: correct mapping
   still adopted by frame 1 (identity may be kept); compare per-frame decisions
   against the same-runtime baseline and inspect any lost/delayed/shortened STOP.
4. Run all 24 rotations on both original recordings, including
   `doubleT_obstacle`. Report each rotation's expected/actual mapping, adoption
   frame, decisions, first matched STOP and matched STOP frame set. STOP counts
   alone are not evidence that the real obstacle was detected. Check the
   `doubleT_obstacle` labels and nearest distances.
5. Unit/geometry controls: rail-like ridges on a wall must not independently
   confirm a contradicted mount; correct mounts and small tilts still work;
   absent/invalid ring information must not be mistaken for orientation proof.
6. Run affected calibration/reseed/health/native tests. Record failures and
   missing inputs explicitly. Full gate without waivers and independent review
   are required before shipping; no reseal as part of this author patch.

Use `OPENBLAS_CORETYPE=Haswell`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`.
Preserve exact source hashes and commands for candidate results, since the
candidate will be an uncommitted worktree. Any unmet criterion means partial
or rejected acceptance, not a fixed B4 claim.
