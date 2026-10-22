# Confirmation bench run on a second team VM, 25 September afternoon

> **Purpose:** the repeat of `scripts/bench_8core.sh` after the start-up catch-up and drop-counting fixes, on a second VM
> of the same type: the figures that the documents quote for the 360-degree frame rate and p95 latency on 4 physical cores.
> **Audience:** team, jury · **Owner:** P1 (runs, timing, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: `summary.txt` compared with `summary.json`, `runs.tsv`, `facts.txt`, the log §3a re-run table
> and `DECISIONS.md` row 5 (all agree); the node and checker output of `dry_obstacle_native/run.txt` read ·
> **Status:** dated record, superseded for the shipped path by [`bench_2026-09-28/`](../bench_2026-09-28/summary.txt)

## 1. What was run, when

* Run: 2026-09-25T14:51:51+00:00 (`facts.txt`), second team VM `compute-vm-8-16-100-ssd-1790344754523`, Xeon Icelake 2.0 GHz,
  8 vCPU = 4 cores x 2 threads, 15.6 GiB, Docker 29.8.1, image `e825c96cf0f2` with native kernels (`facts.txt`).
  Bags from a RAM tmpfs (`runs.tsv`). The git dates of the folder (`315ad1d`, revert `6962519`, `054a8ea` on 2026-09-27) are commit dates.
* Code: `76bf24e` (`facts.txt`, `dirty=0`; full SHA in `system.txt`). That SHA is not an object in this checkout, so it is unverified here.
  Lane: not recorded in the folder or the docs; the log §3a calls it the "confirmation re-run" after the fixes.
* Companion folders: [`dry_run_2026-09-25_2/`](../dry_run_2026-09-25_2/dry_obstacle.txt), [`vm_2026-09-25_2/`](../vm_2026-09-25_2/machine.txt).

## 2. Result

`summary.txt`: the native path passes everything, numpy fails at 360 degrees.

* `dry_obstacle_native` PASS: 147 of 201 frames, 9.8 fps, latency mean 60 / p95 73 / max 84 ms, 51 dropped (the checker counts 4 after +7.7 s, `dry_obstacle_native/run.txt`).
* `dry_clear_native` PASS, 234 of 252, p95 48 ms. `dry_clear_numpy` PASS (p95 79 ms).
* `dry_obstacle_numpy` FAIL: 120 of 201, 8.3 fps, p95 119 ms, "12 frames of the recording not processed after +10.6 s".
* `ct_image` 382 and `ct_stock` 384 of 453, both PASS, p95 68 and 69 ms.
* Offline node path at 360 degrees: 45.1 / 56.4 ms native, 90.9 / 105.5 ms numpy (`summary.txt`).

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3a "Confirmation re-run": its table copies these rows (checked, all six Docker rows).
* [`DECISIONS.md`](../../DECISIONS.md) row 5: "9,8 frames/s, p95 73 ms native; numpy p95 119 ms: FAIL" are this folder's numbers; row 5 cites the log §3a.
* CAPTAIN board C8 and action 7 ([`CAPTAIN_board_2026-09-28.md`](../../archive/CAPTAIN_board_2026-09-28.md)), [`VM_GUIDE.md`](../../VM_GUIDE.md) §4.3 (what `bench_<date>/` must contain).
  `BACKLOG.md`, `SCORECARD.md` and `CHANGELOG.md` do not name the folder.

## 4. Contents (40 files)

* `summary.txt`, `summary.json`, `runs.tsv`, `facts.txt`, `system.txt`: as in [`bench_2026-09-25/`](../bench_2026-09-25/README.md) (this folder has no `vm_result.txt`).
* `build/run.txt`; `dry_{obstacle,clear}_{native,numpy}/` (4 folders, 4 files each); `ct_image/` (4 files), `ct_stock/` (6 files); `offline/` (8 files).

## 5. Caveats

* The PASS is against the redefined drop criterion (`5be4143`, not an object in this checkout: drops counted after the end of the start-up catch-up and against the recording's own
  messages). The `dropped` column of `summary.txt` still shows the old window: "51 (20)" for `dry_obstacle_native` is PASS here. The log §3a says so
  ("would have failed the first one").
* 4 physical cores, not the jury's 8. Numpy is not the shipped path.
