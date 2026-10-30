# Regression gate with the ride on the second team VM (25.09, code 76bf24e)

> **Purpose:** the full regression gate (six recordings, set O, ride, set F straight) at `76bf24e`
> on a second team VM, against the ride baseline of the `column_hold` change, to show the gate
> reproduces on another machine.
> **Audience:** team, P3, P4 · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from the named files; the table and the JSON `gate`
> block agree; nothing re-run · **Status:** historical (detector of 25.09; later gates in
> `../results/` and `../gate_2026-09-28/`)

## 1. What was run, and when

* `scripts/regression_gate.py` with the ride and set F on the second team VM (8 vCPU, `--jobs 4`),
  2026-09-25, JSON created 15:27:31 UTC, wall 492.7 s (`gate_76bf24e.json`, `run`).
* Code `76bf24ebac2d586f092b7c7493a5cb363fa1bdf1`, version 1.0.0, no uncommitted detector
  changes (`gate_76bf24e.json`, `code`).
* Baseline: `../results/regression_baseline_2026-09-25_ride_column.json`, code `d117c8c`
  (`gate_table.txt` line 29; JSON `gate.baseline_commit`).
* The git date of this folder is a merge date. Lane: not recorded in the folder or the docs.

## 2. Result

`GATE PASS: no gated metric worse (0 gated better, 0 worse but allowed, 16 information rows
changed)` (`gate_table.txt`, line 152); JSON `gate`: same 105, worse_gated 0, missing_gated 0
(`gate_76bf24e.json`). Ride 187 alarm frames / 46 events / 39 STOP episodes in 11271 frames; five
obstacle-free recordings 58 / 13 / 16 in 2287 frames (`gate_table.txt`). The 16 changed rows are
all `latency_ms.*` rows. Final line `exit 0`.

## 3. What it supports

* [`archive/EXPERIMENTS_log_2026-09.md`](../../archive/EXPERIMENTS_log_2026-09.md) line 3160: the
  confirmation re-run; the log quotes "all 105 gated rows the same on this second machine (ride
  187 / 46 / 39)", which matches the figures above.
* [`../README.md`](../README.md) section 2 row for the second team VM.
* [`../../VM_GUIDE.md`](../../VM_GUIDE.md) §4.4 is the procedure.
* No DECISIONS, BACKLOG or SCORECARD row names this folder (grep, 2026-10-22).

## 4. Contents (2 files)

| file | what |
|---|---|
| `gate_table.txt` | printed gate: per-recording summary, set O, set F, then metric / baseline / current / verdict (153 lines) |
| `gate_76bf24e.json` | the gate JSON (`schema resense-regression-gate-v1`) |

## 5. Caveats

* The "105" is the JSON's `same` count; counting the table rows marked as gated by hand gives a
  different number (60 with a "yes" column), so cite the JSON.
* The baseline is the 25.09 ride baseline; superseded by the 26-27.09 baselines.
* The JSON names a branch (omitted here). `gate_table.txt` carries the VM's home path.
