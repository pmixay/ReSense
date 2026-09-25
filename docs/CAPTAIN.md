# Captain Board

> **Purpose:** P1's board: criteria, plan to 29.09, runbook, rules, contracts, owners, decisions;
> history of 16–24.09 in [`archive/CAPTAIN_log_2026-09.md`](archive/CAPTAIN_log_2026-09.md).
> **Audience:** P1, team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-25 against `8932f3a` · **Status:** current

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

Statuses as of 25.09 ~08:35 UTC on `8932f3a` (the four merges of the day), checked against CI
and the repository; they start from the independent progress check of 25.09 08:05 UTC and add
what merged after it (ci-bench, regression-gate, deck, late-changes). HUMAN = only a person can
close it.

| # | criterion (spec) | status | evidence / gap |
|---|---|---|---|
| C1 | image builds from scratch, no manual steps (§3.3.1, §7.2, 8.6) | DONE | `docker/Dockerfile`: pip pinned, non-editable install checked from `/`. CI run 36112092652 (`8932f3a`): the `docker` job builds the image; the `offline-build` job builds the runtime image `--no-cache` from `git archive HEAD` (1.34 GiB). Gap: apt and the base image unpinned (accepted); the stand has no internet, so the image goes as an archive (C25) |
| C2 | `docker run` starts the node with no arguments, either topic / frame pair (answers §1 #2) | DONE | default command `ros2 launch resense_ros detector.launch.py`, topic auto-discovery; CI (run 36112092652) starts it with no arguments and switches between both pairs ("input switched … detector restarted"); `tests/test_node.py` |
| C3 | every parameter a launch argument; mount configurable (Q&A fact 7) | DONE | `launch/detector.launch.py`: 31 launch arguments, the node declares exactly those plus `config_file` (checked by script 25.09), plus `bag:=`, `rviz:=`, `loop:=`, `rate:=`, `delay:=` |
| C4 | organizers' console path: `ros2 bag play` by a normal user on the host | DONE | CI plays as uid 1000 from our image twice. With the image's UDP profile (step 7) and, since 25.09, with stock Fast DDS: `PLAYER_DDS=stock` in `scripts/console_test.sh`, no XML profile, shared memory + UDPv4, a stock uid-1000 listener. Run 36112092652 (`8932f3a`), docker job step 8 green: `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, both profile variables unset, fastrtps 2.6.12; each play exited 0 and created 5 new shared-memory files of its own; the listener heard 111 `/resense/decision` messages, 42 `STOP`. The node announces no shared-memory locators, so stock clients reach it over UDP. CycloneDDS not tested; a real host console is part of the 28.09 dry run (action 15) |
| C5 | start of a played bag not lost (8.3, 8.6) | DONE | v0.6.4 catch-up (`input_queue_depth` 40, `catchup_step` 0.3); CI on the synthetic bags: 39–40 frames in the first 5 s, first STOP at +1.9 s (run 36112092652). Caveat: the real-bag figure (first STOP 4.02 → 1.59 s, EXPERIMENTS §3b) has no committed raw capture |
| C6 | acceptance script asserting the result | DONE | `scripts/dry_run.sh` + `scripts/check_dry_run.py` (`--distance 50:62 --max-p95-latency 100 --max-dropped 0`); `IMAGE_TAR` / `OFFLINE` (offline stand) and `DOCKER_ARGS` (25.09); `scripts/bench_8core.sh` runs it on both bags, native and numpy. Gap: it needs the dataset, so CI never runs it; its offline path is first used on 28.09 (H) |
| C7 | clean-machine dry run with the original bags (§7.2) | NOT DONE · HUMAN | 28.09 (action 15) on the team's 8-core machine, offline, from the rc1 archive: the organizers' stand is not available before the upload (organizers, 25.09). Rehearsed 23.09 on bags rebuilt from the cache; the 4-vCPU dev VM runs 360° at 7–10 fps, p95 112–130 ms. No `docs/evidence/dry_run_2026-09-28/` yet |
| C8 | timing on an 8-core analogue of the i7-9700E (8.3; the stand is not available before the upload, [`organizers/answers.md`](organizers/answers.md) §6) | NOT DONE (kit ready) · HUMAN | one command, `scripts/bench_8core.sh` (`8242c3e`, merged 25.09): build, dry runs on both bags with the node native and numpy, console tests with the image's and a stock player, `docker stats` every 2 s, offline `bench_node_path.py` / `resense bench` native and numpy with peak RSS → `docs/evidence/bench_<date>/summary.txt`; tested only against a mock `docker`. Only the 4-vCPU dev VM is measured so far (EXPERIMENTS §3): C++ kernels −38…−57 % there, DBSCAN on cKDTree −1.3…−2.6 ms more; GPU evaluated, not used. DONE when `dry_obstacle_native` passes (p95 ≤ 100 ms, no frame dropped after 5 s) |
| C9 | README per §5 (description, build, run, bag processing, parameters) | DONE | [`../README.md`](../README.md): jury commands first (step 1 `docker load`), how a bag is processed, build / run, node and config parameters; verified 25.09 against `8932f3a` |
| C10 | architecture and algorithm descriptions (§5) | DONE | [`ARCHITECTURE.md`](ARCHITECTURE.md) ("Native kernels" with DBSCAN on cKDTree, "GPU: evaluated, not used", "Deployment without internet"), [`ALGORITHM.md`](ALGORITHM.md) (§3.3 the two opt-in rules of 25.09); verified 25.09 |
| C11 | evaluation protocol (stream C) | DONE | [`EVALUATION.md`](EVALUATION.md), sets S / E / R / O / F / H; §3 step 6 is the regression gate (`scripts/regression_gate.py`, 25.09) |
| C12 | SUBMISSION matches reality | DONE | 25.09: row 10 (gate, bench kit), 11 (five clips, video script), 13 (deck: 16 slides, 289 tests), 14 (289 tests, CI jobs) and 17 (archive 0.49 GiB in CI) match the repo. Both open points closed later on 25.09: the upload form takes links and has no size limit ([`organizers/answers.md`](organizers/answers.md) §8), so "Upload" lists the links to type and the check before submitting, row 17 the archive as the tag's GitHub release asset; the intermediate stage is settled as not held (C14). Re-check row 17 when `.github/workflows/release.yml` (being added) is merged |
| C13 | release tag and upload package (§7.2) | NOT DONE | GitHub: 0 tags, 0 releases; the version is still 0.6.3 in `pyproject.toml`, `resense/__init__.py`, `package.xml`, `setup.py` (bump on 27.09, action 14); no changes after the deadline (Q&A fact 22), so the upload points at a tag (§5) |
| C14 | intermediate submission (§7.1) | DONE (resolved: not held) | decided 25.09: no separate intermediate upload in the organizers' timeline; the §7.1 content (Dockerfile, prototype, description, mini-demo, first experiments) is in the repository (SUBMISSION "Intermediate submission"). Evidence: the organizers' timeline ([`organizers/README_organizers.md`](organizers/README_organizers.md) "Ключевые этапы конкурса") lists only «Приём заявок \| до 14 сентября», «Разработка решений \| 15–29 сентября», «Техническая экспертиза \| 30 сентября – 14 октября», «Презентация проектов \| 23 октября», «Церемония награждения \| 30 октября»; spec §7.1 («7.1. Промежуточная сдача», «К промежуточной сдаче необходимо предоставить: …», `technical_specification_case05.txt` lines 184–193) gives the content but no date, form or place; the Q&A of 22.09 does not mention it. No `v0.1-intermediate` tag |
| C15 | liaison: questions sent, answers applied (8.7) | PARTIAL | answers of 22–24.09 recorded, and the statements of 25.09 from the captain's oral reports: no stand access before the upload (`organizers/answers.md` §6), no internet on the test machine (§7), the upload form takes links with no size limit and **Q3 answered: the 30 × 30 × 10 cm object on the bed between the rails is not an obstacle** (§8; QUESTIONS "Answered"). Open: Q1–Q2 (24.09, edge reference and #8), drafted in QUESTIONS, **not known whether they were sent** (captain to confirm, action 2) |
| C16 | main green, every PR reviewed, captain merges | PARTIAL | **`main` is green again:** PR #11 merged 06:51 UTC (`5de0844`) brought the near-bed gate fix `7df1796` to `main`; run 36104815305 green (`main` was red ~12 h, from run 36044487647 at 18:54 UTC 24.09). **Still failing the §6 rules:** PR #11 had 0 reviews and was merged by its author 3.5 min after opening; branch protection is off; 0 reviews on PRs #1–#11; the branch is 39 commits (without merges) ahead of `main` (offline delivery, kernels, gate, deck not on `main`) and no branch → `main` PR is open (action 3b); P2 pushed 10 dashboard commits straight onto the branch (24.09); the 25.09 agent branches changed files in P2's (deck, video), P3's (`clustering.py`, configs) and P4's (gate) lanes with no recorded owner OK — the owners confirm in the review of that PR |
| C17 | one parameter source, lint, tests in CI (8.5) | DONE | 289 tests in `tests/` (green on the native and numpy paths) + 11 in `web/demo`; CI jobs `pytest` (with "no test may have been skipped"), `web`, `lint` (ruff 0.15.8), `params-in-sync`, `docker` (289 passed in the image, run 36112092652), `offline-build`. The `web` job was red at `8932f3a` (the test still expected the 15-slide deck); fixed the same day (action 10b) |
| C18 | demo chain on screen (§4) | DONE | `video/docker_chain_rviz.mp4` (69 s), `scripts/run_demo.sh` |
| C19 | live remote demo (§4) | PARTIAL · HUMAN | runbook in README (RViz screen share, Foxglove on port 8765); Foxglove not yet tried against a live `foxglove_bridge`; never rehearsed from a second machine (28.09, action 15) |
| C20 | video of the algorithm (§5, §7.2) | PARTIAL | 5 clips, all silent (25.09: `video/fake_objects_cab.mp4`, 20.5 s, the organizers' 2 × 2 m box from the cab on a moving train, STOP from 98 m); RU narration and shot list with timings in PRESENTATION «Сценарий видео (2–3 мин)» (2:50, ~400 words, `8e843d8`). Left: voice (H) and edit (P2) → `video/resense_overview.mp4` (action 9) |
| C21 | pitch: team slides 2–4, captain slides, rehearsal (8.8) | PARTIAL | public deck rebuilt 25.09 (`16d2a07`, then after the merges): 16 slides, 289 tests, the organizers' objects (slide 13), the anchored 154 m next to 150 m legacy in the same 5 pairs, «~210 м — предел отражений в тоннеле», the real-data UI capture, C++ kernels / train speed / GPU lines; the 17 `<…>` stay only on slides 2–3 of the public build by design. Left: `private/team.json` + photos of P1 and P4, the private `--team` build (action 8), two rehearsals |
| C22 | decision: train speed | DONE (measured 24.09) | organizers' fact: no odometry in the recordings, some trains have none (Q&A fact 6). Team decision: ship the no-speed path; a given speed is honoured; the LiDAR-only estimator is accurate (median error 0.06–0.08 m/s) but buys nothing on the organizers' check, so it stays opt-in (EXPERIMENTS §9) |
| C23 | decision: GPU / stand software | DONE (evaluated 24.09) | CPU-only, the image installs no CUDA ([`organizers/test_stand_software.md`](organizers/test_stand_software.md)); GPU evaluated and not used ([`ARCHITECTURE.md`](ARCHITECTURE.md) "GPU: evaluated, not used"); of the CPU savings that study found, the cKDTree DBSCAN shipped 25.09, the forward crop did not (no gain on the native path) |
| C24 | captain docs current (CAPTAIN, PLAN) | DONE | refreshed 25.09 against `8932f3a` (this revision and PLAN): every discrepancy of the 08:05 UTC check fixed (C16 `main` state, the stale headers, C25 / action 1b CI results, action 3b's open half, the C1 / C17 evidence, the 148 / 150 / 154 m pairing, the test count) |
| C25 | runs on the offline stand: the test machine has no internet ([`organizers/answers.md`](organizers/answers.md) §7, 25.09) | PARTIAL | tooling: `export_image.sh`, `load_image.sh`, `check_no_network.py`, `dry_run.sh` `IMAGE_TAR` / `OFFLINE`, roslib bundled; no network use in the node, launch file, entrypoint or compose (audit). CI runs 36109782167 (`2b3cbd0`) and 36112092652 (`8932f3a`), all green: `docker save` → `docker rmi` → `docker load` keeps the layers; the smoke test passes with `--network none`; node and a uid-1000 player pass on an `--internal` network; `offline-build`: runtime archive 521 185 902 bytes (0.49 GiB at gzip -1, 1.34 GiB unpacked, base image included), and after loading it `docker build --cache-from` with Docker Hub blocked took all 18 steps from the cache. Gaps: no bag played through the **runtime** image loaded from an archive (CI plays through the tools image); the rc1 / final archives (actions 14b, 16); the upload form's size limit (action 1b); the offline dry run with the real bags (action 15). Cosmetic: `load_image.sh` prints the Ubuntu base's version label ('22.04') for an image exported with `SKIP_BUILD=1`; a real export labels the version; Kit ready: [`scripts/vm/`](../scripts/vm/AGENT_BRIEF.md) (`run_plan.sh offline`: outbound blocked with an automatic restore, a host `ros2 bag play` into the loaded image) |

16 DONE · 6 PARTIAL · 3 NOT DONE · 0 UNKNOWN. Every open item is release, timing, pitch, liaison or
merge discipline.

**Progress 25.09:** criteria DONE 16 of 25 (board of 24.09: 13 of 24; the independent check at
08:05 UTC: 12 of 25), new since then C4 (stock-DDS CI step green), C24 (this refresh), and later on
25.09 C12 and C14 (organizers' answers of 25.09: upload by links with no size limit; intermediate
stage not held), C21 NOT DONE → PARTIAL; actions done 7 of 21 (1b, 4, 5, 6, 10, 10b, 12; at
08:05 UTC: 1 of 20), 4 in progress (3b, 7, 9, 11), 4 due or overdue (1, 2, 3, 8, all human), 6
dated 27.09 or later.

## 3. Next actions to 29.09

| # | date | action | owner (H = human captain only; A = agent, captain merges) | priority |
|---|---|---|---|---|
| 1 | 24.09 | **overdue.** Read the i.moscow upload form (fields, file or link, limits), settle the intermediate stage (C14); announce the §6 rules; turn on branch protection on `main` (API: off) | H | must |
| 1b | 25.09 | ~~find the upload form's file-size limit and whether it takes a link~~ done 25.09 (organizers, [`organizers/answers.md`](organizers/answers.md) §8): the form takes **links**, **no size limit**. The runtime archive (521 185 902 bytes, 0.49 GiB at gzip -1, CI run 36109782167) goes as the tag's GitHub release asset `resense-image-<tag>.tar.gz` + `.sha256` (`.github/workflows/release.yml` on a `v*` tag push, being added; by hand `gh release upload` otherwise), the sha256 typed in the form; the links to type and the check before submitting (every link opened logged out, `load_image.sh` on a second machine) in SUBMISSION "Upload" | H | must |
| 2 | 24.09 | Q3 (bed object) **answered 25.09**: not an obstacle ([`organizers/answers.md`](organizers/answers.md) §8, moved to QUESTIONS "Answered"). **Open:** confirm whether Q1–Q2 were sent (the repository records no sending); if not, send them as one message to @gorbatovaol **from the current file** (now Q1–Q2 only; not an older Q1: its second sentence was built on the moving-objects error); file the answers in `organizers/answers.md` | H (A drafted) | must |
| 3 | 25.09 12:00 | give P3 / P4 the frame caches (six bags, the ride `new_data`, `cloud_with_fake_obj`) and the harness (`eval_real.py`, `score_fake_objects.py`, `start_offsets.py`, `regression_gate.py`); the ride cache is what actions 6 and 11 still need | P1 → P3, P4 | must |
| 3b | 25.09 | ~~prove the Docker build with the C++ kernels~~ done (CI since run 36058665640, 24.09; every docker job since); **open:** the branch → `main` PR (39 commits without merges), reviewed by the owners of the lanes the agents touched (P2, P3, P4), CI green, then the captain merges | A opens, owners review, H merges | must |
| 4 | 25.09 12:00 | ~~stop the verification loop~~ done 25.09: numbers live in EXPERIMENTS "Current results" + raw JSON, and re-measuring is one command, `scripts/regression_gate.py` (one JSON; baseline `docs/evidence/results/regression_baseline_2026-09-25.json`), run only when `resense/`, `configs/` or the node change | P1 (A) | must |
| 5 | 25.09 | ~~CI step with a stock-Fast-DDS player~~ done 25.09: `PLAYER_DDS=stock` / `PLAYER_ENV` in `console_test.sh`, CI step "the jury's console with stock Fast DDS" (`fbef12b`), green on its first run (36112092652) | A | should |
| 6 | 25.09 18:00 | ~~regression gate: one command, one JSON~~ done 25.09 (A for P4): `scripts/regression_gate.py`, `tests/test_regression_gate.py`, baseline of the six recordings + set O (native path, equal to the 24.09 numbers; 66 s at `--jobs 2` on the dev VM); the merged `8932f3a` passes. Left (P4 / H): a baseline including the ride and set F straight on the 8-core machine (`--cache` with `new_data`), then the gate on every P3 PR within 2 h | P4 | must |
| 7 | 25.09 | 8-core bench (stands in for the i7 stand, not available before the upload): kit done (`8242c3e`, A); **run open (H):** `scripts/bench_8core.sh <bags>/doubleT_obstacle <bags>/roundT_doubleT` (it builds and times the build; `SKIP_BUILD=1` reuses an image; ~10–25 min, fails fast without Docker or data; `OFFLINE_ONLY=1` for the host part alone); commit `docs/evidence/bench_<date>/` as written; `summary.txt` numbers into EXPERIMENTS §3; by 26.09 midday, early enough to act before the freeze; kit ready: [`scripts/vm/`](../scripts/vm/AGENT_BRIEF.md) (`run_plan.sh bench`, `gate` with the ride) | H (+A) | must  |
| 8 | 25.09 18:00 | every member sends a photo; fill `docs/presentation/private/team.json`; build the private deck with 0 `<…>` left | H + all | must |
| 9 | 26.09 | narrated 2–3 min video `docs/video/resense_overview.mp4`: script and shot list done 25.09 (PRESENTATION «Сценарий видео (2–3 мин)»; new clip `video/fake_objects_cab.mp4`); left: voice (H) and edit (P2) on 26.09; a new-UI dashboard clip is optional (the stills in `images/` are used) | P2 edits, H voice | should |
| 10 | 26.09 | ~~deck refresh and rebuild~~ done 25.09 (`16d2a07`, rebuilt again after the merges): pptx and pdf, 16 slides, 289 tests, the 148 / 150 / 154 m wording as in EXPERIMENTS | P2 (A) | should |
| 10b | 25.09 | ~~the `web` CI job red at `8932f3a` (`web/demo/test_web.py` asserted 15 slides; the rebuilt deck has 16)~~ done 25.09: the expected count follows the deck (16), all 11 web tests pass; P2 informed by this row | A | must |
| 11 | 26.09 20:00 | go / no-go on late changes by the §6 gate (`scripts/regression_gate.py --baseline …` exits 0 on the change, or every worse row is named with `--allow` and accepted here). 25.09, measured and merged (EXPERIMENTS §1f): DBSCAN on cKDTree shipped (identical, −1.3…−2.6 ms); forward crop and `zf` reuse not shipped (no native gain); `cluster.floating_long_min_length: 3.0` gate PASS, five bags 107 / 20 / 27 → 60 / 14 / 17; `cluster.short_signature_max_length: 3.0` gate FAIL on 5 rows, set O +49 STOP frames; both flags off. **Left:** the ride and set F straight on the 8-core machine with `--set …` (P4 / H, who have the ride cache), then H decides; flipping a flag needs no code (`configs/default.yaml`, `scripts/sync_params.sh`) | H decides, P3 / P4 measure | must |
| 12 | 26.09 | ~~decide on the saved-image release asset~~ decided 25.09: the image archive is a must, not insurance (no internet on the stand, C25, §5) | H | done |
| 13 | 27.09 | final consistency pass: every headline number equals EXPERIMENTS "Current results" (the gate's JSON for the real data and set O) | A | must |
| 14 | 27.09 18:00 | version bump and `v1.0-rc1` tag, whatever the state | A prepares, H tags | must |
| 14b | 27.09 | export the rc1 image archive from a clean clone of the tag, on a machine with internet: `VERSION=v1.0-rc1 ./scripts/export_image.sh` → `dist/resense-image-v1.0-rc1.tar.gz` + `.sha256`; note size and sha256 here; `scripts/load_image.sh` on a second machine; kit ready: [`scripts/vm/`](../scripts/vm/AGENT_BRIEF.md) (`run_plan.sh export --ref v1.0-rc1`) | H (Docker) | must  |
| 15 | 28.09 | **offline** dry run on a clean team machine (the stand is not available), network disconnected: the rc1 archive, `IMAGE_TAR=… OFFLINE=1 ./scripts/dry_run.sh` on both bags, then the README jury commands by hand from a normal user's host console (stock ROS 2 if installed) (SUBMISSION "Dry run"), logs to `docs/evidence/dry_run_2026-09-28/`; remote demo from a second laptop; kit ready: [`scripts/vm/`](../scripts/vm/AGENT_BRIEF.md) (`run_plan.sh dryrun`, `run_plan.sh offline`) | H | must  |
| 16 | 29.09 | final tag, the final archive (`VERSION=v1.0-final ./scripts/export_image.sh`) and upload with its sha256 (§5) | H | must |
| 17 | 30.09–23.10 | answer the organizers daily during the expertise; pitch on 23.10 after two rehearsals (fallback demo `video/docker_chain_rviz.mp4`) | H (+P2) | must |

## 4. Human-only checklist

- [ ] **overdue (24.09):** upload form read, intermediate stage settled (C14); Q1–Q3 sent; §6
  rules announced; branch protection on `main`
- [ ] 25.09: upload form's file-size limit and link policy checked against the 0.49 GiB archive (1b)
- [ ] 25.09: `scripts/bench_8core.sh` on the 8-core machine (no Docker for agents), its folder
  committed; the ride cache to P4 / an agent, then `scripts/regression_gate.py` with the ride and
  set F for the two opt-in flags (action 11)
- [ ] 25.09: `private/` team data, photos, the private deck
- [ ] 25.09–26.09: the branch → `main` PR reviewed by the lane owners (P2, P3, P4) and merged (3b)
- [ ] 26.09: go / no-go taken by 20:00 (action 11); voice-over recorded · 27.09: `v1.0-rc1`
  pushed, its archive exported (size and sha256 noted), loaded once on a second machine
- [ ] 28.09: clean team-machine dry run **offline** (network disconnected, from the archive),
  host console, remote demo · 29.09: `v1.0-final`, its archive + sha256, release, upload by 18:00
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
  25.09: PR #11 (the `main` fix) went in without a review, 3.5 min after opening, protection still
  off; the branch → `main` PR (action 3b) is the first to follow the rule.
- No edits in another lane's files without the owner's OK (§8). Contract changes (§7): `[contract]`
  in the PR title and a heads-up to the consumers; add, never rename or remove.
- Freeze: detector and config **26.09 20:00**, docs **27.09 20:00**; from 28.09 blockers only.
- Detector / config gate: `python scripts/regression_gate.py --baseline
  docs/evidence/results/regression_baseline_2026-09-25.json` exits 0 on the change. Every gated
  metric must be identical or better on the six recordings and set O, and also on the ride and
  set F straight wherever `/data/cache/new_data` exists. Otherwise the PR names each worse metric
  with `--allow` and the captain accepts the trade-off, or it is "tried, not shipped"
  (EXPERIMENTS §7). The JSON and the table go into the PR. A change meant to move the numbers
  commits a new baseline. Nothing in the gate needs the organizers' stand.
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
| `docker/`, `docker-compose.yml`, `ros2_ws/src/resense_ros/` (except `rviz/`), `scripts/*.sh` (except `build_native.sh`), `scripts/{check_dry_run,make_smoke_bag,cache_to_bag,bench_node_path,bench_summary,check_no_network}.py` | P1 |
| `README.md`, `CHANGELOG.md`, `docs/{README,ARCHITECTURE,ALGORITHM,EVALUATION,SUBMISSION,SENSOR,PLAN,CAPTAIN,QUESTIONS,SCORECARD}.md`, `docs/archive/`, team notes in `docs/organizers/` | P1 (P3 reviews ALGORITHM) |
| `.github/workflows/ci.yml` | P4 `pytest`, P2 `web`, P1 the other jobs |
| `configs/default.yaml` | P3 values, P1 structure |
| `resense/{track,gauge,clustering,tracking,accumulate,egomotion,lowobj,calibration,health,config,detector,_native}.py`, `native/`, `setup.py`, `scripts/build_native.sh`, `tests/{test_algorithm,test_lowobj_near,test_native,test_cpu_savings,test_late_candidates}.py` | P3 |
| `resense/{frame,pointcloud,sensor}.py` | P1 decoding / P3 geometry |
| `resense/{synthetic,metrics,io,cli}.py`, other `tests/` (`test_node.py`: P1), `labels/`, `scripts/{cache_frames,eval_real,far_range_eval,compare_setf,label_fake_objects,score_fake_objects,short_signature_experiment,unpack_dataset,start_offsets,regression_gate}.py`, `scripts/speed_*.py` (with `tests/test_speed_eval_helpers.py`), `tests/test_regression_gate.py`, `docs/{P4_AUDIT,DATASET}.md`, `docs/evidence/results/` | P4 |
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
| 25.09 | the regression gate is the single results check: `scripts/regression_gate.py` against `regression_baseline_2026-09-25.json` (six recordings + set O; ride and set F where cached); a change that moves the numbers commits a new baseline | EVALUATION §3 step 6, §6 |
| 25.09 | DBSCAN on cKDTree ships (exact scikit-learn labels, per-frame output identical, gate PASS on the merged code); the forward crop and the bed-height reuse do not (no gain on the native path) | ARCHITECTURE "Native kernels", EXPERIMENTS §7 |
| 25.09 | the long overhead rule and the short-signature rule are merged **off** (`cluster.floating_long_min_length`, `cluster.short_signature_max_length` = 0); go / no-go 26.09 20:00 after the ride and set F on the 8-core machine | EXPERIMENTS §1f, action 11 |
| 25.09 | the node keeps its UDP-only Fast DDS profile: stock Fast DDS clients (shared memory on) reach it over UDP, proven in CI with a uid-1000 player and listener | C4, `scripts/console_test.sh` |
| 25.09 | the public deck keeps the 17 team placeholders by design; personal data only in the private `--team` build | PRESENTATION, action 8 |
| 25.09 | upload by links, no file-size limit (organizers): the form gets the repository at the release tag with its commit hash, the tag's GitHub release page with `resense-image-<tag>.tar.gz` + `.sha256` (attached by `.github/workflows/release.yml` on a `v*` tag push, being added; by hand otherwise), the video and the presentation; every link opened logged out and the archive loaded on a second machine before submitting | [`organizers/answers.md`](organizers/answers.md) §8, SUBMISSION "Upload", action 1b |
| 25.09 | intermediate submission not held as a separate upload: the organizers' timeline has no such stage; the §7.1 content is in the repository | C14, SUBMISSION "Intermediate submission" |
| 25.09 | bed object: a 30 × 30 × 10 cm object on the bed between the rails is **not an obstacle** (organizers' answer to Q3) → the envelope-floor policy of 24.09 is the organizers'; the near-bed path (`lowobj.near_enabled`) stays off for good, its ride / set F re-run is dropped | [`organizers/answers.md`](organizers/answers.md) §8, ALGORITHM §3.3b |

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

State on 25.09 ~08:35 UTC: 1 done (the gate is the single results check, §3 action 4); 2 open
(the ride cache, action 3); 3 in progress (both rules measured and merged off, action 11); 4 done
by an agent for P4 without the ride (action 6); 5 in progress (video script, deck done; the UI kept
changing on 24.09); 6 partly (stock-DDS CI step, bench kit; Q1–Q3, photos, timing run open); 7 not
done (0 GitHub issues: §3 is the tracker); 8 done.
