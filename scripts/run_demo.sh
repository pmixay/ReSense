#!/usr/bin/env bash
# Full demo: detector + RViz + bag playback in one container.
#   ./scripts/run_demo.sh /path/to/for_hackathon/roundT_doubleT [rate]
set -euo pipefail
BAG_DIR="$(cd "$(dirname "$1")" && pwd)"; BAG_NAME="$(basename "$1")"; RATE="${2:-1.0}"
xhost +local:docker >/dev/null 2>&1 || true
docker run --rm -it --net=host --ipc=host \
  -e DISPLAY="${DISPLAY:-:0}" -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$BAG_DIR":/data:ro \
  resense:latest ros2 launch resense_ros detector.launch.py bag:=/data/"$BAG_NAME" rviz:=true rate:="$RATE"
