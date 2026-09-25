#!/bin/bash
# The README jury path with a stock ROS 2 Humble on the host (apt packages, no profile file):
# the node from the image's default command (README step 2), `ros2 bag play` from this normal
# user's console (step 3), /resense/decision and /resense/status echoed on the host (steps 4-5).
#   host_console.sh <name> <bag> [RMW for the host side]
set -u
NAME=$1; BAG=$2; RMW=${3:-}
cd ~/ReSense
OUT=${OUT:-$HOME/evidence/bench_2026-09-25}/host_${NAME}
mkdir -p "$OUT"; rm -f "$OUT"/*
set +u; source /opt/ros/humble/setup.bash; set -u
unset FASTRTPS_DEFAULT_PROFILES_FILE
if [ -n "$RMW" ]; then export RMW_IMPLEMENTATION=$RMW; else unset RMW_IMPLEMENTATION; fi
{ echo "host: $(id -un) uid $(id -u); RMW ${RMW_IMPLEMENTATION:-default (rmw_fastrtps_cpp)}; FASTRTPS_DEFAULT_PROFILES_FILE unset"
  echo "ros2: $(dpkg-query -W -f '${Version}' ros-humble-rosbag2 2>/dev/null) rosbag2, $(dpkg-query -W -f '${Version}' ros-humble-fastrtps 2>/dev/null) fastrtps"; } > "$OUT/setup.txt"
docker rm -f resense_host_node >/dev/null 2>&1
docker run -d --name resense_host_node --net=host --ipc=host ${RESENSE_NATIVE:+-e RESENSE_NATIVE=$RESENSE_NATIVE} resense >/dev/null
for _ in $(seq 1 60); do docker logs resense_host_node 2>&1 | grep -q "ReSense detector listening" && break; sleep 1; done
ros2 topic echo /resense/decision --field data > "$OUT/decision.txt" 2>"$OUT/echo_err.txt" &
E1=$!
ros2 topic echo /resense/status --field data > "$OUT/status.jsonl" 2>>"$OUT/echo_err.txt" &
E2=$!
sleep 4
T0=$(date +%s.%N)
ros2 bag play "$BAG" --delay 3 --disable-keyboard-controls > "$OUT/play.txt" 2>&1
echo "player exit $? after $(echo "$(date +%s.%N) - $T0" | bc) s" >> "$OUT/play.txt"
sleep 3
kill $E1 $E2 2>/dev/null; wait $E1 $E2 2>/dev/null
docker logs resense_host_node > "$OUT/node.log" 2>&1
docker rm -f resense_host_node >/dev/null
grep -v -- '^---$' "$OUT/decision.txt" | uniq -c > "$OUT/decision_runs.txt"
if [ "$(basename "$BAG")" = doubleT_obstacle ]; then
  python3 scripts/check_dry_run.py "$OUT/status.jsonl" --expect-obstacle --distance 50:62 --max-p95-latency 100 --max-dropped 0 > "$OUT/check.txt" 2>&1
else
  python3 scripts/check_dry_run.py "$OUT/status.jsonl" --expect-clear --max-alarm-frames 2 --max-p95-latency 100 --max-dropped 0 > "$OUT/check.txt" 2>&1
fi
echo "host_$NAME: $(grep -E '^(PASS|FAIL)' "$OUT/check.txt" | tr '\n' ' ')"
