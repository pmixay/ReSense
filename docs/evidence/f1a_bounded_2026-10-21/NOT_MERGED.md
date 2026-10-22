# Code of this lane: kept as a patch, not merged

**What:** F1a bounded head top revision 2 (switch off; safe on all synthetic rows, almost no ride gain; DECISIONS row 54).

The branch `claude/f1a-bounded-1.3` (tip `6cc7445`) changed 5 files outside this folder (detector, configs, ROS config or tests).
Those changes are **not** in the 1.3.0 line: they would change the sealed 1.3.0 detector (seal
`docs/evidence/detector_freeze_2026-10-22_1.3.0.json`) or add a switch that is off. They are kept here so the branch can be
deleted (captain, 22.10, at the user's request).

* `code_not_merged.patch`: `git diff --binary 6ee469c 6cc7445`, everything outside `docs/evidence/`.
* To continue: `git worktree add --detach ../work 6ee469c && cd ../work && git apply --index <this repository>/docs/evidence/f1a_bounded_2026-10-21/code_not_merged.patch`,
  then rebase onto the current line; any detector change needs the strict gate, X3, an independent review and a reseal.
