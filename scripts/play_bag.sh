#!/usr/bin/env bash
# One node, several bags. Default: headless stand playback. --interactive: native player keys.
# scripts/play_bag.sh [--interactive] [--rate 0.5] [--rviz] [--software-rendering] BAG [BAG ...]
# --sensor-profile manual|pandar128|falcon_ros|falcon_native applies to subsequent bags.
# Example: scripts/play_bag.sh --interactive --sensor-profile pandar128 BAG1 --sensor-profile falcon_ros BAG2
# Optional --archive IMAGE.tar.gz loads an offline image; IMAGE defaults to resense:latest.
set -euo pipefail
usage() { sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; }
BAGS=(); PROFILES=(); ARCHIVE=""; RATE=1.0; INTERACTIVE=0; RVIZ=0; SOFTWARE=0; PROFILE=manual; RANGE_POLICY=auto
while [ $# -gt 0 ]; do
  case "$1" in
    --archive|--rate|--sensor-profile|--clear-range-policy)
      [ $# -ge 2 ] || { usage >&2; exit 2; }
      case "$1" in --archive) ARCHIVE="$2";; --rate) RATE="$2";; --sensor-profile) PROFILE="$2";; --clear-range-policy) RANGE_POLICY="$2";; esac
      shift 2 ;;
    --interactive) INTERACTIVE=1; shift ;;
    --rviz) RVIZ=1; shift ;;
    --software-rendering) SOFTWARE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --*) echo "play_bag: unknown option $1" >&2; exit 2 ;;
    *) BAGS+=("$1"); PROFILES+=("$PROFILE"); shift ;;
  esac
done
[ "${#BAGS[@]}" -gt 0 ] || { usage >&2; exit 2; }
[[ "$RATE" =~ ^[0-9]+([.][0-9]+)?$ ]] && awk "BEGIN {exit !($RATE > 0)}" || { echo 'play_bag: --rate must be positive' >&2; exit 2; }
case "$RANGE_POLICY" in auto|legacy|conservative) ;; *) echo 'play_bag: --clear-range-policy must be auto, legacy or conservative' >&2; exit 2;; esac
for i in "${!BAGS[@]}"; do
  [ -f "${BAGS[$i]}/metadata.yaml" ] || { echo "play_bag: not a ROS bag directory: ${BAGS[$i]}" >&2; exit 2; }
  case "${PROFILES[$i]}" in manual|pandar128|falcon_ros|falcon_native) ;; *) echo "play_bag: unknown sensor profile ${PROFILES[$i]}" >&2; exit 2;; esac
  BAGS[$i]="$(cd "${BAGS[$i]}" && pwd)"
done
if [ "$INTERACTIVE" = 1 ] && { [ ! -t 0 ] || [ ! -t 1 ]; }; then
  echo 'play_bag: --interactive requires a terminal for player keyboard controls' >&2; exit 2
fi
IMAGE="${IMAGE:-resense:latest}"
HERE="$(cd "$(dirname "$0")" && pwd)"
USER_ID="${PLAYER_USER:-$(id -u):$(id -g)}"
if [ "${USER_ID%%:*}" = 0 ] && [ -n "${SUDO_UID:-}" ]; then USER_ID="$SUDO_UID:${SUDO_GID:-$SUDO_UID}"; fi
if ! command -v docker >/dev/null || ! docker info >/dev/null 2>&1; then echo 'play_bag: Docker unavailable' >&2; exit 3; fi
WANT=33554432
HAVE="$(cat /proc/sys/net/core/rmem_max 2>/dev/null || echo "$WANT")"
if [ "$HAVE" -lt "$WANT" ]; then
  if [ "$(id -u)" = 0 ]; then sysctl -q -w net.core.rmem_max=$WANT || true
  elif command -v sudo >/dev/null; then sudo -n sysctl -q -w net.core.rmem_max=$WANT || true; fi
fi
if [ -n "$ARCHIVE" ]; then IMAGE="$IMAGE" "$HERE/load_image.sh" "$ARCHIVE"; fi
docker image inspect "$IMAGE" >/dev/null 2>&1 || { echo "play_bag: image $IMAGE not found" >&2; exit 3; }
NODE="${NODE_NAME:-resense_play_node_$$}"; LISTEN="${NODE}_listen"; PLAYER="${NODE}_player"; LOGS=""
cleanup() {
  [ -z "$LOGS" ] || kill "$LOGS" 2>/dev/null || true
  docker rm -f "$NODE" "$LISTEN" "$PLAYER" >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
GRAPHICS=()
if [ "$RVIZ" = 1 ]; then
  [ -n "${DISPLAY:-}" ] || { echo 'play_bag: --rviz needs DISPLAY (X11 or xvfb-run)' >&2; exit 2; }
  GRAPHICS=(-e "DISPLAY=$DISPLAY" -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix:rw)
  AUTH_FILE="${XAUTHORITY:-$HOME/.Xauthority}"
  if [ -f "$AUTH_FILE" ]; then
    GRAPHICS+=(-e XAUTHORITY=/tmp/resense.xauth -v "$AUTH_FILE":/tmp/resense.xauth:ro)
  fi
  if [ "$SOFTWARE" = 1 ]; then GRAPHICS+=(-e LIBGL_ALWAYS_SOFTWARE=1); fi
fi
docker run -d --name "$NODE" --net=host --ipc=host "${GRAPHICS[@]}" "$IMAGE" \
  ros2 launch resense_ros detector.launch.py freshness_mode:=replay clear_range_policy:="$RANGE_POLICY" rviz:="$([ "$RVIZ" = 1 ] && echo true || echo false)" >/dev/null
READY_TIMEOUT="${READY_TIMEOUT:-60}"
waited=0
until docker logs "$NODE" 2>&1 | grep -q 'ReSense detector listening on'; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$NODE" || [ "$waited" -ge $((READY_TIMEOUT * 2)) ]; then
    echo 'play_bag: node did not start' >&2; docker logs "$NODE" 2>&1 | tail -20; exit 3
  fi
  sleep 0.5; waited=$((waited + 1))
done
echo "== node $NODE; second console: docker exec -it $NODE bash"
docker run -d --name "$LISTEN" --net=host --ipc=host --user "$USER_ID" -e HOME=/tmp "$IMAGE" python3 -u -c '
import json, time, rclpy
from std_msgs.msg import String
rclpy.init(); node = rclpy.create_node("play_bag_listener")
start, state = time.time(), {"last": None}
def report(msg):
    row = json.loads(msg.data)
    key = (row.get("node", {}).get("recording"), row["decision"], row.get("sensor_profile"))
    if key != state["last"]:
        distance = row.get("nearest_distance")
        decision, profile = row["decision"], row.get("sensor_profile", "manual")
        print(f"{time.time()-start:7.1f} s  {decision:<7s} " + (f"{distance:.1f} m" if distance is not None else "-") + f"  profile={profile}", flush=True)
        state["last"] = key
node.create_subscription(String, "/resense/status", report, 10)
rclpy.spin(node)
' >/dev/null
waited=0
until [ -n "$(docker logs "$LISTEN" 2>/dev/null)" ]; do
  [ "$waited" -lt $((READY_TIMEOUT * 2)) ] || { echo 'play_bag: no listener status' >&2; exit 3; }
  sleep 0.5; waited=$((waited + 1))
done
docker logs -f "$LISTEN" & LOGS=$!
PLAYER_FLAGS=(); KEYS=(--disable-keyboard-controls)
if [ "$INTERACTIVE" = 1 ]; then
  PLAYER_FLAGS=(-it); KEYS=()
  echo '== player keys: SPACE pause/resume; RIGHT next message while paused; UP/DOWN change rate'
fi
for i in "${!BAGS[@]}"; do
  BAG="${BAGS[$i]}"; PROFILE="${PROFILES[$i]}"
  # Previous player has exited. Let the active-input timeout elapse before a profile change.
  if [ "$i" -gt 0 ]; then sleep 1.1; fi
  docker exec "$NODE" /entrypoint.sh python3 /opt/resense/scripts/reset_replay.py --profile "$PROFILE"
  echo "== $(basename "$BAG"): rate=$RATE profile=$PROFILE; same node $NODE"
  docker run --rm --name "$PLAYER" "${PLAYER_FLAGS[@]}" --net=host --ipc=host --user "$USER_ID" -e HOME=/tmp \
    -v "$BAG":/data/bag:ro "$IMAGE" ros2 bag play /data/bag --rate "$RATE" --delay 3 \
    --read-ahead-queue-size 10 "${KEYS[@]}"
done
sleep 1
echo "== ${#BAGS[@]} bag(s) played; node $NODE stopped"
