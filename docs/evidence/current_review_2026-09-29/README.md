# Internal review score of 29.09 (`dcaa5db`): one score file

> **Purpose:** explain the single file `score.json`: an internal score of 65/100 for commit `dcaa5db` after the thin-far threshold change, and where its supporting evidence is.
> **Audience:** team, jury · **Owner:** lane not recorded in the folder or the docs · **Language:** EN
> **Last verified:** 2026-10-22: JSON parses; the eight criterion scores sum to 65 of 100 (checked with a one-line script); the numbers
> in section 2 were compared with [`../cycle_2026-09-29/thin_far_threshold.md`](../cycle_2026-09-29/thin_far_threshold.md); nothing was re-run ·
> **Status:** current as a record; an internal score, not an organizer score. It is not quoted in the current `docs/SCORECARD.md`.

## 1. What was run, when, by whom

* **Review date:** 2026-09-29 (`score.json`, field `review_date`). **Assessed commit:** `dcaa5dbddb1dbc0ed30ccb50bed569390bca060d` (`assessed_commit`). **Import date:** 2026-10-16, squash commit `44b462e`, which is not the review date.
* The file is a score, not a run: it summarizes gate, acceptance and test results that were produced elsewhere (`validation` in `score.json`). Who wrote the review is not recorded in the folder or the docs: lane not recorded.
* The sibling folder `../current_review_2026-09-28/` has a README and attachments; this one does not.

## 2. Result

`score.json`: `score` 65, `previous_score` 65, `change` 0. Criteria (score / max): functionality 16/25, detection range 6/15, speed 8/10, generalization 6/15, technical quality 9/10, launch 8/10, team approach 9/10, pitch 3/5.
Its `change_assessment`: the threshold change improves one synthetic small-box approach, sustained range is unchanged, so no criterion moves.
The `validation` block quotes: default gate passed with 202 gated metrics the same, two better, none worse; five added ride CAUTION frames, no STOP changes; 33 histories, 204 STOP frames and 55 events; 17 focused tests passed; full pytest 1,206 passed with 1 real-data failure (missing `new_data_55_0013.npy`) and 7 deselected.
The gate and history figures agree with `../cycle_2026-09-29/thin_far_threshold.md`. The pytest, ruff, freeze and focused-test lines have no log in this folder; I did not search `cycle_2026-09-29/` for them: unverified.

## 3. Supports

* [`../README.md`](../README.md) section 2 lists the folder with the experimental-line reviews (28-29.09), as a file link to `score.json`.
* `previous_score` 65 equals the 29.09 row for `2923978` in `docs/SCORECARD.md` (line 74 when read, 65/100, checkpoint 4). `dcaa5db` itself appears in `docs/SCORECARD.md` nowhere (grep), so this score is not in the scorecard table.
* Cited evidence (`score.json`, field `evidence`): [`../cycle_2026-09-29/thin_far_threshold.md`](../cycle_2026-09-29/thin_far_threshold.md), `thin_far_threshold/default_gate.json`, `thin_far_threshold/default_acceptance.json`, [`../detector_freeze_2026-09-27.json`](../detector_freeze_2026-09-27.json). All four paths exist in this checkout.

## 4. Contents

* [`score.json`](score.json): schema `resense-internal-score-v1`; its `rubric_note` says the weights are internal because the organizer does not publish numeric weights.

## 5. Caveats

* Internal weights, not organizer weights. The synthetic Set F small-box results are point injections into recorded backgrounds (`limits` in `score.json`).
* `score.json` lists `limits`: the zero-GO-overclaim diagnostic still fails with 16 GO overclaims on Set O.
* The "detector_freeze PASS at source digest f20dd9ef..." line is not checked against a freeze file for `dcaa5db` here (unverified); the cited `detector_freeze_2026-09-27.json` is the 27.09 seal.
* Later detector changes are not covered: `docs/EXPERIMENTS.md` (the row of the `shell` signature, line 390 when read) records another rule (the `shell` signature) switched on in the evening of 29.09 and off at night. Whether this score's `dcaa5db` includes it was not checked (unverified).
