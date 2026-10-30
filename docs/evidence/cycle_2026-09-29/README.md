# Evidence of the 29.09 cycle: gates of the day's detector changes

> **Purpose:** map of the five items of 29.09 (a health-histogram speed-up, a threshold change, a round of
> false-alarm rules, the shell-rule-off gate, a timestamp-aware clearance cap),
> so a reader can find the gate or record behind each number in the docs.
> **Audience:** team, jury, reviewers · **Owner:** not recorded in the folder or the docs ·
> **Language:** EN · **Last verified:** 2026-10-22 (only the numbers named below were opened and copied;
> nothing was re-run) · **Status:** dated records; see the supersession order in section 5.

## 1. What was run, and when

Run dates come from `created` inside the gate files, all 2026-09-29 (UTC). The folder (228 files) entered
the repository with the squash import `44b462e` on 2026-10-16 (per `git log`); that is the import date.
Lane: not recorded in the folder or the docs, except where a sub-README says so. In time order:

| item | `created` (UTC) | code | machine |
|---|---|---|---|
| [`timestamped_persistent_evidence/gate.json`](timestamped_persistent_evidence/gate.json) | 01:15 | `1a05ea76` (experimental line) | 8 CPUs (`run.machine`) |
| [`thin_far_threshold/default_gate.json`](thin_far_threshold/default_gate.json) | 02:52 | `dcaa5db` | 8 CPUs (`run.machine`) |
| [`health_compare_counts/`](health_compare_counts/README.md) | day | `3eeb106` (v1 `838f45c` rejected) | 4-core cloud container (README) |
| [`competitor_rules/gate.json`](competitor_rules/gate.json) | 15:21 (candidates from 12:40) | `1e2ed82` | 4 CPUs |
| [`shell_off/gate.json`](shell_off/gate.json) | 17:15 | `7464d80` | 4-vCPU sandbox (README) |

## 2. Result

* Threshold 4 to 3: 202 metrics unchanged, 2 better, Set F 0.5 m box 1/6 to 2/6 (`thin_far_threshold/default_gate.json`).
* Health compare-count change: exit 0, 207 compared metrics unchanged, 15 269 frames identical outside
  timing (`health_compare_counts/README.md`).
* Three rules from other teams: PASS, ride 26 events / 28 STOP episodes against 32 / 31
  (`competitor_rules/gate.json`, `gate_table.md`).
* Shell rule off: PASS, 6 better, 196 same; ride 27 events / 30 episodes (`shell_off/README.md`, `shell_off/gate.json`).
* Timestamp-aware clearance cap: `gate.passed` true, 0 better (`timestamped_persistent_evidence/gate.json`).

## 3. Supports

[`../../DECISIONS.md`](../../DECISIONS.md) rows 30 and 31; [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md) lines 334 to 336;
[`../README.md`](../README.md) lines 46, 48, 67 to 69, 123 to 125 (the file-by-file index of these folders);
[`../../DETECTOR_FREEZE.md`](../../DETECTOR_FREEZE.md) (seals).

## 4. Contents

| path | files | README |
|---|---|---|
| [`thin_far_threshold.md`](thin_far_threshold.md) | 1 | note for the 4 to 3 change |
| [`thin_far_threshold/`](thin_far_threshold/README.md) | 70 | yes |
| [`health_compare_counts/`](health_compare_counts/README.md) | 124 | yes (own) |
| [`competitor_rules/`](competitor_rules/README.md) | 18 | yes |
| [`shell_off/`](shell_off/README.md) | 3 | yes (own) |
| [`timestamped_persistent_evidence/`](timestamped_persistent_evidence/README.md) | 12 | yes (own) |

File counts are from `find` before these READMEs were added; they sum to 228.

## 5. Caveats

* Supersession on 29.09: the seal `1e2ed82` (competitor rules, shell on) was replaced the same night by
  the seal at `7464d80` (shell off); `3eeb106` was the seal before both. Current baseline:
  [`../results/regression_baseline_2026-09-29_shell_off.json`](../results/regression_baseline_2026-09-29_shell_off.json).
* Metric counts: `timestamped_persistent_evidence/README.md` says 146 gated metrics match; its
  `gate.json` has `gate.same` 208. Not a conflict: `../cycle_2026-09-28/complete_timing/default/README.md`
  and `../cycle_2026-09-28/p3_sync/default/README.md` state 146 enforced rows and 208 comparable
  metrics for the same baseline. The gate files themselves do not label which 146 are enforced
  (unverified).
* The threshold-3 and threshold-4 history reports name different source commits (see
  [`thin_far_threshold/README.md`](thin_far_threshold/README.md)).
