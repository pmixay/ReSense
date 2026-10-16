# Integration checkpoint — 15–16 October 2026

**Передача 16.10:** по указанию пользователя работа этой сессии остановлена;
[P4_HANDOFF.md](P4_HANDOFF.md) задаёт текущий этап, очередность X3/X1/J1/G3,
доступ к данным и оставшиеся действия P1 после отдельной команды.

> **Purpose:** selected shipping scope, preserved acceptance history and the checks still needed
> before version/seal/main completion. **Owner:** P1 · **Language:** EN
> **Verified:** 16 October, reviewed scope `c9aea87cb5322092070158cd8987115ee44833c9`
> (withdrawal defaults `795a243`); final measured 1.1.0 `52115654417a660669b8dddfce447692c1d782cc`.
> **Status:** replacement H3/probes/H4 and H5 complete; current 1.1.0 seal 16.10;
> parent-owned H6/CI/main and E1 PENDING.

**H1/free-top is dropped under the original ship-at-no-cost-or-drop plan.** H2's physical
structure-cut bar, the monitored-range cap, shared C1 v1, E2, P4 tooling/evidence and P2
documentation/pitch preparation remain selected. **Current package 1.1.0 is sealed 16.10**;
the published tag/archive remains **v1.0.0**. Version 1.1.0 is **unreleased**: no E1 tag/archive
or new J1 score is claimed.

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

## Current seal — H5 DONE, 16 October

[H5 final gate and seal](h5/README.md) authenticates all four committed version declarations
at **1.1.0**, the unchanged numerical core/config relative to independent H4's `c9aea87`, and
the final full gate: **PASS, exit 0**, **208/208 non-latency rows identical**, same **146 gated
rows passed**, no overrides/waivers. All **18,329 raw/serialized frames** have **zero non-latency
changes** from the reviewed selection, outside the registered timing telemetry.

| Identity / proof | Actual value |
|---|---|
| Measured final commit | `52115654417a660669b8dddfce447692c1d782cc` |
| Evidence/source commit used to create seal | `21e1d6195eda438056fb51c3bab886e420d19ee2` |
| Manifest | [`detector_freeze_2026-10-16_1.1.0.json`](../detector_freeze_2026-10-16_1.1.0.json) |
| Frozen source | **36 files**, digest `db3f588df59184ad703436996f72bd94a91eca91dfcfe4a02655fcdd4397d751` |
| Seal publication commit | `d6319c237213743897c661990c2c78adfa7b4796` |
| Committed-seal proof publication | `ec81e78a0de835fde321a2d6950f25e2fb1e2439` |
| Clean LF Linux verification | **PASS before and after native rebuild** of committed seal `d6319c2`; [completion](h5/seal_verify/completion.json), [before](h5/seal_verify/verify_before_native.txt), [after](h5/seal_verify/verify_after_native_or_create.txt) |

These are explicit-new-manifest checks; default-pointer/freeze-overview integration belongs to
the parent. The current seal does not close inherited **High 8.1**, publish a release, or provide
a new independent judgement. H6 and E1 remain pending.

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
| H5 version / final gate / seal | **DONE — PASS:** [H5](h5/README.md), measured `5211565`, all four declarations 1.1.0 before final gate; 208/208 non-latency rows identical, same 146 gated rows passed, all 18,329 frames unchanged vs reviewed `c9aea87` outside registered timing. Current [16.10 manifest](../detector_freeze_2026-10-16_1.1.0.json), source/evidence `21e1d61`, seal `d6319c2`, clean-LF before/after-native proof `ec81e78` |
| H6 main / CI | **PENDING:** parent supplies complete CI and normal main-merge commit/PR. E1 release tag/archive verification is a separate later operation |
| Branch retirement | [Verified archive](branch_archive/README.md) exists (20 refs, 47,312,366-byte bundle, restore proof). Web raw preservation is committed at **`f29e212`** on `integration/web-ci-20261016`: [immutable receipt](https://github.com/pmixay/ReSense/blob/f29e212abe933dcfa76ee9b0ea4afb9cd95bf810/docs/evidence/integration_2026-10-16/web_ci/retirement/README.md). At this reconciliation it is not an ancestor of integration HEAD or local main. Final-main inclusion/restore, refreshed refs/worktrees and actual retirement receipt remain parent-owned H6 follow-up |
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
Parent follow-up: H5's actual version-bumped gate/seal/proof are linked above; finish the
default-pointer/freeze-overview integration and replace **H6 PENDING** only with actual CI/main
receipts. Resolve the web retirement receipt on final main after the parent merge; record
branch retirement, O1 dispatch/reply and E1 release links when completed.
