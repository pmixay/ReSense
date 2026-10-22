# Dry run with the original bags on the first team VM, 25 September morning

> **Purpose:** the first real "dry run" of the deployment path on the original bags: Docker dry runs of both recordings, the two console tests,
> a host console as a normal user with Fast DDS and with CycloneDDS, and the CycloneDDS buffer diagnosis that followed.
> **Audience:** team, jury · **Owner:** P1 (runs, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: `result.txt`, `highlights.txt`, `meta.txt` and the per-run `.txt` files compared with each other, with the log §3b and CAPTAIN board
> rows C4 and C5; status captures and logs not re-scored ·
> **Status:** dated record of a FAIL run; the failures it found were fixed the same day (see section 5)

## 1. What was run, when

* `meta.txt`: subcommand `dryrun` of the VM kit (`scripts/vm/run_plan.sh dryrun`), started 2026-09-25T09:26:18+00:00; `result.txt`: finished 09:35:24, 546 s.
  The node logs span 09:29 to 09:43 UTC (ROS time stamps), the diagnosis `diag_cyclonedds_buffers/` is dated "~09:40 UTC" in its README.
  First team VM, user `mdm`, 8 vCPU = 4 physical cores, Ubuntu 22.04, host ROS 2 Humble, Docker 29.8.1, bags from a RAM tmpfs (`meta.txt`, `original_bags.txt`).
* Code: `7290873` (`result.txt`; full SHA `72908737f2f8d1caf2b513f730abd930c8dac20d` in `meta.txt`, worktree clean). That SHA is not an object in this checkout, so it is unverified here.
  `meta.txt` names a branch; the name is omitted here. Lane: not recorded in the folder or the docs.
* Git dates (`315ad1d` 2026-09-25, reverted in `6962519`, present again via `054a8ea` 2026-09-27) are commit dates, not run dates.

## 2. Result

`result.txt`: dryrun FAIL. `original_bags` PASS (metadata identical to [`bag_metadata/`](../bag_metadata)), `console_image` PASS (69 s), `console_stock_dds` PASS (70 s), `host_fastdds` PASS (75 s);
`dry_obstacle` FAIL, `dry_clear` FAIL, `host_cyclonedds` FAIL; `ride_replay` SKIPPED (20-minute bag not on this disk). From `highlights.txt`:

* `dry_obstacle`: 132 alarm frames at 55.7-56.5 m, latency p95 69 ms, first STOP +1.6 s, FAIL only on "20 dropped input frames after the first 5 s".
* `dry_clear`: 3 alarm frames at 111.0-114.9 m, FAIL ("3 false alarms ... allowed 2").
* `host_fastdds` (label as written in the file): 137 alarm frames, 55.7 m, PASS. `host_cyclonedds`: FAIL, "recording 2: 0 alarm frames, expected >= 3".
* `diag_cyclonedds_buffers/README.txt`: at `rmem_max` 212992 the node got no 360-degree cloud (55 status messages, all FAULT); with 32 MiB (`host_cyclone_32mb/check.txt`) 132 messages, 111 alarm frames at 55.8-56.2 m, p95 72 ms.

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3b "Dry run with the original bags ..." (cites this folder and `diag_cyclonedds_buffers/`), §3a "What fails, and why" (same-day repeats).
* CAPTAIN board rows C4 (host console, "137 STOP, 55.7 m"), C5 (first STOP +1.6 s) and C7 ([`CAPTAIN_board_2026-09-28.md`](../../archive/CAPTAIN_board_2026-09-28.md)); [`DECISIONS.md`](../../DECISIONS.md) row 6 (CycloneDDS got 0-1 of 201 clouds at 212992, all at 32 MiB).
* Index row [`../README.md`](../README.md) line 148; [`vm_2026-09-25/summary.md`](../vm_2026-09-25/summary.md) line 21. [`results/column_hold_2026-09-25.json`](../results/column_hold_2026-09-25.json) scores five captures of this folder (`dry_clear`, `host_cyclonedds`, `host_fastdds`, `console_image`, `console_stock_dds`).

## 4. Contents (56 files)

* Run record (12 top-level files): `result.txt`, `steps.tsv`, `highlights.txt`, `meta.txt`, `original_bags.txt`, `run_log.txt` (1217 lines); checker output per step `dry_obstacle.txt`, `dry_clear.txt`, `console_image.txt`, `console_stock_dds.txt`, `host_fastdds.txt`, `host_cyclonedds.txt`.
* One folder per step with the raw capture: `dry_obstacle/`, `dry_clear/` (node log, `status.jsonl.gz`, `docker_stats.tsv`); `console_image/` (2 files), `console_stock_dds/` (4 files, with player and listener logs);
  `host_fastdds/`, `host_cyclonedds/` (7 files each: decision, nearest distance, check, logs, status, stats).
* `diag_cyclonedds_buffers/`: `README.txt`, `host_console.sh`, and two runs (`host_cyclone_default/`, `host_cyclone_32mb/`, 8 files each) with `setup.txt`, `play.txt`, `decision_runs.txt`, `check.txt`.

## 5. Caveats

* Superseded as the current result: `dry_obstacle` FAIL is the old drop criterion (the log §3a: 16 of the 20 drops were catch-up skips, 4 are missing from the recording); the 3 alarm frames of `dry_clear` were the subject of `tracking.column_hold` (log §3a);
  the re-runs pass ([`dry_run_2026-09-25_2/`](../dry_run_2026-09-25_2/dry_obstacle.txt), [`dry_run_2026-09-28/`](../dry_run_2026-09-28/e2e_vm.txt)).
* Whether the `host_fastdds` player really ran Fast DDS is not shown in this folder: `host_fastdds.txt` states `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, but no `/proc/<pid>/maps` check exists here. On the second VM the same label hid a CycloneDDS player
  (see [`dry_run_2026-09-25_2/diag_host_fastdds/README.txt`](../dry_run_2026-09-25_2/diag_host_fastdds/README.txt)); that README and the third VM's treat the first VM's PASS as genuine. Unverified.
* `diag_cyclonedds_buffers/` reads the 360-degree recording only; the 120-degree one arrived in both settings (README there).
