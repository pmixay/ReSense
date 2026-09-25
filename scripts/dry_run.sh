#!/usr/bin/env bash
# Acceptance test for the submission (docs/SUBMISSION.md): build the image from scratch, play a
# bag through the node headlessly, capture /resense/status and assert the numbers we promise.
#
#   ./scripts/dry_run.sh /data/for_hackathon/doubleT_obstacle          # the known obstacle at 55-57 m
#   SKIP_BUILD=1 ./scripts/dry_run.sh /data/for_hackathon/roundT_doubleT --expect-clear
#   IMAGE_TAR=dist/resense-image-<ver>.tar.gz OFFLINE=1 ./scripts/dry_run.sh <bag>   # the stand
#
# Environment:
#   SKIP_BUILD=1     reuse the existing resense:latest instead of rebuilding
#   IMAGE_TAR=<tgz>  load the image from an archive of scripts/export_image.sh instead of building
#                    (scripts/load_image.sh: sha256, docker load, check with --network none)
#   OFFLINE=1        the test stand has no internet (docs/organizers/answers.md section 7): run
#                    node, player and recorder in a container with --network none (loopback only);
#                    needs IMAGE_TAR or SKIP_BUILD=1, since a build needs the internet
#   RATE=1.0         bag playback rate passed to `ros2 bag play`
#   OUT=out/dry_run  where status.jsonl and node.log are written on the host
#   DOCKER_ARGS=""   extra `docker run` arguments, split on whitespace, e.g. "-e RESENSE_NATIVE=0"
#                    (the node on the numpy path) or "--name resense_bench_dry" (scripts/bench_8core.sh)
#   RESENSE_DATA     ignored here: the bag path given on the command line decides the mount
#
# Any argument after the bag path is forwarded to scripts/check_dry_run.py, so the acceptance
# thresholds live in one place. With no extra arguments the doubleT_obstacle criteria are used.
#
# Needs the dataset, so this runs on a team machine, not in GitHub CI. The 28.09 dry run simulates
# the stand: scripts/export_image.sh on a machine with internet, the archive copied to the dry-run
# machine, its network disconnected, then IMAGE_TAR=<archive> OFFLINE=1 (docs/SUBMISSION.md).
set -euo pipefail
cd "$(dirname "$0")/.."
. "$(dirname "${BASH_SOURCE[0]}")/require_docker.sh"

if [ $# -lt 1 ]; then
  sed -n '2,27p' "$0" >&2
  exit 2
fi

BAG_PATH="$1"; shift
if [ ! -d "$BAG_PATH" ] || [ ! -f "$BAG_PATH/metadata.yaml" ]; then
  echo "ERROR: $BAG_PATH is not a ROS 2 bag directory (no metadata.yaml)" >&2
  exit 2
fi
OFFLINE="${OFFLINE:-0}"
IMAGE_TAR="${IMAGE_TAR:-}"
if [ -n "$IMAGE_TAR" ] && [ ! -f "$IMAGE_TAR" ]; then
  echo "ERROR: IMAGE_TAR=$IMAGE_TAR does not exist" >&2
  exit 2
fi
if [ "$OFFLINE" = "1" ] && [ -z "$IMAGE_TAR" ] && [ "${SKIP_BUILD:-0}" != "1" ]; then
  echo "ERROR: OFFLINE=1 cannot build the image (the build needs the internet): set" >&2
  echo "       IMAGE_TAR=<archive of scripts/export_image.sh> or SKIP_BUILD=1" >&2
  exit 2
fi
require_docker_daemon
BAG_DIR="$(cd "$(dirname "$BAG_PATH")" && pwd)"
BAG_NAME="$(basename "$BAG_PATH")"
RATE="${RATE:-1.0}"
read -r -a EXTRA_ARGS <<< "${DOCKER_ARGS:-}"
OUT="${OUT:-out/dry_run}"
mkdir -p "$OUT"
OUT_ABS="$(cd "$OUT" && pwd)"
rm -f "$OUT_ABS/status.jsonl" "$OUT_ABS/node.log"

if [ -n "$IMAGE_TAR" ]; then
  echo "== IMAGE_TAR: loading resense:latest from $IMAGE_TAR instead of building =="
  scripts/load_image.sh "$IMAGE_TAR"
elif [ "${SKIP_BUILD:-0}" != "1" ]; then
  echo "== building resense:latest from scratch =="
  docker build --no-cache -t resense:latest -f docker/Dockerfile .
else
  echo "== SKIP_BUILD=1: reusing resense:latest =="
fi

NET_ARGS=(--net=host --ipc=host)
if [ "$OFFLINE" = "1" ]; then
  NET_ARGS=(--network none)
  echo "== OFFLINE=1: the container gets no network at all (--network none, loopback only) =="
  if command -v timeout >/dev/null 2>&1 && timeout 3 bash -c 'exec 3<>/dev/tcp/1.1.1.1/443' 2>/dev/null; then
    echo "   (this host still reaches the internet; the container cannot)"
  else
    echo "   (this host does not reach the internet either)"
  fi
  docker run --rm --network none resense:latest python3 scripts/check_no_network.py
fi

echo "== playing $BAG_NAME at rate $RATE through the node (headless) =="
# One container so that discovery cannot be the thing that fails. The node is started first and
# we wait for it to advertise before playing: the launch file's own bag:= argument races the
# node's startup and silently loses the first frames.
docker run --rm -i "${NET_ARGS[@]}" ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} \
  -v "$BAG_DIR":/data:ro \
  -v "$OUT_ABS":/out \
  -e BAG_NAME="$BAG_NAME" -e RATE="$RATE" \
  resense:latest bash -s <<'INNER'
set -euo pipefail
ros2 launch resense_ros detector.launch.py rviz:=false >/out/node.log 2>&1 &
LAUNCH_PID=$!

for _ in $(seq 1 60); do
  if ros2 topic list 2>/dev/null | grep -qx /resense/status; then break; fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "detector exited during startup; see node.log" >&2
    exit 3
  fi
  sleep 1
done
if ! ros2 topic list 2>/dev/null | grep -qx /resense/status; then
  echo "detector never advertised /resense/status; see node.log" >&2
  kill "$LAUNCH_PID" 2>/dev/null || true
  exit 3
fi

ros2 topic echo /resense/status --field data >/out/status.jsonl 2>/dev/null &
ECHO_PID=$!
sleep 2

ros2 bag play "/data/$BAG_NAME" --rate "$RATE" --clock --delay 3 --disable-keyboard-controls   # --delay: let DDS discovery finish before the first frame
sleep 3        # let the last frames finish and one more stats tick land

kill "$ECHO_PID" "$LAUNCH_PID" 2>/dev/null || true
wait "$ECHO_PID" 2>/dev/null || true
INNER

echo
echo "== checking $OUT/status.jsonl =="
if [ $# -gt 0 ]; then
  CHECK_ARGS=("$@")
else
  CHECK_ARGS=(--expect-obstacle --distance 50:62 --max-p95-latency 100 --max-dropped 0)
fi
python3 scripts/check_dry_run.py "$OUT_ABS/status.jsonl" "${CHECK_ARGS[@]}"
