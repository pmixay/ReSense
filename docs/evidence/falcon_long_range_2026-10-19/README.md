# Falcon long range (to 300 m): protocol, instruments, measurements, review (19.10)

> **Purpose:** the P3 lane's attempt to detect objects out to 300 m on the Falcon Prime recording: the
> pre-registered protocol, the injection instruments and their validation, the before/after rows, three
> independent review rounds, and the recommendation to merge the code OFF.
> **Audience:** jury, P1 (integration), P3 and the lane that later took card N7 · **Owner:** P3 lane
> (`PROTOCOL.md`: "Owner: P3 lane (with P4-style measurement), ordered by P1") · **Language:** EN
> **Last verified:** 2026-10-22: links resolve; the numbers below were re-read in the named JSON files ·
> **Status:** historical; superseded as a candidate by the N7 work of 21.10 (section 5)

## 1. What was run, when, by whom

* Lane P3, 19.10, base `aec88d2` (1.2.0 candidate); candidate code measured is `89e0f3b`. `REPORT.md` says a
  final commit (SHA not given) only flips `farrange.with_falcon_profile` to false; branch name omitted.
  Protocol written before the injected measurements, amended by A1 and A2 (`PROTOCOL.md`).
* Review: a fresh subagent, 19.10, three rounds, HEAD at review `ad753b6` (`INDEPENDENT_REVIEW.md` header).
* Runtime: Python 3.12 venv, `numpy==1.26.4`, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1` (`REPORT.md`, HANDOFF block).
  The Falcon recording was cached at full range (4.9 GB, not stored here). Git: the folder arrived with squash commit
  `0acb18c` (2026-10-19, "(#42)").

## 2. Result

Real recording, candidate `89e0f3b` against baseline `aec88d2` (`falcon_recording_eval_final6.json`, same numbers in `REPORT.md` section 4):
first STOP on the main person 146.3 m instead of 127.1 m; STOP frames not on a person 0 (baseline 18); 1,388 vs 1,387 STOP
frames; CAUTION share 0.368 (baseline 0.6849); but STOP episodes **9 vs 8**, so the pre-registered rule 5.1(b) (<= 8) fails.
Injection matrix seeds 10 to 12: no long-range gain (`matrix_tables_seeds10-12.md`). The walk control fails for the
candidate: real first STOP 146.5 m vs injected 122.0, 126.9 and 121.0 m for seeds 0 to 2 (`walk_control_candidate.json`).
The `REPORT.md` recommendation: merge the code, ship it off; no 250 m or 300 m claim. Not completed (`REPORT.md` section 5): full
Pandar gate, candidate X3, map300 matrix, moving-target amendment.
Note: the Falcon person/false-STOP counts here (18 false, 1,369 person STOP frames) use a different association (N2 anchors plus
far-walker labels) than the F1 lane's 12 and 1,360 in [`../f1_false_alarms_2026-10-19/README.md`](../f1_false_alarms_2026-10-19/README.md); they are not directly comparable.

## 3. Supports

* [`DECISIONS.md`](../../DECISIONS.md) row 41: Falcon `farrange` stays off ("не прошла правило 5.1b: 9 эпизодов против 8"); the C5 clear-distance value for Falcon is on.
* [`BACKLOG.md`](../../BACKLOG.md) card N7 (line 505) and table rows at lines 126 and 237; [`integration_2026-10-19`](../integration_2026-10-19/README.md) (merged off).
* Instruments reused by [falcon_far_range_2026-10-21](../falcon_far_range_2026-10-21/README.md) and [track_opinion_2026-10-21](../track_opinion_2026-10-21/README.md) (scripts `run_cache.py`, `falcon_eval.py`, `matrix.py`).

## 4. Contents (46 files)

* `REPORT.md`, `PROTOCOL.md`, `INDEPENDENT_REVIEW.md`, `matrix_tables_seeds10-12.md`: report, protocol, review, tables.
* `falcon_recording_eval*.json` (3), `walk_control_{baseline,candidate}.json`, `far_walker_eval*.json` (2), `far_walker_labels.json`,
  `count_control.json`, `raster_validation.json`: evaluation rows and instrument controls; `matrix/` (6 summaries) and `matrix_baseline_frames300.json`.
* `person_model.json`, `person_calibration.json`, `far_calibration.json`, `track_reference.json`: calibrations and the track reference.
* `far_walker.png`, `far_scene_empty_frames.png`: pictures of the far walker and the empty far scene.
* `raw/replays_final6.tar.gz` and `raw/SHA256SUMS`: raw replays (baseline, candidate, map300, walk controls); `scripts/` (17): cache, replay, injector, evaluators.

## 5. Caveats

* **Superseded.** The N7 lane of 21.10 [falcon_far_range_2026-10-21](../falcon_far_range_2026-10-21/README.md) re-did the work ("Switch state: ON" at its
  revision 2, `c431b2e`, on its own branch); whether that was merged was not checked here. `BACKLOG.md` line 237 still says `farrange` off.
* Missing: `REPORT.md` links `x3_candidate_incomplete.log`, which is not in this folder; the run named `new_off` and the baseline matrix `baseline_summary.json` are not here either (`matrix/` has `baseline_s10_summary.json`).
* `matrix.py` and `run_cache.py` default to `/home/user/data/falcon`; the data is external and not available here, so nothing could be rerun (all numbers above are copied, not recomputed).
* The injected rows depend on a fitted person model; the review notes C6 was evaluated in-sample (`INDEPENDENT_REVIEW.md` verdict table).
