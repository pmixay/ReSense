# Re-judgement of 26.09 evening: raw runs of judge A

> **Purpose:** index of the raw outputs of the 26.09 evening re-judgement (tests, offline and node dry
> runs, stock console test, set O, full regression gate, bench, P3/P4 checks), and what each shows.
> **Audience:** jury, team · **Owner:** lane not recorded in the folder or the docs (the docs call the author "judge A" of the re-judgement) · **Language:** EN
> **Last verified:** 2026-10-22: every file listed exists; the numbers below were copied from the named files and
> read against `README.txt` of this folder; nothing was re-run (the dataset is not available) ·
> **Status:** superseded (the scores of this re-judgement are replaced by the judgement of 28.09 evening; the raw outputs stay as records)

The folder already has [`README.txt`](README.txt) (the judge's own file list, in the order of the run) and
[`p34/README.txt`](p34/README.txt). This file is an index and a list of caveats; it does not replace them.

## 1. What was run, when, by whom

* **Run date:** 26.09.2026, evening (`README.txt`). **Import date:** 2026-10-16, squash commit `44b462e` (the only
  commit that touches this folder); the import date is not the run date.
* **Who:** an independent re-judgement ("judge A", per `docs/archive/CAPTAIN_history_2026-10-19.md` rows dated
  26.09 and 26.09 evening). No person or lane name is given.
* **Code under test:** `be5f5fce104b8f246c80effd33debcdf8f66424d` (`code.commit` in `gate_result.json`; `README.txt`
  says the detector of `fa18832`, config sha256 `d2c8ab8d...`). The P3/P4 checks in `p34/` ran at head `1f8b8ff`
  (`p34/README.txt`). A branch name appears in `gate_result.json` and `README.txt`; branch name omitted here.
* **Machine:** a 4-core cloud sandbox, 15 GiB RAM, no ROS on the host, Docker image built from `docker/Dockerfile`
  (`README.txt`). Not the jury stand.

## 2. Result

* Tests: 585 passed, 1 deselected (`pytest.txt`); the deselected ride test passed once the ride was cached: 28 passed (`pytest_ride_test.txt`).
* Full regression gate: "GATE PASS ... 0 gated better, 0 worse but allowed, 16 information rows changed" (`gate_run.txt`); 183 gated metrics `same` (`gate_result.json`, field `gate.same`).
* Node dry run, `doubleT_obstacle`: warm page cache PASS, 139 status messages, 126 alarm frames, p95 81 ms (`dry_obstacle_warm.txt`);
  with the page cache dropped FAIL, 34 status messages, 94 frames not processed (`dry_obstacle_cold.txt`);
  default settings with a 4 MiB host buffer FAIL, 53 messages (`dry_obstacle.txt`). `roundT_doubleT` warm PASS, 0 alarm frames (`dry_clear.txt`).
* Set O through the node: PASS, 1452 status messages, 368 alarm frames (`ros_setO.txt`, `ros_setO_score.txt`).
* Bench, native path, mean per frame: 30.7 ms (`doubleT_obstacle`), 25.8 ms (`roundT_doubleT`), 22.7 ms (`cloud_with_fake_obj`) (`bench_native.txt`).
* Cold-disk variant: `catchup_max_lag:=20.0` still FAIL cold (43 messages, `variant_cold_maxlag20.txt`), PASS warm (139 messages, 129 alarm frames, `variant_warm_maxlag20.txt`).

## 3. Supports

* `docs/SCORECARD.md`: the folder is cited as the evidence of the 26.09 re-judgement section (per `docs/archive/CHANGELOG_2026-09.md` line 138, which points to SCORECARD section 0). Not re-read in current `SCORECARD.md`: a grep for the folder name there finds nothing.
* `docs/archive/CAPTAIN_board_2026-09-28.md` item C7 (clean-machine dry run, cold page cache) and `docs/archive/CAPTAIN_history_2026-10-19.md` (rows 26.09 and 26.09 evening).
* `docs/archive/EXPERIMENTS_log_2026-09.md` lines 86 and 124 (gate against `_ride_p3d`; bench figures).
* `docs/evidence/README.md` section 2, row `rejudge_2026-09-26/`.
* `README.txt` names "CAPTAIN action 21" (catch-up lag trade-off); not checked in a current document.

## 4. Contents (56 files)

* [`README.txt`](README.txt), [`p34/README.txt`](p34/README.txt): the judge's descriptions.
* `pytest.txt`, `pytest_ride_test.txt`: test runs on the host.
* `dry_obstacle*.txt`, `dry_obstacle*_node_log.txt`, `dry_obstacle*_status.jsonl.gz`: four variants (default, `step0`, `warm`, `cold`) of the 360 degree dry run; `dry_clear*`: the 120 degree clear run; `ct_stock*` (txt, status, node, listener, player logs): stock console test.
* `setO_raw_bag*` (jsonl.gz, score txt, clear-distance json): set O from the float bag, offline.
* `ros_setO*` (txt, node log, status, score txt and json), `setO_header_stamps.jsonl`, `node_to_frames.py`: set O through the node and the stamp-to-frame mapping.
* `gate_run.txt`, `gate_result.json`: the full gate; `bench_native.txt`: bench.
* `variant_run.sh` and 9 `variant_*` files (3 variants: cold default, cold maxlag 20, warm maxlag 20): catch-up under a cold disk.
* [`p34/`](p34) (10 files): robustness (4 txt), start offsets (txt, json), gates of candidate B and of the axis union (2 json), `run.sh`, `README.txt`.

## 5. Caveats

* **Superseded:** the scores of this re-judgement are replaced by the judgement of 28.09 evening (`CAPTAIN_history_2026-10-19.md`).
* **Superseded detector:** `be5f5fc` is the 26.09 head (P3d baseline `_ride_p3d`), not the later sealed detectors.
* **Test count differs from a doc:** `docs/archive/CHANGELOG_2026-09.md` line 138 says "587 tests green"; this folder shows 585 passed + 1 deselected, and 28 in the ride test file. Not reconciled.
* The cold FAIL is a finding about the player burst plus `catchup_max_lag`, recorded as such in `README.txt`; the folder holds no fix.
* Quoted by `README.txt` but not re-found in the named files by me: gate duration 302 s; set O "387 of 801 inside STOP frames" and "7 false STOP frames" (the table in `setO_raw_bag_score.txt` shows 7 alarm frames on box #7 and 1 background frame). Treat as unverified.
* `ros_setO.txt` says "132 of its messages not processed"; `README.txt` explains this checker line as wrong for this bag (header stamps drift against receive times).
* `setO_header_stamps.jsonl` was committed with `git add -f` (`README.txt`).
* Data not in the repository (dataset not available here): none of the runs can be repeated from this checkout.
