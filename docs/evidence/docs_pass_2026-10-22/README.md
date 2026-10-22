# Documentation pass of 22.10: evidence READMEs, folder index, "last verified" dates, deleted branches

> **Purpose:** record of what the docs-and-evidence lane changed on 22.10 on top of the sealed 1.3.0 tree
> (`f24d939`), how each part was verified, and what was not checked.
> **Audience:** captain (P1), team · **Owner:** docs-and-evidence lane · **Language:** EN
> **Last verified:** 2026-10-22 · **Status:** current
> **Scope:** documentation only. No file under `resense/`, `native/`, `configs/`, `ros2_ws/`, `tests/` or `scripts/`
> was changed, no existing file inside an evidence folder was changed (the index `../README.md` is the one
> deliberate exception, item 2), nothing in `heldout_2026-10-15/` was read or changed.

## 1. READMEs for the 40 folders that had none

All 40 now have `README.md` (list: the folders added in the commits below; each lists what ran, when and by which lane,
the result with numbers copied from named files, the supported decision, the contents, and caveats).
Lane is written "not recorded in the folder or the docs" where neither says (all of the 23-28.09 folders).
Most of these folders came in by squash import (`44b462e`, 16.10) or merge, so the git date is not the run date; each README
takes the run date from the files and says so. Two sub-folder READMEs were added where missing
(`cycle_2026-09-29/competitor_rules/`, `cycle_2026-09-29/thin_far_threshold/`).

Verification:
* every relative link in the 40 READMEs resolves (script, 0 broken);
* an independent script took every number with 3 or more digits (or a decimal) in the 40 READMEs (684 numbers) and looked for it in
  the folder's own files, the docs and the linked files: 671 found. The 13 not found are line numbers: 12 into `docs/archive/EXPERIMENTS_log_2026-09.md` and 1 into `BACKLOG.md`. I opened each: 10 point at the cited line,
  1 was off by 10 lines (`timing_2026-09-23`, 2780 -> 2790) and was corrected, and 2 are range ends that land on a blank line (log 3153) or a table separator (BACKLOG 309), so the extent of those two ranges is not verified. A substring match shows a number exists in the
  sources, not that it is attached to the right quantity; that part rests on the writing agents' reading of the files. My own spot checks of agent output (not of the READMEs): the `labels/doubleT_obstacle.json` ranges behind the DATASET corrections (recomputed: 3 of 3 match), `gate_release_ed67d25.txt:265` behind VM_GUIDE, `detector.py:854`, the `axis_joint_union`/`axis_joint_fit` defaults and the `farrange` section behind ALGORITHM, and the `detector_freeze.py verify` result (PASS, 42 files);
* the writing agents re-read gate/summary files; none re-ran a measurement (no dataset in this lane).

Discrepancies the READMEs record but do not fix (all in files this lane may not change) are in §5.

## 2. The evidence index

`../README.md` had rows for only some folders (86 of the 154 folders were not named in it). A new section **§4 "Every folder, by date"**
lists all 154 folders (+ this one) with date, topic and the title of the folder's README, grouped by period like the existing
sections (newest first). Checked by script: every directory of `docs/evidence/` appears in §4 (154/154 before this folder was
added), 0 broken links in the index. The header "Last verified" line was updated. Existing rows were not changed.
The `heldout_2026-10-15` row says only that the folder is registered and was not read.
Note: `docs/evidence/` has 170 entries, of which 154 are folders (16 are files: seals, JSON).

Four entries of `results/` are named in no doc (`single_review_2026-09-28`, `available_gate_testovaya_2026-09-28`,
`oracle_accumulation_2026-09-28`, `quality_monitoring_baseline_2026-09-26`); `results/README.md` §5 lists the 34 entries of `results/` that
the index §1 does not name.

## 3. "Last verified" dates before 19.10

17 pages carried a date before 19.10 (some under the Russian header "Проверено"). Each was re-read statement by
statement against the current tree (config values, code names, scripts and flags, links, cross-references, evidence numbers), the
errors fixed, and the header set to 2026-10-22 with the earlier record kept after "earlier:"/"ранее:". Statements that need
data, a VM, ROS or the network are unverified (§4).

Corrections (old -> new):

* **VM_GUIDE.md:** CI runs the cold start "on every push to `main`" -> on a push that can affect the image (`ci.yml`);
  same for §4.6; baseline comment now "code 7464d80, shell off; baseline of every seal since 16.10, also of 1.3.0"; §4.4 "Done" now cites the 1.3.0 gate
  (`integration_1.3_2026-10-21/gate_release_ed67d25.txt:265`: 8 gated better, 0 worse); §4.5 release text: `v1.2.0` since 20.10, CI-artifact fallback removed (no job uploads one).
* **ALGORITHM.md:** seal state (1.2.0 candidate, 40 files) -> 1.3.0, 42 files, measured `ed67d25`; K2 union and the Falcon far axis are **on** in 1.3.0 (were "off");
  §3.4 min-points factor `1 + n_merged*min_points_scale` -> `max(1, n_frames*min_points_scale)` (`detector.py:854`);
  §5 "only exception is `tracking.hold_misses`" -> list of values that live only in code defaults; §4b "a lost track model makes clear_distance 0" -> lost bed or unconfirmed orientation
  (`clear_lost_model` is off); §3.5b and §6 numbers relabelled as the 29.09 detector with the 1.3.0 values added (five empty 11 episodes / 37 frames, ride 29 episodes / 119 frames, from `integration_1.3_2026-10-21`);
  two dead cross-references fixed. Known gap, not added: the K2 joint-fit axis (`_step_y`, `_curve_clusters`) is not described in the doc.
* **ARCHITECTURE.md:** seal "40 files, 1.2.0_r3" -> 1.3.0, 42 files; input topics "two pairs" -> three (`/iv_points`); CI "5 jobs" -> 6 (checks, pytest, webapp, webapp-e2e x4 shards, docker, offline-build) and which are conditional;
  "uploaded as an artifact" removed; release v1.2.0 added; CI state of 22.10 (#844 on `3a3eabc`); `scripts/clear_past_object.py` -> its path under `integration_1.3_2026-10-21/scripts/`;
  webapp test counts 149/278/44 -> 179/371/78 (collect-only and vitest, not CI pass counts).
* **web/DEMO_HANDOFF.md:** "Seal PASS, 40 files" -> 42 (two places); "two actual runs 19.10 and 22.10" -> two rehearsals planned 20.10 and 22.10, no results in the repository.
* **DATASET.md:** two citations of README sections that no longer exist -> «Сборка, запуск, обработка бэга»; "26 files span 6-12 s" -> 24 (`extended_dataset_intake.json`);
  `person_crossing` 55,4-56,7 -> 54,6-56,7 m, `object_on_rail` X 56,1-56,6 -> 55,9-56,5 and lateral -0,6...-1,2 -> -0,6...-1,0, `person_walkway` 15,4 -> 15,8 m (re-derived from `labels/doubleT_obstacle.json`: 54.64-56.68, 55.91-56.52, 0.9-15.8).
* **SENSOR.md:** removed "ISO 26262 ASIL B" and its consequence: the manual text contains neither "ASIL" nor "26262".
* **organizers/QA_session.md, test_stand_software.md:** "EXPERIMENTS.md §9 / §3" -> `archive/EXPERIMENTS_log_2026-09.md` (the current EXPERIMENTS.md has no numbered sections); ARCHITECTURE heading cited in both languages; DATASET heading cited in both.
* **EVALUATION.md:** Set F start "150-220 m" -> 220 m (`--start`); `bench` does include the health monitor; "current seal gate" -> the 29.09 seal's gate (still the 1.3.0 baseline); §4 numbers labelled as the 29.09 detector.
* **REQUIREMENTS_MAP.md:** v1.2.0 released 20.10 (`3b73bbe`), 1.3.0 sealed (42 files), not released; image name; GPU and EXPERIMENTS heading citations; 8.1 box 0.5 m "1 of 6" -> "2 of 6" (29.09 gate);
  8.5 test and CI state (2 551 passed, 1 known failure, quoted from `integration_1.3_2026-10-21/README.md`; 6 CI jobs; `verify` PASS 42 files).
* **SCORECARD.md:** "seal passes verify, 40 files" -> 1.3.0, 42 files; row 8.5 test state; risk 1: K2 union is on in 1.3.0 (was "pending"); risk 7: 1.3.0 is sealed, not released.
* **RESEARCH.md:** no factual error found; date only.
* **COMPETITOR_SURVEY_2026-10.md:** code line references `clustering.py:349` -> `:733-734`, `config.py:361-365` -> `:437-441`, `opinion.py:28` -> `:30`; "ours 2.1-2.5 per km" and "12 episodes" marked as v1.0.0 measurements; pointer to the archived BACKLOG for closed cards.
* **video/README.md:** the 81-82 ms latency source `judgement_2026-09-28` (which gives 85-94 ms) -> `vm_2026-09-28/summary.md` (3 places); "the final detector of 29.09" -> the detector in the video, not rebuilt, 1.3.0 differs; reserve clip is the 21.10 state with a 1.2.0 image.
* **web/README.md:** "v0.6.3" -> "v0.6.2" for the Docker chain video and `/resense/decision` (two places); source of the overview-video numbers -> the `GATE` block of `make_overview_video.py`.
* **web/P2_REVIEW.md:** "18-slide draft is separate" -> the draft folder was removed on 19.10. **web/P2_STATUS.md:** date only (plus the branch fix in §4).

Not re-dated: `docs/images/README.md` (09-28; the web-player lane edits `docs/images/**`), `docs/EXPERIMENTS.md` (09-29; captain's file), `docs/archive/*` (frozen records, their dates are the record),
READMEs inside evidence folders (not to be changed), `configs/experimental_far_rail_rings.yaml` (a sealed config, not a page).

## 4. Unverified

Anything needing the recordings, a VM, ROS, Docker, a GPU or the network: timing, CPU and memory tables, node behaviour, bag sizes and checksums of downloads, test counts that need `pytest` collection
beyond the figures quoted from evidence (the webapp counts are collect-only/vitest), literature claims in RESEARCH §1-6, the other teams' repositories in COMPETITOR_SURVEY, the voice and the human viewing of the videos,
`scripts/verify_release.sh v1.2.0` (downloads 472 MB). The semantic correctness of the numbers in the 40 READMEs (that a number is attached to the right quantity) was checked by the writing agents against the sources; I checked that every number exists in the sources (§1), not row by row what it means.

## 5. Found, but in files this lane may not edit (for the captain)

* `README.md` (root) lines 132-133 still offer the CI artifact `resense-image-<version>-<commit>` as a fallback; `ci.yml` says no job uploads an artifact.
* `docs/DETECTOR_FREEZE.md` (header, "current state 1.2.0", manifest table) still names the R3 seal (40 files) as the reference; `DEFAULT_MANIFEST` is the 1.3.0 seal (42 files).
* `docs/DECISIONS.md` lines 3-7 (hand-over: K2/K1 "stay off") is not marked as superseded by row 51; row 44 still quotes 113.0 m and 158 lost frames, which `k1_k2_gauge_2026-10-19/P4_PACKAGE.md` and `k2_v5c_2026-10-20` call overstated (122.27 m, 37 frames).
* `docs/BACKLOG.md` ("Current plan", ~l.595) and `CAPTAIN.md` l.168 still say the next J1 is on 1.2.0 (decision 57 releases 1.3.0); BACKLOG l.135 says the preview host "now serves another app", but on 22.10 it returned HTTP 200 titled "ReSense" (`/deployment.json` returns the SPA HTML).
* `docs/EXPERIMENTS.md` and `gitbook/reference/results.md` still have the stale "300/605" clear-distance sentence; `EXPERIMENTS.md:391` cites the ARCHITECTURE heading in English.
* The ARCHITECTURE section «Развёртывание без интернета» is cited in English ("Deployment without internet") in `docs/organizers/answers.md:145`, `ci.yml:354`, `scripts/export_image.sh:16` name ARCHITECTURE «Развёртывание без интернета» in English; `answers.md:108` cites a README section that no longer exists.
* `docs/REQUIREMENTS_MAP.md` §7 contains full names of team members; the CHANGELOG of 20.10 says full names stay out of git. Left unchanged: captain's policy decision.
* Commits cited in docs but absent from the repository: `7464d80`, `a5455b3`, `3eeb106`, `4d218ed`, `ead83747`, `4192f13`, `7b8f638`, `0a68b11`, `972d19a`, `1e2a3ff`, `7290873`, `76bf24e`, `d4b396e` (the dated records are left as they are).
* Folder-versus-doc discrepancies the READMEs record: CHANGELOG_2026-09 l.691 ("5 rows" vs 7 in `gate_2026-09-25/variants/short`) and l.138 ("587 tests" vs 585 + 1 deselected); the "CORRECTION line" in the evidence index row for the second VM is in 7 files of `dry_run_2026-09-25_2/`, not in `offline_2026-09-25_2/`;
  `low_return_support`: the pilot patch is not byte-identical to the gated candidate patch and its candidate commit `1e2a3ff` is not in the repository; `falcon_long_range_2026-10-19/REPORT.md` links `x3_candidate_incomplete.log`, which is not in the folder; `k1_k2_gauge` `SHA256SUMS`: 100 of 105 entries read OK (2 data files and 3 `.pyc` absent).

## 6. References to deleted branches

Live branches (`git ls-remote --heads origin`, 22.10): `main`, `claude/f1a-bounded-1.3`, `claude/integration-1.3`, `claude/ml-far-axis-1.3`, `claude/p1-work-list-verification-o1hdlh`, `claude/review-1.3.0` (`ls_remote_heads_tags_start.txt`, taken at the start; `ls_remote_heads_tags_end.txt`, at the end: other lanes had by then pushed `claude/h1-continue-1.3` and `claude/webapp-cab-finish-1.3`; their content was not examined). The clone was deepened (`git fetch --unshallow`) so that reachability could be tested with
`git merge-base --is-ancestor <sha> <live branch>`.

Replaced in editable pages (commit reachable from a live branch -> SHA):

| name | reachable commit | where |
|---|---|---|
| `ui-improvement` (PR #47) | `8453458` | AGENTS.md, webapp/README.md, gitbook/visualisation/web-prototype.md, web/P2_STATUS.md, docs/CAPTAIN.md |
| `claude/optimistic-mccarthy-z5nmwd` (PR #42) | `0acb18c` | docs/CAPTAIN.md |
| `claude/trusting-dirac-ywtapy` (PR #46) | `6d5fd4b` | docs/CAPTAIN.md |
| `claude/wonderful-planck-tpv33h` (PR #48) | `12582e3` (its tip `4192f13` is not in the repository; the PR was squash-merged) | docs/CAPTAIN.md |
| `final/silent-misses` | `14f83dd` | docs/SCORECARD.md |

Marked "(branch deleted; raw outputs not retained)" (no reachable commit): `claude/sleepy-bohr-nedkui` (its README is kept in `p4_review_final_bundle_2026-10-20/`), `claude/jolly-brahmagupta-ehpapw` (docs/CAPTAIN.md),
`experiment/cross-ring-sparse-evidence`, `gpt-score-push-20260928`, `integration/p3-score-sync-20260928` (docs/P3_SCORE_SYNC_2026-09-28.md; its SHAs `6385ff9`, `8547009`, `290c337`, `ef1d8f5`, `84763cf`, `f41d20a` are not in the repository),
`claude/admiring-pascal-ex9v51` (docs/video/README.md), `r3/axis`, `r3/column` (docs/SCORECARD.md).

**`fix/k1-k2-repair-20261020`:** not reachable (its commits `4d218ed` and `ead83747` are not in the repository; `git fetch origin 4d218ed` fails). Raw outputs gone: about 29 MB of traces, replays, `*.tar.xz`, audits and scripts, and the detector code and tests of the r1-r5a repairs
(`resense/clustering.py`, `config.py`, `detector.py`, `egomotion.py`, `track.py`, `tests/test_k1_*`, `tests/test_k2_*`), as `k1_k2_repair_2026-10-20/PORTED.md` itself says. The markdown records are kept in that folder. The name occurs in `docs/DECISIONS.md` (row 48), `docs/BACKLOG.md` (2 places) and four files of that evidence folder; none can be edited by this lane, so
the note "(branch deleted; raw outputs not retained)" applies to them and is stated here and in the index entry for that folder.

Other gone branches whose commits are cited with SHAs in their own folders: see the evidence READMEs. Outside this lane's files, still naming deleted branches: `README.md` l.40, `CHANGELOG.md` (`ui-improvement`, `det/b4-orientation`, `final/silent-misses`, `r3/on`), `docs/BACKLOG.md` (12 names), `docs/DECISIONS.md` (`det/*`, `claude/optimistic-mccarthy-z5nmwd`, `claude/ml-far-axis-1.3` is live), `scripts/build_deck.py` (`final/silent-misses`), `resense/config.py` (a comment naming `det/falcon-long-range`; sealed), `web/demo/evidence/p2_criteria_2026-09-28.json` (data), all of `docs/evidence/**` and `docs/archive/**` (records). The inventory (73 distinct names found by a regex over the tracked text files, 69 of them not live; some are paths or labels, filtered only roughly) was produced by script, so a differently written branch name may have been missed: the regex needs a slash prefix (`claude/`, `fix/`, `integration/`, `det/`, `r3/`, `final/<known>`) or the name `ui-improvement`; `experiment/...`, `gpt-score-push-...`, `improvement/...` and `wf2/...` were found by hand.

Raw outputs that those docs cite and that are gone: the 29 MB of the K1/K2 repair above; the files that `h1_miss_audit_2026-10-20/manifest-before.json` lists for `b4_release_2026-10-18` (`b4-raw.tar.xz`, `b4-summary.json`, `directed.json`); `falcon_long_range_2026-10-19` (`x3_candidate_incomplete.log`, run `new_off`, `baseline_summary.json`);
`k1_k2_gauge_2026-10-19` (`results/k2wall/k2_1_base_cand3.jsonl`, `results/ride/ride_episodes.jsonl`, the `/opt/work` helper scripts); `low_return_support` (candidate commit); the per-bag JSONL inputs of `caution_policy_2026-10-15`; the baseline `/home/mdm/gate_ref/head_7290873_ride.json` of `gate_2026-09-25/variants`.

## 7. Checks run before each push and the result

See the final message of the session for the commit SHAs, the check results and the CI conclusions of the final head.

## 8. Contents

* `README.md` (this file);
* `ls_remote_heads_tags_start.txt`, `ls_remote_heads_tags_end.txt`: `git ls-remote --heads --tags origin` at the start and at the end of the pass.
