#!/usr/bin/env bash
# One command for the jury: load the image (optionally), start the node, play a bag as a normal user
# and print every change of the decision with the nearest distance, then stop the node.
#
#   scripts/play_bag.sh <bag dir>                                  # image resense:latest already loaded
#   scripts/play_bag.sh <bag dir> --archive resense-image-<ver>.tar.gz   # the stand: no internet
#   IMAGE=resense:ci scripts/play_bag.sh /tmp/bags/smoke_bag
#
# What it does (the steps of README "Кратко для жюри" 0-5, in one script):
# 0. raises net.core.rmem_max to 32 MiB when it is lower (the UDP buffer for 360-degree clouds; with
#    sudo when not root; a warning when that is not possible - the bag still plays, frames may drop);
# 1. with --archive: scripts/load_image.sh (checksum, docker load, check with no network);
# 2. the node in its own container (--net=host --ipc=host, freshness_mode:=replay: a historical bag);
# 3. a listener printing each change of /resense/decision (GO | CAUTION | STOP | FAULT) with
#    /resense/nearest_distance, e.g. "12.3 s  STOP  55.6 m";
# 4. `ros2 bag play` from the same image as the calling user (uid:gid; a normal host console user);
# 5. stops the containers when the bag has played (Ctrl-C stops everything too).
# It waits for readiness, not for fixed times: the node's "listening" log line, then the
# listener's first decision (the node's no-input FAULT), at most READY_TIMEOUT s (default 60).
# Needs Docker, not ROS on the host. Exits 2 on a bad argument, 3 without Docker / image / node.
set -euo pipefail

usage() { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[ $# -ge 1 ] || usage
BAG=""
ARCHIVE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --archive) ARCHIVE="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) [ -z "$BAG" ] || usage; BAG="$1"; shift ;;
  esac
done
[ -n "$BAG" ] && [ -d "$BAG" ] || { echo "play_bag: no bag directory: '$BAG'" >&2; exit 2; }
IMAGE="${IMAGE:-resense:latest}"
HERE="$(cd "$(dirname "$0")" && pwd)"
BAG_ABS="$(cd "$BAG" && pwd)"
PARENT="$(dirname "$BAG_ABS")"
NAME="$(basename "$BAG_ABS")"
USER_ID="${PLAYER_USER:-$(id -u):$(id -g)}"
if [ "${USER_ID%%:*}" = 0 ] && [ -n "${SUDO_UID:-}" ]; then USER_ID="$SUDO_UID:${SUDO_GID:-$SUDO_UID}"; fi

if ! command -v docker >/dev/null || ! docker info >/dev/null 2>&1; then echo "play_bag: Docker is not available" >&2; exit 3; fi

# 0. the UDP receive buffer
WANT=33554432
HAVE="$(cat /proc/sys/net/core/rmem_max 2>/dev/null || echo "$WANT")"
if [ "$HAVE" -lt "$WANT" ]; then
  if [ "$(id -u)" = 0 ]; then sysctl -q -w net.core.rmem_max=$WANT || true
  elif command -v sudo >/dev/null; then sudo sysctl -q -w net.core.rmem_max=$WANT || true
  fi
  HAVE="$(cat /proc/sys/net/core/rmem_max 2>/dev/null || echo 0)"
  [ "$HAVE" -ge "$WANT" ] || echo "play_bag: warning: net.core.rmem_max is $HAVE (< $WANT): 360-degree frames may be dropped" >&2
fi

# 1. the image
if [ -n "$ARCHIVE" ]; then
  IMAGE="$IMAGE" "$HERE/load_image.sh" "$ARCHIVE"
fi
docker image inspect "$IMAGE" >/dev/null 2>&1 || { echo "play_bag: image $IMAGE not found (docker load -i <archive>, or --archive)" >&2; exit 3; }

READY_TIMEOUT="${READY_TIMEOUT:-60}"
NODE=resense_play_node
LISTEN=resense_play_listen
cleanup() { docker rm -f "$NODE" "$LISTEN" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM
cleanup

# 2. the node
docker run -d --name "$NODE" --net=host --ipc=host "$IMAGE" \
  ros2 launch resense_ros detector.launch.py freshness_mode:=replay >/dev/null
# ready = subscribed to its inputs (the node logs "ReSense detector listening on ..." then)
waited=0
until docker logs "$NODE" 2>&1 | grep -q "ReSense detector listening on"; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$NODE" || [ "$waited" -ge $((READY_TIMEOUT * 2)) ]; then
    echo "play_bag: the node did not start" >&2; docker logs "$NODE" 2>&1 | tail -20; exit 3
  fi
  sleep 0.5; waited=$((waited + 1))
done

# 3. the listener: each change of the decision, with the nearest distance of that frame
docker run -d --name "$LISTEN" --net=host --ipc=host --user "$USER_ID" -e HOME=/tmp "$IMAGE" \
  python3 -u -c '
import time, rclpy
from std_msgs.msg import Float32, String
rclpy.init()
n = rclpy.create_node("play_bag_listener")
t0, state = time.time(), {"dist": -1.0, "last": None}
def dist(m): state["dist"] = m.data
def dec(m):
    if m.data != state["last"]:
        d = state["dist"]
        print(f"{time.time() - t0:7.1f} s  {m.data:<7s} " + (f"{d:.1f} m" if d >= 0 else "-"), flush=True)
        state["last"] = m.data
n.create_subscription(Float32, "/resense/nearest_distance", dist, 10)
n.create_subscription(String, "/resense/decision", dec, 10)
rclpy.spin(n)
' >/dev/null
# ready = the listener has heard the node (its first line: the no-input FAULT, ~2 s after the node started)
waited=0
until [ -n "$(docker logs "$LISTEN" 2>/dev/null)" ]; do
  if [ "$waited" -ge $((READY_TIMEOUT * 2)) ]; then
    echo "play_bag: the listener heard nothing from the node in ${READY_TIMEOUT} s" >&2; exit 3
  fi
  sleep 0.5; waited=$((waited + 1))
done

# 4. the bag, played by the calling user from the same image
echo "== $NAME: playing as uid:gid $USER_ID; decision changes (time since start, decision, nearest distance):"
docker logs -f "$LISTEN" &
LOGS=$!
docker run --rm --net=host --ipc=host --user "$USER_ID" -e HOME=/tmp -v "$PARENT":/data:ro "$IMAGE" \
  ros2 bag play "/data/$NAME" --delay 3 --read-ahead-queue-size 10 --disable-keyboard-controls >/dev/null 2>&1
sleep 3
kill "$LOGS" 2>/dev/null || true
echo "== $NAME played; node stopped"
