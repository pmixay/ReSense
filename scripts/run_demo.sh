#!/usr/bin/env bash
# Full demo: detector + RViz + bag playback in one container.
#   ./scripts/run_demo.sh /path/to/for_hackathon/roundT_doubleT [rate]
#   RVIZ=0 ./scripts/run_demo.sh <bag> [rate]   # no X11 — delegates to run_headless.sh
#
# The directory holding the bag is mounted at /data inside the container, so the bag path on the
# command line is the only thing that decides where the data comes from (see README, "Where the
# data lives"). docker compose uses $RESENSE_DATA for the same mount.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -lt 1 ]; then
  sed -n '2,5p' "$0" >&2
  exit 2
fi

if [ "${RVIZ:-1}" = "0" ]; then
  exec ./scripts/run_headless.sh "$@"
fi

BAG_PATH="$1"; RATE="${2:-1.0}"
if [ ! -d "$BAG_PATH" ] || [ ! -f "$BAG_PATH/metadata.yaml" ]; then
  echo "ERROR: $BAG_PATH is not a ROS 2 bag directory (no metadata.yaml)" >&2
  exit 2
fi
BAG_DIR="$(cd "$(dirname "$BAG_PATH")" && pwd)"
BAG_NAME="$(basename "$BAG_PATH")"

xhost +local:docker >/dev/null 2>&1 || true
docker run --rm -it --net=host --ipc=host \
  -e DISPLAY="${DISPLAY:-:0}" -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$BAG_DIR":/data:ro \
  resense:latest ros2 launch resense_ros detector.launch.py bag:=/data/"$BAG_NAME" rviz:=true rate:="$RATE"
