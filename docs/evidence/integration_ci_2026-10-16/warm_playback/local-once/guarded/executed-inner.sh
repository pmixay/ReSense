source /opt/ros/humble/setup.bash
source /tmp/repro/ros2_ws/install/setup.bash
source /opt/resense/dds_transport.sh
resense_dds_transport
set -euo pipefail
ros2 launch resense_ros detector.launch.py rviz:=false freshness_mode:=replay >/out/node.log 2>&1 &
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

if [[ "$WARM_CACHE" == 1 ]]; then
  python3 scripts/check_warm_cache.py "/data/$BAG_NAME" --out /out/warm_cache_before.json
fi
ros2 bag play "/data/$BAG_NAME" --rate "$RATE" --clock --delay 3 \
  --read-ahead-queue-size "$BAG_READ_AHEAD_QUEUE_SIZE" --disable-keyboard-controls \
  2>&1 | tee /out/player.log   # --delay: let DDS discovery finish before the first frame
if [[ "$WARM_CACHE" == 1 ]]; then
  python3 scripts/check_warm_cache.py "/data/$BAG_NAME" --observe-only --out /out/warm_cache_after.json
fi
sleep 3        # let the last frames finish and one more stats tick land

kill "$ECHO_PID" "$LAUNCH_PID" 2>/dev/null || true
wait "$ECHO_PID" 2>/dev/null || true