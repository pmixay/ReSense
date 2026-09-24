# Submission Checklist

> **Purpose:** status of every deliverable the organizers ask for (spec §5, §7), the dry run and the
> upload procedure.
> **Audience:** team · **Owner:** P1 · **Language:** EN, cover message RU
> **Last verified:** 2026-09-24, `537e220` (detector v0.6.3, node v0.6.4) · **Status:** current

Owner codes as in [`PLAN.md`](PLAN.md). Update this file in the PR that completes an item.

## Intermediate submission (spec §7.1)

**Status (24.09): not recorded.** No tag `v0.1-intermediate` exists and nothing records that the
package was sent; the organizers' timeline
([`organizers/README_organizers.md`](organizers/README_organizers.md) "Ключевые этапы") has no
intermediate stage. P1 confirms and records the date here, or marks it "not held".

| # | required | where | owner | status |
|---|---|---|---|---|
| 1 | Dockerfile and/or image with everything needed | [`docker/Dockerfile`](../docker/Dockerfile), `scripts/build.sh` | P1 | done (runtime image; `WITH_TOOLS=1` adds tests) |
| 2 | working prototype of the algorithm | `resense/`, `ros2_ws/` | all | done (v0 at the intermediate; now detector v0.6.3, node v0.6.4) |
| 3 | short description of the chosen approach | [`README.md`](../README.md) intro, [`ALGORITHM.md`](ALGORITHM.md) §1–4 | P1 | done |
| 4 | minimal demonstration on the provided data | `scripts/run_demo.sh doubleT_obstacle`; real renders in [`img/`](img/) (`hero_person.png` from the cab, `doubleT_obstacle_0024_v062.png` top / side view), videos in [`video/`](video/), dashboard (`web/index.html`, screenshots [`images/dashboard-stop.png`](images/dashboard-stop.png), [`images/dashboard-cab-real.png`](images/dashboard-cab-real.png)) | P1 / P2 | done offline on the real bag (v0.6.2), and in Docker with RViz on the real frames (23.09, [`video/docker_chain_rviz.mp4`](video/docker_chain_rviz.mp4)) |
| 5 | first experiment results | [`EXPERIMENTS.md`](EXPERIMENTS.md) | P3 / P4 | done, v0.3 |

Package to send: link to the repository at a tagged commit (`v0.1-intermediate`), plus the five
rows above quoted in the cover message. On the day: `git tag -a v0.1-intermediate -m
"intermediate submission" && git push origin v0.1-intermediate`, then send the text below with
the commit hash filled in (the intermediate deadline, the form of the final package and the stand
procedure are the team's own to settle, not organizer questions: `organizers/answers.md` §4).

### Cover message (draft, Russian — the organizers' language)

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
| 1 | Docker container with everything needed; runs in the jury environment without manual dependency installation | `docker/`, `docker-compose.yml` | P1 | done; re-verify on a clean machine on 28.09 |
| 2 | source code | this repository | all | ongoing |
| 3 | README: project description | [`README.md`](../README.md) | P1 | done |
| 4 | README: how to build the image | README "Кратко для жюри", "ROS 2 / Docker" | P1 | done |
| 5 | README: how to run | README "Кратко для жюри", "How a bag is processed", "Quick start" | P1 | done |
| 6 | README: how a bag is processed | README "How a bag is processed" (the organizers will play the bag from the console and asked for the pipeline to be described, 23.09: `ros2 bag play` → the node → the topics; the solution does not read bags; either topic / frame pair, one recording after another), [`ARCHITECTURE.md`](ARCHITECTURE.md) data flow | P1 | done (23.09) |
| 7 | README: parameters and configuration | README "Node parameters", "Parameters worth knowing", [`ALGORITHM.md`](ALGORITHM.md) §5, `configs/default.yaml` | P1 / P3 | done |
| 8 | architecture description (components, data flow) | [`ARCHITECTURE.md`](ARCHITECTURE.md) | P1 | done |
| 9 | algorithm description (problem, data, processing, decision, parameters, limitations) | [`ALGORITHM.md`](ALGORITHM.md) | P1, reviewed by P3 | done for v0.6 (mount calibration §2b, low objects §3.3b, far field §3.3c, decision / clear distance / health §4b, limitations §6) |
| 10 | experiment results (range, latency, FPS, false alarms, hard cases, improvement over time) | [`EXPERIMENTS.md`](EXPERIMENTS.md), protocol in [`EVALUATION.md`](EVALUATION.md), raw summaries in [`evidence/results/`](evidence/results/), labels in `labels/` | P3 / P4 | v0.6.3 (23.09; re-run on the current code on 24.09, identical on every frame): all 13 759 frames of the organizer data at full rate for every change, with a leave-one-subset-out check and false alarms by the first processed frame (§0); ride tracks classified (`labels/new_data_objects.json`); long range on the moving ride (set F, §2d) and its paired audit ([`P4_AUDIT.md`](P4_AUDIT.md)); the organizers' synthetic-obstacle recording graded per object (set O, P4_AUDIT); mount calibration on re-mounted real frames (§6); learned second-opinion experiment (§8); clean timing (§3); i7 bench timing pending |
| 11 | video of the algorithm at work | [`video/`](video/): the Docker chain with RViz, `docker_chain_rviz.mp4` (69 s, node container + `ros2 bag play` as uid 1000 from another container + `/resense/decision`, sandbox, bag at 0.5×, EXPERIMENTS §3b); `doubleT_obstacle_cab.mp4` (the real bag from the cab: envelope, obstacle, STOP / distance, 20 s), `doubleT_obstacle_offline.mp4` (top and side view), `dashboard_doubleT_obstacle.mp4` (dashboard replay); recipes in `scripts/hero_view.py` and [`web/README.md`](../web/README.md) | P2 | done on real data (v0.6.2; the Docker chain v0.6.3); all four clips are silent, and the dashboard clip shows the earlier UI |
| 12 | full demonstration on the control bag: `docker build → docker run → ros2 bag play → result` | `scripts/build.sh`, `scripts/run_demo.sh`; the same chain on synthetic bags in CI (`scripts/smoke_test.sh`, `scripts/console_test.sh`) | P1 | proven in CI on synthetic bags (since 21.09) and on the real frames in Docker, with RViz on screen (23.09, EXPERIMENTS §3b, `video/docker_chain_rviz.mp4`); the run on the i7 stand is left |
| 13 | presentation, slides 7–11 exactly per template | [`presentation/ReSense_LCT2026.pptx`](presentation/ReSense_LCT2026.pptx) (15 slides in the organizers' template, built by `scripts/build_deck.py`; PDF next to it), drafts and speaker text in [`PRESENTATION.md`](PRESENTATION.md) | P2 | built; open: the personal data and photos on slides 2–4 (17 `<…>` placeholders, P1), the slides still print 199 tests (235 now), rebuild (P2) |
| 14 | tests (spec §8.5) | `tests/` (235 tests: algorithm on the ray-cast tunnel, envelope and low objects, mount calibration and guards, P4 placement, evaluation and the synthetic-obstacle labels, the node's decision / fault / watchdog / input-switching logic against ROS stand-ins in `tests/test_node.py`) + `web/demo/` (11); CI jobs `pytest`, `web`, `lint` (ruff), `params-in-sync`, `docker` (the Docker job also plays synthetic bags through the node, the second time the organizers' way: node and a uid-1000 player in separate containers) | P4 / P1 / P2 | done |
| 15 | input data description | [`DATASET.md`](DATASET.md) (the organizers' links: Google Drive bags, the Yandex Disk extended dataset and the synthetic-obstacle recording of 24.09, labelled in `labels/cloud_with_fake_obj.json`), sensor: [`SENSOR.md`](SENSOR.md) with the Hesai manual in [`sensor/`](sensor/); the test stand's driver / CUDA state in [`organizers/test_stand_software.md`](organizers/test_stand_software.md) | P4 / P1 | done |
| 16 | the organizers' answers applied (envelope 2.1 × 3.0 m, 30 × 30 × 10 cm, hanging cables, mount, object on the rail, decision output; 24.09: mounts as in the provided bags, switches) | [`organizers/answers.md`](organizers/answers.md), [`organizers/QA_session.md`](organizers/QA_session.md) (the Q&A of 22.09 and the facts that changed the code), [`organizers/mount_and_switch_qa.md`](organizers/mount_and_switch_qa.md); criteria judgement: [`SCORECARD.md`](SCORECARD.md) (24.09) | all | done (22.09; 24.09 answers recorded) |

## Dry run (28.09)

On a machine that has never built the project:

```bash
git clone <repo> && cd ReSense
./scripts/dry_run.sh /data/for_hackathon/doubleT_obstacle      # builds --no-cache, plays, checks, exits 0/1
SKIP_BUILD=1 ./scripts/dry_run.sh /data/for_hackathon/roundT_doubleT --expect-clear --max-alarm-frames 2
./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle     # RViz shows OBSTACLE ~55 m (needs X11)
RVIZ=0 ./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle   # the same over ssh
```

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
(7–10 fps, p95 112–130 ms), so the latency and drop criteria are for the i7-9700E stand. Two
transport bugs found and fixed: a best-effort input lost 196 of 201 clouds (`input_reliability:
auto`), and a normal user's player could not reach the root node through shared memory (DDS over
UDP). On the stand, play the bag from a normal user's console as the organizers will
(`scripts/console_test.sh` does the same with containers). Expect `FAULT` / `NO_INPUT` while the
player preloads the recording (2.6–4 s for 1.9 GB in the page cache, longer from a slow disk), then
the first `STOP` on `doubleT_obstacle` 1.3–1.6 s into the recording (v0.6.4). The RViz run stays in
the procedure because the jury sees it, but it does not decide whether the dry run passed.

## Upload

Deadline 29.09 23:59; target 18:00. **Deferred (24.09): no release tag until development
settles.** When it does: tag the commit `v1.0-final`, build the image from that tag, save it with
`docker save resense:latest | zstd > resense-v1.0.tar.zst` if the organizers want an image file,
and attach the README section list above in the cover message.
