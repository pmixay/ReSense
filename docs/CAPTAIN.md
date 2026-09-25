# Captain Board

> **Purpose:** P1's board: criteria, plan to 29.09, runbook, rules, contracts, owners, decisions;
> history of 16–24.09 in [`archive/CAPTAIN_log_2026-09.md`](archive/CAPTAIN_log_2026-09.md).
> **Audience:** P1, team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-25 against `79109f5` · **Status:** current

## 1. Role and dates

P1 is the system analyst and ROS 2 / integration developer ([`PLAN.md`](PLAN.md)): the jury chain
`docker load` (or `docker build`) `→ docker run → ros2 bag play → /resense/decision`, the
evaluation protocol, liaison with the organizers ([`QUESTIONS.md`](QUESTIONS.md),
[`organizers/answers.md`](organizers/answers.md)),
merges, the submission ([`SUBMISSION.md`](SUBMISSION.md)) and the pitch; in the criteria: 8.3
(node side), 8.5 (CI, Docker, docs), 8.6, the §7 deliverables and 8.8. Dates (organizers' README):
upload by 29.09 23:59 (target 18:00), technical expertise 30.09–14.10, pitch 23.10.

| criteria judgement, 24.09 ([`SCORECARD.md`](SCORECARD.md)) | 8.1 | 8.2 | 8.3 | 8.4 | 8.5 | 8.6 | 8.7 | 8.8 | total |
|---|---|---|---|---|---|---|---|---|---|
| score / max (maxima follow the spec's emphasis; the organizers publish no weights) | 13 / 25 | 7 / 15 | 6 / 10 | 8.5 / 15 | 7 / 10 | 7.5 / 10 | 8 / 10 | 3 / 5 | **60 / 100** |

## 2. Criteria board (25.09)

Statuses as of 25.09 ~10:30 UTC on `79109f5` (the day's merges: version 1.0.0 and the release
workflow, the overview video, the `offline-build` gate with the runtime image, the organizers'
answers of 25.09, the rules decision on the ride), checked against the repository and CI: run
36122640174 (`5a15c7c`) and run 36123184213 (`79109f5`), all six jobs green in both. GitHub at
10:30 UTC: 0 tags, 0 releases, 0 open PRs, the repository public. HUMAN = only a person can close
it.

| # | criterion (spec) | status | evidence / gap |
|---|---|---|---|
| C1 | image builds from scratch, no manual steps (§3.3.1, §7.2, 8.6) | DONE | `docker/Dockerfile`: pip pinned, non-editable install checked from `/`. CI run 36123184213 (`79109f5`): the `docker` job builds the image; the `offline-build` job builds the runtime image `--no-cache` from `git archive HEAD` (1.34 GiB). Gap: apt and the base image unpinned (accepted); the stand has no internet, so the image goes as an archive (C25) |
| C2 | `docker run` starts the node with no arguments, either topic / frame pair (answers §1 #2) | DONE | default command `ros2 launch resense_ros detector.launch.py`, topic auto-discovery; CI (run 36123184213) starts it with no arguments and switches between both pairs ("input switched … detector restarted"), also from the runtime archive (`offline-build`); `tests/test_node.py` |
| C3 | every parameter a launch argument; mount configurable (Q&A fact 7) | DONE | `launch/detector.launch.py`: 31 launch arguments, the node declares exactly those plus `config_file` (checked by script 25.09), plus `bag:=`, `rviz:=`, `loop:=`, `rate:=`, `delay:=` |
| C4 | organizers' console path: `ros2 bag play` by a normal user on the host | DONE | CI plays as uid 1000 from our image twice: with the image's UDP profile and with stock Fast DDS (`PLAYER_DDS=stock` in `scripts/console_test.sh`: no XML profile, shared memory + UDPv4, a stock uid-1000 listener). Run 36123184213 (`79109f5`), docker job step 8 green: the listener heard 111 `/resense/decision` messages, 42 `STOP` (first proven in run 36112092652: `rmw_fastrtps_cpp`, fastrtps 2.6.12, each play created its own shared-memory files). The node announces no shared-memory locators, so stock clients reach it over UDP. CycloneDDS not tested; a real host console is part of the dry run (action 15) |
| C5 | start of a played bag not lost (8.3, 8.6) | DONE | v0.6.4 catch-up (`input_queue_depth` 40, `catchup_step` 0.3); CI on the synthetic bags: 39–40 frames in the first 5 s, first STOP at +1.9 s (run 36123184213, every playback step). Caveat: the real-bag figure (first STOP 4.02 → 1.59 s, EXPERIMENTS §3b) has no committed raw capture |
| C6 | acceptance script asserting the result | DONE | `scripts/dry_run.sh` + `scripts/check_dry_run.py` (`--distance 50:62 --max-p95-latency 100 --max-dropped 0`); `IMAGE_TAR` / `OFFLINE` (offline stand) and `DOCKER_ARGS`; `scripts/bench_8core.sh` runs it on both bags, native and numpy. Gap: it needs the dataset, so CI runs `check_dry_run.py` only on the synthetic bags; its offline path with the real bags is first used in the dry run (action 15) |
| C7 | clean-machine dry run with the original bags (§7.2) | NOT DONE · HUMAN | action 15: the local agent on the team's VM (`scripts/vm/run_plan.sh dryrun`, then `offline` from the rc1 release archive fetched by `scripts/verify_release.sh v1.0.0-rc1`), or a clean team machine; the organizers' stand is not available before the upload (organizers, 25.09). Rehearsed 23.09 on bags rebuilt from the cache; the 4-vCPU dev VM runs 360° at 7–10 fps, p95 112–130 ms. No `docs/evidence/dry_run_<date>/` yet |
| C8 | timing on an 8-core analogue of the i7-9700E (8.3; the stand is not available before the upload, [`organizers/answers.md`](organizers/answers.md) §6) | NOT DONE (kit ready) · HUMAN | action 7: the local agent on the VM runs `scripts/vm/run_plan.sh bench` (= `scripts/bench_8core.sh`: build, dry runs on both bags with the node native and numpy, console tests with the image's and a stock player, `docker stats`, offline timing with peak RSS → `docs/evidence/bench_<date>/summary.txt`); the kit is tested only against a mock `docker`. Only the 4-vCPU dev VM is measured (EXPERIMENTS §3): C++ kernels −38…−57 %, DBSCAN on cKDTree −1.3…−2.6 ms more; GPU evaluated, not used. DONE when `dry_obstacle_native` passes (p95 ≤ 100 ms, no frame dropped after 5 s) |
| C9 | README per §5 (description, build, run, bag processing, parameters) | DONE | [`../README.md`](../README.md): jury commands first (step 1 `docker load`; the release assets and `scripts/verify_release.sh`), how a bag is processed, build / run, node and config parameters (the 25.09 rules), the overview video; verified 25.09 against `79109f5` |
| C10 | architecture and algorithm descriptions (§5) | DONE | [`ARCHITECTURE.md`](ARCHITECTURE.md) ("Native kernels", "GPU: evaluated, not used", "Deployment without internet" with the `offline-build` playback and "Release"), [`ALGORITHM.md`](ALGORITHM.md) (§3.3: the long overhead rule on, short signatures tried and not shipped) |
| C11 | evaluation protocol (stream C) | DONE | [`EVALUATION.md`](EVALUATION.md), sets S / E / R / O / F / H; §3 step 6 is the regression gate (`scripts/regression_gate.py`), its baseline with the ride and set F straight since 25.09 |
| C12 | SUBMISSION matches reality | DONE | at `79109f5`: row 10 (the gate with the ride, the rules decision), 11 (the overview video), 13 (the deck, its stale counts named), 14 (347 tests, 344 in the image, the CI jobs), 17 (the release workflow; archive 521 317 060 bytes in CI) and "Upload" (four links with the `v1.0.0` tag, the release asset's link, the checks with `verify_release.sh`) match the repo; the release links go live with the tags (C13) |
| C13 | release tag and upload package (§7.2) | PARTIAL | version 1.0.0 in `pyproject.toml`, `resense/__init__.py`, `package.xml` and `setup.py` (`tests/test_release.py` keeps them equal); `.github/workflows/release.yml`: a pushed `v1.0.0-rcN` / `v1.0.0` tag (any other name publishes nothing) gets its tests run, the runtime archive built (gzip -6), the image removed and loaded back, both smoke bags played through the loaded image (internal network and the jury's `--net=host` form), and a GitHub release (a pre-release for `-rc`) with `resense-image-<tag>.tar.gz`, its `.sha256` and `SHA256SUMS`; the published archive is downloaded again and its sum checked; re-runs replace the assets; fallback `scripts/release.sh`, check `scripts/verify_release.sh <tag>`. Not yet run (no Docker in the agents' sandbox; every Docker step copies a green `ci.yml` step). Left for DONE: `v1.0.0-rc1` pushed (the agent, action 14) and its release run green; then `v1.0.0` on 29.09 (action 16). rc1: |
| C14 | intermediate submission (§7.1) | DONE (resolved: not held) | decided 25.09: no separate intermediate upload in the organizers' timeline; the §7.1 content (Dockerfile, prototype, description, mini-demo, first experiments) is in the repository (SUBMISSION "Intermediate submission"). Evidence: the organizers' timeline ([`organizers/README_organizers.md`](organizers/README_organizers.md) "Ключевые этапы конкурса") lists only «Приём заявок \| до 14 сентября», «Разработка решений \| 15–29 сентября», «Техническая экспертиза \| 30 сентября – 14 октября», «Презентация проектов \| 23 октября», «Церемония награждения \| 30 октября»; spec §7.1 («7.1. Промежуточная сдача», `technical_specification_case05.txt` lines 184–193) gives the content but no date, form or place; the Q&A of 22.09 does not mention it |
| C15 | liaison: questions sent, answers applied (8.7) | PARTIAL | answers of 22–24.09 recorded, and the statements of 25.09 from the captain's oral reports: no stand access before the upload (`organizers/answers.md` §6), no internet on the test machine (§7), the upload form takes links with no size limit and **Q3 answered: the 30 × 30 × 10 cm object on the bed between the rails is not an obstacle** (§8; QUESTIONS "Answered"). Open: Q1–Q2 (24.09, edge reference and #8), drafted in QUESTIONS, **not known whether they were sent** (captain to confirm, action 2) |
| C16 | main green, every PR reviewed, captain merges | PARTIAL | `main` is green (`5de0844`, PR #11, run 36104815305). **Still failing the §6 rules:** PR #11 had 0 reviews and was merged by its author 3.5 min after opening; branch protection is off; 0 reviews on PRs #1–#11; the branch is 51 commits (without merges) ahead of `main` and no branch → `main` PR is open (action 3b); the 25.09 agent branches changed files in P2's (deck, video), P3's (`clustering.py`, `configs/`: the rules decision) and P4's (gate, `docs/evidence/results/`) lanes with no recorded owner OK — the owners confirm in the review of that PR |
| C17 | one parameter source, lint, tests in CI (8.5) | DONE | 347 tests in `tests/` (green on the native and numpy paths) + 11 in `web/demo`; CI run 36123184213 (`79109f5`), all green: `pytest` (347, 0 skipped: "no test may have been skipped"), `web`, `lint` (ruff 0.15.8), `params-in-sync`, `docker` (344 passed in the image, which has no `docs/`), `offline-build` (a gate since 25.09: the runtime archive loaded, rebuilt offline from its cache, both synthetic bags played through the loaded runtime image on an internal network) |
| C18 | demo chain on screen (§4) | DONE | `video/docker_chain_rviz.mp4` (69 s), `scripts/run_demo.sh` |
| C19 | live remote demo (§4) | PARTIAL · HUMAN | runbook in README (RViz screen share, Foxglove on port 8765); Foxglove not yet tried against a live `foxglove_bridge`; never rehearsed from a second machine (action 15) |
| C20 | video of the algorithm (§5, §7.2) | DONE | `video/resense_overview.mp4` (25.09, `798a28f`; closing card «релиз v1.0.0», `5a15c7c`): 2:50, 1920×1080 H.264, 20.6 MB, no audio track; the script's seven blocks and shot list, Russian subtitles burned in (≤ 2 lines) and as `video/resense_overview.ru.srt` with the same timings, every number marked as in the deck; built by `scripts/make_overview_video.py`; 5 source clips, all silent. Optional: a voice-over (H), muxed on without re-encoding. Its ride card (3,6 на км, 47 за 13 км) predates the 25.09 rule decision (now 46, 3.5 per km): rebuild at action 13 |
| C21 | pitch: team slides 2–4, captain slides, rehearsal (8.8) | PARTIAL | public deck rebuilt 25.09 (`16d2a07`, then after the morning's merges): 16 slides, the organizers' objects (slide 13), the anchored 154 m next to 150 m legacy in the same 5 pairs, «~210 м — предел отражений в тоннеле», the real-data UI capture, C++ kernels / train speed / GPU lines; the 17 `<…>` stay only on slides 2–3 of the public build by design. It still says 289 tests and the pre-rule false alarms (now 347; five bags 14, ride 46): rebuild at action 13. Left: `private/team.json` + photos of P1 and P4, the private `--team` build (action 8), two rehearsals |
| C22 | decision: train speed | DONE (measured 24.09) | organizers' fact: no odometry in the recordings, some trains have none (Q&A fact 6). Team decision: ship the no-speed path; a given speed is honoured; the LiDAR-only estimator is accurate (median error 0.06–0.08 m/s) but buys nothing on the organizers' check, so it stays opt-in (EXPERIMENTS §9) |
| C23 | decision: GPU / stand software | DONE (evaluated 24.09) | CPU-only, the image installs no CUDA ([`organizers/test_stand_software.md`](organizers/test_stand_software.md)); GPU evaluated and not used ([`ARCHITECTURE.md`](ARCHITECTURE.md) "GPU: evaluated, not used"); of the CPU savings that study found, the cKDTree DBSCAN shipped 25.09, the forward crop did not (no gain on the native path) |
| C24 | captain docs current (CAPTAIN, PLAN) | DONE | refreshed 25.09 against `79109f5` (this revision and PLAN): the day's merges, the CI runs of `5a15c7c` and `79109f5`, the tag names `v1.0.0-rcN` / `v1.0.0`, Q3 answered, the rules decision |
| C25 | runs on the offline stand: the test machine has no internet ([`organizers/answers.md`](organizers/answers.md) §7, 25.09) | DONE | tooling: `export_image.sh`, `load_image.sh`, `check_no_network.py`, `dry_run.sh` `IMAGE_TAR` / `OFFLINE`, roslib bundled; no network use in the node, launch file, entrypoint or compose (audit). CI on every push: the `docker` job's `docker save` → `docker rmi` → `docker load` keeps the layers, the smoke test passes with `--network none`, node and a uid-1000 player pass on an `--internal` network (tools image); the `offline-build` job (a gate since `abbbc08`, 25.09; the offline rebuild passed on all four runs made with continue-on-error: 36109782167, 36112092652, 36113989932, 36116178404) makes the runtime archive as for the release (521 317 060 bytes, 0.49 GiB at gzip -1, 1.34 GiB unpacked, base image included, run 36123184213), removes every image and loads it, (1) rebuilds it with `docker build --cache-from` with Docker Hub blocked, all 18 steps from the cache, and (2) plays both synthetic bags through **the runtime image as loaded from the archive** (checked: the built layers, its version and commit labels, no open3d / rosbags, rosbag2 with sqlite3) on an `--internal` network: node on the default command, a uid-1000 player of the same image, `check_dry_run.py --expect-obstacle --expect-inputs 2`. Green on `5a15c7c` (run 36122640174, the first) and on `79109f5` (run 36123184213: 78 status messages, 42 alarm frames at 44.9–59.9 m, both recordings, PASS). Upload: the form takes links, no size limit (action 1b). Left, tracked elsewhere: the rc1 / final releases (C13); the offline dry run with the real bags (action 15, a confirmation). Cosmetic: `load_image.sh` prints the Ubuntu base's version label ('22.04') for an image exported with `SKIP_BUILD=1`. Kit: [`scripts/vm/`](../scripts/vm/AGENT_BRIEF.md) (`run_plan.sh offline`) |

18 DONE · 5 PARTIAL · 2 NOT DONE · 0 UNKNOWN. What is open: the release tags (C13), the two runs
on the VM (C7, C8), the pitch (C19, C21), liaison (C15) and merge discipline (C16).

**Progress 25.09:** criteria DONE 18 of 25 (board of 24.09: 13 of 24; the independent check at
08:05 UTC: 12 of 25; this board at 08:35 UTC: 16). New since 08:35: C12 and C14 (the organizers'
answers of 25.09), C20 (the captioned overview video), C25 (the runtime image played from the
archive in CI); C13 NOT DONE → PARTIAL (version 1.0.0 and the release workflow). Actions done 9 of
21 (1b, 4, 5, 6, 9, 10, 10b, 11, 12; at 08:35 UTC: 7; at 08:05 UTC: 1 of 20), 2 in progress (3,
14), 5 due or overdue, all human (1, 2, 3b, 8; 7 by 26.09 midday), 5 dated 27.09 or later (13, 14b,
15, 16, 17).

## 3. Next actions to 29.09

| # | date | action | owner (H = human captain only; A = agent, captain merges) | priority |
|---|---|---|---|---|
| 1 | 24.09 | **overdue.** ~~read the upload form, settle the intermediate stage~~ done 25.09 (1b, C14). **Open:** announce the §6 rules to the team; turn on branch protection on `main` (API: off) | H | must |
| 1b | 25.09 | ~~upload form limit~~ done 25.09 (organizers, [`organizers/answers.md`](organizers/answers.md) §8): the form takes **links**, **no size limit** → the link to the release asset `resense-image-v1.0.0.tar.gz` with its sha256 in the cover message; the links to type and the check before submitting in SUBMISSION "Upload" | H | done |
| 2 | 24.09 | Q3 (bed object) **answered 25.09**: not an obstacle ([`organizers/answers.md`](organizers/answers.md) §8, QUESTIONS "Answered"). **Open:** confirm whether Q1–Q2 were sent (the repository records no sending); if not, send them as one message to @gorbatovaol **from the current file** (Q1–Q2 only); file the answers in `organizers/answers.md` | H (A drafted) | must |
| 3 | 25.09 12:00 | frame caches and harness to P3 / P4. Partly done 25.09: an agent streamed the ride on the dev VM (`scripts/vm/stream_cache.py`, 221 of 221 split files) and ran the gate with it (action 11); P3's and P4's own copies are not recorded | P1 → P3, P4 | should |
| 3b | 25.09 | ~~prove the Docker build with the C++ kernels~~ done (CI since run 36058665640). **Opened 25.09:** [pmixay/ReSense#12](https://github.com/pmixay/ReSense/pull/12), reviews requested from P2, P3, P4 (was: the branch → `main` PR (51 commits without merges; CI green on `79109f5`), reviewed by the owners of the lanes the agents touched (P2: video, deck; P3: `configs/`, `clustering.py`; P4: gate, evidence), then the captain merges; `v1.0.0` is tagged on `main` after it) | A opens, owners review, H merges | must |
| 4 | 25.09 12:00 | ~~stop the verification loop~~ done 25.09: numbers live in EXPERIMENTS "Current results" + raw JSON; re-measuring is one command, `scripts/regression_gate.py` (baseline `docs/evidence/results/regression_baseline_2026-09-25_ride.json` since the rules decision), run only when `resense/`, `configs/` or the node change | P1 (A) | must |
| 5 | 25.09 | ~~CI step with a stock-Fast-DDS player~~ done 25.09 (`fbef12b`), green on every run since 36112092652 | A | should |
| 6 | 25.09 18:00 | ~~regression gate: one command, one JSON~~ done 25.09 (A for P4): `scripts/regression_gate.py`, `tests/test_regression_gate.py`; the baseline with the ride and set F straight done on the dev VM (25.09, `regression_baseline_2026-09-25_ride.json`, 394 s at `--jobs 3`); the 8-core run is timing only (action 7). The rule stays: the gate on every P3 PR within 2 h | P4 | must |
| 7 | 26.09 midday | 8-core bench (stands in for the i7 stand): kit done (`8242c3e`, A); **run open:** the local agent on the VM, `scripts/vm/run_plan.sh bench` (= `scripts/bench_8core.sh <bags>/doubleT_obstacle <bags>/roundT_doubleT`, ~10–25 min); commit `docs/evidence/bench_<date>/` as written; `summary.txt` numbers into EXPERIMENTS §3, early enough to act before the freeze | H (VM agent) | must |
| 8 | 25.09 18:00 | every member sends a photo; fill `docs/presentation/private/team.json`; build the private deck with 0 `<…>` left; its link (e.g. Yandex Disk, opens without a sign-in) goes into the upload | H + all | must |
| 9 | 26.09 | ~~narrated 2–3 min video~~ done 25.09: the captioned 2:50 `docs/video/resense_overview.mp4` + `resense_overview.ru.srt` (`scripts/make_overview_video.py`, `798a28f`, `5a15c7c`); optional: the captain's voice-over read against the .srt and muxed on (PRESENTATION «Сборка ролика»); a new-UI dashboard clip stays optional | H voice (optional) | could |
| 10 | 26.09 | ~~deck refresh and rebuild~~ done 25.09 (`16d2a07`): pptx and pdf, 16 slides (its counts: action 13) | P2 (A) | should |
| 10b | 25.09 | ~~the `web` CI job red at `8932f3a`~~ done 25.09: the expected slide count follows the deck (16); P2 informed by this row | A | must |
| 11 | 26.09 20:00 | ~~go / no-go on late changes~~ done 25.09 (A, delegated): the ride streamed on the dev VM (11 271 frames); criteria pre-registered; long overhead rule GO and shipped (`935eecf`: ride 47 → 46 events, five bags 20 → 14, set O / set F unchanged); short signatures NO-GO (ride STOP episodes +6 > +5); new baseline `regression_baseline_2026-09-25_ride.json`; EXPERIMENTS §1f | H decides, P3 / P4 measure | done |
| 12 | 26.09 | ~~decide on the saved-image release asset~~ decided 25.09: the image archive is a must, not insurance (no internet on the stand, C25, §5) | H | done |
| 13 | 27.09 | final consistency pass: every headline number equals EXPERIMENTS "Current results". Known now: the deck (289 tests; five bags 20, ride 47 / 3.6 per km) and the video's ride card (3,6 на км, 47 за 13 км) predate the 25.09 rule decision and the 347 tests: rebuild both (`scripts/build_deck.py`, the table of `scripts/make_overview_video.py`) with P2's OK, or keep them and date the figures | A (P2 OK) | must |
| 14 | 25–27.09 | version 1.0.0 done 25.09 (`65a5305`); **tag `v1.0.0-rc1`** on the green branch head (`git tag -a v1.0.0-rc1 -m "ReSense 1.0.0 release candidate 1" && git push origin v1.0.0-rc1`) → `release.yml` publishes the pre-release; at the latest 27.09 18:00, whatever the state. The tag must be pushed by a person: the agents' git access in the dev sandbox is limited to the working branch (tag push refused, 25.09); `79109f5` (CI run 36123184213 green) is a valid rc1 commit | H tags and checks | must |
| 14b | 27.09 | check the rc1 release: the run green, size and sha256 noted in C13 (release notes / job summary), `scripts/verify_release.sh v1.0.0-rc1`, then `scripts/load_image.sh` on a second machine (the VM: `run_plan.sh offline`); fallback without Actions: `scripts/release.sh v1.0.0-rc1` in a clean clone of the tag | H (+ VM agent) | must |
| 15 | 28.09 | **offline** dry run with the original bags (the stand is not available), network disconnected: the rc1 archive, `IMAGE_TAR=… OFFLINE=1 ./scripts/dry_run.sh` on both bags, then the README jury commands by hand from a normal user's host console (stock ROS 2 if installed) (SUBMISSION "Dry run"), logs to `docs/evidence/dry_run_<date>/`; remote demo from a second laptop; kit: [`scripts/vm/`](../scripts/vm/AGENT_BRIEF.md) (`run_plan.sh dryrun`, `run_plan.sh offline`) | H (VM agent) | must |
| 16 | 29.09 | final tag `v1.0.0` on `main` → `release.yml` publishes the full release; upload the links + sha256 (§5, SUBMISSION "Upload") | H | must |
| 17 | 30.09–23.10 | answer the organizers daily during the expertise; pitch on 23.10 after two rehearsals (fallback demo `video/docker_chain_rviz.mp4`) | H (+P2) | must |

## 4. Human-only checklist

In order; only the captain can do these.

- [ ] **25.09, overdue:** confirm whether Q1–Q2 were sent; if not, send them from
  [`QUESTIONS.md`](QUESTIONS.md) (action 2)
- [ ] **25.09:** announce the §6 rules (overdue since 24.09); by 18:00 photos from every member,
  `private/team.json`, the private deck (actions 1, 8)
- [ ] 25.09–26.09: the branch → `main` PR (an agent opens it): the lane owners review (P2 video and
  deck, P3 `configs/` and `clustering.py`, P4 gate and evidence), CI green, you merge; then branch
  protection on `main` (actions 1, 3b)
- [ ] 26.09 by midday: the local agent on the VM runs `scripts/vm/run_plan.sh bench` (C8, action
  7) and commits `docs/evidence/bench_<date>/`; optional: record the voice-over (action 9)
- [ ] 25–27.09: **you** push `v1.0.0-rc1` (action 14; the agents' git access here cannot push tags, 25.09); you check the release run, note size
  and sha256; `scripts/verify_release.sh v1.0.0-rc1` and `load_image.sh` on a second machine (14b)
- [ ] 27–28.09: the VM agent runs `run_plan.sh dryrun` (C7) and `run_plan.sh offline` (the offline
  rehearsal from the rc1 archive); host console and a remote demo from a second laptop (action 15)
- [ ] 29.09: last merge to `main` 12:00; `v1.0.0` on `main` 13:00 → release run green; upload by
  18:00 (repository, release asset + sha256, video, presentation link); every link opened logged
  out (action 16, §5)
- [ ] 30.09–14.10: reachable for the organizers · 23.10: pitch led after two rehearsals (action 17)

## 5. Release and upload runbook

```bash
# rc1 (action 14): CI green; version 1.0.0 in the four declarations (python3 scripts/release_meta.py version)
git tag -a v1.0.0-rc1 -m "ReSense 1.0.0 release candidate 1" && git push origin v1.0.0-rc1
#  -> .github/workflows/release.yml (~30 min): tests, smoke bags, build + export (gzip -6), rmi, load back,
#     both bags through the loaded image, pre-release with resense-image-v1.0.0-rc1.tar.gz, .sha256, SHA256SUMS
#     https://github.com/pmixay/ReSense/releases/tag/v1.0.0-rc1
scripts/verify_release.sh v1.0.0-rc1                           # any machine: download + sha256, no Docker
scripts/load_image.sh dist/resense-image-v1.0.0-rc1.tar.gz      # second machine: sum, load, no-network run
# 29.09 13:00, on main after the branch -> main merge: the full release
git tag -a v1.0.0 -m "LCT-2026 case 05 final" && git push origin v1.0.0
#     https://github.com/pmixay/ReSense/releases/tag/v1.0.0
#     https://github.com/pmixay/ReSense/releases/download/v1.0.0/resense-image-v1.0.0.tar.gz
# re-run (assets replaced): Actions -> release -> Re-run jobs; once release.yml is on main: gh workflow run release.yml -f tag=v1.0.0
# no Actions: scripts/release.sh v1.0.0 in a clean clone of the tag (Docker + internet), then PUBLISH=1
```

Tag names: only `v1.0.0-rcN` (a pre-release) and `v1.0.0` (the full release) publish; any other
`v*` tag fails the version check and publishes nothing. **The image archive is a must, not
insurance** (25.09): the stand has no internet ([`organizers/answers.md`](organizers/answers.md)
§7), so `docker build` cannot run there and the jury's step 1 is `docker load -i
resense-image-v1.0.0.tar.gz`. gzip, not zstd: `docker load` reads gzip on any Docker. The archive
also holds the base image's tag and the build's layer cache, so an offline `docker build
--cache-from` may work (best effort on the stand, ARCHITECTURE "Deployment without internet").
CI's `offline-build` job checks both on every push: the offline rebuild, and both synthetic bags
played through the runtime image as loaded from the archive with no internet. 29.09: last merge
12:00; the release run on `v1.0.0` 13:00–14:00 (green; sha256 from the notes); CI green on the
tag 14:00; upload on i.moscow 15:00 (the form takes links with no size limit: the repository link
with the tag and commit hash, the release asset's link with the sha256, SUBMISSION cover message,
the video and the deck as the form asks); 16:00 open every link logged out, then
`scripts/verify_release.sh v1.0.0` and `load_image.sh` on a second machine. Then no pushes to
`main` (Q&A fact 22). After rc1: blocker PRs, then `v1.0.0-rc2`.

## 6. Freeze and merge rules

- From 25.09 `main` changes only by a PR with CI green and a GitHub review from another lane; the
  captain merges; branch protection on. A red `main` is fixed by its author within 1 h or reverted.
  25.09: PR #11 (the `main` fix) went in without a review, 3.5 min after opening, protection still
  off; the branch → `main` PR (action 3b) is the first to follow the rule.
- No edits in another lane's files without the owner's OK (§8). Contract changes (§7): `[contract]`
  in the PR title and a heads-up to the consumers; add, never rename or remove.
- Freeze: detector and config **26.09 20:00**, docs **27.09 20:00**; from 28.09 blockers only.
- Detector / config gate: `python scripts/regression_gate.py --baseline
  docs/evidence/results/regression_baseline_2026-09-25_ride.json` exits 0 on the change. Every
  gated metric must be identical or better on the six recordings, set O, the ride and set F
  straight (the last two wherever `/data/cache/new_data` exists; the dev VM streams it with
  `scripts/vm/stream_cache.py`). Otherwise the PR names each worse metric with `--allow` and the
  captain accepts the trade-off, or it is "tried, not shipped" (EXPERIMENTS §7). The JSON and the
  table go into the PR. A change meant to move the numbers commits a new baseline. Nothing in the
  gate needs the organizers' stand.
- Numbers only in EXPERIMENTS "Current results" and the README summary; one sprint numbering (PLAN).

## 7. Contracts

| contract | where | consumers |
|---|---|---|
| jury path `docker load` (no internet on the stand; `docker build` where there is) `→ docker run → ros2 bag play → /resense/decision` | README, SUBMISSION "Dry run" | jury, P2 video |
| release: tags `v1.0.0-rcN` / `v1.0.0` only; assets `resense-image-<tag>.tar.gz`, its `.sha256` and `SHA256SUMS` | `.github/workflows/release.yml`, `scripts/release_meta.py`, `scripts/verify_release.sh` | jury (upload links), SUBMISSION "Upload" |
| 12 topics `/resense/{decision, obstacle_detected, warning, nearest_distance, clear_distance, detections, status, health, markers, corridor_points, latency_ms, fps}` + `/tf_static` | `detector_node.py`, README "Topics published by the node" | P2, jury |
| status JSON: `stamp, obstacle, warning, nearest_distance, clear_distance, detections[], warnings[], track, health, mount, timing_ms, ego_speed*, n_accumulated, n_*` + `node` (added by the node) | `FrameResult.to_dict()` in `resense/detector.py` | P2 dashboard, `resense run --out` |
| `Frame` (xyz in the vehicle frame, intensity, ring, stamp) | `resense/frame.py` | P3, P4 |
| one parameter file `configs/default.yaml`, root key `resense:`, ROS copy in sync | `resense/config.py`, `scripts/sync_params.sh` | P3 tunes, node loads |
| offline formats: `*.npz` + `gt.json` from `inject`, JSONL from `run` | `resense/cli.py` | P4 `eval`, P2 label tool |

## 8. Ownership map (a file not listed: its author's lane; ask P1)

| path | owner |
|---|---|
| `docker/`, `docker-compose.yml`, `ros2_ws/src/resense_ros/` (except `rviz/`), `scripts/*.sh` (except `build_native.sh`), `scripts/vm/`, `scripts/{check_dry_run,make_smoke_bag,cache_to_bag,bench_node_path,bench_summary,check_no_network,release_meta}.py`, `tests/test_release.py` | P1 |
| `README.md`, `CHANGELOG.md`, `docs/{README,ARCHITECTURE,ALGORITHM,EVALUATION,SUBMISSION,SENSOR,PLAN,CAPTAIN,QUESTIONS,SCORECARD}.md`, `docs/archive/`, team notes in `docs/organizers/` | P1 (P3 reviews ALGORITHM) |
| `.github/workflows/ci.yml`, `.github/workflows/release.yml` | `ci.yml`: P4 `pytest`, P2 `web`, P1 the other jobs; `release.yml`: P1 |
| `configs/default.yaml` | P3 values, P1 structure |
| `resense/{track,gauge,clustering,tracking,accumulate,egomotion,lowobj,calibration,health,config,detector,_native}.py`, `native/`, `setup.py`, `scripts/build_native.sh`, `tests/{test_algorithm,test_lowobj_near,test_native,test_cpu_savings,test_late_candidates}.py` | P3 |
| `resense/{frame,pointcloud,sensor}.py` | P1 decoding / P3 geometry |
| `resense/{synthetic,metrics,io,cli}.py`, other `tests/` (`test_node.py`: P1), `labels/`, `scripts/{cache_frames,eval_real,far_range_eval,compare_setf,label_fake_objects,score_fake_objects,short_signature_experiment,unpack_dataset,start_offsets,regression_gate}.py`, `scripts/speed_*.py` (with `tests/test_speed_eval_helpers.py`), `tests/test_regression_gate.py`, `docs/{P4_AUDIT,DATASET}.md`, `docs/evidence/results/` | P4 |
| `docs/EXPERIMENTS.md` | P3 / P4; P1 appends timing |
| `web/` (incl. `web/assets/fonts/`, `web/demo/`), `ros2_ws/src/resense_ros/rviz/`, `docs/{PRESENTATION.md,images/,img/,video/,presentation/}`, `scripts/{build_deck,hero_view,make_overview_video}.py`, `tests/test_overview_video.py` | P2 (`docs/img/` stays in place: scripts read it) |

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
| 24.09 | the criteria judgement in SCORECARD (60 / 100) replaces every earlier scorecard; the release tag is no longer deferred (rc1 on 27.09 18:00; its name is `v1.0.0-rc1` since 25.09, the only form the release workflow accepts) | §1, §5 |
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
| 25.09 | upload by links, no file-size limit (organizers): the form gets the repository at the release tag with its commit hash, the release asset `resense-image-v1.0.0.tar.gz` with its sha256 (published by `.github/workflows/release.yml` on the tag push; `scripts/release.sh` by hand), the video and the presentation; every link opened logged out and the archive loaded on a second machine before submitting | [`organizers/answers.md`](organizers/answers.md) §8, SUBMISSION "Upload", action 1b |
| 25.09 | intermediate submission not held as a separate upload: the organizers' timeline has no such stage; the §7.1 content is in the repository | C14, SUBMISSION "Intermediate submission" |
| 25.09 | bed object: a 30 × 30 × 10 cm object on the bed between the rails is **not an obstacle** (organizers' answer to Q3) → the envelope-floor policy of 24.09 is the organizers'; the near-bed path (`lowobj.near_enabled`) stays off for good, its ride / set F re-run is dropped | [`organizers/answers.md`](organizers/answers.md) §8, ALGORITHM §3.3b |
| 25.09 | version 1.0.0 and one release path: a pushed `v1.0.0-rcN` / `v1.0.0` tag (no other name) runs `.github/workflows/release.yml`, which builds the runtime archive, proves it (removed, loaded back, both smoke bags through the loaded image) and publishes it with its `.sha256` and `SHA256SUMS` as the GitHub release; the agent tags `v1.0.0-rc1`, the captain `v1.0.0` on `main` on 29.09; `scripts/release.sh` is the manual fallback | C13, §5, CHANGELOG 1.0.0 |
| 25.09 | the overview video ships captioned and silent (`docs/video/resense_overview.mp4`, 2:50, Russian subtitles burned in and as `.srt`); a voice-over is optional, muxed on without re-editing; C20 done | C20, action 9, PRESENTATION «Сборка ролика» |
| 25.09 | `offline-build` is a gate (continue-on-error removed after 4 of 4 green runs) and plays both synthetic bags through the runtime image loaded from the release archive on an `--internal` network; green on `5a15c7c` and `79109f5`; C25 done | C25, `.github/workflows/ci.yml` |
| 25.09 | long overhead rule on (`cluster.floating_long_min_length` 3.0), short-signature rule off: decided on the ride against pre-registered criteria; ride 204 / 47 / 39 → 197 / 46 / 39; short signatures would add 6 STOP episodes on the ride for +49 set O STOP frames | EXPERIMENTS §1f, [`rules_decision_2026-09-25.json`](evidence/results/rules_decision_2026-09-25.json), action 11 |

## 10. Why we slowed down (analysis of 24.09) and corrective rules

| # | root cause (ranked by effect on §8) | key numbers |
|---|---|---|
| 1 | P3 had no data, so the detector stopped improving after v0.6.3 (23.09) | 0 detector-output changes on 24.09; two opt-in paths landed off (near-bed 47 → 667 ride events, far-rail unmeasured); that push turned `main` red for 9 h 46 min |
| 2 | a verification loop replaced the improvement loop | 4 scorecards in 28 h; 107 / 20 reproduced 6 times on 24.09; set F straight run 3 times in 30 h; 1 of 28 commits after v0.6.3 moved a §8 metric, ~14 of 34 in the 19 h before |
| 3 | docs too big and duplicated: every change costs N edits | 5 893 md lines against 5 812 lines of product Python; 12:1 markdown to shipped-behaviour lines on 24.09; ~12 commits only propagated numbers |
| 4 | the captain is the bottleneck and works in other lanes | 63 of 77 commits (82 %) since 22.09 from the captain's sessions; P1 items 2–8 days old; 0 GitHub issues |
| 5 | late start, lost sprint | no push 16.09 18:41 → 20.09 20:12; human P2 / P3 / P4 first commits on days 9–10; no range lever replaced accumulation, which is off without a speed input |
| 6 | low-weight polish instead of owned deliverables | ~18 h on 4 dashboard restyles (not in the jury chain); narrated video, new-UI deck, set-O visual open |
| 7 | no merge discipline | 0 reviews; PRs merged 10–31 s after opening; direct pushes; `main` red twice (29.5 h, 9.8 h) and again since `537e220`; a repair by a non-author changed another owner's parameter |
| 8 | external: organizer input every day on 22–24.09 | absorbed correctly, at captain time |

| # | who | corrective action | by |
|---|---|---|---|
| 1 | P1 | stop the verification loop: one results source; no re-measure without a code change; no review until the freeze check (27.09 18:00) | 25.09 12:00 |
| 2 | P1 → P3 | data and harness to P3; no detector PR without their numbers | 25.09 12:00 |
| 3 | P3 | two detector PRs with numbers only: short-signature rule (ride ≤ ~50 events, five bags ≤ 22) and station / platform-end false STOPs (25 of 27 STOP episodes); near-bed and far-rail stay off | 26.09 20:00 |
| 4 | P4 | own the regression gate (one command, one JSON, every P3 PR within 2 h); fix ride-data access with P1 | 25.09 18:00 |
| 5 | P2 | freeze the UI; narrated video, new-UI dashboard clip, deck on the `docs/images/` captures, one set-O results visual | 26.09 20:00 |
| 6 | P1 | send Q1–Q2 (Q3 answered 25.09); stock-DDS CI step; photos by 25.09 18:00 and the private deck; 8-core timing; rc1 tag on 27.09 | 25–27.09 |
| 7 | all | freeze-week merge rules (§6); remaining items as GitHub issues with owners | 25.09 morning |
| 8 | P1 | doc diet: one sprint numbering, current results on one screen, history archived, numbers in one place | 25.09 |

State on 25.09 ~10:30 UTC: 1 done (the gate is the single results check, §3 action 4); 2 partly
(the ride streamed on the dev VM and used by the gate; P3's and P4's own copies not recorded,
action 3); 3 done by agents (both rules measured on the ride and decided: the long overhead rule
on, 10 of the 25 station STOP episodes gone; short signatures off; the 82.9 m platform end stays
open); 4 done by an agent for P4 (the gate and its baseline with the ride); 5 done by agents except
the new-UI clip (the captioned video, the deck); 6 partly (stock-DDS CI step, bench kit, version
1.0.0 and the release workflow done; confirming Q1–Q2, photos, the timing run open); 7 not done (0
GitHub issues: §3 is the tracker); 8 done.
