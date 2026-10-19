# P3 R3 / H1 development protocol

Base: `6be817abf725f9d6836d53866ff38a8cea1253dc`, branch `det/r3-h1`.
Registered before new reproduction runs or detector changes. Existing B4 untracked
results are preserved. L16/S3 are part of the base; the predecessor seal is not
an acceptance oracle for these changed sources. P4 review and P1 reseal are separate.

## Diagnosis first

* Reuse the archived X1 Haswell ICP (not freshly recomputed odometry), the judge's
  unchanged E6 raycast and node replica, and the current node-decoded Set O cache.
* Run E6 (`0.05,0.05,2.6`, base 0.2, A start 150, end 340, d0 230)
  and Set O through frame 790 with/without the unchanged X1 observer. Require
  all non-timing fields equal before attribution; check samples per cause from
  full states, and inspect raw target returns / plots. Preserve source identity.
* Reproduce physical H4 case45 using its archived independent slab caster,
  default config and `column_free_max_top=0`; inspect actual above-cut points.
* Record hypotheses and candidate-specific criteria in a separate diagnosis
  document before modifying any detector algorithm. Keep failed variants.

## Acceptance fixed in advance

R3: E6 first matched STOP >=80 m, held-90% >=60 m; node-path Set O
thin_hanging first matched STOP >=45 m. Report exact new/lost object-matched
STOP rows as well as unrelated false STOPs. Preserve positive controls (A-axis,
C-person and doubleT_obstacle), background Set O, low objects and all existing
STOP rows in the full paired gate. No weakening thresholds in the gate.

H1: new approach must handle the physical tall narrow case45 and returning
hits, retain short-pole positives and avoid the prior dark-continuation excess.
Free-top remains disabled. A diagnosis/proposal alone does not close H1.
Any candidate enabled by default needs the same paired full gate, perturbation
and exact STOP-retention scrutiny as R3. A failing experimental variant stays
separate from a proposed default candidate.

For a suitable candidate run affected tests, the complete regression gate
against `regression_baseline_2026-09-29_shell_off.json` (no overrides/waivers),
paired current-main raw-row comparison, and X3 against the full 1.1.0 reference
and a same-runtime current-main control. Report inherited failures separately.
G3 is excluded. This is author development evidence, not independent P4 review.

All runs explicitly set `RESENSE_REPO`, `PYTHONPATH`, Haswell OpenBLAS,
`OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`; assert NumPy 1.26.4.
Large working artifacts live under `/tmp/opencode/r3-h1/`.
