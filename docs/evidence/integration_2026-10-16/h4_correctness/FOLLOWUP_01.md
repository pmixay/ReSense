# Registered harness corrections and investigation

Preserve every `run-002` output and the original `independent_checks.py`.

- `boundaries` completed computation but JSON rejected `numpy.bool_`; serialize
  through the existing `freeze` function and retain the actual case results.
  No expected boundary or geometry changes.
- The health algebra fixture had 3,000 returns, below the **unchanged default
  20,000** minimum (`health.py:163`). Its range was correctly faulted to zero.
  Use 24,000 returns with the same angular coverage, unchanged default config,
  same 3,024 algebra combinations and separate hard-fault check. This corrects
  the input precondition rather than changing the health oracle or threshold.
- The tracker recovery fixture supplied only eight hits, but the unchanged
  default `zone_window` is **10** (`config.py:391`), not five. Two column hits
  correctly held the track advisory. Extend the repeated-spare tail to 13 hits;
  retain its early expected column hold and check eventual release after the
  actual configured history evicts the old column hits. Exhaustive spare and
  actual-Track clear-cap predicates are unchanged and rerun for recorded counts.

Only these affected checks are rerun in `run-003` against the original source
volume/image. Any further oracle failure is preserved and investigated anew.
