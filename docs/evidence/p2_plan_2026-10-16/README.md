# P2 planning review — 16 October 2026

**Deliverable:** [Role 2 execution plan](../../archive/ROLE_2_PLAN.md), branch `role-2`.
This records repository/source review and integrity checks, not implementation completion
or a new detector evaluation.

## Repository intake

Actual repository: `/home/pichotiner/ReSense/ReSense` (the parent directory is not Git).
Ran `git pull --ff-only` on `p2/docs-and-pitch-20261015`: already up to date, then
`git fetch origin --prune`. Inspected all fetched branch tips and the integration history.
Created `role-2` from **`b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1`**, which includes the
earlier P2 work and selected 1.1.0 acceptance. No `role-2` remote existed at intake.
The two untracked root PNG files were present before the review and preserved.

The tracked-tree inventory contained **4,660 files**: 3,949 under `docs/`, 41 GitBook,
329 webapp, 28 web, 112 scripts, 137 tests, 26 core-library, 11 ROS and the remaining
configuration/native/build/CI files. Reviewed repository structure, runtime and consumer
contracts, test/build entry points, current evidence and participant handoffs. This was a
planning-oriented cross-repository review, not a line-by-line audit of every archived raw
artifact or a rerun of every test/recording.

## Source register

### All files in `docs/organizers/`

| Source | Use in the plan |
|---|---|
| [Technical specification PDF](../../organizers/technical_specification_case05.pdf) and [text](../../organizers/technical_specification_case05.txt) | Checked original PDF/text: §3 runtime, §4 demo chain, §5 docs/video, §7 delivery and all eight §8 criteria |
| [Case README](../../organizers/README_organizers.md) | Product/roles and 29.09 / 23.10 dates |
| [Q&A summary](../../organizers/QA_session.md) and [full machine transcript](../../organizers/QA_session_transcript_ru.md) | Envelope, cables, range/sightlines, 10 Hz, no odometry, offline operation, unknown test data, demo and deadline statements |
| [Written answers](../../organizers/answers.md) | Rail-head reference, approximate synthetic placement, bed negative control, both topic/frame pairs, no stand access/internet, O1 pending |
| [Mount/switch answers](../../organizers/mount_and_switch_qa.md) | Variable/provided mounts, centreline/1075 mm, switch-state caveat |
| [Stand software](../../organizers/test_stand_software.md) | i7-9700E 8-core target, CPU-only choice, stand-in benchmark |

Organizer quotations are distinguished from team interpretations; later written clarification
governs the bed object. Template constraints are recorded in PRESENTATION and the previous P2
build review. Sensor facts were cross-checked with the maintained SENSOR documentation; the
separate long sensor manual was not treated as a new organizer requirement.

### Team plans and accepted handoffs

| Snapshot | Source / consequence |
|---|---|
| `main` `3fdc87957f5d09ff32573eabe6637924b91ea376` | Original backlog and 13.10 assessment; not the latest integrated implementation |
| P1 `01e1f669d8b558755cf0c8ebd680c7641d59becf` | [Handoff](../p1_start_2026-10-15/README.md): O1 pending, S1 FAIL, C1 v2 FAIL, E2 local PASS |
| P2 `90a472e31f225efc7689ce74db6c36c6e4d7fc5c` | [D1/PT1 evidence](../p2_2026-10-15/README.md): docs and slide cuts done; dependencies open |
| P3 `527a76c4139add1862b7eaaf954129a73d65964f` | [Handoff](../p3_start_2026-10-15/README.md): H1/H2 original gates; five R1/R2 screens rejected; X1 before more tuning |
| P4 `ab295b144c67d9ea5a63ef9fa75fd7d72346073a` | [Handoff](../p4_start_2026-10-15/README.md): H0 and 40-case v1 X3 baseline; G3 registration only |
| Integration `b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1` | [Plan](../integration_2026-10-16/PLAN.md), [ledger](../integration_2026-10-16/README.md), [P4 handoff](../integration_2026-10-16/P4_HANDOFF.md): H1 withdrawal supersedes early gain; H2/range cap retained; H5 done, H6/E1 pending |
| Active P4 `058a45193a6d68d8e8e5d9b85ca4ac91817de338` | [New protocol at immutable SHA](https://github.com/pmixay/ReSense/blob/058a45193a6d68d8e8e5d9b85ca4ac91817de338/docs/evidence/p4_eval_1.1.0_2026-10-16/PROTOCOL.md): Linux control → X3 → X1 → J1 prep, final release J1 later; G3 untouched |

Also reviewed PLAN, CAPTAIN ownership/rules, BACKLOG cards and calendar, REQUIREMENTS_MAP,
SCORECARD and the actual [13.10 scores/deductions](../judgement_2026-10-13/scores.json),
PRESENTATION, video documentation, P2_STATUS/P2_REVIEW/DEMO_HANDOFF, C1 CONTRACT,
runtime-selection evidence, archive preservation receipts and documentation/test indexes.

## Code and artifact findings that drive the plan

| Finding at the base SHA | Planned resolution |
|---|---|
| Node serializes `decision_policy` / `caution_reason`; grep finds no reason consumer in web JS/TS/HTML | P2-02 validates and renders additive fields, with legacy/unknown cases |
| `web/index.html:decisionOf` has a local decision fallback and established freshness/latch checks; `web/assets/result-format.js` validates incoming frames | Extend existing boundaries and prove parity; retain STOP/FAULT handling |
| `webapp/frontend/src/api/rosbridge.ts` casts parsed JSON, `pages/Live/feed.ts:isMessage` checks only a string decision; optional reason types absent | Trace and strengthen consumer validation as part of C1, with malformed payload tests |
| `src/lib/decisions.ts` says GO = `СВОБОДНО`; Live has receipt-age handling and additional node freshness | Align visible meaning to “not detected”, verify source-age versus receipt-age behaviour |
| `detector_node.py:make_markers` uses generic CAUTION wording | P1 owns producer text; P2 owns RViz layout/visual acceptance |
| Backend shared decision function returns the word; stored/simulated rows need a field-flow audit | Coordinate metadata propagation without rewriting historical decisions |
| `build_deck.py` and current docs distinguish GATE/N/JUDGE; final J1 import/verification is still needed | Source-driven chart check, at least three geometries, exact row provenance |
| README/docs index say video 2:50, video README says 3:00 | P2-01 measures file duration; update maintained descriptions, preserve historical accounts |
| `bench_8core.sh` defaults to building/reusing `resense:latest`; console smoke limits are permissive and not the four-condition S1 matrix | Pin inspected release image with SKIP_BUILD and run the separate registered matrix |
| Local CPU is i5-8250U, 1 socket × 4 cores × 2 threads | S5 requires another host; 8 logical CPUs is insufficient |
| P4's new protocol leaves some raw outputs in an ephemeral container | Request a durable raw export before depending on it for reproducible final charts |
| New immutable archived-lint and web-raw preservation checks exist | D2 must respect manifests and restoration, not just move files |

The older integration ledger says web preservation is still separate. At **b0c9c17** the
preservation content is already included by the latest commit; final-main acceptance/retirement
still belongs to P1. Likewise the older P4 handoff leaves default-pointer verification pending:
the local check below now verifies that pointer for this branch, not full CI or E1.

## Checks performed during planning

* `python3 scripts/detector_freeze.py verify` — **PASS**, 36 files, digest
  `db3f588df59184ad703436996f72bd94a91eca91dfcfe4a02655fcdd4397d751`.
  Tool explicitly reports integrity only; no recordings replayed.
* `python3 scripts/release_meta.py version` — **1.1.0**.
* `bash scripts/sync_params.sh --check` — **parameter files in sync**.
* `git ls-remote --heads --tags origin` — integration/participant refs match the table;
  only release tag listed is **v1.0.0 → 5d6e9b5**.
* `lscpu` — **4 physical cores / 8 logical CPUs**, Intel Core i5-8250U.
* Relative Markdown-link validation across the four plan/status/index files — **93 checked,
  0 broken**; `git diff --check` — **PASS**.

No new detection, latency, score, PDF visual acceptance, archive download or rehearsal result
is claimed by this planning pass. Implementation checks are prescribed in the plan.
