# H1 follow-up: absolute axis anchor and far misses

Author lane P3; starting source `f47a090` / measured detector `fd89712`.
This follow-up preserves all previous H1 evidence and its OPEN verdict.

## Questions registered before implementation

1. Which actual collision-core predicate rejects each of the nine standing far
   misses, and the moving opaque-body scans above 100 m? Trace the executed
   predicate and compare each traced FrameResult with an equal-input plain run.
2. Can current observed paired rails supply the absolute anchor missing from the
   local-minus-near boundary guard? A constant coordinate-model displacement must
   not cancel. No tunnel symmetry, sensor centring, or known fixture axis may be
   supplied to the production detector. Missing/ambiguous support must abstain.
3. Does a geometrically justified far core improve moving-body coverage while
   preserving critical positives and rejecting outside objects?

## Fixed checks

* Reuse all 32 standing physical cases, distances 37/67/109/137 m, both sides,
  three opaque tops and absorbing continuation; inspect actual object returns.
* Outside controls include both signs of 0.6 m model displacement, the previous
  +/-0.3 m controls, near-edge and wider outside bodies. Extend with yaw error,
  asymmetric tunnels, missing/false rail support and coherent boundary movement.
  A positive in-gauge control must exercise the same comparison/tracing tools.
* Moving opaque bodies: 155 -> 34 m, 22 m/s, 10 Hz, y=+/-0.68 m. Report first,
  matched row sets, gaps, and pooled held90 separately. A 100 m objective is a
  development target, not a verified braking requirement.
* Preserve ordinary confirmation, current-frame support, shape/height validity,
  doubtful/ego guards. The retired free-top feature remains off.
* Independent calculations from raw rail/wall/target points must check any
  claimed anchor/interval and every claimed eliminated false-positive case.
* Affected tests, full gate and critical Falcon/A-axis/C-person/R3 probes are
  required for a retained detector change; X3 follows a passing gate. Keep any
  failures and rejected candidates. No G3 or new judging run.

Changes in geometric scope or tests must be recorded before measuring acceptance.
No percentage completion or overall H1 closure is inferred from a bounded pass.
