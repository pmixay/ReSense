#!/usr/bin/env bash
# The organizers' procedure with separate processes: the node in its own container on the image's
# default command (root), `ros2 bag play` in a second container as a normal user (a host console:
# uid 1000 by default), /resense/status recorded by a third; then scripts/check_dry_run.py.
#
#   scripts/console_test.sh <bag dir> [<second bag dir, same parent>] [-- <check_dry_run.py args>]
#   IMAGE=resense:ci PLAYER_USER=1001:1001 scripts/console_test.sh /tmp/bags/smoke_bag /tmp/bags/smoke_bag2
#
# A second bag is played into the same running node after the first (the input switch). With no
# check arguments: an obstacle must be reported in every recording and, with two bags, two
# recordings seen (the CI bags both have one). The organizers' recordings, a clear one first:
#   scripts/console_test.sh <bags>/roundT_doubleT <bags>/doubleT_obstacle -- --expect-obstacle \
#       --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
# Exits with check_dry_run.py's code. Needs Docker, not ROS on the host.
set -uo pipefail
cd "$(dirname "$0")/.."
IMAGE="${IMAGE:-resense:latest}"
PLAYER_USER="${PLAYER_USER:-1000:1000}"
OUT="${OUT:-out/console_test}"
BAG1="${1:?usage: scripts/console_test.sh <bag dir> [<second bag dir>] [-- check args]}"; shift
BAG2=""
if [ $# -gt 0 ] && [ "$1" != "--" ]; then BAG2="$1"; shift; fi
[ "${1:-}" = "--" ] && shift
PARENT="$(cd "$(dirname "$BAG1")" && pwd)"
mkdir -p "$OUT"; OUT_ABS="$(cd "$OUT" && pwd)"
rm -f "$OUT_ABS/status.jsonl" "$OUT_ABS/node.log"
cleanup() { docker rm -f resense_ct_node resense_ct_echo >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

docker run -d --name resense_ct_node --net=host --ipc=host "$IMAGE" >/dev/null
for _ in $(seq 1 60); do
  docker logs resense_ct_node 2>&1 | grep -q "ReSense detector listening" && break
  sleep 1
done
docker run -d --name resense_ct_echo --net=host --ipc=host -v "$OUT_ABS":/out "$IMAGE" \
  bash -c "ros2 topic echo /resense/status --field data > /out/status.jsonl" >/dev/null
sleep 4
PLAY="ros2 bag play /data/$(basename "$BAG1") --delay 3 --disable-keyboard-controls"
if [ -n "$BAG2" ]; then
  PLAY="$PLAY; sleep 5; ros2 bag play /data/$(basename "$BAG2") --delay 3 --disable-keyboard-controls"
fi
echo "== playing as user $PLAYER_USER from a separate container: $(basename "$BAG1") ${BAG2:+then $(basename "$BAG2")}"
docker run --rm --net=host --ipc=host --user "$PLAYER_USER" -e HOME=/tmp -v "$PARENT":/data:ro "$IMAGE" \
  bash -c "$PLAY >/dev/null 2>&1"
sleep 4
docker logs resense_ct_node > "$OUT_ABS/node.log" 2>&1
grep -E "input [0-9]+:|re-created|NO_INPUT" "$OUT_ABS/node.log" | cut -c1-220 || true

if [ $# -gt 0 ]; then
  CHECK_ARGS=("$@")
else
  CHECK_ARGS=(--expect-obstacle --min-frames 20 --max-p95-latency 1000 --max-dropped 100000)
  [ -n "$BAG2" ] && CHECK_ARGS+=(--expect-inputs 2)
fi
python3 scripts/check_dry_run.py "$OUT_ABS/status.jsonl" "${CHECK_ARGS[@]}"
