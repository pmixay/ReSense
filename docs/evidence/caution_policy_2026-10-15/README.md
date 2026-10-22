# C1 caution policy: contract, saved-output rescore, packaging fixes (15.10)

> **Purpose:** the proposed shared decision-policy contract (v1 default, v2 opt-in), the offline rescore
> that tested v2 against the 1.0.0 gate outputs, and the follow-up check that the policy module imports
> from installed wheels.
> **Audience:** captain, P1/P2 (consumers of the status fields), reviewers of the C1 decision ·
> **Owner:** P1 (DECISIONS.md row 32 calls C1 "задача P1") · **Language:** EN
> **Last verified:** 2026-10-22: numbers below checked against the named files, links resolve ·
> **Status:** historical; v2 not accepted, v1 selected (see section 3)

## 1. What was run, when, by whom

* Rescore: 2026-10-15 (title of `EVIDENCE.md`), in a P1 scratch worktree `rs-p1-policy` on a Windows
  machine (paths in `EVIDENCE.md`), based on `d0d17bb`. Branch name omitted.
* Input: previously generated 1.0.0 regression-gate outputs (producer commit
  `264f5b29304fd685f4042ded9eb382070da90563`, default config, Windows Python 3.11.9, per `EVIDENCE.md`).
  These are not final-1.1.0 judge-runner outputs. No new detector replay was made (`EVIDENCE.md`).
* `PACKAGING_REVIEW.md` and `wheel_import_review.json`: a follow-up fixing two independent-review
  findings on the combined P1 worktree starting at `4e4d5a9`; the date is not written in either file
  (unverified; it is after 15.10, the listing of `../p1_start_2026-10-15/README.md` places it in the P1 start work).
* Git: the folder arrived with import commit `44b462e` (2026-10-16); that is the import date, not the run date.

## 2. Result

At D_c = 80 m and compact extent <= 3 m, v2 **fails** (`EVIDENCE.md`, table; same values in
`scratch_baseline_rescore.json` `groups`, `checks`):

| measure | v1 | v2 |
|---|---:|---:|
| empty CAUTION of 13,558 frames | 5,710 (42.12%) | 4,130 (30.46%), target <= 25%: fail |
| in-gauge object-frame CAUTION-or-STOP of 801 | 619 | 600, 19 lost: fail |

Empty STOP stays 165 and FAULT 0 in both (`EVIDENCE.md`). B/C visible-object retention was not measured
(`scratch_baseline_rescore.json` `checks.range_visible_alert_retention: not_measured`). The packaging follow-up
reports `status: pass` for the isolated wheel import (`wheel_import_review.json`).
Counts are frame-level alert retention, not object-matched recall (`EVIDENCE.md`).

## 3. Supports

* [`DECISIONS.md`](../../DECISIONS.md) row 32 (C1 semantics): v2 FAIL cited, "16.10 выбран единый чистый модуль v1", runtime v2 rejected.
* [`BACKLOG.md`](../../BACKLOG.md) card "C1 · CAUTION policy" (line 306 to 309): "Shared v1 is selected; offline v2 FAILED".
* [`ARCHITECTURE.md`](../../ARCHITECTURE.md) line 206 links the contract; [`../integration_2026-10-16/runtime_selection.md`](../integration_2026-10-16/runtime_selection.md)
  states C1 v2 remains unaccepted. `../p1_start_2026-10-15/finalize_checks.py` reads `scratch_baseline_rescore.json`.

## 4. Contents (5 files)

* `CONTRACT.md`: API, semantics and additive reason codes of the decision policy (v1 default, v2 opt-in).
* `EVIDENCE.md`: rescore result, sources and limits, reproduction command, test results, remaining conditions.
* `scratch_baseline_rescore.json`: machine-readable rescore (hashes, per-source counts, 19 lost-frame examples).
* `PACKAGING_REVIEW.md`: backend declares `resense-ros>=1.0.0`; observer policy import by source origin; E2 fixture handoff.
* `wheel_import_review.json`: output of the isolated wheel build and import check.

## 5. Caveats

* The rescore used Windows paths, 1.0.0 gate outputs and a base-decision-only scope (no node freshness, watchdog
  or STOP latch: `scratch_baseline_rescore.json` `scope`). It was never repeated on 1.1.0 or later detectors.
* Later fact: the organizers' answer that everything inside the gauge is an obstacle settles in-gauge objects
  (`BACKLOG.md` card text).
* The raw per-bag JSONL inputs are not in this folder (paths point to a local scratch directory): the counts
  can be read here but not recomputed from this folder.
* `EVIDENCE.md` reports 220 tests passed with 3 deselected Windows-specific tests; I did not rerun them (unverified).
