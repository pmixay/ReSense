# Baseline integrity after correcting clearance comments

Commit `cc834fc` replaces unsupported clearance/braking guarantees in three files' comments and
docstrings. Their executable syntax trees match the parent after removing docstrings; YAML
configuration files and effective parameters are unchanged. An independent reviewer checked this.

The fresh [full gate](../regression_gate_2026-09-26_comment_correction.json) passes: **199 comparison
rows, all 146 enforced metrics unchanged**, no missing rows or waivers. The six recordings,
organizer objects, full ride and set F are included. Compressed frame streams, the set F result,
configuration, command receipt and complete gate log are retained here. Timing is informational
because other work ran on this machine.

The prior seal remains at
[`detector_freeze_2026-09-26_before_comment_correction.json`](../../detector_freeze_2026-09-26_before_comment_correction.json).
The refreshed seal records the unchanged P3d behavior with corrected comments. **Final detector
quality freeze remains on hold.** M2 and T1 are not integrated by this source-integrity refresh.
