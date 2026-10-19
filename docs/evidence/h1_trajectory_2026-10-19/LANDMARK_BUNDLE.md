# Multi-view landmark reconstruction attempt

Short-step geometry and color trajectories still disagree after repairing the
initial longitudinal alias and compensation. Direct dense/sparse matching fails
reverse closure even when both seeds converge to the same local minimum. A
rolling map reduces A's accumulated drift but does not validate it; reverse A
mapping itself loses longitudinal capture. These estimates remain rejected.

Next attempt: track localized reflective raw features over multiple real frames,
jointly optimize all poses and stationary landmark positions, and reserve a
deterministic subset of complete landmark tracks for validation. This differs
from chaining point-to-point feature ICP (which drifted). Association proposals
use the correctly seeded geometric motion, not the detector. Keep ambiguous,
short, sparse or partially observed feature tracks explicit.

* Raw intensity threshold 30, connected components at 0.25 m, at least three
  distinct returns, extent <=1 m (same pre-existing landmark extractor).
* Consecutive association at <=0.30 m predicted centroid distance; past feature
  may be at most five frames old. Use one-to-one assignment; retain every link.
* Use tracks with >=8 observations and >=15 m viewing-baseline translation.
  Every fifth retained track is validation-only, never an optimizer landmark.
* Optimize rigid poses and 3D landmark positions jointly, anchor frame 0, use
  robust residuals and short geometric edges as regularizers. This is a proposed
  reconstruction, not truth. Validate withheld raw-feature spatial consistency,
  known full-pose controls, observability and independent geometry before use.
* Do not infer absolute error solely from a low training residual or from the
  geometric regularizer. No detector changes or H1 closure depend on this attempt
  until validation actually succeeds.
