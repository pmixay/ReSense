# N3 dust guard: protocol, dev tables, acceptance battery with the guard on (19.10)

> **Purpose:** the P3 lane's dust guard (`resense/dust_guard.py`, switch `dust.enabled`, off by default): the
> acceptance protocol registered before measuring, development tables, the one acceptance battery that was run with
> the switch on, the Falcon identity run, and the diagnosis of why the battery fails.
> **Audience:** jury, P1/P3 (dust decision), reviewers of the N3 card · **Owner:** P3 lane (`PROTOCOL.md`: "Owner: P3 lane
> (agent), ordered by P1") · **Language:** EN
> **Last verified:** 2026-10-22: links resolve; the table numbers were re-read in `battery_on_table.txt` and
> `falcon_full.json` · **Status:** historical, stopped unfinished; the guard stays off (section 5)

## 1. What was run, when, by whom

* Lane P3, 19.10 (`PROTOCOL.md` title and `HANDOFF.md`: "19.10.2026, ~16:10 UTC", stopped on P1's order). Base `aec88d2`;
  protocol registered at `1de9c47` before any acceptance run (`HANDOFF.md`); branch name omitted. The folder arrived with squash
  commit `0acb18c` (2026-10-19, "(#42)").
* Acceptance battery, switch on, registered seed 20261018: `run_acceptance.py --stage battery-on`. Identities in
  `battery-on_execution.json`: runner source commit `44b514c4ede0bebb75da02994ff6fa69c6151c02`, reference `aec88d2`
  (`aec88d248fb1a48a275937607bd36c3587dc0dc9`), guard-on tree commit `58921434296799726de9aac78a05e5a0cfb0ae8f`
  (differs from the source only by `dust.enabled: true`, `on_source.diff`), native `67fa0887...`, `OPENBLAS_CORETYPE=Haswell`,
  one thread, `status: complete`, `identity_unchanged: True`. Falcon run: `falcon-full_execution.json`.
* Data are synthetic-model results from the generator `resense/dust.py`; no physical dust recording exists (`HANDOFF.md`).

## 2. Result

* Battery with the guard on (`battery_on_table.txt`, `acceptance_battery_on.json`; `HANDOFF.md` criteria table): empty recordings pass 6 of 15
  rows (criterion 1 FAIL); low dust: person 61/61 rows, rail object 104 of 128 rows (`HANDOFF.md`), medium: `doubleT_platform` STOP episodes 6, `roundT_squareT`
  5 (`battery_on_table.txt`); no silent GO, 14/14 (criterion 3 PASS). Gate, X3, dimmed-object control were not run (criterion 4).
* Falcon, whole recording, switch off and on: 4,443 frames, 1,372 STOP frames in 8 intervals, 0 decision differences versus the committed
  1.1.0 run, on vs off identical in every non-timing field (`falcon_full.json`). Dust windows on Falcon were not run.
* `HANDOFF.md` recommendation: do not enable by default. Parity "off equals `aec88d2`" was shown only on Falcon, not on battery, gate or X3.

## 3. Supports

* [`DECISIONS.md`](../../DECISIONS.md) row 41 (dust guard off: "не прошла приёмку"); [`BACKLOG.md`](../../BACKLOG.md) card "N3 . Dust / suspension"
  (line 493: "6 of 15"); [`FINALS_BRIEF_2026-10-16.md`](../../FINALS_BRIEF_2026-10-16.md) line 72.
* The generator and the 18.10 development batteries it uses: [n3_dust_2026-10-18](../n3_dust_2026-10-18/README.md). Front page [`../README.md`](../README.md) line 37.
* Organizers' dust (11 bursts) later checked on the shipped source: [p4_dust_markers_final_2026-10-20](../p4_dust_markers_final_2026-10-20/README.md).

## 4. Contents (75 files)

* `HANDOFF.md`, `PROTOCOL.md`: handoff and registered protocol; `on_source.diff`: the 4-line diff that turns the guard on in both YAMLs.
* `run_acceptance.py`, `acceptance_summary.py`, `compare_rows.py`, `falcon_compare.py`, `falcon_dust_stream.py`: drivers and comparators.
* `battery-on_execution.json`, `falcon-full_execution.json`: runs with identities and receipts; `acceptance_battery_on.json`, `battery_on_table.txt`, `falcon_full.json`: results.
* `dev/` (21): development seed-7 tables `g1,g2,g5,g6` with 16 shard summaries, and `b1_boundary_check/dust_guard_prototype.py`.
* `diag/` (6 scripts): signal, support, ablation, oracle-track diagnostics.
* `raw/` (35): `battery-on/shard0..3` (28 per-frame gzip outputs + 4 shard `summary.json`) and `falcon-full/` (clean on and off gzip, `summary.json`).

## 5. Caveats

* **Unfinished by design.** No gate, X3, dimmed control, Falcon dust windows, organizers' non-regression set or independent review, and no REPORT.md (`HANDOFF.md`, open items 1 to 4).
* The guard is off in 1.2.0. Organizers' dust causes no STOP or CAUTION on 1.1.0 and was re-checked on later sources (BACKLOG line 493, P4 folder above); this folder did not measure that.
* Dev tables `dev/g5_table.txt` / `g6_table.txt` are seed 7; `HANDOFF.md` says the acceptance seed reproduces the same picture (not recomputed here).
* The `HANDOFF.md` expectation that organizers' bursts stay below activation is marked "unverified" in that file.
