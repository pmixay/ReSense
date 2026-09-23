# Evidence of the runs quoted in the docs

## `docker_2026-09-23/`: the ROS 2 node in Docker on the real frames (EXPERIMENTS.md §3b)

These runs used Docker in the development sandbox (4 vCPU). The recordings were rebuilt from the frame cache by
`scripts/cache_to_bag.py`: same topic, `frame_id`, PointCloud2 layout, scan order and receive
times as the originals, coordinates quantised to 5 mm. `checks.txt` is the output of
`scripts/check_dry_run.py` on each capture. For each run the folder has the node log (`*_node.log`)
and the status stream (`*_status.jsonl.gz`).

| run | how | result |
|---|---|---|
| `clear` | `scripts/dry_run.sh roundT_doubleT --expect-clear --max-alarm-frames 2`; node and player in one container, root | 237 of 252 frames, 10 fps, p95 76 ms; the recording's 2 known alarm frames at 128–130 m (the offline evaluation has the same two) — PASS |
| `obstacle` | `scripts/dry_run.sh doubleT_obstacle`, one container, root | person and object at 55.9–56.5 m; at 360° the sandbox runs at the frame period, so the p95 ≤ 100 ms and "no dropped frame" criteria fail here |
| `ct_smoke` | `scripts/console_test.sh`, with the node in its own container on the image's default command and the player **as uid 1000** in a second container; two synthetic bags, both topic / frame pairs | PASS; input switched, detector restarted |
| `ct_real` | the same procedure on `roundT_doubleT` and then `doubleT_obstacle` | both recordings; obstacle at 56.1 m; the only out-of-window distances are the 2 known frames at 128–130 m of the first recording; `ct_real_docker_stats.txt` shows the node container at ~100 % of one core while frames arrive (busy median), 186 MB |

The `clear` and `obstacle` runs predate the image's UDP-only DDS profile (`docker/fastdds_udp.xml`). The `ct_*` runs use it.

## `bag_metadata/`: the original `metadata.yaml` of the six recordings

These files are copied unchanged from the organizers' dataset. Every recording was made with
`reliability: 1`, which is RELIABLE in rosbag2's QoS encoding (`history: 1` is keep-last,
`depth: 10`, `durability: 2` is volatile). `ros2 bag play` publishes with these recorded
profiles. This is why the node's `input_reliability: auto` subscribes reliable to such a
player (EXPERIMENTS.md §3b). A best-effort subscription lost 196 of the 201 clouds of
`doubleT_obstacle`.
