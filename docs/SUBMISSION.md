# Submission checklist

Live status of every deliverable the organizers ask for (spec §5 and §7). Owner codes as in
[`PLAN.md`](PLAN.md). Update this file in the PR that completes an item.

## Intermediate submission (spec §7.1)

| # | required | where | owner | status |
|---|---|---|---|---|
| 1 | Dockerfile and/or image with everything needed | [`docker/Dockerfile`](../docker/Dockerfile), `scripts/build.sh` | P1 | done (runtime image; `WITH_TOOLS=1` adds tests) |
| 2 | working prototype of the algorithm | `resense/`, `ros2_ws/` | all | done (v0 at the intermediate; v0.6.3 now) |
| 3 | short description of the chosen approach | [`README.md`](../README.md) intro, [`ALGORITHM.md`](ALGORITHM.md) §1–4 | P1 | done |
| 4 | minimal demonstration on the provided data | `scripts/run_demo.sh doubleT_obstacle`; real renders in [`img/`](img/) (`hero_person.png` from the cab, `doubleT_obstacle_0024_v062.png` top / side view), videos in [`video/`](video/), dashboard replay (`web/index.html`, screenshot `img/dashboard_doubleT_obstacle.png`) | P1 / P2 | done offline on the real bag (v0.6.2), and in Docker with RViz on the real frames (23.09, [`video/docker_chain_rviz.mp4`](video/docker_chain_rviz.mp4)) |
| 5 | first experiment results | [`EXPERIMENTS.md`](EXPERIMENTS.md) | P3 / P4 | done, v0.3 |

Package to send: link to the repository at a tagged commit (`v0.1-intermediate`), plus the
five rows above quoted in the cover message. On the day: `git tag -a v0.1-intermediate -m
"intermediate submission" && git push origin v0.1-intermediate`, then send the text below with
the commit hash filled in (the intermediate deadline, the form of the final package and the
stand procedure are the team's own to settle — not organizer questions, `organizers/answers.md` §3).

### Cover message (draft, Russian — the organizers' language)

> Команда ReSense, кейс 05 («Обнаружение посторонних объектов в тоннеле метро по данным
> 3D-лидара») — промежуточная сдача.
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
>    на размеченных объектах —
>    обобщается на новые записи.
> 4. **Демонстрация** — человек, переходящий путь в `doubleT_obstacle`, обнаруживается на
>    55–57 м (`docs/img/hero_person.png`, видео `docs/video/doubleT_obstacle_cab.mp4`); `scripts/dry_run.sh` воспроизводит это как
>    автоматическую проверку.
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
| 4 | README: how to build the image | README "ROS 2 / Docker" | P1 | done |
| 5 | README: how to run | README "ROS 2 / Docker", "Quick start" | P1 | done |
| 6 | README: how a bag is processed | README "How a bag is processed" (the organizers will play the bag from the console and asked for the pipeline to be described, 23.09: `ros2 bag play` → the node → the topics; the solution does not read bags; either topic / frame pair, one recording after another), [`ARCHITECTURE.md`](ARCHITECTURE.md) data flow | P1 | done (23.09) |
| 7 | README: parameters and configuration | README "Parameters worth knowing", [`ALGORITHM.md`](ALGORITHM.md) §5, `configs/default.yaml` | P1 / P3 | done |
| 8 | architecture description (components, data flow) | [`ARCHITECTURE.md`](ARCHITECTURE.md) | P1 | done |
| 9 | algorithm description (problem, data, processing, decision, parameters, limitations) | [`ALGORITHM.md`](ALGORITHM.md) | P1, reviewed by P3 | done for v0.6 (mount calibration §2b, low objects §3.3b, far field §3.3c, decision / clear distance / health §4b, limitations §6) |
| 10 | experiment results (range, latency, FPS, false alarms, hard cases, improvement over time) | [`EXPERIMENTS.md`](EXPERIMENTS.md) (full-rate real-data numbers of v0.3 → v0.5, causes of false alarms, real labels, synthetic-on-real recall), protocol in [`EVALUATION.md`](EVALUATION.md), raw files `experiments_*.json`, labels in `labels/` | P3 / P4 | v0.6.3 (23.09, re-run on the current code on 24.09: identical on every frame): every frame of all organizer data run at full rate for every change (13 759 frames: six bags + the 20-minute ride, EXPERIMENTS §0 / §0a / §1d) with a leave-one-subset-out consistency check and false alarms by the first processed frame (§0), ride tracks classified and person-like tracks checked by eye (`labels/new_data_objects.json`), long range on the moving ride (set F, §2d), mount calibration on rotated real frames (§6), learned second-opinion experiment (§8), clean timing (§3); i7 bench timing pending |
| 11 | video of the algorithm at work | [`video/doubleT_obstacle_cab.mp4`](video/doubleT_obstacle_cab.mp4) (the real bag from the cab: envelope, obstacle, STOP / distance, v0.6.2, 20 s), [`video/doubleT_obstacle_offline.mp4`](video/doubleT_obstacle_offline.mp4) (top and side view) and [`video/dashboard_doubleT_obstacle.mp4`](video/dashboard_doubleT_obstacle.mp4) (dashboard replay); **the Docker chain with RViz**: [`video/docker_chain_rviz.mp4`](video/docker_chain_rviz.mp4) (69 s, node container + `ros2 bag play` as uid 1000 from another container + `/resense/decision`, sandbox, bag at 0.5×, EXPERIMENTS.md §3b); recipes in `scripts/hero_view.py` and [`web/README.md`](../web/README.md) | P2 | done on real data (v0.6.2), including the Docker chain on screen |
| 12 | full demonstration on the control bag: `docker build → docker run → ros2 bag play → result` (rehearsed on the real frames in Docker on 23.09, EXPERIMENTS.md §3b) | `scripts/build.sh`, `scripts/run_demo.sh`; same chain on a synthetic bag in CI (`scripts/smoke_test.sh`) | P1 | container chain proven in CI on synthetic bags (21.09) and on the real frames in Docker, with RViz on screen (23.09, EXPERIMENTS.md §3b, `video/docker_chain_rviz.mp4`); the run on the i7 stand is left |
| 13 | presentation, slides 7–11 exactly per template | [`presentation/ReSense_LCT2026.pptx`](presentation/ReSense_LCT2026.pptx) (15 slides in the organizers' template, built by `scripts/build_deck.py`; PDF next to it), drafts and speaker text in [`PRESENTATION.md`](PRESENTATION.md) | P2 | done; the captain fills the `<…>` personal data and the photos on slides 2–4 |
| 14 | tests (spec §8.5) | `tests/` (198 tests: algorithm on the ray-cast tunnel, envelope and low objects, mount calibration and guards, the node's decision / fault / watchdog / input-switching logic against ROS stand-ins in `tests/test_node.py`), `web/demo/`, CI (`pytest`, `lint` (ruff), `web` and Docker jobs; the Docker job also plays synthetic bags through the node, the second time the organizers' way: node and a uid-1000 player in separate containers) | P4 / P1 / P2 | done |
| 15 | input data description | [`DATASET.md`](DATASET.md) (both organizer links: Google Drive bags and the Yandex Disk extended dataset), sensor: [`SENSOR.md`](SENSOR.md) with the Hesai manual in [`sensor/`](sensor/); the test stand's driver / CUDA state in [`organizers/test_stand_software.md`](organizers/test_stand_software.md) | P4 / P1 | done |
| 16 | the organizers' Q&A answers applied (envelope 2.1 × 3.0 m, 30 × 30 × 10 cm, hanging cables, variable mount, object on the rail, decision output) | [`organizers/QA_session.md`](organizers/QA_session.md) (transcript and the facts that changed the code), [`SCORECARD.md`](SCORECARD.md) (independent review against the criteria, 24.09) | all | done (22.09) |

## Dry run (28.09)

On a machine that has never built the project:

```bash
git clone <repo> && cd ReSense
./scripts/dry_run.sh /data/for_hackathon/doubleT_obstacle      # builds --no-cache, plays, checks, exits 0/1
SKIP_BUILD=1 ./scripts/dry_run.sh /data/for_hackathon/roundT_doubleT --expect-clear --max-alarm-frames 2
./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle     # RViz shows OBSTACLE ~55 m (needs X11)
RVIZ=0 ./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle   # the same over ssh
```

Pass criteria, all asserted by `dry_run.sh` (it exits non-zero otherwise): the image builds
from scratch with no manual steps, the node starts on the default command, the person in
`doubleT_obstacle` is reported in 50–62 m for at least 3 frames, p95 of decode + detect stays
≤ 100 ms and no input frame is dropped at rate 1.0 after the first 5 s (`--settle-s`: the first
2–4 s of a played bag are lost to the DDS start-up, whatever the node does). `--expect-clear` on an empty bag is the
false-alarm half of the same check (`roundT_doubleT` has 2 known alarm frames at 128–130 m in
v0.6.3, hence `--max-alarm-frames 2`). Raw capture: `out/dry_run/status.jsonl`, `node.log`.

**Rehearsed on 23.09 in the development sandbox** (Docker, 4 vCPU; recordings rebuilt from the
frame cache; EXPERIMENTS.md §3b): build, default command, both topic / frame pairs, two
recordings into one running node, the player in a separate container — all as expected; the
person and the object at 55.9–56.6 m; `roundT_doubleT` PASS (10 fps, p95 76 ms, its 2 known
frames; a run gives 1–4 alarm frames depending on the frame processing starts from,
EXPERIMENTS.md §0). The 360° `doubleT_obstacle` runs at 7–10 fps in steady state there (p95 112–130 ms), so the latency
and dropped-frame criteria are for the i7-9700E stand to confirm. The rehearsal and a review
found and fixed two transport bugs: a best-effort subscription lost 196 of 201 ten-megabyte
clouds (v0.6.2 `input_reliability: auto`), and a player run by a normal user could not reach
the root node through shared memory (the image now runs DDS over UDP). On the stand, play the
bag from a normal user's console as the organizers will — `scripts/console_test.sh` does the
same with containers (node, player as uid 1000, status recorder). Expect the first 2–4 s of a
played recording to be lost to the DDS start-up with 5–10 MB reliable samples (EXPERIMENTS.md §3b).

The RViz run stays in the procedure because the jury sees it, but it is no longer what decides
whether the dry run passed.

## Upload

Deadline 29.09 23:59; target 18:00. **Deferred (24.09): no release tag until development settles.** When it does: tag the commit `v1.0-final`, build the image from that tag,
save it with `docker save resense:latest | zstd > resense-v1.0.tar.zst` if the organizers want
an image file, and attach the README section list above in the cover message.
