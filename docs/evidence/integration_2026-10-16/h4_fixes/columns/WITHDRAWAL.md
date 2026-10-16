# Registered H1 shipping withdrawal — author protocol, 16 October 2026

Parent decision under PLAN/BACKLOG H1: ship only at no cost, otherwise DROP.
Candidate 08 is unaccepted: zero dark excess costs A-axis 157 -> 139, other
short-pole/surface updates and an existing under-beam positive. No new column
variant is authorized. This is accepted-only scope selection, not an H4 fix,
acceptance PASS or test waiver.

This protocol and withdrawal expectations are committed **before the config patch**.

## Minimal shipping selection

Set only `cluster.column_free_max_top` from 2.95 to **0.0** in DetectorConfig,
the canonical YAML and its identical ROS mirror. Other parameter values remain;
they are inert behind the master switch. Keep the opt-in algorithm as explicitly
experimental development code, including its known unaccepted tall/dark limits.
H2 structure-cut, r3 axis, E2, P4, docs and the separately authored re-arm code
remain in history/production unchanged. Re-arm is only an experimental-path
improvement here, with no shipping detection gain claimed.

## Tests and preservation

* Move `tests/test_h4_column_evidence.py` byte-for-byte to this folder as
  `withdrawn_acceptance.py.txt`, with apply_patch Move. It is the permanent failed
  acceptance criteria/evidence for a feature excluded from shipping. Its removal
  from default pytest collection does not mean those criteria passed. Verify
  exact bytes, SHA-256 and Git blob against **4c6ea25**. All prior measured reports
  stay immutable; old pinned candidate reconstruction still uses the original
  test path from its original Git commit. The Git history and 47 MB branch bundle
  remain preserved; this work removes no branch or archive.
* Existing free-top algorithm tests explicitly opt in at 2.95 through a named
  fixture/config. Keep their algorithm expectations. The column-specific test
  in test_late_candidates.py likewise explicitly opts in; tracking assertions
  and production are unchanged.
* New test_column_shipping.py checks class/CLI/YAML/ROS defaults and unchanged
  H2/axis settings, exact YAML mirror bytes, a matched physical off/on pole pair,
  and default ordinary-detector/CLI execution with top_is_free forbidden.
  Candidates must have spared=false; spare/provisional histories remain false.

## Required measurements

1. Run the new shipping expectations on the committed pre-config source and retain
   the red failure. Apply the minimal config patch, then run column, tracking,
   re-arm, structure, native and synthetic impacted units in the same immutable
   Linux/Open3D image, zero failures/skips. No host native build or shared venv edit.
2. Run unchanged critical development probes with the same node-decoded input,
   odometry and Linux/native environment. A-axis shipping expectation is the
   sealed **82/177**, not the withdrawn H1 157 gain; C-person must retain
   **82.77 m / 55**. Preserve exact matched frame sets and source/config identity.
3. Replay actual entire ride pieces 1 and 3 through the exact inherited observer
   adapter. Assert effective config disables free-top, install a fail-fast guard
   against any call, and verify all observer records are empty / candidates
   unspared. Expected STOP frames match sealed plain **14 / 2**, with zero-tolerance
   serialized-center matching. This does not alter the artificial mask or evade
   it: the disabled feature must never invoke that observer.
4. Explicit-on historical false cases remain rejected. Preserve the old source
   reconstruction and failed reports, and measure an explicit-on control if needed
   for the revised configuration proof. No claim of repairing tall/dark ambiguity.

## Review boundary

The baseline's inherited tall-object miss remains **OPEN under criterion 8.1**,
not a new regression and not resolved by feature withdrawal. Independent H4 must
review the revised shipping patch against **707ea9c** with the same full gates.
The parent owns the final full gate/re-review and any continuation to main. Author
unit/probe results establish readiness for those steps, not independent clearance.

New measurements and identities will be added under `withdrawal/` without changing
the prior reports. The execution report is `WITHDRAWAL_RESULTS.md`.
