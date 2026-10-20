# Captain Board

> **Purpose:** P1's board: the captain's role, the criteria the captain owns with their current
> score, the work left, the state of the branches, the rules, contracts, owners and decisions. The
> board as it stood until 28.09 (criteria checklist C1–C25, action list, release notes, the
> analysis of 24.09) is archived in
> [`archive/CAPTAIN_board_2026-09-28.md`](archive/CAPTAIN_board_2026-09-28.md); 16–24.09 in
> [`archive/CAPTAIN_log_2026-09.md`](archive/CAPTAIN_log_2026-09.md); the submission history of 29.09, the branch and
> release text of 19.10 before the clean-up and the decision-log rows of 22–29.09 in
> [`archive/CAPTAIN_history_2026-10-19.md`](archive/CAPTAIN_history_2026-10-19.md).
> **Audience:** P1, team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-20, ~19:00 MSK: §1, §3–§5 and §9 against git (`main` `8453458`), GitHub (branches, PRs #42–#47, CI
> runs, releases, tags) and `python3 scripts/detector_freeze.py verify` (PASS, 40 files); §2 numbers against SCORECARD and the
> judgement of 13.10 (v1.0.0, 66/100); §6–§8 paths, the 12 topics and the baseline file against the files; earlier: 2026-10-15,
> D1 pass 1: tag `v1.0.0` → `5d6e9b5`, detector baseline and ownership against the current files. The decision log retains its
> original dates.
> **Status:** current

19.10 D1 supplement: current package/source, release distinction and P2 ownership
were reconciled against the available 18.10 evidence; [receipt and open owner
requests](evidence/p2_d1_2026-10-19/README.md). The earlier review/date and decision
log below remain historical; no fresh public release availability is asserted.

## 1. Role and dates

P1 is the captain: system analyst and ROS 2 / integration developer ([`PLAN.md`](PLAN.md)). The
captain owns the jury chain `docker load` (or `docker build`) `→ docker run → ros2 bag play →
/resense/decision`, the node, Docker, CI and the release, the documents in §8, liaison with the
organizers ([`QUESTIONS.md`](QUESTIONS.md), [`organizers/answers.md`](organizers/answers.md)),
merges and the submission (sent by the captain personally). The pitch and the video went to P2 on
28.09; **on 29.09 evening P2 declined the pitch** after delivering the deck with the team's photos: the
captain owns the pitch again (deck, speech, demo, rehearsals, the defence on 23.10) with agent help,
and the team records the video ([`PRESENTATION.md`](PRESENTATION.md)).

Dates (organizers' README): upload by **29.09 23:59** (target 18:00; the form takes links),
technical expertise 30.09–14.10, pitch 23.10, awards 30.10. The detector changes only through the seal
process (branch, protocol, full gate, independent review, reseal by P1: §6 and
[`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)); the reference seal is
[`detector_freeze_2026-10-20_1.2.0_r3.json`](evidence/detector_freeze_2026-10-20_1.2.0_r3.json) (40 files, measured `0a472d6`),
which the working tree passes; the final reseal follows the final source (§3, §5).

## 2. The captain's criteria and their score

From the independent judgement of **13.10 on v1.0.0** ([`SCORECARD.md`](SCORECARD.md));
maxima are the team's reading of the spec, the organizers publish no weights. These are agent
review scores, not organizer scores; pending work in BACKLOG has not been credited.

| criterion | max | score | what of it is the captain's | what costs points | evidence / next check |
|---|---:|---:|---|---|---|
| **8.3 Speed** (node side) | 10 | **7** | input, catch-up, freshness, timing evidence | 4 vCPU: 360° node p95 111 ms, only 35/201 results current with README flags; literal player 0/146 current, RSS 3.4 GB; no 8-core run | S1 failed (16.10, removed from the runtime, [`DECISIONS.md`](DECISIONS.md) row 33); S2/S5 pending; the historical 29.09 catch-up A/B used explicit step 0.2, not the shipped default 0 |
| **8.5 Technical quality** (CI, Docker, docs) | 10 | **7** | CI, Dockerfile, release workflow, README / ARCHITECTURE / ALGORITHM / EVALUATION, this board | Markdown volume and dated process notes; stale statements | 29.09: README cut to the jury path; EXPERIMENTS compacted (full log archived); dated records archived; stale facts fixed across the docs and the GitBook |
| **8.6 Ease of launch** | 10 | **8** | all of it | `--read-ahead-queue-size 10` and host networking required; build needs internet; non-root player needs HOME | v1.0.0 archive and checksum verified by the judge 13.10; offline node starts in ~3 s; E2 local PASS, tagged run pending |
| **captain's criteria** | **30** | **22** | | | |
| 8.7 Team approach (shared) | 10 | 8 | DECISIONS, the documents' structure | the record was scattered and partly described an older detector | 29.09: one compact EXPERIMENTS, DECISIONS current |
| 8.8 Pitch — **the captain since 29.09 evening**, P2 visuals | 5 | 4 | deck, speech, demo, rehearsals | text-heavy slides, favourable range/timing headlines; live delivery not observed | named deck and videos inspected 13.10; PT1 cuts and PT2 rehearsals tracked in BACKLOG |

The rest of the total is the detector's (8.1, 8.2, 8.4: P3 with P4's evaluation); the detector is
sealed, so moving those needs the captain to unfreeze it (§6, [`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md)).

## 3. Work to do

**Current work per role (20.10, evening): [`BACKLOG.md`](BACKLOG.md) "Current plan"**: priorities instead of dates, **P0** before
the code stop (20.10 23:59 MSK), **P1** before the pitch, **P2** after 23.10. The captain's own list there (P1 table): CI repair,
done (all five jobs green on `main`, runs #667 and #669); the integrity reseal of the R3 source, done (`verify` passes), with P4's
acceptance of the bundle still open; the F1a ride cost, accepted 20.10 and then removed by P3's completion (§9); the open decisions (K2 off unless a candidate passes review
before the code stop, R3 B2: §9); E1, tag and release 1.2.0, delayed until the final source exists (the last commit before the
code stop), then reseal, P4's acceptance, image and tag; final numbers into the deck and speech and the rehearsals (planned
20.10 and 22.10, no completion record; deck, speech and number edits come after the code stop, and rehearsal 2 on 22.10 is the
real deadline); the S5 bench of the final image; the human read of the 29.09 safety review (below); the Falcon results and
1.2.0 status to the organizers if updates are allowed. P1's agent (the second table there): the final gate, X3 and Falcon and
the dust and marked-bag replay on the final source (both after the code stop), the full-suite disposition and the final
numerical pass of the documents. The organizers answered in part on 19.10 ([`organizers/answers.md`](organizers/answers.md)
§12); open: the filter, bag playback, O1.

The full requirement → artifact map and the upload list: [`REQUIREMENTS_MAP.md`](REQUIREMENTS_MAP.md) §4–§5. The submission
history of 29.09 and the list "after the upload" are in the archive; still binding from them: the pitch on 23.10 with two
rehearsals and the live remote demo from a second device ([`../web/DEMO_HANDOFF.md`](../web/DEMO_HANDOFF.md), speech in
[`PRESENTATION.md`](PRESENTATION.md)) · a human read of the safety review of 29.09 night (the agent review: `shell` BLOCKING →
switched off; `explained_run`, the ego veto NON-BLOCKING with documented limits; P1, P3) · the bench on available hardware
with `scripts/bench_8core.sh` (captain, 17.10: 2–4 cores are acceptable; it needs the image, so it waits for the final source).

## 4. Branches (20.10, evening)

Remote refs (GitHub branch list, 20.10 evening): `main` `fb92213` (`769d075` plus two docs-only H1 review commits), `claude/trusting-dirac-ywtapy`, `claude/wonderful-planck-tpv33h`,
`claude/jolly-brahmagupta-ehpapw` (P4's merged PR branches, kept), `claude/sleepy-bohr-nedkui` (P4's final-bundle review, no PR yet) and `claude/p1-work-list-verification-o1hdlh`. Gone from the remote: the integration branch `claude/optimistic-mccarthy-z5nmwd`
(PR #42, merged 19.10 at 23:49 MSK), the four `det/*` agent branches, `ui-improvement` (PR #47, merged 20.10) and the older work
branches of 15–18.10 (merged: PR #33, #35–#38). No open PR.

| branch | state | recommendation |
|---|---|---|
| `main` | `8453458` (PR #47 on `f56ad5e`): the 1.2.0 candidate with the 19.10 integration (PR #42), H1 partial, K2 v5c off (PR #43), the F1a, L16 and R3 repairs and P4's data run (PR #44, #45); `detector_freeze.py verify` PASS (40 files, R3 integrity reseal); CI green at `5d83c5b` (#667) and `f56ad5e` (#669); run #680 on `8453458` **failed** in the webapp browser suite (22 of 75 end-to-end tests; the other four jobs green), so `main` is red since the PR #47 merge; not released | base of everything; the final source is the last commit before the code stop 20.10 23:59 MSK; the red `main` is P2's lane to fix within 1 h or revert (§6) |
| `claude/trusting-dirac-ywtapy` | PR #46, merged 20.10: P4's review of H′ and the Falcon clear-distance model on `cc6226e`, Falcon and the H′-off gate re-run on `f56ad5e`; no detector, config or ROS file touched (checked with `git diff`), small edits to `DETECTOR_FREEZE.md` and `BACKLOG.md` (11 insertions, 5 deletions) | P1 reads the findings and decides on the merge (its `BACKLOG.md` lines overlap with this reconciliation); the findings for P3 are reported, not fixed |
| `claude/wonderful-planck-tpv33h` | PR #48, merged 20.10: P4's switch review of R3 and H1 (`docs/evidence/p4_review_r3_h1_2026-10-20/`, head `4192f13`); its README says it is not the independent review of `0a472d6` itself | P1 reads it; P4 opens the PR |
| `claude/sleepy-bohr-nedkui` | no PR yet: P4's independent final-bundle review of the R3 reseal `f56ad5e` ([README](https://github.com/pmixay/ReSense/blob/7b8f63827ae95661b5c6f4efa615294ae2140a3d/docs/evidence/p4_review_final_bundle_2026-10-20/README.md)): R3's 208 gate metrics and 18,329 rows reproduce, no defect that blocks the seal, accept the B2 STOPs at 37 m; its conditions: the B2 decision recorded, the test record worded "2,387 of 2,387 in the CI-like configuration", H1 stays open, the N5 supplement fixed. It reviews `f56ad5e`, so the F1a completion (`resense/lowobj.py`) is outside it | P4 opens the PR; P1 reads it and decides B2 |
| `claude/p1-work-list-verification-o1hdlh` | no PR: P1's documentation reconciliation of 20.10 (BACKLOG commits `fe08f4f`, `9018b87`, `4635e9e`: CI, seal, `ui-improvement`, K1/K2 moved to P2); CAPTAIN and CHANGELOG are added to it | P1 merges to `main` |

## 5. Release and submission

**v1.0.0 is the only published release** (tag `5d6e9b5`, 29.09, with `resense-image-v1.0.0.tar.gz`, its `.sha256` and
`SHA256SUMS`; the judge verified it on 13.10; GitHub lists no other release or tag, checked 20.10). **1.1.0 (sealed 16.10) was
not released and will not be** (captain, 19.10). The sources carry the **1.2.0 candidate**: all four version declarations are
1.2.0 (`tests/test_release.py`). **The detector seal passes `verify`** ([`detector_freeze_2026-10-20_1.2.0_r3.json`](evidence/detector_freeze_2026-10-20_1.2.0_r3.json),
40 files, measured `0a472d6`, re-run 20.10 ~19:05 MSK on `8453458`). It is an **integrity seal only**: the author checks are
complete, P4's independent acceptance of the final bundle is open. **Release, tag and demo image are delayed (captain, 20.10):**
development is still active and there is no final source yet; the final source is the last commit before the code stop 20.10
23:59 MSK, and only then the reseal, P4's acceptance, the image and the tag of **v1.2.0**. `.github/workflows/release.yml`
builds the runtime image from a pushed `v*` tag, loads the archive back, plays both smoke bags with no internet, runs the E2
check and publishes the archive with its checksums. **CI works now**: all five jobs passed on `main` at `5d83c5b` (run #667)
and `f56ad5e` (#669); run #680 on `8453458` (PR #47) failed in the webapp browser suite (see §4). Since the captain's instruction of 20.10 evening the jobs are `checks`, `changes`, `pytest`, `webapp`, `docker` and `offline-build`; `docker` and `offline-build` run only for a push that touches something the Dockerfile copies, `webapp` (the web tests, kept) only for a push that touches the web prototype or what it uses, and a push of documents runs the first three (`scripts/ci_changes.py`). Pushes only, no pull-request CI. 19.10: 0 of the last 100 runs
succeeded; the failure on `cefd4c4` before any step no longer reproduces; fallbacks: `scripts/release.sh`, `scripts/export_image.sh`. Whether an updated archive may be
re-run is asked in O1 (sent, unanswered).

## 6. Freeze and merge rules

- From 25.09 `main` changes only by a PR with CI green and a review (a lane owner's GitHub review or the code review); the
  captain merges. No branch protection (the captain, 25.09). A red `main` is fixed by its author within 1 h or reverted.
- No edits in another lane's files without the owner's OK (§8), unless the captain orders them. Contract changes (§7):
  `[contract]` in the PR title and a heads-up to the consumers; add, never rename or remove.
- Freeze: detector and config sealed since 27.09 ([`DETECTOR_FREEZE.md`](DETECTOR_FREEZE.md), checked by `verify`; passes since the 20.10 reseal, §5); the node, the image, the tools and the documents change through reviewed PRs with CI green.
- Detector / config gate: `python scripts/regression_gate.py --baseline
  docs/evidence/results/regression_baseline_2026-09-29_shell_off.json` (the baseline of every manifest since 16.10) exits 0 on
  the change. Every gated metric must be identical or better on the six recordings, set O, the ride and set F straight (the last
  two need `/data/cache/new_data`, streamed split by split as in [`VM_GUIDE.md`](VM_GUIDE.md) §2.3; a run without the ride
  passes only with `--allow 'ride.*' --allow 'set_F_straight.*'` named in the PR). Otherwise the PR names each worse metric with
  `--allow` and the captain accepts the trade-off, or it is "tried, not shipped" (EXPERIMENTS §7). The JSON and the table go
  into the PR; a change meant to move the numbers commits a new baseline.
- Numbers only in EXPERIMENTS "Current results" and the README summary; one sprint numbering (PLAN).

## 7. Contracts

| contract | where | consumers |
|---|---|---|
| jury path `docker load` (no internet on the stand; `docker build` where there is) `→ docker run → ros2 bag play → /resense/decision` | README «Кратко для жюри»; GitBook «Приёмочный тест» (`gitbook/guides/acceptance-test.md`) | jury, P2 video |
| release: `v<version>` / `v<version>-rcN` matching the four package versions; assets `resense-image-<tag>.tar.gz`, its `.sha256` and `SHA256SUMS`; v1.0.0 published on `5d6e9b5` | `.github/workflows/release.yml`, `scripts/release_meta.py`, `scripts/verify_release.sh` | jury; P1 E1; P2 demo/fallback |
| 12 topics `/resense/{decision, obstacle_detected, warning, nearest_distance, clear_distance, detections, status, health, markers, corridor_points, latency_ms, fps}` + `/tf_static` | `detector_node.py`, GitBook «Топики и JSON статуса» (`gitbook/reference/topics.md`) | P2, jury |
| status JSON: `stamp, obstacle, warning, nearest_distance, clear_distance, detections[], warnings[], track, health, mount, timing_ms, ego_speed*, n_accumulated, n_*` + `node` (added by the node) | `FrameResult.to_dict()` in `resense/detector.py` | P2 dashboard, `resense run --out` |
| `Frame` (xyz in the vehicle frame, intensity, ring, stamp) | `resense/frame.py` | P3, P4 |
| one parameter file `configs/default.yaml`, root key `resense:`, ROS copy in sync | `resense/config.py`, `scripts/sync_params.sh` | P3 tunes, node loads |
| offline formats: `*.npz` + `gt.json` from `inject`, JSONL from `run` | `resense/cli.py` | P4 `eval`, P2 label tool |

## 8. Ownership map (a file not listed: its author's lane; ask P1)

| path | owner |
|---|---|
| `docker/`, `docker-compose.yml`, `ros2_ws/src/resense_ros/` (except `rviz/`), `scripts/*.sh` (except `build_native.sh`), `scripts/{check_dry_run,make_smoke_bag,cache_to_bag,bench_node_path,bench_summary,check_no_network,release_meta}.py`, `tests/test_release.py` | P1 |
| `README.md`, `CHANGELOG.md`, `gitbook/`, `docs/{README,ARCHITECTURE,ALGORITHM,EVALUATION,SENSOR,PLAN,CAPTAIN,QUESTIONS,SCORECARD,VM_GUIDE,DECISIONS,DETECTOR_FREEZE,RESEARCH}.md`, `docs/archive/`, team notes in `docs/organizers/` | P1 (P3 reviews ALGORITHM) |
| `.github/workflows/ci.yml`, `.github/workflows/release.yml` | `ci.yml`: P4 `pytest` (P2 its `web/demo` steps), P1 the other jobs; `release.yml`: P1 |
| `configs/default.yaml` | P3 values, P1 structure |
| `resense/{track,gauge,clustering,tracking,accumulate,egomotion,lowobj,calibration,health,config,detector,_native}.py`, `native/`, `setup.py`, `scripts/build_native.sh`, `tests/{test_algorithm,test_lowobj_near,test_native,test_cpu_savings,test_late_candidates}.py` | P3 |
| `resense/{frame,pointcloud,sensor}.py` | P1 decoding / P3 geometry |
| `resense/{synthetic,metrics,io,cli}.py`, other `tests/` (`test_node.py`: P1), `labels/`, `scripts/{cache_frames,eval_real,far_range_eval,compare_setf,label_fake_objects,score_fake_objects,short_signature_experiment,unpack_dataset,start_offsets,regression_gate}.py`, `scripts/speed_*.py` (with `tests/test_speed_eval_helpers.py`), `tests/test_regression_gate.py`, `docs/DATASET.md`, `docs/archive/P4_AUDIT.md`, `docs/evidence/results/` | P4 |
| `docs/EXPERIMENTS.md` (the full log of 16–28.09 archived in `docs/archive/EXPERIMENTS_log_2026-09.md`) | P3 / P4; P1 the node timing |
| `web/` (incl. `web/assets/fonts/`, `web/demo/`), `ros2_ws/src/resense_ros/rviz/`, `docs/{images/,img/}`, `scripts/hero_view.py` | P2 (`docs/img/` stays in place: scripts read it) |
| `docs/PRESENTATION.md`, `docs/presentation/`, `scripts/build_deck.py` | P1 owns pitch, content and approval since 29.09 evening; P2 slide cuts, range-chart rendering and visuals (BACKLOG PT1) |
| `docs/video/`, `scripts/make_overview_video.py`, `tests/test_overview_video.py` | P1 coordinates the team's recording; P2 video cards and the release-matched fallback (BACKLOG PT1/PT2) |

## 9. Decision log

The rows of 22–29.09 that are still binding; the full log of 22–29.09 (55 rows, word for word) is in
[`archive/CAPTAIN_history_2026-10-19.md`](archive/CAPTAIN_history_2026-10-19.md). Key decisions with their evidence: [`DECISIONS.md`](DECISIONS.md).

| date | decision | source |
|---|---|---|
| 22.09 | obstacle = anything ≥ 30 × 30 × 10 cm in the 2.1 × 3.0 m envelope, hanging cables included; advisory zone 0.35 m wider | Q&A facts 1–3 |
| 22.09 | train speed: organizers' fact (no odometry, some trains have none) → team decision: operate without it; `ego_speed_mps` / `speed_topic` / `odom_topic` optional, accumulation off unless a speed is given | Q&A fact 6, [`organizers/answers.md`](organizers/answers.md) §4 |
| 25.09 | bed object: a 30 × 30 × 10 cm object on the bed between the rails is **not an obstacle** (organizers' answer to Q3) → the envelope-floor policy of 24.09 is the organizers'; the near-bed path (`lowobj.near_enabled`) stays off for good, its ride / set F re-run is dropped | [`organizers/answers.md`](organizers/answers.md) §8, ALGORITHM §3.3b |
| 25.09 | no internet on the test machine: the image is delivered as a `docker load` archive with its sha256 (`scripts/export_image.sh`, a must in the upload); README step 1 is `docker load`, `docker build` only with internet; CI proves save → load → run with no network; an offline `docker build --cache-from` is best effort only; the dry run runs offline from the archive; the dashboard's roslib bundled; the Dockerfile's layers unchanged before the freeze | [`organizers/answers.md`](organizers/answers.md) §7, C25 |
| 25.09 | the regression gate is the single results check: `scripts/regression_gate.py` against the committed baseline (six recordings + set O; ride and set F where cached; since the rules decision `regression_baseline_2026-09-25_ride.json`, with both); a change that moves the numbers commits a new baseline | EVALUATION §3 step 6, §6 |
| 29.09 evening | P2 declined the pitch after delivering the deck with the team's photos; the captain owns the pitch with agent help, the team records the video; the named deck (names and photos) is committed to the public repository (the user's decision; lifts the placeholder rule of 25.09) | the user, 29.09 |
| 29.09 night | **the `shell` rule off** (`cluster.shell_min_top` 0, `a5455b3`; the user's decision on the safety review): the rule read a floor-standing cluster's own top above the 3.0 m envelope as the lining, so a cable hanging from the vault to the rails, a pole, a standing train were CAUTION beyond 40 m (ray-cast tunnel, 22 m/s: catalogue `cable_low` first STOP 21.0 m on vs 73.8 m off; pole 36.4 vs 104.6 m); alone it bought ride 32 / 31 → 31 / 29. `explained_run` and the ego veto stay (NON-BLOCKING; the ego veto must only get a measured speed). Full gate of the shell-off commit `7464d80` against the `3eeb106` gate: PASS, 6 better, none worse (ride 27 / 30 events / STOP episodes; the five empty recordings, `doubleT_obstacle`, set O and set F first detections as with the rule on); new seal `detector_freeze_2026-09-29_shell_off.json` (`fe27068`) | the user, 29.09; safety review in the doc PR |
| 19.10 | 1.1.0 will not be released; development continues on 1.2.0; the next release, J1 and G3 use the final 1.2.0 seal | the captain, 19.10; [`DECISIONS.md`](DECISIONS.md) row 35 |
| 19.10 | O1 and the five open questions of 16.10 sent to the organizers (send date not recorded); partly answered the same day (row below) | the captain, 19.10; [`organizers/answers.md`](organizers/answers.md) §11 |
| 19.10 | work that depends only on answered questions starts on four agent branches (`det/k1-k2-gauge`, `det/f1-false-alarms`, `det/falcon-long-range`, `det/n3-dust-robustness`) with one combined reseal; C1 waited for the CAUTION answer (it came the same day, row below) | the captain, 19.10; [`BACKLOG.md`](BACKLOG.md) §9 |
| 19.10 | new goal: stable obstacle detection to 300 m on the Falcon Prime (card N7) | the captain, 19.10; [`DECISIONS.md`](DECISIONS.md) row 38 |
| 19.10 | update the deck, speech and rehearsal plan for 1.2.0 and the second lidar; rehearsals planned for 20.10 and 22.10 | the captain, 19.10; [`PRESENTATION.md`](PRESENTATION.md) |
| 19.10 | organizers' answers recorded (in-gauge = obstacle, moving objects, no labels but marked bags + `obstacles.md`, dust in every synthetic bag); the markers become the reference for the synthetic bags; the organizers' dust is a non-regression set; the four agents informed | organizers via the captain, 19.10; [`organizers/answers.md`](organizers/answers.md) §12, [`DECISIONS.md`](DECISIONS.md) row 39, [evidence](evidence/synth_markers_2026-10-19/README.md) |
| 19.10 | the four agent branches merged into the integration branch with every switch off (identity proven on the full gate per frame and the whole Falcon recording); agents stopped with handoffs, their remaining work continues in P1's session and per role | the captain, 19.10; [`DECISIONS.md`](DECISIONS.md) row 40 |
| 19.10 | switches: F1a on (B1 risk accepted, P3 improves), H′ on, R3 on, L16/S3 on, K2 on (variant from v5, P4 develops), Falcon clear-distance model kept; S2, Falcon far range (P3) and the dust guard off | the captain, 19.10; [`DECISIONS.md`](DECISIONS.md) row 41 |
| 19.10 | code stop 20.10 23:59 MSK; dated targets replaced by priorities (P0 before code stop, P1 before the pitch, P2 after 23.10) | the captain, 19.10; [`DECISIONS.md`](DECISIONS.md) row 42, [`BACKLOG.md`](BACKLOG.md) "Current plan" |
| 19.10 | K2 on as variant B (v5b without K1), the set O `small_center` gate exception accepted; improving K2/K1 is P4's first P0 | the captain, 19.10; [`DECISIONS.md`](DECISIONS.md) row 43, [package](evidence/k1_k2_gauge_2026-10-19/P4_PACKAGE.md) |
| 19.10 | K2 held off after the Falcon run (variant B stopped the walking person 12 m later: 124.8 → 113.0 m, 158 person STOP frames lost); P4 resolves the problems and brings it back for a new decision | the captain, 19.10; [`DECISIONS.md`](DECISIONS.md) row 44, [package](evidence/k1_k2_gauge_2026-10-19/P4_PACKAGE.md) |
| 20.10 | the partial H1 improvement (positive collision core, `cluster.column_core_margin` 0.02) is published in `main` without closing the finding; H1 / High stays OPEN | the user, 20.10; [`DECISIONS.md`](DECISIONS.md) row 45, [record](evidence/h1_partial_integration_2026-10-20/README.md) |
| 20.10, in session | release, tag and demo image are delayed: development is still active, there is no final source yet; the final source is the last commit before the code stop 20.10 23:59 MSK, and only then reseal, P4 acceptance, image and tag | the captain, made in session on 20.10 (not yet in `DECISIONS.md`); [`BACKLOG.md`](BACKLOG.md) E1 |
| 20.10, in session | the dust and marked-bag replay on the final source is delayed for the same reason (it needs the final source) | the captain, in session, 20.10; [`BACKLOG.md`](BACKLOG.md) N3 |
| 20.10, in session | K1/K2 moved from P4 to P2 (P2 has started; no P2 K1/K2 branch or PR is visible on GitHub yet, checked 20.10 ~19:00 MSK) | the captain, in session, 20.10; [`BACKLOG.md`](BACKLOG.md) P2 table |
| 20.10, in session | deck, speech and presentation-number edits (`PRESENTATION.md`, `scripts/build_deck.py`, the deck) are done after the code stop; rehearsal 2 on 22.10 is the real deadline for them | the captain, in session, 20.10; [`BACKLOG.md`](BACKLOG.md) PT1/PT2 |
| 20.10, in session | a separate agent is building a short Falcon demo bag (window of `falcon_test` around 280–330 s); its handoff text is applied after the code stop | the captain, in session, 20.10; built 20.10; the captain keeps the file on Google Drive and the repository holds its pointer, checksums and `metadata.yaml` ([record](evidence/falcon_demo_bag_2026-10-20/README.md) §8); the Drive link is readable by anyone who has it and the repository is public |
| 20.10, in session | P4 and P2 are working; no ping needed | the captain, in session, 20.10 |
| 20.10, in session | **the repaired F1a was accepted as shipped, with its ride cost, and P3's completion (decision 46) then removed the cost: ride 23 → 18 events, 26 → 24 episodes, 111 → 102 alarm frames, the pre-repair values, read from the raw gate JSON by P1's session.** The acceptance was: (alarm events 18 → 23, STOP episodes 24 → 26 against the intermediate starting main; against the registered baseline the ride is better: 27 → 23 events, 30 → 26 episodes, 126 → 111 alarm frames). No further F1a code change before the code stop; follow-up after the pitch: P3, the tracker chains on rail-head fragments. Reasons: the full gate passes against the registered baseline without `--allow`; P4 reproduced the numbers and traced all 16 changed decisions (9 new STOP frames on rail-head fragments, no object above the rail head) and found no real object lost on the recordings (T4); the repair restores the real low obstacle the capped-top check dropped (8 → 0 STOP frames on P4's raised-rail box) and keeps 12 of 12 two-rail fragments as ordinary tracks, so reverting would bring back two known misses; a tuning change now would need code, a gate run, review and a reseal before 23:59. | the captain delegated the choice to Claude ("make best decision for F1a to support P3"); the captain can overrule. [F1a repair](evidence/f1a_b1_2026-10-20/README.md), [P4 acceptance run](evidence/f1a_acceptance_2026-10-20/README.md), [T4](evidence/f1a_exposure_2026-10-20/README.md) |
| 20.10, in session | the Falcon clear-distance finding of PR #46 (38 of the Falcon frames 4373–4414: the detector's clear distance lies beyond a person-like object 2.5–7 m ahead while the frame is not STOP) moved from P3 to P2 (evening; P2 decides by ~22:15 MSK between a documented limit and a gated fix) | the captain, in session, 20.10; [`BACKLOG.md`](BACKLOG.md) P2 table |
| 20.10, in session | the red `webapp` job on main and the record of the commit the live preview was built from move from P2 to the captain, who does them separately | the captain, in session, 20.10; [`BACKLOG.md`](BACKLOG.md) P1 table |
| 20.10, **open** | **not decided, owner the captain:** K2 stays off unless a candidate passes review before the code stop | [`DECISIONS.md`](DECISIONS.md) row 44; K1/K2 are P2's ([`BACKLOG.md`](BACKLOG.md)) |
| 20.10, **open** | **not decided, owner the captain:** R3 B2 — P3 says the STOP on co-moving physical targets is correct, P4's switch review leaves the labelling to the captain and P4's final-bundle review recommends accepting it | [R3 completion](evidence/r3_completion_2026-10-20/README.md), [P4's switch review](https://github.com/pmixay/ReSense/blob/4192f13ea9c44fabb7ce4d96b84ee13d3021fee6/docs/evidence/p4_review_r3_h1_2026-10-20/README.md) (branch `claude/wonderful-planck-tpv33h`) |

*Experimental branch integration of 28.09:* accepted P3 changes and health histogram optimization: measured commits, acceptance
checks and remaining work in [`P3_SCORE_SYNC_2026-09-28.md`](P3_SCORE_SYNC_2026-09-28.md) and the
[health evidence](evidence/cycle_2026-09-28/health_histogram/README.md); the historical 61/100 judgement assessed `464f5bc`, the current 13.10
judgement of v1.0.0 is 66/100 (§2).
