# Troubleshooting

## The decision stays `FAULT`

| cause | check | fix |
|---|---|---|
| the node is not on the host network | `docker ps` shows the node without `--net=host` | start it with `--net=host` (the image uses DDS over UDP only) |
| different ROS domains | `echo $ROS_DOMAIN_ID` in the player's console | use the same value for player and node (default 0) |
| `live` freshness on a recorded bag | the status JSON's `freshness.reason` mentions clocks or age | use the image's default command, or pass `freshness_mode:=replay` in your own |
| the bag has not started yet | `FAULT` for the first seconds, then results | normal: the player preloads the bag; `--delay 3` gives discovery time |
| the bag ended | `FAULT` 0.5 s after the last frame | normal: no input means the path is not monitored |
| a topic the node does not see | `ros2 topic list` on the host | the node takes both known names and any `PointCloud2`; with `auto_discover:=false` pass `input_topic:=<topic>` |

## No frames arrive from a 360-degree bag

The 360° clouds are 24 MB each. A CycloneDDS player at Ubuntu's default UDP receive buffer
(`net.core.rmem_max` 212992) delivers almost none of them.

```bash
sudo sysctl -w net.core.rmem_max=33554432     # until reboot
```

The node logs a WARN at start when the buffer is smaller. The stock Fast DDS player of ROS 2 Humble
is not affected; 120° clouds arrive either way. `scripts/play_bag.sh` raises the buffer itself when
it can.

## Results are late or frames are skipped at the start

`ros2 bag play` with Humble's default read-ahead (1 000 messages) preloads the recording while its
clock runs and then sends the overdue first seconds in one burst. Play with
`--read-ahead-queue-size 10`, the supported setting. On a cold disk, pre-reading a 360° bag helps
if memory allows:

```bash
cat <bag>/*.db3 > /dev/null
```

The node reports its own start-up skips in the status (`node.catchup_skipped`, `node.catchup`);
they are deliberate, not transport losses.

## Docker

| symptom | fix |
|---|---|
| `permission denied … docker.sock` | add yourself to the `docker` group and log in again, or `newgrp docker` |
| `apt-get update` fails during the build | `PULL=1 ./scripts/build.sh` refreshes an old cached base image |
| no internet on the machine | do not build: `docker load` the archive ([Stand without internet](guides/offline-stand.md)); with compose never pass `--build` |
| a script exits with 3 | Docker is not running, the image is missing, or the node did not start (see its log) |
| checksum mismatch in `load_image.sh` (exit 4) | the archive is incomplete or not the one the `.sha256` was made for; download it again |

## RViz

| symptom | fix |
|---|---|
| `cannot open display` | run `xhost +local:docker` and pass `-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix` |
| one raw-cloud display is grey | normal: the layout has both topic names; the bag carries one |
| no cloud at all | a bag with a third topic name: *Add → PointCloud2 →* pick it; detections still show |

## The web dashboard

| symptom | fix |
|---|---|
| "Подключить" fails | rosbridge is not in the image (`apt install ros-humble-rosbridge-suite`); a copy of the page served over HTTPS cannot reach a remote `ws://`: open `web/index.html` locally, or use `wss://` |
| a file loads but shows nothing | it must contain status JSON objects, one per line (`resense run --out` or a `/resense/status` capture) |
| the banner shows «ДАННЫЕ УСТАРЕЛИ» live | the node's and the browser's clocks differ; synchronize UTC (NTP) |

Still stuck: the node's log (`docker logs <container>`) and `/resense/health` name the problem in
most cases; issues go to [GitHub](https://github.com/pmixay/ReSense/issues).
