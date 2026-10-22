# Judgement of 29.09: scripts only, no completed re-run

> **Purpose:** say what this folder is (12 judge scripts prepared for a re-run of the 28.09 judgement) and that it holds no results.
> **Audience:** jury, team · **Owner:** lane not recorded in the folder or the docs · **Language:** EN
> **Last verified:** 2026-10-22: file list and the script comparison below checked in this checkout (`cmp` against
> `../judgement_2026-09-28/scripts`); no script was run (the dataset is not available) ·
> **Status:** incomplete (scripts only); the completed later judgement is [`../judgement_2026-10-13/`](../judgement_2026-10-13)

## 1. What was run, when, by whom

Nothing in this folder records a completed run. The scripts' own docstrings carry the date "29.09" and say what they
changed against the 28.09 versions. There are no outputs, logs, commit SHA or lane name in the folder, and the docs that
cite it do not name a lane: lane not recorded in the folder or the docs. Import date: 2026-10-16, squash commit
`44b462e`; that is the import date, not a run date. The code commit the scripts were meant to run against is not recorded.

## 2. Result

None. `docs/archive/CAPTAIN_history_2026-10-19.md` (row 1 of its action table) says: "`evidence/judgement_2026-09-29/`
contains scripts only, not a completed re-run; the completed later judgement is 13.10." `docs/archive/BACKLOG_history_2026-10-19.md`
(line 901) records the same finding: the folder "holds only scripts, though CAPTAIN cites it".

## 3. Supports

No decision, backlog item or score uses a number from this folder (there are none). It is cited only as the intended
home of the 29.09 re-judgement (the two archive lines above). `docs/evidence/README.md` section 2 has no row for it.
The scripts are in the lint coverage lists of `../integration_ci_2026-10-16/lint_record/` (so they were linted, not run).

## 4. Contents (12 files, all in [`scripts/`](scripts))

Compared with [`../judgement_2026-09-28/scripts`](../judgement_2026-09-28/scripts) by `cmp`:

* byte-identical to 28.09 (7): `extract_bags.py` (stream named bags out of the nested archive), `ride_consumer.py`, `ride_producer.py` (stream the 20-minute ride), `score_bag.py`, `score_ride.py`, `score_setO.py`, `transplant_summary.py`.
* new on 29.09 (3): `compare_2809.py` (28.09 figures next to the re-run's), `ride_producer_range.py` (ride download by HTTP Range requests after the single download slowed from ~40 MB/s to ~1 MB/s, per its docstring), `summarize_offline.py` (scores the six offline runs; 28.09 assembled this by hand).
* changed against 28.09 (2): `transplant.py` (docstring: `CONFIG` can replace the default config), `tp_batch.sh` (`TPOUT` output directory).

## 5. Caveats

* No result in this folder can be quoted. The 28.09 figures live in [`../judgement_2026-09-28/`](../judgement_2026-09-28/README.md); the completed judgement is [`../judgement_2026-10-13/`](../judgement_2026-10-13).
* `compare_2809.py` reads `../judgement_2026-09-28` and expects to be run inside this folder; it was not run here.
* Scripts need the organizers' dataset and the `resense` package; not run in this review (unverified that they still work).
