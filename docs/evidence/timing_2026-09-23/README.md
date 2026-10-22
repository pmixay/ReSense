# Per-stage timing of v0.6.3 on every recording, 23 September

> **Purpose:** the raw `resense bench` output behind the v0.6.3 timing table of the September
> experiment log: milliseconds per stage and per frame on each recording.
> **Audience:** team, jury · **Owner:** P1 (runs, timing, per the [evidence index](../README.md)) · **Language:** EN
> **Last verified:** 2026-10-22: every number below compared with `bench_v063.txt` and with the
> table in the log; the file itself carries no date, machine or commit · **Status:** dated record,
> superseded for the node path by the VM benches ([`bench_2026-09-25_2/`](../bench_2026-09-25_2/summary.txt), [`bench_2026-09-28/`](../bench_2026-09-28/summary.txt))

## 1. What was run, when

* Command and conditions, from the log (not from the folder): `resense bench --npy <recording>`, every
  frame, recordings back to back, `OMP_NUM_THREADS=1`, the idle 4-vCPU sandbox, numpy path
  ([EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3, "v0.6.3 (23.09 ...)").
* Run date 23.09 comes from the log and from [`../README.md`](../README.md) section 2 (line 150). The file has no
  timestamp. The git date of the folder (2026-09-24, `dfdebe5`, "raw timing and mount checks") is the commit date, not the run date.
* Code: the log says the v0.6.3 numbers were measured on `c1c2b6a` (merged as `1210580`). That SHA is not an object in this
  checkout (`git cat-file` fails), so it is unverified here; `1210580` resolves.
* Lane: not recorded in the folder or the docs.

## 2. Result

Total per frame, mean / p95 / max, all from `bench_v063.txt`: `roundT_doubleT` 50.2 / 63.4 / 76.1 ms;
`doubleT_obstacle` (360 degrees) 63.6 / 77.8 / 119.2 ms; `doubleT_platform` 53.7 / 75.2 / 115.1 ms. Every one
of the seven blocks has a p95 total between 52.8 and 77.8 ms. The log table (around line 2780) copies these
values, checked for all seven rows.

## 3. Supports

* [EXPERIMENTS log](../../archive/EXPERIMENTS_log_2026-09.md) §3, v0.6.3 table; it cites this file as "Raw output".
* [`DECISIONS.md`](../../DECISIONS.md) row 5 asks the same question (360 degrees in 100 ms) but cites log §3a, the later VM run, not this folder.
  No row of `BACKLOG.md`, `EXPERIMENTS.md`, `SCORECARD.md`, `VM_GUIDE.md` or `CHANGELOG.md` names the folder.

## 4. Contents

* `bench_v063.txt`: 7 blocks (`roundT_doubleT`, `doubleT_obstacle`, `doubleT_platform`, `roundT_pressureGate_roundT`,
  `roundT_squareT_pressureGate_squareT`, `squareT_platform_squareT_switch`, `new_data 2550-3149`), each with
  seven rows: track, corridor, egomotion, accumulate, cluster, tracking, total (mean, p95, max in ms).

## 5. Caveats

* `total` leaves out the health monitor (7-14 ms per frame on the sandbox, log §3 "What is timed"). It is not the node latency.
* Numpy path only. The C++ kernels merged on 24.09 cut the detector time afterwards (log §3), so these figures are
  not those of the shipped image.
* Sandbox, not the team VM and not the jury stand.
* The 24.09 re-measurement quoted next to the table (log §3) has no raw file here.
