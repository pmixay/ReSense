# R3 target-specific K1 measurement

Registered before this author lane's 100/150 m measurements. Detector source is
`64f5d74c`. No detection repair is claimed by the cadence change. The original
K1-1/2/3/4/5 criteria remain unchanged.

Run the existing curvature-step-aware `tools/range_test.py` through
`standing_probe.py`, with per-variant object-free baselines, at 100 and 150 m
(`--start 360 --end 620 --obj 0.5,0.5,1.75`), and sudden appearance at 100 m
(`--start 450 --end 620 --appear 100`). Source is the full 877-frame decoded
`squareT_platform_squareT_switch`, whose X3 content fingerprint equals the
historical reference. ICP is independently recomputed by the unchanged jury
`icp_odometry.py`; inspect its standing section and compare independent B6
motion before interpreting results. Original absolute counts remain the gate;
different placement/visibility rows must be explicitly disclosed.

Variants: default off, K1 only (`walls_smoothing_distance=1.5`), v5c-15
(the five `V5C` overrides in `run_recordings.py`), and both. The default minima,
K2 reach and every detection/tracker setting remain unchanged. Platform
object-free and doubleT_obstacle controls use full `probe.py` outputs.

Report the historical position-matched count **and** current injected-return
support. The wrapper reads the range generator's actual appended-return ledger,
checks those bytes equal the last `2*n_obj` input returns, and records how many
appear in each reported track's current cluster. A held detection is labeled
as such, never given invented current support. Nonzero support demonstrates
source participation, not perfect object segmentation or an independent truth
for the track axis. Zero source support alone cannot classify a held detection
as false. Inspect raw target cases and use detected near/100 m objects as the
positive control. The separate trace must leave every ordinary output field
equal to a plain run before using its attribution.
