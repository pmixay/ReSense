# Code of this lane: kept as a patch, not merged

**What:** dead-switch cleanup, paused work in progress (not gated, not resealed).

The branch `claude/cleanup-switches-1.3` (tip `3db349a`) changed 18 files outside this folder (detector, configs, ROS config or tests).
Those changes are **not** in the 1.3.0 line: they would change the sealed 1.3.0 detector (seal
`docs/evidence/detector_freeze_2026-10-22_1.3.0.json`) or add a switch that is off. They are kept here so the branch can be
deleted (captain, 22.10, at the user's request).

* `code_not_merged.patch`: `git diff --binary f24d939 3db349a`, everything outside `docs/evidence/`.
* To continue: `git worktree add --detach ../work f24d939 && cd ../work && git apply /home/user/ReSense/docs/evidence/cleanup_switches_2026-10-22/code_not_merged.patch`,
  then rebase onto the current line; any detector change needs the strict gate, X3, an independent review and a reseal.
