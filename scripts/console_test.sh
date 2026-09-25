#!/usr/bin/env bash
# The organizers' procedure with separate processes: the node in its own container on the image's
# default command (root), `ros2 bag play` in a second container as a normal user (a host console:
# uid 1000 by default), /resense/status recorded by a third; then scripts/check_dry_run.py.
#
#   scripts/console_test.sh <bag dir> [<second bag dir, same parent>] [-- <check_dry_run.py args>]
#   IMAGE=resense:ci PLAYER_USER=1001:1001 scripts/console_test.sh /tmp/bags/smoke_bag /tmp/bags/smoke_bag2
#   PLAYER_DDS=stock scripts/console_test.sh /tmp/bags/smoke_bag /tmp/bags/smoke_bag2   # stock Fast DDS player
#
# A second bag is played into the same running node after the first (the input switch). With no
# check arguments: an obstacle must be reported in every recording and, with two bags, two
# recordings seen (the CI bags both have one). The organizers' recordings, a clear one first:
#   scripts/console_test.sh <bags>/roundT_doubleT <bags>/doubleT_obstacle -- --expect-obstacle \
#       --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
# Exits with check_dry_run.py's code (1 also for a failed stock-DDS assertion below; 2 bad
# arguments; 3 no Docker daemon or the node did not start). Needs Docker, not ROS on the host.
#
# Environment:
#   IMAGE=resense:latest     image of every container
#   PLAYER_USER=1000:1000    uid:gid of the player (a host console user)
#   PLAYER_ENV="..."         extra `docker run` arguments for the player container (and the stock
#                            listener), split on whitespace, e.g. "-e ROS_DOMAIN_ID=0"
#   PLAYER_DDS=image         image: the player uses the image's Fast DDS profile (UDP only, like the node)
#                            stock: Humble's default rmw_fastrtps_cpp settings, as a host console with a
#                            stock ROS 2 install (below)
#   OUT=out/console_test     status.jsonl, node.log (+ player.log, listener.log with PLAYER_DDS=stock)
#
# PLAYER_DDS=stock. The image sets FASTRTPS_DEFAULT_PROFILES_FILE=/opt/resense/fastdds_udp.xml (UDP
# only); `docker run -e VAR=` could only empty it, so the player's shell unsets it, together with
# FASTDDS_DEFAULT_PROFILES_FILE and RMW_FASTRTPS_USE_QOS_FROM_XML, runs in an empty directory (no
# DEFAULT_FASTRTPS_PROFILES.xml to pick up) with RMW_IMPLEMENTATION defaulting to rmw_fastrtps_cpp:
# Fast DDS's builtin transports, shared memory + UDPv4 - what the organizers' console runs. A
# listener with the same settings and uid echoes /resense/decision. The node keeps its UDP-only
# profile: it announces no shared-memory locators, so the stock participants must reach it (and be
# reached) over UDP. Asserted on top of the check_dry_run.py criteria:
#   - every play exits 0, and with Fast DDS it created new shared-memory files of its uid in
#     /dev/shm while it ran (--ipc=host: the host's /dev/shm), i.e. shared memory really was on;
#   - the listener heard the node, and heard STOP when an obstacle is expected.
# With PLAYER_DDS=stock a profile variable passed in PLAYER_ENV is removed too; to try a custom
# profile use PLAYER_DDS=image PLAYER_ENV="-e FASTRTPS_DEFAULT_PROFILES_FILE=/data/<profile>.xml"
# (a file in the bag directory, mounted at /data). Another RMW, if installed in the image:
# PLAYER_DDS=stock PLAYER_ENV="-e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" (no shared-memory check then).
set -euo pipefail
cd "$(dirname "$0")/.."
. "$(dirname "${BASH_SOURCE[0]}")/require_docker.sh"
IMAGE="${IMAGE:-resense:latest}"
PLAYER_USER="${PLAYER_USER:-1000:1000}"
PLAYER_DDS="${PLAYER_DDS:-image}"
OUT="${OUT:-out/console_test}"
case "$PLAYER_DDS" in
  image|stock) ;;
  *) echo "ERROR: PLAYER_DDS must be 'image' or 'stock', not '$PLAYER_DDS'" >&2; exit 2 ;;
esac
read -r -a PLAYER_ARGS <<< "${PLAYER_ENV:-}"
BAG1="${1:?usage: scripts/console_test.sh <bag dir> [<second bag dir>] [-- check args]}"; shift
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
[ "${1:-}" = "--" ] && shift
require_docker_daemon
PARENT="$(cd "$(dirname "$BAG1")" && pwd)"
mkdir -p "$OUT"; OUT_ABS="$(cd "$OUT" && pwd)"
rm -f "$OUT_ABS/status.jsonl" "$OUT_ABS/node.log" "$OUT_ABS/player.log" "$OUT_ABS/listener.log"
cleanup() { docker rm -f resense_ct_node resense_ct_echo resense_ct_listen >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

# Humble's default rmw_fastrtps_cpp settings inside a container of the image (PLAYER_DDS=stock); run by
# the player's / listener's shell, so the variables are expanded there, not here.
# shellcheck disable=SC2016
STOCK_DDS='unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
cd "$(mktemp -d)"
echo "DDS uid=$(id -u) RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION FASTRTPS_DEFAULT_PROFILES_FILE=${FASTRTPS_DEFAULT_PROFILES_FILE-unset} FASTDDS_DEFAULT_PROFILES_FILE=${FASTDDS_DEFAULT_PROFILES_FILE-unset} cwd=$PWD profile_in_cwd=$(ls DEFAULT_FASTRTPS_PROFILES.xml 2>/dev/null || echo none) fastrtps=$(dpkg-query -W -f="\${Version}" ros-humble-fastrtps 2>/dev/null || echo unknown)"
'
# The stock player: every play is watched for new Fast DDS shared-memory files of the player's uid.
# shellcheck disable=SC2016
STOCK_PLAYER="$STOCK_DDS"'
export LC_ALL=C
shm_files() { find /dev/shm -maxdepth 1 -user "$(id -u)" \( -name "*fastrtps*" -o -name "*fastdds*" \) -printf "%f\n" 2>/dev/null | sort; }
play() {
  shm_files > shm_before.txt
  ros2 bag play "/data/$1" --delay 3 --disable-keyboard-controls > "play_$1.txt" 2>&1 &
  local pid=$! new=0 rc=0
  for _ in $(seq 1 120); do
    new=$(shm_files | comm -13 shm_before.txt - | wc -l)
    [ "$new" -gt 0 ] && break
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
  wait "$pid" || rc=$?
  echo "PLAY bag=$1 rc=$rc new_shm_files=$new"
  sed "s/^/  play: /" "play_$1.txt" | tail -n 20
}
play "$CT_BAG1"
if [ -n "$CT_BAG2" ]; then sleep 5; play "$CT_BAG2"; fi
'

docker run -d --name resense_ct_node --net=host --ipc=host "$IMAGE" >/dev/null
READY=0
for _ in $(seq 1 60); do
  if docker logs resense_ct_node 2>&1 | grep -q "ReSense detector listening"; then
    READY=1
    break
  fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "ERROR: detector container did not become ready within 60 s" >&2
  docker logs resense_ct_node 2>&1 || true
  exit 3
fi
docker run -d --name resense_ct_echo --net=host --ipc=host -v "$OUT_ABS":/out "$IMAGE" \
  bash -c "ros2 topic echo /resense/status --field data > /out/status.jsonl" >/dev/null
if [ "$PLAYER_DDS" = stock ]; then
  docker run -d --name resense_ct_listen --net=host --ipc=host --user "$PLAYER_USER" -e HOME=/tmp \
    ${PLAYER_ARGS[@]+"${PLAYER_ARGS[@]}"} "$IMAGE" \
    bash -c "$STOCK_DDS
exec ros2 topic echo /resense/decision std_msgs/msg/String --field data" >/dev/null
fi
sleep 4
PLAY="ros2 bag play /data/$(basename "$BAG1") --delay 3 --disable-keyboard-controls"
if [ -n "$BAG2" ]; then
  PLAY="$PLAY; sleep 5; ros2 bag play /data/$(basename "$BAG2") --delay 3 --disable-keyboard-controls"
fi
echo "== playing as user $PLAYER_USER ($PLAYER_DDS Fast DDS settings) from a separate container: $(basename "$BAG1") ${BAG2:+then $(basename "$BAG2")}"
PLAYER_RC=0
if [ "$PLAYER_DDS" = stock ]; then
  docker run --rm --net=host --ipc=host --user "$PLAYER_USER" -e HOME=/tmp \
    -e CT_BAG1="$(basename "$BAG1")" -e CT_BAG2="${BAG2:+$(basename "$BAG2")}" \
    ${PLAYER_ARGS[@]+"${PLAYER_ARGS[@]}"} -v "$PARENT":/data:ro "$IMAGE" \
    bash -c "$STOCK_PLAYER" > "$OUT_ABS/player.log" 2>&1 || PLAYER_RC=$?
else
  docker run --rm --net=host --ipc=host --user "$PLAYER_USER" -e HOME=/tmp \
    ${PLAYER_ARGS[@]+"${PLAYER_ARGS[@]}"} -v "$PARENT":/data:ro "$IMAGE" \
    bash -c "$PLAY >/dev/null 2>&1"
fi
sleep 4
docker logs resense_ct_node > "$OUT_ABS/node.log" 2>&1
grep -E "input [0-9]+:|re-created|NO_INPUT|per-frame kernels" "$OUT_ABS/node.log" | cut -c1-220 || true

if [ $# -gt 0 ]; then
  CHECK_ARGS=("$@")
else
  CHECK_ARGS=(--expect-obstacle --min-frames 20 --max-p95-latency 1000 --max-dropped 100000)
  [ -n "$BAG2" ] && CHECK_ARGS+=(--expect-inputs 2)
fi
CHECK_RC=0
python3 scripts/check_dry_run.py "$OUT_ABS/status.jsonl" "${CHECK_ARGS[@]}" || CHECK_RC=$?
[ "$PLAYER_DDS" = stock ] || exit "$CHECK_RC"

# ---- PLAYER_DDS=stock: did the player run with stock Fast DDS, shared memory on, and was it heard?
docker logs resense_ct_listen > "$OUT_ABS/listener.log" 2>&1 || true
STOCK_FAIL=()
echo
echo "== stock Fast DDS client (uid ${PLAYER_USER%%:*}): player and listener without the image's profile"
grep -m1 "^DDS " "$OUT_ABS/player.log" | sed 's/^/player   /' || true
grep -m1 "^DDS " "$OUT_ABS/listener.log" | sed 's/^/listener /' || true
grep "^PLAY " "$OUT_ABS/player.log" || true
if ! grep -q "^DDS .*FASTRTPS_DEFAULT_PROFILES_FILE=unset FASTDDS_DEFAULT_PROFILES_FILE=unset .*profile_in_cwd=none" "$OUT_ABS/player.log"; then
  STOCK_FAIL+=("the player did not run without a Fast DDS XML profile (see $OUT/player.log)")
fi
# PLAY lines: "PLAY bag=<name> rc=<exit code> new_shm_files=<n>"
read -r N_PLAYS N_BAD N_NOSHM < <(awk '/^PLAY /{n++; if ($3 != "rc=0") bad++; if ($4 == "new_shm_files=0") noshm++}
                                      END {printf "%d %d %d\n", n, bad, noshm}' "$OUT_ABS/player.log")
N_WANT=1; [ -n "$BAG2" ] && N_WANT=2
if [ "$PLAYER_RC" -ne 0 ] || [ "$N_PLAYS" -ne "$N_WANT" ] || [ "$N_BAD" -ne 0 ]; then
  STOCK_FAIL+=("the player exited $PLAYER_RC; $N_PLAYS of $N_WANT plays ran, $N_BAD failed (see $OUT/player.log)")
fi
if grep -q "^DDS .*RMW_IMPLEMENTATION=rmw_fastrtps_cpp " "$OUT_ABS/player.log" && [ "$N_NOSHM" -ne 0 ]; then
  STOCK_FAIL+=("$N_NOSHM play(s) created no Fast DDS shared-memory file in /dev/shm: shared memory was not on in the player, so this run does not show the stock transports")
fi
N_DEC="$(grep -cxE "GO|CAUTION|STOP|FAULT" "$OUT_ABS/listener.log" || true)"
N_STOP="$(grep -cx "STOP" "$OUT_ABS/listener.log" || true)"
N_DEC="${N_DEC:-0}"; N_STOP="${N_STOP:-0}"
EXPECT_OBSTACLE=0
for a in "${CHECK_ARGS[@]}"; do
  if [ "$a" = "--expect-obstacle" ]; then EXPECT_OBSTACLE=1; fi
done
echo "listener /resense/decision: $N_DEC messages, $N_STOP STOP"
if [ "$N_DEC" -eq 0 ]; then
  STOCK_FAIL+=("the stock listener received no /resense/decision message (see $OUT/listener.log)")
elif [ "$N_STOP" -eq 0 ] && [ "$EXPECT_OBSTACLE" -eq 1 ]; then
  STOCK_FAIL+=("the stock listener never heard STOP although an obstacle is expected")
fi
if [ ${#STOCK_FAIL[@]} -gt 0 ]; then
  for f in "${STOCK_FAIL[@]}"; do echo "FAIL: $f"; done
  [ "$CHECK_RC" -ne 0 ] && exit "$CHECK_RC"
  exit 1
fi
echo "PASS: a stock Fast DDS player and listener (shared memory on) reached the UDP-only node"
exit "$CHECK_RC"
