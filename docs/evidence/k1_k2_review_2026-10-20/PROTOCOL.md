# K1/K2: independent review of the measured v5c package

> **Purpose:** review the existing candidate and produce an explicit enablement recommendation and handoff.
> **Audience:** P3, P4, captain · **Reviewer:** new OpenCode session (not a v5c author)
> **Date:** 2026-10-20 · **Starting main:** `f56ad5e6`
> **Scope:** evidence/code review, not a new detector candidate or a new real-data acceptance run.

## Order and boundaries

1. Read the current plan, freeze contract, original K1/K2 protocol and reviews, P4 package, v5c measurements
   and `PROPOSAL_r3.md`. Preserve the original criteria and measured failures.
2. Recompute the existing gate/X3 verdicts and object losses from the committed reports/per-frame outputs.
   Check self-comparison and planted-loss controls; inspect retained point-cloud pictures and concrete rows.
3. Review the proposed Falcon scorer, including frame alignment, first-STOP semantics and per-frame retention.
   A gain in total detections is not proof that the original detections were retained.
4. Check current-source defaults/configuration synchronization/freeze and existing K1/K2-related tests.
   Use isolated Python 3.12, numpy 1.26.4, scipy 1.13.1, sklearn 1.5.2 with
   `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=<checkout> PYTHONPATH=<checkout>`.
5. Probe the reviewed missing-observation/range-cap path with deterministic synthetic inputs and positive controls.
   Report a synthetic finding as synthetic; do not present it as exposure on recordings.
6. Publish a review verdict and a P3/P4/P1 handoff. Reconcile only the K1/K2 backlog statements contradicted by
   the committed measurement. Any revised criterion remains a proposal until the captain decides.

The latest P4 proposal explicitly assigns detector changes to P3 (`../k2_v5c_2026-10-20/PROPOSAL_r3.md`, header).
The current plan also prohibits evaluation sessions from changing detector code (`../../BACKLOG.md` §1;
`../../../CLAUDE.md`). This session takes the fresh-reviewer step. If a production repair is required, it is handed
to P3; the reviewer cannot also author the repair and independently accept it. Switch-on and final reseal are P1's.

Both K1/K2 stay at the existing off defaults while acceptance is unresolved. G3 is outside this review.
The historical v5c source is `8c2bf51`; main has later F1a/L16/R3 changes, so old numbers cannot be relabelled
as measurements of `f56ad5e6`. Local `/data` is absent; committed detector outputs are available for re-scoring.
No new candidate values or data-dependent thresholds are selected here.
