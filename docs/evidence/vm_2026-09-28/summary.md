# ReSense VM runs, 2026-09-28 (`main` at `464f5bc`)

Every step of [`../../VM_GUIDE.md`](../../VM_GUIDE.md) §1–§5 on one team VM, run by an agent over
SSH, code `464f5bc6b193ff3dcc4bd7d30b03745d8d260f6a` (PR #20 merged: the node's fast input path).
No code, config or test was changed on the VM. The scripts that ran the steps are in `scripts/`
(`r_runs.sh` one subcommand per run, `r_chain.sh` their order, `r_offline.sh` §5, `r_data_*.sh` §2).

## Machine

The third team VM of 25.09 (its folders `*_2026-09-25_3`), reused: Yandex Cloud, Intel Xeon
(Icelake), **8 vCPU = 4 physical cores × 2 threads**, 15.6 GiB, Ubuntu 22.04.5, kernel
5.15.0-191, Docker 29.8.1, CPU steal 0; ROS 2 Humble on the host with `rmw_fastrtps_cpp` 6.2.10
(fastrtps 2.6.12) and `rmw_cyclonedds_cpp` 1.3.5; `rosbags` 0.11.5 in the venv. The network disk
reads **79 MB/s** sequentially (direct I/O); the bags were played from it (no RAM tmpfs as on
25.09). All in `machine.txt`.

**Setup.** The clone was on `claude/nifty-pascal-lzgl78` at `d4b396e`. Its two untracked 25.09
evidence folders were moved out of the clone (identical to the committed ones but for the later
edited `README.txt`). `git fetch` from GitHub stalled on the VM's link, so `main` came as a git
bundle over SSH (`git bundle verify`, fast-forward to `464f5bc`, worktree clean). Then
`pip install -e ".[dev]"`, `rosbags==0.11.5`, `scripts/build_native.sh`: native kernels.

**Data (§2).** The organizers' zip (3.94 GB, Google Drive) unpacked to all six recordings (kept),
`cloud_with_fake_obj` from Yandex Disk, the ride streamed split by split (221 of 221, no failed
split): every count as §2.4 (201, 345, 252, 268, 545, 877, 1 510, 11 271), all six `metadata.yaml`
identical to `bag_metadata/` (`data_recordings.txt`, `data_ride.txt`).

**Tests.** `python -m pytest -q`: **754 passed, 6 subtests passed** in 306 s, run while the data was
prepared (`pytest.txt`).

## Runs

| step | folder | result |
|---|---|---|
| §3 machine facts | `vm_2026-09-28/machine.txt` | 4 physical cores, steal 0, `rmem_max` 212992, disk 79 MB/s |
| §4.1 `--no-cache` build | `dry_run_2026-09-28/build_no_cache.txt` | exit 0, 534 s (while the data was prepared), native kernels in the image |
| §4.1 dry run, both original bags | `dry_run_2026-09-28/dry_{obstacle,clear}.txt`, `dry_clear_replay.txt` | **PASS / PASS**: STOP 55.5–56.6 m, decode + detect p95 72 ms, 0 of the recording's messages unprocessed; 0 alarm frames, replay 0 = node 0 |
| §4.1 cold-cache procedure, twice | `cold_{obstacle,clear}_{1,2}.txt` | **PASS × 4**; 360° end to end p95 88 / 96 ms |
| same, recording in the page cache, twice | `warm_{obstacle,clear}_{1,2}.txt` | **PASS × 4**; 360° end to end p95 82 / 81 ms at 10.0 fps |
| PR #20 fast input path, in the image | `fast_input.txt`, `fast_input.json` | **PASS**: 201 / 201 and 252 / 252 frames identical |
| §4.2 stock player in Docker | `ct_stock*.txt` | **PASS** |
| §4.2 README jury steps 0, 2–5 from the host | `host_jury*.txt` | **PASS**: stock Fast DDS 2.6.12, uid 1000, 453 / 453 frames, 195 `STOP` |
| §4.2 host, Fast DDS at 212992 / CycloneDDS at 32 MiB | `host_fastdds*.txt`, `host_cyclonedds*.txt` | **PASS / PASS** |
| §4.6 `RESENSE_DDS=shm`: Fast DDS at 212992, CycloneDDS at 32 MiB, Docker | `host_shm*.txt`, `host_shm_cyclonedds*.txt`, `ct_shm*.txt` | **PASS / PASS / PASS**; the Fast DDS player maps the node's `root 666 /dev/shm/fastrtps_port7411` |
| §4.3 bench | `bench_2026-09-28/` | **`dry_obstacle_native` PASS** (10.0 fps, p95 63 ms), every native run and both console tests PASS; `dry_obstacle_numpy` FAIL (p95 103 ms, no current result), so the script exits 1 |
| §4.4 gate with the ride and set F | `gate_2026-09-28/` | **GATE PASS**: every metric identical to `regression_baseline_2026-09-27_quality.json` but 16 informational latency rows; 7 min at `--jobs 4` |
| §4.5 export and load | `export_2026-09-28/` | **PASS**: 475 947 817 bytes, sha256 `1019cd3c…a9d8` (`archive.txt`) |
| §5 offline, pass 1 | `offline_2026-09-28/` | block PASS (IPv4 and IPv6, a new SSH login worked, containers on Docker's bridge blocked too); archive loaded; `dry_obstacle` PASS; **`dry_clear` FAIL**: 10 frames skipped by the catch-up after a 1.4 s input stall; README jury console PASS (381 / 453 frames: 72 skipped after a 1.2 s input hole); `play_bag.sh --archive` exit 0 |
| §5 offline, pass 2, recordings read into the page cache first | `offline_2026-09-28/warm_bags/` | **all PASS**: both dry runs (0 unprocessed), jury console 453 / 453 frames, 195 `STOP`; `play_bag.sh --archive` exit 0 |

Both offline windows were restored by hand (6 min 43 s and 5 min 48 s; the 30-minute timer was
stopped afterwards); `rules_*.txt` count 1 210 and 1 148 rejected IPv4 packets (IPv6: 0) and 51
from Docker's bridge per window; the rules count, they do not log destinations. Nothing was allowed
out (no step 3b): the agent's own connection was incoming SSH.

## Findings

1. **Storage, not the node, limits playback from this VM's disk.** The 360° recording is 4.5 GB
   for 20 s (~225 MB/s at rate 1.0); read from the 79 MB/s disk it plays in 62.5–62.7 s (~3 fps;
   wall times from `freshness.evaluated_at_utc_s`), in 19.1–19.4 s from the page cache. The 120°
   recording (~76 MB/s) plays in real time at the disk's limit; in offline pass 1 (most likely
   no longer in the page cache: the gate had read 20 GB of frame caches since, then the export build
   and the image load) the player stalled for 1.2–1.4 s and the node's catch-up then skipped frames, as designed. Pass 2, identical but for the
   recordings read first, passes everything. The same VM type on 25.09 played the bags from a RAM
   tmpfs for this reason (EXPERIMENTS §3a).
2. **The check does not see a player that falls behind real time.** `check_dry_run.py` PASSes the
   ~3 fps disk-bound runs: the end-to-end age starts at the player's publication, and every message
   is eventually processed. A wall-clock playback rate in its output would expose it. On the
   organizers' stand the bag's storage speed is unknown.
3. **End to end at 360° is under the 100 ms period on this machine** when the recording arrives at
   10 Hz: p95 81–82 ms (warm dry runs), 71–84 ms in the host consoles but for one shm-mode run at
   113 ms; decode + detect p95 63 ms. Over every frame result, start-up included (`e2e_vm.txt`), the
   one-container dry runs reach 0.7–0.9 s p95 at 360°, the host consoles 75–126 ms with the
   recordings in the page cache.
4. **The node exits with code 1 on Ctrl+C** (every host run, and on 25.09): rclpy's SIGINT handler
   has shut the context down, then `rclpy.shutdown()` in `main()`'s `finally`
   (`ros2_ws/src/resense_ros/resense_ros/detector_node.py`) raises `RCLError: rcl_shutdown already
   called`, and launch prints `[ERROR] … process has died … exit code 1` after a traceback. The
   work is done by then; `rclpy.try_shutdown()` would end it cleanly. Not changed here (evidence only).
5. **The numpy fallback is not real time at 360° on 4 cores** (91 ms mean per frame at a 100 ms
   period; its start-up catch-up never ends), as on 25.09. The image ships the native kernels.
6. `build_no_cache.txt` repeats its last lines: the harness script was edited while that build ran
   and bash re-read it. The build ran once (exit 0, 534 s).
