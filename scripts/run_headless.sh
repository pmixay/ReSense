#!/usr/bin/env bash
# Demo without X11: detector + bag playback + a live distance readout in one container.
# Same scene as run_demo.sh, but it prints instead of drawing — this is the path to use over
# ssh, on the jury's machine before RViz is set up, and in the recorded terminal of the video.
#
#   ./scripts/run_headless.sh /data/for_hackathon/doubleT_obstacle [rate]
#
# Prints the node's own stats lines (fps, latency mean / p95 / max, dropped frames) and, next to
# them, /resense/nearest_distance in metres (-1.0 = path clear).
set -euo pipefail
cd "$(dirname "$0")/.."
. "$(dirname "${BASH_SOURCE[0]}")/require_docker.sh"

if [ $# -lt 1 ]; then
  sed -n '2,10p' "$0" >&2
  exit 2
fi

BAG_PATH="$1"; RATE="${2:-1.0}"
if [ ! -d "$BAG_PATH" ] || [ ! -f "$BAG_PATH/metadata.yaml" ]; then
  echo "ERROR: $BAG_PATH is not a ROS 2 bag directory (no metadata.yaml)" >&2
  exit 2
fi
require_docker_daemon
BAG_DIR="$(cd "$(dirname "$BAG_PATH")" && pwd)"
BAG_NAME="$(basename "$BAG_PATH")"

docker run --rm -i --net=host --ipc=host \
  -v "$BAG_DIR":/data:ro \
  -e BAG_NAME="$BAG_NAME" -e RATE="$RATE" \
  resense:latest bash -s <<'INNER'
set -uo pipefail
ros2 launch resense_ros detector.launch.py rviz:=false &
LAUNCH_PID=$!
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT

# wait for the node before playing: starting the bag with the launch file's bag:= argument races
# the node's startup and loses the first frames
for _ in $(seq 1 60); do
  ros2 topic list 2>/dev/null | grep -qx /resense/status && break
  sleep 1
done

stdbuf -oL ros2 topic echo /resense/nearest_distance --field data 2>/dev/null \
  | stdbuf -oL awk '{ if ($1 < 0) print "  path clear"; else printf "  OBSTACLE %.1f m\n", $1 }' &

sleep 2
ros2 bag play "/data/$BAG_NAME" --rate "$RATE" --clock --delay 3   # --delay: let DDS discovery finish before the first frame
sleep 2
INNER
