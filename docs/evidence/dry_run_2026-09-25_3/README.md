# Transport runs on a third team VM: Fast DDS and CycloneDDS, UDP and shared memory, 25 September evening

> **Purpose:** the host-console runs with a verified stock Fast DDS player and with a CycloneDDS player, over the node's default UDP profile and its opt-in
> shared-memory mode, at Ubuntu's `rmem_max` 212992 and at 32 MiB. They correct the "stock Fast DDS fails" reading of the second VM.
> **Audience:** team, jury · **Owner:** P1 (runs, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: the table of `README.txt` (the folder's own) compared with the 11 checker files (result, `rmem_max`, STOP counts, loaded RMW);
> two headers disagree with it, see section 5 · **Status:** dated record, the evidence for [`DECISIONS.md`](../../DECISIONS.md) row 6

The folder has its own plain-text README, [`README.txt`](README.txt), written on the day. This file indexes it and checks it.

## 1. What was run, when

* Third team VM, user `kladmin`, 8 vCPU = 4 physical cores; node log time stamps 2026-09-25 18:30 to 18:44 UTC. Git date of the folder: `054a8ea`, 2026-09-27 (a commit date).
* Code: `d4b396e` (`README.txt`: the transport fixes of `be39362`, README jury step 0 and opt-in `RESENSE_DDS=shm`). The SHAs `d4b396e` and `be39362` are not objects in this checkout; unverified here.
  Image built by `dry_run.sh --no-cache` as the VM's first build; bags from a RAM tmpfs. Driver script: `g_fix.sh`. Lane: not recorded in the folder or the docs.
* Companion: [`vm_2026-09-25_3/machine.txt`](../vm_2026-09-25_3/machine.txt); [`../README.md`](../README.md) line 146.

## 2. Result

From the checker files (each read for `rmem_max`, STOP count and verdict):

* `dry_obstacle.txt` PASS (145 alarm frames at 55.6-56.5 m, p95 65 ms, first STOP +1.4 s, 4 drops after +6.8 s); `dry_clear.txt` PASS (0 alarm frames, p95 46 ms).
* Stock Fast DDS (`libfastrtps.so.2.6.12` recorded in the `*_console4.txt` files), UDP, `rmem_max` 212992: `host_fastdds_udp.txt` PASS 152 alarm frames, `host_fastdds_udp2.txt` PASS 150.
  Shared-memory mode, 212992: `host_shm_fastdds.txt` PASS 148, `host_shm_fastdds2.txt` PASS 146 (player maps the node's `root 666 /dev/shm/fastrtps_port7411`). At 32 MiB, README step 0: `host_jury_step0_fastdds.txt` PASS 153.
* CycloneDDS: shared-memory mode at 212992 (`host_shm_cyclonedds_rmem212992.txt`) FAIL, "1 recordings seen, expected 2", 4 alarm frames; at 32 MiB `host_shm_cyclonedds.txt` PASS 153, `host_jury_step0_cyclonedds.txt` PASS 152.
* `ct_shm.txt` (stock Fast DDS player in Docker, shm mode, 212992) PASS, 149 alarm frames.

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3b "Transport fixes on a third team VM" (its table copies `README.txt`); [`DECISIONS.md`](../../DECISIONS.md) row 6; [`CHANGELOG_2026-09.md`](../../archive/CHANGELOG_2026-09.md) line 545 (the correction);
  [`VM_GUIDE.md`](../../VM_GUIDE.md) §4.6 (shared-memory mode). `vm_2026-09-28/scripts/r_runs.sh` reuses `g_fix.sh` ([`../vm_2026-09-28/scripts/r_runs.sh`](../vm_2026-09-28/scripts/r_runs.sh)).
* It is the source of the CORRECTION lines in [`dry_run_2026-09-25_2/`](../dry_run_2026-09-25_2/diag_host_fastdds/README.txt) and of the opt-in status of `RESENSE_DDS=shm`.

## 4. Contents (86 files)

* `README.txt` (day-of summary), `g_fix.sh` (the driver).
* `dry_obstacle*`, `dry_clear*`: checker text, node log, `status.jsonl.gz` (6 files).
* `ct_shm*`: checker text, listener / node / player logs, `/dev/shm` listing, status (6 files).
* 8 host-console runs (`host_fastdds_udp`, `host_fastdds_udp2`, `host_shm_fastdds`, `host_shm_fastdds2`, `host_jury_step0_fastdds`, `host_jury_step0_cyclonedds`, `host_shm_cyclonedds`, `host_shm_cyclonedds_rmem212992`),
  9 files each (72 in all): checker text, `_console4` (loaded RMW and mapped ports), `_decision`, `_nearest_distance`, `_node_log`, `_player_log`, `_status.jsonl.gz`, `_ls`, `_ls_after` (`/dev/shm` before and after).

## 5. Caveats

* The CycloneDDS identity of the player in `host_jury_step0_cyclonedds` and `host_shm_cyclonedds_rmem212992` is not shown by the data files. `README.txt` says it was checked in `/proc/<pid>/maps`
  (`librmw_cyclonedds_cpp.so`, `libddsc.so.0.10.5`), but their `*_console4.txt` hold only "player pid N (kladmin):" with no library line, and the checker headers say "RMW rmw_fastrtps_cpp (default)".
  Only `host_shm_cyclonedds.txt` states `rmw_cyclonedds_cpp` in its header. The Fast DDS runs do record `librmw_fastrtps_cpp.so`. The later `dry_run_2026-09-28/host_cyclonedds_console4.txt` records `libddsc.so.0.10.5`. Unverified for these two runs.
* Two runs per Fast DDS cell only ("2 of 2"); one run per CycloneDDS cell.
* In the shm-mode CycloneDDS FAIL the file lists one recording seen (`/lidar_points`, the 120-degree bag) and 4 alarm frames at 51.5-52.8 m; their cause is not analysed in the folder
  (`host_shm_cyclonedds_rmem212992.txt`). `README.txt` reads the failure as the 360-degree recording never arriving.
