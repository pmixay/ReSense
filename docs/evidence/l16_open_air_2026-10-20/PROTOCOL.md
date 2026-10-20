# L16/S3 A1 repair and acceptance — registered 20 October 2026

Base: main `8c2bf51a2e2a2eece7d844da4c42eabbd8b18578`; isolated branch
`fix/l16-open-air`, checkout `/tmp/opencode/l16-open-air-checkout`.
The user's request authorizes the complete L16/S3 follow-up, integration and push.
Unrelated ongoing F1a changes in the shared checkout are not this candidate.

## Defect and proposed bounded repair

The delivered 19.10 L16 directional recovery and S3 search budget remain present.
P4 A1 is a distinct new regression: full-revolution open-air returns mostly below
the sensor produce a false signed-forward -Z cue. That cue blocks observation of
the valid configured mount and remains in conflict after fallback at 400 frames.

Register tests before the repair. A unique >98% one-sided coordinate is necessary
but insufficient for a directional FOV. Require the existing <=16,384-point sample
to occupy a forward cone (at least 98% within 80 degrees, P4's proposed guard)
before returning either directional constraint. Preserve the existing channel-axis
evidence, bed/rail checks, votes, normal readiness, real-conflict behavior, replay
defaults, coordinate arithmetic and <=60,000-point search budget. No blanket
timeout conflict clearing and no suppression of real obstacle STOPs.

## Registered checks

1. New ground-half-space negative controls in all 24 proper rotations, with 0/1%
   points above; reproduce the original 450-frame A1 with/without ring, stationary
   and open-to-tunnel startup. Existing directional-FOV rotations are the positive
   control. Run new tests on pre-fix source and affected tests on committed repair.
2. Raw analytic open-air/tunnel paired runs against the pre-fix main, including a
   real-size box/person-positive scene. Inspect XYZ/state examples; independently
   reconstruct decisions and trace the executed branch. An accepted traced case
   must equal its plain case outside wall-clock timing.
3. T1: raw-CDR first 10 frames of six Pandar recordings, Set O, first ride split,
   Falcon and three marked bags (12 starts /120 frames). Independently decode raw
   XYZ views, apply the jury runner's configured vehicle-axis matrix, compare
   counts/cues, and retain hashes, fractions, readiness and actual remap provenance.
   Do not call a legitimate Falcon remap an A1 failure. Known synthetic A1 is the
   exposure-check positive control. Acquire the first ride split if absent.
4. Paired recorded startup prefixes (all 24 rotations, first 32 frames) and full
   representative Falcon cases 0/4/5/12, plus Pandar empty/positive controls. Compare
   source-bound raw STOP/detection rows; retain every mismatch, not only totals.
5. Complete default regression gate, no waivers, and X3 on committed source; compare
   raw outputs against the exact pre-fix main. Include complete ordinary Falcon and
   affected calibration/replay/health/native tests. If integration brings detector
   changes, revalidate the final combined source, not only the earlier candidate.
6. Reopen raw archives and verify hashes; independently recompute principal results
   and exercise comparators with planted losses. Update backlog with delivered S3,
   resolved A1 and T1 evidence. Keep unsupported general/physical-mount assumptions
   explicit rather than claiming gravity from field shape. Final-bundle independent
   P4 review/reseal and unrelated H1/F1a/R3 issues are separate release requirements.

Runtime: NumPy 1.26.4, native kernels, explicit `RESENSE_REPO` and `PYTHONPATH`,
`OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`.
No G3 data, judging, release, or seal-pointer change is part of these runs.
