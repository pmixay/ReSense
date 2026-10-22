# Third team VM, 25.09 evening (code d4b396e): machine facts

> **Purpose:** the machine facts of the third team VM, on which the transport fixes (README jury
> step 0, opt-in `RESENSE_DDS=shm`) were checked in the evening of 25.09.
> **Audience:** team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: `machine.txt` read; commit compared with
> `../dry_run_2026-09-25_3/README.txt`; nothing re-run · **Status:** historical

## 1. What was run, and when

* A collect-style dump (lscpu, `free`, `df`, `uname`, Docker, `vmstat`, commit, `net.core.rmem_*`)
  on the third team VM, code `d4b396e967c48555e1e997d4090b7d777dbaaa8c` (`machine.txt`). No
  timestamp in the file; the evening of 25.09 comes from
  [`../dry_run_2026-09-25_3/README.txt`](../dry_run_2026-09-25_3/README.txt) ("Runs of 25.09 evening on
  a third team VM ... code d4b396e").
* The git date is a merge date. Lane: not recorded in the folder or the docs.

## 2. Result

No measurement result. Facts: Intel Xeon (Icelake), 8 CPUs, 2 threads per core, 4 cores per
socket; 15 GiB RAM; root disk 87G with 75G available; Linux 5.15.0-191; Docker 29.8.1;
`net.core.rmem_max = 212992`, `net.core.rmem_default = 212992` (`machine.txt`).

## 3. What it supports

* [`../README.md`](../README.md) section 2 row for `dry_run_2026-09-25_3/` and this folder (stock Fast
  DDS at 212992 PASS over UDP and in shm mode; CycloneDDS needs 32 MiB).
* The 28.09 summary says the 28.09 VM is this one, reused
  ([`../vm_2026-09-28/summary.md`](../vm_2026-09-28/summary.md), "Machine").

## 4. Contents (1 file)

| file | what |
|---|---|
| `machine.txt` | lscpu, memory, disk, `uname`, Docker, `vmstat`, commit, `rmem_*` |

## 5. Caveats

* Reuse is unverified from the files: `../vm_2026-09-28/machine.txt` shows a 145G root disk and no
  hostname, this one 87G; the CPU is the same model. The two dumps cannot show it is the same VM.
* `machine.txt` contains the VM hostname; not repeated here.
