#!/usr/bin/env bash
# the inner part of scripts/dry_run.sh (OFFLINE=1), with extra launch arguments; page cache dropped first
set -u
cd /home/user/ReSense
NAME=$1; shift; OUT=/tmp/claude-0/work/$NAME; mkdir -p $OUT; rm -f $OUT/status.jsonl $OUT/node.log
BAG=/home/user/data/for_hackathon/doubleT_obstacle
case "$NAME" in *warm*) cat $BAG/*.db3 > /dev/null ;; *) sync; echo 3 > /proc/sys/vm/drop_caches ;; esac
docker run --rm -i --network none -v /home/user/data/for_hackathon:/data:ro -v $OUT:/out \
  -e BAG_NAME=doubleT_obstacle -e RATE=1.0 -e LAUNCH_ARGS="$*" resense:latest bash -s <<'INNER'
set -euo pipefail
ros2 launch resense_ros detector.launch.py rviz:=false $LAUNCH_ARGS >/out/node.log 2>&1 &
LAUNCH_PID=$!
for _ in $(seq 1 60); do ros2 topic list 2>/dev/null | grep -qx /resense/status && break; sleep 1; done
ros2 topic echo /resense/status --field data >/out/status.jsonl 2>/dev/null &
ECHO_PID=$!
sleep 2
ros2 bag play "/data/$BAG_NAME" --rate "$RATE" --clock --delay 3 --disable-keyboard-controls
sleep 3
kill "$ECHO_PID" "$LAUNCH_PID" 2>/dev/null || true
wait "$ECHO_PID" 2>/dev/null || true
INNER
python3 scripts/check_dry_run.py $OUT/status.jsonl --expect-obstacle --distance 50:62 --max-p95-latency 100 --max-dropped 0 --bag $BAG > $OUT/check.txt 2>&1
echo "check exit $?"; tail -14 $OUT/check.txt
