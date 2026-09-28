# Node input path and end-to-end latency through ROS (28.09)

(Corrected 28.09 after the independent re-judgement: the all-frame latency, the disputed
"before" baseline and the frame-111 GO added; every figure recomputed from the captures here.)

What changed (P1, ROS node only; the sealed detector, its configuration and the image's layers
below the ROS package are unchanged):

* the input clouds are taken as serialized bytes (`raw_input`, default true) and read by
  `ros2_ws/src/resense_ros/resense_ros/fastcloud.py` instead of rclpy's message conversion;
* (the `ab/new_*` runs below also used a one-gather decode; the independent review measured it
  as barely faster on the sandbox, 19.4 → 18.4 ms median at 360° (judge A), and slower on the CI
  runner, 8.82 → 9.30 ms (judge B), so the final code keeps the reference decode
  `pointcloud2_to_arrays`, same output);
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

| recording | frames identical | rclpy conversion median / p95 | bytes parsed median / p95 |
|---|---|---|---|
| `doubleT_obstacle` (360°, 921 600 points) | **201 of 201** | 12.7 / 33.4 ms | 0.10 / 0.17 ms |
| `roundT_doubleT` (120°, 307 200 points) | **252 of 252** | 3.2 / 4.4 ms | 0.08 / 0.14 ms |

(Final code: parsed bytes, row padding removed, the reference decode. CI runner, run 36397511351:
rclpy 7.0 / 30.0 ms and parse 0.07 / 2.5 ms at 360°; 453 of 453 frames identical.)

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
| decisions from frame 75 that are not STOP (bag message index) | 111 GO, 117 / 197 CAUTION | 111 GO, 117 / 197 CAUTION | 197 CAUTION | 111 GO, 117 / 197 CAUTION |

| `roundT_doubleT` (120°, clear) | base run 1 | base run 2 | new run 1 | new run 2 |
|---|---|---|---|---|
| decode + detect mean / p95 / max | 41 / 53 / 66 ms | 40 / 56 / 92 ms | 38 / 52 / 75 ms | 37 / 48 / 62 ms |
| **end to end, current results: median / p95 / max** | 59 / **76** / 153 ms | 46 / **68** / 118 ms | 45 / **61** / 96 ms | 44 / **57** / 92 ms |
| alarm frames | 0 | 0 | 0 | 0 |
| node CPU median / max, peak RSS | – | – | 0.47 / 0.52 cores, 127 MB | 0.45 / 0.50 cores, 128 MB |

The detections are the same in both images: 190 STOP frames at 55.5–56.6 m wherever the node
processed all 201 frames, with the same single GO at frame 111 and CAUTION at frames 117 and 197
while the object on the rail is in view (new run 1, whose start-up skipped 10 frames, has STOP at
111 and 117). That is a limitation of the sealed detector, not of the input path
([`ALGORITHM.md`](../../ALGORITHM.md) §6; recomputed by
[`judge_outputs_2026-09-28/recompute.py`](../judge_outputs_2026-09-28/README.md)).

**Cold disk** (`scripts/p1_cold_bag_test.sh` as CI runs it, the page cache dropped before each
recording, the same machine, the final build; `cold_local/`): 360° end to end median 74 / **p95
114** / max 181 ms over 182 current results, decode + detect p95 72 ms, node 0.63 cores, 0 recording
messages unprocessed after settle; 120° median 44 / **p95 59** / max 104 ms, 0.46 cores; the identity
check PASS on both. The player reading 240 MB/s of 360° recording from a cold disk delays the
DDS delivery (the node's own p95 is unchanged); the CI runner's cold baseline before the change was
p95 126 / 49 ms (run 36319767736).

**Current results and all frames.** The end-to-end figures above (and those `check_dry_run.py`
prints) cover the **current** results: those whose input was fresh when they were made, the
ones a consumer may act on. The start-up catch-up is not in them: while the player's first burst
is worked through, results are published as FAULT, CAUTION or a held STOP (never GO) with an
input age of up to seconds. Over **every frame result the node published** (start-up included;
frames the catch-up skipped are in neither), from the same captures
([`e2e_all_frames.py`](e2e_all_frames.py)):

| capture | current results: n, median / p95 / max | all frame results: n, median / p95 / max |
|---|---|---|
| 360°, base run 1 / run 2 | 122: 88 / 120 / 181 ms · 103: 84 / 127 / 171 ms | 201: 104 / 1 227 / 1 355 ms · 201: 135 / 2 143 / 2 309 ms |
| 360°, new run 1 / run 2 | 179: 74 / 93 / 150 ms · 180: 73 / 97 / 153 ms | 191: 75 / 243 / 1 209 ms · 201: 75 / 455 / 683 ms |
| 360°, new, cold disk (`cold_local/`) | 182: 74 / 114 / 181 ms | 201: 75 / 418 / 625 ms |
| 360°, CI runner cold, 27.09, before the change (run 36319767736) | 175: 92 / 126 / 140 ms | 201: 94 / 762 / 905 ms |
| 120°, base run 1 / run 2 | 250: 59 / 76 / 153 ms · 248: 46 / 68 / 118 ms | 252: 59 / 76 / 157 ms · 252: 46 / 72 / 227 ms |
| 120°, new run 1 / run 2 | 250: 45 / 61 / 96 ms · 250: 44 / 57 / 92 ms | 252: 45 / 62 / 118 ms · 252: 44 / 57 / 120 ms |
| 120°, new, cold disk | 250: 44 / 59 / 104 ms | 252: 44 / 60 / 128 ms |
| 120°, CI runner cold, 27.09 (run 36319767736) | 242: 43 / 49 / 107 ms | 252: 43 / 52 / 354 ms |

In every capture, once the first current result is out, every later result is current: the
difference between the two columns is the start-up alone. At 360° the start-up results are
6–10 % of the frames with the new node (12, 21 and 19 of 191–201) and 39–49 % in the team's two
base runs (79 and 98 of 201), which is why the all-frame p95 moved most (1.2–2.1 s → 0.24–0.46 s). The CI figures of
28.09 (60 / 37 ms) are current results from the run's log; its captures are not committed.

Per stage in the new node (`node.decode_ms` / `node.detect_ms`, median / p95): 360° 19.3 / 27 and
33 / 45–51 ms; 120° 7.8–8.0 / 11 and 28 / 40–42 ms.

**Independent check (28.09 re-judgement, judge A, 5 alternating pairs at 360° on the same kind of
machine, 4-vCPU Intel Xeon 2.1 GHz):** end-to-end p95 of the current results, median of the
runs, 113 → 102 ms with the recording cached (base 102–169, reviewed 87–111 ms), 137 → 118 ms
cold; decode + detect p95 75 → 75 ms (unchanged, as expected: the gain is the conversion before
the callback and the visualisation after it). The team's two pairs above overstate the gain: it
is ~10–20 ms at 360°, and p95 is not reliably under the 100 ms period on this 2.1 GHz 4-vCPU
machine (the organizers' i7-9700E, 8 faster cores, was not available). On a CI runner the final
code measured 60 ms (360°) and 37 ms (120°) cold (run 36397511351, from its log). The remaining
time is the detector (sealed) and the DDS transfer of the 24 MB cloud over UDP.

**The "before" baseline is disputed.** The team's two base runs above (+7.9 and +9.8 s until the
start-up catch-up was back on the newest frame; 122 and 103 current results of 201) are worse
than judge A's six base runs with the same base image on the same kind of machine: +2.2–3.5 s
warm and +3.9 s cold by his checker outputs (his summary says +3.1–3.9 s), 149–178 current
results warm, 159 cold ([his checker outputs](../judge_outputs_2026-09-28/provenance/node_dry_runs_checker_output.txt),
[report](../results/rejudge_2026-09-28.json)). Both are stated; the team's base runs are the ones
committed here, his raw captures are not. The before / after comparison of the current results
therefore rests on judge A's pairs and on the CI runner, not on the team's two base runs, which
also compare different subsets (103–122 against 179–182 current results).

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
