# Additional reference attempt: original per-return timestamps

Raw A/C PointCloud2 fields include double timestamps over about33.31 ms per
scan; reduced decoded caches omitted these values. Before concluding that the
LiDAR-only reference cannot be validated, test motion compensation using these
original timestamps and the measured full SE(3) between header stamps.

First require byte-exact XYZ equality between each original decoded raw cloud
and its cached input when extracting timestamp alignment. Use a known constant
nonzero SE(3) motion with varying acquisition times as a sign/units control.
Compensate to the header start, re-register both resolutions, then repeat the
same direct comparison gates without relaxing their thresholds. No detector
source change or acceptance is inferred merely from lower registration error.
