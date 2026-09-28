# ReSense

ReSense looks down the track ten times a second and tells a driverless metro train whether
something is inside its clearance envelope, and how far away it is. It was built for LCT 2026,
case 05, «Обнаружение посторонних объектов в тоннеле метро по данным 3D-лидара» (Moscow
Transport / Moscow Metro).

From each LiDAR point cloud it builds a model of the normal tunnel (track bed, rail heads, the
track axis and its curvature from the walls), cuts out the organizers' 2.1 × 3.0 m train
envelope along that axis, and reports every persistent object inside it: distance along the
track, lateral offset, size and confidence. No object classes or training labels are needed:
geometry decides, and a small learned model only delays a doubtful far `STOP` by a bounded amount.

This book is the **how-to**: getting the image, running it on a ROS 2 bag, reading the answer,
watching it in RViz, Foxglove or the browser dashboard, and working on the code. Design
rationale, measurements and team records stay in the repository documents it links to.

## What you get

| output | where |
|---|---|
| `GO` / `CAUTION` / `STOP` / `FAULT` | ROS 2 topic `/resense/decision` |
| distance to the obstacle along the track, m (−1: none) | `/resense/nearest_distance` |
| estimated monitored range, m | `/resense/clear_distance` |
| everything per frame as JSON (objects, track model, health, mount, timing, freshness) | `/resense/status` |
| boxes, corridor outline, corridor points | `/resense/detections`, `/resense/markers`, `/resense/corridor_points` |

## The shortest path

```bash
docker load -i resense-image-<version>.tar.gz     # or: docker build -t resense -f docker/Dockerfile .
scripts/play_bag.sh <bag directory>               # node + player + readout, prints "12.3 s  STOP  55.6 m"
```

Step-by-step: [Run on a bag](getting-started/run-on-a-bag.md). The jury's version in Russian:
[Кратко для жюри](getting-started/jury-quickstart-ru.md).

## Where things are

* Source code and every document: [github.com/pmixay/ReSense](https://github.com/pmixay/ReSense)
* The browser dashboard: `web/index.html` in the repository, opened locally in a browser (see
  [Web dashboard](visualisation/web-dashboard.md) for what it can and cannot do)
* Results, experiments and their dates:
  [`docs/EXPERIMENTS.md`](https://github.com/pmixay/ReSense/blob/main/docs/EXPERIMENTS.md) and the
  [README summary](https://github.com/pmixay/ReSense/blob/main/README.md#current-results)

> **Note.** Numbers (ranges, false alarms, timings) are deliberately not repeated in this book.
> They live in one place, `docs/EXPERIMENTS.md` and the README summary, with the date and the data
> each was measured on.
