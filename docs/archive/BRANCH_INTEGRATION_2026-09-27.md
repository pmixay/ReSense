# Branch integration — 27 September 2026

The user requested integration into `claude/nifty-pascal-lzgl78` and removal of completed work
branches. `main`, the detector quality hold and the prohibition on release publication remain
unchanged.

## Preserved work

| Source branch | Retained tip | Integration |
|---|---|---|
| `claude/p1-p2-completion-20260926` | `9540d66` | Full fast-forward integration, followed by reviewed fixes below. |
| `work/association-quality-20260926` | `f76ed30` | A1 history retained; rejected detector source remains disabled. |
| `work/detector-quality-20260926` | `9f00c1f` | D1 history retained; rejected detector source remains disabled. |
| `work/monitoring-quality-20260926` | `eb4e082` locally; `25ad3dd` remotely | M2 history retained; unaccepted detector source remains disabled. |
| `work/trust-quality-20260926` | `810966e` | T1 and its M2 ancestry retained; rejected detector source remains disabled. |

Accepted evidence and runtime fixes from the experimental branches were already integrated.
Merge `68338b9` retains their original commits as ancestors using Git's `ours` strategy. Its
tree is byte-identical to parent `5b6c96f`: `a4c3f2746b717818a566425eefc1fb16a5416dc1`.
Every listed local and remote tip is an ancestor. The retained histories allow branch-reference
deletion without losing those commits or applying failed candidates.

Two original M2 metadata files were additionally recovered for direct access:

- [Implementation plan](../evidence/results/quality_monitoring_M2_implementation_2026-09-26.json)
- [Fixed placement plan](../evidence/results/quality_monitoring_M2_novel_plan_2026-09-26.json.gz)

The placement plan is compressed without changing its original bytes (uncompressed SHA-256
`00f3eb584ef965cc99203a4316eef9e4f21ee78574d123bcef56ee2b95ff053a`). Its historical metric-count
wording is governed by the existing [199-row / 146-enforced clarification](../evidence/results/quality_cycle_2026-09-26_clarifications.json).

## Merge corrections

- Keep the member's startup cadence change: retain observed input-period frames during the
  initial backlog, then return to the configured live catch-up behavior. Source-age checks and
  STOP priority remain active. The default 1,000-message cold prefetch limitation stays open;
  passing original-bag checks use explicit ten-message read-ahead.
- Run the viewer and cold-bag CI checks on the retained working branch and `main`; remove their
  dependency on the deleted P1/P2 branch name.
- Launch the viewer's bag-driven node in replay mode and require an actually current status
  after startup/recovery. The probe decodes CDR and checks source, residence and transport age;
  stale topic traffic alone cannot pass.
- Invalidate a previous live result immediately on reconnect or connection error. Retain STOP
  and mark its distance as last known. The regression was reproduced before the fix.
- Correct an unsupported clearance guarantee in the presentation and rebuild its public PPTX
  and PDF. Preserve historical cold-run failures and separate the passing bounded-prefetch
  procedure from the failing default setup.

## Validation and limits

Local validation covers **715 passing tests plus six subtests**. The combined suite passes
714 tests and deselects one because its default cache path is absent; that remaining test
passes separately with `RESENSE_RIDE_CACHE` set to the existing recording cache. There are no
skipped or unrun cases after that targeted check. Lint, diff and shell checks pass.
[Validation receipt](../evidence/results/branch_integration_2026-09-27/validation.json),
[raw test output](../evidence/results/branch_integration_2026-09-27/pytest.log.gz),
[real-data check](../evidence/results/branch_integration_2026-09-27/realdata_pytest.log.gz), and
[history-preservation receipt](../evidence/results/branch_integration_2026-09-27/history_merge_receipt.json)
record the tested source and every preserved branch tip.

The baseline detector's 27-file integrity seal and parameter synchronization pass. There are no
changes to `resense/`, `configs/`, `native/` or the copied ROS detector configuration relative
to `c45626f`. This integration changes the node, viewer, validation harness and documentation.
The P1 cold clear check retains its historical allowance of two alarm frames; it does not waive
the separate zero-alarm quality criterion.

Final CI and branch cleanup status are recorded in [PR #12](https://github.com/pmixay/ReSense/pull/12).
The earlier `d480b13` image receipt remains dated evidence and does not cover the merged node.
The current criteria judgement is in [`SCORECARD.md`](../SCORECARD.md). Final detector acceptance and release remain
on hold; no merge into `main` or release publication is part of this task.
