# H1 trajectory / completion follow-up

Starting tree: `0f02b28`, incorporating `origin/main` `0acb18c` and the retained
H1 candidate E. The automatic merge passes 252 affected tests. The user's push
authorization is conditional on actually closing H1 without blockers.

## Independent reference work, registered before measurements

1. Diagnose the rejected direct registration, particularly overlap asymmetry,
   repetitive tunnel geometry, seed capture and sparse far normals. Preserve the
   previous 72 failed checks and their exact thresholds.
2. Test overlap-restricted, multi-resolution generalized ICP and symmetric
   registration on the same fixed A/C frame pairs. Keep point clouds, source
   hashes and all seeds. Never use detector axis/floor/candidates as reference
   input. Per-point timing compensation must be explicit and checked.
3. Check identity, known nonzero transforms with partial overlap, perturbation
   capture, withheld raw geometry, reverse closure and method/seed agreement.
   Existing acceptance limits remain 0.10 m projection/translation, 0.05 degree
   reverse rotation and 0.70 common-region fitness. A consistent reconstruction
   is not automatically an absolute survey: rail identification, registration
   observability and cumulative uncertainty also require evidence.
4. If long direct matches are underconstrained, attempt local scan-to-map and
   multi-view pose constraints, checked against separate shorter chains and
   raw near/far rail evidence. Use clear abstention outside validated support.
5. Organizer markers can supply independent obstacle geometry and visibility,
   not an assumed rail axis or stationary-world landmarks. Preserve sparse,
   off-sensor-range and moving-injection rows rather than crediting them as
   guaranteed real obstacle detection.

## Detector and release work

Trace actual remaining misses on the merged source; plain and instrumented runs
must match outside wall-clock telemetry before attribution is used. Register
changes before implementation, preserve ordinary confirmation and collision
proof boundaries, repeat physical controls and the complete original gate/X3,
Falcon and critical A/C/cable positives. No G3 input or execution.

H1 closure requires evidence for the remaining axis/column/range failures, no
unresolved acceptance regressions, and independently checked results. A bounded
component improvement or successful reference subset does not close the task.
Publish the exact source/evidence and remaining limits. Push/merge to remote main
only after those conditions are actually met; fetch again and resolve conflicts
without dropping remote work.
