# Independent P4 H1 A-axis miss audit — acceptance fixed before replay

Date: 2026-10-20. Requested checkout: `/home/aiops/resense`, main,
`f56ad5e62d9d051811c804734c7731b6951eae90`.

## Scope and write boundary

Read CLAUDE.md and docs/DETECTOR_FREEZE.md before this protocol. The latter
identifies the R3 40-file seal as current; verify the actual default seal and
hash the current source before and after replay. Do not change detector, tests,
existing evidence, Git index/branches; no commit/push and no G3 access.
Only remote output locations are
`docs/evidence/h1_miss_audit_2026-10-20/` and
`/tmp/opencode/h1-miss-audit/`. Disable Python bytecode writes.

## Fixed input and execution

- Python: `/tmp/opencode/resense-b4-venv/bin/python`.
- Library path: `/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu`.
- `RESENSE_REPO=/home/aiops/resense`, `PYTHONPATH=/home/aiops/resense`,
  `OPENBLAS_CORETYPE=Haswell`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`.
- Judged `docs/evidence/judgement_2026-10-13/scripts/range_test.py`.
- Cache: `/tmp/opencode/r3-h1/baseline/cache/roundT_squareT_pressureGate_squareT`.
- ICP: `/tmp/opencode/r3-h1/baseline/icp_roundT_squareT_pressureGate_squareT.json`.
- Flags: `--obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340`.
- Preserve every evaluator row; visible means full-precision X > 3 and n_obj > 0.
- This injection axis is the detector baseline, not external ground truth.
  No claim of independently established in-gauge placement is permitted.

## Acceptance checks

1. Fresh plain and traced replay on the SAME current source and inputs. Hash
   source, tools, input files, and per-frame injected arrays. Use the same fixed
   previous latency (42 ms when a previous value exists), recording the reason
   and scope, since wall-clock feedback can otherwise alter behavior.
2. Compare EVERY FrameResult field except wall-clock timing, recursively and
   without rounding/tolerance, including exact dtype/shape/bytes for arrays.
   Preserve per-frame raw fingerprints and full compressed results. A failed
   equivalence blocks causal interpretation until explained/corrected.
3. Recompute matching for EVERY visible row using full-precision injection
   coordinates and raw detection distance/center, independently of range hit
   output. Check against evaluator hits, without assuming historical counts.
4. Positive controls: plant a lost hit on a known hit and require the independent
   checker to detect it; mutate a non-timing result field and require the exact
   trace comparator to detect it. Include a timing-only mutation control.
5. For EVERY fresh visible miss retain relevant intermediate snapshots and
   executed code events: candidate/cluster survival, collision-core returns,
   column demotion/hold, axis/height/sparse rules, tracker confirmation/hold and
   final output. Labels must cite actual executed branches and their state,
   never merely infer a branch from a final candidate reason. If insufficient,
   label `unverified` and explain exactly what is missing. Multiple mechanisms
   may be recorded; do not invent a unique root cause from correlation.
6. Inspect raw examples and check geometry/count/distance plausibility. State
   how many frames/rows were checked for each rule. Any negative claim requires
   a positive exercised control or an explicit unverified qualification.
7. Compare exact historical expected miss row sets from existing H1 evidence
   (identify source and visibility convention). Report added/removed rows and
   changes honestly; historical 63/114 is not an acceptance target.
8. Durable deliverables: protocol, reproducible audit script, JSON report,
   compressed raw captures and hashes, README with all contiguous miss
   intervals/counts, checked rules, commands, limitations/blockers.

Wrong-selected-rail-pair/no-rails limitations are covered by the main agent's
separate [h1_rail_limits evidence](../h1_rail_limits_2026-10-20/README.md).
This audit does not adjust the detector to the unverified injection axis.

Publication routing annotation: only the handoff reference above was updated;
the pre-replay acceptance criteria are unchanged. Original production bytes and
their original protocol hash are preserved in VM-only storage, as recorded by
`storage-map.json`; `SHA256SUMS` is the historical production record.
