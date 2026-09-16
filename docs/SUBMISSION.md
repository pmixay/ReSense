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
five rows above quoted in the cover message.

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
| 15 | input data description | [`DATASET.md`](DATASET.md) | P4 | done |

## Dry run (28.09)

On a machine that has never built the project:

```bash
git clone <repo> && cd ReSense
./scripts/build.sh                                        # must finish without manual steps
./scripts/run_demo.sh /data/for_hackathon/doubleT_obstacle # RViz shows OBSTACLE ~55 m
docker run --rm --net=host resense ros2 topic echo /resense/nearest_distance   # from a second terminal
docker run --rm --net=host resense ros2 topic echo /resense/fps                # ~10 fps expected
```

Pass criteria: the image builds from scratch, the node starts on the default command, the
person in `doubleT_obstacle` is reported at 55–57 m, `/resense/fps` stays at the bag rate and
the node log shows no dropped frames at rate 1.0.

## Upload

Deadline 29.09 23:59; target 18:00. Tag the commit `v1.0-final`, build the image from that tag,
save it with `docker save resense:latest | zstd > resense-v1.0.tar.zst` if the organizers want
an image file, and attach the README section list above in the cover message.
