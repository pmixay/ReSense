# Submission checklist

Live status of every deliverable the organizers ask for (spec §5 and §7). Owner codes as in
[`PLAN.md`](PLAN.md). Update this file in the PR that completes an item.

## Intermediate submission (spec §7.1)

| # | required | where | owner | status |
|---|---|---|---|---|
| 1 | Dockerfile and/or image with everything needed | [`docker/Dockerfile`](../docker/Dockerfile), `scripts/build.sh` | P1 | done (runtime image; `WITH_TOOLS=1` adds tests) |
| 2 | working prototype of the algorithm | `resense/`, `ros2_ws/` | all | done, v0 |
| 3 | short description of the chosen approach | [`README.md`](../README.md) intro, [`ALGORITHM.md`](ALGORITHM.md) §1–4 | P1 | done |
| 4 | minimal demonstration on the provided data | `scripts/run_demo.sh doubleT_obstacle`; renders in [`img/`](img/) | P1 / P2 | renders done; live demo recording pending (P2) |
| 5 | first experiment results | [`EXPERIMENTS.md`](EXPERIMENTS.md) | P3 / P4 | done, v0.3 |

Package to send: link to the repository at a tagged commit (`v0.1-intermediate`), plus the
five rows above quoted in the cover message. On the day: `git tag -a v0.1-intermediate -m
"intermediate submission" && git push origin v0.1-intermediate`, then send the text below with
the commit hash filled in (the intermediate deadline itself is question 6 in
[`QUESTIONS.md`](QUESTIONS.md)).

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
>    кластеризация с адаптацией к дальности, подтверждение по нескольким кадрам, накопление
>    кадров с компенсацией движения для 150+ м. Без обучения на размеченных объектах —
>    обобщается на новые записи.
> 4. **Демонстрация** — человек, переходящий путь в `doubleT_obstacle`, обнаруживается на
>    55–57 м (`docs/img/`, видео: `<ссылка>`); `scripts/dry_run.sh` воспроизводит это как
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
| 6 | README: how a bag is processed | README, [`ARCHITECTURE.md`](ARCHITECTURE.md) data flow | P1 | done |
| 7 | README: parameters and configuration | README "Parameters worth knowing", [`ALGORITHM.md`](ALGORITHM.md) §5, `configs/default.yaml` | P1 / P3 | done |
| 8 | architecture description (components, data flow) | [`ARCHITECTURE.md`](ARCHITECTURE.md) | P1 | done |
| 9 | algorithm description (problem, data, processing, decision, parameters, limitations) | [`ALGORITHM.md`](ALGORITHM.md) | P1, reviewed by P3 | done for v0; update with accumulation |
| 10 | experiment results (range, latency, FPS, false alarms, hard cases, improvement over time) | [`EXPERIMENTS.md`](EXPERIMENTS.md), protocol in [`EVALUATION.md`](EVALUATION.md) | P3 / P4 | v0 done; extended dataset and bench timing pending |
| 11 | video of the algorithm at work | `docs/video/` or a link in README | P2 | pending |
| 12 | full demonstration on the control bag: `docker build → docker run → ros2 bag play → result` | `scripts/build.sh`, `scripts/run_demo.sh` | P1 | pending dry run 28.09 |
| 13 | presentation, slides 7–11 exactly per template | [`PRESENTATION.md`](PRESENTATION.md), pptx | P2 | pending |
| 14 | tests (spec §8.5) | `tests/`, CI (`pytest` job, Docker job runs the suite inside the image) | P4 / P1 | done |
| 15 | input data description | [`DATASET.md`](DATASET.md), sensor: [`SENSOR.md`](SENSOR.md) | P4 / P1 | done |

## Dry run (28.09)

On a machine that has never built the project:

```bash
git clone <repo> && cd ReSense
./scripts/dry_run.sh /data/for_hackathon/doubleT_obstacle      # builds --no-cache, plays, checks, exits 0/1
SKIP_BUILD=1 ./scripts/dry_run.sh /data/for_hackathon/roundT_doubleT --expect-clear
./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle     # RViz shows OBSTACLE ~55 m (needs X11)
RVIZ=0 ./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle   # the same over ssh
```

Pass criteria, all asserted by `dry_run.sh` (it exits non-zero otherwise): the image builds
from scratch with no manual steps, the node starts on the default command, the person in
`doubleT_obstacle` is reported in 50–62 m for at least 3 frames, p95 of decode + detect stays
≤ 100 ms and no input frame is dropped at rate 1.0. `--expect-clear` on an empty bag is the
false-alarm half of the same check. Raw capture: `out/dry_run/status.jsonl`, `node.log`.

The RViz run stays in the procedure because the jury sees it, but it is no longer what decides
whether the dry run passed.

## Upload

Deadline 29.09 23:59; target 18:00. Tag the commit `v1.0-final`, build the image from that tag,
save it with `docker save resense:latest | zstd > resense-v1.0.tar.zst` if the organizers want
an image file, and attach the README section list above in the cover message.
