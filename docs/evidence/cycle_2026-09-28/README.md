# Evidence of the 28.09 improvement cycle (experimental line, checkpoints 0 to 4)

> **Purpose:** map of the 28.09 cycle: the reviewer checkpoints 0 to 4 and the candidate folders
> (continuity, health histogram, complete timing, P3/score sync, onset near, regression, image checks),
> so each number in the docs can be traced to its gate or review file.
> **Audience:** team, jury, reviewers · **Owner:** not recorded in the folder or the docs ·
> **Language:** EN · **Last verified:** 2026-10-22 (gate files and checkpoint headers opened and copied;
> nothing re-run; sub-folder READMEs not re-verified) · **Status:** dated records of an experimental line;
> not the sealed 1.1.0/1.2.0 detector.

## 1. What was run, and when

* **Run dates:** `created` in the gate files is 2026-09-28, 18:12 to 20:45 UTC (table below). The reviews
  are dated 2026-09-28 (checkpoints 0 to 3, `date` / body of the files) and 2026-09-29 (checkpoint 4,
  body of [`checkpoint4_fresh_astra.md`](checkpoint4_fresh_astra.md)).
* **Import date:** the folder entered the repository with the squash import `44b462e` (2026-10-16, per
  `git log`); `0acb18c` (2026-10-19, PR #42) also touched the evidence folders. Neither is the run date.
* **Lanes:** the code lines are P3's experimental line and a separate score/checkpoint line merged on 28.09
  ([`../../P3_SCORE_SYNC_2026-09-28.md`](../../P3_SCORE_SYNC_2026-09-28.md)); the reviews name their
  reviewer as "GPT-6 Astra" (`reviewer` field). Which lane produced each sub-folder is stated in its own
  README where it is stated at all; otherwise: lane not recorded in the folder or the docs.
* **Gates** (all `run.machine.cpus` 8, from the gate files):

| gate file | `created` (UTC) | code | passed | metrics same |
|---|---|---|---|---|
| [`regression/baseline/gate.json`](regression/baseline/gate.json) | 18:12 | `4b6f3440` | true | 208 |
| [`regression/candidate/gate.json`](regression/candidate/gate.json) | 18:26 | `ef1d8f50` | true | 203 |
| [`p3_sync/default/gate.json`](p3_sync/default/gate.json) | 19:16 | `b84ea8f2` | true | 208 |
| [`health_histogram/default/gate.json`](health_histogram/default/gate.json) | 19:44 | `ef71c9dc` | true | 208 |
| [`onset_near/default/gate.json`](onset_near/default/gate.json) | 20:06 | `0ca664ce` | false | 192 |
| [`complete_timing/default/gate.json`](complete_timing/default/gate.json) | 20:45 | `bc75abe0` | true | 208 |

## 2. Result

Reviewer scores (internal judgments, "not an organizer score" in each file): checkpoint 0 total 68
([`checkpoint0_astra.json`](checkpoint0_astra.json)); checkpoint 1 66 and paired 66 to 66, delta 0
([`checkpoint1_astra.json`](checkpoint1_astra.json), [`checkpoint1_astra_paired.md`](checkpoint1_astra_paired.md));
checkpoint 2 67 ([`checkpoint2_priority_astra.md`](checkpoint2_priority_astra.md)); checkpoint 3 67 to 67.5,
delta +0.5 in speed ([`checkpoint3_health_astra.json`](checkpoint3_health_astra.json)); checkpoint 4 65 at
`292397833` ([`checkpoint4_fresh_astra.md`](checkpoint4_fresh_astra.md)). Gates: five PASS, `onset_near` FAIL
(its README: rejected, two Set F first-detection metrics failed). `complete_timing/default/README.md`: 208
non-latency metrics identical, 146 enforced, 15,269 frames over 15 captures.

## 3. Supports

* [`../../SCORECARD.md`](../../SCORECARD.md) lines 71 to 74 (checkpoints 1 to 4 reports); the checkpoint 0
  and the unpaired checkpoint 1 files are cited by no doc I searched (unverified).
* [`../../P3_SCORE_SYNC_2026-09-28.md`](../../P3_SCORE_SYNC_2026-09-28.md) (p3_sync, evaluation),
  [`../../README.md`](../../README.md) line 121 and [`../../CAPTAIN.md`](../../CAPTAIN.md) line 195
  (complete timing, health), [`../../VM_GUIDE.md`](../../VM_GUIDE.md) line 502 and
  [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md) line 406 (health record).
* [`../../DECISIONS.md`](../../DECISIONS.md) row 29 (GO at `doubleT_obstacle` frame 111) rests on the cause
  found in `continuity/` ([`../frame111_2026-09-29/README.md`](../frame111_2026-09-29/README.md) line 54).
* [`../README.md`](../README.md) line 127 (index row); the 61/100 judgement of the old `main` is a different
  record: [`../judgement_2026-09-28/`](../judgement_2026-09-28/README.md).
* `complete_timing/default/gate.json` is the reference gate of
  [`../cycle_2026-09-29/thin_far_threshold/`](../cycle_2026-09-29/thin_far_threshold/README.md) and of
  [`../low_return_support/full_gate/`](../low_return_support/full_gate/README.md).

## 4. Contents (527 files, `find` count before this README)

| path | files | what |
|---|---|---|
| `checkpoint0_astra.json`, `checkpoint1_astra.json` | 2 | reviews 0 and 1, structured (no `.md` twin for either) |
| `checkpoint1_astra_paired.{json,md}` | 2 | same-reviewer baseline vs continuity, 66 vs 66 |
| `checkpoint2_priority_astra.{json,md}` | 2 | source and priority review, 67 |
| `checkpoint3_health_astra.{json,md}` | 2 | paired health-histogram review |
| `checkpoint4_fresh_astra.md` | 1 | fresh review of 29.09, 65 |
| [`continuity/`](continuity/README.md) | 92 | low object height continuity candidate (`ef1d8f5`), with `history/` (71 files) and `runtime/` (5) |
| [`evaluation/`](evaluation/README.md) | 34 | synthetic evaluation protocol, comparisons, `p3_sync_raw_positive/` (8) |
| [`health_histogram/`](health_histogram/README.md) | 68 | exact-count health histogram candidate; `default/`, `runtime/` (33) |
| [`complete_timing/`](complete_timing/default/README.md) | 37 | `protocol.json` and `default/` full validation (no README at this level) |
| [`p3_sync/`](p3_sync/default/README.md) | 48 | `default/` combined P3/score defaults gate; [`ci_25a218a/`](p3_sync/ci_25a218a/README.md) CI and capture audit (no README at this level) |
| [`onset_near/`](onset_near/README.md) | 94 | near-preserving fresh STOP onset candidate, rejected; `observer/` (48) |
| [`regression/`](regression/README.md) | 43 | fresh baseline and candidate full gates |
| [`intake/`](intake/README.md) | 5 | fresh local cache intake manifest |
| [`image_candidate/`](image_candidate/README.md) | 33 | candidate Docker image checks; `ci_8547009/` (13) |
| [`main_sync/`](main_sync/README.md) | 52 | combined node and health validation, source `75ef4e2`; `ci/` (19) |
| [`tooling/`](tooling/README.md) | 12 | split-file intake fix (`rosbags` pin) |

## 5. Caveats

* Experimental line, not the sealed detector; the later seals (`3eeb106`, `1e2ed82`, `7464d80`, then 1.1.0)
  supersede it. Reviewer scores of different reviewers and methods are not a measured gain
  ([`../../SCORECARD.md`](../../SCORECARD.md) line 65).
* `continuity/README.md` says deployment is provisional and the local positive ROS run fails for both
  candidate and baseline.
* `checkpoint2_priority_astra.md` and the archived `../../archive/2026-09-28/CHECKPOINT1_REVIEW_2026-09-28.md`
  name working paths on a developer machine (`/home/likikikpa/...`); those paths are not in the repository.
* Branch names appear in these files and are omitted here; commit SHAs are used.
