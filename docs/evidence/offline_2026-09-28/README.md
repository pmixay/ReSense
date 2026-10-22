# Offline rehearsal on the team VM (28.09, code 464f5bc), two passes

> **Purpose:** raw output of the offline rehearsal in the full VM run of 28.09: pass 1 with the
> recordings possibly out of the page cache, pass 2 (`warm_bags/`) with them read into the cache
> first. Outbound traffic blocked, archive loaded after the image was deleted.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from the named files and compared with
> `../vm_2026-09-28/summary.md`; nothing re-run · **Status:** historical (detector of 27.09;
> pass 1 contains a FAIL that the summary attributes to the storage, not the node)

## 1. What was run, and when

* `scripts/r_offline.sh` (in [`../vm_2026-09-28/scripts/`](../vm_2026-09-28/scripts/r_offline.sh)) on the
  team VM of [`../vm_2026-09-28/`](../vm_2026-09-28/summary.md), code `464f5bc`, archive
  `resense-image-1.0.0.tar.gz` (475947817 bytes, sha256 `1019cd3c…`) from
  [`../export_2026-09-28/`](../export_2026-09-28/README.md).
* Pass 1: block on 17:10:08, off 17:16:51 UTC, 2026-09-28 (`window.txt`). Pass 2 (`warm_bags/`):
  17:18:51 to 17:24:39 (`warm_bags/window.txt`). Both restored by hand; nothing allowed out.
* Git date = merge date of the VM-run PR. Lane: "an agent over SSH" per
  `../vm_2026-09-28/summary.md`; the lane is not recorded.

## 2. Result

* Block: IPv4 and IPv6 blocked, a new SSH login worked at 17:10:50, a container on Docker's bridge
  network is blocked too (`steps.txt`); the rules counted 1210 rejected IPv4 packets and 51 from the
  bridge in pass 1, 1148 in pass 2 (`rules_ipv4.txt`, `rules_docker_user.txt`,
  `warm_bags/rules_ipv4.txt`).
* Pass 1: `dry_obstacle` PASS (200 status messages, 189 alarm frames, 55.5 to 56.6 m);
  `dry_clear` FAIL: "10 frames of the recording not processed after the first 5 s", all 10
  skipped by the catch-up, whose log line reads "1.4 s of recording waiting: catching up"
  (`dry_clear.txt`, `off_clear_node_log.txt` lines 23-25); host jury console (Fast DDS 2.6.12,
  `host_jury_console4.txt`) PASS with 381 status messages and 129 `STOP` after a "1.2 s hole in the
  input" warning (`host_jury.txt`, `host_jury_node_log.txt`); `play_bag.sh --archive` exit 0.
* Pass 2 (`warm_bags/`): all PASS: `dry_obstacle` 201 messages, 190 alarm frames; `dry_clear` 251
  messages, 0 alarm frames, 0 frames dropped; host console 453 messages, 195 `STOP`;
  `play_bag_obstacle.txt` exit 0 (`warm_bags/*.txt`).

## 3. What it supports

* [`../vm_2026-09-28/summary.md`](../vm_2026-09-28/summary.md) rows "§5 offline, pass 1 / pass 2" and
  Finding 1 (storage, not the node, limits playback); all figures above agree with them.
* [`archive/EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) §3e (line 3369) and
  [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md) line 288 (storage-limited playback).
* [`../dry_run_2026-09-28/e2e_vm.txt`](../dry_run_2026-09-28/e2e_vm.txt) reads the status files of this
  folder and of `warm_bags/` (end-to-end percentiles).
* [`../../VM_GUIDE.md`](../../VM_GUIDE.md) §5; archive CAPTAIN board C25 / action 15.

## 4. Contents (46 files)

| path | what |
|---|---|
| `steps.txt`, `window.txt` | timeline of pass 1, block window |
| `rules_ipv4.txt`, `rules_ipv6.txt`, `rules_docker_user.txt` | rules with packet counters |
| `check_no_network.txt`, `check_no_network_bridge_container.txt` | block checks |
| `dry_obstacle.txt`, `dry_clear.txt`, `off_{obstacle,clear}_node_log.txt`, `off_{obstacle,clear}_status.jsonl.gz` | the two dry runs |
| `host_jury*.txt`, `host_jury_status.jsonl.gz` | the README jury console from the host (decisions, distances, logs, `ls` of `/dev/shm`) |
| `play_bag_obstacle.txt` | `play_bag.sh --archive` |
| `warm_bags/` | 23 files, the same set for pass 2 |

## 5. Caveats

* The sentence "host consoles ... all PASS, 453 of 453 frames, 195 `STOP` each" in the archived
  log §3e does not describe pass 1 here (381 messages, 129 `STOP`); pass 2 matches (453, 195).
* Pass 1 `dry_clear` FAIL is real in the files; the cause (storage stall) is the summary's reading,
  consistent with the node log, not independently measured.
* Detector of 27.09, superseded. `host_jury_ls*.txt` show `/dev/shm` files of the VM.
