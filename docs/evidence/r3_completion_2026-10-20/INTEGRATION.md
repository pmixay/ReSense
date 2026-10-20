# Integration amendment after main advanced

The first protocol/patch were registered on `5fa865b`; source `0a472d6` was
measured while main advanced by 27 commits to `5d83c5b` (PR #45). Main added
independent F1a/L16 evidence, image/test fixes and a new integrity seal, but
changed no detector, native, model, configuration or ROS-package bytes.

The integration merge retains exactly the measured R3 production tree:
`git diff 0a472d6 HEAD -- resense native configs ros2_ws/src/resense_ros
pyproject.toml setup.py` is empty. Full pytest is repeated after integrating
main's proxy-hook fix; all earlier failed runs remain available.

The protocol originally excluded resealing. To keep the integrated source's
integrity check usable after main introduced a new seal, the integration may
replace that seal using the strict, unmodified full R3 gate and the exact
measured source inventory. This is an **integrity record**, not independent
P4 acceptance. Final bundle review, the general M1 battery and release stay
open. No numerical acceptance threshold or input population changes.
