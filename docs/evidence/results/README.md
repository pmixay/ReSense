# `results/`: orientation to the result summaries (21.09 to 29.09)

> **Purpose:** short map of the 771 files in this folder: the families, the naming rules, the counts and
> where the file-by-file index is. It does not re-index the files.
> **Audience:** team, jury, reviewers · **Owner:** not recorded in the folder; the index
> [`../README.md`](../README.md) names P4 for the result summaries · **Language:** EN ·
> **Last verified:** 2026-10-22 (counts from `find` and `ls` on this checkout; contents of the files
> not re-checked) · **Status:** dated records; later seals supersede most of the gates

## 1. What this folder is, and when it was run

Result summaries of the experiments and gates of the development cycle 21 to 29 September 2026. The date
in a name is the date of the run as the file's author wrote it (names carry 24.09 to 29.09; the 14
`experiments_v*`/`experiments_p4_*` files carry no date, the index dates them to 21 to 24.09). The folder
was added by the squash import `44b462e` (2026-10-16) and touched again by `0acb18c` (2026-10-19, PR #42)
per `git log`; those are import dates, not run dates. Lane: the `p1_`, `p3_`, `p4_` prefixes are part of
the names; beyond that, lane not recorded in the folder or the docs, look at each file's own `note` /
`_meta` block (see the header of the index section).

## 2. Where the index is

[`../README.md`](../README.md) section 1 ("`results/`: summaries of the experiments", from line 60) lists
the files one row each: date, code commit, result. Sections 2 and 3 of that file cover the run folders
and the quoted-but-not-committed items. Current numbers: [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md);
decisions: [`../../DECISIONS.md`](../../DECISIONS.md); the current gate baseline is
[`regression_baseline_2026-09-29_shell_off.json`](regression_baseline_2026-09-29_shell_off.json)
(see [`../cycle_2026-09-29/shell_off/README.md`](../cycle_2026-09-29/shell_off/README.md)).

## 3. Families and counts

Totals from `find results -type f`: 771 files; 116 at top level, 655 inside 28 sub-folders.

| family (name prefix) | top-level files | sub-folders | files in sub-folders |
|---|---:|---:|---:|
| `experiments_` (versions v0.4 to v0.6.3, P4 set O / set F) | 16 | 0 | 0 |
| `regression_gate_` (full gate outputs) | 18 | 0 | 0 |
| `regression_baseline_` (files a gate is compared against) | 10 | 0 | 0 |
| `p3_` (P3 candidate results) | 19 | 0 | 0 |
| `p4_` (P4 protocols, screens, inventories, validations) | 27 | 9 | 227 |
| `quality_` (quality cycle 26 to 27.09: D1, T1, M1, M2, freshness, delivery, root checks) | 13 | 13 | 389 |
| `oracle_`, `range_metric_` (28.09) | 0 | 3 | 13 |
| single-topic files (`scorecard13_`, `seto_suffix_`, rules, reviews, residual events, competitor screen, ...) | 13 | 0 | 0 |
| other folders: `available_gate_testovaya_2026-09-28/` (11), `branch_integration_2026-09-27/` (8), `p1_raw_continuity_2026-09-28/` (7) | 0 | 3 | 26 |
| total | 116 | 28 | 655 |

Largest sub-folders (`find` counts): `quality_freshness_2026-09-26/` 89, `p4_full_data_2026-09-28/` 87,
`quality_cycle_2026-09-26_T1/` 56, `p4_p3d_artifacts_2026-09-26/` 47, `quality_cycle_2026-09-27/` 44,
`quality_cycle_2026-09-26_clear_failure/` 43, `quality_cycle_2026-09-26_M2_validation/` 35. File types over
all 771: 347 `.json`, 262 `.gz`, 50 `.txt`, 29 `.npz`, 24 `.png`, 22 `.md`, 19 `.log`, 16 `.yaml`, 1 `.xml`, 1 `.sha256`.

## 4. Naming rules

* Top level: `<what>_<YYYY-MM-DD>[_<suffix>].json` (one `.json.gz`: `quality_monitoring_M2_novel_plan_2026-09-26.json.gz`).
  Suffixes seen: `_protocol` and `_novel_plan` (names suggest they were registered before the run;
  not checked), `_evening`; candidate tags (`p3d`, `B`, `M2`) appear inside names.
* Folders: `<what>_<YYYY-MM-DD>/`. A new run gets a new file or folder; an old one is not overwritten
  (rule stated in [`../README.md`](../README.md), second paragraph).
* Dates by name, top-level files: 24.09: 2, 25.09: 27, 26.09: 59, 27.09: 3, 28.09: 8, 29.09: 3, no date: 14.
* 22 of the 28 sub-folders have their own `README.md`; the six without are `branch_integration_2026-09-27/`,
  `p4_artifacts_2026-09-26/`, `p4_candidate_B_checks_2026-09-26/`, `p4_p3d_artifacts_2026-09-26/`,
  `p4_robustness_2026-09-26_evening/`, `quality_cycle_2026-09-27/`.

## 5. Caveats

* Superseded: gates and baselines of 25 to 27.09 describe earlier detector states; the 29.09 shell-off seal
  is the current baseline (section 2).
* The index does not name 34 entries here (exact-name search of `../README.md`): 20 top-level files
  (`cross_ring_false_alarm_analysis_2026-09-28`, `fresh_local_support_2026-09-28`, `residual_events_2026-09-28`,
  `single_review_2026-09-28`, four `p4_*_2026-09-28` files (candidate screen protocol and results, data
  intake, false-alarm inventory), and twelve `quality_*` protocol / plan / baseline files) and 14 folders (`available_gate_testovaya_`,
  `oracle_accumulation_`, `oracle_full_returns_`, `p1_raw_continuity_`, `p4_full_data_`, `range_metric_`
  and eight `quality_*` folders). Most are cited by dated docs under `../../archive/` or `../../`
  (checked by name search for a sample of 16, 4 of which, `single_review_2026-09-28`,
  `available_gate_testovaya_2026-09-28`, `oracle_accumulation_2026-09-28`,
  `quality_monitoring_baseline_2026-09-26`, were found in no doc: unverified whether they are indexed elsewhere).
* Several 28.09 files here (`p1_raw_continuity_2026-09-28/`, `p4_full_data_2026-09-28/`) concern the
  experimental line of [`../cycle_2026-09-28/`](../cycle_2026-09-28/README.md), not the sealed detector.
