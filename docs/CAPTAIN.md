# Captain Board

> **Purpose:** P1's board: the captain's role, the criteria the captain owns with their current
> score, the work left, the state of the branches, the rules, contracts, owners and decisions. The
> board as it stood until 28.09 (criteria checklist C1–C25, action list, release notes, the
> analysis of 24.09) is archived in
> [`archive/CAPTAIN_board_2026-09-28.md`](archive/CAPTAIN_board_2026-09-28.md); 16–24.09 in
> [`archive/CAPTAIN_log_2026-09.md`](archive/CAPTAIN_log_2026-09.md).
> **Audience:** P1, team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-29 evening: GitHub (0 tags, 0 releases, no open PR; `main` at `7532a6b`,
> PR #29, CI green), the seal (`1e2ed82`, verify PASS), 1 279 tests passing on `7532a6b`, the VM run of
> 28.09 and the independent judgement of 28.09 ([`SCORECARD.md`](SCORECARD.md)); the requirements map
> [`REQUIREMENTS_MAP.md`](REQUIREMENTS_MAP.md).
> **Status:** current

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
technical expertise 30.09–14.10, pitch 23.10, awards 30.10. The detector is sealed; only the node,
the image, the tools and the documents change (§6).

## 2. The captain's criteria and their score

From the independent judgement of 28.09 evening ([`SCORECARD.md`](SCORECARD.md), not re-scored
since); maxima are the team's reading of the spec, the organizers publish no weights.

| criterion | max | score | what of it is the captain's | what costs points | done since the judgement |
|---|---:|---:|---|---|---|
| **8.3 Speed** (node side) | 10 | **7.5** | the node's input path, catch-up, freshness, the timing evidence | slow start-up (e2e p95 0.5–1.1 s over the first seconds at 360°); stale output under the default player; no 8-core measurement | 29.09: faster decode, warm-up, 5 Hz start-up catch-up — first 3 s at 360° 312–325 → 38–105 ms median e2e, all results p95 410–447 → 212–344 ms (cold 864–1084 → 333–599 ms), identical decisions ([evidence](evidence/node_startup_2026-09-29/README.md)); `check_dry_run.py` reports the playback pace and the start-up lag |
| **8.5 Technical quality** (CI, Docker, docs) | 10 | **7** | CI, Dockerfile, release workflow, README / ARCHITECTURE / ALGORITHM / EVALUATION, this board | Markdown volume and dated process notes; stale statements | 29.09: README cut to the jury path; EXPERIMENTS compacted (full log archived); dated records archived; stale facts fixed across the docs and the GitBook |
| **8.6 Ease of launch** | 10 | **7** | all of it | no published image archive for README step 1; `--read-ahead-queue-size 10` required; `--net=host` | 29.09: the node exits cleanly on Ctrl+C; the start-up burst is caught up faster |
| **captain's criteria** | **30** | **21.5** | | | |
| 8.7 Team approach (shared) | 10 | 8 | DECISIONS, the documents' structure | the record was scattered and partly described an older detector | 29.09: one compact EXPERIMENTS, DECISIONS current |
| 8.8 Pitch — P2 28.09, **the captain again since 29.09 evening** | 5 | 3 | the deck, the speech, the demo, rehearsals | silent video, team slides without names, dense slides, no rehearsal | 29.09: the deck with the team's photos and current numbers, the speech and the video script ([`PRESENTATION.md`](PRESENTATION.md)) |

The rest of the total is the detector's (8.1, 8.2, 8.4: P3 with P4's evaluation); the detector is
sealed, so moving those needs the captain to unfreeze it (§3, item 6).

## 3. Work to do

H = only a person can do it; A = an agent can do it, the captain merges. The full requirement →
artifact map and the upload list: [`REQUIREMENTS_MAP.md`](REQUIREMENTS_MAP.md) §4–§5.

**Before the upload (29.09, closes 23:59 MSK):**

| # | item | who | state |
|---|---|---|---|
| 1 | **Final documentation pass** (every doc against `7532a6b`, the 29.09 rules in ALGORITHM / EXPERIMENTS / DECISIONS, the pitch deck with current numbers, the requirements map, the judgement's offline measurements re-run on `7532a6b` as `evidence/judgement_2026-09-29/`) → one PR from `claude/admiring-pascal-ex9v51`; merge after CI is green. Docs only: no sealed file changes. | A; H merges | in progress |
| 2 | **Release candidate:** push `v1.0.0-rc2` on the commit of the new seal (the image's code is final there; `rc1` on `7532a6b` is cancelled: it still has the `shell` rule). `release.yml` publishes the archive; then on the team VM, logged out: download, `sha256sum -c`, `IMAGE_TAR=… OFFLINE=1 scripts/dry_run.sh` on `doubleT_obstacle` and `roundT_doubleT`; commit the output as `evidence/vm_2026-09-29/`. The agent session cannot push tags (its git proxy takes only its branch). | H tags, H runs the VM | after the reseal |
| 3 | **Final release:** push `v1.0.0` on the final `main` after item 1 merges; check the release assets and their sha256. | H | after 1 |
| 4 | **Submit** (links): the repository with the final commit hash, the `v1.0.0` archive and its sha256, the video, the deck (PDF), the GitBook — every link opened logged out first. | H | after 3 |
| 5 | Keep `--read-ahead-queue-size 10` prominent in every instruction: with Humble's default read-ahead the results stay stale. | A | done in README / GitBook |

**After the upload:**

| # | item | who |
|---|---|---|
| 6 | Answer the organizers daily during the expertise 30.09–14.10; new answers into `organizers/answers.md` (no question open). | H |
| 7 | Pitch on 23.10: two rehearsals, the live remote demo from a second device ([`../web/DEMO_HANDOFF.md`](../web/DEMO_HANDOFF.md)), the speech of [`PRESENTATION.md`](PRESENTATION.md). | P1 + team |
| 8 | A human read of the safety review of 29.09 night (the agent review: `shell` BLOCKING → switched off; `explained_run`, the ego veto NON-BLOCKING with documented limits). | P1, P3 |
| 9 | If an 8-core machine is available: `scripts/bench_8core.sh` on both original bags, evidence committed. | H (+ A) |

## 4. Branches other than `main` (29.09 evening)

Checked on GitHub: `main` and one other branch; no open pull request.

| branch | state | recommendation |
|---|---|---|
| `claude/admiring-pascal-ex9v51` | the final documentation pass (item 1) | PR to `main` tonight |
| `claude/prototype-website-rebuild-tz31o0` | a work-in-progress web app (FastAPI backend, React pages in the «Линия» design; its last commit says the player and system pages are partial); not merged into `main` | **do not merge before the upload**; decide after 30.09 |
| `experiment/cross-ring-sparse-evidence`, `claude/funny-gates-3358a8`, `claude/amazing-fermi-t67v8g`, `gpt-score-push-20260928` | merged into `main` (PR #27, #28, #29) or deleted on the remote | nothing to do |

## 5. Release and submission

No tag or release exists yet (GitHub, 29.09 19:30 MSK). `.github/workflows/release.yml` publishes one
per pushed tag `v1.0.0-rcN` / `v1.0.0` (§3, items 2–3): it builds the runtime image from the tag,
removes it, loads the archive back, plays both smoke bags through the loaded image with no internet
and publishes `resense-image-<tag>.tar.gz`, its `.sha256` and `SHA256SUMS`. The version in
`pyproject.toml`, `resense/__init__.py`, `package.xml` and `setup.py` is 1.0.0, kept equal by
`tests/test_release.py`. Fallbacks: the CI artifact of a `main` run (GitHub login, 30 days) or
`scripts/export_image.sh` on a machine with internet. The submission is the captain's personally.

## 6. Freeze and merge rules

- From 25.09 `main` changes only by a PR with CI green and a review: a lane owner's GitHub review
  or the code review (the captain, 25.09: PR #12 counts as reviewed by the code review of 25.09;
  P2, P3 and P4 will not review it, and the lane-owner review is lifted for it);
  the captain merges. No branch protection (the captain, 25.09: not needed). A red `main` is fixed
  by its author within 1 h or reverted. 25.09: PR #11 (the `main` fix) went in without a review,
  3.5 min after opening; PR #12 is the first to follow the rule.
- No edits in another lane's files without the owner's OK (§8), unless the captain orders them
  (25.09: the dashboard regressions in P2's lane, the P3 detector items, fixed by agents). Contract changes (§7): `[contract]`
  in the PR title and a heads-up to the consumers; add, never rename or remove.
- Freeze: detector and config sealed since 27.09 (`docs/DETECTOR_FREEZE.md`, checked by CI); the node, the image, the tools and the documents change through reviewed PRs with CI green.
- Detector / config gate: `python scripts/regression_gate.py --baseline
  docs/evidence/results/regression_baseline_2026-09-29_competitor_rules.json` (the sealing gate of `1e2ed82`) exits 0 on the change. Every
  gated metric must be identical or better on the six recordings, set O, the ride and set F
  straight (the last two need `/data/cache/new_data`, streamed split by split as in
  [`VM_GUIDE.md`](VM_GUIDE.md) §2.3; without it their rows fail as "missing in this run", and a run
  without the ride passes only with `--allow 'ride.*' --allow 'set_F_straight.*'` named in the PR). Otherwise the PR names each worse metric with `--allow` and the
  captain accepts the trade-off, or it is "tried, not shipped" (EXPERIMENTS §7). The JSON and the
  table go into the PR. A change meant to move the numbers commits a new baseline. Nothing in the
  gate needs the organizers' stand.
- Numbers only in EXPERIMENTS "Current results" and the README summary; one sprint numbering (PLAN).

## 7. Contracts

| contract | where | consumers |
|---|---|---|
| jury path `docker load` (no internet on the stand; `docker build` where there is) `→ docker run → ros2 bag play → /resense/decision` | README «Кратко для жюри»; GitBook «Приёмочный тест» (`gitbook/guides/acceptance-test.md`) | jury, P2 video |
| release (deferred by the captain, 25.09; inert until a tag is pushed): tags `v1.0.0-rcN` / `v1.0.0` only; assets `resense-image-<tag>.tar.gz`, its `.sha256` and `SHA256SUMS` | `.github/workflows/release.yml`, `scripts/release_meta.py`, `scripts/verify_release.sh` | the later deployment |
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
| `web/` (incl. `web/assets/fonts/`, `web/demo/`), `ros2_ws/src/resense_ros/rviz/`, `docs/{PRESENTATION.md,images/,img/,video/,presentation/}`, `scripts/{build_deck,hero_view,make_overview_video}.py`, `tests/test_overview_video.py`; the pitch and the video since 28.09 | P2 (`docs/img/` stays in place: scripts read it) |

## 9. Decision log

| date | decision | source |
|---|---|---|
| 22.09 | obstacle = anything ≥ 30 × 30 × 10 cm in the 2.1 × 3.0 m envelope, hanging cables included; advisory zone 0.35 m wider | Q&A facts 1–3 |
| 22.09 | no map: the tunnel model is rebuilt from every frame | Q&A fact 15 |
| 22.09 | train speed: organizers' fact (no odometry, some trains have none) → team decision: operate without it; `ego_speed_mps` / `speed_topic` / `odom_topic` optional, accumulation off unless a speed is given | Q&A fact 6, [`organizers/answers.md`](organizers/answers.md) §4 |
| 22.09 | CPU-only image; any GPU stage optional with a CPU fallback | `organizers/test_stand_software.md` |
| 23.09 | confirmation 0.5 s (v0.6.2), a STOP held over one missed frame (v0.6.3); Fast DDS over UDP only in the image, `input_reliability: auto` | EXPERIMENTS §0, §3b |
| 24.09 | bed policy: nothing below the envelope floor (0.12 m above the rail head) between the rails is reported; asked as Q3, **confirmed by the organizers on 25.09** (a bed object is not an obstacle, row of 25.09 below) | ALGORITHM §3.3b, [`organizers/answers.md`](organizers/answers.md) §8 |
| 24.09 | opt-in near-bed path (`lowobj.near_enabled`) and far-rail check (`track.rails_far_check_enabled`) stay off: near-bed first gates 47 → 667 ride events (raw not committed); current gates (`537e220` + box fix `7df1796`) five bags 20 → 107 events, ride not re-run; far-rail unmeasured | ALGORITHM §6, EXPERIMENTS §1e |
| 24.09 | mount: test bags use the provided mounts, LiDAR 1075 mm above the rail head on the centreline; auto-calibration stays as a safeguard (it measures 1.12 m / −0.02 m on `roundT_doubleT`) | [`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md) |
| 24.09 | switch glitches are not counted against us → station / platform false STOPs come first for P3 | `mount_and_switch_qa.md` §5 |
| 24.09 | the criteria judgement in SCORECARD replaces every earlier scorecard; the release tag is no longer deferred (rc1 on 27.09 18:00; its name is `v1.0.0-rc1` since 25.09, the only form the release workflow accepts); deferred again by the captain on 25.09 (row below) | §1, §5 |
| 24.09 | train speed, measured: estimator accurate, but even a perfect speed gives no earlier STOP on set O and more false STOPs; `estimate_speed` stays `false`, a given speed is honoured | EXPERIMENTS §9 |
| 24.09 | no GPU before 29.09 (≤ 30–45 ms per 360° frame at best, untestable in CI, container start depends on the host toolkit) | ARCHITECTURE "GPU: evaluated, not used" |
| 24.09 | C++ kernels merged on the branch (bit-identical, −38…−57 %); to `main` only after the CI docker job and with an 8-core bench to follow; `RESENSE_NATIVE=0` is the fallback | ARCHITECTURE "Native kernels" |
| 25.09 | no run on the organizers' stand before submission (they give no access): timing on the team's own 8-core machine (action 7), the dry run on a clean team machine or the VM (action 15), the Docker chain in CI; stand facts and estimates stay, labelled as such | [`organizers/answers.md`](organizers/answers.md) §6 |
| 25.09 | no internet on the test machine: the image is delivered as a `docker load` archive with its sha256 (`scripts/export_image.sh`, a must in the upload); README step 1 is `docker load`, `docker build` only with internet; CI proves save → load → run with no network; an offline `docker build --cache-from` is best effort only; the dry run runs offline from the archive; the dashboard's roslib bundled; the Dockerfile's layers unchanged before the freeze | [`organizers/answers.md`](organizers/answers.md) §7, C25 |
| 25.09 | the regression gate is the single results check: `scripts/regression_gate.py` against the committed baseline (six recordings + set O; ride and set F where cached; since the rules decision `regression_baseline_2026-09-25_ride.json`, with both); a change that moves the numbers commits a new baseline | EVALUATION §3 step 6, §6 |
| 25.09 | DBSCAN on cKDTree ships (exact scikit-learn labels, per-frame output identical, gate PASS on the merged code); the forward crop and the bed-height reuse do not (no gain on the native path) | ARCHITECTURE "Native kernels", EXPERIMENTS §7 |
| 25.09 | the long overhead rule and the short-signature rule are merged **off** (`cluster.floating_long_min_length`, `cluster.short_signature_max_length` = 0), for a go / no-go after the ride; decided the same day (the rules-decision row below) | EXPERIMENTS §1f, action 11 |
| 25.09 | the node keeps its UDP-only Fast DDS profile: stock Fast DDS clients (shared memory on) reach it over UDP, proven in CI with a uid-1000 player and listener | C4, `scripts/console_test.sh` |
| 25.09 | the public deck keeps the 17 team placeholders by design; personal data only in the private `--team` build | PRESENTATION, action 8 |
| 25.09 | upload by links, no file-size limit (organizers): the form gets the repository at the release tag with its commit hash, the release asset `resense-image-v1.0.0.tar.gz` with its sha256 (published by `.github/workflows/release.yml` on the tag push; `scripts/release.sh` by hand), the video and the presentation; every link opened logged out and the archive loaded on a second machine before submitting; superseded the same day: the submission is the captain's and releases are deferred (rows below) | [`organizers/answers.md`](organizers/answers.md) §8, action 1b |
| 25.09 | intermediate submission not held as a separate upload: the organizers' timeline has no such stage; the §7.1 content is in the repository | C14, [`organizers/answers.md`](organizers/answers.md) §4 |
| 25.09 | bed object: a 30 × 30 × 10 cm object on the bed between the rails is **not an obstacle** (organizers' answer to Q3) → the envelope-floor policy of 24.09 is the organizers'; the near-bed path (`lowobj.near_enabled`) stays off for good, its ride / set F re-run is dropped | [`organizers/answers.md`](organizers/answers.md) §8, ALGORITHM §3.3b |
| 25.09 | version 1.0.0 and one release path: a pushed `v1.0.0-rcN` / `v1.0.0` tag (no other name) runs `.github/workflows/release.yml`, which builds the runtime archive, proves it (removed, loaded back, both smoke bags through the loaded image) and publishes it with its `.sha256` and `SHA256SUMS` as the GitHub release; the tags (`v1.0.0-rc1` by the agent, `v1.0.0` on `main` on 29.09) were deferred by the captain the same day (row below); `scripts/release.sh` is the manual fallback | C13, §5, CHANGELOG "Unreleased" |
| 25.09 | the overview video ships captioned and silent (`docs/video/resense_overview.mp4`, 2:50, Russian subtitles burned in and as `.srt`); a voice-over is optional, muxed on without re-editing; C20 done | C20, action 9, PRESENTATION «Сборка ролика» |
| 25.09 | `offline-build` is a gate (continue-on-error removed after 4 of 4 green runs) and plays both synthetic bags through the runtime image loaded from the release archive on an `--internal` network; green on `5a15c7c` and `79109f5`; C25 done | C25, `.github/workflows/ci.yml` |
| 25.09 | long overhead rule on (`cluster.floating_long_min_length` 3.0), short-signature rule off: decided on the ride against pre-registered criteria; ride 204 / 47 / 39 → 197 / 46 / 39; short signatures would add 6 STOP episodes on the ride for +49 set O STOP frames | EXPERIMENTS §1f, [`rules_decision_2026-09-25.json`](evidence/results/rules_decision_2026-09-25.json), action 11 |
| 25.09 | review finding fixed (the captain: "fix it"): the long overhead rule's along-track branch applies only when the cluster's lowest point is above `cluster.floating_long_min_bottom` 1.6 m (a tray / duct / pipe fallen onto the axis 0.7–1.6 m above the rail is a STOP again); pre-registered 2.0 / 1.8 / 1.6 m, the highest keeping every gain: 2.0 and 1.8 m bring back the ride event at 105–110 m (ride 46 → 47 events; 1.8 m also 39 → 40 STOP episodes), 1.6 m identical frame by frame on the six recordings, the ride, set O and set F straight; the gate baseline stays; a long cluster near the axis with its bottom above 1.6 m stays advisory | EXPERIMENTS §1f, ALGORITHM §3.3 / §6, [`long_rule_bottom_2026-09-25.json`](evidence/results/long_rule_bottom_2026-09-25.json) |
| 25.09 | no tags or releases now (the captain: "we don't need releases now, the system is still actively developing"): `.github/workflows/release.yml` and the release scripts stay, inert until a tag is pushed; every step that scheduled a tag or a release (`v1.0.0-rc1` on 27.09, `v1.0.0` on 29.09, the release checks, the archive exports for them) is deferred; the package version stays 1.0.0 | C13, actions 14, 14b, 16, §5, CHANGELOG "Unreleased" |
| 25.09 | the submission is the captain's (the captain: "I will send it myself with all links"): `docs/SUBMISSION.md` removed and every link to it replaced (jury commands: README; dry run: README "Acceptance test and CI", `scripts/dry_run.sh`, the VM brief, now [`VM_GUIDE.md`](VM_GUIDE.md); offline delivery: ARCHITECTURE "Deployment without internet"); C12 HANDLED | C12, action 16, §5 |
| 25.09 | deployment and the presentation later (the captain: "we will deploy the project and make the presentation later"): the image archive export or release, the clean-machine and offline dry run and the bench on the 8-core stand-in wait for the deployment (VM kit ready; reduced to instructions the same day, row below); the deck, the team slides and the video voice-over are the team's later work | C7, C8, C21, actions 7, 8, 13, 15 |
| 25.09 | VM kit reduced to instructions (the captain: remove the kit's automation scripts, keep instructions only, no hard-coded fixes; the code review had found the feature branch built in as the default clone target): `scripts/vm/` removed (`setup_vm.sh`, `fetch_data.sh`, `run_plan.sh`, `lib.sh`, `stream_cache.py`); its brief rewritten as [`VM_GUIDE.md`](VM_GUIDE.md): plain commands of the repository's tools with variables the reader sets (no branch, address or machine path built in), the ride streamed split by split with `curl`, `zstd`, `tar` and `scripts/cache_frames.py`, the offline rehearsal as steps with the restore armed first | C7, C8, C25, actions 7, 15 |
| 25.09 | dry-run drops (the VM run): the node lost no frame; of the 20 "after 5 s" on `doubleT_obstacle`, 16 were the start-up catch-up's own skips (the player's 5.7–6.5 s preload, back on the newest frame at +7.7–7.9 s) and 4 are missing from the recording itself. The node reports the skips (`node.catchup_skipped`, `node.catchup`; `dropped_frames` unchanged); `check_dry_run.py` counts drops after the later of 5 s and the end of the start-up catch-up (at most 15 s; a catch-up that never ends still fails) and, with `--bag` (passed by `dry_run.sh`), against the recording's own messages; BLAS / OpenMP one thread outside the image too. The criterion "no frame lost in steady state" is unchanged | EXPERIMENTS §3a, `5be4143`, C7 |
| 25.09 | CycloneDDS host player: the image's UDP profile asks for a 32 MiB receive buffer (was 8 MiB; the kernel caps it at `net.core.rmem_max`, so nothing changes on a stock host), the node logs one WARN below 32 MiB; a jury console on CycloneDDS needs `sudo sysctl -w net.core.rmem_max=33554432` on the host (README, ARCHITECTURE, VM_GUIDE §4.2). The organizers' default, Fast DDS, is not affected | EXPERIMENTS §3b, `5be4143`, C4 |
| 25.09 | `tracking.column_hold` 2 ships (the captain's delegation of 25.09: detector rules that do not need the stand are the agents' to decide): a track demoted as a `column` in ≥ 2 of its last 10 hits stays advisory (the `roundT_doubleT` column at 101–149 m: 3 alarm frames at 111–115 m in all 10 VM captures → ≤ 1). Pre-registered at 12:18 UTC before any run: of 3 / 2 / 1 the highest with ≤ 2 alarm frames on every VM capture and no gated row worse; 3 failed the gate (ride STOP episodes 39 → 40), 2 passed (7 rows better, none worse): five bags 60 / 14 / 17 → 58 / 13 / 16, ride 197 / 46 / 39 → 187 / 46 / 39, set F straight false detections 56 → 35, `doubleT_obstacle`, set O and set F detections identical. New baseline `regression_baseline_2026-09-25_ride_column.json`. Safety test: a person beside a column is a STOP on its usual frame; one who stood in front of it ≥ 2 frames and steps onto the axis gets it 4 frames later | EXPERIMENTS §3a, [`column_hold_2026-09-25.json`](evidence/results/column_hold_2026-09-25.json), `d117c8c` |
| 25.09 | PR #12 counts as reviewed (the captain: "CI ran and you ran code review before"): the code review of 25.09 plus green CI on every push satisfy the review rule of §6; the captain merges it when he chooses; C16 DONE | C16, action 3b, §6 |
| 25.09 | no branch protection on `main` (the captain: "we don't need this"): the merge rules of §6 stay as a team rule, not enforced by GitHub | §6, action 1 |
| 25.09 | C8 closed on the 4-core team VM (the captain: "if 4 core ran matched expectations it will run even better or similar on 8 core"): native p95 70 ms at 10 fps on 4 physical cores, drops explained (C7); no 8-core run needed; the VM re-run of VM_GUIDE §4.0 repeats the bench as a confirmation | C8, action 7, EXPERIMENTS §3a |
| 25.09 | jury step 0: the README jury commands start with `sudo sysctl -w net.core.rmem_max=33554432` (the second team VM: a host player delivered 0–1 of 201 360° clouds at Ubuntu's 212992 in 5 of 5 runs, all at 32 MiB; recorded as stock Fast DDS, **corrected 25.09 evening: it was CycloneDDS**, and a genuine Fast DDS player passes at 212992 on the first and third VMs, so step 0 is for CycloneDDS consoles); an opt-in shared-memory mode for the node was built; §4.6 passed on the third VM, the default flip is open | C4, EXPERIMENTS §3b, README «Кратко для жюри» |
| 25.09 | C4 closed on the jury instructions (decided by the agent, delegated by the captain): README step 0 `sudo sysctl -w net.core.rmem_max=33554432` and the node's WARN; the opt-in shared-memory mode (`RESENSE_DDS=shm`) continues as an improvement, its default flips only after a VM pass | C4 |
| 25.09 | Q1–Q2 sent by the captain; the team told the §6 rules; PR #12's merge is not a blocker (merging it completes action 3b); releases stay later | C15, actions 1, 2, 3b, C13 |
| 25.09 | no lane-owner review of PR #12 (the captain: P2, P3 and P4 will not review it): the code review of 25.09 and green CI stand; the requested reviews are not waited for | C16, §6 |
| 25.09 | P4's standing duties dropped (the captain: "we are operating with it ourselves"): the captain and the agents hold the frame caches and run the regression gate on every detector change; the review of P4's lane in PR #12 is not needed | action 3, §10 row 4 |
| 25.09 | the dashboard regressions of P2's lane (the keyboard guard found by the code review, and any others) are fixed by an agent on the captain's order; P2 is not waited for | §6, PR #12 comment |
| 25.09 | P3 round 1 (the captain: "complete all P3 tasks that don't depend on other roles"), each item against pre-registered criteria: the rail-shadow rules ship (`track.floor_shadow_*`, `cluster.oversize_split_*`, `cluster.gauge_distance`; set O #1's wrong 3.0 m distance gone, the plank held from 90.8 m, set F false detections 35 → 24), after a safety review that made the distance never later than the envelope entry and capped the bed hold; platform end, far switch parts and far bed bins tried, not shipped (flags off) | EXPERIMENTS §1h, `p3_*_2026-09-25.json`, `f46a669` |
| 26.09 | P3 round 2 (the captain: "make items 5–7, complete all P3 work that is possible"): the organizers' hanging cube #2 a STOP from 52.5 m (was 34.0 m, `cluster.floating_free_max_size`), their 5 cm hanging object a STOP from 30.1 m (was never, `cluster.hanging_enabled` with a rail-lock guard): set O 6 of 8 objects with a STOP, inside STOP frames 311 → 337; `health.clear_cap` on although it missed its pre-registered clutter limit by 0.5 pp (the delegate's decision: a conservative verified-clear distance, set O overclaim 147 → 60 frames, no decision changes); rate-independent calibration (5 Hz stress: five bags 13 → 10 events). A safety review blocked `calibration.refine_min_deg` (a re-seed could drop a confirmed STOP under tilt): refinement off, a ≤ 1° change rotates the model and tracks, a STOP is held for a fixed window through any change; the re-review passed with the hold fixed. Gate PASS (6 better, 0 worse), baseline `_ride_p3b`, 486 tests | EXPERIMENTS §1i, `p3_round2_*`, `p3_round2_review_fixes_2026-09-26.json`, `8de3a92` |
| 26.09 | P3 wf14 integrated — rail-start (4 m, with the 0.06 m reference condition), near escalation (A) and wall keep (D) on; axis union off (safety review: blocking); baseline `_ride_p3c`; re-review of the fixes: rail start CLEAN, near escalation NON-BLOCKING, axis union CLEAN as shipped (off) | EXPERIMENTS §1k–§1n, `p3_integration_2026-09-26.json`, `regression_gate_2026-09-26_p3_integrated.json` |
| 26.09 | P3 range — stop keep B10 on (`tracking.stop_keep_*`, cap 10 s after the safety review); set O box at the envelope top 22 → 51 STOP frames, continuous from 101.3 m; no first STOP moves; baseline `_ride_p3d` | EXPERIMENTS §1o, `p3_range_2026-09-26.json`, `regression_gate_2026-09-26_range_final.json` |
| 26.09 | re-judgement of the integrated head (the user: "complete all P1 and P2 work; re-judge against the criteria, don't trust the docs"): two independent judges (their scores are superseded by the judgement of 28.09 evening); every agent-doable P1 / P2 item closed (deck, PDF, video and `.srt` on `_ride_p3d` and tested against the newest baseline; the claims found wrong fixed); the captain's remaining items then in the archived board's §4 |  [`evidence/rejudge_2026-09-26/`](evidence/rejudge_2026-09-26) |
| 26.09 | jury step 3 reads the bag before playing it (`cat <bag>/*.db3 > /dev/null`): from a cold disk the 360° dry run FAILS (34 of 201 frames), warm it PASSES; the node fix is action 21, the captain's decision | C7, README «Кратко для жюри», "Acceptance test and CI" |
| 26.09 evening | P3 / P4 completion on a second machine (the captain: complete all P3 and P4 work): the strict gate with the ride and set F passes with every row the same; P4's candidate B passes the full gate (set O #4 2 → 3 frames) and is eligible but **not shipped** (the freeze is the captain's; one frame at 7 m); the envelope union with the review fixes passes the full gate (#4 2 → 9 frames) and stays **off** (Q1 unanswered, one re-review item open); +3° pitch measured, no candidate; the 221-start census on the head: no STOP within 10 m; nothing shipped, `_ride_p3d` stands | EXPERIMENTS §1p, `p3_p4_prereg_2026-09-26_evening.json`, `regression_gate_2026-09-26_{head_fresh_machine,p4_candidate_B_full,axis_union_fixed_full}.json` |
| 26.09 evening | the P3 / P4 pass checked by both re-judgement judges (the user: "p3 & p4 work arrived, re-judge and check your scores"): judge A re-ran the rate / mount / start-offset checks and the gates of candidate B and the union on its own machine, judge B diffed the JSONs; every number reproduces; seven text issues fixed (EXPERIMENTS §1p counts, the 1–3 m pitch STOP and the roll's unfinished calibration, the third judge's self-credit); no score moved (those scores are superseded by the judgement of 28.09 evening) | [`evidence/rejudge_2026-09-26/p34/`](evidence/rejudge_2026-09-26/p34) |
| 28.09 evening | independent judgement of `464f5bc` (the user: "re-judge independently all criteria, don't trust current scores and docs, write your new judgement and purge old"): re-measured on the organizers' data; it replaces every earlier judgement, whose scores and judge reports are removed; the dated board is archived; the captain's work and the branches are in §2–§4 | [`SCORECARD.md`](SCORECARD.md), [`evidence/judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md) |
| 29.09 | the start-up lag fixed in the node only (the user: "fix lags in results on start … apply optimizations on root causes"): a byte-identical fast decode, a 5 Hz start-up catch-up, a warm-up and a clean Ctrl+C; the detector stays sealed; pitch and video moved to P2; the documentation swept and compacted; P2's branch `claude/amazing-fermi-t67v8g` merged into the working branch | [`evidence/node_startup_2026-09-29/`](evidence/node_startup_2026-09-29/README.md), [`DECISIONS.md`](DECISIONS.md) row 28 |
| 29.09 | the organizers answer Q1 / Q2: the envelope is measured from the rail heads, the rails may run at any angle to the LiDAR, the synthetic objects are placed approximately and the check corrects for that; `gauge.reference` 3 kept (bounded union, no measured false-alarm cost), `gauge.axis_union` stays off, Q2's object stays an obstacle; no detector change, the seal stands | [`organizers/answers.md`](organizers/answers.md) §9, [`QUESTIONS.md`](QUESTIONS.md), [`DECISIONS.md`](DECISIONS.md) rows 1, 18 |
| 29.09 evening | three false-alarm rules from other case-05 teams' public solutions on by default (`tracking.explained_run` 5, `cluster.shell_min_top` 2.3 m, `tracking.ego_veto_min_speed` 4 m/s), each gated on all organizer data: PASS, 7 metrics better, none worse (ride 32 / 31 → 26 / 28 events / STOP episodes); five other candidates rejected; resealed at `1e2ed82`; the safety review of step 3 was not done before the seal | PR #29, [`evidence/cycle_2026-09-29/competitor_rules/gate_table.md`](evidence/cycle_2026-09-29/competitor_rules/gate_table.md), CHANGELOG |
| 29.09 evening | the current gate becomes the regression baseline (`evidence/results/regression_baseline_2026-09-29_competitor_rules.json`, a copy of the sealing gate; the user's decision): the deck and video tests check today's numbers and a future gate compares against the shipped detector | the user, 29.09 |
| 29.09 evening | P2 declined the pitch after delivering the deck with the team's photos; the captain owns the pitch with agent help, the team records the video; the named deck (names and photos) is committed to the public repository (the user's decision; lifts the placeholder rule of 25.09) | the user, 29.09 |
| 29.09 night | **the `shell` rule off** (`cluster.shell_min_top` 0, `a5455b3`; the user's decision on the safety review): the rule read a floor-standing cluster's own top above the 3.0 m envelope as the lining, so a cable hanging from the vault to the rails, a pole, a standing train were CAUTION beyond 40 m (ray-cast tunnel, 22 m/s: catalogue `cable_low` first STOP 21.0 m on vs 73.8 m off; pole 36.4 vs 104.6 m); alone it bought ride 32 / 31 → 31 / 29. `explained_run` and the ego veto stay (NON-BLOCKING; the ego veto must only get a measured speed). Full gate of the shell-off commit against the `3eeb106` gate, then a new seal | the user, 29.09; safety review in the doc PR |
| 29.09 night | release: `v1.0.0-rc1` on `7532a6b` cancelled (it has the `shell` rule); `v1.0.0-rc2` on the new seal's commit, verified on the team VM from the published archive; `v1.0.0` on the final `main` after the documentation PR | the user, 29.09; §3 items 2–3 |

## Experimental branch integration, 28.09

The experimental branch also contains the accepted P3 changes and health histogram optimization.
Their measured commits, acceptance checks and remaining work are in
[`P3_SCORE_SYNC_2026-09-28.md`](P3_SCORE_SYNC_2026-09-28.md) and the
[health evidence](evidence/cycle_2026-09-28/health_histogram/README.md). The 61/100 judgement above
remains the assessment of `464f5bc`; it does not score the combined branch.
