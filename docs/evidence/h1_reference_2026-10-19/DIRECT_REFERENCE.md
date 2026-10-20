# Long-baseline validation of the retrospective rail reference

Before accepting cumulative-pose reference rows, directly align later near-view
scans to earlier wide-range scans (3..190 m), initialized independently from the
two reconstructed chains. Use larger2 m normal neighbourhoods for sparse far
surfaces. Check reverse registration and the transformed rail point agreement
between the two initializations. Do not change detector source for this check.

Fixed earlier frames: A50/100/150/180/220/260; C0/25/50/75/100/125. Request
stations60/100/140 m, choosing the nearest independently accepted future rail
observation within8 m of the requested station. Preserve missing observations.
Record both convergence results, reverse closure and source hashes. Treat a row
as consistent only with <=0.10 m projected-point disagreement, <=0.10 m reverse
translation closure, <=0.05 degree reverse rotation closure, and overlapping
registration fitness>=0.70. These are validation checks, not survey calibration.
