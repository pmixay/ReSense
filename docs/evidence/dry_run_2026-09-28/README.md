# Dry runs, host consoles and end-to-end latency of `main` 464f5bc on a 4-core team VM, 28 September

> **Purpose:** the `--no-cache` build, the dry runs of both original bags (once as written, then warm and cold twice each), the Docker console tests,
> five host consoles (README jury steps with stock Fast DDS, CycloneDDS, UDP and shared-memory mode), the detector-input identity check and the end-to-end latency table.
> **Audience:** team, jury · **Owner:** P1 (runs, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: all 17 checker files read for verdict, alarm frames, latency and drops; the loaded RMW of the five host consoles read in `*_console4.txt`;
> `e2e_vm.txt` compared with the log §3e table; `e2e_vm.py` not re-run · **Status:** current record for the 27.09 detector (image `464f5bc`)

## 1. What was run, when

* Run: 2026-09-28, node log time stamps 16:32 to 16:51 UTC (ROS time); the bench of the same VM follows at 16:51:49 ([`bench_2026-09-28/`](../bench_2026-09-28/summary.txt)).
  Git date of the folder: 2026-09-28 (`2d28d2a`, "VM runs of 2026-09-28 ... (#21)"), the same day.
* Code: `464f5bc` (first line of `build_no_cache.txt`; resolves in this checkout). Team VM, user `kladmin`, 4 physical cores ([`vm_2026-09-28/summary.md`](../vm_2026-09-28/summary.md) indexes the day).
  Bags played from the VM's disk with `--read-ahead` 10 ("rosbag2 read-ahead queue: 10 messages", printed by the 10 dry / warm / cold run files). Lane: not recorded in the folder or the docs.
* "warm" = recording read into the page cache just before, "cold" = page cache dropped (log §3e); this is not written in the folder's files except in their names.

## 2. Result

All 17 checker files (2 + 4 + 4 + 2 + 5 runs) end PASS (verdict lines read; `fast_input.txt` and `dry_clear_replay.txt` have their own checks, below).

* 360 degrees (`dry_obstacle.txt`, `warm_obstacle_*`, `cold_obstacle_*`): 189-190 alarm frames at 55.5-56.6 m, 4 drops (the recording's own missing frames), "freshness contract: PASS".
  Warm: 10.0 fps, decode + detect p95 63 ms, end-to-end p95 82 and 81 ms (`warm_obstacle_1.txt`, `_2.txt`). Cold: "fps (last report): 3.0", end-to-end p95 88 and 96 ms (`cold_obstacle_*.txt`).
* 120 degrees (`dry_clear.txt`, `warm_clear_*`, `cold_clear_*`): 0 alarm frames, 0 drops; `dry_clear_replay.txt`: node 252 frames, replay 252 frames, 0 alarm frames each.
* Host consoles (`host_jury`, `host_fastdds`, `host_cyclonedds`, `host_shm`, `host_shm_cyclonedds`): each 190 alarm frames, 195 STOP decisions, 453 of 453 frame results in `e2e_vm.txt`.
  Loaded RMW (`*_console4.txt`): `librmw_fastrtps_cpp.so` (fastrtps 2.6.12) for `host_jury`, `host_fastdds`, `host_shm`; `librmw_cyclonedds_cpp.so` with `libddsc.so.0.10.5` for `host_cyclonedds`, `host_shm_cyclonedds`; `rmem_max` 33554432 for `host_jury`, `host_cyclonedds`, `host_shm_cyclonedds`, 212992 for `host_fastdds` and `host_shm`.
* `ct_stock.txt`, `ct_shm.txt` PASS (stock Fast DDS 2.6.12 player in Docker, 189 and 186 alarm frames). `fast_input.txt`: "201 of 201 frames identical" and "252 of 252 frames identical".

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3e "Dry runs and end to end": its table of warm / cold runs and the host-console sentence match these files. Also §3b "Re-run 28.09".
* [`vm_2026-09-28/summary.md`](../vm_2026-09-28/summary.md) lines 36-37 (build 534 s, both dry runs PASS); index row [`../README.md`](../README.md) line 132.
* `DECISIONS.md` and `BACKLOG.md` do not name the folder; row 6 of [`DECISIONS.md`](../../DECISIONS.md) (transport) is the question the host consoles answer. [`EXPERIMENTS.md`](../../EXPERIMENTS.md) line 177 quotes the 81-82 ms (warm) and 88-96 ms (cold) end-to-end figures and cites `vm_2026-09-28/summary.md`.

## 4. Contents (92 files)

* `build_no_cache.txt` (`docker build --no-cache`, "build exit 0, 534 s", image 1.0.0 with native kernels); `fast_input.txt`, `fast_input.json` (detector input identity per frame); `e2e_vm.py`, `e2e_vm.txt` (end-to-end age of current and of all frame results; the script also reads [`../offline_2026-09-28/`](../offline_2026-09-28) and `../node_input_2026-09-28/e2e_all_frames.py`).
* `dry_obstacle*`, `dry_clear*`, `dry_clear_replay.txt`: the run "as written" in VM_GUIDE §4.1 (3 files each; replay 1 file).
* `warm_{obstacle,clear}_{1,2}*`, `cold_{obstacle,clear}_{1,2}*`: 8 runs, 3 files each (checker text, node log, status).
* `ct_stock*` (5 files), `ct_shm*` (6 files): Docker console tests.
* 5 host consoles, 9 files each (45 in all): checker text, `_console4`, `_decision`, `_nearest_distance`, `_ls`, `_ls_after`, node and player logs, `status.jsonl.gz`.

## 5. Caveats

* Cold 360-degree runs play at 3.0 fps because the VM disk reads 79 MB/s (log) against about 225 MB/s needed; they PASS because end-to-end age starts at the player's publication. Log §3e says so:
  a player falling behind real time is invisible to the checker. The cold "current" results are 187-188 of 201.
* The end-to-end p95 over all frame results (start-up included) is 725 to 944 ms at 360 degrees in the one-container runs (`e2e_vm.txt`, "all" column) against 77 to 126 ms in the host consoles; the 81-82 ms figure is the current results only.
* The columns of `e2e_vm.txt` are `n: median / p95 / max` in ms (the format string of `stats()` in `../node_input_2026-09-28/e2e_all_frames.py`).
* `build_no_cache.txt` ends with image id `7dbd6a26d2bc...`; the bench of the same afternoon recorded image `7ddefbc6ffad` (`bench_2026-09-28/facts.txt`). A second build between the two is likely; not reconciled.
* CycloneDDS at `rmem_max` 212992 was not repeated on 28.09 (log §3b). Detector of 27.09; later seals are not run here.
