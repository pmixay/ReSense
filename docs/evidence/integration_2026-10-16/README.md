# Integration checkpoint — 15–16 October 2026

> **Purpose:** selected shipping scope, preserved acceptance history and the checks still needed
> before version/seal/main completion. **Owner:** P1 · **Language:** EN
> **Verified:** 16 October, measured/reviewed source `c9aea87cb5322092070158cd8987115ee44833c9`
> (withdrawal defaults `795a243`); committed H3, withdrawal and independent H4 reports below.
> **Status:** replacement H3/probes/H4 complete; parent-owned H5/H6 PENDING.

**H1/free-top is dropped under the original ship-at-no-cost-or-drop plan.** H2's physical
structure-cut bar, the monitored-range cap, shared C1 v1, E2, P4 tooling/evidence and P2
documentation/pitch preparation remain selected. The published release is still **v1.0.0**;
the planned **1.1.0 is unreleased**, with no new seal or J1 score claimed here.

## Selected scope

| Item | Measured outcome / current selection |
|---|---|
| S1 runtime | **FAIL, removed from shipping.** Original-bag Docker acceptance failed, including the verified Linux-volume follow-up. Node/launch keep published queue depth **40**, startup step **0**, startup lag **20 s**, original continuity/drop accounting and freshness; no one-period freshness allowance or S1 Python queue cap |
| C1 | Shared **v1**, strict raw flag/health validation and additive `decision_policy` / `caution_reason` retained. Runtime v2 is rejected; pure offline v2 remains **experimental, FAIL**: **30.46% CAUTION** versus ≤25%, **19 lost labelled object-frame alerts**. Those are frame-level retained-alert counts, not object-matched recall |
| E2 | **Local offline PASS**: clean source/native/ROS rebuild from the loaded E2-compatible image; first build **18.609 s**, later integrated rebuild **19.156 s**. New release-workflow check is implemented but **untagged/unexecuted on a new release** |
| H0 / P4 | **PASS** on exact v1.0.0 control `707ea9c`: **208/208 non-latency gate rows identical**. Windows-local reproduction and the later Linux H3 control are separately identified in their reports |
| X3 | Reusable battery and **v1.0.0 baseline only**: **40/40 cases, 29,765 frames**, all requested historical judge counts reproduced. Baseline status is MEASURED, not candidate PASS; selected-scope/1.1.0 baseline remains pending |
| G3 | **Specification only**; no held-out execution or detection result. No generalization/held-out gain is credited |
| H1 / original column free-top | **DROP.** Original nominal gates passed, but H4 confirmed exact inherited dark excess **9 + 5 STOP frames**, a returning-hit gap and an inherited tall-object miss. Author attempt 08 removed dark excess at a positive cost: A-axis **157 → 139/177**, with other pole/surface/under-beam losses. It is rejected |
| H1 shipping configuration | `cluster.column_free_max_top=0` in the class default, canonical YAML and ROS mirror (`795a243`). Explicit positive opt-in remains unaccepted experimental code. [Measured withdrawal](h4_fixes/columns/WITHDRAWAL_RESULTS.md) at `c9aea87`: **A-axis 82/177**, exact sealed scored frame set; complete dark pieces 1/3 **14/2 STOP frames**, zero extra/lost STOPs and zero feature/observer calls. The inherited High tall miss stays **OPEN, criterion 8.1** |
| H2 | Structure cut retained with **1.3 m** residual, **8-voxel** bar and one full physical azimuth step (**0.1°**, two resolved columns). Separate candidate: mast false matches **2 → 0**. Selected-scope withdrawal probe reconfirms C person **82.77 m / 55 STOP frames** (sealed **73.94 m / 49**, six added matched frames, none lost); fresh independent H4 checks its physical boundaries and paired clustering route |
| Axis range cap | `axis_wall_drift=0.8 m` retained: limits `monitored_range` / `clear_distance`, without moving the axis/corridor. It is not a curve-axis or obstacle-recall fix |
| P2 D1 / PT1 | Documentation corrections and lighter named deck delivered. Slides/pitch numbers remain explicitly **v1.0.0 / dated history** until J1; final range chart, approval, release-matched video and rehearsals remain open |
| O1 | Message **prepared, not sent**; no organizer reply or permission to count post-submission changes |

## Preserved measured history

These reports retain their measured commits, source hashes, data and verdicts. A later scope
selection does not convert a blocked experiment into a passing one.

| Record | What it establishes |
|---|---|
| [Original combined H3](h3/README.md) | **PASS at `f8c088d`**, with H1 enabled: 208/208 non-latency rows identical; 18,329 raw/serialized frames compared; intended range-cap changes explained. This is not the post-withdrawal H3 |
| [Independent H4 safety](h4_safety/README.md), [blocked findings](h4_safety/BLOCKED.md) | **BLOCKED** on that original combined core: inherited tall miss, returning-hit gap, exact dark excess 9+5. The wider-mask 9+10 replay is a separate experiment |
| [Independent H4 correctness](h4_correctness/README.md) | **PASS for its registered original scope**; does not override the safety verdict or cover the later withdrawal automatically |
| [Re-arm author record](h4_fixes/rearm/README.md) | Separately measured experimental-path author correction; not independent clearance or a shipping detection gain with free-top off |
| [Rejected column author work](h4_fixes/columns/README.md) | Attempt 08, exact masks/positive costs and restored-source failures retained as **BLOCKED** |
| [Withdrawal protocol](h4_fixes/columns/WITHDRAWAL.md) | Registered before the config patch; disables the master switch, preserves failed acceptance bytes and specifies new probes/dark checks. It does not claim a fix of tall/dark ambiguity |
| [Runtime selection](runtime_selection.md) | Exact published queue/freshness behavior plus shared v1, with runtime v2 rejection; no S1 speed claim |

## Current acceptance ledger — committed results

Replacement H3, author withdrawal probes/dark controls and fresh independent H4 all identify
**`c9aea87cb5322092070158cd8987115ee44833c9`**, compared against sealed
**`707ea9cda051369326fb9407c42488c1033dad76`**. Reports were committed as **`5282d6f`**,
**`829b243`** and **`70072f1`**, respectively. The measured source remains `c9aea87`;
these later publication commits do not identify a different measured detector.

| Step | Actual state / remaining acceptance |
|---|---|
| H3 replacement, selected scope | **DONE — PASS**, exit 0: [selected H3](h3_selected/README.md), published `5282d6f`. Clean Linux/native source; **208/208 non-latency rows identical**, same **146 gated rows passed**, no overrides/waivers. **18,329/18,329 raw/serialized frames** aligned against the same-runtime sealed control; all differences explained by the range cap/additive fields and registered timing telemetry. No unexplained change or gated improvement |
| Withdrawal critical probes / dark | **DONE — author protocol satisfied:** [withdrawal results](h4_fixes/columns/WITHDRAWAL_RESULTS.md), published `829b243`. **260 passed**, **6 existing external-data deselections**, zero failures/errors/skips. A-axis **82/177**; C-person **82.77 m / 55**. Entire pieces 1/3, **1,409 frames each**, exact inherited adapter: **14/2 STOP frames**, exact detection/warning descriptors, zero extra/lost STOPs, zero free-top/observer calls |
| H4 revised-scope independent review | **DONE — ACCEPTED for revised difference `707ea9c..c9aea87`:** [fresh independent H4](h4_selected/README.md), published `70072f1`. **306 passed**, no failures/skips/deselections; **36 H2 angular/voxel boundary cases** and **1,344 paired Tracker updates per source**. No supported **NEW medium-or-higher** finding remains. **Inherited High tall miss OPEN 8.1**; original H4 safety **BLOCKED** unchanged |
| H5 version / final gate / seal | **PENDING:** parent commits all four 1.1.0 declarations, runs final committed gate, creates/verifies actual manifest and updates the freeze documentation. No seal PASS yet |
| H6 main / CI | **PENDING:** parent supplies complete CI and normal main-merge commit/PR. E1 release tag/archive verification is a separate later operation |
| Branch retirement | [Verified archive](branch_archive/README.md) exists (20 refs, 47,312,366-byte bundle, restore proof). **Deletion not completed here**; parent records final-main ancestry/restore verification and refreshed head/worktree inventory, including preservation of ignored web evidence |
| J1 / PT1 | **PENDING** on a shipped new seal. Current independent score remains **66/100, v1.0.0, 13.10** |

## Stable original handoffs

GitHub publication links use original commit IDs so retiring branches does not retarget them.
The local evidence remains accessible through the [evidence index](../README.md).

| Work | Original publication |
|---|---|
| P1 | [checkpoint at `01e1f669d8b558755cf0c8ebd680c7641d59becf`](https://github.com/pmixay/ReSense/blob/01e1f669d8b558755cf0c8ebd680c7641d59becf/docs/evidence/p1_start_2026-10-15/README.md) |
| P2 | [D1/PT1 at `90a472e31f225efc7689ce74db6c36c6e4d7fc5c`](https://github.com/pmixay/ReSense/blob/90a472e31f225efc7689ce74db6c36c6e4d7fc5c/docs/evidence/p2_2026-10-15/README.md) |
| P3 | [checkpoint at `527a76c4139add1862b7eaaf954129a73d65964f`](https://github.com/pmixay/ReSense/blob/527a76c4139add1862b7eaaf954129a73d65964f/docs/evidence/p3_start_2026-10-15/README.md) |
| P4 | [H0/X3 at `ab295b144c67d9ea5a63ef9fa75fd7d72346073a`](https://github.com/pmixay/ReSense/blob/ab295b144c67d9ea5a63ef9fa75fd7d72346073a/docs/evidence/p4_start_2026-10-15/README.md) |
| H1 | [historical candidate at `ccb68c106f562a1768636685f4513c09336dbec6`](https://github.com/pmixay/ReSense/blob/ccb68c106f562a1768636685f4513c09336dbec6/docs/evidence/column_hardening_2026-10-15/README.md) |
| H2 | [separate candidate at `7380f650829fd1c64a9b894afcf2868b6ffc2434`](https://github.com/pmixay/ReSense/blob/7380f650829fd1c64a9b894afcf2868b6ffc2434/docs/evidence/structure_cut_bar_2026-10-15/README.md) |

**Documentation reconciliation, 16 October:** the P1/P4 handoff crosslinks and the original
calendar link are pinned to their original SHAs. P4's [intake table](../p4_start_2026-10-15/README.md#shared-data-paths)
has an explicit dated alias correction: **B = roundT_doubleT**,
**C = roundT_pressureGate_roundT**, matching the judge's `run_range_matrix.sh`.
Full recording names, measured data and historical verdicts are preserved.
Parent follow-up: replace H5/H6 PENDING only with actual version-bumped gate/seal/CI/main
receipts; record branch retirement, O1 dispatch/reply and final release links when completed.
