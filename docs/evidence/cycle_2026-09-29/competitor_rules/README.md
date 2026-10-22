# Gates of false-alarm rules taken from other teams' solutions (29.09 evening)

> **Purpose:** the full regression gate of each rule (and combination) that was tried from the public
> repositories of other case 5 teams, the gates of the three shipped rules, and the latency A/B of the
> ego-motion veto.
> **Audience:** team, jury, reviewers · **Owner:** not recorded in the folder or the docs ·
> **Language:** EN · **Last verified:** 2026-10-22 (numbers copied from the named files; the 13
> candidate files were listed and their `created`, `code`, `config.set` fields read, not recomputed) ·
> **Status:** dated record; the detector state it sealed (`1e2ed82`) was superseded the same night.

## 1. What was run, and when

* **Run date:** 2026-09-29, `created` between 12:40 and 15:21 UTC across the files
  (`q_em03.json` earliest, [`gate.json`](gate.json) 15:21:56 latest). The folder entered the repository
  with the squash import `44b462e` (2026-10-16); that is the import date, not the run date.
* **Code:** every candidate was run on one of the commits `daff91bc`, `68018789`, `7647b2ee` (`code.commit`
  in `candidates/*.json`); the three gates on `ee7b920` ([`gate_ee7b920.json`](gate_ee7b920.json)),
  `f67e4fb` ([`gate_f67e4fb.json`](gate_f67e4fb.json)) and `1e2ed82` ([`gate.json`](gate.json)), default
  config with no overrides, no uncommitted detector changes. The branch name in these files is omitted here.
* **Machine:** `run.machine` in the three gates: 4 CPUs, Python 3.11.15, recordings from the cached organizer
  data. Lane: not recorded in the folder or the docs.
* **Reference:** the `3eeb106` gate, [`../health_compare_counts/candidate/gate.json`](../health_compare_counts/candidate/gate.json)
  (`gate.baseline_commit` in the three gates).

## 2. Result

[`gate.json`](gate.json) (seal `1e2ed82`): `gate.passed` true, 0 worse, 7 better, 196 same, 21 information
changes. Ride: 26 alarm events, 28 STOP episodes, 123 alarm frames, median monitored range 127.6 m; five
empty recordings: 8 events, 12 episodes, 39 alarm frames. [`gate_ee7b920.json`](gate_ee7b920.json) and
[`gate_f67e4fb.json`](gate_f67e4fb.json) give the same counts. The veto costs +2.1 ms mean and +2.42 ms p95
per frame on `doubleT_obstacle` (360 degrees), +1.68 / +1.6 ms on `squareT_platform_squareT_switch`
(120 degrees) in [`latency_ab.json`](latency_ab.json). [`gate_table.md`](gate_table.md) lists 14 runs: PASS for
`f_base`, `f_lowtop08`, `f_expl5i`, `f_ego4`, `f_ego4b`, `f_shell`, `f_combo4`, `f_combo4_v2`, `f_defaults3`,
`f_seal`, `r_1e2ed82`; FAIL for `f_fresh`, `f_expl5`, `f_combo` (first-detection medians of Set F person,
box 1.0, trolley drop, e.g. person 151.0 to 129.1 m for `f_expl5`).

## 3. Supports

* [`../../../DECISIONS.md`](../../../DECISIONS.md) rows 30 (take rules from other teams' solutions) and 31
  (safety of the three rules).
* [`../../../EXPERIMENTS.md`](../../../EXPERIMENTS.md) lines 335, 350 (this table), 390 to 393 (rules not shipped:
  `shell` later off, `explained_run` with range downgrades, `lowobj.min_top` 0.08, `fresh_stop_evidence`),
  line 184 (latency).
* [`../../../ALGORITHM.md`](../../../ALGORITHM.md) lines 398 and 453; [`../../../ARCHITECTURE.md`](../../../ARCHITECTURE.md) line 238.
* [`../../detector_freeze_2026-09-29_competitor_rules.json`](../../detector_freeze_2026-09-29_competitor_rules.json) (the seal),
  [`../../results/regression_baseline_2026-09-29_competitor_rules.json`](../../results/regression_baseline_2026-09-29_competitor_rules.json)
  (copy of `gate.json` per [`../../README.md`](../../README.md) line 68; not byte-compared here, unverified).
* Next state: [`../shell_off/README.md`](../shell_off/README.md) (shell rule off after the safety review).

## 4. Contents (18 files, not counting this README)

| file | what |
|---|---|
| [`gate_table.md`](gate_table.md) | one row per run: gate verdict, five empty / ride / doubleT / Set O / Set F columns |
| [`gate.json`](gate.json) | sealing gate of the three shipped rules, commit `1e2ed82` |
| [`gate_f67e4fb.json`](gate_f67e4fb.json), [`gate_ee7b920.json`](gate_ee7b920.json) | the same gate on the two earlier commits |
| [`latency_ab.json`](latency_ab.json) | veto on/off latency A/B, commit `f67e4fb`, first 300 frames, 3 reps |
| `candidates/` | 13 full gate outputs, one per tried rule or combination (`f_base`, `f_lowtop08`, `f_fresh`, `f_expl5`, `f_expl5i`, `f_ego4`, `f_ego4b`, `f_shell`, `f_combo`, `f_combo4`, `f_combo4_v2`, `f_defaults3`, `q_em03`) |

## 5. Caveats

* Superseded: `shell` (`cluster.shell_min_top` 2.3 m) was switched off after the safety review; the
  current baseline is [`../../results/regression_baseline_2026-09-29_shell_off.json`](../../results/regression_baseline_2026-09-29_shell_off.json).
  The rows with shell on describe a state that is not the current seal.
* `gate_table.md` has rows `f_seal` and `r_1e2ed82` with no file of that name here (their numbers equal
  `gate.json`: 28 / 26 / 123 ride), and no row for `q_em03.json`, which is in `candidates/`. Mapping unverified.
* `q_em03.json` (`gauge.edge_margin_per_100m` 0.3) is not discussed in the docs searched (unverified why it is kept).
* The first-detection columns come from synthetic Set F; Set O envelope labels inherit a prior detector fit.
