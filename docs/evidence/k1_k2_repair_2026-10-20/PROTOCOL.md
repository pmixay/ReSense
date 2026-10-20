# K1/K2 repair: author protocol, revision 1

Date: 2026-10-20. Role: **P3, detector author**, reassigned by the user's
«приступай к доработке». Branch: `fix/k1-k2-repair-20261020`, based on the reviewed
R3 detector (`f56ad5e6`) plus current main `84534583` (no detector changes).
The earlier [independent review](../k1_k2_review_2026-10-20/README.md) remains a
review of v5c. This session cannot independently accept its own new patch.

## Ordered work

1. **R5 / candidate r1:** register and commit failing observation-loss regressions,
   then repair the joint output's range bookkeeping. A failed bed fit must not
   unwrap the output into the uncapped base. Missing usable wall evidence has the
   same requirement. Preserve the independent base estimator and joint shape;
   monotonically shorten unsupported output range, using the existing 20 m
   no-boundary decay per nominal period, down to zero when nothing supports it.
   No dual extension is renewed by missing evidence. Current observations must
   restore range normally; rotation must keep the carried restriction. Test both
   native and numpy, off/cap-disabled controls, cold start and repeated dropouts.
2. Obtain the public raw bags/caches from the [data handoff](../p4_handoff_2026-10-20/HANDOFF.md).
   Trace R2/R3 losses on current source: `small_center`, crossing-person entry,
   marked tunnels 19. Compare hooked/plain rows (excluding only timings) before
   using attribution. Preserve the historical failures.
3. Register any further candidate **before its measurements**, with defect tests
   and exact overrides. Then repair Falcon retention (including 4410–4411) and K1
   target-specific convergence/standstill. Do not tune a global OR of gauges or
   relax the original acceptance criteria to recover a reported aggregate.

## Checks and acceptance

- Author r1 checks: regression fails on unchanged source, passes after repair;
  existing K1/K2, wall-drift, rail-extension, gauge and native tests; lint and
  configuration synchronization. Paired off-identity against the exact parent.
- Recorded candidate checks: strict full gate without waivers, X3, all 4,443
  Falcon frames with input alignment and lost/gained matched-frame sets; all
  1,667 marked frames with object-level first STOP/retention; target-specific K1
  100/150 m and sudden appearance with false-alarm controls; K2/B6 reference-axis
  accuracy and honest trusted range. Every row must identify its exact source.
- Reference: same-source K1/K2 off. Initial K2 override is v5c-15:
  `axis_joint_fit=true`, `axis_joint_range=false`,
  `axis_joint_min_curvature=0.0001`, `axis_joint_reach_cap=true`,
  `axis_joint_reach_dual=15.0`; K1 remains off for the R5 repair.
- Environment: Python 3.12, numpy 1.26.4, scipy 1.13.1, sklearn 1.5.2;
  `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=<checkout> PYTHONPATH=<checkout>`.
- A fresh independent reviewer, P4's exact-source acceptance, and captain/P1
  switch decision/reseal are still required. Both defaults remain off. G3 is
  untouched. A development preview is not a detector acceptance or a new seal.

This protocol precedes the new regression run and all candidate measurements.
