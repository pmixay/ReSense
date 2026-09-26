#!/usr/bin/env bash
# The organizers' procedure with no internet: the node in its own container on the image's default
# command, `ros2 bag play` as a normal user (uid 1000) in a second container, /resense/status
# recorded by a third, all on a `docker network create --internal` network (a bridge with no way
# out: the containers reach each other and nothing else, as on a stand whose network card is up but
# not connected to the internet); then scripts/check_dry_run.py on the host. The same chain as the
# ci.yml docker step "no internet, the organizers' way", as a script, so that the release workflow
# (.github/workflows/release.yml) and scripts/release.sh run it on the image loaded from the archive.
#
#   scripts/internal_net_test.sh <bag dir> [<second bag dir, same parent>] [-- <check_dry_run.py args>]
#   IMAGE=resense:v1.0.0-rc1 scripts/internal_net_test.sh /tmp/bags/smoke_bag /tmp/bags/smoke_bag2
#
# scripts/check_no_network.py runs first, inside the network: no TCP connection to the internet.
# Default check (no arguments after --): an obstacle in every recording, and with two bags two
# recordings seen, as scripts/console_test.sh. Exits with check_dry_run.py's code; 1 also when the
# network check fails; 2 bad arguments; 3 no Docker daemon or the node did not start.
#
# Environment:
#   IMAGE=resense:latest        image of every container
#   PLAYER_USER=1000:1000       uid:gid of the player
#   NET=resense-internal-test   name of the internal network (created and removed here)
#   OUT=out/internal_net_test   status.jsonl, node.log
set -euo pipefail
cd "$(dirname "$0")/.."
. "$(dirname "${BASH_SOURCE[0]}")/require_docker.sh"
IMAGE="${IMAGE:-resense:latest}"
PLAYER_USER="${PLAYER_USER:-1000:1000}"
NET="${NET:-resense-internal-test}"
OUT="${OUT:-out/internal_net_test}"
if [ $# -lt 1 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  awk 'NR > 1 && /^#/ { print; next } NR > 1 { exit }' "$0" >&2    # the header comment
  exit 2
fi
BAG1="$1"; shift
if [ ! -d "$BAG1" ] || [ ! -f "$BAG1/metadata.yaml" ]; then
  echo "ERROR: $BAG1 is not a ROS 2 bag directory (no metadata.yaml)" >&2
  exit 2
fi
BAG2=""
if [ $# -gt 0 ] && [ "$1" != "--" ]; then BAG2="$1"; shift; fi
if [ -n "$BAG2" ] && { [ ! -d "$BAG2" ] || [ ! -f "$BAG2/metadata.yaml" ]; }; then
  echo "ERROR: $BAG2 is not a ROS 2 bag directory (no metadata.yaml)" >&2
  exit 2
fi
PARENT="$(cd "$(dirname "$BAG1")" && pwd)"
if [ -n "$BAG2" ] && [ "$(cd "$(dirname "$BAG2")" && pwd)" != "$PARENT" ]; then
  echo "ERROR: both bags must be in the same directory (it is mounted into the player)" >&2
  exit 2
fi
[ "${1:-}" = "--" ] && shift
require_docker_daemon || exit 3
mkdir -p "$OUT"; OUT_ABS="$(cd "$OUT" && pwd)"
rm -f "$OUT_ABS/status.jsonl" "$OUT_ABS/node.log"
NODE=resense_int_node ECHO=resense_int_echo
cleanup() {
  docker rm -f "$NODE" "$ECHO" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup

docker network create --internal "$NET" >/dev/null
echo "== $IMAGE on the internal network $NET: no way to the internet"
if ! docker run --rm --network "$NET" "$IMAGE" python3 scripts/check_no_network.py; then
  echo "ERROR: the internal network reaches the internet; this run would prove nothing" >&2
  exit 1
fi
docker run -d --name "$NODE" --network "$NET" "$IMAGE" >/dev/null
READY=0
for _ in $(seq 1 60); do
  if docker logs "$NODE" 2>&1 | grep -q "ReSense detector listening"; then READY=1; break; fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "ERROR: the detector container did not become ready within 60 s" >&2
  docker logs "$NODE" 2>&1 | tail -n 30 >&2 || true
  exit 3
fi
docker logs "$NODE" 2>&1 | grep -o "ReSense detector listening.*" | cut -c1-240 || true
docker run -d --name "$ECHO" --network "$NET" -v "$OUT_ABS":/out "$IMAGE" \
  bash -c "ros2 topic echo /resense/status --field data > /out/status.jsonl" >/dev/null
sleep 4
PLAY="ros2 bag play /data/$(basename "$BAG1") --delay 3 --disable-keyboard-controls"
if [ -n "$BAG2" ]; then
  PLAY="$PLAY && sleep 5 && ros2 bag play /data/$(basename "$BAG2") --delay 3 --disable-keyboard-controls"
fi
echo "== playing as user $PLAYER_USER from a separate container: $(basename "$BAG1") ${BAG2:+then $(basename "$BAG2")}"
docker run --rm --network "$NET" --user "$PLAYER_USER" -e HOME=/tmp -v "$PARENT":/data:ro "$IMAGE" \
  bash -c "$PLAY"
sleep 4
docker logs "$NODE" > "$OUT_ABS/node.log" 2>&1 || true
grep -E "input [0-9]+:|re-created|NO_INPUT" "$OUT_ABS/node.log" | cut -c1-220 || true

if [ $# -gt 0 ]; then
  CHECK_ARGS=("$@")
else
  CHECK_ARGS=(--expect-obstacle --min-frames 20 --max-p95-latency 1000 --max-dropped 100000)
  [ -n "$BAG2" ] && CHECK_ARGS+=(--expect-inputs 2)
fi
python3 scripts/check_dry_run.py "$OUT_ABS/status.jsonl" "${CHECK_ARGS[@]}"
