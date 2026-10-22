# First bench run on a team VM (8 vCPU = 4 physical cores), 25 September morning

> **Purpose:** the first run of `scripts/bench_8core.sh`: dry runs of both original bags on the native and the numpy path,
> two console tests, and the offline timing, as a stand-in for the jury's 8-core machine.
> **Audience:** team, jury · **Owner:** P1 (runs, timing, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: `summary.txt` compared with `summary.json`, `runs.tsv`, `facts.txt` and the log §3a table (all agree);
> the run's own verdict is FAIL, see section 2 · **Status:** dated record, superseded by [`bench_2026-09-25_2/`](../bench_2026-09-25_2/summary.txt) and [`bench_2026-09-28/`](../bench_2026-09-28/summary.txt)

## 1. What was run, when

* Run: 2026-09-25T10:31:24+00:00 (`facts.txt`, `summary.txt`), first team VM `compute-vm-8-16-100-ssd-1790323951159`,
  `scripts/bench_8core.sh` through the VM kit (`vm_result.txt`: "bench: FAIL (2026-09-25T10:38:30+00:00, 430 s)").
  The folder reached the repository later (`315ad1d` 2026-09-25, reverted in `6962519`, present again via `054a8ea` 2026-09-27); those are commit dates.
* Code: `7290873` (`facts.txt`, `dirty=0`; the full SHA `72908737f2f8d1caf2b513f730abd930c8dac20d` is in `system.txt`). That SHA is not an object in this checkout,
  so it is unverified here. The branch name in `system.txt` is omitted.
* Bags played from a RAM tmpfs (`/mnt/ramdata/for_hackathon/...`, `runs.tsv`). Image `3c711572c471`, native kernels present (`facts.txt`). Lane: not recorded in the folder or the docs.
* Companion folders of the same VM and day: [`dry_run_2026-09-25/`](../dry_run_2026-09-25/result.txt), [`vm_2026-09-25/`](../vm_2026-09-25/summary.md).

## 2. Result

Four of the six Docker runs FAIL, both console tests PASS (`summary.txt`):

* `dry_obstacle_native` 146 of 201 frames, 10.0 fps, latency mean 58 / p95 70 / max 171 ms, FAIL: "20 dropped input frames after the first 5 s".
* `dry_clear_native` FAIL: "4 false alarms on a bag expected to be clear (allowed 2)"; `dry_clear_numpy` FAIL with 3.
* `dry_obstacle_numpy` 116 of 201, 8.3 fps, p95 118 ms, FAIL (p95 and 45 drops).
* `ct_image` 378 of 453 and `ct_stock` 381 of 453, both PASS, p95 68 ms.
* Offline (`summary.txt`): node path at 360 degrees 43.4 / 54.7 ms mean / p95 native, 84.3 / 97.4 numpy.

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3a: its first table copies these rows (checked for all six Docker rows and the two 360-degree offline rows); cited at "raw: evidence/bench_2026-09-25/".
* CAPTAIN board C8 and action 7 ([`CAPTAIN_board_2026-09-28.md`](../../archive/CAPTAIN_board_2026-09-28.md), rows C8 and 7): C8 closed on this run. C8 quotes "p95 70 ms, max 98 ms"; the p95 is this folder's, the 98 ms max is that of
  [`dry_run_2026-09-25/highlights.txt`](../dry_run_2026-09-25/highlights.txt), while this folder's `dry_obstacle_native` max is 171 ms.
* [`DECISIONS.md`](../../DECISIONS.md) row 5 uses the second run (9.8 fps, p95 73 ms), not this one. Cited by [`vm_2026-09-25/summary.md`](../vm_2026-09-25/summary.md) (line 22) and by [`results/column_hold_2026-09-25.json`](../results/column_hold_2026-09-25.json) (captures of this folder).

## 4. Contents (41 files)

* `summary.txt`, `summary.json`: the bench table (written by `scripts/bench_summary.py`); `runs.tsv`: exit code and wall time per step; `facts.txt`, `system.txt`: machine, image, `lscpu`, commit list; `vm_result.txt`: the VM kit's verdict.
* `build/run.txt`: image build log (exit 0, 1 s, layer cache).
* `dry_obstacle_native/`, `dry_obstacle_numpy/`, `dry_clear_native/`, `dry_clear_numpy/`: 4 files each (`run.txt`, `node_log.txt`, `status.jsonl.gz`, `docker_stats.tsv`).
* `ct_image/` (4 files), `ct_stock/` (6 files, adds `player_log.txt`, `listener_log.txt`): console tests with the image's and a stock Fast DDS player.
* `offline/`: 8 files, `node_*` (`bench_node_path.py`) and `stages_*` (`resense bench`) for the two recordings, native and numpy.

## 5. Caveats

* The FAIL verdicts are against the drop criterion as it stood on 25.09. `5be4143` (not an object in this checkout) then changed it to count drops after the end of the start-up catch-up and against the recording's own messages; the log §3a says 16 of the 20 drops were deliberate catch-up skips and 4 are missing from the recording.
  The raw files here keep the old verdict.
* 4 physical cores, not the jury's 8 (`summary.txt` says so). The VM disk is slower than the 360-degree bag needs, hence the RAM tmpfs.
* The 3 to 4 alarm frames on `roundT_doubleT` (`summary.txt`) are a different result from the offline evaluation (2 frames at 128.3-130.2 m); the log §3a analyses it (111.0-114.9 m, fixed by `tracking.column_hold`).
