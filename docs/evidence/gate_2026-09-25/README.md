# Regression gate on the first team VM (25.09, code 7290873) and four what-if variants

> **Purpose:** the full regression gate (six recordings, set O, the 20-minute ride, set F straight)
> run on the first team VM at `7290873`, plus four gate runs with one or two detector parameters
> overridden with `--set`.
> **Audience:** team, P3, P4 · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: numbers read from the named files; the gate JSON `gate` block read
> with a script, the table and the JSON agree; nothing re-run · **Status:** historical (detector
> of 25.09; superseded by `../gate_2026-09-25_2/` and `../gate_2026-09-28/`)

## 1. What was run, and when

* `scripts/vm/run_plan.sh gate` on the first team VM (8 vCPU = 4 physical cores), 2026-09-25,
  09:44:05 to 09:53:01 UTC; commit `72908737f2f8d1caf2b513f730abd930c8dac20d`, native kernels,
  config `configs/default.yaml` (`meta.txt`, `result.txt`, `gate_native.json`).
* Four variants in `variants/`, same commit and VM, 09:59 to 10:30 UTC (each `meta.txt` /
  `result.txt`): `long` (`--set cluster.floating_long_min_length=3.0`), `short`
  (`cluster.short_signature_max_length=3.0`), `short_long` (both), `nearbed`
  (`lowobj.near_enabled=true`); see each `variant.txt`.
* The git date of this folder is a merge date, not the run date. Lane: not recorded in the
  folder or the docs.

## 2. Result

* Main run: `gate: PASS`, `GATE PASS: no gated metric worse (0 gated better, 0 worse but allowed,
  14 information rows changed)` (`gate_native.txt`); JSON `gate`: same 81, info_changed 14
  (`gate_native.json`). Baseline: `regression_baseline_2026-09-25.json`, code `ca557cb`. The ride
  and set F were only measured, not compared: ride 204 alarm frames / 47 events / 39 STOP episodes in
  11271 frames, five obstacle-free recordings 107 / 20 / 27 in 2287 frames (`gate_native.txt`).
* Variants against `head_7290873_ride.json` (each `gate_native.txt`, last line): `long` PASS (3
  gated better); `short` FAIL (7 gated worse, 5 better); `short_long` FAIL (5 worse, 7 better);
  `nearbed` FAIL (21 gated worse, 2 better).

## 3. What it supports

* [`../vm_2026-09-25/summary.md`](../vm_2026-09-25/summary.md) row "gate" (CAPTAIN action 11).
* [`../../VM_GUIDE.md`](../../VM_GUIDE.md) §4.4 is the procedure.
* Variants: no doc cites the folder by name (grep for `nearbed`, `short_long`, 2026-10-22), but
  their numbers match the go / no-go of 26.09 in [`archive/CHANGELOG_2026-09.md`](../../archive/CHANGELOG_2026-09.md)
  lines 640-646 and 689-695 (decided on the ride against
  [`rules_decision_2026-09-25.json`](../results/rules_decision_2026-09-25.json)): `long` ride
  197 / 46 / 39 and five bags 60 / 14 / 17, `short` five bags 113 / 22 / 29 and set O 352 inside
  STOP frames (these four figures read from the variants' `gate_native.txt`, equal to the CHANGELOG).
  Decision there: `floating_long_min_length` 3.0 chosen, `short_signature_max_length` stays 0.
  `nearbed`: five bags 459 / 107 / 72, ride 2416 / 528 / 294 (not in the CHANGELOG lines read).
* No DECISIONS, BACKLOG or SCORECARD row names this folder (grep).

## 4. Contents (44 files)

| path | what |
|---|---|
| `gate_native.json`, `gate_native.txt` | the gate result (JSON and the printed table, 155 lines) |
| `result.txt`, `steps.tsv`, `highlights.txt`, `notes.txt`, `meta.txt`, `run_log.txt` | step result, extracts, machine facts, full log |
| `variants/{long,short,short_long,nearbed}/` | 9 files each: the same eight files plus `variant.txt` (the `--set` arguments and the baseline) |

## 5. Caveats

* Baseline of the main run is the first baseline of 25.09 (`ca557cb`, six recordings and set O, no
  ride); the ride rows read "not in baseline".
* The baseline of the variants, `/home/mdm/gate_ref/head_7290873_ride.json`, is not in this folder
  or (checked by name) in `../results/`; the variant verdicts cannot be re-derived here.
* Discrepancy to note, not fixed: CHANGELOG line 691 says the `short` gate fails "on 5 rows"; the
  `short` variant here prints 7 gated metrics worse (`variants/short/gate_native.txt`). The
  CHANGELOG entry may count a different run or different rows; unverified.
* Detector of 25.09 (`7290873`, version 0.6.3), superseded. The gate JSON names a branch; omitted here.
