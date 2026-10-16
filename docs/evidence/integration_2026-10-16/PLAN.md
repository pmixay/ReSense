# Integration and branch retirement — registered 16 October 2026

User authorization: integrate the accepted 15–16 October work, obtain green checks,
merge the PR into main, and retire temporary branches after preserving their contents.
Baseline main: `3fdc87957f5d09ff32573eabe6637924b91ea376`.

## Inputs

| Work | Published tip |
|---|---|
| Detector base / inherited column and surface-cut fixes | `final/silent-misses` / `d0d17bb` |
| H1 hardening | `r3/column` / `ccb68c1` |
| H2 physical evidence bar | `h2/cut-bar` / `7380f65` |
| Honest monitored range | `r3/axis` / `972edd2` |
| P1 implementation and measured failed candidates | `p1/start-2026-10-15` / `01e1f66` |
| P2 documentation and lighter presentation | `p2/docs-and-pitch-20261015` / `90a472e` |
| P3 rejected configuration screens and evidence | `p3/range-screen` / `527a76c` |
| P4 H0, G3 registration, X3 and evidence | `p4/eval-start-2026-10-15` / `ab295b1` |

The inherited detector changes and H1/H2 have committed acceptance tests. Their separate
passing gates do not substitute for this combined gate or independent H4 review.

## Acceptance order

1. Integrate feature history on a branch from main. Retain all measured evidence.
2. Keep the published startup queue/freshness behavior in the shipping node: the failed
   S1 runtime candidate is archived rather than enabled. Share the v1 decision implementation;
   failed v2 remains available for offline measurement, not as the runtime default.
3. Fix the actual Docker X3 fixture omission and browser CI failures. Do not suppress failures
   or relax their assertions to obtain green CI.
4. Reproduce exact sealed `707ea9c` and run the combined committed detector in a clean Linux
   Git checkout with native kernels. Full gate against the 29.09 shell-off baseline, no waivers.
   Preserve every output frame, compare against the same-runtime sealed control, and explain
   changed fields (including the intended monitored-range cap).
5. A fresh agent that wrote none of the detector reviews `707ea9c..candidate` after the combined
   gate, including stress/probe evidence. Fix confirmed medium-or-higher findings and repeat
   affected acceptance as necessary. This is the detector's H4 review.
6. Commit version 1.1.0 in all four declarations before the final full gate. Create the new
   manifest only from the passing committed gate. Verify clean LF bytes and synchronized configs.
7. Green complete CI on the PR; merge normally, preserving the integration history. No release
   tag is part of this request; tag publication remains the separate E1 release operation.

## Preservation and cleanup

Before deleting any branch, inventory original local/remote heads and check every associated
worktree for uncommitted or unfamiliar files. Preserve retired heads (including rejected
`r3/axis-B-trial` and intermediate local P1/P4 work) in a verified incremental Git bundle,
with exact refs, prerequisites, SHA-256 and restore instructions committed outside detector scope.
The existing main commit is an explicit bundle prerequisite. Confirm the archive is reachable
from merged main before removing refs/worktrees. Preserve dataset/cache/raw-run directories.
Unrelated detached worktrees are outside this cleanup.

O1 remains pending actual dispatch/reply. G3 stays a pre-registered future final-seal batch;
no held-out cases are run or tuned during integration.
