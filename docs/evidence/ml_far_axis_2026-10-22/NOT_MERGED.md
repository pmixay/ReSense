# Code of this lane: kept as a patch, not merged

**What:** learned far-axis model (track.learned_far_axis, off; accuracy gain, no range gain under the registered rule A3).

The branch `claude/ml-far-axis-1.3` (tip `7599136`) changed 8 files outside this folder (detector, configs, ROS config or tests).
Those changes are **not** in the 1.3.0 line: they would change the sealed 1.3.0 detector (seal
`docs/evidence/detector_freeze_2026-10-22_1.3.0.json`) or add a switch that is off. They are kept here so the branch can be
deleted (captain, 22.10, at the user's request).

* `code_not_merged.patch`: `git diff --binary 2a64cfe 7599136`, everything outside `docs/evidence/`.
* To continue: `git worktree add --detach ../work 2a64cfe && cd ../work && git apply --index <this repository>/docs/evidence/ml_far_axis_2026-10-22/code_not_merged.patch`,
  then rebase onto the current line; any detector change needs the strict gate, X3, an independent review and a reseal.
