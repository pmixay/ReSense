# Full VM run of VM_GUIDE on the team VM (28.09, code 464f5bc)

> **Purpose:** the machine facts, data preparation logs, test run and run order of the one
> complete pass of VM_GUIDE §1-§5 on a 4-core team VM, with `summary.md` as the index of every
> run and its findings.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from the named files; `summary.md` rows compared
> with the sibling folders for the gate, export and offline runs (those agree); the dry-run and
> bench folders were not re-read for this README · **Status:** historical (detector of 27.09;
> still the latest complete team-VM run named by `../../VM_GUIDE.md`)

## 1. What was run, and when

* Every step of [`VM_GUIDE.md`](../../VM_GUIDE.md) §1-§5 on one team VM, 2026-09-28, code
  `464f5bc6b193ff3dcc4bd7d30b03745d8d260f6a` (`machine.txt`; "PR #20 merged: the node's fast
  input path", `summary.md`). Timeline of the chain: 16:31:23 to 17:09:05 UTC (`chain.txt`), offline
  passes 17:10:08 to 17:24:39 (`../offline_2026-09-28/`).
* "Run by an agent over SSH ... No code, config or test was changed on the VM" (`summary.md`); the
  lane is not recorded. The git date is the merge date of the VM-run PR, not the run date.
* The VM: 8 vCPU = 4 physical cores, 15 GiB, network disk 79.0 MB/s sequential direct read,
  `rmem_max` 212992, Docker 29.8.1 (`machine.txt`).

## 2. Result

`pytest`: 754 passed, 6 subtests passed in 305.90 s (`pytest.txt`). All recordings and the ride
fetched: 221 split files cached (`data_ride.txt`), the six `metadata.yaml` compared with
`bag_metadata/` (`data_recordings.txt`). Runs (`summary.md` table): dry runs, cold and warm, stock
player, host consoles with Fast DDS and CycloneDDS, shm mode: PASS; bench: `dry_obstacle_native`
PASS, `dry_obstacle_numpy` FAIL (p95 103 ms); gate PASS; export PASS; offline pass 1 `dry_clear`
FAIL (storage stall), pass 2 all PASS. Six findings, among them: disk-bound playback of the 360°
recording (62.5 to 62.7 s instead of 20 s), end-to-end p95 81 to 82 ms warm, node exits with code 1 on
Ctrl+C.

## 3. What it supports

* [`../../VM_GUIDE.md`](../../VM_GUIDE.md) header and §0 name `summary.md` as the latest complete run.
* [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md) lines 177 and 288 (end-to-end latency, storage-limited
  playback); [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) line 227; archived
  [`EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) §3e (line 3317 and 3324).
* [`../README.md`](../README.md) section 2 row `vm_2026-09-28/`; SCORECARD row "28.09, evening"
  concerns the separate judgement, not this run.
* Sibling folders it indexes: [`../dry_run_2026-09-28/`](../dry_run_2026-09-28/), [`../bench_2026-09-28/`](../bench_2026-09-28/),
  [`../gate_2026-09-28/`](../gate_2026-09-28/README.md), [`../export_2026-09-28/`](../export_2026-09-28/README.md),
  [`../offline_2026-09-28/`](../offline_2026-09-28/README.md).

## 4. Contents (12 files)

| path | what |
|---|---|
| `summary.md` | index of every run with folder and result, machine, findings (83 lines) |
| `machine.txt` | lscpu, memory, disk, Docker, `vmstat`, commit, `rmem_*`, `dd` read speed |
| `data_recordings.txt`, `data_ride.txt` | shell traces of the recordings check and the ride fetch |
| `pytest.txt` | pytest output tail |
| `chain.txt` | timestamps and verdict lines of the run chain |
| `scripts/` | 6 shell scripts that ran the steps: `r_env.sh`, `r_runs.sh`, `r_chain.sh`, `r_offline.sh`, `r_data_a.sh`, `r_data_b.sh` |

## 5. Caveats

* `summary.md` says this is "the third team VM of 25.09 ... reused"; the machine dumps do not show it
  (see [`../vm_2026-09-25_3/README.md`](../vm_2026-09-25_3/README.md)). Unverified.
* `summary.md` finding 6 notes that `build_no_cache.txt` (in `../dry_run_2026-09-28/`) repeats its
  last lines.
* `summary.md` names a branch (omitted here). Detector of 27.09; the sealed 1.1.0 / 1.3.0 detectors
  were not run on this VM.
