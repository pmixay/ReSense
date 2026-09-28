# Web dashboard

A single static page (`web/index.html`, Russian interface, no build step, no server) that shows
what the detector decided, frame by frame: the decision banner, a driver's-eye cab view with the
envelope and the obstacle boxes, a top-down plan, a distance timeline, health and node statistics,
a run summary and the alarm log.

Open `web/index.html` from a checkout of the repository in a browser; there is nothing to install
or build.

## What it can and cannot do

| you want to… | possible? | how |
|---|---|---|
| see the interface without any data | yes | press **Демо**: a 60-frame synthetic approach (UI demonstration, not an evaluation result) |
| replay results of a real run | yes | **Выбрать файл** (or drop the file on the page): a `results.jsonl` or a `/resense/status` capture |
| watch a running node live | yes, if the browser can reach a rosbridge server | enter `ws://<host>:9090`, press **Подключить** |
| **upload a ROS 2 bag and have it processed** | **no** | the page has no backend; the detector runs in Python/C++ in the Docker image, not in the browser. Process the bag first (below), then replay the result |
| download a run report | yes, for a loaded replay | section *Сводка запуска* → **Скачать отчёт** (`resense_run_report.json`) |

The page only ever reads **results** (one JSON `FrameResult` per frame). No point cloud is sent to
the browser, and nothing you load leaves your browser.

## Try it with real recordings

The repository carries two node status streams recorded in CI from the organizers' original bags
with the supported playback settings (`--read-ahead-queue-size 10`), gzip-compressed:

* [`doubleT_obstacle_status.jsonl.gz`](https://github.com/pmixay/ReSense/blob/main/docs/evidence/p1_p2_supported_playback_2026-09-27/cached_bags_run_36319767736/doubleT_obstacle_status.jsonl.gz)
  — a person crossing the track, then an object on the rail, ≈ 55–57 m ahead (STOP)
* [`roundT_doubleT_status.jsonl.gz`](https://github.com/pmixay/ReSense/blob/main/docs/evidence/p1_p2_supported_playback_2026-09-27/cached_bags_run_36319767736/roundT_doubleT_status.jsonl.gz)
  — an obstacle-free run from a round into a double-track tunnel

Download one, `gunzip` it, open the dashboard, press **Выбрать файл** and pick the `.jsonl`. Their
provenance: [the run's README](https://github.com/pmixay/ReSense/blob/main/docs/evidence/p1_p2_supported_playback_2026-09-27/cached_bags_run_36319767736/README.md).

## Replay your own bag

1. Produce results, either offline (no ROS needed):

   ```bash
   pip install -e ".[dev]"
   resense run --bag /data/for_hackathon/doubleT_obstacle --out results.jsonl
   ```

   or by capturing the node's status while the bag plays:

   ```bash
   ros2 topic echo /resense/status --field data > status.jsonl    # the command scripts/dry_run.sh uses
   ```

   (`scripts/dry_run.sh <bag>` writes this capture for you to `out/dry_run/status.jsonl`.)
2. Open the dashboard and load the file. Non-JSON lines (such as the `---` separators of
   `ros2 topic echo`) and blank lines are skipped; malformed records are ignored rather than shown.

Playback: space = play / pause, ← → = step, a seek slider, speed 0.25×–10×, loop. The timeline's
x-axis is the recording's time.

## Live mode

The dashboard subscribes to `/resense/status` through **rosbridge**, which is not in the ReSense
image:

```bash
sudo apt install ros-humble-rosbridge-suite
ros2 launch rosbridge_server rosbridge_websocket_launch.xml     # on the machine running the node
```

Then enter `ws://<host>:9090` and press **Подключить**. Open the page as a local file: a copy
served over HTTPS cannot open an unencrypted `ws://` connection to another machine (mixed content)
unless rosbridge is behind `wss://`. On a machine without internet use [Foxglove](foxglove.md),
whose bridge is in the image.

Live mode requires synchronized UTC clocks on the node and the browser. The panels stay covered
until the first current result, and again on disconnect or when a result expires; invalid or
decision-less data can never turn the banner green.

## Details

Widget-by-widget description, the headless checks (`python -m pytest -q web/demo`) and the video
recipes: [`web/README.md`](https://github.com/pmixay/ReSense/blob/main/web/README.md).
