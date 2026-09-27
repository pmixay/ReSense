#!/usr/bin/env bash
# Exercise the live Foxglove path as a remote client on a second Docker endpoint.
# Requires the CI tools image (WITH_TOOLS=1); no organizer data or physical second device needed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-resense:ci}"
SUFFIX="$$"
NETWORK="resense-p2-viewer-${SUFFIX}"
SERVER="resense-p2-server-${SUFFIX}"
PLAYER="resense-p2-player-${SUFFIX}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/resense-p2-viewer.XXXXXX")"

cleanup() {
  docker rm -f "$PLAYER" "$SERVER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

docker network create --internal "$NETWORK" >/dev/null
chmod 777 "$WORK"
docker run --rm --network "$NETWORK" --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 -v "$WORK:/data" "$IMAGE" \
  python3 scripts/make_smoke_bag.py /data/p2_smoke_bag >/dev/null

# The server endpoint runs the normal image entrypoint and node. Start only the included
# Foxglove bridge as an extra process; its WebSocket stays inside the Docker network.
docker run -d --name "$SERVER" --network "$NETWORK" "$IMAGE" \
  ros2 launch resense_ros detector.launch.py freshness_mode:=replay >/dev/null
ready=0
for _ in $(seq 1 60); do
  if docker logs "$SERVER" 2>&1 | grep -q "ReSense detector listening"; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  docker logs "$SERVER" >&2
  echo "detector did not become ready" >&2
  exit 1
fi
docker exec -d "$SERVER" /entrypoint.sh ros2 run foxglove_bridge foxglove_bridge \
  --ros-args -p address:=0.0.0.0 -p port:=8765
sleep 2

# Keep positive messages flowing so a second endpoint can verify channel discovery and data.
docker run -d --rm --name "$PLAYER" --network "$NETWORK" --user 1000:1000 -e HOME=/tmp \
  -v "$WORK:/data:ro" "$IMAGE" bash -lc \
  "ros2 bag play /data/p2_smoke_bag --delay 3 --disable-keyboard-controls --loop" >/dev/null

probe() {
  local timeout="$1"
  docker run --rm --network "$NETWORK" -v "$ROOT/web:/web:ro" "$IMAGE" \
    python3 /web/demo/check_foxglove_live.py \
      --layout /web/foxglove_layout.json --url "ws://$SERVER:8765" --timeout "$timeout" \
      --require-freshness
}

if ! probe 60; then
  docker logs "$SERVER" >&2
  exit 1
fi

# A paused server models a dropped demo link. A fresh viewer must fail while it is paused and
# succeed again after the server resumes, which makes the recovery check deterministic.
docker pause "$SERVER" >/dev/null
if probe 4; then
  echo "viewer unexpectedly received a live stream while the server was paused" >&2
  exit 1
fi
docker unpause "$SERVER" >/dev/null
if ! probe 60; then
  docker logs "$SERVER" >&2
  echo "viewer did not recover after the server resumed" >&2
  exit 1
fi
echo "PASS: remote viewer received live detector topics, detected the outage, and recovered"
