# Node input path and end-to-end latency through ROS (28.09)

What changed (P1, ROS node only; the sealed detector, its configuration and the image's layers
below the ROS package are unchanged):

* the input clouds are taken as serialized bytes (`raw_input`, default true) and read by
  `ros2_ws/src/resense_ros/resense_ros/fastcloud.py` instead of rclpy's message conversion;
* the decode gathers the kept points once by index (`fastcloud.decode`);
* the decision topics are published before the status JSON; the RViz markers and the corridor
  cloud are built only while something subscribes to them (corridor edges vectorised);
* the status `node` object also reports `decode_ms`, `detect_ms`, `cpu_cores` (node process CPU
  time per wall second over the last stats period, DDS threads included) and `rss_peak_mb`;
* `scripts/check_dry_run.py` prints the end-to-end latency of the current results
  (`freshness.source_age_s`: the player's publication of the input → the result, through DDS,
  the node's queue, decode and detection) and the node's CPU; `--max-p95-e2e` asserts it.

## The detector gets the same input

`fast_input.json` (`scripts/check_fast_input.py`, in the image): every message of both original
recordings read both ways, compared byte for byte (header, layout, payload, and the xyz /
intensity / ring arrays and counts the detector receives).

| recording | frames identical | rclpy conversion median / p95 | bytes parsed median / p95 | reference decode median | fast decode median |
|---|---|---|---|---|---|
| `doubleT_obstacle` (360°, 921 600 points) | **201 of 201** | 12.5 / 32.4 ms | 0.09 / 1.9 ms | 19.2 ms | 18.1 ms |
| `roundT_doubleT` (120°, 307 200 points) | **252 of 252** | 3.2 / 4.4 ms | 0.07 / 0.13 ms | 7.2 ms | 5.8 ms |

(Sequential read of the bag, each message decoded once; on repeated warm buffers the fast
decode measured 14.2 against 20.1 ms at 360°.)

## Before / after through ROS

`scripts/dry_run.sh` (node, player and recorder in one container, the recording in the page
cache, `--read-ahead-queue-size 10`), twice per image and recording, alternating. Machine: the
session's sandbox, 4 vCPU Intel Xeon @ 2.10 GHz, Docker 29.3.1. `base` = the image of `main`
at `8f23284` (tools build); `new` = the same build with this change. `ab/<run>.txt` is the
checker's output, `ab/<run>_status.jsonl.gz` the raw `/resense/status` capture,
`ab/<run>_node.log.gz` the node's log.

| `doubleT_obstacle` (360°) | base run 1 | base run 2 | new run 1 | new run 2 |
|---|---|---|---|---|
| decode + detect mean / p95 / max | 66 / 86 / 114 ms | 61 / 81 / 92 ms | 55 / 70 / 114 ms | 56 / 75 / 111 ms |
| **end to end, current results: median / p95 / max** | 88 / **120** / 181 ms | 84 / **127** / 171 ms | 74 / **93** / 150 ms | 73 / **97** / 153 ms |
| current (valid) results | 122 | 103 | 179 | 180 |
| start-up catch-up back on the newest frame | +7.9 s | +9.8 s | within 5 s | within 5 s |
| first STOP, distance | +0.8 s, 55.5–56.6 m | +0.8 s, 55.5–56.6 m | +1.2 s, 55.6–56.5 m | +0.8 s, 55.5–56.6 m |
| recording messages not processed after settle | 0 | 0 | 0 | 0 |
| node CPU median / max, peak RSS | – | – | 0.71 / 0.93 cores, 476 MB | 0.73 / 1.02 cores, 408 MB |

| `roundT_doubleT` (120°, clear) | base run 1 | base run 2 | new run 1 | new run 2 |
|---|---|---|---|---|
| decode + detect mean / p95 / max | 41 / 53 / 66 ms | 40 / 56 / 92 ms | 38 / 52 / 75 ms | 37 / 48 / 62 ms |
| **end to end, current results: median / p95 / max** | 59 / **76** / 153 ms | 46 / **68** / 118 ms | 45 / **61** / 96 ms | 44 / **57** / 92 ms |
| alarm frames | 0 | 0 | 0 | 0 |
| node CPU median / max, peak RSS | – | – | 0.47 / 0.52 cores, 127 MB | 0.45 / 0.50 cores, 128 MB |

**Cold disk** (`scripts/p1_cold_bag_test.sh` as CI runs it, the page cache dropped before each
recording, the same machine, the final build; `cold_local/`): 360° end to end median 74 / **p95
114** / max 181 ms over 182 current results, decode + detect p95 72 ms, node 0.63 cores, 0 recording
messages unprocessed after settle; 120° median 44 / **p95 59** / max 104 ms, 0.46 cores; the identity
check PASS on both. The player reading 240 MB/s of 360° recording from a cold disk delays the
DDS delivery (the node's own p95 is unchanged); the CI runner's cold baseline before the change was
p95 126 / 49 ms (run 36319767736).

Per stage in the new node (`node.decode_ms` / `node.detect_ms`, median / p95): 360° 19.3 / 27 and
33 / 45–51 ms; 120° 7.8–8.0 / 11 and 28 / 40–42 ms.

The end-to-end p95 at 360° moved under the 100 ms frame period on this 2.1 GHz 4-vCPU machine
(the organizers' i7-9700E has 8 faster cores; it was not available). The largest single gain is
the start-up: queued clouds that the catch-up skips no longer cost a conversion each, so the node
is current within the first 5 s instead of +7.9–9.8 s. The remaining time is the detector
(sealed) and the DDS transfer of the 24 MB cloud over UDP.

## Reproduce

```bash
scripts/fetch_cold_bags.sh /data/cold                       # the two original bags, checksums pinned
docker build -t resense:new --build-arg WITH_TOOLS=1 -f docker/Dockerfile .
SKIP_BUILD=1 IMAGE=resense:new scripts/dry_run.sh /data/cold/for_hackathon/doubleT_obstacle
SKIP_BUILD=1 IMAGE=resense:new scripts/dry_run.sh /data/cold/for_hackathon/roundT_doubleT --expect-clear --max-alarm-frames 2
docker run --rm -v /data/cold/for_hackathon:/data:ro resense:new \
  python3 /opt/resense/scripts/check_fast_input.py /data/doubleT_obstacle /data/roundT_doubleT
```

CI runs the last command and prints the end-to-end figures of both cold original-bag dry runs
(`scripts/p1_cold_bag_test.sh`, job `docker`, on `main` and the working branch).
