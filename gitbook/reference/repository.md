# Repository map and documents

## Layout

| path | what |
|---|---|
| `resense/` | the core library (numpy / scipy / scikit-learn, no ROS): point-cloud decoding, mount calibration, track model, envelope corridor, low-object stage, clustering, tracking, health, detector, synthetic injection, metrics, the `resense` CLI |
| `native/` | optional C++ kernels for the per-frame hot spots; numpy fallback with identical output |
| `ros2_ws/src/resense_ros/` | the ROS 2 Humble node, launch file, parameter copy, RViz layout |
| `configs/default.yaml` | every detector parameter |
| `docker/`, `docker-compose.yml` | the image and the compose services |
| `scripts/` | build, run, dry run, export / load of the image archive, evaluation and the regression gate |
| `web/` | the browser dashboard, Foxglove layout, label tool and their headless checks |
| `tests/` | the test suite |
| `labels/` | labels of the real obstacles and of the organizers' synthetic objects |
| `docs/` | every document; the organizers' material in `docs/organizers/` |
| `gitbook/` | this book |

## Documents in the repository

| document | read it for |
|---|---|
| [README](https://github.com/pmixay/ReSense/blob/main/README.md) | the jury commands, current status and headline results with dates |
| [ARCHITECTURE](https://github.com/pmixay/ReSense/blob/main/docs/ARCHITECTURE.md) | components, data flow, timing budget, native kernels, offline deployment |
| [ALGORITHM](https://github.com/pmixay/ReSense/blob/main/docs/ALGORITHM.md) | the method stage by stage, decision rule, parameters, limitations |
| [EXPERIMENTS](https://github.com/pmixay/ReSense/blob/main/docs/EXPERIMENTS.md) | every measurement: range, latency, FPS, false alarms, hard cases, what did not work |
| [EVALUATION](https://github.com/pmixay/ReSense/blob/main/docs/EVALUATION.md) | the evaluation protocol and sets |
| [DATASET](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md), [SENSOR](https://github.com/pmixay/ReSense/blob/main/docs/SENSOR.md) | the recordings, formats, the Hesai Pandar128 |
| [DECISIONS](https://github.com/pmixay/ReSense/blob/main/docs/DECISIONS.md) | the key decisions on one page |
| [VM_GUIDE](https://github.com/pmixay/ReSense/blob/main/docs/VM_GUIDE.md) | clean-machine dry run, bench and offline rehearsal on a cloud VM |
| [CHANGELOG](https://github.com/pmixay/ReSense/blob/main/CHANGELOG.md) | what changed, per version and merge |
| [docs/README](https://github.com/pmixay/ReSense/blob/main/docs/README.md) | the index of every document, its purpose and owner |

The organizers' specification and their answers:
[`docs/organizers/`](https://github.com/pmixay/ReSense/tree/main/docs/organizers).
