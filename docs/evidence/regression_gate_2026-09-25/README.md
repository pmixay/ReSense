# The regression gate demonstrated (25.09): same code on two paths, and a deliberate failure

> **Purpose:** show that the new gate (`scripts/regression_gate.py`) passes unchanged code on the
> native and on the numpy path, and fails when one detector parameter is changed.
> **Audience:** team, P3, P4 · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-22: the three printed gates read; the headline counts compared with
> `archive/CHANGELOG_2026-09.md` lines 674-681; nothing re-run; the code commit is not resolvable
> here (see 5) · **Status:** historical (gate of the first baseline; the ride and set F were not
> available on this machine)

## 1. What was run, and when

* Three gate runs on the dev VM ([`../README.md`](../README.md) section 2: "dev VM"), all with code
  `0772c2a6d558d9e310209464d08f89f5fa23004a` and the baseline
  [`regression_baseline_2026-09-25.json`](../results/regression_baseline_2026-09-25.json)
  (code `ca557cb`, line 25 of each file): `pass_native.txt` (native kernels), `pass_numpy.txt`
  (`RESENSE_NATIVE=0`), `fail_cluster_min_points_8.txt` (`--set cluster.min_points=8`).
* Date: the files carry no date. The docs place it on 25.09 (folder name; CHANGELOG entry
  "Regression gate (`ca557cb` … `5017dec`, 25.09)"). Run date within the day is unverified.
  The git date is a merge date. Lane: not recorded in the folder; the CHANGELOG entry is headed
  "A for P4".

## 2. Result

* `pass_native.txt`: `GATE PASS: no gated metric worse (0 gated better, 0 worse but allowed, 13
  information rows changed)`, exit code 0.
* `pass_numpy.txt`: `GATE PASS` with 14 information rows changed (latency rows slower, e.g.
  `cloud_with_fake_obj` p95 27.6 to 51.0 ms), exit code 0.
* `fail_cluster_min_points_8.txt`: `GATE FAIL: 4 gated metric(s) worse` (platform-switch alarm
  events and STOP episodes, set O `small_center` stop frames and first stop; 3 gated better, 29
  information rows changed), exit code 1. Five-recording totals there: 118 alarm frames / 22 events
  / 31 STOP episodes against 107 / 20 / 27 in the passing runs.

## 3. What it supports

* [`archive/CHANGELOG_2026-09.md`](../../archive/CHANGELOG_2026-09.md) lines 674-681: "the same code passes on
  the numpy path, `--set cluster.min_points=8` fails (it adds platform events)". Matches this folder.
* [`../README.md`](../README.md) section 2 row `regression_gate_2026-09-25/`;
  [`../../EVALUATION.md`](../../EVALUATION.md) §3 step 6 (named by the CHANGELOG entry).
* No DECISIONS, BACKLOG or SCORECARD row names this folder (grep, 2026-10-22).

## 4. Contents (3 files)

| file | what |
|---|---|
| `pass_native.txt` | printed gate, native path, PASS (43 lines) |
| `pass_numpy.txt` | printed gate, numpy path, PASS (44 lines) |
| `fail_cluster_min_points_8.txt` | printed gate with the override, FAIL (66 lines) |

## 5. Caveats

* Commit `0772c2a` is not resolvable in this checkout (`git log 0772c2a` fails), so the code
  state is unverified; the CHANGELOG entry covers commits `ca557cb` to `5017dec`.
* Ride (set E) and set F straight were "not available" in all three runs (no cache), so this is
  the gate of the six recordings and set O only.
* Superseded by the gates with the ride (`../gate_2026-09-25/`, `../results/`).
