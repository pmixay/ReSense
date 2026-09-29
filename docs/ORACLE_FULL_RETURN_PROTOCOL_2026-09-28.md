# Full-return oracle translation follow-up

Registered after first-study commit `e4121e4`, before this follow-up is executed.
One worker; unchanged production code, thresholds, voxelizer and shape rules.
This is conditional clustering, with no tracker, actual odometry or STOP claim.

Use the same 44 frames, exact source identities, historical track fits, preserved
timestamps and fixed causal motion rule as the first protocol. Windows are fixed at
two and three frames. The neighbor graph is the previously defined bounded physical
graph throughout; no motion fitting uses cluster results.

For each window shift **all original cached XYZ returns** along vehicle X by the
accumulated supplied displacement. Do not register Y/Z through the detector's track
model. Retain old points only while their shifted X is at least 40 m, matching the
production accumulation range. Current-frame points keep normal corridor selection.
Select the combined physical cloud with the current serialized historical geometry.
The point set is shared between these two strict-membership alternatives:

1. Historical flags: each return retains its strict and rails-only strict flags computed
   at capture time. A point outside the historical corridor has false flags.
2. Recomputed flags: recompute both strict masks from the current serialized geometry
   after translating the full cloud. Retain current physical XYZ and current dy/height.

The advisory corridor uses current geometry in both alternatives. Keeping unselected
raw returns until alignment is an explicit difference from the production buffer, which
stores only past corridor candidates. Record source counts before and after current
corridor selection so this extra information is visible.

Paired controls remove all organizer-appended object groups and use the identical motion,
geometry, point-selection and membership rules. Preserve exact source indices, their
frame identities and current/history markers. Report source/background contamination,
strict source occupied voxels, contributing source frames, actual cluster rejection,
scaled thresholds and surviving gauge candidates. Count a pure-source cluster separately
from one whose shape/count depends on background returns.

Decision: the >100 m source-only result survives clutter only if the full-return run
has source-supported gauge candidates there, including a candidate with three contributing
source frames in the three-frame variant. Any paired-background gauge candidates are
reported as failures of the clean-improvement screen; no trial outcome is a STOP claim.
Historical vs recomputed strict flags isolate membership retention under the same
physical union. Comparing either with the earlier production buffer additionally changes
coordinate re-embedding and retained raw support, so it cannot identify only one cause.

After this run, stop diagnostics and recommend the next production feasibility gate;
do not choose a default or retune thresholds on the result.
