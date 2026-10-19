# Reference validation correction, before accepting axis-error numbers

The first608-frame reconstruction completed its manufactured/identity controls,
but its point-to-point alternate trajectory disagrees by metres at long range.
Those first axis-error percentiles are **unverified and not accepted**. Direct
ten-frame closures also reach0.46 m /0.185 degree on A; no universal centimetre
reference claim is allowed from that chain.

Use the previously independently checked whole-cloud point-to-plane registration
configuration (3..80 m,0.15 m voxels,0.5 m association,40 iterations) for the main
full SE(3) reconstruction. Compare another point-to-plane resolution/range, and
direct skipped-frame closures. Compare longitudinal steps to the retained earlier
odometry and flag implausible motion. Keep both initial failed method outputs.

Near-rail cross-view variation must be computed after removing the local lateral
slope: a five-metre bin on a curve legitimately changes Y. Raw Y span is not an
uncertainty estimate. Reference rows with unresolved registration disagreement,
bad closure, missing/ambiguous rails remain excluded with explicit reasons.
