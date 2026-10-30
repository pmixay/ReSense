# First team VM, 25.09 morning (code 7290873): setup, data inventory and the collected summary

> **Purpose:** the machine facts, data inventory and the packed summary of the first run of the VM
> kit on a team VM: setup, data fetch, dry runs, bench, gate, export and offline rehearsal.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from `summary.md` and the other files here; the
> per-run raw folders were not re-read for this README except those with their own README ·
> **Status:** historical (first run; failures fixed the same day, see section 5)

## 1. What was run, and when

* The VM kit `scripts/vm/run_plan.sh` (removed from the repository on 25.09; the procedure is now
  [`VM_GUIDE.md`](../../VM_GUIDE.md) §3-§5) on the first team VM: Intel Xeon (Icelake), 8 vCPU = 4
  physical cores, 15.6 GiB, Ubuntu 22.04.5, kernel 5.15.0-191 (`summary.md`, `setup_resources.txt`).
* Date: 2026-09-25. Setup report 09:13:48 UTC (`setup_summary.txt`), data inventory 09:23:19
  (`fetch_inventory.txt`), dry run ended 09:35:24, gate 09:53:01, export 09:53:09, offline 09:58:04,
  bench 10:38:30, `collect` 10:39:02 (`summary.md`). Code `72908737f2f8d1caf2b513f730abd930c8dac20d`
  (`7290873`), clean worktree. The bags were played from a RAM tmpfs (see
  `../offline_2026-09-25/jury_console/check.txt`).
* The git date is a merge date. Lane: not recorded in the folder or the docs.

## 2. Result

`summary.md` table: setup READY; fetch DATA READY (all six bags, `cloud_with_fake_obj` 1510 frames,
ride cache 221 of 221 split files, `fetch_inventory.txt`); dryrun FAIL (546 s); bench FAIL (430 s);
gate PASS (536 s); export PASS (550 s); offline FAIL (243 s). Failures, as printed in `summary.md`:
`dry_obstacle` "20 dropped input frames after the first 5 s > 0"; `dry_clear` "3 false alarms on a
bag expected to be clear (allowed 2)"; `host_cyclonedds` "0 alarm frames, expected >= 3"; the
console tests and `host_fastdds` PASS (137 alarm frames). Ride replay SKIPPED (the 20-minute bag
is not kept on this disk).

## 3. What it supports

* [`archive/EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) §3a (line 2868) and §3b
  lines 3128-3153: the same numbers and the fixes (start-up catch-up, `column_hold`, receive buffer).
* [`archive/CAPTAIN_board_2026-09-28.md`](../../archive/CAPTAIN_board_2026-09-28.md) C7, C25;
  [`../README.md`](../README.md) section 2 row for the first team VM.
* Raw folders it points to: [`../dry_run_2026-09-25/`](../dry_run_2026-09-25/), [`../bench_2026-09-25/`](../bench_2026-09-25/),
  [`../gate_2026-09-25/`](../gate_2026-09-25/README.md), [`../export_2026-09-25/`](../export_2026-09-25/README.md),
  [`../offline_2026-09-25/`](../offline_2026-09-25/README.md).
* No DECISIONS, BACKLOG or SCORECARD row names this folder (grep, 2026-10-22).

## 4. Contents (5 files)

| file | what |
|---|---|
| `summary.md` | packed summary of every run (259 lines): table, per-run printed checks, "before committing" scan |
| `setup_summary.txt`, `setup_resources.txt` | readiness report and resource / internet probe |
| `fetch_plan.txt`, `fetch_inventory.txt` | disk plan and the inventory of `/data` after the fetch |

## 5. Caveats

* Failing runs: superseded by the fixes of 25.09 and confirmed on the second team VM
  (`../offline_2026-09-25_2/`, `../gate_2026-09-25_2/`).
* `host_fastdds` is labelled stock Fast DDS; the player's RMW was set by variable
  (`../dry_run_2026-09-25/host_fastdds.txt` line 1). Later notes found that the hosts of the second
  and third VM had no Fast DDS RMW; whether this VM's player really loaded Fast DDS is
  unverified.
* The summary names a branch (omitted here) and the VM hostname (not repeated).
