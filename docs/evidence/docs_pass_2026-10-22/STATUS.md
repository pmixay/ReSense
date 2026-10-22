# Status of the docs pass at the pause (22.10)

> Written when the lane was paused on the captain's request (usage limits). `README.md` in this folder is the full record; this file says what is done and what remains.

## Done
* **READMEs:** all 40 folders that had none now have one (pushed in earlier commits); links 0 broken; number presence check 671/684 (13 line numbers checked by hand, 1 corrected).
* **Index:** `../README.md` §4 lists all folders (155 with this one), date / topic / README title; header "Last verified" updated.
* **Stale dates:** 17 pages re-verified against the 1.3.0 tree and set to 2026-10-22 (list and corrections in `README.md` §3).
* **Deleted branches:** replaced or annotated in the editable pages (`README.md` §6); `fix/k1-k2-repair-20261020` is unreachable, its raw outputs are gone.
* **Checks on the working tree at pause:** ruff 0.15.8 `check_archived_lint.py --lint` PASS; `detector_freeze.py verify` PASS (42 files); full suite `2552 passed, 8 deselected` (open3d and libEGL installed in a scratch venv; the docs quote 2 551 passed and 1 known failure for another environment; not reconciled).

## Not done
* No CI run on the final head was waited for or recorded (the WIP commit is pushed without `[skip ci]`, so CI will run on it; its conclusions are not recorded here).
* `docs/images/README.md` (09-28) not re-dated: the web-player lane edits `docs/images/**`.
* Findings in files this lane may not edit are only listed (`README.md` §5), not fixed.
* The branch inventory is regex-based; names outside the patterns may remain (`README.md` §6).
* Evidence folders added by other lanes after this pass (`h1_continue_2026-10-22`, `webapp_cab_finish_2026-10-22`) are not in index §4.
* The numbers inside the 40 READMEs are checked for presence in their sources, not row by row for meaning.
