# Submission Checklist

> **Purpose:** status of every deliverable the organizers ask for (spec §5, §7), the dry run and the
> upload procedure.
> **Audience:** team · **Owner:** P1 · **Language:** EN, cover message RU
> **Last verified:** 2026-09-25, `79109f5` (detector v0.6.3 with the long overhead rule on, node
> v0.6.4, package 1.0.0) · **Status:** current

Owner codes as in [`PLAN.md`](PLAN.md). Update this file in the PR that completes an item.

## Intermediate submission (spec §7.1)

**Status (25.09): resolved — not held as a separate upload.** The organizers' timeline has no
intermediate upload stage; its stages are, verbatim
([`organizers/README_organizers.md`](organizers/README_organizers.md) "Ключевые этапы конкурса"):
«Приём заявок | до 14 сентября», «Разработка решений | 15–29 сентября», «Техническая экспертиза |
30 сентября – 14 октября», «Презентация проектов | 23 октября», «Церемония награждения | 30
октября». Spec §7.1 («7.1. Промежуточная сдача», «К промежуточной сдаче необходимо
предоставить: …») lists what an intermediate package holds but gives no date, form or place.
Decision (25.09, [`CAPTAIN.md`](CAPTAIN.md) C14): no separate intermediate upload in the
organizers' timeline; the §7.1 content (Dockerfile, prototype, description, mini-demo, first
experiments) is in the repository (the table below) and is part of the final upload. No
`v0.1-intermediate` tag is made.

| # | required | where | owner | status |
|---|---|---|---|---|
| 1 | Dockerfile and/or image with everything needed | [`docker/Dockerfile`](../docker/Dockerfile), `scripts/build.sh` | P1 | done (runtime image; `WITH_TOOLS=1` adds tests) |
| 2 | working prototype of the algorithm | `resense/`, `ros2_ws/` | all | done (v0 at the intermediate; now detector v0.6.3, node v0.6.4) |
| 3 | short description of the chosen approach | [`README.md`](../README.md) intro, [`ALGORITHM.md`](ALGORITHM.md) §1–4 | P1 | done |
| 4 | minimal demonstration on the provided data | `scripts/run_demo.sh doubleT_obstacle`; real renders in [`img/`](img/) (`hero_person.png` from the cab, `doubleT_obstacle_0024_v062.png` top / side view), videos in [`video/`](video/), dashboard (`web/index.html`, screenshots [`images/dashboard-stop.png`](images/dashboard-stop.png), [`images/dashboard-cab-real.png`](images/dashboard-cab-real.png)) | P1 / P2 | done offline on the real bag (v0.6.2), and in Docker with RViz on the real frames (23.09, [`video/docker_chain_rviz.mp4`](video/docker_chain_rviz.mp4)) |
| 5 | first experiment results | [`EXPERIMENTS.md`](EXPERIMENTS.md) | P3 / P4 | done, v0.3 |

Nothing is sent separately. The cover message drafted for an intermediate package (below; not sent
as one) is kept as the base of the final one: replace «промежуточная сдача» and the tag
`v0.1-intermediate` with `v1.0.0`, add step 1 `docker load -i resense-image-v1.0.0.tar.gz` and the
sha256 (see "Upload").

### Cover message (draft, Russian — the organizers' language; not sent, base of the final one)

> Команда «Молоток» (решение ReSense), кейс 05 («Обнаружение посторонних объектов в тоннеле метро
> по данным 3D-лидара») — промежуточная сдача.
> Репозиторий: https://github.com/pmixay/ReSense, тег `v0.1-intermediate` (коммит `<sha>`).
>
> 1. **Dockerfile** — `docker/Dockerfile`, сборка `./scripts/build.sh` (ROS 2 Humble, нода,
>    RViz, foxglove_bridge; зависимости ставятся при сборке образа). CI на каждом коммите
>    собирает образ, прогоняет тесты внутри него и сквозной прогон синтетического bag-файла
>    через ноду.
> 2. **Прототип** — пакет `resense` (Python: numpy / scipy / scikit-learn) и ROS 2-нода
>    `resense_ros`. Запуск: `./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle` (RViz)
>    или `./scripts/run_headless.sh …` (без X11); выход — флаг препятствия, расстояние,
>    `vision_msgs/Detection3DArray`, маркеры RViz, JSON-статус.
> 3. **Подход** (README, `docs/ALGORITHM.md`) — геометрическая модель «нормального тоннеля»:
>    самокалибровка по рельсам, ось пути и кривизна по стенам / рядам колонн, коридор габарита,
>    кластеризация с адаптацией к дальности, подтверждение по нескольким кадрам; дальнее
>    правило для высоких объектов (человек — ~148 м без датчика скорости, ~167 м с ним:
>    накопление кадров с компенсацией движения); автокалибровка крепления лидара. Без обучения
>    на размеченных объектах — обобщается на новые записи.
> 4. **Демонстрация** — человек, переходящий путь в `doubleT_obstacle`, обнаруживается на
>    55–57 м (`docs/img/hero_person.png`, видео `docs/video/doubleT_obstacle_cab.mp4`);
>    `scripts/dry_run.sh` воспроизводит это как автоматическую проверку.
> 5. **Эксперименты** — `docs/EXPERIMENTS.md`: дальность на синтетических препятствиях,
>    внесённых в реальные кадры трассировкой лучей; задержка и FPS; ложные срабатывания по типам
>    сцен (платформы, стрелки, гермозатворы) и что с ними сделано.
>
> Вопросы к организаторам отправлены отдельно (`docs/QUESTIONS.md`).

## Final submission (spec §7.2 and §5)

| # | required | where | owner | status |
|---|---|---|---|---|
| 1 | Docker container with everything needed; runs in the jury environment without manual dependency installation | `docker/`, `docker-compose.yml`; the stand has **no internet** ([`organizers/answers.md`](organizers/answers.md) §7), so the container goes as the image archive of row 17 | P1 | done; in CI on every push: `docker save` → `docker rmi` → `docker load` and the node with `--network none` (docker job), and the runtime archive loaded and both synthetic bags played through it on an internal network (`offline-build`, a gate since 25.09); re-verify offline on a clean machine on 28.09 |
| 2 | source code | this repository | all | ongoing |
| 3 | README: project description | [`README.md`](../README.md) | P1 | done |
| 4 | README: how to build the image | README "Кратко для жюри", "ROS 2 / Docker" | P1 | done |
| 5 | README: how to run | README "Кратко для жюри", "How a bag is processed", "Quick start" | P1 | done |
| 6 | README: how a bag is processed | README "How a bag is processed" (the organizers will play the bag from the console and asked for the pipeline to be described, 23.09: `ros2 bag play` → the node → the topics; the solution does not read bags; either topic / frame pair, one recording after another), [`ARCHITECTURE.md`](ARCHITECTURE.md) data flow | P1 | done (23.09) |
| 7 | README: parameters and configuration | README "Node parameters", "Parameters worth knowing", [`ALGORITHM.md`](ALGORITHM.md) §5, `configs/default.yaml` | P1 / P3 | done |
| 8 | architecture description (components, data flow) | [`ARCHITECTURE.md`](ARCHITECTURE.md) | P1 | done |
| 9 | algorithm description (problem, data, processing, decision, parameters, limitations) | [`ALGORITHM.md`](ALGORITHM.md) | P1, reviewed by P3 | done for v0.6 (mount calibration §2b, low objects §3.3b, far field §3.3c, decision / clear distance / health §4b, limitations §6) |
| 10 | experiment results (range, latency, FPS, false alarms, hard cases, improvement over time) | [`EXPERIMENTS.md`](EXPERIMENTS.md), protocol in [`EVALUATION.md`](EVALUATION.md), raw summaries in [`evidence/results/`](evidence/results/), labels in `labels/` | P3 / P4 | detector v0.6.3 (23.09; re-run on the current code on 24.09, identical on every frame) with the long overhead rule on since 25.09: all 13 759 frames of the organizer data at full rate for every change, with a leave-one-subset-out check and false alarms by the first processed frame (§0); ride tracks classified (`labels/new_data_objects.json`); long range on the moving ride (set F, §2d) and its paired audit ([`P4_AUDIT.md`](P4_AUDIT.md)); the organizers' synthetic-obstacle recording graded per object (set O, P4_AUDIT); mount calibration on re-mounted real frames (§6); learned second opinion (§8); clean timing (§3); since 25.09 the six recordings, set O, the ride and set F straight are re-checked by one command, `scripts/regression_gate.py` against [`evidence/results/regression_baseline_2026-09-25_ride.json`](evidence/results/regression_baseline_2026-09-25_ride.json); the two late rules were decided on the ride against pre-registered criteria (long overhead rule on: ride 47 → 46 events, five bags 20 → 14; short signatures off; EXPERIMENTS §1f, [`rules_decision_2026-09-25.json`](evidence/results/rules_decision_2026-09-25.json)); 8-core timing: the kit `scripts/bench_8core.sh` is ready, its run pending ([`CAPTAIN.md`](CAPTAIN.md) action 7; the i7-9700E stand is not available before submission, [`organizers/answers.md`](organizers/answers.md) §6) |
| 11 | video of the algorithm at work | [`video/resense_overview.mp4`](video/resense_overview.mp4): 2:50 overview on the script of PRESENTATION «Сценарий видео (2–3 мин)», 1920×1080 H.264, 25 fps, 20.6 MB, no audio track, Russian subtitles burned in (≤ 2 lines) and as [`video/resense_overview.ru.srt`](video/resense_overview.ru.srt), a chapter per block; built by `scripts/make_overview_video.py` (one table: sources, timings, cards, subtitles). Its sources in [`video/`](video/): `docker_chain_rviz.mp4` (69 s, node container + `ros2 bag play` as uid 1000 from another container + `/resense/decision`, sandbox, bag at 0.5×, EXPERIMENTS §3b), `doubleT_obstacle_cab.mp4` (the real bag from the cab: envelope, obstacle, STOP / distance, 20 s), `doubleT_obstacle_offline.mp4` (top and side view), `fake_objects_cab.mp4` (the organizers' 2 × 2 m box from the cab, GO → STOP at 98.0 m → 25 m, train 1.5–7.7 m/s, 20.5 s), `dashboard_doubleT_obstacle.mp4` (earlier UI, not used); recipes in `scripts/hero_view.py` and [`web/README.md`](../web/README.md) | P2 | done 25.09 (`798a28f`; closing card «релиз v1.0.0», `5a15c7c`): captioned, silent; its ride card still says 3.6 per km (47 events), the 24.09 figure: rebuild at the final consistency pass (CAPTAIN action 13); optional: the captain's voice-over muxed on without re-editing (PRESENTATION «Сборка ролика»); the upload form takes links: the file at the release tag ("Upload") |
| 12 | full demonstration on the control bag: `docker build → docker run → ros2 bag play → result` (on the stand, with no internet: `docker load` of row 17 instead of the build) | `scripts/build.sh`, `scripts/run_demo.sh`; the same chain on synthetic bags in CI (`scripts/smoke_test.sh`, `scripts/console_test.sh`; since 25.09 also after `docker load`, with no network, and with a stock Fast DDS player and listener, `PLAYER_DDS=stock`) | P1 | proven in CI on synthetic bags (since 21.09) and on the real frames in Docker, with RViz on screen (23.09, EXPERIMENTS §3b, `video/docker_chain_rviz.mp4`); left: the dry run with the original bags on a clean team machine (28.09; no run on the organizers' stand before submission, [`organizers/answers.md`](organizers/answers.md) §6) |
| 13 | presentation, slides 7–11 exactly per template | [`presentation/ReSense_LCT2026.pptx`](presentation/ReSense_LCT2026.pptx) (16 slides in the organizers' template, built by `scripts/build_deck.py`; LibreOffice PDF next to it), drafts, speaker text and the video script in [`PRESENTATION.md`](PRESENTATION.md) | P2 | rebuilt 25.09 (before the release tooling, the video and the 25.09 rule decision: it still says 289 tests and 47 ride events, now 347 and 46; rebuild at the final consistency pass, CAPTAIN action 13): the organizers' objects (slide 13), the anchored 154 m next to 150 m legacy in the same 5 pairs, «~210 м — предел отражений в тоннеле», new UI capture, C++ kernels / train speed / GPU; open: the personal data and photos on slides 2–3 (17 `<…>` placeholders in the public build by design; P1 builds the private deck with `--team`), two rehearsals |
| 14 | tests (spec §8.5) | `tests/` (347 tests: algorithm on the ray-cast tunnel, envelope and low objects, mount calibration and guards, the native kernels against their numpy code, the cKDTree DBSCAN against scikit-learn, the two 25.09 rules, the regression gate's rules, P4 placement, evaluation, the synthetic-obstacle labels and the speed-evaluation helpers, the release tooling (`tests/test_release.py`), the overview video's table and subtitles, the node's decision / fault / watchdog / input-switching logic against ROS stand-ins in `tests/test_node.py`) + `web/demo/` (11); CI jobs `pytest` (347, none skipped), `web`, `lint` (ruff), `params-in-sync`, `docker` (344 in the image, which has no `docs/`; the Docker job also plays synthetic bags through the node: the organizers' way with node and a uid-1000 player in separate containers, with a stock Fast DDS player and listener, and after `docker save` / `docker load` with no network), `offline-build` (the runtime archive: loaded, rebuilt offline from its cache, both synthetic bags played through the loaded runtime image on an internal network) | P4 / P1 / P2 | done (CI state: [`CAPTAIN.md`](CAPTAIN.md) C17) |
| 15 | input data description | [`DATASET.md`](DATASET.md) (the organizers' links: Google Drive bags, the Yandex Disk extended dataset and the synthetic-obstacle recording of 24.09, labelled in `labels/cloud_with_fake_obj.json`), sensor: [`SENSOR.md`](SENSOR.md) with the Hesai manual in [`sensor/`](sensor/); the test stand's driver / CUDA state in [`organizers/test_stand_software.md`](organizers/test_stand_software.md) | P4 / P1 | done |
| 16 | the organizers' answers applied (envelope 2.1 × 3.0 m, 30 × 30 × 10 cm, hanging cables, mount, object on the rail, decision output; 24.09: mounts as in the provided bags, switches) | [`organizers/answers.md`](organizers/answers.md), [`organizers/QA_session.md`](organizers/QA_session.md) (the Q&A of 22.09 and the facts that changed the code), [`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md); criteria judgement: [`SCORECARD.md`](SCORECARD.md) (24.09) | all | done (22.09; 24.09 answers recorded; 25.09: no stand access before submission, `organizers/answers.md` §6; no internet on the stand, §7) |
| 17 | **the image archive** (the stand has no internet, so `docker build` cannot run there): `resense-image-<tag>.tar.gz`, its `.sha256` and `SHA256SUMS`, linked from the upload form as assets of the tag's GitHub release, loaded with `docker load -i` | `.github/workflows/release.yml` (a pushed `v1.0.0-rcN` / `v1.0.0` tag; any other name publishes nothing), by hand `scripts/release.sh <tag>` in a clean clone of the tag (`PUBLISH=1` publishes); `scripts/verify_release.sh <tag>` downloads the asset and checks the sum; `scripts/load_image.sh`; README "Кратко для жюри" step 1 | P1 | tooling done 25.09; `release.yml` publishes the archive on the tag push after loading it back and playing both smoke bags through the loaded runtime image (internal network and `--net=host`); CI's `offline-build` does the load-and-play on every push (green since run 36122640174); runtime archive 521 317 060 bytes, 0.49 GiB at gzip -1, 1.34 GiB unpacked (run 36123184213, `79109f5`; the release uses gzip -6); the form takes links with no size limit ([`organizers/answers.md`](organizers/answers.md) §8): the upload gives the asset's link and its sha256. Releases: [`v1.0.0-rc1`](https://github.com/pmixay/ReSense/releases/tag/v1.0.0-rc1) (27.09) and [`v1.0.0`](https://github.com/pmixay/ReSense/releases/tag/v1.0.0) (29.09), neither pushed yet |

## Dry run (28.09)

On a team machine that has never built the project, with 8 cores for the latency and drop criteria
(the organizers give no access to their i7-9700E stand before submission,
[`organizers/answers.md`](organizers/answers.md) §6):

```bash
git clone <repo> && cd ReSense
./scripts/dry_run.sh /data/for_hackathon/doubleT_obstacle      # builds --no-cache, plays, checks, exits 0/1
SKIP_BUILD=1 ./scripts/dry_run.sh /data/for_hackathon/roundT_doubleT --expect-clear --max-alarm-frames 2
SKIP_BUILD=1 ./scripts/bench_8core.sh /data/for_hackathon/doubleT_obstacle /data/for_hackathon/roundT_doubleT
#   timing evidence (native + numpy), console tests (image and stock Fast DDS), docker stats
#   -> docs/evidence/bench_<date>/ (commit it as written)
./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle     # RViz shows OBSTACLE ~55 m (needs X11)
RVIZ=0 ./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle   # the same over ssh
```

**Offline, as on the stand** (no internet there, [`organizers/answers.md`](organizers/answers.md)
§7): the archive is made where there is internet; the dry-run machine gets a clone of the tag (for
the scripts), the archive and the bags, and its network is disconnected (cable out, Wi-Fi off)
before the load:

```bash
# on a machine with internet: the release asset into dist/, sha256 checked (no Docker needed)
git clone --branch v1.0.0-rc1 <repo> && cd ReSense && scripts/verify_release.sh v1.0.0-rc1
#   (no release yet: VERSION=v1.0.0-rc1 ./scripts/export_image.sh in the same clean clone)
# copy dist/resense-image-v1.0.0-rc1.tar.gz and its .sha256 to the dry-run machine; disconnect it
A=dist/resense-image-v1.0.0-rc1.tar.gz; B=/data/for_hackathon
IMAGE_TAR=$A OFFLINE=1 ./scripts/dry_run.sh $B/doubleT_obstacle
SKIP_BUILD=1 OFFLINE=1 ./scripts/dry_run.sh $B/roundT_doubleT --expect-clear --max-alarm-frames 2
# then the jury's own commands by hand: README "Кратко для жюри" 1-5, the player from a normal
# user's console, still without network
```

`IMAGE_TAR` makes `dry_run.sh` load the archive (`scripts/load_image.sh`: sha256, `docker load`, a
check with `--network none`) instead of building; `OFFLINE=1` runs node, player and recorder in a
container with `--network none` (loopback only), so a PASS shows that nothing is fetched at run
time even if the host were still connected; it refuses to build. The pass criteria below are the
same, except that the image is loaded instead of built.

Pass criteria, all asserted by `dry_run.sh` (it exits non-zero otherwise): the image builds from
scratch with no manual steps, the node starts on the default command, the person in
`doubleT_obstacle` is reported in 50–62 m for at least 3 frames, p95 of decode + detect stays
≤ 100 ms and no input frame is dropped at rate 1.0 after the first 5 s (`--settle-s`: the player
preloads the bag and sends its first seconds back to back; since v0.6.4 the node works through
that burst one frame every 0.3 s of recording, so frames in between are skipped). `--expect-clear`
on an empty bag is the false-alarm half of the same check (`roundT_doubleT` has 2 known alarm
frames at 128–130 m, hence `--max-alarm-frames 2`). Thresholds are arguments of
`scripts/check_dry_run.py`; raw capture: `out/dry_run/status.jsonl`, `node.log`.

**Rehearsed on 23.09 in the sandbox** (Docker, 4 vCPU; bags rebuilt from the frame cache;
EXPERIMENTS §3b, raw in [`evidence/docker_2026-09-23/`](evidence/docker_2026-09-23/)): build,
default command, both topic / frame pairs, two recordings into one node, the player in another
container as expected; `roundT_doubleT` PASS (237 of 252 frames, 10 fps, p95 76 ms, its 2 known
alarm frames; a run gives 1–4 depending on the first processed frame, EXPERIMENTS §0);
`doubleT_obstacle` person and object at 55.9–56.6 m, but at 360° the sandbox is at the frame period
(7–10 fps, p95 112–130 ms), so the latency and drop criteria are judged on the team's 8-core
machine: teams cannot test on the organizers' stand (i7-9700E) before the upload (organizers,
25.09). Two transport bugs found and fixed: a best-effort input lost 196 of 201 clouds
(`input_reliability: auto`), and a normal user's player could not reach the root node through
shared memory (DDS over UDP). On the 8-core machine, play the bag from a normal user's console as
the organizers will, with a stock ROS 2 install if there is one (`PLAYER_DDS=stock
scripts/console_test.sh` does the same with containers, and CI runs it on every push).
Expect `FAULT` / `NO_INPUT` while the player preloads the recording (2.6–4 s for 1.9 GB in the
page cache, longer from a slow disk), then the first `STOP` on `doubleT_obstacle` 1.3–1.6 s into
the recording (v0.6.4). The RViz run stays in the procedure because the jury sees it, but it does
not decide whether the dry run passed.

## Upload

Deadline 29.09 23:59; target 18:00; the tags and times are in [`CAPTAIN.md`](CAPTAIN.md) §5. The
i.moscow form takes **links** and has **no file-size limit** (organizers, 25.09,
[`organizers/answers.md`](organizers/answers.md) §8): nothing is attached as a file. Pushing the
tag `v1.0.0` runs `.github/workflows/release.yml`, which publishes the release
https://github.com/pmixay/ReSense/releases/tag/v1.0.0 with `resense-image-v1.0.0.tar.gz`, its
`.sha256` and `SHA256SUMS` (the rc1 rehearsal: `v1.0.0-rc1`, a pre-release, 27.09). Links to type
(`<sha>` = `git rev-list -n 1 v1.0.0`):

| # | item | link to type | made by |
|---|---|---|---|
| 1 | the repository at the release tag, with its commit hash | `https://github.com/pmixay/ReSense/tree/v1.0.0` and «коммит `<sha>`» | the tag pushed on 29.09 (CAPTAIN §5) |
| 2 | **the image archive** (row 17; the stand has no internet, so this is what the jury runs, not an extra) | `https://github.com/pmixay/ReSense/releases/download/v1.0.0/resense-image-v1.0.0.tar.gz` (the release page `https://github.com/pmixay/ReSense/releases/tag/v1.0.0` also carries the `.sha256` and `SHA256SUMS`); the sha256 value, from the release notes, typed next to the link | `release.yml` on the tag push; if it did not run or failed: `scripts/release.sh v1.0.0` in a clean clone of the tag (Docker and internet), then `PUBLISH=1 scripts/release.sh v1.0.0` (Yandex Disk only as a second mirror) |
| 3 | the video | `https://github.com/pmixay/ReSense/blob/v1.0.0/docs/video/resense_overview.mp4` (2:50, Russian subtitles, no sound), or a video-hosting link | done 25.09 (row 11); a voice-over is optional |
| 4 | the presentation | to be filled later: the private `--team` build (row 13) carries the team's personal data, so it goes by a link that opens without a sign-in but is not in the public repository (e.g. Yandex Disk); the public build is `docs/presentation/ReSense_LCT2026.pptx` / `.pdf` at the tag | P2, P1 (row 13, CAPTAIN action 8) |

If the form has a description field, it takes the cover message (above, adapted) with the README
section list of the final submission, step 1 as `docker load -i resense-image-v1.0.0.tar.gz`, the
sha256 and the line «Видео (2:50, субтитры на русском):
https://github.com/pmixay/ReSense/blob/v1.0.0/docs/video/resense_overview.mp4». The archive is gzip
because `docker load` reads it on any Docker version (zstd would be ~10–20 % smaller but is not
read everywhere); its size and sha256 are in the release notes and the job summary.

**Check before submitting** (29.09, before 16:00; CAPTAIN §5):

1. open every link in a private browser window, **logged out** of GitHub and Yandex: the
   repository at the tag, the release page, the assets (each downloads), the video (plays), the
   presentation (opens); a link that asks for a sign-in is a failed link (a private repository or
   release is invisible to the jury);
2. the commit hash typed in the form equals `git rev-list -n 1 v1.0.0`, and the tag's `release`
   and `ci` runs are green;
3. on a second machine: `EXPECT_SHA256=<the sum typed in the form> scripts/verify_release.sh
   v1.0.0` (downloads the assets logged out into `dist/` and checks the `.sha256`, `SHA256SUMS`
   and the typed sum), then `./scripts/load_image.sh dist/resense-image-v1.0.0.tar.gz` (sum,
   `docker load`, a run with `--network none`).
