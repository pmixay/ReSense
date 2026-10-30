# Bench of `main` 464f5bc on a 4-core team VM, 28 September

> **Purpose:** `scripts/bench_8core.sh` on the code that the 28.09 judgement used: frame rate, latency, CPU and memory of the
> node in Docker on both original bags, native and numpy, plus the offline timing. These are the figures the documents quote for the shipped path.
> **Audience:** team, jury · **Owner:** P1 (runs, timing, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: `summary.txt` compared with `summary.json`, `runs.tsv`, `facts.txt`, the log §3e table, `EXPERIMENTS.md` lines 180 and 183,
> `VM_GUIDE.md` line 31 and `ARCHITECTURE.md` line 271; one run (`dry_obstacle_native/run.txt`) read in full · **Status:** current record for the 27.09 detector (image `464f5bc`)

## 1. What was run, when

* Run: 2026-09-28T16:51:49+00:00 (`facts.txt`), team VM `compute-vm-2-2-90-ssd-1790359373525df`, Xeon Icelake, 8 vCPU = 4 cores x 2 threads, 15.6 GiB,
  Docker 29.8.1, image `7ddefbc6ffad` (resense 1.0.0, native kernels). Commit `464f5bc` (`facts.txt`, `dirty=0`); it resolves in this checkout.
  Git date of the folder: 2026-09-28 (`2d28d2a`, "VM runs of 2026-09-28 ... (#21)"), the same day.
* Unlike 25.09, the bags were played from the VM's disk (`/data/for_hackathon/...`, `runs.tsv`), not a RAM tmpfs; the disk is the one the log calls 79 MB/s.
* Lane: not recorded in the folder or the docs beyond "team VM" ([`vm_2026-09-28/summary.md`](../vm_2026-09-28/summary.md) indexes the day). Companion: [`dry_run_2026-09-28/`](../dry_run_2026-09-28/e2e_vm.txt).

## 2. Result

`summary.txt` (the numpy 360-degree run fails, so the script exits 1):

* `dry_obstacle_native` PASS: 200 of 201 frames, 10.0 fps, latency mean 53 / p95 63 / max 76 ms, 4 dropped, CPU 93 / 135 %, 1053 MiB.
* `dry_clear_native` PASS: 251 of 252, p95 44 ms, 0 dropped. `ct_image` 442 and `ct_stock` 446 of 453, both PASS, p95 62 ms.
* `dry_obstacle_numpy` FAIL: p95 103 ms and "freshness: no valid result in recording(s) 1"; `dry_clear_numpy` PASS (p95 71 ms).
* Offline node path at 360 degrees: 40.2 / 49.9 ms native, 76.3 / 89.0 ms numpy; stages 24.6 against 55.9 ms mean (`summary.txt`).

## 3. Supports

* [`EXPERIMENTS.md`](../../EXPERIMENTS.md) line 180 (10.0 fps at 360 degrees) and line 183 (numpy p95 103 ms, not real time); [`ARCHITECTURE.md`](../../ARCHITECTURE.md) line 271 (24.6 against 55.9 ms stages);
  [`VM_GUIDE.md`](../../VM_GUIDE.md) line 31 (native path met every timing criterion on 4 cores) and section 4.3.
* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3e "Bench" table (copied, all six rows match); [`vm_2026-09-28/summary.md`](../vm_2026-09-28/summary.md) line 45; index row [`../README.md`](../README.md) line 133.
* No row of `DECISIONS.md`, `BACKLOG.md`, `SCORECARD.md` or `CHANGELOG.md` names the folder.

## 4. Contents (40 files)

* `summary.txt`, `summary.json`, `runs.tsv`, `facts.txt`, `system.txt`; `build/run.txt` (exit 0, 2 s, layer cache).
* `dry_{obstacle,clear}_{native,numpy}/`: 4 folders of 4 files (`run.txt` with the checker output, `node_log.txt`, `status.jsonl.gz`, `docker_stats.tsv`).
* `ct_image/` (4 files), `ct_stock/` (6 files: adds `player_log.txt`, `listener_log.txt`); `offline/` (8 files, `node_*` and `stages_*`).

## 5. Caveats

* The "(4)" and "(5)" in the `dropped` column are drops after the first 5 s; the checker's criterion is drops after the end of the start-up catch-up and against the recording's own messages
  (`dry_obstacle_native/run.txt`: "4 frame(s) missing from the recording itself; 0 of its messages not processed").
* The page-cache state of the bags during the bench is not recorded in the folder. The bench shows 10.0 fps at 360 degrees; the cold runs of the same day
  in [`dry_run_2026-09-28/dry_obstacle.txt`](../dry_run_2026-09-28/dry_obstacle.txt) show "fps (last report): 3.0" because the VM disk (79 MB/s per the log) cannot feed the bag at 10 Hz.
  The log §3e "Reading" notes that the checker cannot see a player that falls behind. So read the 10.0 as the warm-cache figure (inference from the two folders, unverified for this run).
* Detector of 27.09 (`464f5bc`); later seals (29.09 and after) are not measured here. 4 physical cores, not the jury's 8.
