#!/usr/bin/env bash
# Dataset-free end-to-end check of the ROS 2 node (docs/CAPTAIN.md item 10): play a synthetic bag
# through the node and assert the status stream. Runs INSIDE the image (needs ros2), e.g.
#
#   docker run --rm resense:ci bash -lc \
#       "python3 scripts/make_smoke_bag.py /tmp/smoke_bag && scripts/smoke_test.sh /tmp/smoke_bag"
#
# The bag (scripts/make_smoke_bag.py) holds a clear synthetic tunnel followed by the same tunnel
# with a person standing on the track at 60 m, so the check is: the node starts on the default
# command, the first frames are clear, the person is reported at 55-66 m, nothing was dropped.
# An optional second bag is played into the same running node after the first (the organizers,
# 23.09: the control data may use either topic / frame pair); CI makes it on
# /sensing/lidar/hesai128/pointcloud + lidar_livox with the person at 45 m and checks that the
# node took it as a new recording and reported the person in both.
#
# Environment: RATE (bag playback rate, default 0.5 because CI runners are slow), DELAY (s the
# player waits before publishing, default 3), OUT (capture directory, default /tmp/smoke_out),
# CHECK_ARGS (overrides the acceptance thresholds).
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v ros2 >/dev/null 2>&1; then
  echo "ERROR: ros2 is unavailable. Run smoke_test.sh inside the built ROS 2/Docker image;" >&2
  echo "       this script cannot provide a ROS acceptance result on the host." >&2
  exit 3
fi
BAG="${1:?usage: scripts/smoke_test.sh <bag directory> [<second bag directory>]}"
BAG2="${2:-}"
RATE="${RATE:-0.5}"
OUT="${OUT:-/tmp/smoke_out}"
mkdir -p "$OUT"
rm -f "$OUT/status.jsonl" "$OUT/node.log"

ros2 launch resense_ros detector.launch.py rviz:=false > "$OUT/node.log" 2>&1 &
LAUNCH_PID=$!
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT

# wait for the node before playing (the launch file's own bag:= argument races node startup)
READY=0
for _ in $(seq 1 90); do
  if ros2 topic list 2>/dev/null | grep -qx /resense/status; then
    READY=1
    break
  fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "detector exited during startup:" >&2; cat "$OUT/node.log" >&2; exit 3
  fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "detector never advertised /resense/status:" >&2; cat "$OUT/node.log" >&2; exit 3
fi

ros2 topic echo /resense/status --field data > "$OUT/status.jsonl" 2>/dev/null &
ECHO_PID=$!
sleep 3
# --delay: publishers exist for DELAY s before the first message, so DDS discovery with the node
# completes; without it the first 1-3 s of a bag are silently lost (13 frames in CI run 21).
ros2 bag play "$BAG" --rate "$RATE" --clock --delay "${DELAY:-3}" --disable-keyboard-controls
if [ -n "$BAG2" ]; then
  sleep 2        # > input_switch_timeout (1 s): the first recording has ended
  ros2 bag play "$BAG2" --rate "$RATE" --clock --delay "${DELAY:-3}" --disable-keyboard-controls
fi
sleep 4          # let the last frames finish and one more stats tick land
kill "$ECHO_PID" "$LAUNCH_PID" 2>/dev/null || true
wait "$ECHO_PID" 2>/dev/null || true

echo "== node.log (tail) =="
tail -n 12 "$OUT/node.log"
echo "== checking $OUT/status.jsonl =="
if [ -n "${CHECK_ARGS:-}" ]; then
  # shellcheck disable=SC2086
  python3 scripts/check_dry_run.py "$OUT/status.jsonl" $CHECK_ARGS
elif [ -n "$BAG2" ]; then
  python3 scripts/check_dry_run.py "$OUT/status.jsonl" --expect-obstacle --distance 40:66 \
      --first-clear 10 --min-frames 50 --max-dropped 6 --max-p95-latency 500 --expect-inputs 2
else
  python3 scripts/check_dry_run.py "$OUT/status.jsonl" --expect-obstacle --distance 55:66 \
      --first-clear 10 --min-frames 25 --max-dropped 3 --max-p95-latency 500
fi
