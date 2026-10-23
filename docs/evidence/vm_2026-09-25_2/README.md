# Second team VM, 25.09 afternoon (code 76bf24e): machine facts

> **Purpose:** the machine facts of the second team VM, on which the confirmation re-run of 25.09
> afternoon was made.
> **Audience:** team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: `machine.txt` read; nothing re-run · **Status:** historical

## 1. What was run, and when

* A collect-style dump (lscpu, `free`, `df`, `uname`, Docker version, `vmstat`, repository commit,
  `net.core.rmem_*`) taken on the second team VM during the confirmation re-run of 25.09,
  code `76bf24ebac2d586f092b7c7493a5cb363fa1bdf1` (third-last line of `machine.txt`). The file
  carries no timestamp; the day comes from the sibling folders of the same VM
  ([`../gate_2026-09-25_2/`](../gate_2026-09-25_2/README.md), [`../offline_2026-09-25_2/`](../offline_2026-09-25_2/README.md)).
* The git date is a merge date. Lane: not recorded in the folder or the docs.

## 2. Result

No measurement result. Facts: Intel Xeon (Icelake), 8 CPUs, 2 threads per core, 4 cores per
socket; 15 GiB RAM; root disk 97G with 57G available; Linux 5.15.0-191; Docker 29.8.1;
`net.core.rmem_max = 212992`, `net.core.rmem_default = 212992` (all `machine.txt`).

## 3. What it supports

* The "second team VM" rows of [`../README.md`](../README.md) section 2 and
  [`archive/EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) lines 3156-3160.
  No doc cites this folder by name (grep, 2026-10-22).
* `rmem_max` 212992 is the setting under which the host console failed
  ([`../offline_2026-09-25_2/`](../offline_2026-09-25_2/README.md)).

## 4. Contents (1 file)

| file | what |
|---|---|
| `machine.txt` | lscpu, memory, disk, `uname`, Docker, `vmstat`, commit, `rmem_*` |

## 5. Caveats

* The 4-core, 8-vCPU facts match the first VM ([`../vm_2026-09-25/summary.md`](../vm_2026-09-25/summary.md)); the disk
  size differs (97G here).
* `machine.txt` contains the VM hostname; not repeated here.
