# F1a / B1 author repair protocol — 20 October 2026

Starting source: main `cefd4c4`. P3 detector work requested by the user.
The current default F1a is on (margin 0.01), cross-rail and global low-point
exclusion are off. B1: pieces of one long low object along a rail can raise
each other's rail-head reference and become weak evidence.

## Acceptance registered before measurements / detector edits

1. Reproduce the six-piece, 8 cm review counterexample on the starting source;
   an isolated piece is a positive detection control. The repair must retain
   all pieces as ordinary confirmation candidates on either rail. Check
   shared model-height offsets, cant, weak/advisory neighbouring pieces,
   missing rail support and both rails occupied. Missing independent support
   must not be treated as evidence that a real object is rail geometry.
2. Keep the rule useful: an ordinary rail fragment with both rail-head lines
   elevated relative to the model must still be rejected. Preserve the
   30 x 30 x 10 cm rail-head box controls and ordinary tracker confirmation.
3. Full gate, ride and Set F, without `--allow`: compare with the existing
   seal baseline and the exact starting main source. No lost/delayed STOP
   for labelled obstacles; no added empty-recording STOP episodes/events.
   Inspect frame-level differences, not just aggregates.
4. Replay the whole ride with one continuous detector. Compare low-kind
   episodes and all new STOP frames with starting main. Explicitly inspect
   the previous failed cross-rail correction's region (frames 5709–5717).
   Preserve the original F1a false-alarm reduction if achievable; report any
   trade-off instead of silently changing acceptance.
5. Directed physical scenes must match real object geometry; handcrafted
   low-cluster counterexamples establish only the reference-rule property.
   Verify any instrumentation against a plain run and independently inspect
   raw points / per-frame changes. Include positive controls for zero counts.
6. Run affected tests and the X3 battery where the environment permits.
   Record exact source hashes for uncommitted measurements. This session
   does not claim independent P4 review, release acceptance or a new seal.

Repository freeze workflow asks for commits before runs; commits were not
requested in this session. Protocol, tests and source are therefore retained
as working-tree changes, with this procedural deviation explicit.

## Candidate design (registered before its detector implementation)

Exclude every low cluster's points (including already-weak and advisory
clusters) from the independent rail reference. Keep the existing weak mode;
the old exclusion experiment changed advisory mode at the same time, so its
aggregate result does not isolate exclusion's cost. Measure exclusion + weak
as a diagnostic comparison.

For the repair, require **both** the original and independent reference to
reject the cluster: use their minimum; if either is unavailable, do not
suppress it through F1a. This matters because removing low returns can
*raise* a median by removing its lower bins. Capping the independent line by
the original line prevents newly suppressing a previously accepted cluster.
No cross-rail substitution, no new tolerance and no tuning on a frame ID.
`local_rail_exclude_low` defaults to true; false retains the old unsafe path
only for explicit ablation. Missing independent rails retain ordinary
confirmation, not a newly invented STOP or advisory vote.

## Capped-top B1 follow-up (before second candidate)

During this session main advanced to `a5b0ede` (documentation and R3 reporting;
detector source unchanged from `cefd4c4`). The reconciled backlog links P4's
shipping review at PR #43 / `972d19a`. It identifies a second F1a defect:
plain low-cluster `height_max` is capped by the low-stage input floor.
Reproduce its raised-rail physical scene on the unchanged reference.

Use current-frame heights over each low cluster's footprint, including
returns above the low-stage input floor, below existing `foot_max_top`.
Exclude the **whole footprint**, not just the originally selected low points,
from independent support so that those added upper points cannot reintroduce
fragment self-support. A top from outside the footprint or the ceiling must
not exempt a rail fragment. Add direct controls and the P4 physical scene,
including flat / raised rails, no obstacle and a moving approach. Earlier
candidate gate/replay runs were stopped; their partial outputs are not final
acceptance evidence.

## Original-eligibility refinement (registered before measurement)

The capped-top correction makes the earlier minimum-of-two-references guard
unnecessarily strict: the original reference is an ablation limit, not the
independent safety evidence. Evaluate the following parameter-free refinement
on the captured states first: retain the **original rejection decision on the
original selected top** as an eligibility gate, and require the independent
reference to reject the **full observed footprint top**. This still cannot
newly weaken any cluster accepted by starting main, still excludes all low
footprints from the safety reference, and still protects the P4 upper-body
counterexample. It may keep more of the existing false-alarm reduction where
the independent rail reference is higher than the original one.

Outcome: on all 111 originally rejected clusters in 250 captured states,
both formulations retain exactly the same 66 rejections, row for row. A known
synthetic tuple distinguishes the two formulations (recorded in
`snapshot-audit.json`), so this is a checked negative result. No production
refinement was made; the more conservative minimum-reference rule remains.
