# Thin far scan-line threshold: gate and history reports (29.09)

> **Purpose:** archive of the full regression gate, the paired monitoring acceptance and the two
> 33-history replays behind the change `tracking.thin_far_min_voxels` 4 to 3.
> **Audience:** team, jury, reviewers · **Owner:** not recorded in the folder or the docs ·
> **Language:** EN · **Last verified:** 2026-10-22 (numbers below copied from the named files; the
> per-frame captures were not opened) · **Status:** dated record; the note
> [`../thin_far_threshold.md`](../thin_far_threshold.md) is the narrative, this file is the map.

## 1. What was run, and when

* **Run date:** 2026-09-29. `created` in [`default_gate.json`](default_gate.json) is
  2026-09-29T02:52:15+00:00; `created_utc` in [`history_threshold3.json`](history_threshold3.json)
  is 2026-09-29T02:46:19+00:00 and in [`history_threshold4.json`](history_threshold4.json)
  2026-09-29T02:22:16+00:00.
* **Import date:** the folder entered the repository with the squash import `44b462e` (2026-10-16,
  per `git log`). That is not the run date.
* **Code:** gate and threshold-3 history on commit `dcaa5db` (`code.commit` in `default_gate.json`,
  `source_commit` in `history_threshold3.json`). The threshold-4 control history names source
  commit `49bfc70b` in `history_threshold4.json`; the folder does not say why it differs.
  The branch name written in `default_gate.json` is omitted here.
* **Machine:** `run.machine` in `default_gate.json` says 8 CPUs, Python 3.10.12, wall 1034.8 s,
  not the 4-vCPU cloud sandbox of the other 29.09 gates. Lane: not recorded in the folder or the docs.
* **Reference gate:** the 28.09 default gate, commit `bc75abe0`
  ([`../../cycle_2026-09-28/complete_timing/default/gate.json`](../../cycle_2026-09-28/complete_timing/default/gate.json),
  `gate.baseline_commit` in `default_gate.json`).

## 2. Result

`default_gate.json`: `gate.passed` true, 0 worse, 0 missing, 202 metrics `same`, 2 `better`
(`set_F_straight.box0.5.detected`, `set_F_straight.box0.5.first_detection_median_m`), 20 information
changes. Set F 0.5 m box: 1/6 to 2/6 sequences detected, median first detection 51.9 m to 64.4 m
(this folder's gate and the 28.09 gate, `set_F_straight.kinds.box0.5`); false detections 0 in both.
The ride in `default_gate.json`: 130 alarm frames, 32 alarm events, 31 STOP episodes, monitored range
median 127.6 m. The 64.4 m is a median over a different successful set, not a paired gain (stated in
[`../thin_far_threshold.md`](../thin_far_threshold.md)). Both history reports give 33 histories,
204 STOP frames, 55 STOP events (`totals`). The "5 of 11,271 ride frames GO to CAUTION" and
"18 of 12,468 history rows differ only by track ID" figures are quoted from the note and were not
recomputed here (unverified).

## 3. Supports

* [`../../../EXPERIMENTS.md`](../../../EXPERIMENTS.md) line 165 (Set F box 0.5 m 2 of 6) and line 334
  (row 29.09, `thin_far_min_voxels` 4 to 3).
* [`../../../../CHANGELOG.md`](../../../../CHANGELOG.md) line 363 (default 4 to 3); the full entry is in
  [`../../../archive/CHANGELOG_history_2026-10-19.md`](../../../archive/CHANGELOG_history_2026-10-19.md) line 404.
* [`../../README.md`](../../README.md) line 124 (index row, commit `dcaa5db`).
* [`default_gate.json`](default_gate.json) is also the "previous seal" gate that the `3eeb106` gate was
  compared with ([`../../../archive/DETECTOR_FREEZE_history_2026-10-19.md`](../../../archive/DETECTOR_FREEZE_history_2026-10-19.md) line 230)
  and is cited by [`../../detector_freeze_2026-09-27.json`](../../detector_freeze_2026-09-27.json) and
  [`../../current_review_2026-09-29/score.json`](../../current_review_2026-09-29/score.json).

## 4. Contents (70 files, not counting this README)

| file | what |
|---|---|
| [`default_gate.json`](default_gate.json) | full regression gate, default config, no overrides |
| [`default_acceptance.json`](default_acceptance.json) | paired monitoring acceptance against the reference; `monitoring_cost_passed` true, `no_new_negative_alarm_frames` true, `identical_negative_alarm_outputs` false |
| [`history_threshold3.json`](history_threshold3.json) | 33-history replay with threshold 3 |
| [`history_threshold4.json`](history_threshold4.json) | same replay, threshold 4 (control) |
| `history_threshold3_frames/` | 33 per-history frame outputs (`*.jsonl.gz`), threshold 3 |
| `history_threshold4_frames/` | 33 per-history frame outputs (`*.jsonl.gz`), threshold 4 |

Frame file names are `cache__<recording>__<stress>__0` (5 recordings times 6 stress modes: `catchup`,
`dither5`, `drop20`, `drop40`, `every`, `offset`) and `capture__roundT_doubleT__<case>__0`
(`failed_clear`, `old_pass`, `old_stock`).

## 5. Caveats

* Set F objects are synthetic injections into recorded backgrounds (note, paragraph 4); this is a
  narrow recall change, not general small-object evidence.
* Superseded as the shipped state: later seals (`3eeb106`, then `1e2ed82`, `7464d80`) were gated against
  this gate; the threshold stays 3 in them (not rechecked here, unverified).
* Both history reports state: known clear development recordings, not new holdout data; concurrent run
  timings are not latency evidence (`limitations`).
* `identical_negative_alarm_outputs` is false in the acceptance file; the note explains it by 69 ride
  payloads differing only by track ID (not recomputed).
