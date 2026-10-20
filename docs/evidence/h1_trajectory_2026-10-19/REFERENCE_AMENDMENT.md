# Longitudinal alias discovered in rejected trajectory

The raw transform inspection identifies a concrete estimator failure, not merely
an unknown noise budget: the original A chain initialized ICP at zero motion.
Frame 1 converged to 0.335 m instead of the alternate 1.34 m textured solution.
It then accumulated -40 degrees roll by frame 100. The tunnel's repetitive
geometry admits a longitudinal alias approximately one metre apart; propagating
the wrong local minimum corrupts the later trajectory and direct-match seeds.

Before extending the new reference, test intensity-textured registration with
five motion seeds (0, 0.6, 1.2, 1.8, 2.4 m), three fixed voxel scales and a raw
geometry/intensity validation score. The initial screen has distinct 0.341 m and
1.342 m solutions; the latter has lower raw joint cost, smaller intensity error
and better overlap. Neither is yet accepted as truth.

Next: reconstruct the fixed full A/C sequences with correctly captured short
steps by geometric and intensity-based methods, test reverse and skipped-frame
closure, and rerun the original long-baseline checks. Known-transform controls
must exercise longitudinal alias capture, not just an already correct seed.
Keep rejected initializations. Do not relax the previous validation limits or
use organizer object motion as train odometry.
