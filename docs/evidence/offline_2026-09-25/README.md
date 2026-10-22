# Offline rehearsal on the first team VM (25.09, code 7290873)

> **Purpose:** raw output of the first offline rehearsal: outbound traffic blocked on the VM, the
> image archive loaded after all images were deleted, both original bags and the README jury
> commands run.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from the named files; the 54 blocked attempts counted
> in `blocked_attempts.txt`; nothing re-run · **Status:** historical (drop and false-alarm criteria
> failed here and were fixed later the same day; see `../offline_2026-09-25_2/`)

## 1. What was run, and when

* `scripts/vm/run_plan.sh offline --minutes 30` on the first team VM (8 vCPU = 4 physical cores),
  2026-09-25, started 09:54:01 UTC, ended 09:58:04 (`meta.txt`, `window.txt`, `result.txt`). Code
  `72908737f2f8d1caf2b513f730abd930c8dac20d` (`7290873`). Block: iptables chain on IPv4 and IPv6,
  SSH kept, no host allowed, automatic restore timer for 10:24:01, restored by hand 09:58:03
  (`window.txt`, `rules.txt`).
* Archive loaded: the one of [`../export_2026-09-25/`](../export_2026-09-25/README.md).
* The bags were played from a RAM tmpfs (`jury_console/check.txt`, path `/mnt/ramdata/...`).
* Git date is a merge date. Lane: not recorded in the folder or the docs.

## 2. Result

`offline: FAIL` (`result.txt`): block, image removal and image load PASS (load 29 s);
`dry_obstacle` FAIL: 22 dropped input frames after the first 5 s (`dry_obstacle.txt`);
`dry_clear` FAIL: 3 alarm frames on a bag expected clear, 2 allowed (`dry_clear.txt`);
`jury_console` PASS: 134 `STOP`, obstacle 55.7 to 56.5 m, first `STOP` at +2.3 s, p95 71 ms
(`jury_console.txt`). 54 outbound attempts were blocked and logged, 7 by uid 1000 and 47 by uid 101
(`result.txt`; `blocked_attempts.txt` has 54 lines); they include the checker's own probes.

## 3. What it supports

* [`../vm_2026-09-25/summary.md`](../vm_2026-09-25/summary.md) row "offline" (CAPTAIN C25).
* [`archive/EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) lines 3128-3153 (§3b)
  quote these numbers (134 `STOP`, +2.3 s, p95 71 ms, 22 dropped, 3 alarm frames); they match.
* [`archive/CAPTAIN_board_2026-09-28.md`](../../archive/CAPTAIN_board_2026-09-28.md) C25.
* [`DECISIONS.md`](../../DECISIONS.md) row 7 (offline stand) lists offline dry runs on the VM (25.09) among its evidence (Russian text).
* [`../results/column_hold_2026-09-25.json`](../results/column_hold_2026-09-25.json) lists
  `offline_2026-09-25/dry_clear` among the roundT_doubleT captures it uses for `tracking.column_hold`.
* [`../../VM_GUIDE.md`](../../VM_GUIDE.md) §5 is the current procedure.

## 4. Contents (28 files)

| path | what |
|---|---|
| `result.txt`, `steps.tsv`, `highlights.txt`, `notes.txt`, `meta.txt`, `run_log.txt` | step results, extracts, machine facts, full log |
| `apply_block.sh`, `restore_block.sh` | the generated block and restore scripts |
| `rules.txt`, `window.txt`, `blocked_attempts.txt`, `verify_blocked.txt` | iptables chains, window times, 54 kernel log lines, the no-network check |
| `remove_images.txt`, `load_image.txt` | image removal and archive load |
| `dry_obstacle.txt`, `dry_clear.txt`, `jury_console.txt` | checker output of the three runs |
| `dry_obstacle/`, `dry_clear/` | `node_log.txt`, `status.jsonl.gz` each |
| `jury_console/` | 7 files: check, decision, docker stats, nearest distance, node and player logs, status |

## 5. Caveats

* Superseded: the drop and false-alarm failures were fixed the same day; confirmation in
  [`../offline_2026-09-25_2/`](../offline_2026-09-25_2/README.md).
* The jury console player was started with `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
  (`jury_console/check.txt`); which library it actually loaded was not recorded here. The later
  correction (a host without a Fast DDS RMW ran CycloneDDS) concerns the second and third VM
  (`../dry_run_2026-09-25_3/README.txt`); for this VM it is unverified.
* `blocked_attempts.txt` holds the VM's hostname; not repeated here.
