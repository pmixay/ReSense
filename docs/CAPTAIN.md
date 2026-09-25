# Captain Board

> **Purpose:** P1's board: criteria, plan to 29.09, runbook, rules, contracts, owners, decisions;
> history of 16–24.09 in [`archive/CAPTAIN_log_2026-09.md`](archive/CAPTAIN_log_2026-09.md).
> **Audience:** P1, team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-24 against `537e220` · **Status:** current

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

## 2. Criteria board (24.09)

| # | criterion (spec) | status | evidence / gap |
|---|---|---|---|
| C1 | image builds from scratch, no manual steps (§3.3.1, §7.2, 8.6) | DONE | `docker/Dockerfile`: pip pinned, non-editable install checked from `/`; CI `docker` job green on `4b5786b`. Gap: the build needs the network, which the stand does not have (C25: the image goes as an archive); apt and base image unpinned |
| C2 | `docker run` starts the node with no arguments, either topic / frame pair (answers §1 #2) | DONE | default command `ros2 launch resense_ros detector.launch.py`, topic auto-discovery, input switching in `tests/test_node.py` |
| C3 | every parameter a launch argument; mount configurable (Q&A fact 7) | DONE | `launch/detector.launch.py`: all node parameters plus `bag:=`, `rviz:=`, `loop:=`, `rate:=`, `delay:=` |
| C4 | organizers' console path: `ros2 bag play` by a normal user on the host | PARTIAL | CI plays as uid 1000 from our image (`scripts/console_test.sh`); a host player with stock Fast DDS or CycloneDDS is not tested (action 5) |
| C5 | start of a played bag not lost (8.3, 8.6) | DONE | v0.6.4 catch-up: first STOP 4.02 → 1.59 s of recording time (EXPERIMENTS §3b; raw capture not committed) |
| C6 | acceptance script asserting the result | DONE | `scripts/dry_run.sh` + `scripts/check_dry_run.py` (`--distance 50:62 --max-p95-latency 100 --max-dropped 0`) |
| C7 | clean-machine dry run with the original bags (§7.2) | NOT DONE | 28.09 on a clean team machine (action 15; the organizers' stand is not available before submission). Rehearsed 23.09 on bags rebuilt from the cache; the 4-vCPU dev VM runs 360° at 7–10 fps, p95 112–130 ms |
| C8 | timing on an 8-core analogue, the team's own 8-core machine (8.3); the i7-9700E stand is not available before submission ([`organizers/answers.md`](organizers/answers.md) §6, 25.09) | NOT DONE | owed since 16.09; only the 4-vCPU dev VM is measured (EXPERIMENTS §3). 24.09: C++ kernels merged, detector time −38…−57 % on the dev VM (ARCHITECTURE "Native kernels"), built and tested in the CI image (run 36058665640); the 8-core run is still owed (action 7); GPU evaluated, not used (ARCHITECTURE "GPU: evaluated, not used") |
| C9 | README per §5 (description, build, run, bag processing, parameters) | DONE | [`../README.md`](../README.md) |
| C10 | architecture and algorithm descriptions (§5) | DONE | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ALGORITHM.md`](ALGORITHM.md); stale spots and the 24.09 mount answer handled in the docs pass of 24.09 |
| C11 | evaluation protocol (stream C) | DONE | [`EVALUATION.md`](EVALUATION.md), sets S / E / R / O / F / H |
| C12 | SUBMISSION matches reality | PARTIAL | intermediate submission unrecorded (C14); the deck row reads "done" while the pptx shows 199 tests (now 266) and 17 `<…>` placeholders |
| C13 | release tag and upload package (§7.2) | NOT DONE | no tag, no GitHub release; no changes after the deadline (Q&A fact 22), so the upload points at a tag (§5) |
| C14 | intermediate submission (§7.1) | UNKNOWN | content in SUBMISSION; no tag, no record it was sent; the organizers' timeline has no intermediate stage (H confirms, action 1) |
| C15 | liaison: questions sent, answers applied (8.7) | PARTIAL | answers of 22–24.09 recorded, and the 25.09 statement on the stand (no access before submission, `organizers/answers.md` §6); Q1–Q2 (24.09) and Q3 (bed / envelope floor) drafted in QUESTIONS, not sent; Q1 corrected on 24.09 (its second sentence assumed moving objects) |
| C16 | main green, every PR reviewed, captain merges | PARTIAL | 0 GitHub reviews on PRs #3–#10; 5 of the 14 commits on `main` after the initial one were direct pushes (`a92625e`, `769619a`, `dfdebe5`, `41b7ae7`, `537e220`); main red 9 h 46 min on 24.09 after `769619a` (fixed 10:52); red again since `537e220`, fixed on the branch by `7df1796`, not yet on `main` |
| C17 | one parameter source, lint, tests in CI (8.5) | DONE | 266 tests in `tests/` (green on the native and numpy paths) + 11 in `web/demo`; CI jobs `pytest`, `web`, `lint` (ruff 0.15.8), `params-in-sync`, `docker`; the docker job builds the C++ kernels and runs the suite in the image (run 36058665640) |
| C18 | demo chain on screen (§4) | DONE | `video/docker_chain_rviz.mp4` (69 s), `scripts/run_demo.sh` |
| C19 | live remote demo (§4) | PARTIAL | runbook in README (RViz screen share, Foxglove on port 8765); never rehearsed from a second machine |
| C20 | video of the algorithm (§5, §7.2) | PARTIAL | 4 clips of 20–69 s, all silent; a narrated 2–3 min video is owed (P2) |
| C21 | pitch: team slides 2–4, captain slides, rehearsal (8.8) | NOT DONE | 17 `<…>` placeholders, photos of P1 and P4 missing; `build_deck.py` now says 266 tests, but the pptx is not rebuilt |
| C22 | decision: train speed | DONE (measured 24.09) | organizers' fact: no odometry in the recordings, some trains have none (Q&A fact 6). Team decision: ship the no-speed path; a given speed is honoured; the LiDAR-only estimator is accurate (median error 0.06–0.08 m/s) but buys nothing on the organizers' check, so it stays opt-in (EXPERIMENTS §9) |
| C23 | decision: GPU / stand software | DONE (evaluated 24.09) | CPU-only, the image installs no CUDA ([`organizers/test_stand_software.md`](organizers/test_stand_software.md)); GPU evaluated and not used: PCIe 3.0 on the i7, dispatch-bound port, the container would not start without `nvidia-container-toolkit` ([`ARCHITECTURE.md`](ARCHITECTURE.md) "GPU: evaluated, not used") |
| C24 | captain docs current (CAPTAIN, PLAN) | DONE | rewritten 24.09; the log is in `archive/` |
| C25 | runs on the offline stand: the test machine has no internet ([`organizers/answers.md`](organizers/answers.md) §7, 25.09) | PARTIAL | 25.09: the image is delivered as `resense-image-<version>.tar.gz` + `.sha256` (`scripts/export_image.sh`), loaded and checked with `--network none` by `scripts/load_image.sh`; no run-time network use in the node, launch file, entrypoint or compose services (audit of 25.09), the dashboard's roslib bundled; CI docker job: `docker save` → `docker rmi` → `docker load`, the synthetic bags through the loaded image with `--network none` and on an internal network; the job `offline-build` tries `docker build --cache-from` from the archive (best effort). Gap: first CI result of these steps; the rc1 / final archives (actions 14b, 16); the upload form's size limit (action 1b); the offline dry run (action 15) |

13 DONE · 7 PARTIAL · 4 NOT DONE · 1 UNKNOWN; every open item is release, timing, pitch or liaison.

## 3. Next actions to 29.09

| # | date | action | owner (H = human captain only; A = agent, captain merges) | priority |
|---|---|---|---|---|
| 1 | 24.09 | read the i.moscow upload form (fields, file or link, limits), settle the intermediate stage (C14); announce the §6 rules; approve branch protection on `main` | H | must |
| 1b | 25.09 | the stand has no internet (C25): find the upload form's file-size limit and whether it takes a link; the image archive must reach the jury (its size is printed by `export_image.sh`; the runtime image is expected well under 2 GB gzip, unmeasured). Over the limit: a link (Yandex Disk, or a GitHub release asset ≤ 2 GB) with the sha256 in the cover message | H | must |
| 2 | 24.09 | send QUESTIONS Q1–Q3 as one message to @gorbatovaol, **from the current file** (do not send an older Q1: its second sentence was built on the moving-objects error); file the answers in `organizers/answers.md` | H (A drafted) | must |
| 3 | 25.09 12:00 | give P3 the frame caches (six bags, ride, `cloud_with_fake_obj`) and the harness (`eval_real.py`, `score_fake_objects.py`, `start_offsets.py`) | P1 → P3 | must |
| 3b | 25.09 | ~~prove the Docker build with the C++ kernels~~ done: CI run 36058665640 green on the branch (24.09); merge the branch to `main` through a PR | H merges | must |
| 4 | 25.09 12:00 | stop the verification loop: numbers live in EXPERIMENTS "Current results" + raw JSON; re-measure only when `resense/`, `configs/` or the node change | P1 | must |
| 5 | 25.09 | CI step with a stock-Fast-DDS player (`PLAYER_ENV` in `console_test.sh`, `ci.yml`) | A | should |
| 6 | 25.09 18:00 | regression gate: one command, one JSON (six bags, ride, set O, set F straight), run on every P3 PR within 2 h | P4 | must |
| 7 | 25.09 | 8-core bench on the team's own machine (no stand access before submission, [`organizers/answers.md`](organizers/answers.md) §6), native and numpy (`RESENSE_NATIVE=0`) paths: `build.sh`, `dry_run.sh` on both bags, `console_test.sh`, `docker stats`, `bench_node_path.py`; raw logs to `docs/evidence/bench_2026-09-25/`, summary to EXPERIMENTS §3 | H (+A) | must |
| 8 | 25.09 18:00 | every member sends a photo; fill `docs/presentation/private/team.json`; build the private deck with 0 `<…>` left | H + all | must |
| 9 | 26.09 | narrated 2–3 min video `docs/video/resense_overview.mp4`; dashboard clip with the new UI | P2 edits, H voice | should |
| 10 | 26.09 | deck refresh: organizers' objects, anchored 154 m, slide-12 caption, new UI captures; rebuild pptx / pdf ([`PRESENTATION.md`](PRESENTATION.md)) | P2 | should |
| 11 | 26.09 20:00 | go / no-go on late changes (P3 short-signature rule, station false STOPs, the CPU savings of the GPU study) by the §6 gate | H decides, P3 / P4 measure | must |
| 12 | 26.09 | ~~decide on the saved-image release asset~~ decided 25.09: the image archive is a must, not insurance (no internet on the stand, C25, §5) | H | done |
| 13 | 27.09 | final consistency pass: every headline number equals EXPERIMENTS "Current results" | A | must |
| 14 | 27.09 18:00 | version bump and `v1.0-rc1` tag, whatever the state | A prepares, H tags | must |
| 14b | 27.09 | export the rc1 image archive from a clean clone of the tag, on a machine with internet: `VERSION=v1.0-rc1 ./scripts/export_image.sh` → `dist/resense-image-v1.0-rc1.tar.gz` + `.sha256`; note size and sha256 here; `scripts/load_image.sh` on a second machine | H (Docker) | must |
| 15 | 28.09 | **offline** dry run on a clean team machine (the stand is not available), network disconnected: the rc1 archive, `IMAGE_TAR=… OFFLINE=1 ./scripts/dry_run.sh` on both bags, then the README jury commands by hand (SUBMISSION "Dry run"), logs to `docs/evidence/dry_run_2026-09-28/`; remote demo from a second laptop | H | must |
| 16 | 29.09 | final tag, the final archive (`VERSION=v1.0-final ./scripts/export_image.sh`) and upload with its sha256 (§5) | H | must |
| 17 | 30.09–23.10 | answer the organizers daily during the expertise; pitch on 23.10 after two rehearsals (fallback demo `video/docker_chain_rviz.mp4`) | H (+P2) | must |

## 4. Human-only checklist

- [ ] 24.09: upload form read, intermediate stage settled (C14); Q1–Q3 sent; §6 rules announced
- [ ] 25.09: 8-core bench and dry runs (no Docker for agents); `private/` team data, photos, deck
- [ ] 25.09: upload form's file-size limit and link policy checked for the image archive (1b)
- [ ] 26.09: go / no-go taken; voice-over recorded · 27.09: `v1.0-rc1` pushed, its archive exported
  (size and sha256 noted), loaded once on a second machine
- [ ] 28.09: clean team-machine dry run **offline** (network disconnected, from the archive),
  remote demo · 29.09: `v1.0-final`, its archive + sha256, release, upload by 18:00
- [ ] 30.09–14.10: reachable for the organizers · 23.10: pitch led after two rehearsals

## 5. Release and upload runbook

```bash
# 27.09 18:00, CI green; version bumped in pyproject.toml, __init__.py, package.xml, setup.py
git tag -a v1.0-rc1 -m "release candidate" && git push origin v1.0-rc1
git clone --branch v1.0-rc1 <repo> rc1 && cd rc1                # clean clone, machine with internet
VERSION=v1.0-rc1 ./scripts/export_image.sh      # dist/resense-image-v1.0-rc1.tar.gz + .sha256
git tag -a v1.0-final -m "LCT-2026 case 05 final" && git push origin v1.0-final   # 29.09 13:00
VERSION=v1.0-final ./scripts/export_image.sh    # from a clean clone of v1.0-final: the upload
./scripts/load_image.sh dist/resense-image-v1.0-final.tar.gz    # second machine: sum, load, run
```

**The image archive is a must, not insurance** (25.09): the stand has no internet
([`organizers/answers.md`](organizers/answers.md) §7), so `docker build` cannot run there and the
jury's step 1 is `docker load -i resense-image-<version>.tar.gz`. gzip, not zstd: `docker load`
reads gzip on any Docker. The archive also holds the base image's tag and the build's layer cache,
so an offline `docker build --cache-from` may work (best effort, ARCHITECTURE "Deployment without
internet"). 29.09: last merge 12:00; CI green on the tag 14:00; the final archive and its sha256
13:00–14:30; upload on i.moscow 15:00 (link with the tag and commit hash, the archive or its link
with the sha256, SUBMISSION cover message, video and deck as the form asks); 16:00 open it logged
out, clone the tag and load the archive. Then no pushes to `main` (Q&A fact 22). After rc1: blocker
PRs, then `v1.0-rc2`.

## 6. Freeze and merge rules

- From 25.09 `main` changes only by a PR with CI green and a GitHub review from another lane; the
  captain merges; branch protection on. A red `main` is fixed by its author within 1 h or reverted.
- No edits in another lane's files without the owner's OK (§8). Contract changes (§7): `[contract]`
  in the PR title and a heads-up to the consumers; add, never rename or remove.
- Freeze: detector and config **26.09 20:00**, docs **27.09 20:00**; from 28.09 blockers only.
- Detector / config gate: identical or better on the 13 759 real frames (`scripts/eval_real.py`),
  set O (`score_fake_objects.py`) and set F straight; else "tried, not shipped" (EXPERIMENTS §7).
- Numbers only in EXPERIMENTS "Current results" and the README summary; one sprint numbering (PLAN).

## 7. Contracts

| contract | where | consumers |
|---|---|---|
| jury path `docker load` (no internet on the stand; `docker build` where there is) `→ docker run → ros2 bag play → /resense/decision` | README, SUBMISSION "Dry run" | jury, P2 video |
| 12 topics `/resense/{decision, obstacle_detected, warning, nearest_distance, clear_distance, detections, status, health, markers, corridor_points, latency_ms, fps}` + `/tf_static` | `detector_node.py`, README "Topics published by the node" | P2, jury |
| status JSON: `stamp, obstacle, warning, nearest_distance, clear_distance, detections[], warnings[], track, health, mount, timing_ms, ego_speed*, n_accumulated, n_*` + `node` (added by the node) | `FrameResult.to_dict()` in `resense/detector.py` | P2 dashboard, `resense run --out` |
| `Frame` (xyz in the vehicle frame, intensity, ring, stamp) | `resense/frame.py` | P3, P4 |
| one parameter file `configs/default.yaml`, root key `resense:`, ROS copy in sync | `resense/config.py`, `scripts/sync_params.sh` | P3 tunes, node loads |
| offline formats: `*.npz` + `gt.json` from `inject`, JSONL from `run` | `resense/cli.py` | P4 `eval`, P2 label tool |

## 8. Ownership map (a file not listed: its author's lane; ask P1)

| path | owner |
|---|---|
| `docker/`, `docker-compose.yml`, `ros2_ws/src/resense_ros/` (except `rviz/`), `scripts/*.sh` (except `build_native.sh`), `scripts/{check_dry_run,make_smoke_bag,cache_to_bag,bench_node_path,check_no_network}.py` | P1 |
| `README.md`, `CHANGELOG.md`, `docs/{README,ARCHITECTURE,ALGORITHM,EVALUATION,SUBMISSION,SENSOR,PLAN,CAPTAIN,QUESTIONS,SCORECARD}.md`, `docs/archive/`, team notes in `docs/organizers/` | P1 (P3 reviews ALGORITHM) |
| `.github/workflows/ci.yml` | P4 `pytest`, P2 `web`, P1 the other jobs |
| `configs/default.yaml` | P3 values, P1 structure |
| `resense/{track,gauge,clustering,tracking,accumulate,egomotion,lowobj,calibration,health,config,detector,_native}.py`, `native/`, `setup.py`, `scripts/build_native.sh`, `tests/{test_algorithm,test_lowobj_near,test_native}.py` | P3 |
| `resense/{frame,pointcloud,sensor}.py` | P1 decoding / P3 geometry |
| `resense/{synthetic,metrics,io,cli}.py`, other `tests/` (`test_node.py`: P1), `labels/`, `scripts/{cache_frames,eval_real,far_range_eval,compare_setf,label_fake_objects,score_fake_objects,short_signature_experiment,unpack_dataset,start_offsets}.py`, `scripts/speed_*.py` (with `tests/test_speed_eval_helpers.py`), `docs/{P4_AUDIT,DATASET}.md`, `docs/evidence/results/` | P4 |
| `docs/EXPERIMENTS.md` | P3 / P4; P1 appends timing |
| `web/` (incl. `web/assets/fonts/`, `web/demo/`), `ros2_ws/src/resense_ros/rviz/`, `docs/{PRESENTATION.md,images/,img/,video/,presentation/}`, `scripts/{build_deck,hero_view}.py` | P2 (`docs/img/` stays in place: scripts read it) |

## 9. Decision log

| date | decision | source |
|---|---|---|
| 22.09 | obstacle = anything ≥ 30 × 30 × 10 cm in the 2.1 × 3.0 m envelope, hanging cables included; advisory zone 0.35 m wider | Q&A facts 1–3 |
| 22.09 | no map: the tunnel model is rebuilt from every frame | Q&A fact 15 |
| 22.09 | train speed: organizers' fact (no odometry, some trains have none) → team decision: operate without it; `ego_speed_mps` / `speed_topic` / `odom_topic` optional, accumulation off unless a speed is given | Q&A fact 6, [`organizers/answers.md`](organizers/answers.md) §4 |
| 22.09 | CPU-only image; any GPU stage optional with a CPU fallback | `organizers/test_stand_software.md` |
| 23.09 | confirmation 0.5 s (v0.6.2), a STOP held over one missed frame (v0.6.3); Fast DDS over UDP only in the image, `input_reliability: auto` | EXPERIMENTS §0, §3b |
| 24.09 | bed policy: nothing below the envelope floor (0.12 m above the rail head) between the rails is reported; asked as Q3 | ALGORITHM §3.3b, QUESTIONS Q3 |
| 24.09 | opt-in near-bed path (`lowobj.near_enabled`) and far-rail check (`track.rails_far_check_enabled`) stay off: near-bed first gates 47 → 667 ride events (raw not committed); current gates (`537e220` + box fix `7df1796`) five bags 20 → 107 events, ride not re-run; far-rail unmeasured | ALGORITHM §6, EXPERIMENTS §1e |
| 24.09 | mount: test bags use the provided mounts, LiDAR 1075 mm above the rail head on the centreline; auto-calibration stays as a safeguard (it measures 1.12 m / −0.02 m on `roundT_doubleT`) | [`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md) |
| 24.09 | switch glitches are not counted against us → station / platform false STOPs come first for P3 | `mount_and_switch_qa.md` §5 |
| 24.09 | the criteria judgement in SCORECARD (60 / 100) replaces every earlier scorecard; the release tag is no longer deferred (`v1.0-rc1` on 27.09 18:00) | §1, §5 |
| 24.09 | train speed, measured: estimator accurate, but even a perfect speed gives no earlier STOP on set O and more false STOPs; `estimate_speed` stays `false`, a given speed is honoured | EXPERIMENTS §9 |
| 24.09 | no GPU before 29.09 (≤ 30–45 ms per 360° frame at best, untestable in CI, container start depends on the host toolkit) | ARCHITECTURE "GPU: evaluated, not used" |
| 24.09 | C++ kernels merged on the branch (bit-identical, −38…−57 %); to `main` only after the CI docker job and with an 8-core bench to follow; `RESENSE_NATIVE=0` is the fallback | ARCHITECTURE "Native kernels" |
| 25.09 | no run on the organizers' stand before submission (they give no access): timing on the team's own 8-core machine (action 7), the 28.09 dry run on a clean team machine (action 15), the Docker chain in CI; stand facts and estimates stay, labelled as such | [`organizers/answers.md`](organizers/answers.md) §6 |
| 25.09 | no internet on the test machine: the image is delivered as a `docker load` archive with its sha256 (`scripts/export_image.sh`, a must in the upload); README step 1 is `docker load`, `docker build` only with internet; CI proves save → load → run with no network; an offline `docker build --cache-from` is best effort only; the 28.09 dry run runs offline from the archive; the dashboard's roslib bundled; the Dockerfile's layers unchanged before the freeze | [`organizers/answers.md`](organizers/answers.md) §7, C25 |

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
| 6 | P1 | send Q1–Q3; stock-DDS CI step; photos by 25.09 18:00 and the private deck; 8-core timing; rc1 tag on 27.09 | 25–27.09 |
| 7 | all | freeze-week merge rules (§6); remaining items as GitHub issues with owners | 25.09 morning |
| 8 | P1 | doc diet: one sprint numbering, current results on one screen, history archived, numbers in one place | 25.09 |
