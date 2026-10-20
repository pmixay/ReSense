# Revision 5: upper-body context for a low object crossing the gauge edge

Registered before the r5 edit or measurements, following the complete paired
545-frame r3 low-stage traces. At tunnels 259 the same cube's 0.478 m width is
clipped to 0.226 m before the 0.35 m straddle width rule. R4 only changes K1 speed.

Candidate: with the existing K2 switch on, the straddle stage may include its
current corridor candidates immediately above the floor and outside the low
search band as **shape context**. Limit the context laterally by the existing
maximum permitted object width. Keep the low bed-anomaly seed, local bed
reference and ordinary low candidates unchanged. No unsupported extrapolation
of the learned bed outside its measured cross-section.

Separate membership from shape: contextual points do not enter strict-gauge
voxel counts. A straddle cluster needs the existing `lowobj.min_points` distinct
strict voxels, its strict portion must satisfy the original height threshold,
and its reported distance is the nearest strict return. Shape width/length
checks still use the actual connected body, with all original thresholds. The
feature cannot create an obstacle entirely outside the envelope, turn duplicated
returns into independent support, or turn a rail sliver/long rail into a cube.
The input context is not evidence of free space or a wider train envelope.

Before editing, register and run numpy/native tests for a partial-width cube,
its translation to fully outside, a narrow fastening, an overlong rail-like
body, weak strict support, outside-only height support and K2-off controls.
The acceptance recording is the full tunnels bag versus exact r3, including
all marked objects and unassociated STOPs, followed by full platform/switch
negative controls and Set O. Instrumented/plain equality is mandatory for any
claimed mechanism. Do not declare the 16 lost original frames fixed from an
aggregate increase. Record all lost/gained frame IDs and extra detections.

R4 target and r3 X3 measurements continue on immutable checkouts. This revision
does not claim to repair crossing confirmation, weak far admission, Falcon's
floor fit, 150 m trust, or prolonged missing-floor trust. Those remain separate
original acceptance blockers.

Fixture correction before the edit: the first fully-inside positive control had
a 0.10 m tall corridor slice and was correctly handled by the ordinary corridor
stage (the duplicate low was removed). Set the low fixture's top to 0.18 m so
its corridor slice is thin and the control actually exercises the straddle path.
The initial failing receipt is retained; this is not a detector change.

Post-implementation code audit found a boundary interaction to test before a
follow-up edit: `_dual_zone` reads the complete body's nearest X. R5's new
out-of-envelope upper context can start before the reach cap even while the
strict intrusion starts beyond it, bypassing the dual-axis requirement. Register
a numpy/native regression for this case; the follow-up must read a low body's
strict collision distance. Ordinary low clusters already have distance equal
to their nearest X. Keep the initial r5 replay source immutable and identify
this follow-up separately.
