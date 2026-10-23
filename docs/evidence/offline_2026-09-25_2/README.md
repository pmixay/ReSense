# Offline rehearsal on the second team VM (25.09, code 76bf24e)

> **Purpose:** raw output of the offline rehearsal at `76bf24e` after the drop and false-alarm
> fixes: IPv4 and IPv6 blocked, archive loaded after every `resense` image was deleted, both dry
> runs and the README jury console.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from the named files; nothing re-run; the "Fast DDS"
> label of the jury console is contradicted by a later note (section 5) · **Status:** historical
> (superseded by `../offline_2026-09-28/`)

## 1. What was run, and when

* The offline rehearsal of VM_GUIDE §5 on the second team VM, 2026-09-25, block on 15:14:30,
  restored 15:18:36 UTC (`steps.txt`). Image archive `resense-image-1.0.0.tar.gz`
  (475515293 bytes, from [`../export_2026-09-25_2/`](../export_2026-09-25_2/README.md)), code
  `76bf24ebac2d586f092b7c7493a5cb363fa1bdf1` (commit label printed by `dry_obstacle.txt`).
* No host was allowed; the restore timer was armed for 30 min; the block was restored after 4 min
  (`steps.txt`).
* Git date is a merge date. Lane: not recorded in the folder or the docs.

## 2. Result

* `dry_obstacle` PASS: 146 status messages, 137 alarm frames, 55.6 to 56.5 m, p95 73 ms, start-up
  catch-up ended at +7.7 s, 4 frames missing from the recording itself, 0 messages unprocessed
  (`dry_obstacle.txt`).
* `dry_clear` PASS: 235 status messages, 0 alarm frames, p95 49 ms, 0 frames dropped after 5 s
  (`dry_clear.txt`).
* `jury_console` FAIL, exit 1: only 6 status messages (50 expected), 0 alarm frames, no obstacle
  distance; the node's log carries the `net.core.rmem_max = 212992` warning
  (`jury_console.txt`, `jury_console_node_log.txt`).
* Block checks: IPv4 0 of 3 connections succeeded, IPv6 no route, `OK: no internet from here`
  (`check_no_network.txt`); a new SSH login during the block is stated by the docs, not in this
  folder (unverified here).

## 3. What it supports

* [`archive/EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) lines 3159-3180
  (§3b, confirmation re-run): 55.6 to 56.5 m, p95 73 ms, catch-up end +7.7 s and 4 missing frames
  all match this folder. The log's "6 of 201 clouds" is not in this folder (it has "6 status
  messages"); the 6 of 201 figure is in
  [`../dry_run_2026-09-25_2/diag_host_fastdds/README.txt`](../dry_run_2026-09-25_2/diag_host_fastdds/README.txt).
* [`archive/CAPTAIN_board_2026-09-28.md`](../../archive/CAPTAIN_board_2026-09-28.md) C25; the
  transport fixes: [`../dry_run_2026-09-25_3/README.txt`](../dry_run_2026-09-25_3/README.txt).
* [`../README.md`](../README.md) section 2 row for the second team VM.

## 4. Contents (17 files)

| file | what |
|---|---|
| `steps.txt` | timeline of the run (6 lines plus restore) |
| `rules_ipv4.txt`, `rules_ipv6.txt`, `check_no_network.txt` | block rules with packet counters, the no-network check |
| `image_rm.txt` | image removal |
| `dry_obstacle.txt`, `dry_clear.txt` | checker output (include the sha256 check and `docker load`) |
| `off_obstacle_*`, `off_clear_*` (2 node logs, 2 `status.jsonl.gz`) | node logs and per-frame status of the two dry runs |
| `jury_console.txt`, `jury_console_{decision,nearest_distance,node_log,player_log}.txt`, `jury_console_status.jsonl.gz` | checker output and logs of the host console |

## 5. Caveats

* The jury console was started as "stock RMW"; a later note says the VM had no Fast DDS RMW
  installed, so that player was CycloneDDS
  ([`../dry_run_2026-09-25_3/README.txt`](../dry_run_2026-09-25_3/README.txt)). The files here do not
  carry that correction. The cause given for the FAIL is the 212992-byte receive buffer
  (`../dry_run_2026-09-25_2/diag_host_fastdds/README.txt`; not re-verified here).
* Superseded by [`../offline_2026-09-28/`](../offline_2026-09-28/README.md).
