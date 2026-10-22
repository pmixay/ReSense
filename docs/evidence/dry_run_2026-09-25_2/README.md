# Dry run confirmation on a second team VM, 25 September afternoon

> **Purpose:** the dry runs of both original bags and the console tests after the start-up catch-up and drop-counting fixes, plus a host console
> that was labelled "stock Fast DDS" and was later found to be CycloneDDS, with the diagnostic runs around it.
> **Audience:** team, jury · **Owner:** P1 (runs, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: the six checker files read; the diagnostic table of `diag_host_fastdds/README.txt` compared with its five run files;
> which files carry the CORRECTION line counted with `grep -l` (7 files) · **Status:** dated record; all `fastdds` host runs here are CycloneDDS runs

## 1. What was run, when

* Run: 2026-09-25 afternoon. Node log time stamps run from 14:38 to 14:49 UTC (ROS time); the VM host is the one of [`bench_2026-09-25_2/`](../bench_2026-09-25_2/summary.txt)
  (14:51 UTC that bench), user `admn`, bags from a RAM tmpfs (`diag_host_fastdds/README.txt`). Git dates (`315ad1d`, `6962519`, `054a8ea`) are commit dates, not run dates.
* Code: `76bf24e` (`diag_host_fastdds/README.txt`; same value in `bench_2026-09-25_2/facts.txt`). That SHA is not an object in this checkout, so it is unverified here.
  The checker files carry no commit. Lane: not recorded in the folder or the docs (the log §3b calls it the "confirmation re-run").
* Companion folders: [`bench_2026-09-25_2/`](../bench_2026-09-25_2/summary.txt), [`vm_2026-09-25_2/`](../vm_2026-09-25_2/machine.txt).

## 2. Result

* `dry_obstacle.txt` PASS: 141 alarm frames at 55.5-56.5 m, p95 70 ms, first STOP +0.4 s, 46 dropped, "4 after +6.9 s", 0 of the recording's messages not processed, 10.07 fps.
* `dry_clear.txt` PASS: 0 alarm frames, p95 49 ms; `replay_dry_clear.txt`: node 234 frames and replay 234 frames, 0 alarm frames each.
* `ct_stock.txt` PASS (stock Fast DDS player in Docker, 385 messages, 141 alarm frames, 141 STOP seen by the listener, `rmw_fastrtps_cpp`, fastrtps 2.6.12).
* `host_console_cyclonedds.txt` PASS: `rmw_cyclonedds_cpp`, `rmem_max` 33554432, 144 STOP at 55.6-56.5 m.
* `host_console_fastdds.txt` FAIL (3 alarm frames, none in recording 2; CORRECTION line: the player was CycloneDDS). Diagnostic runs (`diag_host_fastdds/README.txt`, same CycloneDDS player): at
  `rmem_max` 212992, 5 of 5 runs FAIL (0-1 of the 201 360-degree clouds, or the recording is missing); with `rmem_max` 33554432 (`host_console_fastdds_rmem32.txt`) PASS, 144 STOP.

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3b "Confirmation re-run with the original bags" (cites this folder and `diag_host_fastdds/README.txt`); its figures (55.5-56.5 m, +0.4 s, p95 70 ms, 10.07 fps, "dropped 46 (39 skipped)") match.
* [`DECISIONS.md`](../../DECISIONS.md) row 6 (CycloneDDS needs 32 MiB, Fast DDS does not); CAPTAIN board C4 ([`CAPTAIN_board_2026-09-28.md`](../../archive/CAPTAIN_board_2026-09-28.md)); [`../README.md`](../README.md) line 147.
* The correction is made in [`dry_run_2026-09-25_3/README.txt`](../dry_run_2026-09-25_3/README.txt), which re-runs with a verified Fast DDS player.

## 4. Contents (49 files)

* Checker output: `dry_obstacle.txt`, `dry_clear.txt`, `ct_stock.txt`, `replay_dry_clear.txt`, `host_console_cyclonedds.txt`, `host_console_fastdds.txt`.
* Raw captures (flat, one prefix per step): `dry_obstacle_*`, `dry_clear_*`, `ct_stock_*` (node, player, listener logs, `status.jsonl.gz`), `host_cyclonedds_*`, `host_fastdds_*` (decision, node log, player log, status).
* `diag_host_fastdds/` (27 files): `README.txt` (the table of five runs), `g_runs.sh`, `host_console_fastdds_{repeat,repeat2,profile8mib,profile8mib_repeat,rmem32}.txt` and their decision / node / player / status files.

## 5. Caveats

* Naming: every file named `fastdds` in this folder (and `../host_console_fastdds.txt` text) came from a CycloneDDS player. Only 7 files carry the CORRECTION line (`host_console_fastdds.txt` and six in `diag_host_fastdds/`);
  `host_fastdds_decision.txt`, `host_fastdds_node_log.txt`, `host_fastdds_player_log.txt` and `host_fastdds_status.jsonl.gz` do not. The index row ([`../README.md`](../README.md) line 147) says "files carry a CORRECTION line"; that holds for the checker texts only.
* The correction rests on the third VM's README (the host had no Fast DDS RMW installed). Nothing in this folder records the loaded library; unverified here, and consistent with the CycloneDDS-only results at 212992.
* The `profile8mib` runs mount an older 8 MiB UDP profile over the image's as a runtime override only (`diag_host_fastdds/README.txt`); nothing in the repository changed.
