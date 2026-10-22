# Regression gate with the ride on the team VM (28.09, code 464f5bc)

> **Purpose:** the full regression gate (six recordings, set O, ride, set F straight) re-run at
> `464f5bc` on the team VM against the baseline of the 27.09 seal, to show the sealed detector
> reproduces on another machine.
> **Audience:** team, jury, P4 · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from the named files; table and JSON `gate` block
> agree; nothing re-run · **Status:** historical (the 27.09 detector; the current baseline is
> later, see `../README.md`)

## 1. What was run, and when

* `scripts/regression_gate.py` with the ride and set F, `--jobs 4`, on the team VM of
  [`../vm_2026-09-28/`](../vm_2026-09-28/summary.md); gate JSON created 2026-09-28 17:05:36 UTC,
  wall 418.9 s (`gate_464f5bc.json`, `run`). Chain log: step `gate` ended 17:05:36
  (`../vm_2026-09-28/chain.txt`).
* Code `464f5bc6b193ff3dcc4bd7d30b03745d8d260f6a`, version 1.0.0, no uncommitted detector changes
  (`gate_464f5bc.json`, `code`). Baseline `../results/regression_baseline_2026-09-27_quality.json`,
  code `d572807` (`gate_table.txt` line 29).
* Git date = merge date of the VM-run PR. Lane: "an agent over SSH" per `../vm_2026-09-28/summary.md`;
  the lane is not recorded.

## 2. Result

`GATE PASS: no gated metric worse (0 gated better, 0 worse but allowed, 16 information rows
changed)` (`gate_table.txt` line 255); JSON `gate`: same 208, worse_gated 0, missing_gated 0.
The 16 changed rows are the `latency_ms.*` rows, each printed "worse" (`gate_table.txt`). Quality figures: ride 130 alarm frames / 32 events / 31 STOP
episodes in 11271 frames; five obstacle-free recordings 40 / 11 / 13 in 2287; set O 411 of 801 inside
frames (8 of 8 objects), 6 false STOP frames outside, background 0 frames (`gate_table.txt`).

## 3. What it supports

* [`../vm_2026-09-28/summary.md`](../vm_2026-09-28/summary.md) row "§4.4 gate with the ride and set F".
* [`archive/DETECTOR_FREEZE_history_2026-10-19.md`](../../archive/DETECTOR_FREEZE_history_2026-10-19.md)
  line 252 cites this folder: the re-run on the team VM gave the same result as the seal except
  the latency rows.
* [`../README.md`](../README.md) section 2 row `gate_2026-09-28/`.
* No DECISIONS, BACKLOG or SCORECARD row names this folder (grep, 2026-10-22).

## 4. Contents (2 files)

| file | what |
|---|---|
| `gate_table.txt` | printed gate (280 lines): summaries, set O, set F, metric table, `exit 0` |
| `gate_464f5bc.json` | the gate JSON |

## 5. Caveats

* Detector of 27.09 (`464f5bc`), superseded by later seals; the numbers here are not the
  current detector's.
* Latency rows are informational and differ by machine; only the quality rows are gated.
* The JSON names a branch (omitted here).
